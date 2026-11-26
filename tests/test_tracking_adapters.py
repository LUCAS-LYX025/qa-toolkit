"""统一缺陷绩效分析：5 个数据源适配器的同一份契约测试。

HTTP 适配器用可注入 FakeTransport，禅道适配器用 FakeExporter / FakeClient，
全部无网络、无数据库依赖。
"""
import sys
from datetime import date, datetime
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import tracking_registry as reg  # noqa: E402
from qa_toolkit.integrations.tracking.adapter_base import TrackingAdapter  # noqa: E402
from qa_toolkit.integrations.tracking.adapters import (  # noqa: E402
    jira, tapd, yunxiao, zentao_db, zentao_proxy,
)
from qa_toolkit.integrations.tracking.models import Option, QuerySpec, WorkItem  # noqa: E402


@pytest.fixture(autouse=True)
def _reset():
    reg.reset_tracking_registry()
    yield
    reg.reset_tracking_registry()


def _row(prefix):
    return {
        "id": prefix + "-1",
        "title": "登录偶发 500",
        "raw_status": "Fixed",
        "severity": 1,
        "priority": 2,
        "reporter": "报告人",
        "assignee": "开发A",
        "resolver": "开发A",
        "closer": "测试A",
        "opened_at": "2026-01-05 09:00:00",
        "resolved_at": "2026-01-06 09:00:00",
        "closed_at": "2026-01-07 09:00:00",
    }


class FakeTransport:
    def __init__(self, routes=None, fail=False):
        self.routes = routes or {}
        self.fail = fail
        self.calls = []
        self.closed = False

    def request(self, method, url, *, params=None, json=None, headers=None):
        self.calls.append({"method": method, "url": url, "params": dict(params or {}),
                           "headers": dict(headers or {})})
        if self.fail:
            raise RuntimeError("模拟网络故障")
        return self.routes.get(url, {})

    def close(self):
        self.closed = True


# ---------------------------------------------------------------------------
# HTTP 适配器（JIRA / TAPD / 云效）：共享契约
# ---------------------------------------------------------------------------

_HTTP_CASES = [
    (
        "jira", jira.JiraAdapter,
        {"base_url": "https://jira.example.com", "token": "SECRET", "project_key": "TEST"},
        {
            "/rest/api/3/project": [{"id": "100", "key": "TEST", "name": "测试项目"}],
            "/rest/api/3/project/TEST/roles": {"Developers": {"name": "开发组"}},
            "/rest/api/3/issue/createmeta/issuetypes": [{"id": "1", "name": "缺陷"}],
            "/rest/api/3/search": {"issues": [_row("JIRA")]},
        },
    ),
    (
        "tapd", tapd.TapdAdapter,
        {"base_url": "https://api.tapd.cn", "workspace_id": "WS1", "api_password": "SECRET"},
        {
            "/workspaces/projects": [{"id": "1", "name": "TAPD项目"}],
            "/workspaces/users": [{"id": "u1", "name": "张三"}],
            "/workspaces/workitem_types": [{"id": "bug", "name": "缺陷"}],
            "/workspaces/items": {"data": [{"Bug": _row("TAPD")}]},
        },
    ),
    (
        "yunxiao", yunxiao.YunxiaoAdapter,
        {"base_url": "https://openapi.example.com", "organization_id": "ORG", "access_token": "SECRET"},
        {
            "/organization/ORG/projects": [{"id": "p1", "name": "云效项目"}],
            "/organization/ORG/members": [{"userId": "u1", "name": "李四"}],
            "/organization/ORG/workitemTypes": [{"id": "bug", "name": "缺陷"}],
            "/organization/ORG/workitems": {"workitems": [{"workitem": _row("YX")}]},
        },
    ),
]


