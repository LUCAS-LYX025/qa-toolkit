import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))


ZENTAO_PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.zentao_performance_page import render_zentao_performance_page
render_zentao_performance_page()
"""


def test_zentao_performance_page_renders_without_exceptions() -> None:
    app = AppTest.from_string(ZENTAO_PAGE_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("禅道绩效统计" in value for value in markdown_values)
    radio_labels = [getattr(item, "label", "") for item in app.radio]
    assert "连接方式" in radio_labels


def test_zentao_performance_page_handles_proxy_connection_failure_gracefully() -> None:
    app = AppTest.from_string(ZENTAO_PAGE_SCRIPT, default_timeout=5).run()

    for item in app.radio:
        if item.label == "连接方式":
            item.set_value("HTTP代理")
            break
    app.run()

    for item in app.text_input:
        if item.label == "代理地址":
            item.set_value("http://127.0.0.1:1")
            break

    for item in app.button:
        if item.label == "连接并加载数据":
            item.click()
            break
    app.run()

    assert not app.exception, [item.value for item in app.exception]
