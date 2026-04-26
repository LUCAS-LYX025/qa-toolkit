import socket
import sys
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.tools.ip_lookup import IPQueryTool


class MockResponse:
    def __init__(self, text="", json_data=None, status_code=200):
        self.text = text
        self._json_data = json_data
        self.status_code = status_code

    def json(self):
        if self._json_data is not None:
            return self._json_data
        raise ValueError("No JSON payload")

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_parse_target_input_extracts_host_port_and_path_from_url():
    tool = IPQueryTool()

    result = tool.parse_target_input("https://Example.com:8443/login?a=1#frag")

    assert result["success"] is True
    data = result["data"]
    assert data["normalized_target"] == "example.com"
    assert data["target_type"] == "域名"
    assert data["scheme"] == "https"
    assert data["port"] == 8443
    assert data["path"] == "/login"
    assert data["query"] == "a=1"
    assert data["fragment"] == "frag"


def test_parse_target_input_supports_bracketed_ipv6_with_port():
    tool = IPQueryTool()

    result = tool.parse_target_input("https://[2606:4700:4700::1111]:443/dns-query")

    assert result["success"] is True
    data = result["data"]
    assert data["target_type"] == "IP地址"
    assert data["normalized_target"] == "2606:4700:4700::1111"
    assert data["port"] == 443
    assert data["path"] == "/dns-query"


def test_get_ip_domain_info_for_domain_includes_dns_and_network_data():
    tool = IPQueryTool()
    parsed = tool.parse_target_input("https://Example.com:8443/login")

    fake_addrinfo = [
        (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 0)),
        (socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("2606:2800:220:1:248:1893:25c8:1946", 0, 0, 0)),
    ]
    fake_location = {
        "country": "美国",
        "province": "California",
        "city": "Los Angeles",
        "isp": "Example CDN",
        "location": "美国 California Los Angeles",
        "asn": "AS15133",
        "timezone": "America/Los_Angeles",
    }

    with patch("qa_toolkit.tools.ip_lookup.socket.gethostbyname_ex", return_value=("edge.example.com", ["www.example.com"], ["93.184.216.34"])), \
            patch("qa_toolkit.tools.ip_lookup.socket.getaddrinfo", return_value=fake_addrinfo), \
            patch("qa_toolkit.tools.ip_lookup.socket.getfqdn", return_value="edge.example.com"), \
            patch.object(IPQueryTool, "get_detailed_location", return_value=fake_location):
        result = tool.get_ip_domain_info(
            parsed["data"]["normalized_target"],
            parsed["data"]["is_ip"],
            parsed_target=parsed["data"],
        )

    assert result["success"] is True
    data = result["data"]
    assert data["域名"] == "example.com"
    assert data["端口"] == 8443
    assert data["解析状态"] == "成功"
    assert data["解析IP"] == "93.184.216.34"
    assert data["A记录"] == "93.184.216.34"
    assert "2606:2800:220:1:248:1893:25c8:1946" in data["AAAA记录"]
    assert data["ASN信息"] == "AS15133 (Example CDN)"
    assert data["网络段"] == "93.184.216.0/24"


def test_convert_ip_address_auto_detects_and_returns_all_formats():
    tool = IPQueryTool()

    result = tool.convert_ip_address("0x08080808", "自动识别并展示全部格式")

    assert result["success"] is True
    data = result["data"]
    assert data["识别格式"] == "十六进制"
    assert data["点分十进制"] == "8.8.8.8"
    assert data["十进制"] == "134744072"
    assert data["十六进制"] == "0x08080808"
    assert data["二进制"] == "00001000.00001000.00001000.00001000"


def test_convert_ip_address_rejects_decimal_out_of_ipv4_range():
    tool = IPQueryTool()

    result = tool.convert_ip_address("4294967296", "十进制 ↔ 点分十进制")

    assert result["success"] is False
    assert "超出 IPv4 范围" in result["error"]


def test_ip_data_sources_are_https_only():
    tool = IPQueryTool()

    assert tool.ip_apis
    assert all(str(url).startswith("https://") for url in tool.ip_apis.values())


def test_get_detailed_location_includes_source_and_fallback_notes():
    tool = IPQueryTool()
    tool._source_last_error["ipapi"] = "timeout"
    tool._source_failures["ipapi"] = 1

    with patch.object(
        IPQueryTool,
        "_query_ip_api",
        side_effect=[
            None,
            {
                "country": "美国",
                "province": "California",
                "city": "Los Angeles",
                "isp": "Example ISP",
                "location": "美国 California Los Angeles",
                "asn": "AS15169",
                "timezone": "America/Los_Angeles",
            },
        ],
    ):
        result = tool.get_detailed_location("8.8.8.8")

    assert result["_source"] == tool.SOURCE_LABELS["ipinfo"]
    assert "ipapi.co" in result.get("_fallback_notes", "")


