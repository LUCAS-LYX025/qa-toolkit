"""界面国际化核心：语言注册、翻译目录与原文回退。

设计原则：
1. 简体中文原文即翻译键，未翻译的文案自动回退原文，新增页面无需先补齐四语言。
2. 语言目录可注册扩展，方便外部插件按同一机制补充文案。
3. 本模块不依赖 Streamlit，纯函数可在脚本、测试和服务端复用。
"""

from __future__ import annotations

import html
import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Mapping, Optional

DEFAULT_LOCALE = "zh-CN"
LOCALE_ENV_VAR = "QA_TOOLKIT_LOCALE"
_LOCALE_DIR = Path(__file__).resolve().parents[1] / "config" / "locales"
_LOCK = threading.RLock()


@dataclass(frozen=True)
class LocaleSpec:
    """一个可切换的界面语言。"""

    code: str
    label: str
    english_label: str
    fallback: Optional[str] = DEFAULT_LOCALE
    aliases: tuple = ()


_LOCALES: Dict[str, LocaleSpec] = {}
_CATALOGS: Dict[str, Dict[str, str]] = {}
_TOOL_DOCS: Dict[str, Dict[str, Dict[str, str]]] = {}


def register_locale(spec: LocaleSpec, replace: bool = False) -> None:
    """注册界面语言；默认拒绝静默覆盖内置语言。"""
    with _LOCK:
        if spec.code in _LOCALES and not replace:
            raise ValueError(f"locale already registered: {spec.code}")
        _LOCALES[spec.code] = spec


def get_locales() -> Dict[str, LocaleSpec]:
    """返回语言注册表的副本。"""
    with _LOCK:
        return dict(_LOCALES)


def get_locale_spec(code: str) -> Optional[LocaleSpec]:
    with _LOCK:
        return _LOCALES.get(code)


def normalize_locale(value: object) -> Optional[str]:
    """把常见语言标记归一到已注册语言；未知值返回 None。"""
    if not value:
        return None
    text = str(value).strip().replace("_", "-")
    if not text:
        return None
    with _LOCK:
        specs = dict(_LOCALES)
    lowered = text.lower()
    for code, spec in specs.items():
        candidates = {code.lower(), *{alias.lower() for alias in spec.aliases}}
        if lowered in candidates:
            return code
        # zh-Hant / zh-Hans 等主子标签写法
        if lowered.startswith(code.lower() + "-"):
            return code
    return None


def register_translations(locale: str, translations: Mapping[str, str], replace: bool = False) -> None:
    """向指定语言注册翻译，重复键默认拒绝覆盖。"""
    code = normalize_locale(locale)
    if code is None:
        raise ValueError(f"unsupported locale: {locale}")
    with _LOCK:
        catalog = _CATALOGS.setdefault(code, {})
        for source, target in translations.items():
            if not isinstance(source, str) or not isinstance(target, str):
                raise ValueError("translation keys and values must be strings")
            if source in catalog and not replace:
                raise ValueError(f"translation already registered: {code}:{source}")
            catalog[source] = target


def get_catalog(locale: str) -> Dict[str, str]:
    with _LOCK:
        return dict(_CATALOGS.get(locale, {}))


def register_tool_doc(
    locale: str,
    tool_name: str,
    *,
    title: str,
    usage: str,
    notes: str,
    replace: bool = False,
) -> None:
    """注册整篇工具文档的译文，供 documentation 组件按当前语言读取。"""
    code = normalize_locale(locale)
    if code is None:
        raise ValueError(f"unsupported locale: {locale}")
    with _LOCK:
        docs = _TOOL_DOCS.setdefault(code, {})
        if tool_name in docs and not replace:
            raise ValueError(f"tool doc already registered: {code}:{tool_name}")
        docs[tool_name] = {"title": title, "usage": usage, "notes": notes}


