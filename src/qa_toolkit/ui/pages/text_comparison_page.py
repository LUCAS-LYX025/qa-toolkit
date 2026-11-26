from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qa_toolkit.core.i18n import t
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
)
from qa_toolkit.utils.text_analysis import TEXT_UPLOAD_TYPES, decode_uploaded_text
from qa_toolkit.utils.text_comparison import (
    DEFAULT_LEFT_TEXT,
    DEFAULT_RIGHT_TEXT,
    build_comparison_report,
    build_export_payloads,
    build_text_profile,
    compare_texts,
    format_similarity,
    prepare_line_rows_for_display,
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
    "text_comparison_ignore_punctuation": False,
    "text_comparison_ignore_all_whitespace": False,
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
    st.caption(t("当前来源: `{src}`", src=st.session_state[source_key]))

    uploaded_file = st.file_uploader(
        f"导入{label}",
        type=TEXT_UPLOAD_TYPES,
        key=upload_key,
        help="支持 txt / md / json / csv / log / yaml / yml / doc / docx",
    )
    if uploaded_file is not None:
        st.caption(f"已选择: `{uploaded_file.name}` | {uploaded_file.size:,} bytes")
        if st.button("导入文件到当前文本框", key=load_button_key, width="stretch"):
            try:
                decoded_text = decode_uploaded_text(uploaded_file.getvalue(), filename=uploaded_file.name)
                _load_side_text(side, decoded_text, uploaded_file.name)
                st.rerun()
            except ValueError as exc:
                render_error_feedback(f"导入失败: {exc}")

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
        render_info_feedback("本次对比已应用以下规则:\n" + "\n".join(notes), title="规则预处理")


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

    if summary.get("empty_both"):
        render_info_feedback("两侧文本均为空，没有可对比内容。粘贴文本或载入示例后即可开始。", title="等待输入")
        return
    if summary.get("empty_side"):
        render_info_feedback("仅有一侧文本，相似度不代表内容重合度，请补充另一侧文本。", title="单侧输入")
        return
    if not summary["changed"]:
        render_success_feedback("两侧文本在当前对比规则下完全一致。", title="对比完成")
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
        render_info_feedback(" | ".join(finding_parts), title="差异摘要")
        if summary["first_change_left_line"] or summary["first_change_right_line"]:
            st.markdown(
                '<a href="#tc-first-change" style="color:#2563eb;">跳转到首个差异 →</a>',
                unsafe_allow_html=True,
            )

    if summary.get("matching_mode") == "sampled":
        render_info_feedback(
            "文本较大，已启用采样匹配模式；小改动可能被合并成较大的差异块。",
            title="匹配模式",
        )

    st.markdown("### 对比概览")
    metric_cols = st.columns(6)
    metric_cols[0].metric("文本相似度", format_similarity(summary["text_similarity"]))
    metric_cols[1].metric("行相似度", format_similarity(summary["line_similarity"]))
    metric_cols[2].metric("词级相似度", format_similarity(summary["token_similarity"]))
    metric_cols[3].metric("差异组", summary["change_group_count"])
    metric_cols[4].metric("修改行", summary["modified_lines"])
    metric_cols[5].metric("新增/删除", f"{summary['added_lines']}/{summary['removed_lines']}")

    st.markdown("### 文本画像")
    st.dataframe(_build_profile_table(comparison), width="stretch", hide_index=True)


def _render_line_diff_tab(comparison: Dict[str, Any]):
    rows = comparison["line_diff"]["rows"]
    blocks = comparison["line_diff"]["blocks"]
    unified_diff = comparison["line_diff"]["unified_diff"]

    st.markdown('<a id="tc-first-change"></a>', unsafe_allow_html=True)

    if not rows:
        render_success_feedback("当前没有行级差异。", title="行级差异")
        if unified_diff:
            st.code(unified_diff, language="diff")
        return

    filter_col1, filter_col2 = st.columns([1.2, 2])
    with filter_col1:
        selected_statuses = st.multiselect("差异类型", STATUS_OPTIONS, default=STATUS_OPTIONS)
    with filter_col2:
        keyword = st.text_input("关键词过滤", placeholder="只看包含某个关键词的差异行")

    filtered_rows = []
    normalized_keyword = keyword.strip().casefold()
    for row in rows:
        if row["status"] not in selected_statuses:
            continue
        if normalized_keyword:
            haystack = f"{row.get('left_text', '')}\n{row.get('right_text', '')}".casefold()
            if normalized_keyword not in haystack:
                continue
        filtered_rows.append(row)

    st.caption(f"当前显示 {len(filtered_rows)} / {len(rows)} 条差异行。")

    if filtered_rows:
        display_rows, truncated = prepare_line_rows_for_display(filtered_rows)
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "差异组": row["group"],
                        "状态": row["status"],
                        "原始行号": row["left_line_number"],
                        "对比行号": row["right_line_number"],
                        "原始文本": row["left_text"],
                        "对比文本": row["right_text"],
                        "行内相似度": row["similarity"],
                    }
                    for row in display_rows
                ]
            ),
            width="stretch",
            hide_index=True,
        )
        if truncated:
            st.caption(f"有 {truncated} 个长文本单元格已截断显示，完整内容请到『导出』Tab 下载。")
    else:
        render_info_feedback("当前过滤条件下没有匹配的差异行。", title="过滤结果")

    if st.checkbox("并排查看差异", key="text_comparison_side_by_side"):
        left_view = "\n".join(
            f"{row['left_line_number'] or '-'}: {row.get('left_text', '')}" for row in filtered_rows
        )
        right_view = "\n".join(
            f"{row['right_line_number'] or '-'}: {row.get('right_text', '')}" for row in filtered_rows
        )
        side_left, side_right = st.columns(2)
        with side_left:
            st.markdown("#### 原始文本")
            st.code(left_view or "（无内容）", language="text")
        with side_right:
            st.markdown("#### 对比文本")
            st.code(right_view or "（无内容）", language="text")

    st.markdown("### 差异块")
    st.dataframe(pd.DataFrame(blocks), width="stretch", hide_index=True)

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
        st.dataframe(pd.DataFrame(token_rows), width="stretch", hide_index=True)
    else:
        render_success_feedback("当前没有词级差异。", title="词级高亮")


