"""Helpers for safely updating Streamlit widget-backed session_state keys.

Streamlit raises ``StreamlitAPIException`` when a widget's ``key`` is assigned
after that widget has been instantiated in the current run.  Button callbacks
passed via ``on_click`` run *before* widgets are re-instantiated on the next
rerun, so assigning keys there is always safe.

This module centralises that pattern so pages do not each reinvent it.
"""

from __future__ import annotations

from typing import Any, Callable, Dict

import streamlit as st


def set_widget_value(key: str, value: Any) -> None:
    """Assign a widget-backed key. Safe when called from an ``on_click`` callback."""
    st.session_state[key] = value


def make_setter(key: str, value: Any) -> Callable[[], None]:
    """Return a zero-arg callback suitable for ``st.button(on_click=...)``."""
    def _setter() -> None:
        st.session_state[key] = value
    return _setter


def set_many(values: Dict[str, Any]) -> None:
    """Assign several widget-backed keys from an ``on_click`` callback."""
    for key, value in values.items():
        st.session_state[key] = value


def make_multi_setter(values: Dict[str, Any]) -> Callable[[], None]:
    def _setter() -> None:
        for key, value in values.items():
            st.session_state[key] = value
    return _setter


def queue_widget_updates(namespace: str, values: Dict[str, Any]) -> None:
    """Queue widget key updates to be applied at the start of the next rerun.

    Use this when the update depends on values computed *after* widgets have
    been instantiated (e.g. a save action that calls an external manager).
    Call :func:`pop_widget_updates` at the top of the page/component, before
    any widget is created.
    """
    key = f"_pending_widget_updates_{namespace}"
    pending = dict(st.session_state.get(key) or {})
    pending.update(values)
    st.session_state[key] = pending


def pop_widget_updates(namespace: str) -> None:
    """Apply and clear updates queued by :func:`queue_widget_updates`."""
    key = f"_pending_widget_updates_{namespace}"
    pending = st.session_state.pop(key, None)
    if not pending:
        return
    for widget_key, value in pending.items():
        st.session_state[widget_key] = value