def get_tool_doc(tool_name: str, locale: Optional[str] = None) -> Optional[Dict[str, str]]:
    code = normalize_locale(locale) if locale is not None else _runtime_locale()
    with _LOCK:
        docs = _TOOL_DOCS.get(code or DEFAULT_LOCALE, {})
        doc = docs.get(tool_name)
        return dict(doc) if doc else None


def _load_builtin_catalogs() -> None:
    for locale in (DEFAULT_LOCALE, "zh-TW", "en-US", "ko-KR"):
        path = _LOCALE_DIR / f"{locale}.json"
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        if not isinstance(data, dict):
            raise ValueError(f"invalid locale catalog: {path}")
        with _LOCK:
            messages = data.get("messages", data) if "messages" in data else data
            if not isinstance(messages, dict):
                raise ValueError(f"invalid messages in locale catalog: {path}")
            _CATALOGS.setdefault(locale, {}).update(messages)
            for tool_name, doc in (data.get("tool_docs") or {}).items():
                _TOOL_DOCS.setdefault(locale, {})[tool_name] = dict(doc)


def _runtime_locale() -> str:
    """读取运行时语言，供未显式传 locale 的调用点使用。"""
    try:
        import streamlit as st

        value = st.session_state.get("ui_locale")
        resolved = normalize_locale(value)
        if resolved:
            return resolved
    except Exception:
        # 非 Streamlit 上下文（脚本 / 单测）中 session_state 不可用。
        pass
    return normalize_locale(os.environ.get(LOCALE_ENV_VAR)) or DEFAULT_LOCALE


def current_locale() -> str:
    """返回当前运行时语言（供 HTML lang 等元信息使用）。"""
    return _runtime_locale()


def t(source: str, *, locale: Optional[str] = None, **kwargs: object) -> str:
    """翻译文案；未命中时回退到原文（简体中文）。

    支持 ``str.format`` 命名占位符，例如 ``t("切换到{name}", name=...)``。
    """
    if not isinstance(source, str):
        return str(source)
    code = normalize_locale(locale) if locale is not None else _runtime_locale()
    code = code or DEFAULT_LOCALE

    with _LOCK:
        catalog = dict(_CATALOGS.get(code, {}))
        fallback = get_locale_spec(code)
        fallback_code = fallback.fallback if fallback else None
        fallback_catalog = dict(_CATALOGS.get(fallback_code, {})) if fallback_code else {}

    text = catalog.get(source, fallback_catalog.get(source, source))
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, IndexError, ValueError):
            return text
    return text


def th(source: str, *, locale: Optional[str] = None, **kwargs: object) -> str:
    """翻译并做 HTML 转义，供 unsafe_allow_html 的模板使用。"""
    return html.escape(t(source, locale=locale, **kwargs), quote=True)


def resolve_locale(
    explicit: object = None,
    *,
    persisted: object = None,
    detected: object = None,
) -> str:
    """统一优先级：手动选择 > 本地保存偏好 > IP/浏览器检测 > 默认语言。

    ``explicit`` 通常来自 URL 查询参数，用户在界面切换语言时直接写入它，
    因此天然拥有最高优先级。
    """
    for candidate in (explicit, persisted, detected):
        resolved = normalize_locale(candidate)
        if resolved:
            return resolved
    return DEFAULT_LOCALE


register_locale(LocaleSpec(DEFAULT_LOCALE, "简体中文", "Simplified Chinese", None,
                           ("zh", "zh-CN", "zh-Hans", "cn")))
register_locale(LocaleSpec("zh-TW", "繁體中文", "Traditional Chinese", DEFAULT_LOCALE,
                           ("zh-TW", "zh-Hant", "zh-HK", "zh-MO", "hk", "tw")))
register_locale(LocaleSpec("en-US", "English", "English", DEFAULT_LOCALE,
                           ("en", "en-US", "en-GB", "us", "uk", "gb")))
register_locale(LocaleSpec("ko-KR", "한국어", "Korean", DEFAULT_LOCALE,
                           ("ko", "ko-KR", "kr")))
_load_builtin_catalogs()
