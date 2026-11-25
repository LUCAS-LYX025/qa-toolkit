"""文本对比工具的可注册扩展点。

新增规范化规则、分词器、序列匹配算法或导出格式时，只需在启动时调用对应
register_*，不需要修改 text_comparison.py / text_comparison_page.py 的 if/elif。
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Sequence

MAX_EXACT_MATCH_ITEMS = 5000

DEFAULT_TOKEN_RE = re.compile(
    r"[\u4e00-\u9fff]|[A-Za-z0-9]+(?:['’_-][A-Za-z0-9]+)*|[^\w\s]|\s+"
)
_PUNCTUATION_RE = re.compile(r"[^\w\s]", re.UNICODE)
_ALL_WHITESPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class NormalizerRule:
    name: str
    apply: Callable[[List[str]], List[str]]
    description: str = ""


@dataclass(frozen=True)
class TokenizerSpec:
    name: str
    tokenize: Callable[[str], List[str]]
    description: str = ""


@dataclass(frozen=True)
class MatcherSpec:
    name: str
    build: Callable[[Sequence[Any], Sequence[Any]], Any]
    description: str = ""


@dataclass(frozen=True)
class ExporterSpec:
    name: str
    filename: str
    mime: str
    render: Callable[[Dict[str, Any], Dict[str, Any]], Any]
    description: str = ""


def _ignore_punctuation(lines: List[str]) -> List[str]:
    return [_PUNCTUATION_RE.sub("", line) for line in lines]


def _ignore_all_whitespace(lines: List[str]) -> List[str]:
    return [_ALL_WHITESPACE_RE.sub("", line) for line in lines]


def _default_tokenize(text: str) -> List[str]:
    # 中文按单字切分：连续汉字整体作为一个 token 会让任意词序/插入都变成整块替换。
    return DEFAULT_TOKEN_RE.findall(text)


def _build_difflib_matcher(left: Sequence[Any], right: Sequence[Any]) -> Any:
    # autojunk 会把高频重复项从匹配中剔除，在日志/CSV 场景会误报成百上千行修改。
    # 大序列保留 autojunk 作为性能降级，调用方会拿到 matching_mode 提示。
    autojunk = max(len(left), len(right)) > MAX_EXACT_MATCH_ITEMS
    return difflib.SequenceMatcher(None, left, right, autojunk=autojunk)


def _default_normalizers() -> Dict[str, NormalizerRule]:
    return {
        "ignore_punctuation": NormalizerRule(
            "ignore_punctuation", _ignore_punctuation, "忽略标点符号差异"
        ),
        "ignore_all_whitespace": NormalizerRule(
            "ignore_all_whitespace", _ignore_all_whitespace, "忽略所有空白字符"
        ),
    }


def _default_tokenizers() -> Dict[str, TokenizerSpec]:
    return {
        "default": TokenizerSpec("default", _default_tokenize, "中文单字 + 英文单词")
    }


def _default_matchers() -> Dict[str, MatcherSpec]:
    return {
        "difflib": MatcherSpec("difflib", _build_difflib_matcher, "difflib 序列匹配（关闭 autojunk）")
    }


def _default_exporters() -> Dict[str, ExporterSpec]:
    from qa_toolkit.utils.text_comparison import default_exporters

    return default_exporters()


_NORMALIZERS: Dict[str, NormalizerRule] = _default_normalizers()
_TOKENIZERS: Dict[str, TokenizerSpec] = _default_tokenizers()
_MATCHERS: Dict[str, MatcherSpec] = _default_matchers()
# 延迟填充：默认导出器需要 text_comparison 的函数，模块加载期导入会形成循环。
_EXPORTERS: Dict[str, ExporterSpec] = {}


def _ensure_default_exporters() -> None:
    if not _EXPORTERS:
        _EXPORTERS.update(_default_exporters())


def reset_text_comparison_registry() -> None:
    """恢复默认注册项，供测试隔离使用。"""
    global _NORMALIZERS, _TOKENIZERS, _MATCHERS, _EXPORTERS
    _NORMALIZERS = _default_normalizers()
    _TOKENIZERS = _default_tokenizers()
    _MATCHERS = _default_matchers()
    _EXPORTERS = _default_exporters()


def register_normalizer(name: str, apply: Callable[[List[str]], List[str]], description: str = "") -> None:
    _NORMALIZERS[name] = NormalizerRule(name, apply, description)


def register_tokenizer(name: str, tokenize: Callable[[str], List[str]], description: str = "") -> None:
    _TOKENIZERS[name] = TokenizerSpec(name, tokenize, description)


def register_matcher(
    name: str,
    build: Callable[[Sequence[Any], Sequence[Any]], Any],
    description: str = "",
) -> None:
    _MATCHERS[name] = MatcherSpec(name, build, description)


def register_exporter(
    name: str,
    filename: str,
    mime: str,
    render: Callable[[Dict[str, Any], Dict[str, Any]], Any],
    description: str = "",
) -> None:
    _ensure_default_exporters()
    _EXPORTERS[name] = ExporterSpec(name, filename, mime, render, description)


def normalizers() -> Dict[str, NormalizerRule]:
    return dict(_NORMALIZERS)


def tokenizers() -> Dict[str, TokenizerSpec]:
    return dict(_TOKENIZERS)


def matchers() -> Dict[str, MatcherSpec]:
    return dict(_MATCHERS)


def exporters() -> Dict[str, ExporterSpec]:
    _ensure_default_exporters()
    return dict(_EXPORTERS)


def get_normalizer(name: str) -> NormalizerRule:
    if name not in _NORMALIZERS:
        raise KeyError(f"未注册的规范化规则: {name}")
    return _NORMALIZERS[name]


def get_tokenizer(name: str) -> TokenizerSpec:
    if name not in _TOKENIZERS:
        raise KeyError(f"未注册的分词器: {name}")
    return _TOKENIZERS[name]


def get_matcher(name: str) -> MatcherSpec:
    if name not in _MATCHERS:
        raise KeyError(f"未注册的匹配算法: {name}")
    return _MATCHERS[name]


def get_exporter(name: str) -> ExporterSpec:
    _ensure_default_exporters()
    if name not in _EXPORTERS:
        raise KeyError(f"未注册的导出格式: {name}")
    return _EXPORTERS[name]
