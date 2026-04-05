import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.text_comparison import (
    build_comparison_report,
    compare_line_texts,
    compare_texts,
    compare_token_texts,
    normalize_compare_text,
    render_token_diff_html,
)


def test_normalize_compare_text_applies_explicit_rules():
    result = normalize_compare_text(
        "  Hello  \r\n\r\nWorld\t\t",
        ignore_case=True,
        trim_line_edges=True,
        collapse_inner_spaces=True,
        ignore_blank_lines=True,
    )

    assert result["text"] == "hello\nworld"
    assert result["trimmed_lines"] == 2
    assert result["removed_blank_lines"] == 1
    assert result["case_folded_lines"] == 2
    assert "已统一换行符格式" in result["changes"]


def test_compare_line_texts_summarizes_add_delete_and_modify():
    result = compare_line_texts(
        "status: success\namount: 100\ntrace: abc",
        "status: success\namount: 200\ntrace: abc\nremark: created",
    )

    assert result["summary"]["modified_lines"] == 1
    assert result["summary"]["added_lines"] == 1
    assert result["summary"]["removed_lines"] == 0
    assert result["rows"][0]["status"] == "修改"
    assert result["rows"][0]["left_line_number"] == 2
    assert result["rows"][0]["right_line_number"] == 2
    assert "remark: created" in result["unified_diff"]


def test_compare_texts_can_ignore_case_and_blank_lines():
    result = compare_texts(
        "Hello\n\nWorld",
        "hello\nworld",
        ignore_case=True,
        ignore_blank_lines=True,
    )

    assert result["summary"]["changed"] is False
    assert result["summary"]["text_similarity"] == 1.0
    assert result["line_diff"]["rows"] == []


def test_compare_token_texts_and_render_html_escape():
    token_result = compare_token_texts("payload=<id>1001", "payload=<id>1002")
    html_result = render_token_diff_html(token_result["segments"])

    assert token_result["summary"]["replaced_blocks"] == 1
    assert token_result["rows"][0]["status"] == "修改"
    assert "&lt;" in html_result
    assert "1002" in html_result


def test_build_comparison_report_contains_summary_and_diff():
    comparison = compare_texts("line1\nline2", "line1\nlineX")
    report = build_comparison_report(comparison, left_source="A", right_source="B")

    assert "# 文本对比报告" in report
    assert "- 原始来源: A" in report
    assert "lineX" in report
    assert "```diff" in report