def _render_export_tab(comparison: Dict[str, Any]):
    left_source = st.session_state.text_comparison_left_source
    right_source = st.session_state.text_comparison_right_source
    context = {"left_source": left_source, "right_source": right_source}
    markdown_report = build_comparison_report(
        comparison,
        left_source=left_source,
        right_source=right_source,
    )

    # 导出格式来自注册表，新增格式不需要再改这里。
    payloads = build_export_payloads(comparison, context)
    st.caption(f"当前提供 {len(payloads)} 种导出格式（可通过注册表扩展）。")
    button_cols = st.columns(len(payloads))
    for column, (name, filename, mime, data) in zip(button_cols, payloads):
        with column:
            st.download_button(
                f"导出 {name}",
                data=data,
                file_name=filename,
                mime=mime,
                width="stretch",
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
    ignore_punctuation = st.sidebar.checkbox("忽略标点符号", key="text_comparison_ignore_punctuation")
    ignore_all_whitespace = st.sidebar.checkbox("忽略所有空白字符", key="text_comparison_ignore_all_whitespace")
    hide_equal_tokens = st.sidebar.checkbox("词级结果仅显示差异", key="text_comparison_hide_equal_tokens")

    st.caption("支持两侧分别导入文件或直接粘贴文本。结果会实时更新，并给出行级差异、词级高亮、统一 diff 和导出。")
    if ignore_blank_lines:
        st.caption("已忽略空行：差异行号仍映射回源文件真实行号，可直接按行号定位。")

    action_cols = st.columns([1, 1, 1, 2.2])
    with action_cols[0]:
        if st.button("载入示例", width="stretch"):
            _load_example_pair()
            st.rerun()
    with action_cols[1]:
        if st.button("交换左右", width="stretch"):
            _swap_sides()
            st.rerun()
    with action_cols[2]:
        if st.button("清空全部", width="stretch"):
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

    # difflib.SequenceMatcher 在大文本上是平方级耗时，超限直接提示，避免每次 rerun 卡死。
    if max(len(left_text), len(right_text)) > 200_000:
        st.error("单侧文本超过 20 万字符，diff 计算耗时过长。建议只保留变化附近片段，或按文件分段对比。")
        return

    active_rules: List[str] = []
    if ignore_punctuation:
        active_rules.append("ignore_punctuation")
    if ignore_all_whitespace:
        active_rules.append("ignore_all_whitespace")

    comparison = compare_texts(
        left_text,
        right_text,
        ignore_case=ignore_case,
        trim_line_edges=trim_line_edges,
        collapse_inner_spaces=collapse_spaces,
        ignore_blank_lines=ignore_blank_lines,
        rules=active_rules,
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