@pytest.mark.parametrize("key,adapter_cls,config,routes", _HTTP_CASES)
def test_http_adapter_contract(key, adapter_cls, config, routes):
    transport = FakeTransport(routes)
    adapter = adapter_cls(config, transport=transport)

    assert isinstance(adapter, TrackingAdapter)
    projects = adapter.get_projects()
    roles = adapter.get_roles()
    item_types = adapter.get_item_types()
    assert projects and roles and item_types
    assert all(isinstance(o, Option) and o.value and o.label for o in projects + roles + item_types)

    items = adapter.fetch_items(QuerySpec())
    assert len(items) == 1
    assert isinstance(items[0], WorkItem)
    assert items[0].source == key
    assert items[0].status == "RESOLVED"  # Fixed 归一化
    assert items[0].severity == 1 and items[0].title == "登录偶发 500"
    assert items[0].raw

    adapter.close_connection()
    assert transport.calls and transport.closed is True
    assert adapter.config.get("token", adapter.config.get("api_password",
                              adapter.config.get("access_token", ""))) == ""


@pytest.mark.parametrize("key,adapter_cls,config,routes", _HTTP_CASES)
def test_http_adapter_passes_filters_as_parameters(key, adapter_cls, config, routes):
    transport = FakeTransport(routes)
    adapter = adapter_cls(config, transport=transport)
    spec = QuerySpec(project_id="TEST", start_date=date(2026, 1, 1),
                     end_date=date(2026, 1, 31), exclude_types=("需求",), keywords="登录")
    assert adapter.fetch_items(spec)
    fetch_calls = [c for c in transport.calls if c["params"]]
    assert fetch_calls
    payload = str(fetch_calls[-1]["params"])
    assert "2026-01-01" in payload and "2026-01-31" in payload and "登录" in payload
    if key == "jira":
        assert "project = " in payload and "issuetype NOT IN" in payload
        assert "TEST" in payload
    else:
        assert "TEST" in payload


@pytest.mark.parametrize("key,adapter_cls,config,routes", _HTTP_CASES)
def test_http_adapter_rejects_bad_date_without_raising(key, adapter_cls, config, routes):
    transport = FakeTransport(routes)
    adapter = adapter_cls(config, transport=transport)
    assert adapter.fetch_items(QuerySpec(start_date="2026/01/01")) == []
    assert adapter.last_error


@pytest.mark.parametrize("key,adapter_cls,config,routes", _HTTP_CASES)
def test_http_adapter_isolates_transport_errors(key, adapter_cls, config, routes):
    adapter = adapter_cls(config, transport=FakeTransport(routes, fail=True))
    assert adapter.get_projects() == []
    assert adapter.fetch_items(QuerySpec()) == []
    assert adapter.last_error
    assert adapter.get_item_types() == []


@pytest.mark.parametrize("key,adapter_cls,config,routes", _HTTP_CASES)
def test_http_adapter_reports_missing_required_config(key, adapter_cls, config, routes):
    adapter = adapter_cls({})
    assert adapter.last_error
    assert adapter.get_projects() == []
    assert adapter.fetch_items(QuerySpec()) == []


# ---------------------------------------------------------------------------
# 禅道直连数据库适配器
# ---------------------------------------------------------------------------

def _raw_row():
    return {
        "id": "101", "title": "禅道缺陷", "project_id": "1", "project_name": "产品一",
        "item_type": "缺陷", "raw_status": "active", "severity": 1, "priority": 2,
        "reporter": "报告人", "assignee": "开发A", "resolver": "开发A", "closer": "测试A",
        "openedDate": "2026-01-05 09:00:00", "resolvedDate": "2026-01-06 09:00:00",
        "closedDate": "2026-01-07 09:00:00", "deleted": "0",
    }


class FakeDb:
    def __init__(self, rows):
        self.rows = rows
        self.last_sql = ""
        self.last_params = None

    def fetchall_to_dict(self, sql=None, params=None):
        self.last_sql = sql or ""
        self.last_params = params
        return list(self.rows)


class FakeCursor:
    def __init__(self):
        self.last_sql = ""
        self.last_params = None

    def execute(self, sql, params):
        self.last_sql = sql
        self.last_params = params


class FakeCursorDb:
    def __init__(self, rows):
        self.rows = rows
        self.cur = FakeCursor()

    def fetchall_to_dict(self):
        return list(self.rows)


