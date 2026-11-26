"""接口自动化测试工具专项审计回归（Issues #389-#423 / AUTO-01 ~ AUTO-35）。

每条对应该专项在 GitHub 上提交并修复的一个问题；运行时行为直接调用
InterfaceAutoTestCore / EnhancedReportGenerator / api_automation_registry，
UI 结构用源码契约断言（与历史专项一致）。
"""
import json
import math
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core.api_test_core import InterfaceAutoTestCore  # noqa: E402
from qa_toolkit.core import api_automation_registry as reg  # noqa: E402
from qa_toolkit.reporting.report_generator import EnhancedReportGenerator  # noqa: E402

CORE_SRC = (ROOT / "src/qa_toolkit/core/api_test_core.py").read_text(encoding="utf-8")
PAGE_SRC = (ROOT / "src/qa_toolkit/ui/pages/api_automation_page.py").read_text(encoding="utf-8")
REPORT_SRC = (ROOT / "src/qa_toolkit/reporting/report_generator.py").read_text(encoding="utf-8")
REGISTRY_FILE = ROOT / "src/qa_toolkit/core/api_automation_registry.py"

IFACE = {
    "name": "登录",
    "method": "POST",
    "path": "/login",
    "expected_status": 200,
    "expected_response": {},
}
SECRET = "SUPER_SECRET_TOKEN_123"


@pytest.fixture(autouse=True)
def _reset_registry():
    reg.reset_automation_registry()
    yield
    reg.reset_automation_registry()


@pytest.fixture
def core(tmp_path):
    instance = InterfaceAutoTestCore()
    for attr in ("test_dir", "report_dir", "upload_dir"):
        path = tmp_path / attr
        path.mkdir(parents=True, exist_ok=True)
        setattr(instance, attr, str(path))
    return instance


def _manifest(core, files):
    return json.loads(files["interface_manifest.json"])


def _runtime_ns(core, files):
    manifest = _manifest(core, files)
    ns = {}
    helpers = core._build_runtime_helpers(manifest["config"], manifest["cases"])
    exec(helpers, ns)
    return ns


def _generated(core, interfaces=None, **kwargs):
    params = {
        "framework": "requests脚本",
        "base_url": "https://api.example.com",
        "timeout": 30,
        "retry_times": 0,
        "verify_ssl": None,
    }
    params.update(kwargs)
    return core.generate_test_cases(interfaces or [IFACE], **params)


# ---------------------------------------------------------------------------
# 一、安全性
# ---------------------------------------------------------------------------

def test_auto_01_html_report_escapes_all_dynamic_fields(core, tmp_path):
    """#389 详细报告里的接口名/路径/错误信息必须转义，杜绝存储型 XSS。"""
    generator = EnhancedReportGenerator()
    generator.report_dir = str(tmp_path)
    evil_name = '<img src=x onerror=alert(document.domain)>'
    detail = {
        "case_id": "c1", "name": evil_name, "method": "GET",
        "path": '/x"><script>alert(1)</script>', "status": "failed",
        "status_code": 500, "response_time": 0.1,
        "error": "</pre><script>alert(2)</script>", "assertions": [],
        "response_body": "", "headers": {}, "parameters": {}, "url": "", "environment": "",
    }
    path = generator.generate_detailed_report(
        {"total": 1, "passed": 0, "failed": 1, "errors": 0, "success": False,
         "test_details": [detail]},
        "<b>framework</b>", [], [detail],
    )
    html = Path(path).read_text(encoding="utf-8")
    assert evil_name not in html
    assert "<script>alert(1)</script>" not in html
    assert "<script>alert(2)</script>" not in html
    assert "&lt;img" in html
    assert "&lt;b&gt;framework&lt;/b&gt;" in html
    rows_fn = REPORT_SRC.split("def _generate_test_cases_rows")[1].split("\n    def ")[0]
    assert "html.escape" in rows_fn


