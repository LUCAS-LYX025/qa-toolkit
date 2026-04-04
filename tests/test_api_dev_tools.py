import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.api_dev_tools import InterfaceDevTools


def test_compare_interfaces_detects_added_and_high_risk_changes():
    tool = InterfaceDevTools()

    baseline = [
        {
            "name": "创建订单",
            "method": "POST",
            "path": "/orders",
            "headers": {"Content-Type": "application/json"},
            "body": {"amount": 100},
            "expected_status": 200,
            "expected_response": {"id": 1},
        }
    ]
    target = [
        {
            "name": "创建订单",
            "method": "POST",
            "path": "/orders",
            "headers": {"Content-Type": "application/json"},
            "body": {"amount": 100, "currency": "CNY"},
            "request_format": "form",
            "expected_status": 201,
            "expected_response": {"id": 1, "status": "created"},
        },
        {
            "name": "查询订单列表",
            "method": "GET",
            "path": "/orders",
            "expected_status": 200,
            "expected_response": {"items": []},
        },
    ]

    diff = tool.compare_interfaces(baseline, target)

    assert diff["summary"]["added_count"] == 1
    assert diff["summary"]["changed_count"] == 1
    assert diff["summary"]["high_risk_count"] == 1
    assert diff["changed"][0]["risk_level"] == "high"
    assert any(change["label"] == "请求格式" for change in diff["changed"][0]["changes"])


def test_export_normalized_interfaces_and_snippet_generation_are_usable():
    tool = InterfaceDevTools()
    interface = {
        "name": "创建订单",
        "method": "POST",
        "path": "/orders",
        "headers": {"Content-Type": "application/json"},
        "body": {"sku": "sku-1", "amount": 100},
        "expected_status": 201,
        "expected_response": {"id": 1, "status": "created"},
        "tags": ["order"],
    }

    exported = tool.export_normalized_interfaces([interface])
    snippet = tool.generate_request_snippet(interface, language="Python requests", base_url="https://api.example.com")
    mock_script = tool.generate_mock_server_script([interface], port=9000)

    assert exported["summary"]["interface_count"] == 1
    assert exported["summary"]["with_body_count"] == 1
    assert "标准化接口清单" in exported["markdown_artifact"]
    assert "requests.post(" in snippet
    assert "https://api.example.com/orders" in snippet
    assert "DEFAULT_PORT = 9000" in mock_script
    assert "/orders" in mock_script


def test_analyze_interface_quality_reports_duplicates_and_path_param_problems():
    tool = InterfaceDevTools()

    interfaces = [
        {
            "name": "",
            "method": "GET",
            "path": "/users/{id}",
            "path_params": {},
            "expected_response": {},
            "tags": [],
        },
        {
            "name": "重复接口A",
            "method": "GET",
            "path": "/dup",
            "expected_response": {"ok": True},
        },
        {
            "name": "重复接口B",
            "method": "GET",
            "path": "/dup",
            "expected_response": {"ok": True},
        },
    ]

    quality = tool.analyze_interface_quality(interfaces)
    categories = {issue["category"] for issue in quality["issues"]}

    assert quality["summary"]["duplicate_count"] == 1
    assert "path_param_missing" in categories
    assert "duplicate_endpoint" in categories
    assert quality["summary"]["high_count"] >= 3


def test_generate_regression_checklist_covers_auth_paging_and_mutations():
    tool = InterfaceDevTools()

    interfaces = [
        {
            "name": "用户登录",
            "method": "POST",
            "path": "/auth/login",
            "body": {"username": "demo", "password": "secret"},
            "expected_response": {"token": "abc"},
        },
        {
            "name": "创建订单",
            "method": "POST",
            "path": "/orders",
            "body": {"sku": "sku-1", "amount": 100},
            "expected_response": {"id": 1},
        },
        {
            "name": "订单列表",
            "method": "GET",
            "path": "/orders",
            "query_params": {"page": 1, "sort": "created_at"},
            "expected_response": {"items": [], "total": 0},
        },
    ]

    checklist = tool.generate_regression_checklist(interfaces)
    items_by_name = {item["name"]: item for item in checklist["items"]}

    assert checklist["summary"]["interface_count"] == 3
    assert "接口回归清单" in checklist["markdown_artifact"]
    assert "鉴权" in items_by_name["用户登录"]["focus_points"]
    assert "数据变更" in items_by_name["创建订单"]["focus_points"]
    assert "分页" in items_by_name["订单列表"]["focus_points"]
