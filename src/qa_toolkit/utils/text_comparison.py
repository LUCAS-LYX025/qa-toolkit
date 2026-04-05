from __future__ import annotations

import difflib
import html
import re
from typing import Any, Dict, List

from qa_toolkit.utils.text_analysis import normalize_line_endings


DEFAULT_LEFT_TEXT = """接口返回示例
status: success
message: 创建订单成功
data:
  id: 1001
  amount: 199
  coupon: null
"""

DEFAULT_RIGHT_TEXT = """接口返回示例
status: success
message: 订单创建成功
data:
  id: 1001
  amount: 299
  discount: 20
"""

WORD_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9]+(?:['’_-][A-Za-z0-9]+)*")
TOKEN_RE = re.compile(r"[\u4e00-\u9fff]+|[A-Za-z0-9]+(?:['’_-][A-Za-z0-9]+)*|[^\w\s]|\s+")


def split_lines(text: str) -> List[str]:
    normalized = normalize_line_endings(text)
    if not normalized:
        return []
    return normalized.split("\n")


def tokenize_text(text: str) -> List[str]:
    return TOKEN_RE.findall(normalize_line_endings(text))


def build_text_profile(text: str) -> Dict[str, int]:
    normalized = normalize_line_endings(text)
    lines = split_lines(normalized)
    non_empty_lines = [line for line in lines if line.strip()]
    paragraphs = [block for block in re.split(r"\n\s*\n", normalized) if block.strip()]
    return {
        "chars": len(normalized),
        "lines": len(lines),
        "non_empty_lines": len(non_empty_lines),
        "words": len(WORD_RE.findall(normalized)),
        "paragraphs": len(paragraphs),
    }


def normalize_compare_text(
    text: str,
    *,
    ignore_case: bool = False,
    trim_line_edges: bool = False,
    collapse_inner_spaces: bool = False,
    ignore_blank_lines: bool = False,
) -> Dict[str, Any]:
    original_text = normalize_line_endings(text)
    normalized_line_endings = text != original_text
    source_lines = split_lines(original_text)

    trimmed_lines = 0
    collapsed_space_runs = 0
    removed_blank_lines = 0
    case_folded_lines = 0
    normalized_lines: List[str] = []

    for line in source_lines:
        updated_line = line

        if trim_line_edges:
            stripped_line = updated_line.strip()
            if stripped_line != updated_line:
                trimmed_lines += 1
            updated_line = stripped_line

        if collapse_inner_spaces:
            updated_line, replacement_count = re.subn(r"[ \t]{2,}", " ", updated_line)
            collapsed_space_runs += replacement_count

        if ignore_case:
            folded_line = updated_line.lower()
            if folded_line != updated_line:
                case_folded_lines += 1
            updated_line = folded_line

        if ignore_blank_lines and not updated_line.strip():
            removed_blank_lines += 1
            continue

        normalized_lines.append(updated_line)

    normalized_text = "\n".join(normalized_lines)
    changes: List[str] = []
    if normalized_line_endings:
        changes.append("已统一换行符格式")
    if trimmed_lines:
        changes.append(f"已清理 {trimmed_lines} 行首尾空白")
    if collapsed_space_runs:
        changes.append(f"已压缩 {collapsed_space_runs} 处连续空格或制表符")
    if removed_blank_lines:
        changes.append(f"已忽略 {removed_blank_lines} 个空行")
    if case_folded_lines:
        changes.append(f"已按忽略大小写规则处理 {case_folded_lines} 行")

    return {
        "text": normalized_text,
        "lines": normalized_lines,
        "changed": normalized_text != original_text,
        "changes": changes,
        "normalized_line_endings": normalized_line_endings,
        "trimmed_lines": trimmed_lines,
        "collapsed_space_runs": collapsed_space_runs,
        "removed_blank_lines": removed_blank_lines,
        "case_folded_lines": case_folded_lines,
    }


def _line_similarity(left_line: str, right_line: str) -> float | None:
    if not left_line or not right_line:
        return None
    return round(difflib.SequenceMatcher(None, left_line, right_line).ratio(), 3)


def compare_line_texts(left_text: str, right_text: str) -> Dict[str, Any]:
    left_lines = split_lines(left_text)
    right_lines = split_lines(right_text)
    matcher = difflib.SequenceMatcher(None, left_lines, right_lines)

    change_rows: List[Dict[str, Any]] = []
    change_blocks: List[Dict[str, Any]] = []
    equal_lines = 0
    group_index = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            equal_lines += i2 - i1
            continue

        group_index += 1
        left_chunk = left_lines[i1:i2]
        right_chunk = right_lines[j1:j2]
        change_blocks.append(
            {
                "group": group_index,
                "tag": tag,
                "left_range": f"{i1 + 1}-{i2}" if left_chunk else "-",
                "right_range": f"{j1 + 1}-{j2}" if right_chunk else "-",
                "left_preview": "\n".join(left_chunk[:2]).strip(),
                "right_preview": "\n".join(right_chunk[:2]).strip(),
            }
        )

        if tag == "replace":
            max_len = max(len(left_chunk), len(right_chunk))
            for offset in range(max_len):
                left_exists = offset < len(left_chunk)
                right_exists = offset < len(right_chunk)
                left_line = left_chunk[offset] if left_exists else ""
                right_line = right_chunk[offset] if right_exists else ""

                if left_exists and right_exists:
                    status = "修改"
                elif left_exists:
                    status = "删除"
                else:
                    status = "新增"

                change_rows.append(
                    {
                        "group": group_index,
                        "status": status,
                        "left_line_number": i1 + offset + 1 if left_exists else None,
                        "right_line_number": j1 + offset + 1 if right_exists else None,
                        "left_text": left_line,
                        "right_text": right_line,
                        "similarity": _line_similarity(left_line, right_line),
                    }
                )
            continue

        if tag == "delete":
            for offset, line in enumerate(left_chunk):
                change_rows.append(
                    {
                        "group": group_index,
                        "status": "删除",
                        "left_line_number": i1 + offset + 1,
                        "right_line_number": None,
                        "left_text": line,
                        "right_text": "",
                        "similarity": None,
                    }
                )
            continue

        if tag == "insert":
            for offset, line in enumerate(right_chunk):
                change_rows.append(
                    {
                        "group": group_index,
                        "status": "新增",
                        "left_line_number": None,
                        "right_line_number": j1 + offset + 1,
                        "left_text": "",
                        "right_text": line,
                        "similarity": None,
                    }
                )

    unified_diff = "\n".join(
        difflib.unified_diff(
            left_lines,
            right_lines,
            fromfile="原始文本",
            tofile="对比文本",
            lineterm="",
        )
    )

    added_lines = sum(1 for row in change_rows if row["status"] == "新增")
    removed_lines = sum(1 for row in change_rows if row["status"] == "删除")
    modified_lines = sum(1 for row in change_rows if row["status"] == "修改")
    first_change = change_rows[0] if change_rows else None

    return {
        "rows": change_rows,
        "blocks": change_blocks,
        "unified_diff": unified_diff,
        "summary": {
            "left_line_count": len(left_lines),
            "right_line_count": len(right_lines),
            "equal_lines": equal_lines,
            "added_lines": added_lines,
            "removed_lines": removed_lines,
            "modified_lines": modified_lines,
            "change_groups": len(change_blocks),
            "line_similarity": round(matcher.ratio(), 4),
            "first_change_left_line": first_change.get("left_line_number") if first_change else None,
            "first_change_right_line": first_change.get("right_line_number") if first_change else None,
        },
    }


def _count_significant_tokens(tokens: List[str]) -> int:
    return sum(1 for token in tokens if token.strip())


def compare_token_texts(left_text: str, right_text: str) -> Dict[str, Any]:
    left_tokens = tokenize_text(left_text)
    right_tokens = tokenize_text(right_text)
    matcher = difflib.SequenceMatcher(None, left_tokens, right_tokens)

    segments: List[Dict[str, str]] = []
    change_rows: List[Dict[str, Any]] = []
    equal_count = 0
    inserted_count = 0
    deleted_count = 0
    replaced_blocks = 0

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        left_chunk = left_tokens[i1:i2]
        right_chunk = right_tokens[j1:j2]
        left_text_chunk = "".join(left_chunk)
        right_text_chunk = "".join(right_chunk)

        if tag == "equal":
            equal_count += _count_significant_tokens(left_chunk)
            if left_text_chunk:
                segments.append({"type": "equal", "text": left_text_chunk})
            continue

        if tag == "replace":
            replaced_blocks += 1
            deleted_count += _count_significant_tokens(left_chunk)
            inserted_count += _count_significant_tokens(right_chunk)
            if left_text_chunk:
                segments.append({"type": "delete", "text": left_text_chunk})
            if right_text_chunk:
                segments.append({"type": "insert", "text": right_text_chunk})
            change_rows.append(
                {
                    "status": "修改",
                    "left_text": left_text_chunk,
                    "right_text": right_text_chunk,
                    "similarity": round(difflib.SequenceMatcher(None, left_text_chunk, right_text_chunk).ratio(), 3),
                }
            )
            continue

        if tag == "delete":
            deleted_count += _count_significant_tokens(left_chunk)
            if left_text_chunk:
                segments.append({"type": "delete", "text": left_text_chunk})
                change_rows.append(
                    {
                        "status": "删除",
                        "left_text": left_text_chunk,
                        "right_text": "",
                        "similarity": None,
                    }
                )
            continue

        if tag == "insert":
            inserted_count += _count_significant_tokens(right_chunk)
            if right_text_chunk:
                segments.append({"type": "insert", "text": right_text_chunk})
                change_rows.append(
                    {
                        "status": "新增",
                        "left_text": "",
                        "right_text": right_text_chunk,
                        "similarity": None,
                    }
                )

    return {
        "segments": segments,
        "rows": change_rows,
        "summary": {
            "left_token_count": _count_significant_tokens(left_tokens),
            "right_token_count": _count_significant_tokens(right_tokens),
            "equal_tokens": equal_count,
            "inserted_tokens": inserted_count,
            "deleted_tokens": deleted_count,
            "replaced_blocks": replaced_blocks,
            "token_similarity": round(matcher.ratio(), 4),
        },
    }


def render_token_diff_html(segments: List[Dict[str, str]], *, hide_equal: bool = False) -> str:
    html_parts = [
        "<div style='background:#f8fafc;border:1px solid #e2e8f0;border-radius:10px;padding:14px;"
        "font-family:monospace;white-space:pre-wrap;line-height:1.7;'>"
    ]

    for segment in segments:
        segment_type = segment.get("type", "equal")
        text = segment.get("text", "")
        if not text:
            continue
        if hide_equal and segment_type == "equal":
            continue

        escaped_text = html.escape(text)
        if segment_type == "delete":
            html_parts.append(
                "<span style='background:#fee2e2;color:#991b1b;padding:1px 3px;border-radius:4px;"
                "text-decoration:line-through;'>"
                f"{escaped_text}</span>"
            )
        elif segment_type == "insert":
            html_parts.append(
                "<span style='background:#dcfce7;color:#166534;padding:1px 3px;border-radius:4px;'>"
                f"{escaped_text}</span>"
            )
        else:
            html_parts.append(f"<span style='color:#475569;'>{escaped_text}</span>")

    html_parts.append("</div>")
    return "".join(html_parts)


def compare_texts(
    left_text: str,
    right_text: str,
    *,
    ignore_case: bool = False,
    trim_line_edges: bool = False,
    collapse_inner_spaces: bool = False,
    ignore_blank_lines: bool = False,
) -> Dict[str, Any]:
    left_normalized = normalize_compare_text(
        left_text,
        ignore_case=ignore_case,
        trim_line_edges=trim_line_edges,
        collapse_inner_spaces=collapse_inner_spaces,
        ignore_blank_lines=ignore_blank_lines,
    )
    right_normalized = normalize_compare_text(
        right_text,
        ignore_case=ignore_case,
        trim_line_edges=trim_line_edges,
        collapse_inner_spaces=collapse_inner_spaces,
        ignore_blank_lines=ignore_blank_lines,
    )

    line_diff = compare_line_texts(left_normalized["text"], right_normalized["text"])
    token_diff = compare_token_texts(left_normalized["text"], right_normalized["text"])
    text_similarity = difflib.SequenceMatcher(None, left_normalized["text"], right_normalized["text"]).ratio()

    return {
        "left": {
            "original_text": normalize_line_endings(left_text),
            "normalized": left_normalized,
            "profile": build_text_profile(left_text),
            "normalized_profile": build_text_profile(left_normalized["text"]),
        },
        "right": {
            "original_text": normalize_line_endings(right_text),
            "normalized": right_normalized,
            "profile": build_text_profile(right_text),
            "normalized_profile": build_text_profile(right_normalized["text"]),
        },
        "settings": {
            "ignore_case": ignore_case,
            "trim_line_edges": trim_line_edges,
            "collapse_inner_spaces": collapse_inner_spaces,
            "ignore_blank_lines": ignore_blank_lines,
        },
        "summary": {
            "text_similarity": round(text_similarity, 4),
            "changed": bool(line_diff["rows"]),
            "change_row_count": len(line_diff["rows"]),
            "change_group_count": line_diff["summary"]["change_groups"],
            "added_lines": line_diff["summary"]["added_lines"],
            "removed_lines": line_diff["summary"]["removed_lines"],
            "modified_lines": line_diff["summary"]["modified_lines"],
            "line_similarity": line_diff["summary"]["line_similarity"],
            "token_similarity": token_diff["summary"]["token_similarity"],
            "first_change_left_line": line_diff["summary"]["first_change_left_line"],
            "first_change_right_line": line_diff["summary"]["first_change_right_line"],
        },
        "line_diff": line_diff,
        "token_diff": token_diff,
    }


def build_comparison_report(
    result: Dict[str, Any],
    *,
    left_source: str = "原始文本",
    right_source: str = "对比文本",
) -> str:
    summary = result.get("summary", {})
    line_rows = result.get("line_diff", {}).get("rows", [])
    lines = [
        "# 文本对比报告",
        "",
        f"- 原始来源: {left_source}",
        f"- 对比来源: {right_source}",
        f"- 文本相似度: {summary.get('text_similarity', 0):.2%}",
        f"- 行相似度: {summary.get('line_similarity', 0):.2%}",
        f"- 词级相似度: {summary.get('token_similarity', 0):.2%}",
        f"- 修改行: {summary.get('modified_lines', 0)}",
        f"- 新增行: {summary.get('added_lines', 0)}",
        f"- 删除行: {summary.get('removed_lines', 0)}",
        "",
        "## 行级差异",
    ]

    if not line_rows:
        lines.append("- 未发现差异")
    else:
        for row in line_rows[:50]:
            lines.append(
                f"- [{row['status']}] 左 {row.get('left_line_number') or '-'} / 右 {row.get('right_line_number') or '-'}"
            )
            lines.append(f"  原始: {row.get('left_text', '')}")
            lines.append(f"  对比: {row.get('right_text', '')}")

    unified_diff = result.get("line_diff", {}).get("unified_diff", "")
    lines.extend(["", "## Unified Diff", "```diff", unified_diff or "(无差异)", "```"])
    return "\n".join(lines).strip() + "\n"
