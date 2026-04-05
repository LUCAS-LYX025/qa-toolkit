import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

AUTHOR_PROFILE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.components.author_profile import AuthorProfile
AuthorProfile().render_sidebar_compact_profile()
"""


def test_sidebar_compact_author_profile_renders_without_exception() -> None:
    app = AppTest.from_string(AUTHOR_PROFILE_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    assert app.expander[0].label == "扫码名片 / 更多资源"
