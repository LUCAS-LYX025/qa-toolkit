from __future__ import annotations

import html

import streamlit as st


STATUS_META = {
    "success": {"icon": "✓", "title": "处理成功", "bg": "#ecfdf5", "border": "#10b981", "text": "#065f46"},
    "info": {"icon": "i", "title": "结果提示", "bg": "#eff6ff", "border": "#3b82f6", "text": "#1d4ed8"},
    "warning": {"icon": "!", "title": "请先确认", "bg": "#fffbeb", "border": "#f59e0b", "text": "#92400e"},
    "error": {"icon": "×", "title": "处理失败", "bg": "#fef2f2", "border": "#ef4444", "text": "#b91c1c"},
}


def _inject_styles() -> None:
    if st.session_state.get("_status_feedback_styles_ready"):
        return

    st.session_state["_status_feedback_styles_ready"] = True
    st.markdown(
        """
        <style>
        .qa-status-feedback {
            display: flex;
            gap: 12px;
            align-items: flex-start;
            border-radius: 16px;
            padding: 14px 16px;
            margin: 10px 0;
            border: 1px solid var(--feedback-border);
            background: var(--feedback-bg);
        }
        .qa-status-feedback__icon {
            width: 28px;
            height: 28px;
            border-radius: 999px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-size: 15px;
            font-weight: 700;
            color: #ffffff;
            background: var(--feedback-border);
            flex: 0 0 auto;
        }
        .qa-status-feedback__body {
            min-width: 0;
        }
        .qa-status-feedback__title {
            margin: 0 0 4px;
            font-size: 0.96rem;
            font-weight: 700;
            color: var(--feedback-text);
        }
        .qa-status-feedback__desc {
            margin: 0;
            color: #334155;
            line-height: 1.65;
            font-size: 0.92rem;
            white-space: pre-wrap;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_status_feedback(kind: str, description: str, title: str | None = None) -> None:
    _inject_styles()
    meta = STATUS_META.get(kind, STATUS_META["info"])
    safe_title = html.escape(title or meta["title"])
    safe_description = html.escape(str(description or "")).replace("\n", "<br/>")
    st.markdown(
        f"""
        <div class="qa-status-feedback"
             style="--feedback-bg: {meta['bg']}; --feedback-border: {meta['border']}; --feedback-text: {meta['text']};">
            <div class="qa-status-feedback__icon">{meta['icon']}</div>
            <div class="qa-status-feedback__body">
                <div class="qa-status-feedback__title">{safe_title}</div>
                <p class="qa-status-feedback__desc">{safe_description}</p>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def push_status_feedback(slot: str, kind: str, description: str, title: str | None = None) -> None:
    st.session_state[f"_status_feedback_flash_{slot}"] = {
        "kind": kind,
        "description": str(description or ""),
        "title": title,
    }


def render_flash_status_feedback(slot: str) -> None:
    payload = st.session_state.pop(f"_status_feedback_flash_{slot}", None)
    if not payload:
        return
    render_status_feedback(
        str(payload.get("kind", "info")),
        str(payload.get("description", "")),
        title=payload.get("title"),
    )


def render_success_feedback(description: str, title: str | None = None) -> None:
    render_status_feedback("success", description, title=title)


def render_info_feedback(description: str, title: str | None = None) -> None:
    render_status_feedback("info", description, title=title)


def render_warning_feedback(description: str, title: str | None = None) -> None:
    render_status_feedback("warning", description, title=title)


def render_error_feedback(description: str, title: str | None = None) -> None:
    render_status_feedback("error", description, title=title)
