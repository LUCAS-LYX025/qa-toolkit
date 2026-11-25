"""IP/域名查询工具专项审计回归（#291-#310）。"""
from __future__ import annotations

import io
import sys
import time
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from qa_toolkit.core import ip_lookup_registry as registry  # noqa: E402
from qa_toolkit.tools.ip_lookup import IPQueryTool  # noqa: E402
from qa_toolkit.ui.pages.ip_lookup_page import (  # noqa: E402
    _build_batch_row,
    _prepare_batch_targets,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_ip_lookup_registry()
    yield
    registry.reset_ip_lookup_registry()


class MockResponse:
    def __init__(self, text="", json_data=None, status_code=200):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        if self._json_data is None:
            raise ValueError("no json")
        return self._json_data

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def _script(extra: str = "") -> str:
    # AppTest 在同一 Python 进程内执行脚本，直接给类方法赋值会污染后续测试。
    # 用 try/finally 在每次脚本执行结束后还原，保证跨文件回归互不干扰。
    return f"""
import sys
sys.path.insert(0, {str(SRC)!r})
from qa_toolkit.core import ip_lookup_registry as reg
{extra}
from qa_toolkit.tools.ip_lookup import IPQueryTool
from qa_toolkit.ui.pages.ip_lookup_page import render_ip_lookup_page

_ORIGINAL_METHODS = {{
    name: getattr(IPQueryTool, name)
    for name in ("get_ip_domain_info", "query_subdomains", "query_reverse_sites", "query_icp_info")
}}

IPQueryTool.get_ip_domain_info = lambda self, target, *a, **k: {{
    "success": True,
    "data": {{
        "输入类型": "域名", "域名": str(target).strip(), "结果状态": "成功",
        "国家": "中国", "省份": "北京", "城市": "北京", "运营商": "测试", "ASN信息": "AS64500",
    }},
}}
IPQueryTool.query_subdomains = lambda self, target, *a, **k: {{
    "success": True, "status": "partial",
    "data": {{"查询状态": "partial", "错误信息": "一个来源失败", "结果": [{{"子域名": "api.example.com"}}]}},
}}
IPQueryTool.query_reverse_sites = lambda self, target, *a, **k: {{"success": True, "status": "ok", "data": {{"结果": []}}}}
IPQueryTool.query_icp_info = lambda self, target, *a, **k: {{"success": True, "status": "ok", "data": {{"备案号": "测试"}}}}

try:
    render_ip_lookup_page()
finally:
    for _name, _method in _ORIGINAL_METHODS.items():
        setattr(IPQueryTool, _name, _method)
"""


def _app(extra: str = "") -> AppTest:
    return AppTest.from_string(_script(extra), default_timeout=5)


def test_ip01_loopback_and_linklocal_are_classified_correctly():
    tool = IPQueryTool()
    assert tool.get_detailed_location("127.0.0.1")["province"] == "回环网络"
    assert tool.get_detailed_location("169.254.10.1")["province"] == "链路本地"
    assert tool.get_detailed_location("192.168.1.10")["province"] == "私有IP"


def test_ip02_credentials_are_redacted_in_parse_and_info():
    tool = IPQueryTool()
    parsed = tool.parse_target_input("https://user:s3cr3t@example.com/login")
    assert parsed["success"] is True
    assert "s3cr3t" not in parsed["data"]["original_input"]
    assert "已隐藏" in " ".join(parsed["data"]["notes"])
    info = tool.get_ip_domain_info("example.com", parsed_target=parsed["data"])
    assert "s3cr3t" not in str(info["data"])


@pytest.mark.parametrize("target", ["https://example.com:99999/path", "https://example.com:0/path", "https://example.com:abc/path"])
def test_ip03_invalid_ports_are_rejected(target):
    result = IPQueryTool().parse_target_input(target)
    assert result["success"] is False
    assert "端口" in result["error"]


@pytest.mark.parametrize("target", ["javascript:alert(1)", "mailto:user@example.com", "ftp://example.com/file"])
def test_ip04_unsupported_schemes_are_rejected(target):
    result = IPQueryTool().parse_target_input(target)
    assert result["success"] is False
    assert "协议" in result["error"]


def test_ip05_dns_timeout_guard_returns_partial_result_fast():
    registry.configure_ip_lookup_limits(dns_timeout_seconds=0.2)
    tool = IPQueryTool()

    def slow_addrinfo(host, port, *args, **kwargs):
        time.sleep(0.6)
        return [(2, 1, 6, "", ("93.184.216.34", 0))]

    started = time.monotonic()
    with mock.patch("qa_toolkit.tools.ip_lookup.socket.gethostbyname_ex", side_effect=RuntimeError("skip")), \
            mock.patch("qa_toolkit.tools.ip_lookup.socket.getaddrinfo", side_effect=slow_addrinfo), \
            mock.patch("qa_toolkit.tools.ip_lookup.socket.getfqdn", side_effect=RuntimeError("skip")):
        result = tool.resolve_domain_records("slow.example.com")
    assert time.monotonic() - started < 0.5
    assert "getaddrinfo 查询超时" in result["解析提示"]


def test_ip06_geo_cache_avoids_duplicate_requests():
    tool = IPQueryTool()
    calls = {"n": 0}

    def fake_get(url, timeout=8, headers=None, **kwargs):
        calls["n"] += 1
        assert kwargs.get("allow_redirects") is False
        return MockResponse(json_data={"country_name": "美国", "region": "CA", "city": "Mountain View", "org": "Google"})

    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        tool.clear_cache()
        first = tool.get_detailed_location("8.8.8.8")
        second = tool.get_detailed_location("8.8.8.8")
    assert calls["n"] == 1
    assert first["country"] == second["country"] == "美国"


def test_ip07_public_ip_cache_and_https_only_services():
    tool = IPQueryTool()
    calls = {"n": 0}

    def fake_get(url, timeout=5, headers=None, **kwargs):
        calls["n"] += 1
        assert str(url).startswith("https://")
        return MockResponse(text="8.8.8.8", json_data={"ip": "8.8.8.8"})

    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        tool.clear_cache()
        assert tool.get_public_ip() == "8.8.8.8"
        after_first = calls["n"]
        assert tool.get_public_ip() == "8.8.8.8"
        assert tool.get_public_ip() == "8.8.8.8"
    # 首个 HTTPS 服务即成功，后续两次查询必须完全命中缓存，不再发起请求。
    assert after_first == 1
    assert calls["n"] == after_first


def test_ip08_subdomain_all_sources_failed_is_not_success():
    def fake_get(url, timeout=15, headers=None, **kwargs):
        raise RuntimeError("source down")

    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        result = IPQueryTool().query_subdomains("example.com")
    assert result["success"] is False
    assert result["status"] == "failed"
    assert "所有数据源均失败" in result["error"]


def test_ip09_invalid_limit_falls_back_to_default():
    payload = [{"name_value": "\n".join(f"h{i}.example.com" for i in range(300))}]

    def fake_get(url, timeout=15, headers=None, **kwargs):
        return MockResponse(json_data=payload) if "crt.sh" in url else MockResponse(text="")

    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        result = IPQueryTool().query_subdomains("example.com", limit=-1)
    assert result["data"]["子域名数量"] == registry.get_ip_lookup_limits().subdomain_limit


def test_ip10_icp_error_code_is_not_accepted():
    def fake_get(url, timeout=15, headers=None, **kwargs):
        return MockResponse(json_data={"code": 401, "message": "invalid key", "data": {"DomainIcpNum": "假备案号"}})

    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        result = IPQueryTool().query_icp_info("example.com")
    assert result["success"] is False
    assert "401" in result["error"]
    assert "假备案号" not in str(result)


def test_ip11_asn_inference_is_labeled():
    tool = IPQueryTool()
    assert "[根据域名推断]" in tool.get_asn_info("fake-google-host.example")
    assert "[根据IP段推断]" in tool._get_asn_from_local("8.8.8.8")


def test_ip12_batch_csv_cells_are_formula_safe():
    formula = '=HYPERLINK("http://evil.test","click")'
    row = _build_batch_row(formula, {"success": False, "error": "输入无效"})
    assert row["输入"].startswith("'=")
    csv_text = pd.DataFrame([row]).to_csv(index=False).encode("utf-8-sig").decode("utf-8-sig")
    assert not csv_text.splitlines()[1].split(",")[0].lstrip('"').startswith("=")


def test_ip13_stale_single_result_shows_warning():
    app = _app().run()
    assert not app.exception, [item.value for item in app.exception]
    app.text_input(key="ip_lookup_single_input").set_value("8.8.8.8").run()
    app.button(key="ip_lookup_single_button").click().run()
    app.text_input(key="ip_lookup_single_input").set_value("1.1.1.1").run()
    assert any("结果可能已过期" in item.value for item in app.markdown)


def test_ip14_partial_asset_status_shows_warning():
    app = _app().run()
    app.text_input(key="ip_lookup_asset_input").set_value("example.com").run()
    app.button(key="ip_lookup_subdomains").click().run()
    assert not app.exception, [item.value for item in app.exception]
    assert any("部分数据源失败" in item.value for item in app.markdown)


def test_ip15_geo_provider_registration_is_https_only_and_callable():
    with pytest.raises(ValueError, match="HTTPS"):
        registry.register_geo_provider("local", "本地", "http://example.com/{ip}", lambda payload, ctx: {})
    calls = {"n": 0}

    def parser(payload, ctx):
        calls["n"] += 1
        return {"country": "测试国", "province": "测试省", "city": "测试市", "isp": "测试ISP", "location": "测试"}

    registry.register_geo_provider("custom", "自定义源", "https://geo.example/{ip}", parser, priority=1)
    tool = IPQueryTool()
    assert "custom" in tool.ip_apis
    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", return_value=MockResponse(json_data={"ok": True})):
        result = tool.get_detailed_location("8.8.8.8")
    assert result["_source"] == "自定义源"
    assert calls["n"] == 1


def test_ip16_public_ip_service_registration():
    registry.unregister_public_ip_service("ipify")
    registry.unregister_public_ip_service("identme")
    registry.unregister_public_ip_service("amazonaws")
    registry.unregister_public_ip_service("ifconfigme")
    registry.register_public_ip_service(
        "custom", "https://ip.example/current", response_type="json", json_path="address", priority=1
    )
    tool = IPQueryTool()
    with mock.patch("qa_toolkit.tools.ip_lookup.requests.get", return_value=MockResponse(json_data={"address": "1.1.1.1"})):
        assert tool.get_public_ip() == "1.1.1.1"


def test_ip17_conversion_types_are_registry_driven():
    registry.register_conversion_type("仅看十进制", ("十进制",))
    tool = IPQueryTool()
    result = tool.convert_ip_address("0x08080808", "仅看十进制")
    assert result["success"] is True
    assert set(result["data"]) == {"识别格式", "十进制"}
    app = _app().run()
    options = [option for select in app.selectbox for option in select.options]
    assert "仅看十进制" in options


def test_ip18_suffix_port_and_country_registration():
    registry.register_suffix("example.test")
    registry.register_service_name(9000, "CUSTOM-SVC")
    registry.register_country_name("XX", "测试国")
    tool = IPQueryTool()
    assert tool.get_registered_domain("a.b.example.test") == "b.example.test"
    assert tool._get_service_name(9000) == "CUSTOM-SVC"
    assert tool._get_country_name("xx") == "测试国"


def test_ip19_asset_actions_are_registry_driven():
    extra = 'reg.register_asset_action("extra", "查询 WHOIS", "ip_lookup_whois", "query_subdomains", priority=1, replace=True)'
    app = _app(extra).run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.button(key="ip_lookup_whois")
    app.text_input(key="ip_lookup_asset_input").set_value("example.com").run()
    app.button(key="ip_lookup_whois").click().run()
    assert not app.exception, [item.value for item in app.exception]
    assert app.session_state["ip_lookup_asset_action"] == "extra"


def test_ip20_limits_are_configurable_and_validated():
    registry.configure_ip_lookup_limits(max_batch_targets=2)
    targets = _prepare_batch_targets("a.example\nb.example\nc.example")
    assert len(targets) == 2
    with pytest.raises(ValueError, match="正数"):
        registry.configure_ip_lookup_limits(max_batch_targets=0)
