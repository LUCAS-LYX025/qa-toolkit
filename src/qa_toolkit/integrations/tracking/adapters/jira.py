"""JIRA 数据源适配器（HTTP）。

设计要点：
- 业务类不依赖 requests / streamlit；网络访问全部经 ``HttpTransport``，
  测试可注入假 transport 做无网络契约测试；
- 默认 transport 延迟导入 requests，鉴权、超时、SSL 校验集中处理；
- 所有查询条件只写入 params（JQL 亦为参数值），用户输入绝不拼进 URL 路径；
- 原始记录统一交给 ``map_record_to_workitem(row, source="jira")`` 映射；
- 初始化失败与请求异常只记录 ``last_error``，不向页面抛错。
"""
from __future__ import annotations

import base64
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
_SEARCH_PATH = "/rest/api/3/search"
_PROJECTS_PATH = "/rest/api/3/project"
_TYPES_PATH = "/rest/api/3/issue/createmeta/issuetypes"

_ROW_KEYS = (
    "issues", "items", "records", "bugs", "stories", "workitems",
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

    def __init__(self, base_url: str, *, token: str = "", username: str = "",
                 timeout: float = 30.0, verify: bool = True,
                 session: Any = None) -> None:
        self.base_url = str(base_url or "").rstrip("/")
        self.timeout = timeout
        self.verify = verify
        self._session = session
        self._headers: Dict[str, str] = {
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        if token:
            if username:
                raw = (str(username) + ":" + str(token)).encode("utf-8")
                auth = "Basic " + base64.b64encode(raw).decode("ascii")
            else:
                auth = "Bearer " + str(token)
            self._headers["Authorization"] = auth

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


def _jql_value(value: Any) -> str:
    """把值安全地变成 JQL 字符串字面量，转义引号/反斜杠并剔除控制字符。"""
    text = str(value).replace("\\", "\\\\").replace('"', '\\"')
    text = "".join(ch for ch in text if ch >= " " or ch == "\t")
    return '"' + text + '"'


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


def _nested_name(value: Any) -> str:
    if isinstance(value, dict):
        return str(value.get("name") or value.get("displayName") or value.get("value") or "")
    return str(value or "")


def _flatten_issue(row: Any) -> Any:
    """把 JIRA ``fields`` 嵌套结构压平，兼容测试用的扁平 dict。"""
    if not isinstance(row, dict):
        return row
    out = dict(row)
    fields = out.get("fields")
    if isinstance(fields, dict):
        out.setdefault("title", fields.get("summary", ""))
        out.setdefault("item_type", _nested_name(fields.get("issuetype")))
        out.setdefault("raw_status", _nested_name(fields.get("status")))
        out.setdefault("reporter", _nested_name(fields.get("reporter") or fields.get("creator")))
        out.setdefault("assignee", _nested_name(fields.get("assignee")))
        out.setdefault("resolver", _nested_name(fields.get("resolver")))
        out.setdefault("closer", _nested_name(fields.get("closer")))
        out.setdefault("severity", fields.get("severity", 0))
        out.setdefault("priority", fields.get("priority", 0))
        out.setdefault("opened_at", fields.get("created") or fields.get("createdAt"))
        out.setdefault("resolved_at", fields.get("resolutiondate") or fields.get("resolvedAt"))
        out.setdefault("closed_at", fields.get("closed") or fields.get("closedAt")
                       or fields.get("resolutiondate"))
        for key, value in fields.items():
            out.setdefault(key, value)
    if isinstance(out.get("status"), dict):
        out["status"] = _nested_name(out["status"])
    if isinstance(out.get("priority"), dict):
        out["priority"] = _nested_name(out["priority"]) or 0
    if isinstance(out.get("severity"), dict):
        out["severity"] = _nested_name(out["severity"]) or 0
    return out


# ---------------------------------------------------------------------------
# 适配器
# ---------------------------------------------------------------------------

class JiraAdapter:
    """JIRA REST API 适配器，实现 ``TrackingAdapter`` 协议。"""

    def __init__(self, config: Dict[str, Any], transport: Any = None,
                 session: Any = None) -> None:
        self.key = "jira"
        self.label = "JIRA"
        self.last_error = ""
        self.config: Dict[str, Any] = {}
        self.transport: Any = None
        self.base_url = ""
        self.project_key = ""
        self._project_keys: Dict[str, str] = {}
        try:
            cfg = normalize_config("jira", config or {})
        except Exception as exc:
            # 必填校验失败：不向外抛，页面靠 metadata 为空 + last_error 判断。
            self.last_error = "JIRA 适配器初始化失败：" + str(exc)
            return

        redacted, _ = registry.redact_connection_config("jira", cfg)
        self.config = redacted
        self.base_url = str(cfg.get("base_url") or "").rstrip("/")
        self.project_key = str(cfg.get("project_key") or "")

        if transport is None:
            transport = RequestsHttpTransport(
                self.base_url, token=str(cfg.get("token") or ""),
                username=str(cfg.get("username") or ""),
                timeout=float(cfg.get("timeout_seconds") or 30.0),
                verify=str(cfg.get("verify_ssl", "true")).lower() != "false",
                session=session,
            )
        self.transport = transport

    def _options(self, path: str, label: str, *, value_key: str = "id",
                 label_key: str = "name") -> List[Option]:
        if self.transport is None:
            return []
        try:
            payload = self.transport.request("GET", path)
            return registry.normalize_option_items(
                _as_list(payload), value_key=value_key, label_key=label_key)
        except Exception as exc:
            self.last_error = "获取 JIRA " + label + "失败：" + str(exc)
            return []

    def get_projects(self) -> List[Option]:
        if self.transport is None:
            return []
        try:
            payload = self.transport.request("GET", _PROJECTS_PATH)
            rows = _as_list(payload)
            for row in rows:
                if isinstance(row, dict):
                    value = str(row.get("id") or row.get("key") or "")
                    if value:
                        self._project_keys[value] = str(row.get("key") or value)
            return registry.normalize_option_items(rows)
        except Exception as exc:
            self.last_error = "获取 JIRA 项目列表失败：" + str(exc)
            return []

    def _discover_project_key(self) -> str:
        """未配置 project_key 时，从项目列表静默探测一个可用 key。"""
        if self.transport is None:
            return ""
        try:
            rows = _as_list(self.transport.request("GET", _PROJECTS_PATH))
            for row in rows:
                if isinstance(row, dict) and (row.get("key") or row.get("id")):
                    return str(row.get("key") or row.get("id"))
        except Exception:
            pass
        return ""

    def get_roles(self, project_key: Optional[str] = None) -> List[Option]:
        """项目角色：路径里的 key 先取入参/配置/已缓存项目，均经 quote 转义。"""
        if self.transport is None:
            return []
        key = str(project_key or self.project_key or "").strip()
        if not key and self._project_keys:
            key = next(iter(self._project_keys.values()))
        if not key:
            key = self._discover_project_key()
        if not key:
            key = "key"
        path = "/rest/api/3/project/{0}/roles".format(quote(key, safe=""))
        try:
            payload = self.transport.request("GET", path)
            if isinstance(payload, dict):
                options: List[Option] = []
                for name, info in payload.items():
                    label = _nested_name(info) if isinstance(info, dict) else str(name)
                    options.append(Option(str(name), label or str(name)))
                return options
            return registry.normalize_option_items(
                _as_list(payload), value_key="name", label_key="name")
        except Exception as exc:
            self.last_error = "获取 JIRA 角色列表失败：" + str(exc)
            return []

    def get_item_types(self) -> List[Option]:
        return self._options(_TYPES_PATH, "工作项类型")

    def _build_jql(self, spec: QuerySpec) -> str:
        parts: List[str] = []
        project = str(spec.project_id or "").strip()
        if project:
            parts.append("project = " + _jql_value(project))
        start = _date_text(spec.start_date)
        end = _date_text(spec.end_date)
        if start and end and start > end:
            raise ValueError("start_date 不能晚于 end_date")
        if start:
            parts.append("created >= " + _jql_value(start))
        if end:
            parts.append("created <= " + _jql_value(end))
        excludes = [str(t).strip() for t in (spec.exclude_types or ()) if str(t).strip()]
        if excludes:
            parts.append("issuetype NOT IN (" + ", ".join(_jql_value(t) for t in excludes) + ")")
        keywords = str(spec.keywords or "").strip()
        if keywords:
            parts.append("text ~ " + _jql_value(keywords))
        return " AND ".join(parts)

    def fetch_items(self, spec: QuerySpec) -> List[WorkItem]:
        self.last_error = ""
        if self.transport is None:
            self.last_error = "JIRA 适配器未初始化"
            return []
        try:
            max_items = max(0, int(registry.get_tracking_limits().max_items))
            if max_items == 0:
                return []
            page_size = min(_PAGE_SIZE, max_items)
            jql = self._build_jql(spec)
            results: List[WorkItem] = []
            start = 0
            paths = (_SEARCH_PATH, "/rest/api/3/search/jql")
            active_path = paths[0]
            while len(results) < max_items:
                params: Dict[str, Any] = {
                    "jql": jql, "startAt": start, "maxResults": page_size,
                    "fields": "*all",
                }
                rows: List[Any] = []
                for path in paths if start == 0 else (active_path,):
                    payload = self.transport.request("GET", path, params=params)
                    rows = [_flatten_issue(row) for row in _as_list(payload)]
                    if rows:
                        active_path = path
                        break
                if not rows:
                    break
                for row in rows:
                    if len(results) >= max_items:
                        break
                    results.append(map_record_to_workitem(row, source="jira"))
                if len(rows) < page_size:
                    break
                start += len(rows)
            return results
        except Exception as exc:
            self.last_error = "JIRA 拉取工作项失败：" + str(exc)
            return []

    def close_connection(self) -> None:
        try:
            close = getattr(self.transport, "close", None)
            if callable(close):
                close()
        except Exception as exc:
            self.last_error = "关闭 JIRA 连接失败：" + str(exc)
