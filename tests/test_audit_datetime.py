"""时间处理工具专项审计回归测试（issues #250-#268）。"""
from __future__ import annotations

import datetime
import io
import json
import sys
from pathlib import Path

import pytest

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
ROOT_DIR = SRC_DIR.parent
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.core import datetime_registry  # noqa: E402
from qa_toolkit.utils.datetime_tools import (  # noqa: E402
    MAX_BUSINESS_DAY_OFFSET,
    DateTimeUtils,
)

PAGE_SCRIPT = """
import sys; sys.path.insert(0, "src")
from qa_toolkit.ui.pages.time_processor_page import render_time_processor_page
render_time_processor_page()
"""


def _markdown_text(app) -> str:
    return "\n".join(item.value for item in app.markdown)


def _no_exception(app) -> None:
    assert not app.exception, [e.value for e in app.exception]


# ---------- DT-01/DT-02: 时区转换错误处理 ----------

def test_timezone_conversion_rejects_invalid_zone() -> None:
    with pytest.raises(ValueError, match="无效的目标时区"):
        DateTimeUtils.get_timezone_conversion(
            datetime.datetime(2026, 4, 6, 9, 0), "Asia/Shanghai", "Not/AZone")
    with pytest.raises(ValueError, match="无效的源时区"):
        DateTimeUtils.get_timezone_conversion(
            datetime.datetime(2026, 4, 6, 9, 0), "Bad/Zone", "Asia/Shanghai")


def test_timezone_conversion_dst_errors() -> None:
    with pytest.raises(ValueError, match="不存在"):
        DateTimeUtils.get_timezone_conversion(
            datetime.datetime(2026, 3, 8, 2, 30), "America/New_York", "Asia/Shanghai")
    # 正常转换仍然工作
    result = DateTimeUtils.get_timezone_conversion(
        datetime.datetime(2026, 4, 6, 9, 0), "Asia/Shanghai", "America/New_York")
    assert result.strftime("%Y-%m-%d %H:%M") == "2026-04-05 21:00"


# ---------- DT-03: 节假日年份缺口降级 ----------

def test_summarize_far_future_year_degrades_without_crash() -> None:
    summary = DateTimeUtils.summarize_date_range(
        datetime.date(2100, 1, 1), datetime.date(2100, 1, 7), country="CN")
    assert summary["calendar_days"] == 7
    assert summary["business_days"] == 5  # 无节假日数据时按纯周末统计
    assert 2100 in summary["unsupported_holiday_years"]


def test_is_holiday_unsupported_year_returns_false() -> None:
    assert DateTimeUtils.is_holiday(datetime.date(2101, 1, 1), "CN") is False


# ---------- DT-04: 自定义调休表 ----------

@pytest.fixture()
def _cn_2024_tiaoxiu():
    datetime_registry.register_business_calendar("CN", extra_workdays={datetime.date(2024, 2, 4)})
    yield
    datetime_registry.clear_business_calendar("CN")


def test_custom_workday_override(_cn_2024_tiaoxiu) -> None:
    assert DateTimeUtils.count_business_days(
        datetime.date(2024, 2, 4), datetime.date(2024, 2, 4), country="CN") == 1
    assert DateTimeUtils.is_holiday(datetime.date(2024, 2, 4), "CN") is False


def test_custom_holiday_override() -> None:
    holiday = datetime.date(2026, 12, 31)
    datetime_registry.register_business_calendar("CN", extra_holidays={holiday})
    try:
        assert DateTimeUtils.count_business_days(holiday, holiday, country="CN") == 0
        assert DateTimeUtils.is_holiday(holiday, "CN") is True
        assert DateTimeUtils.is_workday(holiday, "CN") is False
    finally:
        datetime_registry.clear_business_calendar("CN")


# ---------- DT-05: 结果过期 ----------

