"""接口性能测试工具专项审计回归（GitHub Issues #312-#331）。

覆盖测试专家视角（正确性/边界/并发/安全/统计口径）与产品工程师视角
（拓展性/易用性）：结果过期签名、CSV EOF 三态、URL 编码与 SSRF 护栏、
worker 异常隔离、活跃窗口吞吐、注册表扩展点等。
"""
from __future__ import annotations

import sys
import tempfile
import types
from pathlib import Path
from unittest import mock

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from qa_toolkit.core import api_performance_registry as registry  # noqa: E402
from qa_toolkit.core import api_performance_tool as core_mod  # noqa: E402
from qa_toolkit.core.api_performance_tool import PerformanceTestTool  # noqa: E402
from qa_toolkit.ui.pages import api_performance_page as page  # noqa: E402

PAGE_SRC = (SRC / "qa_toolkit/ui/pages/api_performance_page.py").read_text(encoding="utf-8")
CORE_SRC = (SRC / "qa_toolkit/core/api_performance_tool.py").read_text(encoding="utf-8")


@pytest.fixture(autouse=True)
def _reset_registry():
    registry.reset_performance_registry()
    yield
    registry.reset_performance_registry()


class AttrDict(dict):
    """模拟 Streamlit session_state：同时支持属性读写与 dict 方法。"""

    def __getattr__(self, key):
        return self.get(key)

    def __setattr__(self, key, value):
        self[key] = value


class FakeResponse:
    def __init__(self, text="ok", status_code=200):
        self.text = text
        self.content = text.encode("utf-8")
        self.status_code = status_code
        self.reason = "OK"
        self.headers = {"Content-Type": "text/plain"}


class CapturingSession:
    def __init__(self, response=None):
        self.response = response or FakeResponse()
        self.kwargs = None

    def request(self, method, url, **kwargs):
        self.kwargs = kwargs
        return self.response

    def close(self):
        return None


def _fake_st(state=None):
    return types.SimpleNamespace(
        session_state=state if state is not None else AttrDict(),
        error=mock.Mock(), warning=mock.Mock(), caption=mock.Mock(),
        info=mock.Mock(), success=mock.Mock(), markdown=mock.Mock(),
    )


def _base_plan(tool, **overrides):
    args = {
        "interfaces": [{"name": "s", "method": "GET", "path": "/"}],
        "base_url": "https://example.com",
        "thread_group": {"users": 1, "loop_count": 1},
    }
    args.update(overrides)
    return tool.build_test_plan(**args)


# ---------------------------------------------------------------------------
# PERF-01 结果过期
# ---------------------------------------------------------------------------

def test_perf_01_result_signature_and_stale_banner():
    state = AttrDict({key: None for key in page._CONFIG_SIGNATURE_KEYS})
    state["performance_users"] = 10
    fake = _fake_st(state)
    with mock.patch.object(page, "st", fake):
        signature = page._current_config_signature()
        assert signature and len(signature) == 16
        assert not page._is_result_stale({"input_signature": signature})
        assert not page._is_result_stale({})

        state["performance_users"] = 200
        stale = {"input_signature": signature}
        assert page._is_result_stale(stale)
        page._render_result_state_feedback(stale)
        assert fake.error.called
    assert "结果可能已过期" in PAGE_SRC
    assert 'result["input_signature"]' in PAGE_SRC


# ---------------------------------------------------------------------------
# PERF-02 / PERF-03 CSV EOF 三态与未解析变量
# ---------------------------------------------------------------------------

