"""正则测试工具的可注册扩展点。

预定义模式、QA 场景样例、代码生成语言与字段提取规则都通过注册表提供，
新增公司私有规则或新语言只需 register，不必修改 constants.py 或页面核心逻辑。

设计约束：
- 默认注册表与历史行为兼容（默认值即旧常量），保证零回归；
- 提供 reset_regex_registry() 便于测试隔离；
- 每个扩展点带稳定 name，导出 payload 可记录使用了哪些规则。
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Set

from qa_toolkit.config.constants import LANGUAGE_TEMPLATES, PREDEFINED_PATTERNS


PatternBuilder = Callable[[str, str], Optional[str]]
LiteralEscaper = Callable[[str], str]


@dataclass(frozen=True)
class PatternPreset:
    """一个预定义表达式。"""

    name: str
    pattern: str
    description: str = ""
    replacement: str = ""


@dataclass(frozen=True)
class SampleCase:
    """一个可直接载入的 QA 场景样例。"""

    name: str
    pattern: str
    text: str
    replacement: str = ""
    description: str = ""


@dataclass(frozen=True)
class FieldExtractor:
    """字段提取向导的一个候选规则构造器。"""

    name: str
    build: PatternBuilder
    description: str = ""


@dataclass(frozen=True)
class CodeLanguageSpec:
    """代码生成目标语言：模板 / flags / 字面量转义规则都由扩展点决定。"""

    name: str
    templates: Mapping[str, str]
    flags: Mapping[str, str]
    escape_pattern: LiteralEscaper
    escape_replacement: LiteralEscaper
    flag_style: str = "suffix"  # suffix | named | inline
    inline_flags: bool = False
    global_flag: str = ""
    description: str = ""


# ---------------------------------------------------------------------------
# 字面量转义：按目标语言的字符串 / 正则字面量规则处理用户输入
# ---------------------------------------------------------------------------

def escape_delimited_regex(value: str, delimiter: str = "/") -> str:
    """JS / PHP / Ruby 的 /.../ 字面量：转义分隔符与真实换行。"""
    parts: List[str] = []
    index = 0
    while index < len(value):
        char = value[index]
        if char == "\\" and index + 1 < len(value):
            parts.append(value[index:index + 2])
            index += 2
            continue
        if char == delimiter:
            parts.append("\\" + delimiter)
        elif char == "\n":
            parts.append(r"\n")
        elif char == "\r":
            parts.append(r"\r")
        else:
            parts.append(char)
        index += 1
    return "".join(parts)


def escape_python_literal(value: str) -> str:
    """Python 用 repr 生成完整字面量：raw string 无法安全承载引号。"""
    return repr(value)


def escape_java_literal(value: str) -> str:
    """Java 双引号字符串内部内容（JSON 的转义规则与之兼容）。"""
    return json.dumps(value, ensure_ascii=True)[1:-1]


def escape_cs_verbatim(value: str) -> str:
    """C# verbatim 字符串 @\"...\" 内部内容。"""
    return value.replace('"', '""')


def escape_php_literal(value: str) -> str:
    """PHP 单引号正则串：先处理反斜杠，再处理单引号与分隔符。"""
    return value.replace("\\", "\\\\").replace("'", "\\'").replace("/", "\\/")


def escape_go_raw(value: str) -> str:
    """Go 反引号字符串不能包含反引号，用 RE2 十六进制转义代替。"""
    return value.replace("`", r"\x60")


def escape_ruby_replacement(value: str) -> str:
    """Ruby 单引号字符串只识别 \\\\ 和 \\'。"""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def escape_double_quoted_inner(value: str) -> str:
    """Go / Java / JS 双引号字符串内部内容。"""
    return json.dumps(value, ensure_ascii=True)[1:-1]


def escape_json_literal(value: str) -> str:
    """JS 替换文本：完整双引号字面量。"""
    return json.dumps(value, ensure_ascii=False)


# ---------------------------------------------------------------------------
# 默认扩展点
# ---------------------------------------------------------------------------

