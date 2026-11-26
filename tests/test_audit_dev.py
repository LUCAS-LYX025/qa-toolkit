"""接口研发辅助工具专项审计回归：逐条对应 GitHub Issues #357-#387（DEV-01 ~ DEV-31）。

视角：测试专家（正确性/安全性/边界）+ 产品工程师（拓展性/易用性），不局限于当前业务。
DEV-01 ~ DEV-21 为第一轮注册式重构，DEV-22 ~ DEV-31 为重构后二次走查新发现的问题。
"""
import ast
import json
import math
import sys
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import api_dev_registry as dev_reg  # noqa: E402
from qa_toolkit.core import api_test_core as test_core_mod  # noqa: E402
from qa_toolkit.core.api_dev_registry import StatusCodeBucketSpec  # noqa: E402
from qa_toolkit.core.api_dev_tools import InterfaceDevTools  # noqa: E402
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore  # noqa: E402
from qa_toolkit.ui.pages import api_dev_tools_page as page  # noqa: E402

CORE_SRC = (ROOT / "src/qa_toolkit/core/api_dev_tools.py").read_text(encoding="utf-8")
PAGE_SRC = (ROOT / "src/qa_toolkit/ui/pages/api_dev_tools_page.py").read_text(encoding="utf-8")
REG_SRC = (ROOT / "src/qa_toolkit/core/api_dev_registry.py").read_text(encoding="utf-8")
TEST_CORE_SRC = (ROOT / "src/qa_toolkit/core/api_test_core.py").read_text(encoding="utf-8")

BASE = {
    "name": "下单",
    "method": "POST",
    "path": "/orders",
    "description": "创建订单",
    "headers": {"Content-Type": "application/json"},
    "body": {"count": 1, "enabled": True, "note": None},
    "expected_status": 200,
    "expected_response": {"ok": True},
    "tags": ["order"],
}


@pytest.fixture(autouse=True)
def _reset_registry():
    dev_reg.reset_dev_registry()
    yield
    dev_reg.reset_dev_registry()


@pytest.fixture
def tool():
    return InterfaceDevTools()


# ---------------------------------------------------------------------------
# 第一轮：注册式重构（#357-#377）
# ---------------------------------------------------------------------------

def test_dev_01_python_snippet_verifies_ssl_by_default(tool):
    """#357 调试代码默认必须校验 SSL，不再输出 verify=False。"""
    snippet = tool.generate_request_snippet(BASE, "Python requests", "https://api.example.com")
    assert "verify=True" in snippet
    assert "verify=False" not in snippet
    assert "timeout=" in snippet
    assert dev_reg.get_dev_limits().verify_ssl_by_default is True


def test_dev_02_method_whitelist_blocks_python_injection(tool):
    """#358 method 走白名单，上传文档里的恶意 method 不能注入 Python 代码。"""
    evil = dict(BASE, method="GET\nimport os; os.system('echo PWNED')\nrequests.get")
    snippet = tool.generate_request_snippet(evil, "Python requests", "https://api.example.com")
    assert "os.system" not in snippet
    assert "requests.get(" in snippet
    assert any("非法 HTTP 方法" in item for item in tool.get_warnings())
    assert "requests.request(" in REG_SRC  # 未注册方法走参数化调用


def test_dev_03_unknown_language_is_explicit_not_silent(tool):
    """#359 未知语言必须明确告警，不能静默回落 Python。"""
    result = tool.generate_request_snippet(BASE, "Go", "https://api.example.com")
    assert "import requests" not in result
    assert "未知代码类型" in result
    assert any("未知代码类型" in item for item in tool.get_warnings())


def test_dev_04_path_params_are_url_encoded(tool):
    """#360 占位符值必须整体编码，不能篡改路径或注入 query。"""
    iface = dict(BASE, path="/api/users/{id}", path_params={"id": "1/../../admin?debug=1#frag"})
    snippet = tool.generate_request_snippet(iface, "curl", "https://api.example.com")
    assert "../../admin" not in snippet
    assert "%2F" in snippet and "%3F" in snippet
    raw = tool.generate_request_snippet(
        dict(BASE, path="/api/{id}", path_params={"id": "raw:a/b"}),
        "curl", "https://api.example.com")
    assert "/api/a/b" in raw


def test_dev_05_query_params_preserve_duplicate_keys_and_lists(tool):
    """#361 同名 query 追加、list doseq 展开、路径自带 query 不丢。"""
    iface = dict(BASE, path="/api?tag=a&tag=b", query_params={"tag": ["c", "d"]})
    snippet = tool.generate_request_snippet(iface, "curl", "https://api.example.com")
    for value in ("tag=a", "tag=b", "tag=c", "tag=d"):
        assert value in snippet
    assert snippet.count("?") == 1


