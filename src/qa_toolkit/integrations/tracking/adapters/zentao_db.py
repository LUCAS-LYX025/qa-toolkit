"""禅道（直连数据库）数据源适配器。

复用既有 ``ZenTaoPerformanceExporter`` 的连接与元数据能力；工作项拉取使用本模块
内的轻量参数化 SQL（既有 exporter 只有聚合 SQL）。所有用户输入仅以占位符参数
传入，绝不拼接进 SQL 文本；异常统一记录到 ``last_error``，不向 UI 抛出。
"""
from __future__ import annotations

import inspect
import re
from typing import Any, Dict, List, Optional, Tuple

from qa_toolkit.core import tracking_registry as registry

from qa_toolkit.integrations.tracking.adapter_base import normalize_config
from qa_toolkit.integrations.tracking.adapters.zentao_proxy import (
    map_record_to_workitem, normalize_date_text,
)
from qa_toolkit.integrations.tracking.models import QuerySpec, WorkItem
from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter

# 工作项基础查询：固定文本，不含任何来自调用方的片段。
_RAW_ITEMS_SQL = (
    "SELECT b.id, b.title, b.product AS project_id, p.name AS project_name, "
    "b.type AS item_type, b.status AS raw_status, b.severity, b.pri AS priority, "
    "b.openedBy AS reporter, b.assignedTo AS assignee, "
    "b.resolvedBy AS resolver, b.closedBy AS closer, "
    "b.openedDate, b.resolvedDate, b.closedDate, b.deleted "
    "FROM zt_bug b LEFT JOIN zt_product p ON b.product = p.id "
    "WHERE b.deleted = '0'"
)


class ZentaoDbAdapter:
    """禅道 MySQL 直连适配器，实现 ``TrackingAdapter`` 协议。"""

    def __init__(self, config: Dict[str, Any]) -> None:
        self.key = "zentao_db"
        self.label = "禅道（直连数据库）"
        self.last_error = ""
        self.config: Dict[str, Any] = {}
        self.exporter: Optional[ZenTaoPerformanceExporter] = None
        try:
            cfg = normalize_config("zentao_db", config or {})
            # 明文仅用于建立数据库连接；实例上保留的配置一律脱敏。
            self.config, _ = registry.redact_connection_config("zentao_db", cfg)
            exporter_config = {
                "host": cfg.get("host", ""),
                "port": cfg.get("port", 3306),
                "database": cfg.get("database", ""),
                "db": cfg.get("database", ""),
                "name": cfg.get("database", ""),
                "user": cfg.get("user", ""),
                "password": cfg.get("password", ""),
            }
            self.exporter = ZenTaoPerformanceExporter(exporter_config)
        except Exception as exc:
            # 页面通过 metadata 为空 + last_error 判断连接状态，构造函数不抛错。
            self.last_error = "禅道直连数据库适配器初始化失败：" + str(exc)

    def _options(self, method_name: str, label: str) -> List[Any]:
        try:
            if self.exporter is None:
                return []
            method = getattr(self.exporter, method_name)
            return registry.normalize_option_items(method() or [])
        except Exception as exc:
            self.last_error = "获取禅道" + label + "失败：" + str(exc)
            return []

    def get_projects(self) -> List[Any]:
        return self._options("get_products", "产品列表")

    def get_roles(self) -> List[Any]:
        return self._options("get_user_roles", "角色列表")

    def get_item_types(self) -> List[Any]:
        return self._options("get_bug_types", "缺陷类型")

    @staticmethod
    def _fetchall(db: Any, sql: str, params: Tuple[Any, ...]) -> List[Dict[str, Any]]:
        """执行参数化查询并取回 dict 行。

        兼容两种 MysqlDB 形态：较新的 ``fetchall_to_dict(sql, params)`` 包装，
        以及仓库当前真实实现 ``cur.execute(sql, params)`` + ``fetchall_to_dict()``。
        """
        fetcher = getattr(db, "fetchall_to_dict", None)
        if not callable(fetcher):
            raise RuntimeError("数据库连接未提供 fetchall_to_dict")
        try:
            inspect.signature(fetcher).bind(sql, params)
            supports_params = True
        except (TypeError, ValueError):
            supports_params = False

        if supports_params:
            return list(fetcher(sql, params) or [])

        cursor = getattr(db, "cur", None)
        if cursor is None or not callable(getattr(cursor, "execute", None)):
            raise RuntimeError("数据库连接不支持参数化查询")
        cursor.execute(sql, params)
        return list(fetcher() or [])

    def _fetch_raw_items(self, spec: QuerySpec) -> List[Dict[str, Any]]:
        """按 QuerySpec 拉取统一模型所需的原始字段（全部条件参数化）。"""
        sql = _RAW_ITEMS_SQL
        params: List[Any] = []

        # product id 必须是数字；非法输入直接拒绝，不进入 SQL。
        project_id = str(spec.project_id or "").strip()
        if project_id:
            if not re.fullmatch(r"\d+", project_id):
                raise ValueError("project_id 必须是数字")
            sql += " AND b.product = %s"
            params.append(int(project_id))

        start = normalize_date_text(spec.start_date)
        end = normalize_date_text(spec.end_date)
        if start and end and start > end:
            raise ValueError("start_date 不能晚于 end_date")
        if start and end:
            sql += " AND b.openedDate BETWEEN %s AND %s"
            params.extend((start, end))
        elif start:
            sql += " AND b.openedDate >= %s"
            params.append(start)
        elif end:
            sql += " AND b.openedDate <= %s"
            params.append(end)

        # IN 列表只拼接占位符数量；类型值本身始终作为参数传入。
        exclude_types = [str(t).strip() for t in (spec.exclude_types or ()) if str(t).strip()]
        if exclude_types:
            placeholders = ", ".join(["%s"] * len(exclude_types))
            sql += " AND b.type NOT IN (" + placeholders + ")"
            params.extend(exclude_types)

        db = getattr(self.exporter, "mysql_db", None)
        if db is None:
            raise RuntimeError("禅道数据库未连接")
        return self._fetchall(db, sql, tuple(params))

    def fetch_items(self, spec: QuerySpec) -> List[WorkItem]:
        self.last_error = ""
        try:
            if self.exporter is None:
                raise RuntimeError("禅道直连数据库适配器未初始化成功")
            rows = self._fetch_raw_items(spec)
            max_items = max(0, int(registry.get_tracking_limits().max_items))
            return [map_record_to_workitem(row, source="zentao") for row in rows][:max_items]
        except Exception as exc:
            self.last_error = "禅道直连数据库拉取工作项失败：" + str(exc)
            return []

    def close_connection(self) -> None:
        try:
            if self.exporter is not None:
                self.exporter.close_connection()
        except Exception as exc:
            self.last_error = "关闭禅道数据库连接失败：" + str(exc)
