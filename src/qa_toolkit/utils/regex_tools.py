from __future__ import annotations

import difflib
import html
import re
from time import perf_counter
from typing import Any, Dict, Iterable, List, Sequence, Tuple

from qa_toolkit.config.constants import LANGUAGE_TEMPLATES

_VISIBLE_FLAG_ITEMS: Sequence[Tuple[str, int, str]] = (
    ("忽略大小写", re.IGNORECASE, "i"),
    ("多行模式", re.MULTILINE, "m"),
    ("点号匹配换行", re.DOTALL, "s"),
)

_TOKEN_PATTERN = re.compile(r"\d+|[A-Za-z]+|[\u4e00-\u9fff]+|\s+|[_-]+|[^A-Za-z0-9_\-\s\u4e00-\u9fff]+")


def build_regex_flags(
    *,
    ignore_case: bool = False,
    multiline: bool = False,
    dotall: bool = False,
) -> int:
    flags = 0
    if ignore_case:
        flags |= re.IGNORECASE
    if multiline:
        flags |= re.MULTILINE
    if dotall:
        flags |= re.DOTALL
    return flags


def describe_enabled_flags(flags: int) -> List[str]:
    enabled: List[str] = []
    for label, flag_value, flag_code in _VISIBLE_FLAG_ITEMS:
        if flags & flag_value:
            enabled.append(f"{flag_code} ({label})")
    return enabled


def _position_to_line_column(text: str, offset: int) -> Tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    last_newline = text.rfind("\n", 0, offset)
    if last_newline == -1:
        column = offset + 1
    else:
        column = offset - last_newline
    return line, column


def _summarize_groups(match: re.Match[str]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    indexed_groups = [{"index": index, "value": value} for index, value in enumerate(match.groups(), start=1)]
    named_groups = {name: value for name, value in match.groupdict().items()}
    return indexed_groups, named_groups


def _excerpt_text(text: str, spans: Sequence[Tuple[int, int]], *, context_chars: int = 40, max_windows: int = 6) -> Tuple[str, List[Tuple[int, int]], bool]:
    if len(text) <= 4000 or not spans:
        return text, list(spans), False

    windows: List[List[int]] = []
    for start, end in spans[:max_windows]:
        window_start = max(start - context_chars, 0)
        window_end = min(end + context_chars, len(text))
        if windows and window_start <= windows[-1][1]:
            windows[-1][1] = max(windows[-1][1], window_end)
        else:
            windows.append([window_start, window_end])

    parts: List[str] = []
    new_spans: List[Tuple[int, int]] = []
    cursor = 0
    inserted_gap = False
    for index, (window_start, window_end) in enumerate(windows):
        if index > 0:
            gap = "\n...\n"
            parts.append(gap)
            cursor += len(gap)
            inserted_gap = True

        chunk = text[window_start:window_end]
        parts.append(chunk)

        for start, end in spans:
            if start >= window_start and end <= window_end:
                new_spans.append((cursor + (start - window_start), cursor + (end - window_start)))

        cursor += len(chunk)

    return "".join(parts), new_spans, inserted_gap


def highlight_regex_matches(text: str, spans: Sequence[Tuple[int, int]]) -> str:
    excerpt, excerpt_spans, truncated = _excerpt_text(text, spans)

    if not excerpt_spans:
        return (
            "<div style='padding:14px;border:1px solid #dbeafe;border-radius:12px;background:#f8fafc;"
            "white-space:pre-wrap;word-break:break-word;font-family:Menlo,Consolas,monospace;'>"
            f"{html.escape(excerpt)}"
            "</div>"
        )

    parts: List[str] = []
    cursor = 0
    for start, end in excerpt_spans:
        if start > cursor:
            parts.append(html.escape(excerpt[cursor:start]))
        parts.append(
            "<mark style='background:#fde68a;color:#7c2d12;padding:0 2px;border-radius:4px;'>"
            f"{html.escape(excerpt[start:end])}"
            "</mark>"
        )
        cursor = end
    if cursor < len(excerpt):
        parts.append(html.escape(excerpt[cursor:]))

    title = "高亮预览（已截取匹配附近上下文）" if truncated else "高亮预览"
    return (
        "<div style='padding:14px;border:1px solid #dbeafe;border-radius:12px;background:#f8fafc;'>"
        f"<div style='font-size:12px;font-weight:700;color:#1d4ed8;margin-bottom:8px;'>{title}</div>"
        "<div style='white-space:pre-wrap;word-break:break-word;font-family:Menlo,Consolas,monospace;'>"
        + "".join(parts)
        + "</div></div>"
    )


def _build_match_records(matches: Iterable[re.Match[str]], text: str) -> List[Dict[str, Any]]:
    records: List[Dict[str, Any]] = []
    for index, match in enumerate(matches, start=1):
        start = match.start()
        end = match.end()
        line, column = _position_to_line_column(text, start)
        groups, named_groups = _summarize_groups(match)
        records.append(
            {
                "index": index,
                "match_text": match.group(),
                "start": start,
                "end": end,
                "length": end - start,
                "line": line,
                "column": column,
                "groups": groups,
                "named_groups": named_groups,
            }
        )
    return records


def _build_unique_rows(records: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    counter: Dict[str, int] = {}
    for record in records:
        text = record["match_text"]
        counter[text] = counter.get(text, 0) + 1

    return [
        {"match_text": match_text, "count": count}
        for match_text, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))
    ]


