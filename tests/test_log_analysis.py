import sys
from pathlib import Path

import pandas as pd


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.log_analysis import (
    apply_json_filters,
    apply_text_filters,
    detect_json_columns,
    detect_log_level,
    extract_timestamp,
    search_lines,
    summarize_log_lines,
)


def test_detect_log_level_avoids_partial_debug_match():
    assert detect_log_level("2026-04-05 10:00:00 DEBUG started") == "调试"
    assert detect_log_level("2026-04-05 10:00:00 debugger attached") == "其他"
    assert detect_log_level("2026-04-05 10:00:00 ERROR failed") == "错误"


def test_apply_text_filters_supports_quick_and_csv_column_filters():
    csv_columns = ["time", "status", "message"]
    line = "2026-04-05 10:00:00 | 500 | order create failed"

    filters = [
        {"type": "status_code", "value": "500"},
        {"type": "keyword", "column": "message", "operator": "包含", "value": "failed"},
    ]

    assert apply_text_filters(line, filters, logic_operator="AND", csv_columns=csv_columns) is True
    assert apply_text_filters(line, [{"type": "exclude_keyword", "value": "failed"}], logic_operator="AND") is False
    assert apply_text_filters(line, [{"type": "ip_filter", "value": "10.0.0.0/24"}], logic_operator="AND") is False


def test_apply_json_filters_supports_text_and_range_conditions():
    df = pd.DataFrame(
        {
            "payload": [
                '{"status":"ok","duration":120,"traceId":"abc"}',
                '{"status":"fail","duration":1820,"traceId":"def"}',
                '{"status":"ok","duration":75,"traceId":""}',
            ]
        }
    )

    filtered_contains = apply_json_filters(
        df,
        [{"column": "payload", "field": "status", "operator": "等于", "value": "ok"}],
    )
    filtered_range = apply_json_filters(
        df,
        [{"column": "payload", "field": "duration", "operator": "数值范围", "value_range": [100, 2000]}],
    )
    filtered_has_value = apply_json_filters(
        df,
        [{"column": "payload", "field": "traceId", "operator": "有值", "value": None}],
    )

    assert len(filtered_contains) == 2
    assert len(filtered_range) == 2
    assert len(filtered_has_value) == 2


def test_detect_json_columns_extracts_keys_from_stringified_dicts():
    df = pd.DataFrame(
        {
            "payload": ['{"status":"ok","duration":120}', '{"status":"fail","duration":1820}'],
            "message": ["plain text", "another text"],
        }
    )

    json_fields = detect_json_columns(df)

    assert json_fields == {"payload": ["duration", "status"]}


def test_summarize_log_lines_builds_structured_insights():
    lines = [
        "2026-04-05 09:30:01 INFO GET /api/orders 200 duration=120ms ip=10.0.0.8",
        "2026-04-05 09:30:03 WARN GET /api/orders 429 duration=850ms ip=10.0.0.8",
        "2026-04-05 09:30:07 ERROR POST /api/orders 500 duration=1820ms ip=10.0.1.16 RuntimeException: failed",
        "2026-04-05 09:30:07 ERROR POST /api/orders 500 duration=1820ms ip=10.0.1.16 RuntimeException: failed",
    ]

    summary = summarize_log_lines(lines, slow_threshold_ms=1000, top_n=5)

    assert summary["total_lines"] == 4
    assert summary["level_counts"]["错误"] == 2
    assert summary["status_code_counts"][0] == ("500", 2)
    assert summary["ip_counts"][0] == ("10.0.0.8", 2)
    assert summary["path_counts"][0] == ("/api/orders", 4)
    assert summary["exception_counts"][0] == ("RuntimeException", 2)
    assert summary["duplicate_line_groups"] == 1
    assert summary["slow_line_count"] == 2
    assert summary["time_range"]["start"] == "2026-04-05 09:30:01"


def test_search_lines_supports_regex_context_and_original_line_numbers():
    lines = [
        "2026-04-05 09:30:01 INFO gateway started",
        "2026-04-05 09:30:03 ERROR payment failed order=1001",
        "2026-04-05 09:30:05 INFO retry payment order=1001",
    ]

    results = search_lines(
        lines,
        "payment",
        use_regex=False,
        context_before=1,
        context_after=1,
        line_number_map=[10, 20, 30],
    )

    assert len(results) == 2
    assert results[0]["line_number"] == 21
    assert results[0]["context_before"][0]["line_number"] == 11
    assert results[0]["context_after"][0]["line_number"] == 31
    assert results[0]["position"] == "第 27 字符"


def test_extract_timestamp_returns_unknown_when_missing():
    assert extract_timestamp("no timestamp here") == "未知时间"
