import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

IP_LOOKUP_PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})

from qa_toolkit.tools.ip_lookup import IPQueryTool


def _fake_single_result(target):
    normalized = str(target or "").strip()
    return {{
        "success": True,
        "data": {{
            "输入类型": "IP地址" if normalized.count(".") == 3 else "域名",
            "IP地址": normalized if normalized.count(".") == 3 else "203.0.113.10",
            "解析IP": normalized if normalized.count(".") == 3 else "203.0.113.10",
            "域名": "" if normalized.count(".") == 3 else normalized,
            "国家": "中国",
            "省份": "北京",
            "城市": "北京",
            "运营商": "测试运营商",
            "ASN信息": "AS64500",
        }},
    }}


IPQueryTool.get_public_ip = lambda self: "1.1.1.1"
IPQueryTool.get_ip_domain_info = lambda self, target, *args, **kwargs: _fake_single_result(target)
IPQueryTool.convert_ip_address = lambda self, value, mode: {{
    "success": True,
    "data": {{
        "输入": value,
        "模式": mode,
        "点分十进制": "8.8.8.8",
        "十进制": "134744072",
    }},
}}
IPQueryTool.query_subdomains = lambda self, target: {{
    "success": True,
    "data": {{
        "结果": [{{"子域名": "api.example.com", "解析IP": "203.0.113.10", "来源": "mock"}}],
        "查询目标": target,
    }},
}}
IPQueryTool.query_reverse_sites = lambda self, target: {{
    "success": True,
    "data": {{
        "结果": [{{"站点域名": "site-a.example.com"}}],
        "查询IP": "203.0.113.10",
    }},
}}
IPQueryTool.query_icp_info = lambda self, target: {{
    "success": True,
    "data": {{
        "查询域名": target,
        "备案号": "京ICP证000001号",
        "主办单位": "测试公司",
    }},
}}

from qa_toolkit.ui.pages.ip_lookup_page import render_ip_lookup_page

render_ip_lookup_page()
"""


def _build_app() -> AppTest:
    return AppTest.from_string(IP_LOOKUP_PAGE_SCRIPT, default_timeout=5)


def _assert_no_exceptions(app: AppTest) -> None:
    assert not app.exception, [item.value for item in app.exception]


def test_ip_lookup_page_public_ip_backfill_and_single_query_do_not_raise() -> None:
    app = _build_app().run()
    _assert_no_exceptions(app)

    app.button(key="ip_lookup_public_ip").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["ip_lookup_single_input"] == "1.1.1.1"

    app.button(key="ip_lookup_single_button").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["ip_lookup_single_result"]["data"]["IP地址"] == "1.1.1.1"


def test_ip_lookup_page_batch_convert_and_asset_actions_do_not_raise() -> None:
    app = _build_app().run()
    _assert_no_exceptions(app)

    app.text_area(key="ip_lookup_batch_text").set_value("8.8.8.8\nexample.com\n8.8.8.8").run()
    app.button(key="ip_lookup_batch_button").click().run()
    _assert_no_exceptions(app)
    assert len(app.session_state["ip_lookup_batch_result"]) == 2

    app.text_input(key="ip_lookup_convert_input").set_value("0x08080808").run()
    app.button(key="ip_lookup_convert_button").click().run()
    _assert_no_exceptions(app)

    app.text_input(key="ip_lookup_asset_input").set_value("example.com").run()

    app.button(key="ip_lookup_subdomains").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["ip_lookup_asset_label"] == "子域名查询"

    app.button(key="ip_lookup_reverse").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["ip_lookup_asset_label"] == "旁站查询"

    app.button(key="ip_lookup_icp").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["ip_lookup_asset_label"] == "ICP备案查询"
