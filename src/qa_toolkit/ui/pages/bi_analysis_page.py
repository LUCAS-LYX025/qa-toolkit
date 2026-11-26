from __future__ import annotations

import hashlib
from typing import Any, Dict, Optional

import pandas as pd
import streamlit as st

from qa_toolkit.core.i18n import t
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.bi_analysis import BIAnalyzer
from qa_toolkit.ui.components.action_controls import primary_action_button, secondary_action_button
from qa_toolkit.ui.components.status_feedback import render_error_feedback, render_success_feedback, render_warning_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_empty_state, render_tool_page_hero, render_tool_tips


DEFAULT_STATE = {
    "bi_loaded_df": None,
    "bi_loaded_file_name": "",
    "bi_loaded_signature": "",
    "bi_loaded_sheet_name": "",
}


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def dataset_signature(uploaded_file, sheet_name: str) -> str:
    """签名带上内容摘要，避免同名同大小的不同文件复用旧分析结果。"""
    digest = hashlib.sha256(uploaded_file.getvalue()).hexdigest()[:16]
    return f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}:{sheet_name or ''}:{digest}"


@st.cache_data(show_spinner=False, max_entries=3)
def cached_analysis_context(signature: str, frame: pd.DataFrame) -> Dict[str, Any]:
    """同一数据集的字段画像/质量诊断只计算一次，跨 rerun 复用。"""
    return BIAnalyzer().build_analysis_context(frame)


def _clear_loaded_dataset(analyzer: BIAnalyzer) -> None:
    st.session_state.bi_loaded_df = None
    st.session_state.bi_loaded_file_name = ""
    st.session_state.bi_loaded_signature = ""
    st.session_state.bi_loaded_sheet_name = ""
    analyzer.reset_runtime_state()


def _load_dataset(
    analyzer: BIAnalyzer,
    uploaded_file,
    sheet_name: str,
    encoding: Optional[str] = None,
    delimiter: Optional[str] = None,
) -> None:
    if uploaded_file is None:
        render_warning_feedback("请先上传一个待分析的数据文件。")
        return

    signature = dataset_signature(uploaded_file, sheet_name)
    if signature != st.session_state.bi_loaded_signature:
        analyzer.reset_runtime_state()

    df, message = analyzer.load_data(
        uploaded_file,
        sheet_name=sheet_name or None,
        encoding=encoding or None,
        delimiter=delimiter or None,
    )
    if df is None:
        render_error_feedback(message)
        return

    st.session_state.bi_loaded_df = df
    st.session_state.bi_loaded_file_name = uploaded_file.name
    st.session_state.bi_loaded_signature = signature
    st.session_state.bi_loaded_sheet_name = sheet_name or ""
    if message:
        render_success_feedback(message)


def _render_dataset_summary(df: pd.DataFrame, context: Dict[str, Any]) -> None:
    overview = context["overview"]
    metric_cols = st.columns(6)
    metric_cols[0].metric("总行数", f"{overview['总行数']:,}")
    metric_cols[1].metric("总列数", overview["总列数"])
    metric_cols[2].metric("缺失值", f"{overview['缺失值']:,}")
    metric_cols[3].metric("重复行", f"{overview['重复行']:,}")
    metric_cols[4].metric("完整率", f"{overview['完整率(%)']:.1f}%")
    metric_cols[5].metric("内存占用", f"{overview['内存占用(MB)']:.2f} MB")

    st.caption(
        "已识别字段: "
        f"时间列 {len(context['datetime_columns'])} 个 | "
        f"数值列 {len(context['numeric_columns'])} 个 | "
        f"JSON 列 {len(context['json_columns'])} 个"
    )


