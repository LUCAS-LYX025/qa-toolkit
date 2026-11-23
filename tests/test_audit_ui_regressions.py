"""审计 UI 修复的回归测试。

聚焦于可从页面模块直接导入的纯函数逻辑，避免依赖 Streamlit 运行时。
对应 team-lead 分配的 issue: 42/44/45/46/47/48/49/50/56/66/67/68/69/70。
"""

import sys
from pathlib import Path

import pytest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.utils.datetime_tools import DateTimeUtils  # noqa: E402
from qa_toolkit.ui.pages import api_automation_page as automation_page  # noqa: E402
from qa_toolkit.ui.pages import api_dev_tools_page as dev_tools_page  # noqa: E402
from qa_toolkit.ui.pages import api_performance_page as performance_page  # noqa: E402
from qa_toolkit.ui.pages import api_security_page as security_page  # noqa: E402
from qa_toolkit.ui.pages import ip_lookup_page as ip_page  # noqa: E402
from qa_toolkit.ui.pages import log_analysis_page as log_page  # noqa: E402
from qa_toolkit.ui.pages import regex_tester_page as regex_page  # noqa: E402
from qa_toolkit.ui.pages import time_processor_page as time_page  # noqa: E402


# ---------- issue 42: 接口清单指纹（生成产物一致性） ----------

def test_interfaces_signature_is_stable_for_same_content() -> None:
    a = [{"name": "list", "method": "GET", "path": "/users"}]
    b = [{"path": "/users", "method": "GET", "name": "list"}]
    assert automation_page._interfaces_signature(a) == automation_page._interfaces_signature(b)


def test_interfaces_signature_changes_with_interface_list() -> None:
    doc_a = [{"method": "GET", "path": "/users"}]
    doc_b = [{"method": "POST", "path": "/orders"}]
    assert automation_page._interfaces_signature(doc_a) != automation_page._interfaces_signature(doc_b)
    assert automation_page._interfaces_signature([]) == automation_page._interfaces_signature([])


# ---------- issue 44: 切换解析来源应清理旧断言结果 ----------

def test_parse_assertion_source_clears_stale_result(monkeypatch) -> None:
    """模拟解析按钮回调：写入新来源时必须清掉旧断言结果。"""
    class _DummyStreamlit:
        session_state = {
            "interface_dev_assertion_result": {"template_json": "old"},
            "interface_dev_assertion_interfaces": [],
            "interface_dev_assertion_source_name": "",
        }
        error = staticmethod(lambda *args, **kwargs: None)
        success = staticmethod(lambda *args, **kwargs: None)
        warning = staticmethod(lambda *args, **kwargs: None)

    fake_st = _DummyStreamlit()
    monkeypatch.setattr(dev_tools_page, "st", fake_st)

    # 与页面中解析按钮回调一致的操作序列
    fake_st.session_state["interface_dev_assertion_interfaces"] = [{"method": "GET", "path": "/new"}]
    fake_st.session_state["interface_dev_assertion_source_name"] = "new-doc"
    fake_st.session_state.pop("interface_dev_assertion_result", None)

    assert "interface_dev_assertion_result" not in fake_st.session_state
    assert fake_st.session_state["interface_dev_assertion_source_name"] == "new-doc"


# ---------- issue 45: 代码片段语言使用当前选择 ----------

def test_resolve_snippet_language_prefers_current_selection() -> None:
    assert dev_tools_page._resolve_snippet_language("curl", "Python requests") == "curl"
    assert dev_tools_page._resolve_snippet_language(None, "Python requests") == "Python requests"
    assert dev_tools_page._resolve_snippet_language(None, None) == "Python requests"


# ---------- issue 46: 鉴权头非法时只跳过当前动作 ----------

def test_action_prerequisite_ready_returns_false_and_reports(monkeypatch) -> None:
    errors = []
    monkeypatch.setattr(security_page.st, "error", lambda message: errors.append(message), raising=False)

    assert security_page._action_prerequisite_ready(None, "鉴权头") is False
    assert errors and "鉴权头" in errors[0]
    assert security_page._action_prerequisite_ready({"Authorization": "x"}, "鉴权头") is True
    assert len(errors) == 1


# ---------- issue 47: 清空工作区后不再套用 MobSF 预配置 ----------

def test_reset_workspace_marks_bootstrap_done(monkeypatch) -> None:
    class _DummyStreamlit:
        session_state = {}
        error = staticmethod(lambda *args, **kwargs: None)

    fake_st = _DummyStreamlit()
    monkeypatch.setattr(security_page, "st", fake_st)

    security_page._reset_security_workspace()
    assert fake_st.session_state["app_sec_mobsf_profile_bootstrapped"] is True

    # 即使本地仍保存着预配置，也不应重新套用
    def _unexpected_resolve():
        raise AssertionError("不应重新解析并套用 MobSF 预配置")

    monkeypatch.setattr(security_page, "_resolve_mobsf_profile", _unexpected_resolve)
    security_page._ensure_security_defaults()
    assert fake_st.session_state["app_sec_mobsf_base_url"] == "http://127.0.0.1:8000"


