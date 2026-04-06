import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))


def _build_app(module_path: str, render_name: str) -> AppTest:
    script = (
        f"import sys\n"
        f"sys.path.insert(0, {str(SRC_DIR)!r})\n"
        f"from {module_path} import {render_name}\n"
        f"{render_name}()\n"
    )
    return AppTest.from_string(script, default_timeout=5)


def _assert_no_exceptions(app: AppTest) -> None:
    assert not app.exception, [item.value for item in app.exception]


def test_api_dev_tools_page_renders_without_exceptions() -> None:
    app = _build_app("qa_toolkit.ui.pages.api_dev_tools_page", "render_api_dev_tools_page").run()

    _assert_no_exceptions(app)
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("接口研发辅助工具" in value for value in markdown_values)


def test_api_security_page_renders_without_exceptions() -> None:
    app = _build_app("qa_toolkit.ui.pages.api_security_page", "render_api_security_test_page").run()

    _assert_no_exceptions(app)
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("应用安全测试" in value for value in markdown_values)
