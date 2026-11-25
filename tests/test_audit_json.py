"""JSON 处理工具专项审计回归测试（19 项问题）。"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core.json_registry import (  # noqa: E402
    get_export_formats,
    get_jsonpath_functions,
    register_export_format,
    register_jsonpath_function,
    register_validator,
)
from qa_toolkit.utils.json_utils import (  # noqa: E402
    MAX_INPUT_CHARS,
    JsonParseError,
    analyze_json_structure_safe,
    build_input_signature,
    compare_json_values,
    execute_jsonpath,
    format_jsonpath_result,
    format_parse_error,
    get_json_depth_safe,
    parse_json_text,
    serialize_json,
)

STORE_DATA = {
    "store": {
        "book": [
            {"title": "A", "author": "X", "price": 8, "isbn": "1", "tags": ["a", "b"]},
            {"title": "B", "author": "Y", "price": 12, "tags": ["c"]},
            {"title": "C", "author": "Z", "price": 5, "isbn": "3"},
        ],
        "bicycle": {"color": "red", "price": 19},
    }
}


def _markdown_text(app: AppTest) -> str:
    return "\n".join(item.value for item in app.markdown)


def _open_json_page(mode: str = "JSON解析与格式化") -> AppTest:
    app = AppTest.from_file(str(ROOT / "src" / "qa_toolkit" / "streamlit_app.py"), default_timeout=30)
    app.session_state.selected_tool = "JSON处理工具"
    app.run()
    if mode != "JSON解析与格式化":
        app.radio[0].set_value(mode).run()
    assert len(app.exception) == 0
    return app


# ---------------------------------------------------------------------------
# 核心正确性
# ---------------------------------------------------------------------------
def test_duplicate_keys_and_non_standard_numbers_are_reported():
    parsed = parse_json_text('{"a":1,"a":2}')
    assert parsed.value == {"a": 2}
    assert any("重复键" in warning for warning in parsed.warnings)

    with pytest.raises(JsonParseError, match="不是标准 JSON"):
        parse_json_text("NaN")
    lenient = parse_json_text("Infinity", strict=False)
    assert lenient.value == float("inf")
    assert any("非标准数值" in warning for warning in lenient.warnings)


def test_bom_and_jsonl_are_supported():
    assert parse_json_text('\ufeff{"a":1}').value == {"a": 1}
    parsed = parse_json_text('{"a":1}\n{"a":2}\n{"a":3}')
    assert parsed.jsonl is True
    assert parsed.value == [{"a": 1}, {"a": 2}, {"a": 3}]
    assert any("JSONL" in warning for warning in parsed.warnings)


def test_comparison_is_deterministic_and_numeric_equivalent():
    differences, stats = compare_json_values(
        {"a": 1, "b": 2, "c": 3, "d": 4}, {}
    )
    assert differences == [
        "键缺失于 JSON2: a", "键缺失于 JSON2: b",
        "键缺失于 JSON2: c", "键缺失于 JSON2: d",
    ]
    assert stats.differences_count == 4
    assert compare_json_values({"score": 1}, {"score": 1.0})[0] == []
    assert compare_json_values({"ok": True}, {"ok": 1})[0]


def test_structure_analysis_and_depth_are_bounded():
    deep: dict = {}
    cursor = deep
    for _ in range(1200):
        cursor["next"] = {}
        cursor = cursor["next"]
    structure = analyze_json_structure_safe(deep)
    assert structure["truncated"] is True
    assert "上限" in structure["truncation_reason"]

    assert get_json_depth_safe({}) == 1
    assert get_json_depth_safe({"a": 1}) == 1
    assert get_json_depth_safe({"a": {}}) == 2
    assert get_json_depth_safe(deep) <= 200


def test_recursive_descent_returns_each_node_once():
    assert execute_jsonpath(STORE_DATA, "$..author") == ["X", "Y", "Z"]
    assert execute_jsonpath(STORE_DATA, "$..book[0].title") == ["A"]
    values = execute_jsonpath(STORE_DATA, "$..*")
    assert len(values) == len(set(id(value) for value in values))
    assert len(values) > 10


def test_filters_and_bracket_notation():
    assert execute_jsonpath(STORE_DATA, "$['store']['book'][0]['title']") == ["A"]
    assert execute_jsonpath(STORE_DATA, "$.store.book[?(@.tags[0]=='a')].title") == ["A"]
    assert execute_jsonpath(STORE_DATA, "$..book[?(@.isbn)].title") == ["A", "C"]
    assert execute_jsonpath(STORE_DATA, "$..book[?(@.price>=10)].title") == ["B"]
    assert execute_jsonpath(STORE_DATA, "$..book[-2:].title") == ["B", "C"]
    with pytest.raises(JsonParseError, match="步长不能为 0"):
        execute_jsonpath(STORE_DATA, "$.store.book[0:3:0].title")


def test_registry_extensions_are_usable():
    register_jsonpath_function("first_char", lambda value: str(value)[:1], replace=True)
    register_export_format(
        "CSV-ish", extension="csv", mime="text/csv",
        serializer=lambda value: ",".join(map(str, value if isinstance(value, list) else [value])),
        replace=True,
    )
    register_validator("dummy", lambda text: [], replace=True)
    assert execute_jsonpath(STORE_DATA, "$..author.first_char()") == ["X", "Y", "Z"]
    assert "CSV-ish" in get_export_formats()
    assert "first_char" in get_jsonpath_functions()


def test_jsonpath_export_is_valid_json():
    values = execute_jsonpath(STORE_DATA, "$..book[0].title")
    assert json.loads(format_jsonpath_result(values)) == ["A"]
    assert serialize_json({"a": 1}, compact=True) == '{"a":1}'
    with pytest.raises(ValueError):
        serialize_json({"a": float("nan")})


def test_error_message_has_line_column_and_hint():
    source = '{\n  "a": 1,\n}'
    try:
        parse_json_text(source)
    except JsonParseError as exc:
        message = format_parse_error(exc, source)
    else:
        pytest.fail("应当解析失败")
    assert "第 3 行" in message
    assert "常见原因" in message
    assert "附近内容" in message


def test_input_limit_and_signatures():
    with pytest.raises(JsonParseError, match="上限"):
        parse_json_text("x" * (MAX_INPUT_CHARS + 1))
    signature_a = build_input_signature('{"a":1}', {"strict": True})
    signature_b = build_input_signature('{"a":2}', {"strict": True})
    assert signature_a != signature_b


# ---------------------------------------------------------------------------
# 页面行为（AppTest）
# ---------------------------------------------------------------------------
def test_format_and_clear_update_visible_input():
    app = _open_json_page()
    app.text_area(key="json_parser_input_0").set_value('{"a":1}').run()
    app.button(key="json_format").click().run()
    assert app.text_area(key="json_parser_input_1").value == '{\n  "a": 1\n}'

    app.button(key="json_parser_clear").click().run()
    assert app.text_area(key="json_parser_input_2").value == ""


def test_stale_parse_result_is_hidden():
    app = _open_json_page()
    app.text_area(key="json_parser_input_0").set_value('{"a":1}').run()
    app.button(key="json_parse").click().run()
    assert "解析结果" in _markdown_text(app)

    app.text_area(key="json_parser_input_0").set_value('{"a":999}').run()
    app.button(key="json_parse").click().run()
    text = _markdown_text(app)
    assert "结果已过期" in text or "解析结果" in text
    app.text_area(key="json_parser_input_0").set_value('{"b":2}').run()
    assert "结果已过期" in _markdown_text(app)


def test_parse_error_shows_line_hint():
    app = _open_json_page()
    app.text_area(key="json_parser_input_0").set_value('{\n  "a": 1,\n}').run()
    app.button(key="json_parse").click().run()
    errors = "\n".join(item.value for item in app.error)
    assert "第 3 行" in errors
    assert "常见原因" in errors


def test_comparison_stale_result_is_hidden():
    app = _open_json_page("JSON数据对比")
    app.text_area(key="json_compare_left_0").set_value('{"a":1}').run()
    app.text_area(key="json_compare_right_0").set_value('{"a":2}').run()
    app.button(key="json_compare").click().run()
    assert "对比结果" in _markdown_text(app)

    app.text_area(key="json_compare_right_0").set_value('{"a":1}').run()
    assert "结果已过期" in _markdown_text(app)


def test_jsonpath_errors_clear_old_result_and_stale_is_hidden():
    app = _open_json_page("JSONPath查询")
    app.text_input(key="json_query_expr_0").set_value("$.store.book[*].author").run()
    app.button(key="json_query_run").click().run()
    assert "找到 2 个匹配项" in _markdown_text(app) or "查询结果" in _markdown_text(app)

    app.text_area(key="json_query_input_0").set_value("{bad json").run()
    app.button(key="json_query_run").click().run()
    assert app.session_state.json_query_result is None
    assert "JSON 数据格式错误" in "\n".join(item.value for item in app.error)

    app.text_area(key="json_query_input_0").set_value('{"a":1}').run()
    app.text_input(key="json_query_expr_0").set_value("$.a").run()
    app.button(key="json_query_run").click().run()
    app.text_input(key="json_query_expr_0").set_value("$.b").run()
    assert "结果已过期" in _markdown_text(app)


def test_page_exposes_registry_options_and_samples():
    app = _open_json_page()
    assert len(app.selectbox) >= 1
    options = [option for box in app.selectbox for option in box.options]
    assert "JSON" in options and "JSONL" in options and "纯文本" in options
    assert "接口响应" in options and "店铺数据" in options
