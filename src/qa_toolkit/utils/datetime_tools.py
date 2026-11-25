import datetime
import math
import re
import time
from datetime import timedelta

import pytz
from dateutil import parser as dateutil_parser

from qa_toolkit.core import datetime_registry

WEEKDAY_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 工作日偏移上限：防止超大输入导致长时间循环。
MAX_BUSINESS_DAY_OFFSET = 100_000


class DateTimeUtils:
    """
    时间处理工具类
    提供日期相关的各种计算和判断功能
    """

    @staticmethod
    def is_leap_year(year):
        """判断是否为闰年"""
        return (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)

    @staticmethod
    def days_in_month(year, month):
        """获取指定年月的天数"""
        days_per_month = [31, 29 if DateTimeUtils.is_leap_year(year) else 28, 31,
                          30, 31, 30, 31, 31, 30, 31, 30, 31]
        if not isinstance(month, int) or not 1 <= month <= 12:
            raise ValueError(f"月份必须在 1-12 之间，收到: {month}")
        return days_per_month[month - 1]

    @staticmethod
    def add_months(source_date, months):
        """添加指定月数到日期"""
        try:
            month = source_date.month - 1 + months
            year = source_date.year + month // 12
            month = month % 12 + 1
            day = min(source_date.day, DateTimeUtils.days_in_month(year, month))
            if isinstance(source_date, datetime.datetime):
                return source_date.replace(year=year, month=month, day=day)
            return datetime.date(year, month, day)
        except (ValueError, OverflowError) as exc:
            raise ValueError(
                f"月份计算超出可表示日期范围（{source_date} {months:+d} 个月）: {exc}"
            ) from exc

    @staticmethod
    def subtract_months(source_date, months):
        """从日期减去指定月数"""
        return DateTimeUtils.add_months(source_date, -months)

    # ------------------------------------------------------------------
    # 自定义工作日/节假日覆盖（调休安排）
    # ------------------------------------------------------------------

    @staticmethod
    def _calendar_override(country):
        if not country:
            return None
        return datetime_registry.get_business_calendar(country)

    @staticmethod
    def apply_calendar_override(date_obj, is_workday_by_default, country):
        """按自定义覆盖表修正某个日期是否为工作日。

        返回 True/False 表示按覆盖表判定；None 表示无覆盖、按默认规则。
        """
        override = DateTimeUtils._calendar_override(country)
        if override is None:
            return None
        if date_obj in override.extra_workdays:
            return True
        if date_obj in override.extra_holidays:
            return False
        return None

    @staticmethod
    def is_workday(date_obj, country=None):
        """综合周末/法定节假日/自定义调休表判断是否为工作日。"""
        overridden = DateTimeUtils.apply_calendar_override(date_obj, None, country)
        if overridden is not None:
            return overridden
        if date_obj.weekday() >= 5:
            return False
        if country and DateTimeUtils.is_holiday(date_obj, country):
            return False
        return True

    # ------------------------------------------------------------------
    # 工作日统计
    # ------------------------------------------------------------------

    @staticmethod
    def count_business_days(start_date, end_date, country=None):
        """计算两个日期之间的工作日数量（可选排除节假日，支持自定义调休表）"""
        if start_date == end_date:
            return 1 if DateTimeUtils.is_workday(start_date, country) else 0

        direction = 1 if end_date >= start_date else -1
        range_start = min(start_date, end_date)
        range_end = max(start_date, end_date)

        holiday_dates = {}
        if country:
            holiday_dates = DateTimeUtils._get_country_holidays(
                country,
                years=range(range_start.year, range_end.year + 1),
            )

        business_days = 0
        current_day = range_start
        while current_day <= range_end:
            if DateTimeUtils.is_workday(current_day, country) and \
                    current_day not in holiday_dates:
                business_days += 1
            current_day += timedelta(days=1)
        return business_days * direction

    @staticmethod
    def get_current_date():
        """获取当前日期"""
        return datetime.date.today()

    @staticmethod
    def get_current_datetime():
        """获取当前日期时间"""
        return datetime.datetime.now()

    @staticmethod
    def date_to_string(date, format_str="%Y-%m-%d"):
        """将日期对象转换为字符串"""
        return date.strftime(format_str)

    @staticmethod
    def string_to_date(date_string, format_str="%Y-%m-%d"):
        """将字符串转换为日期对象"""
        return datetime.datetime.strptime(date_string, format_str).date()

    @staticmethod
    def is_weekend(date):
        """判断是否为周末"""
        return date.weekday() >= 5

    @staticmethod
    def add_days(source_date, days):
        """添加指定天数到日期"""
        return source_date + timedelta(days=days)

    @staticmethod
    def subtract_days(source_date, days):
        """从日期减去指定天数"""
        return source_date - timedelta(days=days)

    @staticmethod
    def date_difference(start_date, end_date):
        """计算两个日期之间的天数差"""
        return (end_date - start_date).days

    # 新增功能
    @staticmethod
    def get_week_number(date):
        """获取日期所在的周数（ISO周数）"""
        return date.isocalendar()[1]

    @staticmethod
    def get_quarter(date):
        """获取日期所在的季度"""
        return (date.month - 1) // 3 + 1

    @staticmethod
    def get_first_day_of_month(date):
        """获取当月的第一天"""
        return date.replace(day=1)

    @staticmethod
    def get_last_day_of_month(date):
        """获取当月的最后一天"""
        next_month = date.replace(day=28) + timedelta(days=4)
        return next_month - timedelta(days=next_month.day)

    @staticmethod
    def get_age(birth_date, current_date=None):
        """计算年龄；出生日期晚于基准日期时抛出明确错误"""
        if current_date is None:
            current_date = datetime.date.today()
        if birth_date > current_date:
            raise ValueError(
                f"出生日期 {birth_date} 晚于基准日期 {current_date}，无法计算年龄"
            )
        return current_date.year - birth_date.year - (
                    (current_date.month, current_date.day) < (birth_date.month, birth_date.day))

    @staticmethod
    def format_duration(seconds):
        """格式化时间间隔（秒转换为天、小时、分钟、秒）"""
        sign = "-" if seconds < 0 else ""
        seconds = abs(int(round(seconds)))
        days, remainder = divmod(seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)

        parts = []
        if days > 0:
            parts.append(f"{int(days)}天")
        if hours > 0:
            parts.append(f"{int(hours)}小时")
        if minutes > 0:
            parts.append(f"{int(minutes)}分钟")
        if seconds > 0 or not parts:
            parts.append(f"{int(seconds)}秒")

        return sign + " ".join(parts)

    @staticmethod
    def is_valid_date(date_string, format_str="%Y-%m-%d"):
        """验证日期字符串是否有效"""
        try:
            datetime.datetime.strptime(date_string, format_str)
            return True
        except ValueError:
            return False

    @staticmethod
    def get_timezones():
        """获取常用时区列表（注册中心可扩展）"""
        return datetime_registry.get_timezones()

    @staticmethod
    def get_supported_holiday_countries():
        """获取常用节假日日历国家"""
        return {
            '中国': 'CN',
            '美国': 'US',
            '英国': 'GB',
            '德国': 'DE',
            '日本': 'JP',
            '韩国': 'KR',
        }

    @staticmethod
    def get_week_range(date):
        """获取日期所在周的起始和结束日期（周一到周日）"""
        start = date - timedelta(days=date.weekday())
        end = start + timedelta(days=6)
        return start, end

    @staticmethod
    def get_chinese_zodiac(year):
        """根据年份获取生肖"""
        zodiacs = ['猴', '鸡', '狗', '猪', '鼠', '牛', '虎', '兔', '龙', '蛇', '马', '羊']
        return zodiacs[year % 12]

    @staticmethod
    def get_constellation(month, day):
        """根据月份和日期获取星座；无效日期返回空字符串"""
        if not (isinstance(month, int) and isinstance(day, int)):
            return ""
        try:
            datetime.date(2024, month, day)  # 仅用于校验月日有效性
        except ValueError:
            return ""
        boundaries = [
            (120, '水瓶座'),
            (219, '双鱼座'),
            (321, '白羊座'),
            (420, '金牛座'),
            (521, '双子座'),
            (622, '巨蟹座'),
            (723, '狮子座'),
            (823, '处女座'),
            (923, '天秤座'),
            (1024, '天蝎座'),
            (1123, '射手座'),
            (1222, '摩羯座'),
        ]
        date_num = month * 100 + day
        constellation = '摩羯座'
        for start_num, name in boundaries:
            if date_num >= start_num:
                constellation = name
            else:
                break
        return constellation

    @staticmethod
    def generate_test_dates(start_date, end_date, frequency='daily', count=None):
        """生成测试用的日期序列"""
        if count is not None and count <= 0:
            return []

        if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime) and frequency == 'hourly':
            current = datetime.datetime.combine(start_date, datetime.time.min)
            limit = (
                end_date if isinstance(end_date, datetime.datetime)
                else datetime.datetime.combine(end_date, datetime.time.max)
            )
        else:
            current = start_date
            limit = end_date

        dates = []
        while current <= limit and (count is None or len(dates) < count):
            dates.append(current)

            if frequency == 'daily':
                current += timedelta(days=1)
            elif frequency == 'weekly':
                current += timedelta(weeks=1)
            elif frequency == 'monthly':
                current = DateTimeUtils.add_months(current, 1)
            elif frequency == 'hourly':
                current += timedelta(hours=1)
            else:
                current += timedelta(days=1)
        return dates

    @staticmethod
    def get_working_hours(start_datetime, end_datetime, work_start_hour=9, work_end_hour=17):
        """计算工作时间（排除非工作时间）"""
        if end_datetime <= start_datetime:
            return 0
        DateTimeUtils._validate_work_window(work_start_hour, work_end_hour)
        total_hours = 0
        current = start_datetime

        while current < end_datetime:
            # 检查是否是工作日
            if current.weekday() < 5:  # 周一到周五
                # 检查是否在工作时间内
                work_start = current.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
                work_end = current.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)

                day_start = max(current, work_start)
                day_end = min(end_datetime, work_end)

                if day_start < day_end:
                    total_hours += (day_end - day_start).total_seconds() / 3600

            # 移动到下一天
            current = (current + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        return total_hours

    @staticmethod
    def calculate_sla_due_date(start_datetime, sla_hours, work_start_hour=9, work_end_hour=17, country=None):
        """计算SLA到期时间（可选按国家日历与自定义调休表跳过节假日）"""
        if sla_hours < 0:
            raise ValueError("SLA 时长不能为负数")
        if sla_hours == 0:
            return start_datetime

        DateTimeUtils._validate_work_window(work_start_hour, work_end_hour)
        current = start_datetime
        remaining_hours = sla_hours
        guard = 0  # 防御异常配置导致的死循环
        max_iterations = 100_000

        while remaining_hours > 1e-9 and guard < max_iterations:
            guard += 1
            if DateTimeUtils.is_workday(current.date(), country):
                work_start = current.replace(hour=work_start_hour, minute=0, second=0, microsecond=0)
                work_end = current.replace(hour=work_end_hour, minute=0, second=0, microsecond=0)

                # 调整到工作时间
                if current < work_start:
                    current = work_start
                elif current >= work_end:
                    current = work_start + timedelta(days=1)
                    continue

                # 计算今天剩余的工作时间
                today_remaining = min((work_end - current).total_seconds() / 3600, remaining_hours)

                if today_remaining > 0:
                    current += timedelta(hours=today_remaining)
                    remaining_hours -= today_remaining
                else:
                    current = work_start + timedelta(days=1)
            else:
                # 非工作日，跳到下一个工作日
                current = (current + timedelta(days=1)).replace(hour=work_start_hour, minute=0, second=0, microsecond=0)

        if remaining_hours > 1e-9:
            raise ValueError("SLA 计算迭代超限，请检查工作时间段配置")
        return current

    @staticmethod
    def get_performance_test_timestamps(duration_seconds, requests_per_second, start_datetime=None):
        """生成性能测试时间戳（计划请求数按向上取整）"""
        if duration_seconds <= 0 or requests_per_second <= 0:
            return []

        timestamps = []
        if start_datetime is None:
            start_time = time.time()
        else:
            start_time = start_datetime.timestamp()

        plan_count = math.ceil(duration_seconds * requests_per_second)
        for i in range(plan_count):
            timestamp = start_time + (i / requests_per_second)
            timestamps.append(timestamp)

        return timestamps

    @staticmethod
    def calculate_response_time_percentiles(response_times, percentiles=None):
        """计算响应时间百分位数"""
        if not response_times:
            return {}

        if percentiles is None:
            percentiles = [50, 90, 95, 99]
        elif isinstance(percentiles, (int, float)):
            percentiles = [percentiles]

        clean_times = [v for v in response_times if isinstance(v, (int, float)) and not isinstance(v, bool)]
        if not clean_times:
            return {}
        sorted_times = sorted(clean_times)
        results = {}

        for p in percentiles:
            if not isinstance(p, (int, float)) or not 0 <= p <= 100:
                continue
            if len(sorted_times) == 1:
                results[p] = sorted_times[0]
                continue

            rank = (len(sorted_times) - 1) * (p / 100)
            lower = math.floor(rank)
            upper = math.ceil(rank)
            if lower == upper:
                value = sorted_times[lower]
            else:
                weight = rank - lower
                value = sorted_times[lower] + (sorted_times[upper] - sorted_times[lower]) * weight
            results[p] = round(value, 3)

        return results

    # ------------------------------------------------------------------
    # Cron
    # ------------------------------------------------------------------

    @staticmethod
    def generate_cron_runs(cron_expression, start_date, count=5):
        """解析 cron 表达式并返回结构化结果。

        返回 dict：{'ok': bool, 'runs': [datetime], 'error': str}
        """
        if count is None or int(count) <= 0:
            return {"ok": True, "runs": [], "error": ""}
        try:
            from croniter import croniter
        except ImportError:
            return {
                "ok": False,
                "runs": [],
                "error": "缺少 croniter 依赖。请在部署环境执行: pip install croniter"
                         "（qa-toolkit requirements.txt 已声明该依赖）。",
            }

        if int(count) > 200:
            return {"ok": False, "runs": [], "error": "生成次数过多，单次上限 200。"}

        # 修正：将 date 转换为 datetime
        if isinstance(start_date, datetime.date) and not isinstance(start_date, datetime.datetime):
            base_time = datetime.datetime.combine(start_date, datetime.time(0, 0))
        else:
            base_time = start_date

        try:
            iterator = croniter(cron_expression, base_time)
            next_runs = []
            for _ in range(int(count)):
                next_runs.append(iterator.get_next(datetime.datetime))
            return {"ok": True, "runs": next_runs, "error": ""}
        except Exception as exc:
            return {
                "ok": False,
                "runs": [],
                "error": f"Cron 表达式无法解析: {exc}。"
                         "标准格式为“分 时 日 月 周”，例如 0 9 * * 1-5 表示工作日 09:00。",
            }

    @staticmethod
    def generate_cron_next_runs(cron_expression, start_date, count=5):
        """兼容旧接口：正常时返回 datetime 列表，失败时返回含单条错误说明的列表。"""
        result = DateTimeUtils.generate_cron_runs(cron_expression, start_date, count)
        if result["ok"]:
            return result["runs"]
        return [result["error"]]

    # ------------------------------------------------------------------
    # 节假日
    # ------------------------------------------------------------------

    @staticmethod
    def is_holiday(date, country='CN'):
        """判断是否是节假日（优先应用自定义覆盖表）"""
        if not country:
            return False
        override = DateTimeUtils._calendar_override(country)
        if override is not None:
            if date in override.extra_workdays:
                return False
            if date in override.extra_holidays:
                return True
        try:
            country_holidays = DateTimeUtils._get_country_holidays(country, years=[date.year])
            return date in country_holidays
        except Exception:
            # 节假日库不支持该年份/地区时按“无节假日数据”处理，不再静默吞掉所有异常
            return False

    @staticmethod
    def get_timezone_conversion(dt, from_tz, to_tz):
        """时区转换；无效时区或夏令时歧义时间抛出明确错误"""
        try:
            from_zone = pytz.timezone(from_tz)
        except Exception as exc:
            raise ValueError(f"无效的源时区 {from_tz!r}: {exc}") from exc
        try:
            to_zone = pytz.timezone(to_tz)
        except Exception as exc:
            raise ValueError(f"无效的目标时区 {to_tz!r}: {exc}") from exc

        if dt.tzinfo is None:
            try:
                localized_dt = from_zone.localize(dt, is_dst=None)
            except pytz.NonExistentTimeError as exc:
                raise ValueError(
                    f"本地时间 {dt} 在 {from_tz} 不存在（夏令时切换跳过了该时刻）: {exc}"
                ) from exc
            except pytz.AmbiguousTimeError as exc:
                raise ValueError(
                    f"本地时间 {dt} 在 {from_tz} 有歧义（夏令时回拨出现两次），请改用带时区的时间: {exc}"
                ) from exc
        else:
            localized_dt = dt.astimezone(from_zone)
        return localized_dt.astimezone(to_zone)

    @staticmethod
    def calculate_business_hours_diff(start_dt, end_dt, business_hours=(9, 17), country=None):
        """计算两个日期时间之间的实际工作时间差（可选按国家日历排除节假日）"""
        if start_dt == end_dt:
            return 0

        DateTimeUtils._validate_work_window(business_hours[0], business_hours[1])
        direction = 1 if end_dt > start_dt else -1
        current = min(start_dt, end_dt)
        end_limit = max(start_dt, end_dt)
        business_seconds = 0
        guard = 0
        max_iterations = 200_000

        while current < end_limit and guard < max_iterations:
            guard += 1
            if DateTimeUtils.is_workday(current.date(), country):
                day_start = current.replace(hour=business_hours[0], minute=0, second=0, microsecond=0)
                day_end = current.replace(hour=business_hours[1], minute=0, second=0, microsecond=0)

                # 调整到工作时间
                if current < day_start:
                    current = day_start
                if end_limit > day_end:
                    segment_end = day_end
                else:
                    segment_end = end_limit

                if current < segment_end:
                    business_seconds += (segment_end - current).total_seconds()

            # 移动到下一天
            current = (current + timedelta(days=1)).replace(hour=business_hours[0], minute=0, second=0, microsecond=0)

        if guard >= max_iterations and current < end_limit:
            raise ValueError("工作时间计算迭代超限，请检查区间大小")
        return direction * (business_seconds / 3600)

    @staticmethod
    def add_business_days(source_date, business_days, country=None):
        """在指定日期上偏移工作日（偏移量有上限保护）"""
        if business_days == 0:
            return source_date

        remaining_days = abs(int(business_days))
        if remaining_days > MAX_BUSINESS_DAY_OFFSET:
            raise ValueError(
                f"工作日偏移量过大（{business_days}），单次上限 ±{MAX_BUSINESS_DAY_OFFSET}"
            )
        direction = 1 if business_days > 0 else -1

        current = source_date
        while remaining_days > 0:
            current += timedelta(days=direction)
            if not DateTimeUtils.is_workday(current, country):
                continue
            remaining_days -= 1

        return current

    @staticmethod
    def summarize_date_range(start_date, end_date, country=None):
        """输出日期区间摘要（节假日库不支持的年份按无节假日数据降级）"""
        if start_date is None or end_date is None:
            return {
                "signed_diff_days": 0, "weekend_days": 0, "holiday_days": 0,
                "holiday_only_days": 0, "total_days": 0, "invalid": True,
            }
        ordered_start = min(start_date, end_date)
        ordered_end = max(start_date, end_date)
        sign = 1 if end_date >= start_date else -1
        weekend_days = 0
        holiday_days = 0
        holiday_only_days = 0
        unsupported_years = set()
        current = ordered_start

        holiday_dates = {}
        if country:
            holiday_dates, unsupported_years = DateTimeUtils._get_country_holidays_safe(
                country, years=range(ordered_start.year, ordered_end.year + 1),
            )

        while current <= ordered_end:
            is_weekend = current.weekday() >= 5
            override = DateTimeUtils.apply_calendar_override(current, None, country)
            if override is True:
                is_holiday = False  # 自定义调休上班日不算节假日
            elif override is False or (country and current in holiday_dates):
                is_holiday = True
            else:
                is_holiday = False

            if is_weekend:
                weekend_days += 1
            if is_holiday:
                holiday_days += 1
                if not is_weekend:
                    holiday_only_days += 1
            current += timedelta(days=1)

        business_days = DateTimeUtils.count_business_days(ordered_start, ordered_end, country=country)

        return {
            "start": ordered_start,
            "end": ordered_end,
            "signed_diff_days": (end_date - start_date).days,
            "calendar_days": (ordered_end - ordered_start).days + 1,
            "business_days": business_days * sign,
            "weekend_days": weekend_days,
            "holiday_days": holiday_days,
            "holiday_only_days": holiday_only_days,
            "unsupported_holiday_years": sorted(unsupported_years),
        }

    # ------------------------------------------------------------------
    # 解析
    # ------------------------------------------------------------------

    @staticmethod
    def weekday_name(value, locale='zh'):
        """返回星期名称，locale='zh' 返回中文（默认），'en' 返回英文缩写风格 %A。"""
        if locale == 'zh':
            return WEEKDAY_ZH[value.weekday()]
        return value.strftime('%A')

    @staticmethod
    def parse_datetime_input(value, timezone_name='Asia/Shanghai'):
        """解析时间戳或常见日期时间字符串"""
        raw_text = str(value or '').strip()
        if not raw_text:
            raise ValueError("请输入时间戳或日期时间，例如 1712361600 或 2026-04-06 09:30:00")

        try:
            target_timezone = pytz.timezone(timezone_name)
        except Exception as exc:
            raise ValueError(f"无效的时区 {timezone_name!r}: {exc}") from exc

        if DateTimeUtils._looks_like_timestamp(raw_text):
            raw_value = float(raw_text)
            integer_part = raw_text.lstrip('-').split('.', 1)[0]
            digits = len(integer_part)
            if digits >= 16:
                precision, divisor = '微秒', 1_000_000
            elif digits >= 13:
                precision, divisor = '毫秒', 1000
            else:
                precision, divisor = '秒', 1
            seconds = raw_value / divisor
            try:
                parsed_dt = datetime.datetime.fromtimestamp(seconds, tz=target_timezone)
            except (OverflowError, OSError, ValueError) as exc:
                raise ValueError(f"时间戳 {raw_text} 超出可表示的时间范围: {exc}") from exc
            input_type = f'时间戳({precision})'
        else:
            custom_formats = datetime_registry.get_custom_parse_formats()
            parsed_dt = None
            for fmt in custom_formats:
                try:
                    parsed_dt = datetime.datetime.strptime(raw_text, fmt)
                    break
                except ValueError:
                    continue
            if parsed_dt is None:
                try:
                    parsed_dt = dateutil_parser.parse(raw_text)
                except (ValueError, OverflowError) as exc:
                    raise ValueError(
                        f"无法识别的时间格式“{raw_text}”: {exc}。"
                        "支持 10/13/16 位时间戳、YYYY-MM-DD HH:MM:SS 及常见 ISO8601 格式。"
                    ) from exc
            if parsed_dt.tzinfo is None:
                try:
                    parsed_dt = target_timezone.localize(parsed_dt, is_dst=None)
                except pytz.NonExistentTimeError as exc:
                    raise ValueError(f"该本地时间在 {timezone_name} 不存在（夏令时切换）: {exc}") from exc
                except pytz.AmbiguousTimeError as exc:
                    raise ValueError(f"该本地时间在 {timezone_name} 有歧义（夏令时回拨）: {exc}") from exc
                input_type = '日期时间'
            else:
                parsed_dt = parsed_dt.astimezone(target_timezone)
                input_type = '带时区日期时间'

        timestamp_seconds = parsed_dt.timestamp()
        return {
            'raw_input': raw_text,
            'input_type': input_type,
            'timezone': timezone_name,
            'datetime': parsed_dt,
            'display_text': parsed_dt.strftime('%Y-%m-%d %H:%M:%S %Z%z'),
            'isoformat': parsed_dt.isoformat(),
            'timestamp_seconds': int(timestamp_seconds),
            'timestamp_milliseconds': int(timestamp_seconds * 1000),
            'weekday': parsed_dt.strftime('%A'),
            'weekday_zh': DateTimeUtils.weekday_name(parsed_dt),
        }

    @staticmethod
    def batch_convert_temporal_values(text, timezone_name='Asia/Shanghai'):
        """批量解析多行时间输入（失败行给出可操作的中文诊断）"""
        rows = []
        for index, line in enumerate(str(text or '').splitlines(), start=1):
            raw_text = line.strip()
            if not raw_text:
                continue

            try:
                parsed = DateTimeUtils.parse_datetime_input(raw_text, timezone_name)
                rows.append(
                    {
                        '序号': index,
                        '输入': raw_text,
                        '状态': '成功',
                        '类型': parsed['input_type'],
                        '日期时间': parsed['display_text'],
                        '星期': parsed['weekday_zh'],
                        '秒级时间戳': parsed['timestamp_seconds'],
                        '毫秒级时间戳': parsed['timestamp_milliseconds'],
                        'ISO8601': parsed['isoformat'],
                    }
                )
            except Exception as exc:
                rows.append(
                    {
                        '序号': index,
                        '输入': raw_text,
                        '状态': '失败',
                        '类型': '-',
                        '日期时间': DateTimeUtils._friendly_parse_error(exc),
                        '星期': '-',
                        '秒级时间戳': '',
                        '毫秒级时间戳': '',
                        'ISO8601': '',
                    }
                )

        return rows

    @staticmethod
    def get_multi_timezone_snapshot(dt, timezone_names, source_timezone_name=None):
        """将同一时刻转换为多个时区视图"""
        if dt.tzinfo is None:
            if not source_timezone_name:
                raise ValueError("源时间缺少时区信息")
            try:
                dt = pytz.timezone(source_timezone_name).localize(dt, is_dst=None)
            except pytz.NonExistentTimeError as exc:
                raise ValueError(f"该本地时间在 {source_timezone_name} 不存在（夏令时切换）: {exc}") from exc
            except pytz.AmbiguousTimeError as exc:
                raise ValueError(f"该本地时间在 {source_timezone_name} 有歧义（夏令时回拨）: {exc}") from exc

        rows = []
        for timezone_name in timezone_names:
            try:
                target_zone = pytz.timezone(timezone_name)
            except Exception as exc:
                raise ValueError(f"无效的时区 {timezone_name!r}: {exc}") from exc
            converted = dt.astimezone(target_zone)
            rows.append(
                {
                    '时区': timezone_name,
                    '当地时间': converted.strftime('%Y-%m-%d %H:%M:%S'),
                    '缩写': converted.strftime('%Z'),
                    'UTC偏移': converted.strftime('%z'),
                    '星期': DateTimeUtils.weekday_name(converted),
                }
            )
        return rows

    @staticmethod
    def _looks_like_timestamp(raw_text):
        if not re.fullmatch(r"-?\d+(\.\d+)?", raw_text):
            return False
        integer_part = raw_text.lstrip('-').split('.', 1)[0]
        return len(integer_part) in {10, 13, 16}

    @staticmethod
    def _friendly_parse_error(exc):
        """把解析异常转成可操作的中文诊断。"""
        text = str(exc)
        lowered = text.lower()
        if '无法识别的时间格式' in text or '请输入时间戳或日期时间' in text or '超出可表示' in text:
            return text
        if 'could not convert string to float' in lowered:
            return "输入不是时间戳也不是可识别的日期时间；请检查是否混入了单位或符号（支持 10/13/16 位时间戳、YYYY-MM-DD HH:MM:SS）"
        if 'unknown string format' in lowered:
            return f"无法识别的时间格式（{text}）；支持 10/13/16 位时间戳、YYYY-MM-DD HH:MM:SS 及 ISO8601"
        if 'year' in lowered and 'out of range' in lowered:
            return "时间超出可表示范围（1-9999 年），请检查时间戳位数是否正确"
        return f"解析失败: {text}"

    @staticmethod
    def _validate_work_window(work_start_hour, work_end_hour):
        if work_start_hour < 0 or work_end_hour > 24 or work_start_hour >= work_end_hour:
            raise ValueError("工作时间范围无效，请确保开始小时小于结束小时")

    @staticmethod
    def _get_country_holidays(country, years=None):
        """构造节假日对象；节假日库不支持或构造失败的年份自动跳过。"""
        import holidays as holidays_lib

        if years is None:
            years = [datetime.date.today().year]
        merged = holidays_lib.HolidayBase()
        for year in years:
            try:
                merged.update(holidays_lib.country_holidays(country, years=[year]))
            except Exception:
                # 该年份/地区不受支持（如 2100+ 年），视为无节假日数据
                continue
        return merged

    @staticmethod
    def _get_country_holidays_safe(country, years=None):
        """返回 (节假日集合, 不受支持年份集合)，供区间统计标注数据缺口。"""
        import holidays as holidays_lib

        if years is None:
            years = [datetime.date.today().year]
        merged = holidays_lib.HolidayBase()
        unsupported = set()
        for year in years:
            try:
                merged.update(holidays_lib.country_holidays(country, years=[year]))
            except Exception:
                unsupported.add(year)
        return merged, unsupported