def test_timestamp_result_expires_on_input_change() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=60).run()
    _no_exception(app)
    app.text_input(key="time_tool_timestamp_input").set_value("1712361600").run()
    app.button(key="time_tool_convert_to_datetime").click().run()
    first = app.session_state["time_tool_timestamp_result"]
    assert first is not None
    app.text_input(key="time_tool_timestamp_input").set_value("1712448000").run()
    assert app.session_state["time_tool_timestamp_result"] == first
    assert "结果已过期" in _markdown_text(app)


def test_batch_result_expires_on_input_change() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=60).run()
    app.text_area(key="time_tool_batch_input").set_value("1712361600").run()
    app.button(key="time_tool_batch_convert").click().run()
    assert len(app.session_state["time_tool_batch_result"]) == 1
    app.text_area(key="time_tool_batch_input").set_value("1712361600\n1712361700").run()
    assert "结果已过期" in _markdown_text(app)


def test_cron_result_expires_on_input_change() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=60).run()
    app.text_input(key="time_tool_cron_expression").set_value("0 9 * * 1-5").run()
    app.button(key="time_tool_generate_cron").click().run()
    result = app.session_state["time_tool_cron_result"]
    assert result and result["ok"]
    app.text_input(key="time_tool_cron_expression").set_value("*/10 * * * *").run()
    assert "结果已过期" in _markdown_text(app)


# ---------- DT-06: CSV 公式注入 ----------

def test_batch_csv_export_neutralizes_formulas() -> None:
    rows = DateTimeUtils.batch_convert_temporal_values("=1+1\n")
    assert rows and rows[0]["状态"] == "失败"
    assert rows[0]["日期时间"].startswith("无法识别的时间格式")
    # 页面导出 helper
    from qa_toolkit.ui.pages.time_processor_page import _safe_csv_cell
    assert _safe_csv_cell("=1+1") == "'=1+1"
    assert _safe_csv_cell("2026-04-06") == "2026-04-06"


# ---------- DT-07: Cron 结构化返回 ----------

def test_generate_cron_runs_structured_result() -> None:
    ok = DateTimeUtils.generate_cron_runs("0 9 * * 1-5", datetime.date(2026, 1, 1), 3)
    assert ok["ok"] is True and len(ok["runs"]) == 3 and ok["error"] == ""
    bad = DateTimeUtils.generate_cron_runs("bad cron", datetime.date(2026, 1, 1), 3)
    assert bad["ok"] is False and not bad["runs"] and "分 时 日 月 周" in bad["error"]
    # 兼容旧接口
    legacy = DateTimeUtils.generate_cron_next_runs("bad cron", datetime.date(2026, 1, 1), 3)
    assert isinstance(legacy[0], str)


# ---------- DT-08: 批量失败行中文诊断 ----------

def test_batch_errors_are_actionable_chinese() -> None:
    rows = DateTimeUtils.batch_convert_temporal_values("abc\n999999999999999999999\n")
    messages = [row["日期时间"] for row in rows]
    assert messages[0].startswith("无法识别的时间格式")
    assert "too large" in messages[1] or "超出可表示范围" in messages[1] or "时间戳" in messages[1]


# ---------- DT-09: 中文星期 ----------

def test_chinese_weekday_outputs() -> None:
    parsed = DateTimeUtils.parse_datetime_input("2026-04-06 09:30:00")
    assert parsed["weekday_zh"] == "周一"
    assert DateTimeUtils.weekday_name(parsed["datetime"]) == "周一"
    assert DateTimeUtils.weekday_name(parsed["datetime"], locale="en") == "Monday"
    snapshot = DateTimeUtils.get_multi_timezone_snapshot(
        parsed["datetime"], ["Asia/Shanghai"], source_timezone_name="Asia/Shanghai")
    assert snapshot[0]["星期"] == "周一"


# ---------- DT-10/DT-11: 年龄与星座校验 ----------

