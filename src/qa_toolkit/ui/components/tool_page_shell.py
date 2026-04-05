from __future__ import annotations

from typing import Iterable

import streamlit as st


def _inject_styles() -> None:
    if st.session_state.get("_tool_page_shell_styles_ready"):
        return

    st.session_state["_tool_page_shell_styles_ready"] = True
    st.markdown(
        """
        <style>
        .qa-tool-shell-hero {
            position: relative;
            overflow: hidden;
            border-radius: 22px;
            padding: 24px 24px 18px;
            margin: 10px 0 18px;
            background:
                radial-gradient(circle at top right, rgba(255,255,255,0.22), transparent 36%),
                linear-gradient(135deg, var(--hero-accent) 0%, #0f172a 100%);
            color: #f8fafc;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.14);
        }
        .qa-tool-shell-hero h3 {
            margin: 0 0 8px;
            font-size: 1.6rem;
            font-weight: 700;
            color: #ffffff;
        }
        .qa-tool-shell-hero p {
            margin: 0;
            font-size: 0.96rem;
            line-height: 1.65;
            color: rgba(248, 250, 252, 0.92);
            max-width: 900px;
        }
        .qa-tool-shell-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 16px;
        }
        .qa-tool-shell-tag {
            padding: 6px 10px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 600;
            background: rgba(255, 255, 255, 0.14);
            border: 1px solid rgba(255, 255, 255, 0.22);
            color: #ffffff;
        }
        .qa-tool-shell-empty {
            border: 1px dashed rgba(100, 116, 139, 0.45);
            border-radius: 18px;
            padding: 20px 18px;
            margin: 14px 0;
            background: linear-gradient(180deg, rgba(248, 250, 252, 0.9), rgba(241, 245, 249, 0.96));
        }
        .qa-tool-shell-empty h4 {
            margin: 0 0 8px;
            font-size: 1rem;
            color: #0f172a;
        }
        .qa-tool-shell-empty p {
            margin: 0;
            color: #475569;
            line-height: 1.6;
            font-size: 0.92rem;
        }
        .qa-tool-shell-tips {
            border-radius: 16px;
            padding: 14px 16px;
            margin: 8px 0 18px;
            background: #f8fafc;
            border: 1px solid rgba(148, 163, 184, 0.24);
        }
        .qa-tool-shell-tips strong {
            display: block;
            margin-bottom: 8px;
            color: #0f172a;
        }
        .qa-tool-shell-tips ul {
            margin: 0;
            padding-left: 18px;
            color: #334155;
        }
        .qa-tool-shell-tips li {
            margin: 4px 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_tool_page_hero(
    icon: str,
    title: str,
    description: str,
    tags: Iterable[str] | None = None,
    accent: str = "#2563eb",
) -> None:
    _inject_styles()
    tag_items = "".join(f'<span class="qa-tool-shell-tag">{tag}</span>' for tag in (tags or []))
    st.markdown(
        f"""
        <div class="qa-tool-shell-hero" style="--hero-accent: {accent};">
            <h3>{icon} {title}</h3>
            <p>{description}</p>
            <div class="qa-tool-shell-tags">{tag_items}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_tips(title: str, tips: Iterable[str]) -> None:
    _inject_styles()
    tip_items = "".join(f"<li>{tip}</li>" for tip in tips)
    st.markdown(
        f"""
        <div class="qa-tool-shell-tips">
            <strong>{title}</strong>
            <ul>{tip_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_tool_empty_state(title: str, description: str) -> None:
    _inject_styles()
    st.markdown(
        f"""
        <div class="qa-tool-shell-empty">
            <h4>{title}</h4>
            <p>{description}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
