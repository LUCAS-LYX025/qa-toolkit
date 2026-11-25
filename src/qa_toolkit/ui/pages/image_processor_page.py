from __future__ import annotations

import csv
import hashlib
import io
import re
import warnings
import zipfile
from pathlib import Path

from PIL import Image, ImageOps
import streamlit as st

try:
    from streamlit_cropper import st_cropper

    INTERACTIVE_CROP_AVAILABLE = True
except Exception:
    st_cropper = None
    INTERACTIVE_CROP_AVAILABLE = False

from qa_toolkit.core.image_registry import (
    find_image_format,
    get_aspect_ratios,
    get_image_formats,
    get_image_limits,
    get_preset_sizes,
    get_preset_targets,
    get_registry_summary,
    get_resample_methods,
    get_watermark_positions,
)
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button
from qa_toolkit.ui.components.status_feedback import render_error_feedback, render_success_feedback, render_warning_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_empty_state, render_tool_page_hero, render_tool_tips
from qa_toolkit.utils.image_processing import ImageProcessor


# 兼容旧导入的只读快照；实际选项每次从注册表读取，新增注册项自动出现在页面。
PRESET_TARGETS = {label: spec.bytes_ for label, spec in get_preset_targets().items()}
RESAMPLE_OPTIONS = {name: name for name in get_resample_methods()}
ASPECT_RATIO_OPTIONS = {
    label: (spec.width, spec.height) for label, spec in get_aspect_ratios().items()
}
FILE_EXTENSION_MAP = {
    name: spec.extension for name, spec in get_image_formats().items()
}


def _load_image(uploaded_file) -> Image.Image:
    """加载上传图片：限制体积/像素、应用 EXIF 方向、保留动画帧。"""
    payload = uploaded_file.getvalue()
    limits = get_image_limits()

    if len(payload) > limits.max_upload_bytes:
        raise ValueError(
            f"图片体积 {len(payload) / 1024 / 1024:.1f} MB 超过上限 "
            f"{limits.max_upload_bytes / 1024 / 1024:.1f} MB"
        )

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            image = Image.open(io.BytesIO(payload))
            declared_pixels = image.width * image.height
            if declared_pixels > limits.max_image_pixels:
                raise ValueError(
                    f"图片像素数 {declared_pixels:,} 超过上限 {limits.max_image_pixels:,}，请缩小后上传"
                )
            allowed_formats = {spec.pil_format for spec in get_image_formats().values()}
            if image.format not in allowed_formats:
                raise ValueError(
                    f"不支持的图片格式: {image.format or '未知'}；允许: {'、'.join(sorted(allowed_formats))}"
                )
            image.load()
    except ValueError:
        raise
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise ValueError(f"图片像素过大，已阻止加载以保护服务稳定性: {exc}") from exc
    except Exception as exc:
        raise ValueError(f"图片读取失败: {exc}") from exc

    # GIF/WEBP 动画需要保留多帧，exif_transpose 会把它拍平成首帧。
    if getattr(image, "n_frames", 1) > 1:
        image.seek(0)
        return image

    transposed = ImageOps.exif_transpose(image)
    transposed.load()
    return transposed


def _hex_to_rgb(color_value: str) -> tuple[int, int, int]:
    cleaned = str(color_value or "").lstrip("#")
    if len(cleaned) != 6:
        raise ValueError("颜色值必须是 #RRGGBB 格式")
    return tuple(int(cleaned[index:index + 2], 16) for index in (0, 2, 4))  # type: ignore[return-value]


def _format_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / 1024 / 1024:.2f} MB"
    return f"{num_bytes / 1024:.2f} KB"


def _format_dimensions(image: Image.Image) -> str:
    return f"{image.width} × {image.height}"


def _is_animated(image: Image.Image) -> bool:
    return getattr(image, "n_frames", 1) > 1


def _safe_download_stem(stem_name: str) -> str:
    """清洗上传文件名，避免下载名/ZIP 条目带路径或系统保留字符。"""
    raw = str(stem_name or "").strip()
    cleaned = re.sub(r'[\x00-\x1f<>:"/\\|?*]', "_", raw)
    cleaned = cleaned.strip(" .") or "uploaded-image"
    return cleaned[:80]


def _safe_csv_cell(value) -> str:
    text = str(value if value is not None else "")
    if text.startswith(("=", "+", "-", "@")):
        return "'" + text
    return text


def _build_manifest_bytes(results: list[dict]) -> bytes:
    """生成带 BOM 的 manifest，脱离页面也能追溯批量结果。"""
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["目标档位", "目标字节", "实际字节", "缩放比例", "是否达标", "备注"])
    for item in results:
        writer.writerow([
            _safe_csv_cell(item.get("target_label") or item.get("target_bytes")),
            _safe_csv_cell(item.get("target_bytes")),
            _safe_csv_cell(item.get("size_bytes")),
            _safe_csv_cell(round(float(item.get("scale_ratio", 1.0)), 3)),
            _safe_csv_cell("是" if item.get("target_achieved") else "否"),
            _safe_csv_cell(item.get("note", "")),
        ])
    return ("\ufeff" + buffer.getvalue()).encode("utf-8")


