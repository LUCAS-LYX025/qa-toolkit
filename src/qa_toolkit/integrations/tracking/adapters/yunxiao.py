"""阿里云效数据源适配器（HTTP）。

设计要点：
- 业务类不依赖 requests / streamlit；网络访问全部经 ``HttpTransport``，
  测试可注入假 transport 做无网络契约测试；
- 默认 transport 延迟导入 requests，Bearer 鉴权、超时、SSL 校验集中处理；
- organization_id 属于资源标识，只在构造路径时经 quote 转义；查询条件全部放 params；
- 原始记录统一交给 ``map_record_to_workitem(row, source="yunxiao")`` 映射；
- 初始化失败与请求异常只记录 ``last_error``，不向页面抛错。
"""
from __future__ import annotations

import re
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Protocol
from urllib.parse import quote

from qa_toolkit.core import tracking_registry as registry

from qa_toolkit.integrations.tracking.adapter_base import normalize_config
from qa_toolkit.integrations.tracking.adapters.zentao_proxy import map_record_to_workitem
from qa_toolkit.integrations.tracking.models import Option, QuerySpec, WorkItem

_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_PAGE_SIZE = 100

_ROW_KEYS = (
    "workitems", "items", "records", "bugs", "stories",
    "data", "result", "results", "list", "content", "rows", "values",
)


# ---------------------------------------------------------------------------
# transport：协议 + 基于 requests.Session 的默认实现（延迟导入）
# ---------------------------------------------------------------------------

