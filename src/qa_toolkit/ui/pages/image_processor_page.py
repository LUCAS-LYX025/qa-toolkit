from __future__ import annotations

import hashlib
import io
import zipfile
from pathlib import Path

from PIL import Image
import streamlit as st

try:
    from streamlit_cropper import st_cropper

    INTERACTIVE_CROP_AVAILABLE = True
except Exception:
    st_cropper = None
    INTERACTIVE_CROP_AVAILABLE = False

from qa_toolkit.config.constants import PRESET_SIZES
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button
from qa_toolkit.ui.components.status_feedback import render_error_feedback, render_success_feedback, render_warning_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_empty_state, render_tool_page_hero, render_tool_tips
from qa_toolkit.utils.image_processing import ImageProcessor


PRESET_TARGETS = {
    "50 KB": 50 * 1024,
    "100 KB": 100 * 1024,
    "200 KB": 200 * 1024,
    "500 KB": 500 * 1024,
    "1 MB": 1024 * 1024,
    "2 MB": 2 * 1024 * 1024,
    "5 MB": 5 * 1024 * 1024,
}

RESAMPLE_OPTIONS = {
    "LANCZOS (高质量)": "LANCZOS",
    "BILINEAR (平衡)": "BILINEAR",
    "NEAREST (快速)": "NEAREST",
}

ASPECT_RATIO_OPTIONS = {
    "1:1 (正方形)": (1, 1),
    "16:9 (宽屏)": (16, 9),
    "4:3 (标准)": (4, 3),
    "3:2 (照片)": (3, 2),
    "9:16 (竖屏)": (9, 16),
}

FILE_EXTENSION_MAP = {
    "JPG": "jpg",
    "JPEG": "jpg",
    "PNG": "png",
    "WEBP": "webp",
    "GIF": "gif",
    "BMP": "bmp",
}


def _load_image(uploaded_file) -> Image.Image:
    image = Image.open(io.BytesIO(uploaded_file.getvalue()))
    image.load()
    return image


def _hex_to_rgb(color_value: str) -> tuple[int, int, int]:
    cleaned = color_value.lstrip("#")
    return tuple(int(cleaned[index:index + 2], 16) for index in (0, 2, 4))


def _format_size(num_bytes: int) -> str:
    if num_bytes >= 1024 * 1024:
        return f"{num_bytes / 1024 / 1024:.2f} MB"
    return f"{num_bytes / 1024:.2f} KB"


def _format_dimensions(image: Image.Image) -> str:
    return f"{image.width} × {image.height}"


def _get_download_extension(target_format: str) -> str:
    return FILE_EXTENSION_MAP.get(target_format.upper(), target_format.lower())


def _get_download_mime(target_format: str) -> str:
    return f"image/{'jpeg' if target_format.upper() in {'JPG', 'JPEG'} else target_format.lower()}"


def _resolve_quality(target_format: str, quality: int, compression_mode: str) -> int:
    if target_format.upper() not in {"JPG", "JPEG", "WEBP"}:
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


def _render_size_inputs(prefix: str, default_width: int, default_height: int) -> tuple[int, int]:
    keep_ratio = st.checkbox("保持原始宽高比", value=True, key=f"{prefix}_keep_ratio")
    if keep_ratio:
        anchor = st.radio("按哪一边调整", ["按宽度", "按高度"], horizontal=True, key=f"{prefix}_anchor")
        if anchor == "按宽度":
            new_width = int(st.number_input("宽度(像素)", min_value=1, value=default_width, step=1, key=f"{prefix}_width"))
            new_height = max(1, int(round(new_width * default_height / max(1, default_width))))
            st.caption(f"高度自动计算为 {new_height} 像素")
        else:
            new_height = int(st.number_input("高度(像素)", min_value=1, value=default_height, step=1, key=f"{prefix}_height"))
            new_width = max(1, int(round(new_height * default_width / max(1, default_height))))
            st.caption(f"宽度自动计算为 {new_width} 像素")
    else:
        width_col, height_col = st.columns(2)
        with width_col:
            new_width = int(st.number_input("宽度(像素)", min_value=1, value=default_width, step=1, key=f"{prefix}_width"))
        with height_col:
            new_height = int(st.number_input("高度(像素)", min_value=1, value=default_height, step=1, key=f"{prefix}_height"))

    st.caption(f"输出尺寸: {new_width} × {new_height} 像素")
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
            <div class="qa-image-cropper-metrics__eyebrow">Current Selection</div>
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
    action_download_button(
        label,
        data=data,
        file_name=f"{stem_name}_{suffix}.{_get_download_extension(target_format)}",
        mime=_get_download_mime(target_format),
    )