def _apply_transform_and_export(
    processor: ImageProcessor,
    image: Image.Image,
    transform,
    target_format: str,
    *,
    quality: int,
    preserve_metadata: bool,
    background_color: tuple[int, int, int] = (255, 255, 255),
):
    """对静态图/动画帧执行同一变换，并给出准确的动画处理提示。"""
    frames, duration, loop = processor.extract_frames(image)
    spec = find_image_format(target_format)

    if len(frames) > 1 and spec is not None and spec.supports_animation:
        transformed = [transform(frame) for frame in frames]
        data = processor.save_animated_image(
            transformed,
            target_format,
            duration,
            loop,
            quality=quality,
            preserve_metadata=preserve_metadata,
            background_color=background_color,
        )
        note = "（动画已逐帧处理，预览显示第一帧）"
    else:
        transformed = [transform(frames[0])]
        data = processor.save_image_to_bytes(
            transformed[0],
            target_format,
            quality=quality,
            preserve_metadata=preserve_metadata,
            background_color=background_color,
        )
        note = "（源图含多帧，该格式不支持动画，仅处理首帧）" if len(frames) > 1 else ""

    return transformed[0], data, note


def _get_download_extension(target_format: str) -> str:
    spec = find_image_format(target_format)
    return spec.extension if spec else str(target_format).lower()


def _get_download_mime(target_format: str) -> str:
    spec = find_image_format(target_format)
    return spec.mime if spec else f"image/{str(target_format).lower()}"


def _resolve_quality(target_format: str, quality: int, compression_mode: str) -> int:
    spec = find_image_format(target_format)
    if spec is None or not spec.lossy:
        return int(quality)

    mode_offsets = {
        "质量优先": 0,
        "平衡模式": -15,
        "体积优先": -30,
    }
    resolved_quality = int(quality) + mode_offsets.get(compression_mode, 0)
    return max(1, min(100, resolved_quality))


def _render_source_summary(image: Image.Image, uploaded_file) -> None:
    source_size = getattr(uploaded_file, "size", len(uploaded_file.getvalue()))
    metric_cols = st.columns(4)
    metric_cols[0].metric("宽度", image.width)
    metric_cols[1].metric("高度", image.height)
    metric_cols[2].metric("模式", image.mode)
    metric_cols[3].metric("原图大小", _format_size(source_size))
    if _is_animated(image):
        st.caption(f"检测到动画：共 {getattr(image, 'n_frames', 1)} 帧，单帧时长约 {image.info.get('duration', 100)} 毫秒。")


def _render_size_inputs(prefix: str, default_width: int, default_height: int) -> tuple[int, int]:
    limits = get_image_limits()
    max_side = limits.max_output_side
    computed_key = f"{prefix}_computed_dimensions"
    if computed_key not in st.session_state:
        st.session_state[computed_key] = (default_width, default_height)

    keep_ratio = st.checkbox("保持原始宽高比", value=True, key=f"{prefix}_keep_ratio")
    if keep_ratio:
        anchor = st.radio("按哪一边调整", ["按宽度", "按高度"], horizontal=True, key=f"{prefix}_anchor")
        previous_width, previous_height = st.session_state[computed_key]
        if anchor == "按宽度":
            suggested_width = min(max_side, max(1, previous_width))
            new_width = int(st.number_input(
                "宽度(像素)", min_value=1, max_value=max_side,
                value=suggested_width, step=1, key=f"{prefix}_width",
            ))
            new_height = max(1, int(round(new_width * default_height / max(1, default_width))))
            st.caption(f"高度自动计算为 {new_height} 像素")
        else:
            suggested_height = min(max_side, max(1, previous_height))
            new_height = int(st.number_input(
                "高度(像素)", min_value=1, max_value=max_side,
                value=suggested_height, step=1, key=f"{prefix}_height",
            ))
            new_width = max(1, int(round(new_height * default_width / max(1, default_height))))
            st.caption(f"宽度自动计算为 {new_width} 像素")
        st.session_state[computed_key] = (new_width, new_height)
    else:
        previous_width, previous_height = st.session_state[computed_key]
        width_col, height_col = st.columns(2)
        with width_col:
            new_width = int(st.number_input(
                "宽度(像素)", min_value=1, max_value=max_side,
                value=min(max_side, max(1, previous_width)), step=1, key=f"{prefix}_width",
            ))
        with height_col:
            new_height = int(st.number_input(
                "高度(像素)", min_value=1, max_value=max_side,
                value=min(max_side, max(1, previous_height)), step=1, key=f"{prefix}_height",
            ))

    st.caption(f"输出尺寸: {new_width} × {new_height} 像素（单边上限 {max_side}）")
    return new_width, new_height


def _get_crop_metrics(crop_box: tuple[int, int, int, int], image_width: int, image_height: int) -> tuple[int, int, float]:
    left, top, right, bottom = crop_box
    crop_width = right - left
    crop_height = bottom - top
    usage_ratio = crop_width * crop_height / max(1, image_width * image_height) * 100
    return crop_width, crop_height, usage_ratio