def test_dev_06_dangerous_base_url_is_rejected(tool):
    """#362 file:// / 内网地址不能生成调试代码。"""
    blocked = tool.generate_request_snippet(BASE, "curl", "file:///etc/passwd")
    assert "校验失败" in blocked
    assert "curl -X" not in blocked
    private = tool.generate_request_snippet(BASE, "curl", "http://169.254.169.254/latest/meta-data/")
    assert "校验失败" in private
    assert "curl -X" not in private


def test_dev_07_mock_custom_headers_are_not_silently_dropped(tool):
    """#363 自定义响应头要么显式告警，要么经注册白名单透传。"""
    merged, warnings = dev_reg.build_mock_response_headers(
        {"X-Rate-Limit": "100", "Content-Type": "application/json"}, {"a": 1})
    assert "X-Rate-Limit" not in merged
    assert any("X-Rate-Limit" in item for item in warnings)
    dev_reg.register_mock_header_allowlist("X-Rate-Limit")
    merged2, warnings2 = dev_reg.build_mock_response_headers({"X-Rate-Limit": "100"}, {"a": 1})
    assert merged2["X-Rate-Limit"] == "100"
    assert not warnings2


def test_dev_08_mock_script_has_resource_guards(tool):
    """#364 生成的 Mock 服务必须带请求体/响应体/头/路由上限。"""
    script = tool.generate_mock_server_script([BASE])
    compile(script, "<mock>", "exec")
    for marker in ("MAX_REQUEST_BODY_BYTES", "MAX_RESPONSE_BODY_CHARS",
                   "MAX_HEADER_VALUE_CHARS", "MAX_ROUTES", "route limit exceeded"):
        assert marker in script


def test_dev_09_crlf_header_injection_is_filtered(tool):
    """#365 CRLF/控制字符头必须被拒绝并写入告警。"""
    snippet = tool.generate_request_snippet(
        dict(BASE, headers={"X-Test": "a\r\nInjected: 1"}), "curl", "https://api.example.com")
    assert "\r\nInjected" not in snippet
    assert "Injected: 1" not in snippet
    assert any("请求头" in item for item in tool.get_warnings())


def test_dev_10_mock_defaults_and_port_feedback(tool):
    """#366 默认监听 127.0.0.1、安全 CORS 来源、非法端口明确反馈。"""
    script = tool.generate_mock_server_script([BASE])
    assert "DEFAULT_HOST = '127.0.0.1'" in script
    assert "DEFAULT_PORT = 8000" in script
    assert "CORS_ORIGIN = 'http://localhost:3000'" in script
    assert "0.0.0.0" not in script
    assert "shlex.quote" in PAGE_SRC
    bad = InterfaceDevTools()
    bad.generate_mock_server_script([BASE], port="abc")
    assert any("不是合法整数" in item for item in bad.get_warnings())
    large = InterfaceDevTools()
    large.generate_mock_server_script([BASE], delay_ms=10 ** 9)
    assert any("钳制" in item for item in large.get_warnings())


def test_dev_11_cyclic_reference_and_assertion_style_are_safe(tool):
    """#367 循环引用不崩溃，断言风格与深度有注册式兜底。"""
    cyclic = {}
    cyclic["self"] = cyclic
    normalized = tool._normalize_interface(dict(BASE, body=cyclic))
    assert normalized["body"]["self"] == {}
    assert any("循环引用" in item for item in tool.get_warnings())
    template = tool.generate_assertion_template('{"a":1}', template_style="未知风格")
    assert template["template_style"] in dev_reg.get_assertion_styles().values()
    shallow = tool.generate_assertion_template('{"a":{"b":1}}', max_depth=-1)
    assert shallow["field_count"] >= 0


def test_dev_12_markdown_and_structured_text_are_escaped(tool):
    """#368 恶意名称不能形成独立标题行 / 破坏表格 / 破坏结构化文本回读。"""
    evil = dict(BASE, name="A | B\n## 注入标题", tags=["t|1"])
    exported = tool.export_normalized_interfaces([evil])
    md = exported["markdown_artifact"]
    assert not any(line.strip() == "## 注入标题" for line in md.splitlines())
    assert "A \\| B" in md and "⏎" in md
    assert "\\n" in exported["text_artifact"]


