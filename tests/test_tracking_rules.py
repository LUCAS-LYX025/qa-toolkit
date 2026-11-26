"""统一缺陷绩效分析：纯 Python 规则引擎契约测试。

覆盖：归因规则、SLA 阈值语义（允许工时上限，不是逐小时累加）、一级/普通判定、
绩效率分母、节假日/周末开关、统计过滤、告警与纯函数性。
"""
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import tracking_registry as reg  # noqa: E402
from qa_toolkit.integrations.tracking import rules  # noqa: E402
from qa_toolkit.integrations.tracking.models import (  # noqa: E402
    Person, QuerySpec, WorkItem,
)


@pytest.fixture(autouse=True)
def _reset():
    reg.reset_tracking_registry()
    yield
    reg.reset_tracking_registry()


def _item(**overrides):
    """2026-01-05 是周一，便于稳定验证工作日/周末语义。"""
    base = dict(
        id="BUG-1",
        title="登录偶发 500",
        source="jira",
        item_type="缺陷",
        severity=3,
        priority=3,
        reporter="报告人",
        assignee="开发A",
        resolver="开发A",
        closer="测试A",
        opened_at=datetime(2026, 1, 5, 9, 0),
        resolved_at=datetime(2026, 1, 5, 11, 0),
        closed_at=datetime(2026, 1, 5, 12, 0),
    )
    base.update(overrides)
    return WorkItem(**base)


# ---------------------------------------------------------------------------
# 有效工时
# ---------------------------------------------------------------------------

def test_effective_hours_counts_each_hour_once():
    hours, warnings = rules.compute_effective_hours(
        datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 12))
    assert hours == 3.0
    assert warnings == []


def test_effective_hours_can_exclude_weekends():
    # 2026-01-03 是周六，至周日 23:00 全部落在周末
    hours, _ = rules.compute_effective_hours(
        datetime(2026, 1, 3, 9), datetime(2026, 1, 4, 23), count_weekend=False)
    assert hours == 0.0
    included, _ = rules.compute_effective_hours(
        datetime(2026, 1, 3, 9), datetime(2026, 1, 4, 23), count_weekend=True)
    assert included == 38.0


def test_effective_hours_handles_reversed_and_bad_values():
    assert rules.compute_effective_hours(
        datetime(2026, 1, 6, 9), datetime(2026, 1, 5, 9))[0] == 0.0
    assert rules._as_datetime("") is None
    assert rules._as_datetime("2026/02/03 10:11:12") == datetime(2026, 2, 3, 10, 11, 12)


# ---------------------------------------------------------------------------
# SLA 阈值语义与优先级判定
# ---------------------------------------------------------------------------

def test_threshold_is_allowed_hours_not_accumulated():
    """100 小时高优先级项必须超时；历史实现按小时累加阈值导致永不超时。"""
    item = _item(severity=1, resolved_at=datetime(2026, 1, 9, 13))
    summary, details, warnings = rules.compute_performance(
        [item], attribution_key="dev", sla_key="default",
        query=QuerySpec(sla={"high_normal": 24, "normal": 72}))
    assert not warnings
    assert len(details) == 1
    assert details[0].timeout_level == "一级超时"
    assert details[0].threshold_hours == 24
    assert details[0].duration_hours >= 100
    assert summary[0].high_timeout == 1
    assert summary[0].timeout_rate == 100.0


def test_short_normal_item_does_not_timeout():
    item = _item()
    summary, details, _ = rules.compute_performance(
        [item], attribution_key="dev",
        query=QuerySpec(sla={"normal": 72}))
    assert details == []
    assert summary[0].total_timeout == 0
    assert summary[0].timeout_rate == 0.0


def test_high_priority_values_are_registry_driven():
    reg.register_sla_rule(reg.SlaRuleSpec(
        "sev3", "Severity 3 也算一级", high_priority_values=(3,)), replace=True)
    item = _item(severity=3)
    _, details, _ = rules.compute_performance(
        [item], attribution_key="dev", sla_key="sev3",
        query=QuerySpec(sla={"normal": 1}))
    assert details and details[0].timeout_level == "一级超时"


def test_weekend_threshold_selected_by_end_time():
    item = _item(severity=1, opened_at=datetime(2026, 1, 9, 9),
                 resolved_at=datetime(2026, 1, 10, 11))  # 周六结束
    _, details, _ = rules.compute_performance(
        [item], attribution_key="dev",
        query=QuerySpec(sla={"high_normal": 1, "high_weekend": 2}))
    assert details and details[0].threshold_hours == 2


# ---------------------------------------------------------------------------
# 归因规则
# ---------------------------------------------------------------------------

def test_attribution_rule_controls_person_and_sla_window():
    """qa 用 resolved->closed（2h），dev 用 opened->resolved；两者结论必须不同。"""
    item = _item(resolver="开发A", closer="测试A",
                 resolved_at=datetime(2026, 1, 5, 11),
                 closed_at=datetime(2026, 1, 5, 13))
    qa_rows, qa_details, _ = rules.compute_performance(
        [item], attribution_key="qa", query=QuerySpec(sla={"normal": 1}))
    dev_rows, dev_details, _ = rules.compute_performance(
        [item], attribution_key="dev", query=QuerySpec(sla={"normal": 1}))
    assert qa_rows[0].person.display_name == "测试A"
    assert dev_rows[0].person.display_name == "开发A"
    assert len(qa_details) == 1 and qa_details[0].timeout_kind == "关闭超时"
    assert len(dev_details) == 1 and dev_details[0].timeout_kind == "响应超时"


