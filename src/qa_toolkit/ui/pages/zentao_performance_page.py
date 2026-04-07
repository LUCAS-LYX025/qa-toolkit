from __future__ import annotations

import io
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import (
    primary_action_button,
    secondary_action_button,
)
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
    render_warning_feedback,
)
from qa_toolkit.ui.components.tool_page_shell import render_tool_empty_state, render_tool_page_hero, render_tool_tips
from qa_toolkit.ui.components.workflow_panels import render_download_panel, render_workflow_guide
from qa_toolkit.utils.datetime_tools import DateTimeUtils


HOLIDAY_CALENDAR_OPTIONS = {"仅周末": None, **DateTimeUtils.get_supported_holiday_countries()}

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
    "zentao_holiday_calendar": "中国",
    "zentao_summary_keyword": "",
    "zentao_summary_only_timeout": False,
    "zentao_detail_keyword": "",
    "zentao_detail_status_filter": [],
}


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            if isinstance(value, list):
                st.session_state[key] = list(value)
            elif isinstance(value, dict):
                st.session_state[key] = dict(value)
            else:
                st.session_state[key] = value


def _get_db_config() -> Dict[str, Any]:
    return {
        "host": st.session_state.zentao_db_host.strip(),
        "port": int(st.session_state.zentao_db_port),
        "user": st.session_state.zentao_db_user.strip(),
        "password": st.session_state.zentao_db_password,
        "database": st.session_state.zentao_db_name.strip(),
    }


def _selected_holiday_country() -> Optional[str]:
    return HOLIDAY_CALENDAR_OPTIONS.get(st.session_state.zentao_holiday_calendar)


def _create_exporter() -> Optional[ZenTaoPerformanceExporter]:
    db_config = _get_db_config()
    if not all([db_config["host"], db_config["user"], db_config["database"]]):
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
        "holiday_country": _selected_holiday_country(),
    }


def _validate_query_inputs() -> bool:
    if st.session_state.zentao_selected_product_id is None:
        render_warning_feedback("请先选择产品后再执行统计。", title="缺少产品")
        return False
    if st.session_state.zentao_start_date > st.session_state.zentao_end_date:
        render_error_feedback("开始日期不能晚于结束日期。", title="时间范围无效")
        return False
    return True


def _apply_date_preset(preset: str) -> None:
    today = date.today()
    if preset == "last_7_days":
        st.session_state.zentao_start_date = today - timedelta(days=6)
        st.session_state.zentao_end_date = today
    elif preset == "last_30_days":
        st.session_state.zentao_start_date = today - timedelta(days=29)
        st.session_state.zentao_end_date = today
    elif preset == "this_week":
        start_date, end_date = DateTimeUtils.get_week_range(today)
        st.session_state.zentao_start_date = start_date
        st.session_state.zentao_end_date = end_date
    elif preset == "this_month":
        st.session_state.zentao_start_date = DateTimeUtils.get_first_day_of_month(today)
        st.session_state.zentao_end_date = DateTimeUtils.get_last_day_of_month(today)


def _clear_result_state() -> None:
    st.session_state.zentao_summary_df = None
    st.session_state.zentao_detail_df = None
    st.session_state.zentao_selected_person = ""
    st.session_state.zentao_summary_keyword = ""
    st.session_state.zentao_summary_only_timeout = False
    st.session_state.zentao_detail_keyword = ""
    st.session_state.zentao_detail_status_filter = []


def _pick_first_numeric_sum(df: pd.DataFrame, keywords: List[str]) -> Any:
    for column in df.columns:
        if any(keyword in str(column) for keyword in keywords) and pd.api.types.is_numeric_dtype(df[column]):
            return int(df[column].fillna(0).sum())
    return "-"


def _pick_first_numeric_column(df: pd.DataFrame, keywords: List[str]) -> Optional[str]:
    for column in df.columns:
        if any(keyword in str(column) for keyword in keywords) and pd.api.types.is_numeric_dtype(df[column]):
            return str(column)
    return None


