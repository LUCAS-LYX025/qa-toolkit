from __future__ import annotations

import json
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.utils.text_analysis import TEXT_UPLOAD_TYPES, decode_uploaded_text
from qa_toolkit.utils.text_comparison import (
    DEFAULT_LEFT_TEXT,
    DEFAULT_RIGHT_TEXT,
    build_comparison_report,
    build_text_profile,
    compare_texts,
    render_token_diff_html,
)


DEFAULT_STATE = {
    "text_comparison_left_text": "",
    "text_comparison_right_text": "",
    "text_comparison_left_source": "手动输入",
    "text_comparison_right_source": "手动输入",
    "text_comparison_ignore_case": False,
    "text_comparison_trim_edges": False,
    "text_comparison_collapse_spaces": False,
    "text_comparison_ignore_blank_lines": False,
    "text_comparison_hide_equal_tokens": False,
}

STATUS_OPTIONS = ["修改", "新增", "删除"]


def _ensure_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_side_text(side: str, text: str, source_name: str):
    st.session_state[f"text_comparison_{side}_text"] = text
    st.session_state[f"text_comparison_{side}_source"] = source_name


def _load_example_pair():
    _load_side_text("left", DEFAULT_LEFT_TEXT, "示例原文")
    _load_side_text("right", DEFAULT_RIGHT_TEXT, "示例对比文")


def _clear_all():
    _load_side_text("left", "", "手动输入")
    _load_side_text("right", "", "手动输入")


def _swap_sides():
    left_text = st.session_state.text_comparison_left_text
    right_text = st.session_state.text_comparison_right_text
    left_source = st.session_state.text_comparison_left_source
    right_source = st.session_state.text_comparison_right_source

    _load_side_text("left", right_text, right_source)
    _load_side_text("right", left_text, left_source)


def _render_source_panel(side: str, label: str):
    source_key = f"text_comparison_{side}_source"
    text_key = f"text_comparison_{side}_text"
    upload_key = f"text_comparison_{side}_upload"
    load_button_key = f"text_comparison_{side}_load_button"

    st.markdown(f"### {label}")
    st.caption(f"当前来源: `{st.session_state[source_key]}`")

    uploaded_file = st.file_uploader(
        f"导入{label}",
        type=TEXT_UPLOAD_TYPES,
        key=upload_key,
        help="支持 txt / md / json / csv / log / yaml / yml / doc / docx",
    )
    if uploaded_file is not None:
        st.caption(f"已选择: `{uploaded_file.name}` | {uploaded_file.size:,} bytes")
        if st.button("导入文件到当前文本框", key=load_button_key, use_container_width=True):
            try:
                decoded_text = decode_uploaded_text(uploaded_file.getvalue(), filename=uploaded_file.name)
                _load_side_text(side, decoded_text, uploaded_file.name)
                st.rerun()
            except ValueError as exc:
                st.error(f"导入失败: {exc}")

    text_value = st.text_area(
        label,
        height=260,
        key=text_key,
        placeholder="粘贴配置、接口返回、需求文档、日志片段或代码片段...",
    )

    profile = build_text_profile(text_value)
    stat_cols = st.columns(4)
    stat_cols[0].metric("字符", profile["chars"])
    stat_cols[1].metric("行数", profile["lines"])
    stat_cols[2].metric("非空行", profile["non_empty_lines"])
    stat_cols[3].metric("词数", profile["words"])


def _render_normalization_notes(comparison: Dict[str, Any]):
    notes: List[str] = []
    left_changes = comparison["left"]["normalized"]["changes"]
    right_changes = comparison["right"]["normalized"]["changes"]

    if left_changes:
        notes.append(f"原始文本: {'；'.join(left_changes)}")
    if right_changes:
        notes.append(f"对比文本: {'；'.join(right_changes)}")

    if notes:
        st.info("本次对比已应用以下规则:\n\n" + "\n\n".join(notes))


