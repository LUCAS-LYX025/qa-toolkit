import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.regex_tools import (
    analyze_regex,
    build_replacement_diff,
    build_regex_code,
    detect_regex_risks,
    generate_regex_from_examples,
    highlight_regex_matches,
    parse_example_items,
    suggest_field_patterns,
)


def test_analyze_regex_returns_group_details_unique_values_and_replacement():
    result = analyze_regex(
        r"order=(?P<order_id>ORD-\d{6})",
        "order=ORD-100001\norder=ORD-100002\norder=ORD-100001",
        replacement=r"order=<\g<order_id>>",
    )

    assert result["match_count"] == 3
    assert result["unique_match_count"] == 2
    assert result["group_count"] == 1
    assert result["named_group_names"] == ["order_id"]
    assert result["matches"][1]["line"] == 2
    assert result["matches"][1]["column"] == 1
    assert result["matches"][0]["named_groups"]["order_id"] == "ORD-100001"
    assert result["replacement"]["count"] == 3
    assert "order=<ORD-100002>" in result["replacement"]["text"]
    assert "@@ -1,3 +1,3 @@" in result["replacement"]["diff"]


def test_analyze_regex_can_limit_to_first_match_and_first_replacement():
    result = analyze_regex(
        r"\d+",
        "A1 B22 C333",
        global_match=False,
        replacement="#",
        replace_all=False,
    )

    assert result["match_count"] == 1
    assert result["matches"][0]["match_text"] == "1"
    assert result["replacement"]["count"] == 1
    assert result["replacement"]["text"] == "A# B22 C333"


def test_highlight_regex_matches_escapes_html_content():
    html = highlight_regex_matches("payload=<script>alert(1)</script>", [(8, 16)])

    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "<mark" in html


def test_generate_regex_from_examples_supports_newlines_and_pattern_generalization():
    examples = "ORD-102401\nORD-102402\nORD-102499"
    pattern = generate_regex_from_examples("待处理订单: ORD-102401, ORD-102402, ORD-102499", examples)

    assert parse_example_items(examples) == ["ORD-102401", "ORD-102402", "ORD-102499"]
    assert r"\d{6}" in pattern
    assert re.fullmatch(pattern, "ORD-102401")
    assert re.fullmatch(pattern, "ORD-102499")
    assert not re.fullmatch(pattern, "PAY-102499")


def test_build_regex_code_supports_go_inline_flags_and_python_flag_payload():
    go_code = build_regex_code(
        r"trace-\d+",
        target_language="Go",
        operation_type="匹配",
        selected_flags=["i", "m"],
    )
    python_code = build_regex_code(
        r"trace-\d+",
        target_language="Python",
        operation_type="测试",
        selected_flags=["re.IGNORECASE", "re.MULTILINE"],
    )

    assert "regexp.MustCompile(`(?i)(?m)trace-\\d+`)" in go_code["code"]
    assert "re.IGNORECASE | re.MULTILINE" in python_code["code"]
    assert "re.search" in python_code["code"]


def test_build_replacement_diff_and_risk_detection_cover_practical_cases():
    diff_text = build_replacement_diff("token=abc123", "token=***")
    risks = detect_regex_risks(r"(a+)+$", text_length=50000, global_match=True)

    assert "--- before" in diff_text
    assert "+++ after" in diff_text
    assert "-token=abc123" in diff_text
    assert any(item["title"] == "疑似嵌套量词" for item in risks)


def test_suggest_field_patterns_handles_json_and_query_style_text():
    text = '{"traceId":"trace-1001","amount":99}\nhttps://qa.example.com?id=1&token=abc123'
    trace_suggestions = suggest_field_patterns(text, "traceId")
    token_suggestions = suggest_field_patterns(text, "token")

    assert trace_suggestions[0]["sample_values"][0] == "trace-1001"
    assert any(item["pattern"].startswith("(?:^|[?&])token=") for item in token_suggestions)
