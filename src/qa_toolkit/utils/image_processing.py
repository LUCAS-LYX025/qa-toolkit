"""图片处理核心能力：格式、尺寸、体积、动画与水印。

所有可扩展选项都来自 ``qa_toolkit.core.image_registry``；本模块保留旧的
``LOSSY_FORMATS`` / ``PIL_FORMAT_MAP`` / ``RESAMPLE_MAP`` 常量作为兼容快照，
但实际校验每次都读注册表，避免运行期注册的新格式被旧快照挡住。
"""
from __future__ import annotations

import io
from typing import Any, Callable, Iterable, Sequence, Tuple

from PIL import Image, ImageDraw, ImageFont

from qa_toolkit.core.image_registry import (
    get_image_format,
    get_image_formats,
    get_image_limits,
    get_resample_methods,
    get_resample_spec,
    get_watermark_position,
)
from qa_toolkit.paths import FONTS_DIR


# 兼容旧调用的只读快照；新注册的项通过注册表实时生效。
_formats = get_image_formats()
_resamplers = get_resample_methods()
LOSSY_FORMATS = {name for name, spec in _formats.items() if spec.lossy}
PIL_FORMAT_MAP = {name: spec.pil_format for name, spec in _formats.items()}
RESAMPLE_MAP = {name: spec.resample for name, spec in _resamplers.items()}


