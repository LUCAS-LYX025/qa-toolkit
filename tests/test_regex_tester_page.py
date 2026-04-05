import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.config.constants import PREDEFINED_PATTERNS

REGEX_PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.regex_tester_page import render_regex_tester_page
render_regex_tester_page()
"""


def _build_app() -> AppTest:
    return AppTest.from_string(REGEX_PAGE_SCRIPT, default_timeout=5)


def _assert_no_exceptions(app: AppTest) -> None:
    assert not app.exception, [item.value for item in app.exception]


def test_regex_tester_stateful_playground_buttons_do_not_raise() -> None:
    app = _build_app().run()
    _assert_no_exceptions(app)

    preset_name = next(iter(PREDEFINED_PATTERNS))
    app.selectbox(key="regex_tool_selected_preset").select(preset_name).run()
    app.button(key="regex_tool_load_preset").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_pattern"] == PREDEFINED_PATTERNS[preset_name]

    app.button(key="regex_tool_load_sample").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_pattern"] == r'"traceId"\s*:\s*"([^"]+)"'
    assert "trace-20260405-0001" in app.session_state["regex_tool_text"]

    app.button(key="regex_tool_run").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_test_result"]["match_count"] == 1

    app.button(key="regex_tool_run").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_recent_patterns"][0] == r'"traceId"\s*:\s*"([^"]+)"'

    app.button(key="regex_tool_add_favorite").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_favorites"][0]["pattern"] == r'"traceId"\s*:\s*"([^"]+)"'

    app.button(key="regex_tool_apply_favorite_0").click().run()
    _assert_no_exceptions(app)

    app.button(key="regex_tool_clear").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_pattern"] == ""
    assert app.session_state["regex_tool_text"] == ""


def test_regex_tester_cross_tab_backfill_buttons_do_not_raise() -> None:
    app = _build_app().run()
    _assert_no_exceptions(app)

    app.text_area(key="regex_tool_examples_source").set_value("订单号: ORD-102401, ORD-102402").run()
    app.text_area(key="regex_tool_examples_input").set_value("ORD-102401\nORD-102402").run()
    app.button(key="regex_tool_generate_from_examples").click().run()
    _assert_no_exceptions(app)

    generated_pattern = app.session_state["regex_tool_generated_example_result"]["pattern"]
    app.button(key="regex_tool_apply_generated_pattern").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_pattern"] == generated_pattern
    assert app.session_state["regex_tool_text"] == "订单号: ORD-102401, ORD-102402"

    app.button(key="regex_tool_quick_use_test_text").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_quick_extract_source"] == "订单号: ORD-102401, ORD-102402"

    app.text_input(key="regex_tool_quick_field_name").set_value("traceId").run()
    app.text_area(key="regex_tool_quick_extract_source").set_value('{"traceId":"trace-1001"}').run()
    app.button(key="regex_tool_quick_extract_run").click().run()
    _assert_no_exceptions(app)

    candidate_pattern = app.session_state["regex_tool_quick_extract_result"][0]["pattern"]
    app.button(key="regex_tool_apply_quick_candidate_0").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_pattern"] == candidate_pattern
    assert app.session_state["regex_tool_text"] == '{"traceId":"trace-1001"}'


def test_regex_tester_import_and_clear_buttons_do_not_raise() -> None:
    app = _build_app().run()
    _assert_no_exceptions(app)

    app.text_area(key="regex_tool_favorite_import_text").set_value(
        '[{"name":"订单号","pattern":"ORD-\\\\d+","note":"OMS"}]'
    ).run()
    app.button(key="regex_tool_import_favorites").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_favorite_import_text"] == ""
    assert app.session_state["regex_tool_favorites"][0]["pattern"] == r"ORD-\d+"

    app.radio(key="regex_tool_codegen_source").set_value("手动输入").run()
    app.text_input(key="regex_tool_codegen_custom_pattern").set_value(r"trace-\d+").run()
    app.radio(key="regex_tool_codegen_operation").set_value("替换").run()
    app.text_input(key="regex_tool_codegen_replacement").set_value("***").run()
    app.multiselect(key="regex_tool_codegen_flags").set_value(["i"]).run()
    app.button(key="regex_tool_clear_codegen").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_codegen_custom_pattern"] == ""
    assert app.session_state["regex_tool_codegen_replacement"] == ""
    assert app.session_state["regex_tool_codegen_flags"] == []

    app.text_area(key="regex_tool_examples_source").set_value("abc").run()
    app.text_area(key="regex_tool_examples_input").set_value("abc").run()
    app.button(key="regex_tool_clear_examples").click().run()
    _assert_no_exceptions(app)
    assert app.session_state["regex_tool_examples_source"] == ""
    assert app.session_state["regex_tool_examples_input"] == ""