def test_get_age_rejects_future_birth_date() -> None:
    with pytest.raises(ValueError, match="出生日期"):
        DateTimeUtils.get_age(datetime.date(2030, 1, 1))
    assert DateTimeUtils.get_age(datetime.date(2000, 1, 1), datetime.date(2026, 6, 1)) == 26


def test_get_constellation_rejects_invalid_dates() -> None:
    assert DateTimeUtils.get_constellation(2, 30) == ""
    assert DateTimeUtils.get_constellation(4, 31) == ""
    assert DateTimeUtils.get_constellation(4, 20) == "金牛座"
    assert DateTimeUtils.get_constellation(1, 1) == "摩羯座"


# ---------- DT-12: 工作日偏移上限 ----------

def test_add_business_days_clamped() -> None:
    with pytest.raises(ValueError, match="偏移量过大"):
        DateTimeUtils.add_business_days(datetime.date(2026, 1, 1), MAX_BUSINESS_DAY_OFFSET + 1)
    assert DateTimeUtils.add_business_days(datetime.date(2026, 1, 1), 0) == datetime.date(2026, 1, 1)
    # 2026-01-01 是周四：+1 个工作日 → 01-02（周五）
    assert DateTimeUtils.add_business_days(datetime.date(2026, 1, 1), 1) == datetime.date(2026, 1, 2)


def test_page_clamps_business_offset() -> None:
    from qa_toolkit.ui.pages.time_processor_page import _clamp_business_offset
    assert _clamp_business_offset(10**9) == MAX_BUSINESS_DAY_OFFSET
    assert _clamp_business_offset("bad") == 0


# ---------- DT-13: 性能测试语义与校验 ----------

def test_perf_timestamps_ceil_and_response_validation() -> None:
    assert len(DateTimeUtils.get_performance_test_timestamps(10.5, 5)) == 53
    from qa_toolkit.ui.pages.time_processor_page import _parse_response_times
    with pytest.raises(ValueError, match="负数"):
        _parse_response_times("100, -5")
    with pytest.raises(ValueError, match="不是数字"):
        _parse_response_times("100, abc")


# ---------- DT-14: add_months 边界 ----------

def test_add_months_boundary_friendly_error() -> None:
    with pytest.raises(ValueError, match="超出可表示日期范围"):
        DateTimeUtils.add_months(datetime.date(1, 1, 1), -1)
    with pytest.raises(ValueError, match="超出可表示日期范围"):
        DateTimeUtils.add_months(datetime.date(9999, 12, 31), 1)
    # 常规钳月语义不变
    assert DateTimeUtils.add_months(datetime.date(2026, 1, 31), 1) == datetime.date(2026, 2, 28)


# ---------- DT-15: 结果表类型一致 ----------

def test_date_calculator_result_rows_all_strings() -> None:
    from qa_toolkit.ui.pages.time_processor_page import _build_date_calculation_rows

    today = datetime.date.today()
    rows = _build_date_calculation_rows(
        datetime.date(2026, 1, 31), "CN",
        offset_days=7, offset_months=1, business_offset=3,
        birthday=today - datetime.timedelta(days=9000),
        signed_diff_days=0,
    )
    assert all(isinstance(row["结果"], str) for row in rows)
    age_row = next(row for row in rows if row["场景"] == "年龄")
    assert age_row["结果"].isdigit()

    future_rows = _build_date_calculation_rows(
        datetime.date(2026, 1, 31), None,
        offset_days=7, offset_months=1, business_offset=3,
        birthday=today + datetime.timedelta(days=30),
        signed_diff_days=0,
    )
    future_age = next(row for row in future_rows if row["场景"] == "年龄")
    assert "无法计算年龄" in future_age["结果"]

    # 越界月偏移不再让整表崩溃
    overflow_rows = _build_date_calculation_rows(
        datetime.date(1, 1, 1), None,
        offset_days=7, offset_months=1200, business_offset=3,
        birthday=today, signed_diff_days=0,
    )
    assert all(row["结果"] for row in overflow_rows)


