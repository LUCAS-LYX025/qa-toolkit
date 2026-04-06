import datetime
import math
import re
import time
from datetime import timedelta

import holidays
import pytz
from dateutil import parser


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
        return days_per_month[month - 1]

    @staticmethod
    def add_months(source_date, months):
        """添加指定月数到日期"""
        month = source_date.month - 1 + months
        year = source_date.year + month // 12
        month = month % 12 + 1
        day = min(source_date.day, DateTimeUtils.days_in_month(year, month))
        if isinstance(source_date, datetime.datetime):
            return source_date.replace(year=year, month=month, day=day)
        return datetime.date(year, month, day)

    @staticmethod
    def subtract_months(source_date, months):
        """从日期减去指定月数"""
        return DateTimeUtils.add_months(source_date, -months)

    @staticmethod
    def count_business_days(start_date, end_date, country=None):
        """计算两个日期之间的工作日数量（可选排除节假日）"""
        if start_date == end_date:
            if start_date.weekday() >= 5:
                return 0
            if country and DateTimeUtils.is_holiday(start_date, country):
                return 0
            return 1

        direction = 1 if end_date >= start_date else -1
        range_start = min(start_date, end_date)
        range_end = max(start_date, end_date)

        if country:
            holiday_dates = DateTimeUtils._get_country_holidays(
                country,
                years=range(range_start.year, range_end.year + 1),
            )
            business_days = 0
            current_day = range_start
            while current_day <= range_end:
                if current_day.weekday() < 5 and current_day not in holiday_dates:
                    business_days += 1
                current_day += timedelta(days=1)
            return business_days * direction

        total_days = (range_end - range_start).days + 1
        full_weeks, extra_days = divmod(total_days, 7)
        business_days = full_weeks * 5
        for i in range(extra_days):
            current_day = range_start + timedelta(days=i)
            if current_day.weekday() < 5:
                business_days += 1
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
        """计算年龄"""
        if current_date is None:
            current_date = datetime.date.today()
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
        """获取常用时区列表"""
        return {
            'UTC': 'UTC',
            '北京': 'Asia/Shanghai',
            '新加坡': 'Asia/Singapore',
            '东京': 'Asia/Tokyo',
            '首尔': 'Asia/Seoul',
            '纽约': 'America/New_York',
            '洛杉矶': 'America/Los_Angeles',
            '伦敦': 'Europe/London',
            '巴黎': 'Europe/Paris',
            '柏林': 'Europe/Berlin',
            '迪拜': 'Asia/Dubai',
            '孟买': 'Asia/Kolkata',
            '悉尼': 'Australia/Sydney'
        }

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
        """根据月份和日期获取星座"""
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
    def calculate_sla_due_date(start_datetime, sla_hours, work_start_hour=9, work_end_hour=17):
        """计算SLA到期时间"""
        if sla_hours < 0:
            raise ValueError("SLA 时长不能为负数")
        if sla_hours == 0:
            return start_datetime

        DateTimeUtils._validate_work_window(work_start_hour, work_end_hour)
        current = start_datetime
        remaining_hours = sla_hours

        while remaining_hours > 0:
            # 如果是工作日
            if current.weekday() < 5:
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

        return current

    @staticmethod
    def get_performance_test_timestamps(duration_seconds, requests_per_second, start_datetime=None):
        """生成性能测试时间戳"""
        if duration_seconds <= 0 or requests_per_second <= 0:
            return []

        timestamps = []
        if start_datetime is None:
            start_time = time.time()
        else:
            start_time = start_datetime.timestamp()

        for i in range(int(duration_seconds * requests_per_second)):
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

        sorted_times = sorted(response_times)
        results = {}

        for p in percentiles:
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

    @staticmethod
    def generate_cron_next_runs(cron_expression, start_date, count=5):
        """生成cron表达式的下一次执行时间"""
        if count <= 0:
            return []
        try:
            from croniter import croniter
            # 修正：将 date 转换为 datetime
            if isinstance(start_date, datetime.date):
                base_time = datetime.datetime.combine(start_date, datetime.time(0, 0))
            else:
                base_time = start_date

            iterator = croniter(cron_expression, base_time)
            next_runs = []

            for _ in range(count):
                next_run = iterator.get_next(datetime.datetime)
                next_runs.append(next_run)

            return next_runs
        except ImportError:
            return ["需要安装croniter库: pip install croniter"]
        except Exception as e:
            return [f"解析错误: {str(e)}"]

    @staticmethod
    def is_holiday(date, country='CN'):
        """判断是否是节假日"""
        try:
            country_holidays = DateTimeUtils._get_country_holidays(country)
            return date in country_holidays
        except Exception:
            return False

    @staticmethod
    def get_timezone_conversion(dt, from_tz, to_tz):
        """时区转换"""
        try:
            from_zone = pytz.timezone(from_tz)
            to_zone = pytz.timezone(to_tz)

            if dt.tzinfo is None:
                localized_dt = from_zone.localize(dt)
            else:
                localized_dt = dt.astimezone(from_zone)
            converted_dt = localized_dt.astimezone(to_zone)

            return converted_dt
        except Exception:
            return dt

    @staticmethod
    def calculate_business_hours_diff(start_dt, end_dt, business_hours=(9, 17)):
        """计算两个日期时间之间的实际工作时间差"""
        if start_dt == end_dt:
            return 0

        DateTimeUtils._validate_work_window(business_hours[0], business_hours[1])
        direction = 1 if end_dt > start_dt else -1
        current = min(start_dt, end_dt)
        end_limit = max(start_dt, end_dt)
        business_seconds = 0

        while current < end_limit:
            # 检查是否是工作日
            if current.weekday() < 5:
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

        return direction * (business_seconds / 3600)

    @staticmethod
    def add_business_days(source_date, business_days, country=None):
        """在指定日期上偏移工作日"""
        if business_days == 0:
            return source_date

        current = source_date
        remaining_days = abs(int(business_days))
        direction = 1 if business_days > 0 else -1

        while remaining_days > 0:
            current += timedelta(days=direction)
            if current.weekday() >= 5:
                continue
            if country and DateTimeUtils.is_holiday(current, country):
                continue
            remaining_days -= 1

        return current

    @staticmethod
    def summarize_date_range(start_date, end_date, country=None):
        """输出日期区间摘要"""
        ordered_start = min(start_date, end_date)
        ordered_end = max(start_date, end_date)
        sign = 1 if end_date >= start_date else -1
        weekend_days = 0
        holiday_days = 0
        holiday_only_days = 0
        current = ordered_start

        while current <= ordered_end:
            is_weekend = current.weekday() >= 5
            is_holiday = bool(country) and DateTimeUtils.is_holiday(current, country)
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
        }

    @staticmethod
    def parse_datetime_input(value, timezone_name='Asia/Shanghai'):
        """解析时间戳或常见日期时间字符串"""
        raw_text = str(value or '').strip()
        if not raw_text:
            raise ValueError("请输入时间戳或日期时间")

        target_timezone = pytz.timezone(timezone_name)
        if DateTimeUtils._looks_like_timestamp(raw_text):
            raw_value = float(raw_text)
            integer_part = raw_text.lstrip('-').split('.', 1)[0]
            precision = '毫秒' if len(integer_part) >= 13 else '秒'
            seconds = raw_value / 1000 if precision == '毫秒' else raw_value
            parsed_dt = datetime.datetime.fromtimestamp(seconds, tz=target_timezone)
            input_type = f'时间戳({precision})'
        else:
            parsed_dt = parser.parse(raw_text)
            if parsed_dt.tzinfo is None:
                parsed_dt = target_timezone.localize(parsed_dt)
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
        }

    @staticmethod
    def batch_convert_temporal_values(text, timezone_name='Asia/Shanghai'):
        """批量解析多行时间输入"""
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
                        '日期时间': str(exc),
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
            dt = pytz.timezone(source_timezone_name).localize(dt)

        rows = []
        for timezone_name in timezone_names:
            converted = dt.astimezone(pytz.timezone(timezone_name))
            rows.append(
                {
                    '时区': timezone_name,
                    '当地时间': converted.strftime('%Y-%m-%d %H:%M:%S'),
                    '缩写': converted.strftime('%Z'),
                    'UTC偏移': converted.strftime('%z'),
                    '星期': converted.strftime('%A'),
                }
            )
        return rows

    @staticmethod
    def _looks_like_timestamp(raw_text):
        if not re.fullmatch(r"-?\d+(\.\d+)?", raw_text):
            return False
        integer_part = raw_text.lstrip('-').split('.', 1)[0]
        return len(integer_part) in {10, 13}

    @staticmethod
    def _validate_work_window(work_start_hour, work_end_hour):
        if work_start_hour < 0 or work_end_hour > 24 or work_start_hour >= work_end_hour:
            raise ValueError("工作时间范围无效，请确保开始小时小于结束小时")

    @staticmethod
    def _get_country_holidays(country, years=None):
        try:
            return holidays.country_holidays(country, years=years)
        except AttributeError:
            return holidays.CountryHoliday(country, years=years)
