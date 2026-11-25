"""时间处理工具注册中心。

提供与 regex_registry / crypto_registry / json_registry 同风格的注册式扩展点：

- 时间单位（页面单位换算表）
- 时区（常用时区 + 自定义 IANA 名称）
- Cron 模板
- 多时区对照清单
- 自定义工作日 / 节假日覆盖表（调休安排）
- 批量解析的自定义格式

所有扩展点均线程安全（写操作极少，读操作直接返回浅拷贝）。
"""

from __future__ import annotations

import datetime
import threading
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Set, Tuple

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# 时间单位
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TimeUnitSpec:
    """一个时间单位：相对秒数与说明。"""
    seconds: float
    description: str = ""
    approximate: bool = False  # 月/年这类按近似值换算的单位


_TIME_UNITS: Dict[str, TimeUnitSpec] = {}


def register_time_unit(name: str, seconds: float, *, description: str = "",
                       approximate: bool = False, replace: bool = False) -> None:
    """注册/替换一个时间单位。seconds 为 1 个该单位等于多少秒。"""
    if seconds <= 0:
        raise ValueError(f"时间单位 {name!r} 的秒数必须为正数，收到: {seconds}")
    with _LOCK:
        if name in _TIME_UNITS and not replace:
            raise ValueError(f"时间单位 {name!r} 已存在，如需覆盖请传 replace=True")
        _TIME_UNITS[name] = TimeUnitSpec(seconds=float(seconds), description=description,
                                         approximate=approximate)


def get_time_units() -> Dict[str, TimeUnitSpec]:
    with _LOCK:
        return dict(_TIME_UNITS)


# ---------------------------------------------------------------------------
# 时区
# ---------------------------------------------------------------------------

_TIMEZONES: Dict[str, str] = {}


def register_timezone(label: str, iana_name: str, *, replace: bool = False) -> None:
    """注册一个展示名 -> IANA 时区名的映射。"""
    with _LOCK:
        if label in _TIMEZONES and not replace:
            raise ValueError(f"时区 {label!r} 已存在，如需覆盖请传 replace=True")
        _TIMEZONES[label] = iana_name


def get_timezones() -> Dict[str, str]:
    with _LOCK:
        return dict(_TIMEZONES)


def resolve_timezone(label_or_name: str) -> str:
    """把展示名或 IANA 名称解析成 IANA 名称；无法识别时抛 ValueError。"""
    with _LOCK:
        if label_or_name in _TIMEZONES:
            return _TIMEZONES[label_or_name]
    return label_or_name


# ---------------------------------------------------------------------------
# Cron 模板
# ---------------------------------------------------------------------------

_CRON_PRESETS: Dict[str, str] = {}


def register_cron_preset(name: str, expression: str, *, replace: bool = False) -> None:
    with _LOCK:
        if name in _CRON_PRESETS and not replace:
            raise ValueError(f"Cron 模板 {name!r} 已存在，如需覆盖请传 replace=True")
        _CRON_PRESETS[name] = expression


def get_cron_presets() -> Dict[str, str]:
    with _LOCK:
        return dict(_CRON_PRESETS)


# ---------------------------------------------------------------------------
# 多时区对照清单
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ComparisonColumnSpec:
    """多时区对照表中的一列：展示标签与时区名。"""
    label: str
    timezone: str


_COMPARISON_COLUMNS: List[ComparisonColumnSpec] = []


def set_comparison_columns(columns: Iterable[Tuple[str, str]]) -> None:
    """整体替换多时区对照表列（按传入顺序）。"""
    cols = [ComparisonColumnSpec(label=label, timezone=tz) for label, tz in columns]
    if not cols:
        raise ValueError("多时区对照表至少需要一列")
    with _LOCK:
        global _COMPARISON_COLUMNS
        _COMPARISON_COLUMNS = cols


def get_comparison_columns() -> List[ComparisonColumnSpec]:
    with _LOCK:
        return list(_COMPARISON_COLUMNS)


# ---------------------------------------------------------------------------
# 自定义工作日 / 节假日覆盖（调休安排）
# ---------------------------------------------------------------------------

@dataclass
class BusinessCalendarOverride:
    """某个国家/地区日历的覆盖表。

    extra_workdays: 本来是周末/节假日、但实际要上班的日期（调休上班日）。
    extra_holidays: 本来是工作日、但实际放假的日期（临时假期）。
    """
    country: str
    extra_workdays: Set[datetime.date] = field(default_factory=set)
    extra_holidays: Set[datetime.date] = field(default_factory=set)