class FakeExporter:
    def __init__(self, db):
        self.mysql_db = db
        self.closed = False

    def get_products(self):
        return [("1", "产品一")]

    def get_user_roles(self):
        return [{"value": "dev", "label": "开发"}]

    def get_bug_types(self):
        return [("bug", "缺陷")]

    def close_connection(self):
        self.closed = True


_ZENTAO_DB_CONFIG = {"host": "127.0.0.1", "database": "zentao", "user": "u", "password": "p"}


def _make_db_adapter(monkeypatch, db):
    exporter = FakeExporter(db)
    monkeypatch.setattr(zentao_db, "ZenTaoPerformanceExporter", lambda config: exporter)
    return zentao_db.ZentaoDbAdapter(_ZENTAO_DB_CONFIG), exporter


def test_zentao_db_adapter_contract_and_parameterized_sql(monkeypatch):
    db = FakeDb([_raw_row()])
    adapter, exporter = _make_db_adapter(monkeypatch, db)

    assert isinstance(adapter, TrackingAdapter)
    assert [o.value for o in adapter.get_projects()] == ["1"]
    assert [o.label for o in adapter.get_roles()] == ["开发"]
    assert [o.value for o in adapter.get_item_types()] == ["bug"]

    spec = QuerySpec(project_id="1", start_date=date(2026, 1, 1),
                     end_date=date(2026, 1, 31), exclude_types=("需求",))
    items = adapter.fetch_items(spec)
    assert len(items) == 1 and items[0].source == "zentao"
    assert items[0].status == "ACTIVE"
    assert "需求" not in db.last_sql and "2026" not in db.last_sql
    assert db.last_params == (1, "2026-01-01", "2026-01-31", "需求")

    adapter.close_connection()
    assert exporter.closed is True


def test_zentao_db_rejects_non_numeric_project_id(monkeypatch):
    db = FakeDb([_raw_row()])
    adapter, _ = _make_db_adapter(monkeypatch, db)
    assert adapter.fetch_items(QuerySpec(project_id="1 OR 1=1")) == []
    assert "必须是数字" in adapter.last_error
    assert db.last_sql == ""  # 非法输入不应落到 SQL


def test_zentao_db_supports_cursor_style_fetcher(monkeypatch):
    db = FakeCursorDb([_raw_row()])
    adapter, _ = _make_db_adapter(monkeypatch, db)
    assert len(adapter.fetch_items(QuerySpec())) == 1
    assert db.cur.last_sql and db.cur.last_params == ()


def test_zentao_db_respects_max_items(monkeypatch):
    reg.configure_tracking_limits(max_items=1)
    adapter, _ = _make_db_adapter(monkeypatch, FakeDb([_raw_row(), _raw_row()]))
    assert len(adapter.fetch_items(QuerySpec())) == 1


def test_zentao_db_reports_missing_config():
    adapter = zentao_db.ZentaoDbAdapter({})
    assert adapter.last_error
    assert adapter.fetch_items(QuerySpec()) == []


# ---------------------------------------------------------------------------
# 禅道 HTTP 代理适配器
# ---------------------------------------------------------------------------

class FakeClient:
    def __init__(self, records=None, fail=False):
        self.records = records or []
        self.fail = fail
        self.calls = []
        self.closed = False

    def get_products(self):
        return [("1", "产品一")]

    def get_user_roles(self):
        return [("dev", "开发")]

    def get_bug_types(self):
        return [("bug", "缺陷")]

    def _request(self, method, path, payload):
        self.calls.append((method, path, payload))
        if self.fail:
            raise RuntimeError("代理不可用")
        return {"records": self.records}

    def close_connection(self):
        self.closed = True


def _make_proxy_adapter(monkeypatch, client):
    def factory(**kwargs):
        for key, value in kwargs.items():
            setattr(client, key, value)
        return client
    monkeypatch.setattr(zentao_proxy, "ZenTaoProxyClient", factory)
    return zentao_proxy.ZentaoProxyAdapter({"url": "http://proxy.example", "token": "SECRET"})


