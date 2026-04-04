import datetime
import time
from datetime import timedelta

import holidays as holidays
import pytz
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
        return datetime.date(year, month, day)

    @staticmethod
    def subtract_months(source_date, months):
        """从日期减去指定月数"""
        month = source_date.month - 1 - months
        year = source_date.year + month // 12
        month = month % 12 + 1
        if month <= 0:
            year -= 1
            month += 12
        day = min(source_date.day, DateTimeUtils.days_in_month(year, month))
        return datetime.date(year, month, day)

    @staticmethod
    def count_business_days(start_date, end_date):
        """计算两个日期之间的工作日数量（周一到周五）"""
        total_days = (end_date - start_date).days + 1
        full_weeks, extra_days = divmod(total_days, 7)
        business_days = full_weeks * 5
        for i in range(extra_days):
            current_day = start_date + timedelta(days=i)
            if current_day.weekday() < 5:
                business_days += 1
        return business_days

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

        return " ".join(parts)

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
            '东京': 'Asia/Tokyo',
            '纽约': 'America/New_York',
            '伦敦': 'Europe/London',
            '巴黎': 'Europe/Paris',
            '悉尼': 'Australia/Sydney'
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
        constellations = [
            (120, '摩羯座'), (219, '水瓶座'), (321, '双鱼座'), (420, '白羊座'),
            (521, '金牛座'), (621, '双子座'), (723, '巨蟹座'), (823, '狮子座'),
            (923, '处女座'), (1023, '天秤座'), (1122, '天蝎座'), (1222, '射手座'),
            (1232, '摩羯座')
        ]
        date_num = month * 100 + day
        for i in range(len(constellations)):
            if date_num <= constellations[i][0]:
                return constellations[i][1]
        return '摩羯座'
        # 新增测试开发专用功能

    @staticmethod
    def generate_test_dates(start_date, end_date, frequency='daily', count=None):
        """生成测试用的日期序列"""
        if frequency == 'daily':
            delta = timedelta(days=1)
        elif frequency == 'weekly':
            delta = timedelta(weeks=1)
        elif frequency == 'monthly':
            delta = timedelta(days=30)  # 近似值
        elif frequency == 'hourly':
            delta = timedelta(hours=1)
        else:
            delta = timedelta(days=1)

        dates = []
        current = start_date
        while current <= end_date and (count is None or len(dates) < count):
            dates.append(current)
            current += delta
        return dates

    @staticmethod
    def get_working_hours(start_datetime, end_datetime, work_start_hour=9, work_end_hour=17):
        """计算工作时间（排除非工作时间）"""
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
    def calculate_response_time_percentiles(response_times, percentiles=[50, 90, 95, 99]):
        """计算响应时间百分位数"""
        sorted_times = sorted(response_times)
        results = {}

        for p in percentiles:
            index = int(len(sorted_times) * p / 100)
            results[p] = sorted_times[index] if index < len(sorted_times) else sorted_times[-1]

        return results

    @staticmethod
    def generate_cron_next_runs(cron_expression, start_date, count=5):
        """生成cron表达式的下一次执行时间"""
        try:
            from croniter import croniter
            # 修正：将 date 转换为 datetime
            if isinstance(start_date, datetime.date):
                base_time = datetime.datetime.combine(start_date, datetime.time(0, 0))
            else:
                base_time = start_date

            iter = croniter(cron_expression, base_time)
            next_runs = []

            for _ in range(count):
                next_run = iter.get_next(datetime.datetime)
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
            country_holidays = holidays.CountryHoliday(country)
            return date in country_holidays
        except:
            return False

    @staticmethod
    def get_timezone_conversion(dt, from_tz, to_tz):
        """时区转换"""
        try:
            from_zone = pytz.timezone(from_tz)
            to_zone = pytz.timezone(to_tz)

            localized_dt = from_zone.localize(dt)
            converted_dt = localized_dt.astimezone(to_zone)

            return converted_dt
        except:
            return dt

    @staticmethod
    def calculate_business_hours_diff(start_dt, end_dt, business_hours=(9, 17)):
        """计算两个日期时间之间的实际工作时间差"""
        business_seconds = 0
        current = start_dt

        while current < end_dt:
            # 检查是否是工作日
            if current.weekday() < 5:
                day_start = current.replace(hour=business_hours[0], minute=0, second=0, microsecond=0)
                day_end = current.replace(hour=business_hours[1], minute=0, second=0, microsecond=0)

                # 调整到工作时间
                if current < day_start:
                    current = day_start
                if end_dt > day_end:
                    segment_end = day_end
                else:
                    segment_end = end_dt

                if current < segment_end:
                    business_seconds += (segment_end - current).total_seconds()

            # 移动到下一天
            current = (current + timedelta(days=1)).replace(hour=business_hours[0], minute=0, second=0, microsecond=0)

        return business_seconds / 3600  # 返回小时数