def test_get_ip_domain_info_exposes_geo_source_and_downgrade_note():
    tool = IPQueryTool()
    parsed = tool.parse_target_input("8.8.8.8")

    with patch.object(
        IPQueryTool,
        "get_detailed_location",
        return_value={
            "country": "美国",
            "province": "California",
            "city": "Los Angeles",
            "isp": "Example ISP",
            "location": "美国 California Los Angeles",
            "asn": "AS15169",
            "timezone": "America/Los_Angeles",
            "_source": "ipinfo.io (HTTPS)",
            "_fallback_notes": "ipapi.co (HTTPS) 失败: timeout",
        },
    ), patch.object(IPQueryTool, "get_rdns_info", return_value={"success": False, "error": "mock"}), patch(
        "qa_toolkit.tools.ip_lookup.socket.getfqdn",
        return_value="dns.google",
    ):
        result = tool.get_ip_domain_info(
            parsed["data"]["normalized_target"],
            parsed["data"]["is_ip"],
            parsed_target=parsed["data"],
        )

    assert result["success"] is True
    data = result["data"]
    assert data["地理数据来源"] == "ipinfo.io (HTTPS)"
    assert "timeout" in data["来源降级说明"]


def test_query_subdomains_merges_crtsh_and_hostsearch_results():
    tool = IPQueryTool()

    def fake_get(url, timeout=15, headers=None):
        if "crt.sh" in url:
            return MockResponse(json_data=[
                {
                    "common_name": "*.example.com",
                    "name_value": "*.example.com\napi.example.com\nwww.example.com",
                }
            ])
        if "hostsearch" in url:
            return MockResponse(text="www.example.com,104.18.26.120\ncdn.example.com,104.18.27.120\n")
        raise AssertionError(f"unexpected url: {url}")

    with patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        result = tool.query_subdomains("https://example.com/login")

    assert result["success"] is True
    data = result["data"]
    assert data["查询目标"] == "example.com"
    assert data["可注册主域"] == "example.com"
    assert data["子域名数量"] == 3
    assert [item["子域名"] for item in data["结果"]] == [
        "api.example.com",
        "cdn.example.com",
        "www.example.com",
    ]
    assert data["结果"][-1]["解析IP"] == "104.18.26.120"


def test_query_reverse_sites_resolves_domain_then_parses_hostnames():
    tool = IPQueryTool()

    def fake_get(url, timeout=15, headers=None):
        if "reverseiplookup" in url:
            return MockResponse(text="a.example.net\nb.example.net\na.example.net\n")
        raise AssertionError(f"unexpected url: {url}")

    with patch.object(IPQueryTool, "resolve_domain_records", return_value={"preferred_ip": "93.184.216.34"}), \
            patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        result = tool.query_reverse_sites("https://www.example.com")

    assert result["success"] is True
    data = result["data"]
    assert data["查询IP"] == "93.184.216.34"
    assert data["旁站数量"] == 2
    assert data["结果"] == [{"站点域名": "a.example.net"}, {"站点域名": "b.example.net"}]


def test_query_icp_info_uses_registered_domain_and_parses_payload():
    tool = IPQueryTool()

    def fake_get(url, timeout=15, headers=None):
        assert "baidu.com" in url
        return MockResponse(json_data={
            "code": 200,
            "from": "cache",
            "data": {
                "CompanyName": "北京百度网讯科技有限公司",
                "CompanyType": "企业",
                "DomainIcpNum": "京ICP证030173号-1",
                "WebsiteName": "-",
                "WebsiteHomeUrl": "-",
                "AuditTime": "2019-05-16",
                "Domain": "baidu.com",
                "InTencent": False,
            },
        })

    with patch("qa_toolkit.tools.ip_lookup.requests.get", side_effect=fake_get):
        result = tool.query_icp_info("https://www.baidu.com")

    assert result["success"] is True
    data = result["data"]
    assert data["查询域名"] == "www.baidu.com"
    assert data["备案主域"] == "baidu.com"
    assert data["备案号"] == "京ICP证030173号-1"
    assert data["主办单位"] == "北京百度网讯科技有限公司"
    assert data["官方核验"] == tool.MIIT_ICP_VERIFY_URL
