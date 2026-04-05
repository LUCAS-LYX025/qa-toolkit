import json
import re
from copy import deepcopy
from typing import Any, Dict, List, Tuple
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse


class InterfaceDevTools:
    """接口研发辅助工具"""

    ISSUE_SEVERITY_ORDER = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    def compare_interfaces(
        self,
        baseline_interfaces: List[Dict[str, Any]],
        target_interfaces: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """对比两份接口定义并输出摘要"""
        baseline_index = {self._build_interface_key(item): self._normalize_interface(item) for item in baseline_interfaces}
        target_index = {self._build_interface_key(item): self._build_interface_value(item) for item in target_interfaces}

        added_keys = sorted(set(target_index) - set(baseline_index))
        removed_keys = sorted(set(baseline_index) - set(target_index))
        common_keys = sorted(set(baseline_index) & set(target_index))

        added = [self._build_summary_item(target_index[key]) for key in added_keys]
        removed = [self._build_summary_item(baseline_index[key]) for key in removed_keys]

        changed: List[Dict[str, Any]] = []
        high_risk_changes: List[Dict[str, Any]] = []
        unchanged_count = 0

        for key in common_keys:
            baseline_item = baseline_index[key]
            target_item = target_index[key]
            field_changes, risk_level = self._diff_interface(baseline_item, target_item)
            if not field_changes:
                unchanged_count += 1
                continue

            change_item = {
                "key": key,
                "name": target_item.get("name") or baseline_item.get("name"),
                "method": target_item.get("method") or baseline_item.get("method"),
                "path": target_item.get("path") or baseline_item.get("path"),
                "risk_level": risk_level,
                "changes": field_changes,
            }
            changed.append(change_item)
            if risk_level == "high":
                high_risk_changes.append(change_item)

        return {
            "summary": {
                "baseline_total": len(baseline_index),
                "target_total": len(target_index),
                "added_count": len(added),
                "removed_count": len(removed),
                "changed_count": len(changed),
                "unchanged_count": unchanged_count,
                "high_risk_count": len(high_risk_changes),
            },
            "added": added,
            "removed": removed,
            "changed": changed,
            "high_risk_changes": high_risk_changes,
        }

    def build_markdown_report(self, diff_result: Dict[str, Any]) -> str:
        """生成 Markdown 版本的接口差异报告"""
        summary = diff_result.get("summary", {})
        lines = [
            "# 接口变更分析报告",
            "",
            "## 概览",
            f"- 基线接口数: {summary.get('baseline_total', 0)}",
            f"- 当前接口数: {summary.get('target_total', 0)}",
            f"- 新增接口: {summary.get('added_count', 0)}",
            f"- 删除接口: {summary.get('removed_count', 0)}",
            f"- 变更接口: {summary.get('changed_count', 0)}",
            f"- 高风险变更: {summary.get('high_risk_count', 0)}",
            "",
        ]

        for section_title, items in [
            ("新增接口", diff_result.get("added", [])),
            ("删除接口", diff_result.get("removed", [])),
        ]:
            lines.append(f"## {section_title}")
            if not items:
                lines.append("- 无")
            else:
                for item in items:
                    lines.append(f"- `{item['method']} {item['path']}` {item['name']}")
            lines.append("")

        lines.append("## 变更接口")
        if not diff_result.get("changed"):
            lines.append("- 无")
        else:
            for item in diff_result.get("changed", []):
                risk_text = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(item.get("risk_level"), "未知")
                lines.append(f"### `{item['method']} {item['path']}` {item['name']}")
                lines.append(f"- 风险等级: {risk_text}")
                for change in item.get("changes", []):
                    lines.append(f"- {change.get('label')}: {change.get('message')}")
                lines.append("")

        return "\n".join(lines).strip() + "\n"

    def export_normalized_interfaces(self, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将接口定义标准化并导出多种格式"""
        normalized_interfaces = [self._normalize_interface(item) for item in interfaces]
        method_distribution: Dict[str, int] = {}
        tag_distribution: Dict[str, int] = {}
        body_count = 0
        auth_related_count = 0
        missing_response_count = 0

        for item in normalized_interfaces:
            method = item.get("method", "GET")
            method_distribution[method] = method_distribution.get(method, 0) + 1
            if item.get("body") not in (None, "", {}, []):
                body_count += 1
            if self._is_auth_related(item):
                auth_related_count += 1
            if item.get("expected_response") in (None, "", {}, []):
                missing_response_count += 1
            for tag in item.get("tags", []):
                tag_distribution[tag] = tag_distribution.get(tag, 0) + 1

        summary = {
            "interface_count": len(normalized_interfaces),
            "method_distribution": method_distribution,
            "tag_count": len(tag_distribution),
            "with_body_count": body_count,
            "auth_related_count": auth_related_count,
            "missing_expected_response_count": missing_response_count,
        }

        export_payload = {
            "summary": summary,
            "interfaces": normalized_interfaces,
        }

        return {
            "summary": summary,
            "interfaces": normalized_interfaces,
            "json_artifact": json.dumps(export_payload, ensure_ascii=False, indent=2),
            "markdown_artifact": self._build_interface_catalog_markdown(normalized_interfaces, summary),
            "text_artifact": self._build_structured_text_export(normalized_interfaces),
        }

    def analyze_interface_quality(self, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查接口定义质量并输出问题清单"""
        normalized_interfaces = [self._normalize_interface(item) for item in interfaces]
        issues: List[Dict[str, Any]] = []
        key_index_map: Dict[str, List[Dict[str, Any]]] = {}

        for index, item in enumerate(normalized_interfaces, start=1):
            item_key = self._build_interface_key(item)
            key_index_map.setdefault(item_key, []).append({"index": index, "interface": item})

            placeholders = self._extract_path_placeholders(item.get("path", ""))
            path_params = item.get("path_params") or {}
            missing_path_params = sorted(placeholders - set(path_params.keys()))
            extra_path_params = sorted(set(path_params.keys()) - placeholders)
            content_type = self._get_content_type(item.get("headers") or {})
            body = item.get("body")
            expected_response = item.get("expected_response")
            method = item.get("method", "GET")

            if not item.get("name"):
                issues.append(self._build_issue(index, item, "medium", "missing_name", "接口名称为空"))

            if not item.get("description"):
                issues.append(self._build_issue(index, item, "low", "missing_description", "接口描述为空，后续维护成本会偏高"))

            if expected_response in (None, "", {}, []):
                issues.append(self._build_issue(index, item, "medium", "missing_expected_response", "缺少期望响应示例，自动断言会偏弱"))

            if missing_path_params:
                issues.append(
                    self._build_issue(
                        index,
                        item,
                        "high",
                        "path_param_missing",
                        f"路径占位符缺少参数: {', '.join(missing_path_params)}",
                    )
                )

            if extra_path_params:
                issues.append(
                    self._build_issue(
                        index,
                        item,
                        "medium",
                        "path_param_extra",
                        f"存在未在路径中使用的 path 参数: {', '.join(extra_path_params)}",
                    )
                )

            empty_path_param_values = [
                key for key, value in path_params.items()
                if key in placeholders and value in (None, "", [])
            ]
            if empty_path_param_values:
                issues.append(
                    self._build_issue(
                        index,
                        item,
                        "medium",
                        "path_param_empty",
                        f"路径参数值为空: {', '.join(sorted(empty_path_param_values))}",
                    )
                )

            if method == "GET" and body not in (None, "", {}, []):
                issues.append(self._build_issue(index, item, "medium", "get_with_body", "GET 请求携带 body，兼容性风险较高"))

            if method in {"POST", "PUT", "PATCH"}:
                if body in (None, "", {}, []):
                    issues.append(
                        self._build_issue(
                            index,
                            item,
                            "low",
                            "empty_request_body",
                            f"{method} 请求未提供 body，请确认是否符合接口设计",
                        )
                    )
                else:
                    if not content_type:
                        issues.append(
                            self._build_issue(
                                index,
                                item,
                                "medium",
                                "missing_content_type",
                                "请求体存在但未声明 Content-Type",
                            )
                        )

                    request_format = item.get("request_format", "auto")
                    if request_format in {"json", "data_json"} and "application/json" not in content_type:
                        issues.append(
                            self._build_issue(
                                index,
                                item,
                                "medium",
                                "json_content_type_mismatch",
                                "请求格式为 JSON，但 Content-Type 不是 application/json",
                            )
                        )

                    if request_format == "form" and not any(
                        token in content_type for token in ("application/x-www-form-urlencoded", "multipart/form-data")
                    ):
                        issues.append(
                            self._build_issue(
                                index,
                                item,
                                "medium",
                                "form_content_type_mismatch",
                                "请求格式为 form，但 Content-Type 不是 form 类型",
                            )
                        )

            if not item.get("tags"):
                issues.append(self._build_issue(index, item, "low", "missing_tags", "未配置标签，后续分组与筛选不方便"))

        duplicate_groups = []
        for key, entries in key_index_map.items():
            if len(entries) <= 1:
                continue
            duplicate_groups.append(
                {
                    "key": key,
                    "indexes": [entry["index"] for entry in entries],
                    "method": entries[0]["interface"].get("method", "GET"),
                    "path": entries[0]["interface"].get("path", "/"),
                    "count": len(entries),
                }
            )
            duplicate_indexes = ", ".join(str(entry["index"]) for entry in entries)
            for entry in entries:
                issues.append(
                    self._build_issue(
                        entry["index"],
                        entry["interface"],
                        "high",
                        "duplicate_endpoint",
                        f"与其他接口重复定义，重复序号: {duplicate_indexes}",
                    )
                )

        sorted_issues = sorted(
            issues,
            key=lambda item: (
                self.ISSUE_SEVERITY_ORDER.get(item.get("severity", "low"), 99),
                item.get("index", 0),
                item.get("category", ""),
            ),
        )

        severity_counts = {"high": 0, "medium": 0, "low": 0}
        category_counts: Dict[str, int] = {}
        for issue in sorted_issues:
            severity = issue.get("severity", "low")
            category = issue.get("category", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

        score = max(
            0,
            100 - severity_counts.get("high", 0) * 18 - severity_counts.get("medium", 0) * 8 - severity_counts.get("low", 0) * 3,
        )
        if score >= 90:
            health_level = "优秀"
        elif score >= 75:
            health_level = "良好"
        elif score >= 60:
            health_level = "一般"
        else:
            health_level = "需整改"

        return {
            "summary": {
                "interface_count": len(normalized_interfaces),
                "issue_count": len(sorted_issues),
                "high_count": severity_counts.get("high", 0),
                "medium_count": severity_counts.get("medium", 0),
                "low_count": severity_counts.get("low", 0),
                "duplicate_count": len(duplicate_groups),
                "health_score": score,
                "health_level": health_level,
            },
            "issues": sorted_issues,
            "duplicate_groups": duplicate_groups,
            "category_counts": category_counts,
        }

    def build_quality_markdown_report(self, quality_result: Dict[str, Any]) -> str:
        """生成接口文档体检报告"""
        summary = quality_result.get("summary", {})
        lines = [
            "# 接口文档体检报告",
            "",
            "## 概览",
            f"- 接口总数: {summary.get('interface_count', 0)}",
            f"- 问题总数: {summary.get('issue_count', 0)}",
            f"- 高风险问题: {summary.get('high_count', 0)}",
            f"- 中风险问题: {summary.get('medium_count', 0)}",
            f"- 低风险问题: {summary.get('low_count', 0)}",
            f"- 重复接口组数: {summary.get('duplicate_count', 0)}",
            f"- 健康分: {summary.get('health_score', 0)} ({summary.get('health_level', '未知')})",
            "",
            "## 重复接口",
        ]

        duplicate_groups = quality_result.get("duplicate_groups", [])
        if not duplicate_groups:
            lines.append("- 无")
        else:
            for item in duplicate_groups:
                lines.append(
                    f"- `{item.get('method', 'GET')} {item.get('path', '/')}` 出现 {item.get('count', 0)} 次，序号: {', '.join(map(str, item.get('indexes', [])))}"
                )

        lines.extend(["", "## 问题明细"])
        issues = quality_result.get("issues", [])
        if not issues:
            lines.append("- 未发现问题")
        else:
            for issue in issues:
                severity_text = {
                    "high": "高风险",
                    "medium": "中风险",
                    "low": "低风险",
                }.get(issue.get("severity"), "未知")
                lines.append(
                    f"- [{severity_text}] 序号 {issue.get('index', 0)} | `{issue.get('method', 'GET')} {issue.get('path', '/')}` | {issue.get('message', '')}"
                )

        return "\n".join(lines).strip() + "\n"

    def generate_regression_checklist(
        self,
        interfaces: List[Dict[str, Any]],
        include_negative: bool = True,
        include_auth_checks: bool = True,
        include_performance_checks: bool = True,
    ) -> Dict[str, Any]:
        """根据接口定义生成回归清单"""
        normalized_interfaces = [self._normalize_interface(item) for item in interfaces]
        checklist_items: List[Dict[str, Any]] = []
        priority_counts = {"high": 0, "medium": 0, "low": 0}

        for index, item in enumerate(normalized_interfaces, start=1):
            focus_points: List[str] = []
            checklist: List[str] = [f"校验状态码为 {item.get('expected_status', 200)}"]

            if item.get("expected_response") not in (None, "", {}, []):
                checklist.append("校验关键响应字段和业务码")
                focus_points.append("响应结构")
            else:
                checklist.append("补充最小可用响应断言")
                focus_points.append("响应样例缺失")

            if include_performance_checks:
                checklist.append("关注响应时间是否在可接受范围内")

            if item.get("query_params"):
                focus_points.append("查询参数")
                checklist.append("覆盖查询参数正常组合")
                if include_negative:
                    checklist.append("验证查询参数缺失、非法值、边界值")

            if item.get("path_params"):
                focus_points.append("路径参数")
                checklist.append("验证路径参数替换后的资源是否正确")
                if include_negative:
                    checklist.append("验证无效路径参数、越权访问或不存在资源")

            if item.get("body") not in (None, "", {}, []):
                focus_points.append("请求体")
                checklist.append("覆盖请求体必填字段、类型和边界值")
                if include_negative:
                    checklist.append("验证请求体字段缺失、超长、非法格式")

            if include_auth_checks and self._is_auth_related(item):
                focus_points.append("鉴权")
                checklist.append("验证有效鉴权下接口可正常访问")
                if include_negative:
                    checklist.append("验证缺少鉴权、鉴权失效、权限不足场景")

            if item.get("method") in {"POST", "PUT", "PATCH", "DELETE"}:
                focus_points.append("数据变更")
                checklist.append("确认接口对数据的新增、更新或删除结果正确")
                if include_negative:
                    checklist.append("验证重复提交、幂等性或回滚处理")

            if self._has_pagination_hint(item):
                focus_points.append("分页")
                checklist.append("验证分页参数、总数、页码边界和空列表场景")

            if self._has_sort_hint(item):
                focus_points.append("排序筛选")
                checklist.append("验证排序字段和筛选条件组合")

            priority = self._decide_regression_priority(item)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1

            checklist_items.append(
                {
                    "index": index,
                    "name": item.get("name", "未命名接口"),
                    "method": item.get("method", "GET"),
                    "path": item.get("path", "/"),
                    "priority": priority,
                    "focus_points": sorted(dict.fromkeys(focus_points)) or ["基础可用性"],
                    "checklist": checklist,
                }
            )

        summary = {
            "interface_count": len(checklist_items),
            "high_priority_count": priority_counts.get("high", 0),
            "medium_priority_count": priority_counts.get("medium", 0),
            "low_priority_count": priority_counts.get("low", 0),
            "check_item_count": sum(len(item.get("checklist", [])) for item in checklist_items),
        }

        checklist_rows = []
        for item in checklist_items:
            checklist_rows.append(
                {
                    "序号": item.get("index", 0),
                    "优先级": {"high": "高", "medium": "中", "low": "低"}.get(item.get("priority"), "低"),
                    "方法": item.get("method", "GET"),
                    "路径": item.get("path", "/"),
                    "接口": item.get("name", "未命名接口"),
                    "关注点": "、".join(item.get("focus_points", [])),
                    "建议检查项数": len(item.get("checklist", [])),
                }
            )

        return {
            "summary": summary,
            "items": checklist_items,
            "rows": checklist_rows,
            "markdown_artifact": self._build_regression_markdown(checklist_items, summary),
            "json_artifact": json.dumps(
                {"summary": summary, "items": checklist_items},
                ensure_ascii=False,
                indent=2,
            ),
        }

    def generate_assertion_template(
        self,
        sample: Any,
        template_style: str = "标准断言",
        max_depth: int = 4,
    ) -> Dict[str, Any]:
        """根据响应样例生成断言模板"""
        parsed_sample = self._parse_sample_value(sample)
        style = {
            "字段存在断言": "presence",
            "标准断言": "standard",
            "严格断言": "strict",
            "presence": "presence",
            "standard": "standard",
            "strict": "strict",
        }.get(template_style, "standard")

        if style == "presence":
            template = self._build_presence_template(parsed_sample, 0, max_depth)
        elif style == "strict":
            template = self._build_strict_template(parsed_sample, 0, max_depth)
        else:
            template = self._build_standard_template(parsed_sample, 0, max_depth)

        field_paths = self._collect_field_paths(parsed_sample, "response", 0, max_depth)
        field_paths = sorted(dict.fromkeys(field_paths))
        case_fragment = {
            "expected_status": 200,
            "expected_response": template,
        }

        return {
            "template_style": style,
            "sample_type": type(parsed_sample).__name__,
            "field_count": len(field_paths),
            "field_paths": field_paths,
            "template": template,
            "template_json": json.dumps(template, ensure_ascii=False, indent=2),
            "case_fragment_json": json.dumps(case_fragment, ensure_ascii=False, indent=2),
        }

    def generate_mock_server_script(
        self,
        interfaces: List[Dict[str, Any]],
        host: str = "0.0.0.0",
        port: int = 8000,
        enable_cors: bool = True,
        delay_ms: int = 0,
    ) -> str:
        """根据接口定义生成一个可直接运行的 Mock 服务脚本"""
        routes = []
        for interface in interfaces:
            item = self._normalize_interface(interface)
            response_body = item.get("expected_response")
            if response_body in (None, "", {}, []):
                response_body = {
                    "success": True,
                    "message": f"mock response for {item['name']}",
                    "path": item.get("path", ""),
                    "method": item.get("method", "GET"),
                }

            routes.append(
                {
                    "name": item.get("name", "未命名接口"),
                    "method": item.get("method", "GET"),
                    "path": item.get("path", "/"),
                    "status_code": item.get("expected_status", 200),
                    "response_body": response_body,
                    "headers": self._build_mock_headers(item.get("headers") or {}, response_body),
                }
            )

        route_json = json.dumps(routes, ensure_ascii=False, indent=2)
        return f'''"""自动生成的本地 Mock 服务"""
import argparse
import json
import re
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_HOST = {host!r}
DEFAULT_PORT = {int(port)}
DEFAULT_DELAY_MS = {int(delay_ms)}
ENABLE_CORS = {bool(enable_cors)}
ROUTES = json.loads({route_json!r})


def clone_value(value):
    return deepcopy(value)


def normalize_path(path):
    actual = (path or "/").strip()
    if not actual:
        return "/"
    if actual.startswith(("http://", "https://")):
        actual = urlparse(actual).path or "/"
    if not actual.startswith("/"):
        actual = "/" + actual
    if len(actual) > 1:
        actual = actual.rstrip("/")
    return actual


def compile_route_pattern(path):
    normalized = normalize_path(path)
    pattern = re.escape(normalized)
    pattern = re.sub(r"\\\{{[^/]+\\\}}", r"([^/]+)", pattern)
    return re.compile("^" + pattern + "$")


def find_route(method, path):
    actual_path = normalize_path(path)
    for route in ROUTES:
        if route.get("method", "GET").upper() != method.upper():
            continue
        if compile_route_pattern(route.get("path", "/")).match(actual_path):
            return route
    return None


class MockRequestHandler(BaseHTTPRequestHandler):
    server_version = "GeneratedMockServer/1.0"

    def _set_headers(self, status_code, headers):
        self.send_response(int(status_code))
        header_map = clone_value(headers or {{}})
        if ENABLE_CORS:
            header_map.setdefault("Access-Control-Allow-Origin", "*")
            header_map.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
            header_map.setdefault("Access-Control-Allow-Headers", "*")
        for key, value in header_map.items():
            self.send_header(str(key), str(value))
        self.end_headers()

    def _read_body(self):
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length <= 0:
            return None
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except Exception:
            return raw_body.decode("utf-8", errors="replace")

    def _dispatch(self):
        parsed = urlparse(self.path)
        route = find_route(self.command, parsed.path)
        if not route:
            payload = {{
                "success": False,
                "message": "mock route not found",
                "method": self.command,
                "path": parsed.path,
            }}
            self._set_headers(404, {{"Content-Type": "application/json; charset=utf-8"}})
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        if DEFAULT_DELAY_MS > 0:
            time.sleep(DEFAULT_DELAY_MS / 1000)

        request_body = self._read_body()
        response_body = clone_value(route.get("response_body"))
        if isinstance(response_body, dict):
            response_body.setdefault("_request", {{
                "method": self.command,
                "path": parsed.path,
                "query": parse_qs(parsed.query),
                "body": request_body,
            }})

        headers = clone_value(route.get("headers") or {{}})
        is_json = isinstance(response_body, (dict, list))
        headers.setdefault(
            "Content-Type",
            "application/json; charset=utf-8" if is_json else "text/plain; charset=utf-8"
        )
        self._set_headers(route.get("status_code", 200), headers)

        if self.command == "HEAD":
            return

        if is_json:
            body = json.dumps(response_body, ensure_ascii=False, indent=2)
        else:
            body = str(response_body)
        self.wfile.write(body.encode("utf-8"))

    def do_GET(self):
        self._dispatch()

    def do_POST(self):
        self._dispatch()

    def do_PUT(self):
        self._dispatch()

    def do_PATCH(self):
        self._dispatch()

    def do_DELETE(self):
        self._dispatch()

    def do_HEAD(self):
        self._dispatch()

    def do_OPTIONS(self):
        self._set_headers(204, {{
            "Content-Type": "text/plain; charset=utf-8",
            "Access-Control-Max-Age": "86400",
        }})


def main():
    parser = argparse.ArgumentParser(description="运行自动生成的 Mock 服务")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()

    server = ThreadingHTTPServer((args.host, args.port), MockRequestHandler)
    print(f"Mock server is running on http://{{args.host}}:{{args.port}}")
    print(f"Loaded routes: {{len(ROUTES)}}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\\nMock server stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
'''

    def generate_request_snippet(
        self,
        interface: Dict[str, Any],
        language: str = "Python requests",
        base_url: str = "",
    ) -> str:
        """生成接口调试代码片段"""
        item = self._normalize_interface(interface)
        headers = deepcopy(item.get("headers") or {})
        body = deepcopy(item.get("body"))
        query_params = deepcopy(item.get("query_params") or {})
        method = item.get("method", "GET").upper()

        if language == "curl":
            full_url = self._build_full_url(item, base_url, include_query=True)
            return self._render_curl_snippet(method, full_url, headers, body)
        if language == "JavaScript fetch":
            full_url = self._build_full_url(item, base_url, include_query=False)
            return self._render_fetch_snippet(method, full_url, headers, query_params, body)
        full_url = self._build_full_url(item, base_url, include_query=False)
        return self._render_requests_snippet(method, full_url, headers, query_params, body)

    def _build_interface_key(self, interface: Dict[str, Any]) -> str:
        item = self._normalize_interface(interface)
        return f"{item['method']} {self._normalize_path(item['path'])}"

    def _build_interface_value(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        return self._normalize_interface(interface)

    def _normalize_interface(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        method = str(interface.get("method") or "GET").upper()
        query_params = self._normalize_mapping(interface.get("query_params"))
        body = interface.get("body")
        parameters = interface.get("parameters")
        if method == "GET" and not query_params and isinstance(parameters, dict):
            query_params = self._normalize_mapping(parameters)
        if body is None and method != "GET":
            body = parameters
        return {
            "name": str(interface.get("name") or "").strip(),
            "method": method,
            "path": self._normalize_path(str(interface.get("path") or interface.get("url") or "/")),
            "description": str(interface.get("description") or "").strip(),
            "headers": self._normalize_mapping(interface.get("headers")),
            "path_params": self._normalize_mapping(interface.get("path_params")),
            "query_params": query_params,
            "body": self._normalize_value(body),
            "expected_status": self._to_int(interface.get("expected_status"), 200),
            "expected_response": self._normalize_value(interface.get("expected_response")),
            "request_format": str(interface.get("request_format") or "auto").strip() or "auto",
            "tags": self._normalize_tags(interface.get("tags")),
        }

    def _normalize_path(self, path: str) -> str:
        actual_path = (path or "/").strip()
        if not actual_path:
            return "/"
        if actual_path.startswith(("http://", "https://")):
            actual_path = urlparse(actual_path).path or "/"
        if not actual_path.startswith("/"):
            actual_path = "/" + actual_path
        actual_path = re.sub(r"/+", "/", actual_path)
        if len(actual_path) > 1:
            actual_path = actual_path.rstrip("/")
        return actual_path

    def _normalize_mapping(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {str(key): self._normalize_value(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}

    def _normalize_tags(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _normalize_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {str(key): self._normalize_value(val) for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
        if isinstance(value, list):
            return [self._normalize_value(item) for item in value]
        if isinstance(value, str):
            return value.strip()
        return value

    def _to_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _build_summary_item(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "name": interface.get("name", ""),
            "method": interface.get("method", "GET"),
            "path": interface.get("path", "/"),
        }

    def _build_issue(
        self,
        index: int,
        interface: Dict[str, Any],
        severity: str,
        category: str,
        message: str,
    ) -> Dict[str, Any]:
        return {
            "index": index,
            "name": interface.get("name", "") or "未命名接口",
            "method": interface.get("method", "GET"),
            "path": interface.get("path", "/"),
            "severity": severity,
            "category": category,
            "message": message,
        }

    def _build_interface_catalog_markdown(
        self,
        interfaces: List[Dict[str, Any]],
        summary: Dict[str, Any],
    ) -> str:
        lines = [
            "# 标准化接口清单",
            "",
            "## 概览",
            f"- 接口总数: {summary.get('interface_count', 0)}",
            f"- 含请求体接口: {summary.get('with_body_count', 0)}",
            f"- 鉴权相关接口: {summary.get('auth_related_count', 0)}",
            f"- 缺少响应样例: {summary.get('missing_expected_response_count', 0)}",
            f"- 请求方法分布: {', '.join(f'{key}:{value}' for key, value in summary.get('method_distribution', {}).items()) or '无'}",
            "",
            "## 接口清单",
            "| 序号 | 方法 | 路径 | 名称 | 请求格式 | 标签 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]

        for index, item in enumerate(interfaces, start=1):
            lines.append(
                f"| {index} | {item.get('method', 'GET')} | `{item.get('path', '/')}` | "
                f"{item.get('name', '未命名接口')} | {item.get('request_format', 'auto')} | "
                f"{', '.join(item.get('tags', [])) or '-'} |"
            )

        lines.extend(["", "## 详细定义"])
        for index, item in enumerate(interfaces, start=1):
            lines.extend(
                [
                    f"### {index}. `{item.get('method', 'GET')} {item.get('path', '/')}` {item.get('name', '未命名接口')}",
                    f"- 描述: {item.get('description') or '无'}",
                    f"- 标签: {', '.join(item.get('tags', [])) or '无'}",
                    f"- 请求头: `{self._serialize_inline(item.get('headers', {}))}`",
                    f"- 路径参数: `{self._serialize_inline(item.get('path_params', {}))}`",
                    f"- 查询参数: `{self._serialize_inline(item.get('query_params', {}))}`",
                    f"- 请求体: `{self._serialize_inline(item.get('body'))}`",
                    f"- 期望状态码: {item.get('expected_status', 200)}",
                    f"- 期望响应: `{self._serialize_inline(item.get('expected_response'))}`",
                    "",
                ]
            )

        return "\n".join(lines).strip() + "\n"

    def _build_structured_text_export(self, interfaces: List[Dict[str, Any]]) -> str:
        blocks = []
        for item in interfaces:
            blocks.append(
                "\n".join(
                    [
                        f"接口名称: {item.get('name', '未命名接口')}",
                        f"请求方法: {item.get('method', 'GET')}",
                        f"接口路径: {item.get('path', '/')}",
                        f"接口描述: {item.get('description') or ''}",
                        f"请求头: {self._serialize_inline(item.get('headers', {}))}",
                        f"路径参数: {self._serialize_inline(item.get('path_params', {}))}",
                        f"查询参数: {self._serialize_inline(item.get('query_params', {}))}",
                        f"请求体: {self._serialize_inline(item.get('body'))}",
                        f"请求格式: {item.get('request_format', 'auto')}",
                        f"标签: {', '.join(item.get('tags', []))}",
                        f"期望状态码: {item.get('expected_status', 200)}",
                        f"期望响应: {self._serialize_inline(item.get('expected_response'))}",
                    ]
                )
            )
        return "\n---\n".join(blocks)

    def _build_regression_markdown(self, items: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
        lines = [
            "# 接口回归清单",
            "",
            "## 概览",
            f"- 接口总数: {summary.get('interface_count', 0)}",
            f"- 高优先级: {summary.get('high_priority_count', 0)}",
            f"- 中优先级: {summary.get('medium_priority_count', 0)}",
            f"- 低优先级: {summary.get('low_priority_count', 0)}",
            f"- 建议检查项总数: {summary.get('check_item_count', 0)}",
            "",
        ]

        for item in items:
            priority_text = {"high": "高", "medium": "中", "low": "低"}.get(item.get("priority"), "低")
            lines.append(
                f"## {item.get('index', 0)}. [{priority_text}] `{item.get('method', 'GET')} {item.get('path', '/')}` {item.get('name', '未命名接口')}"
            )
            lines.append(f"- 关注点: {'、'.join(item.get('focus_points', []))}")
            for check_item in item.get("checklist", []):
                lines.append(f"- [ ] {check_item}")
            lines.append("")

        return "\n".join(lines).strip() + "\n"

    def _diff_interface(self, baseline: Dict[str, Any], target: Dict[str, Any]) -> Tuple[List[Dict[str, str]], str]:
        changes: List[Dict[str, str]] = []
        risk_rank = 0

        def add_change(label: str, message: str, risk: str):
            nonlocal risk_rank
            if not message:
                return
            changes.append({"label": label, "message": message, "risk": risk})
            risk_rank = max(risk_rank, {"low": 1, "medium": 2, "high": 3}.get(risk, 0))

        if baseline.get("name") != target.get("name"):
            add_change("接口名称", f"{baseline.get('name') or '未命名'} -> {target.get('name') or '未命名'}", "low")

        if baseline.get("description") != target.get("description"):
            add_change("接口描述", "描述内容发生变化", "low")

        if baseline.get("request_format") != target.get("request_format"):
            add_change(
                "请求格式",
                f"{baseline.get('request_format', 'auto')} -> {target.get('request_format', 'auto')}",
                "high",
            )

        if baseline.get("expected_status") != target.get("expected_status"):
            add_change(
                "期望状态码",
                f"{baseline.get('expected_status', 200)} -> {target.get('expected_status', 200)}",
                "high",
            )

        header_message, header_risk = self._describe_mapping_change(baseline.get("headers"), target.get("headers"))
        add_change("请求头", header_message, header_risk)

        path_message, path_risk = self._describe_mapping_change(baseline.get("path_params"), target.get("path_params"))
        add_change("路径参数", path_message, path_risk)

        query_message, query_risk = self._describe_mapping_change(
            baseline.get("query_params"),
            target.get("query_params"),
        )
        add_change("查询参数", query_message, query_risk)

        body_message, body_risk = self._describe_value_change(baseline.get("body"), target.get("body"))
        add_change("请求体", body_message, body_risk)

        response_message, response_risk = self._describe_value_change(
            baseline.get("expected_response"),
            target.get("expected_response"),
        )
        add_change("期望响应", response_message, response_risk)

        tags_message, tags_risk = self._describe_tag_change(baseline.get("tags"), target.get("tags"))
        add_change("标签", tags_message, tags_risk)

        risk_level = {0: "low", 1: "low", 2: "medium", 3: "high"}[risk_rank]
        return changes, risk_level

    def _describe_mapping_change(self, baseline: Any, target: Any) -> Tuple[str, str]:
        baseline_map = baseline if isinstance(baseline, dict) else {}
        target_map = target if isinstance(target, dict) else {}
        if baseline_map == target_map:
            return "", "low"

        added_keys = sorted(set(target_map) - set(baseline_map))
        removed_keys = sorted(set(baseline_map) - set(target_map))
        changed_keys = sorted(
            key for key in set(baseline_map) & set(target_map)
            if baseline_map.get(key) != target_map.get(key)
        )

        parts = []
        if added_keys:
            parts.append(f"新增字段: {', '.join(added_keys)}")
        if removed_keys:
            parts.append(f"删除字段: {', '.join(removed_keys)}")
        if changed_keys:
            parts.append(f"字段值变化: {', '.join(changed_keys)}")

        if removed_keys or changed_keys:
            return "; ".join(parts), "high" if removed_keys else "medium"
        return "; ".join(parts), "medium"

    def _describe_value_change(self, baseline: Any, target: Any) -> Tuple[str, str]:
        if baseline == target:
            return "", "low"

        if type(baseline) is not type(target):
            return f"类型变化: {type(baseline).__name__} -> {type(target).__name__}", "high"

        if isinstance(baseline, dict):
            return self._describe_mapping_change(baseline, target)

        if isinstance(baseline, list):
            if baseline and all(isinstance(item, str) for item in baseline):
                baseline_set = set(baseline)
                target_set = set(target)
                added_items = sorted(target_set - baseline_set)
                removed_items = sorted(baseline_set - target_set)
                parts = []
                if added_items:
                    parts.append(f"新增项: {', '.join(added_items)}")
                if removed_items:
                    parts.append(f"删除项: {', '.join(removed_items)}")
                return "; ".join(parts) or "数组内容发生变化", "high" if removed_items else "medium"

            if len(baseline) != len(target):
                return f"数组长度变化: {len(baseline)} -> {len(target)}", "medium"
            return "数组内容发生变化", "medium"

        return f"{baseline!r} -> {target!r}", "medium"

    def _describe_tag_change(self, baseline: List[str], target: List[str]) -> Tuple[str, str]:
        baseline_tags = baseline or []
        target_tags = target or []
        if baseline_tags == target_tags:
            return "", "low"

        added_tags = sorted(set(target_tags) - set(baseline_tags))
        removed_tags = sorted(set(baseline_tags) - set(target_tags))
        parts = []
        if added_tags:
            parts.append(f"新增标签: {', '.join(added_tags)}")
        if removed_tags:
            parts.append(f"删除标签: {', '.join(removed_tags)}")
        return "; ".join(parts), "low"

    def _build_mock_headers(self, headers: Dict[str, Any], response_body: Any) -> Dict[str, Any]:
        merged_headers = {
            "Cache-Control": "no-store",
        }
        if isinstance(response_body, (dict, list)):
            merged_headers["Content-Type"] = "application/json; charset=utf-8"
        elif isinstance(response_body, str):
            merged_headers["Content-Type"] = "text/plain; charset=utf-8"
        for key in ("Set-Cookie", "X-Trace-Id"):
            if key in headers:
                merged_headers[key] = headers[key]
        return merged_headers

    def _build_full_url(self, interface: Dict[str, Any], base_url: str, include_query: bool = True) -> str:
        path = interface.get("path", "/")
        path_params = deepcopy(interface.get("path_params") or {})
        for key, value in path_params.items():
            path = path.replace("{" + str(key) + "}", str(value))

        if path.startswith(("http://", "https://")):
            url = path
        else:
            actual_base_url = (base_url or "").strip()
            if actual_base_url:
                url = actual_base_url.rstrip("/") + "/" + path.lstrip("/")
            else:
                url = path

        query_params = deepcopy(interface.get("query_params") or {})
        if not include_query or not query_params:
            return url

        parsed = urlparse(url)
        existing_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        existing_query.update({str(key): str(value) for key, value in query_params.items()})
        return urlunparse(parsed._replace(query=urlencode(existing_query, doseq=True)))

    def _render_requests_snippet(
        self,
        method: str,
        full_url: str,
        headers: Dict[str, Any],
        query_params: Dict[str, Any],
        body: Any,
    ) -> str:
        lines = [
            "import requests",
            "",
            f"url = {json.dumps(full_url, ensure_ascii=False)}",
            f"headers = {json.dumps(headers or {}, ensure_ascii=False, indent=2)}",
        ]
        if query_params:
            lines.append(f"params = {json.dumps(query_params, ensure_ascii=False, indent=2)}")
        if body not in (None, "", {}, []):
            lines.append(f"payload = {json.dumps(body, ensure_ascii=False, indent=2)}")
        lines.append("")

        request_parts = [f"response = requests.{method.lower()}(", "    url,"]
        if headers:
            request_parts.append("    headers=headers,")
        if query_params:
            request_parts.append("    params=params,")
        if body not in (None, "", {}, []):
            if isinstance(body, (dict, list)):
                request_parts.append("    json=payload,")
            else:
                request_parts.append("    data=payload,")
        request_parts.extend(
            [
                "    timeout=30,",
                "    verify=False,",
                ")",
                "print(response.status_code)",
                "print(response.text)",
            ]
        )
        lines.extend(request_parts)
        return "\n".join(lines)

    def _render_fetch_snippet(
        self,
        method: str,
        full_url: str,
        headers: Dict[str, Any],
        query_params: Dict[str, Any],
        body: Any,
    ) -> str:
        options: Dict[str, Any] = {"method": method}
        if headers:
            options["headers"] = headers
        if body not in (None, "", {}, []):
            options["body"] = "JSON.stringify(payload)" if isinstance(body, (dict, list)) else str(body)

        lines = [
            f"const url = {json.dumps(full_url, ensure_ascii=False)};",
        ]
        if query_params:
            lines.extend(
                [
                    f"const params = {json.dumps(query_params, ensure_ascii=False, indent=2)};",
                    "const query = new URLSearchParams(params).toString();",
                    "const requestUrl = query ? `${url}${url.includes('?') ? '&' : '?'}${query}` : url;",
                ]
            )
        else:
            lines.append("const requestUrl = url;")
        if body not in (None, "", {}, []):
            lines.append(f"const payload = {json.dumps(body, ensure_ascii=False, indent=2)};")
        lines.extend(
            [
                f"const options = {json.dumps({key: value for key, value in options.items() if key != 'body'}, ensure_ascii=False, indent=2)};",
            ]
        )
        if body not in (None, "", {}, []):
            if isinstance(body, (dict, list)):
                lines.append("options.body = JSON.stringify(payload);")
            else:
                lines.append("options.body = payload;")
        lines.extend(
            [
                "",
                "fetch(requestUrl, options)",
                "  .then((response) => response.text().then((text) => ({ status: response.status, text })))",
                "  .then(({ status, text }) => {",
                "    console.log(status);",
                "    console.log(text);",
                "  });",
            ]
        )
        return "\n".join(lines)

    def _render_curl_snippet(
        self,
        method: str,
        full_url: str,
        headers: Dict[str, Any],
        body: Any,
    ) -> str:
        parts = [f"curl -X {method} {json.dumps(full_url, ensure_ascii=False)}"]
        for key, value in headers.items():
            parts.append(f"  -H {json.dumps(f'{key}: {value}', ensure_ascii=False)}")
        if body not in (None, "", {}, []):
            if isinstance(body, (dict, list)):
                payload = json.dumps(body, ensure_ascii=False)
            else:
                payload = str(body)
            parts.append(f"  -d {json.dumps(payload, ensure_ascii=False)}")
        return " \\\n".join(parts)

    def _extract_path_placeholders(self, path: str) -> set:
        return set(re.findall(r"\{([^}]+)\}", path or ""))

    def _get_content_type(self, headers: Dict[str, Any]) -> str:
        content_type = headers.get("Content-Type") or headers.get("content-type") or ""
        return str(content_type).lower().strip()

    def _serialize_inline(self, value: Any) -> str:
        if value in (None, "", {}, []):
            return "{}" if isinstance(value, dict) else "[]" if isinstance(value, list) else ""
        if isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, sort_keys=True)
        return str(value)

    def _parse_sample_value(self, sample: Any) -> Any:
        if isinstance(sample, str):
            text = sample.strip()
            if not text:
                raise ValueError("响应样例不能为空")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        return deepcopy(sample)

    def _build_presence_template(self, value: Any, depth: int, max_depth: int) -> Any:
        if depth >= max_depth:
            return self._compress_terminal_value(value)

        if isinstance(value, dict):
            return [str(key) for key in value.keys()]

        if isinstance(value, list):
            if not value:
                return []
            first_item = value[0]
            if isinstance(first_item, dict):
                return [str(key) for key in first_item.keys()]
            if isinstance(first_item, list):
                return [self._build_presence_template(first_item, depth + 1, max_depth)]
            return [self._normalize_value(first_item)]

        return self._normalize_value(value)

    def _build_standard_template(self, value: Any, depth: int, max_depth: int) -> Any:
        if depth >= max_depth:
            return self._compress_terminal_value(value)

        if isinstance(value, dict):
            result = {}
            for key, item in value.items():
                if isinstance(item, dict):
                    result[str(key)] = self._build_standard_template(item, depth + 1, max_depth)
                elif isinstance(item, list):
                    if not item:
                        result[str(key)] = []
                    elif isinstance(item[0], dict):
                        result[str(key)] = [str(child_key) for child_key in item[0].keys()]
                    elif isinstance(item[0], list):
                        result[str(key)] = [self._build_standard_template(item[0], depth + 1, max_depth)]
                    else:
                        result[str(key)] = [self._normalize_value(item[0])]
                else:
                    result[str(key)] = self._normalize_value(item)
            return result

        if isinstance(value, list):
            if not value:
                return []
            first_item = value[0]
            if isinstance(first_item, dict):
                return [str(key) for key in first_item.keys()]
            if isinstance(first_item, list):
                return [self._build_standard_template(first_item, depth + 1, max_depth)]
            return [self._normalize_value(first_item)]

        return self._normalize_value(value)

    def _build_strict_template(self, value: Any, depth: int, max_depth: int) -> Any:
        if depth >= max_depth:
            return self._compress_terminal_value(value)

        if isinstance(value, dict):
            return {
                str(key): self._build_strict_template(item, depth + 1, max_depth)
                for key, item in value.items()
            }

        if isinstance(value, list):
            if not value:
                return []
            return [self._build_strict_template(value[0], depth + 1, max_depth)]

        return self._normalize_value(value)

    def _collect_field_paths(self, value: Any, prefix: str, depth: int, max_depth: int) -> List[str]:
        if depth >= max_depth:
            return [prefix]

        if isinstance(value, dict):
            paths: List[str] = []
            for key, item in value.items():
                current_prefix = f"{prefix}.{key}"
                paths.append(current_prefix)
                paths.extend(self._collect_field_paths(item, current_prefix, depth + 1, max_depth))
            return paths

        if isinstance(value, list):
            list_prefix = f"{prefix}[]"
            paths = [list_prefix]
            if value:
                paths.extend(self._collect_field_paths(value[0], list_prefix, depth + 1, max_depth))
            return paths

        return [prefix]

    def _compress_terminal_value(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {}
        if isinstance(value, list):
            return []
        return self._normalize_value(value)

    def _is_auth_related(self, interface: Dict[str, Any]) -> bool:
        headers = interface.get("headers") or {}
        auth_keywords = ("authorization", "token", "api-key", "apikey", "x-auth", "access-key")
        if any(any(keyword in str(key).lower() for keyword in auth_keywords) for key in headers.keys()):
            return True

        auth_text_keywords = ("auth", "login", "logout", "token", "signin", "sign-in", "鉴权", "登录", "认证")
        candidates = [
            interface.get("name"),
            interface.get("path"),
            interface.get("description"),
            " ".join(interface.get("tags") or []),
        ]
        return any(
            any(keyword in str(candidate or "").lower() for keyword in auth_text_keywords)
            for candidate in candidates
        )

    def _has_pagination_hint(self, interface: Dict[str, Any]) -> bool:
        query_params = interface.get("query_params") or {}
        pagination_keys = {"page", "pageNum", "pageNo", "size", "pageSize", "limit", "offset"}
        lower_keys = {str(key).lower() for key in query_params.keys()}
        return any(key.lower() in lower_keys for key in pagination_keys)

    def _has_sort_hint(self, interface: Dict[str, Any]) -> bool:
        query_params = interface.get("query_params") or {}
        sort_keys = {"sort", "order", "orderBy", "sortBy", "direction", "filter", "keyword"}
        lower_keys = {str(key).lower() for key in query_params.keys()}
        return any(key.lower() in lower_keys for key in sort_keys)

    def _decide_regression_priority(self, interface: Dict[str, Any]) -> str:
        method = interface.get("method", "GET")
        if method in {"POST", "PUT", "PATCH", "DELETE"}:
            return "high"
        if interface.get("path_params") or self._is_auth_related(interface):
            return "high"
        if interface.get("body") not in (None, "", {}, []):
            return "high"
        if interface.get("query_params"):
            return "medium"
        return "low"