class HttpTransport(Protocol):
    """最小 HTTP 契约：返回已解析的 JSON。"""

    def request(self, method: str, url: str, *, params: Optional[Dict[str, Any]] = None,
                json: Optional[Any] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        ...

    def close(self) -> None:
        ...


class RequestsHttpTransport:
    """默认 HTTP 实现：requests.Session 延迟导入，可注入现成 session。"""

    def __init__(self, base_url: str, *, access_token: str = "", timeout: float = 30.0,
                 verify: bool = True, session: Any = None) -> None:
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout = timeout
        self.verify = verify
        self._session = session
        self._headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if access_token:
            self._headers["Authorization"] = "Bearer " + str(access_token)

    def _get_session(self) -> Any:
        if self._session is None:
            import requests  # 延迟导入：业务模块与无网络测试都不需要它
            self._session = requests.Session()
        return self._session

    def request(self, method: str, url: str, *, params: Optional[Dict[str, Any]] = None,
                json: Optional[Any] = None, headers: Optional[Dict[str, str]] = None) -> Any:
        full_url = self.base_url + "/" + url.lstrip("/") if url.startswith("/") else url
        merged = dict(self._headers)
        merged.update(headers or {})
        response = self._get_session().request(
            method, full_url, params=params, json=json, headers=merged,
            timeout=self.timeout, verify=self.verify,
        )
        try:
            response.raise_for_status()
        except AttributeError:
            pass
        if not getattr(response, "content", None):
            return {}
        return response.json()

    def close(self) -> None:
        if self._session is not None:
            close = getattr(self._session, "close", None)
            if callable(close):
                close()
            self._session = None


DefaultHttpTransport = RequestsHttpTransport


# ---------------------------------------------------------------------------
# 纯函数工具
# ---------------------------------------------------------------------------

def _date_text(value: Any) -> str:
    """校验并归一化日期；格式必须是 YYYY-MM-DD 且为有效日历日期。"""
    if value is None or value == "":
        return ""
    if isinstance(value, datetime):
        value = value.date()
    text = value.isoformat() if isinstance(value, date) else str(value).strip()
    if not _DATE_RE.match(text):
        raise ValueError("日期格式必须为 YYYY-MM-DD：" + text)
    try:
        date.fromisoformat(text)
    except ValueError as exc:
        raise ValueError("日期不是有效日历日期：" + text) from exc
    return text


def _as_list(payload: Any) -> List[Any]:
    if isinstance(payload, list):
        return list(payload)
    if isinstance(payload, dict):
        for key in _ROW_KEYS:
            value = payload.get(key)
            if isinstance(value, list):
                return value
            if isinstance(value, dict):
                nested = _as_list(value)
                if nested:
                    return nested
    return []


def _unwrap_row(row: Any) -> Any:
    """拆掉单个 workitem / bug 包装，便于统一字段映射。"""
    if not isinstance(row, dict):
        return row
    for key in ("workitem", "WorkItem", "bug", "Bug", "story", "Story"):
        inner = row.get(key)
        if isinstance(inner, dict):
            out = dict(inner)
            for name, value in row.items():
                out.setdefault(name, value)
            return out
    return row


# ---------------------------------------------------------------------------
# 适配器
# ---------------------------------------------------------------------------

class YunxiaoAdapter:
    """阿里云效 OpenAPI 适配器，实现 ``TrackingAdapter`` 协议。"""

    def __init__(self, config: Dict[str, Any], transport: Any = None,
                 session: Any = None) -> None:
        self.key = "yunxiao"
        self.label = "阿里云效"
        self.last_error = ""
        self.config: Dict[str, Any] = {}
        self.transport: Any = None
        self.base_url = ""
        self.organization_id = ""
        try:
            cfg = normalize_config("yunxiao", config or {})
        except Exception as exc:
            self.last_error = "云效适配器初始化失败：" + str(exc)
            return

        redacted, _ = registry.redact_connection_config("yunxiao", cfg)
        self.config = redacted
        self.base_url = str(cfg.get("base_url") or "").rstrip("/")
        self.organization_id = str(cfg.get("organization_id") or "")

        if transport is None:
            limits = registry.get_tracking_limits()
            transport = RequestsHttpTransport(
                self.base_url, access_token=str(cfg.get("access_token") or ""),
                timeout=float(cfg.get("timeout_seconds") or limits.default_timeout_seconds),
                verify=str(cfg.get("verify_ssl", "true")).lower() != "false",
                session=session,
            )
        self.transport = transport

    def _org_path(self, suffix: str) -> str:
        """资源路径只由配置派生的 organization_id 构成，经 quote 转义。"""
        org = quote(str(self.organization_id or ""), safe="")
        return "/organization/{0}/{1}".format(org, suffix)

    def _options(self, suffix: str, label: str, *, value_key: str = "id",
                 label_key: str = "name") -> List[Option]:
        if self.transport is None:
            return []
        try:
            payload = self.transport.request("GET", self._org_path(suffix))
            return registry.normalize_option_items(
                _as_list(payload), value_key=value_key, label_key=label_key)
        except Exception as exc:
            self.last_error = "获取云效" + label + "失败：" + str(exc)
            return []

    def get_projects(self) -> List[Option]:
        return self._options("projects", "项目列表")

    def get_roles(self) -> List[Option]:
        """组织成员映射为角色选项：value 取 userId，label 取姓名。"""
        if self.transport is None:
            return []
        try:
            payload = self.transport.request("GET", self._org_path("members"))
            options: List[Option] = []
            for row in _as_list(payload):
                if isinstance(row, dict):
                    value = row.get("userId") or row.get("id") or row.get("user_id") or ""
                    label = row.get("name") or row.get("displayName") or value
                    options.append(Option(str(value), str(label)))
            return options
        except Exception as exc:
            self.last_error = "获取云效角色列表失败：" + str(exc)
            return []

    def get_item_types(self) -> List[Option]:
        return self._options("workitemTypes", "工作项类型")

    def _build_params(self, spec: QuerySpec, page: int, page_size: int) -> Dict[str, Any]:
        params: Dict[str, Any] = {
            "organizationId": self.organization_id,
            "page": page,
            "limit": page_size,
        }
        project_id = str(spec.project_id or "").strip()
        if project_id:
            params["project_id"] = project_id
        start = _date_text(spec.start_date)
        end = _date_text(spec.end_date)
        if start and end and start > end:
            raise ValueError("start_date 不能晚于 end_date")
        if start:
            params["start_date"] = start
        if end:
            params["end_date"] = end
        excludes = [str(t).strip() for t in (spec.exclude_types or ()) if str(t).strip()]
        if excludes:
            params["exclude_types"] = excludes
        keywords = str(spec.keywords or "").strip()
        if keywords:
            params["keywords"] = keywords
        return params

    def fetch_items(self, spec: QuerySpec) -> List[WorkItem]:
        self.last_error = ""
        if self.transport is None:
            self.last_error = "云效适配器未初始化"
            return []
        try:
            max_items = max(0, int(registry.get_tracking_limits().max_items))
            if max_items == 0:
                return []
            page_size = min(_PAGE_SIZE, max_items)
            paths = (self._org_path("workitems"), self._org_path("workitems/search"))
            results: List[WorkItem] = []
            page = 1
            active_path = paths[0]
            while len(results) < max_items:
                params = self._build_params(spec, page, page_size)
                rows: List[Any] = []
                for path in paths if page == 1 else (active_path,):
                    payload = self.transport.request("GET", path, params=params)
                    rows = [_unwrap_row(row) for row in _as_list(payload)]
                    if rows:
                        active_path = path
                        break
                if not rows:
                    break
                for row in rows:
                    if len(results) >= max_items:
                        break
                    results.append(map_record_to_workitem(row, source="yunxiao"))
                if len(rows) < page_size:
                    break
                page += 1
            return results
        except Exception as exc:
            self.last_error = "云效拉取工作项失败：" + str(exc)
            return []

    def close_connection(self) -> None:
        try:
            close = getattr(self.transport, "close", None)
            if callable(close):
                close()
        except Exception as exc:
            self.last_error = "关闭云效连接失败：" + str(exc)