def _pick_person_column(df: pd.DataFrame) -> str:
    preferred = "测试人员" if st.session_state.zentao_stat_type == "测试绩效统计" else "开发人员"
    if preferred in df.columns:
        return preferred
    for candidate in ["测试人员", "开发人员"]:
        if candidate in df.columns:
            return candidate
    return str(df.columns[0])


def _build_excel_bytes(sheets: Dict[str, pd.DataFrame]) -> Optional[bytes]:
    for engine in ["openpyxl", "xlsxwriter"]:
        try:
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine=engine) as writer:
                for sheet_name, dataframe in sheets.items():
                    dataframe.to_excel(writer, sheet_name=sheet_name[:31], index=False)
            buffer.seek(0)
            return buffer.getvalue()
        except ModuleNotFoundError:
            continue
    return None


def _render_summary_metrics(df: pd.DataFrame) -> None:
    metric_cols = st.columns(4)
    metric_cols[0].metric("人员数", len(df))
    metric_cols[1].metric("Bug 总量", _pick_first_numeric_sum(df, ["数量", "总bug"]))
    metric_cols[2].metric("一级超时", _pick_first_numeric_sum(df, ["一级超时"]))
    metric_cols[3].metric("普通超时", _pick_first_numeric_sum(df, ["普通超时"]))


def _safe_labels(selected_values: List[str], label_map: Dict[str, str], empty_text: str) -> str:
    if not selected_values:
        return empty_text
    return "、".join(label_map.get(value, value) for value in selected_values)


def _range_summary() -> Dict[str, Any]:
    return DateTimeUtils.summarize_date_range(
        st.session_state.zentao_start_date,
        st.session_state.zentao_end_date,
        country=_selected_holiday_country(),
    )


def _build_rule_lines() -> List[str]:
    holiday_label = st.session_state.zentao_holiday_calendar
    holiday_enabled = bool(_selected_holiday_country())
    holiday_text = "基础工作日时限 + 节假日剩余时长" if holiday_enabled else "未启用法定节假日顺延，仅按周末规则计算"
    return [
        "高优先级缺陷:",
        f"工作日建议 {st.session_state.zentao_high_priority_normal_hours} 小时内响应",
        f"周末建议 {st.session_state.zentao_high_priority_weekend_hours} 小时内响应",
        f"法定节假日: {holiday_text} ({holiday_label})",
        "",
        "普通优先级缺陷:",
        f"工作日建议 {st.session_state.zentao_normal_priority_normal_hours} 小时内响应",
        f"周末建议 {st.session_state.zentao_normal_priority_weekend_hours} 小时内响应",
        f"法定节假日: {'基础工作日时限 + 节假日剩余时长' if holiday_enabled else '未启用法定节假日顺延'}",
    ]


def _build_context_sheet(
    products: List[tuple[int, str]],
    role_label_map: Dict[str, str],
    bug_type_label_map: Dict[str, str],
) -> pd.DataFrame:
    product_name_map = {product_id: product_name for product_id, product_name in products}
    range_summary = _range_summary()
    high_holiday_rule = f"{st.session_state.zentao_high_priority_normal_hours}小时 + 节假日剩余时长"
    normal_holiday_rule = f"{st.session_state.zentao_normal_priority_normal_hours}小时 + 节假日剩余时长"
    holiday_rule = st.session_state.zentao_holiday_calendar if _selected_holiday_country() else "仅周末"

    rows = [
        {"项目": "统计类型", "说明": st.session_state.zentao_stat_type},
        {
            "项目": "产品",
            "说明": product_name_map.get(st.session_state.zentao_selected_product_id, str(st.session_state.zentao_selected_product_id)),
        },
        {
            "项目": "统计周期",
            "说明": f"{st.session_state.zentao_start_date} 至 {st.session_state.zentao_end_date}",
        },
        {"项目": "自然天数", "说明": range_summary["calendar_days"]},
        {"项目": "工作日数", "说明": range_summary["business_days"]},
        {"项目": "周末天数", "说明": range_summary["weekend_days"]},
        {"项目": "法定节假日天数", "说明": range_summary["holiday_only_days"] if _selected_holiday_country() else 0},
        {"项目": "节假日日历", "说明": holiday_rule},
        {"项目": "统计角色", "说明": _safe_labels(list(st.session_state.zentao_selected_roles), role_label_map, "全部角色")},
        {"项目": "排除 Bug 类型", "说明": _safe_labels(list(st.session_state.zentao_exclude_types), bug_type_label_map, "无")},
        {
            "项目": "高优先级规则",
            "说明": (
                f"工作日 {st.session_state.zentao_high_priority_normal_hours}h | "
                f"周末 {st.session_state.zentao_high_priority_weekend_hours}h | "
                f"节假日 {high_holiday_rule if _selected_holiday_country() else '未启用'}"
            ),
        },
        {
            "项目": "普通优先级规则",
            "说明": (
                f"工作日 {st.session_state.zentao_normal_priority_normal_hours}h | "
                f"周末 {st.session_state.zentao_normal_priority_weekend_hours}h | "
                f"节假日 {normal_holiday_rule if _selected_holiday_country() else '未启用'}"
            ),
        },
        {"项目": "导出时间", "说明": datetime.now().strftime("%Y-%m-%d %H:%M:%S")},
    ]
    return pd.DataFrame(rows)