def test_perf_02_eof_policy_normalization_and_stop_thread():
    assert registry.normalize_csv_eof_policy(True, False) == "recycle"
    assert registry.normalize_csv_eof_policy(False, True) == "stop_thread"
    assert registry.normalize_csv_eof_policy(False, False) == "continue_empty"
    assert registry.normalize_csv_eof_policy(True, True) == "recycle"

    tool = PerformanceTestTool()
    config = {
        "enabled": True,
        "rows": [{"u": "1"}, {"u": "2"}],
        "sharing_mode": "all_threads",
        "eof_policy": "stop_thread",
    }
    runtime = tool._create_csv_runtime(config)
    rows, stops = [], []
    for _ in range(3):
        row, _idx, stop = tool._next_csv_row(runtime, config, 1, 0)
        rows.append(row.get("u"))
        stops.append(stop)
    assert rows == ["1", "2", None]
    assert stops == [False, False, True]  # 修复前 Stop Thread 永不生效


def test_perf_03_continue_empty_records_unresolved_variables():
    tool = PerformanceTestTool()
    config = {"enabled": True, "rows": [{"t": "1"}], "sharing_mode": "all_threads",
              "eof_policy": "continue_empty"}
    runtime = tool._create_csv_runtime(config)
    for _ in range(2):
        tool._next_csv_row(runtime, config, 1, 0)
    row, _idx, stop = tool._next_csv_row(runtime, config, 1, 0)
    assert row == {} and stop is False

    sampler = {"path": "/q?token=${t}", "path_params": {}, "query_params": {},
               "headers": {}, "body": None, "contains_text": "", "method": "GET"}
    materialized = tool._materialize_sampler(sampler, {"base_url": "https://h"}, {})
    assert materialized["unresolved_variables"]
    assert "${t}" in materialized["full_url"]
    assert "_on_recycle_toggle" in PAGE_SRC and "_on_stop_toggle" in PAGE_SRC


# ---------------------------------------------------------------------------
# PERF-04 query 参数
# ---------------------------------------------------------------------------

def test_perf_04_query_params_append_instead_of_overwrite():
    tool = PerformanceTestTool()
    url = tool._build_full_url(
        {"path": "/search?tag=a&tag=b&token=x", "query_params": {"tag": "c"}, "path_params": {}},
        "https://h",
    )
    assert "tag=a" in url and "tag=b" in url and "tag=c" in url and "token=x" in url
    list_url = tool._build_full_url(
        {"path": "/s", "query_params": {"tag": ["a", "b"]}, "path_params": {}}, "https://h"
    )
    assert "tag=a" in list_url and "tag=b" in list_url
    assert "%5B" not in list_url  # list 不再被 str() 化


# ---------------------------------------------------------------------------
# PERF-05 worker 异常隔离
# ---------------------------------------------------------------------------

def test_perf_05_worker_exception_does_not_lose_results():
    tool = PerformanceTestTool()
    plan = _base_plan(tool, thread_group={"users": 2, "loop_count": 1})
    with mock.patch.object(tool, "_run_virtual_user", side_effect=RuntimeError("worker exploded")):
        result = tool.run_test_plan(plan)
    assert result["summary"]["total_requests"] == 2
    assert result["summary"]["failed_requests"] == 2
    assert all(item.get("error_type") == "worker_error" for item in result["samples"])
    assert result["html_report"]  # 报告照常生成


# ---------------------------------------------------------------------------
# PERF-06 deadline 感知 sleep 与 0 样本告警
# ---------------------------------------------------------------------------

def test_perf_06_sleep_is_deadline_aware_and_zero_sample_warns():
    tool = PerformanceTestTool()
    with mock.patch.object(core_mod.time, "sleep") as sleep_mock:
        tool._sleep_with_deadline(25.0, 0.0)  # 截止时间已过
        sleep_mock.assert_not_called()
    with mock.patch.object(core_mod.time, "sleep") as sleep_mock:
        tool._sleep_with_deadline(2.0, 1e9)  # 剩余时间充足
        sleep_mock.assert_called_once_with(2.0)

    empty = tool._build_result({}, [], [], 1700000000.0, 1700000001.0, 0.0, 1.0)
    assert empty["warnings"] and "0 样本" in empty["warnings"][0]
    assert "warnings" in PAGE_SRC