def build_replacement_diff(original_text: str, replaced_text: str, *, context_lines: int = 2) -> str:
    diff_lines = list(
        difflib.unified_diff(
            original_text.splitlines(),
            replaced_text.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm="",
            n=context_lines,
        )
    )
    return "\n".join(diff_lines)


def detect_regex_risks(
    pattern: str,
    *,
    text_length: int = 0,
    global_match: bool = True,
) -> List[Dict[str, str]]:
    warnings: List[Dict[str, str]] = []

    if re.search(r"\((?:[^()\\]|\\.)*[+*](?:[^()\\]|\\.)*\)\s*(?:[+*]|\{\d*,?\d*\})", pattern):
        warnings.append(
            {
                "level": "warning",
                "title": "疑似嵌套量词",
                "message": "表达式里存在重复组再叠加重复次数，复杂文本下可能触发灾难性回溯。",
            }
        )

    if re.search(r"\((?:[^()\\]|\\.)*\|(?:[^()\\]|\\.)+\)\s*(?:[+*]|\{\d*,?\d*\})", pattern):
        warnings.append(
            {
                "level": "warning",
                "title": "分支回溯成本较高",
                "message": "带有 alternation 的分组又被重复匹配，长文本下可能明显变慢。",
            }
        )

    if re.search(r"(^|[^\\])\.\*", pattern) and text_length >= 20000:
        warnings.append(
            {
                "level": "info",
                "title": "大文本全量扫描",
                "message": "表达式包含 `.*` 且当前文本较大，建议增加锚点或更明确的前缀。",
            }
        )

    if global_match:
        try:
            compiled = re.compile(pattern)
            zero_width = compiled.match("") and compiled.match("").end() == 0
            if zero_width:
                warnings.append(
                    {
                        "level": "info",
                        "title": "可命中空字符串",
                        "message": "全局匹配时可能出现大量零宽匹配，结果数量会快速放大。",
                    }
                )
        except re.error:
            pass

    if len(pattern) >= 120:
        warnings.append(
            {
                "level": "info",
                "title": "表达式较长",
                "message": "当前表达式较复杂，建议拆分验证并保留注释说明用途。",
            }
        )

    return warnings


