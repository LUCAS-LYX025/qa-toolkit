from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.utils.text_analysis import (
    DEFAULT_SAMPLE_TEXT,
    TEXT_UPLOAD_TYPES,
    analyze_text,
    build_export_payload,
    build_text_report,
    decode_uploaded_text,
    export_rows,
    preprocess_text,
)


DEFAULT_STATE = {
    "word_counter_text": "",
    "word_counter_source_name": "手动输入",
    "word_counter_target_words": 1000,
    "word_counter_target_chars": 5000,
    "word_counter_show_charts": True,
    "word_counter_ignore_case": True,
    "word_counter_trim_edges": False,
    "word_counter_collapse_blank_lines": False,
    "word_counter_collapse_spaces": False,
}

SPECIAL_CHARS_DISPLAY = {
    " ": "[空格]",
    "\n": "[换行]",
    "\t": "[制表符]",
    "\r": "[回车]",
}


def _ensure_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _display_char(char: str) -> str:
    return SPECIAL_CHARS_DISPLAY.get(char, char)


def _render_progress(label: str, current: int, target: int):
    if target <= 0:
        return

    progress_ratio = min(current / target, 1.0) if target else 0.0
    st.write(f"{label}: {current:,} / {target:,}")
    st.progress(progress_ratio)
    if current >= target:
        st.success(f"{label}目标已达成")
    else:
        st.caption(f"完成度 {progress_ratio * 100:.1f}%")


def _build_markdown_report(payload: Dict[str, Any]) -> str:
    top_keywords = payload.get("top_keywords", [])
    keyword_lines = "\n".join(f"- `{item['keyword']}`: {item['count']}" for item in top_keywords[:10]) or "- 无"
    suggestion_lines = "\n".join(
        f"- **{item['title']}**: {item['message']}"
        for item in payload.get("suggestions", [])
    ) or "- 无"
    preprocess_lines = "\n".join(f"- {line}" for line in payload.get("preprocess", {}).get("changes", [])) or "- 未启用预处理"

    return f"""# 文本统计报告

- 生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
- 来源: {payload.get("source", "手动输入")}

## 基础统计

- 字符数（含空格）: {payload["basic"]["total_chars"]}
- 字符数（不含空格）: {payload["basic"]["total_chars_no_spaces"]}
- 字符数（不含空白）: {payload["basic"]["total_chars_no_whitespace"]}
- 单词数: {payload["basic"]["total_words"]}
- 阅读单元: {payload["basic"]["reading_units"]}
- 行数: {payload["basic"]["total_lines"]}
- 非空行: {payload["basic"]["non_empty_lines"]}
- 句子数: {payload["basic"]["total_sentences"]}
- 段落数: {payload["basic"]["total_paragraphs"]}

## 质量指标

- 平均词长: {payload["quality"]["avg_word_length"]}
- 平均句长: {payload["quality"]["avg_sentence_length"]}
- 平均段落长: {payload["quality"]["avg_paragraph_length"]}
- 阅读时间: {payload["quality"]["reading_time_minutes"]} 分钟
- 词汇多样性: {payload["quality"]["lexical_diversity"]}

## 预处理

{preprocess_lines}

## 关键词 Top10

{keyword_lines}

## 建议

{suggestion_lines}
"""


def _render_summary_metrics(analysis: Dict[str, Any]):
    basic = analysis["basic"]
    metrics_row1 = st.columns(6)
    metrics_row1[0].metric("字符数（含空格）", f"{basic['total_chars']:,}")
    metrics_row1[1].metric("字符数（不含空格）", f"{basic['total_chars_no_spaces']:,}")
    metrics_row1[2].metric("字符数（不含空白）", f"{basic['total_chars_no_whitespace']:,}")
    metrics_row1[3].metric("单词数", f"{basic['total_words']:,}")
    metrics_row1[4].metric("阅读单元", f"{basic['reading_units']:,}")
    metrics_row1[5].metric("段落数", f"{basic['total_paragraphs']:,}")

    metrics_row2 = st.columns(4)
    metrics_row2[0].metric("总行数", f"{basic['total_lines']:,}")
    metrics_row2[1].metric("非空行", f"{basic['non_empty_lines']:,}")
    metrics_row2[2].metric("句子数", f"{basic['total_sentences']:,}")
    metrics_row2[3].metric("英文词数", f"{basic['latin_words']:,}")


