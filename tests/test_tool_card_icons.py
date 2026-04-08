from pathlib import Path


def test_tool_picker_uses_svg_badges_for_professional_icons() -> None:
    streamlit_app_path = Path(__file__).resolve().parents[1] / "src" / "qa_toolkit" / "streamlit_app.py"
    constants_path = Path(__file__).resolve().parents[1] / "src" / "qa_toolkit" / "config" / "constants.py"
    icon_assets_path = Path(__file__).resolve().parents[1] / "src" / "qa_toolkit" / "config" / "tool_icon_assets.py"

    streamlit_app_source = streamlit_app_path.read_text(encoding="utf-8")
    constants_source = constants_path.read_text(encoding="utf-8")
    icon_assets_source = icon_assets_path.read_text(encoding="utf-8")

    assert "from qa_toolkit.config.tool_icon_assets import build_tool_icon_badge" in streamlit_app_source
    assert "TOOL_ICON_SVG_BODIES" in icon_assets_source
    assert "def build_tool_icon_badge" in icon_assets_source
    assert "_build_tool_icon_badge" not in streamlit_app_source
    assert "tool-picker-icon-badge" in constants_source
    assert "tool-picker-banner-icon" in constants_source
    assert 'st.button(f"切换到{category}"' in streamlit_app_source
