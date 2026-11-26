"""纯 Python 绩效与 SLA 计算引擎（无 SQL、无 Streamlit、无平台依赖）。

职责：把「统一工作项 WorkItem 列表」按注册的归因规则 + SLA 规则 + 绩效规则
计算成 ``PerformanceRow`` 汇总与 ``TimeoutDetail`` 明细。所有平台适配器只要
产出统一模型，就能复用这里的一整套计算逻辑。

关键设计：
- 归因规则（AttributionRuleSpec）决定「按哪些人员字段归因」「SLA 起止字段」；
- SLA 规则（SlaRuleSpec）决定「一级/普通判定」「工作日/周末/节假日阈值」；
- 阈值按起止时间**逐小时**累加（每小时按其落在的日历类型取对应阈值），
  这是原禅道 SQL `CASE WHEN ... TIMESTAMPDIFF` 的更精确、可测试的等价实现；
- 计算过程不产生任何 UI 副作用；周假日历缺失时返回告警而非崩溃。
"""
from __future__ import annotations

from datetime import date, datetime, time, timedelta
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from qa_toolkit.core import tracking_registry as registry
from qa_toolkit.integrations.tracking.models import (
    Person, PerformanceRow, QuerySpec, TimeoutDetail, WorkItem,
)


def _as_datetime(value: Any) -> Optional[datetime]:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime.combine(value, time.min)
    if value is None or value == "":
        return None
    text = str(value).strip().replace("T", " ")
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _holiday_set(country: Optional[str], years: Sequence[int]) -> Tuple[set, List[str]]:
    """返回 (节假日日期集合, 告警列表)；无日历/不支持年份时安全降级。"""
    warnings: List[str] = []
    if not country:
        return set(), warnings
    try:
        from qa_toolkit.utils.datetime_tools import DateTimeUtils
        merged, unsupported = DateTimeUtils._get_country_holidays_safe(
            country, years=list(years))
        days = {d for d in merged}
        if unsupported:
            warnings.append(f"节假日日历不支持年份 {sorted(unsupported)}，这些年份按工作日处理")
        return days, warnings
    except Exception as exc:  # 节假日库缺失等
        warnings.append(f"节假日日历不可用（{exc}），全部按工作日处理")
        return set(), warnings


def _hour_is_weekend(moment: datetime) -> bool:
    return moment.weekday() >= 5