def render_bi_analysis_page() -> None:
    _ensure_defaults()
    analyzer = BIAnalyzer()

    show_doc("bi_analyzer")
    render_tool_page_hero(
        "📊",
        "BI 数据分析工作台",
        "面向测试、开发、数据和业务场景做统一验数，覆盖模板下载、场景识别、质量诊断、可视化分析和报告导出。",
        tags=["CSV / Excel / JSON", "质量诊断", "透视趋势", "图表导出"],
        accent="#0f766e",
    )
    render_tool_tips(
        "推荐路径",
        [
            "先上传模板或真实数据并加载，再看“场景洞察”确认字段语义。",
            "进入“质量诊断”和“测试校验”优先排掉空值、重复键和时间格式问题。",
            "最后再看统计分析和图表工作台，避免基于脏数据输出结论。",
        ],
    )

    uploaded_file = analyzer.show_upload_section()
    selected_sheet = ""
    if uploaded_file is not None and uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        sheet_names = analyzer.get_excel_sheet_names(uploaded_file)
        if sheet_names:
            selected_sheet = st.selectbox(
                "选择工作表",
                sheet_names,
                index=sheet_names.index(st.session_state.bi_loaded_sheet_name)
                if st.session_state.bi_loaded_sheet_name in sheet_names
                else 0,
                key="bi_selected_sheet_name",
            )

    with st.expander("高级解析选项（非标准 CSV）", expanded=False):
        st.caption("留空时自动识别编码与分隔符；分号、制表符、竖线分隔的文件也可直接上传。")
        csv_encoding = st.text_input("文件编码", key="bi_csv_encoding", placeholder="例如 gb18030")
        csv_delimiter = st.text_input("字段分隔符", key="bi_csv_delimiter", placeholder="例如 ; 或 \\t")

    action_col1, action_col2, action_col3 = st.columns([1, 1, 3])
    with action_col1:
        if primary_action_button("开始加载数据", key="bi_load_dataset"):
            _load_dataset(analyzer, uploaded_file, selected_sheet, csv_encoding, csv_delimiter)
    with action_col2:
        if secondary_action_button("清空数据", key="bi_clear_dataset"):
            _clear_loaded_dataset(analyzer)
            st.rerun()
    with action_col3:
        current_file = st.session_state.bi_loaded_file_name or "未加载"
        if st.session_state.bi_loaded_sheet_name:
            current_file = f"{current_file} / {st.session_state.bi_loaded_sheet_name}"
        st.caption(t("当前数据集: `{file}`", file=t(current_file)))

    df = st.session_state.bi_loaded_df
    if not isinstance(df, pd.DataFrame):
        render_tool_empty_state(
            "等待数据集加载",
            "上传文件后点击“加载数据”，就可以继续做场景洞察、质量诊断、测试校验和图表分析。",
        )
        return

    if df.empty:
        st.warning("当前数据集没有数据行，分析功能暂不可用。请重新加载包含记录的文件。")
        st.caption(f"识别到字段: {', '.join(str(column) for column in df.columns) or '无'}")
        return

    context = cached_analysis_context(st.session_state.bi_loaded_signature, df)
    _render_dataset_summary(df, context)

    insight_tab, preview_tab, quality_tab, validation_tab, dev_tab, analysis_tab, viz_tab = st.tabs(
        [
            "场景洞察",
            "数据预览",
            "质量诊断",
            "测试校验",
            "开发/大数据",
            "统计分析",
            "图表与导出",
        ]
    )

    with insight_tab:
        analyzer.scenario_insights(df, context)
    with preview_tab:
        analyzer.data_preview(df, context)
    with quality_tab:
        analyzer.data_quality_analysis(df, context)
    with validation_tab:
        analyzer.validation_workbench(df, context)
    with dev_tab:
        analyzer.developer_workbench(df, context)
    with analysis_tab:
        basic_tab, corr_tab, pivot_tab, ts_tab = st.tabs(["基础统计", "相关性", "透视分析", "趋势分析"])
        with basic_tab:
            analyzer.basic_statistics(df, context)
        with corr_tab:
            analyzer.correlation_analysis(df, context)
        with pivot_tab:
            analyzer.create_pivot_table(df, context)
        with ts_tab:
            analyzer.time_series_analysis(df, context)
    with viz_tab:
        chart_tab, export_tab = st.tabs(["图表工作台", "导出报告"])
        with chart_tab:
            analyzer.create_dashboard(df, context)
        with export_tab:
            analyzer.export_report(df, context)