def _render_conversion_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        target_format = st.selectbox("目标格式", ["JPG", "PNG", "WEBP", "GIF", "BMP"], key="image_tool_target_format")
    with col2:
        quality = st.slider("基础质量", min_value=10, max_value=100, value=90, key="image_tool_quality")
        compression_mode = st.radio("压缩模式", ["质量优先", "平衡模式", "体积优先"], horizontal=True, key="image_tool_compression_mode")
        if target_format not in {"JPG", "WEBP"}:
            st.caption("当前格式不使用质量参数，系统会忽略该项。")
    with col3:
        resize_option = st.radio("输出尺寸", ["保持原尺寸", "自定义尺寸"], horizontal=True, key="image_tool_convert_resize_mode")
        if resize_option == "自定义尺寸":
            new_width, new_height = _render_size_inputs("image_tool_convert_resize", image.width, image.height)
        else:
            new_width, new_height = image.width, image.height
            st.caption(f"输出尺寸: {new_width} × {new_height} 像素")

    if primary_action_button("开始格式转换", key="image_tool_convert_button"):
        try:
            converted_image = image.copy()
            if (new_width, new_height) != converted_image.size:
                converted_image = processor.resize_image(converted_image, new_width, new_height)
            resolved_quality = _resolve_quality(target_format, quality, compression_mode)
            image_bytes = processor.save_image_to_bytes(converted_image, target_format, quality=resolved_quality)
            render_success_feedback(
                f"格式转换完成，输出 {_format_dimensions(converted_image)}，文件大小 {_format_size(len(image_bytes))}。"
            )
            st.image(converted_image, caption="转换结果预览", use_container_width=True)
            _render_processed_download("导出转换结果", image_bytes, stem_name, "converted", target_format)
        except Exception as exc:
            render_error_feedback(f"格式转换失败: {exc}")


def _render_target_size_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    col1, col2, col3 = st.columns(3)
    with col1:
        target_size = st.number_input("目标大小", min_value=1, value=100, key="image_tool_target_size")
    with col2:
        size_unit = st.selectbox("大小单位", ["KB", "MB"], key="image_tool_target_unit")
    with col3:
        output_format = st.selectbox("输出格式", ["JPG", "WEBP", "PNG"], key="image_tool_target_format_2")

    option_col1, option_col2, option_col3 = st.columns(3)
    with option_col1:
        exact_padding = st.checkbox("开启精确补齐", value=False, key="image_tool_exact_padding")
    with option_col2:
        allow_resize = st.checkbox("允许自动缩放", value=True, key="image_tool_allow_resize")
    with option_col3:
        if output_format in {"JPG", "WEBP"}:
            min_quality = st.slider("最低质量底线", min_value=1, max_value=100, value=10, key="image_tool_target_min_quality")
        else:
            min_quality = 100
            st.caption("PNG 主要通过缩尺寸逼近目标体积。")

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
            )
            render_success_feedback(
                f"目标体积图片已生成。结果 {_format_size(result['size_bytes'])} | "
                f"原始导出 {_format_size(result['raw_size_bytes'])} | 缩放比例 {result['scale_ratio']:.2f}"
            )
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


def _render_batch_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    selected_labels = st.multiselect(
        "选择批量输出档位",
        list(PRESET_TARGETS.keys()),
        default=["100 KB", "500 KB", "5 MB"],
        key="image_tool_batch_targets",
    )
    output_format = st.selectbox("批量输出格式", ["JPG", "WEBP", "PNG"], key="image_tool_batch_format")
    exact_padding = st.checkbox("批量模式开启精确补齐", value=True, key="image_tool_batch_padding")
    if output_format in {"JPG", "WEBP"}:
        min_quality = st.slider("批量最低质量底线", min_value=1, max_value=100, value=10, key="image_tool_batch_min_quality")
    else:
        min_quality = 100

    if primary_action_button("开始批量造图", key="image_tool_batch_button"):
        if not selected_labels:
            render_warning_feedback("请先选择至少一个批量输出档位。")
            return

        try:
            targets = [(label, PRESET_TARGETS[label]) for label in selected_labels]
            results = processor.convert_to_multiple_filesizes(
                image,
                targets=targets,
                output_format=output_format,
                exact_padding=exact_padding,
                min_quality=min_quality,
            )
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for item in results:
                    archive.writestr(
                        f"{stem_name}_{item['target_label'].replace(' ', '_').lower()}.{_get_download_extension(output_format)}",
                        item["data"],
                    )
            zip_buffer.seek(0)

            st.dataframe(
                [
                    {
                        "目标档位": item["target_label"],
                        "输出大小": _format_size(item["size_bytes"]),
                        "缩放比例": round(item["scale_ratio"], 3),
                    }
                    for item in results
                ],
                use_container_width=True,
                hide_index=True,
            )
            action_download_button(
                "导出批量 ZIP",
                data=zip_buffer.getvalue(),
                file_name=f"{stem_name}_batch_images.zip",
                mime="application/zip",
            )
        except Exception as exc:
            render_error_feedback(f"批量造图失败: {exc}")


