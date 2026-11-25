from __future__ import annotations

import difflib
import hashlib
import html
import json
import re
from time import perf_counter
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

from qa_toolkit.core.regex_registry import get_code_language, get_field_extractors

try:  # regex 模块提供方法级 timeout，缺失时退回标准库（静态风险提示仍有效）
    import regex as _regex_engine
except ImportError:  # pragma: no cover - 取决于部署环境
    _regex_engine = None

_REGEX_ERROR = getattr(_regex_engine, "error", re.error) if _regex_engine else re.error

_VISIBLE_FLAG_ITEMS: Sequence[Tuple[str, int, str]] = (
    ("忽略大小写", re.IGNORECASE, "i"),
    ("多行模式", re.MULTILINE, "m"),
    ("点号匹配换行", re.DOTALL, "s"),
)

_TOKEN_PATTERN = re.compile(r"\d+|[A-Za-z]+|[\u4e00-\u9fff]+|\s+|[_-]+|[^A-Za-z0-9_\-\s\u4e00-\u9fff]+")

# 单次分析最多保留的匹配记录数，避免海量匹配拖垮页面。
MAX_MATCH_RECORDS = 5000
# 执行超时与文本上限：拒绝服务保护，统一由核心层执行，页面层不再各自硬编码。
DEFAULT_TIMEOUT_MS = 2000
MAX_TEXT_CHARS = 100_000
# 高亮窗口参数可由 configure_highlight 调整。
HIGHLIGHT_CONTEXT_CHARS = 40
HIGHLIGHT_MAX_WINDOWS = 6


def configure_highlight(*, context_chars: Optional[int] = None, max_windows: Optional[int] = None) -> None:
    """配置长文本高亮的上下文长度与窗口数量。"""
    global HIGHLIGHT_CONTEXT_CHARS, HIGHLIGHT_MAX_WINDOWS
    if context_chars is not None:
        if not isinstance(context_chars, int) or context_chars < 0:
            raise ValueError("context_chars 必须是非负整数")
        HIGHLIGHT_CONTEXT_CHARS = context_chars
    if max_windows is not None:
        if not isinstance(max_windows, int) or max_windows < 1:
            raise ValueError("max_windows 必须是正整数")
        HIGHLIGHT_MAX_WINDOWS = max_windows


def build_input_signature(
    pattern: str,
    text: str,
    *,
    flags: int,
    global_match: bool,
    replacement: Optional[str],
    replace_all: bool,
    context_chars: int,
    max_windows: int,
) -> str:
    """计算结果签名：输入任一变化即可判定展示中的结果已过期。"""
    payload = {
        "pattern": pattern,
        "text": text,
        "flags": flags,
        "global_match": bool(global_match),
        "replacement": replacement,
        "replace_all": bool(replace_all),
        "context_chars": context_chars,
        "max_windows": max_windows,
    }
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()[:16]


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


def _summarize_groups(match: Any) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    indexed_groups = [{"index": index, "value": value} for index, value in enumerate(match.groups(), start=1)]
    named_groups = {name: value for name, value in match.groupdict().items()}
    return indexed_groups, named_groups


def _excerpt_text(
    text: str,
    spans: Sequence[Tuple[int, int]],
    *,
    context_chars: Optional[int] = None,
    max_windows: Optional[int] = None,
) -> Tuple[str, List[Tuple[int, int]], bool]:
    context_chars = HIGHLIGHT_CONTEXT_CHARS if context_chars is None else context_chars
    max_windows = HIGHLIGHT_MAX_WINDOWS if max_windows is None else max_windows

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