def _render_key_findings(analysis: Dict[str, Any], preprocess_result: Dict[str, Any]):
    diagnostics = analysis["diagnostics"]
    quality = analysis["quality"]
    top_keywords = analysis["frequencies"]["top_keywords"]

    findings: List[str] = []
    if preprocess_result["changed"]:
        findings.append(f"预处理后减少 {preprocess_result['character_delta']} 个字符")
    if diagnostics["repeated_line_count"] > 0:
        findings.append(f"检测到 {diagnostics['repeated_line_count']} 组重复行")
    if diagnostics["blank_lines"] > 0:
        findings.append(f"包含 {diagnostics['blank_lines']} 个空行")
    if diagnostics["lines_with_edge_spaces"] > 0:
        findings.append(f"{diagnostics['lines_with_edge_spaces']} 行带首尾空白")
    if top_keywords:
        findings.append(f"高频关键词: {top_keywords[0][0]} x {top_keywords[0][1]}")
    findings.append(f"预计阅读时间 {quality['reading_time_minutes']:.1f} 分钟")

    st.info(" | ".join(findings))


def _render_overview_tab(analysis: Dict[str, Any]):
    char_types = analysis["char_types"]
    quality = analysis["quality"]
    suggestions = analysis["suggestions"]

    st.markdown("### 字符类型")
    char_cols = st.columns(6)
    char_cols[0].metric("非中文字母", f"{char_types['latin_letters']:,}")
    char_cols[1].metric("数字", f"{char_types['digits']:,}")
    char_cols[2].metric("标点", f"{char_types['punctuation']:,}")
    char_cols[3].metric("空格", f"{char_types['spaces']:,}")
    char_cols[4].metric("中文字符", f"{char_types['chinese_chars']:,}")
    char_cols[5].metric("换行/制表", f"{char_types['tabs'] + char_types['newlines']:,}")

    st.markdown("### 文本质量")
    quality_cols = st.columns(5)
    quality_cols[0].metric("平均词长", f"{quality['avg_word_length']:.1f}")
    quality_cols[1].metric("平均句长", f"{quality['avg_sentence_length']:.1f}")
    quality_cols[2].metric("平均段落长", f"{quality['avg_paragraph_length']:.1f}")
    quality_cols[3].metric("阅读时间", f"{quality['reading_time_minutes']:.1f} 分钟")
    quality_cols[4].metric("词汇多样性", f"{quality['lexical_diversity']:.2f}")

    st.markdown("### 诊断建议")
    for item in suggestions:
        if item["level"] == "warning":
            st.warning(f"**{item['title']}**: {item['message']}")
        elif item["level"] == "success":
            st.success(f"**{item['title']}**: {item['message']}")
        else:
            st.info(f"**{item['title']}**: {item['message']}")