def test_auto_02_credentials_are_redacted_from_artifacts(core):
    """#390 默认不把 token/密码写进 manifest / 脚本 / 页面 / 下载件。"""
    auth = {"enabled": True, "type": "bearer", "token": SECRET}
    files = _generated(core, framework="pytest", auth_config=auth)
    assert SECRET not in files["interface_manifest.json"]
    assert SECRET not in files["test_interfaces.py"]
    manifest = _manifest(core, files)
    assert manifest["config"]["credential_env_vars"]
    assert any("脱敏" in w for w in manifest["warnings"])
    # 显式开启时才保留凭据，且必须写醒目告警
    explicit = _generated(core, framework="pytest", auth_config=auth, include_credentials=True)
    assert SECRET in explicit["interface_manifest.json"]
    assert any("已显式开启" in w for w in _manifest(core, explicit)["warnings"])


def test_auto_03_ssl_verification_is_on_by_default(core):
    """#391 页面与生成脚本默认都开启 TLS 校验。"""
    assert reg.get_automation_limits().default_verify_ssl is True
    manifest = _manifest(core, _generated(core))
    assert manifest["config"]["verify_ssl"] is True
    checkbox = PAGE_SRC.split('st.checkbox("验证 SSL 证书"')[1][:140]
    assert "value=False" not in checkbox
    assert "default_verify_ssl" in checkbox
    assert 'bool(CONFIG.get("verify_ssl", True))' in CORE_SRC


def test_auto_04_path_params_are_url_encoded(core):
    """#392 生成脚本里的路径参数逐段 quote，杜绝路径穿越 / query 注入。"""
    ns = _runtime_ns(core, _generated(core))
    url = ns["build_url"]("https://api.example.com", "/users/{id}",
                          {"id": "1/../../admin?debug=1#frag"})
    assert "%2F" in url and "/../../" not in url and "%3F" in url
    encoded, warnings = reg.build_full_url(
        "https://api.example.com/api?token=Z", "/users/{id}", {"id": "1/../../admin"},
        {"tag": ["c", "d"]},
    )
    assert "token=Z" in encoded and "tag=c" in encoded and "tag=d" in encoded
    assert "/../../" not in encoded


def test_auto_05_execution_target_guard(core):
    """#393 执行目标默认拒绝内网/元数据，显式开关才放行。"""
    ok, reason = reg.validate_target_url("http://169.254.169.254/latest/meta-data/")
    assert not ok and "内网" in reason
    ns = _runtime_ns(core, _generated(core))
    assert not ns["validate_target_url"]("http://127.0.0.1:8080/admin")[0]
    core.set_allow_private_targets(True)
    ns2 = _runtime_ns(core, _generated(core))
    assert ns2["validate_target_url"]("http://127.0.0.1:8080/admin")[0]
    assert "set_allow_private_targets" in PAGE_SRC


def test_auto_06_header_crlf_is_filtered(core):
    """#394 Header 名/值走 RFC 7230 token + CRLF 校验，非法项显式告警。"""
    headers, warnings = reg.sanitize_headers({"X-Bad\r\nInjected": "1", "X-Ok": "ok"})
    assert headers == {"X-Ok": "ok"} and warnings
    bad_auth = reg.normalize_auth_config(
        {"enabled": True, "type": "api_key", "api_key_name": "X-Key\r\nX-Inj: 1", "api_key_value": "v"}
    )
    built, auth_warnings = reg.build_auth_headers(bad_auth)
    assert not built and auth_warnings


def test_auto_07_csv_export_is_formula_sanitized():
    """#395 CSV 公式注入统一走注册式清洗器。"""
    assert reg.sanitize_csv_value('=HYPERLINK("http://evil","x")').startswith("'")
    rows = reg.sanitize_export_rows([{"接口": "=cmd|calc", "路径": "/ok"}])
    assert rows[0]["接口"].startswith("'") and rows[0]["路径"] == "/ok"
    # CSV 序列化统一收口到注册中心；页面只消费 get_export_items，不再硬编码。
    assert "to_csv(index=False" in REGISTRY_FILE.read_text(encoding="utf-8")
    assert "get_export_items(" in PAGE_SRC
    csv_bytes = reg.csv_bytes([{"接口": "=cmd|calc"}])
    assert b"cmd" in csv_bytes and b"'" in csv_bytes


