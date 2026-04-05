from __future__ import annotations

import io
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button
from qa_toolkit.ui.components.status_feedback import render_info_feedback, render_success_feedback, render_warning_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_empty_state, render_tool_page_hero, render_tool_tips


DEFAULT_STATE = {
    "zentao_db_host": "127.0.0.1",
    "zentao_db_port": 3306,
    "zentao_db_user": "",
    "zentao_db_password": "",
    "zentao_db_name": "zentao",
    "zentao_products": [],
    "zentao_roles": [],
    "zentao_bug_types": [],
    "zentao_connection_ready": False,
    "zentao_selected_product_id": None,
    "zentao_selected_roles": [],
    "zentao_exclude_types": [],
    "zentao_start_date": date.today() - timedelta(days=30),
    "zentao_end_date": date.today(),
    "zentao_stat_type": "测试绩效统计",
    "zentao_summary_df": None,
    "zentao_detail_df": None,
    "zentao_selected_person": "",
    "zentao_high_priority_normal_hours": 24,
    "zentao_high_priority_weekend_hours": 72,
    "zentao_normal_priority_normal_hours": 72,
    "zentao_normal_priority_weekend_hours": 120,
}


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _get_db_config() -> Dict[str, Any]:
    return {
        "host": st.session_state.zentao_db_host.strip(),
        "port": int(st.session_state.zentao_db_port),
        "user": st.session_state.zentao_db_user.strip(),
        "passwd": st.session_state.zentao_db_password,
        "db": st.session_state.zentao_db_name.strip(),
    }


def _create_exporter() -> Optional[ZenTaoPerformanceExporter]:
    db_config = _get_db_config()
    if not all([db_config["host"], db_config["user"], db_config["db"]]):
        render_warning_feedback("请先填写完整的数据库连接信息。")
        return None

    exporter = ZenTaoPerformanceExporter(db_config)
    if getattr(exporter, "mysql_db", None) is None:
        return None
    return exporter


def _load_metadata() -> None:
    exporter = _create_exporter()
    if exporter is None:
        st.session_state.zentao_connection_ready = False
        return

    try:
        products = exporter.get_products()
        roles = exporter.get_user_roles()
        bug_types = exporter.get_bug_types()
    finally:
        exporter.close_connection()

    st.session_state.zentao_products = products
    st.session_state.zentao_roles = roles
    st.session_state.zentao_bug_types = bug_types
    st.session_state.zentao_connection_ready = True

    if products and st.session_state.zentao_selected_product_id is None:
        st.session_state.zentao_selected_product_id = products[0][0]
    if roles and not st.session_state.zentao_selected_roles:
        st.session_state.zentao_selected_roles = [role_key for role_key, _ in roles]


def _build_query_config() -> Dict[str, Any]:
    selected_roles = list(st.session_state.zentao_selected_roles)
    if not selected_roles:
        selected_roles = [role_key for role_key, _ in st.session_state.zentao_roles]
    if not selected_roles:
        selected_roles = ["__NO_ROLE__"]

    exclude_types = list(st.session_state.zentao_exclude_types)
    if not exclude_types:
        exclude_types = ["__NO_EXCLUDE__"]

    return {
        "roles": selected_roles,
        "exclude_types": exclude_types,
        "start_date": str(st.session_state.zentao_start_date),
        "end_date": str(st.session_state.zentao_end_date),
        "high_priority_normal_hours": int(st.session_state.zentao_high_priority_normal_hours),
        "high_priority_weekend_hours": int(st.session_state.zentao_high_priority_weekend_hours),
        "normal_priority_normal_hours": int(st.session_state.zentao_normal_priority_normal_hours),
        "normal_priority_weekend_hours": int(st.session_state.zentao_normal_priority_weekend_hours),
    }


def _pick_first_numeric_sum(df: pd.DataFrame, keywords: List[str]) -> Any:
    for column in df.columns:
        if any(keyword in str(column) for keyword in keywords) and pd.api.types.is_numeric_dtype(df[column]):
            return int(df[column].fillna(0).sum())
    return "-"


def _build_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for sheet_name, dataframe in sheets.items():
            dataframe.to_excel(writer, sheet_name=sheet_name[:31], index=False)
    buffer.seek(0)
    return buffer.getvalue()


def _render_summary_metrics(df: pd.DataFrame) -> None:
    metric_cols = st.columns(4)
    metric_cols[0].metric("人员数", len(df))
    metric_cols[1].metric("Bug 总量", _pick_first_numeric_sum(df, ["数量", "bug"]))
    metric_cols[2].metric("一级超时", _pick_first_numeric_sum(df, ["一级超时"]))
    metric_cols[3].metric("普通超时", _pick_first_numeric_sum(df, ["普通超时"]))


