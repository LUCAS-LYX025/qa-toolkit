"""自动生成的接口测试脚本 - unittest"""

import unittest

import json
import re
import time
from copy import deepcopy

import requests

CONFIG = json.loads(r'''{"base_url": "https://jsonplaceholder.typicode.com", "timeout": 20, "retry_times": 0, "verify_ssl": true, "request_format": "auto", "template_style": "标准模板"}''')
CASES = json.loads(r'''[{"name": "获取单个帖子", "method": "GET", "path": "/posts/1", "description": "获取帖子详情", "headers": {}, "parameters": {}, "path_params": {}, "query_params": {}, "body": null, "expected_status": 200, "expected_response": ["userId", "id", "title", "body"], "request_format": "auto", "tags": [], "source": "", "case_id": "case_001", "test_name": "test_case_001"}]''')
CASE_INDEX = {case["case_id"]: case for case in CASES}


def clone_value(value):
    return deepcopy(value)


def build_url(base_url, path, path_params):
    actual_path = path or "/"
    for key, value in (path_params or {}).items():
        actual_path = actual_path.replace("{" + str(key) + "}", str(value))
    if actual_path.startswith(("http://", "https://")):
        return actual_path
    if not base_url:
        return actual_path
    return base_url.rstrip("/") + "/" + actual_path.lstrip("/")


def merge_request_parts(case):
    path = case.get("path", "")
    path_params = clone_value(case.get("path_params") or {})
    query_params = clone_value(case.get("query_params") or {})
    body = clone_value(case.get("body"))
    placeholders = set(re.findall(r"\{([^}]+)\}", path or ""))
    for name in placeholders:
        if name not in path_params:
            if isinstance(query_params, dict) and name in query_params:
                path_params[name] = query_params.pop(name)
            elif isinstance(body, dict) and name in body:
                path_params[name] = body.pop(name)
    return path_params, query_params, body


def resolve_request_format(case):
    override = CONFIG.get("request_format", "auto")
    if override and override != "auto":
        return override
    case_format = case.get("request_format", "auto")
    if case_format and case_format != "auto":
        return case_format
    headers = case.get("headers") or {}
    content_type = str(headers.get("Content-Type") or headers.get("content-type") or "").lower()
    body = case.get("body")
    if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
        return "form"
    if "application/json" in content_type:
        return "json"
    if isinstance(body, (dict, list)):
        return "json"
    if isinstance(body, str):
        return "raw"
    return "auto"


def response_json(response):
    try:
        return response.json()
    except ValueError:
        return None


def compare_standard(expected, actual, prefix):
    failures = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{prefix} 应为对象，实际为 {type(actual).__name__}"]
        for key, value in expected.items():
            if key not in actual:
                failures.append(f"{prefix} 缺少字段 {key}")
                continue
            if isinstance(value, (dict, list)):
                continue
            if value not in (None, "", {}, []) and actual.get(key) != value:
                failures.append(f"{prefix}.{key} 期望 {value!r}，实际 {actual.get(key)!r}")
        return failures

    if isinstance(expected, list):
        if all(isinstance(item, str) for item in expected):
            if isinstance(actual, list) and actual and isinstance(actual[0], dict):
                for key in expected:
                    if key not in actual[0]:
                        failures.append(f"{prefix}[0] 缺少字段 {key}")
                return failures
            if isinstance(actual, dict):
                for key in expected:
                    if key not in actual:
                        failures.append(f"{prefix} 缺少字段 {key}")
                return failures
        if not isinstance(actual, list) or not actual:
            return [f"{prefix} 应返回非空数组"]
        return []

    if isinstance(expected, str):
        if expected not in str(actual):
            return [f"{prefix} 未包含期望文本 {expected!r}"]
        return []

    if expected not in (None, "", {}, []) and expected != actual:
        return [f"{prefix} 期望 {expected!r}，实际 {actual!r}"]
    return failures


def compare_strict(expected, actual, prefix):
    failures = []
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            return [f"{prefix} 应为对象，实际为 {type(actual).__name__}"]
        for key, value in expected.items():
            if key not in actual:
                failures.append(f"{prefix} 缺少字段 {key}")
                continue
            failures.extend(compare_strict(value, actual[key], f"{prefix}.{key}"))
        return failures

    if isinstance(expected, list):
        if all(isinstance(item, str) for item in expected):
            if isinstance(actual, list) and actual and isinstance(actual[0], dict):
                for key in expected:
                    if key not in actual[0]:
                        failures.append(f"{prefix}[0] 缺少字段 {key}")
                return failures
            if isinstance(actual, dict):
                for key in expected:
                    if key not in actual:
                        failures.append(f"{prefix} 缺少字段 {key}")
                return failures
        if not isinstance(actual, list):
            return [f"{prefix} 应为数组，实际为 {type(actual).__name__}"]
        if len(actual) < len(expected):
            failures.append(f"{prefix} 长度不足，期望至少 {len(expected)}，实际 {len(actual)}")
        for index, value in enumerate(expected):
            if index >= len(actual):
                break
            failures.extend(compare_strict(value, actual[index], f"{prefix}[{index}]"))
        return failures

    if expected != actual:
        failures.append(f"{prefix} 期望 {expected!r}，实际 {actual!r}")
    return failures


