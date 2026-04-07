import sys
from pathlib import Path
from typing import Any, Dict

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.api_test_core import InterfaceAutoTestCore


def test_parse_text_content_supports_windows_cmd_curl_blocks() -> None:
    curl_text = r'''curl ^"https://tanjitest.xmbus.com:30767/api-tanji/v1/common/passenger/on-the-way/order/get?passengerPhone=18850367503^" ^
  -H ^"Accept: application/json, text/plain, */*^" ^
  -H ^"Authorization: Bearer demo-token^" ^
  -b ^"x-domain=tanjitest.xmbus.com; token=abc123; tenant=xmzsx^" ^
  -H ^"sec-ch-ua: ^\^"Google Chrome^\^";v=^\^"137^\^", ^\^"Chromium^\^";v=^\^"137^\^"^" ^
  -H ^"tenant-code: xmzsx^" ^
  -H ^"tenant-id: zh00002^"'''

    core = InterfaceAutoTestCore()
    interfaces = core.parse_text_content(curl_text)

    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface["method"] == "GET"
    assert interface["path"] == "https://tanjitest.xmbus.com:30767/api-tanji/v1/common/passenger/on-the-way/order/get?passengerPhone=18850367503"
    assert interface["query_params"] == {"passengerPhone": "18850367503"}
    assert interface["headers"]["Authorization"] == "Bearer demo-token"
    assert interface["headers"]["Cookie"] == "x-domain=tanjitest.xmbus.com; token=abc123; tenant=xmzsx"
    assert interface["headers"]["tenant-code"] == "xmzsx"
    assert interface["headers"]["tenant-id"] == "zh00002"
    assert interface["headers"]["sec-ch-ua"] == '"Google Chrome";v="137", "Chromium";v="137"'
    assert core.last_parse_meta["detected_base_url"] == "https://tanjitest.xmbus.com:30767"


def test_parse_text_content_supports_windows_cmd_curl_json_body() -> None:
    curl_text = r'''curl ^"https://example.com/api/demo^" ^
  -X POST ^
  -H ^"Content-Type: application/json^" ^
  --data-raw ^"{\^"name\^": \^"alice\^", \^"enabled\^": true}^"'''

    core = InterfaceAutoTestCore()
    interfaces = core.parse_text_content(curl_text)

    assert len(interfaces) == 1
    interface = interfaces[0]
    assert interface["method"] == "POST"
    assert interface["body"] == {"name": "alice", "enabled": True}
    assert interface["headers"]["Content-Type"] == "application/json"


def test_run_tests_falls_back_to_requests_script_when_pytest_missing(tmp_path: Path, monkeypatch) -> None:
    core = InterfaceAutoTestCore()
    core.test_dir = str(tmp_path)
    tmp_path.mkdir(parents=True, exist_ok=True)

    interfaces = [
        {
            "name": "获取订单",
            "method": "GET",
            "path": "/api/orders",
            "headers": {"Accept": "application/json"},
            "expected_status": 200,
            "expected_response": {},
        }
    ]
    generated_files = core.generate_test_cases(
        interfaces=interfaces,
        framework="pytest",
        base_url="https://example.com",
        timeout=30,
        retry_times=0,
        verify_ssl=False,
    )
    core.save_test_files(generated_files)

    monkeypatch.setattr(
        InterfaceAutoTestCore,
        "_is_runtime_module_available",
        staticmethod(lambda module_name: False if module_name == "pytest" else True),
    )

    captured: Dict[str, Any] = {}

    def _fake_run_command(command, mode):
        captured["command"] = command
        captured["mode"] = mode
        return {
            "total": 1,
            "passed": 1,
            "failed": 0,
            "errors": 0,
            "success": True,
            "test_details": [],
            "output": "",
        }

    monkeypatch.setattr(core, "_run_command", _fake_run_command)

    results = core.run_tests("pytest")

    assert captured["mode"] == "requests_script"
    assert captured["command"] == [sys.executable, "run_interfaces.py"]
    assert (tmp_path / "run_interfaces.py").exists()
    assert results["requested_mode"] == "pytest"
    assert results["executed_mode"] == "requests_script"
    assert "已自动降级为 requests脚本" in results["runner_note"]
