import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

IMAGE_PROCESSOR_PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.image_processor_page import render_image_processor_page
render_image_processor_page()
"""


def test_image_processor_page_renders_empty_state_without_exceptions():
    app = AppTest.from_string(IMAGE_PROCESSOR_PAGE_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("图片处理工具" in value for value in markdown_values)
    assert any("等待图片输入" in value for value in markdown_values)
