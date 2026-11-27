from __future__ import annotations

import html
import json

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


# 常见异常的「可操作提示」：把内部实现噪音翻译成用户能据以行动的描述。
# 只做保守匹配，未识别的异常回退到一行通用提示 + 原始消息，绝不显示空白。
_EXCEPTION_HINTS = (
    (json.JSONDecodeError, "输入不是合法 JSON，请检查括号、逗号与引号后重试。"),
    (ValueError, "输入内容不符合要求，请核对配置项后重试。"),
    (KeyError, "缺少必需的字段，请对照示例补齐后再执行。"),
    (TypeError, "参数类型不匹配，请检查输入格式。"),
    (FileNotFoundError, "找不到指定的文件，请确认路径或重新上传。"),
    (PermissionError, "没有访问权限，请检查文件或目录权限。"),
    (TimeoutError, "请求超时，请稍后重试或检查网络连接。"),
    (ConnectionError, "网络连接失败，请检查地址与网络后重试。"),
)


def format_exception_hint(exc: BaseException, action: str = "") -> str:
    """把异常转成「动作 + 可操作原因 + 原始消息」，避免在界面裸抛异常原文。

    ``action`` 是用户刚执行的动作（如“生成标准化清单”），用于给出上下文；
    原始异常消息保留在末尾，便于用户反馈问题时提供线索，但前面一定有
    一句能看懂、能照着改的提示。
    """
    message = str(exc).strip()
    hint = ""
    for exc_type, template in _EXCEPTION_HINTS:
        if isinstance(exc, exc_type):
            hint = template
            break
    if not hint:
        hint = "操作未能完成，请检查输入与配置后重试。"

    prefix = f"{action}失败。" if action else "操作失败。"
    if not message:
        return prefix + hint
    # 异常原文可能很长或含换行，压成单行，避免撑破提示卡片。
    detail = " ".join(message.split())
    return f"{prefix}{hint}（{type(exc).__name__}: {detail}）"


def render_action_error(action: str, exc: BaseException) -> None:
    """渲染带上下文与可操作建议的错误提示。"""
    render_error_feedback(format_exception_hint(exc, action))
