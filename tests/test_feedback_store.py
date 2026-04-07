import sys
from pathlib import Path
from unittest.mock import patch

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.support.feedback_store import FeedbackStore


FEEDBACK_PANEL_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})

from qa_toolkit.ui.components.feedback_panel import FeedbackSection

FeedbackSection().render_tool_feedback_bar("数据生成工具")
"""

FEEDBACK_BAR_CLICK_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})

from qa_toolkit.ui.components.feedback_panel import FeedbackSection

FeedbackSection().render_tool_feedback_bar("Demo Tool")
"""


def test_feedback_store_persists_records_across_instances(tmp_path: Path) -> None:
    db_path = tmp_path / "feedback.sqlite3"

    store = FeedbackStore(db_path)
    first = store.add_feedback({
        "type": "功能建议",
        "urgency": "一般",
        "rating": 4,
        "content": "希望支持批量导入模板。",
        "nickname": "小李",
        "tool_name": "数据生成工具",
        "source": "compact_popover",
    })
    store.add_feedback({
        "type": "问题反馈",
        "urgency": "重要",
        "rating": 2,
        "content": "刷新后统计会丢失。",
        "nickname": "匿名用户",
        "tool_name": "日志分析工具",
        "source": "full_page",
    })

    reloaded_store = FeedbackStore(db_path)
    feedbacks = reloaded_store.list_feedbacks()
    latest_tool_feedback = reloaded_store.list_feedbacks(tool_name="数据生成工具", newest_first=True, limit=1)

    assert first["id"] == 1
    assert len(feedbacks) == 2
    assert feedbacks[0]["content"] == "希望支持批量导入模板。"
    assert feedbacks[1]["content"] == "刷新后统计会丢失。"
    assert latest_tool_feedback[0]["tool_name"] == "数据生成工具"
    assert latest_tool_feedback[0]["nickname"] == "小李"


def test_feedback_panel_reads_persisted_counts_from_storage(tmp_path: Path) -> None:
    db_path = tmp_path / "feedback.sqlite3"
    store = FeedbackStore(db_path)
    store.add_feedback({
        "type": "功能建议",
        "urgency": "一般",
        "rating": 5,
        "content": "这个工具很好用。",
        "nickname": "匿名用户",
        "tool_name": "数据生成工具",
        "source": "quick_action",
        "reaction": "有帮助",
    })
    store.add_feedback({
        "type": "问题反馈",
        "urgency": "重要",
        "rating": 2,
        "content": "别的工具也有一条反馈。",
        "nickname": "匿名用户",
        "tool_name": "日志分析工具",
        "source": "full_page",
    })

    with patch.dict("os.environ", {"QA_TOOLKIT_FEEDBACK_DB_PATH": str(db_path)}, clear=False):
        app = AppTest.from_string(FEEDBACK_PANEL_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("当前工具已收到 1 条反馈，全站累计 2 条" in value for value in markdown_values)


def test_feedback_panel_quick_feedback_updates_counts_without_manual_refresh(tmp_path: Path) -> None:
    db_path = tmp_path / "feedback.sqlite3"

    with patch.dict("os.environ", {"QA_TOOLKIT_FEEDBACK_DB_PATH": str(db_path)}, clear=False):
        app = AppTest.from_string(FEEDBACK_BAR_CLICK_SCRIPT, default_timeout=5).run()

        assert not app.exception, [item.value for item in app.exception]
        markdown_values = [getattr(item, "value", "") for item in app.markdown]
        assert any("当前工具已收到 0 条反馈，全站累计 0 条" in value for value in markdown_values)

        app.button(key="feedback_helpful_demo_tool").click().run()

        assert not app.exception, [item.value for item in app.exception]
        markdown_values = [getattr(item, "value", "") for item in app.markdown]
        assert any("当前工具已收到 1 条反馈，全站累计 1 条" in value for value in markdown_values)

    reloaded_store = FeedbackStore(db_path)
    feedbacks = reloaded_store.list_feedbacks(tool_name="Demo Tool")
    assert len(feedbacks) == 1
    assert feedbacks[0]["reaction"] == "有帮助"
