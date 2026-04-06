import sys
from io import BytesIO
from pathlib import Path

from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.image_processing import ImageProcessor


def build_test_image(width=256, height=256):
    """构造高细节图片，便于稳定测试体积控制逻辑。"""
    image = Image.new("RGB", (width, height))
    pixels = []
    for y in range(height):
        for x in range(width):
            pixels.append((
                (x * 17 + y * 13) % 256,
                (x * 29 + y * 19) % 256,
                (x * 7 + y * 23) % 256,
            ))
    image.putdata(pixels)
    return image


def test_save_image_to_bytes_converts_rgba_to_jpg():
    processor = ImageProcessor()
    image = Image.new("RGBA", (64, 64), (30, 90, 180, 120))

    image_bytes = processor.save_image_to_bytes(image, "JPG", quality=85)
    reopened = Image.open(BytesIO(image_bytes))
    reopened.load()

    assert reopened.format == "JPEG"
    assert reopened.mode == "RGB"
    assert reopened.size == (64, 64)


def test_convert_to_target_filesize_can_pad_to_exact_bytes_for_testing():
    processor = ImageProcessor()
    image = build_test_image()
    baseline_size = len(processor.save_image_to_bytes(image, "JPG", quality=95))
    target_size = baseline_size + 4096

    result = processor.convert_to_target_filesize(
        image,
        target_bytes=target_size,
        output_format="JPG",
        exact_padding=True,
    )
    reopened = Image.open(BytesIO(result["data"]))
    reopened.load()

    assert result["padding_applied"] is True
    assert result["size_bytes"] == target_size
    assert reopened.format == "JPEG"
    assert reopened.size == image.size


def test_convert_to_target_filesize_reduces_image_when_target_is_smaller():
    processor = ImageProcessor()
    image = build_test_image(512, 512)

    result = processor.convert_to_target_filesize(
        image,
        target_bytes=12_000,
        output_format="JPG",
        exact_padding=False,
    )

    assert result["size_bytes"] <= 12_000
    assert result["image"].width <= image.width
    assert result["image"].height <= image.height


def test_convert_to_multiple_filesizes_returns_all_requested_variants():
    processor = ImageProcessor()
    image = build_test_image()

    results = processor.convert_to_multiple_filesizes(
        image,
        [("100 KB", 100 * 1024), ("150 KB", 150 * 1024)],
        output_format="JPG",
        exact_padding=True,
    )

    assert [item["target_label"] for item in results] == ["100 KB", "150 KB"]
    assert [item["target_bytes"] for item in results] == [100 * 1024, 150 * 1024]
    assert [item["size_bytes"] for item in results] == [100 * 1024, 150 * 1024]


def test_resize_image_returns_requested_dimensions():
    processor = ImageProcessor()
    image = build_test_image(320, 180)

    resized = processor.resize_image(image, 160, 90, "BILINEAR")

    assert resized.size == (160, 90)


def test_flip_image_supports_horizontal_and_vertical_modes():
    processor = ImageProcessor()
    image = Image.new("RGB", (2, 2))
    image.putdata(
        [
            (255, 0, 0),
            (0, 255, 0),
            (0, 0, 255),
            (255, 255, 0),
        ]
    )

    horizontal = processor.flip_image(image, "左右翻转")
    vertical = processor.flip_image(image, "上下翻转")

    assert horizontal.getpixel((0, 0)) == (0, 255, 0)
    assert horizontal.getpixel((1, 0)) == (255, 0, 0)
    assert vertical.getpixel((0, 0)) == (0, 0, 255)
    assert vertical.getpixel((0, 1)) == (255, 0, 0)


def test_rotate_image_positive_angle_is_clockwise():
    processor = ImageProcessor()
    image = Image.new("RGB", (2, 1))
    image.putdata([(255, 0, 0), (0, 0, 255)])

    rotated = processor.rotate_image(image, 90)

    assert rotated.size == (1, 2)
    assert rotated.getpixel((0, 0)) == (255, 0, 0)
    assert rotated.getpixel((0, 1)) == (0, 0, 255)


def test_crop_image_normalizes_out_of_bounds_box():
    processor = ImageProcessor()
    image = build_test_image(10, 10)

    cropped = processor.crop_image(image, (-5, -4, 14, 13))

    assert cropped.size == (10, 10)