# ---------------------------------------------------------------------------
# PERF-07 断言明细基于全量响应
# ---------------------------------------------------------------------------

def test_perf_07_assertion_results_use_full_response():
    tool = PerformanceTestTool()
    sampler = {
        "sampler_id": "S1", "name": "s", "label": "GET /x", "method": "GET",
        "path": "/x", "path_params": {}, "query_params": {}, "headers": {},
        "body": None, "request_format": "auto", "contains_text": "KEYWORD",
        "expected_status": 200, "max_response_ms": 0,
    }
    response_text = "x" * 450 + "KEYWORD"  # 关键字在 400 字符预览之外
    session = CapturingSession(FakeResponse(response_text))
    sample = tool._execute_sampler(
        session=session, sampler=sampler, http_defaults={"base_url": "https://h"},
        user_number=1, loop_number=1, start_wall=1700000000.0,
    )
    assert sample["success"] is True
    contains = [item for item in sample["assertion_results"] if item["key"] == "contains_text"]
    assert contains and contains[0]["passed"] is True

    nodes = page._build_assertion_result_nodes({}, sample)
    labels = {node["label"]: node["passed"] for node in nodes}
    assert labels["Response Contains"] is True  # 不再与 success 自相矛盾


# ---------------------------------------------------------------------------
# PERF-08 sampler_id 分组与配置匹配
# ---------------------------------------------------------------------------

def test_perf_08_sampler_id_grouping_and_config_lookup():
    tool = PerformanceTestTool()
    samples = [
        {"sampler_id": "S1", "sampler_label": "GET /a", "sampler_name": "接口A",
         "success": True, "elapsed_ms": 1.0},
        {"sampler_id": "S2", "sampler_label": "GET /a", "sampler_name": "接口B",
         "success": False, "elapsed_ms": 2.0, "error_type": "status_mismatch"},
    ]
    rows = tool._build_per_sampler_summary(samples, 1.0)
    assert len(rows) == 2  # 同路径不再被合并

    plan = {"samplers": [
        {"sampler_id": "S1", "name": "接口A", "label": "GET /a", "headers": {"X": "A"}},
        {"sampler_id": "S2", "name": "接口B", "label": "GET /a", "headers": {"X": "B"}},
    ]}
    matched = page._find_sampler_config(plan, {"sampler_id": "S2", "sampler_label": "GET /a"})
    assert matched["name"] == "接口B"
    preview = page._build_sampler_request_preview(
        plan,
        {"sampler_id": "S2", "sampler_label": "GET /a", "method": "GET", "url": "https://h/a",
         "request_headers": {"X": "B"}, "materialized_query_params": {"p": "1"},
         "materialized_body": {"k": "v"}, "csv_variables": {}},
    )
    assert '"X": "B"' in preview and '"p": "1"' in preview and "${" not in preview


# ---------------------------------------------------------------------------
# PERF-09 bodyless methods / parameters 合并 / 合法注解
# ---------------------------------------------------------------------------

def test_perf_09_bodyless_methods_and_valid_annotations():
    tool = PerformanceTestTool()
    normalized = tool._normalize_interface(
        {"method": "GET", "parameters": {"page": 1}, "query_params": {"tag": "a"}}
    )
    assert normalized["query_params"] == {"page": 1, "tag": "a"}

    sampler = {
        "sampler_id": "S1", "name": "s", "label": "GET /", "method": "GET", "path": "/",
        "path_params": {}, "query_params": {}, "headers": {}, "body": {"k": "v"},
        "request_format": "auto", "contains_text": "", "expected_status": 200,
        "max_response_ms": 0,
    }
    session = CapturingSession()
    tool._execute_sampler(
        session=session, sampler=sampler, http_defaults={"base_url": "https://h"},
        user_number=1, loop_number=1, start_wall=1700000000.0,
    )
    assert "json" not in session.kwargs and "data" not in session.kwargs

    import typing
    assert typing.get_type_hints(PerformanceTestTool._assert_response)["return"] is not None
    annotation = PerformanceTestTool._assert_response.__annotations__["return"]
    assert not isinstance(annotation, tuple)  # 修复前是 (bool, str) 元组字面量