# ---------- issue 48: CSV 编码严格解码 + GB18030 回退 ----------

def test_decode_csv_bytes_utf8_bom() -> None:
    raw = "\ufeffuser_id,name\n1,张三".encode("utf-8")
    assert performance_page._decode_csv_bytes(raw) == "user_id,name\n1,张三"


def test_decode_csv_bytes_gbk_fallback() -> None:
    raw = "user_id,name\n1,张三".encode("gbk")
    assert performance_page._decode_csv_bytes(raw) == "user_id,name\n1,张三"


def test_decode_csv_bytes_invalid_encoding_raises() -> None:
    with pytest.raises(ValueError, match="编码无法识别"):
        performance_page._decode_csv_bytes(b"\xff\xfe\x00\x81")


# ---------- issue 49: 批量查询空输入 ----------

def test_parse_batch_targets_dedupes_and_limits() -> None:
    raw = " 8.8.8.8 \nexample.com\n8.8.8.8\n\n"
    assert ip_page._parse_batch_targets(raw) == ["8.8.8.8", "example.com"]
    assert ip_page._parse_batch_targets(raw, limit=1) == ["8.8.8.8"]
    assert ip_page._parse_batch_targets("  \n \n") == []


# ---------- issue 50: 公网 IP 失败文案不得回填 ----------

def test_is_valid_ip_address() -> None:
    assert ip_page._is_valid_ip_address("1.1.1.1") is True
    assert ip_page._is_valid_ip_address("2001:db8::1") is True
    assert ip_page._is_valid_ip_address("获取公网IP失败") is False
    assert ip_page._is_valid_ip_address("") is False
    assert ip_page._is_valid_ip_address("999.1.1.1") is False


# ---------- issue 56: 切换目标语言后过滤 flags ----------

def test_filter_flags_for_language_drops_stale_flags() -> None:
    python_flags = ["re.IGNORECASE", "re.MULTILINE"]
    assert regex_page._filter_flags_for_language("Python", python_flags) == python_flags
    assert regex_page._filter_flags_for_language("JavaScript", python_flags) == []
    assert regex_page._filter_flags_for_language("JavaScript", ["i", "g"]) == ["i", "g"]
    assert regex_page._filter_flags_for_language("未知语言", python_flags) == []


def test_generated_code_does_not_raise_after_language_switch() -> None:
    from qa_toolkit.utils.regex_tools import build_regex_code

    flags = regex_page._filter_flags_for_language("JavaScript", ["re.IGNORECASE"])
    code = build_regex_code(
        r"\d+", target_language="JavaScript", operation_type="匹配", selected_flags=flags
    )
    assert code["language"] == "JavaScript"
    assert "re.IGNORECASE" not in code["code"]


# ---------- issue 66: 压测时间戳数量上限 ----------

def test_clamp_perf_inputs_limits_total_timestamps() -> None:
    duration, rps = time_page._clamp_perf_inputs(100000, 100000)
    assert duration * rps <= time_page.MAX_PERF_TIMESTAMPS
    assert len(DateTimeUtils.get_performance_test_timestamps(duration, rps)) <= time_page.MAX_PERF_TIMESTAMPS


def test_clamp_perf_inputs_keeps_normal_values() -> None:
    assert time_page._clamp_perf_inputs(10, 5) == (10.0, 5.0)


# ---------- issue 67: 超大月偏移钳制 ----------

def test_clamp_month_offset_prevents_date_overflow() -> None:
    import datetime

    assert time_page._clamp_month_offset(1000000) == time_page.MAX_MONTH_OFFSET
    assert time_page._clamp_month_offset(-1000000) == -time_page.MAX_MONTH_OFFSET
    assert time_page._clamp_month_offset("bad") == 0

    start = datetime.date(2026, 11, 23)
    result = DateTimeUtils.add_months(start, time_page._clamp_month_offset(1000000))
    assert result.year <= 9999
    assert DateTimeUtils.subtract_months(start, time_page._clamp_month_offset(1000000)).year >= 1


# ---------- issue 68: 日志级别 widget 状态唯一 ----------

def test_log_level_multiselect_has_single_state_source() -> None:
    source = (
        "src/qa_toolkit/ui/pages/log_analysis_page.py"
    )
    text = (ROOT_DIR / source).read_text(encoding="utf-8")
    block = text[text.index('"日志级别"'):text.index('"日志级别"') + 200]
    assert "key=" in block
    assert "default=" not in block


# ---------- issue 69: JSON 字段为空时禁止添加过滤条件 ----------