def test_auto_08_upload_is_bounded_whitelisted_and_cleaned():
    """#396 上传有大小/后缀上限，临时文件 try/finally 删除。"""
    load_fn = PAGE_SRC.split("def _load_uploaded_document")[1].split("\ndef ")[0]
    assert "max_upload_bytes" in load_fn
    assert "suffix" in load_fn and "INTERFACE_FILE_TYPES" in load_fn
    assert "os.remove" in load_fn and "finally" in load_fn
    assert "uuid" in load_fn
    assert REGISTRY_FILE.exists() and "max_upload_bytes" in REGISTRY_FILE.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# 二、正确性与数据保真
# ---------------------------------------------------------------------------

def test_auto_09_standard_assertions_are_recursive(core):
    """#397 标准模板必须递归比对嵌套字段，不能跳过 dict/list。"""
    ns = _runtime_ns(core, _generated(core))
    expected = {"code": 0, "data": {"user": {"id": 1, "role": "admin"}}}
    actual = {"code": 0, "data": {"user": {"id": 999, "role": "hacker"}}}
    failures = ns["compare_standard"](expected, actual, "response")
    assert any("response.data.user.id" in f for f in failures)
    assert any("response.data.user.role" in f for f in failures)
    assert ns["compare_response"](expected, actual, "smoke") == []
    strict = ns["compare_strict"]({"a": 1}, {"a": 1, "b": 2}, "response")
    assert any("多余字段" in f for f in strict)
    assert reg.compare_response(expected, actual, "standard")


def test_auto_10_report_does_not_silently_rewrite_totals(core, tmp_path):
    """#398 明细缺失时保留执行总数，只标注覆盖率。"""
    generator = EnhancedReportGenerator()
    generator.report_dir = str(tmp_path)
    detail = {"case_id": "c1", "name": "A", "method": "GET", "path": "/a",
              "status": "passed", "status_code": 200, "response_time": 0.1,
              "error": "", "assertions": [], "response_body": "", "headers": {},
              "parameters": {}, "url": "", "environment": ""}
    path = generator.generate_detailed_report(
        {"total": 10, "passed": 10, "failed": 0, "errors": 0, "success": True,
         "test_details": [detail]}, "pytest", [], [detail],
    )
    html = Path(path).read_text(encoding="utf-8")
    assert "总计 10" in html or "统计用例数: <strong>10</strong>" in html
    tpl = REPORT_SRC.split("def _generate_html_template")[1].split("return f'''")[0]
    assert "total = calculated_total" not in tpl
    assert "total = 1" not in tpl


def test_auto_11_report_filenames_are_unique(core, tmp_path):
    """#399 同一秒连续生成两份报告不互相覆盖。"""
    generator = EnhancedReportGenerator()
    generator.report_dir = str(tmp_path)
    results = {"total": 1, "passed": 1, "failed": 0, "errors": 0, "success": True, "test_details": []}
    first = generator.generate_detailed_report(results, "pytest", [], [])
    second = generator.generate_detailed_report(results, "pytest", [], [])
    assert os.path.basename(first) != os.path.basename(second)
    assert "uuid" in REPORT_SRC
    simple = core.generate_html_report(results, "pytest")
    assert "uuid" in CORE_SRC and os.path.basename(simple).count("_") >= 2


def test_auto_12_unknown_values_warn_instead_of_silent_fallback(core):
    """#400 非法方法 / 请求格式 / 执行模式回落时必须写告警。"""
    normalized = core._normalize_interface(
        {"name": "x", "path": "/x", "method": "TRACE", "request_format": "BOGUS"}
    )
    assert normalized["method"] == "GET" and normalized["request_format"] == "auto"
    warnings = core.get_warnings()
    assert any("非法 HTTP 方法" in w for w in warnings)
    assert any("未知请求格式" in w for w in warnings)
    assert core._normalize_execution_mode("bogus") == "pytest"
    assert any("未知执行模式" in w for w in core.get_warnings())