# ---------- DT-16: 注册式扩展点 ----------

def test_registry_extension_points() -> None:
    summary = datetime_registry.get_registry_summary()
    assert summary["time_units"] >= 7
    assert summary["timezones"] >= 13
    assert summary["cron_presets"] >= 4
    assert summary["comparison_columns"] >= 5

    datetime_registry.register_time_unit("刻钟", 900)
    try:
        assert datetime_registry.get_time_units()["刻钟"].seconds == 900
        with pytest.raises(ValueError, match="已存在"):
            datetime_registry.register_time_unit("刻钟", 900)
    finally:
        datetime_registry._TIME_UNITS.pop("刻钟", None)

    with pytest.raises(ValueError):
        datetime_registry.register_time_unit("坏单位", -5)


def test_time_units_backed_by_registry() -> None:
    from qa_toolkit.ui.pages import time_processor_page
    assert time_processor_page.TIME_UNIT_SECONDS["小时"] == 3600


# ---------- DT-17: 时区搜索与自定义 ----------

def test_custom_timezone_resolution() -> None:
    assert datetime_registry.resolve_timezone("北京") == "Asia/Shanghai"
    assert datetime_registry.resolve_timezone("Asia/Ho_Chi_Minh") == "Asia/Ho_Chi_Minh"
    with pytest.raises(ValueError, match="无效的时区"):
        DateTimeUtils.parse_datetime_input("2026-04-06 09:30", timezone_name="NoSuch/Zone")


def test_tz_tab_accepts_custom_iana_zone() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=60).run()
    app.text_input(key="time_tool_custom_tz").set_value("Asia/Ho_Chi_Minh").run()
    snapshot = app.session_state["time_tool_timezone_snapshot"]
    labels = [row["时区"] for row in snapshot]
    assert any("自定义: Asia/Ho_Chi_Minh" in label for label in labels)


# ---------- DT-18: 批量解析拓展性 ----------

def test_microsecond_timestamp_and_custom_formats() -> None:
    parsed = DateTimeUtils.parse_datetime_input("1712361600123456")
    assert parsed["input_type"] == "时间戳(微秒)"

    datetime_registry.configure_custom_parse_formats(["%d/%m/%Y %H:%M"])
    try:
        parsed = DateTimeUtils.parse_datetime_input("06/04/2026 09:30")
        assert parsed["datetime"].strftime("%Y-%m-%d %H:%M") == "2026-04-06 09:30"
    finally:
        datetime_registry.configure_custom_parse_formats([])


def test_batch_rows_include_chinese_weekday_column() -> None:
    rows = DateTimeUtils.batch_convert_temporal_values("2026-04-06 09:30:00\n")
    assert rows[0]["星期"] == "周一"


# ---------- DT-19: SLA 节假日日历 ----------

def test_sla_honors_holiday_calendar() -> None:
    # 2026-05-01（周五）是中国法定节假日
    due = DateTimeUtils.calculate_sla_due_date(
        datetime.datetime(2026, 4, 30, 16, 0), 4, 9, 18, country="CN")
    assert due == datetime.datetime(2026, 5, 4, 11, 0)
    # 不传 country 时保持旧行为（只跳周末）：5-1 周五算工作日
    due_default = DateTimeUtils.calculate_sla_due_date(
        datetime.datetime(2026, 4, 30, 16, 0), 4, 9, 18)
    assert due_default == datetime.datetime(2026, 5, 1, 11, 0)
    with pytest.raises(ValueError, match="迭代超限|工作时间"):
        DateTimeUtils.calculate_sla_due_date(
            datetime.datetime(2026, 1, 1, 9, 0), 1, 9, 9)  # 起止相等的工作窗口


# ---------- 页面冒烟 ----------

def test_page_renders_without_exception() -> None:
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_string(PAGE_SCRIPT, default_timeout=60).run()
    _no_exception(app)
    assert "时间处理工具" in _markdown_text(app)
