"""字数统计工具的可注册扩展点。

把字符分类规则、分词策略、停用词、阅读速度等统计口径做成扩展点，
新增业务维度或新的语言支持只需 register，不必改动 text_analysis.py 的核心扫描逻辑。

设计约束：
- 默认注册表必须与历史行为兼容（默认值即旧常量），保证零回归；
- 提供 reset_text_analysis_registry() 便于测试隔离；
- 每个扩展点都带稳定 name，导出 payload 可记录使用了哪些规则。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


CharacterPredicate = Callable[[str], bool]
Tokenizer = Callable[[str], List[str]]


@dataclass(frozen=True)
class CharacterClass:
    """一个字符分类规则：按 name 有序参与统计，predicate 判定字符是否归属。"""

    name: str
    predicate: CharacterPredicate
    description: str = ""


@dataclass(frozen=True)
class TokenizerSpec:
    name: str
    tokenize: Tokenizer
    description: str = ""


def _is_cjk_ideograph(char: str) -> bool:
    """覆盖 CJK 基本区、扩展 A-G 与兼容表意文字（含 surrogate pair 拆出的单码点）。"""
    code = ord(char)
    ranges = (
        (0x3400, 0x4DBF),    # 扩展 A
        (0x4E00, 0x9FFF),    # 基本区
        (0xF900, 0xFAFF),    # 兼容表意文字
        (0x20000, 0x2A6DF),  # 扩展 B
        (0x2A700, 0x2EBEF),  # 扩展 C-D-E-F
        (0x2F800, 0x2FA1F),  # 兼容扩展
        (0x30000, 0x323AF),  # 扩展 G/H
    )
    return any(start <= code <= end for start, end in ranges)


def _is_emoji(char: str) -> bool:
    code = ord(char)
    return (
        0x1F000 <= code <= 0x1FAFF
        or 0x2600 <= code <= 0x27BF
        or code in (0xFE0F, 0xFE0E, 0x200D, 0x20E3)
        or 0x1F1E6 <= code <= 0x1F1FF  # 国旗区域指示符
    )


def _is_space_char(char: str) -> bool:
    """所有可见空白：ASCII 空格、全角空格、NBSP 等，但不含 \t/\n 等控制空白。"""
    return char.isspace() and char not in ("\t", "\n", "\r", "\v", "\f", "\x85", "\u2028", "\u2029")


def _is_punctuation(char: str) -> bool:
    import unicodedata
    return unicodedata.category(char).startswith("P") and not _is_emoji(char)


def _default_character_classes() -> List[CharacterClass]:
    return [
        CharacterClass("cjk_chars", _is_cjk_ideograph, "中日韩表意文字（含扩展区）"),
        CharacterClass("latin_letters", lambda c: c.isalpha() and not _is_cjk_ideograph(c) and not _is_emoji(c), "非中日韩字母"),
        CharacterClass("digits", lambda c: c.isdigit(), "数字"),
        CharacterClass("punctuation", _is_punctuation, "标点符号"),
        CharacterClass("emoji", _is_emoji, "Emoji 及组合控制符"),
        CharacterClass("spaces", _is_space_char, "可见空白字符（含全角空格/NBSP）"),
        CharacterClass("newlines", lambda c: c in ("\n", "\r"), "换行"),
        CharacterClass("tabs", lambda c: c == "\t", "制表符"),
        CharacterClass("invisible", lambda c: ord(c) in (0x200B, 0x200C, 0x200D, 0xFEFF, 0x2060, 0x00AD), "零宽/不可见字符"),
    ]


_WORD_RE = None  # 延迟编译，避免在导入期重复


def _latin_word_tokenizer(text: str) -> List[str]:
    """Unicode 感知的拉丁词提取：保留重音字母，不再从非 ASCII 处截断。"""
    import re
    global _WORD_RE
    if _WORD_RE is None:
        # \w 覆盖 Unicode 字母/数字/下划线；排除中日韩表意文字与 emoji。
        _WORD_RE = re.compile(
            r"[^\W_]+(?:['’_\-][^\W_]+)*",
            flags=re.UNICODE,
        )
    tokens: List[str] = []
    for match in _WORD_RE.finditer(text):
        token = match.group()
        if any(_is_cjk_ideograph(c) or _is_emoji(c) for c in token):
            # 逐段切出纯拉丁片段，避免把 "café中文" 当成一个词。
            buffer = []
            for c in token:
                if not (_is_cjk_ideograph(c) or _is_emoji(c)):
                    buffer.append(c)
                elif buffer:
                    tokens.append("".join(buffer))
                    buffer = []
            if buffer:
                tokens.append("".join(buffer))
        else:
            tokens.append(token)
    return [t for t in tokens if t]


def _cjk_bigram_tokenizer(text: str) -> List[str]:
    """中文按连续汉字块切分（默认口径），可被用户注册的jieba等分词器替换。"""
    import re
    tokens: List[str] = []
    for match in re.finditer(r"[\u3400-\u9fff\uf900-\ufaff]+", text):
        block = match.group()
        if len(block) >= 2:
            tokens.append(block)
    return tokens


def _default_tokenizers() -> Dict[str, TokenizerSpec]:
    return {
        "latin": TokenizerSpec("latin", _latin_word_tokenizer, "Unicode 拉丁词（支持重音）"),
        "cjk_block": TokenizerSpec("cjk_block", _cjk_bigram_tokenizer, "中文连续汉字块"),
    }


DEFAULT_STOPWORDS: Set[str] = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from",
    "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "with",
    # 中文虚词（默认补充，解决 Top10 被虚词占据）
    "的", "了", "和", "是", "在", "我", "我们", "你", "你们", "他", "他们",
    "这", "这个", "那", "那个", "有", "也", "就", "都", "而", "及", "与",
}


# ---------------------------- 可变注册表状态 ----------------------------

_CHARACTER_CLASSES: List[CharacterClass] = _default_character_classes()
_TOKENIZERS: Dict[str, TokenizerSpec] = _default_tokenizers()
_STOPWORDS: Set[str] = set(DEFAULT_STOPWORDS)
_SETTINGS: Dict[str, Any] = {
    "reading_speed_per_minute": 220,
    "long_line_threshold": 40,
    "min_keyword_length": 2,
    "unicode_normalization": "NFC",
}


def register_character_class(
    name: str,
    predicate: CharacterPredicate,
    *,
    description: str = "",
    replace: bool = False,
    priority: bool = False,
) -> None:
    """注册或替换一个字符分类规则。

    replace=True 替换同名规则；priority=True 时插入最前，使自定义规则先于内置规则匹配
    （例如想把 `#` 单列为"标签符"而非通用标点）。
    """
    spec = CharacterClass(name, predicate, description)
    if replace:
        for index, existing in enumerate(_CHARACTER_CLASSES):
            if existing.name == name:
                _CHARACTER_CLASSES[index] = spec
                return
        raise KeyError(f"未注册的字符分类: {name}")
    if any(existing.name == name for existing in _CHARACTER_CLASSES):
        raise ValueError(f"字符分类已存在: {name}")
    if priority:
        _CHARACTER_CLASSES.insert(0, spec)
    else:
        _CHARACTER_CLASSES.append(spec)


def character_classes() -> List[CharacterClass]:
    return list(_CHARACTER_CLASSES)


def register_tokenizer(name: str, tokenize: Tokenizer, *, description: str = "", replace: bool = False) -> None:
    if not replace and name in _TOKENIZERS:
        raise ValueError(f"分词器已存在: {name}")
    _TOKENIZERS[name] = TokenizerSpec(name, tokenize, description)


def get_tokenizer(name: str) -> Tokenizer:
    if name not in _TOKENIZERS:
        raise KeyError(f"未注册的分词器: {name}")
    return _TOKENIZERS[name].tokenize


def tokenizer_names() -> List[str]:
    return list(_TOKENIZERS)


def configure_stopwords(words: Optional[Set[str] | List[str] | Tuple[str, ...]], *, append: bool = False) -> None:
    """设置停用词。append=True 时在现有词表上追加。"""
    global _STOPWORDS
    normalized = {str(w).lower() for w in (words or []) if str(w).strip()}
    if append:
        _STOPWORDS |= normalized
    else:
        _STOPWORDS = normalized


def stopwords() -> Set[str]:
    return set(_STOPWORDS)


def configure_settings(**kwargs: Any) -> None:
    """更新统计配置：reading_speed_per_minute / long_line_threshold / min_keyword_length / unicode_normalization。"""
    for key, value in kwargs.items():
        if key not in _SETTINGS:
            raise KeyError(f"未知配置项: {key}")
        if value is None:
            continue
        if key in ("reading_speed_per_minute", "long_line_threshold", "min_keyword_length") and (not isinstance(value, (int, float)) or value <= 0):
            raise ValueError(f"{key} 必须为正数")
        if key == "unicode_normalization" and value not in ("NFC", "NFD", "NFKC", "NFKD", "none"):
            raise ValueError("unicode_normalization 必须是 NFC/NFD/NFKC/NFKD/none")
        _SETTINGS[key] = value


def settings() -> Dict[str, Any]:
    return dict(_SETTINGS)


def reset_text_analysis_registry() -> None:
    """恢复到默认扩展点，供测试隔离使用。"""
    global _CHARACTER_CLASSES, _TOKENIZERS, _STOPWORDS, _SETTINGS
    _CHARACTER_CLASSES = _default_character_classes()
    _TOKENIZERS = _default_tokenizers()
    _STOPWORDS = set(DEFAULT_STOPWORDS)
    _SETTINGS = {
        "reading_speed_per_minute": 220,
        "long_line_threshold": 40,
        "min_keyword_length": 2,
        "unicode_normalization": "NFC",
    }
