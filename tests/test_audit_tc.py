"""文本对比工具专项审计回归测试（issues #153-#168）。"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core.text_comparison_registry import (  # noqa: E402
    exporters,
    register_exporter,
    register_matcher,
    register_normalizer,
    register_tokenizer,
    reset_text_comparison_registry,
    tokenizers,
)
from qa_toolkit.utils.text_comparison import (  # noqa: E402
    build_comparison_report,
    build_export_payloads,
    build_summary_text,
    compare_texts,
    compare_token_texts,
    format_similarity,
    prepare_line_rows_for_display,
    safe_csv_bytes,
    split_lines,
)
from qa_toolkit.utils.text_analysis import normalize_line_endings  # noqa: E402


def test_issue_153_trailing_newline_is_not_a_change():
    result = compare_texts("alpha\nbeta\n", "alpha\nbeta")
    assert result["summary"]["changed"] is False
    assert result["line_diff"]["rows"] == []


def test_issue_154_no_autojunk_false_modifications_on_repeated_lines():
    left = "\n".join(["same"] * 300)
    right_lines = ["same"] * 300
    right_lines[150] = "changed"
    result = compare_texts(left, "\n".join(right_lines))

    assert result["summary"]["modified_lines"] == 0
    assert result["summary"]["added_lines"] == 1
    assert result["summary"]["removed_lines"] == 1
    assert result["summary"]["matching_mode"] == "exact"


def test_issue_155_ignoring_blank_lines_keeps_source_line_numbers():
    result = compare_texts("A\n\nX\nB", "A\nB", ignore_blank_lines=True)
    removed = [row for row in result["line_diff"]["rows"] if row["status"] == "删除"]

    assert len(removed) == 1
    assert removed[0]["left_line_number"] == 3
    assert result["left"]["normalized"]["line_numbers"] == [1, 3, 4]


def test_issue_156_unicode_line_separators_are_normalized():
    assert split_lines("a\u2028b\u2029c\x85d") == ["a", "b", "c", "d"]
    assert normalize_line_endings("a\r\nb\rc") == "a\nb\nc"


def test_issue_157_ignore_case_uses_casefold():
    assert compare_texts("Straße", "STRASSE", ignore_case=True)["summary"]["changed"] is False


def test_issue_158_chinese_tokens_are_not_one_whole_block():
    result = compare_token_texts("创建订单成功", "创建支付订单成功")
    inserted = [segment for segment in result["segments"] if segment["type"] == "insert"]

    assert any("支付" in segment["text"] for segment in inserted)
    assert result["summary"]["token_similarity"] > 0.8


def test_issue_159_markdown_report_escapes_injected_content():
    result = compare_texts("hello", "see [click](javascript:alert(1))")
    report = build_comparison_report(
        result,
        left_source="[假来源](http://evil.com)",
        right_source="evil`source",
    )

    assert "[假来源](http://evil.com)" not in report
    assert "\\[假来源\\]" in report
    assert "see \\[click\\](javascript:alert(1))" in report

    fenced = compare_texts("a\n```\nold\n```", "a\n```\nnew\n```")
    fenced_report = build_comparison_report(fenced)
    assert "\\`\\`\\`" in fenced_report
    assert fenced_report.count("```") == 2


def test_issue_160_csv_export_has_bom_and_neutralizes_formulas():
    raw = '=HYPERLINK("http://evil","click")'
    payload = safe_csv_bytes([{"left_text": raw, "status": "修改"}])

    assert payload.startswith(b"\xef\xbb\xbf")
    decoded = payload.decode("utf-8-sig")
    assert decoded.count("'=HYPERLINK") == 1
    assert "+SUM(A1:A2)" not in decoded


def test_issue_161_report_states_truncation():
    left = "\n".join(f"L{i}" for i in range(60))
    right = "\n".join(f"R{i}" for i in range(60))
    result = compare_texts(left, right)
    report = build_comparison_report(result)

    assert "仅展示前 50 条，共 60 条差异" in report
    assert report.count("  原始: ") == 50


def test_issue_162_empty_state_and_similarity_format():
    empty = compare_texts("", "")
    one_side = compare_texts("hello", "")

    assert empty["summary"]["empty_both"] is True
    assert one_side["summary"]["empty_side"] is True
    assert format_similarity(0.9999) == ">99.9%"
    assert format_similarity(0.9999) != "100.0%"
    assert format_similarity(0.5) == "50.0%"


def test_issue_163_long_rows_are_truncated_and_page_has_side_by_side():
    rows = [{"left_text": "x" * 500, "right_text": "y" * 500}]
    display_rows, truncated = prepare_line_rows_for_display(rows, max_chars=100)

    assert truncated == 2
    assert len(display_rows[0]["left_text"]) < 200
    assert "已截断" in display_rows[0]["left_text"]

    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(ROOT / ".qa-audit" / "tc_app.py"), default_timeout=30).run()
    assert not [exc.value for exc in app.exception]
    assert "并排查看差异" in [checkbox.label for checkbox in app.checkbox] or "并排查看差异" in (
        ROOT / "src/qa_toolkit/ui/pages/text_comparison_page.py"
    ).read_text(encoding="utf-8")


def test_issue_164_empty_diff_export_is_not_zero_bytes():
    result = compare_texts("same", "same")
    payloads = {name: data for name, _, _, data in build_export_payloads(result)}

    assert payloads["Unified Diff"] == "# 两侧文本无差异\n"
    assert "# 文本对比报告" in payloads["Markdown"]
    assert "文本对比摘要" in payloads["TXT"]


def test_issue_165_registry_allows_custom_algorithm_and_tokenizer():
    try:
        register_tokenizer("chars_only", lambda text: list(text), "按字符切分")
        register_matcher("always_equal", lambda left, right: type(
            "M", (), {"ratio": lambda self: 1.0, "get_opcodes": lambda self: []}
        )())

        result = compare_texts("abc", "abd", tokenizer_name="chars_only", matcher_name="always_equal")

        assert result["settings"]["tokenizer_name"] == "chars_only"
        assert result["settings"]["matcher_name"] == "always_equal"
        assert result["summary"]["text_similarity"] == 1.0
        assert "chars_only" in tokenizers()
    finally:
        reset_text_comparison_registry()


def test_issue_166_extra_normalizer_rules_are_optional_and_composable():
    assert compare_texts("a,b", "a。b")["summary"]["changed"] is True
    try:
        result = compare_texts("a,b", "a。b", rules=["ignore_punctuation"])
        assert result["summary"]["changed"] is False
        assert "ignore_punctuation" in result["settings"]["rules"]
    finally:
        reset_text_comparison_registry()


def test_issue_167_exporters_are_registerable():
    try:
        register_exporter("Custom TXT", "custom.txt", "text/plain", lambda result, context: "custom!")
        payloads = {name: data for name, _, _, data in build_export_payloads(compare_texts("a", "b"))}

        assert payloads["Custom TXT"] == "custom!"
        assert "Custom TXT" in exporters()
    finally:
        reset_text_comparison_registry()
        assert "Custom TXT" not in exporters()


def test_issue_168_no_deprecated_container_width_argument():
    page_source = (
        ROOT / "src/qa_toolkit/ui/pages/text_comparison_page.py"
    ).read_text(encoding="utf-8")

    assert "use_container_width" not in page_source
    assert 'width="stretch"' in page_source