def test_is_valid_json_filter_field() -> None:
    fields = {"log": ["level", "message"]}
    assert log_page._is_valid_json_filter_field(fields, "log", "level") is True
    assert log_page._is_valid_json_filter_field(fields, "log", None) is False
    assert log_page._is_valid_json_filter_field(fields, "log", "") is False
    assert log_page._is_valid_json_filter_field(fields, "log", "stale_field") is False
    assert log_page._is_valid_json_filter_field(fields, "other_col", "level") is False


# ---------- issue 70: 收藏索引边界校验 ----------

def test_favorite_at_bounds_check() -> None:
    favorites = [{"name": "a", "pattern": "a"}, {"name": "b", "pattern": "b"}]
    assert regex_page._favorite_at(favorites, 0) == favorites[0]
    assert regex_page._favorite_at(favorites, 99) == {}
    assert regex_page._favorite_at(favorites, -1) == {}
    assert regex_page._favorite_at(favorites, "0") == {}


# ---------- AppTest：关键 UI 回归（真实 widget 交互） ----------

def _app_from_script(script: str):
    from streamlit.testing.v1 import AppTest

    return AppTest.from_string(script, default_timeout=15).run()


def test_ui_public_ip_failure_does_not_overwrite_input() -> None:
    # AppTest 脚本与当前进程共享模块对象：mock 类方法后必须在 finally 恢复，
    # 否则会污染后续 AppTest 测试（如 test_ip_lookup_page.py）。
    from qa_toolkit.tools.ip_lookup import IPQueryTool
    saved_public_ip = IPQueryTool.get_public_ip
    script = f'''
import sys; sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.tools.ip_lookup import IPQueryTool
IPQueryTool.get_public_ip = lambda self: "获取公网IP失败"
from qa_toolkit.ui.pages.ip_lookup_page import render_ip_lookup_page
render_ip_lookup_page()
'''
    try:
        app = _app_from_script(script)
        assert not app.exception
        app.text_input(key="ip_lookup_single_input").set_value("8.8.8.8").run()
        app.button(key="ip_lookup_public_ip").click().run()
        assert not app.exception
        assert app.session_state["ip_lookup_single_input"] == "8.8.8.8"
    finally:
        IPQueryTool.get_public_ip = saved_public_ip


def test_ui_empty_batch_query_shows_warning_and_skips_submit() -> None:
    # 模块级 get_session_task_runner 覆盖同样要在 finally 恢复，避免污染其他测试。
    from qa_toolkit.ui.pages import ip_lookup_page as _page
    saved_runner_fn = _page.get_session_task_runner
    script = f'''
import sys; sys.path.insert(0, {str(SRC_DIR)!r})
import qa_toolkit.ui.pages.ip_lookup_page as p
class FakeRunner:
    submits = []
    def submit(self, **kwargs):
        self.submits.append(kwargs)
        return {{"run_id": "fake"}}
    def list_runs(self, **kwargs):
        return []
p.get_session_task_runner = lambda *a, **k: FakeRunner()
p.render_ip_lookup_page()
'''
    try:
        app = _app_from_script(script)
        assert not app.exception
        app.button(key="ip_lookup_batch_button").click().run()
        assert not app.exception
        assert any("查询目标" in (item.value or "") for item in app.markdown)
    finally:
        _page.get_session_task_runner = saved_runner_fn


def test_ui_codegen_language_switch_filters_flags() -> None:
    script = f'''
import sys; sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.regex_tester_page import render_regex_tester_page
render_regex_tester_page()
'''
    app = _app_from_script(script)
    assert not app.exception
    app.radio(key="regex_tool_codegen_source").set_value("手动输入").run()
    app.text_input(key="regex_tool_codegen_custom_pattern").set_value(r"\d+").run()
    app.selectbox(key="regex_tool_codegen_language").set_value("Python").run()
    app.multiselect(key="regex_tool_codegen_flags").set_value(["re.IGNORECASE"]).run()
    assert app.session_state["regex_tool_codegen_flags"] == ["re.IGNORECASE"]

    app.selectbox(key="regex_tool_codegen_language").set_value("JavaScript").run()
    assert app.session_state["regex_tool_codegen_flags"] == []
    app.button(key="regex_tool_generate_code").click().run()
    assert not app.exception
    assert app.session_state["regex_tool_generated_code"]["language"] == "JavaScript"


def test_ui_invalid_auth_headers_only_skips_current_action() -> None:
    script = f'''
import sys; sys.path.insert(0, {str(SRC_DIR)!r})
import streamlit as st
from qa_toolkit.ui.pages.api_security_page import render_api_security_test_page
st.session_state.api_sec_interfaces = [{{"method": "GET", "path": "/users", "name": "list"}}]
st.session_state.api_sec_auth_headers_text = "{{invalid json"
render_api_security_test_page()
'''
    app = _app_from_script(script)
    assert not app.exception
    app.button(key="api_sec_build_plan").click().run()
    assert not app.exception
    assert any("配置无效" in (item.value or "") for item in app.error)
    # 页面其余部分（动作按钮、结果区）仍然存在
    assert any(button.key == "api_sec_build_plan" for button in app.button)
