from __future__ import annotations

import ipaddress
import json
import re
from collections import Counter
from datetime import datetime
from typing import Any, Dict, Iterable, List

import pandas as pd


LOG_LEVEL_PATTERNS = {
    "错误": re.compile(r"(^|[\s\[\(])(?:ERROR|ERR|FATAL|SEVERE|EXCEPTION)(?=$|[\s\]\):,])", re.IGNORECASE),
    "警告": re.compile(r"(^|[\s\[\(])(?:WARN|WARNING)(?=$|[\s\]\):,])", re.IGNORECASE),
    "信息": re.compile(r"(^|[\s\[\(])(?:INFO|INFORMATION)(?=$|[\s\]\):,])", re.IGNORECASE),
    "调试": re.compile(r"(^|[\s\[\(])(?:DEBUG|DBG|TRACE)(?=$|[\s\]\):,])", re.IGNORECASE),
}
TIMESTAMP_REGEXES = [
    re.compile(r"\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?(?:Z|[+-]\d{2}:?\d{2})?"),
    re.compile(r"\d{4}/\d{2}/\d{2}[ T]\d{2}:\d{2}:\d{2}(?:[.,]\d{1,6})?"),
    re.compile(r"\d{2}/\d{2}/\d{4}[ T]\d{2}:\d{2}:\d{2}"),
    re.compile(r"\d{2}:\d{2}:\d{2}"),
]
TIMESTAMP_FORMATS = [
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
    "%Y/%m/%d %H:%M:%S.%f",
    "%Y/%m/%d %H:%M:%S",
    "%d/%m/%Y %H:%M:%S",
    "%H:%M:%S",
]
IP_REGEX = re.compile(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
STATUS_CODE_REGEX = re.compile(r"(?<!\d)([1-5]\d{2})(?!\d)")
HTTP_PATH_REGEX = re.compile(
    r"(?:\"|^|\s)(GET|POST|PUT|DELETE|PATCH|HEAD|OPTIONS)\s+([^\s\"?]+)",
    re.IGNORECASE,
)
DURATION_PATTERNS = [
    re.compile(r"(?:duration|cost|elapsed|latency|耗时|用时)\s*[:=]\s*(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE),
    re.compile(r"(\d+(?:\.\d+)?)\s*ms", re.IGNORECASE),
]
EXCEPTION_REGEX = re.compile(r"\b([A-Z][A-Za-z0-9_]*(?:Exception|Error))\b")


def decode_log_bytes(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "gb18030"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1")


def stringify_dataframe_row(row: pd.Series) -> str:
    return " | ".join("" if pd.isna(value) else str(value) for value in row.tolist())


def dataframe_to_lines(df: pd.DataFrame) -> List[str]:
    if df.empty:
        return []
    return [stringify_dataframe_row(row) for _, row in df.iterrows()]


def detect_json_columns(df: pd.DataFrame, sample_rows: int = 10) -> Dict[str, List[str]]:
    json_fields: Dict[str, List[str]] = {}
    if df.empty:
        return json_fields

    for column in df.columns:
        discovered_keys = set()
        for value in df[column].dropna().head(sample_rows):
            try:
                if isinstance(value, dict):
                    discovered_keys.update(value.keys())
                    continue
                if isinstance(value, str):
                    stripped = value.strip()
                    if not stripped.startswith("{") or not stripped.endswith("}"):
                        continue
                    parsed = json.loads(stripped)
                    if isinstance(parsed, dict):
                        discovered_keys.update(parsed.keys())
            except Exception:
                continue
        if discovered_keys:
            json_fields[str(column)] = sorted(str(key) for key in discovered_keys)
    return json_fields


def detect_log_level(line: str) -> str:
    for level in ("错误", "警告", "信息", "调试"):
        if LOG_LEVEL_PATTERNS[level].search(line or ""):
            return level
    return "其他"


def parse_timestamp(text: str) -> datetime | None:
    if not text:
        return None

    for regex in TIMESTAMP_REGEXES:
        match = regex.search(text)
        if not match:
            continue

        timestamp_text = match.group()
        normalized = timestamp_text.replace(",", ".")

        if "T" in normalized or normalized.endswith("Z") or re.search(r"[+-]\d{2}:?\d{2}$", normalized):
            iso_text = normalized.replace("Z", "+00:00")
            if re.search(r"[+-]\d{4}$", iso_text):
                iso_text = f"{iso_text[:-5]}{iso_text[-5:-2]}:{iso_text[-2:]}"
            try:
                return datetime.fromisoformat(iso_text)
            except ValueError:
                pass

        for fmt in TIMESTAMP_FORMATS:
            try:
                return datetime.strptime(normalized, fmt)
            except ValueError:
                continue
    return None


def extract_timestamp(line: str) -> str:
    parsed = parse_timestamp(line)
    if parsed is None:
        return "未知时间"
    if parsed.year == 1900:
        return parsed.strftime("%H:%M:%S")
    return parsed.strftime("%Y-%m-%d %H:%M:%S")


def extract_ip_addresses(line: str) -> List[str]:
    results: List[str] = []
    seen = set()
    for candidate in IP_REGEX.findall(line or ""):
        try:
            ipaddress.ip_address(candidate)
        except ValueError:
            continue
        if candidate not in seen:
            seen.add(candidate)
            results.append(candidate)
    return results


def extract_status_codes(line: str) -> List[str]:
    results: List[str] = []
    seen = set()
    for candidate in STATUS_CODE_REGEX.findall(line or ""):
        code = int(candidate)
        if 100 <= code <= 599 and candidate not in seen:
            seen.add(candidate)
            results.append(candidate)
    return results


def extract_http_path(line: str) -> str | None:
    match = HTTP_PATH_REGEX.search(line or "")
    if not match:
        return None
    return match.group(2)


def extract_duration_ms(line: str) -> float | None:
    for pattern in DURATION_PATTERNS:
        match = pattern.search(line or "")
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                return None
    return None


def extract_exception_name(line: str) -> str | None:
    match = EXCEPTION_REGEX.search(line or "")
    if match:
        return match.group(1)
    return None


def _percentile(values: List[float], percentile: float) -> float | None:
    if not values:
        return None
    sorted_values = sorted(values)
    if len(sorted_values) == 1:
        return sorted_values[0]

    position = (len(sorted_values) - 1) * percentile
    lower = int(position)
    upper = min(lower + 1, len(sorted_values) - 1)
    weight = position - lower
    return sorted_values[lower] * (1 - weight) + sorted_values[upper] * weight


def summarize_log_lines(lines: Iterable[str], *, slow_threshold_ms: float = 1000.0, top_n: int = 10) -> Dict[str, Any]:
    line_list = list(lines or [])
    non_empty_lines = [line for line in line_list if str(line).strip()]

    level_counts = Counter(detect_log_level(line) for line in non_empty_lines)
    status_counts: Counter[str] = Counter()
    ip_counts: Counter[str] = Counter()
    path_counts: Counter[str] = Counter()
    exception_counts: Counter[str] = Counter()
    duplicate_counter = Counter(line.strip() for line in non_empty_lines)
    durations: List[float] = []
    timeline_counter: Counter[str] = Counter()
    parsed_timestamps: List[datetime] = []

    for line in non_empty_lines:
        for status_code in extract_status_codes(line):
            status_counts[status_code] += 1
        for ip in extract_ip_addresses(line):
            ip_counts[ip] += 1

        path = extract_http_path(line)
        if path:
            path_counts[path] += 1

        exception_name = extract_exception_name(line)
        if exception_name:
            exception_counts[exception_name] += 1

        duration_ms = extract_duration_ms(line)
        if duration_ms is not None:
            durations.append(duration_ms)

        parsed = parse_timestamp(line)
        if parsed:
            parsed_timestamps.append(parsed)
            bucket = parsed.strftime("%Y-%m-%d %H:%M")
            timeline_counter[bucket] += 1

    top_duplicate_lines = [
        {"line": line, "count": count}
        for line, count in duplicate_counter.most_common(top_n)
        if count > 1
    ]

    summary = {
        "total_lines": len(line_list),
        "non_empty_lines": len(non_empty_lines),
        "level_counts": {level: level_counts.get(level, 0) for level in ("错误", "警告", "信息", "调试", "其他")},
        "status_code_counts": status_counts.most_common(top_n),
        "ip_counts": ip_counts.most_common(top_n),
        "path_counts": path_counts.most_common(top_n),
        "exception_counts": exception_counts.most_common(top_n),
        "duplicate_lines": top_duplicate_lines,
        "duplicate_line_groups": len(top_duplicate_lines),
        "unique_ip_count": len(ip_counts),
        "exception_line_count": sum(exception_counts.values()),
        "slow_line_count": sum(1 for value in durations if value >= slow_threshold_ms),
        "time_range": None,
        "timeline": [{"bucket": bucket, "count": count} for bucket, count in sorted(timeline_counter.items())],
        "duration_stats": {
            "count": len(durations),
            "avg_ms": round(sum(durations) / len(durations), 2) if durations else None,
            "max_ms": round(max(durations), 2) if durations else None,
            "p95_ms": round(_percentile(durations, 0.95), 2) if durations else None,
            "p99_ms": round(_percentile(durations, 0.99), 2) if durations else None,
        },
    }

    if parsed_timestamps:
        time_start = min(parsed_timestamps)
        time_end = max(parsed_timestamps)
        summary["time_range"] = {
            "start": time_start.isoformat(sep=" ", timespec="seconds"),
            "end": time_end.isoformat(sep=" ", timespec="seconds"),
        }

    return summary


def build_health_notes(summary: Dict[str, Any]) -> List[str]:
    notes: List[str] = []
    total_lines = int(summary.get("total_lines", 0) or 0)
    level_counts = summary.get("level_counts", {})
    error_count = int(level_counts.get("错误", 0) or 0)
    warning_count = int(level_counts.get("警告", 0) or 0)
    duplicate_groups = int(summary.get("duplicate_line_groups", 0) or 0)
    slow_count = int(summary.get("slow_line_count", 0) or 0)
    exception_count = int(summary.get("exception_line_count", 0) or 0)

    if total_lines == 0:
        return ["当前日志为空，暂无可分析内容。"]

    if error_count == 0 and warning_count == 0:
        notes.append("当前日志未发现错误或警告级别行。")
    elif error_count > 0:
        notes.append(f"检测到 {error_count} 行错误日志，建议优先排查异常和失败链路。")

    if exception_count > 0:
        notes.append(f"日志中提取到 {exception_count} 条异常关键字，适合先看异常类型 Top。")

    if slow_count > 0:
        notes.append(f"检测到 {slow_count} 条慢日志，建议结合耗时分布看 P95/P99。")

    if duplicate_groups > 0:
        notes.append(f"发现 {duplicate_groups} 组重复日志，可能存在重试、循环刷屏或重复打印。")

    time_range = summary.get("time_range")
    if time_range:
        notes.append(f"日志时间范围从 {time_range['start']} 到 {time_range['end']}。")

    if not notes:
        notes.append("日志总体结构正常，可进一步使用筛选和搜索做精确排障。")
    return notes


def _parse_line_columns(line: str) -> List[str]:
    if " | " in line:
        return line.split(" | ")
    for separator in ("\t", "|", ","):
        if separator in line:
            return [item.strip() for item in line.split(separator)]
    return line.split()


def _is_empty_value(value: Any) -> bool:
    if value is None:
        return True
    normalized = str(value).strip().lower()
    return normalized in {"", "none", "null", "nan", "undefined"}


def _match_text_operator(value: Any, operator: str, expected: Any) -> bool:
    actual = "" if value is None else str(value)
    expected_text = "" if expected is None else str(expected)

    if operator == "有值":
        return not _is_empty_value(actual)
    if operator == "没有值":
        return _is_empty_value(actual)
    if operator == "等于":
        return actual == expected_text
    if operator == "开头为":
        return actual.startswith(expected_text)
    if operator == "结尾为":
        return actual.endswith(expected_text)
    return expected_text.lower() in actual.lower()


def _match_ip_filter(line: str, filter_value: str) -> bool:
    if not filter_value:
        return True

    extracted_ips = extract_ip_addresses(line)
    terms = [term.strip() for term in str(filter_value).split(",") if term.strip()]
    for term in terms:
        if "/" in term:
            try:
                network = ipaddress.ip_network(term, strict=False)
            except ValueError:
                continue
            if any(ipaddress.ip_address(ip) in network for ip in extracted_ips):
                return True
        elif term in line or term in extracted_ips:
            return True
    return False


def apply_text_filters(
    line: str,
    text_filters: List[Dict[str, Any]],
    logic_operator: str = "AND",
    csv_columns: List[str] | None = None,
) -> bool:
    if not text_filters:
        return True

    logic = str(logic_operator or "AND").upper()
    include_line = logic == "AND"

    for filter_config in text_filters:
        filter_type = filter_config.get("type")
        filter_value = filter_config.get("value")
        filter_operator = filter_config.get("operator", "包含")
        filter_match = False

        if filter_type == "keyword" and filter_config.get("column"):
            column_name = filter_config.get("column")
            columns = _parse_line_columns(line)
            if csv_columns and column_name in csv_columns and len(columns) == len(csv_columns):
                column_index = csv_columns.index(column_name)
                column_value = columns[column_index].strip()
                filter_match = _match_text_operator(column_value, filter_operator, filter_value)

        elif filter_type == "log_level":
            selected_levels = list(filter_value or [])
            filter_match = detect_log_level(line) in selected_levels

        elif filter_type == "ip_filter":
            filter_match = _match_ip_filter(line, str(filter_value or ""))

        elif filter_type == "status_code":
            codes = [code.strip() for code in str(filter_value or "").split(",") if code.strip()]
            line_codes = extract_status_codes(line)
            filter_match = any(code in line_codes for code in codes)

        elif filter_type == "keyword":
            filter_match = str(filter_value or "").lower() in line.lower()

        elif filter_type == "exclude_keyword":
            filter_match = str(filter_value or "").lower() not in line.lower()

        elif filter_type == "show_only_errors":
            filter_match = detect_log_level(line) == "错误" or bool(extract_exception_name(line))

        elif filter_type == "hide_debug":
            filter_match = detect_log_level(line) != "调试"

        if logic == "AND":
            include_line = include_line and filter_match
            if not include_line:
                break
        else:
            include_line = include_line or filter_match
            if include_line:
                break

    return include_line


def _load_json_cell(value: Any) -> Any:
    if isinstance(value, dict):
        return value
    if value is None or pd.isna(value):
        return None
    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return None
        return json.loads(stripped)
    return None


def apply_json_filters(df: pd.DataFrame, json_filters: List[Dict[str, Any]], logic_operator: str = "AND") -> pd.DataFrame:
    if not json_filters or df.empty:
        return df

    logic = str(logic_operator or "AND").upper()
    base_value = True if logic == "AND" else False
    mask = pd.Series([base_value] * len(df), index=df.index)

    for filter_config in json_filters:
        column = filter_config.get("column")
        field = filter_config.get("field")
        operator = filter_config.get("operator", "包含")
        value = filter_config.get("value")
        value_range = filter_config.get("value_range")

        if not column or not field or column not in df.columns:
            continue

        def check_json_condition(row: pd.Series) -> bool:
            try:
                json_data = _load_json_cell(row[column])
            except Exception:
                return False

            if not isinstance(json_data, dict) or field not in json_data:
                return False if operator != "没有值" else True

            field_value = json_data.get(field)
            if operator == "没有值":
                return _is_empty_value(field_value)
            if operator == "有值":
                return not _is_empty_value(field_value)
            if operator == "数值范围":
                if value_range is None:
                    return False
                if isinstance(field_value, (int, float)):
                    return float(value_range[0]) <= float(field_value) <= float(value_range[1])
                return False
            return _match_text_operator(field_value, operator, value)

        column_mask = df.apply(check_json_condition, axis=1)
        if logic == "AND":
            mask = mask & column_mask
        else:
            mask = mask | column_mask

    return df[mask]


def search_lines(
    lines: List[str],
    keyword: str,
    *,
    case_sensitive: bool = False,
    whole_word: bool = False,
    use_regex: bool = False,
    context_before: int = 0,
    context_after: int = 0,
    line_number_map: List[int] | None = None,
    max_results: int | None = 200,
) -> List[Dict[str, Any]]:
    if not keyword:
        return []

    flags = 0 if case_sensitive else re.IGNORECASE
    if use_regex:
        try:
            pattern = re.compile(keyword, flags)
        except re.error as exc:
            raise ValueError(f"正则表达式错误: {exc}") from exc
    else:
        escaped = re.escape(keyword)
        if whole_word:
            pattern = re.compile(rf"\b{escaped}\b", flags)
        else:
            pattern = re.compile(escaped, flags)

    results: List[Dict[str, Any]] = []
    for index, line in enumerate(lines):
        matches = list(pattern.finditer(line))
        if not matches:
            continue

        results.append(
            {
                "line_number": (line_number_map[index] + 1) if line_number_map and index < len(line_number_map) else index + 1,
                "line": line,
                "match_count": len(matches),
                "level": detect_log_level(line),
                "timestamp": extract_timestamp(line),
                "position": f"第 {matches[0].start() + 1} 字符",
                "context_before": [
                    {
                        "line_number": (line_number_map[ctx_index] + 1) if line_number_map and ctx_index < len(line_number_map) else ctx_index + 1,
                        "line": lines[ctx_index],
                    }
                    for ctx_index in range(max(0, index - context_before), index)
                ],
                "context_after": [
                    {
                        "line_number": (line_number_map[ctx_index] + 1) if line_number_map and ctx_index < len(line_number_map) else ctx_index + 1,
                        "line": lines[ctx_index],
                    }
                    for ctx_index in range(index + 1, min(len(lines), index + context_after + 1))
                ],
            }
        )

        if max_results and len(results) >= max_results:
            break

    return results


class LogAnalyzerUtils:
    """日志分析工具辅助类。"""

    decode_log_bytes = staticmethod(decode_log_bytes)
    stringify_dataframe_row = staticmethod(stringify_dataframe_row)
    dataframe_to_lines = staticmethod(dataframe_to_lines)
    detect_json_columns = staticmethod(detect_json_columns)
    summarize_log_lines = staticmethod(summarize_log_lines)
    build_health_notes = staticmethod(build_health_notes)
    apply_text_filters = staticmethod(apply_text_filters)
    apply_json_filters = staticmethod(apply_json_filters)
    search_lines = staticmethod(search_lines)
    detect_log_level = staticmethod(detect_log_level)
    extract_timestamp = staticmethod(extract_timestamp)

    @staticmethod
    def find_keyword_position(line: str, keyword: str) -> str:
        if not keyword:
            return "未指定"
        position = line.lower().find(keyword.lower())
        if position != -1:
            return f"第 {position + 1} 字符"
        return "未找到"
