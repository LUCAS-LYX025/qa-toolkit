from __future__ import annotations

import datetime
from typing import Dict

import pandas as pd
import pytz
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import primary_action_button
from qa_toolkit.ui.components.status_feedback import render_error_feedback, render_info_feedback, render_success_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_page_hero, render_tool_tips
from qa_toolkit.utils.datetime_tools import DateTimeUtils


TIME_UNIT_SECONDS = {
    "秒": 1,
    "分钟": 60,
    "小时": 3600,
    "天": 86400,
    "周": 7 * 86400,
    "月(按30天)": 30 * 86400,
    "年(按365天)": 365 * 86400,
}


def _render_timestamp_tab() -> None:
    st.markdown("### 时间戳转换")

    tz_options = DateTimeUtils.get_timezones()
    convert_col1, convert_col2 = st.columns(2)

    with convert_col1:
        timestamp_text = st.text_input("输入时间戳", key="time_tool_timestamp_input", placeholder="支持秒级或毫秒级")
        unit_mode = st.selectbox("时间戳类型", ["自动识别", "秒", "毫秒"], key="time_tool_timestamp_mode")
        timezone_label = st.selectbox("展示时区", list(tz_options.keys()), key="time_tool_timestamp_tz")
        if primary_action_button("开始转换为日期时间", key="time_tool_convert_to_datetime"):
            try:
                raw_value = float(timestamp_text.strip())
                if unit_mode == "毫秒" or (unit_mode == "自动识别" and abs(raw_value) >= 1_000_000_000_000):
                    raw_value = raw_value / 1000
                timezone_name = tz_options[timezone_label]
                timezone = pytz.timezone(timezone_name)
                target_dt = datetime.datetime.fromtimestamp(raw_value, tz=timezone)

                render_success_feedback("时间戳已经成功转换为日期时间。")
                st.code(
                    "\n".join(
                        [
                            f"时区: {timezone_name}",
                            f"日期时间: {target_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}",
                            f"ISO8601: {target_dt.isoformat()}",
                            f"星期: 周{target_dt.isoweekday()}",
                        ]
                    )
                )
            except Exception as exc:
                render_error_feedback(f"时间戳转换失败: {exc}")

    with convert_col2:
        selected_date = st.date_input("选择日期", key="time_tool_date_input")
        selected_time = st.time_input("选择时间", key="time_tool_time_input", value=datetime.time(9, 0, 0))
        timezone_label = st.selectbox("输入时间所属时区", list(tz_options.keys()), key="time_tool_datetime_tz")
        if primary_action_button("开始转换为时间戳", key="time_tool_convert_to_timestamp"):
            timezone = pytz.timezone(tz_options[timezone_label])
            combined = datetime.datetime.combine(selected_date, selected_time)
            localized = timezone.localize(combined)
            seconds = localized.timestamp()

            render_success_feedback("日期时间已经成功转换为时间戳。")
            st.code(
                "\n".join(
                    [
                        f"原始时间: {localized.strftime('%Y-%m-%d %H:%M:%S %Z%z')}",
                        f"秒级时间戳: {int(seconds)}",
                        f"毫秒级时间戳: {int(seconds * 1000)}",
                    ]
                )
            )

    now = datetime.datetime.now()
    metric_cols = st.columns(3)
    metric_cols[0].metric("当前本地时间", now.strftime("%H:%M:%S"))
    metric_cols[1].metric("当前秒级时间戳", int(now.timestamp()))
    metric_cols[2].metric("当前毫秒级时间戳", int(now.timestamp() * 1000))


def _render_unit_conversion_tab() -> None:
    st.markdown("### 时间单位换算")

    value_col1, value_col2 = st.columns([1, 1])
    with value_col1:
        numeric_value = st.number_input("输入数值", min_value=0.0, value=1.0, key="time_tool_unit_value")
    with value_col2:
        source_unit = st.selectbox("原始单位", list(TIME_UNIT_SECONDS.keys()), key="time_tool_source_unit")

    base_seconds = float(numeric_value) * TIME_UNIT_SECONDS[source_unit]
    rows = []
    for unit_name, seconds in TIME_UNIT_SECONDS.items():
        rows.append({"单位": unit_name, "换算结果": round(base_seconds / seconds, 6)})
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("月和年按近似值换算，分别按 30 天和 365 天处理。")


