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
            isolation: isolate;
            border-radius: 24px;
            padding: 24px 24px 20px;
            margin: 10px 0 18px;
            background:
                radial-gradient(circle at top right, rgba(255,255,255,0.24), transparent 34%),
                linear-gradient(135deg, var(--hero-accent) 0%, #10253a 58%, #0f172a 100%);
            color: #f8fafc;
            border: 1px solid rgba(255, 255, 255, 0.12);
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.16);
        }
        .qa-tool-shell-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(135deg, rgba(7, 20, 39, 0.14), rgba(7, 20, 39, 0.34)),
                radial-gradient(circle at bottom left, rgba(255,255,255,0.08), rgba(255,255,255,0) 42%);
            pointer-events: none;
            z-index: 0;
        }
        .qa-tool-shell-hero__content {
            position: relative;
            z-index: 1;
            max-width: 920px;
        }
        .qa-tool-shell-hero h3 {
            margin: 0 0 8px;
            font-size: 1.72rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            color: #ffffff;
            text-shadow: 0 2px 8px rgba(7, 20, 39, 0.28);
        }
        .qa-tool-shell-hero p {
            margin: 0;
            font-size: 1rem;
            line-height: 1.72;
            color: rgba(248, 250, 252, 0.98);
            font-weight: 600;
            text-shadow: 0 1px 4px rgba(7, 20, 39, 0.32);
        }
        .qa-tool-shell-tags {
            display: flex;
            flex-wrap: wrap;
            gap: 10px;
            margin-top: 16px;
        }
        .qa-tool-shell-tag {
            padding: 6px 11px;
            border-radius: 999px;
            font-size: 0.82rem;
            font-weight: 700;
            background: rgba(255, 255, 255, 0.18);
            border: 1px solid rgba(255, 255, 255, 0.28);
            color: #ffffff;
            backdrop-filter: blur(6px);
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.12);
        }
        .qa-tool-shell-empty {
            border: 1px dashed rgba(250, 204, 21, 0.28);
            border-radius: 18px;
            padding: 20px 18px;
            margin: 14px 0;
            background:
                radial-gradient(circle at top right, rgba(250, 204, 21, 0.10), rgba(250, 204, 21, 0) 40%),
                linear-gradient(145deg, rgba(247, 249, 253, 0.98), rgba(238, 243, 250, 0.98), rgba(247, 239, 223, 0.98));
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.88),
                0 12px 22px rgba(7, 20, 39, 0.06);
        }
        .qa-tool-shell-empty h4 {
            margin: 0 0 8px;
            font-size: 1rem;
            color: #17324a;
        }
        .qa-tool-shell-empty p {
            margin: 0;
            color: #436176;
            line-height: 1.6;
            font-size: 0.92rem;
        }
        .qa-tool-shell-tips {
            border-radius: 18px;
            padding: 14px 16px;
            margin: 8px 0 18px;
            background:
                radial-gradient(circle at top right, rgba(250, 204, 21, 0.10), rgba(250, 204, 21, 0) 38%),
                linear-gradient(145deg, rgba(247, 249, 253, 0.98), rgba(238, 243, 250, 0.98), rgba(247, 239, 223, 0.98));
            border: 1px solid rgba(213, 220, 232, 0.96);
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.88),
                0 10px 20px rgba(7, 20, 39, 0.06);
        }
        .qa-tool-shell-tips strong {
            display: block;
            margin-bottom: 8px;
            color: #17324a;
        }
        .qa-tool-shell-tips ul {
            margin: 0;
            padding-left: 18px;
            color: #436176;
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
            <div class="qa-tool-shell-hero__content">
                <h3>{icon} {title}</h3>
                <p>{description}</p>
                <div class="qa-tool-shell-tags">{tag_items}</div>
            </div>
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