def _build_upload_signature(uploaded_file) -> str:
    payload = uploaded_file.getvalue()
    digest = hashlib.sha1(payload).hexdigest()[:12]
    stem_name = Path(getattr(uploaded_file, "name", "uploaded-image")).stem or "uploaded-image"
    size = getattr(uploaded_file, "size", len(payload))
    return f"{stem_name}-{size}-{digest}"


def _build_default_crop_box(
    processor: ImageProcessor,
    image_width: int,
    image_height: int,
    aspect_ratio: tuple[int, int] | None,
) -> tuple[int, int, int, int]:
    inset_ratio = 0.08
    max_crop_width = max(1, int(round(image_width * (1 - inset_ratio * 2))))
    max_crop_height = max(1, int(round(image_height * (1 - inset_ratio * 2))))

    if aspect_ratio:
        target_ratio = aspect_ratio[0] / aspect_ratio[1]
        if max_crop_width / max_crop_height > target_ratio:
            crop_height = max_crop_height
            crop_width = max(1, int(round(crop_height * target_ratio)))
        else:
            crop_width = max_crop_width
            crop_height = max(1, int(round(crop_width / target_ratio)))
    else:
        crop_width = max_crop_width
        crop_height = max_crop_height

    left = max(0, (image_width - crop_width) // 2)
    top = max(0, (image_height - crop_height) // 2)
    return processor.normalize_crop_box((left, top, left + crop_width, top + crop_height), image_width, image_height)


def _to_cropper_default_coords(
    processor: ImageProcessor,
    crop_box: tuple[int, int, int, int],
    image_width: int,
    image_height: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = processor.normalize_crop_box(crop_box, image_width, image_height)
    return left, right, top, bottom


def _render_cropper_style() -> None:
    st.markdown(
        """
        <style>
        .qa-image-cropper-guide {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            margin-bottom: 14px;
            padding: 14px 16px;
            border-radius: 16px;
            border: 1px solid rgba(255, 122, 24, 0.28);
            background: linear-gradient(135deg, rgba(255, 247, 237, 0.96) 0%, rgba(255, 255, 255, 0.98) 100%);
            box-shadow: 0 12px 24px rgba(15, 23, 42, 0.06);
        }
        .qa-image-cropper-guide__dot {
            width: 12px;
            height: 12px;
            margin-top: 5px;
            flex: 0 0 12px;
            border-radius: 999px;
            background: linear-gradient(135deg, #ff7a18 0%, #ffb347 100%);
            box-shadow: 0 0 0 4px rgba(255, 122, 24, 0.16);
        }
        .qa-image-cropper-guide__title {
            color: #8a3b06;
            font-size: 1rem;
            font-weight: 800;
            line-height: 1.45;
            margin-bottom: 2px;
        }
        .qa-image-cropper-guide__desc {
            color: #92400e;
            font-size: 0.93rem;
            font-weight: 600;
            line-height: 1.6;
        }
        .qa-image-cropper-metrics {
            padding: 16px 18px;
            border-radius: 18px;
            border: 1px solid rgba(15, 76, 129, 0.12);
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.98) 0%, rgba(240, 249, 255, 0.95) 100%);
            box-shadow: 0 18px 32px rgba(15, 23, 42, 0.07);
            margin-bottom: 12px;
        }
        .qa-image-cropper-metrics__eyebrow {
            color: #0f4c81;
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: 0.08em;
            text-transform: uppercase;
            margin-bottom: 6px;
        }
        .qa-image-cropper-metrics__size {
            color: #10253a;
            font-size: 1.45rem;
            font-weight: 900;
            line-height: 1.15;
            margin-bottom: 8px;
        }
        .qa-image-cropper-metrics__meta {
            color: #365168;
            font-size: 0.92rem;
            font-weight: 700;
            line-height: 1.65;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_crop_metrics_card(
    crop_box: tuple[int, int, int, int],
    original_width: int,
    original_height: int,
) -> None:
    crop_width, crop_height, usage_ratio = _get_crop_metrics(crop_box, original_width, original_height)
    left, top, right, bottom = crop_box
    st.markdown(
        f"""
        <div class="qa-image-cropper-metrics">
            <div class="qa-image-cropper-metrics__eyebrow">当前选区</div>
            <div class="qa-image-cropper-metrics__size">{crop_width} × {crop_height} px</div>
            <div class="qa-image-cropper-metrics__meta">起点 ({left}, {top}) · 终点 ({right}, {bottom})</div>
            <div class="qa-image-cropper-metrics__meta">原图利用率 {usage_ratio:.1f}%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _crop_box_to_coordinates(processor: ImageProcessor, box, image_width: int, image_height: int) -> tuple[int, int, int, int] | None:
    if not box:
        return None

    left = box.get("left", 0)
    top = box.get("top", 0)
    width = box.get("width", image_width)
    height = box.get("height", image_height)
    return processor.normalize_crop_box((left, top, left + width, top + height), image_width, image_height)


def _render_processed_download(
    label: str,
    data: bytes,
    stem_name: str,
    suffix: str,
    target_format: str,
) -> None:
    safe_stem = _safe_download_stem(stem_name)
    action_download_button(
        label,
        data=data,
        file_name=f"{safe_stem}_{suffix}.{_get_download_extension(target_format)}",
        mime=_get_download_mime(target_format),
    )


def _render_conversion_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    formats = get_image_formats()
    col1, col2, col3 = st.columns(3)
    with col1:
        target_format = st.selectbox("目标格式", list(formats.keys()), key="image_tool_target_format")
        format_spec = formats[target_format]
        st.caption(format_spec.description or f"扩展名 .{format_spec.extension}")
    with col2:
        if format_spec.lossy:
            quality = st.slider("基础质量", min_value=1, max_value=100, value=90, key="image_tool_quality")
            compression_mode = st.radio(
                "压缩模式", ["质量优先", "平衡模式", "体积优先"],
                horizontal=True, key="image_tool_compression_mode",
            )
        else:
            quality = 95
            compression_mode = "质量优先"
            st.caption("当前格式不使用质量参数，已隐藏无效选项。")
    with col3:
        resize_option = st.radio("输出尺寸", ["保持原尺寸", "自定义尺寸"], horizontal=True, key="image_tool_convert_resize_mode")
        if resize_option == "自定义尺寸":
            new_width, new_height = _render_size_inputs("image_tool_convert_resize", image.width, image.height)
        else:
            new_width, new_height = image.width, image.height
            st.caption(f"输出尺寸: {new_width} × {new_height} 像素")
        if not format_spec.supports_alpha:
            background_color = _hex_to_rgb(
                st.color_picker("透明区域背景色", "#FFFFFF", key="image_tool_convert_background")
            )
            st.caption("透明像素会填充为该颜色，避免 JPG/BMP 出现黑块。")
        else:
            background_color = (255, 255, 255)

    if primary_action_button("开始格式转换", key="image_tool_convert_button"):
        try:
            def transform(frame: Image.Image) -> Image.Image:
                if (new_width, new_height) == frame.size:
                    return frame.copy()
                return processor.resize_image(frame, new_width, new_height)

            resolved_quality = _resolve_quality(target_format, quality, compression_mode)
            converted_image, image_bytes, animation_note = _apply_transform_and_export(
                processor,
                image,
                transform,
                target_format,
                quality=resolved_quality,
                preserve_metadata=preserve_metadata,
                background_color=background_color,
            )
            render_success_feedback(
                f"格式转换完成，输出 {_format_dimensions(converted_image)}，文件大小 {_format_size(len(image_bytes))}{animation_note}。"
            )
            st.image(converted_image, caption="转换结果预览", use_container_width=True)
            _render_processed_download("导出转换结果", image_bytes, stem_name, "converted", target_format)
        except Exception as exc:
            render_error_feedback(f"格式转换失败: {exc}")


def _render_target_size_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    formats = get_image_formats()
    col1, col2, col3 = st.columns(3)
    with col1:
        target_size = st.number_input("目标大小", min_value=1, value=100, key="image_tool_target_size")
    with col2:
        size_unit = st.selectbox("大小单位", ["KB", "MB"], key="image_tool_target_unit")
    with col3:
        output_format = st.selectbox("输出格式", list(formats.keys()), key="image_tool_target_format_2")

    option_col1, option_col2, option_col3 = st.columns(3)
    with option_col1:
        exact_padding = st.checkbox("开启精确补齐", value=False, key="image_tool_exact_padding")
    with option_col2:
        allow_resize = st.checkbox("允许自动缩放", value=True, key="image_tool_allow_resize")
    with option_col3:
        if formats[output_format].lossy:
            min_quality = st.slider("最低质量底线", min_value=1, max_value=100, value=10, key="image_tool_target_min_quality")
        else:
            min_quality = 100
            st.caption("当前格式主要通过缩尺寸逼近目标体积。")

    if primary_action_button("开始生成目标体积图", key="image_tool_target_button"):
        try:
            target_bytes = int(target_size) * (1024 if size_unit == "KB" else 1024 * 1024)
            result = processor.convert_to_target_filesize(
                image,
                target_bytes=target_bytes,
                output_format=output_format,
                exact_padding=exact_padding,
                allow_resize=allow_resize,
                min_quality=min_quality,
                preserve_metadata=preserve_metadata,
            )
            message = (
                f"目标体积图片已生成。结果 {_format_size(result['size_bytes'])} | "
                f"原始导出 {_format_size(result['raw_size_bytes'])} | 缩放比例 {result['scale_ratio']:.2f}"
            )
            if result["target_achieved"]:
                render_success_feedback(message)
            else:
                render_warning_feedback(
                    f"{message}；未达到目标 {_format_size(target_bytes)}。{result['note']}"
                )
            animation_note = (
                "动画帧已按同一比例处理，预览显示第一帧。"
                if result.get("animated") else ""
            )
            if animation_note:
                st.caption(animation_note)
            st.image(result["image"], caption="输出预览", use_container_width=True)
            _render_processed_download(
                "导出目标体积图",
                result["data"],
                stem_name,
                f"{target_size}{size_unit.lower()}",
                output_format,
            )
        except Exception as exc:
            render_error_feedback(f"目标体积图片生成失败: {exc}")


def _render_batch_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    preset_targets = get_preset_targets()
    selected_labels = st.multiselect(
        "选择批量输出档位",
        list(preset_targets.keys()),
        default=[label for label in ("100 KB", "500 KB", "5 MB") if label in preset_targets],
        key="image_tool_batch_targets",
    )
    output_format = st.selectbox("批量输出格式", list(get_image_formats().keys()), key="image_tool_batch_format")
    formats = get_image_formats()
    exact_padding = st.checkbox("批量模式开启精确补齐", value=True, key="image_tool_batch_padding")
    if formats[output_format].lossy:
        min_quality = st.slider("批量最低质量底线", min_value=1, max_value=100, value=10, key="image_tool_batch_min_quality")
    else:
        min_quality = 100

    if primary_action_button("开始批量造图", key="image_tool_batch_button"):
        if not selected_labels:
            render_warning_feedback("请先选择至少一个批量输出档位。")
            return

        progress = st.progress(0.0, text="准备批量造图…")
        try:
            targets = [(label, preset_targets[label].bytes_) for label in selected_labels]
            results = []
            for index, (label, size) in enumerate(targets, start=1):
                progress.progress(
                    (index - 1) / len(targets),
                    text=f"正在生成 {label}（{index}/{len(targets)}）…",
                )
                results.append(processor.convert_to_target_filesize(
                    image,
                    target_bytes=size,
                    output_format=output_format,
                    exact_padding=exact_padding,
                    min_quality=min_quality,
                    preserve_metadata=preserve_metadata,
                ))
                results[-1]["target_label"] = label
                results[-1]["target_bytes"] = size
            progress.progress(1.0, text="批量造图完成，正在打包…")

            zip_buffer = io.BytesIO()
            safe_stem = _safe_download_stem(stem_name)
            extension = _get_download_extension(output_format)
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for item in results:
                    archive.writestr(
                        f"{safe_stem}_{_safe_download_stem(item['target_label'])}.{extension}",
                        item["data"],
                    )
                archive.writestr("manifest.csv", _build_manifest_bytes(results))
            zip_buffer.seek(0)

            st.dataframe(
                [
                    {
                        "目标档位": item["target_label"],
                        "输出大小": _format_size(item["size_bytes"]),
                        "缩放比例": round(item["scale_ratio"], 3),
                        "是否达标": "是" if item["target_achieved"] else "否",
                    }
                    for item in results
                ],
                use_container_width=True,
                hide_index=True,
            )
            unmet = [item["target_label"] for item in results if not item["target_achieved"]]
            if unmet:
                render_warning_feedback(
                    f"以下档位未达到目标体积: {'、'.join(unmet)}；实际体积见 manifest.csv。"
                )
            else:
                render_success_feedback("全部档位已达到目标体积，ZIP 内含 manifest.csv。")
            action_download_button(
                "导出批量 ZIP",
                data=zip_buffer.getvalue(),
                file_name=f"{safe_stem}_batch_images.zip",
                mime="application/zip",
            )
        except Exception as exc:
            render_error_feedback(f"批量造图失败: {exc}")
        finally:
            progress.empty()


def _render_resize_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    limits = get_image_limits()
    col1, col2 = st.columns(2)
    with col1:
        resize_method = st.radio("调整方式", ["自定义尺寸", "按比例缩放", "预设尺寸"], horizontal=True, key="image_tool_resize_method")
        if resize_method == "自定义尺寸":
            new_width, new_height = _render_size_inputs("image_tool_resize_custom", image.width, image.height)
        elif resize_method == "按比例缩放":
            scale_percent = st.slider("缩放比例 (%)", 10, 200, 100, key="image_tool_resize_scale")
            new_width = max(1, int(round(image.width * scale_percent / 100)))
            new_height = max(1, int(round(image.height * scale_percent / 100)))
            st.caption(f"输出尺寸: {new_width} × {new_height} 像素")
        else:
            preset_sizes = get_preset_sizes()
            preset_name = st.selectbox("选择预设尺寸", list(preset_sizes.keys()), key="image_tool_resize_preset")
            preset = preset_sizes[preset_name]
            new_width, new_height = preset.width, preset.height
            st.caption(f"输出尺寸: {new_width} × {new_height} 像素")

    with col2:
        resample_name = st.selectbox("重采样算法", list(get_resample_methods().keys()), key="image_tool_resample")
        output_format = st.selectbox("输出格式", list(get_image_formats().keys()), key="image_tool_resize_format")

    if primary_action_button("开始调整尺寸", key="image_tool_resize_button"):
        try:
            def transform(frame: Image.Image) -> Image.Image:
                return processor.resize_image(frame, new_width, new_height, resample_name)

            resized, image_bytes, animation_note = _apply_transform_and_export(
                processor, image, transform, output_format,
                quality=95, preserve_metadata=preserve_metadata,
            )
            render_success_feedback(
                f"尺寸调整完成，原图 {_format_dimensions(image)}，输出 {_format_dimensions(resized)}{animation_note}。"
            )
            st.image(resized, caption="尺寸调整预览", use_container_width=True)
            _render_processed_download("导出调整结果", image_bytes, stem_name, "resized", output_format)
        except Exception as exc:
            render_error_feedback(f"尺寸调整失败: {exc}")


def _render_flip_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    col1, col2 = st.columns(2)
    with col1:
        flip_direction = st.radio("翻转方向", ["上下翻转", "左右翻转", "同时翻转"], key="image_tool_flip_direction")
        st.caption("上下翻转为垂直镜像，左右翻转为水平镜像。")
    with col2:
        output_format = st.selectbox("输出格式", list(get_image_formats().keys()), key="image_tool_flip_format")

    if primary_action_button("开始翻转图片", key="image_tool_flip_button"):
        try:
            flipped, image_bytes, animation_note = _apply_transform_and_export(
                processor, image,
                lambda frame: processor.flip_image(frame, flip_direction),
                output_format,
                quality=95, preserve_metadata=preserve_metadata,
            )
            render_success_feedback(f"图片翻转完成，输出 {_format_dimensions(flipped)}{animation_note}。")
            st.image(flipped, caption="翻转结果预览", use_container_width=True)
            _render_processed_download("导出翻转结果", image_bytes, stem_name, "flipped", output_format)
        except Exception as exc:
            render_error_feedback(f"图片翻转失败: {exc}")


def _render_rotate_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    col1, col2 = st.columns(2)
    with col1:
        rotation_direction = st.radio("旋转方向", ["顺时针", "逆时针"], horizontal=True, key="image_tool_rotation_direction")
        rotation_angle = st.slider("旋转角度", min_value=0, max_value=360, value=90, step=1, key="image_tool_rotation_angle")
        expand_canvas = st.checkbox("自动扩展画布", value=True, key="image_tool_rotation_expand")
    with col2:
        bg_color = st.color_picker("背景填充颜色", "#FFFFFF", key="image_tool_rotation_fill")
        output_format = st.selectbox("输出格式", list(get_image_formats().keys()), key="image_tool_rotate_format")

    if primary_action_button("开始旋转图片", key="image_tool_rotate_button"):
        try:
            signed_angle = rotation_angle if rotation_direction == "顺时针" else -rotation_angle
            fill_color = _hex_to_rgb(bg_color)

            def transform(frame: Image.Image) -> Image.Image:
                return processor.rotate_image(
                    frame,
                    signed_angle,
                    fill_color=fill_color,
                    expand=expand_canvas,
                )

            rotated, image_bytes, animation_note = _apply_transform_and_export(
                processor, image, transform, output_format,
                quality=95, preserve_metadata=preserve_metadata,
            )
            render_success_feedback(f"图片旋转完成，输出 {_format_dimensions(rotated)}{animation_note}。")
            st.image(rotated, caption="旋转结果预览", use_container_width=True)
            _render_processed_download("导出旋转结果", image_bytes, stem_name, "rotated", output_format)
        except Exception as exc:
            render_error_feedback(f"图片旋转失败: {exc}")


def _render_crop_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    upload_signature: str,
    *,
    preserve_metadata: bool,
) -> None:
    crop_method = st.radio("裁剪方式", ["自由裁剪", "按比例裁剪"], horizontal=True, key="image_tool_crop_method")
    crop_interaction_options = ["拖拽裁剪框", "数值微调"] if INTERACTIVE_CROP_AVAILABLE else ["数值微调"]
    crop_interaction = st.radio("裁剪交互", crop_interaction_options, horizontal=True, key="image_tool_crop_interaction")
    if not INTERACTIVE_CROP_AVAILABLE:
        st.caption("当前环境未安装交互裁剪组件，已自动回退为数值微调模式。")

    aspect_ratio_tuple = None
    if crop_method == "按比例裁剪":
        aspect_ratio_label = st.selectbox(
            "裁剪比例",
            [*get_aspect_ratios().keys(), "自定义"],
            key="image_tool_crop_ratio",
        )
        if aspect_ratio_label == "自定义":
            ratio_col1, ratio_col2 = st.columns(2)
            with ratio_col1:
                ratio_width = int(st.number_input("宽度比例", min_value=1, value=1, key="image_tool_crop_ratio_width"))
            with ratio_col2:
                ratio_height = int(st.number_input("高度比例", min_value=1, value=1, key="image_tool_crop_ratio_height"))
        else:
            ratio_spec = get_aspect_ratios()[aspect_ratio_label]
            ratio_width, ratio_height = ratio_spec.width, ratio_spec.height
        aspect_ratio_tuple = (ratio_width, ratio_height)
        st.caption(f"当前固定比例: {ratio_width}:{ratio_height}")

    crop_box = None
    original_width = image.width
    original_height = image.height

    if crop_interaction == "拖拽裁剪框" and INTERACTIVE_CROP_AVAILABLE:
        _render_cropper_style()
        cropper_col, info_col = st.columns([1.35, 1])
        with cropper_col:
            st.markdown(
                """
                <div class="qa-image-cropper-guide">
                    <span class="qa-image-cropper-guide__dot"></span>
                    <div>
                        <div class="qa-image-cropper-guide__title">拖动高亮裁剪框，首屏会自动给出一个清晰可见的默认区域</div>
                        <div class="qa-image-cropper-guide__desc">橙色边框就是最终保留范围。拖四角可以改尺寸，拖中间可以改位置。</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            default_crop_box = _build_default_crop_box(processor, original_width, original_height, aspect_ratio_tuple)
            cropped_preview, crop_box_data = st_cropper(
                image,
                realtime_update=True,
                default_coords=_to_cropper_default_coords(processor, default_crop_box, original_width, original_height),
                box_color="#ff7a18",
                aspect_ratio=aspect_ratio_tuple,
                return_type="both",
                should_resize_image=True,
                stroke_width=4,
                key=f"image_tool_cropper_{upload_signature}_{crop_method}_{aspect_ratio_tuple or 'free'}",
            )
        crop_box = _crop_box_to_coordinates(processor, crop_box_data, original_width, original_height) or default_crop_box
        if cropped_preview is None:
            cropped_preview = processor.crop_image(image, crop_box)
        with info_col:
            if crop_box is not None:
                _render_crop_metrics_card(crop_box, original_width, original_height)
                if cropped_preview is not None:
                    st.image(cropped_preview, caption="裁剪预览", use_container_width=True)
    else:
        if crop_method == "自由裁剪":
            col_setting, col_preview = st.columns([1, 1])
            with col_setting:
                left = st.slider("左边距", 0, max(0, original_width - 1), 0, key="image_tool_crop_left")
                top = st.slider("上边距", 0, max(0, original_height - 1), 0, key="image_tool_crop_top")
                right_min = min(left + 1, original_width)
                bottom_min = min(top + 1, original_height)
                right = st.slider("右边距", right_min, max(right_min + 1, original_width), original_width, key="image_tool_crop_right", disabled=right_min >= original_width)
                bottom = st.slider("下边距", bottom_min, max(bottom_min + 1, original_height), original_height, key="image_tool_crop_bottom", disabled=bottom_min >= original_height)
                crop_box = processor.normalize_crop_box((left, top, right, bottom), original_width, original_height)
            with col_preview:
                preview_image = processor.crop_image(image, crop_box)
                crop_width, crop_height, usage_ratio = _get_crop_metrics(crop_box, original_width, original_height)
                st.image(preview_image, caption="裁剪预览", use_container_width=True)
                st.caption(
                    f"位置 ({crop_box[0]}, {crop_box[1]}) 到 ({crop_box[2]}, {crop_box[3]})，"
                    f"尺寸 {crop_width} × {crop_height}，原图利用率 {usage_ratio:.1f}%"
                )
        else:
            target_ratio = ratio_width / ratio_height
            current_ratio = original_width / original_height
            if current_ratio > target_ratio:
                max_crop_width = int(original_height * target_ratio)
                max_crop_height = original_height
            else:
                max_crop_width = original_width
                max_crop_height = int(original_width / target_ratio)

            col_setting, col_preview = st.columns([1, 1])
            with col_setting:
                scale_percent = st.slider("裁剪框大小 (%)", 10, 100, 100, key="image_tool_crop_scale")
                crop_width = max(1, int(round(max_crop_width * scale_percent / 100)))
                crop_height = max(1, int(round(crop_width / target_ratio)))
                if crop_height > max_crop_height:
                    crop_height = max_crop_height
                    crop_width = max(1, int(round(crop_height * target_ratio)))

                max_left = max(0, original_width - crop_width)
                max_top = max(0, original_height - crop_height)
                left = st.slider("水平位置", 0, max(1, max_left), min(max_left, max(1, max_left) // 2), key="image_tool_crop_ratio_left", disabled=max_left <= 0)
                top = st.slider("垂直位置", 0, max(1, max_top), min(max_top, max(1, max_top) // 2), key="image_tool_crop_ratio_top", disabled=max_top <= 0)
                crop_box = processor.normalize_crop_box(
                    (left, top, left + crop_width, top + crop_height),
                    original_width,
                    original_height,
                )
            with col_preview:
                preview_image = processor.crop_image(image, crop_box)
                preview_width, preview_height, usage_ratio = _get_crop_metrics(crop_box, original_width, original_height)
                st.image(preview_image, caption="比例裁剪预览", use_container_width=True)
                st.caption(
                    f"位置 ({crop_box[0]}, {crop_box[1]}) 到 ({crop_box[2]}, {crop_box[3]})，"
                    f"尺寸 {preview_width} × {preview_height}，原图利用率 {usage_ratio:.1f}%"
                )

    output_format = st.selectbox("输出格式", list(get_image_formats().keys()), key="image_tool_crop_output_format")

    if primary_action_button("开始裁剪图片", key="image_tool_crop_button"):
        if crop_box is None:
            render_warning_feedback("当前还没有可用的裁剪区域。")
            return

        try:
            cropped, image_bytes, animation_note = _apply_transform_and_export(
                processor, image,
                lambda frame: processor.crop_image(frame, crop_box),
                output_format,
                quality=95, preserve_metadata=preserve_metadata,
            )
            render_success_feedback(f"图片裁剪完成，输出 {_format_dimensions(cropped)}{animation_note}。")
            st.image(cropped, caption="裁剪结果预览", use_container_width=True)
            _render_processed_download("导出裁剪结果", image_bytes, stem_name, "cropped", output_format)
        except Exception as exc:
            render_error_feedback(f"图片裁剪失败: {exc}")


def _render_watermark_tab(
    processor: ImageProcessor,
    image: Image.Image,
    stem_name: str,
    *,
    preserve_metadata: bool,
) -> None:
    watermark_text = st.text_input("水印文本", value="QA TOOLKIT", key="image_tool_watermark_text")
    position = st.selectbox(
        "水印位置",
        list(get_watermark_positions().keys()),
        key="image_tool_watermark_position",
    )
    option_col1, option_col2, option_col3 = st.columns(3)
    with option_col1:
        font_size = st.slider("字体大小", min_value=12, max_value=120, value=36, key="image_tool_font_size")
    with option_col2:
        opacity = st.slider("透明度", min_value=0.05, max_value=1.0, value=0.25, key="image_tool_opacity")
    with option_col3:
        rotation = st.slider("旋转角度", min_value=-180, max_value=180, value=0, key="image_tool_rotation")

    color_value = st.color_picker("水印颜色", "#FFFFFF", key="image_tool_color")
    font_file = st.file_uploader("上传自定义字体（可选）", type=["ttf", "ttc", "otf"], key="image_tool_font_file")

    if primary_action_button("开始添加水印", key="image_tool_watermark_button"):
        try:
            color = _hex_to_rgb(color_value)

            def transform(frame: Image.Image) -> Image.Image:
                return processor.add_watermark(
                    image=frame,
                    text=watermark_text,
                    position=position,
                    font_size=font_size,
                    color=color,
                    opacity=float(opacity),
                    rotation=int(rotation),
                    font_file=font_file,
                )

            watermarked, image_bytes, animation_note = _apply_transform_and_export(
                processor, image, transform, "PNG",
                quality=95, preserve_metadata=preserve_metadata,
            )
            st.image(watermarked, caption="水印效果预览", use_container_width=True)
            if animation_note:
                st.caption(animation_note)
            _render_processed_download("导出水印图片", image_bytes, stem_name, "watermarked", "PNG")
        except Exception as exc:
            render_error_feedback(f"添加水印失败: {exc}")


def render_image_processor_page() -> None:
    show_doc("image_processor")
    render_tool_page_hero(
        "🖼️",
        "图片处理工具",
        "覆盖测试高频图片场景：格式转换、目标体积控制、尺寸调整、翻转、旋转、裁剪和文字水印。",
        tags=["格式转换", "指定体积", "尺寸调整", "翻转", "旋转", "裁剪", "水印"],
        accent="#0f4c81",
    )
    render_tool_tips(
        "推荐用法",
        [
            "上传边界值验证优先走“指定体积”和“批量造图”，可以一次产出多档测试图片。",
            "JPG / WEBP 更适合压缩体积；PNG 适合透明图、裁剪预览和水印结果。",
            "若环境安装了交互裁剪组件，可以直接拖动裁剪框；否则会自动回退为数值微调。",
        ],
    )

    with st.expander("当前注册的格式与档位", expanded=False):
        summary = get_registry_summary()
        st.caption(
            f"格式: {'、'.join(summary['formats'])} | "
            f"重采样: {'、'.join(summary['resamplers'])} | "
            f"体积档位: {'、'.join(summary['preset_targets'])}"
        )
        st.caption(f"资源上限: {summary['limits']}")

    upload_types = sorted(
        {spec.extension for spec in get_image_formats().values()} | {"jpeg"}
    )
    uploaded_file = st.file_uploader(
        "上传图片",
        type=upload_types,
        key="image_tool_upload",
    )
    if uploaded_file is None:
        render_tool_empty_state(
            "等待图片输入",
            "上传一张测试图片后，就可以继续做格式转换、指定体积、批量造图、尺寸调整、翻转、旋转、裁剪和水印处理。",
        )
        return

    try:
        image = _load_image(uploaded_file)
    except Exception as exc:
        render_error_feedback(f"图片读取失败: {exc}")
        return

    processor = ImageProcessor()
    stem_name = _safe_download_stem(Path(uploaded_file.name).stem)
    upload_signature = _build_upload_signature(uploaded_file)
    st.image(image, caption="原图预览", use_container_width=True)
    _render_source_summary(image, uploaded_file)
    preserve_metadata = st.checkbox(
        "导出时保留 EXIF（可能包含拍摄位置与设备信息）",
        value=False,
        key="image_tool_preserve_metadata",
    )

    (
        convert_tab,
        target_tab,
        batch_tab,
        resize_tab,
        flip_tab,
        rotate_tab,
        crop_tab,
        watermark_tab,
    ) = st.tabs(["格式转换", "指定体积", "批量造图", "调整尺寸", "图片翻转", "图片旋转", "图片裁剪", "添加水印"])

    with convert_tab:
        _render_conversion_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
    with target_tab:
        _render_target_size_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
    with batch_tab:
        _render_batch_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
    with resize_tab:
        _render_resize_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
    with flip_tab:
        _render_flip_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
    with rotate_tab:
        _render_rotate_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
    with crop_tab:
        _render_crop_tab(processor, image, stem_name, upload_signature, preserve_metadata=preserve_metadata)
    with watermark_tab:
        _render_watermark_tab(processor, image, stem_name, preserve_metadata=preserve_metadata)