def test_auto_13_invalid_expected_status_is_rejected(core):
    """#401 99999 回落为 200 并写告警，不生成永不可能通过的断言。"""
    normalized = core._normalize_interface(
        {"name": "x", "path": "/x", "expected_status": 99999}
    )
    assert normalized["expected_status"] == 200
    assert normalized["status_valid"] is False
    assert any("100-599" in w for w in core.get_warnings())
    assert reg.classify_status_code(404)["bucket"] == "client_error"


def test_auto_14_manifest_is_strict_json(core):
    """#402 NaN / Infinity 被清洗为 null，严格 JSON 解析可通过。"""
    iface = dict(IFACE, expected_response={"v": float("nan"), "i": float("inf")})
    files = _generated(core, [iface], framework="pytest")
    raw = files["interface_manifest.json"]
    assert "NaN" not in raw and "Infinity" not in raw
    json.loads(raw, parse_constant=lambda c: (_ for _ in ()).throw(ValueError(c)))
    assert "strict_json_dumps" in CORE_SRC
    registry_src = REGISTRY_FILE.read_text(encoding="utf-8")
    assert '"allow_nan"' in registry_src and "_sanitize_json_numbers" in registry_src


def test_auto_15_limits_clamp_timeout_retry_and_interfaces(core):
    """#403 超时/重试/接口数量受 AutomationLimits 钳制并写告警。"""
    limits = reg.get_automation_limits()
    files = _generated(core, [IFACE] * 3, framework="pytest", timeout=10 ** 9, retry_times=10 ** 6)
    manifest = _manifest(core, files)
    assert manifest["config"]["timeout"] == limits.max_timeout_seconds
    assert manifest["config"]["retry_times"] == limits.max_retry_times
    assert any("钳制" in w for w in manifest["warnings"])
    reg.configure_automation_limits(max_interfaces=2)
    truncated = _manifest(core, _generated(core, [IFACE] * 5))
    assert len(truncated["cases"]) == 2
    assert truncated["truncation"]["interfaces"]["total"] == 5
    assert "AutomationLimits" in CORE_SRC


# ---------------------------------------------------------------------------
# 三、易用性与状态反馈
# ---------------------------------------------------------------------------

def test_auto_16_config_is_part_of_signature():
    """#404 配置签名覆盖 base_url/鉴权/模板/上限，改配置即过期。"""
    assert "_current_config_signature" in PAGE_SRC
    fn = PAGE_SRC.split("def _current_config_signature")[1].split("\ndef ")[0]
    for token in ("base_url", "auth_fingerprint", "template_style", "verify_ssl",
                  "allow_private_targets", "include_credentials"):
        assert token in fn
    assert "_ensure_generated_file(execution_mode, current_sig)" in PAGE_SRC
    assert "已过期" in PAGE_SRC


def test_auto_17_results_include_plain_text_conclusion():
    """#405 关键结论渲染成纯文本，不再只躺在 dataframe 里。"""
    assert "_render_text_summary" in PAGE_SRC
    assert "本轮测试结论" in PAGE_SRC
    assert "st.dataframe(" in PAGE_SRC
    assert "build_text_summary" in REGISTRY_FILE.read_text(encoding="utf-8")


def test_auto_18_exports_carry_snapshot_and_warnings():
    """#406 导出件附 config snapshot / 输入签名 / warnings / truncation。"""
    payload = reg.build_export_payload(
        {"total": 1}, config_snapshot={"base_url": "https://x"},
        input_signature="sig", warnings=["w"], truncation={"x": 1},
    )
    assert payload["config_snapshot"]["base_url"] == "https://x"
    assert payload["input_signature"] == "sig"
    assert payload["warnings"] == ["w"] and payload["truncation"] == {"x": 1}
    assert payload["registry_summary"]["导入模板"] >= 13
    assert "_build_download_payload(" in PAGE_SRC and "config_snapshot" in PAGE_SRC