def test_dev_13_csv_export_sanitizes_formula_injection():
    """#369 CSV 公式注入必须统一清洗，且不允许裸 to_csv。"""
    data = page._csv_bytes([{"Title": "=1+1", "Evidence": "@SUM(A1)", "Target": "-2+3+cmd"}])
    text = data.decode("utf-8-sig")
    assert "'=1+1" in text and "'@SUM(A1)" in text and "'-2+3+cmd" in text
    assert "sanitize_export_rows" in PAGE_SRC
    csv_fn = PAGE_SRC.split("def _csv_bytes")[1].split("\ndef ")[0]
    assert all(line.strip() in csv_fn for line in PAGE_SRC.splitlines() if ".to_csv(" in line)


def test_dev_14_upload_filename_is_sanitized_and_temp_file_removed(tmp_path):
    """#370 路径穿越文件名只取 basename，临时文件用完即删。"""
    class FakeUpload:
        name = "../../evil/../../tmp.json"

        def getbuffer(self):
            return b"{}"

    class FakeParser:
        upload_dir = str(tmp_path)

        def parse_document(self, file_path):
            assert Path(file_path).name.startswith("probe_")
            return []

    interfaces, original_name = page._parse_interface_source(
        FakeParser(), {"mode": "文件上传", "uploaded_file": FakeUpload()}, "probe")
    assert interfaces == []
    assert original_name == "tmp.json"
    assert list(tmp_path.iterdir()) == []
    assert "os.path.basename" in PAGE_SRC and "os.remove" in PAGE_SRC


def test_dev_15_unknown_raw_format_and_copy_button_are_safe():
    """#371 未知 raw_format 抛 ValueError；复制按钮 button_text 做 HTML 转义。"""
    class DummyParser:
        upload_dir = "/tmp"

        def parse_content(self, *args, **kwargs):
            return []

    with pytest.raises(ValueError, match="未知文本格式"):
        page._parse_interface_source(
            DummyParser(), {"mode": "原始文本", "raw_content": "{}", "raw_format": "未知格式"}, "x")

    captured = {}
    with mock.patch.object(page.components, "html",
                           side_effect=lambda code, **kw: captured.setdefault("html", code)):
        page._create_copy_button("text", button_text="<img src=x onerror=alert(1)>", key="copy_probe")
    assert "<img src=x onerror=alert(1)>" not in captured["html"]
    assert "&lt;img" in captured["html"]


def test_dev_16_results_have_signature_and_stale_feedback():
    """#372 结果必须带配置签名与过期反馈。"""
    for marker in ("_snapshot_state", "_mark_result_current", "_is_result_stale",
                   "_render_result_feedback", "当前展示的是上一次"):
        assert marker in PAGE_SRC
    tool = InterfaceDevTools()
    result = tool.compare_interfaces([BASE], [dict(BASE, expected_status=201)])
    assert result["config_snapshot"] and result["input_signature"]


def test_dev_17_registry_exposes_extension_points():
    """#373 所有规则/词表/渲染器/上限均可注册扩展。"""
    for name in (
        "register_snippet_language", "register_snippet_renderer", "register_quality_rule",
        "register_assertion_style", "register_status_bucket", "register_mock_header_allowlist",
        "configure_dev_limits", "register_checklist_template", "reset_dev_registry",
    ):
        assert callable(getattr(dev_reg, name, None)), name
    assert (ROOT / "src/qa_toolkit/core/api_dev_registry.py").exists()


def test_dev_18_all_results_have_text_summaries(tool):
    """#374 dataframe 是 canvas，读屏/e2e 读不到，必须补中文文字结论。"""
    assert PAGE_SRC.count("st.dataframe(") >= 6
    assert "build_text_summary" in PAGE_SRC and "_render_text_summary" in PAGE_SRC
    diff = tool.compare_interfaces([BASE], [dict(BASE, expected_status=201)])
    assert "基线" in diff["text_summary"] and "变更" in diff["text_summary"]
    quality = tool.analyze_interface_quality([BASE])
    assert "健康分" in quality["text_summary"]


def test_dev_19_exports_carry_config_snapshot(tool):
    """#375 导出必须带 config_snapshot / input_signature / registry_summary / warnings。"""
    result = tool.analyze_interface_quality([BASE])
    for key in ("config_snapshot", "input_signature", "registry_summary", "warnings", "truncation"):
        assert key in result
    assert "_build_download_payload" in PAGE_SRC
    assert "build_export_payload" in PAGE_SRC