def test_zentao_proxy_adapter_contract(monkeypatch):
    client = FakeClient([_raw_row()])
    adapter = _make_proxy_adapter(monkeypatch, client)

    assert isinstance(adapter, TrackingAdapter)
    assert [o.label for o in adapter.get_projects()] == ["产品一"]
    assert [o.label for o in adapter.get_roles()] == ["开发"]
    assert adapter.get_item_types()

    spec = QuerySpec(project_id="1", start_date=date(2026, 1, 1),
                     roles=("dev",), exclude_types=("需求",), keywords="登录")
    items = adapter.fetch_items(spec)
    assert len(items) == 1 and items[0].source == "zentao"
    assert "1" in adapter.config.get("url", "http://proxy.example") or client.calls
    method, path, payload = client.calls[-1]
    assert method == "POST" and path == "/query/items"
    assert payload["start_date"] == "2026-01-01" and payload["roles"] == ["dev"]
    assert payload["exclude_types"] == ["需求"] and payload["keywords"] == "登录"

    adapter.close_connection()
    assert client.closed is True


def test_zentao_proxy_prefers_client_fetch_items(monkeypatch):
    class ClientWithFetch(FakeClient):
        def fetch_items(self, spec):
            return [_raw_row()]

    client = ClientWithFetch()
    adapter = _make_proxy_adapter(monkeypatch, client)
    assert len(adapter.fetch_items(QuerySpec())) == 1
    assert client.calls == []


def test_zentao_proxy_isolates_errors(monkeypatch):
    adapter = _make_proxy_adapter(monkeypatch, FakeClient(fail=True))
    assert adapter.fetch_items(QuerySpec()) == []
    assert adapter.last_error
    assert adapter.get_projects()  # 元数据端点仍可用


def test_map_record_to_workitem_handles_object_and_validates_dates():
    class Row:
        id = "9"
        name = "对象形式"
        status = "closed"
        pri = "1"
        assignedTo = "开发B"
        closedDate = "2026-01-08 10:00:00"
        deleted = "yes"

    item = zentao_proxy.map_record_to_workitem(Row(), source="custom")
    assert item.source == "custom" and item.status == "CLOSED"
    assert item.title == "对象形式" and item.priority == 1
    assert item.assignee == "开发B" and item.deleted is True
    assert zentao_proxy.map_record_to_workitem(item) is item
    assert zentao_proxy.normalize_date_text(date(2026, 1, 5)) == "2026-01-05"
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        zentao_proxy.normalize_date_text("2026/01/05")


# ---------------------------------------------------------------------------
# 审计回归：凭据脱敏 / 声明式连接字段
# ---------------------------------------------------------------------------

def test_zentao_adapters_store_redacted_config(monkeypatch):
    db_adapter, _ = _make_db_adapter(monkeypatch, FakeDb([]))
    assert db_adapter.config["password"] == ""

    client = FakeClient()
    proxy_adapter = _make_proxy_adapter(monkeypatch, client)
    assert proxy_adapter.config["token"] == ""
    assert client.token == "SECRET"  # 明文只传给真实客户端


def test_jira_project_key_comes_from_normalized_config():
    adapter = jira.JiraAdapter(
        {"base_url": "https://jira.example", "token": "SECRET", "project_key": "PROJ"},
        transport=FakeTransport())
    assert adapter.project_key == "PROJ"


def test_tapd_and_yunxiao_honor_timeout_and_ssl_fields():
    class DummySession:
        def request(self, *args, **kwargs):
            return type("Resp", (), {"content": b"", "raise_for_status": lambda self: None})()

        def close(self):
            pass

    tapd_adapter = tapd.TapdAdapter(
        {"base_url": "https://x", "workspace_id": "WS", "api_password": "p",
         "timeout_seconds": 7, "verify_ssl": "false"}, session=DummySession())
    assert tapd_adapter.transport.timeout == 7.0
    assert tapd_adapter.transport.verify is False

    yunxiao_adapter = yunxiao.YunxiaoAdapter(
        {"base_url": "https://x", "organization_id": "ORG", "access_token": "t",
         "timeout_seconds": 9, "verify_ssl": "false"}, session=DummySession())
    assert yunxiao_adapter.transport.timeout == 9.0
    assert yunxiao_adapter.transport.verify is False