def _render_date_calculator_tab() -> None:
    st.markdown("### 日期计算与信息查询")

    start_col, end_col = st.columns(2)
    with start_col:
        start_date = st.date_input("开始日期", key="time_tool_start_date")
    with end_col:
        end_date = st.date_input("结束日期", key="time_tool_end_date")

    diff_days = DateTimeUtils.date_difference(start_date, end_date)
    business_days = DateTimeUtils.count_business_days(min(start_date, end_date), max(start_date, end_date))
    week_start, week_end = DateTimeUtils.get_week_range(start_date)

    metric_cols = st.columns(5)
    metric_cols[0].metric("自然日差值", diff_days)
    metric_cols[1].metric("工作日数量", business_days)
    metric_cols[2].metric("开始日期周数", DateTimeUtils.get_week_number(start_date))
    metric_cols[3].metric("开始日期季度", f"Q{DateTimeUtils.get_quarter(start_date)}")
    metric_cols[4].metric("是否周末", "是" if DateTimeUtils.is_weekend(start_date) else "否")

    render_info_feedback(
        f"开始日期所在周: {week_start.strftime('%Y-%m-%d')} 至 {week_end.strftime('%Y-%m-%d')} | "
        f"开始日期节假日标记: {'是' if DateTimeUtils.is_holiday(start_date, 'CN') else '否'}",
        title="日期补充信息",
    )

    offset_col1, offset_col2, offset_col3 = st.columns(3)
    with offset_col1:
        offset_days = st.number_input("偏移天数", value=7, key="time_tool_offset_days")
    with offset_col2:
        offset_months = st.number_input("偏移月数", value=1, key="time_tool_offset_months")
    with offset_col3:
        birthday = st.date_input("生日 / 出生日期", value=start_date, key="time_tool_birthday")

    result_rows = [
        {"场景": "开始日期 + 天数", "结果": DateTimeUtils.add_days(start_date, int(offset_days)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 - 天数", "结果": DateTimeUtils.subtract_days(start_date, int(offset_days)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 + 月数", "结果": DateTimeUtils.add_months(start_date, int(offset_months)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 - 月数", "结果": DateTimeUtils.subtract_months(start_date, int(offset_months)).strftime("%Y-%m-%d")},
        {"场景": "当月第一天", "结果": DateTimeUtils.get_first_day_of_month(start_date).strftime("%Y-%m-%d")},
        {"场景": "当月最后一天", "结果": DateTimeUtils.get_last_day_of_month(start_date).strftime("%Y-%m-%d")},
        {"场景": "年龄", "结果": DateTimeUtils.get_age(birthday)},
        {"场景": "生肖", "结果": DateTimeUtils.get_chinese_zodiac(birthday.year)},
        {"场景": "星座", "结果": DateTimeUtils.get_constellation(birthday.month, birthday.day)},
    ]
    st.dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)


def _render_advanced_tab() -> None:
    sla_tab, cron_tab, perf_tab, tz_tab = st.tabs(["SLA/工作时间", "Cron", "性能测试", "时区转换"])

    with sla_tab:
        start_date = st.date_input("SLA 开始日期", key="time_tool_sla_date")
        start_time = st.time_input("SLA 开始时间", key="time_tool_sla_time", value=datetime.time(9, 0, 0))
        sla_hours = st.number_input("SLA 时长(小时)", min_value=1.0, value=24.0, key="time_tool_sla_hours")
        work_col1, work_col2 = st.columns(2)
        with work_col1:
            work_start = st.number_input("工作开始小时", min_value=0, max_value=23, value=9, key="time_tool_work_start")
        with work_col2:
            work_end = st.number_input("工作结束小时", min_value=1, max_value=24, value=18, key="time_tool_work_end")

        start_dt = datetime.datetime.combine(start_date, start_time)
        due_dt = DateTimeUtils.calculate_sla_due_date(start_dt, sla_hours, int(work_start), int(work_end))
        st.code(
            "\n".join(
                [
                    f"SLA 开始时间: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"SLA 到期时间: {due_dt.strftime('%Y-%m-%d %H:%M:%S')}",
                    f"工作时间差(小时): {DateTimeUtils.calculate_business_hours_diff(start_dt, due_dt, (int(work_start), int(work_end))):.2f}",
                ]
            )
        )

    with cron_tab:
        cron_expression = st.text_input("Cron 表达式", value="0 9 * * 1-5", key="time_tool_cron_expression")
        cron_base_date = st.date_input("Cron 基准日期", key="time_tool_cron_base")
        cron_count = st.number_input("生成次数", min_value=1, max_value=20, value=5, key="time_tool_cron_count")
        next_runs = DateTimeUtils.generate_cron_next_runs(cron_expression, cron_base_date, int(cron_count))
        st.dataframe(pd.DataFrame({"下一次执行时间": [str(item) for item in next_runs]}), use_container_width=True, hide_index=True)

    with perf_tab:
        duration = st.number_input("持续时间(秒)", min_value=1.0, value=10.0, key="time_tool_perf_duration")
        rps = st.number_input("每秒请求数", min_value=1.0, value=5.0, key="time_tool_perf_rps")
        response_times_text = st.text_area(
            "响应时间列表(ms)",
            value="120, 98, 240, 300, 180, 90, 110, 150, 600, 220",
            key="time_tool_response_times",
        )

        timestamps = DateTimeUtils.get_performance_test_timestamps(duration, rps)
        parsed_response_times = [float(item.strip()) for item in response_times_text.split(",") if item.strip()]
        percentiles = DateTimeUtils.calculate_response_time_percentiles(parsed_response_times)

        metric_cols = st.columns(4)
        metric_cols[0].metric("生成时间点", len(timestamps))
        metric_cols[1].metric("P50", percentiles.get(50, "-"))
        metric_cols[2].metric("P95", percentiles.get(95, "-"))
        metric_cols[3].metric("P99", percentiles.get(99, "-"))

    with tz_tab:
        tz_options = DateTimeUtils.get_timezones()
        from_col, to_col = st.columns(2)
        with from_col:
            source_tz = st.selectbox("源时区", list(tz_options.keys()), key="time_tool_from_tz")
        with to_col:
            target_tz = st.selectbox("目标时区", list(tz_options.keys()), index=1, key="time_tool_to_tz")
        source_date = st.date_input("源日期", key="time_tool_tz_date")
        source_time = st.time_input("源时间", key="time_tool_tz_time", value=datetime.time(10, 0, 0))
        source_dt = datetime.datetime.combine(source_date, source_time)
        converted = DateTimeUtils.get_timezone_conversion(source_dt, tz_options[source_tz], tz_options[target_tz])
        st.code(
            "\n".join(
                [
                    f"源时间: {source_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_options[source_tz]})",
                    f"转换结果: {converted.strftime('%Y-%m-%d %H:%M:%S %Z%z')}",
                ]
            )
        )


def render_time_processor_page() -> None:
    show_doc("time_processor")
    render_tool_page_hero(
        "⏰",
        "时间处理工具",
        "覆盖时间戳转换、日期计算、SLA 到期、Cron 预测、时区换算和性能测试时间辅助，适合测试联调和排障。",
        tags=["时间戳", "日期计算", "SLA", "Cron", "时区转换"],
        accent="#0f766e",
    )
    render_tool_tips(
        "推荐路径",
        [
            "接口联调用“时间戳转换”，先确认秒级还是毫秒级。",
            "缺陷响应或工单时效场景用“SLA/工作时间”页做工作时长估算。",
            "定时任务排查优先看 Cron 预览结果，能快速验证下次触发时间。",
        ],
    )

    timestamp_tab, convert_tab, date_tab, advanced_tab = st.tabs(
        ["时间戳转换", "单位换算", "日期计算", "高级能力"]
    )

    with timestamp_tab:
        _render_timestamp_tab()
    with convert_tab:
        _render_unit_conversion_tab()
    with date_tab:
        _render_date_calculator_tab()
    with advanced_tab:
        _render_advanced_tab()
