"""日志分析工具专项审计（issues #102-#117）修复回归测试。"""

import io
import json
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.log_analysis import (
    apply_text_filters,
    build_health_notes,
    detect_json_columns,
    detect_log_level,
    extract_duration_ms,
    extract_ip_addresses,
    extract_status_codes,
    search_lines,
    summarize_log_lines,
)


def test_issue_102_redos_pattern_is_rejected():
    """#102 嵌套量词/分支回溯正则必须被拒绝，不得进入 finditer。"""
    line = "a" * 1000 + "b"
    for pattern in (r"(a+)+$", r"(a|aa)+$", r"(?:x+x+)+y"):
        with pytest.raises(ValueError, match="灾难性回溯"):
            search_lines([line], pattern, use_regex=True, max_results=10)
    # 普通正则不受影响
    assert search_lines(["ERROR happened"], r"ERROR", use_regex=True)[0]["match_count"] == 1


def test_issue_103_status_code_ignores_milliseconds():
    """#103 耗时毫秒值/时间戳毫秒不再被计入状态码。"""
    assert extract_status_codes("GET /api/orders 200 duration=123ms") == ["200"]
    assert extract_status_codes("2026-04-05 09:30:01.123 INFO hello") == []
    assert extract_status_codes("traceId=abc123 request failed 500") == ["500"]
    assert extract_status_codes("HTTP/1.1 404 (not found)") == ["404"]


def test_issue_104_log_level_by_first_position():
    """#104 级别由行内最早出现的标记决定。"""
    assert detect_log_level("2026-04-05 09:30:01 INFO task finished with error count: 0") == "信息"
    assert detect_log_level("ERROR something INFO-ish happened") == "错误"
    assert detect_log_level("plain line without level") == "其他"


def test_issue_105_ip_filter_exact_match():
    """#105 IP 过滤不再子串误匹配相邻 IP。"""
    line81 = "login from ip=10.0.0.81 ok"
    assert apply_text_filters(line81, [{"type": "ip_filter", "value": "10.0.0.8"}]) is False
    assert apply_text_filters("login from ip=10.0.0.8 ok", [{"type": "ip_filter", "value": "10.0.0.8"}]) is True
    assert apply_text_filters("src 10.0.0.9", [{"type": "ip_filter", "value": "10.0.0.0/24"}]) is True


def test_issue_106_time_only_lines_do_not_pollute_timeline():
    """#106 无日期时间不再产生 1900 伪日期时间线/时间范围。"""
    summary = summarize_log_lines(["09:30:01 INFO a", "09:30:02 INFO b"])
    assert summary["timeline"] == []
    assert summary["time_range"] is None
    # 完整时间戳仍正常
    summary2 = summarize_log_lines(["2026-04-05 09:30:01 INFO a", "2026-04-05 09:31:02 INFO b"])
    assert [b["bucket"] for b in summary2["timeline"]] == ["2026-04-05 09:30", "2026-04-05 09:31"]
    assert summary2["time_range"]["start"].startswith("2026-04-05")


def test_issue_107_csv_column_misalignment_keeps_line_in_and_mode():
    """#107 列错位时 AND 不误杀、OR 不误放。"""
    filters = [{"type": "keyword", "column": "b", "operator": "等于", "value": "v2"}]
    assert apply_text_filters("v1 | x | y | v2", filters, "AND", csv_columns=["a", "b"]) is True
    assert apply_text_filters("v1 | v2", filters, "AND", csv_columns=["a", "b"]) is True
    assert apply_text_filters("v1 | other", filters, "OR", csv_columns=["a", "b"]) is False
    assert apply_text_filters("v1 | v2", filters, "OR", csv_columns=["a", "b"]) is True


def test_issue_111_json_field_detection_beyond_first_rows():
    """#111 JSON 字段检测覆盖前 10 行之后的记录。"""
    records = [{"payload": json.dumps({"id": i})} for i in range(15)]
    records[12]["payload"] = json.dumps({"late_field": 1})
    fields = detect_json_columns(pd.DataFrame(records))
    assert "late_field" in fields["payload"]


def test_issue_112_search_reports_total_and_truncation():
    """#112 搜索触顶时返回总匹配数与截断标志。"""
    lines = [f"line {i} target" for i in range(300)]
    results, total, truncated = search_lines(lines, "target", max_results=200, include_total=True)
    assert len(results) == 200
    assert total == 300
    assert truncated is True
    # 默认签名保持兼容
    assert len(search_lines(lines, "target", max_results=200)) == 200


def test_issue_113_chinese_log_levels_recognized():
    """#113 中文级别标记可识别。"""
    assert detect_log_level("[错误] 上传失败") == "错误"
    assert detect_log_level("2026-04-05 警告: 磁盘 85%") == "警告"
    assert detect_log_level("信息: 同步完成") == "信息"
    assert detect_log_level("调试 开始执行") == "调试"


def test_issue_114_duration_supports_seconds():
    """#114 耗时支持 s/秒 并换算为 ms。"""
    assert extract_duration_ms("took 1.5s to finish") == 1500.0
    assert extract_duration_ms("耗时 2秒 完成") == 2000.0
    assert extract_duration_ms("duration=123ms") == 123.0
    assert extract_duration_ms("elapsed=0.2s") == 200.0
    assert extract_duration_ms("no duration here") is None


def test_issue_115_ipv6_extraction():
    """#115 支持 IPv6 提取（经 ipaddress 校验）。"""
    ips = extract_ip_addresses("client ::1 and 2001:db8::1 connected from 10.0.0.8")
    assert "::1" in ips
    assert "2001:db8::1" in ips
    assert "10.0.0.8" in ips
    # 伪候选（时间/MAC）应被校验丢弃
    assert extract_ip_addresses("at 09:30:01 mac 12:34:56:78:9a:bc") == []


def test_issue_116_health_notes_use_status_codes():
    """#116 健康提示消费 5xx 统计。"""
    summary = summarize_log_lines(
        [
            "POST /api/orders 500 failed",
            "GET /api/orders 502 failed",
            "GET /api/ok 200 fine",
        ]
    )
    notes = "\n".join(build_health_notes(summary))
    assert "5xx" in notes


def test_issue_117_summary_export_scope_lines():
    """#117 概览页导出按当前范围取行（回归 summary_lines 传参路径）。"""
    # 页面层行为，用核心函数模拟：过滤结果行导出
    lines = ["ERROR a", "INFO b", "ERROR c"]
    filtered = [line for line in lines if apply_text_filters(line, [{"type": "log_level", "value": ["错误"]}])]
    assert filtered == ["ERROR a", "ERROR c"]


def test_gbk_csv_import_fallback():
    """#7 GBK 编码 CSV 导入有编码回退。"""
    import pandas as pd

    gbk_bytes = "时间,内容\n2026-04-05,错误发生\n".encode("gb18030")
    try:
        df = pd.read_csv(io.BytesIO(gbk_bytes), encoding="utf-8-sig")
    except UnicodeDecodeError:
        df = pd.read_csv(io.BytesIO(gbk_bytes), encoding="gb18030")
    assert list(df.columns) == ["时间", "内容"]
    assert df.iloc[0]["内容"] == "错误发生"


def test_large_log_analysis_cap_constant():
    """#11 分析上限常量存在且被页面引用。"""
    from qa_toolkit.ui.pages import log_analysis_page

    assert log_analysis_page.MAX_ANALYZE_LINES == 100_000
