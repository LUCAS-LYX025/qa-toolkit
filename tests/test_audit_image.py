"""图片处理工具专项审计回归（GitHub issues #270-#289）。"""
from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from unittest import mock

import pytest
from PIL import Image
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.core.image_registry import (  # noqa: E402
    AspectRatioSpec,
    ImageFormatSpec,
    PresetSizeSpec,
    PresetTargetSpec,
    ResampleSpec,
    WatermarkPositionSpec,
    configure_image_limits,
    get_aspect_ratios,
    get_image_formats,
    get_image_limits,
    get_preset_sizes,
    get_preset_targets,
    get_registry_summary,
    get_resample_methods,
    get_watermark_positions,
    register_aspect_ratio,
    register_image_format,
    register_preset_size,
    register_preset_target,
    register_resample_method,
    register_watermark_position,
    reset_image_registry,
)
from qa_toolkit.ui.pages.image_processor_page import (  # noqa: E402
    _build_manifest_bytes,
    _hex_to_rgb,
    _load_image,
    _render_crop_metrics_card,
    _safe_download_stem,
)
from qa_toolkit.utils.image_processing import ImageProcessor  # noqa: E402

IMAGE_PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.image_processor_page import render_image_processor_page
render_image_processor_page()
"""


class DummyUpload:
    def __init__(self, payload: bytes, name: str = "sample.png") -> None:
        self._payload = payload
        self.name = name
        self.size = len(payload)

    def getvalue(self) -> bytes:
        return self._payload


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_image_registry()
    yield
    reset_image_registry()


def make_image(width: int = 64, height: int = 48, mode: str = "RGB") -> Image.Image:
    return Image.new(mode, (width, height), (30, 90, 180))


def make_gif_bytes(colors=((255, 0, 0), (0, 0, 255)), duration=120, loop=2) -> bytes:
    frames = [Image.new("RGB", (32, 32), color) for color in colors]
    buffer = io.BytesIO()
    frames[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames[1:],
        duration=duration,
        loop=loop,
    )
    return buffer.getvalue()


def test_registry_defaults_and_summary():
    summary = get_registry_summary()
    assert {"JPG", "PNG", "WEBP", "GIF", "BMP"} <= set(summary["formats"])
    assert summary["resamplers"] == ["BICUBIC", "BILINEAR", "LANCZOS", "NEAREST"]
    assert "100 KB" in summary["preset_targets"]
    assert "图片中心" in summary["watermark_positions"]
    assert summary["limits"]["max_output_side"] == 8192


def test_register_image_format_rejects_duplicate_and_supports_replace():
    spec = ImageFormatSpec("XPNG", "PNG", "xpng", "image/x-png", supports_alpha=True)
    register_image_format(spec)
    assert ImageProcessor().get_pil_format("xpng") == "PNG"

    with pytest.raises(ValueError, match="已存在"):
        register_image_format(spec)
    register_image_format(
        ImageFormatSpec("XPNG", "PNG", "xpng2", "image/x-png2", supports_alpha=True),
        replace=True,
    )
    assert get_image_formats()["XPNG"].extension == "xpng2"


def test_register_resample_target_size_ratio_and_position():
    register_resample_method(ResampleSpec("BOX", Image.Resampling.BOX))
    register_preset_target(PresetTargetSpec("75 KB", 75 * 1024))
    register_preset_size(PresetSizeSpec("测试方图", 320, 320))
    register_aspect_ratio(AspectRatioSpec("测试比例", 7, 5))
    register_watermark_position(
        WatermarkPositionSpec("左上角固定", lambda w, h, tw, th: (0, 0))
    )

    assert ImageProcessor().get_resample_filter("BOX") == Image.Resampling.BOX
    assert get_preset_targets()["75 KB"].bytes_ == 75 * 1024
    assert get_preset_sizes()["测试方图"].width == 320
    assert get_aspect_ratios()["测试比例"].height == 5
    assert "左上角固定" in get_watermark_positions()

    watermarked = ImageProcessor().add_watermark(
        make_image(), "QA", "左上角固定", 20, (255, 255, 255), 0.5, 0
    )
    assert watermarked.size == (64, 48)


def test_registry_rejects_invalid_specs():
    with pytest.raises(ValueError, match="不能为空"):
        register_image_format(ImageFormatSpec(" ", "PNG", "png", "image/png"))
    with pytest.raises(ValueError, match="大于 0"):
        register_preset_target(PresetTargetSpec("坏档位", 0))
    with pytest.raises(ValueError, match="正整数"):
        register_preset_size(PresetSizeSpec("坏尺寸", -1, 10))
    with pytest.raises(ValueError, match="可调用"):
        register_watermark_position(WatermarkPositionSpec("坏位置", None))


def test_reset_image_registry_removes_custom_entries():
    register_preset_target(PresetTargetSpec("临时档位", 1024))
    assert "临时档位" in get_preset_targets()
    reset_image_registry()
    assert "临时档位" not in get_preset_targets()
    assert "100 KB" in get_preset_targets()


def test_unknown_format_and_resampler_raise_with_available_options():
    processor = ImageProcessor()
    with pytest.raises(ValueError, match="当前可用"):
        processor.get_pil_format("XYZ")
    with pytest.raises(ValueError, match="当前可用"):
        processor.convert_image_for_format(make_image(), "XYZ")
    with pytest.raises(ValueError, match="当前可用"):
        processor.get_resample_filter("LANCZOSZ")


def test_la_transparent_pixels_are_composited_on_white_background():
    image = Image.new("LA", (2, 1))
    image.putdata([(0, 0), (255, 255)])
    converted = ImageProcessor().convert_image_for_format(image, "JPG")
    assert list(converted.getdata()) == [(255, 255, 255), (255, 255, 255)]


def test_convert_transparent_pixels_honors_custom_background():
    image = Image.new("LA", (1, 1), (0, 0))
    converted = ImageProcessor().convert_image_for_format(
        image, "BMP", background_color=(0, 0, 255)
    )
    assert converted.getpixel((0, 0)) == (0, 0, 255)


def test_save_image_to_bytes_validates_quality_range():
    processor = ImageProcessor()
    for quality in (-20, 0, 101, 250):
        with pytest.raises(ValueError, match="1-100"):
            processor.save_image_to_bytes(make_image(), "JPG", quality=quality)


def test_preserve_metadata_is_opt_in():
    image = make_image()
    exif = Image.Exif()
    exif[270] = "GPS-LAT-31.23-LON-121.47"
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)
    source = Image.open(io.BytesIO(buffer.getvalue()))
    processor = ImageProcessor()

    default_export = Image.open(io.BytesIO(processor.save_image_to_bytes(source, "JPG")))
    assert default_export.getexif().get(270) is None

    preserved = Image.open(io.BytesIO(
        processor.save_image_to_bytes(source, "JPG", preserve_metadata=True)
    ))
    assert preserved.getexif().get(270) == "GPS-LAT-31.23-LON-121.47"


def test_resize_rejects_oversized_side_and_pixel_budget():
    processor = ImageProcessor()
    with pytest.raises(ValueError, match="不能超过 8192"):
        processor.resize_image(make_image(), 1_000_000, 1)

    configure_image_limits(max_image_pixels=100)
    with pytest.raises(ValueError, match="像素数超过上限"):
        processor.resize_image(make_image(), 20, 20)


def test_load_image_applies_exif_orientation():
    image = make_image(64, 48)
    exif = Image.Exif()
    exif[274] = 6
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", exif=exif)

    loaded = _load_image(DummyUpload(buffer.getvalue(), "photo.jpg"))
    assert loaded.size == (48, 64)


def test_load_image_keeps_animation_frames():
    loaded = _load_image(DummyUpload(make_gif_bytes(), "animated.gif"))
    assert getattr(loaded, "n_frames", 1) == 2


def test_load_image_rejects_oversized_and_unsupported_inputs():
    configure_image_limits(max_upload_bytes=100)
    with pytest.raises(ValueError, match="超过上限"):
        _load_image(DummyUpload(b"x" * 200, "big.png"))

    configure_image_limits(max_upload_bytes=50 * 1024 * 1024)
    buffer = io.BytesIO()
    make_image().save(buffer, format="TIFF")
    with pytest.raises(ValueError, match="不支持的图片格式"):
        _load_image(DummyUpload(buffer.getvalue(), "fake.png"))


def test_normalize_crop_box_swaps_reversed_coordinates():
    processor = ImageProcessor()
    assert processor.normalize_crop_box((50, 40, 5, 5), 64, 48) == (5, 5, 50, 40)
    assert processor.crop_image(make_image(), (50, 40, 5, 5)).size == (45, 35)


def test_target_size_validates_quality_range_and_resize_step():
    processor = ImageProcessor()
    with pytest.raises(ValueError, match="不能高于"):
        processor.convert_to_target_filesize(
            make_image(), 5000, "JPG", min_quality=90, max_quality=10
        )
    with pytest.raises(ValueError, match="缩放步长"):
        processor.convert_to_target_filesize(make_image(), 5000, "JPG", resize_step=1.5)


def test_target_size_reports_unachievable_target():
    result = ImageProcessor().convert_to_target_filesize(
        make_image(), 100, "JPG", exact_padding=False
    )
    assert result["target_achieved"] is False
    assert "目标体积过小" in result["note"]


def test_target_size_and_save_preserve_animation():
    source = Image.open(io.BytesIO(make_gif_bytes()))
    processor = ImageProcessor()

    direct = Image.open(io.BytesIO(processor.save_image_to_bytes(source, "GIF")))
    assert direct.n_frames == 2

    result = processor.convert_to_target_filesize(source, 20000, "GIF")
    assert result["animated"] is True
    assert result["frame_count"] == 2
    animated = Image.open(io.BytesIO(result["data"]))
    assert animated.n_frames == 2
    assert animated.info.get("duration") == 120
    assert animated.info.get("loop") == 2


def test_watermark_validates_opacity_color_and_size():
    processor = ImageProcessor()
    with pytest.raises(RuntimeError, match="添加水印失败: 透明度"):
        processor.add_watermark(make_image(), "QA", "图片中心", 20, (255, 255, 255), 5.0, 0)
    with pytest.raises(RuntimeError, match="0-255"):
        processor.add_watermark(make_image(), "QA", "图片中心", 20, (999, 0, 0), 0.5, 0)
    with pytest.raises(RuntimeError, match="不能为空"):
        processor.add_watermark(make_image(), "", "图片中心", 20, (255, 255, 255), 0.5, 0)
    assert processor.add_watermark(
        make_image(), "QA", "图片中心", 20, (255, 255, 255, 128), 0.5, 0
    ).size == (64, 48)


def test_invalid_custom_font_does_not_leave_temp_file():
    real_unlink = os.unlink
    calls = []

    def tracking_unlink(path):
        calls.append(path)
        return real_unlink(path)

    with mock.patch("os.unlink", tracking_unlink):
        with pytest.raises(RuntimeError, match="添加水印失败: 自定义字体加载失败"):
            ImageProcessor().add_watermark(
                make_image(), "QA", "图片中心", 20, (255, 255, 255), 0.5, 0,
                font_file=io.BytesIO(b"not-a-real-font"),
            )
    assert calls == []


def test_safe_download_stem_removes_path_and_reserved_chars():
    assert _safe_download_stem(Path("../../evil?name.png").stem) == "evil_name"
    assert _safe_download_stem("  ") == "uploaded-image"
    assert "/" not in _safe_download_stem("a/b:c")


def test_manifest_has_bom_and_formula_guard():
    payload = _build_manifest_bytes([{
        "target_label": "=1+1",
        "target_bytes": 1024,
        "size_bytes": 1000,
        "scale_ratio": 0.9,
        "target_achieved": False,
        "note": "目标体积过小",
    }])
    assert payload.startswith(b"\xef\xbb\xbf")
    assert "'=1+1" in payload.decode("utf-8-sig")


def test_crop_metric_card_is_chinese():
    with mock.patch(
        "qa_toolkit.ui.pages.image_processor_page.st.markdown"
    ) as markdown:
        _render_crop_metrics_card((0, 0, 10, 10), 100, 100)
    rendered = markdown.call_args.args[0]
    assert "当前选区" in rendered
    assert "Current Selection" not in rendered


def test_hex_to_rgb_rejects_malformed_color():
    with pytest.raises(ValueError, match="#RRGGBB"):
        _hex_to_rgb("#FFF")


def test_page_renders_registered_format_in_selectbox():
    register_image_format(
        ImageFormatSpec("TIFFTEST", "TIFF", "tiff", "image/tiff", supports_metadata=True)
    )
    buffer = io.BytesIO()
    make_image(8, 8).save(buffer, format="PNG")
    upload = DummyUpload(buffer.getvalue(), "sample.png")

    with mock.patch(
        "qa_toolkit.ui.pages.image_processor_page.st.file_uploader",
        return_value=upload,
    ):
        app = AppTest.from_string(IMAGE_PAGE_SCRIPT, default_timeout=5).run()

    assert not app.exception, [item.value for item in app.exception]
    options = [option for select in app.selectbox for option in select.options]
    assert "TIFFTEST" in options
