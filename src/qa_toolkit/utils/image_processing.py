import io

from PIL import Image

from qa_toolkit.paths import FONTS_DIR


class ImageProcessor:
    """
    图片处理工具类
    提供格式转换、水印添加等功能
    """

    LOSSY_FORMATS = {"JPG", "JPEG", "WEBP"}
    PIL_FORMAT_MAP = {
        "JPG": "JPEG",
        "JPEG": "JPEG",
        "PNG": "PNG",
        "GIF": "GIF",
        "BMP": "BMP",
        "WEBP": "WEBP",
    }
    RESAMPLE_MAP = {
        "LANCZOS": Image.Resampling.LANCZOS,
        "BILINEAR": Image.Resampling.BILINEAR,
        "NEAREST": Image.Resampling.NEAREST,
        "BICUBIC": Image.Resampling.BICUBIC,
    }

    def __init__(self):
        self.available_fonts = self._detect_fonts()

    def _detect_fonts(self):
        """检测可用的字体"""
        fonts = []
        # 这里可以添加字体检测逻辑
        return fonts

    def convert_image_for_format(self, image, target_format):
        """根据目标格式转换图片模式"""
        img = image.copy()
        target_format = target_format.upper()

        if target_format in ["JPG", "JPEG", "BMP"]:
            # JPG和BMP不支持透明通道，需要转换为RGB
            if img.mode in ('RGBA', 'LA', 'P'):
                # 创建白色背景
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                # 将原图粘贴到背景上
                background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                img = background
            elif img.mode not in ('RGB', 'L'):
                img = img.convert('RGB')
        elif target_format == "PNG":
            # PNG支持透明通道，保持原模式或转换为RGBA
            if img.mode in ('P', 'LA'):
                img = img.convert('RGBA')
        elif target_format == "WEBP":
            # WEBP支持透明通道
            if img.mode in ('P', 'LA'):
                img = img.convert('RGBA')

        return img

    def get_pil_format(self, target_format):
        """获取 Pillow 保存格式。"""
        normalized_format = target_format.upper()
        if normalized_format not in self.PIL_FORMAT_MAP:
            raise ValueError(f"不支持的图片格式: {target_format}")
        return self.PIL_FORMAT_MAP[normalized_format]

    def save_image_to_bytes(self, image, target_format, quality=95):
        """统一导出图片字节，避免页面层重复处理保存参数。"""
        pil_format = self.get_pil_format(target_format)
        converted_image = self.convert_image_for_format(image, target_format)
        output_buffer = io.BytesIO()
        save_kwargs = {}

        if pil_format == "JPEG":
            save_kwargs = {"quality": int(quality), "optimize": True}
        elif pil_format == "WEBP":
            save_kwargs = {"quality": int(quality), "optimize": True}
        elif pil_format == "PNG":
            save_kwargs = {"optimize": True}
        elif pil_format == "GIF":
            save_kwargs = {"optimize": True}

        converted_image.save(output_buffer, format=pil_format, **save_kwargs)
        return output_buffer.getvalue()

    def get_resample_filter(self, resample_method="LANCZOS"):
        """获取缩放算法，默认返回高质量 LANCZOS。"""
        normalized_method = str(resample_method or "LANCZOS").upper()
        return self.RESAMPLE_MAP.get(normalized_method, Image.Resampling.LANCZOS)

    def resize_image(self, image, width, height, resample_method="LANCZOS"):
        """按指定尺寸缩放图片。"""
        target_width = max(1, int(width))
        target_height = max(1, int(height))
        return image.resize((target_width, target_height), self.get_resample_filter(resample_method))

    def flip_image(self, image, direction):
        """按方向翻转图片。"""
        normalized_direction = str(direction or "").strip()

        if normalized_direction == "上下翻转":
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM)
        if normalized_direction == "左右翻转":
            return image.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        if normalized_direction == "同时翻转":
            return image.transpose(Image.Transpose.FLIP_TOP_BOTTOM).transpose(Image.Transpose.FLIP_LEFT_RIGHT)
        raise ValueError(f"不支持的翻转方向: {direction}")

    def rotate_image(self, image, angle, fill_color=(255, 255, 255), expand=True):
        """旋转图片，正数为顺时针，负数为逆时针。"""
        normalized_angle = float(angle)
        if abs(normalized_angle) < 1e-6:
            return image.copy()

        effective_fill = self._normalize_fill_color(fill_color, image.mode)
        return image.rotate(-normalized_angle, expand=bool(expand), fillcolor=effective_fill)

    def normalize_crop_box(self, crop_box, image_width, image_height):
        """标准化裁剪坐标，确保不越界。"""
        left, top, right, bottom = crop_box
        left = max(0, min(int(round(left)), image_width - 1))
        top = max(0, min(int(round(top)), image_height - 1))
        right = max(left + 1, min(int(round(right)), image_width))
        bottom = max(top + 1, min(int(round(bottom)), image_height))
        return left, top, right, bottom

    def crop_image(self, image, crop_box):
        """按指定区域裁剪图片。"""
        normalized_crop_box = self.normalize_crop_box(crop_box, image.width, image.height)
        return image.crop(normalized_crop_box)

    def pad_image_to_size(self, image_data, target_bytes):
        """测试场景下用填充字节补齐体积，保持图片内容不变。"""
        if target_bytes <= len(image_data):
            return image_data
        return image_data + (b"\0" * (target_bytes - len(image_data)))

    def convert_to_target_filesize(
            self,
            image,
            target_bytes,
            output_format="JPG",
            exact_padding=False,
            min_quality=10,
            max_quality=100,
            allow_resize=True,
            resize_step=0.92,
            max_resize_steps=12,
    ):
        """
        将图片尽量压缩到目标体积。

        - 对 JPG / WEBP 优先搜索质量参数
        - 如果最低质量仍过大，则逐步缩小尺寸
        - 若启用 exact_padding，在结果小于目标时补齐到精确字节数
        """
        if target_bytes <= 0:
            raise ValueError("目标文件大小必须大于 0")

        target_format = output_format.upper()
        best_candidate = None
        current_scale = 1.0
        resize_steps = 0

        while True:
            working_image = self._resize_by_scale(image, current_scale)
            candidate = self._find_best_candidate(
                working_image=working_image,
                target_bytes=target_bytes,
                output_format=target_format,
                min_quality=min_quality,
                max_quality=max_quality,
                scale_ratio=current_scale,
            )

            best_candidate = self._pick_better_candidate(best_candidate, candidate, target_bytes)

            if candidate["size_bytes"] <= target_bytes:
                break

            if not allow_resize or resize_steps >= max_resize_steps:
                break

            next_scale = current_scale * resize_step
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

        return {
            "data": result_bytes,
            "image": best_candidate["image"],
            "format": target_format,
            "quality": best_candidate["quality"],
            "size_bytes": len(result_bytes),
            "raw_size_bytes": best_candidate["size_bytes"],
            "scale_ratio": best_candidate["scale_ratio"],
            "padding_applied": padding_applied,
        }

    def convert_to_multiple_filesizes(self, image, targets, output_format="JPG", **kwargs):
        """
        批量生成多个目标体积的图片。

        targets 支持:
        - [102400, 204800]
        - [("100 KB", 102400), ("200 KB", 204800)]
        """
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

    def _resize_by_scale(self, image, scale_ratio):
        """按比例缩放图片，scale=1 时返回副本。"""
        if abs(scale_ratio - 1.0) < 1e-6:
            return image.copy()

        new_width = max(1, int(round(image.width * scale_ratio)))
        new_height = max(1, int(round(image.height * scale_ratio)))
        return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

    def _find_best_candidate(self, working_image, target_bytes, output_format, min_quality, max_quality,
                             scale_ratio):
        """查找当前尺寸下最接近目标体积的导出结果。"""
        if output_format not in self.LOSSY_FORMATS:
            data = self.save_image_to_bytes(working_image, output_format)
            return {
                "data": data,
                "image": working_image,
                "quality": None,
                "size_bytes": len(data),
                "scale_ratio": scale_ratio,
            }

        low = min_quality
        high = max_quality
        best_under = None
        best_over = None
        cache = {}

        def get_candidate(quality_value):
            if quality_value not in cache:
                image_data = self.save_image_to_bytes(working_image, output_format, quality=quality_value)
                cache[quality_value] = {
                    "data": image_data,
                    "image": working_image,
                    "quality": quality_value,
                    "size_bytes": len(image_data),
                    "scale_ratio": scale_ratio,
                }
            return cache[quality_value]

        while low <= high:
            mid = (low + high) // 2
            candidate = get_candidate(mid)

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
            candidate = get_candidate(quality_value)
            if candidate["size_bytes"] <= target_bytes:
                if best_under is None or candidate["size_bytes"] > best_under["size_bytes"]:
                    best_under = candidate
            else:
                if best_over is None or candidate["size_bytes"] < best_over["size_bytes"]:
                    best_over = candidate

        return best_under or best_over or get_candidate(min_quality)

    def _pick_better_candidate(self, current_best, new_candidate, target_bytes):
        """优先选不超过目标且最接近目标体积的候选结果。"""
        if current_best is None:
            return new_candidate

        def score(candidate):
            return (
                0 if candidate["size_bytes"] <= target_bytes else 1,
                abs(candidate["size_bytes"] - target_bytes),
                -candidate["size_bytes"],
            )

        if score(new_candidate) < score(current_best):
            return new_candidate
        return current_best

    def _normalize_fill_color(self, fill_color, image_mode):
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
                if len(fill_color) == 4:
                    return fill_color
                if len(fill_color) == 2:
                    return fill_color
                return fill_color[:3] + (255,)
            return (int(fill_color), int(fill_color), int(fill_color), 255)

        if isinstance(fill_color, tuple):
            return fill_color[:3]
        return (int(fill_color), int(fill_color), int(fill_color))

    def add_watermark(self, image, text, position, font_size, color, opacity, rotation, font_file=None):
        """添加水印 - 增强版，支持中文字体"""
        try:
            from PIL import ImageDraw, ImageFont
            import os

            # 创建水印图层
            if image.mode != 'RGBA':
                watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
                image_rgba = image.convert('RGBA')
            else:
                watermark = Image.new('RGBA', image.size, (0, 0, 0, 0))
                image_rgba = image

            draw = ImageDraw.Draw(watermark)

            # 字体处理逻辑
            font = None

            # 1. 如果用户上传了字体文件
            if font_file is not None:
                try:
                    # 保存上传的字体文件到临时位置
                    import tempfile
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.ttf') as tmp_file:
                        tmp_file.write(font_file.getvalue())
                        font_path = tmp_file.name

                    font = ImageFont.truetype(font_path, font_size)
                    # 清理临时文件
                    os.unlink(font_path)
                except Exception:
                    pass

            # 2. 自动检测系统字体
            if font is None:
                font = self._get_available_font(font_size)

            # 3. 如果还是没找到字体，使用默认字体
            if font is None:
                try:
                    font = ImageFont.load_default()
                except:
                    pass

            # 获取文字尺寸 - 兼容新版和旧版 PIL
            try:
                # 方法1: 使用 textbbox (PIL 9.2.0+)
                if hasattr(draw, 'textbbox'):
                    bbox = draw.textbbox((0, 0), text, font=font)
                    text_width = bbox[2] - bbox[0]
                    text_height = bbox[3] - bbox[1]
                # 方法2: 使用 textlength 和 getsize (较新版本)
                elif hasattr(draw, 'textlength'):
                    text_width = int(draw.textlength(text, font=font))
                    # 估算高度
                    text_height = font_size
                # 方法3: 使用 getsize (旧版本)
                elif hasattr(font, 'getsize'):
                    text_width, text_height = font.getsize(text)
                # 方法4: 最后回退方案
                else:
                    text_width = len(text) * font_size // 2
                    text_height = font_size
            except:
                # 如果所有方法都失败，使用估计值
                text_width = len(text) * font_size // 2
                text_height = font_size

            # 计算位置
            positions = {
                "顶部居左": (10, 10),
                "顶部居中": ((image.width - text_width) // 2, 10),
                "顶部居右": (image.width - text_width - 10, 10),
                "左边居中": (10, (image.height - text_height) // 2),
                "图片中心": ((image.width - text_width) // 2, (image.height - text_height) // 2),
                "右边居中": (image.width - text_width - 10, (image.height - text_height) // 2),
                "底部居左": (10, image.height - text_height - 10),
                "底部居中": ((image.width - text_width) // 2, image.height - text_height - 10),
                "底部居右": (image.width - text_width - 10, image.height - text_height - 10)
            }

            x, y = positions.get(position, (10, 10))

            # 绘制水印（带透明度）
            alpha = int(255 * opacity)
            fill_color = color + (alpha,)

            # 添加文字阴影效果，提高可读性
            shadow_color = (0, 0, 0, alpha // 2)
            draw.text((x + 1, y + 1), text, font=font, fill=shadow_color)
            draw.text((x, y), text, font=font, fill=fill_color)

            # 旋转水印
            if rotation != 0:
                watermark = watermark.rotate(rotation, expand=False, resample=Image.Resampling.BICUBIC,
                                             center=(x + text_width // 2, y + text_height // 2))

            # 合并图片和水印
            result = Image.alpha_composite(image_rgba, watermark)

            # 如果原图不是RGBA，转换回去
            if image.mode != 'RGBA':
                result = result.convert(image.mode)

            return result

        except Exception:
            return image

    def _get_available_font(self, font_size):
        """获取可用的字体"""
        from PIL import ImageFont
        import sys
        import os

        # 常见的中文字体路径
        font_paths = []

        # Windows 字体路径
        if sys.platform == "win32":
            windir = os.environ.get("WINDIR", "C:\\Windows")
            font_paths.extend([
                os.path.join(windir, "Fonts", "simhei.ttf"),  # 黑体
                os.path.join(windir, "Fonts", "simsun.ttc"),  # 宋体
                os.path.join(windir, "Fonts", "msyh.ttc"),  # 微软雅黑
                os.path.join(windir, "Fonts", "msyhbd.ttc"),  # 微软雅黑粗体
            ])

        # Linux 字体路径
        elif sys.platform.startswith("linux"):
            font_paths.extend([
                str(FONTS_DIR / "PingFang.ttc"),
                # 中文相关字体
                "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",  # Android 字体
                "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",  # 文泉驿微米黑
                "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",  # 文泉驿正黑
                "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Google Noto 字体

                # Ubuntu/Debian 常见路径
                "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
                "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
                "/usr/share/fonts/truetype/freefont/FreeSans.ttf",

                # RedHat/CentOS/Fedora 常见路径
                "/usr/share/fonts/dejavu/DejaVuSans.ttf",
                "/usr/share/fonts/liberation-sans/LiberationSans-Regular.ttf",

                # 其他可能的中文字体路径
                "/usr/share/fonts/truetype/arphic/ukai.ttc",  # AR PL 楷体
                "/usr/share/fonts/truetype/arphic/uming.ttc",  # AR PL 明体
                "/usr/share/fonts/truetype/ttf-wps-fonts/simfang.ttf",  # WPS 仿宋
                "/usr/share/fonts/truetype/ttf-wps-fonts/simhei.ttf",  # WPS 黑体
                "/usr/share/fonts/truetype/ttf-wps-fonts/simkai.ttf",  # WPS 楷体

                # Noto 字体其他可能位置
                "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
                "/usr/share/fonts/noto/NotoSansCJK-Regular.ttc",

                # 用户安装字体
                "/usr/local/share/fonts/wqy-microhei.ttc",
                os.path.expanduser("~/.local/share/fonts/wqy-microhei.ttc"),

                # 容器/云环境常见字体
                "/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf",
            ])

        # macOS 字体路径
        elif sys.platform == "darwin":
            font_paths.extend([
                "/System/Library/Fonts/PingFang.ttc",
                "/System/Library/Fonts/STHeiti Light.ttc",
                "/System/Library/Fonts/Helvetica.ttc",
                "/Library/Fonts/Arial.ttf",
            ])

        # 尝试每个字体路径
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, font_size)
                except Exception:
                    continue

        # 尝试项目自定义字体
        custom_font_path = str(FONTS_DIR / "PingFang.ttc")

        if os.path.exists(custom_font_path):
            try:
                return ImageFont.truetype(custom_font_path, font_size)
            except Exception:
                pass

        # 最终回退方案
        try:
            return ImageFont.truetype("arial.ttf", font_size)
        except:
            try:
                return ImageFont.load_default()
            except:
                return None