def test_dev_20_limits_and_truncation_are_observable(tool):
    """#376 运行上限可配置，超限写 truncation 与 warnings。"""
    limits = dev_reg.get_dev_limits()
    assert 0 < limits.max_interfaces <= 1000
    assert limits.max_mock_routes > 0 and limits.max_recursion_depth > 0
    dev_reg.configure_dev_limits(max_interfaces=1)
    result = tool.export_normalized_interfaces([BASE, dict(BASE, name="第二个")])
    assert result["truncation"].get("normalize_interfaces")
    assert any("超过上限" in item for item in result["warnings"])


def test_dev_21_duplicate_definitions_are_explicit(tool):
    """#377 重复 method+path 不再静默覆盖，未配对定义显式列出并告警。"""
    baseline = [dict(BASE, name="one", body={"v": 1}), dict(BASE, name="two", body={"v": 2})]
    target = [dict(BASE, name="two", body={"v": 2})]
    diff = tool.compare_interfaces(baseline, target)
    assert diff["summary"]["baseline_duplicate_count"] == 1
    assert diff["summary"]["removed_count"] == 1
    assert diff["duplicates"]["unmatched_definitions"]
    assert any("重复定义" in item for item in diff["warnings"])


# ---------------------------------------------------------------------------
# 第二轮：重构后二次走查（#378-#387）
# ---------------------------------------------------------------------------

def test_dev_22_normalization_keeps_string_values_verbatim(tool):
    """#378 token / 签名里的首尾空格是有效数据，不能被 strip 篡改。"""
    normalized = tool._normalize_interface(dict(BASE, body={"token": "  ABC  "}))
    assert normalized["body"]["token"] == "  ABC  "
    assert "return value.strip()" not in CORE_SRC


def test_dev_23_python_snippet_uses_python_literals(tool):
    """#379 payload 必须输出 True/False/None，不能是 true/false/null。"""
    snippet = tool.generate_request_snippet(
        dict(BASE, body={"enabled": True, "note": None, "ok": False}),
        "Python requests", "https://api.example.com")
    tree = ast.parse(snippet)
    names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)}
    assert not ({"true", "false", "null"} & names)
    assert "True" in snippet and "False" in snippet and "None" in snippet
    assert dev_reg.format_python_literal({"a": True}) == "{'a': True}"


def test_dev_24_copy_button_escapes_script_close_tag():
    """#380 </script> 不能提前闭合内联脚本块。"""
    captured = {}
    with mock.patch.object(page.components, "html",
                           side_effect=lambda code, **kw: captured.setdefault("html", code)):
        page._create_copy_button("</script><img src=x onerror=alert(1)>", key="copy_probe2")
    html_code = captured["html"]
    assert "</script><img src=x" not in html_code
    assert "\\u003c/script\\u003e" in html_code
    assert "\\u003cimg" in html_code


def test_dev_25_remote_spec_fetch_has_ssrf_guard():
    """#381 远程 Swagger 拉取默认拒绝内网/元数据地址，逐跳校验重定向。"""
    core = InterfaceAutoTestCore()
    assert core.allow_private_targets is False
    assert core._looks_like_url("http://169.254.169.254/latest/meta-data/")
    with mock.patch.object(test_core_mod.requests, "get") as fake_get:
        with pytest.raises(ValueError, match="校验失败"):
            core._fetch_remote_content("http://169.254.169.254/latest/meta-data/")
        fake_get.assert_not_called()
    assert "validate_target_url" in TEST_CORE_SRC
    assert "allow_redirects=False" in TEST_CORE_SRC
    parse_fn = PAGE_SRC.split("def _parse_interface_source")[1].split("\ndef ")[0]
    assert "validate_target_url" in parse_fn
    assert "api_dev_allow_private_targets" in PAGE_SRC

    class DummyParser:
        def parse_content(self, *args, **kwargs):
            pytest.fail("不应在地址校验失败后继续解析")

    with pytest.raises(ValueError, match="校验失败"):
        page._parse_interface_source(
            DummyParser(),
            {"mode": "原始文本", "raw_content": "http://127.0.0.1:8080/swagger.json",
             "raw_format": "自动检测"},
            "probe")

    class FakeResponse:
        is_redirect = False
        headers = {}

        def raise_for_status(self):
            return None

        text = '{"openapi": "3.0.0"}'

    core.set_allow_private_targets(True)
    with mock.patch.object(test_core_mod.requests, "get", return_value=FakeResponse()) as fake_get:
        assert core._fetch_remote_content("http://127.0.0.1:8080/swagger.json")
        fake_get.assert_called_once()