def highlight_regex_matches(
    text: str,
    spans: Sequence[Tuple[int, int]],
    *,
    context_chars: Optional[int] = None,
    max_windows: Optional[int] = None,
) -> str:
    excerpt, excerpt_spans, truncated = _excerpt_text(
        text, spans, context_chars=context_chars, max_windows=max_windows
    )

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

    effective_windows = HIGHLIGHT_MAX_WINDOWS if max_windows is None else max_windows
    title = f"高亮预览（已截取前 {effective_windows} 个匹配窗口的上下文）" if truncated else "高亮预览"
    return (
        "<div style='padding:14px;border:1px solid #dbeafe;border-radius:12px;background:#f8fafc;'>"
        f"<div style='font-size:12px;font-weight:700;color:#1d4ed8;margin-bottom:8px;'>{title}</div>"
        "<div style='white-space:pre-wrap;word-break:break-word;font-family:Menlo,Consolas,monospace;'>"
        + "".join(parts)
        + "</div></div>"
    )


def _build_match_records(matches: Iterable[Any], text: str) -> List[Dict[str, Any]]:
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


def safe_csv_cell(value: Any) -> str:
    """防止 Excel / WPS 把用户内容当作公式执行。"""
    text = "" if value is None else str(value)
    if text.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + text
    return text


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
    """静态风险提示：与运行时超时保护互补，提示里给出可执行的改写建议。"""
    warnings: List[Dict[str, str]] = []
    timeout_hint = f"页面已启用 {DEFAULT_TIMEOUT_MS} 毫秒执行超时保护。"

    nested_quantifier = re.compile(
        r"\((?:[^()\\]|\\.)*?(?:[+*]|\{\d+(?:,\d*)?\})(?:[^()\\]|\\.)*?\)"
        r"\s*(?:[+*]|\{\d+(?:,\d*)?\})"
    )
    if nested_quantifier.search(pattern):
        warnings.append(
            {
                "level": "warning",
                "title": "疑似嵌套量词",
                "message": "分组内部已有重复量词，外层又重复匹配，长文本下可能触发灾难性回溯。建议合并量词或加锚点；" + timeout_hint,
            }
        )

    repeated_alternation = re.compile(
        r"\(([^()]*\|[^()]*)\)\s*(?:[+*]|\{\d+(?:,\d*)?\})"
    )
    overlap_match = repeated_alternation.search(pattern)
    if overlap_match:
        branches = [branch.strip() for branch in overlap_match.group(1).split("|") if branch.strip()]
        first_chars = {branch[0] for branch in branches if branch and branch[0].isalnum()}
        overlapping = len(branches) >= 2 and len(first_chars) == 1
        warnings.append(
            {
                "level": "warning",
                "title": "重复分支存在重叠前缀" if overlapping else "分支回溯成本较高",
                "message": (
                    "重复分组内的分支共享相同前缀（如 a / aa），长文本上会指数级回溯；建议合并分支、提取公共前缀或加锚点。"
                    if overlapping else "带 alternation 的分组又被重复匹配，长文本下可能明显变慢。"
                ) + timeout_hint,
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
            compiled = _compile_pattern(pattern, 0)
            if compiled.search("") or compiled.match(""):
                warnings.append(
                    {
                        "level": "info",
                        "title": "可命中空字符串",
                        "message": "全局匹配时可能出现大量零宽匹配，结果数量会快速放大。",
                    }
                )
        except (re.error, _REGEX_ERROR):
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


def _compile_pattern(pattern: str, flags: int) -> Any:
    if _regex_engine is not None:
        return _regex_engine.compile(pattern, flags)
    return re.compile(pattern, flags)


def _iter_matches(compiled: Any, text: str, timeout_seconds: Optional[float]) -> Iterable[Any]:
    if _regex_engine is not None and timeout_seconds is not None:
        return compiled.finditer(text, timeout=timeout_seconds)
    return compiled.finditer(text)


def _subn(compiled: Any, replacement: str, text: str, count: int, timeout_seconds: Optional[float]) -> Tuple[str, int]:
    if _regex_engine is not None and timeout_seconds is not None:
        return compiled.subn(replacement, text, count=count, timeout=timeout_seconds)
    return compiled.subn(replacement, text, count=count)


def _count_total_matches(compiled: Any, text: str, timeout_seconds: Optional[float]) -> Optional[int]:
    try:
        return sum(1 for _ in _iter_matches(compiled, text, timeout_seconds))
    except TimeoutError:
        return None


def suggest_field_patterns(text: str, field_name: str) -> List[Dict[str, Any]]:
    normalized_field = field_name.strip()
    if not text or not normalized_field:
        return []

    suggestions: List[Dict[str, Any]] = []
    seen_patterns: Set[str] = set()
    for extractor in get_field_extractors().values():
        try:
            candidate = extractor.build(text, normalized_field)
        except (re.error, ValueError):
            continue
        if not candidate or candidate in seen_patterns:
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
                "label": extractor.description or extractor.name,
                "pattern": candidate,
                "match_count": len(normalized_matches),
                "sample_values": normalized_matches[:5],
                "extractor": extractor.name,
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
    replacement: Optional[str] = None,
    replace_all: Optional[bool] = None,
    timeout_ms: Optional[int] = DEFAULT_TIMEOUT_MS,
    context_chars: Optional[int] = None,
    max_windows: Optional[int] = None,
) -> Dict[str, Any]:
    flags = build_regex_flags(ignore_case=ignore_case, multiline=multiline, dotall=dotall)
    effective_context = HIGHLIGHT_CONTEXT_CHARS if context_chars is None else context_chars
    effective_windows = HIGHLIGHT_MAX_WINDOWS if max_windows is None else max_windows
    signature = build_input_signature(
        pattern, text, flags=flags, global_match=global_match,
        replacement=replacement, replace_all=bool(replace_all) if replace_all is not None else global_match,
        context_chars=effective_context, max_windows=effective_windows,
    )
    timeout_seconds = None if timeout_ms is None else max(timeout_ms, 1) / 1000.0

    def _failure(title: str, message: str, elapsed: float) -> Dict[str, Any]:
        return {
            "pattern": pattern,
            "flags": flags,
            "flags_display": describe_enabled_flags(flags),
            "global_match": global_match,
            "match_count": 0,
            "has_match": False,
            "total_match_count": 0,
            "truncated": False,
            "unique_match_count": 0,
            "zero_length_match_count": 0,
            "group_count": 0,
            "named_group_names": [],
            "execution_ms": round(elapsed, 3),
            "risk_warnings": [{"level": "error", "title": title, "message": message}],
            "error": message,
            "matches": [],
            "unique_matches": [],
            "preview_html": highlight_regex_matches(
                text, [], context_chars=effective_context, max_windows=effective_windows
            ),
            "replacement": None,
            "signature": signature,
        }

    start_time = perf_counter()
    try:
        compiled = _compile_pattern(pattern, flags)
    except (re.error, _REGEX_ERROR) as exc:
        error_message = f"正则表达式错误: {exc}"
        return _failure("正则表达式无效", error_message, (perf_counter() - start_time) * 1000)

    if len(text) > MAX_TEXT_CHARS:
        message = f"测试文本超过 {MAX_TEXT_CHARS} 字符，请截断后再运行以避免页面卡死。"
        return _failure("文本过长", message, 0.0)

    match_objects: List[Any] = []
    truncated = False
    try:
        if global_match:
            for match in _iter_matches(compiled, text, timeout_seconds):
                match_objects.append(match)
                if len(match_objects) >= MAX_MATCH_RECORDS:
                    truncated = True
                    break
        else:
            first_match = (
                compiled.search(text, timeout=timeout_seconds)
                if _regex_engine is not None and timeout_seconds is not None
                else compiled.search(text)
            )
            match_objects = [first_match] if first_match else []
    except TimeoutError:
        message = (
            f"表达式执行超时（超过 {DEFAULT_TIMEOUT_MS if timeout_ms is None else timeout_ms} 毫秒），"
            "疑似灾难性回溯，已中止。请检查嵌套量词或重叠分支后重试。"
        )
        return _failure("执行超时", message, (perf_counter() - start_time) * 1000)

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
        try:
            replaced_text, replacement_count = _subn(
                compiled, replacement, text, replace_limit, timeout_seconds
            )
        except TimeoutError:
            message = (
                f"替换阶段执行超时（超过 {DEFAULT_TIMEOUT_MS if timeout_ms is None else timeout_ms} 毫秒），"
                "疑似灾难性回溯，已中止。请检查表达式后重试。"
            )
            return _failure("替换执行超时", message, (perf_counter() - start_time) * 1000)
        replacement_result = {
            "text": replaced_text,
            "count": replacement_count,
            "mode": "全部替换" if replace_all else "仅替换首个匹配",
            "diff": build_replacement_diff(text, replaced_text),
        }

    risk_warnings = detect_regex_risks(pattern, text_length=len(text), global_match=global_match)

    total_match_count: Optional[int] = len(records)
    if truncated:
        total_match_count = _count_total_matches(compiled, text, timeout_seconds)
        total_display = str(total_match_count) if total_match_count is not None else "超过"
        risk_warnings.append(
            {
                "level": "warning",
                "title": "匹配结果已截断",
                "message": (
                    f"匹配数量超过 {MAX_MATCH_RECORDS} 条（共 {total_display} 条），"
                    f"仅展示前 {MAX_MATCH_RECORDS} 条；唯一值指标基于截断样本。"
                ),
            }
        )

    return {
        "pattern": pattern,
        "flags": flags,
        "flags_display": describe_enabled_flags(flags),
        "global_match": global_match,
        "match_count": len(records),
        "has_match": bool(records),
        "total_match_count": total_match_count,
        "truncated": truncated,
        "unique_match_count": len(unique_rows),
        "unique_match_count_is_partial": truncated,
        "zero_length_match_count": zero_length_matches,
        "group_count": compiled.groups,
        "named_group_names": list(compiled.groupindex.keys()),
        "execution_ms": round(elapsed_ms, 3),
        "risk_warnings": risk_warnings,
        "matches": records,
        "unique_matches": unique_rows,
        "preview_html": highlight_regex_matches(
            text, spans, context_chars=effective_context, max_windows=effective_windows
        ),
        "replacement": replacement_result,
        "signature": signature,
    }


def parse_example_items(examples: str) -> List[str]:
    raw = (examples or "").strip()
    if not raw:
        return []
    if "\n" in raw or "\r" in raw:
        return [item.strip() for item in re.split(r"[\r\n]+", raw) if item.strip()]
    # 千分位数字（1,000 / 1,000,000）是单个示例，不应被逗号切开。
    if re.fullmatch(r"\d{1,3}(?:,\d{3})+", raw):
        return [raw]
    return [item.strip() for item in re.split(r"[,，]+", raw) if item.strip()]


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
    global_match: bool = True,
) -> Dict[str, Any]:
    """按注册的语言规格生成代码：转义、flags、匹配范围都由扩展点决定。"""
    spec = get_code_language(target_language)

    if operation_type == "匹配":
        template_key = "match_all" if global_match else "match_first"
        if template_key not in spec.templates:
            template_key = "match"
    elif operation_type == "测试":
        template_key = "test"
    else:
        template_key = "replace"
    template = spec.templates[template_key]

    selected = list(selected_flags or [])
    effective_pattern = pattern

    if spec.inline_flags:
        inline_flags = "".join(spec.flags.get(flag, "") for flag in selected)
        if inline_flags:
            # 内联 flag 必须对整个表达式生效，否则 (?i)cat|dog 只影响左分支。
            effective_pattern = inline_flags + "(?:" + pattern + ")"
        flag_payload = inline_flags
    elif spec.flag_style == "named":
        flag_payload = " | ".join(selected) if selected else "0"
    else:
        flag_payload = "".join(spec.flags.get(flag, "") for flag in selected)

    if (
        spec.global_flag
        and global_match
        and operation_type in {"匹配", "替换"}
        and spec.global_flag not in selected
        and spec.flag_style != "named"
    ):
        flag_payload += spec.global_flag

    generated_code = template.format(
        pattern=spec.escape_pattern(effective_pattern),
        flags=flag_payload,
        flags_value=flag_payload,
        replacement=spec.escape_replacement(replacement),
    )

    return {
        "language": target_language,
        "operation": operation_type,
        "code": generated_code,
        "pattern": effective_pattern,
        "flags": flag_payload,
        "global_match": bool(global_match),
    }
