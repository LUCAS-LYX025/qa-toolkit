"""图片处理工具的注册式扩展点。

把输出格式、重采样算法、预设体积/尺寸、裁剪比例、水印位置和资源上限集中管理：
- 页面下拉从注册表生成，新增业务档位不需要改页面硬编码；
- 核心处理函数通过注册表校验名称，未知格式/算法不再静默降级；
- 注册表返回浅拷贝，Spec 冻结，避免调用方污染全局配置。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, Tuple

from PIL import Image


@dataclass(frozen=True)
class ImageFormatSpec:
    """一种可导出的图片格式。"""

    name: str
    pil_format: str
    extension: str
    mime: str
    lossy: bool = False
    supports_alpha: bool = False
    supports_animation: bool = False
    supports_metadata: bool = False
    description: str = ""


@dataclass(frozen=True)
class ResampleSpec:
    """一种 Pillow 重采样算法。"""

    name: str
    resample: Any
    description: str = ""


@dataclass(frozen=True)
class PresetTargetSpec:
    """目标体积档位。"""

    label: str
    bytes_: int
    description: str = ""


@dataclass(frozen=True)
class PresetSizeSpec:
    """预设输出尺寸。"""

    label: str
    width: int
    height: int
    description: str = ""


@dataclass(frozen=True)
class AspectRatioSpec:
    """裁剪比例。"""

    label: str
    width: int
    height: int
    description: str = ""


@dataclass(frozen=True)
class WatermarkPositionSpec:
    """水印位置解析器。"""

    name: str
    resolve: Callable[[int, int, int, int], Tuple[int, int]]
    description: str = ""


@dataclass(frozen=True)
class ImageLimits:
    """资源使用上限，可按部署环境调整。"""

    max_upload_bytes: int = 50 * 1024 * 1024
    max_image_pixels: int = 40_000_000
    max_output_side: int = 8192
    max_font_bytes: int = 20 * 1024 * 1024


_LOCK = threading.RLock()

_FORMATS: Dict[str, ImageFormatSpec] = {}
_RESAMPLERS: Dict[str, ResampleSpec] = {}
_TARGETS: Dict[str, PresetTargetSpec] = {}
_SIZES: Dict[str, PresetSizeSpec] = {}
_RATIOS: Dict[str, AspectRatioSpec] = {}
_POSITIONS: Dict[str, WatermarkPositionSpec] = {}
_LIMITS = ImageLimits()


def _clean_name(name: str, *, upper: bool = False) -> str:
    key = str(name or "").strip()
    if not key:
        raise ValueError("扩展点名称不能为空")
    return key.upper() if upper else key


def _register(mapping, name, spec, *, replace: bool, upper: bool = False) -> None:
    key = _clean_name(name, upper=upper)
    with _LOCK:
        if key in mapping and not replace:
            raise ValueError(f"扩展点已存在: {key}；如需覆盖请传 replace=True")
        mapping[key] = spec


def register_image_format(spec: ImageFormatSpec, *, replace: bool = False) -> None:
    """注册输出格式；格式名大小写不敏感。"""
    if not isinstance(spec, ImageFormatSpec):
        raise ValueError("spec 必须是 ImageFormatSpec")
    if not str(spec.pil_format or "").strip():
        raise ValueError("Pillow 格式名不能为空")
    if not str(spec.extension or "").strip().lstrip("."):
        raise ValueError("文件扩展名不能为空")
    _register(_FORMATS, spec.name, spec, replace=replace, upper=True)


def register_resample_method(spec: ResampleSpec, *, replace: bool = False) -> None:
    """注册重采样算法。"""
    if not isinstance(spec, ResampleSpec):
        raise ValueError("spec 必须是 ResampleSpec")
    if spec.resample is None:
        raise ValueError("重采样算法不能为空")
    _register(_RESAMPLERS, spec.name, spec, replace=replace, upper=True)


def register_preset_target(spec: PresetTargetSpec, *, replace: bool = False) -> None:
    """注册目标体积档位。"""
    if not isinstance(spec, PresetTargetSpec):
        raise ValueError("spec 必须是 PresetTargetSpec")
    if isinstance(spec.bytes_, bool) or not isinstance(spec.bytes_, int) or spec.bytes_ <= 0:
        raise ValueError("目标体积必须是大于 0 的整数")
    _register(_TARGETS, spec.label, spec, replace=replace)


def register_preset_size(spec: PresetSizeSpec, *, replace: bool = False) -> None:
    """注册预设尺寸。"""
    if not isinstance(spec, PresetSizeSpec):
        raise ValueError("spec 必须是 PresetSizeSpec")
    if spec.width <= 0 or spec.height <= 0:
        raise ValueError("预设尺寸必须为正整数")
    _register(_SIZES, spec.label, spec, replace=replace)


def register_aspect_ratio(spec: AspectRatioSpec, *, replace: bool = False) -> None:
    """注册裁剪比例。"""
    if not isinstance(spec, AspectRatioSpec):
        raise ValueError("spec 必须是 AspectRatioSpec")
    if spec.width <= 0 or spec.height <= 0:
        raise ValueError("裁剪比例必须为正整数")
    _register(_RATIOS, spec.label, spec, replace=replace)


def register_watermark_position(spec: WatermarkPositionSpec, *, replace: bool = False) -> None:
    """注册水印位置解析器。"""
    if not isinstance(spec, WatermarkPositionSpec):
        raise ValueError("spec 必须是 WatermarkPositionSpec")
    if not callable(spec.resolve):
        raise ValueError("水印位置解析器必须可调用")
    _register(_POSITIONS, spec.name, spec, replace=replace)


def configure_image_limits(
    *,
    max_upload_bytes: int | None = None,
    max_image_pixels: int | None = None,
    max_output_side: int | None = None,
    max_font_bytes: int | None = None,
) -> ImageLimits:
    """更新资源上限；未传字段保持原值。"""
    global _LIMITS
    values = {
        "max_upload_bytes": max_upload_bytes,
        "max_image_pixels": max_image_pixels,
        "max_output_side": max_output_side,
        "max_font_bytes": max_font_bytes,
    }
    current = _LIMITS.__dict__
    for key, value in values.items():
        if value is None:
            continue
        if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
            raise ValueError(f"{key} 必须是大于 0 的整数")
        current[key] = value
    with _LOCK:
        _LIMITS = ImageLimits(**current)
        return _LIMITS


def get_image_limits() -> ImageLimits:
    with _LOCK:
        return _LIMITS


def get_image_formats() -> Dict[str, ImageFormatSpec]:
    with _LOCK:
        return dict(_FORMATS)


def get_image_format(name: str) -> ImageFormatSpec:
    key = _clean_name(name, upper=True)
    with _LOCK:
        spec = _FORMATS.get(key)
    if spec is None:
        available = "、".join(sorted(_FORMATS))
        raise ValueError(f"不支持的图片格式: {name}；当前可用: {available}")
    return spec


def find_image_format(name: str) -> ImageFormatSpec | None:
    """宽松查询，供页面推导扩展名/MIME 使用。"""
    try:
        return get_image_format(name)
    except ValueError:
        return None


def get_resample_methods() -> Dict[str, ResampleSpec]:
    with _LOCK:
        return dict(_RESAMPLERS)


def get_resample_spec(name: str) -> ResampleSpec:
    key = _clean_name(name, upper=True)
    with _LOCK:
        spec = _RESAMPLERS.get(key)
    if spec is None:
        available = "、".join(sorted(_RESAMPLERS))
        raise ValueError(f"未知的重采样算法: {name}；当前可用: {available}")
    return spec


def get_preset_targets() -> Dict[str, PresetTargetSpec]:
    with _LOCK:
        return dict(_TARGETS)


def get_preset_sizes() -> Dict[str, PresetSizeSpec]:
    with _LOCK:
        return dict(_SIZES)


def get_aspect_ratios() -> Dict[str, AspectRatioSpec]:
    with _LOCK:
        return dict(_RATIOS)


def get_watermark_positions() -> Dict[str, WatermarkPositionSpec]:
    with _LOCK:
        return dict(_POSITIONS)


def get_watermark_position(name: str) -> WatermarkPositionSpec:
    key = _clean_name(name)
    with _LOCK:
        spec = _POSITIONS.get(key)
    if spec is None:
        available = "、".join(sorted(_POSITIONS))
        raise ValueError(f"未知的水印位置: {name}；当前可用: {available}")
    return spec


def get_registry_summary() -> Dict[str, Any]:
    with _LOCK:
        return {
            "formats": sorted(_FORMATS),
            "resamplers": sorted(_RESAMPLERS),
            "preset_targets": list(_TARGETS),
            "preset_sizes": list(_SIZES),
            "aspect_ratios": list(_RATIOS),
            "watermark_positions": list(_POSITIONS),
            "limits": _LIMITS.__dict__.copy(),
        }


def reset_image_registry() -> None:
    """恢复默认注册项与默认上限（测试隔离用）。"""
    global _LIMITS
    with _LOCK:
        _FORMATS.clear()
        _RESAMPLERS.clear()
        _TARGETS.clear()
        _SIZES.clear()
        _RATIOS.clear()
        _POSITIONS.clear()
        _LIMITS = ImageLimits()
        _register_defaults()


def _position(left: bool, top: bool, *, offset: int = 10):
    """生成位置解析器；left/top 为 False 时靠右/靠下。"""
    def resolve(image_width: int, image_height: int, text_width: int, text_height: int) -> Tuple[int, int]:
        x = offset if left else max(0, image_width - text_width - offset)
        y = offset if top else max(0, image_height - text_height - offset)
        return x, y
    return resolve


def _position_center_x(top: bool):
    def resolve(image_width: int, image_height: int, text_width: int, text_height: int) -> Tuple[int, int]:
        x = max(0, (image_width - text_width) // 2)
        y = 10 if top else max(0, image_height - text_height - 10)
        return x, y
    return resolve


def _position_center_y(left: bool):
    def resolve(image_width: int, image_height: int, text_width: int, text_height: int) -> Tuple[int, int]:
        x = 10 if left else max(0, image_width - text_width - 10)
        y = max(0, (image_height - text_height) // 2)
        return x, y
    return resolve


def _resolve_center(image_width: int, image_height: int, text_width: int, text_height: int) -> Tuple[int, int]:
    return max(0, (image_width - text_width) // 2), max(0, (image_height - text_height) // 2)


def _register_defaults() -> None:
    defaults = [
        ImageFormatSpec("JPG", "JPEG", "jpg", "image/jpeg", lossy=True, supports_metadata=True, description="有损压缩，体积小"),
        ImageFormatSpec("JPEG", "JPEG", "jpg", "image/jpeg", lossy=True, supports_metadata=True, description="JPG 别名"),
        ImageFormatSpec("PNG", "PNG", "png", "image/png", supports_alpha=True, supports_metadata=True, description="无损，支持透明"),
        ImageFormatSpec("GIF", "GIF", "gif", "image/gif", supports_alpha=True, supports_animation=True, description="支持动画"),
        ImageFormatSpec("BMP", "BMP", "bmp", "image/bmp", description="无压缩，体积大"),
        ImageFormatSpec("WEBP", "WEBP", "webp", "image/webp", lossy=True, supports_alpha=True, supports_animation=True, supports_metadata=True, description="现代有损/无损格式"),
    ]
    for spec in defaults:
        register_image_format(spec)

    resamplers = [
        ("LANCZOS", Image.Resampling.LANCZOS, "高质量，适合缩图"),
        ("BILINEAR", Image.Resampling.BILINEAR, "速度与质量平衡"),
        ("NEAREST", Image.Resampling.NEAREST, "最快，像素风"),
        ("BICUBIC", Image.Resampling.BICUBIC, "双三次插值"),
    ]
    for name, value, description in resamplers:
        register_resample_method(ResampleSpec(name, value, description))

    for label, size in (
        ("50 KB", 50 * 1024),
        ("100 KB", 100 * 1024),
        ("200 KB", 200 * 1024),
        ("500 KB", 500 * 1024),
        ("1 MB", 1024 * 1024),
        ("2 MB", 2 * 1024 * 1024),
        ("5 MB", 5 * 1024 * 1024),
    ):
        register_preset_target(PresetTargetSpec(label, size))

    for label, width, height in (
        ("社交媒体头像 (200×200)", 200, 200),
        ("社交媒体帖子 (1080×1080)", 1080, 1080),
        ("手机壁纸 (1080×1920)", 1080, 1920),
        ("电脑壁纸 (1920×1080)", 1920, 1080),
        ("微信头像 (640×640)", 640, 640),
    ):
        register_preset_size(PresetSizeSpec(label, width, height))

    for label, width, height in (
        ("1:1 (正方形)", 1, 1),
        ("16:9 (宽屏)", 16, 9),
        ("4:3 (标准)", 4, 3),
        ("3:2 (照片)", 3, 2),
        ("9:16 (竖屏)", 9, 16),
    ):
        register_aspect_ratio(AspectRatioSpec(label, width, height))

    for name, resolver in (
        ("顶部居左", _position(True, True)),
        ("顶部居中", _position_center_x(True)),
        ("顶部居右", _position(False, True)),
        ("左边居中", _position_center_y(True)),
        ("图片中心", _resolve_center),
        ("右边居中", _position_center_y(False)),
        ("底部居左", _position(True, False)),
        ("底部居中", _position_center_x(False)),
        ("底部居右", _position(False, False)),
    ):
        register_watermark_position(WatermarkPositionSpec(name, resolver))


_register_defaults()
