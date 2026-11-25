"""正则测试工具专项审计回归测试（GitHub issues #189-#207）。"""
import ast
import io
import json
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.config.constants import PREDEFINED_PATTERNS
from qa_toolkit.core.regex_registry import (
    CodeLanguageSpec,
    FieldExtractor,
    PatternPreset,
    SampleCase,
    get_code_languages,
    get_field_extractors,
    get_pattern_presets,
    get_sample_cases,
    register_code_language,
    register_field_extractor,
    register_pattern_preset,
    register_sample_case,
    reset_regex_registry,
)
from qa_toolkit.ui.pages.regex_tester_page import _build_match_csv, _build_unique_csv
from qa_toolkit.utils.regex_tools import (
    DEFAULT_TIMEOUT_MS,
    analyze_regex,
    build_input_signature,
    build_regex_code,
    configure_highlight,
    detect_regex_risks,
    highlight_regex_matches,
    parse_example_items,
    safe_csv_cell,
)

PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.regex_tester_page import render_regex_tester_page
render_regex_tester_page()
"""


def _app() -> AppTest:
    return AppTest.from_string(PAGE_SCRIPT, default_timeout=8).run()


def _no_exception(app: AppTest) -> None:
    assert not app.exception, [item.value for item in app.exception]


# #189 #190 #191 #192（代码生成正确性）
def test_codegen_escapes_literals_for_supported_languages():
    python_code = build_regex_code(
        r"it's\s+\d+", target_language="Python", operation_type="匹配", selected_flags=[]
    )["code"]
    ast.parse(python_code)  # Python 生成代码必须是可解析的源码

    js_code = build_regex_code(
        r"https?://qa\.example\.com", target_language="JavaScript",
        operation_type="匹配", selected_flags=[],
    )["code"]
    assert r"https?:\/\/qa\.example\.com" in js_code

    js_replace = build_regex_code(
        r"\d+", target_language="JavaScript", operation_type="替换",
        selected_flags=[], replacement="it's $&",
    )["code"]
    assert '"it\'s $&"' in js_replace

    java_code = build_regex_code(
        r"ORD-\d+", target_language="Java", operation_type="匹配", selected_flags=[]
    )["code"]
    assert r'Pattern.compile("ORD-\\d+"' in java_code

    csharp_code = build_regex_code(
        'code="x"', target_language="C#", operation_type="匹配", selected_flags=[]
    )["code"]
    assert 'code=""x""' in csharp_code

    php_code = build_regex_code(
        r"it's/d", target_language="PHP", operation_type="匹配", selected_flags=[]
    )["code"]
    assert r"it\'s\/d" in php_code

    ruby_code = build_regex_code(
        r"\d+", target_language="Ruby", operation_type="替换",
        selected_flags=[], replacement="it's \\1",
    )["code"]
    assert "it\\'s \\\\1" in ruby_code


def test_go_inline_flags_wrap_whole_pattern():
    code = build_regex_code(
        r"cat|dog", target_language="Go", operation_type="匹配", selected_flags=["i"]
    )["code"]
    assert "regexp.MustCompile(`(?i)(?:cat|dog)`)" in code


# #193 #194 #195 #196（运行时保护与过期结果）
def test_catastrophic_backtracking_is_aborted_by_timeout():
    pytest.importorskip("regex")
    result = analyze_regex(r"(a|aa)+$", "a" * 60 + "!", timeout_ms=50)
    assert result["error"]
    assert "执行超时" in result["risk_warnings"][0]["title"]
    assert result["match_count"] == 0


def test_rejected_pattern_clears_previous_result():
    app = _app()
    _no_exception(app)
    app.text_input(key="regex_tool_pattern").set_value(r"\d+").run()
    app.text_area(key="regex_tool_text").set_value("abc123").run()
    app.button(key="regex_tool_run").click().run()
    _no_exception(app)
    assert app.session_state["regex_tool_test_result"]["match_count"] == 1

    # 重叠分支是旧黑名单的盲区，现在由执行超时统一兜底。
    app.text_input(key="regex_tool_pattern").set_value("(a|aa)+$").run()
    app.text_area(key="regex_tool_text").set_value("a" * 60 + "!").run()
    app.button(key="regex_tool_run").click().run()
    _no_exception(app)
    assert app.session_state["regex_tool_test_result"] is None
    assert "超时" in app.session_state["regex_tool_test_error"]
    rendered = "\n".join(item.value for item in app.markdown)
    assert "运行结果" not in rendered


def test_stale_result_is_hidden_when_inputs_change():
    app = _app()
    _no_exception(app)
    app.text_input(key="regex_tool_pattern").set_value(r"\d+").run()
    app.text_area(key="regex_tool_text").set_value("abc123").run()
    app.button(key="regex_tool_run").click().run()
    _no_exception(app)
    assert app.session_state["regex_tool_test_result"]["match_count"] == 1

    app.text_area(key="regex_tool_text").set_value("zzz").run()
    _no_exception(app)
    rendered = "\n".join(item.value for item in app.markdown)
    assert "结果已过期" in rendered
    assert "运行结果" not in rendered


def test_risk_warnings_cover_overlap_and_bounded_quantifiers():
    overlap = detect_regex_risks(r"(a|aa)+$", text_length=100)
    assert any(item["title"] == "重复分支存在重叠前缀" for item in overlap)
    assert all("超时" in item["message"] for item in overlap if item["level"] == "warning")
    nested = detect_regex_risks(r"(a{2,})+$", text_length=100)
    assert any(item["title"] == "疑似嵌套量词" for item in nested)


# #197（截断口径）与 #198（CSV 注入）
def test_truncated_result_reports_total_count():
    result = analyze_regex(r"\d+", " ".join(str(i) for i in range(6000)))
    assert result["match_count"] == 5000
    assert result["truncated"] is True
    assert result["total_match_count"] == 6000
    assert result["unique_match_count_is_partial"] is True
    assert any(item["title"] == "匹配结果已截断" for item in result["risk_warnings"])


def test_csv_downloads_neutralize_formula_cells():
    assert safe_csv_cell("=1+1") == "'=1+1"
    assert safe_csv_cell("@SUM(A1)") == "'@SUM(A1)"
    assert safe_csv_cell("普通文本") == "普通文本"

    result = analyze_regex(r"^[+=@-].*$", "=1+1\n@SUM(A1)\n+cmd\n-id", multiline=True)
    unique_csv = _build_unique_csv(result)
    assert "'=1+1" in unique_csv
    assert "'@SUM(A1)" in unique_csv
    match_csv = _build_match_csv(result)
    assert "'=1+1" in match_csv


# #199-#203（预定义表达式正确性）
@pytest.mark.parametrize(
    ("name", "sample", "should_match"),
    [
        ("匹配整数", "0", True),
        ("匹配整数", "-0", True),
        ("匹配整数", "123", True),
        ("网址URL", "foo]://bad", False),
        ("网址URL", "https://qa.example.com/a", True),
        ("格式日期", "2026x04x05", False),
        ("格式日期", "2026-04-05", True),
        ("身份证号", "11010119900307123|", False),
        ("身份证号", "11010119900307123x", True),
        ("中文字符", "𠀀", True),
    ],
)
def test_predefined_patterns_fixed(name, sample, should_match):
    assert bool(re.search(PREDEFINED_PATTERNS[name], sample)) is should_match


# #204（注册扩展点）
def test_registry_supports_custom_presets_languages_samples_and_extractors():
    try:
        register_pattern_preset(PatternPreset("内部订单号", r"IN-\d{8}"))
        register_sample_case(SampleCase("内部样例", r"IN-\d{8}", "IN-12345678"))
        register_field_extractor(FieldExtractor("internal", lambda text, field: rf"{field}=(IN-\d+)"))
        register_code_language(CodeLanguageSpec(
            name="RustLike",
            templates={"match_all": "let re = /{pattern}/{flags};", "test": "let re = /{pattern}/{flags};",
                       "replace": "let re = /{pattern}/{flags}; {replacement}"},
            flags={"i": "i"},
            escape_pattern=lambda value: value.replace("/", r"\/"),
            escape_replacement=lambda value: json.dumps(value),
        ))
        assert get_pattern_presets()["内部订单号"].pattern == r"IN-\d{8}"
        assert get_sample_cases()["内部样例"].text == "IN-12345678"
        assert any(item["extractor"] == "internal" for item in
                   __import__("qa_toolkit.utils.regex_tools", fromlist=["suggest_field_patterns"])
                   .suggest_field_patterns("order=IN-12345678", "order"))
        generated = build_regex_code(r"a/b", target_language="RustLike",
                                     operation_type="测试", selected_flags=["i"])
        assert r"a\/b" in generated["code"]
    finally:
        reset_regex_registry()


def test_registry_reset_restores_defaults():
    before = (len(get_pattern_presets()), len(get_code_languages()), len(get_field_extractors()))
    register_pattern_preset(PatternPreset("临时", r"T\d+"))
    reset_regex_registry()
    after = (len(get_pattern_presets()), len(get_code_languages()), len(get_field_extractors()))
    assert before == after


# #205（匹配范围）
def test_codegen_respects_match_scope():
    all_code = build_regex_code(r"\d+", target_language="Python", operation_type="匹配",
                                selected_flags=[], global_match=True)["code"]
    first_code = build_regex_code(r"\d+", target_language="Python", operation_type="匹配",
                                  selected_flags=[], global_match=False)["code"]
    assert "re.findall" in all_code
    assert "re.search" in first_code and "re.findall" not in first_code

    js_all = build_regex_code(r"\d+", target_language="JavaScript", operation_type="匹配",
                              selected_flags=[], global_match=True)["code"]
    js_first = build_regex_code(r"\d+", target_language="JavaScript", operation_type="匹配",
                                selected_flags=[], global_match=False)["code"]
    assert "/\\d+/g" in js_all
    assert "/\\d+/" in js_first and "/\\d+/g" not in js_first


# #206（收藏夹上下文）
def test_favorites_keep_runtime_context():
    app = _app()
    _no_exception(app)
    app.text_input(key="regex_tool_pattern").set_value(r"ABC").run()
    app.text_area(key="regex_tool_text").set_value("abc").run()
    app.checkbox(key="regex_tool_ignore_case").check().run()
    app.text_input(key="regex_tool_replacement_text").set_value("X").run()
    app.checkbox(key="regex_tool_enable_replacement").check().run()
    app.button(key="regex_tool_add_favorite").click().run()
    _no_exception(app)

    favorite = app.session_state["regex_tool_favorites"][0]
    assert favorite["ignore_case"] is True
    assert favorite["text"] == "abc"
    assert favorite["replacement"] == "X"

    app.text_input(key="regex_tool_pattern").set_value("EMPTY").run()
    app.button(key="regex_tool_apply_favorite_0").click().run()
    _no_exception(app)
    assert app.session_state["regex_tool_pattern"] == r"ABC"
    assert app.session_state["regex_tool_ignore_case"] is True
    assert app.session_state["regex_tool_text"] == "abc"
    assert app.session_state["regex_tool_replacement_text"] == "X"


# #207（高亮可配置 / 结果可导出）
def test_highlight_is_configurable_and_result_is_json_serializable():
    try:
        configure_highlight(context_chars=6, max_windows=2)
        text = "".join("行" * 500 + f"m{i}" for i in range(10))
        result = analyze_regex(r"m\d", text)
        assert "前 2 个匹配窗口" in result["preview_html"]
        assert result["signature"]
        assert json.loads(json.dumps(result, ensure_ascii=False, default=str))["match_count"] == 10

        signature_a = build_input_signature(r"m\d", text, flags=0, global_match=True,
                                            replacement=None, replace_all=True,
                                            context_chars=6, max_windows=2)
        signature_b = build_input_signature(r"m\d", text + "x", flags=0, global_match=True,
                                            replacement=None, replace_all=True,
                                            context_chars=6, max_windows=2)
        assert signature_a != signature_b
    finally:
        configure_highlight(context_chars=40, max_windows=6)


def test_example_items_keep_thousands_separator():
    assert parse_example_items("1,000\n2,000") == ["1,000", "2,000"]
    assert parse_example_items("1,000") == ["1,000"]
    assert parse_example_items("ORD-1,ORD-2") == ["ORD-1", "ORD-2"]


def test_default_timeout_constant_is_exposed_to_page():
    assert DEFAULT_TIMEOUT_MS == 2000
