"""通用「缺陷绩效分析」页面 AppTest 冒烟：首屏渲染 + 连接失败降级。"""
import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))


PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.tracking_performance_page import render_tracking_performance_page
render_tracking_performance_page()
"""


def test_tracking_performance_page_renders_without_exceptions():
    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=8).run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    caption_values = [getattr(item, "value", "") for item in app.caption]
    assert any("缺陷绩效分析" in value for value in markdown_values)
    assert not any("禅道绩效统计工具使用说明" in value for value in markdown_values)
    assert any("已接入数据源" in value for value in caption_values)
    labels = [getattr(item, "label", "") for item in app.selectbox]
    assert "数据源" in labels
    assert "归因规则" not in labels  # 未连接前不暴露统计配置


def test_tracking_performance_page_handles_connection_failure_gracefully():
    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=8).run()
    assert not app.exception, [item.value for item in app.exception]

    for button in app.button:
        if getattr(button, "label", "") == "连接并加载":
            button.click()
            break
    app.run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("数据源连接失败" in value for value in markdown_values)
    assert any("等待数据源连接" in value for value in markdown_values)