def _render_frequency_tab(analysis: Dict[str, Any], show_charts: bool):
    keyword_rows = analysis["frequencies"]["top_keywords"]
    repeated_keywords = analysis["keyword_stats"]["repeated_keywords"]
    repeated_lines = analysis["repeated_lines"]
    top_characters = analysis["frequencies"]["top_characters"]

    left_col, right_col = st.columns(2)

    with left_col:
        st.markdown("### 关键词频率")
        if keyword_rows:
            keyword_df = pd.DataFrame(keyword_rows, columns=["关键词", "次数"])
            st.dataframe(keyword_df, use_container_width=True, hide_index=True)
            if show_charts:
                fig = px.bar(
                    keyword_df.head(10),
                    x="次数",
                    y="关键词",
                    orientation="h",
                    title="Top 10 关键词",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("当前文本没有可用的关键词统计结果。")

    with right_col:
        st.markdown("### 字符频率")
        if top_characters:
            char_df = pd.DataFrame(
                [{"字符": _display_char(char), "次数": count} for char, count in top_characters]
            )
            st.dataframe(char_df.head(10), use_container_width=True, hide_index=True)
            if show_charts:
                fig = px.bar(
                    char_df.head(10),
                    x="次数",
                    y="字符",
                    orientation="h",
                    title="Top 10 字符",
                )
                fig.update_layout(yaxis={"categoryorder": "total ascending"})
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("当前文本没有字符频率数据。")

    bottom_left, bottom_right = st.columns(2)
    with bottom_left:
        st.markdown("### 高频重复关键词")
        if repeated_keywords:
            st.dataframe(
                pd.DataFrame(repeated_keywords, columns=["关键词", "出现次数"]),
                use_container_width=True,
                hide_index=True,
            )
        else:
            st.success("未发现重复关键词。")

    with bottom_right:
        st.markdown("### 重复行")
        if repeated_lines:
            st.dataframe(pd.DataFrame(repeated_lines), use_container_width=True, hide_index=True)
        else:
            st.success("未发现重复行。")

    if show_charts:
        st.markdown("### 文本结构")
        structure_df = pd.DataFrame(
            [
                {"维度": "字符", "数量": analysis["basic"]["total_chars"]},
                {"维度": "单词", "数量": analysis["basic"]["total_words"]},
                {"维度": "句子", "数量": analysis["basic"]["total_sentences"]},
                {"维度": "行数", "数量": analysis["basic"]["total_lines"]},
                {"维度": "段落", "数量": analysis["basic"]["total_paragraphs"]},
            ]
        )
        st.plotly_chart(
            px.bar(structure_df, x="维度", y="数量", color="维度", title="文本结构概览"),
            use_container_width=True,
        )


def _render_diagnostics_tab(
    analysis: Dict[str, Any],
    preprocess_result: Dict[str, Any],
    source_name: str,
):
    diagnostics = analysis["diagnostics"]
    long_lines = analysis["long_lines"]

    diag_cols = st.columns(5)
    diag_cols[0].metric("空行数", diagnostics["blank_lines"])
    diag_cols[1].metric("首尾空白行", diagnostics["lines_with_edge_spaces"])
    diag_cols[2].metric("连续空格段", diagnostics["double_space_runs"])
    diag_cols[3].metric("重复行组数", diagnostics["repeated_line_count"])
    diag_cols[4].metric("长行数", diagnostics["long_line_count"])

    if preprocess_result["changed"]:
        info_col1, info_col2 = st.columns([4, 1.2])
        with info_col1:
            st.info("当前统计基于预处理后的文本。你可以直接把清洗结果覆盖回编辑区，继续修改或导出。")
            st.caption("；".join(preprocess_result["changes"]))
        with info_col2:
            if st.button("回填清洗结果", use_container_width=True):
                st.session_state.word_counter_text = preprocess_result["text"]
                st.session_state.word_counter_source_name = f"{source_name}（已清洗）"
                st.rerun()

        st.markdown("### 清洗后预览")
        st.text_area(
            "清洗结果",
            value=preprocess_result["text"],
            height=220,
            disabled=True,
            label_visibility="collapsed",
        )
    else:
        st.caption("当前未触发预处理变更。")

    st.markdown("### 长行预警")
    if long_lines:
        long_line_df = pd.DataFrame(long_lines)
        st.dataframe(long_line_df, use_container_width=True, hide_index=True)
    else:
        st.success("未发现明显过长的行。")


def _render_export_tab(
    analysis: Dict[str, Any],
    preprocess_result: Dict[str, Any],
    source_name: str,
):
    payload = build_export_payload(analysis, preprocess_result=preprocess_result, source_label=source_name)
    csv_rows = export_rows(payload)
    text_report = build_text_report(payload)
    markdown_report = _build_markdown_report(payload)
    cleaned_text = preprocess_result["text"] if preprocess_result["changed"] else analysis["normalized_text"]

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.download_button(
            "导出 JSON",
            data=json.dumps(payload, ensure_ascii=False, indent=2),
            file_name="文本统计报告.json",
            mime="application/json",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            "导出 CSV",
            data=pd.DataFrame(csv_rows).to_csv(index=False),
            file_name="文本统计报告.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with col3:
        st.download_button(
            "导出 TXT",
            data=text_report,
            file_name="文本统计报告.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with col4:
        st.download_button(
            "导出 Markdown",
            data=markdown_report,
            file_name="文本统计报告.md",
            mime="text/markdown",
            use_container_width=True,
        )

    extra_col1, extra_col2 = st.columns(2)
    with extra_col1:
        st.download_button(
            "下载清洗后文本",
            data=cleaned_text,
            file_name="文本清洗结果.txt",
            mime="text/plain",
            use_container_width=True,
        )
    with extra_col2:
        st.code(markdown_report, language="markdown")


def render_word_counter_page():
    _ensure_defaults()
    show_doc("word_counter")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 目标设置")
    target_words = st.sidebar.number_input(
        "目标单词数",
        min_value=0,
        step=100,
        key="word_counter_target_words",
    )
    target_chars = st.sidebar.number_input(
        "目标字符数",
        min_value=0,
        step=500,
        key="word_counter_target_chars",
    )

    st.sidebar.markdown("### 统计选项")
    show_charts = st.sidebar.checkbox("显示图表", key="word_counter_show_charts")
    ignore_case = st.sidebar.checkbox("关键词忽略大小写", key="word_counter_ignore_case")

    st.sidebar.markdown("### 预处理")
    trim_edges = st.sidebar.checkbox("清理每行首尾空白", key="word_counter_trim_edges")
    collapse_blank_lines = st.sidebar.checkbox(
        "合并连续空行",
        key="word_counter_collapse_blank_lines",
    )
    collapse_spaces = st.sidebar.checkbox(
        "压缩行内连续空格",
        key="word_counter_collapse_spaces",
    )

    st.caption("支持手动输入、示例载入和文件导入。统计结果会覆盖基础指标、结构诊断、关键词频率和导出报告。")

    action_col1, action_col2, action_col3 = st.columns([1, 1, 2.5])
    with action_col1:
        if st.button("载入示例", use_container_width=True):
            st.session_state.word_counter_text = DEFAULT_SAMPLE_TEXT
            st.session_state.word_counter_source_name = "示例文本"
            st.rerun()
    with action_col2:
        if st.button("清空文本", use_container_width=True):
            st.session_state.word_counter_text = ""
            st.session_state.word_counter_source_name = "手动输入"
            st.rerun()
    with action_col3:
        st.caption(f"当前来源: `{st.session_state.word_counter_source_name}`")

    with st.expander("文件导入与快捷操作", expanded=True):
        upload_col1, upload_col2 = st.columns([2.4, 1])
        with upload_col1:
            uploaded_file = st.file_uploader(
                "导入文本文件",
                type=TEXT_UPLOAD_TYPES,
                help="支持 txt / md / json / csv / log / yaml / yml / doc / docx",
            )
            if uploaded_file is not None:
                st.caption(f"已选择: `{uploaded_file.name}` | {uploaded_file.size:,} bytes")
        with upload_col2:
            if st.button("导入到编辑器", disabled=uploaded_file is None, use_container_width=True):
                try:
                    st.session_state.word_counter_text = decode_uploaded_text(
                        uploaded_file.getvalue(),
                        filename=uploaded_file.name,
                    )
                    st.session_state.word_counter_source_name = uploaded_file.name
                    st.rerun()
                except ValueError as exc:
                    st.error(f"导入失败: {exc}")

    text_input = st.text_area(
        "输入要统计的文本",
        height=260,
        placeholder="在这里粘贴文本、日志、需求说明、接口文档或 Markdown 内容...",
        key="word_counter_text",
    )

    if not text_input:
        st.info("请先输入文本，或直接载入示例 / 导入文件。")
        return

    preprocess_result = preprocess_text(
        text_input,
        trim_line_edges=trim_edges,
        collapse_blank_lines=collapse_blank_lines,
        collapse_inner_spaces=collapse_spaces,
    )

    analysis_source_text = preprocess_result["text"] if preprocess_result["changed"] else text_input
    analysis = analyze_text(
        analysis_source_text,
        ignore_case=ignore_case,
        repeated_keyword_threshold=2,
    )

    _render_summary_metrics(analysis)
    _render_key_findings(analysis, preprocess_result)

    if target_words > 0 or target_chars > 0:
        st.markdown("### 目标进度")
        progress_col1, progress_col2 = st.columns(2)
        with progress_col1:
            _render_progress("单词进度", analysis["basic"]["total_words"], int(target_words))
        with progress_col2:
            _render_progress("字符进度", analysis["basic"]["total_chars"], int(target_chars))

    overview_tab, frequency_tab, diagnostics_tab, export_tab = st.tabs(
        ["概览", "词频与结构", "诊断与清洗", "导出"]
    )

    with overview_tab:
        _render_overview_tab(analysis)

    with frequency_tab:
        _render_frequency_tab(analysis, show_charts=show_charts)

    with diagnostics_tab:
        _render_diagnostics_tab(
            analysis,
            preprocess_result=preprocess_result,
            source_name=st.session_state.word_counter_source_name,
        )

    with export_tab:
        _render_export_tab(
            analysis,
            preprocess_result=preprocess_result,
            source_name=st.session_state.word_counter_source_name,
        )