def test_dev_26_type_change_is_never_masked_by_equality(tool):
    """#382 True == 1 不能把布尔/数字互换判成无变更。"""
    message, risk = tool._describe_value_change(True, 1)
    assert "类型变化" in message and risk == "high"
    message2, risk2 = tool._describe_value_change(1, 1.0)
    assert "类型变化" in message2 and risk2 == "high"
    assert tool._describe_value_change("a", "a")[0] == ""


def test_dev_27_nested_diff_reports_dotted_field_paths(tool):
    """#383 深层字段变更必须给出 user.profile.level 这样的路径。"""
    baseline = dict(BASE, body={"user": {"id": 1, "profile": {"level": 1}}})
    target = dict(BASE, body={"user": {"id": 1, "profile": {"level": 2}}})
    diff = tool.compare_interfaces([baseline], [target])
    changes = diff["changed"][0]["changes"]
    assert any("user.profile.level" in item["message"] for item in changes)
    parts, removed, truncated = tool._collect_field_changes(
        {"a": {"b": 1}}, {"a": {}}, "")
    assert removed and not truncated and parts


def test_dev_28_path_placeholders_do_not_leak_into_parameters(tool):
    """#384 parameters 里的路径占位符只用于替换 URL，不再作为业务参数发出。"""
    normalized = tool._normalize_interface({
        "name": "用户详情", "method": "POST", "path": "/users/{id}",
        "parameters": {"id": "7", "verbose": "1"},
    })
    assert normalized["path"] == "/users/{id}"
    assert "id" not in (normalized["body"] or {})
    assert normalized["body"]["verbose"] == "1"
    assert any("路径占位符" in item for item in tool.get_warnings())
    get_item = tool._normalize_interface({
        "name": "用户详情", "method": "GET", "path": "/users/{id}",
        "parameters": {"id": "7", "page": "1"},
    })
    assert "id" not in get_item["query_params"]
    assert "page" in get_item["query_params"]


def test_dev_29_status_codes_are_validated_and_bucketed(tool):
    """#385 非法状态码报高风险，4xx/5xx 分桶告警，分桶可注册扩展。"""
    invalid = tool.analyze_interface_quality([dict(BASE, expected_status=99999)])
    assert "invalid_expected_status" in {item["category"] for item in invalid["issues"]}
    # 高风险结论不能只躺在 dataframe（canvas）里，读屏/e2e 也要能读到。
    assert "不在合法 HTTP 范围" in invalid["text_summary"]
    server = tool.analyze_interface_quality([dict(BASE, expected_status=500)])
    assert "unexpected_status_bucket" in {item["category"] for item in server["issues"]}
    assert server["summary"]["status_buckets"].get("server_error") == 1
    checklist = tool.generate_regression_checklist([BASE])
    assert checklist["items"][0]["status_bucket"] == "2xx 成功"
    assert "状态分桶" in PAGE_SRC or "status_bucket" in CORE_SRC

    dev_reg.register_status_bucket(
        StatusCodeBucketSpec("success", "自定义成功分桶", 200, 299), replace=True)
    assert dev_reg.classify_status_code(201)["label"] == "自定义成功分桶"
    assert dev_reg.classify_status_code(99999)["valid"] is False


def test_dev_30_relative_path_query_is_split_and_merged(tool):
    """#386 相对路径里的 query 不进 path，合并到 query_params 后只出现一个 ?。"""
    assert tool._normalize_path("api/v1/users?page=1") == "/api/v1/users"
    assert tool._normalize_path("https://h/api/x?a=1#frag") == "/api/x"
    normalized = tool._normalize_interface({
        "name": "列表", "method": "GET", "path": "api/v1/users?page=1",
    })
    assert normalized["path"] == "/api/v1/users"
    assert "page" in normalized["query_params"]
    assert any("查询参数" in item for item in tool.get_warnings())
    snippet = tool.generate_request_snippet(normalized, "curl", "https://h")
    assert snippet.count("?") == 1


def test_dev_31_exports_are_strict_json(tool):
    """#387 NaN/Infinity 必须清洗为 null，导出能被标准 JSON 解析器读取。"""
    exported = tool.export_normalized_interfaces([dict(BASE, body={"score": math.nan})])
    assert "NaN" not in exported["json_artifact"] and "Infinity" not in exported["json_artifact"]
    json.loads(exported["json_artifact"],
               parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
    assert any("非有限" in item for item in exported["warnings"])
    payload = page._build_download_payload({"a": float("inf")})
    assert "Infinity" not in payload
    assert "allow_nan=False" in REG_SRC
    assert dev_reg.strict_json_dumps({"a": True}).strip() == '{"a": true}'