# ---------------------------------------------------------------------------
# PERF-10 有限性与上限
# ---------------------------------------------------------------------------

def test_perf_10_non_finite_values_and_configurable_limits():
    tool = PerformanceTestTool()
    assert tool._to_float("inf", 7.0) == 7.0
    assert tool._to_float("nan", 7.0) == 7.0
    assert tool._to_int(float("inf"), 5) == 5

    plan = tool.build_test_plan(
        [{"name": "s", "method": "GET", "path": "/"}],
        "https://example.com",
        thread_group={"users": 999999, "duration_seconds": float("inf"),
                      "ramp_up_seconds": float("inf"), "loop_count": 999999},
        request_defaults={"timeout_seconds": float("inf")},
        timer_config={"think_time_ms": float("inf")},
    )
    limits = registry.get_performance_limits()
    assert plan["thread_group"]["users"] == limits.max_virtual_users
    assert plan["thread_group"]["duration_seconds"] == 0.0
    # inf/nan 回落到安全默认值（30s），有限超大值才钳制到注册上限。
    assert plan["http_defaults"]["timeout_seconds"] == 30.0
    clamped = tool.build_test_plan(
        [{"name": "s", "method": "GET", "path": "/"}], "https://example.com",
        request_defaults={"timeout_seconds": 99999},
    )
    assert clamped["http_defaults"]["timeout_seconds"] == limits.max_timeout_seconds
    assert "max_value=perf_registry.get_performance_limits().max_duration_seconds" in PAGE_SRC

    registry.configure_performance_limits(max_virtual_users=5)
    assert tool.build_test_plan(
        [{"name": "s", "method": "GET", "path": "/"}], "https://example.com",
        thread_group={"users": 100},
    )["thread_group"]["users"] == 5
    with pytest.raises(ValueError):
        registry.configure_performance_limits(unknown_limit=1)


# ---------------------------------------------------------------------------
# PERF-11 URL 字段校验
# ---------------------------------------------------------------------------

def test_perf_11_url_composition_rejects_host_confusion_and_bad_port():
    state = AttrDict({
        "api_perf_protocol": "https", "api_perf_server_name": "internal",
        "api_perf_port": "443@evil.com", "api_perf_base_path": "",
        "performance_base_url": "https://internal",
    })
    with mock.patch.object(page, "st", _fake_st(state)):
        composed = page._compose_base_url_from_fields()
    assert composed == "https://internal"
    assert "evil.com" not in composed
    assert state.get("api_perf_url_error")

    ok, reason = registry.validate_target_url("https://u:p@evil.com/x")
    assert ok is False and "userinfo" in reason
    ok, reason = registry.validate_target_url("ftp://example.com/x")
    assert ok is False and "协议" in reason

    # urlparse(...).port 抛 ValueError 时页面不再崩溃
    state2 = AttrDict({"api_perf_http_fields_synced_from": "", "performance_base_url": "https://x:abc"})
    with mock.patch.object(page, "st", _fake_st(state2)):
        page._sync_http_fields_from_base_url()
    assert state2.get("api_perf_port") == ""


# ---------------------------------------------------------------------------
# PERF-21（e2e 回归新发现）主机名为空时协议/端口仍须校验，不能静默吞掉
# ---------------------------------------------------------------------------