def test_auto_19_downloads_are_lazy_and_cached():
    """#407 报告/CSV/JSON/Markdown 按结果签名缓存，不每次 rerun 急切构建。"""
    render_fn = PAGE_SRC.split("def _render_test_results")[1].split("\ndef ")[0]
    assert "generate_detailed_report(" not in render_fn
    assert "_ensure_report_path(" in render_fn
    assert "api_auto_download_items_cache" in PAGE_SRC
    assert "api_auto_report_cache" in PAGE_SRC
    assert "callable / lazy" in PAGE_SRC


def test_auto_20_page_exposes_private_target_switch():
    """#408 页面提供「允许内网/本地」开关并调用共享解析器。"""
    assert "api_auto_allow_private_targets" in PAGE_SRC
    assert "set_allow_private_targets" in PAGE_SRC
    assert "SSRF 护栏" in PAGE_SRC


def test_auto_21_first_screen_shows_registry_summary():
    """#409 首屏直接渲染安全默认值与能力计数，不藏进折叠面板。"""
    assert "_render_registry_summary()" in PAGE_SRC
    fn = PAGE_SRC.split("def _render_registry_summary")[1].split("\ndef ")[0]
    assert "安全默认" in fn and "运行上限" in fn
    assert "get_registry_summary" in fn
    caption_at = fn.index('"安全默认')
    assert "expanded=False" not in fn[:caption_at]


def test_auto_22_cleanup_only_removes_known_artifacts():
    """#410 清理只删已知产物文件，需二次确认，绝不 rmtree 共享目录。"""
    clean_fn = PAGE_SRC.split("clean_col = st.columns")[1]
    assert "shutil.rmtree" not in clean_fn
    assert "known_generated_files" in clean_fn
    assert "api_auto_clean_confirm" in clean_fn
    assert "get_known_generated_files" in clean_fn


# ---------------------------------------------------------------------------
# 四、拓展性（不局限于当前业务）
# ---------------------------------------------------------------------------

def test_auto_23_registry_is_extensible_and_isolated():
    """#411 方法/格式/模式/模板/上限全部注册化，重复注册需 replace=True。"""
    assert REGISTRY_FILE.exists()
    summary = reg.get_registry_summary()
    assert summary["导入模板"] >= 13 and summary["鉴权方式"] >= 5
    assert summary["状态码分桶"] == 5 and summary["执行模式"] == 3
    reg.register_http_method("PROPFIND")
    assert "PROPFIND" in reg.get_http_methods()
    with pytest.raises(ValueError):
        reg.register_http_method("PROPFIND")
    reg.register_http_method("PROPFIND", replace=True)
    reg.register_request_format(reg.RequestFormatSpec("graphql", "GraphQL", ("gql",)))
    assert reg.normalize_request_format("gql")[0] == "graphql"
    reg.register_mirror("企业内网源", "https://pypi.internal/simple/")
    assert "企业内网源" in reg.get_mirrors()
    reg.configure_automation_limits(max_interfaces=1)
    assert reg.get_automation_limits().max_interfaces == 1
    for stale in ("HTTP_METHODS = {", "REQUEST_FORMAT_MAP = {", "EXECUTION_MODE_MAP = {",
                  "MIRROR_URLS = {", '"value": "13"'):
        assert stale not in CORE_SRC and stale not in PAGE_SRC
    reg.reset_automation_registry()
    assert "PROPFIND" not in reg.get_http_methods()
    assert "企业内网源" not in reg.get_mirrors()


def test_auto_24_auth_modes_and_export_formats_are_registerable():
    """#412 新增鉴权方式/导出格式只需注册，未知方式显式告警而非静默失效。"""
    reg.register_auth_mode(
        reg.AuthModeSpec("oauth2", "OAuth2",
                         lambda cfg: {"Authorization": "Bearer " + str(cfg.get("token", ""))},
                         ("token",)),
    )
    assert "OAuth2" in reg.get_auth_labels()
    cfg = reg.normalize_auth_config({"enabled": True, "type": "oauth2", "token": "T"})
    headers, warnings = reg.build_auth_headers(cfg)
    assert headers["Authorization"] == "Bearer T" and not warnings
    unknown = reg.normalize_auth_config({"enabled": True, "type": "nope"})
    assert unknown["mode_warning"] and unknown["type"] == "none"
    reg.register_export_format("junit", "JUnit XML")
    assert "junit" in reg.get_export_formats()
    reg.register_report_template("allure", "Allure 报告")
    assert "allure" in reg.get_report_templates()