def suggest_field_patterns(text: str, field_name: str) -> List[Dict[str, Any]]:
    normalized_field = field_name.strip()
    if not text or not normalized_field:
        return []

    escaped = re.escape(normalized_field)
    candidates: List[Tuple[str, str]] = [
        ("JSON 字符串字段", rf'"{escaped}"\s*:\s*"([^"]*)"'),
        ("JSON 通用字段", rf'"{escaped}"\s*:\s*([^,\}}\]\s]+)'),
        ("Query / 表单参数", rf"(?:^|[?&]){escaped}=([^&\s]+)"),
        ("日志或 KV 字段", rf"(?:^|[\s,;]){escaped}\s*[:=]\s*([^\s,;]+)"),
    ]

    suggestions: List[Dict[str, Any]] = []
    seen_patterns = set()
    for label, candidate in candidates:
        if candidate in seen_patterns:
            continue
        seen_patterns.add(candidate)

        try:
            matches = re.findall(candidate, text, re.MULTILINE)
        except re.error:
            continue

        if not matches:
            continue

        normalized_matches = [match if isinstance(match, str) else match[0] for match in matches]
        suggestions.append(
            {
                "label": label,
                "pattern": candidate,
                "match_count": len(normalized_matches),
                "sample_values": normalized_matches[:5],
            }
        )

    return suggestions


def analyze_regex(
    pattern: str,
    text: str,
    *,
    global_match: bool = True,
    ignore_case: bool = False,
    multiline: bool = False,
    dotall: bool = False,
    replacement: str | None = None,
    replace_all: bool | None = None,
) -> Dict[str, Any]:
    flags = build_regex_flags(ignore_case=ignore_case, multiline=multiline, dotall=dotall)

    start_time = perf_counter()
    compiled = re.compile(pattern, flags)
    if global_match:
        match_objects = list(compiled.finditer(text))
    else:
        first_match = compiled.search(text)
        match_objects = [first_match] if first_match else []
    elapsed_ms = (perf_counter() - start_time) * 1000

    records = _build_match_records(match_objects, text)
    spans = [(record["start"], record["end"]) for record in records]
    unique_rows = _build_unique_rows(records)
    zero_length_matches = sum(1 for record in records if record["length"] == 0)

    if replace_all is None:
        replace_all = global_match

    replacement_result = None
    if replacement is not None:
        replace_limit = 0 if replace_all else 1
        replaced_text, replacement_count = compiled.subn(replacement, text, count=replace_limit)
        replacement_result = {
            "text": replaced_text,
            "count": replacement_count,
            "mode": "全部替换" if replace_all else "仅替换首个匹配",
            "diff": build_replacement_diff(text, replaced_text),
        }

    return {
        "pattern": pattern,
        "flags": flags,
        "flags_display": describe_enabled_flags(flags),
        "global_match": global_match,
        "match_count": len(records),
        "has_match": bool(records),
        "unique_match_count": len(unique_rows),
        "zero_length_match_count": zero_length_matches,
        "group_count": compiled.groups,
        "named_group_names": list(compiled.groupindex.keys()),
        "execution_ms": round(elapsed_ms, 3),
        "risk_warnings": detect_regex_risks(pattern, text_length=len(text), global_match=global_match),
        "matches": records,
        "unique_matches": unique_rows,
        "preview_html": highlight_regex_matches(text, spans),
        "replacement": replacement_result,
    }


def _build_length_pattern(charset: str, values: Sequence[str]) -> str:
    lengths = sorted({len(value) for value in values})
    if not lengths:
        return ""
    if lengths == [1]:
        return charset
    if len(lengths) == 1:
        return f"{charset}{{{lengths[0]}}}"
    return f"{charset}{{{lengths[0]},{lengths[-1]}}}"


def _segment_kind(segment: str) -> str:
    if re.fullmatch(r"\d+", segment):
        return "digit"
    if re.fullmatch(r"[A-Za-z]+", segment):
        return "alpha"
    if re.fullmatch(r"[\u4e00-\u9fff]+", segment):
        return "chinese"
    if re.fullmatch(r"\s+", segment):
        return "space"
    if re.fullmatch(r"[_-]+", segment):
        return "joiner"
    return "literal"