class ImageProcessor:
    """图片处理工具类：格式转换、体积控制、几何变换与水印。"""

    def __init__(self):
        self.available_fonts = self._detect_fonts()

    def _detect_fonts(self) -> list[str]:
        """检测项目内置字体，供页面展示字体来源。"""
        if not FONTS_DIR.exists():
            return []
        return sorted(str(path) for path in FONTS_DIR.glob("*.tt[fc]"))

    @staticmethod
    def _normalize_quality(quality: Any, *, allow_none: bool = False) -> int | None:
        if quality is None and allow_none:
            return None
        if isinstance(quality, bool) or not isinstance(quality, int):
            raise ValueError("图片质量必须是 1-100 的整数")
        if not 1 <= quality <= 100:
            raise ValueError(f"图片质量必须在 1-100 之间，当前值: {quality}")
        return quality

    @staticmethod
    def _normalize_rgb_color(color: Any) -> Tuple[int, int, int]:
        if isinstance(color, bool):
            raise ValueError("颜色必须是 0-255 的 RGB 数值")
        if isinstance(color, int):
            if not 0 <= color <= 255:
                raise ValueError("颜色分量必须在 0-255 之间")
            return color, color, color
        if isinstance(color, (tuple, list)) and len(color) in (3, 4):
            try:
                values = tuple(int(component) for component in color[:3])
            except (TypeError, ValueError) as exc:
                raise ValueError("颜色分量必须是 0-255 的整数") from exc
            if any(not 0 <= component <= 255 for component in values):
                raise ValueError("颜色分量必须在 0-255 之间")
            return values  # type: ignore[return-value]
        raise ValueError("颜色必须是单个灰度值或 3/4 元 RGB(A) 元组")

    @staticmethod
    def _normalize_dimension(value: Any, label: str) -> int:
        if isinstance(value, bool):
            raise ValueError(f"{label}必须是正整数")
        try:
            number = int(value)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"{label}必须是正整数，当前值: {value}") from exc
        if number <= 0:
            raise ValueError(f"{label}必须大于 0，当前值: {value}")
        return number

    def _validate_output_size(self, width: int, height: int) -> None:
        limits = get_image_limits()
        if width > limits.max_output_side or height > limits.max_output_side:
            raise ValueError(
                f"输出边长不能超过 {limits.max_output_side} 像素（当前 {width}×{height}）；"
                "可在配置中调高 max_output_side"
            )
        if width * height > limits.max_image_pixels:
            raise ValueError(
                f"输出像素数超过上限 {limits.max_image_pixels:,}（当前 {width * height:,}）；"
                "请缩小目标尺寸或调高 max_image_pixels"
            )

    def convert_image_for_format(
        self,
        image: Image.Image,
        target_format: str,
        *,
        background_color: Any = (255, 255, 255),
    ) -> Image.Image:
        """按目标格式转换图片模式，未知格式直接报错。"""
        spec = get_image_format(target_format)
        background = self._normalize_rgb_color(background_color)
        img = image.copy()

        has_alpha = img.mode in {"RGBA", "LA"} or (
            img.mode == "P" and "transparency" in img.info
        )
        if not spec.supports_alpha:
            if has_alpha:
                rgba = img.convert("RGBA")
                canvas = Image.new("RGBA", rgba.size, background + (255,))
                img = Image.alpha_composite(canvas, rgba).convert("RGB")
            elif img.mode not in {"RGB", "L", "CMYK"}:
                img = img.convert("RGB")
            return img

        if img.mode == "LA" or has_alpha:
            return img.convert("RGBA")
        return img

    def get_pil_format(self, target_format: str) -> str:
        """获取 Pillow 保存格式。"""
        return get_image_format(target_format).pil_format

    def save_image_to_bytes(
        self,
        image: Image.Image,
        target_format: str,
        quality: Any = 95,
        *,
        preserve_metadata: bool = False,
        background_color: Any = (255, 255, 255),
    ) -> bytes:
        """统一导出图片字节，集中处理质量、元数据与格式校验。"""
        spec = get_image_format(target_format)
        normalized_quality = self._normalize_quality(quality, allow_none=True)

        if self.has_animation(image) and spec.supports_animation:
            frames, duration, loop = self.extract_frames(image)
            return self.save_animated_image(
                frames,
                target_format,
                duration,
                loop,
                quality=quality,
                preserve_metadata=preserve_metadata,
                background_color=background_color,
            )

        converted_image = self.convert_image_for_format(
            image, target_format, background_color=background_color
        )
        output_buffer = io.BytesIO()
        save_kwargs: dict[str, Any] = {}

        if spec.lossy:
            save_kwargs["quality"] = normalized_quality if normalized_quality is not None else 95
            save_kwargs["optimize"] = True
        elif spec.pil_format in {"PNG", "GIF"}:
            save_kwargs["optimize"] = True

        if preserve_metadata and spec.supports_metadata:
            exif_payload = image.info.get("exif")
            if exif_payload:
                save_kwargs["exif"] = exif_payload
            png_info = image.info.get("pnginfo")
            if spec.pil_format == "PNG" and png_info is not None:
                save_kwargs["pnginfo"] = png_info

        converted_image.save(output_buffer, format=spec.pil_format, **save_kwargs)
        return output_buffer.getvalue()

    def get_resample_filter(self, resample_method: str = "LANCZOS"):
        """获取缩放算法；未知算法明确报错。"""
        return get_resample_spec(resample_method or "LANCZOS").resample

    def resize_image(
        self,
        image: Image.Image,
        width: Any,
        height: Any,
        resample_method: str = "LANCZOS",
    ) -> Image.Image:
        """按指定尺寸缩放图片，并校验输出尺寸与像素预算。"""
        target_width = self._normalize_dimension(width, "宽度")
        target_height = self._normalize_dimension(height, "高度")
        self._validate_output_size(target_width, target_height)
        return image.resize(
            (target_width, target_height), self.get_resample_filter(resample_method)
        )

    def flip_image(self, image: Image.Image, direction: str) -> Image.Image:
        """按方向翻转图片。"""
        normalized_direction = str(direction or "").strip()

        if normalized_direction == "上下翻转":
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if normalized_direction == "左右翻转":
            return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if normalized_direction == "同时翻转":
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        raise ValueError(f"不支持的翻转方向: {direction}")

    def rotate_image(
        self,
        image: Image.Image,
        angle: Any,
        fill_color: Any = (255, 255, 255),
        expand: bool = True,
    ) -> Image.Image:
        """旋转图片，正数为顺时针，负数为逆时针。"""
        try:
            normalized_angle = float(angle)
        except (TypeError, ValueError) as exc:
            raise ValueError(f"旋转角度必须是数字，当前值: {angle}") from exc
        if abs(normalized_angle) < 1e-6:
            return image.copy()

        effective_fill = self._normalize_fill_color(fill_color, image.mode)
        return image.rotate(-normalized_angle, expand=bool(expand), fillcolor=effective_fill)

    def normalize_crop_box(
        self,
        crop_box: Sequence[Any],
        image_width: int,
        image_height: int,
    ) -> Tuple[int, int, int, int]:
        """标准化裁剪坐标：先纠正反向坐标，再裁剪到图片范围内。"""
        if image_width <= 0 or image_height <= 0:
            raise ValueError("裁剪目标图片尺寸必须大于 0")

        left, top, right, bottom = crop_box
        left_value = int(round(float(left)))
        right_value = int(round(float(right)))
        top_value = int(round(float(top)))
        bottom_value = int(round(float(bottom)))

        if left_value > right_value:
            left_value, right_value = right_value, left_value
        if top_value > bottom_value:
            top_value, bottom_value = bottom_value, top_value

        clamped_left = max(0, min(left_value, image_width - 1))
        clamped_top = max(0, min(top_value, image_height - 1))
        clamped_right = max(clamped_left + 1, min(right_value, image_width))
        clamped_bottom = max(clamped_top + 1, min(bottom_value, image_height))
        return clamped_left, clamped_top, clamped_right, clamped_bottom

    def crop_image(self, image: Image.Image, crop_box: Sequence[Any]) -> Image.Image:
        """按指定区域裁剪图片。"""
        normalized_crop_box = self.normalize_crop_box(crop_box, image.width, image.height)
        return image.crop(normalized_crop_box)

    @staticmethod
    def has_animation(image: Image.Image) -> bool:
        return getattr(image, "n_frames", 1) > 1

    def extract_frames(
        self, image: Image.Image
    ) -> Tuple[list[Image.Image], int, int]:
        """拆出动画帧，返回 (帧列表, 单帧时长毫秒, 循环次数)。"""
        frame_count = getattr(image, "n_frames", 1)
        duration = int(image.info.get("duration", 100) or 100)
        loop = int(image.info.get("loop", 0) or 0)
        if frame_count <= 1:
            return [image.copy()], duration, loop

        frames = []
        for index in range(frame_count):
            image.seek(index)
            frames.append(image.convert("RGBA"))
        image.seek(0)
        return frames, duration, loop

    def save_animated_image(
        self,
        frames: Iterable[Image.Image],
        target_format: str,
        duration: Any = 100,
        loop: int = 0,
        *,
        quality: Any = 95,
        preserve_metadata: bool = False,
        background_color: Any = (255, 255, 255),
    ) -> bytes:
        """把多帧写到支持动画的格式；不支持动画的格式明确报错。"""
        spec = get_image_format(target_format)
        if not spec.supports_animation:
            raise ValueError(f"{target_format} 不支持动画，无法写入多帧；请改用 GIF 或 WEBP")

        normalized_quality = self._normalize_quality(quality, allow_none=True)
        prepared = [
            self.convert_image_for_format(
                frame, target_format, background_color=background_color
            )
            for frame in frames
        ]
        if not prepared:
            raise ValueError("动画帧列表不能为空")

        if isinstance(duration, (list, tuple)):
            durations = [int(value) for value in duration]
            if len(durations) != len(prepared):
                raise ValueError("逐帧时长数量必须与帧数一致")
        else:
            durations = [int(duration)] * len(prepared)
        if any(value <= 0 for value in durations):
            raise ValueError("动画帧时长必须大于 0 毫秒")

        save_kwargs: dict[str, Any] = {
            "format": spec.pil_format,
            "save_all": True,
            "append_images": prepared[1:],
            "duration": durations,
            "loop": max(0, int(loop)),
        }
        if spec.lossy:
            save_kwargs["quality"] = normalized_quality if normalized_quality is not None else 95
        if spec.pil_format == "GIF":
            save_kwargs["optimize"] = True
        if preserve_metadata and spec.supports_metadata:
            exif_payload = getattr(frames[0], "info", {}).get("exif") if frames else None
            if exif_payload:
                save_kwargs["exif"] = exif_payload

        output_buffer = io.BytesIO()
        prepared[0].save(output_buffer, **save_kwargs)
        return output_buffer.getvalue()

    def pad_image_to_size(self, image_data: bytes, target_bytes: int) -> bytes:
        """测试场景下用填充字节补齐体积，保持图片内容不变。"""
        if target_bytes <= len(image_data):
            return image_data
        return image_data + (b"\0" * (target_bytes - len(image_data)))

    def convert_to_target_filesize(
        self,
        image: Image.Image,
        target_bytes: int,
        output_format: str = "JPG",
        exact_padding: bool = False,
        min_quality: int = 10,
        max_quality: int = 100,
        allow_resize: bool = True,
        resize_step: float = 0.92,
        max_resize_steps: int = 12,
        preserve_metadata: bool = False,
    ) -> dict[str, Any]:
        """将图片压缩到目标体积；动图会逐帧按同一比例处理。"""
        if isinstance(target_bytes, bool) or not isinstance(target_bytes, int) or target_bytes <= 0:
            raise ValueError("目标文件大小必须是大于 0 的整数")

        spec = get_image_format(output_format)
        target_format = spec.name
        low_quality = self._normalize_quality(min_quality)
        high_quality = self._normalize_quality(max_quality)
        if low_quality > high_quality:
            raise ValueError(f"最低质量 ({low_quality}) 不能高于最高质量 ({high_quality})")
        if isinstance(resize_step, bool):
            raise ValueError("缩放步长必须是 0 到 1 之间的小数")
        try:
            step = float(resize_step)
        except (TypeError, ValueError) as exc:
            raise ValueError("缩放步长必须是 0 到 1 之间的小数") from exc
        if not 0 < step < 1:
            raise ValueError(f"缩放步长必须在 0 和 1 之间，当前值: {resize_step}")
        if isinstance(max_resize_steps, bool) or not isinstance(max_resize_steps, int) or max_resize_steps < 0:
            raise ValueError("最大缩放次数必须是不小于 0 的整数")

        animated_frames: list[Image.Image] = []
        animation_duration = 100
        animation_loop = 0
        if spec.supports_animation and self.has_animation(image):
            animated_frames, animation_duration, animation_loop = self.extract_frames(image)
        animated = len(animated_frames) > 1

        def serialize(working_image: Image.Image, quality_value: int | None, scale: float) -> bytes:
            if animated:
                scaled_frames = [self._resize_by_scale(frame, scale) for frame in animated_frames]
                return self.save_animated_image(
                    scaled_frames,
                    target_format,
                    animation_duration,
                    animation_loop,
                    quality=quality_value if quality_value is not None else high_quality,
                    preserve_metadata=preserve_metadata,
                )
            return self.save_image_to_bytes(
                working_image,
                target_format,
                quality=quality_value,
                preserve_metadata=preserve_metadata,
            )

        best_candidate = None
        current_scale = 1.0
        resize_steps = 0

        while True:
            working_image = self._resize_by_scale(image, current_scale)
            candidate = self._find_best_candidate(
                working_image=working_image,
                target_bytes=target_bytes,
                output_format=target_format,
                min_quality=low_quality,
                max_quality=high_quality,
                scale_ratio=current_scale,
                serializer=serialize,
            )

            best_candidate = self._pick_better_candidate(best_candidate, candidate, target_bytes)

            if candidate["size_bytes"] <= target_bytes:
                break

            if not allow_resize or resize_steps >= max_resize_steps:
                break

            next_scale = current_scale * step
            next_image = self._resize_by_scale(image, next_scale)
            if next_image.size == working_image.size:
                break

            current_scale = next_scale
            resize_steps += 1

        result_bytes = best_candidate["data"]
        padding_applied = False

        if exact_padding and len(result_bytes) < target_bytes:
            result_bytes = self.pad_image_to_size(result_bytes, target_bytes)
            padding_applied = True

        target_achieved = len(result_bytes) <= target_bytes
        return {
            "data": result_bytes,
            "image": best_candidate["image"],
            "format": target_format,
            "quality": best_candidate["quality"],
            "size_bytes": len(result_bytes),
            "raw_size_bytes": best_candidate["size_bytes"],
            "scale_ratio": best_candidate["scale_ratio"],
            "padding_applied": padding_applied,
            "target_achieved": target_achieved,
            "animated": animated,
            "frame_count": len(animated_frames) if animated else 1,
            "note": "" if target_achieved else "目标体积过小，已返回可达到的最小体积",
        }

    def convert_to_multiple_filesizes(
        self,
        image: Image.Image,
        targets: Iterable[Any],
        output_format: str = "JPG",
        **kwargs: Any,
    ) -> list[dict[str, Any]]:
        """批量生成多个目标体积的图片。"""
        results = []
        for item in targets:
            if isinstance(item, tuple):
                target_label, target_bytes = item
            else:
                target_label, target_bytes = None, item

            result = self.convert_to_target_filesize(
                image,
                target_bytes=int(target_bytes),
                output_format=output_format,
                **kwargs,
            )
            result["target_bytes"] = int(target_bytes)
            result["target_label"] = target_label
            results.append(result)

        return results

    def _resize_by_scale(self, image: Image.Image, scale_ratio: float) -> Image.Image:
        """按比例缩放图片，scale=1 时返回副本。"""
        if abs(scale_ratio - 1.0) < 1e-6:
            return image.copy()

        new_width = max(1, int(round(image.width * scale_ratio)))
        new_height = max(1, int(round(image.height * scale_ratio)))
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _find_best_candidate(
        self,
        working_image: Image.Image,
        target_bytes: int,
        output_format: str,
        min_quality: int,
        max_quality: int,
        scale_ratio: float,
        serializer: Callable[[Image.Image, int | None, float], bytes],
    ) -> dict[str, Any]:
        """查找当前尺寸下最接近目标体积的导出结果。"""
        spec = get_image_format(output_format)

        def get_candidate(quality_value: int | None) -> dict[str, Any]:
            data = serializer(working_image, quality_value, scale_ratio)
            return {
                "data": data,
                "image": working_image,
                "quality": quality_value,
                "size_bytes": len(data),
                "scale_ratio": scale_ratio,
            }

        if not spec.lossy:
            return get_candidate(None)

        low = min_quality
        high = max_quality
        best_under = None
        best_over = None
        cache: dict[int | None, dict[str, Any]] = {}

        def cached_candidate(quality_value: int | None) -> dict[str, Any]:
            if quality_value not in cache:
                cache[quality_value] = get_candidate(quality_value)
            return cache[quality_value]

        while low <= high:
            mid = (low + high) // 2
            candidate = cached_candidate(mid)

            if candidate["size_bytes"] <= target_bytes:
                if best_under is None or candidate["size_bytes"] > best_under["size_bytes"]:
                    best_under = candidate
                low = mid + 1
            else:
                if best_over is None or candidate["size_bytes"] < best_over["size_bytes"]:
                    best_over = candidate
                high = mid - 1

        quality_window = []
        for quality_value in (low, high):
            for offset in range(-2, 3):
                candidate_quality = quality_value + offset
                if min_quality <= candidate_quality <= max_quality:
                    quality_window.append(candidate_quality)

        for quality_value in sorted(set(quality_window)):
            candidate = cached_candidate(quality_value)
            if candidate["size_bytes"] <= target_bytes:
                if best_under is None or candidate["size_bytes"] > best_under["size_bytes"]:
                    best_under = candidate
            else:
                if best_over is None or candidate["size_bytes"] < best_over["size_bytes"]:
                    best_over = candidate

        return best_under or best_over or cached_candidate(min_quality)

    def _pick_better_candidate(
        self,
        current_best: dict[str, Any] | None,
        new_candidate: dict[str, Any],
        target_bytes: int,
    ) -> dict[str, Any]:
        """优先选不超过目标且最接近目标体积的候选结果。"""
        if current_best is None:
            return new_candidate

        def score(candidate: dict[str, Any]):
            return (
                0 if candidate["size_bytes"] <= target_bytes else 1,
                abs(candidate["size_bytes"] - target_bytes),
                -candidate["size_bytes"],
            )

        return new_candidate if score(new_candidate) < score(current_best) else current_best

    def _normalize_fill_color(self, fill_color: Any, image_mode: str) -> Any:
        """根据图片模式标准化旋转填充色。"""
        if image_mode == "1":
            if isinstance(fill_color, tuple):
                return 255 if any(component > 0 for component in fill_color[:3]) else 0
            return 255 if int(fill_color) > 0 else 0

        if image_mode == "L":
            if isinstance(fill_color, tuple):
                red, green, blue = fill_color[:3]
                return int(round((red + green + blue) / 3))
            return int(fill_color)

        if image_mode in {"LA", "RGBA"}:
            if isinstance(fill_color, tuple):
                if len(fill_color) in (2, 4):
                    return fill_color
                return fill_color[:3] + (255,)
            return (int(fill_color), int(fill_color), int(fill_color), 255)

        if isinstance(fill_color, tuple):
            return fill_color[:3]
        return (int(fill_color), int(fill_color), int(fill_color))

    def add_watermark(
        self,
        image: Image.Image,
        text: str,
        position: str,
        font_size: int,
        color: Any,
        opacity: float,
        rotation: float,
        font_file: Any = None,
    ) -> Image.Image:
        """添加水印：参数严格校验，字体不落盘，失败给中文诊断。"""
        try:
            if not str(text or "").strip():
                raise ValueError("水印文本不能为空")
            normalized_size = self._normalize_dimension(font_size, "字体大小")
            limits = get_image_limits()
            if normalized_size > 512:
                raise ValueError("字体大小不能超过 512 像素")
            if isinstance(opacity, bool) or not isinstance(opacity, (int, float)):
                raise ValueError("透明度必须是 0-1 的数字")
            normalized_opacity = float(opacity)
            if not 0 <= normalized_opacity <= 1:
                raise ValueError(f"透明度必须在 0-1 之间，当前值: {opacity}")
            try:
                normalized_rotation = float(rotation)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"旋转角度必须是数字，当前值: {rotation}") from exc
            rgb = self._normalize_rgb_color(color)
            position_spec = get_watermark_position(position)

            watermark = Image.new("RGBA", image.size, (0, 0, 0, 0))
            image_rgba = image.convert("RGBA")
            draw = ImageDraw.Draw(watermark)

            font = None
            if font_file is not None:
                payload = font_file.getvalue() if hasattr(font_file, "getvalue") else bytes(font_file)
                if len(payload) > limits.max_font_bytes:
                    raise ValueError(
                        f"字体文件不能超过 {limits.max_font_bytes // 1024 // 1024} MB"
                    )
                if not payload:
                    raise ValueError("字体文件为空")
                try:
                    font = ImageFont.truetype(io.BytesIO(payload), normalized_size)
                except Exception as exc:
                    raise ValueError(f"自定义字体加载失败，请确认是有效的 ttf/ttc/otf 文件: {exc}") from exc

            if font is None:
                font = self._get_available_font(normalized_size) or ImageFont.load_default()

            try:
                bbox = draw.textbbox((0, 0), text, font=font)
                text_width = max(1, bbox[2] - bbox[0])
                text_height = max(1, bbox[3] - bbox[1])
            except Exception:
                text_width = max(1, len(text) * normalized_size // 2)
                text_height = normalized_size

            x, y = position_spec.resolve(image.width, image.height, text_width, text_height)
            alpha = int(255 * normalized_opacity)
            fill_color = rgb + (alpha,)
            shadow_color = (0, 0, 0, alpha // 2)
            draw.text((x + 1, y + 1), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill_color)

            if abs(normalized_rotation) > 1e-6:
                watermark = watermark.rotate(
                    normalized_rotation,
                    expand=False,
                    resample=Image.Resampling.BICUBIC,
                    center=(x + text_width // 2, y + text_height // 2),
                )

            result = Image.alpha_composite(image_rgba, watermark)
            if image.mode != "RGBA":
                result = result.convert(image.mode)
            return result

        except RuntimeError:
            raise
        except Exception as exc:
            # 统一对页面暴露 RuntimeError，保证任何失败都带“添加水印失败”前缀。
            raise RuntimeError(f"添加水印失败: {exc}") from exc

    def _get_available_font(self, font_size: int):
        """获取可用的字体，优先项目内置字体与常见中文字体。"""
        import os
        import sys

        font_paths: list[str] = []

        if sys.platform == "win32":
            windir = os.environ.get("WINDIR", "C:\\Windows")
            font_paths.extend([
                os.path.join(windir, "Fonts", "simhei.ttf"),
                os.path.join(windir, "Fonts", "simsun.ttc"),
                os.path.join(windir, "Fonts", "msyh.ttc"),
                os.path.join(windir, "Fonts", "msyhbd.ttc"),
            ])
        elif sys.platform.startswith("linux"):
            font_paths.extend([
                str(FONTS_DIR / "PingFang.ttc"),
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/arphic/ukai.ttc",
                "/usr/share/fonts/truetype/arphic/uming.ttc",
                "/usr/share/fonts/truetype/ttf-wps-fonts/simfang.ttf",
                "/usr/share/fonts/truetype/ttf-wps-fonts/simhei.ttf",
                "/usr/share/fonts/truetype/ttf-wps-fonts/simkai.ttf",
                "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",
                "/usr/local/share/fonts/wqy-microhei.ttc",
                os.path.expanduser("~/.local/share/fonts/wqy-microhei.ttc"),
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            ])
        elif sys.platform == "darwin":
            font_paths.extend([
                str(FONTS_DIR / "PingFang.ttc"),
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
            ])

        for font_path in [*font_paths, "arial.ttf"]:
            if font_path != "arial.ttf" and not os.path.exists(font_path):
                continue
            try:
                return ImageFont.truetype(font_path, font_size)
            except Exception:
                continue
        return None
