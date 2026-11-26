"""数据源适配器协议：所有平台适配器都实现这组方法，页面/规则引擎零差别调用。

同时提供 ``LegacyStatsAdapter``过渡协议：包装既有禅道实现时保持中文列名 DataFrame，
让页面在灰度期无需改动即可工作（阶段 1 零回归）。
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Protocol, runtime_checkable

from qa_toolkit.core import tracking_registry as registry
from qa_toolkit.integrations.tracking.models import Option, Project, QuerySpec, WorkItem


@runtime_checkable
class TrackingAdapter(Protocol):
    """统一数据源协议：取元数据 + 拉工作项 + 关闭连接。"""

    key: str
    label: str

    def get_projects(self) -> List[Option]:
        ...

    def get_roles(self) -> List[Option]:
        ...

    def get_item_types(self) -> List[Option]:
        ...

    def fetch_items(self, spec: QuerySpec) -> List[WorkItem]:
        ...

    def close_connection(self) -> None:
        ...


@runtime_checkable
class LegacyStatsAdapter(Protocol):
    """过渡协议：禅道旧实现的同名方法，返回中文列名 DataFrame。"""

    def get_products(self) -> Any:
        ...

    def get_user_roles(self) -> Any:
        ...

    def get_bug_types(self) -> Any:
        ...

    def query_qa_stats(self, product_id: Any, config: Dict[str, Any]) -> Any:
        ...

    def query_dev_stats(self, product_id: Any, config: Dict[str, Any]) -> Any:
        ...

    def query_qa_timeout_bugs_detail(self, person: str, product_id: Any,
                                     start: Any, end: Any, config: Dict[str, Any]) -> Any:
        ...

    def query_timeout_bugs_detail(self, person: str, product_id: Any,
                                  start: Any, end: Any, config: Dict[str, Any]) -> Any:
        ...

    def close_connection(self) -> None:
        ...


def normalize_config(adapter_key: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """按 ConnectionFieldSpec 归一化并校验必填字段；返回副本，不修改入参。"""
    fields = registry.get_connection_fields(adapter_key)
    cleaned: Dict[str, Any] = {}
    for f in fields:
        value = config.get(f.key, f.default)
        if f.kind == "number":
            try:
                value = int(value)
            except (TypeError, ValueError):
                value = int(f.default) if str(f.default).lstrip("-").isdigit() else 0
        elif f.kind == "select":
            value = str(value)
            if f.options and value not in f.options:
                value = str(f.default)
        else:
            value = "" if value is None else str(value)
        if f.required and (value is None or value == "" or value == 0):
            raise ValueError(f"{adapter_key} 缺少必填连接项：{f.label}")
        cleaned[f.key] = value
    return cleaned
