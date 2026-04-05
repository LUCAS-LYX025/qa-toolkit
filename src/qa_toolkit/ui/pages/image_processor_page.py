from __future__ import annotations

import io
import zipfile
from pathlib import Path

from PIL import Image
import streamlit as st

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


def _render_source_summary(image: Image.Image, uploaded_file) -> None:
    source_size = getattr(uploaded_file, "size", len(uploaded_file.getvalue()))
    metric_cols = st.columns(4)
    metric_cols[0].metric("宽度", image.width)
    metric_cols[1].metric("高度", image.height)
    metric_cols[2].metric("模式", image.mode)
    metric_cols[3].metric("原图大小", _format_size(source_size))


def _render_conversion_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    target_col1, target_col2 = st.columns(2)
    with target_col1:
        target_format = st.selectbox("目标格式", ["JPG", "PNG", "WEBP", "GIF", "BMP"], key="image_tool_target_format")
    with target_col2:
        quality = st.slider("压缩质量", min_value=10, max_value=100, value=90, key="image_tool_quality")

    if primary_action_button("开始格式转换", key="image_tool_convert_button"):
        try:
            image_bytes = processor.save_image_to_bytes(image, target_format, quality=quality)
            render_success_feedback(f"格式转换完成，输出大小 {_format_size(len(image_bytes))}。")
            st.image(image, caption="原图预览", use_container_width=True)
            action_download_button(
                "导出转换结果",
                data=image_bytes,
                file_name=f"{stem_name}_converted.{target_format.lower()}",
                mime=f"image/{'jpeg' if target_format == 'JPG' else target_format.lower()}",
            )
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

    option_col1, option_col2 = st.columns(2)
    with option_col1:
        exact_padding = st.checkbox("开启精确补齐", value=False, key="image_tool_exact_padding")
    with option_col2:
        allow_resize = st.checkbox("允许自动缩放", value=True, key="image_tool_allow_resize")

    if primary_action_button("开始生成目标体积图", key="image_tool_target_button"):
        try:
            target_bytes = int(target_size) * (1024 if size_unit == "KB" else 1024 * 1024)
            result = processor.convert_to_target_filesize(
                image,
                target_bytes=target_bytes,
                output_format=output_format,
                exact_padding=exact_padding,
                allow_resize=allow_resize,
            )
            render_success_feedback(
                f"目标体积图片已生成。结果 {_format_size(result['size_bytes'])} | "
                f"原始导出 {_format_size(result['raw_size_bytes'])} | 缩放比例 {result['scale_ratio']:.2f}"
            )
            st.image(result["image"], caption="输出预览", use_container_width=True)
            action_download_button(
                "导出目标体积图",
                data=result["data"],
                file_name=f"{stem_name}_{target_size}{size_unit.lower()}.{output_format.lower()}",
                mime=f"image/{'jpeg' if output_format == 'JPG' else output_format.lower()}",
            )
        except Exception as exc:
            render_error_feedback(f"目标体积图片生成失败: {exc}")


def _render_batch_tab(processor: ImageProcessor, image: Image.Image, stem_name: str) -> None:
    selected_labels = st.multiselect("选择批量输出档位", list(PRESET_TARGETS.keys()), default=["100 KB", "500 KB"], key="image_tool_batch_targets")
    output_format = st.selectbox("批量输出格式", ["JPG", "WEBP", "PNG"], key="image_tool_batch_format")
    exact_padding = st.checkbox("批量模式开启精确补齐", value=True, key="image_tool_batch_padding")

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
            )
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
                for item in results:
                    archive.writestr(
                        f"{stem_name}_{item['target_label'].replace(' ', '_').lower()}.{output_format.lower()}",
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
            action_download_button(
                "导出水印图片",
                data=image_bytes,
                file_name=f"{stem_name}_watermarked.png",
                mime="image/png",
            )
        except Exception as exc:
            render_error_feedback(f"添加水印失败: {exc}")


def render_image_processor_page() -> None:
    show_doc("image_processor")
    render_tool_page_hero(
        "🖼️",
        "图片处理工具",
        "聚焦测试高频场景：格式转换、目标体积控制、批量造图和水印，适合上传校验、边界值验证和素材预处理。",
        tags=["格式转换", "指定体积", "批量造图", "文字水印"],
        accent="#0f4c81",
    )
    render_tool_tips(
        "推荐用法",
        [
            "上传边界值验证优先走“指定体积”和“批量造图”，可以一次产出多档测试图片。",
            "PNG 适合透明图和水印预览，JPG / WEBP 更适合压缩体积场景。",
            "若服务端严格校验文件结构，精确补齐模式生成的图片建议先在目标系统验证一次。",
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
            "上传一张测试图片后，就可以继续做格式转换、目标体积压缩、批量测试图生成和水印处理。",
        )
        return

    try:
        image = _load_image(uploaded_file)
    except Exception as exc:
        render_error_feedback(f"图片读取失败: {exc}")
        return

    processor = ImageProcessor()
    stem_name = Path(uploaded_file.name).stem
    st.image(image, caption="原图预览", use_container_width=True)
    _render_source_summary(image, uploaded_file)

    convert_tab, target_tab, batch_tab, watermark_tab = st.tabs(["格式转换", "指定体积", "批量造图", "添加水印"])

    with convert_tab:
        _render_conversion_tab(processor, image, stem_name)
    with target_tab:
        _render_target_size_tab(processor, image, stem_name)
    with batch_tab:
        _render_batch_tab(processor, image, stem_name)
    with watermark_tab:
        _render_watermark_tab(processor, image, stem_name)
