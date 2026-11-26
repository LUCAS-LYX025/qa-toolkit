"""侧边栏语言切换器：手动选择优先，首访自动按 IP / 浏览器定位。"""

from __future__ import annotations

import streamlit as st
import streamlit.components.v1 as components

from qa_toolkit.core.i18n import DEFAULT_LOCALE, get_locales, normalize_locale, resolve_locale, t
from qa_toolkit.core.locale_detector import (
    build_browser_locale_bootstrap,
    build_locale_persistence_script,
)

LANG_QUERY_KEY = "lang"


def _query_locale() -> str | None:
    try:
        value = st.query_params.get(LANG_QUERY_KEY, "")
    except Exception:
        return None
    if isinstance(value, list):
        value = value[0] if value else ""
    return normalize_locale(value)


def _write_query_locale(locale: str) -> None:
    try:
        st.query_params[LANG_QUERY_KEY] = locale
    except Exception:
        # 某些嵌入环境禁止改写 URL，此时 session_state 仍然生效。
        pass


def _on_locale_change() -> None:
    code = normalize_locale(st.session_state.get("ui_locale_select"))
    if not code:
        return
    st.session_state["ui_locale"] = code
    _write_query_locale(code)


def render_locale_switcher() -> str:
    """渲染语言选择组件，返回当前生效的语言代码。"""
    explicit = _query_locale()
    if "ui_locale" not in st.session_state:
        st.session_state["ui_locale"] = resolve_locale(explicit=explicit)
    elif explicit and explicit != st.session_state.get("ui_locale"):
        st.session_state["ui_locale"] = explicit

    current = normalize_locale(st.session_state.get("ui_locale")) or DEFAULT_LOCALE
    locales = get_locales()
    codes = list(locales.keys())
    labels = {code: spec.label for code, spec in locales.items()}

    with st.sidebar:
        st.selectbox(
            t("界面语言"),
            codes,
            index=codes.index(current),
            format_func=lambda code: labels.get(code, code),
            key="ui_locale_select",
            on_change=_on_locale_change,
        )
        if explicit:
            st.caption(t("手动切换后，本次访问会以你的选择为准。"))
            components.html(build_locale_persistence_script(current), height=0)
        else:
            st.caption(t("自动定位（按 IP / 浏览器）"))
            components.html(build_browser_locale_bootstrap(DEFAULT_LOCALE), height=0)

    return current