def _default_presets() -> Dict[str, PatternPreset]:
    return {
        name: PatternPreset(name=name, pattern=pattern)
        for name, pattern in PREDEFINED_PATTERNS.items()
    }


def _default_samples() -> Dict[str, SampleCase]:
    return {
        "接口响应字段提取": SampleCase(
            name="接口响应字段提取",
            pattern=r'"traceId"\s*:\s*"([^"]+)"',
            text='{\n  "code": 0,\n  "message": "success",\n  "traceId": "trace-20260405-0001",\n  "data": {"userId": 1001}\n}',
            replacement="traceId: <masked>",
        ),
        "日志关键字段定位": SampleCase(
            name="日志关键字段定位",
            pattern=r"ERROR\s+\[(?P<trace>[A-Z0-9-]+)\]\s+(.+)",
            text="2026-04-05 10:23:18 INFO [TRACE-1001] start request\n2026-04-05 10:23:19 ERROR [TRACE-1002] payment timeout\n2026-04-05 10:23:20 WARN [TRACE-1003] retry scheduled",
            replacement=r"ERROR [\g<trace>] <masked>",
        ),
        "URL 参数批量清洗": SampleCase(
            name="URL 参数批量清洗",
            pattern=r"([?&]token=)[^&]+",
            text="https://qa.example.com/order?id=1001&token=abc123\nhttps://qa.example.com/refund?id=1002&token=xyz999",
            replacement=r"\1***",
        ),
        "订单号规则归纳": SampleCase(
            name="订单号规则归纳",
            pattern=r"ORD-\d{6}",
            text="待处理订单: ORD-102401, ORD-102402, ORD-102499",
            replacement="ORDER-******",
        ),
    }


def _json_string_extractor(text: str, field: str) -> Optional[str]:
    return rf'"{re.escape(field)}"\s*:\s*"([^"]*)"'


def _json_generic_extractor(text: str, field: str) -> Optional[str]:
    return rf'"{re.escape(field)}"\s*:\s*([^,\}}\]\s]+)'


def _query_extractor(text: str, field: str) -> Optional[str]:
    return rf"(?:^|[?&]){re.escape(field)}=([^&\s]+)"


def _kv_extractor(text: str, field: str) -> Optional[str]:
    return rf"(?:^|[\s,;]){re.escape(field)}\s*[:=]\s*([^\s,;]+)"


def _default_field_extractors() -> Dict[str, FieldExtractor]:
    return {
        "json_string": FieldExtractor("json_string", _json_string_extractor, "JSON 字符串字段"),
        "json_generic": FieldExtractor("json_generic", _json_generic_extractor, "JSON 通用字段"),
        "query": FieldExtractor("query", _query_extractor, "Query / 表单参数"),
        "kv": FieldExtractor("kv", _kv_extractor, "日志或 KV 字段"),
    }


def _default_languages() -> Dict[str, CodeLanguageSpec]:
    escaped_delimited = escape_delimited_regex
    specs: Dict[str, CodeLanguageSpec] = {}
    style_by_name = {
        "JavaScript": ("suffix", False, "g"),
        "Python": ("named", False, ""),
        "PHP": ("suffix", False, ""),
        "Java": ("named", False, ""),
        "Go": ("inline", True, ""),
        "C#": ("named", False, ""),
        "Ruby": ("suffix", False, ""),
    }
    pattern_escaper_by_name = {
        "JavaScript": escaped_delimited,
        "Python": escape_python_literal,
        "PHP": escape_php_literal,
        "Java": escape_java_literal,
        "Go": escape_go_raw,
        "C#": escape_cs_verbatim,
        "Ruby": escaped_delimited,
    }
    replacement_escaper_by_name = {
        "JavaScript": escape_json_literal,
        "Python": escape_python_literal,
        "PHP": escape_php_literal,
        "Java": escape_java_literal,
        "Go": escape_double_quoted_inner,
        "C#": escape_cs_verbatim,
        "Ruby": escape_ruby_replacement,
    }
    for name, config in LANGUAGE_TEMPLATES.items():
        templates = dict(config)
        style, inline, global_flag = style_by_name.get(name, ("suffix", False, ""))
        specs[name] = CodeLanguageSpec(
            name=name,
            templates=templates,
            flags=dict(config["flags"]),
            escape_pattern=pattern_escaper_by_name.get(name, escape_delimited_regex),
            escape_replacement=replacement_escaper_by_name.get(name, escape_python_literal),
            flag_style=style,
            inline_flags=inline,
            global_flag=global_flag,
        )
    return specs


