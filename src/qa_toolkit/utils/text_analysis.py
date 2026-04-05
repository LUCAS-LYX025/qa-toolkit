from __future__ import annotations

import io
import os
import re
import shutil
import string
import subprocess
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


DEFAULT_SAMPLE_TEXT = """这是一个示例文本，用于展示升级后的字数统计工具。

你可以直接粘贴需求、接口说明、测试总结、周报或 Markdown 文本。
工具会同时给出基础统计、文本诊断、关键词频率和阅读时长等结果。

为了让统计更贴近真实使用场景，现在还支持：
- 导入 txt / md / json / csv / log 文件
- 预处理空白字符、连续空行和多余空格
- 识别重复行、长句和高频关键词
- 一键导出 JSON / CSV / TXT / Markdown 报告
"""

TEXT_UPLOAD_TYPES = ["txt", "md", "json", "csv", "log", "yaml", "yml", "doc", "docx"]
LATIN_WORD_RE = re.compile(r"[A-Za-z0-9]+(?:['’_-][A-Za-z0-9]+)*")
READING_UNIT_RE = re.compile(r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:['’_-][A-Za-z0-9]+)*")
KEYWORD_TOKEN_RE = re.compile(r"[\u4e00-\u9fff]{2,}|[A-Za-z0-9]+(?:['’_-][A-Za-z0-9]+)*")
SENTENCE_RE = re.compile(r"[^.!?。！？；;\n]+(?:[.!?。！？；;]+|$)")
WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "that",
    "the",
    "this",
    "to",
    "with",
}


def normalize_line_endings(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def _decode_plaintext_bytes(raw_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "gb18030"):
        try:
            return raw_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw_bytes.decode("latin-1")


def _extract_run_text(node: ET.Element) -> str:
    parts: List[str] = []
    for child in node.iter():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "t":
            parts.append(child.text or "")
        elif tag == "tab":
            parts.append("\t")
        elif tag in {"br", "cr"}:
            parts.append("\n")
    return "".join(parts).strip()


def _extract_text_from_docx(raw_bytes: bytes) -> str:
    try:
        archive = zipfile.ZipFile(io.BytesIO(raw_bytes))
    except zipfile.BadZipFile as exc:
        raise ValueError("DOCX 文件结构无效") from exc

    try:
        xml_bytes = archive.read("word/document.xml")
    except KeyError as exc:
        raise ValueError("DOCX 中缺少 document.xml") from exc
    finally:
        archive.close()

    root = ET.fromstring(xml_bytes)
    blocks: List[str] = []
    body = root.find("w:body", WORD_NS)
    if body is None:
        return ""

    for child in body:
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            paragraph_text = _extract_run_text(child)
            if paragraph_text:
                blocks.append(paragraph_text)
        elif tag == "tbl":
            table_rows: List[str] = []
            for row in child.findall("w:tr", WORD_NS):
                cell_texts: List[str] = []
                for cell in row.findall("w:tc", WORD_NS):
                    paragraph_texts = [_extract_run_text(paragraph) for paragraph in cell.findall(".//w:p", WORD_NS)]
                    cell_content = "\n".join(text for text in paragraph_texts if text)
                    cell_texts.append(cell_content)
                row_text = "\t".join(text for text in cell_texts if text)
                if row_text:
                    table_rows.append(row_text)
            if table_rows:
                blocks.append("\n".join(table_rows))

    return "\n\n".join(blocks).strip()


def _extract_text_with_textutil(raw_bytes: bytes, suffix: str) -> str:
    if shutil.which("textutil") is None:
        raise ValueError("当前运行环境未提供 textutil，暂时无法解析该 Word 文件。")

    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as file:
            file.write(raw_bytes)
            temp_path = file.name

        result = subprocess.run(
            ["textutil", "-convert", "txt", "-stdout", temp_path],
            capture_output=True,
            check=True,
        )
        return _decode_plaintext_bytes(result.stdout)
    except subprocess.CalledProcessError as exc:
        stderr = _decode_plaintext_bytes(exc.stderr or b"").strip()
        message = stderr or "Word 文件转换失败"
        raise ValueError(message) from exc
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def decode_uploaded_text(raw_bytes: bytes, filename: str | None = None) -> str:
    suffix = Path(filename or "").suffix.lower()

    if suffix == ".docx":
        try:
            return _extract_text_from_docx(raw_bytes)
        except ValueError:
            raise
        except Exception as exc:
            raise ValueError(f"DOCX 文件解析失败: {exc}") from exc

    if suffix == ".doc":
        return _extract_text_with_textutil(raw_bytes, suffix)

    return _decode_plaintext_bytes(raw_bytes)


def preprocess_text(
    text: str,
    *,
    trim_line_edges: bool = False,
    collapse_blank_lines: bool = False,
    collapse_inner_spaces: bool = False,
) -> Dict[str, Any]:
    original_text = normalize_line_endings(text)
    cleaned_text = original_text

    normalized_line_endings = text != original_text
    trimmed_lines = 0
    collapsed_blank_line_groups = 0
    collapsed_space_runs = 0

    if trim_line_edges:
        lines = cleaned_text.split("\n")
        updated_lines = []
        for line in lines:
            stripped = line.strip()
            if stripped != line:
                trimmed_lines += 1
            updated_lines.append(stripped)
        cleaned_text = "\n".join(updated_lines)

    if collapse_inner_spaces:
        updated_lines = []
        for line in cleaned_text.split("\n"):
            collapsed_line, replacement_count = re.subn(r"(?<=\S)[ \t]{2,}(?=\S)", " ", line)
            if replacement_count:
                collapsed_space_runs += replacement_count
            updated_lines.append(collapsed_line)
        cleaned_text = "\n".join(updated_lines)

    if collapse_blank_lines:
        cleaned_text, collapsed_blank_line_groups = re.subn(r"\n\s*\n(?:\s*\n)+", "\n\n", cleaned_text)

    changes: List[str] = []
    if normalized_line_endings:
        changes.append("已统一换行符格式")
    if trimmed_lines:
        changes.append(f"已清理 {trimmed_lines} 行的首尾空白")
    if collapsed_space_runs:
        changes.append(f"已压缩 {collapsed_space_runs} 处连续空格或制表符")
    if collapsed_blank_line_groups:
        changes.append(f"已合并 {collapsed_blank_line_groups} 组连续空行")

    return {
        "text": cleaned_text,
        "changed": cleaned_text != original_text,
        "changes": changes,
        "character_delta": len(original_text) - len(cleaned_text),
        "normalized_line_endings": normalized_line_endings,
        "trimmed_lines": trimmed_lines,
        "collapsed_blank_line_groups": collapsed_blank_line_groups,
        "collapsed_space_runs": collapsed_space_runs,
    }


def split_sentences(text: str) -> List[str]:
    normalized_text = normalize_line_endings(text)
    return [match.group().strip() for match in SENTENCE_RE.finditer(normalized_text) if match.group().strip()]


def _extract_latin_words(text: str) -> List[str]:
    return LATIN_WORD_RE.findall(text or "")


def _extract_reading_units(text: str) -> List[str]:
    return READING_UNIT_RE.findall(text or "")


def _extract_keyword_tokens(text: str, *, ignore_case: bool = True, min_length: int = 2) -> List[str]:
    tokens: List[str] = []
    for raw_token in KEYWORD_TOKEN_RE.findall(text or ""):
        token = raw_token.lower() if ignore_case and raw_token.isascii() else raw_token
        if token.isascii():
            normalized_token = token.strip(string.punctuation + "_-")
            if len(normalized_token) < min_length or normalized_token in STOPWORDS:
                continue
            tokens.append(normalized_token)
            continue

        if len(token) >= min_length:
            tokens.append(token)
    return tokens


def _build_suggestions(analysis: Dict[str, Any]) -> List[Dict[str, str]]:
    suggestions: List[Dict[str, str]] = []
    basic = analysis["basic"]
    quality = analysis["quality"]
    diagnostics = analysis["diagnostics"]

    if basic["total_chars"] < 50:
        suggestions.append(
            {
                "level": "warning",
                "title": "文本偏短",
                "message": f"当前仅 {basic['total_chars']} 字符，适合补充上下文、示例或结论。",
            }
        )

    if diagnostics["lines_with_edge_spaces"] > 0 or diagnostics["double_space_runs"] > 0:
        suggestions.append(
            {
                "level": "warning",
                "title": "存在空白噪音",
                "message": (
                    f"检测到 {diagnostics['lines_with_edge_spaces']} 行首尾空白，"
                    f"{diagnostics['double_space_runs']} 处连续空格。"
                ),
            }
        )

    if diagnostics["blank_lines"] > max(2, basic["total_paragraphs"]):
        suggestions.append(
            {
                "level": "info",
                "title": "空行偏多",
                "message": f"当前包含 {diagnostics['blank_lines']} 个空行，排版上可能偏松散。",
            }
        )

    if quality["avg_sentence_length"] > 28:
        suggestions.append(
            {
                "level": "warning",
                "title": "句子偏长",
                "message": f"平均句长约 {quality['avg_sentence_length']:.1f} 个阅读单元，建议拆分复杂长句。",
            }
        )
    elif basic["total_sentences"] >= 3 and quality["avg_sentence_length"] < 6:
        suggestions.append(
            {
                "level": "info",
                "title": "句子偏短",
                "message": f"平均句长约 {quality['avg_sentence_length']:.1f} 个阅读单元，可适度合并零散短句。",
            }
        )

    if diagnostics["repeated_line_count"] > 0:
        suggestions.append(
            {
                "level": "warning",
                "title": "存在重复行",
                "message": f"发现 {diagnostics['repeated_line_count']} 组重复行，适合去重或合并表达。",
            }
        )

    if quality["lexical_diversity"] and quality["lexical_diversity"] < 0.45 and analysis["keyword_stats"]["total_keywords"] >= 20:
        suggestions.append(
            {
                "level": "warning",
                "title": "用词重复度偏高",
                "message": f"词汇多样性仅 {quality['lexical_diversity']:.2f}，可考虑替换高频重复词。",
            }
        )

    if not suggestions and basic["total_chars"] >= 50:
        suggestions.append(
            {
                "level": "success",
                "title": "结构状态良好",
                "message": "未发现明显的长度、空白或重复问题，可以继续关注内容本身。",
            }
        )

    return suggestions


def analyze_text(
    text: str,
    *,
    ignore_case: bool = True,
    keyword_top_n: int = 12,
    char_top_n: int = 15,
    repeated_keyword_threshold: int = 2,
) -> Dict[str, Any]:
    normalized_text = normalize_line_endings(text)
    lines = normalized_text.split("\n") if normalized_text else []
    non_empty_lines = [line for line in lines if line.strip()]
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n+", normalized_text.strip()) if part.strip()] if normalized_text.strip() else []
    sentences = split_sentences(normalized_text)
    whitespace_words = normalized_text.split()
    latin_words = _extract_latin_words(normalized_text)
    reading_units = _extract_reading_units(normalized_text)
    keyword_tokens = _extract_keyword_tokens(normalized_text, ignore_case=ignore_case)

    char_frequency = Counter(normalized_text)
    keyword_frequency = Counter(keyword_tokens)
    repeated_keywords = sorted(
        [(token, count) for token, count in keyword_frequency.items() if count >= repeated_keyword_threshold],
        key=lambda item: (-item[1], item[0]),
    )

    repeated_lines_counter = Counter(line.strip() for line in non_empty_lines if line.strip())
    repeated_lines = [
        {"text": line, "count": count}
        for line, count in repeated_lines_counter.most_common()
        if count > 1
    ]

    sentence_lengths = [len(_extract_reading_units(sentence)) for sentence in sentences]
    paragraph_lengths = [len(_extract_reading_units(paragraph)) for paragraph in paragraphs]
    long_lines = sorted(
        [
            {"line_number": index + 1, "length": len(line), "text": line}
            for index, line in enumerate(lines)
            if len(line.strip()) >= 40
        ],
        key=lambda item: (-item["length"], item["line_number"]),
    )[:10]

    chinese_chars = sum(1 for char in normalized_text if "\u4e00" <= char <= "\u9fff")
    latin_letters = sum(1 for char in normalized_text if char.isalpha() and not ("\u4e00" <= char <= "\u9fff"))
    digits = sum(1 for char in normalized_text if char.isdigit())
    punctuation = sum(1 for char in normalized_text if unicodedata.category(char).startswith("P"))
    spaces = normalized_text.count(" ")
    tabs = normalized_text.count("\t")
    newlines = normalized_text.count("\n")
    whitespace_chars = sum(1 for char in normalized_text if char.isspace())
    blank_lines = sum(1 for line in lines if not line.strip())
    lines_with_leading_spaces = sum(1 for line in lines if line.startswith((" ", "\t")) and line.strip())
    lines_with_trailing_spaces = sum(1 for line in lines if line.endswith((" ", "\t")) and line.strip())
    double_space_runs = len(re.findall(r"(?<=\S)[ \t]{2,}(?=\S)", normalized_text))

    total_chars = len(normalized_text)
    total_words = len(whitespace_words)
    total_sentences = len(sentences)
    total_paragraphs = len(paragraphs)

    avg_word_length = sum(len(word) for word in whitespace_words) / total_words if total_words else 0.0
    avg_sentence_length = sum(sentence_lengths) / total_sentences if total_sentences else 0.0
    avg_paragraph_length = sum(paragraph_lengths) / total_paragraphs if total_paragraphs else 0.0
    lexical_diversity = len(set(keyword_tokens)) / len(keyword_tokens) if keyword_tokens else 0.0
    reading_time_minutes = len(reading_units) / 220 if reading_units else 0.0

    analysis = {
        "normalized_text": normalized_text,
        "sentences": sentences,
        "paragraphs": paragraphs,
        "basic": {
            "total_chars": total_chars,
            "total_chars_no_spaces": len(normalized_text.replace(" ", "")),
            "total_chars_no_whitespace": len(re.sub(r"\s+", "", normalized_text)),
            "total_words": total_words,
            "reading_units": len(reading_units),
            "latin_words": len(latin_words),
            "total_lines": len(lines),
            "non_empty_lines": len(non_empty_lines),
            "total_sentences": total_sentences,
            "total_paragraphs": total_paragraphs,
        },
        "char_types": {
            "latin_letters": latin_letters,
            "digits": digits,
            "punctuation": punctuation,
            "spaces": spaces,
            "tabs": tabs,
            "newlines": newlines,
            "whitespace_chars": whitespace_chars,
            "chinese_chars": chinese_chars,
            "other_chars": total_chars - (latin_letters + digits + punctuation + spaces + tabs + newlines + chinese_chars),
        },
        "quality": {
            "avg_word_length": avg_word_length,
            "avg_sentence_length": avg_sentence_length,
            "avg_paragraph_length": avg_paragraph_length,
            "reading_time_minutes": reading_time_minutes,
            "lexical_diversity": lexical_diversity,
            "longest_sentence_length": max(sentence_lengths, default=0),
            "longest_line_length": max((len(line) for line in lines), default=0),
        },
        "diagnostics": {
            "blank_lines": blank_lines,
            "lines_with_leading_spaces": lines_with_leading_spaces,
            "lines_with_trailing_spaces": lines_with_trailing_spaces,
            "lines_with_edge_spaces": lines_with_leading_spaces + lines_with_trailing_spaces,
            "double_space_runs": double_space_runs,
            "repeated_line_count": len(repeated_lines),
            "long_line_count": len(long_lines),
        },
        "frequencies": {
            "top_characters": char_frequency.most_common(char_top_n),
            "top_keywords": keyword_frequency.most_common(keyword_top_n),
        },
        "keyword_stats": {
            "total_keywords": len(keyword_tokens),
            "unique_keywords": len(set(keyword_tokens)),
            "repeated_keywords": repeated_keywords,
        },
        "repeated_lines": repeated_lines,
        "long_lines": long_lines,
    }
    analysis["suggestions"] = _build_suggestions(analysis)
    return analysis


def build_export_payload(
    analysis: Dict[str, Any],
    *,
    preprocess_result: Dict[str, Any] | None = None,
    source_label: str = "手动输入",
) -> Dict[str, Any]:
    top_keywords = [
        {"keyword": keyword, "count": count}
        for keyword, count in analysis["frequencies"]["top_keywords"]
    ]
    top_characters = [
        {"character": character, "count": count}
        for character, count in analysis["frequencies"]["top_characters"]
    ]

    payload = {
        "source": source_label,
        "basic": analysis["basic"],
        "char_types": analysis["char_types"],
        "quality": {
            key: round(value, 2) if isinstance(value, float) else value
            for key, value in analysis["quality"].items()
        },
        "diagnostics": analysis["diagnostics"],
        "top_keywords": top_keywords,
        "top_characters": top_characters,
        "repeated_lines": analysis["repeated_lines"],
        "suggestions": analysis["suggestions"],
    }
    if preprocess_result is not None:
        payload["preprocess"] = {
            "changed": preprocess_result.get("changed", False),
            "changes": preprocess_result.get("changes", []),
            "character_delta": preprocess_result.get("character_delta", 0),
        }
    return payload


def export_rows(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for category_key in ("basic", "char_types", "quality", "diagnostics"):
        category = payload.get(category_key, {})
        for metric, value in category.items():
            rows.append({"类别": category_key, "指标": metric, "数值": value})
    return rows


def build_text_report(
    payload: Dict[str, Any],
    *,
    generated_at: datetime | None = None,
) -> str:
    report_time = (generated_at or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
    preprocess_info = payload.get("preprocess", {})
    preprocess_lines = preprocess_info.get("changes") or ["未启用预处理"]
    suggestion_lines = payload.get("suggestions") or [{"title": "无", "message": "未生成建议"}]

    top_keywords = payload.get("top_keywords", [])
    keyword_text = "\n".join(
        f"- {item['keyword']}: {item['count']} 次"
        for item in top_keywords[:10]
    ) or "- 无"

    return (
        "文本统计报告\n"
        f"生成时间: {report_time}\n"
        f"来源: {payload.get('source', '手动输入')}\n"
        "==============================\n\n"
        "基础统计:\n"
        f"- 字符数（含空格）: {payload['basic']['total_chars']}\n"
        f"- 字符数（不含空格）: {payload['basic']['total_chars_no_spaces']}\n"
        f"- 字符数（不含空白）: {payload['basic']['total_chars_no_whitespace']}\n"
        f"- 单词数: {payload['basic']['total_words']}\n"
        f"- 阅读单元: {payload['basic']['reading_units']}\n"
        f"- 行数: {payload['basic']['total_lines']}\n"
        f"- 非空行: {payload['basic']['non_empty_lines']}\n"
        f"- 句子数: {payload['basic']['total_sentences']}\n"
        f"- 段落数: {payload['basic']['total_paragraphs']}\n\n"
        "质量指标:\n"
        f"- 平均词长: {payload['quality']['avg_word_length']}\n"
        f"- 平均句长: {payload['quality']['avg_sentence_length']}\n"
        f"- 平均段落长: {payload['quality']['avg_paragraph_length']}\n"
        f"- 预计阅读时间: {payload['quality']['reading_time_minutes']} 分钟\n"
        f"- 词汇多样性: {payload['quality']['lexical_diversity']}\n\n"
        "预处理摘要:\n"
        + "\n".join(f"- {line}" for line in preprocess_lines)
        + "\n\n关键词 Top10:\n"
        + keyword_text
        + "\n\n建议:\n"
        + "\n".join(f"- {item['title']}: {item['message']}" for item in suggestion_lines)
        + "\n"
    )
