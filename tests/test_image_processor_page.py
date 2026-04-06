import sys
from pathlib import Path

from streamlit.testing.v1 import AppTest


ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.ui.pages.image_processor_page import (
    _build_default_crop_box,
    _build_upload_signature,
    _to_cropper_default_coords,
)
from qa_toolkit.utils.image_processing import ImageProcessor

IMAGE_PROCESSOR_PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.image_processor_page import render_image_processor_page
render_image_processor_page()
"""


class _DummyUploadedFile:
    def __init__(self, name: str, payload: bytes) -> None:
        self.name = name
        self._payload = payload
        self.size = len(payload)

    def getvalue(self) -> bytes:
        return self._payload


def test_build_upload_signature_is_stable_for_same_file():
    uploaded_file = _DummyUploadedFile("sample-image.png", b"sample-image-payload")

    signature_a = _build_upload_signature(uploaded_file)
    signature_b = _build_upload_signature(uploaded_file)

    assert signature_a == signature_b
    assert signature_a.startswith("sample-image-")


def test_build_default_crop_box_uses_centered_inset_for_free_crop():
    processor = ImageProcessor()

    crop_box = _build_default_crop_box(processor, 1000, 600, None)

    assert crop_box == (80, 48, 920, 552)
    assert _to_cropper_default_coords(processor, crop_box, 1000, 600) == (80, 920, 48, 552)


def test_build_default_crop_box_respects_aspect_ratio():
    processor = ImageProcessor()

    crop_box = _build_default_crop_box(processor, 1000, 600, (1, 1))

    assert crop_box == (248, 48, 752, 552)
    assert (crop_box[2] - crop_box[0]) == (crop_box[3] - crop_box[1])


def test_image_processor_page_renders_empty_state_without_exceptions():
    app = AppTest.from_string(IMAGE_PROCESSOR_PAGE_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    markdown_values = [getattr(item, "value", "") for item in app.markdown]
    assert any("图片处理工具" in value for value in markdown_values)
    assert any("等待图片输入" in value for value in markdown_values)
