from __future__ import annotations

import datetime
import re
from typing import Any, Dict, List

import pandas as pd
import pytz
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import primary_action_button, secondary_action_button
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
    render_warning_feedback,
)
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

DEFAULT_BATCH_SAMPLE = "\n".join(
    [
        "1712361600",
        "1712361600000",
        "2026-04-06 09:30:00",
        "2026-04-06T01:30:00Z",
    ]
)

CRON_PRESETS = {
    "工作日 09:00": "0 9 * * 1-5",
    "每 5 分钟": "*/5 * * * *",
    "每天 00:00": "0 0 * * *",
    "每周一 10:00": "0 10 * * 1",
}

DEFAULT_STATE: Dict[str, Any] = {
    "time_tool_timestamp_input": "",
    "time_tool_timestamp_mode": "自动识别",
    "time_tool_timestamp_tz": "北京",
    "time_tool_date_input": datetime.date.today(),
    "time_tool_time_input": datetime.time(9, 0, 0),
    "time_tool_datetime_tz": "北京",
    "time_tool_batch_input": DEFAULT_BATCH_SAMPLE,
    "time_tool_batch_timezone": "北京",
    "time_tool_unit_value": 1.0,
    "time_tool_source_unit": "小时",
    "time_tool_start_date": datetime.date.today(),
    "time_tool_end_date": datetime.date.today(),
    "time_tool_holiday_calendar": "仅周末",
    "time_tool_offset_days": 7,
    "time_tool_offset_months": 1,
    "time_tool_business_offset": 3,
    "time_tool_birthday": datetime.date.today(),
    "time_tool_sla_date": datetime.date.today(),
    "time_tool_sla_time": datetime.time(9, 0, 0),
    "time_tool_sla_hours": 24.0,
    "time_tool_work_start": 9,
    "time_tool_work_end": 18,
    "time_tool_cron_preset": "工作日 09:00",
    "time_tool_cron_expression": CRON_PRESETS["工作日 09:00"],
    "time_tool_cron_base": datetime.date.today(),
    "time_tool_cron_count": 5,
    "time_tool_perf_duration": 10.0,
    "time_tool_perf_rps": 5.0,
    "time_tool_response_times": "120, 98, 240, 300, 180, 90, 110, 150, 600, 220",
    "time_tool_from_tz": "北京",
    "time_tool_to_tz": "纽约",
    "time_tool_tz_date": datetime.date.today(),
    "time_tool_tz_time": datetime.time(10, 0, 0),
    "time_tool_timestamp_result": None,
    "time_tool_datetime_result": None,
    "time_tool_batch_result": [],
    "time_tool_range_summary": None,
    "time_tool_cron_result": [],
    "time_tool_perf_result": None,
    "time_tool_timezone_snapshot": [],
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


def _weekday_label(target: datetime.datetime | datetime.date) -> str:
    names = ["一", "二", "三", "四", "五", "六", "日"]
    return f"周{names[target.weekday()]}"


def _format_lines(lines: List[str]) -> str:
    return "\n".join(lines)


def _convert_timestamp_input(raw_text: str, unit_mode: str, timezone_name: str) -> Dict[str, Any]:
    value = float(str(raw_text).strip())
    if unit_mode == "毫秒" or (unit_mode == "自动识别" and abs(value) >= 1_000_000_000_000):
        seconds = value / 1000
        precision = "毫秒"
    else:
        seconds = value
        precision = "秒"

    timezone = pytz.timezone(timezone_name)
    parsed_dt = datetime.datetime.fromtimestamp(seconds, tz=timezone)
    return {
        "precision": precision,
        "timezone": timezone_name,
        "datetime": parsed_dt,
        "timestamp_seconds": int(seconds),
        "timestamp_milliseconds": int(seconds * 1000),
    }


def _parse_response_times(text: str) -> List[float]:
    chunks = [item.strip() for item in re.split(r"[\s,，]+", str(text or "").strip()) if item.strip()]
    if not chunks:
        raise ValueError("请至少输入一个响应时间")
    return [float(item) for item in chunks]


def _apply_range_preset(preset: str) -> None:
    today = datetime.date.today()
    if preset == "today":
        start_date = today
        end_date = today
    elif preset == "last_7_days":
        start_date = today - datetime.timedelta(days=6)
        end_date = today
    elif preset == "this_week":
        start_date, end_date = DateTimeUtils.get_week_range(today)
    elif preset == "this_month":
        start_date = DateTimeUtils.get_first_day_of_month(today)
        end_date = DateTimeUtils.get_last_day_of_month(today)
    else:
        return

    st.session_state["time_tool_start_date"] = start_date
    st.session_state["time_tool_end_date"] = end_date


def _render_timestamp_tab() -> None:
    st.markdown("### 时间戳转换")
    tz_options = DateTimeUtils.get_timezones()

    single_tab, batch_tab = st.tabs(["单条转换", "批量转换"])

    with single_tab:
        action_cols = st.columns(4)
        if secondary_action_button("填入当前秒级", key="time_tool_fill_now_seconds"):
            st.session_state["time_tool_timestamp_input"] = str(int(datetime.datetime.now().timestamp()))
            st.session_state["time_tool_timestamp_mode"] = "秒"
        if secondary_action_button("填入当前毫秒级", key="time_tool_fill_now_milliseconds"):
            st.session_state["time_tool_timestamp_input"] = str(int(datetime.datetime.now().timestamp() * 1000))
            st.session_state["time_tool_timestamp_mode"] = "毫秒"
        if secondary_action_button("填入当前时间", key="time_tool_fill_now_datetime"):
            now = datetime.datetime.now()
            st.session_state["time_tool_date_input"] = now.date()
            st.session_state["time_tool_time_input"] = now.time().replace(microsecond=0)
        if secondary_action_button("加载示例", key="time_tool_fill_sample"):
            st.session_state["time_tool_timestamp_input"] = "1712361600"
            st.session_state["time_tool_timestamp_mode"] = "秒"
            st.session_state["time_tool_date_input"] = datetime.date(2026, 4, 6)
            st.session_state["time_tool_time_input"] = datetime.time(9, 30, 0)

        convert_col1, convert_col2 = st.columns(2)

        with convert_col1:
            timestamp_text = st.text_input(
                "输入时间戳",
                key="time_tool_timestamp_input",
                placeholder="支持秒级或毫秒级，建议使用 10 位或 13 位时间戳",
            )
            unit_mode = st.selectbox("时间戳类型", ["自动识别", "秒", "毫秒"], key="time_tool_timestamp_mode")
            timezone_label = st.selectbox("展示时区", list(tz_options.keys()), key="time_tool_timestamp_tz")
            if primary_action_button("转换为日期时间", key="time_tool_convert_to_datetime"):
                try:
                    result = _convert_timestamp_input(timestamp_text, unit_mode, tz_options[timezone_label])
                    st.session_state["time_tool_timestamp_result"] = result
                    render_success_feedback("时间戳已经成功转换为日期时间。")
                except Exception as exc:
                    st.session_state["time_tool_timestamp_result"] = None
                    render_error_feedback(f"时间戳转换失败: {exc}")

            timestamp_result = st.session_state.get("time_tool_timestamp_result")
            if timestamp_result:
                target_dt = timestamp_result["datetime"]
                st.code(
                    _format_lines(
                        [
                            f"识别精度: {timestamp_result['precision']}",
                            f"时区: {timestamp_result['timezone']}",
                            f"日期时间: {target_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z')}",
                            f"ISO8601: {target_dt.isoformat()}",
                            f"星期: {_weekday_label(target_dt)}",
                        ]
                    )
                )
            else:
                render_info_feedback("左侧适合处理单个时间戳；右侧适合把一个日期时间回算成秒级或毫秒级时间戳。")

        with convert_col2:
            selected_date = st.date_input("选择日期", key="time_tool_date_input")
            selected_time = st.time_input("选择时间", key="time_tool_time_input")
            timezone_label = st.selectbox("输入时间所属时区", list(tz_options.keys()), key="time_tool_datetime_tz")
            if primary_action_button("转换为时间戳", key="time_tool_convert_to_timestamp"):
                timezone = pytz.timezone(tz_options[timezone_label])
                combined = datetime.datetime.combine(selected_date, selected_time)
                localized = timezone.localize(combined)
                seconds = localized.timestamp()
                st.session_state["time_tool_datetime_result"] = {
                    "datetime": localized,
                    "timestamp_seconds": int(seconds),
                    "timestamp_milliseconds": int(seconds * 1000),
                }
                render_success_feedback("日期时间已经成功转换为时间戳。")

            datetime_result = st.session_state.get("time_tool_datetime_result")
            if datetime_result:
                localized = datetime_result["datetime"]
                st.code(
                    _format_lines(
                        [
                            f"原始时间: {localized.strftime('%Y-%m-%d %H:%M:%S %Z%z')}",
                            f"秒级时间戳: {datetime_result['timestamp_seconds']}",
                            f"毫秒级时间戳: {datetime_result['timestamp_milliseconds']}",
                        ]
                    )
                )

        now = datetime.datetime.now()
        metric_cols = st.columns(4)
        metric_cols[0].metric("当前本地时间", now.strftime("%H:%M:%S"))
        metric_cols[1].metric("当前日期", now.strftime("%Y-%m-%d"))
        metric_cols[2].metric("当前秒级时间戳", int(now.timestamp()))
        metric_cols[3].metric("当前毫秒级时间戳", int(now.timestamp() * 1000))

    with batch_tab:
        control_col, info_col = st.columns([2, 1])
        with control_col:
            batch_text = st.text_area(
                "批量输入",
                key="time_tool_batch_input",
                height=180,
                placeholder="一行一个值，支持混合输入时间戳、日期、ISO8601 时间",
            )
        with info_col:
            timezone_label = st.selectbox("结果展示时区", list(tz_options.keys()), key="time_tool_batch_timezone")
            st.caption("适合日志排查、批量核对回调时间或把多种格式统一成一张表。")
            if secondary_action_button("填入示例数据", key="time_tool_fill_batch_sample"):
                st.session_state["time_tool_batch_input"] = DEFAULT_BATCH_SAMPLE
            if secondary_action_button("清空批量输入", key="time_tool_clear_batch_input"):
                st.session_state["time_tool_batch_input"] = ""
            if primary_action_button("开始批量转换", key="time_tool_batch_convert"):
                rows = DateTimeUtils.batch_convert_temporal_values(batch_text, tz_options[timezone_label])
                st.session_state["time_tool_batch_result"] = rows

        batch_rows = st.session_state.get("time_tool_batch_result", [])
        if batch_rows:
            success_count = sum(row["状态"] == "成功" for row in batch_rows)
            fail_count = len(batch_rows) - success_count
            metric_cols = st.columns(3)
            metric_cols[0].metric("总条数", len(batch_rows))
            metric_cols[1].metric("成功", success_count)
            metric_cols[2].metric("失败", fail_count)

            if fail_count:
                render_warning_feedback("部分输入未能解析，失败行会保留原始错误信息，便于继续清洗。", title="批量转换完成")
            else:
                render_success_feedback("全部输入都已成功转换。", title="批量转换完成")

            result_df = pd.DataFrame(batch_rows)
            st.dataframe(result_df, use_container_width=True, hide_index=True)
            st.download_button(
                "下载批量结果 CSV",
                data=result_df.to_csv(index=False).encode("utf-8-sig"),
                file_name="time_batch_result.csv",
                mime="text/csv",
                use_container_width=True,
            )
        else:
            render_info_feedback("批量页支持混合贴入 10 位/13 位时间戳、标准日期时间和带时区的 ISO8601 时间。")


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

    metric_cols = st.columns(3)
    metric_cols[0].metric("折算秒数", round(base_seconds, 3))
    metric_cols[1].metric("可读时长", DateTimeUtils.format_duration(base_seconds))
    metric_cols[2].metric("分钟数", round(base_seconds / 60, 3))

    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption("月和年按近似值换算，分别按 30 天和 365 天处理。")


def _render_date_calculator_tab() -> None:
    st.markdown("### 日期计算与信息查询")

    preset_cols = st.columns(4)
    if secondary_action_button("今天", key="time_tool_preset_today"):
        _apply_range_preset("today")
    if secondary_action_button("最近 7 天", key="time_tool_preset_last_7_days"):
        _apply_range_preset("last_7_days")
    if secondary_action_button("本周", key="time_tool_preset_this_week"):
        _apply_range_preset("this_week")
    if secondary_action_button("本月", key="time_tool_preset_this_month"):
        _apply_range_preset("this_month")

    country_options = {"仅周末": None, **DateTimeUtils.get_supported_holiday_countries()}

    input_cols = st.columns(3)
    with input_cols[0]:
        start_date = st.date_input("开始日期", key="time_tool_start_date")
    with input_cols[1]:
        end_date = st.date_input("结束日期", key="time_tool_end_date")
    with input_cols[2]:
        holiday_label = st.selectbox("工作日日历", list(country_options.keys()), key="time_tool_holiday_calendar")

    holiday_country = country_options[holiday_label]
    summary = DateTimeUtils.summarize_date_range(start_date, end_date, country=holiday_country)
    st.session_state["time_tool_range_summary"] = summary

    if summary["signed_diff_days"] < 0:
        render_warning_feedback("结束日期早于开始日期。差值按负数展示，但区间统计会按排序后的日期范围计算。", title="日期顺序提示")

    metric_cols = st.columns(5)
    metric_cols[0].metric("自然日差值", summary["signed_diff_days"])
    metric_cols[1].metric("包含首尾天数", summary["calendar_days"])
    metric_cols[2].metric("工作日数量", abs(summary["business_days"]))
    metric_cols[3].metric("周末天数", summary["weekend_days"])
    metric_cols[4].metric("法定节假日", summary["holiday_only_days"])

    week_start, week_end = DateTimeUtils.get_week_range(start_date)
    today = datetime.date.today()
    render_info_feedback(
        f"开始日期所在周: {week_start:%Y-%m-%d} 至 {week_end:%Y-%m-%d} | "
        f"开始日期节假日标记: {'是' if holiday_country and DateTimeUtils.is_holiday(start_date, holiday_country) else '否'} | "
        f"相对今天偏移: {(start_date - today).days:+d} 天",
        title="日期补充信息",
    )

    offset_col1, offset_col2, offset_col3, offset_col4 = st.columns(4)
    with offset_col1:
        offset_days = st.number_input("自然日偏移", value=7, step=1, key="time_tool_offset_days")
    with offset_col2:
        offset_months = st.number_input("月偏移", value=1, step=1, key="time_tool_offset_months")
    with offset_col3:
        business_offset = st.number_input("工作日偏移", value=3, step=1, key="time_tool_business_offset")
    with offset_col4:
        birthday = st.date_input("生日 / 出生日期", key="time_tool_birthday")

    business_offset_date = DateTimeUtils.add_business_days(start_date, int(business_offset), country=holiday_country)
    result_rows = [
        {"场景": "开始日期 + 自然日", "结果": DateTimeUtils.add_days(start_date, int(offset_days)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 - 自然日", "结果": DateTimeUtils.subtract_days(start_date, int(offset_days)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 + 月数", "结果": DateTimeUtils.add_months(start_date, int(offset_months)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 - 月数", "结果": DateTimeUtils.subtract_months(start_date, int(offset_months)).strftime("%Y-%m-%d")},
        {"场景": "开始日期 + 工作日偏移", "结果": business_offset_date.strftime("%Y-%m-%d")},
        {"场景": "当月第一天", "结果": DateTimeUtils.get_first_day_of_month(start_date).strftime("%Y-%m-%d")},
        {"场景": "当月最后一天", "结果": DateTimeUtils.get_last_day_of_month(start_date).strftime("%Y-%m-%d")},
        {"场景": "差值可读化", "结果": DateTimeUtils.format_duration(abs(summary["signed_diff_days"]) * 86400)},
        {"场景": "年龄", "结果": DateTimeUtils.get_age(birthday)},
        {"场景": "生肖", "结果": DateTimeUtils.get_chinese_zodiac(birthday.year)},
        {"场景": "星座", "结果": DateTimeUtils.get_constellation(birthday.month, birthday.day)},
    ]
    st.dataframe(pd.DataFrame(result_rows), use_container_width=True, hide_index=True)


def _render_advanced_tab() -> None:
    sla_tab, cron_tab, perf_tab, tz_tab = st.tabs(["SLA/工作时间", "Cron", "性能测试", "时区转换"])

    with sla_tab:
        start_date = st.date_input("SLA 开始日期", key="time_tool_sla_date")
        start_time = st.time_input("SLA 开始时间", key="time_tool_sla_time")
        sla_hours = st.number_input("SLA 时长(小时)", min_value=0.0, value=24.0, key="time_tool_sla_hours")
        work_col1, work_col2 = st.columns(2)
        with work_col1:
            work_start = st.number_input("工作开始小时", min_value=0, max_value=23, value=9, key="time_tool_work_start")
        with work_col2:
            work_end = st.number_input("工作结束小时", min_value=1, max_value=24, value=18, key="time_tool_work_end")

        try:
            start_dt = datetime.datetime.combine(start_date, start_time)
            due_dt = DateTimeUtils.calculate_sla_due_date(start_dt, sla_hours, int(work_start), int(work_end))
            business_hours = DateTimeUtils.calculate_business_hours_diff(start_dt, due_dt, (int(work_start), int(work_end)))

            metric_cols = st.columns(3)
            metric_cols[0].metric("工作时长", f"{business_hours:.2f} 小时")
            metric_cols[1].metric("自然耗时", DateTimeUtils.format_duration((due_dt - start_dt).total_seconds()))
            metric_cols[2].metric("到期日期", due_dt.strftime("%Y-%m-%d"))

            st.code(
                _format_lines(
                    [
                        f"SLA 开始时间: {start_dt.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"SLA 到期时间: {due_dt.strftime('%Y-%m-%d %H:%M:%S')}",
                        f"工作时间差(小时): {business_hours:.2f}",
                    ]
                )
            )
        except Exception as exc:
            render_error_feedback(f"SLA 计算失败: {exc}")

    with cron_tab:
        preset_col, action_col = st.columns([2, 1])
        with preset_col:
            selected_preset = st.selectbox("常用模板", list(CRON_PRESETS.keys()), key="time_tool_cron_preset")
        with action_col:
            if secondary_action_button("载入模板", key="time_tool_load_cron_preset"):
                st.session_state["time_tool_cron_expression"] = CRON_PRESETS[selected_preset]

        cron_expression = st.text_input("Cron 表达式", key="time_tool_cron_expression")
        cron_base_date = st.date_input("Cron 基准日期", key="time_tool_cron_base")
        cron_count = st.number_input("生成次数", min_value=1, max_value=20, value=5, key="time_tool_cron_count")

        if primary_action_button("生成执行计划", key="time_tool_generate_cron"):
            st.session_state["time_tool_cron_result"] = DateTimeUtils.generate_cron_next_runs(
                cron_expression,
                cron_base_date,
                int(cron_count),
            )

        cron_result = st.session_state.get("time_tool_cron_result", [])
        if cron_result:
            if isinstance(cron_result[0], str):
                render_error_feedback(str(cron_result[0]), title="Cron 解析失败")
            else:
                render_success_feedback("Cron 表达式已解析完成。")
                st.dataframe(
                    pd.DataFrame({"下一次执行时间": [str(item) for item in cron_result]}),
                    use_container_width=True,
                    hide_index=True,
                )
        else:
            render_info_feedback("可直接用模板验证工作日任务、定时轮询和每日批处理的下次触发时间。")

    with perf_tab:
        duration = st.number_input("持续时间(秒)", min_value=1.0, value=10.0, key="time_tool_perf_duration")
        rps = st.number_input("每秒请求数", min_value=1.0, value=5.0, key="time_tool_perf_rps")
        response_times_text = st.text_area(
            "响应时间列表(ms)",
            key="time_tool_response_times",
            height=120,
        )

        if primary_action_button("分析性能时间", key="time_tool_run_perf_analysis"):
            try:
                parsed_response_times = _parse_response_times(response_times_text)
                timestamps = DateTimeUtils.get_performance_test_timestamps(duration, rps)
                percentiles = DateTimeUtils.calculate_response_time_percentiles(parsed_response_times)
                st.session_state["time_tool_perf_result"] = {
                    "timestamps": timestamps,
                    "count": len(parsed_response_times),
                    "min": round(min(parsed_response_times), 3),
                    "max": round(max(parsed_response_times), 3),
                    "avg": round(sum(parsed_response_times) / len(parsed_response_times), 3),
                    "percentiles": percentiles,
                }
            except Exception as exc:
                st.session_state["time_tool_perf_result"] = None
                render_error_feedback(f"性能分析失败: {exc}")

        perf_result = st.session_state.get("time_tool_perf_result")
        if perf_result:
            percentiles = perf_result["percentiles"]
            metric_cols = st.columns(5)
            metric_cols[0].metric("计划请求数", len(perf_result["timestamps"]))
            metric_cols[1].metric("平均响应", f"{perf_result['avg']} ms")
            metric_cols[2].metric("P95", percentiles.get(95, "-"))
            metric_cols[3].metric("P99", percentiles.get(99, "-"))
            metric_cols[4].metric("最大响应", f"{perf_result['max']} ms")

            preview_rows = [
                {
                    "序号": index + 1,
                    "计划时间点": datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                }
                for index, ts in enumerate(perf_result["timestamps"][:10])
            ]
            st.dataframe(pd.DataFrame(preview_rows), use_container_width=True, hide_index=True)
        else:
            render_info_feedback("输入压测持续时间、RPS 和响应时间列表后，可以快速估算计划请求点并查看 P95/P99。")

    with tz_tab:
        tz_options = DateTimeUtils.get_timezones()
        from_col, to_col = st.columns(2)
        with from_col:
            source_tz = st.selectbox("源时区", list(tz_options.keys()), key="time_tool_from_tz")
        with to_col:
            target_tz = st.selectbox("目标时区", list(tz_options.keys()), key="time_tool_to_tz")
        source_date = st.date_input("源日期", key="time_tool_tz_date")
        source_time = st.time_input("源时间", key="time_tool_tz_time")
        source_dt = datetime.datetime.combine(source_date, source_time)
        converted = DateTimeUtils.get_timezone_conversion(source_dt, tz_options[source_tz], tz_options[target_tz])

        comparison_labels = []
        for label in [source_tz, target_tz, "UTC", "北京", "东京", "纽约", "伦敦"]:
            if label in tz_options and label not in comparison_labels:
                comparison_labels.append(label)

        snapshot_rows = DateTimeUtils.get_multi_timezone_snapshot(
            source_dt,
            [tz_options[label] for label in comparison_labels],
            source_timezone_name=tz_options[source_tz],
        )
        timezone_label_map = {value: key for key, value in tz_options.items()}
        rendered_rows = [
            {
                "时区": timezone_label_map.get(item["时区"], item["时区"]),
                "当地时间": item["当地时间"],
                "缩写": item["缩写"],
                "UTC偏移": item["UTC偏移"],
                "星期": item["星期"],
            }
            for item in snapshot_rows
        ]
        st.session_state["time_tool_timezone_snapshot"] = rendered_rows

        st.code(
            _format_lines(
                [
                    f"源时间: {source_dt.strftime('%Y-%m-%d %H:%M:%S')} ({tz_options[source_tz]})",
                    f"转换结果: {converted.strftime('%Y-%m-%d %H:%M:%S %Z%z')}",
                ]
            )
        )
        st.dataframe(pd.DataFrame(rendered_rows), use_container_width=True, hide_index=True)


def render_time_processor_page() -> None:
    _ensure_defaults()
    show_doc("time_processor")
    render_tool_page_hero(
        "⏰",
        "时间处理工具",
        "覆盖时间戳转换、日期区间分析、工作日排期、SLA 到期、Cron 预测、时区换算和性能测试时间辅助，适合测试联调和排障。",
        tags=["时间戳", "日期计算", "工作日", "SLA", "Cron", "时区转换"],
        accent="#0f766e",
    )
    render_tool_tips(
        "推荐路径",
        [
            "接口联调用“时间戳转换”，单条看精确结果，批量页统一清洗日志时间。",
            "排查工单和测试计划时，优先在“日期计算”里看工作日、周末和节假日拆解。",
            "定时任务排查先载入 Cron 模板，再看“时区转换”里的多时区对照表。",
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
