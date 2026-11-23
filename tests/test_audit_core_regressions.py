"""本轮审计 core 批次修复的回归测试（issue 4/5/6/9/10/13/19/23/26/29/99）。"""

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.api_dev_tools import InterfaceDevTools
from qa_toolkit.core.api_performance_tool import PerformanceTestTool
from qa_toolkit.core.api_security_tool import SecurityTestTool
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore
from qa_toolkit.core.application_security_tool import ApplicationSecurityTool
from qa_toolkit.core.env_profile_manager import EnvProfileManager


def test_issue_4_clear_active_namespace_does_not_fall_back(tmp_path):
    """clear_active(namespace) 写入空串后不应回退到 default。"""
    manager = EnvProfileManager(store_file=tmp_path / "store.json", key_file=tmp_path / "key")
    manager.upsert_profile("P", {"base_url": "https://example.com"})
    manager.set_active("P", "default")
    manager.clear_active("teamA")

    assert manager.get_active_profile_name("teamA") == ""
    # 未显式设置过的命名空间仍应回退 default
    assert manager.get_active_profile_name("teamB") == "P"


def test_issue_5_key_rotation_keeps_encrypted_credentials(tmp_path):
    """Fernet 密钥更换后 upsert 不能把旧密文覆盖成空凭据。"""
    store_file = tmp_path / "profiles.json"
    key_a = tmp_path / "keyA"
    key_b = tmp_path / "keyB"
    key_a.write_text("secret-alpha", encoding="utf-8")
    key_b.write_text("secret-beta", encoding="utf-8")

    first = EnvProfileManager(store_file=store_file, key_file=key_a)
    first.upsert_profile(
        "P",
        {"base_url": "https://a.example.com", "auth": {"mode": "bearer", "token": "tok-123"}},
    )
    original_cipher = json.loads(store_file.read_text(encoding="utf-8"))["profiles"]["P"]["auth_encrypted"]

    second = EnvProfileManager(store_file=store_file, key_file=key_b)
    public = second.get_profile("P")
    assert public["auth"]["mode"] == "none"
    assert public["encryption_error"] is True

    second.upsert_profile("P", dict(public, base_url="https://b.example.com"))
    assert json.loads(store_file.read_text(encoding="utf-8"))["profiles"]["P"]["auth_encrypted"] == original_cipher

    third = EnvProfileManager(store_file=store_file, key_file=key_a)
    restored = third.get_profile("P")
    assert restored["auth"]["mode"] == "bearer"
    assert restored["auth"]["token"] == "tok-123"
    assert restored["base_url"] == "https://b.example.com"


def test_issue_6_duplicate_interface_keys_are_counted():
    """同名 method+path 的接口不应被字典推导式静默覆盖。"""
    tools = InterfaceDevTools()
    baseline = [
        {"name": "A", "method": "GET", "path": "/x"},
        {"name": "B", "method": "GET", "path": "/x"},
    ]
    target = [{"name": "A", "method": "GET", "path": "/x"}]

    result = tools.compare_interfaces(baseline, target)
    summary = result["summary"]

    assert summary["baseline_total"] == 2
    assert summary["target_total"] == 1
    assert summary["baseline_duplicate_count"] == 1
    assert summary["target_duplicate_count"] == 0
    assert result["duplicates"]["baseline"] == ["GET /x"]


def test_issue_9_string_array_changes_report_counter_details():
    """字符串数组差异应基于 Counter 报告新增/删除项及数量。"""
    tools = InterfaceDevTools()

    message, risk = tools._describe_value_change(["a"], ["a", "a"])
    assert "新增项" in message and "a" in message and "1" in message
    assert risk == "medium"

    message, risk = tools._describe_value_change(["a", "a"], ["a"])
    assert "删除项" in message and "a" in message and "1" in message
    assert risk == "high"

    message, _ = tools._describe_value_change(["a", "b"], ["b", "a"])
    assert "顺序" in message
    assert message != "数组内容发生变化"


def test_issue_13_virtual_users_are_capped(monkeypatch):
    """虚拟用户数必须有上限，避免创建十万线程。"""
    tool = PerformanceTestTool()
    cap = tool.MAX_VIRTUAL_USERS
    assert cap < 100000

    plan = tool.build_test_plan(
        [{"name": "s", "method": "GET", "path": "/"}],
        "https://example.com",
        thread_group={"users": 100000},
    )
    assert plan["thread_group"]["users"] == cap

    captured = {}

    class FakeFuture:
        def result(self):
            return {"samples": [], "transaction_samples": []}

    class FakeExecutor:
        def __init__(self, max_workers):
            captured["max_workers"] = max_workers

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def submit(self, fn, *args):
            return FakeFuture()

    monkeypatch.setattr("qa_toolkit.core.api_performance_tool.ThreadPoolExecutor", FakeExecutor)
    monkeypatch.setattr(tool, "_build_result", lambda *args, **kwargs: {})
    monkeypatch.setattr(tool, "build_html_report", lambda result: "")

    tool.run_test_plan({"thread_group": {"users": 100000}, "samplers": [{"name": "s"}]})
    assert captured["max_workers"] == cap