def _parse_percentage(value: Any) -> float:
    text = str(value or "").strip().replace("%", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _filter_dataframe_by_keyword(df: pd.DataFrame, keyword: str) -> pd.DataFrame:
    normalized = keyword.strip().lower()
    if not normalized:
        return df
    mask = df.astype(str).apply(lambda column: column.str.lower().str.contains(normalized, na=False))
    return df[mask.any(axis=1)]


def _build_focus_table(df: pd.DataFrame) -> pd.DataFrame:
    timeout_column = _pick_first_numeric_column(df, ["总超时"])
    if timeout_column is None:
        return pd.DataFrame()

    person_column = _pick_person_column(df)
    role_column = "测试角色" if "测试角色" in df.columns else "开发角色" if "开发角色" in df.columns else None
    bug_total_column = _pick_first_numeric_column(df, ["提交bug数量", "开发总bug数", "总bug"])
    rate_column = next((str(column) for column in df.columns if "超时响应率" in str(column)), None)

    focus_df = df.copy()
    focus_df["_timeout_total"] = pd.to_numeric(focus_df[timeout_column], errors="coerce").fillna(0)
    focus_df["_timeout_rate"] = focus_df[rate_column].map(_parse_percentage) if rate_column else 0
    focus_df = focus_df.sort_values(["_timeout_total", "_timeout_rate"], ascending=[False, False]).head(5)

    display_columns = [column for column in [role_column, person_column, bug_total_column, timeout_column, rate_column] if column]
    return focus_df[display_columns]


def render_zentao_performance_page() -> None:
    _ensure_defaults()

    show_doc("zentao_performance_stats")
    render_tool_page_hero(
        "📈",
        "禅道绩效统计",
        "连接禅道数据库后生成测试绩效、开发绩效和超时明细，适合绩效复盘、缺陷响应分析和数据核对。",
        tags=["测试绩效", "开发绩效", "超时明细", "节假日顺延", "Excel / CSV 导出"],
        accent="#15803d",
    )
    render_workflow_guide(
        title="建议操作顺序",
        description="先连库拿到产品和角色，再配置统计口径，先看汇总趋势，最后按人回查超时明细。",
        steps=[
            "连接数据库并加载产品、角色、缺陷类型",
            "选择产品、周期、统计角色和排除类型",
            "确认工作日、周末和法定节假日响应规则",
            "生成汇总报表后再按人员回查超时明细",
        ],
        tips=["建议先用月度或季度范围", "汇总和明细共用同一套超时规则", "导出文件会附带统计口径说明"],
        eyebrow="统计流程",
    )
    render_tool_tips(
        "使用建议",
        [
            "优先先看汇总中的超时率和总超时次数，再决定是否追到人。",
            "法定节假日顺延默认按中国节假日日历计算，也可以切回“仅周末”口径。",
            "导出结果会附带“统计说明”Sheet，方便复盘时还原本次统计口径。",
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

        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            if primary_action_button("连接并加载数据", key="zentao_connect_button"):
                _load_metadata()
                if st.session_state.zentao_connection_ready:
                    render_success_feedback("数据库连接成功，产品、角色和缺陷类型已加载。")
        with action_col2:
            if secondary_action_button("清空统计结果", key="zentao_clear_results"):
                _clear_result_state()
                render_info_feedback("已清空汇总结果、明细结果和筛选条件。", title="结果已重置")
        with action_col3:
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
        if st.session_state.zentao_holiday_calendar not in HOLIDAY_CALENDAR_OPTIONS:
            st.session_state.zentao_holiday_calendar = "仅周末"

        st.markdown("### 快捷时间范围")
        preset_col1, preset_col2, preset_col3, preset_col4 = st.columns(4)
        with preset_col1:
            if secondary_action_button("最近 7 天", key="zentao_preset_last_7"):
                _apply_date_preset("last_7_days")
        with preset_col2:
            if secondary_action_button("最近 30 天", key="zentao_preset_last_30"):
                _apply_date_preset("last_30_days")
        with preset_col3:
            if secondary_action_button("本周", key="zentao_preset_this_week"):
                _apply_date_preset("this_week")
        with preset_col4:
            if secondary_action_button("本月", key="zentao_preset_this_month"):
                _apply_date_preset("this_month")

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

        date_col1, date_col2, date_col3 = st.columns(3)
        with date_col1:
            st.date_input("开始日期", key="zentao_start_date")
        with date_col2:
            st.date_input("结束日期", key="zentao_end_date")
        with date_col3:
            st.selectbox("节假日日历", list(HOLIDAY_CALENDAR_OPTIONS.keys()), key="zentao_holiday_calendar")

        range_summary = _range_summary()
        metric_cols = st.columns(4)
        metric_cols[0].metric("自然天数", range_summary["calendar_days"])
        metric_cols[1].metric("工作日", range_summary["business_days"])
        metric_cols[2].metric("周末", range_summary["weekend_days"])
        metric_cols[3].metric("法定节假日", range_summary["holiday_only_days"] if _selected_holiday_country() else "未启用")

        filter_col1, filter_col2 = st.columns(2)
        with filter_col1:
            st.multiselect(
                "统计角色",
                [role_key for role_key, _ in roles],
                default=st.session_state.zentao_selected_roles,
                format_func=lambda role_key: role_label_map.get(role_key, role_key),
                key="zentao_selected_roles",
            )
        with filter_col2:
            st.multiselect(
                "排除的 Bug 类型",
                [type_key for type_key, _ in bug_types],
                default=st.session_state.zentao_exclude_types,
                format_func=lambda type_key: bug_type_label_map.get(type_key, type_key),
                key="zentao_exclude_types",
            )

        st.markdown("### SLA 规则设置")
        timeout_col1, timeout_col2, timeout_col3, timeout_col4 = st.columns(4)
        with timeout_col1:
            st.number_input("一级优先级工作日时限(小时)", min_value=1, key="zentao_high_priority_normal_hours")
        with timeout_col2:
            st.number_input("一级优先级周末时限(小时)", min_value=1, key="zentao_high_priority_weekend_hours")
        with timeout_col3:
            st.number_input("普通优先级工作日时限(小时)", min_value=1, key="zentao_normal_priority_normal_hours")
        with timeout_col4:
            st.number_input("普通优先级周末时限(小时)", min_value=1, key="zentao_normal_priority_weekend_hours")

        render_info_feedback("\n".join(_build_rule_lines()), title="当前响应规则")

        with st.expander("当前统计口径预览", expanded=True):
            st.code(
                "\n".join(
                    [
                        f"统计类型: {st.session_state.zentao_stat_type}",
                        f"产品: {product_name_map.get(st.session_state.zentao_selected_product_id, '-')}",
                        f"统计周期: {st.session_state.zentao_start_date} 至 {st.session_state.zentao_end_date}",
                        f"节假日日历: {st.session_state.zentao_holiday_calendar}",
                        f"统计角色: {_safe_labels(list(st.session_state.zentao_selected_roles), role_label_map, '全部角色')}",
                        f"排除类型: {_safe_labels(list(st.session_state.zentao_exclude_types), bug_type_label_map, '无')}",
                    ]
                )
            )

        if primary_action_button("开始汇总统计", key="zentao_run_summary"):
            if _validate_query_inputs():
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
                        st.session_state.zentao_detail_status_filter = []
                        if summary_df is not None and not summary_df.empty:
                            person_column = _pick_person_column(summary_df)
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
            control_col1, control_col2 = st.columns([2, 1])
            with control_col1:
                summary_keyword = st.text_input(
                    "结果筛选",
                    key="zentao_summary_keyword",
                    placeholder="按人员、角色、超时率或 Bug 总量快速过滤",
                )
            with control_col2:
                st.checkbox("只看存在超时的人员", key="zentao_summary_only_timeout")

            filtered_summary = _filter_dataframe_by_keyword(summary_df, summary_keyword)
            timeout_total_column = _pick_first_numeric_column(filtered_summary, ["总超时"])
            if timeout_total_column and st.session_state.zentao_summary_only_timeout:
                filtered_summary = filtered_summary[
                    pd.to_numeric(filtered_summary[timeout_total_column], errors="coerce").fillna(0) > 0
                ]

            if filtered_summary.empty:
                render_info_feedback("当前筛选条件下没有匹配结果。", title="汇总结果为空")
            else:
                _render_summary_metrics(filtered_summary)
                focus_df = _build_focus_table(filtered_summary)
                if not focus_df.empty:
                    st.markdown("### 关注清单")
                    st.dataframe(focus_df, use_container_width=True, hide_index=True)

                st.markdown("### 汇总明细")
                st.dataframe(filtered_summary, use_container_width=True, hide_index=True)

                context_df = _build_context_sheet(products, role_label_map, bug_type_label_map)
                excel_bytes = _build_excel_bytes({"汇总报表": filtered_summary, "统计说明": context_df})
                csv_bytes = filtered_summary.to_csv(index=False).encode("utf-8-sig")
                if excel_bytes is None:
                    render_warning_feedback("当前环境缺少 Excel 导出依赖，已保留 CSV 导出。", title="Excel 导出不可用")
                render_download_panel(
                    title="导出汇总结果",
                    description="导出的 Excel 会附带统计口径说明；CSV 适合继续做透视和二次分析。",
                    items=[
                        {
                            "label": "导出 Excel",
                            "data": excel_bytes,
                            "file_name": "zentao_summary.xlsx",
                            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "key": "summary_excel",
                            "caption": "包含汇总报表 + 统计说明",
                        },
                        {
                            "label": "导出 CSV",
                            "data": csv_bytes,
                            "file_name": "zentao_summary.csv",
                            "mime": "text/csv",
                            "key": "summary_csv",
                            "caption": "仅导出当前筛选后的汇总结果",
                        },
                    ],
                    key_prefix="zentao_summary_download",
                    metrics=[
                        {"label": "当前行数", "value": len(filtered_summary)},
                        {"label": "当前人员", "value": filtered_summary[_pick_person_column(filtered_summary)].nunique()},
                    ],
                )

    with detail_tab:
        summary_df = st.session_state.zentao_summary_df
        if not isinstance(summary_df, pd.DataFrame) or summary_df.empty:
            render_info_feedback("先生成汇总报表，再查询指定人员的超时明细。", title="暂无明细结果")
            return

        person_column = _pick_person_column(summary_df)
        person_options = summary_df[person_column].dropna().astype(str).tolist()
        if not person_options:
            render_info_feedback("当前汇总结果缺少可回查的人员字段。", title="无法查询明细")
            return
        if person_options and st.session_state.zentao_selected_person not in person_options:
            st.session_state.zentao_selected_person = person_options[0]

        detail_col1, detail_col2 = st.columns([2, 1])
        with detail_col1:
            st.selectbox("选择人员", person_options, key="zentao_selected_person")
        with detail_col2:
            if primary_action_button("查询超时明细", key="zentao_run_detail"):
                if _validate_query_inputs():
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
                            st.session_state.zentao_detail_status_filter = []
                            if detail_df is not None and not detail_df.empty:
                                render_success_feedback(f"超时明细查询完成，本次共返回 {len(detail_df)} 条记录。")
                            else:
                                render_info_feedback("当前人员在该时间范围内没有超时明细。", title="明细结果为空")
                        finally:
                            exporter.close_connection()

        detail_df = st.session_state.zentao_detail_df
        if isinstance(detail_df, pd.DataFrame) and not detail_df.empty:
            filter_col1, filter_col2 = st.columns([2, 1.4])
            with filter_col1:
                detail_keyword = st.text_input(
                    "明细检索",
                    key="zentao_detail_keyword",
                    placeholder="按 BugID、标题、状态、类型快速过滤",
                )
            with filter_col2:
                status_options = sorted(str(value) for value in detail_df["状态"].dropna().unique()) if "状态" in detail_df.columns else []
                default_statuses = [
                    status for status in (st.session_state.zentao_detail_status_filter or status_options) if status in status_options
                ]
                st.multiselect(
                    "状态筛选",
                    status_options,
                    default=default_statuses,
                    key="zentao_detail_status_filter",
                )

            filtered_detail = _filter_dataframe_by_keyword(detail_df, detail_keyword)
            if "状态" in filtered_detail.columns and st.session_state.zentao_detail_status_filter:
                filtered_detail = filtered_detail[
                    filtered_detail["状态"].astype(str).isin(st.session_state.zentao_detail_status_filter)
                ]

            if filtered_detail.empty:
                render_info_feedback("当前筛选条件下没有匹配的超时明细。", title="明细结果为空")
            else:
                duration_column = (
                    "响应处理时长_小时"
                    if "响应处理时长_小时" in filtered_detail.columns
                    else "处理时长_小时"
                    if "处理时长_小时" in filtered_detail.columns
                    else None
                )
                metric_cols = st.columns(4)
                metric_cols[0].metric("超时记录", len(filtered_detail))
                metric_cols[1].metric("一级超时", int((filtered_detail.get("超时类型") == "一级超时").sum()) if "超时类型" in filtered_detail.columns else "-")
                metric_cols[2].metric("普通超时", int((filtered_detail.get("超时类型") == "普通超时").sum()) if "超时类型" in filtered_detail.columns else "-")
                if duration_column is not None:
                    avg_duration = pd.to_numeric(filtered_detail[duration_column], errors="coerce").dropna()
                    metric_cols[3].metric("平均处理时长", f"{avg_duration.mean():.1f}h" if not avg_duration.empty else "-")
                else:
                    metric_cols[3].metric("平均处理时长", "-")

                st.dataframe(filtered_detail, use_container_width=True, hide_index=True)

                context_df = _build_context_sheet(products, role_label_map, bug_type_label_map)
                excel_bytes = _build_excel_bytes({"超时明细": filtered_detail, "统计说明": context_df})
                csv_bytes = filtered_detail.to_csv(index=False).encode("utf-8-sig")
                if excel_bytes is None:
                    render_warning_feedback("当前环境缺少 Excel 导出依赖，已保留 CSV 导出。", title="Excel 导出不可用")
                render_download_panel(
                    title="导出明细结果",
                    description="适合直接贴到缺陷复盘、绩效复核或排期跟踪文档中。",
                    items=[
                        {
                            "label": "导出明细 Excel",
                            "data": excel_bytes,
                            "file_name": "zentao_timeout_detail.xlsx",
                            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "key": "detail_excel",
                            "caption": "包含超时明细 + 统计说明",
                        },
                        {
                            "label": "导出明细 CSV",
                            "data": csv_bytes,
                            "file_name": "zentao_timeout_detail.csv",
                            "mime": "text/csv",
                            "key": "detail_csv",
                            "caption": "仅导出当前筛选后的明细结果",
                        },
                    ],
                    key_prefix="zentao_detail_download",
                    metrics=[{"label": "当前记录", "value": len(filtered_detail)}],
                )
