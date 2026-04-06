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
            isolation: isolate;
            background:
                radial-gradient(circle at top right, rgba(250, 204, 21, 0.17), rgba(250, 204, 21, 0) 34%),
                linear-gradient(145deg, rgba(249, 250, 252, 0.99) 0%, rgba(240, 244, 251, 0.99) 52%, rgba(248, 241, 226, 0.99) 100%);
            border: 1px solid rgba(193, 204, 219, 0.96);
            border-radius: 22px;
            padding: 1.08rem 1.18rem 1.14rem;
            margin: 0.7rem 0 1.06rem 0;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.88),
                0 16px 32px rgba(15, 23, 42, 0.09);
        }
        .qa-guide-card::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 5px;
            pointer-events: none;
            background: linear-gradient(180deg, rgba(234, 88, 12, 0.74) 0%, rgba(250, 204, 21, 0.58) 100%);
        }
        .qa-guide-card::after {
            content: "";
            position: absolute;
            inset: 0;
            pointer-events: none;
            background: linear-gradient(135deg, rgba(255,255,255,0.20), rgba(255,255,255,0));
            z-index: -1;
        }
        .qa-guide-eyebrow {
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            padding: 0.22rem 0.56rem;
            border-radius: 999px;
            font-size: 0.76rem;
            font-weight: 700;
            letter-spacing: 0.04em;
            color: #9a3412;
            text-transform: uppercase;
            margin-bottom: 0.46rem;
            background: rgba(255, 247, 237, 0.92);
            border: 1px solid rgba(251, 191, 36, 0.24);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.82);
        }
        .qa-guide-title {
            font-size: 1.16rem;
            font-weight: 800;
            color: #10253a;
            margin-bottom: 0.4rem;
            letter-spacing: 0.01em;
        }
        .qa-guide-desc {
            color: #314b61;
            line-height: 1.72;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.92rem;
        }
        .qa-guide-steps {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 0.82rem;
        }
        .qa-guide-step {
            position: relative;
            background: linear-gradient(145deg, rgba(255,255,255,0.96) 0%, rgba(249,243,232,0.86) 100%);
            border: 1px solid rgba(210, 219, 231, 0.96);
            border-radius: 16px;
            padding: 0.8rem 0.9rem 0.86rem;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.84),
                0 8px 18px rgba(15, 23, 42, 0.05);
        }
        .qa-guide-step::before {
            content: "";
            position: absolute;
            inset: 0 auto auto 0;
            width: 100%;
            height: 3px;
            background: linear-gradient(90deg, rgba(37, 99, 235, 0.60) 0%, rgba(59, 130, 246, 0.18) 100%);
        }
        .qa-guide-step-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 30px;
            height: 30px;
            border-radius: 999px;
            background: linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
            color: #f8fafc;
            font-weight: 800;
            font-size: 0.88rem;
            margin-bottom: 0.52rem;
            border: 1px solid rgba(250, 204, 21, 0.24);
            box-shadow: 0 10px 16px rgba(7, 20, 39, 0.16);
        }
        .qa-guide-step-text {
            color: #17324a;
            line-height: 1.62;
            font-size: 0.93rem;
            font-weight: 600;
        }
        .qa-guide-tips {
            margin-top: 0.88rem;
        }
        .qa-guide-tip {
            display: inline-block;
            background: rgba(255,255,255,0.9);
            border: 1px solid rgba(251, 191, 36, 0.22);
            color: #28455d;
            border-radius: 999px;
            padding: 0.26rem 0.68rem;
            margin: 0 0.44rem 0.44rem 0;
            font-size: 0.81rem;
            font-weight: 600;
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.84),
                0 4px 10px rgba(15, 23, 42, 0.04);
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
    class_name: Optional[str] = None,
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
            f"<div class='qa-guide-card{' ' + html.escape(class_name) if class_name else ''}'>"
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
