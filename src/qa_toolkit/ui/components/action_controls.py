from __future__ import annotations

from typing import Any

import streamlit as st


def action_button(
    label: str,
    *,
    key: str,
    kind: str = "secondary",
    use_container_width: bool = True,
    **kwargs: Any,
) -> bool:
    params = {
        "label": label,
        "key": key,
        "use_container_width": use_container_width,
        **kwargs,
    }
    try:
        return st.button(type=kind, **params)
    except TypeError:
        return st.button(**params)


def primary_action_button(label: str, *, key: str, **kwargs: Any) -> bool:
    return action_button(label, key=key, kind="primary", **kwargs)


def secondary_action_button(label: str, *, key: str, **kwargs: Any) -> bool:
    return action_button(label, key=key, kind="secondary", **kwargs)


def action_download_button(
    label: str,
    *,
    kind: str = "secondary",
    use_container_width: bool = True,
    **kwargs: Any,
) -> None:
    params = {
        "label": label,
        "use_container_width": use_container_width,
        **kwargs,
    }
    try:
        st.download_button(type=kind, **params)
    except TypeError:
        st.download_button(**params)