_BUSINESS_CALENDARS: Dict[str, BusinessCalendarOverride] = {}


def register_business_calendar(country: str, *,
                               extra_workdays: Optional[Iterable[datetime.date]] = None,
                               extra_holidays: Optional[Iterable[datetime.date]] = None,
                               replace: bool = False) -> BusinessCalendarOverride:
    """注册/合并一个国家日历的自定义覆盖表。

    默认合并进已有覆盖表；传 replace=True 则整体替换。
    """
    key = str(country).upper()
    with _LOCK:
        existing = _BUSINESS_CALENDARS.get(key)
        if existing is None or replace:
            override = BusinessCalendarOverride(
                country=key,
                extra_workdays=set(extra_workdays or ()),
                extra_holidays=set(extra_holidays or ()),
            )
            _BUSINESS_CALENDARS[key] = override
            return override
        existing.extra_workdays.update(extra_workdays or ())
        existing.extra_holidays.update(extra_holidays or ())
        return existing


def get_business_calendar(country: str) -> Optional[BusinessCalendarOverride]:
    with _LOCK:
        return _BUSINESS_CALENDARS.get(str(country).upper())


def clear_business_calendar(country: str) -> None:
    with _LOCK:
        _BUSINESS_CALENDARS.pop(str(country).upper(), None)


# ---------------------------------------------------------------------------
# 批量解析自定义格式
# ---------------------------------------------------------------------------

_CUSTOM_PARSE_FORMATS: Tuple[str, ...] = ()


def configure_custom_parse_formats(formats: Iterable[str]) -> None:
    """配置批量解析时优先尝试的自定义 strptime 格式（按顺序）。"""
    fmts = tuple(str(f) for f in formats if str(f))
    with _LOCK:
        global _CUSTOM_PARSE_FORMATS
        _CUSTOM_PARSE_FORMATS = fmts


def get_custom_parse_formats() -> Tuple[str, ...]:
    with _LOCK:
        return _CUSTOM_PARSE_FORMATS


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------

def get_registry_summary() -> Dict[str, int]:
    with _LOCK:
        return {
            "time_units": len(_TIME_UNITS),
            "timezones": len(_TIMEZONES),
            "cron_presets": len(_CRON_PRESETS),
            "comparison_columns": len(_COMPARISON_COLUMNS),
            "business_calendars": len(_BUSINESS_CALENDARS),
            "custom_parse_formats": len(_CUSTOM_PARSE_FORMATS),
        }


# ---------------------------------------------------------------------------
# 默认注册（与旧行为完全一致，保证向后兼容）
# ---------------------------------------------------------------------------

register_time_unit("秒", 1)
register_time_unit("分钟", 60)
register_time_unit("小时", 3600)
register_time_unit("天", 86400)
register_time_unit("周", 7 * 86400)
register_time_unit("月(按30天)", 30 * 86400, approximate=True,
                   description="按 30 天近似换算，跨月精确计算请用日期计算功能")
register_time_unit("年(按365天)", 365 * 86400, approximate=True,
                   description="按 365 天近似换算")

for _label, _tz in {
    "UTC": "UTC",
    "北京": "Asia/Shanghai",
    "新加坡": "Asia/Singapore",
    "东京": "Asia/Tokyo",
    "首尔": "Asia/Seoul",
    "纽约": "America/New_York",
    "洛杉矶": "America/Los_Angeles",
    "伦敦": "Europe/London",
    "巴黎": "Europe/Paris",
    "柏林": "Europe/Berlin",
    "迪拜": "Asia/Dubai",
    "孟买": "Asia/Kolkata",
    "悉尼": "Australia/Sydney",
}.items():
    register_timezone(_label, _tz)

register_cron_preset("工作日 09:00", "0 9 * * 1-5")
register_cron_preset("每 5 分钟", "*/5 * * * *")
register_cron_preset("每天 00:00", "0 0 * * *")
register_cron_preset("每周一 10:00", "0 10 * * 1")

set_comparison_columns([
    ("UTC", "UTC"),
    ("北京", "Asia/Shanghai"),
    ("东京", "Asia/Tokyo"),
    ("纽约", "America/New_York"),
    ("伦敦", "Europe/London"),
])
