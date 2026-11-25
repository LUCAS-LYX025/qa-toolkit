"""接口安全测试工具专项审计回归：逐条对应 GitHub Issues #334-#355（SEC-01 ~ SEC-22）。

视角：测试专家（正确性/安全性/边界）+ 产品工程师（拓展性/易用性），不局限于当前业务。
"""
import json
import sys
import types
from pathlib import Path
from unittest import mock

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import api_security_registry as registry  # noqa: E402
from qa_toolkit.core import api_security_tool as core_mod  # noqa: E402
from qa_toolkit.core.api_security_tool import SecurityTestTool  # noqa: E402
from qa_toolkit.ui.pages import api_security_page as page  # noqa: E402

CORE_SRC = (ROOT / "src/qa_toolkit/core/api_security_tool.py").read_text(encoding="utf-8")
PAGE_SRC = (ROOT / "src/qa_toolkit/ui/pages/api_security_page.py").read_text(encoding="utf-8")
REGISTRY_SRC = (ROOT / "src/qa_toolkit/core/api_security_registry.py").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_security_registry()
    yield
    registry.reset_security_registry()


@pytest.fixture
def tool():
    return SecurityTestTool()


@pytest.fixture
def interfaces():
    return [
        {"name": "用户信息", "method": "GET", "path": "/api/users/{id}",
         "path_params": {"id": "42"}, "query_params": {"page": 1}, "headers": {},
         "description": "查询用户资料", "expected_response": {"data": {"id": 42}},
         "expected_status": 200},
        {"name": "管理员导出", "method": "POST", "path": "/admin/export", "headers": {},
         "description": "导出全部订单", "expected_status": 200},
    ]


