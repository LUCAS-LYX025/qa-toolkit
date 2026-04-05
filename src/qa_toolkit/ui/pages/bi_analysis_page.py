from __future__ import annotations

from typing import Any, Dict

import pandas as pd
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.bi_analysis import BIAnalyzer


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


def _clear_loaded_dataset(analyzer: BIAnalyzer) -> None:
    st.session_state.bi_loaded_df = None
    st.session_state.bi_loaded_file_name = ""
    st.session_state.bi_loaded_signature = ""
    st.session_state.bi_loaded_sheet_name = ""
    analyzer.reset_runtime_state()


def _load_dataset(analyzer: BIAnalyzer, uploaded_file, sheet_name: str) -> None:
    if uploaded_file is None:
        st.warning("请先上传一个待分析的数据文件。")
        return

    signature = f"{uploaded_file.name}:{getattr(uploaded_file, 'size', 0)}:{sheet_name or ''}"
    if signature != st.session_state.bi_loaded_signature:
        analyzer.reset_runtime_state()

    df, message = analyzer.load_data(uploaded_file, sheet_name=sheet_name or None)
    if df is None:
        st.error(message)
        return

    st.session_state.bi_loaded_df = df
    st.session_state.bi_loaded_file_name = uploaded_file.name
    st.session_state.bi_loaded_signature = signature
    st.session_state.bi_loaded_sheet_name = sheet_name or ""
    if message:
        st.success(message)


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
    st.markdown('<div class="category-card">📊 BI 数据分析工作台</div>', unsafe_allow_html=True)

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

    action_col1, action_col2, action_col3 = st.columns([1, 1, 3])
    with action_col1:
        if st.button("加载数据", use_container_width=True, key="bi_load_dataset"):
            _load_dataset(analyzer, uploaded_file, selected_sheet)
    with action_col2:
        if st.button("清空当前数据", use_container_width=True, key="bi_clear_dataset"):
            _clear_loaded_dataset(analyzer)
            st.rerun()
    with action_col3:
        current_file = st.session_state.bi_loaded_file_name or "未加载"
        if st.session_state.bi_loaded_sheet_name:
            current_file = f"{current_file} / {st.session_state.bi_loaded_sheet_name}"
        st.caption(f"当前数据集: `{current_file}`")

    df = st.session_state.bi_loaded_df
    if not isinstance(df, pd.DataFrame):
        st.info("上传文件后点击“加载数据”，即可进入场景洞察、质量诊断、校验与可视化分析。")
        return

    context = analyzer.build_analysis_context(df)
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