def _build_profile_table(comparison: Dict[str, Any]) -> pd.DataFrame:
    left_profile = comparison["left"]["profile"]
    right_profile = comparison["right"]["profile"]
    left_normalized = comparison["left"]["normalized_profile"]
    right_normalized = comparison["right"]["normalized_profile"]

    return pd.DataFrame(
        [
            {"指标": "字符数", "原始文本": left_profile["chars"], "对比文本": right_profile["chars"], "规范化后原始": left_normalized["chars"], "规范化后对比": right_normalized["chars"]},
            {"指标": "行数", "原始文本": left_profile["lines"], "对比文本": right_profile["lines"], "规范化后原始": left_normalized["lines"], "规范化后对比": right_normalized["lines"]},
            {"指标": "非空行", "原始文本": left_profile["non_empty_lines"], "对比文本": right_profile["non_empty_lines"], "规范化后原始": left_normalized["non_empty_lines"], "规范化后对比": right_normalized["non_empty_lines"]},
            {"指标": "词数", "原始文本": left_profile["words"], "对比文本": right_profile["words"], "规范化后原始": left_normalized["words"], "规范化后对比": right_normalized["words"]},
            {"指标": "段落数", "原始文本": left_profile["paragraphs"], "对比文本": right_profile["paragraphs"], "规范化后原始": left_normalized["paragraphs"], "规范化后对比": right_normalized["paragraphs"]},
        ]
    )


def _render_overview_tab(comparison: Dict[str, Any]):
    summary = comparison["summary"]
    _render_normalization_notes(comparison)

    if not summary["changed"]:
        st.success("两侧文本在当前对比规则下完全一致。")
    else:
        finding_parts = [
            f"共识别 {summary['change_group_count']} 组差异",
            f"修改 {summary['modified_lines']} 行",
            f"新增 {summary['added_lines']} 行",
            f"删除 {summary['removed_lines']} 行",
        ]
        if summary["first_change_left_line"] or summary["first_change_right_line"]:
            finding_parts.append(
                f"首个变化位置 左 {summary['first_change_left_line'] or '-'} / 右 {summary['first_change_right_line'] or '-'}"
            )
        st.info(" | ".join(finding_parts))

    st.markdown("### 对比概览")
    metric_cols = st.columns(6)
    metric_cols[0].metric("文本相似度", f"{summary['text_similarity'] * 100:.1f}%")
    metric_cols[1].metric("行相似度", f"{summary['line_similarity'] * 100:.1f}%")
    metric_cols[2].metric("词级相似度", f"{summary['token_similarity'] * 100:.1f}%")
    metric_cols[3].metric("差异组", summary["change_group_count"])
    metric_cols[4].metric("修改行", summary["modified_lines"])
    metric_cols[5].metric("新增/删除", f"{summary['added_lines']}/{summary['removed_lines']}")

    st.markdown("### 文本画像")
    st.dataframe(_build_profile_table(comparison), use_container_width=True, hide_index=True)


def _render_line_diff_tab(comparison: Dict[str, Any]):
    rows = comparison["line_diff"]["rows"]
    blocks = comparison["line_diff"]["blocks"]
    unified_diff = comparison["line_diff"]["unified_diff"]

    if not rows:
        st.success("当前没有行级差异。")
        if unified_diff:
            st.code(unified_diff, language="diff")
        return

    filter_col1, filter_col2 = st.columns([1.2, 2])
    with filter_col1:
        selected_statuses = st.multiselect("差异类型", STATUS_OPTIONS, default=STATUS_OPTIONS)
    with filter_col2:
        keyword = st.text_input("关键词过滤", placeholder="只看包含某个关键词的差异行")

    filtered_rows = []
    normalized_keyword = keyword.strip().lower()
    for row in rows:
        if row["status"] not in selected_statuses:
            continue
        if normalized_keyword:
            haystack = f"{row.get('left_text', '')}\n{row.get('right_text', '')}".lower()
            if normalized_keyword not in haystack:
                continue
        filtered_rows.append(row)

    if filtered_rows:
        display_rows = []
        for row in filtered_rows:
            display_rows.append(
                {
                    "差异组": row["group"],
                    "状态": row["status"],
                    "原始行号": row["left_line_number"],
                    "对比行号": row["right_line_number"],
                    "原始文本": row["left_text"],
                    "对比文本": row["right_text"],
                    "行内相似度": row["similarity"],
                }
            )
        st.dataframe(pd.DataFrame(display_rows), use_container_width=True, hide_index=True)
    else:
        st.info("当前过滤条件下没有匹配的差异行。")

    st.markdown("### 差异块")
    st.dataframe(pd.DataFrame(blocks), use_container_width=True, hide_index=True)

    with st.expander("Unified Diff 预览", expanded=False):
        st.code(unified_diff or "(无差异)", language="diff")


