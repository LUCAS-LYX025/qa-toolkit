from pathlib import Path


def test_tool_card_click_bridge_uses_document_level_event_delegation() -> None:
    streamlit_app_path = Path(__file__).resolve().parents[1] / "src" / "qa_toolkit" / "streamlit_app.py"
    source = streamlit_app_path.read_text(encoding="utf-8")

    assert "__qaToolkitToolCardBridgeInstalled" in source
    assert "doc.addEventListener('click'" in source
    assert "doc.addEventListener('keydown'" in source
    assert "trigger.dataset.bound" not in source