def test_auto_25_disabled_auth_credentials_never_leak(core):
    """#413 未启用鉴权时残留凭据也必须脱敏，不能明文写进产物（第二轮走查）。"""
    secret = "DISABLED_BUT_PRESENT_SECRET"
    auth = {"enabled": False, "type": "bearer", "token": secret}
    files = _generated(core, framework="pytest", auth_config=auth)
    assert secret not in files["interface_manifest.json"]
    assert secret not in files["test_interfaces.py"]
    manifest = _manifest(core, files)
    assert manifest["config"]["auth"]["token"] == ""
    assert any("脱敏" in w for w in manifest["warnings"])

    # 页面 Basic Auth 分支：只填密码不填用户名 -> enabled=False + password 非空。
    basic = {"enabled": False, "type": "basic", "username": "", "password": "P_ONLY_SECRET"}
    files_basic = _generated(core, framework="pytest", auth_config=basic)
    assert "P_ONLY_SECRET" not in files_basic["interface_manifest.json"]
    assert "P_ONLY_SECRET" not in files_basic["test_interfaces.py"]

    # 直接调用注册中心也要成立，不依赖 core 的调用顺序。
    cfg = reg.normalize_auth_config(auth)
    cleaned, env_map, warnings = reg.redact_auth_config(cfg, include_credentials=False)
    assert secret not in json.dumps(cleaned, ensure_ascii=False)
    assert cleaned["token"] == ""
    assert env_map == {}  # 未启用不需要环境变量注入
    assert any("脱敏" in w for w in warnings)


def test_auto_26_shared_parser_preserves_invalid_status(core):
    """#414 共享解析器保真：体检仍能报出非法状态码高风险（跨模块回归）。"""
    from qa_toolkit.core.api_dev_tools import InterfaceDevTools

    raw = {"name": "异常状态码接口", "method": "POST", "path": "/api/order",
           "expected_status": 99999}
    normalized = core._normalize_interface(raw)
    assert normalized["expected_status"] == 200       # 生成脚本仍用安全默认值
    assert normalized["raw_expected_status"] == 99999  # 原始值必须保真
    assert normalized["status_valid"] is False

    # _prepare_cases 会再归一化一次，二次归一化不能把原始值冲掉。
    again = core._normalize_interface(normalized)
    assert again["raw_expected_status"] == 99999

    result = InterfaceDevTools().analyze_interface_quality([normalized])
    messages = [str(issue.get("message", "")) for issue in result.get("issues", [])]
    assert any("不在合法 HTTP 范围（100-599）" in m for m in messages)
    assert result["summary"]["high_count"] >= 1


# ---------------------------------------------------------------------------
# 五、第三轮补充（#415-#423 / AUTO-27 ~ AUTO-35，独立审计 + 边界走查）
# ---------------------------------------------------------------------------

def test_auto_27_sentinel_string_does_not_break_generated_script(core):
    """#415 配置含模板哨兵时生成脚本仍可编译，改用 base64 注入。"""
    files = _generated(core, base_url="https://x.example/__CASES_JSON_LITERAL__.com",
                       framework="pytest")
    script = files["test_interfaces.py"]
    compile(script, "test_interfaces.py", "exec")  # 不得抛 SyntaxError
    assert "__CASES_JSON_LITERAL__" not in script  # 哨兵已被 base64 表达式替换


def test_auto_28_bruno_body_json_roundtrip(core):
    """#416 Bruno body:json 用括号配对解析，嵌套 JSON 不被截断。"""
    template = core.build_bruno_template()
    parsed = core.parse_content(template, source_type="bruno")
    assert parsed, "Bruno 模板应解析出至少一个接口"
    body = parsed[0].get("body")
    assert isinstance(body, dict), f"body 应为 dict，实际 {type(body)}: {body!r}"
    assert body.get("username") == "test"
    assert body.get("password") == "123456"