def build_assertions(case, response):
    assertions = []
    failures = []
    expected_status = int(case.get("expected_status", 200))
    status_ok = response.status_code == expected_status
    status_message = f"期望 {expected_status}，实际 {response.status_code}"
    assertions.append({
        "description": f"状态码应为 {expected_status}",
        "passed": status_ok,
        "message": status_message,
    })
    if not status_ok:
        failures.append(status_message)

    expected_response = case.get("expected_response")
    if expected_response in (None, "", {}, []) or CONFIG.get("template_style") == "冒烟模板":
        return assertions, failures

    actual_payload = response_json(response)
    actual_value = actual_payload if actual_payload is not None else response.text
    if CONFIG.get("template_style") == "严格模板":
        payload_failures = compare_strict(expected_response, actual_value, "response")
    else:
        payload_failures = compare_standard(expected_response, actual_value, "response")

    assertions.append({
        "description": "响应内容断言",
        "passed": not payload_failures,
        "message": "通过" if not payload_failures else "; ".join(payload_failures),
    })
    failures.extend(payload_failures)
    return assertions, failures


def build_detail(case, status, response, response_time, url, error, assertions):
    return {
        "case_id": case.get("case_id"),
        "test_name": case.get("test_name"),
        "name": case.get("name"),
        "method": case.get("method"),
        "path": case.get("path"),
        "status": status,
        "status_code": response.status_code if response is not None else 0,
        "response_time": round(response_time, 4),
        "headers": case.get("headers") or {},
        "parameters": case.get("parameters"),
        "response_body": response.text if response is not None else "",
        "error": error or "",
        "assertions": assertions or [],
        "url": url,
    }


def emit_case_result(detail):
    print("CASE_RESULT::" + json.dumps(detail, ensure_ascii=False))


def send_request(session, case):
    path_params, query_params, body = merge_request_parts(case)
    headers = clone_value(case.get("headers") or {})
    method = str(case.get("method", "GET")).upper()
    request_format = resolve_request_format(case)
    url = build_url(CONFIG.get("base_url", ""), case.get("path", ""), path_params)
    request_kwargs = {
        "method": method,
        "url": url,
        "headers": headers,
        "params": query_params or None,
        "timeout": int(CONFIG.get("timeout", 30)),
        "verify": bool(CONFIG.get("verify_ssl", False)),
    }

    if method != "GET" and body is not None:
        if request_format == "data_json":
            headers.setdefault("Content-Type", "application/json")
            request_kwargs["data"] = json.dumps(body, ensure_ascii=False)
        elif request_format == "form":
            request_kwargs["data"] = body
        elif request_format == "raw":
            request_kwargs["data"] = body if isinstance(body, str) else json.dumps(body, ensure_ascii=False)
        else:
            request_kwargs["json"] = body
    elif method == "GET" and body and not request_kwargs["params"] and isinstance(body, dict):
        request_kwargs["params"] = body

    retry_times = int(CONFIG.get("retry_times", 0))
    last_error = None
    for attempt in range(retry_times + 1):
        try:
            return session.request(**request_kwargs), url
        except requests.exceptions.RequestException as exc:
            last_error = exc
            if attempt >= retry_times:
                raise
            time.sleep(1)
    raise last_error or RuntimeError("请求失败")


def execute_case(session, case):
    started_at = time.time()
    response = None
    url = ""
    assertions = []
    try:
        response, url = send_request(session, case)
        assertions, failures = build_assertions(case, response)
        if failures:
            raise AssertionError("; ".join(failures))
        detail = build_detail(case, "passed", response, time.time() - started_at, url, "", assertions)
        emit_case_result(detail)
        return detail
    except AssertionError as exc:
        detail = build_detail(case, "failed", response, time.time() - started_at, url, str(exc), assertions)
        emit_case_result(detail)
        raise
    except Exception as exc:
        detail = build_detail(case, "error", response, time.time() - started_at, url, str(exc), assertions)
        emit_case_result(detail)
        raise



class GeneratedApiTests(unittest.TestCase):

    @classmethod

    def setUpClass(cls):

        cls.session = requests.Session()



    @classmethod

    def tearDownClass(cls):

        cls.session.close()




    def test_case_001(self):
        execute_case(self.session, CASE_INDEX["case_001"])



if __name__ == "__main__":

    unittest.main(verbosity=2)

