import io
import json
import os
import re
import shlex
import base64
import subprocess
import sys
import time
from copy import deepcopy
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlparse

import pandas as pd
import requests

from qa_toolkit.paths import API_CASES_DIR, REPORTS_DIR, UPLOADS_DIR


class InterfaceAutoTestCore:
    """接口自动化测试核心类"""

    HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
    REQUEST_FORMAT_MAP = {
        "自动检测": "auto",
        "auto": "auto",
        "json=参数": "json",
        "json": "json",
        "data=json.dumps()": "data_json",
        "json格式(data)": "data_json",
        "data": "data_json",
        "form-urlencoded": "form",
        "form": "form",
        "raw": "raw",
        "text": "raw",
    }
    EXECUTION_MODE_MAP = {
        "pytest": "pytest",
        "unittest": "unittest",
        "requests脚本": "requests_script",
        "requests_script": "requests_script",
        "requests": "requests_script",
    }

    def __init__(self):
        self.base_dir = str(API_CASES_DIR.parent)
        self.upload_dir = str(UPLOADS_DIR)
        self.test_dir = str(API_CASES_DIR)
        self.report_dir = str(REPORTS_DIR)
        self.last_parse_meta = {
            "source_type": "",
            "source_name": "",
            "detected_base_url": "",
            "interface_count": 0,
        }
        self.setup_directories()

    def setup_directories(self):
        """创建必要的目录"""
        for directory in [self.upload_dir, self.test_dir, self.report_dir]:
            os.makedirs(directory, exist_ok=True)

    def parse_document(self, file_path: str, source_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """解析接口文档"""
        self._reset_parse_meta()
        file_ext = os.path.splitext(file_path)[1].lower().lstrip(".")

        if file_ext in {"xlsx", "xls"}:
            interfaces = self.parse_excel(file_path)
            return self._finalize_interfaces(interfaces, "excel", os.path.basename(file_path))

        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()

        effective_type = source_type or {
            "json": "auto",
            "txt": "text",
            "md": "text",
            "bru": "bruno",
            "yaml": "swagger",
            "yml": "swagger",
        }.get(file_ext, "auto")

        return self.parse_content(content, source_type=effective_type, source_name=os.path.basename(file_path))

    def parse_content(
        self,
        content: str,
        source_type: str = "auto",
        source_name: str = "inline",
    ) -> List[Dict[str, Any]]:
        """解析原始文本内容"""
        self._reset_parse_meta()
        text = (content or "").strip()
        if not text:
            raise ValueError("导入内容不能为空")

        effective_type = (source_type or "auto").lower()
        effective_name = source_name
        if self._looks_like_url(text):
            text = self._fetch_remote_content(text)
            effective_name = source_name if source_name != "inline" else "remote-spec"
            if effective_type == "text":
                effective_type = "auto"

        structured = None
        if effective_type in {"auto", "json", "swagger", "openapi"}:
            structured = self._load_structured_content(text)
            if structured is not None:
                if self._looks_like_openapi(structured):
                    interfaces = self.parse_openapi_data(structured)
                    return self._finalize_interfaces(interfaces, "swagger", effective_name)
                if effective_type in {"auto", "json"}:
                    interfaces = self.parse_json_data(structured)
                    return self._finalize_interfaces(interfaces, "json", effective_name)

        if effective_type in {"auto", "bruno", "text"} and (
            effective_type == "bruno" or self._looks_like_bruno_text(text)
        ):
            interfaces = self.parse_bruno_content(text)
            return self._finalize_interfaces(interfaces, "bruno", effective_name)

        if effective_type in {"auto", "text"}:
            interfaces = self.parse_text_content(text)
            return self._finalize_interfaces(interfaces, "text", effective_name)

        if effective_type in {"json", "swagger", "openapi"} and structured is None:
            raise ValueError("未能解析结构化内容，请检查 JSON/Swagger 格式是否正确")

        raise ValueError(f"不支持的导入方式: {source_type}")

    def parse_excel(self, file_path: str) -> List[Dict[str, Any]]:
        """解析 Excel 文件"""
        interfaces: List[Dict[str, Any]] = []
        try:
            dataframe = pd.read_excel(file_path)
        except Exception as exc:
            raise ValueError(f"解析 Excel 文件失败: {exc}") from exc

        for _, row in dataframe.iterrows():
            name = self._clean_text(row.get("接口名称"))
            path = self._clean_text(row.get("接口路径"))
            if not name and not path:
                continue

            raw_interface = {
                "name": name,
                "method": self._clean_text(row.get("请求方法")) or "GET",
                "path": path,
                "description": self._clean_text(row.get("接口描述")),
                "headers": self.parse_json_field(row.get("请求头")),
                "parameters": self.parse_json_field(row.get("请求参数")),
                "expected_status": self._coerce_int(row.get("期望状态码"), 200),
                "expected_response": self.parse_json_field(row.get("期望响应")),
            }
            interfaces.append(self._normalize_interface(raw_interface))

        return interfaces

    def parse_json(self, file_path: str) -> List[Dict[str, Any]]:
        """兼容旧接口"""
        return self.parse_document(file_path, source_type="json")

    def parse_json_data(self, data: Any) -> List[Dict[str, Any]]:
        """解析 JSON 数据"""
        if isinstance(data, list):
            return [self._normalize_interface(item) for item in data if isinstance(item, dict)]

        if not isinstance(data, dict):
            raise ValueError("JSON 内容必须是对象或数组")

        if "interfaces" in data and isinstance(data["interfaces"], list):
            self.last_parse_meta["detected_base_url"] = self._clean_text(data.get("base_url"))
            return [self._normalize_interface(item) for item in data["interfaces"] if isinstance(item, dict)]

        if self._looks_like_openapi(data):
            return self.parse_openapi_data(data)

        if self._looks_like_postman_collection(data):
            return self.parse_postman_collection(data)

        if self._looks_like_har(data):
            return self.parse_har_data(data)

        if self._looks_like_insomnia_export(data):
            return self.parse_insomnia_export(data)

        if "path" in data or "url" in data:
            self.last_parse_meta["detected_base_url"] = self._clean_text(data.get("base_url"))
            return [self._normalize_interface(data)]

        raise ValueError("不支持的 JSON 接口文档格式")

    def parse_text_content(self, content: str) -> List[Dict[str, Any]]:
        """解析文本格式接口定义"""
        text = (content or "").strip()
        if not text:
            return []

        if text.lower().startswith("curl "):
            blocks = re.split(r"\n(?=curl\s)", text, flags=re.IGNORECASE)
        else:
            blocks = re.split(r"\n\s*---+\s*\n", text)
            if len(blocks) == 1 and len(re.findall(r"(?im)^(?:接口名称|name)\s*:", text)) > 1:
                blocks = [block for block in re.split(r"(?im)(?=^(?:接口名称|name)\s*:)", text) if block.strip()]

        interfaces: List[Dict[str, Any]] = []
        for raw_block in blocks:
            block = raw_block.strip()
            if not block:
                continue
            if block.lower().startswith("curl "):
                interfaces.append(self._parse_curl_block(block))
            else:
                interfaces.append(self._parse_structured_text_block(block))

        if not interfaces:
            raise ValueError("未能从文本中解析出任何接口定义")
        return interfaces

    def parse_openapi_data(self, spec: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 Swagger / OpenAPI 数据"""
        interfaces: List[Dict[str, Any]] = []
        detected_base_url = self._detect_openapi_base_url(spec)
        if detected_base_url:
            self.last_parse_meta["detected_base_url"] = detected_base_url

        paths = spec.get("paths", {})
        if not isinstance(paths, dict):
            raise ValueError("Swagger/OpenAPI 文档缺少 paths 定义")

        for raw_path, path_item in paths.items():
            if not isinstance(path_item, dict):
                continue

            path_level_params = path_item.get("parameters", [])
            for method, operation in path_item.items():
                method_upper = str(method).upper()
                if method_upper not in self.HTTP_METHODS or not isinstance(operation, dict):
                    continue

                merged_params = self._merge_openapi_parameters(path_level_params, operation.get("parameters", []))
                path_params: Dict[str, Any] = {}
                query_params: Dict[str, Any] = {}
                headers: Dict[str, Any] = {}

                for parameter in merged_params:
                    if not isinstance(parameter, dict):
                        continue
                    location = parameter.get("in")
                    value = self._extract_openapi_parameter_value(parameter, spec)
                    name = parameter.get("name")
                    if not name:
                        continue
                    if location == "path":
                        path_params[name] = value
                    elif location == "query":
                        query_params[name] = value
                    elif location == "header":
                        headers[name] = value

                body, request_format, body_headers = self._extract_openapi_request_body(spec, operation, merged_params)
                headers.update(body_headers)

                expected_status, expected_response = self._extract_openapi_expected_response(spec, operation)

                raw_interface = {
                    "name": self._clean_text(operation.get("summary"))
                    or self._clean_text(operation.get("operationId"))
                    or f"{method_upper} {raw_path}",
                    "method": method_upper,
                    "path": raw_path,
                    "description": self._clean_text(operation.get("description"))
                    or self._clean_text(operation.get("summary")),
                    "headers": headers,
                    "path_params": path_params,
                    "query_params": query_params,
                    "body": body,
                    "expected_status": expected_status,
                    "expected_response": expected_response,
                    "request_format": request_format,
                    "tags": operation.get("tags", []),
                    "source": "swagger",
                }
                interfaces.append(self._normalize_interface(raw_interface))

        if not interfaces:
            raise ValueError("Swagger/OpenAPI 文档中未解析到可执行接口")
        return interfaces

    def parse_postman_collection(self, collection: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 Postman Collection"""
        variables = self._extract_postman_variables(collection)
        detected_base_url = self._extract_postman_base_url(collection, variables)
        if detected_base_url:
            self.last_parse_meta["detected_base_url"] = detected_base_url

        interfaces: List[Dict[str, Any]] = []

        def walk_items(items: Any, parents: List[str]):
            for item in items or []:
                if not isinstance(item, dict):
                    continue

                item_name = self._clean_text(item.get("name"))
                if isinstance(item.get("item"), list) and "request" not in item:
                    walk_items(item.get("item"), parents + ([item_name] if item_name else []))
                    continue

                request = item.get("request")
                if not isinstance(request, dict):
                    continue

                interface = self._postman_item_to_interface(item, request, parents, variables)
                if interface:
                    interfaces.append(interface)

        walk_items(collection.get("item", []), [])

        if not interfaces:
            raise ValueError("Postman Collection 中未解析到可执行请求")
        return interfaces

    def parse_har_data(self, har_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 HAR 内容"""
        log_data = har_data.get("log", {})
        entries = log_data.get("entries", [])
        if not isinstance(entries, list):
            raise ValueError("HAR 文件缺少 log.entries")

        interfaces: List[Dict[str, Any]] = []
        for index, entry in enumerate(entries, start=1):
            if not isinstance(entry, dict):
                continue

            request = entry.get("request", {})
            response = entry.get("response", {})
            if not isinstance(request, dict):
                continue

            method = self._clean_text(request.get("method")) or "GET"
            raw_url = self._clean_text(request.get("url"))
            if not raw_url:
                continue

            base_url, path, query_params = self._split_url_parts(raw_url)
            if base_url and not self.last_parse_meta.get("detected_base_url"):
                self.last_parse_meta["detected_base_url"] = base_url
            elif self.last_parse_meta.get("detected_base_url") and base_url and base_url != self.last_parse_meta["detected_base_url"]:
                path = raw_url

            headers = self._headers_list_to_dict(request.get("headers"))
            if not query_params:
                query_params = self._name_value_list_to_dict(request.get("queryString"))

            body, request_format = self._extract_har_request_body(request, headers)
            expected_status = self._coerce_int(response.get("status"), 200)
            expected_response = self._extract_har_response_example(response)

            raw_interface = {
                "name": self._clean_text(entry.get("comment"))
                or self._clean_text(request.get("comment"))
                or f"{method.upper()} {path or raw_url}",
                "method": method.upper(),
                "path": path or raw_url,
                "description": self._clean_text(entry.get("_resourceType")) or self._clean_text(response.get("statusText")),
                "headers": headers,
                "query_params": query_params,
                "body": body,
                "expected_status": expected_status,
                "expected_response": expected_response,
                "request_format": request_format,
                "source": "har",
            }
            interfaces.append(self._normalize_interface(raw_interface))

        if not interfaces:
            raise ValueError("HAR 文件中未解析到可执行请求")
        return interfaces

    def parse_insomnia_export(self, export_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """解析 Insomnia 导出 JSON"""
        resources = export_data.get("resources", [])
        if not isinstance(resources, list):
            raise ValueError("Insomnia 导出内容缺少 resources")

        environment_values = self._extract_insomnia_environment_values(resources)
        request_examples = self._extract_insomnia_response_examples(resources)
        if environment_values.get("base_url") and not self.last_parse_meta.get("detected_base_url"):
            self.last_parse_meta["detected_base_url"] = self._normalize_base_url(environment_values["base_url"])

        interfaces: List[Dict[str, Any]] = []
        for resource in resources:
            if not isinstance(resource, dict) or resource.get("_type") != "request":
                continue

            method = self._clean_text(resource.get("method")) or "GET"
            raw_url = self._replace_insomnia_variables(self._clean_text(resource.get("url")), environment_values)
            if not raw_url:
                continue

            base_url, path, query_params = self._split_url_parts(raw_url)
            if base_url and not self.last_parse_meta.get("detected_base_url"):
                self.last_parse_meta["detected_base_url"] = base_url
            elif self.last_parse_meta.get("detected_base_url") and base_url and base_url != self.last_parse_meta["detected_base_url"]:
                path = raw_url

            headers = self._insomnia_headers_to_dict(resource.get("headers"), environment_values)
            body, request_format = self._extract_insomnia_request_body(resource.get("body"), headers, environment_values)
            example_response = request_examples.get(resource.get("_id"), {})
            raw_interface = {
                "name": self._clean_text(resource.get("name")) or f"{method.upper()} {path}",
                "method": method.upper(),
                "path": path or raw_url,
                "description": self._clean_text(resource.get("description")),
                "headers": headers,
                "query_params": query_params,
                "body": body,
                "expected_status": self._coerce_int(example_response.get("statusCode"), 200),
                "expected_response": example_response.get("body", {}),
                "request_format": request_format,
                "source": "insomnia",
            }
            interfaces.append(self._normalize_interface(raw_interface))

        if not interfaces:
            raise ValueError("Insomnia 导出内容中未解析到可执行请求")
        return interfaces

    def parse_bruno_content(self, content: str) -> List[Dict[str, Any]]:
        """解析 Bruno .bru 文本"""
        text = (content or "").strip()
        if not text:
            return []

        documents = [block.strip() for block in re.split(r"(?m)^(?=\s*meta\s*\{)", text) if block.strip()]
        if not documents:
            documents = [text]

        interfaces: List[Dict[str, Any]] = []
        for document in documents:
            interface = self._parse_bruno_document(document)
            if interface:
                interfaces.append(interface)

        if not interfaces:
            raise ValueError("Bruno 文本中未解析到可执行请求")
        return interfaces

    def parse_json_field(self, field: Any) -> Any:
        """解析 JSON 样式字段"""
        if field is None:
            return {}
        if isinstance(field, (dict, list)):
            return field
        if self._is_empty_value(field):
            return {}

        text = str(field).strip()
        if not text or text.lower() == "nan":
            return {}

        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def generate_test_cases(
        self,
        interfaces: List[Dict[str, Any]],
        framework: str,
        base_url: str,
        timeout: int,
        retry_times: int,
        verify_ssl: bool,
        request_format: str = "自动检测",
        template_style: str = "标准模板",
        environment_config: Optional[Dict[str, Any]] = None,
        auth_config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, str]:
        """生成测试文件"""
        mode = self._normalize_execution_mode(framework)
        cases = self._prepare_cases(interfaces)
        env_config = self._normalize_environment_config(environment_config, base_url)
        normalized_auth = self._normalize_auth_config(auth_config)
        auth_headers = self._build_auth_headers(normalized_auth)
        for env_name, env_item in env_config.get("environments", {}).items():
            merged_headers = dict(env_item.get("headers", {}))
            for key, value in auth_headers.items():
                merged_headers[key] = value
            env_item["headers"] = merged_headers

        active_env = env_config.get("active_env", "custom")
        active_env_config = env_config.get("environments", {}).get(active_env, {})
        config = {
            "base_url": active_env_config.get("base_url") or self._normalize_base_url(base_url),
            "timeout": int(timeout),
            "retry_times": int(retry_times),
            "verify_ssl": bool(verify_ssl),
            "request_format": self._normalize_request_format(request_format),
            "template_style": template_style or "标准模板",
            "active_env": active_env,
            "environments": env_config.get("environments", {}),
            "default_headers": active_env_config.get("headers", {}),
            "auth": normalized_auth,
        }

        manifest = {
            "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            "mode": mode,
            "config": config,
            "cases": cases,
        }

        files = {
            "interface_manifest.json": json.dumps(manifest, ensure_ascii=False, indent=2),
        }

        if mode == "pytest":
            files["test_interfaces.py"] = self._render_pytest_file(cases, config)
        elif mode == "unittest":
            files["test_interfaces.py"] = self._render_unittest_file(cases, config)
        elif mode == "requests_script":
            files["run_interfaces.py"] = self._render_requests_script(cases, config)
        else:
            raise ValueError(f"不支持的执行模式: {framework}")

        return files

    def save_test_files(self, test_files: Dict[str, str]) -> Dict[str, str]:
        """保存生成的测试文件"""
        known_generated_files = {
            "test_interfaces.py",
            "run_interfaces.py",
            "interface_manifest.json",
        }

        for stale_name in known_generated_files - set(test_files.keys()):
            stale_path = os.path.join(self.test_dir, stale_name)
            if os.path.exists(stale_path):
                os.remove(stale_path)

        saved_files: Dict[str, str] = {}
        for filename, content in test_files.items():
            file_path = os.path.join(self.test_dir, filename)
            with open(file_path, "w", encoding="utf-8") as file:
                file.write(content)
            saved_files[filename] = file_path

        return saved_files

    def run_tests(self, framework: str) -> Dict[str, Any]:
        """运行测试用例"""
        mode = self._normalize_execution_mode(framework)

        if mode == "unittest":
            command = [sys.executable, "-m", "unittest", "test_interfaces", "-v"]
        elif mode == "pytest":
            command = [sys.executable, "-m", "pytest", "test_interfaces.py", "-q", "-s"]
        elif mode == "requests_script":
            command = [sys.executable, "run_interfaces.py"]
        else:
            return self._build_runner_error(f"不支持的执行模式: {framework}")

        return self._run_command(command, mode)

    def generate_html_report(self, test_results: Dict[str, Any], framework: str) -> str:
        """生成简单 HTML 测试报告"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        total = test_results.get("total", 0)
        passed = test_results.get("passed", 0)
        failed = test_results.get("failed", 0)
        errors = test_results.get("errors", 0)
        success_rate = (passed / total * 100) if total else 0

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>接口自动化测试报告</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 24px; background: #f3f5f7; }}
        .container {{ max-width: 1100px; margin: 0 auto; background: #fff; border-radius: 12px; padding: 24px; }}
        .metrics {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 24px 0; }}
        .card {{ background: #fafbfc; border-radius: 10px; padding: 16px; border-left: 4px solid #1f77b4; }}
        .value {{ font-size: 28px; font-weight: bold; margin-top: 8px; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 24px; }}
        th, td {{ padding: 12px; border-bottom: 1px solid #eee; text-align: left; }}
        th {{ background: #fafbfc; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>接口自动化测试报告</h1>
        <p>执行模式: {framework} | 生成时间: {timestamp}</p>
        <p>成功率: {success_rate:.1f}%</p>
        <div class="metrics">
            <div class="card"><div>总用例</div><div class="value">{total}</div></div>
            <div class="card"><div>通过</div><div class="value">{passed}</div></div>
            <div class="card"><div>失败</div><div class="value">{failed}</div></div>
            <div class="card"><div>错误</div><div class="value">{errors}</div></div>
        </div>
        <table>
            <tr><th>接口</th><th>方法</th><th>路径</th><th>状态</th><th>状态码</th><th>响应时间</th></tr>
            {self._generate_report_rows(test_results.get("test_details", []))}
        </table>
    </div>
</body>
</html>
"""
        report_path = os.path.join(self.report_dir, f"test_report_{int(time.time())}.html")
        with open(report_path, "w", encoding="utf-8") as file:
            file.write(html_content)
        return report_path

    def build_excel_template_bytes(self) -> bytes:
        """构建 Excel 模板"""
        example_data = pd.DataFrame(
            [
                {
                    "接口名称": "用户登录",
                    "请求方法": "POST",
                    "接口路径": "/api/login",
                    "接口描述": "用户登录接口",
                    "请求头": '{"Content-Type": "application/json"}',
                    "请求参数": '{"username": "test", "password": "123456"}',
                    "期望状态码": 200,
                    "期望响应": '{"code": 0, "message": "success"}',
                },
                {
                    "接口名称": "获取用户信息",
                    "请求方法": "GET",
                    "接口路径": "/api/user/{id}",
                    "接口描述": "获取用户信息",
                    "请求头": '{"Authorization": "Bearer token"}',
                    "请求参数": '{"id": 1}',
                    "期望状态码": 200,
                    "期望响应": '{"id": 1, "name": "test"}',
                },
            ]
        )
        buffer = io.BytesIO()
        example_data.to_excel(buffer, index=False, engine="openpyxl")
        return buffer.getvalue()

    def build_json_template(self) -> str:
        """构建 JSON 模板"""
        example = {
            "base_url": "https://example.com",
            "interfaces": [
                {
                    "name": "用户登录",
                    "method": "POST",
                    "path": "/api/login",
                    "description": "用户登录接口",
                    "headers": {"Content-Type": "application/json"},
                    "body": {"username": "test", "password": "123456"},
                    "expected_status": 200,
                    "expected_response": {"code": 0, "message": "success"},
                }
            ],
        }
        return json.dumps(example, ensure_ascii=False, indent=2)

    def build_text_template(self) -> str:
        """构建文本模板"""
        return """接口名称: 用户登录
请求方法: POST
接口路径: /api/login
接口描述: 用户登录接口
请求头: {"Content-Type": "application/json"}
请求参数: {"username": "test", "password": "123456"}
期望状态码: 200
期望响应: {"code": 0, "message": "success"}
---
接口名称: 获取用户信息
请求方法: GET
接口路径: /api/user/{id}
接口描述: 获取用户信息
请求参数: {"id": 1}
期望状态码: 200
期望响应: {"id": 1, "name": "test"}"""

    def build_openapi_template(self) -> str:
        """构建 OpenAPI JSON 模板"""
        example = self._build_openapi_example()
        return json.dumps(example, ensure_ascii=False, indent=2)

    def build_openapi_yaml_template(self) -> str:
        """构建 OpenAPI YAML 模板"""
        example = self._build_openapi_example()
        try:
            import yaml  # type: ignore
        except ImportError:
            return json.dumps(example, ensure_ascii=False, indent=2)
        return yaml.safe_dump(example, allow_unicode=True, sort_keys=False)

    def build_curl_template(self) -> str:
        """构建 curl 导入模板"""
        return """curl -X POST 'https://example.com/api/login' \\
  -H 'Content-Type: application/json' \\
  -H 'Authorization: Bearer your-token' \\
  -d '{"username":"test","password":"123456"}'

curl -X GET 'https://example.com/api/user/1?verbose=true' \\
  -H 'Accept: application/json'"""

    def build_postman_template(self) -> str:
        """构建 Postman Collection 模板"""
        return json.dumps(self._build_postman_example(), ensure_ascii=False, indent=2)

    def build_har_template(self) -> str:
        """构建 HAR 模板"""
        return json.dumps(self._build_har_example(), ensure_ascii=False, indent=2)

    def build_apifox_template(self) -> str:
        """构建 Apifox 模板"""
        return json.dumps(self._build_apifox_example(), ensure_ascii=False, indent=2)

    def build_bruno_template(self) -> str:
        """构建 Bruno .bru 模板"""
        return """meta {
  name: 用户登录
  type: http
  seq: 1
}

post {
  url: https://example.com/api/login
  body: json
  auth: none
}

headers {
  Content-Type: application/json
  Authorization: Bearer your-token
}

body:json {
  {
    "username": "test",
    "password": "123456"
  }
}

tests {
  status: 200
}"""

    def build_insomnia_template(self) -> str:
        """构建 Insomnia 导出模板"""
        return json.dumps(self._build_insomnia_example(), ensure_ascii=False, indent=2)

    def build_environment_template(self) -> str:
        """构建多环境模板"""
        example = {
            "active_env": "dev",
            "environments": {
                "dev": {
                    "base_url": "https://dev.example.com",
                    "headers": {
                        "X-Env": "dev"
                    }
                },
                "staging": {
                    "base_url": "https://staging.example.com",
                    "headers": {
                        "X-Env": "staging"
                    }
                },
                "prod": {
                    "base_url": "https://example.com",
                    "headers": {
                        "X-Env": "prod"
                    }
                }
            }
        }
        return json.dumps(example, ensure_ascii=False, indent=2)

    def build_auth_template(self) -> str:
        """构建鉴权模板"""
        example = {
            "enabled": True,
            "type": "bearer",
            "header_name": "Authorization",
            "prefix": "Bearer ",
            "token": "your-token",
            "api_key_name": "X-API-Key",
            "api_key_value": "your-api-key",
            "username": "tester",
            "password": "123456",
            "custom_header_name": "X-Custom-Auth",
            "custom_header_value": "custom-auth-value"
        }
        return json.dumps(example, ensure_ascii=False, indent=2)

    def _build_openapi_example(self) -> Dict[str, Any]:
        """构建 OpenAPI 示例对象"""
        return {
            "openapi": "3.0.0",
            "info": {"title": "Sample API", "version": "1.0.0"},
            "servers": [{"url": "https://example.com"}],
            "paths": {
                "/api/login": {
                    "post": {
                        "summary": "用户登录",
                        "requestBody": {
                            "required": True,
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "required": ["username", "password"],
                                        "properties": {
                                            "username": {"type": "string", "example": "test"},
                                            "password": {"type": "string", "example": "123456"},
                                        },
                                    }
                                }
                            },
                        },
                        "responses": {
                            "200": {
                                "description": "success",
                                "content": {
                                    "application/json": {
                                        "schema": {
                                            "type": "object",
                                            "properties": {
                                                "code": {"type": "integer", "example": 0},
                                                "message": {"type": "string", "example": "success"},
                                            },
                                        }
                                    }
                                },
                            }
                        },
                    }
                }
            },
        }

    def _build_postman_example(self) -> Dict[str, Any]:
        """构建 Postman Collection 示例对象"""
        return {
            "info": {
                "name": "接口自动化测试示例集合",
                "_postman_id": "sample-collection-id",
                "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
            },
            "variable": [
                {"key": "baseUrl", "value": "https://example.com"},
                {"key": "token", "value": "your-token"},
            ],
            "item": [
                {
                    "name": "用户登录",
                    "request": {
                        "method": "POST",
                        "header": [
                            {"key": "Content-Type", "value": "application/json"},
                        ],
                        "body": {
                            "mode": "raw",
                            "raw": '{\n  "username": "test",\n  "password": "123456"\n}',
                            "options": {"raw": {"language": "json"}},
                        },
                        "url": {
                            "raw": "{{baseUrl}}/api/login",
                            "host": ["{{baseUrl}}"],
                            "path": ["api", "login"],
                        },
                        "description": "用户登录接口",
                    },
                    "response": [
                        {
                            "name": "success",
                            "status": "OK",
                            "code": 200,
                            "body": '{\n  "code": 0,\n  "message": "success"\n}',
                        }
                    ],
                },
                {
                    "name": "获取用户信息",
                    "request": {
                        "method": "GET",
                        "header": [
                            {"key": "Authorization", "value": "Bearer {{token}}"},
                        ],
                        "url": {
                            "raw": "{{baseUrl}}/api/user/1?verbose=true",
                            "host": ["{{baseUrl}}"],
                            "path": ["api", "user", "1"],
                            "query": [
                                {"key": "verbose", "value": "true"},
                            ],
                        },
                        "description": "获取用户信息接口",
                    },
                },
            ],
        }

    def _build_har_example(self) -> Dict[str, Any]:
        """构建 HAR 示例对象"""
        return {
            "log": {
                "version": "1.2",
                "creator": {"name": "Codex", "version": "1.0"},
                "entries": [
                    {
                        "startedDateTime": "2026-04-03T09:00:00.000Z",
                        "time": 120,
                        "request": {
                            "method": "POST",
                            "url": "https://example.com/api/login",
                            "httpVersion": "HTTP/1.1",
                            "headers": [
                                {"name": "Content-Type", "value": "application/json"},
                            ],
                            "queryString": [],
                            "postData": {
                                "mimeType": "application/json",
                                "text": '{"username":"test","password":"123456"}',
                            },
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "httpVersion": "HTTP/1.1",
                            "headers": [
                                {"name": "Content-Type", "value": "application/json"},
                            ],
                            "content": {
                                "size": 36,
                                "mimeType": "application/json",
                                "text": '{"code":0,"message":"success"}',
                            },
                        },
                        "comment": "用户登录",
                    },
                    {
                        "startedDateTime": "2026-04-03T09:00:02.000Z",
                        "time": 80,
                        "request": {
                            "method": "GET",
                            "url": "https://example.com/api/user/1?verbose=true",
                            "httpVersion": "HTTP/1.1",
                            "headers": [
                                {"name": "Accept", "value": "application/json"},
                            ],
                            "queryString": [
                                {"name": "verbose", "value": "true"},
                            ],
                        },
                        "response": {
                            "status": 200,
                            "statusText": "OK",
                            "httpVersion": "HTTP/1.1",
                            "headers": [
                                {"name": "Content-Type", "value": "application/json"},
                            ],
                            "content": {
                                "size": 28,
                                "mimeType": "application/json",
                                "text": '{"id":1,"name":"test-user"}',
                            },
                        },
                        "comment": "获取用户信息",
                    },
                ],
            }
        }

    def _build_apifox_example(self) -> Dict[str, Any]:
        """构建 Apifox 示例对象"""
        example = self._build_openapi_example()
        example["info"]["title"] = "Apifox Sample API"
        example["info"]["description"] = "Apifox 导出示例，结构兼容 OpenAPI"
        example["x-apifox"] = {
            "projectId": "sample-project-id",
            "folderId": "sample-folder-id",
            "exportedAt": "2026-04-03T00:00:00Z",
        }
        return example

    def _build_insomnia_example(self) -> Dict[str, Any]:
        """构建 Insomnia 导出示例对象"""
        return {
            "_type": "export",
            "__export_format": 4,
            "__export_date": "2026-04-03T00:00:00.000Z",
            "__export_source": "insomnia.desktop.app:v10.0.0",
            "resources": [
                {
                    "_id": "wrk_sample",
                    "_type": "workspace",
                    "name": "接口自动化测试示例",
                },
                {
                    "_id": "env_sample",
                    "_type": "environment",
                    "parentId": "wrk_sample",
                    "name": "Base Environment",
                    "data": {
                        "base_url": "https://example.com",
                        "token": "your-token",
                    },
                },
                {
                    "_id": "req_login",
                    "_type": "request",
                    "parentId": "wrk_sample",
                    "name": "用户登录",
                    "method": "POST",
                    "url": "{{ _.base_url }}/api/login",
                    "headers": [
                        {"name": "Content-Type", "value": "application/json"},
                        {"name": "Authorization", "value": "Bearer {{ _.token }}"},
                    ],
                    "body": {
                        "mimeType": "application/json",
                        "text": '{\n  "username": "test",\n  "password": "123456"\n}',
                    },
                    "description": "用户登录接口",
                },
                {
                    "_id": "res_login",
                    "_type": "response",
                    "parentId": "req_login",
                    "statusCode": 200,
                    "body": '{\n  "code": 0,\n  "message": "success"\n}',
                },
                {
                    "_id": "req_user",
                    "_type": "request",
                    "parentId": "wrk_sample",
                    "name": "获取用户信息",
                    "method": "GET",
                    "url": "{{ _.base_url }}/api/user/1?verbose=true",
                    "headers": [
                        {"name": "Accept", "value": "application/json"},
                    ],
                    "description": "获取用户信息接口",
                },
            ],
        }

    def _normalize_interface(self, raw_interface: Dict[str, Any]) -> Dict[str, Any]:
        """归一化接口定义"""
        if not isinstance(raw_interface, dict):
            raise ValueError("接口定义必须是对象")

        path = self._clean_text(raw_interface.get("path") or raw_interface.get("url"))
        if not path:
            raise ValueError("接口路径不能为空")

        method = self._clean_text(raw_interface.get("method")) or "GET"
        method = method.upper()
        if method not in self.HTTP_METHODS:
            method = "GET"

        headers = self._ensure_mapping(raw_interface.get("headers"))
        parameters = raw_interface.get("parameters")
        path_params = self._ensure_mapping(raw_interface.get("path_params"))
        query_params = self._ensure_mapping(raw_interface.get("query_params"))
        body = raw_interface.get("body")
        if body is None and raw_interface.get("request_body") is not None:
            body = raw_interface.get("request_body")

        if body is None and raw_interface.get("data") is not None:
            body = raw_interface.get("data")

        if parameters is None and raw_interface.get("请求参数") is not None:
            parameters = raw_interface.get("请求参数")

        path_placeholders = set(re.findall(r"\{([^}]+)\}", path))
        if isinstance(parameters, dict):
            temp_parameters = deepcopy(parameters)
            for key in list(temp_parameters.keys()):
                if key in path_placeholders and key not in path_params:
                    path_params[key] = temp_parameters.pop(key)

            if method == "GET":
                if not query_params:
                    query_params = temp_parameters
            elif body is None and not query_params:
                body = temp_parameters

        if parameters is None:
            if method == "GET":
                parameters = {**path_params, **query_params}
            elif isinstance(body, dict):
                parameters = {**path_params, **query_params, **body}
            elif body is not None:
                parameters = body
            else:
                parameters = {**path_params, **query_params}

        request_format = self._normalize_request_format(
            raw_interface.get("request_format")
            or raw_interface.get("body_type")
            or self._infer_request_format(headers, body)
        )

        expected_response = raw_interface.get("expected_response")
        if isinstance(expected_response, str):
            parsed_expected = self.parse_json_field(expected_response)
            expected_response = parsed_expected if parsed_expected != "" else expected_response

        tags = raw_interface.get("tags") or []
        if isinstance(tags, str):
            tags = [item.strip() for item in tags.split(",") if item.strip()]
        elif not isinstance(tags, list):
            tags = []

        return {
            "name": self._clean_text(raw_interface.get("name")) or f"{method} {path}",
            "method": method,
            "path": path,
            "description": self._clean_text(raw_interface.get("description")),
            "headers": headers,
            "parameters": parameters,
            "path_params": path_params,
            "query_params": query_params,
            "body": body,
            "expected_status": self._coerce_int(raw_interface.get("expected_status"), 200),
            "expected_response": expected_response if expected_response is not None else {},
            "request_format": request_format,
            "tags": tags,
            "source": self._clean_text(raw_interface.get("source")),
        }

    def _prepare_cases(self, interfaces: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """准备生成和执行时使用的标准用例"""
        cases: List[Dict[str, Any]] = []
        for index, interface in enumerate(interfaces, start=1):
            case = self._normalize_interface(interface)
            case_id = f"case_{index:03d}"
            case["case_id"] = case_id
            case["test_name"] = self._build_test_name(case_id, case["name"])
            cases.append(case)
        return cases

    def _render_pytest_file(self, cases: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        helpers = self._build_runtime_helpers(config, cases)
        tests = []
        for case in cases:
            tests.append(
                f"""
def {case["test_name"]}(api_session):
    execute_case(api_session, CASE_INDEX["{case["case_id"]}"])
""".rstrip()
            )

        return "\n\n".join(
            [
                '"""自动生成的接口测试脚本 - pytest"""',
                "import pytest",
                helpers,
                "",
                '@pytest.fixture(scope="session")',
                "def api_session():",
                "    session = requests.Session()",
                "    yield session",
                "    session.close()",
                "",
                "\n\n".join(tests),
                "",
            ]
        )

    def _render_unittest_file(self, cases: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        helpers = self._build_runtime_helpers(config, cases)
        methods = []
        for case in cases:
            methods.append(
                f"""
    def {case["test_name"]}(self):
        execute_case(self.session, CASE_INDEX["{case["case_id"]}"])
""".rstrip()
            )

        return "\n\n".join(
            [
                '"""自动生成的接口测试脚本 - unittest"""',
                "import unittest",
                helpers,
                "",
                "class GeneratedApiTests(unittest.TestCase):",
                "    @classmethod",
                "    def setUpClass(cls):",
                "        cls.session = requests.Session()",
                "",
                "    @classmethod",
                "    def tearDownClass(cls):",
                "        cls.session.close()",
                "",
                "\n\n".join(methods),
                "",
                'if __name__ == "__main__":',
                "    unittest.main(verbosity=2)",
                "",
            ]
        )

    def _render_requests_script(self, cases: List[Dict[str, Any]], config: Dict[str, Any]) -> str:
        helpers = self._build_runtime_helpers(config, cases)
        return "\n\n".join(
            [
                '"""自动生成的接口执行脚本 - requests"""',
                "import sys",
                helpers,
                "",
                "def main():",
                "    session = requests.Session()",
                "    failed = 0",
                "    try:",
                "        for case in CASES:",
                "            try:",
                "                execute_case(session, case)",
                "            except Exception:",
                "                failed += 1",
                "    finally:",
                "        session.close()",
                "    return 1 if failed else 0",
                "",
                'if __name__ == "__main__":',
                "    sys.exit(main())",
                "",
            ]
        )

    def _build_runtime_helpers(self, config: Dict[str, Any], cases: List[Dict[str, Any]]) -> str:
        template = """
import json
import os
import re
import time
from copy import deepcopy

import requests

CONFIG = json.loads(r'''__CONFIG_JSON__''')
CASES = json.loads(r'''__CASES_JSON__''')
CASE_INDEX = {case["case_id"]: case for case in CASES}


def clone_value(value):
    return deepcopy(value)


def get_current_env_name():
    env_name = os.environ.get("API_TEST_ENV") or CONFIG.get("active_env") or "custom"
    environments = CONFIG.get("environments", {})
    if env_name in environments:
        return env_name
    if CONFIG.get("active_env") in environments:
        return CONFIG.get("active_env")
    return next(iter(environments.keys()), "custom")


def get_env_config():
    env_name = get_current_env_name()
    env_data = clone_value((CONFIG.get("environments") or {}).get(env_name) or {})
    env_data.setdefault("base_url", CONFIG.get("base_url", ""))
    env_data.setdefault("headers", clone_value(CONFIG.get("default_headers") or {}))
    return env_name, env_data


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
    placeholders = set(re.findall(r"\\{([^}]+)\\}", path or ""))
    for name in placeholders:
        if name not in path_params:
            if isinstance(query_params, dict) and name in query_params:
                path_params[name] = query_params.pop(name)
            elif isinstance(body, dict) and name in body:
                path_params[name] = body.pop(name)
    return path_params, query_params, body


def resolve_request_format(case, headers, body):
    override = CONFIG.get("request_format", "auto")
    if override and override != "auto":
        return override
    case_format = case.get("request_format", "auto")
    if case_format and case_format != "auto":
        return case_format
    content_type = str(headers.get("Content-Type") or headers.get("content-type") or "").lower()
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


def build_detail(case, status, response, response_time, url, error, assertions, env_name, headers):
    return {
        "case_id": case.get("case_id"),
        "test_name": case.get("test_name"),
        "name": case.get("name"),
        "method": case.get("method"),
        "path": case.get("path"),
        "status": status,
        "status_code": response.status_code if response is not None else 0,
        "response_time": round(response_time, 4),
        "headers": headers or case.get("headers") or {},
        "parameters": case.get("parameters"),
        "response_body": response.text if response is not None else "",
        "error": error or "",
        "assertions": assertions or [],
        "url": url,
        "environment": env_name,
    }


def emit_case_result(detail):
    print("CASE_RESULT::" + json.dumps(detail, ensure_ascii=False))


def send_request(session, case):
    path_params, query_params, body = merge_request_parts(case)
    env_name, env_config = get_env_config()
    headers = clone_value(env_config.get("headers") or {})
    headers.update(clone_value(case.get("headers") or {}))
    method = str(case.get("method", "GET")).upper()
    request_format = resolve_request_format(case, headers, body)
    url = build_url(env_config.get("base_url") or CONFIG.get("base_url", ""), case.get("path", ""), path_params)
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
            return session.request(**request_kwargs), url, env_name, headers
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
    env_name = ""
    headers = clone_value(case.get("headers") or {})
    assertions = []
    try:
        response, url, env_name, headers = send_request(session, case)
        assertions, failures = build_assertions(case, response)
        if failures:
            raise AssertionError("; ".join(failures))
        detail = build_detail(case, "passed", response, time.time() - started_at, url, "", assertions, env_name, headers)
        emit_case_result(detail)
        return detail
    except AssertionError as exc:
        detail = build_detail(case, "failed", response, time.time() - started_at, url, str(exc), assertions, env_name, headers)
        emit_case_result(detail)
        raise
    except Exception as exc:
        detail = build_detail(case, "error", response, time.time() - started_at, url, str(exc), assertions, env_name, headers)
        emit_case_result(detail)
        raise
"""
        return (
            template.replace("__CONFIG_JSON__", json.dumps(config, ensure_ascii=False))
            .replace("__CASES_JSON__", json.dumps(cases, ensure_ascii=False))
            .strip()
        )

    def _run_command(self, command: List[str], mode: str) -> Dict[str, Any]:
        """运行子进程并解析结构化输出"""
        start_time = time.time()
        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                cwd=self.test_dir,
            )
        except Exception as exc:
            return self._build_runner_error(str(exc))

        parsed = self._parse_execution_output(result.stdout, result.stderr, result.returncode, mode)
        parsed["start_time"] = start_time
        parsed["end_time"] = time.time()
        parsed["duration"] = parsed["end_time"] - parsed["start_time"]
        return parsed

    def _parse_execution_output(
        self,
        stdout: str,
        stderr: str,
        return_code: int,
        mode: str,
    ) -> Dict[str, Any]:
        """解析执行输出"""
        manifest = self._load_manifest()
        cases = manifest.get("cases", [])
        results_by_case: Dict[str, Dict[str, Any]] = {}
        combined_output = "\n".join(part for part in [stdout, stderr] if part).strip()

        for line in (stdout or "").splitlines():
            if "CASE_RESULT::" not in line:
                continue
            raw_payload = line.split("CASE_RESULT::", 1)[1].strip()
            try:
                payload = json.loads(raw_payload)
            except json.JSONDecodeError:
                continue
            case_id = payload.get("case_id")
            if case_id:
                results_by_case[case_id] = payload

        test_details: List[Dict[str, Any]] = []
        for case in cases:
            case_id = case.get("case_id")
            detail = results_by_case.get(case_id)
            if detail:
                detail = self._merge_case_detail(case, detail)
            else:
                detail = self._build_missing_case_detail(case, combined_output, return_code)
            test_details.append(detail)

        if not test_details and results_by_case:
            test_details = list(results_by_case.values())

        passed = sum(1 for detail in test_details if detail.get("status") == "passed")
        failed = sum(1 for detail in test_details if detail.get("status") == "failed")
        errors = sum(1 for detail in test_details if detail.get("status") == "error")
        total = len(test_details)

        if total == 0 and return_code != 0:
            return self._build_runner_error(
                combined_output or f"{mode} 执行失败，退出码 {return_code}",
                output=combined_output,
            )

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "success": failed == 0 and errors == 0 and return_code == 0,
            "test_details": test_details,
            "output": combined_output,
        }

    def _load_manifest(self) -> Dict[str, Any]:
        """读取生成时保存的 manifest"""
        manifest_path = os.path.join(self.test_dir, "interface_manifest.json")
        if not os.path.exists(manifest_path):
            return {}
        try:
            with open(manifest_path, "r", encoding="utf-8") as file:
                return json.load(file)
        except Exception:
            return {}

    def _merge_case_detail(self, case: Dict[str, Any], detail: Dict[str, Any]) -> Dict[str, Any]:
        """补齐单接口执行结果"""
        merged = {
            "case_id": case.get("case_id"),
            "test_name": case.get("test_name"),
            "name": case.get("name"),
            "method": case.get("method"),
            "path": case.get("path"),
            "status": detail.get("status", "error"),
            "status_code": detail.get("status_code", 0),
            "response_time": max(float(detail.get("response_time", 0)), 0.0),
            "headers": detail.get("headers") or case.get("headers", {}),
            "parameters": detail.get("parameters")
            if detail.get("parameters") is not None
            else case.get("parameters"),
            "response_body": detail.get("response_body", ""),
            "error": detail.get("error", ""),
            "assertions": detail.get("assertions", []),
            "url": detail.get("url", ""),
            "environment": detail.get("environment", ""),
        }
        return merged

    def _build_missing_case_detail(
        self,
        case: Dict[str, Any],
        combined_output: str,
        return_code: int,
    ) -> Dict[str, Any]:
        """为未产出结构化日志的用例构造兜底结果"""
        message = combined_output.strip() if combined_output else "测试进程未输出结构化结果"
        if len(message) > 800:
            message = message[-800:]
        return {
            "case_id": case.get("case_id"),
            "test_name": case.get("test_name"),
            "name": case.get("name"),
            "method": case.get("method"),
            "path": case.get("path"),
            "status": "error" if return_code != 0 else "failed",
            "status_code": 0,
            "response_time": 0.0,
            "headers": case.get("headers", {}),
            "parameters": case.get("parameters"),
            "response_body": "",
            "error": message or "未知错误",
            "assertions": [],
            "url": "",
            "environment": "",
        }

    def _build_runner_error(self, message: str, output: str = "") -> Dict[str, Any]:
        """构造执行失败结果"""
        return {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "errors": 1,
            "success": False,
            "error_message": message,
            "output": output,
            "test_details": [],
        }

    def _generate_report_rows(self, test_details: List[Dict[str, Any]]) -> str:
        rows = []
        for detail in test_details:
            rows.append(
                "<tr>"
                f"<td>{detail.get('name', '未命名接口')}</td>"
                f"<td>{detail.get('method', 'GET')}</td>"
                f"<td>{detail.get('path', '')}</td>"
                f"<td>{detail.get('status', 'unknown')}</td>"
                f"<td>{detail.get('status_code', 0)}</td>"
                f"<td>{detail.get('response_time', 0):.2f}s</td>"
                "</tr>"
            )
        return "".join(rows) or "<tr><td colspan='6'>暂无测试详情</td></tr>"

    def _parse_curl_block(self, block: str) -> Dict[str, Any]:
        """解析 curl 命令"""
        normalized = re.sub(r"\\\s*\n", " ", block).strip()
        parts = shlex.split(normalized)
        if not parts or parts[0].lower() != "curl":
            raise ValueError("curl 文本格式不正确")

        method = "GET"
        url = ""
        headers: Dict[str, Any] = {}
        body: Any = None
        request_format = "auto"

        index = 1
        while index < len(parts):
            token = parts[index]
            if token in {"-X", "--request"} and index + 1 < len(parts):
                method = parts[index + 1].upper()
                index += 2
                continue
            if token in {"-H", "--header"} and index + 1 < len(parts):
                header = parts[index + 1]
                if ":" in header:
                    key, value = header.split(":", 1)
                    headers[key.strip()] = value.strip()
                index += 2
                continue
            if token in {"-d", "--data", "--data-raw", "--data-binary", "--form", "-F"} and index + 1 < len(parts):
                raw_value = parts[index + 1]
                if token in {"--form", "-F"}:
                    request_format = "form"
                else:
                    request_format = "data_json"
                body = self._parse_loose_value(raw_value)
                index += 2
                continue
            if token.startswith(("http://", "https://")):
                url = token
            index += 1

        if not url:
            raise ValueError("curl 命令中缺少 URL")

        parsed_url = urlparse(url)
        query_params = dict(parse_qsl(parsed_url.query, keep_blank_values=True))
        if isinstance(body, str):
            content_type = str(headers.get("Content-Type") or headers.get("content-type") or "").lower()
            if "application/json" in content_type:
                try:
                    body = json.loads(body)
                except json.JSONDecodeError:
                    pass
            elif "=" in body and "&" in body:
                body = dict(parse_qsl(body, keep_blank_values=True))
                request_format = "form"

        return self._normalize_interface(
            {
                "name": f"{method} {parsed_url.path or '/'}",
                "method": method,
                "path": url,
                "headers": headers,
                "query_params": query_params,
                "body": body,
                "expected_status": 200,
                "expected_response": {},
                "request_format": request_format,
                "source": "text",
            }
        )

    def _parse_structured_text_block(self, block: str) -> Dict[str, Any]:
        """解析结构化文本块"""
        key_map = {
            "接口名称": "name",
            "name": "name",
            "请求方法": "method",
            "method": "method",
            "接口路径": "path",
            "路径": "path",
            "path": "path",
            "url": "path",
            "接口描述": "description",
            "description": "description",
            "请求头": "headers",
            "headers": "headers",
            "请求参数": "parameters",
            "parameters": "parameters",
            "query_params": "query_params",
            "query": "query_params",
            "path_params": "path_params",
            "请求体": "body",
            "body": "body",
            "期望状态码": "expected_status",
            "expected_status": "expected_status",
            "期望响应": "expected_response",
            "expected_response": "expected_response",
            "tags": "tags",
            "标签": "tags",
            "请求格式": "request_format",
            "request_format": "request_format",
        }

        raw_interface: Dict[str, Any] = {}
        for raw_line in block.splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue

            method_match = re.match(r"^(GET|POST|PUT|PATCH|DELETE|HEAD|OPTIONS)\s+(.+)$", line, re.IGNORECASE)
            if method_match:
                raw_interface["method"] = method_match.group(1).upper()
                raw_interface["path"] = method_match.group(2).strip()
                continue

            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            normalized_key = key_map.get(key.strip()) or key_map.get(key.strip().lower())
            if not normalized_key:
                continue

            parsed_value = self._parse_loose_value(value.strip())
            if normalized_key == "tags" and isinstance(parsed_value, str):
                parsed_value = [item.strip() for item in parsed_value.split(",") if item.strip()]
            raw_interface[normalized_key] = parsed_value

        return self._normalize_interface(raw_interface)

    def _extract_openapi_expected_response(
        self,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
    ) -> Tuple[int, Any]:
        """解析 OpenAPI 期望状态码和响应结构"""
        responses = operation.get("responses", {})
        if not isinstance(responses, dict):
            return 200, {}

        selected_code = "200"
        for status_code in responses.keys():
            status_text = str(status_code).lower()
            if status_text.startswith("2"):
                selected_code = str(status_code)
                break
            if status_text == "default":
                selected_code = str(status_code)

        expected_status = 200
        if selected_code.isdigit():
            expected_status = int(selected_code)

        response_def = responses.get(selected_code, {})
        if not isinstance(response_def, dict):
            return expected_status, {}

        if "content" in response_def and isinstance(response_def["content"], dict):
            content_type, content_def = self._pick_openapi_content(response_def["content"])
            if content_def:
                if "example" in content_def:
                    return expected_status, deepcopy(content_def["example"])
                if "examples" in content_def and isinstance(content_def["examples"], dict):
                    first_example = next(iter(content_def["examples"].values()), {})
                    if isinstance(first_example, dict) and "value" in first_example:
                        return expected_status, deepcopy(first_example["value"])
                if "schema" in content_def:
                    return expected_status, self._schema_to_example(content_def["schema"], spec)

        if "schema" in response_def:
            return expected_status, self._schema_to_example(response_def["schema"], spec)

        return expected_status, {}

    def _extract_openapi_parameter_value(self, parameter: Dict[str, Any], spec: Dict[str, Any]) -> Any:
        """提取参数默认值"""
        if "$ref" in parameter:
            parameter = self._resolve_ref(spec, parameter["$ref"])
        if "example" in parameter:
            return deepcopy(parameter["example"])
        if "schema" in parameter:
            return self._schema_to_example(parameter["schema"], spec)
        if parameter.get("enum"):
            return deepcopy(parameter["enum"][0])
        if "default" in parameter:
            return deepcopy(parameter["default"])
        param_type = parameter.get("type", "string")
        if param_type in {"integer", "number"}:
            return parameter.get("minimum", 1)
        if param_type == "boolean":
            return True
        return f"{parameter.get('name', 'value')}_sample"

    def _extract_openapi_request_body(
        self,
        spec: Dict[str, Any],
        operation: Dict[str, Any],
        merged_params: List[Dict[str, Any]],
    ) -> Tuple[Any, str, Dict[str, Any]]:
        """提取 OpenAPI 请求体"""
        request_body = operation.get("requestBody")
        if isinstance(request_body, dict) and "$ref" in request_body:
            request_body = self._resolve_ref(spec, request_body["$ref"])

        if isinstance(request_body, dict):
            content = request_body.get("content", {})
            if isinstance(content, dict):
                content_type, content_def = self._pick_openapi_content(content)
                if content_def:
                    example = content_def.get("example")
                    if example is None and isinstance(content_def.get("examples"), dict):
                        first_example = next(iter(content_def["examples"].values()), {})
                        if isinstance(first_example, dict):
                            example = first_example.get("value")
                    if example is None:
                        example = self._schema_to_example(content_def.get("schema", {}), spec)
                    return example, self._infer_request_format({"Content-Type": content_type}, example), {
                        "Content-Type": content_type
                    }

        body_param = None
        form_body: Dict[str, Any] = {}
        for parameter in merged_params:
            if not isinstance(parameter, dict):
                continue
            if parameter.get("in") == "body":
                body_param = parameter
            elif parameter.get("in") == "formData":
                form_body[parameter.get("name")] = self._extract_openapi_parameter_value(parameter, spec)

        if body_param:
            body_param = self._resolve_ref(spec, body_param["$ref"]) if "$ref" in body_param else body_param
            schema = body_param.get("schema", {})
            example = self._schema_to_example(schema, spec)
            return example, "json", {"Content-Type": "application/json"}

        if form_body:
            return form_body, "form", {"Content-Type": "application/x-www-form-urlencoded"}

        return None, "auto", {}

    def _merge_openapi_parameters(self, path_params: Any, op_params: Any) -> List[Dict[str, Any]]:
        """合并 path 级与 operation 级参数"""
        merged: Dict[Tuple[str, str], Dict[str, Any]] = {}
        for group in [path_params or [], op_params or []]:
            for parameter in group:
                if not isinstance(parameter, dict):
                    continue
                name = parameter.get("name")
                location = parameter.get("in")
                if name and location:
                    merged[(name, location)] = parameter
        return list(merged.values())

    def _pick_openapi_content(self, content: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
        """选择最合适的 content-type"""
        preferred_types = [
            "application/json",
            "application/x-www-form-urlencoded",
            "multipart/form-data",
            "text/plain",
        ]
        for content_type in preferred_types:
            if content_type in content:
                return content_type, content[content_type]
        first_type = next(iter(content.keys()), "")
        return first_type, content.get(first_type, {})

    def _schema_to_example(self, schema: Any, spec: Dict[str, Any], depth: int = 0) -> Any:
        """根据 schema 生成示例数据"""
        if depth > 6:
            return {}
        if not isinstance(schema, dict):
            return {}

        if "$ref" in schema:
            return self._schema_to_example(self._resolve_ref(spec, schema["$ref"]), spec, depth + 1)
        if "example" in schema:
            return deepcopy(schema["example"])
        if "default" in schema:
            return deepcopy(schema["default"])
        if schema.get("enum"):
            return deepcopy(schema["enum"][0])
        if schema.get("oneOf"):
            return self._schema_to_example(schema["oneOf"][0], spec, depth + 1)
        if schema.get("anyOf"):
            return self._schema_to_example(schema["anyOf"][0], spec, depth + 1)
        if schema.get("allOf"):
            merged_object: Dict[str, Any] = {}
            for item in schema["allOf"]:
                value = self._schema_to_example(item, spec, depth + 1)
                if isinstance(value, dict):
                    merged_object.update(value)
            return merged_object

        schema_type = schema.get("type")
        if schema_type == "object" or "properties" in schema:
            properties = schema.get("properties", {})
            return {
                key: self._schema_to_example(value, spec, depth + 1)
                for key, value in properties.items()
            }
        if schema_type == "array":
            return [self._schema_to_example(schema.get("items", {}), spec, depth + 1)]
        if schema_type in {"integer", "number"}:
            return schema.get("minimum", 1)
        if schema_type == "boolean":
            return True
        if schema.get("format") == "date-time":
            return "2026-01-01T00:00:00Z"
        if schema.get("format") == "date":
            return "2026-01-01"
        return "sample"

    def _resolve_ref(self, spec: Dict[str, Any], ref: str) -> Dict[str, Any]:
        """解析 schema/parameter 引用"""
        if not ref.startswith("#/"):
            return {}
        node: Any = spec
        for part in ref.lstrip("#/").split("/"):
            if not isinstance(node, dict):
                return {}
            node = node.get(part)
        return node if isinstance(node, dict) else {}

    def _detect_openapi_base_url(self, spec: Dict[str, Any]) -> str:
        """检测文档中的基础地址"""
        servers = spec.get("servers")
        if isinstance(servers, list) and servers:
            first_server = servers[0]
            if isinstance(first_server, dict):
                return self._clean_text(first_server.get("url"))

        host = self._clean_text(spec.get("host"))
        if host:
            schemes = spec.get("schemes") or ["https"]
            scheme = schemes[0] if isinstance(schemes, list) and schemes else "https"
            base_path = self._clean_text(spec.get("basePath"))
            return f"{scheme}://{host}{base_path}"
        return ""

    def _extract_postman_variables(self, collection: Dict[str, Any]) -> Dict[str, str]:
        """提取 Postman 变量"""
        variables: Dict[str, str] = {}
        for variable in collection.get("variable", []):
            if not isinstance(variable, dict):
                continue
            key = self._clean_text(variable.get("key"))
            if key:
                variables[key] = self._clean_text(variable.get("value"))
        return variables

    def _extract_postman_base_url(self, collection: Dict[str, Any], variables: Dict[str, str]) -> str:
        """提取 Postman 基础地址"""
        for key in ["baseUrl", "baseURL", "host", "api_host"]:
            if variables.get(key):
                return self._normalize_base_url(variables[key])

        for item in collection.get("item", []):
            request = item.get("request") if isinstance(item, dict) else None
            if not isinstance(request, dict):
                continue
            raw_url = self._extract_postman_raw_url(request.get("url"), variables)
            base_url, _, _ = self._split_url_parts(raw_url)
            if base_url:
                return base_url
        return ""

    def _postman_item_to_interface(
        self,
        item: Dict[str, Any],
        request: Dict[str, Any],
        parents: List[str],
        variables: Dict[str, str],
    ) -> Optional[Dict[str, Any]]:
        """将 Postman item 转成统一接口定义"""
        method = self._clean_text(request.get("method")) or "GET"
        raw_url = self._extract_postman_raw_url(request.get("url"), variables)
        if not raw_url:
            return None

        base_url, path, query_params = self._split_url_parts(raw_url)
        if base_url and not self.last_parse_meta.get("detected_base_url"):
            self.last_parse_meta["detected_base_url"] = base_url
        elif self.last_parse_meta.get("detected_base_url") and base_url and base_url != self.last_parse_meta["detected_base_url"]:
            path = raw_url

        headers = self._headers_list_to_dict(request.get("header"), variables)
        request_body, request_format = self._extract_postman_request_body(request.get("body"), headers, variables)

        if not query_params and isinstance(request.get("url"), dict):
            query_params = self._name_value_list_to_dict(request["url"].get("query"), variables)

        responses = item.get("response", [])
        expected_status = 200
        expected_response: Any = {}
        if isinstance(responses, list) and responses:
            first_response = responses[0] if isinstance(responses[0], dict) else {}
            expected_status = self._coerce_int(first_response.get("code"), 200)
            response_body = self._clean_text(first_response.get("body"))
            parsed_body = self.parse_json_field(response_body) if response_body else {}
            expected_response = parsed_body if parsed_body not in ("", None) else {}

        name_parts = parents + ([self._clean_text(item.get("name"))] if self._clean_text(item.get("name")) else [])
        description = request.get("description") or item.get("description")

        raw_interface = {
            "name": " / ".join(name_parts) if name_parts else f"{method.upper()} {path}",
            "method": method.upper(),
            "path": path or raw_url,
            "description": self._extract_description_text(description),
            "headers": headers,
            "query_params": query_params,
            "body": request_body,
            "expected_status": expected_status,
            "expected_response": expected_response,
            "request_format": request_format,
            "source": "postman",
        }
        return self._normalize_interface(raw_interface)

    def _extract_postman_raw_url(self, url_data: Any, variables: Dict[str, str]) -> str:
        """提取 Postman 请求 URL"""
        if isinstance(url_data, str):
            return self._replace_postman_variables(url_data, variables)

        if not isinstance(url_data, dict):
            return ""

        raw_url = self._clean_text(url_data.get("raw"))
        if raw_url:
            return self._replace_postman_variables(raw_url, variables)

        host_data = url_data.get("host", [])
        path_data = url_data.get("path", [])
        protocol = self._clean_text(url_data.get("protocol")) or "https"

        if isinstance(host_data, list):
            host = ".".join(self._replace_postman_variables(str(part), variables) for part in host_data if str(part))
        else:
            host = self._replace_postman_variables(str(host_data), variables)

        if isinstance(path_data, list):
            path = "/" + "/".join(self._replace_postman_variables(str(part), variables) for part in path_data if str(part))
        else:
            path = self._replace_postman_variables(str(path_data), variables)

        query = self._name_value_list_to_dict(url_data.get("query"), variables)
        query_suffix = ""
        if query:
            query_suffix = "?" + "&".join(f"{key}={value}" for key, value in query.items())

        if host.startswith("http://") or host.startswith("https://"):
            return f"{host.rstrip('/')}{path}{query_suffix}"
        if host:
            return f"{protocol}://{host}{path}{query_suffix}"
        return f"{path}{query_suffix}"

    def _extract_postman_request_body(
        self,
        body_data: Any,
        headers: Dict[str, Any],
        variables: Dict[str, str],
    ) -> Tuple[Any, str]:
        """提取 Postman 请求体"""
        if not isinstance(body_data, dict):
            return None, "auto"

        mode = self._clean_text(body_data.get("mode"))
        if mode == "raw":
            raw_text = self._replace_postman_variables(self._clean_text(body_data.get("raw")), variables)
            language = self._clean_text(((body_data.get("options") or {}).get("raw") or {}).get("language")).lower()
            if language == "json" or "application/json" in str(headers.get("Content-Type") or "").lower():
                try:
                    return json.loads(raw_text), "json"
                except json.JSONDecodeError:
                    return raw_text, "raw"
            return raw_text, "raw"

        if mode in {"urlencoded", "formdata"}:
            body = self._name_value_list_to_dict(body_data.get(mode), variables)
            return body, "form"

        if mode == "graphql":
            graphql_data = body_data.get("graphql", {})
            return {
                "query": self._replace_postman_variables(self._clean_text(graphql_data.get("query")), variables),
                "variables": graphql_data.get("variables") or {},
            }, "json"

        return None, "auto"

    def _extract_har_request_body(self, request: Dict[str, Any], headers: Dict[str, Any]) -> Tuple[Any, str]:
        """提取 HAR 请求体"""
        post_data = request.get("postData", {})
        if not isinstance(post_data, dict):
            return None, "auto"

        mime_type = self._clean_text(post_data.get("mimeType")).lower()
        params = post_data.get("params")
        if isinstance(params, list) and params:
            body = self._name_value_list_to_dict(params)
            return body, "form"

        text = self._clean_text(post_data.get("text"))
        if not text:
            return None, "auto"

        if "application/json" in mime_type or "application/json" in str(headers.get("Content-Type") or "").lower():
            try:
                return json.loads(text), "json"
            except json.JSONDecodeError:
                return text, "raw"

        if "application/x-www-form-urlencoded" in mime_type:
            return dict(parse_qsl(text, keep_blank_values=True)), "form"

        return text, "raw"

    def _extract_har_response_example(self, response: Dict[str, Any]) -> Any:
        """提取 HAR 响应示例"""
        content = response.get("content", {})
        if not isinstance(content, dict):
            return {}

        text = self._clean_text(content.get("text"))
        if not text:
            return {}

        if self._clean_text(content.get("encoding")).lower() == "base64":
            return {}

        mime_type = self._clean_text(content.get("mimeType")).lower()
        if "application/json" in mime_type:
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return text

    def _extract_insomnia_environment_values(self, resources: List[Dict[str, Any]]) -> Dict[str, str]:
        """提取 Insomnia 环境变量"""
        values: Dict[str, str] = {}
        for resource in resources:
            if not isinstance(resource, dict) or resource.get("_type") != "environment":
                continue
            data = resource.get("data", {})
            if not isinstance(data, dict):
                continue
            for key, value in data.items():
                if value is not None:
                    values[str(key)] = str(value)
        return values

    def _extract_insomnia_response_examples(self, resources: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        """提取 Insomnia 请求对应的响应示例"""
        examples: Dict[str, Dict[str, Any]] = {}
        for resource in resources:
            if not isinstance(resource, dict) or resource.get("_type") != "response":
                continue
            parent_id = self._clean_text(resource.get("parentId"))
            if not parent_id:
                continue
            body_text = self._clean_text(resource.get("body"))
            parsed_body = self.parse_json_field(body_text) if body_text else {}
            examples[parent_id] = {
                "statusCode": self._coerce_int(resource.get("statusCode"), 200),
                "body": parsed_body if parsed_body not in ("", None) else {},
            }
        return examples

    def _extract_insomnia_request_body(
        self,
        body_data: Any,
        headers: Dict[str, Any],
        environment_values: Dict[str, str],
    ) -> Tuple[Any, str]:
        """提取 Insomnia 请求体"""
        if not isinstance(body_data, dict):
            return None, "auto"

        mime_type = self._clean_text(body_data.get("mimeType")).lower()
        text = self._replace_insomnia_variables(self._clean_text(body_data.get("text")), environment_values)
        params = body_data.get("params")

        if isinstance(params, list) and params:
            return self._name_value_list_to_dict(params, environment_values), "form"

        if not text:
            return None, "auto"

        if "application/json" in mime_type or "application/json" in str(headers.get("Content-Type") or "").lower():
            try:
                return json.loads(text), "json"
            except json.JSONDecodeError:
                return text, "raw"

        if "application/x-www-form-urlencoded" in mime_type:
            return dict(parse_qsl(text, keep_blank_values=True)), "form"

        return text, "raw"

    def _replace_insomnia_variables(self, text: str, environment_values: Dict[str, str]) -> str:
        """替换 Insomnia 变量"""
        value = text
        for key, replacement in environment_values.items():
            value = value.replace(f"{{{{ _.{key} }}}}", replacement)
            value = value.replace(f"{{{{ _.{key}}}}}", replacement)
            value = value.replace(f"{{{{{key}}}}}", replacement)
        return value

    def _insomnia_headers_to_dict(self, headers: Any, environment_values: Dict[str, str]) -> Dict[str, Any]:
        """将 Insomnia 头列表转成 dict"""
        result: Dict[str, Any] = {}
        for header in headers or []:
            if not isinstance(header, dict):
                continue
            key = self._clean_text(header.get("name") or header.get("key"))
            value = self._replace_insomnia_variables(self._clean_text(header.get("value")), environment_values)
            if key:
                result[key] = value
        return result

    def _parse_bruno_document(self, document: str) -> Optional[Dict[str, Any]]:
        """解析单个 Bruno 文档"""
        meta_block = self._extract_bruno_block(document, "meta")
        headers_block = self._extract_bruno_block(document, "headers")
        tests_block = self._extract_bruno_block(document, "tests")
        method_match = re.search(r"(?ms)^\s*(get|post|put|patch|delete|head|options)\s*\{(.*?)^\s*\}", document)
        if not method_match:
            return None

        method = method_match.group(1).upper()
        request_block = method_match.group(2)
        request_kv = self._parse_bruno_key_value_block(request_block)
        meta_kv = self._parse_bruno_key_value_block(meta_block)
        headers = self._parse_bruno_headers_block(headers_block)
        tests_kv = self._parse_bruno_key_value_block(tests_block)

        raw_url = request_kv.get("url", "")
        base_url, path, query_params = self._split_url_parts(raw_url)
        if base_url and not self.last_parse_meta.get("detected_base_url"):
            self.last_parse_meta["detected_base_url"] = base_url
        elif self.last_parse_meta.get("detected_base_url") and base_url and base_url != self.last_parse_meta["detected_base_url"]:
            path = raw_url

        body_mode = request_kv.get("body", "").lower()
        body = None
        request_format = "auto"
        if body_mode == "json":
            body_text = self._extract_bruno_typed_block(document, "body:json")
            body = self._parse_loose_value(body_text)
            request_format = "json"
        elif body_mode in {"form", "form-urlencoded"}:
            body_text = self._extract_bruno_typed_block(document, "body:form-urlencoded")
            body = self._parse_bruno_key_value_block(body_text)
            request_format = "form"
        elif body_mode in {"text", "raw"}:
            body = self._extract_bruno_typed_block(document, "body:text")
            request_format = "raw"

        raw_interface = {
            "name": meta_kv.get("name") or f"{method} {path or raw_url}",
            "method": method,
            "path": path or raw_url,
            "description": meta_kv.get("description", ""),
            "headers": headers,
            "query_params": query_params,
            "body": body,
            "expected_status": self._coerce_int(tests_kv.get("status"), 200),
            "expected_response": {},
            "request_format": request_format,
            "source": "bruno",
        }
        return self._normalize_interface(raw_interface)

    def _extract_bruno_block(self, text: str, block_name: str) -> str:
        """提取 Bruno 普通块内容"""
        match = re.search(rf"(?ms)^\s*{re.escape(block_name)}\s*\{{(.*?)^\s*\}}", text)
        return match.group(1).strip() if match else ""

    def _extract_bruno_typed_block(self, text: str, block_name: str) -> str:
        """提取 Bruno 类型块内容"""
        match = re.search(rf"(?ms)^\s*{re.escape(block_name)}\s*\{{(.*?)^\s*\}}", text)
        return match.group(1).strip() if match else ""

    def _parse_bruno_key_value_block(self, block_text: str) -> Dict[str, str]:
        """解析 Bruno key/value 块"""
        result: Dict[str, str] = {}
        for raw_line in (block_text or "").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
        return result

    def _parse_bruno_headers_block(self, block_text: str) -> Dict[str, Any]:
        """解析 Bruno headers 块"""
        result: Dict[str, Any] = {}
        for raw_line in (block_text or "").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("//"):
                continue
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            result[key.strip()] = value.strip()
        return result

    def _extract_description_text(self, description: Any) -> str:
        """提取描述文本"""
        if isinstance(description, dict):
            return self._clean_text(description.get("content")) or self._clean_text(description.get("text"))
        return self._clean_text(description)

    def _headers_list_to_dict(self, headers: Any, variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """将头列表转成 dict"""
        result: Dict[str, Any] = {}
        for header in headers or []:
            if not isinstance(header, dict):
                continue
            if header.get("disabled") is True:
                continue
            key = self._clean_text(header.get("key") or header.get("name"))
            value = self._clean_text(header.get("value"))
            if variables:
                value = self._replace_postman_variables(value, variables)
            if key:
                result[key] = value
        return result

    def _name_value_list_to_dict(self, items: Any, variables: Optional[Dict[str, str]] = None) -> Dict[str, Any]:
        """将 name/value 或 key/value 列表转成 dict"""
        result: Dict[str, Any] = {}
        for item in items or []:
            if not isinstance(item, dict):
                continue
            if item.get("disabled") is True:
                continue
            key = self._clean_text(item.get("key") or item.get("name"))
            value = item.get("value")
            if isinstance(value, str) and variables:
                value = self._replace_postman_variables(value, variables)
            if key:
                result[key] = value
        return result

    def _replace_postman_variables(self, text: str, variables: Dict[str, str]) -> str:
        """替换 Postman 变量"""
        value = text
        for key, replacement in variables.items():
            value = value.replace(f"{{{{{key}}}}}", replacement)
        return value

    def _split_url_parts(self, url: str) -> Tuple[str, str, Dict[str, Any]]:
        """拆分 URL 成 base_url/path/query"""
        parsed = urlparse(url)
        if parsed.scheme and parsed.netloc:
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            path = parsed.path or "/"
            query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
            path = re.sub(r"/:([A-Za-z0-9_]+)", r"/{\1}", path)
            return base_url, path, query_params
        return "", url, {}

    def _build_test_name(self, case_id: str, name: str) -> str:
        """生成安全的测试函数名"""
        safe_name = re.sub(r"[^0-9a-zA-Z_]+", "_", name).strip("_").lower()
        if not safe_name:
            return f"test_{case_id}"
        if safe_name[0].isdigit():
            safe_name = f"case_{safe_name}"
        return f"test_{case_id}_{safe_name}"

    def _normalize_execution_mode(self, mode: str) -> str:
        """归一化执行模式"""
        return self.EXECUTION_MODE_MAP.get((mode or "").strip(), "pytest")

    def _normalize_request_format(self, request_format: Any) -> str:
        """归一化请求格式"""
        if request_format is None:
            return "auto"
        key = str(request_format).strip()
        return self.REQUEST_FORMAT_MAP.get(key, self.REQUEST_FORMAT_MAP.get(key.lower(), "auto"))

    def _normalize_environment_config(self, environment_config: Any, base_url: str) -> Dict[str, Any]:
        """标准化环境配置"""
        parsed = environment_config
        if isinstance(environment_config, str) and environment_config.strip():
            try:
                parsed = json.loads(environment_config)
            except json.JSONDecodeError:
                parsed = {}

        environments: Dict[str, Dict[str, Any]] = {}
        active_env = "custom"
        if isinstance(parsed, dict):
            raw_envs = parsed.get("environments", {})
            active_env = self._clean_text(parsed.get("active_env")) or active_env
            if isinstance(raw_envs, dict):
                for env_name, env_item in raw_envs.items():
                    if not isinstance(env_item, dict):
                        continue
                    environments[str(env_name)] = {
                        "base_url": self._normalize_base_url(
                            self._clean_text(env_item.get("base_url") or env_item.get("url")) or base_url
                        ),
                        "headers": self._ensure_mapping(env_item.get("headers")),
                    }

        fallback_base_url = self._normalize_base_url(base_url)
        if not environments:
            environments = {
                "custom": {
                    "base_url": fallback_base_url,
                    "headers": {},
                }
            }
            active_env = "custom"
        elif active_env not in environments:
            active_env = next(iter(environments.keys()))

        return {
            "active_env": active_env,
            "environments": environments,
        }

    def _normalize_auth_config(self, auth_config: Any) -> Dict[str, Any]:
        """标准化鉴权配置"""
        parsed = auth_config
        if isinstance(auth_config, str) and auth_config.strip():
            try:
                parsed = json.loads(auth_config)
            except json.JSONDecodeError:
                parsed = {}

        if not isinstance(parsed, dict):
            parsed = {}

        auth_type = self._clean_text(parsed.get("type")).lower() or "none"
        return {
            "enabled": bool(parsed.get("enabled")) and auth_type != "none",
            "type": auth_type,
            "header_name": self._clean_text(parsed.get("header_name")) or "Authorization",
            "prefix": self._clean_text(parsed.get("prefix")) or "Bearer ",
            "token": self._clean_text(parsed.get("token")),
            "api_key_name": self._clean_text(parsed.get("api_key_name")) or "X-API-Key",
            "api_key_value": self._clean_text(parsed.get("api_key_value")),
            "username": self._clean_text(parsed.get("username")),
            "password": self._clean_text(parsed.get("password")),
            "custom_header_name": self._clean_text(parsed.get("custom_header_name")),
            "custom_header_value": self._clean_text(parsed.get("custom_header_value")),
        }

    def _build_auth_headers(self, auth_config: Dict[str, Any]) -> Dict[str, str]:
        """根据鉴权配置构建请求头"""
        if not auth_config.get("enabled"):
            return {}

        auth_type = auth_config.get("type", "none")
        if auth_type == "bearer" and auth_config.get("token"):
            return {
                auth_config.get("header_name", "Authorization"): f"{auth_config.get('prefix', 'Bearer ')}{auth_config.get('token')}"
            }

        if auth_type == "api_key" and auth_config.get("api_key_value"):
            return {
                auth_config.get("api_key_name", "X-API-Key"): auth_config.get("api_key_value", "")
            }

        if auth_type == "basic" and auth_config.get("username"):
            credential = f"{auth_config.get('username', '')}:{auth_config.get('password', '')}"
            encoded = base64.b64encode(credential.encode("utf-8")).decode("utf-8")
            return {"Authorization": f"Basic {encoded}"}

        if auth_type == "custom_header" and auth_config.get("custom_header_name"):
            return {
                auth_config.get("custom_header_name", "X-Custom-Auth"): auth_config.get("custom_header_value", "")
            }

        return {}

    def _normalize_base_url(self, base_url: str) -> str:
        """标准化基础 URL"""
        base = (base_url or "").strip()
        if not base:
            return ""
        if base.startswith(("http://", "https://")) or base.startswith("/"):
            return base.rstrip("/")
        return f"http://{base}".rstrip("/")

    def _infer_request_format(self, headers: Dict[str, Any], body: Any) -> str:
        """根据头和请求体推断请求格式"""
        content_type = str(headers.get("Content-Type") or headers.get("content-type") or "").lower()
        if "application/x-www-form-urlencoded" in content_type or "multipart/form-data" in content_type:
            return "form"
        if "application/json" in content_type:
            return "json"
        if isinstance(body, str):
            return "raw"
        if isinstance(body, (dict, list)):
            return "json"
        return "auto"

    def _load_structured_content(self, content: str) -> Optional[Any]:
        """尝试解析 JSON / YAML"""
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            pass

        try:
            import yaml  # type: ignore
        except ImportError:
            return None

        try:
            return yaml.safe_load(content)
        except Exception:
            return None

    def _looks_like_openapi(self, data: Any) -> bool:
        """判断内容是否像 Swagger/OpenAPI"""
        return isinstance(data, dict) and (
            "openapi" in data
            or "swagger" in data
            or (isinstance(data.get("paths"), dict) and ("info" in data or "servers" in data or "host" in data))
        )

    def _looks_like_postman_collection(self, data: Any) -> bool:
        """判断内容是否像 Postman Collection"""
        if not isinstance(data, dict):
            return False
        info = data.get("info")
        schema = self._clean_text((info or {}).get("schema")) if isinstance(info, dict) else ""
        return "postman" in schema.lower() or (isinstance(info, dict) and isinstance(data.get("item"), list))

    def _looks_like_har(self, data: Any) -> bool:
        """判断内容是否像 HAR"""
        return isinstance(data, dict) and isinstance((data.get("log") or {}).get("entries"), list)

    def _looks_like_insomnia_export(self, data: Any) -> bool:
        """判断内容是否像 Insomnia 导出"""
        if not isinstance(data, dict):
            return False
        export_type = self._clean_text(data.get("_type")).lower()
        export_source = self._clean_text(data.get("__export_source")).lower()
        return (export_type == "export" or "insomnia" in export_source) and isinstance(data.get("resources"), list)

    def _looks_like_bruno_text(self, text: str) -> bool:
        """判断文本是否像 Bruno .bru"""
        return bool(
            re.search(r"(?m)^\s*meta\s*\{", text)
            and re.search(r"(?m)^\s*(get|post|put|patch|delete|head|options)\s*\{", text, flags=re.IGNORECASE)
        )

    def _looks_like_url(self, text: str) -> bool:
        """判断文本是否为 URL"""
        parsed = urlparse(text)
        return parsed.scheme in {"http", "https"} and bool(parsed.netloc)

    def _fetch_remote_content(self, url: str) -> str:
        """拉取远程 Swagger/OpenAPI 文档"""
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.text

    def _ensure_mapping(self, value: Any) -> Dict[str, Any]:
        """确保值为 dict"""
        if value is None:
            return {}
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            parsed = self.parse_json_field(value)
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _parse_loose_value(self, value: str) -> Any:
        """尽量宽松地解析文本值"""
        text = (value or "").strip()
        if not text:
            return ""
        if text.startswith(("{", "[")):
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                pass
        if text.lower() in {"true", "false"}:
            return text.lower() == "true"
        if re.fullmatch(r"-?\d+", text):
            return int(text)
        if re.fullmatch(r"-?\d+\.\d+", text):
            return float(text)
        return text

    def _coerce_int(self, value: Any, default: int) -> int:
        """安全转换为 int"""
        if value is None:
            return default
        if isinstance(value, bool):
            return int(value)
        if isinstance(value, (int, float)):
            return int(value)
        text = str(value).strip()
        if not text or text.lower() == "nan":
            return default
        try:
            return int(float(text))
        except ValueError:
            return default

    def _clean_text(self, value: Any) -> str:
        """清理文本"""
        if self._is_empty_value(value):
            return ""
        return str(value).strip()

    def _is_empty_value(self, value: Any) -> bool:
        """判断空值"""
        if value is None:
            return True
        try:
            if pd.isna(value):
                return True
        except Exception:
            pass
        return False

    def _reset_parse_meta(self):
        """重置解析元数据"""
        self.last_parse_meta = {
            "source_type": "",
            "source_name": "",
            "detected_base_url": "",
            "interface_count": 0,
        }

    def _finalize_interfaces(
        self,
        interfaces: List[Dict[str, Any]],
        source_type: str,
        source_name: str,
    ) -> List[Dict[str, Any]]:
        """收尾处理解析结果"""
        cleaned = [self._normalize_interface(item) for item in interfaces if isinstance(item, dict)]
        if not cleaned:
            raise ValueError("未解析到有效接口，请检查导入内容格式")

        self.last_parse_meta["source_type"] = source_type
        self.last_parse_meta["source_name"] = source_name
        self.last_parse_meta["interface_count"] = len(cleaned)
        return cleaned
