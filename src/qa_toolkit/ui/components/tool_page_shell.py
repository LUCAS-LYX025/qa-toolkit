from __future__ import annotations

from typing import Iterable

import streamlit as st


def _inject_styles() -> None:
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
                radial-gradient(circle at top right, color-mix(in srgb, var(--hero-accent) 18%, white 82%), transparent 52%),
                linear-gradient(145deg, rgba(250, 252, 255, 0.99) 0%, rgba(241, 246, 252, 0.99) 56%, rgba(248, 244, 236, 0.99) 100%);
            color: #17324a;
            border: 1px solid rgba(208, 218, 231, 0.96);
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.88),
                0 18px 36px rgba(15, 23, 42, 0.08);
        }
        .qa-tool-shell-hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background:
                linear-gradient(135deg, rgba(255,255,255,0.22), rgba(255,255,255,0.02)),
                radial-gradient(circle at bottom left, color-mix(in srgb, var(--hero-accent) 10%, white 90%), rgba(255,255,255,0) 42%);
            pointer-events: none;
            z-index: 0;
        }
        .qa-tool-shell-hero__content {
            position: relative;
            z-index: 1;
            max-width: 920px;
            padding: 18px 20px 16px;
            border-radius: 18px;
            background: linear-gradient(135deg, rgba(255,255,255,0.84), rgba(255,255,255,0.70));
            border: 1px solid rgba(214, 223, 234, 0.92);
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.84),
                0 10px 22px rgba(15, 23, 42, 0.06);
        }
        .qa-tool-shell-hero__content::before {
            content: "";
            position: absolute;
            inset: 0 auto 0 0;
            width: 4px;
            border-radius: 18px 0 0 18px;
            background: linear-gradient(180deg, var(--hero-accent) 0%, color-mix(in srgb, var(--hero-accent) 42%, white 58%) 100%);
            opacity: 0.9;
        }
        .qa-tool-shell-hero__title {
            margin: 0 0 8px;
            font-size: 1.76rem;
            font-weight: 900;
            letter-spacing: 0.01em;
            color: var(--hero-title-color);
            text-shadow:
                0 1px 0 rgba(255,255,255,0.52),
                0 2px 8px rgba(15, 23, 42, 0.08);
        }
        .qa-tool-shell-hero__desc {
            margin: 0;
            font-size: 1.02rem;
            line-height: 1.72;
            color: var(--hero-desc-color);
            font-weight: 700;
            text-shadow:
                0 1px 0 rgba(255,255,255,0.42);
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
            background: color-mix(in srgb, var(--hero-accent) 10%, white 90%);
            border: 1px solid color-mix(in srgb, var(--hero-accent) 22%, white 78%);
            color: #17324a;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.72);
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
    title_color: str = "#10253a",
    description_color: str = "#365168",
) -> None:
    _inject_styles()
    tag_items = "".join(f'<span class="qa-tool-shell-tag">{tag}</span>' for tag in (tags or []))
    st.markdown(
        f"""
        <div class="qa-tool-shell-hero" style="--hero-accent: {accent}; --hero-title-color: {title_color}; --hero-desc-color: {description_color};">
            <div class="qa-tool-shell-hero__content">
                <h3 class="qa-tool-shell-hero__title">{icon} {title}</h3>
                <p class="qa-tool-shell-hero__desc">{description}</p>
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