def test_auto_29_report_stats_clamped(core, tmp_path):
    """#417 统计不守恒时报告不得渲染 500% 成功率。"""
    generator = EnhancedReportGenerator()
    generator.report_dir = str(tmp_path)
    path = generator.generate_detailed_report(
        {"total": 1, "passed": 5, "failed": 0, "errors": 0, "success": True,
         "test_details": []},
        "pytest", [], [],
    )
    html = Path(path).read_text(encoding="utf-8")
    assert "500.0%" not in html
    assert "100.0%" in html


def test_auto_30_csv_prefix_control_chars_sanitized():
    """#418 CSV 公式注入清洗覆盖 LF/CR/TAB/NUL/Unicode 空白前缀。"""
    payloads = ["\n=1+1", "\r=1+1", "\t=1+1", "\x00=1+1", "\u3000=1+1", "@SUM(A1)"]
    for value in payloads:
        assert str(reg.sanitize_csv_value(value)).startswith("'"), repr(value)


def test_auto_31_json_cleaning_is_observable(core):
    """#419 NaN/Inf 清洗必须写进 manifest warnings，不静默。"""
    iface = dict(IFACE, expected_response={"ratio": float("nan"), "big": float("inf")})
    files = _generated(core, interfaces=[iface])
    manifest = json.loads(files["interface_manifest.json"])
    warnings = manifest.get("warnings") or []
    assert any("非有限" in w or "清洗" in w for w in warnings)
    # 产物本身不得含 NaN/Infinity 字面量
    assert "NaN" not in files["interface_manifest.json"]
    assert "Infinity" not in files["interface_manifest.json"]


def test_auto_32_assertion_strategy_comparator_is_consumed():
    """#420 注册的 comparator 真正生效，未知策略显式提示。"""
    reg.reset_automation_registry()
    called = []

    def custom(expected, actual, prefix="response"):
        called.append(True)
        return ["自定义比较器已生效"]

    reg.register_assertion_strategy("custom_t", "自定义", comparator=custom)
    failures = reg.compare_response({"a": 1}, {"a": 1}, "custom_t")
    assert called and any("自定义比较器已生效" in f for f in failures)
    unknown = reg.compare_response({"a": 1}, {"a": 1}, "unknown_t")
    assert any("未知" in f for f in unknown)


def test_auto_33_export_and_report_specs_drive_artifacts():
    """#421 导出格式/报告模板注册点被产物链消费，而非只登记 label。"""
    reg.reset_automation_registry()
    assert hasattr(reg, "get_export_items")
    assert hasattr(reg, "get_report_renderer")
    reg.register_export_format("junit_t", "JUnit XML T", renderer=lambda ctx: "<testsuite/>")
    items = reg.get_export_items({"test_results": {}, "summary_rows": [],
                                  "config_snapshot": {}, "input_signature": "x",
                                  "warnings": [], "truncation": {}, "markdown_text": ""})
    assert any("JUnit XML T" in str(i.get("label", "")) for i in items)
    assert "get_export_items(" in PAGE_SRC
    assert "get_report_renderer(" in REPORT_SRC or "get_report_templates(" in REPORT_SRC


def test_auto_34_builtin_framework_renderers_registered():
    """#422 内置三种执行模式均有注册渲染器，摘要计数一致。"""
    reg.reset_automation_registry()
    summary = reg.get_registry_summary()
    assert summary["框架渲染器"] >= 3
    for key in ("pytest", "unittest", "requests_script"):
        assert reg.get_framework_renderer(key) is not None


def test_auto_35_registry_summary_distinguishes_live_and_listed_only():
    """#423 首屏摘要区分「已接入产物链」与「仅登记」。"""
    reg.reset_automation_registry()
    summary = reg.get_registry_summary()
    access = summary["接入状态"]
    assert isinstance(access, dict)
    assert any("html" in s.lower() for s in access["已接入报告模板"])
    # 注册一个没有 serializer 的格式，应被标为「仅登记」
    reg.register_export_format("listed_only", "仅登记格式")
    assert "仅登记格式" in reg.get_registry_summary()["接入状态"]["仅登记导出格式"]
