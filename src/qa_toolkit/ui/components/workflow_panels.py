import html
from typing import Any, Dict, List, Optional, Sequence

import streamlit as st


_STYLE_FLAG = "_qa_toolkit_workflow_panels_style_loaded"


def ensure_workflow_panel_styles() -> None:
    """注入统一的页面引导和导出区样式。"""
    if st.session_state.get(_STYLE_FLAG):
        return

    st.markdown(
        """
        <style>
        .qa-guide-card {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(circle at top right, rgba(250, 204, 21, 0.12), rgba(250, 204, 21, 0) 34%),
                linear-gradient(145deg, rgba(247,249,253,0.98) 0%, rgba(238,243,250,0.98) 56%, rgba(247,239,223,0.98) 100%);
            border: 1px solid #d5dce8;
            border-radius: 20px;
            padding: 1rem 1.1rem;
            margin: 0.6rem 0 1rem 0;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.88),
                0 14px 28px rgba(15, 23, 42, 0.08);
        }
        .qa-guide-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-top: 3px solid rgba(250, 204, 21, 0.24);
        }
        .qa-guide-eyebrow {
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: #b45309;
            text-transform: uppercase;
            margin-bottom: 0.35rem;
        }
        .qa-guide-title {
            font-size: 1.08rem;
            font-weight: 700;
            color: #17324a;
            margin-bottom: 0.35rem;
        }
        .qa-guide-desc {
            color: #476179;
            line-height: 1.65;
            margin-bottom: 0.8rem;
        }
        .qa-guide-steps {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.75rem;
        }
        .qa-guide-step {
            background: linear-gradient(145deg, rgba(255,255,255,0.92) 0%, rgba(247,239,223,0.76) 100%);
            border: 1px solid rgba(213, 220, 232, 0.92);
            border-radius: 14px;
            padding: 0.75rem 0.85rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.82);
        }
        .qa-guide-step-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 28px;
            height: 28px;
            border-radius: 999px;
            background: linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
            color: #f8fafc;
            font-weight: 700;
            font-size: 0.86rem;
            margin-bottom: 0.45rem;
            border: 1px solid rgba(250, 204, 21, 0.20);
            box-shadow: 0 8px 14px rgba(7, 20, 39, 0.14);
        }
        .qa-guide-step-text {
            color: #17324a;
            line-height: 1.55;
            font-size: 0.92rem;
        }
        .qa-guide-tips {
            margin-top: 0.8rem;
        }
        .qa-guide-tip {
            display: inline-block;
            background: rgba(255,255,255,0.84);
            border: 1px solid rgba(250, 204, 21, 0.18);
            color: #36506a;
            border-radius: 999px;
            padding: 0.22rem 0.62rem;
            margin: 0 0.42rem 0.42rem 0;
            font-size: 0.8rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.84);
        }
        .qa-export-card {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(circle at top right, rgba(250, 204, 21, 0.14), rgba(250, 204, 21, 0) 34%),
                linear-gradient(145deg, rgba(247,249,253,0.98) 0%, rgba(238,243,250,0.98) 56%, rgba(247,239,223,0.98) 100%);
            border: 1px solid rgba(199, 164, 79, 0.42);
            border-radius: 20px;
            padding: 1rem 1.1rem;
            margin: 0.8rem 0;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.88),
                0 14px 28px rgba(15, 23, 42, 0.08);
        }
        .qa-export-card::before {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            border-left: 4px solid rgba(234, 88, 12, 0.64);
        }
        .qa-export-title {
            font-size: 1.02rem;
            font-weight: 700;
            color: #17324a;
            margin-bottom: 0.22rem;
        }
        .qa-export-desc {
            color: #476179;
            line-height: 1.6;
            font-size: 0.92rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    st.session_state[_STYLE_FLAG] = True


def render_workflow_guide(
    title: str,
    description: str,
    steps: Sequence[str],
    tips: Optional[Sequence[str]] = None,
    eyebrow: str = "操作向导",
) -> None:
    """渲染统一的页面引导区。"""
    ensure_workflow_panel_styles()

    step_cards = []
    for index, step in enumerate(steps, start=1):
        step_cards.append(
            "<div class='qa-guide-step'>"
            f"<div class='qa-guide-step-index'>{index}</div>"
            f"<div class='qa-guide-step-text'>{html.escape(step)}</div>"
            "</div>"
        )

    tip_html = ""
    if tips:
        tip_html = "<div class='qa-guide-tips'>" + "".join(
            f"<span class='qa-guide-tip'>{html.escape(str(tip))}</span>" for tip in tips
        ) + "</div>"

    st.markdown(
        (
            "<div class='qa-guide-card'>"
            f"<div class='qa-guide-eyebrow'>{html.escape(eyebrow)}</div>"
            f"<div class='qa-guide-title'>{html.escape(title)}</div>"
            f"<div class='qa-guide-desc'>{html.escape(description)}</div>"
            f"<div class='qa-guide-steps'>{''.join(step_cards)}</div>"
            f"{tip_html}"
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_download_panel(
    title: str,
    description: str,
    items: Sequence[Dict[str, Any]],
    key_prefix: str,
    metrics: Optional[Sequence[Dict[str, Any]]] = None,
    empty_message: str = "当前没有可导出的结果。",
) -> None:
    """渲染统一的下载导出区。"""
    ensure_workflow_panel_styles()

    st.markdown(
        (
            "<div class='qa-export-card'>"
            f"<div class='qa-export-title'>{html.escape(title)}</div>"
            f"<div class='qa-export-desc'>{html.escape(description)}</div>"
            "</div>"
        ),
        unsafe_allow_html=True,
    )

    if metrics:
        metric_cols = st.columns(len(metrics))
        for col, metric in zip(metric_cols, metrics):
            with col:
                col.metric(str(metric.get("label", "")), str(metric.get("value", "")))

    valid_items: List[Dict[str, Any]] = [item for item in items if item.get("data") is not None]
    if not valid_items:
        st.info(empty_message)
        return

    column_count = min(3, len(valid_items))
    for row_start in range(0, len(valid_items), column_count):
        row_items = valid_items[row_start:row_start + column_count]
        cols = st.columns(len(row_items))
        for idx, (col, item) in enumerate(zip(cols, row_items), start=row_start):
            with col:
                st.download_button(
                    label=str(item.get("label", "下载文件")),
                    data=item.get("data"),
                    file_name=str(item.get("file_name", "download.bin")),
                    mime=str(item.get("mime", "application/octet-stream")),
                    use_container_width=True,
                    key=f"{key_prefix}_{item.get('key', idx)}",
                )
                caption = str(item.get("caption", "") or "").strip()
                if caption:
                    st.caption(caption)
