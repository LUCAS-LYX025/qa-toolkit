import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

STYLE_REINJECTION_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})

import streamlit as st

st.session_state["_qa_toolkit_workflow_panels_style_loaded"] = True
st.session_state["_tool_page_shell_styles_ready"] = True
st.session_state["_status_feedback_styles_ready"] = True

from qa_toolkit.ui.components.tool_page_shell import render_tool_page_hero
from qa_toolkit.ui.components.workflow_panels import render_workflow_guide
from qa_toolkit.ui.components.status_feedback import render_info_feedback

render_tool_page_hero("🌐", "样式回归", "验证第二次进入页面时样式仍会重新注入。", tags=["hero"], accent="#1d4ed8")
render_workflow_guide(
    title="向导回归",
    description="验证页面向导样式不会因为 session_state 标记而丢失。",
    steps=["第一步", "第二步"],
    tips=["样式要重注入"],
    eyebrow="页面向导",
)
render_info_feedback("验证状态反馈样式。")
"""


def test_component_styles_are_reinjected_even_if_session_flags_exist() -> None:
    app = AppTest.from_string(STYLE_REINJECTION_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any(".qa-tool-shell-hero" in value for value in markdown_values)
    assert any(".qa-guide-card" in value for value in markdown_values)
    assert any(".qa-status-feedback" in value for value in markdown_values)