class FakeResponse:
    def __init__(self, status_code=200, headers=None, text="{}", raw=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self.raw = raw


class FakeUpload:
    def __init__(self, name, payload=b"{}"):
        self.name = name
        self._payload = payload

    def getbuffer(self):
        return self._payload


class FakeSessionState(dict):
    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(key) from exc

    def __setattr__(self, key, value):
        self[key] = value


def fake_st(state):
    return types.SimpleNamespace(session_state=FakeSessionState(state))


def probe_ctx(**kwargs):
    defaults = dict(
        headers={}, lower_headers={}, status_code=200, body_preview="{}",
        url="https://api.example.com/api", label="GET /api",
        probe_method="GET", original_method="GET", auth_provided=False,
    )
    defaults.update(kwargs)
    return registry.ProbeContext(**defaults)


# ---------------------------------------------------------------------------
# SEC-01 (#334) 工具整体可用性
# ---------------------------------------------------------------------------

def test_sec_01_all_entrypoints_runnable(tool, interfaces):
    assert registry.to_int("200", 0) == 200  # 不再依赖缺失的 self._to_int
    plan = tool.build_security_plan(interfaces, base_url="https://api.example.com")
    assert plan["targets"] and plan["input_signature"]
    assert tool.analyze_interfaces(interfaces, base_url="https://api.example.com")["findings"] is not None
    with mock.patch.object(core_mod.requests.Session, "request", return_value=FakeResponse()):
        assert tool.run_baseline_probe(interfaces, base_url="https://api.example.com", timeout_seconds=1.0)["samples"]
    assert tool.build_authorization_matrix(interfaces)["matrix"]
    assert tool.build_nuclei_template_pack(interfaces)["templates"]
    assert tool.build_regression_suite(interfaces)["scenarios"] is not None
    with mock.patch.object(core_mod.requests.Session, "request", return_value=FakeResponse()):
        assert tool.run_role_batch_regression(interfaces, base_url="https://api.example.com", timeout_seconds=1.0)["comparisons"] is not None


# ---------------------------------------------------------------------------
# SEC-02 (#335) 空选择不等于全选
# ---------------------------------------------------------------------------

def test_sec_02_empty_selection_is_not_full_selection(tool, interfaces):
    assert tool._select_interfaces(interfaces, [])[0] == []
    assert len(tool._select_interfaces(interfaces, None)[0]) == len(interfaces)
    selected, warnings = tool._select_interfaces(interfaces, [0, 0, 0, 99, -1])
    assert len(selected) == 1
    assert any("越界" in item for item in warnings)
    result = tool.analyze_interfaces(interfaces, base_url="https://api.example.com", selected_indexes=[])
    assert result["findings"] == []
    assert any("未选择任何接口" in item for item in result["warnings"])


# ---------------------------------------------------------------------------
# SEC-03 (#336) SSRF 护栏
# ---------------------------------------------------------------------------

def test_sec_03_private_targets_are_blocked(tool):
    called = []

    def fake_request(self, method, url, **kwargs):
        called.append(url)
        return FakeResponse()

    target = [{"name": "m", "method": "GET", "path": "/latest/meta-data/"}]
    with mock.patch.object(core_mod.requests.Session, "request", fake_request):
        report = tool.run_baseline_probe(target, base_url="http://169.254.169.254", timeout_seconds=1.0)
    assert called == []
    assert any(item["Category"] == "blocked_target" for item in report["findings"])
    assert report["truncation"]["blocked_targets"] == 1
    # 显式放行后才允许内网目标
    with mock.patch.object(core_mod.requests.Session, "request", fake_request):
        tool.run_baseline_probe(target, base_url="http://169.254.169.254",
                                timeout_seconds=1.0, allow_private_targets=True)
    assert called, "显式开启允许内网目标后应发出请求"
    assert registry.validate_target_url("https://user:pass@api.example.com/x")[0] is False
    assert registry.validate_target_url("ftp://api.example.com/x")[0] is False


# ---------------------------------------------------------------------------
# SEC-04 (#337) URL 编码与多值
# ---------------------------------------------------------------------------

def test_sec_04_url_encoding_and_multivalue(tool):
    evil = {"path": "/api/users/{id}", "path_params": {"id": "1/../../admin?x=1&y=2#z"}}
    url = tool._build_full_url(evil, "https://api.example.com")
    assert "/admin" not in url and "%2F" in url and "%3F" in url
    raw = {"path": "/api/{seg}", "path_params": {"seg": "raw:a/b"}}
    assert tool._build_full_url(raw, "https://api.example.com").endswith("/api/a/b")
    multi = {"path": "/search?q=1&q=2", "query_params": {"q": "3", "tags": ["a", "b"]}}
    out = tool._build_full_url(multi, "https://api.example.com")
    assert "q=1" in out and "q=2" in out and "q=3" in out
    assert "tags=a" in out and "tags=b" in out and "%5B" not in out


# ---------------------------------------------------------------------------
# SEC-05 (#338) 响应头大小写不敏感
# ---------------------------------------------------------------------------

def test_sec_05_header_evidence_case_insensitive(tool):
    resp = FakeResponse(headers={"server": "nginx/1.24", "x-powered-by": "Express"})
    findings = tool._analyze_probe_response(resp, "GET /api", "https://api.example.com/api", "GET", "GET", False)
    fingerprints = [item for item in findings if item["Category"] == "fingerprint"]
    assert len(fingerprints) == 2
    assert all(item["Evidence"] for item in fingerprints)


# ---------------------------------------------------------------------------
# SEC-06 (#339) 运行上限与非有限值
# ---------------------------------------------------------------------------

def test_sec_06_limits_and_non_finite_inputs(tool, interfaces):
    # 非有限值回落到安全默认值，有限超大值才钳制到注册上限。
    plan = tool.build_security_plan(interfaces, base_url="https://api.example.com", timeout_seconds=float("inf"))
    assert plan["scope"]["timeout_seconds"] == 15.0
    plan_big = tool.build_security_plan(interfaces, base_url="https://api.example.com", timeout_seconds=99999)
    assert plan_big["scope"]["timeout_seconds"] == registry.get_security_limits().max_timeout_seconds
    plan_none = tool.build_security_plan(interfaces, base_url="https://api.example.com", timeout_seconds=None)
    assert plan_none["scope"]["timeout_seconds"] > 0
    registry.configure_security_limits(max_requests=1)
    with mock.patch.object(core_mod.requests.Session, "request", return_value=FakeResponse()):
        report = tool.run_baseline_probe(interfaces, base_url="https://api.example.com", timeout_seconds=1.0)
    assert report["summary"]["request_count"] <= 1
    assert report["truncation"]["requests_limit"] == 1
    assert "max_response_bytes" in plan["scope"]["limits"]


# ---------------------------------------------------------------------------
# SEC-07 (#340) 浏览页签不隐式发请求
# ---------------------------------------------------------------------------

def test_sec_07_no_implicit_network_in_result_tabs():
    dl_start = PAGE_SRC.index("    with tab_download:")
    dl_end = PAGE_SRC.index("    st.markdown(\"</div>\", unsafe_allow_html=True)", dl_start)
    download_block = PAGE_SRC[dl_start:dl_end]
    assert "run_baseline_probe(" not in download_block
    assert "run_role_batch_regression(" not in download_block
    role_start = PAGE_SRC.index("    with tab_role:")
    role_end = PAGE_SRC.index("    with tab_risk:", role_start)
    role_block = PAGE_SRC[role_start:role_end]
    assert "run_role_batch_regression(" not in role_block
    assert "不会隐式发起多角色探测请求" in role_block


# ---------------------------------------------------------------------------
# SEC-08 (#341) CSV 公式注入
# ---------------------------------------------------------------------------

def test_sec_08_csv_formula_guard():
    payload = page._csv_bytes([{"Title": "=1+1", "Evidence": "@SUM(A1:A9)", "Target": "-2+3+cmd"}])
    assert "'=1+1" in payload and "'@SUM" in payload and "'-2+3+cmd" in payload
    assert PAGE_SRC.count("pd.DataFrame(...).to_csv(index=False)") == 0
    assert PAGE_SRC.count(".to_csv(index=False)") == 1  # 只在 _csv_bytes 内
    assert "_sanitize_csv_frame" in PAGE_SRC


# ---------------------------------------------------------------------------
# SEC-09 (#342) Nuclei YAML 注入与变量名唯一
# ---------------------------------------------------------------------------

def test_sec_09_yaml_injection_blocked(tool, interfaces):
    variables = registry.build_template_header_variables({
        "X-Evil\n  injected: 'yes'\n  severity: critical": "v",
        "X-A": "1", "X_A": "2",
    })
    assert len(variables) == 2  # 非法 header 名被丢弃
    assert len({item["variable"] for item in variables}) == 2
    content = tool._build_nuclei_headers_template(["/api"], "https://audit.local", variables)
    assert "injected: 'yes'" not in content
    assert "severity: critical:" not in content
    pack = tool.build_nuclei_template_pack(interfaces, auth_headers={"X-A": "1", "X_A": "2"})
    assert all("injected" not in item["content"] for item in pack["templates"])


# ---------------------------------------------------------------------------
# SEC-10 (#343) 配置签名与结果过期
# ---------------------------------------------------------------------------

def test_sec_10_config_signature_and_staleness(tool, interfaces):
    plan = tool.build_security_plan(interfaces, base_url="https://api.example.com")
    signature = plan["input_signature"]
    changed = tool.build_security_plan(interfaces, base_url="https://other.example.com")
    assert changed["input_signature"] != signature
    state = {
        "api_sec_base_url": "https://api.example.com", "api_sec_result_signature": "old-signature",
    }
    with mock.patch.object(page, "st", fake_st(state)):
        assert page._is_result_stale() is True
        page._mark_results_current()
        assert page._is_result_stale() is False
    assert "config_snapshot" in plan and "input_signature" in plan
    assert "build_export_payload" in REGISTRY_SRC


# ---------------------------------------------------------------------------
# SEC-11 (#344) 截断提示与 Markdown 明细
# ---------------------------------------------------------------------------

def test_sec_11_truncation_and_markdown_details(tool, interfaces):
    many = [{"name": f"p{i}", "method": "GET", "path": f"/api/p{i}", "headers": {}, "description": "x"}
            for i in range(40)]
    pack = tool.build_nuclei_template_pack(many)
    assert pack["truncation"]["paths_total"] == 40
    assert pack["truncation"]["paths_kept"] < 40
    assert any("截断" in item for item in pack["warnings"])
    with mock.patch.object(core_mod.requests.Session, "request", return_value=FakeResponse()):
        probe = tool.run_baseline_probe(interfaces, base_url="https://api.example.com", timeout_seconds=1.0)
    passive = tool.analyze_interfaces(interfaces, base_url="https://api.example.com")
    plan = tool.build_security_plan(interfaces, base_url="https://api.example.com")
    bundle = tool.build_report_bundle(plan, passive, probe)
    assert "## 发现项明细" in bundle["report_markdown"]
    assert "### 1." in bundle["report_markdown"]
    assert "运行与截断信息" in bundle["report_markdown"]


# ---------------------------------------------------------------------------
# SEC-12 (#345) 文字摘要
# ---------------------------------------------------------------------------

def test_sec_12_text_summaries(tool, interfaces):
    passive = tool.analyze_interfaces(interfaces, base_url="https://api.example.com")
    assert "本轮共" in passive["text_summary"] and "发现项" in passive["text_summary"]
    dashboard = tool.build_risk_dashboard(passive, None)
    assert dashboard["text_summary"]
    assert "_render_text_summary" in PAGE_SRC
    assert PAGE_SRC.count("_render_text_summary(") >= 4


# ---------------------------------------------------------------------------
# SEC-13 (#346) 注册式扩展点（重点）
# ---------------------------------------------------------------------------

def test_sec_13_registry_is_extensible(tool, interfaces):
    def custom_passive(item, label, url):
        return [{"Severity": "low", "Category": "custom_check", "Title": "自定义规则命中",
                 "Evidence": label, "Recommendation": "r", "OWASP": "API9:2023"}]

    registry.register_passive_rule("custom_check", "custom_check", "自定义检查", custom_passive)
    registry.register_probe_rule("custom_probe", "custom_probe", "自定义探测",
                                 lambda ctx: [{"Severity": "info", "Category": "custom_probe",
                                               "Title": "自定义探测规则", "Evidence": ctx.url,
                                               "Recommendation": "r", "OWASP": "API8:2023"}])
    registry.register_owasp_item("API11:2023", "Custom Category", "自定义关注点", "自定义复核步骤")
    registry.register_sensitive_key("internal_secret", "high")
    registry.register_role_rank("审计员", 4)
    registry.register_http_method("PROPFIND", mutating=False)
    registry.register_error_marker("custom-stack-token")
    registry.register_hint("admin", "backoffice")
    registry.register_nuclei_template("custom", "custom.yaml", "Custom", lambda paths, origin, hv: "id: custom\n")

    passive = tool.analyze_interfaces(interfaces, base_url="https://api.example.com")
    assert any(item["Category"] == "custom_check" for item in passive["findings"])
    rules = registry.evaluate_probe_rules(probe_ctx())
    assert any(item["Category"] == "custom_probe" for item in rules)
    assert any(item.code == "API11:2023" for item in registry.get_owasp_items())
    assert "internal_secret" in registry.get_sensitive_keys("high")
    assert registry.role_rank("审计员") == 4
    assert "PROPFIND" in registry.get_http_methods()
    assert "custom-stack-token" in registry.get_error_markers()
    assert "backoffice" in registry.get_hints("admin")
    assert any(spec.key == "custom" for spec in registry.get_nuclei_templates())
    assert len(tool.build_nuclei_template_pack(interfaces)["templates"]) == 4
    # 注册中心可一键复位，保证测试隔离
    registry.reset_security_registry()
    assert "internal_secret" not in registry.get_sensitive_keys("high")
    assert len(tool.build_nuclei_template_pack(interfaces)["templates"]) == 3


# ---------------------------------------------------------------------------
# SEC-14 (#347) 数值健壮性
# ---------------------------------------------------------------------------

def test_sec_14_numeric_robustness(tool):
    assert registry.status_bucket("abc") == "error"
    assert registry.status_bucket(float("nan")) == "error"
    assert registry.status_bucket(200) == "allow"
    assert registry.status_bucket(403) == "deny"
    assert registry.to_float("inf", 15.0) == 15.0
    assert registry.to_int(None, 7) == 7
    assert tool._status_bucket("not-a-number") == "error"
    assert "isfinite" in REGISTRY_SRC


# ---------------------------------------------------------------------------
# SEC-15 (#348) 上传文件名清洗
# ---------------------------------------------------------------------------

def test_sec_15_upload_filename_sanitized():
    fn_src = PAGE_SRC[PAGE_SRC.index("def _load_uploaded_interfaces"): PAGE_SRC.index("def _store_interfaces")]
    assert "os.path.basename" in fn_src and "re.sub" in fn_src
    assert "os.unlink" in fn_src
    core = mock.MagicMock()
    core.parse_document.return_value = []
    core.last_parse_meta = {"source_name": "x"}
    upload = FakeUpload("../../etc/evil.json?x=1\n", b"{}")
    result, meta = page._load_uploaded_interfaces(core, upload)
    assert result == [] and meta["source_name"] == "x"
    called_path = core.parse_document.call_args[0][0]
    assert "/" not in Path(called_path).name
    assert not Path(called_path).exists(), "临时文件必须在 finally 中删除"


# ---------------------------------------------------------------------------
# SEC-16 (#349) 角色状态结构化
# ---------------------------------------------------------------------------

def test_sec_16_role_codes_are_structured(tool, interfaces):
    rows = tool._build_role_comparison_rows([
        {"role": "匿名用户", "report": {"samples": [
            {"Label": "GET /admin", "Probe Method": "GET", "URL": "https://x/admin", "Status Code": 200}]}},
        {"role": "Label", "report": {"samples": [
            {"Label": "GET /admin", "Probe Method": "GET", "URL": "https://x/admin", "Status Code": 403}]}},
    ])
    row = rows[0]
    assert row["Label"] == "GET /admin", "角色名不得覆盖接口标签"
    assert row["Role Codes"]["匿名用户"] == 200
    assert row["Role Codes"]["Label"] == 403, "保留字角色名不得被静默吞掉"
    findings = tool._analyze_role_comparison_rows(rows)
    assert isinstance(findings, list)
    # 自定义角色等级注册后生效
    registry.register_role_rank("Label", 0)
    assert registry.role_rank("Label") == 0


# ---------------------------------------------------------------------------
# SEC-17 (#350) OWASP 多标签 + 去重计数
# ---------------------------------------------------------------------------

def test_sec_17_owasp_multi_match_and_dedupe(tool):
    finding = {"Severity": "high", "Category": "cors", "Title": "CORS 通配", "Target": "GET /a",
               "Evidence": "*", "Recommendation": "r", "OWASP": "API8:2023,API5:2023"}
    checklist = tool.build_owasp_checklist({"findings": [finding]}, None)
    matched = [item for item in checklist if item["Auto Findings"]]
    assert {item["OWASP"] for item in matched} == {"API8:2023", "API5:2023"}
    dashboard = tool.build_risk_dashboard(
        passive_report={"findings": [finding]}, probe_report={"findings": [finding]},
        role_regression={"findings": [finding]},
    )
    assert dashboard["summary"]["finding_count"] == 1
    assert dashboard["summary"]["duplicate_merged"] == 2
    assert "被动审计" in dashboard["text_summary"] or dashboard["summary"]["finding_count"] == 1


# ---------------------------------------------------------------------------
# SEC-18 (#351) CORS / Cookie 检测口径
# ---------------------------------------------------------------------------

def test_sec_18_cors_null_and_multiple_cookies():
    headers = {"access-control-allow-origin": "null", "access-control-allow-credentials": "true",
               "set-cookie": "a=1; Secure; HttpOnly; SameSite=Lax, b=2"}
    lower = {k.lower(): v for k, v in headers.items()}
    findings = registry.evaluate_probe_rules(probe_ctx(headers=headers, lower_headers=lower))
    cors = [item for item in findings if item["Category"] == "cors"]
    assert cors and cors[0]["Severity"] == "high" and "null" in cors[0]["Evidence"]
    cookies = [item for item in findings if item["Category"] == "cookie"]
    assert cookies and "b" in cookies[0]["Evidence"]
    # 反射的非白名单精确来源也要提示
    reflected = registry.evaluate_probe_rules(probe_ctx(
        headers={"access-control-allow-origin": "https://evil.example", "access-control-allow-credentials": "true"},
        lower_headers={"access-control-allow-origin": "https://evil.example", "access-control-allow-credentials": "true"},
    ))
    assert any(item["Category"] == "cors" and item["Severity"] == "high" for item in reflected)


# ---------------------------------------------------------------------------
# SEC-19 (#352) Header CRLF 与 Origin 覆盖
# ---------------------------------------------------------------------------

def test_sec_19_header_crlf_and_origin_override(tool, interfaces):
    cleaned, warnings = registry.validate_request_headers({"X-Test": "v\r\nInjected: 1", "X-Ok": "1"})
    assert cleaned == {"X-Ok": "1"} and warnings
    headers, _ = registry.build_probe_headers(
        {"Origin": "https://attacker.example", "Authorization": "Bearer x"},
        "https://security-audit.local", "OPTIONS", "GET",
    )
    assert headers["Origin"] == "https://security-audit.local"
    assert "Access-Control-Request-Method" in headers
    called = []
    with mock.patch.object(core_mod.requests.Session, "request",
                           lambda self, method, url, **kw: (called.append(kw.get("headers")), FakeResponse())[1]):
        tool.run_baseline_probe([{"name": "x", "method": "GET", "path": "/api"}],
                                base_url="https://api.example.com",
                                auth_headers={"Origin": "https://attacker.example", "X-Test": "v\r\nInjected: 1"},
                                origin="https://security-audit.local", timeout_seconds=1.0)
    assert called and called[0]["Origin"] == "https://security-audit.local"
    assert "X-Test" not in called[0]


# ---------------------------------------------------------------------------
# SEC-20 (#353) 统一导出 payload
# ---------------------------------------------------------------------------

def test_sec_20_unified_export_payload(tool, interfaces):
    payload = registry.build_export_payload(
        {"plan": {"a": 1}, "probe_report": {"findings": [{"Title": "=1+1"}]}},
        config_snapshot={"base_url": "https://api.example.com", "input_signature": "abc123"},
    )
    assert payload["config_snapshot"]["base_url"] == "https://api.example.com"
    assert payload["input_signature"] == "abc123"
    assert "registry_summary" in payload and payload["registry_summary"]["OWASP 条目"] == 10
    assert "_build_download_payload" in PAGE_SRC
    dl = PAGE_SRC[PAGE_SRC.index("    with tab_download:"): PAGE_SRC.index("    st.markdown(\"</div>\", unsafe_allow_html=True)", PAGE_SRC.index("    with tab_download:"))]
    assert "json.dumps(plan," not in dl
    assert dl.count("_csv_bytes(") >= 6


# ---------------------------------------------------------------------------
# SEC-21 (#354) 错误分类 / 截断 / 告警
# ---------------------------------------------------------------------------

def test_sec_21_error_type_truncation_and_warnings(tool, interfaces):
    def boom(self, method, url, **kwargs):
        raise TimeoutError("timed out")

    with mock.patch.object(core_mod.requests.Session, "request", boom):
        report = tool.run_baseline_probe(interfaces, base_url="https://api.example.com", timeout_seconds=1.0)
    samples = report["samples"]
    assert samples and all(item["error_type"] == "timeout" for item in samples)
    assert all("truncated" in item for item in samples)
    assert report["truncation"]["requests_sent"] == len(samples)
    bundle = tool.build_report_bundle(
        tool.build_security_plan(interfaces, base_url="https://api.example.com"), None, report,
    )
    assert bundle["warnings"] and any("探测请求失败" in item for item in bundle["warnings"])
    assert "_render_warnings_panel" in PAGE_SRC and "当前展示的是上一次" in PAGE_SRC


# ---------------------------------------------------------------------------
# SEC-22 (#355) e2e 回归新发现：安全默认值首屏不可见（折叠面板藏关键边界）
# ---------------------------------------------------------------------------

def test_sec_22_security_defaults_rendered_on_first_screen():
    """安全边界属于执行前必读信息，必须直接渲染，不能放进默认折叠的 expander。"""
    fn = PAGE_SRC[PAGE_SRC.index("def _render_registry_summary()"):
                  PAGE_SRC.index("def _render_text_summary(")]
    expander_at = fn.index("with st.expander(")
    caption_at = fn.index('f"安全默认：仅允许')
    assert caption_at < expander_at, "安全默认值必须直接渲染在首屏，不能藏进折叠面板"
    assert "expanded=False" in fn, "仅明细指标可折叠"
    for marker in ("默认校验 SSL", "默认跟随重定向", "默认允许内网目标", "运行上限：接口"):
        assert marker in fn
    # 与接口性能测试页保持一致的呈现口径
    perf_src = (ROOT / "src/qa_toolkit/ui/pages/api_performance_page.py").read_text(encoding="utf-8")
    assert "默认校验 SSL=" in perf_src