def test_perf_21_validation_runs_even_without_server_name():
    state = AttrDict({
        "api_perf_protocol": "https", "api_perf_server_name": "",
        "api_perf_port": "443@evil.com", "api_perf_base_path": "",
        "performance_base_url": "https://example.com",
    })
    with mock.patch.object(page, "st", _fake_st(state)):
        composed = page._compose_base_url_from_fields()
    assert composed == "https://example.com"
    assert "evil.com" not in composed
    assert state.get("api_perf_url_error")
    assert "端口" in state["api_perf_url_error"]

    # 非法协议同样不能被静默吞掉
    state2 = AttrDict({
        "api_perf_protocol": "ftp", "api_perf_server_name": "",
        "api_perf_port": "", "api_perf_base_path": "",
        "performance_base_url": "https://example.com",
    })
    with mock.patch.object(page, "st", _fake_st(state2)):
        page._compose_base_url_from_fields()
    assert "协议" in state2["api_perf_url_error"]

    # 全空（仅默认协议、无主机无端口）不应误报，仍回落 fallback
    state3 = AttrDict({
        "api_perf_protocol": "https", "api_perf_server_name": "",
        "api_perf_port": "", "api_perf_base_path": "",
        "performance_base_url": "https://example.com",
    })
    with mock.patch.object(page, "st", _fake_st(state3)):
        page._compose_base_url_from_fields()
    assert not state3.get("api_perf_url_error")


# ---------------------------------------------------------------------------
# PERF-12 URL 编码与上传文件清理
# ---------------------------------------------------------------------------

def test_perf_12_path_encoding_and_upload_cleanup():
    tool = PerformanceTestTool()
    injected = tool._build_full_url(
        {"path": "/u/{id}", "path_params": {"id": "../../admin?x=1&y=2"}}, "https://h"
    )
    assert "..%2F" in injected and "%3Fx" in injected
    assert tool._substitute_variables("/q?token=${t}", {"t": "a&admin=1"}, url_encode=True) == \
        "/q?token=a%26admin%3D1"
    assert tool._encode_path_value("raw:../../x") == "../../x"

    class FakeUpload:
        name = "../../evil.json"

        def getbuffer(self):
            return b"{}"

    with tempfile.TemporaryDirectory() as td:
        parser = mock.Mock()
        parser.upload_dir = td
        parser.parse_document.return_value = []
        _interfaces, safe_name = page._parse_interface_source(
            {"mode": "文件上传", "uploaded_file": FakeUpload()}, "iface", parser
        )
        assert safe_name == "evil.json"
        assert list(Path(td).glob("*")) == []  # 临时文件已删除
    assert "os.remove(file_path)" in PAGE_SRC


# ---------------------------------------------------------------------------
# PERF-13 CSV 公式注入与 HTML 转义
# ---------------------------------------------------------------------------

def test_perf_13_csv_formula_guard_and_html_escape():
    df = pd.DataFrame([{"error_message": "=1+1", "url": "@SUM(A1)"}])
    sanitized = page._sanitize_csv_frame(df)
    assert sanitized.iloc[0]["error_message"] == "'=1+1"
    assert sanitized.iloc[0]["url"] == "'@SUM(A1)"

    tool = PerformanceTestTool()
    html_report = tool.build_html_report({
        "summary": {"failed_requests": 1}, "per_sampler": [], "per_transaction": [],
        "timeline": [],
        "error_samples": [{"sampler_name": "s", "thread_name": "VU-1",
                           "status_code": "<img src=x>", "elapsed_ms": 1.0,
                           "error_message": "e"}],
    })
    assert "<img src=x>" not in html_report
    assert "html.escape(status_text)" in PAGE_SRC
    assert registry.sanitize_csv_value("+1") == "'+1"


# ---------------------------------------------------------------------------
# PERF-14 SSRF 护栏
# ---------------------------------------------------------------------------