def _build_segment_pattern(values: Sequence[str]) -> str:
    unique_values = sorted(set(values))
    kinds = {_segment_kind(value) for value in values}
    if len(unique_values) == 1:
        return re.escape(unique_values[0])
    if len(kinds) != 1:
        return "(?:" + "|".join(re.escape(value) for value in unique_values) + ")"

    kind = next(iter(kinds))
    if kind == "digit":
        return _build_length_pattern(r"\d", values)
    if kind == "alpha":
        return _build_length_pattern(r"[A-Za-z]", values)
    if kind == "chinese":
        return _build_length_pattern(r"[\u4e00-\u9fff]", values)
    if kind == "space":
        return _build_length_pattern(r"\s", values)
    if kind == "joiner":
        return _build_length_pattern(r"[_-]", values)
    return "(?:" + "|".join(re.escape(value) for value in unique_values) + ")"


def _build_tokenized_pattern(examples: Sequence[str]) -> str:
    tokenized = [_TOKEN_PATTERN.findall(example) for example in examples]
    token_lengths = {len(tokens) for tokens in tokenized}
    if len(token_lengths) != 1:
        return ""

    pieces: List[str] = []
    token_count = token_lengths.pop()
    for index in range(token_count):
        values = [tokens[index] for tokens in tokenized]
        pieces.append(_build_segment_pattern(values))
    return "".join(pieces)


def _build_prefix_suffix_pattern(examples: Sequence[str]) -> str:
    prefix = examples[0]
    suffix = examples[0]

    for example in examples[1:]:
        prefix_len = 0
        while prefix_len < min(len(prefix), len(example)) and prefix[prefix_len] == example[prefix_len]:
            prefix_len += 1
        prefix = prefix[:prefix_len]

        suffix_len = 0
        while (
            suffix_len < min(len(suffix), len(example))
            and suffix[-(suffix_len + 1)] == example[-(suffix_len + 1)]
        ):
            suffix_len += 1
        suffix = suffix[-suffix_len:] if suffix_len else ""

    middles = [example[len(prefix): len(example) - len(suffix) if suffix else len(example)] for example in examples]
    if all(middle for middle in middles):
        middle_pattern = _build_segment_pattern(middles)
        return re.escape(prefix) + middle_pattern + re.escape(suffix)
    return re.escape(examples[0])


def parse_example_items(examples: str) -> List[str]:
    return [item.strip() for item in re.split(r"[\n,，]+", examples or "") if item.strip()]


def generate_regex_from_examples(text: str, examples: str) -> str:
    del text
    example_list = parse_example_items(examples)
    if not example_list:
        return ""

    if len(set(example_list)) == 1:
        return re.escape(example_list[0])

    candidates = [
        _build_tokenized_pattern(example_list),
        _build_prefix_suffix_pattern(example_list),
        "(?:" + "|".join(re.escape(item) for item in sorted(set(example_list))) + ")",
    ]

    for candidate in candidates:
        if not candidate:
            continue
        try:
            if all(re.fullmatch(candidate, example) for example in example_list):
                return candidate
        except re.error:
            continue

    return re.escape(example_list[0])


def build_regex_code(
    pattern: str,
    *,
    target_language: str,
    operation_type: str,
    selected_flags: Sequence[str],
    replacement: str = "",
) -> Dict[str, Any]:
    language_config = LANGUAGE_TEMPLATES[target_language]
    template_key = "match" if operation_type == "匹配" else "test" if operation_type == "测试" else "replace"
    template = language_config[template_key]
    language_flags = language_config["flags"]

    effective_pattern = pattern
    if target_language == "Go":
        inline_flags = "".join(language_flags[flag] for flag in selected_flags)
        effective_pattern = inline_flags + pattern
        flag_payload = inline_flags
    elif target_language in {"Python", "Java", "C#"}:
        flag_payload = " | ".join(selected_flags) if selected_flags else "0"
    else:
        flag_payload = "".join(language_flags[flag] for flag in selected_flags)

    generated_code = template.format(
        pattern=effective_pattern,
        flags=flag_payload,
        flags_value=flag_payload,
        replacement=replacement,
    )

    return {
        "language": target_language,
        "operation": operation_type,
        "code": generated_code,
        "pattern": effective_pattern,
        "flags": flag_payload,
    }
