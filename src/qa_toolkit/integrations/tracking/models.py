"""统一领域模型：把各缺陷管理平台的「工作项 / 人员 / 项目」收敛到一组结构与语义。

设计要点：
- 全部 ``@dataclass(frozen=True)``，不可变，便于跨适配器做同一份契约测试；
- ``WorkItem.raw`` 保留平台原始 payload，方便审计与回查；
- 状态经 ``tracking_registry.normalize_work_item_state`` 归一化到统一枚举；
- ``PerformanceRow.timeout_rate`` 是数值（0-100），展示层再格式化为百分比字符串。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, Mapping, Optional, Tuple

from qa_toolkit.core import tracking_registry as registry

# Option 定义于注册中心；在此重导出，供 adapter_base / 适配器统一从 models 导入。
Option = registry.Option


@dataclass(frozen=True)
class Person:
    id: str
    display_name: str
    account: str = ""
    role_key: str = ""
    role_label: str = ""

    @property
    def match_values(self) -> Tuple[str, ...]:
        """用于把工作项归因到人的候选键（展示名 / 账号 / id）。"""
        return tuple(v for v in (self.display_name, self.account, self.id) if v)


@dataclass(frozen=True)
class Project:
    id: str
    name: str


@dataclass(frozen=True)
class WorkItem:
    """统一工作项：缺陷 / 需求 / 任务在各平台都映射到这一结构。"""
    id: str
    title: str
    source: str                       # zentao / jira / tapd / yunxiao
    project_id: str = ""
    project_name: str = ""
    item_type: str = ""
    status: str = "OPEN"              # 归一化枚举
    raw_status: str = ""
    severity: Any = 0
    priority: Any = 0
    reporter: str = ""
    assignee: str = ""
    resolver: str = ""
    closer: str = ""
    opened_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    closed_at: Optional[datetime] = None
    deleted: bool = False
    raw: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = registry.normalize_work_item_state(self.raw_status or self.status)
        if normalized != self.status:
            object.__setattr__(self, "status", normalized)

    def person_for(self, field_name: str) -> str:
        return str(getattr(self, field_name, "") or "")


@dataclass(frozen=True)
class QuerySpec:
    """统一查询条件：替代页面的裸 config dict 与禅道的哨兵值。"""
    project_id: str = ""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    roles: Tuple[str, ...] = ()
    exclude_types: Tuple[str, ...] = ()
    holiday_country: Optional[str] = None
    sla: Dict[str, int] = field(default_factory=dict)
    keywords: str = ""

    def with_sla(self, **hours: int) -> "QuerySpec":
        merged = dict(self.sla)
        merged.update(hours)
        return QuerySpec(
            project_id=self.project_id, start_date=self.start_date, end_date=self.end_date,
            roles=self.roles, exclude_types=self.exclude_types,
            holiday_country=self.holiday_country, sla=merged, keywords=self.keywords,
        )


@dataclass(frozen=True)
class PerformanceRow:
    """统一绩效汇总行：页面直接读字段，不再按中文列名子串猜列。"""
    person: Person
    role_label: str
    high_timeout: int = 0
    normal_timeout: int = 0
    total_timeout: int = 0
    count: int = 0                     # 率的分母（基数 / 分配数）
    timeout_rate: float = 0.0          # 数值百分比，如 12.34

    def as_record(self) -> Dict[str, Any]:
        return {
            "人员": self.person.display_name,
            "角色": self.role_label,
            "一级超时": self.high_timeout,
            "普通超时": self.normal_timeout,
            "总超时": self.total_timeout,
            "基数": self.count,
            "超时响应率": round(self.timeout_rate, 2),
        }


@dataclass(frozen=True)
class TimeoutDetail:
    """统一超时明细行。"""
    item: WorkItem
    timeout_level: str                 # 一级超时 / 普通超时
    threshold_hours: int
    duration_hours: float
    timeout_kind: str = ""             # 关闭超时 / 验证超时 / 响应超时
    person: str = ""

    def as_record(self) -> Dict[str, Any]:
        return {
            "ID": self.item.id,
            "标题": self.item.title,
            "类型": self.item.item_type,
            "状态": self.item.status,
            "严重程度": self.item.severity,
            "优先级": self.item.priority,
            "超时级别": self.timeout_level,
            "阈值小时": self.threshold_hours,
            "耗时小时": round(self.duration_hours, 2),
            "超时类别": self.timeout_kind,
            "责任人": self.person,
        }