def test_perf_14_ssrf_guard_and_secure_defaults():
    tool = PerformanceTestTool()
    with pytest.raises(ValueError, match="安全校验"):
        tool.build_test_plan(
            [{"name": "meta", "method": "GET", "path": "http://169.254.169.254/latest"}],
            "",
        )
    # 显式开启内网放行后可压测本地服务
    plan = tool.build_test_plan(
        [{"name": "local", "method": "GET", "path": "http://127.0.0.1:8080/health"}],
        "",
        request_defaults={"allow_private_targets": True},
    )
    assert plan["http_defaults"]["allow_private_targets"] is True

    defaults = tool.build_test_plan(
        [{"name": "s", "method": "GET", "path": "/"}], "https://example.com"
    )["http_defaults"]
    assert defaults["verify_ssl"] is True
    assert defaults["follow_redirects"] is False
    assert registry.validate_target_url("https://example.com/api") == (True, "")


# ---------------------------------------------------------------------------
# PERF-15 吞吐口径
# ---------------------------------------------------------------------------

def test_perf_15_throughput_uses_active_window():
    tool = PerformanceTestTool()
    plan = _base_plan(tool, thread_group={"users": 1, "loop_count": 1,
                                          "start_delay_seconds": 5})
    with mock.patch.object(tool, "_sleep_with_deadline") as sleep_mock, \
            mock.patch.object(core_mod.requests.Session, "request", return_value=FakeResponse()):
        result = tool.run_test_plan(plan)
    summary = result["summary"]
    assert "active_window_seconds" in summary
    assert "wall_throughput_rps" in summary
    assert "活跃窗口" in summary["throughput_basis"]
    # start_delay 在计时前，作为第一次 _sleep_with_deadline 调用且不计入分母
    assert sleep_mock.call_args_list[0].args[0] == 5
    assert sleep_mock.call_args_list[0].args[1] is None


# ---------------------------------------------------------------------------
# PERF-16 分位数口径
# ---------------------------------------------------------------------------

def test_perf_16_percentile_method_and_dynamic_specs():
    tool = PerformanceTestTool()
    values = list(range(1, 11))
    assert registry.get_percentile_method() == "nearest_rank"
    assert tool._percentile(values, 95) == 10
    registry.set_percentile_method("linear")
    assert round(tool._percentile(values, 95), 2) == 9.55
    with pytest.raises(ValueError):
        registry.set_percentile_method("unknown")

    registry.register_percentile("p75_ms", 75, label="75% Line")
    plan = _base_plan(tool)
    with mock.patch.object(core_mod.requests.Session, "request", return_value=FakeResponse()):
        result = tool.run_test_plan(plan)
    assert "p75_ms" in result["summary"]
    assert "测试配置快照" in result["html_report"]


# ---------------------------------------------------------------------------
# PERF-17 截断 / error_type / timeline
# ---------------------------------------------------------------------------

def test_perf_17_truncation_error_type_and_timeline_gaps():
    tool = PerformanceTestTool()
    failed = [
        {"sampler_id": "S1", "sampler_label": "GET /x", "sampler_name": "x",
         "success": False, "elapsed_ms": 1.0, "relative_second": 0,
         "error_type": "status_mismatch"}
        for _ in range(150)
    ]
    built = tool._build_result({}, failed, [], 1700000000.0, 1700000001.0, 0.0, 1.0)
    assert len(built["error_samples"]) == registry.get_performance_limits().max_error_samples
    assert built["truncation"]["error_samples"]["total"] == 150
    assert "仅保留前" in built["truncation"]["error_samples"]["note"]

    gap = [
        {"success": True, "elapsed_ms": 1.0, "relative_second": 0},
        {"success": True, "elapsed_ms": 1.0, "relative_second": 3},
    ]
    buckets = [row["second_bucket"] for row in tool._build_timeline(gap)]
    assert buckets == [0, 1, 2, 3]  # 空档秒已补齐

    transactions = [
        {"transaction_name": "T", "success": True, "complete": True,
         "elapsed_ms": 10.0, "sampler_count": 2},
        {"transaction_name": "T", "success": True, "complete": False,
         "elapsed_ms": 1.0, "sampler_count": 1},
    ]
    rows = tool._build_per_transaction_summary(transactions)
    assert rows[0]["transactions"] == 1  # 不完整事务已排除
    assert "error_type" in tool._build_worker_error_sample(1, 1, RuntimeError("x"))