def test_issue_19_duplicate_role_names_keep_both_status_codes():
    """同名角色在对比矩阵中不应互相覆盖。"""
    tool = SecurityTestTool()
    sample = {"Label": "L", "Probe Method": "GET", "URL": "https://example.com/x"}
    role_reports = [
        {"role": "user", "report": {"samples": [dict(sample, **{"Status Code": 200})]}},
        {"role": "user", "report": {"samples": [dict(sample, **{"Status Code": 403})]}},
    ]

    rows = tool._build_role_comparison_rows(role_reports)

    assert len(rows) == 1
    row = rows[0]
    assert row["user"] == 200
    assert row["user#2"] == 403
    assert "user:200" in row["Status Pattern"]
    assert "user#2:403" in row["Status Pattern"]
    assert row["Diversity"] == "有差异"


def test_issue_23_subprocess_run_has_timeout_and_handles_expiry(monkeypatch):
    """子进程执行必须有 timeout，并在超时时返回结构化错误。"""
    core = object.__new__(InterfaceAutoTestCore)
    core.test_dir = "/tmp"

    def fake_run(command, **kwargs):
        assert kwargs.get("timeout") is not None
        raise subprocess.TimeoutExpired(cmd=command, timeout=kwargs["timeout"], output="partial stdout")

    monkeypatch.setattr("qa_toolkit.core.api_test_core.subprocess.run", fake_run)

    result = core._run_command(["python"], "unittest")

    assert result["success"] is False
    assert result["errors"] == 1
    assert "超时" in result["error_message"]
    assert "partial stdout" in result["output"]


def test_issue_26_postman_query_values_are_url_encoded():
    """Postman query 值必须 URL 编码，不能把 & / = 拆成额外参数。"""
    core = object.__new__(InterfaceAutoTestCore)
    url_data = {
        "host": ["h"],
        "path": ["x"],
        "query": [{"key": "q", "value": "a&b=c"}],
    }

    assert core._extract_postman_raw_url(url_data, {}) == "https://h/x?q=a%26b%3Dc"


def test_issue_29_truncated_axml_returns_empty():
    """截断或伪造长度的 Manifest 不能触发 struct.error。"""
    tool = ApplicationSecurityTool()

    assert tool._parse_axml_events(b"\x03\x00") == []
    assert tool._parse_axml_events(b"\x00\x00") == []

    fake_chunk = struct.pack("<HHI", 0x0003, 8, 0xFFFFFFFF) + b"\x00" * 4
    assert tool._parse_axml_events(fake_chunk) == []


def test_issue_99_percentile_out_of_range_is_clamped():
    """分位数越界应被钳制到 [0, 100] 而不是抛 IndexError。"""
    tool = PerformanceTestTool()

    assert tool._percentile([1, 2, 3], 150) == 3
    assert tool._percentile([1, 2, 3], -10) == 1
    assert tool._percentile([1, 2, 3], 100) == 3
    assert tool._percentile([1, 2, 3], 0) == 1


def test_issue_10_no_invalid_escape_syntax_warning():
    """api_dev_tools.py 源码不得包含非法转义（Python 3.12+ 会发 SyntaxWarning）。"""
    source = Path(__file__).resolve().parents[1] / "src/qa_toolkit/core/api_dev_tools.py"
    result = subprocess.run(
        [sys.executable, "-W", "error::SyntaxWarning", "-c",
         f"import py_compile; py_compile.compile({str(source)!r}, doraise=True)"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0, result.stderr


def test_issue_10_mock_server_script_output_unchanged():
    """修复非法转义后，生成的 Mock 服务脚本必须保持原有字节输出。"""
    import hashlib

    tool = InterfaceDevTools.__new__(InterfaceDevTools)
    iface = {
        "name": "用户详情",
        "method": "GET",
        "path": "/api/users/{id}/orders/{oid}",
        "expected_status": 200,
        "expected_response": {"success": True, "data": {"id": 1}},
    }
    script = tool.generate_mock_server_script([iface], host="127.0.0.1", port=9999)

    compile(script, "<mock>", "exec")
    assert hashlib.sha256(script.encode()).hexdigest() == (
        "3fb5df82221891fcf98b2618327cea4fe3842afe2035d58384f1c8e2abe35f6e"
    )