def render_zentao_performance_page() -> None:
    _ensure_defaults()

    show_doc("zentao_performance_stats")
    render_tool_page_hero(
        "📈",
        "禅道绩效统计",
        "连接禅道数据库后生成测试绩效、开发绩效和超时明细，适合绩效复盘、缺陷响应分析和数据核对。",
        tags=["测试绩效", "开发绩效", "超时明细", "Excel / CSV 导出"],
        accent="#15803d",
    )
    render_tool_tips(
        "使用建议",
        [
            "先连接数据库并加载产品、角色和缺陷类型，再开始配置统计参数。",
            "角色和排除类型尽量贴近实际考核口径，否则汇总结果会偏差较大。",
            "汇总先看趋势，争议数据再用“超时明细”按人员回查原始 Bug 记录。",
        ],
    )

    with st.expander("数据库连接配置", expanded=True):
        col1, col2, col3 = st.columns([1.5, 1, 1.2])
        with col1:
            st.text_input("数据库主机", key="zentao_db_host")
        with col2:
            st.number_input("端口", min_value=1, max_value=65535, key="zentao_db_port")
        with col3:
            st.text_input("数据库名", key="zentao_db_name")

        col4, col5 = st.columns(2)
        with col4:
            st.text_input("用户名", key="zentao_db_user")
        with col5:
            st.text_input("密码", key="zentao_db_password", type="password")

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if primary_action_button("连接并加载数据", key="zentao_connect_button"):
                _load_metadata()
                if st.session_state.zentao_connection_ready:
                    render_success_feedback("数据库连接成功，产品、角色和缺陷类型已加载。")
        with action_col2:
            if st.session_state.zentao_connection_ready:
                render_success_feedback("当前连接状态正常，可继续执行统计分析。", title="连接状态")
            else:
                st.caption("当前状态: 未连接")

    if not st.session_state.zentao_connection_ready:
        render_tool_empty_state(
            "等待数据库连接",
            "先完成数据库连接并加载基础数据，再继续配置统计周期、角色范围和超时阈值。",
        )
        return

    products = list(st.session_state.zentao_products)
    roles = list(st.session_state.zentao_roles)
    bug_types = list(st.session_state.zentao_bug_types)
    role_label_map = {role_key: role_name for role_key, role_name in roles}
    bug_type_label_map = {type_key: type_name for type_key, type_name in bug_types}

    config_tab, summary_tab, detail_tab = st.tabs(["统计配置", "汇总报表", "超时明细"])

    with config_tab:
        product_ids = [product_id for product_id, _ in products]
        product_name_map = {product_id: product_name for product_id, product_name in products}
        if product_ids and st.session_state.zentao_selected_product_id not in product_ids:
            st.session_state.zentao_selected_product_id = product_ids[0]

        select_col1, select_col2 = st.columns(2)
        with select_col1:
            st.selectbox(
                "产品",
                product_ids,
                format_func=lambda product_id: product_name_map.get(product_id, str(product_id)),
                key="zentao_selected_product_id",
            )
        with select_col2:
            st.radio(
                "统计类型",
                ["测试绩效统计", "开发绩效统计"],
                horizontal=True,
                key="zentao_stat_type",
            )

        date_col1, date_col2 = st.columns(2)
        with date_col1:
            st.date_input("开始日期", key="zentao_start_date")
        with date_col2:
            st.date_input("结束日期", key="zentao_end_date")

        st.multiselect(
            "统计角色",
            [role_key for role_key, _ in roles],
            default=st.session_state.zentao_selected_roles,
            format_func=lambda role_key: role_label_map.get(role_key, role_key),
            key="zentao_selected_roles",
        )
        st.multiselect(
            "排除的 Bug 类型",
            [type_key for type_key, _ in bug_types],
            default=st.session_state.zentao_exclude_types,
            format_func=lambda type_key: bug_type_label_map.get(type_key, type_key),
            key="zentao_exclude_types",
        )

        st.markdown("### 超时阈值设置")
        timeout_col1, timeout_col2, timeout_col3, timeout_col4 = st.columns(4)
        with timeout_col1:
            st.number_input("一级优先级工作日时限(小时)", min_value=1, key="zentao_high_priority_normal_hours")
        with timeout_col2:
            st.number_input("一级优先级周末时限(小时)", min_value=1, key="zentao_high_priority_weekend_hours")
        with timeout_col3:
            st.number_input("普通优先级工作日时限(小时)", min_value=1, key="zentao_normal_priority_normal_hours")
        with timeout_col4:
            st.number_input("普通优先级周末时限(小时)", min_value=1, key="zentao_normal_priority_weekend_hours")

        if primary_action_button("开始汇总统计", key="zentao_run_summary"):
            exporter = _create_exporter()
            if exporter is not None:
                try:
                    query_config = _build_query_config()
                    if st.session_state.zentao_stat_type == "测试绩效统计":
                        summary_df = exporter.query_qa_stats(st.session_state.zentao_selected_product_id, query_config)
                    else:
                        summary_df = exporter.query_dev_stats(st.session_state.zentao_selected_product_id, query_config)
                    st.session_state.zentao_summary_df = summary_df
                    st.session_state.zentao_detail_df = None
                    if summary_df is not None and not summary_df.empty:
                        person_column = summary_df.columns[0]
                        st.session_state.zentao_selected_person = str(summary_df.iloc[0][person_column])
                        render_success_feedback(f"汇总统计完成，本次共生成 {len(summary_df)} 行报表。")
                    else:
                        render_info_feedback("当前条件下没有查询到统计结果。", title="汇总结果为空")
                finally:
                    exporter.close_connection()

    with summary_tab:
        summary_df = st.session_state.zentao_summary_df
        if not isinstance(summary_df, pd.DataFrame) or summary_df.empty:
            render_info_feedback("先在“统计配置”页生成汇总报表。", title="暂无汇总结果")
        else:
            _render_summary_metrics(summary_df)
            st.dataframe(summary_df, use_container_width=True, hide_index=True)

            excel_bytes = _build_excel_bytes({"汇总报表": summary_df})
            csv_bytes = summary_df.to_csv(index=False).encode("utf-8-sig")
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                action_download_button(
                    "导出 Excel",
                    data=excel_bytes,
                    file_name="zentao_summary.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with export_col2:
                action_download_button(
                    "导出 CSV",
                    data=csv_bytes,
                    file_name="zentao_summary.csv",
                    mime="text/csv",
                )

    with detail_tab:
        summary_df = st.session_state.zentao_summary_df
        if not isinstance(summary_df, pd.DataFrame) or summary_df.empty:
            render_info_feedback("先生成汇总报表，再查询指定人员的超时明细。", title="暂无明细结果")
            return

        person_column = summary_df.columns[0]
        person_options = summary_df[person_column].dropna().astype(str).tolist()
        if person_options and st.session_state.zentao_selected_person not in person_options:
            st.session_state.zentao_selected_person = person_options[0]

        detail_col1, detail_col2 = st.columns([2, 1])
        with detail_col1:
            st.selectbox("选择人员", person_options, key="zentao_selected_person")
        with detail_col2:
            if primary_action_button("查询超时明细", key="zentao_run_detail"):
                exporter = _create_exporter()
                if exporter is not None:
                    try:
                        query_config = _build_query_config()
                        if st.session_state.zentao_stat_type == "测试绩效统计":
                            detail_df = exporter.query_qa_timeout_bugs_detail(
                                st.session_state.zentao_selected_person,
                                st.session_state.zentao_selected_product_id,
                                str(st.session_state.zentao_start_date),
                                str(st.session_state.zentao_end_date),
                                query_config,
                            )
                        else:
                            detail_df = exporter.query_timeout_bugs_detail(
                                st.session_state.zentao_selected_person,
                                st.session_state.zentao_selected_product_id,
                                str(st.session_state.zentao_start_date),
                                str(st.session_state.zentao_end_date),
                                query_config,
                            )
                        st.session_state.zentao_detail_df = detail_df
                        if detail_df is not None and not detail_df.empty:
                            render_success_feedback(f"超时明细查询完成，本次共返回 {len(detail_df)} 条记录。")
                        else:
                            render_info_feedback("当前人员在该时间范围内没有超时明细。", title="明细结果为空")
                    finally:
                        exporter.close_connection()

        detail_df = st.session_state.zentao_detail_df
        if isinstance(detail_df, pd.DataFrame) and not detail_df.empty:
            st.dataframe(detail_df, use_container_width=True, hide_index=True)

            excel_bytes = _build_excel_bytes({"超时明细": detail_df})
            csv_bytes = detail_df.to_csv(index=False).encode("utf-8-sig")
            export_col1, export_col2 = st.columns(2)
            with export_col1:
                action_download_button(
                    "导出明细 Excel",
                    data=excel_bytes,
                    file_name="zentao_timeout_detail.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            with export_col2:
                action_download_button(
                    "导出明细 CSV",
                    data=csv_bytes,
                    file_name="zentao_timeout_detail.csv",
                    mime="text/csv",
                )