def _render_token_diff_tab(comparison: Dict[str, Any], hide_equal_tokens: bool):
    token_summary = comparison["token_diff"]["summary"]
    token_rows = comparison["token_diff"]["rows"]

    metric_cols = st.columns(5)
    metric_cols[0].metric("原始词项", token_summary["left_token_count"])
    metric_cols[1].metric("对比词项", token_summary["right_token_count"])
    metric_cols[2].metric("新增词项", token_summary["inserted_tokens"])
    metric_cols[3].metric("删除词项", token_summary["deleted_tokens"])
    metric_cols[4].metric("替换块", token_summary["replaced_blocks"])

    st.markdown("### 词级高亮")
    st.markdown(
        render_token_diff_html(
            comparison["token_diff"]["segments"],
            hide_equal=hide_equal_tokens,
        ),
        unsafe_allow_html=True,
    )

    st.markdown("### 词级差异明细")
    if token_rows:
        st.dataframe(pd.DataFrame(token_rows), use_container_width=True, hide_index=True)
    else:
        st.success("当前没有词级差异。")


def _render_export_tab(comparison: Dict[str, Any]):
    left_source = st.session_state.text_comparison_left_source
    right_source = st.session_state.text_comparison_right_source
    markdown_report = build_comparison_report(
        comparison,
        left_source=left_source,
        right_source=right_source,
    )
    line_rows = comparison["line_diff"]["rows"]
    export_rows = pd.DataFrame(line_rows).to_csv(index=False) if line_rows else "group,status,left_line_number,right_line_number,left_text,right_text,similarity\n"

    button_cols = st.columns(4)
    with button_cols[0]:
        st.download_button(
            "导出 JSON",
            data=json.dumps(comparison, ensure_ascii=False, indent=2),
            file_name="text_comparison_report.json",
            mime="application/json",
            use_container_width=True,
        )
    with button_cols[1]:
        st.download_button(
            "导出 Markdown",
            data=markdown_report,
            file_name="text_comparison_report.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with button_cols[2]:
        st.download_button(
            "导出 Unified Diff",
            data=comparison["line_diff"]["unified_diff"] or "",
            file_name="text_comparison.diff",
            mime="text/x-diff",
            use_container_width=True,
        )
    with button_cols[3]:
        st.download_button(
            "导出差异 CSV",
            data=export_rows,
            file_name="text_comparison_changes.csv",
            mime="text/csv",
            use_container_width=True,
        )

    st.code(markdown_report, language="markdown")


def render_text_comparison_page():
    _ensure_defaults()
    show_doc("text_comparison")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 对比规则")
    ignore_case = st.sidebar.checkbox("忽略大小写", key="text_comparison_ignore_case")
    trim_line_edges = st.sidebar.checkbox("忽略行首尾空白", key="text_comparison_trim_edges")
    collapse_spaces = st.sidebar.checkbox("压缩连续空格", key="text_comparison_collapse_spaces")
    ignore_blank_lines = st.sidebar.checkbox("忽略空行", key="text_comparison_ignore_blank_lines")
    hide_equal_tokens = st.sidebar.checkbox("词级结果仅显示差异", key="text_comparison_hide_equal_tokens")

    st.caption("支持两侧分别导入文件或直接粘贴文本。结果会实时更新，并给出行级差异、词级高亮、统一 diff 和导出。")

    action_cols = st.columns([1, 1, 1, 2.2])
    with action_cols[0]:
        if st.button("载入示例", use_container_width=True):
            _load_example_pair()
            st.rerun()
    with action_cols[1]:
        if st.button("交换左右", use_container_width=True):
            _swap_sides()
            st.rerun()
    with action_cols[2]:
        if st.button("清空全部", use_container_width=True):
            _clear_all()
            st.rerun()
    with action_cols[3]:
        st.caption(
            f"原始: `{st.session_state.text_comparison_left_source}` | 对比: `{st.session_state.text_comparison_right_source}`"
        )

    left_col, right_col = st.columns(2)
    with left_col:
        _render_source_panel("left", "原始文本")
    with right_col:
        _render_source_panel("right", "对比文本")

    left_text = st.session_state.text_comparison_left_text
    right_text = st.session_state.text_comparison_right_text
    if not left_text and not right_text:
        st.info("请先输入任意一侧文本，或直接载入示例。")
        return

    comparison = compare_texts(
        left_text,
        right_text,
        ignore_case=ignore_case,
        trim_line_edges=trim_line_edges,
        collapse_inner_spaces=collapse_spaces,
        ignore_blank_lines=ignore_blank_lines,
    )

    overview_tab, line_tab, token_tab, export_tab = st.tabs(["概览", "行级差异", "词级高亮", "导出"])

    with overview_tab:
        _render_overview_tab(comparison)

    with line_tab:
        _render_line_diff_tab(comparison)

    with token_tab:
        _render_token_diff_tab(comparison, hide_equal_tokens=hide_equal_tokens)

    with export_tab:
        _render_export_tab(comparison)
