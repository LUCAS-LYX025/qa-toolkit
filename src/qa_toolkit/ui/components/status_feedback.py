from __future__ import annotations

import html

import streamlit as st


STATUS_META = {
    "success": {
        "icon": "✓",
        "title": "处理成功",
        "bg": "linear-gradient(145deg, #fff7e6 0%, #faeecf 54%, #f7efe2 100%)",
        "border": "#f59e0b",
        "text": "#9a3412",
    },
    "info": {
        "icon": "i",
        "title": "结果提示",
        "bg": "linear-gradient(145deg, #eef4ff 0%, #e6edf7 58%, #f3f6fb 100%)",
        "border": "#224d79",
        "text": "#17324a",
    },
    "warning": {
        "icon": "!",
        "title": "请先确认",
        "bg": "linear-gradient(145deg, #fff8e5 0%, #fbefc8 56%, #f8f2df 100%)",
        "border": "#d97706",
        "text": "#92400e",
    },
    "error": {
        "icon": "×",
        "title": "处理失败",
        "bg": "linear-gradient(145deg, #fff1ee 0%, #fde6df 56%, #f8ece8 100%)",
        "border": "#dc2626",
        "text": "#991b1b",
    },
}


def _inject_styles() -> None:
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
            color: var(--feedback-text);
            line-height: 1.65;
            font-size: 0.92rem;
            font-weight: 600;
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