_PRESETS: Dict[str, PatternPreset] = _default_presets()
_SAMPLES: Dict[str, SampleCase] = _default_samples()
_EXTRACTORS: Dict[str, FieldExtractor] = _default_field_extractors()
_LANGUAGES: Dict[str, CodeLanguageSpec] = _default_languages()


# ---------------------------------------------------------------------------
# 注册 API
# ---------------------------------------------------------------------------

def register_pattern_preset(preset: PatternPreset, *, replace: bool = False) -> None:
    if not preset.name.strip() or not preset.pattern:
        raise ValueError("预定义模式需要 name 与 pattern")
    if preset.name in _PRESETS and not replace:
        raise ValueError(f"预定义模式已存在: {preset.name}")
    _PRESETS[preset.name] = preset


def register_sample_case(sample: SampleCase, *, replace: bool = False) -> None:
    if not sample.name.strip() or not sample.pattern:
        raise ValueError("QA 场景需要 name 与 pattern")
    if sample.name in _SAMPLES and not replace:
        raise ValueError(f"QA 场景已存在: {sample.name}")
    _SAMPLES[sample.name] = sample


def register_field_extractor(extractor: FieldExtractor, *, replace: bool = False) -> None:
    if not extractor.name.strip() or not callable(extractor.build):
        raise ValueError("字段提取规则需要 name 与可调用 build")
    if extractor.name in _EXTRACTORS and not replace:
        raise ValueError(f"字段提取规则已存在: {extractor.name}")
    _EXTRACTORS[extractor.name] = extractor


def register_code_language(spec: CodeLanguageSpec, *, replace: bool = False) -> None:
    if not spec.name.strip() or not callable(spec.escape_pattern) or not callable(spec.escape_replacement):
        raise ValueError("代码语言需要 name 与转义函数")
    if spec.name in _LANGUAGES and not replace:
        raise ValueError(f"代码语言已存在: {spec.name}")
    _LANGUAGES[spec.name] = spec


def get_pattern_presets() -> Dict[str, PatternPreset]:
    return dict(_PRESETS)


def get_sample_cases() -> Dict[str, SampleCase]:
    return dict(_SAMPLES)


def get_field_extractors() -> Dict[str, FieldExtractor]:
    return dict(_EXTRACTORS)


def get_code_languages() -> Dict[str, CodeLanguageSpec]:
    return dict(_LANGUAGES)


def get_code_language(name: str) -> CodeLanguageSpec:
    return _LANGUAGES[name]


def get_registry_summary() -> Dict[str, List[str]]:
    return {
        "presets": sorted(_PRESETS),
        "samples": sorted(_SAMPLES),
        "extractors": sorted(_EXTRACTORS),
        "languages": sorted(_LANGUAGES),
    }


def reset_regex_registry() -> None:
    """恢复默认扩展点（测试隔离用）。"""
    global _PRESETS, _SAMPLES, _EXTRACTORS, _LANGUAGES
    _PRESETS = _default_presets()
    _SAMPLES = _default_samples()
    _EXTRACTORS = _default_field_extractors()
    _LANGUAGES = _default_languages()


__all__ = [
    "PatternPreset", "SampleCase", "FieldExtractor", "CodeLanguageSpec",
    "register_pattern_preset", "register_sample_case", "register_field_extractor",
    "register_code_language", "get_pattern_presets", "get_sample_cases",
    "get_field_extractors", "get_code_languages", "get_code_language",
    "get_registry_summary", "reset_regex_registry",
    "escape_delimited_regex", "escape_python_literal", "escape_java_literal",
    "escape_cs_verbatim", "escape_php_literal", "escape_go_raw",
    "escape_ruby_replacement", "escape_double_quoted_inner", "escape_json_literal",
]