def _render_resize_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
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
            preset_name = st.selectbox("选择预设尺寸", list(PRESET_SIZES.keys()), key="image_tool_resize_preset")
            new_width, new_height = PRESET_SIZES[preset_name]
            st.caption(f"输出尺寸: {new_width} × {new_height} 像素")

    with col2:
        resample_label = st.selectbox("重采样算法", list(RESAMPLE_OPTIONS.keys()), key="image_tool_resample")
        output_format = st.selectbox("输出格式", ["JPG", "PNG", "WEBP"], key="image_tool_resize_format")

    if primary_action_button("开始调整尺寸", key="image_tool_resize_button"):
        try:
            resized = processor.resize_image(image, new_width, new_height, RESAMPLE_OPTIONS[resample_label])
            image_bytes = processor.save_image_to_bytes(resized, output_format)
            render_success_feedback(
                f"尺寸调整完成，原图 {_format_dimensions(image)}，输出 {_format_dimensions(resized)}。"
            )
            st.image(resized, caption="尺寸调整预览", use_container_width=True)
            _render_processed_download("导出调整结果", image_bytes, stem_name, "resized", output_format)
        except Exception as exc:
            render_error_feedback(f"尺寸调整失败: {exc}")


def _render_flip_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    col1, col2 = st.columns(2)
    with col1:
        flip_direction = st.radio("翻转方向", ["上下翻转", "左右翻转", "同时翻转"], key="image_tool_flip_direction")
        st.caption("上下翻转为垂直镜像，左右翻转为水平镜像。")
    with col2:
        output_format = st.selectbox("输出格式", ["JPG", "PNG", "WEBP"], key="image_tool_flip_format")

    if primary_action_button("开始翻转图片", key="image_tool_flip_button"):
        try:
            flipped = processor.flip_image(image, flip_direction)
            image_bytes = processor.save_image_to_bytes(flipped, output_format)
            render_success_feedback(f"图片翻转完成，输出 {_format_dimensions(flipped)}。")
            st.image(flipped, caption="翻转结果预览", use_container_width=True)
            _render_processed_download("导出翻转结果", image_bytes, stem_name, "flipped", output_format)
        except Exception as exc:
            render_error_feedback(f"图片翻转失败: {exc}")


def _render_rotate_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    col1, col2 = st.columns(2)
    with col1:
        rotation_direction = st.radio("旋转方向", ["顺时针", "逆时针"], horizontal=True, key="image_tool_rotation_direction")
        rotation_angle = st.slider("旋转角度", min_value=0, max_value=360, value=90, step=1, key="image_tool_rotation_angle")
        expand_canvas = st.checkbox("自动扩展画布", value=True, key="image_tool_rotation_expand")
    with col2:
        bg_color = st.color_picker("背景填充颜色", "#FFFFFF", key="image_tool_rotation_fill")
        output_format = st.selectbox("输出格式", ["JPG", "PNG", "WEBP"], key="image_tool_rotate_format")

    if primary_action_button("开始旋转图片", key="image_tool_rotate_button"):
        try:
            signed_angle = rotation_angle if rotation_direction == "顺时针" else -rotation_angle
            rotated = processor.rotate_image(
                image,
                signed_angle,
                fill_color=_hex_to_rgb(bg_color),
                expand=expand_canvas,
            )
            image_bytes = processor.save_image_to_bytes(rotated, output_format)
            render_success_feedback(f"图片旋转完成，输出 {_format_dimensions(rotated)}。")
            st.image(rotated, caption="旋转结果预览", use_container_width=True)
            _render_processed_download("导出旋转结果", image_bytes, stem_name, "rotated", output_format)
        except Exception as exc:
            render_error_feedback(f"图片旋转失败: {exc}")