def test_custom_attribution_falls_back_to_assignee():
    reg.register_attribution(reg.AttributionRuleSpec(
        "owner", "按处理人", ("missing_field", "assignee"), "opened_at", "closed_at"))
    rows, _, _ = rules.compute_performance([_item()], attribution_key="owner")
    assert rows[0].person.display_name == "开发A"


def test_people_index_matches_account_and_role_label():
    person = Person(id="p1", display_name="张三", account="zhangsan", role_label="开发工程师")
    rows, _, _ = rules.compute_performance(
        [_item(assignee="zhangsan", resolver="zhangsan")],
        attribution_key="dev", people=[person])
    assert rows[0].person.display_name == "张三"
    assert rows[0].role_label == "开发工程师"


# ---------------------------------------------------------------------------
# 率计算 / 过滤 / 告警
# ---------------------------------------------------------------------------

def test_rate_denominator_is_registry_driven():
    items = [
        _item(id="A", severity=1),
        _item(id="B", severity=3, resolved_at=datetime(2026, 1, 9, 13)),
    ]
    spec = QuerySpec(sla={"high_normal": 1, "normal": 200})
    rate_rows, _, _ = rules.compute_performance(items, attribution_key="dev", query=spec)
    share_rows, _, _ = rules.compute_performance(
        items, attribution_key="dev", performance_key="timeout_share", query=spec)
    assert rate_rows[0].count == 2 and rate_rows[0].timeout_rate == 50.0
    assert share_rows[0].timeout_rate == 100.0


def test_deleted_type_and_date_filters_apply():
    items = [
        _item(id="KEEP"),
        _item(id="DELETED", deleted=True),
        _item(id="TYPE", item_type="需求"),
        _item(id="OLD", opened_at=datetime(2025, 12, 1, 9)),
    ]
    rows, _, _ = rules.compute_performance(
        items, attribution_key="dev",
        query=QuerySpec(exclude_types=("需求",), start_date=date(2026, 1, 1),
                        end_date=date(2026, 1, 31)))
    assert rows[0].count == 1


def test_item_without_start_time_counts_but_warns_nothing():
    rows, details, warnings = rules.compute_performance(
        [_item(opened_at=None)], attribution_key="dev")
    assert rows[0].count == 1 and not details and not warnings


def test_reversed_time_window_emits_warning():
    _, _, warnings = rules.compute_performance(
        [_item(resolved_at=datetime(2026, 1, 4, 9))], attribution_key="dev")
    assert any("早于开始时间" in w for w in warnings)


def test_unknown_rule_keys_raise_value_error():
    with pytest.raises(ValueError, match="未知归因规则"):
        rules.compute_performance([], attribution_key="nope")
    with pytest.raises(ValueError, match="未知 SLA 规则"):
        rules.compute_performance([], sla_key="nope")
    with pytest.raises(ValueError, match="未知绩效规则"):
        rules.compute_performance([], performance_key="nope")


def test_compute_performance_is_pure():
    item = _item()
    before = (item.id, item.status, item.resolved_at)
    spec = QuerySpec(sla={"normal": 1})
    rows1, details1, _ = rules.compute_performance([item], attribution_key="dev", query=spec)
    rows2, details2, _ = rules.compute_performance([item], attribution_key="dev", query=spec)
    assert rows1 == rows2 and details1 == details2
    assert (item.id, item.status, item.resolved_at) == before
    assert rows1[0].as_record()["人员"] == "开发A"
    assert details1[0].as_record()["超时级别"] in ("一级超时", "普通超时")


def test_roles_filter_matches_person_account_and_display_name():
    items = [_item(id="A", assignee="开发A", resolver="开发A"),
             _item(id="B", assignee="开发B", resolver="开发B")]
    person = Person(id="u2", display_name="开发B", account="dev_b", role_label="开发工程师")
    rows, _, _ = rules.compute_performance(
        items, attribution_key="dev", people=[person],
        query=QuerySpec(roles=("dev_b",)))
    assert len(rows) == 1
    assert rows[0].person.display_name == "开发B"
    assert rows[0].role_label == "开发工程师"


def test_custom_sla_hours_key_takes_precedence_over_legacy_keys():
    reg.register_sla_rule(reg.SlaRuleSpec(
        "custom_key", "自定义键", normal_hours_key="custom_normal"), replace=True)
    item = _item(resolved_at=datetime(2026, 1, 5, 13))  # 4h
    _, details, _ = rules.compute_performance(
        [item], attribution_key="dev", sla_key="custom_key",
        query=QuerySpec(sla={"custom_normal": 1, "normal_normal": 72}))
    assert details and details[0].threshold_hours == 1


def test_summary_has_no_misleading_submitted_column():
    rows, _, _ = rules.compute_performance([_item()], attribution_key="qa")
    assert "提交数" not in rows[0].as_record()
    assert not hasattr(rows[0], "submitted")


def test_summarize_range_counts_calendar_days():
    result = rules.summarize_range([], date(2026, 1, 5), date(2026, 1, 11))
    assert result == {"natural_days": 7, "workdays": 5, "weekend_days": 2, "holiday_days": 0}
    assert rules.summarize_range([], None, None)["natural_days"] == 0