# ---------------------------------------------------------------------------
# PERF-18 文字摘要与状态反馈
# ---------------------------------------------------------------------------

def test_perf_18_text_summaries_and_feedback():
    assert PAGE_SRC.count("文字摘要") >= 5
    assert "当前注册的能力" in PAGE_SRC
    assert "_render_result_state_feedback" in PAGE_SRC

    state = AttrDict({key: None for key in page._CONFIG_SIGNATURE_KEYS})
    fake = _fake_st(state)
    with mock.patch.object(page, "st", fake):
        page._render_result_state_feedback({
            "input_signature": "old-signature",
            "warnings": ["0 样本"],
            "truncation": {"error_samples": {"note": "仅保留前 100 条"}},
        })
    assert fake.error.called
    assert fake.warning.called
    assert fake.caption.called


# ---------------------------------------------------------------------------
# PERF-19 导出快照与任务配置
# ---------------------------------------------------------------------------

def test_perf_19_export_payload_includes_plan_and_samples():
    payload = registry.build_export_payload({
        "summary": {"total_requests": 1},
        "plan": {"thread_group": {"users": 10}},
        "samples": [{"url": "https://h"}],
        "html_report": "<html></html>",
        "warnings": ["w"], "truncation": {},
    })
    for key in ("plan", "samples", "html_report", "warnings", "truncation", "generated_at"):
        assert key in payload
    assert "build_export_payload(perf_result)" in PAGE_SRC
    assert '"config_signature": _current_config_signature()' in PAGE_SRC
    assert 'payload={"interface_count": len(perf_interfaces)}' not in PAGE_SRC

    registry.configure_performance_limits(max_export_samples=1)
    truncated = registry.build_export_payload({"samples": [{"i": 1}, {"i": 2}, {"i": 3}]})
    assert len(truncated["samples"]) == 1
    assert truncated["samples_truncated"]["total"] == 3


# ---------------------------------------------------------------------------
# PERF-20 注册式扩展点
# ---------------------------------------------------------------------------

def test_perf_20_registry_is_extensible_and_frozen():
    summary = registry.get_registry_summary()
    assert summary["assertion_types"] == 4
    assert summary["listener_tabs"] == 8
    assert summary["protocols"] == 2

    with pytest.raises(ValueError, match="replace=True"):
        registry.register_assertion_type("expected_status", "dup", lambda *a: None)
    registry.register_assertion_type(
        "custom_header", "Header Assertion",
        lambda sampler, text, code, elapsed: registry.AssertionOutcome(True, "custom"),
    )
    ok, errors, details = registry.evaluate_assertions({}, "", 200, 1.0)
    assert ok and not errors
    assert any(item["key"] == "custom_header" for item in details)

    registry.register_percentile("p75_ms", 75, label="75% Line")
    assert any(spec.name == "p75_ms" for spec in registry.get_percentile_specs())
    registry.register_listener_tab("custom_tab", "Custom Tab")
    assert "Custom Tab" in registry.get_listener_tab_labels()
    registry.register_protocol("grpcs")
    assert registry.validate_target_url("grpcs://host/path")[0] is True
    registry.register_export_sanitizer("upper", "upper", lambda value: value)
    assert len(registry.get_export_sanitizers()) == 2

    # 查询返回副本
    tabs = registry.get_listener_tabs()
    tabs.clear()
    assert len(registry.get_listener_tabs()) == 9
    # Spec 冻结
    spec = registry.get_assertion_types()["expected_status"]
    with pytest.raises(Exception):
        spec.label = "changed"

    registry.reset_performance_registry()
    assert registry.get_registry_summary()["assertion_types"] == 4
    assert "Custom Tab" not in registry.get_listener_tab_labels()