def _render_crop_tab(processor: ImageProcessor, image: Image.Image, stem_name: str, upload_signature: str) -> None:
    crop_method = st.radio("裁剪方式", ["自由裁剪", "按比例裁剪"], horizontal=True, key="image_tool_crop_method")
    crop_interaction_options = ["拖拽裁剪框", "数值微调"] if INTERACTIVE_CROP_AVAILABLE else ["数值微调"]
    crop_interaction = st.radio("裁剪交互", crop_interaction_options, horizontal=True, key="image_tool_crop_interaction")
    if not INTERACTIVE_CROP_AVAILABLE:
        st.caption("当前环境未安装交互裁剪组件，已自动回退为数值微调模式。")

    aspect_ratio_tuple = None
    if crop_method == "按比例裁剪":
        aspect_ratio_label = st.selectbox(
            "裁剪比例",
            [*ASPECT_RATIO_OPTIONS.keys(), "自定义"],
            key="image_tool_crop_ratio",
        )
        if aspect_ratio_label == "自定义":
            ratio_col1, ratio_col2 = st.columns(2)
            with ratio_col1:
                ratio_width = int(st.number_input("宽度比例", min_value=1, value=1, key="image_tool_crop_ratio_width"))
            with ratio_col2:
                ratio_height = int(st.number_input("高度比例", min_value=1, value=1, key="image_tool_crop_ratio_height"))
        else:
            ratio_width, ratio_height = ASPECT_RATIO_OPTIONS[aspect_ratio_label]
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
                right = st.slider("右边距", left + 1, original_width, original_width, key="image_tool_crop_right")
                bottom = st.slider("下边距", top + 1, original_height, original_height, key="image_tool_crop_bottom")
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
                left = st.slider("水平位置", 0, max_left if max_left > 0 else 0, max_left // 2, key="image_tool_crop_ratio_left")
                top = st.slider("垂直位置", 0, max_top if max_top > 0 else 0, max_top // 2, key="image_tool_crop_ratio_top")
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

    output_format = st.selectbox("输出格式", ["JPG", "PNG", "WEBP"], key="image_tool_crop_output_format")

    if primary_action_button("开始裁剪图片", key="image_tool_crop_button"):
        if crop_box is None:
            render_warning_feedback("当前还没有可用的裁剪区域。")
            return

        try:
            cropped = processor.crop_image(image, crop_box)
            image_bytes = processor.save_image_to_bytes(cropped, output_format)
            render_success_feedback(f"图片裁剪完成，输出 {_format_dimensions(cropped)}。")
            st.image(cropped, caption="裁剪结果预览", use_container_width=True)
            _render_processed_download("导出裁剪结果", image_bytes, stem_name, "cropped", output_format)
        except Exception as exc:
            render_error_feedback(f"图片裁剪失败: {exc}")


def _render_watermark_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    watermark_text = st.text_input("水印文本", value="QA TOOLKIT", key="image_tool_watermark_text")
    position = st.selectbox(
        "水印位置",
        ["顶部居左", "顶部居中", "顶部居右", "左边居中", "图片中心", "右边居中", "底部居左", "底部居中", "底部居右"],
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
            watermarked = processor.add_watermark(
                image=image,
                text=watermark_text,
                position=position,
                font_size=font_size,
                color=_hex_to_rgb(color_value),
                opacity=float(opacity),
                rotation=int(rotation),
                font_file=font_file,
            )
            image_bytes = processor.save_image_to_bytes(watermarked, "PNG")
            st.image(watermarked, caption="水印效果预览", use_container_width=True)
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

    uploaded_file = st.file_uploader(
        "上传图片",
        type=["png", "jpg", "jpeg", "webp", "bmp", "gif"],
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
    stem_name = Path(uploaded_file.name).stem
    upload_signature = _build_upload_signature(uploaded_file)
    st.image(image, caption="原图预览", use_container_width=True)
    _render_source_summary(image, uploaded_file)

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
        _render_conversion_tab(processor, image, stem_name)
    with target_tab:
        _render_target_size_tab(processor, image, stem_name)
    with batch_tab:
        _render_batch_tab(processor, image, stem_name)
    with resize_tab:
        _render_resize_tab(processor, image, stem_name)
    with flip_tab:
        _render_flip_tab(processor, image, stem_name)
    with rotate_tab:
        _render_rotate_tab(processor, image, stem_name)
    with crop_tab:
        _render_crop_tab(processor, image, stem_name, upload_signature)
    with watermark_tab:
        _render_watermark_tab(processor, image, stem_name)
