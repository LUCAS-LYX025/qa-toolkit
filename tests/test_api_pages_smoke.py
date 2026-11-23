import sys
from pathlib import Path
from types import SimpleNamespace

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


def test_mobsf_hash_fetch_does_not_mutate_instantiated_hash_widget(monkeypatch) -> None:
    from qa_toolkit.ui.pages import api_security_page

    class LockedWidgetState(dict):
        def __getattr__(self, key):
            return self[key]

        def __setattr__(self, key, value):
            if key == "app_sec_mobsf_hash_query":
                raise RuntimeError("instantiated widget cannot be changed")
            self[key] = value

    state = LockedWidgetState(
        app_sec_mobsf_hash_query="scan-hash",
        app_sec_mobsf_base_url="http://127.0.0.1:8000",
        app_sec_mobsf_api_key="test-key",
        app_sec_mobsf_timeout=180.0,
        app_sec_mobsf_verify_ssl=True,
        app_sec_mobsf_include_pdf=True,
    )
    monkeypatch.setattr(api_security_page, "st", SimpleNamespace(session_state=state))

    class FakeSecurityTool:
        def build_mobsf_static_bundle_from_hash(self, **kwargs):
            assert kwargs["file_hash"] == "scan-hash"
            assert kwargs["include_pdf"] is True
            return {"json_report": {"ok": True}, "scorecard": {"score": 1}, "pdf_bytes": b"%PDF"}

    bundle = api_security_page._load_mobsf_static_bundle_by_hash(FakeSecurityTool(), "scan-hash")

    assert bundle["pdf_bytes"] == b"%PDF"
    assert state["app_sec_mobsf_hash_query"] == "scan-hash"
    assert state["app_sec_mobsf_hash_report"] == {"ok": True}
    assert state["app_sec_mobsf_hash_scorecard"] == {"score": 1}
    assert state["app_sec_mobsf_hash_pdf_bytes"] == b"%PDF"
