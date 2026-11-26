"""禅道（HTTP 代理）数据源适配器。

包装既有 ``ZenTaoProxyClient``，把代理侧的原始数据映射为统一 ``WorkItem``。
代理协议目前只有 ``/query/*`` 聚合端点，没有稳定的「原始工作项」端点；本适配器
采用尽力而为策略：优先调用客户端未来的 ``fetch_items``（若存在），否则尝试
``POST /query/items`` 读取 ``records``。端点不存在时异常被记录到 ``last_error``，
不向 UI 冒泡。
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple

from qa_toolkit.core import tracking_registry as registry

from qa_toolkit.integrations.tracking.adapter_base import normalize_config
from qa_toolkit.integrations.tracking.models import QuerySpec, WorkItem
from qa_toolkit.integrations.zentao_proxy_client import ZenTaoProxyClient

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def normalize_date_text(value: Any) -> Optional[str]:
    """把日期对象/字符串归一化为 ``YYYY-MM-DD``；非法格式直接拒绝。"""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        value = value.date()
    if isinstance(value, date):
        text = value.isoformat()
    else:
        text = str(value).strip()
    if not _DATE_RE.match(text):
        raise ValueError("日期格式必须为 YYYY-MM-DD：" + str(text))
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("日期不是有效日历日期：" + str(text)) from exc
    return text


def _get(row: Any, keys: Tuple[str, ...], default: Any = "") -> Any:
    """从 dict 或对象上按候选字段名取第一个非空值。"""
    if isinstance(row, Mapping):
        for key in keys:
            if key in row and row[key] not in (None, ""):
                return row[key]
    else:
        for key in keys:
            value = getattr(row, key, None)
            if value not in (None, ""):
                return value
    return default


def _as_number(value: Any, default: Any = 0) -> Any:
    if value is None or value == "":
        return default
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, float)):
        return value
    text = str(value).strip()
    try:
        return int(text)
    except ValueError:
        try:
            return float(text)
        except ValueError:
            return value


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in ("1", "true", "yes", "y")


def map_record_to_workitem(row: Dict[str, Any], source: str = "zentao") -> WorkItem:
    """把一条原始记录（dict / 对象 / WorkItem）映射为统一 ``WorkItem``。

    纯函数，不访问网络或数据库，便于契约测试直接调用。日期字段保留原始字符串，
    由规则引擎 ``rules._as_datetime`` 统一解析；状态经注册中心归一化。
    """
    if isinstance(row, WorkItem):
        return row

    data = dict(row) if isinstance(row, Mapping) else {}
    status_text = str(_get(row, ("status", "raw_status", "state"), ""))
    raw_status = str(_get(row, ("raw_status", "status", "state"), "")) or status_text
    normalized = registry.normalize_work_item_state(raw_status or status_text)

    return WorkItem(
        id=str(_get(row, ("id", "bug_id", "issue_id"), "")),
        title=str(_get(row, ("title", "name"), "")),
        source=str(source),
        project_id=str(_get(row, ("project_id", "product", "product_id", "project"), "")),
        project_name=str(_get(row, ("project_name", "product_name"), "")),
        item_type=str(_get(row, ("item_type", "type"), "")),
        status=normalized,
        raw_status=raw_status,
        severity=_as_number(_get(row, ("severity",), 0), 0),
        priority=_as_number(_get(row, ("priority", "pri"), 0), 0),
        reporter=str(_get(row, ("reporter", "openedBy", "opened_by"), "")),
        assignee=str(_get(row, ("assignee", "assignedTo", "assigned_to"), "")),
        resolver=str(_get(row, ("resolver", "resolvedBy", "resolved_by"), "")),
        closer=str(_get(row, ("closer", "closedBy", "closed_by"), "")),
        opened_at=_get(row, ("opened_at", "openedDate", "opened_date"), None),
        resolved_at=_get(row, ("resolved_at", "resolvedDate", "resolved_date"), None),
        closed_at=_get(row, ("closed_at", "closedDate", "closed_date"), None),
        deleted=_as_bool(_get(row, ("deleted", "is_deleted"), False)),
        raw=data,
    )


class ZentaoProxyAdapter:
    """禅道 HTTP 代理适配器，实现 ``TrackingAdapter`` 协议。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.key = "zentao_proxy"
        self.label = "禅道（HTTP 代理）"
        self.last_error = ""
        self.config: Dict[str, Any] = {}
        self.client: Optional[ZenTaoProxyClient] = None
        try:
            cfg = normalize_config("zentao_proxy", config or {})
            # 明文仅用于构造客户端；实例上保留的配置一律脱敏。
            self.config, _ = registry.redact_connection_config("zentao_proxy", cfg)
            self.client = ZenTaoProxyClient(
                base_url=cfg.get("url", ""),
                token=cfg.get("token", ""),
                timeout_seconds=cfg.get("timeout_seconds", 30.0),
            )
        except Exception as exc:
            # 不向 UI 抛错：页面通过 metadata 为空 + last_error 判断连接状态。
            self.last_error = "禅道代理适配器初始化失败：" + str(exc)

    def _options(self, method_name: str, label: str) -> List[Any]:
        try:
            if self.client is None:
                return []
            method = getattr(self.client, method_name)
            return registry.normalize_option_items(method() or [])
        except Exception as exc:
            self.last_error = "获取禅道代理" + label + "失败：" + str(exc)
            return []

    def get_projects(self) -> List[Any]:
        return self._options("get_products", "产品列表")

    def get_roles(self) -> List[Any]:
        return self._options("get_user_roles", "角色列表")

    def get_item_types(self) -> List[Any]:
        return self._options("get_bug_types", "缺陷类型")

    def _request_items(self, spec: QuerySpec) -> List[Any]:
        """尽力而为拉取原始记录：未来客户端可直接提供 fetch_items。"""
        fetch = getattr(self.client, "fetch_items", None)
        if callable(fetch):
            return list(fetch(spec) or [])

        # 所有用户输入仅作为 payload 值传递，不拼接进 URL / 路径。
        payload: Dict[str, Any] = {
            "project_id": str(spec.project_id or ""),
            "start_date": normalize_date_text(spec.start_date) or "",
            "end_date": normalize_date_text(spec.end_date) or "",
            "exclude_types": [str(t) for t in (spec.exclude_types or ())],
            "roles": [str(r) for r in (spec.roles or ())],
            "keywords": str(spec.keywords or ""),
        }
        response = self.client._request("POST", "/query/items", payload) or {}
        return list(response.get("records") or [])

    def fetch_items(self, spec: QuerySpec) -> List[WorkItem]:
        self.last_error = ""
        try:
            if self.client is None:
                raise RuntimeError("代理客户端未初始化")
            max_items = max(0, int(registry.get_tracking_limits().max_items))
            records = self._request_items(spec) or []
            return [map_record_to_workitem(row) for row in records][:max_items]
        except Exception as exc:
            self.last_error = "禅道代理拉取工作项失败：" + str(exc)
            return []

    def close_connection(self) -> None:
        try:
            if self.client is not None:
                self.client.close_connection()
        except Exception as exc:
            self.last_error = "关闭禅道代理连接失败：" + str(exc)