def compute_effective_hours(start: datetime, end: datetime, *,
                            holiday_country: Optional[str] = None,
                            count_weekend: bool = True,
                            count_holiday: bool = True) -> Tuple[float, List[str]]:
    """计算区间内的「有效工时」：逐小时判断该小时是否计入 SLA。

    语义对齐原禅道 SQL：SLA 阈值（如 high=24h / normal=72h）是**允许的工时上限**，
    超时判定为 ``有效工时 > 阈值``；周末/节假日是否计入由规则决定。历史实现曾把
    阈值逐小时累加（100 小时算出 2400 允许小时、永不超时），属于严重假绿，已修正。

    区间按半开区间 ``[start, end)`` 计算：9:00→12:00 是 3 小时而不是 4 小时；
    不足整小时的部分按实际占比计入。返回 ``(有效小时数, 告警)``；end <= start 返回 0。
    极端跨度按 366 天截断，避免恶意数据导致逐小时循环爆炸。
    """
    warnings: List[str] = []
    if end <= start:
        return 0.0, warnings
    years = list(range(start.year, end.year + 1))
    holidays, warnings = _holiday_set(holiday_country, years) if count_holiday else (set(), warnings)
    effective = 0.0
    cursor = start.replace(minute=0, second=0, microsecond=0)
    max_buckets = min(int((end - start).total_seconds() // 3600) + 2, 366 * 24)
    for _ in range(max_buckets):
        if cursor >= end:
            break  # 半开区间：终点整点不计入
        bucket_end = cursor + timedelta(hours=1)
        overlap_start = max(cursor, start)
        overlap_end = min(bucket_end, end)
        weight = (overlap_end - overlap_start).total_seconds() / 3600.0
        if weight > 0:
            moment = cursor
            is_weekend = _hour_is_weekend(moment)
            is_holiday = moment.date() in holidays
            # 工作日恒计入；周末/节假日按规则计入（节假日优先于周末）。
            included = (is_holiday and count_holiday) or (not is_holiday and (
                count_weekend if is_weekend else True))
            if included:
                effective += weight
        cursor = bucket_end
    return round(float(effective), 6), warnings


def is_high_priority(item: WorkItem, sla: Any) -> bool:
    fields = tuple(getattr(sla, "high_priority_fields", ("severity", "priority")))
    values = tuple(getattr(sla, "high_priority_values", (1,)))
    for field_name in fields:
        if item.person_for(field_name) in {str(v) for v in values}:
            return True
        raw = getattr(item, field_name, None)
        if raw in values or str(raw) in {str(v) for v in values}:
            return True
    return False


def _threshold_for(item: WorkItem, sla: Any, cfg: Dict[str, int],
                   end: Optional[datetime] = None) -> Tuple[int, bool]:
    """选择 SLA 阈值（允许工时）。终点落在周末时用 weekend 档，否则 normal 档。

    配置键既支持通用 normal/weekend，也兼容旧四阈值命名
    （high_normal / high_weekend / normal_normal / normal_weekend）。
    """
    high = is_high_priority(item, sla)
    normal_key = getattr(sla, "normal_hours_key", "normal")
    weekend_key = getattr(sla, "weekend_hours_key", "weekend")
    weekend = bool(end and _hour_is_weekend(end))
    chosen_key = weekend_key if weekend else normal_key
    high_legacy = "high_weekend" if weekend else "high_normal"
    normal_legacy = "normal_weekend" if weekend else "normal_normal"

    def pick(legacy_key: str, fallback_hours: int) -> int:
        # 规则声明的自定义键优先；normal/weekend 是兼容键，不能覆盖优先级专属 legacy 键。
        if chosen_key not in ("normal", "weekend") and chosen_key in cfg:
            return int(cfg[chosen_key])
        if legacy_key in cfg:
            return int(cfg[legacy_key])
        if chosen_key in cfg:
            return int(cfg[chosen_key])
        return fallback_hours

    hours = pick(high_legacy, 24) if high else pick(normal_legacy, 72)
    return hours, high


def compute_performance(
    items: Iterable[WorkItem],
    *,
    attribution_key: str = "qa",
    sla_key: str = "default",
    performance_key: str = "timeout_rate",
    query: Optional[QuerySpec] = None,
    people: Optional[Sequence[Person]] = None,
    now: Optional[datetime] = None,
) -> Tuple[List[PerformanceRow], List[TimeoutDetail], List[str]]:
    """按统一模型计算绩效汇总与超时明细。

    返回 ``(汇总行, 超时明细, 告警)``。纯函数：无 UI 副作用、不修改入参。
    """
    warnings: List[str] = []
    spec = query or QuerySpec()
    attribution = registry.get_attribution(attribution_key)
    sla = registry.get_sla_rule(sla_key)
    perf = registry.get_performance_rule(performance_key)
    if attribution is None:
        raise ValueError(f"未知归因规则：{attribution_key}")
    if sla is None:
        raise ValueError(f"未知 SLA 规则：{sla_key}")
    if perf is None:
        raise ValueError(f"未知绩效规则：{performance_key}")

    now = now or datetime.now()
    cfg = {k: registry.clamp_hours(v, k) for k, v in (spec.sla or {}).items()}
    country = spec.holiday_country

    # 人员字典：显式传入优先，否则从工作项归因字段收集。
    person_index: Dict[str, Person] = {}
    for p in people or ():
        for key in p.match_values:
            person_index[str(key)] = p

    rows: Dict[str, Dict[str, Any]] = {}
    details: List[TimeoutDetail] = []

    def ensure_row(person: Person) -> Dict[str, Any]:
        key = person.id or person.display_name
        if key not in rows:
            rows[key] = {
                "person": person, "high": 0, "normal": 0, "count": 0,
            }
        return rows[key]

    for item in items:
        if item.deleted:
            continue
        if spec.exclude_types and item.item_type in spec.exclude_types:
            continue
        if spec.start_date and item.opened_at and item.opened_at.date() < spec.start_date:
            continue
        if spec.end_date and item.opened_at and item.opened_at.date() > spec.end_date:
            continue

        # 归因：按顺序取第一个非空的人员字段。
        person_name = ""
        for field_name in attribution.person_fields:
            value = item.person_for(field_name)
            if value:
                person_name = value
                break
        if not person_name:
            continue
        person = person_index.get(person_name) or Person(
            id=person_name, display_name=person_name, account=person_name)
        if spec.roles:
            role_keys = {str(role) for role in spec.roles}
            if not any(str(value) in role_keys for value in person.match_values):
                continue
        row = ensure_row(person)

        # 基数按归因规则决定；不再输出与归因人无关的「提交数」列（与基数口径冲突）。
        row["count"] += 1

        start = _as_datetime(getattr(item, attribution.start_field, None))
        end = _as_datetime(getattr(item, attribution.end_field, None)) if attribution.end_field else None
        if start is None:
            # 没有起止时间无法判 SLA，计数但仍可参与基数统计。
            continue
        end = end or now
        if end < start:
            warnings.append(f"工作项 {item.id} 的结束时间早于开始时间，已按 0 处理")
            end = start

        threshold_hours, high = _threshold_for(item, sla, cfg, end=end)
        effective, w = compute_effective_hours(
            start, end, holiday_country=country,
            count_weekend=bool(getattr(sla, "count_weekend", True)),
            count_holiday=bool(getattr(sla, "count_holiday", True)),
        )
        warnings.extend(w)
        # SLA 阈值是允许的工时上限；有效工时超过阈值才算超时（不是逐小时累加阈值）。
        if effective > threshold_hours:
            row["high" if high else "normal"] += 1
            details.append(TimeoutDetail(
                item=item,
                timeout_level="一级超时" if high else "普通超时",
                threshold_hours=threshold_hours,
                duration_hours=effective,
                timeout_kind="关闭超时" if attribution.end_field == "closed_at" else "响应超时",
                person=person.display_name,
            ))

    summary: List[PerformanceRow] = []
    for data in rows.values():
        person = data["person"]
        total_timeout = data["high"] + data["normal"]
        if perf.rate_denominator == "timeout_only":
            denom = total_timeout
        else:
            denom = data["count"]
        rate = (total_timeout / denom * 100) if denom else 0.0
        summary.append(PerformanceRow(
            person=person,
            role_label=person.role_label or "—",
            high_timeout=data["high"],
            normal_timeout=data["normal"],
            total_timeout=total_timeout,
            count=data["count"],
            timeout_rate=round(rate, int(perf.rate_precision)),
        ))
    summary.sort(key=lambda r: (-r.total_timeout, r.person.display_name))
    details.sort(key=lambda d: (-d.duration_hours, d.item.id))
    return summary, details, warnings


def summarize_range(items: Sequence[WorkItem], start: Optional[date],
                    end: Optional[date]) -> Dict[str, int]:
    """统计区间内的自然日/工作日/周末/节假日，供页面展示。"""
    warnings: List[str] = []
    if not start or not end or end < start:
        return {"natural_days": 0, "workdays": 0, "weekend_days": 0, "holiday_days": 0}
    days = []
    cursor = start
    while cursor <= end:
        days.append(cursor)
        cursor += timedelta(days=1)
    return {
        "natural_days": len(days),
        "workdays": sum(1 for d in days if d.weekday() < 5),
        "weekend_days": sum(1 for d in days if d.weekday() >= 5),
        "holiday_days": 0,  # 页面已单独展示节假日日历；此处保留键兼容
    }
