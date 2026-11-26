"""接口研发辅助工具：变更分析 / 质量体检 / 回归清单 / 断言模板 / Mock / 调试代码。

所有规则、词表、评分口径、代码片段语言、Mock 默认值、安全护栏、清洗器与运行
上限都来自 ``core/api_dev_registry.py``，下游项目可通过 ``register_*`` 扩展，
不需要修改本文件（拓展性视角，不局限于当前业务）。
"""
from __future__ import annotations

import json
import math
import re
from collections import Counter
from copy import deepcopy
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

from qa_toolkit.core import api_dev_registry as dev_registry


# ---------------------------------------------------------------------------
# 生成的 Mock 服务脚本模板（静态字符串 + 占位符，避免 f-string 转义与代码注入）
# ---------------------------------------------------------------------------

_MOCK_SCRIPT_TEMPLATE = r'''"""自动生成的本地 Mock 服务（含资源护栏与响应头清洗）"""
import argparse
import json
import re
import time
from copy import deepcopy
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

DEFAULT_HOST = __QA_DEV_HOST__
DEFAULT_PORT = __QA_DEV_PORT__
DEFAULT_DELAY_MS = __QA_DEV_DELAY_MS__
ENABLE_CORS = __QA_DEV_ENABLE_CORS__
CORS_ORIGIN = __QA_DEV_CORS_ORIGIN__
ROUTES = json.loads(__QA_DEV_ROUTES__)

MAX_REQUEST_BODY_BYTES = __QA_DEV_MAX_REQUEST_BODY__
MAX_RESPONSE_BODY_CHARS = __QA_DEV_MAX_RESPONSE_BODY__
MAX_HEADER_VALUE_CHARS = __QA_DEV_MAX_HEADER_VALUE__
MAX_ROUTES = __QA_DEV_MAX_ROUTES__
HEADER_NAME_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")


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
    pattern = re.sub(r"\\\{[^/]*\\\}", r"([^/]+)", pattern)
    return re.compile("^" + pattern + "$")


def find_route(method, path):
    actual_path = normalize_path(path)
    for route in ROUTES[:MAX_ROUTES]:
        if route.get("method", "GET").upper() != method.upper():
            continue
        if compile_route_pattern(route.get("path", "/")).match(actual_path):
            return route
    return None


def safe_header_value(value):
    """拒绝 CRLF / 控制字符 / 超长值，防止 HTTP 响应头注入。"""
    text = "" if value is None else str(value)
    if any(ord(ch) < 32 and ch != "\t" for ch in text) or "\x7f" in text:
        return None
    if len(text) > MAX_HEADER_VALUE_CHARS:
        return None
    return text


class MockRequestHandler(BaseHTTPRequestHandler):
    server_version = "GeneratedMockServer/2.0"

    def _set_headers(self, status_code, headers):
        self.send_response(int(status_code))
        header_map = clone_value(headers or {})
        if ENABLE_CORS:
            header_map.setdefault("Access-Control-Allow-Origin", CORS_ORIGIN)
            header_map.setdefault("Access-Control-Allow-Methods", "GET, POST, PUT, PATCH, DELETE, OPTIONS")
            header_map.setdefault("Access-Control-Allow-Headers", "Content-Type, Authorization")
        for key, value in header_map.items():
            cleaned = safe_header_value(value)
            if cleaned is None or not HEADER_NAME_RE.match(str(key)):
                continue
            self.send_header(str(key), cleaned)
        self.end_headers()

    def _read_body(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
        except (TypeError, ValueError):
            return None
        if content_length <= 0:
            return None
        if content_length > MAX_REQUEST_BODY_BYTES:
            self._too_large = True
            return None
        raw_body = self.rfile.read(content_length)
        try:
            return json.loads(raw_body.decode("utf-8"))
        except Exception:
            return raw_body.decode("utf-8", errors="replace")

    def _dispatch(self):
        self._too_large = False
        if len(ROUTES) > MAX_ROUTES:
            self._set_headers(503, {"Content-Type": "application/json; charset=utf-8"})
            self.wfile.write(json.dumps({"success": False, "message": "route limit exceeded"}).encode("utf-8"))
            return
        parsed = urlparse(self.path)
        route = find_route(self.command, parsed.path)
        if not route:
            payload = {"success": False, "message": "mock route not found",
                       "method": self.command, "path": parsed.path}
            self._set_headers(404, {"Content-Type": "application/json; charset=utf-8"})
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
            return

        request_body = self._read_body()
        if self._too_large:
            self._set_headers(413, {"Content-Type": "application/json; charset=utf-8"})
            self.wfile.write(json.dumps({"success": False, "message": "request body too large"}).encode("utf-8"))
            return

        if DEFAULT_DELAY_MS > 0:
            time.sleep(DEFAULT_DELAY_MS / 1000)

        response_body = clone_value(route.get("response_body"))
        if isinstance(response_body, dict):
            response_body.setdefault("_request", {
                "method": self.command,
                "path": parsed.path,
                "query": parse_qs(parsed.query),
                "body": request_body,
            })

        headers = clone_value(route.get("headers") or {})
        is_json = isinstance(response_body, (dict, list))
        headers.setdefault("Content-Type",
                           "application/json; charset=utf-8" if is_json else "text/plain; charset=utf-8")
        self._set_headers(route.get("status_code", 200), headers)

        if self.command == "HEAD":
            return
        body = json.dumps(response_body, ensure_ascii=False, indent=2) if is_json else str(response_body)
        if len(body) > MAX_RESPONSE_BODY_CHARS:
            body = body[:MAX_RESPONSE_BODY_CHARS]
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
        self._set_headers(204, {
            "Content-Type": "text/plain; charset=utf-8",
            "Access-Control-Max-Age": "600",
        })


def main():
    parser = argparse.ArgumentParser(description="运行自动生成的 Mock 服务")
    parser.add_argument("--host", default=DEFAULT_HOST, help="监听地址")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="监听端口")
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), MockRequestHandler)
    print("Mock server is running on http://{}:{}".format(args.host, args.port))
    print("Loaded routes: {}".format(min(len(ROUTES), MAX_ROUTES)))
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nMock server stopped")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
'''


class InterfaceDevTools:
    """接口研发辅助工具（规则与默认值全部注册化）。"""

    def __init__(self) -> None:
        self.last_warnings: List[str] = []
        self.last_truncation: Dict[str, Any] = {}

    # ------------------------------------------------------------------
    # 告警与截断观测
    # ------------------------------------------------------------------

    def _warn(self, message: str) -> None:
        if message and message not in self.last_warnings:
            self.last_warnings.append(message)

    def _begin(self, **config: Any) -> Dict[str, Any]:
        self.last_warnings = []
        self.last_truncation = {}
        return dict(config or {})

    def get_warnings(self) -> List[str]:
        return list(self.last_warnings)

    def get_truncation(self) -> Dict[str, Any]:
        return deepcopy(self.last_truncation)

    def _meta(self, config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "config_snapshot": deepcopy(config),
            "input_signature": dev_registry.compute_signature(config),
            "registry_summary": dev_registry.get_registry_summary(),
            "warnings": self.get_warnings(),
            "truncation": self.get_truncation(),
        }

    def _limit_interfaces(self, interfaces: Sequence[Dict[str, Any]], label: str) -> List[Dict[str, Any]]:
        limits = dev_registry.get_dev_limits()
        total = len(interfaces or [])
        kept = list(interfaces or [])[:limits.max_interfaces]
        if total > len(kept):
            self.last_truncation[f"{label}_interfaces"] = {"total": total, "kept": len(kept)}
            self._warn(f"{label} 共 {total} 个接口，超过上限 {limits.max_interfaces}，仅处理前 {len(kept)} 个")
        return kept

    # ------------------------------------------------------------------
    # 1. 接口变更对比
    # ------------------------------------------------------------------

    def compare_interfaces(
        self,
        baseline_interfaces: List[Dict[str, Any]],
        target_interfaces: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """对比两份接口定义并输出摘要；重复 method+path 逐条配对，不静默覆盖。"""
        config = self._begin(baseline_count=len(baseline_interfaces or []),
                             target_count=len(target_interfaces or []))
        baseline = [self._normalize_interface(item) for item in
                    self._limit_interfaces(baseline_interfaces or [], "baseline")]
        target = [self._normalize_interface(item) for item in
                  self._limit_interfaces(target_interfaces or [], "target")]

        baseline_groups: Dict[str, List[Dict[str, Any]]] = {}
        target_groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in baseline:
            baseline_groups.setdefault(self._build_interface_key(item), []).append(item)
        for item in target:
            target_groups.setdefault(self._build_interface_key(item), []).append(item)

        baseline_duplicates = sorted(key for key, group in baseline_groups.items() if len(group) > 1)
        target_duplicates = sorted(key for key, group in target_groups.items() if len(group) > 1)

        added: List[Dict[str, Any]] = []
        removed: List[Dict[str, Any]] = []
        changed: List[Dict[str, Any]] = []
        high_risk_changes: List[Dict[str, Any]] = []
        unchanged_count = 0
        unmatched_definitions: List[Dict[str, Any]] = []

        for key in sorted(set(baseline_groups) | set(target_groups)):
            b_items = baseline_groups.get(key, [])
            t_items = target_groups.get(key, [])

            if not b_items:
                added.extend(self._build_summary_item(item) for item in t_items)
                continue
            if not t_items:
                removed.extend(self._build_summary_item(item) for item in b_items)
                continue

            # 先按完整内容精确配对（重复定义也能逐条对上），剩余按位置配对做 diff。
            remaining_b = list(b_items)
            remaining_t = list(t_items)
            for b_item in list(remaining_b):
                exact = next((t_item for t_item in remaining_t if t_item == b_item), None)
                if exact is not None:
                    unchanged_count += 1
                    remaining_b.remove(b_item)
                    remaining_t.remove(exact)

            pairs = min(len(remaining_b), len(remaining_t))
            for index in range(pairs):
                b_item, t_item = remaining_b[index], remaining_t[index]
                field_changes, risk_level = self._diff_interface(b_item, t_item)
                if not field_changes:
                    unchanged_count += 1
                    continue
                change_item = {
                    "key": key,
                    "name": t_item.get("name") or b_item.get("name"),
                    "method": t_item.get("method") or b_item.get("method"),
                    "path": t_item.get("path") or b_item.get("path"),
                    "risk_level": risk_level,
                    "changes": field_changes,
                }
                changed.append(change_item)
                if risk_level == "high":
                    high_risk_changes.append(change_item)

            # 无法配对的重复定义显式列出，绝不静默丢弃。
            for item in remaining_b[pairs:]:
                removed.append(self._build_summary_item(item))
                unmatched_definitions.append({"side": "baseline", "key": key, "name": item.get("name")})
            for item in remaining_t[pairs:]:
                added.append(self._build_summary_item(item))
                unmatched_definitions.append({"side": "target", "key": key, "name": item.get("name")})

        if unmatched_definitions:
            self._warn(f"发现 {len(unmatched_definitions)} 条重复定义无法一一配对，已显式计入新增/删除，请人工复核")

        result = {
            "summary": {
                "baseline_total": len(baseline_interfaces or []),
                "target_total": len(target_interfaces or []),
                "added_count": len(added),
                "removed_count": len(removed),
                "changed_count": len(changed),
                "unchanged_count": unchanged_count,
                "high_risk_count": len(high_risk_changes),
                "baseline_duplicate_count": len(baseline_duplicates),
                "target_duplicate_count": len(target_duplicates),
            },
            "duplicates": {
                "baseline": baseline_duplicates,
                "target": target_duplicates,
                "unmatched_definitions": unmatched_definitions,
            },
            "added": added,
            "removed": removed,
            "changed": changed,
            "high_risk_changes": high_risk_changes,
            "text_summary": dev_registry.build_text_summary("diff", {
                "baseline_total": len(baseline_interfaces or []),
                "target_total": len(target_interfaces or []),
                "added_count": len(added), "removed_count": len(removed),
                "changed_count": len(changed), "high_risk_count": len(high_risk_changes),
            }),
        }
        result.update(self._meta(config))
        return result

    def build_markdown_report(self, diff_result: Dict[str, Any]) -> str:
        """生成 Markdown 版本的接口差异报告（动态文本统一转义）。"""
        summary = diff_result.get("summary", {})
        esc = dev_registry.escape_markdown_cell
        lines = [
            "# 接口变更分析报告", "", "## 概览",
            f"- 基线接口数: {summary.get('baseline_total', 0)}",
            f"- 当前接口数: {summary.get('target_total', 0)}",
            f"- 新增接口: {summary.get('added_count', 0)}",
            f"- 删除接口: {summary.get('removed_count', 0)}",
            f"- 变更接口: {summary.get('changed_count', 0)}",
            f"- 高风险变更: {summary.get('high_risk_count', 0)}",
            "",
        ]
        if diff_result.get("text_summary"):
            lines.extend([f"> {esc(diff_result['text_summary'])}", ""])
        for section_title, items in [
            ("新增接口", diff_result.get("added", [])),
            ("删除接口", diff_result.get("removed", [])),
        ]:
            lines.append(f"## {section_title}")
            if not items:
                lines.append("- 无")
            else:
                for item in items:
                    lines.append(f"- `{esc(item.get('method', 'GET'))} {esc(item.get('path', '/'))}` {esc(item.get('name', ''))}")
            lines.append("")

        lines.append("## 变更接口")
        if not diff_result.get("changed"):
            lines.append("- 无")
        else:
            for item in diff_result.get("changed", []):
                risk_text = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(item.get("risk_level"), "未知")
                lines.append(f"### `{esc(item.get('method', 'GET'))} {esc(item.get('path', '/'))}` {esc(item.get('name', ''))}")
                lines.append(f"- 风险等级: {risk_text}")
                for change in item.get("changes", []):
                    lines.append(f"- {esc(change.get('label', ''))}: {esc(change.get('message', ''))}")
                lines.append("")

        warnings = diff_result.get("warnings") or []
        truncation = diff_result.get("truncation") or {}
        if warnings or truncation:
            lines.extend(["## 运行告警与截断", ""])
            lines.extend(f"- {esc(item)}" for item in warnings)
            if truncation:
                lines.append(f"- 截断明细: {esc(json.dumps(truncation, ensure_ascii=False))}")
            lines.append("")
        return "\n".join(lines).strip() + "\n"

    # ------------------------------------------------------------------
    # 2. 标准化导出
    # ------------------------------------------------------------------

    def export_normalized_interfaces(self, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """将接口定义标准化并导出多种格式（附配置快照与输入签名）。"""
        config = self._begin(interface_count=len(interfaces or []))
        kept = self._limit_interfaces(interfaces or [], "normalize")
        normalized_interfaces = [self._normalize_interface(item) for item in kept]
        method_distribution: Dict[str, int] = {}
        tag_distribution: Dict[str, int] = {}
        body_count = auth_related_count = missing_response_count = 0

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
        export_payload = {"summary": summary, "interfaces": normalized_interfaces}
        result = {
            "summary": summary,
            "interfaces": normalized_interfaces,
            "json_artifact": dev_registry.strict_json_dumps(export_payload, indent=2),
            "markdown_artifact": self._build_interface_catalog_markdown(normalized_interfaces, summary),
            "text_artifact": self._build_structured_text_export(normalized_interfaces),
            "text_summary": dev_registry.build_text_summary("normalize", summary),
        }
        result.update(self._meta(config))
        return result

    # ------------------------------------------------------------------
    # 3. 接口文档质量体检
    # ------------------------------------------------------------------

    def analyze_interface_quality(self, interfaces: List[Dict[str, Any]]) -> Dict[str, Any]:
        """检查接口定义质量并输出问题清单（规则、权重、阈值全部注册表驱动）。"""
        config = self._begin(interface_count=len(interfaces or []))
        kept = self._limit_interfaces(interfaces or [], "quality")
        normalized_interfaces = [self._normalize_interface(item) for item in kept]
        issues: List[Dict[str, Any]] = []
        key_index_map: Dict[str, List[Dict[str, Any]]] = {}
        status_buckets: Dict[str, int] = {}

        def add(index: int, item: Dict[str, Any], rule_key: str, **fmt: Any) -> None:
            severity, message = dev_registry.build_quality_issue(rule_key, **fmt)
            if severity and message:
                issues.append(self._build_issue(index, item, severity, rule_key, message))

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
                add(index, item, "missing_name")
            if not item.get("description"):
                add(index, item, "missing_description")
            if expected_response in (None, "", {}, []):
                add(index, item, "missing_expected_response")
            if missing_path_params:
                add(index, item, "path_param_missing", detail=", ".join(missing_path_params))
            if extra_path_params:
                add(index, item, "path_param_extra", detail=", ".join(extra_path_params))
            empty_values = [key for key, value in path_params.items()
                            if key in placeholders and value in (None, "", [])]
            if empty_values:
                add(index, item, "path_param_empty", detail=", ".join(sorted(empty_values)))
            if method == "GET" and body not in (None, "", {}, []):
                add(index, item, "get_with_body")

            if method in {"POST", "PUT", "PATCH"}:
                if body in (None, "", {}, []):
                    add(index, item, "empty_request_body", method=method)
                else:
                    if not content_type:
                        add(index, item, "missing_content_type")
                    request_format = item.get("request_format", "auto")
                    if request_format in {"json", "data_json"} and "application/json" not in content_type:
                        add(index, item, "json_content_type_mismatch")
                    if request_format == "form" and not any(
                        token in content_type for token in ("application/x-www-form-urlencoded", "multipart/form-data")
                    ):
                        add(index, item, "form_content_type_mismatch")
            if not item.get("tags"):
                add(index, item, "missing_tags")

            status_value = item.get("raw_expected_status")
            if status_value is None:
                status_value = item.get("expected_status")
            status_info = dev_registry.classify_status_code(status_value, 200)
            status_buckets[status_info["bucket"]] = status_buckets.get(status_info["bucket"], 0) + 1
            if not status_info["valid"]:
                add(index, item, "invalid_expected_status", detail=status_info["code"])
            elif status_info["warn"]:
                add(index, item, "unexpected_status_bucket", detail=status_info["label"])

        duplicate_groups = []
        for key, entries in key_index_map.items():
            if len(entries) <= 1:
                continue
            duplicate_groups.append({
                "key": key,
                "indexes": [entry["index"] for entry in entries],
                "method": entries[0]["interface"].get("method", "GET"),
                "path": entries[0]["interface"].get("path", "/"),
                "count": len(entries),
            })
            indexes = ", ".join(str(entry["index"]) for entry in entries)
            for entry in entries:
                add(entry["index"], entry["interface"], "duplicate_endpoint", detail=indexes)

        severity_order = dev_registry.get_severity_order()
        sorted_issues = sorted(
            issues,
            key=lambda item: (severity_order.get(item.get("severity", "low"), 99),
                              item.get("index", 0), item.get("category", "")),
        )
        severity_counts = {"high": 0, "medium": 0, "low": 0}
        category_counts: Dict[str, int] = {}
        for issue in sorted_issues:
            severity = issue.get("severity", "low")
            category = issue.get("category", "unknown")
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            category_counts[category] = category_counts.get(category, 0) + 1

        weights = dev_registry.get_score_weights()
        score = max(0, 100 - sum(severity_counts.get(level, 0) * weight
                                 for level, weight in weights.items()))
        level = dev_registry.health_level(score)
        summary = {
            "interface_count": len(normalized_interfaces),
            "issue_count": len(sorted_issues),
            "high_count": severity_counts.get("high", 0),
            "medium_count": severity_counts.get("medium", 0),
            "low_count": severity_counts.get("low", 0),
            "duplicate_count": len(duplicate_groups),
            "health_score": score,
            "health_level": level,
            "status_buckets": dict(status_buckets),
        }
        # dataframe 是 canvas，读屏/自动化读不到；把高风险结论补进文字摘要。
        text_summary = dev_registry.build_text_summary("quality", summary)
        highlights = [str(item.get("message", "")) for item in sorted_issues
                      if item.get("severity") == "high"][:3]
        if highlights:
            text_summary += " 高风险提示：" + "；".join(highlights)
        result = {
            "summary": summary,
            "issues": sorted_issues,
            "duplicate_groups": duplicate_groups,
            "category_counts": category_counts,
            "status_buckets": dict(status_buckets),
            "text_summary": text_summary,
        }
        result.update(self._meta(config))
        return result

    def build_quality_markdown_report(self, quality_result: Dict[str, Any]) -> str:
        """生成接口文档体检报告（动态文本统一转义）。"""
        esc = dev_registry.escape_markdown_cell
        summary = quality_result.get("summary", {})
        lines = [
            "# 接口文档体检报告", "", "## 概览",
            f"- 接口总数: {summary.get('interface_count', 0)}",
            f"- 问题总数: {summary.get('issue_count', 0)}",
            f"- 高风险问题: {summary.get('high_count', 0)}",
            f"- 中风险问题: {summary.get('medium_count', 0)}",
            f"- 低风险问题: {summary.get('low_count', 0)}",
            f"- 重复接口组数: {summary.get('duplicate_count', 0)}",
            f"- 健康分: {summary.get('health_score', 0)} ({summary.get('health_level', '未知')})",
            f"- 期望状态码分桶: {esc(dev_registry.strict_json_dumps(summary.get('status_buckets', {}), ensure_ascii=False))}",
            "",
        ]
        if quality_result.get("text_summary"):
            lines.extend([f"> {esc(quality_result['text_summary'])}", ""])
        lines.append("## 重复接口")
        duplicate_groups = quality_result.get("duplicate_groups", [])
        if not duplicate_groups:
            lines.append("- 无")
        else:
            for item in duplicate_groups:
                lines.append(f"- `{esc(item.get('method', 'GET'))} {esc(item.get('path', '/'))}` 出现 {item.get('count', 0)} 次，序号: {', '.join(map(str, item.get('indexes', [])))}")
        lines.extend(["", "## 问题明细"])
        issues = quality_result.get("issues", [])
        if not issues:
            lines.append("- 未发现问题")
        else:
            for issue in issues:
                severity_text = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(issue.get("severity"), "未知")
                lines.append(f"- [{severity_text}] 序号 {issue.get('index', 0)} | `{esc(issue.get('method', 'GET'))} {esc(issue.get('path', '/'))}` | {esc(issue.get('message', ''))}")
        warnings = quality_result.get("warnings") or []
        if warnings:
            lines.extend(["", "## 运行告警"])
            lines.extend(f"- {esc(item)}" for item in warnings)
        return "\n".join(lines).strip() + "\n"

    # ------------------------------------------------------------------
    # 4. 回归清单
    # ------------------------------------------------------------------

    def generate_regression_checklist(
        self,
        interfaces: List[Dict[str, Any]],
        include_negative: bool = True,
        include_auth_checks: bool = True,
        include_performance_checks: bool = True,
    ) -> Dict[str, Any]:
        """根据接口定义生成回归清单（文案、优先级、词表全部注册表驱动）。"""
        config = self._begin(
            interface_count=len(interfaces or []),
            include_negative=bool(include_negative),
            include_auth_checks=bool(include_auth_checks),
            include_performance_checks=bool(include_performance_checks),
        )
        kept = self._limit_interfaces(interfaces or [], "checklist")
        normalized_interfaces = [self._normalize_interface(item) for item in kept]
        templates = dev_registry.get_checklist_templates()
        checklist_items: List[Dict[str, Any]] = []
        priority_counts = {"high": 0, "medium": 0, "low": 0}

        for index, item in enumerate(normalized_interfaces, start=1):
            focus_points: List[str] = []
            status_value = item.get("raw_expected_status")
            if status_value is None:
                status_value = item.get("expected_status")
            status_info = dev_registry.classify_status_code(status_value, 200)
            checklist = [templates.get("status", "校验状态码").format(expected_status=item.get("expected_status", 200))]
            if not status_info["valid"]:
                self._warn(f"接口 {item.get('name') or index} 的期望状态码 {status_info['code']} 非法，回归清单已标注")
            elif status_info["warn"]:
                focus_points.append("非成功状态码")
                checklist.append(f"确认 {status_info['label']} 是刻意设计的契约，而非误填")
            if item.get("expected_response") not in (None, "", {}, []):
                checklist.append(templates.get("response_fields", "校验关键响应字段和业务码"))
                focus_points.append("响应结构")
            else:
                checklist.append(templates.get("response_missing", "补充最小可用响应断言"))
                focus_points.append("响应样例缺失")
            if include_performance_checks:
                checklist.append(templates.get("performance", "关注响应时间是否在可接受范围内"))
            if item.get("query_params"):
                focus_points.append("查询参数")
                checklist.append(templates.get("query_normal", "覆盖查询参数正常组合"))
                if include_negative:
                    checklist.append(templates.get("query_negative", "验证查询参数缺失、非法值、边界值"))
            if item.get("path_params"):
                focus_points.append("路径参数")
                checklist.append(templates.get("path_normal", "验证路径参数替换后的资源是否正确"))
                if include_negative:
                    checklist.append(templates.get("path_negative", "验证无效路径参数、越权访问或不存在资源"))
            if item.get("body") not in (None, "", {}, []):
                focus_points.append("请求体")
                checklist.append(templates.get("body_normal", "覆盖请求体必填字段、类型和边界值"))
                if include_negative:
                    checklist.append(templates.get("body_negative", "验证请求体字段缺失、超长、非法格式"))
            if include_auth_checks and self._is_auth_related(item):
                focus_points.append("鉴权")
                checklist.append(templates.get("auth_normal", "验证有效鉴权下接口可正常访问"))
                if include_negative:
                    checklist.append(templates.get("auth_negative", "验证缺少鉴权、鉴权失效、权限不足场景"))
            if item.get("method") in {"POST", "PUT", "PATCH", "DELETE"}:
                focus_points.append("数据变更")
                checklist.append(templates.get("mutation_normal", "确认接口对数据的新增、更新或删除结果正确"))
                if include_negative:
                    checklist.append(templates.get("mutation_negative", "验证重复提交、幂等性或回滚处理"))
            if self._has_pagination_hint(item):
                focus_points.append("分页")
                checklist.append(templates.get("pagination", "验证分页参数、总数、页码边界和空列表场景"))
            if self._has_sort_hint(item):
                focus_points.append("排序筛选")
                checklist.append(templates.get("sort", "验证排序字段和筛选条件组合"))

            priority = dev_registry.decide_priority(item)
            priority_counts[priority] = priority_counts.get(priority, 0) + 1
            checklist_items.append({
                "index": index,
                "name": item.get("name", "未命名接口"),
                "method": item.get("method", "GET"),
                "path": item.get("path", "/"),
                "priority": priority,
                "status_bucket": status_info["label"],
                "status_valid": status_info["valid"],
                "focus_points": sorted(dict.fromkeys(focus_points)) or ["基础可用性"],
                "checklist": checklist,
            })

        summary = {
            "interface_count": len(checklist_items),
            "high_priority_count": priority_counts.get("high", 0),
            "medium_priority_count": priority_counts.get("medium", 0),
            "low_priority_count": priority_counts.get("low", 0),
            "check_item_count": sum(len(item.get("checklist", [])) for item in checklist_items),
        }
        checklist_rows = [{
            "序号": item.get("index", 0),
            "优先级": {"high": "高", "medium": "中", "low": "低"}.get(item.get("priority"), "低"),
            "方法": item.get("method", "GET"),
            "路径": item.get("path", "/"),
            "接口": item.get("name", "未命名接口"),
            "状态分桶": item.get("status_bucket", "未分类"),
            "关注点": "、".join(item.get("focus_points", [])),
            "建议检查项数": len(item.get("checklist", [])),
        } for item in checklist_items]

        result = {
            "summary": summary,
            "items": checklist_items,
            "rows": checklist_rows,
            "markdown_artifact": self._build_regression_markdown(checklist_items, summary),
            "json_artifact": dev_registry.strict_json_dumps(
                {"summary": summary, "items": checklist_items}, indent=2),
            "text_summary": dev_registry.build_text_summary("checklist", summary),
        }
        result.update(self._meta(config))
        return result

    # ------------------------------------------------------------------
    # 5. 断言模板
    # ------------------------------------------------------------------

    def generate_assertion_template(
        self,
        sample: Any,
        template_style: str = "标准断言",
        max_depth: int = 4,
    ) -> Dict[str, Any]:
        """根据响应样例生成断言模板（风格注册化、深度钳制、循环引用保护）。"""
        limits = dev_registry.get_dev_limits()
        config = self._begin(template_style=str(template_style), requested_max_depth=max_depth)
        style, warning = dev_registry.resolve_assertion_style(template_style)
        if warning:
            self._warn(warning)
        depth = dev_registry.clamp_int(max_depth, 4, 1, limits.max_recursion_depth)
        if depth != max_depth:
            self._warn(f"结构展开深度 {max_depth!r} 已钳制到 1-{limits.max_recursion_depth} 范围")
        parsed_sample = self._parse_sample_value(sample)

        if style == "presence":
            template = self._build_presence_template(parsed_sample, 0, depth)
        elif style == "strict":
            template = self._build_strict_template(parsed_sample, 0, depth)
        else:
            template = self._build_standard_template(parsed_sample, 0, depth)

        field_paths = sorted(dict.fromkeys(
            self._collect_field_paths(parsed_sample, "response", 0, depth)
        ))
        if len(field_paths) > limits.max_field_paths:
            self.last_truncation["field_paths"] = {"total": len(field_paths), "kept": limits.max_field_paths}
            self._warn(f"字段路径共 {len(field_paths)} 条，仅保留前 {limits.max_field_paths} 条")
            field_paths = field_paths[:limits.max_field_paths]

        case_fragment = {"expected_status": 200, "expected_response": template}
        result = {
            "template_style": style,
            "sample_type": type(parsed_sample).__name__,
            "field_count": len(field_paths),
            "field_paths": field_paths,
            "template": template,
            "template_json": dev_registry.strict_json_dumps(template, indent=2),
            "case_fragment_json": dev_registry.strict_json_dumps(case_fragment, indent=2),
            "text_summary": dev_registry.build_text_summary("assertion", {
                "template_style": style, "sample_type": type(parsed_sample).__name__,
                "field_count": len(field_paths),
            }),
        }
        result.update(self._meta(config))
        return result

    # ------------------------------------------------------------------
    # 6. Mock 服务脚本
    # ------------------------------------------------------------------

    def _clamp_with_warning(self, value: Any, default: int, minimum: int,
                            maximum: int, label: str) -> int:
        """钳制运行参数并把「被改过」这件事明确告知用户，不做静默回落。"""
        cleaned = dev_registry.clamp_int(value, default, minimum, maximum)
        try:
            numeric = int(value)
        except (TypeError, ValueError, OverflowError):
            if value not in (None, "", 0):
                self._warn(f"{label} {value!r} 不是合法整数，已回落为 {cleaned}")
            return cleaned
        if numeric != cleaned:
            self._warn(f"{label} {numeric} 超出 {minimum}-{maximum}，已钳制为 {cleaned}")
        return cleaned

    def generate_mock_server_script(
        self,
        interfaces: List[Dict[str, Any]],
        host: str = "",
        port: int = 0,
        enable_cors: Optional[bool] = None,
        delay_ms: int = 0,
    ) -> str:
        """根据接口定义生成可直接运行的 Mock 服务脚本（含资源护栏与安全默认值）。"""
        limits = dev_registry.get_dev_limits()
        config = self._begin(interface_count=len(interfaces or []))
        safe_host = str(host or "").strip() or limits.default_mock_host
        # host 只允许主机名/IP 字面量，不允许空格、分号等 shell/命令注入内容。
        if not re.fullmatch(r"[A-Za-z0-9._:-]+", safe_host):
            self._warn(f"非法监听地址 {safe_host!r}，已回落为 {limits.default_mock_host}")
            safe_host = limits.default_mock_host
        # 0 / 空值表示「使用注册的默认端口」，不能把它当真实端口钳到 min_port。
        requested_port = limits.default_mock_port if port in (None, "", 0) else port
        safe_port = self._clamp_with_warning(
            requested_port, limits.default_mock_port, limits.min_port, limits.max_port, "Mock 端口")
        safe_delay = self._clamp_with_warning(delay_ms, 0, 0, limits.max_delay_ms, "Mock 延迟(ms)")
        cors = limits.default_enable_cors if enable_cors is None else bool(enable_cors)

        kept = self._limit_interfaces(interfaces or [], "mock")
        if len(kept) > limits.max_mock_routes:
            self.last_truncation["mock_routes"] = {"total": len(kept), "kept": limits.max_mock_routes}
            self._warn(f"Mock 路由共 {len(kept)} 条，超过上限 {limits.max_mock_routes}，仅保留前 {limits.max_mock_routes} 条")
        kept = kept[:limits.max_mock_routes]

        routes = []
        for interface in kept:
            item = self._normalize_interface(interface)
            response_body = deepcopy(item.get("expected_response"))
            if response_body in (None, "", {}, []):
                response_body = {
                    "success": True,
                    "message": f"mock response for {item['name']}",
                    "path": item.get("path", ""),
                    "method": item.get("method", "GET"),
                }
            headers, warnings = dev_registry.build_mock_response_headers(
                item.get("headers") or {}, response_body,
            )
            explicit = interface.get("mock_response_headers")
            if isinstance(explicit, dict):
                cleaned, extra_warnings = dev_registry.validate_request_headers(explicit)
                headers.update(cleaned)
                warnings.extend(extra_warnings)
            for message in warnings:
                self._warn(message)
            serialized = dev_registry.strict_json_dumps(response_body)
            if len(serialized) > limits.max_response_body_chars:
                self._warn("存在超长期望响应，生成脚本会按上限截断响应体")
            routes.append({
                "name": item.get("name", "未命名接口"),
                "method": item.get("method", "GET"),
                "path": item.get("path", "/"),
                "status_code": item.get("expected_status", 200),
                "response_body": response_body,
                "headers": headers,
            })

        route_json = dev_registry.strict_json_dumps(routes, indent=2)
        placeholders = {
            "__QA_DEV_HOST__": repr(safe_host),
            "__QA_DEV_PORT__": str(safe_port),
            "__QA_DEV_DELAY_MS__": str(safe_delay),
            "__QA_DEV_ENABLE_CORS__": repr(cors),
            "__QA_DEV_CORS_ORIGIN__": repr(limits.default_cors_origin),
            "__QA_DEV_ROUTES__": repr(route_json),
            "__QA_DEV_MAX_REQUEST_BODY__": str(limits.max_request_body_bytes),
            "__QA_DEV_MAX_RESPONSE_BODY__": str(limits.max_response_body_chars),
            "__QA_DEV_MAX_HEADER_VALUE__": str(limits.max_header_value_chars),
            "__QA_DEV_MAX_ROUTES__": str(limits.max_mock_routes),
        }
        script = re.sub(
            r"__QA_DEV_[A-Z_]+__",
            lambda match: placeholders.get(match.group(0), match.group(0)),
            _MOCK_SCRIPT_TEMPLATE,
        )
        if len(script) > limits.max_script_chars:
            self._warn("生成的 Mock 脚本超过体积上限，请减少接口数或响应体大小")
            return "# Mock 脚本体积超过上限，请减少接口数或响应体大小后重试\n"
        return script

    # ------------------------------------------------------------------
    # 7. 请求代码片段
    # ------------------------------------------------------------------

    def generate_request_snippet(
        self,
        interface: Dict[str, Any],
        language: str = "Python requests",
        base_url: str = "",
    ) -> str:
        """生成接口调试代码片段（语言注册化 + 方法白名单 + 目标地址校验）。"""
        limits = dev_registry.get_dev_limits()
        config = self._begin(language=str(language), base_url=base_url)
        item = self._normalize_interface(interface)
        spec, warning = dev_registry.resolve_snippet_language(language)
        if spec is None:
            self._warn(warning)
            return f"# {warning}\n"
        renderer = dev_registry.get_snippet_renderer(spec.renderer_key)
        if renderer is None:
            self._warn(f"代码类型 {spec.label!r} 缺少渲染器 {spec.renderer_key!r}")
            return f"# 代码类型 {spec.label!r} 尚未注册渲染器\n"

        headers, header_warnings = dev_registry.validate_request_headers(item.get("headers") or {})
        for message in header_warnings:
            self._warn(message)

        actual_base = str(base_url or "").strip()
        if actual_base:
            ok, reason = dev_registry.validate_target_url(actual_base)
            if not ok:
                self._warn(f"目标地址校验失败：{reason}")
                return f"# 目标地址校验失败：{reason}\n# 未生成任何调试代码片段，请修正基础 URL 后重试\n"

        full_url = self._build_full_url(item, actual_base, include_query=spec.include_query_in_url)
        method = item["method"]  # 已由 _normalize_interface 走白名单
        options = {
            "timeout_seconds": limits.default_timeout_seconds,
            "verify_ssl": limits.default_verify_ssl,
        }
        return renderer(method, full_url, headers, item.get("query_params") or {},
                        item.get("body"), options)

    # ------------------------------------------------------------------
    # 归一化与内部工具
    # ------------------------------------------------------------------

    def _build_interface_key(self, interface: Dict[str, Any]) -> str:
        item = self._normalize_interface(interface)
        return f"{item['method']} {self._normalize_path(item['path'])}"

    def _build_interface_value(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        return self._normalize_interface(interface)

    def _normalize_interface(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(interface, dict):
            interface = {}
        method, warning = dev_registry.normalize_method(interface.get("method"), "GET")
        if warning:
            self._warn(warning)
        raw_path = str(interface.get("path") or interface.get("url") or "/")
        path = self._normalize_path(raw_path)
        placeholders = self._extract_path_placeholders(path)
        query_params = self._normalize_mapping(interface.get("query_params"))
        inline_query = self._inline_query_items(raw_path)
        if inline_query:
            for key, value in inline_query:
                existing = query_params.get(key)
                if existing is None:
                    query_params[key] = [value]
                elif isinstance(existing, list):
                    existing.append(value)
                else:
                    query_params[key] = [existing, value]
            self._warn(f"接口路径中含 {len(inline_query)} 个查询参数，已合并到 query_params 统一编码，避免重复 query")
        body = interface.get("body")
        parameters = interface.get("parameters")
        # parameters 里的路径占位符只用于替换 URL，不应再作为业务参数发出。
        business_params: Dict[str, Any] = {}
        if isinstance(parameters, dict):
            business_params = {str(key): value for key, value in parameters.items()
                               if str(key) not in placeholders}
            stripped = sorted({str(key) for key in parameters} & placeholders)
            if stripped:
                self._warn(f"parameters 中的路径占位符 {', '.join(stripped)} 已用于替换 URL 路径，不再作为请求参数发送")
        if method == "GET" and not query_params and business_params:
            query_params = self._normalize_mapping(business_params)
        if body is None and method != "GET" and business_params:
            body = business_params
        return {
            "name": str(interface.get("name") or "").strip()[:dev_registry.get_dev_limits().max_name_chars],
            "method": method,
            "path": path,
            "description": str(interface.get("description") or "").strip(),
            "headers": self._normalize_mapping(interface.get("headers")),
            "path_params": self._normalize_mapping(interface.get("path_params")),
            "query_params": query_params,
            "body": self._normalize_value(body),
            "expected_status": dev_registry.to_int(interface.get("expected_status"), 200),
            # 共享解析器（InterfaceAutoTestCore）会把非法状态码回落到 200，
            # 但把原始值留在这里，文档体检 / 回归清单仍要把它判为高风险。
            "raw_expected_status": interface.get("raw_expected_status"),
            "expected_response": self._normalize_value(interface.get("expected_response")),
            "request_format": str(interface.get("request_format") or "auto").strip() or "auto",
            "tags": self._normalize_tags(interface.get("tags")),
        }

    def _normalize_path(self, path: str) -> str:
        """路径只保留 path 部分；完整 URL 与相对路径行为一致，query/fragment 不进 path。"""
        candidate = (path or "/").strip()
        if not candidate:
            return "/"
        parsed = urlparse(candidate)
        actual_path = parsed.path or "/"
        if not actual_path.startswith("/"):
            actual_path = "/" + actual_path
        actual_path = re.sub(r"/+", "/", actual_path)
        if len(actual_path) > 1:
            actual_path = actual_path.rstrip("/")
        return actual_path

    def _inline_query_items(self, path: str) -> List[Tuple[str, str]]:
        """提取路径里自带的 query（含完整 URL 与相对路径两种写法）。"""
        parsed = urlparse((path or "").strip())
        return parse_qsl(parsed.query, keep_blank_values=True)

    def _normalize_mapping(self, value: Any) -> Dict[str, Any]:
        if not isinstance(value, dict):
            return {}
        return {str(key): self._normalize_value(val)
                for key, val in sorted(value.items(), key=lambda item: str(item[0]))}

    def _normalize_tags(self, value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return []

    def _normalize_value(self, value: Any, depth: int = 0, visited: Optional[frozenset] = None) -> Any:
        """带最大深度与循环引用保护的归一化。"""
        limits = dev_registry.get_dev_limits()
        if isinstance(value, (dict, list)):
            if depth >= limits.max_recursion_depth:
                self._warn(f"数据结构超过 {limits.max_recursion_depth} 层，深层节点已压缩")
                return {} if isinstance(value, dict) else []
            seen = visited or frozenset()
            if id(value) in seen:
                self._warn("检测到循环引用，已压缩该节点，避免递归崩溃")
                return {} if isinstance(value, dict) else []
            seen = seen | {id(value)}
            if isinstance(value, dict):
                return {str(key): self._normalize_value(val, depth + 1, seen)
                        for key, val in sorted(value.items(), key=lambda item: str(item[0]))}
            return [self._normalize_value(item, depth + 1, seen) for item in value]
        if isinstance(value, float) and not math.isfinite(value):
            self._warn("检测到 NaN/Infinity 等非有限数值，已转为 null，保证导出为严格合法 JSON")
            return None
        # 字符串值原样保留：token、签名、Base64 等首尾空格都是有效数据，
        # 归一化阶段 strip 会篡改数据并让差异对比漏报真实变更。
        return value

    def _to_int(self, value: Any, default: int) -> int:
        return dev_registry.to_int(value, default)

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
        esc = dev_registry.escape_markdown_cell
        lines = [
            "# 标准化接口清单", "", "## 概览",
            f"- 接口总数: {summary.get('interface_count', 0)}",
            f"- 含请求体接口: {summary.get('with_body_count', 0)}",
            f"- 鉴权相关接口: {summary.get('auth_related_count', 0)}",
            f"- 缺少响应样例: {summary.get('missing_expected_response_count', 0)}",
            f"- 请求方法分布: {', '.join(f'{esc(key)}:{value}' for key, value in summary.get('method_distribution', {}).items()) or '无'}",
            "",
            "## 接口清单",
            "| 序号 | 方法 | 路径 | 名称 | 请求格式 | 标签 |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for index, item in enumerate(interfaces, start=1):
            lines.append(
                f"| {index} | {esc(item.get('method', 'GET'))} | `{esc(item.get('path', '/'))}` | "
                f"{esc(item.get('name', '未命名接口'))} | {esc(item.get('request_format', 'auto'))} | "
                f"{esc(', '.join(item.get('tags', [])) or '-')} |"
            )
        lines.extend(["", "## 详细定义"])
        for index, item in enumerate(interfaces, start=1):
            lines.extend([
                f"### {index}. `{esc(item.get('method', 'GET'))} {esc(item.get('path', '/'))}` {esc(item.get('name', '未命名接口'))}",
                f"- 描述: {esc(item.get('description') or '无')}",
                f"- 标签: {esc(', '.join(item.get('tags', [])) or '无')}",
                f"- 请求头: `{esc(self._serialize_inline(item.get('headers', {})))}`",
                f"- 路径参数: `{esc(self._serialize_inline(item.get('path_params', {})))}`",
                f"- 查询参数: `{esc(self._serialize_inline(item.get('query_params', {})))}`",
                f"- 请求体: `{esc(self._serialize_inline(item.get('body')))}`",
                f"- 期望状态码: {item.get('expected_status', 200)}",
                f"- 期望响应: `{esc(self._serialize_inline(item.get('expected_response')))}`",
                "",
            ])
        return "\n".join(lines).strip() + "\n"

    def _build_structured_text_export(self, interfaces: List[Dict[str, Any]]) -> str:
        esc = dev_registry.escape_structured_field
        blocks = []
        for item in interfaces:
            blocks.append("\n".join([
                f"接口名称: {esc(item.get('name', '未命名接口'))}",
                f"请求方法: {esc(item.get('method', 'GET'))}",
                f"接口路径: {esc(item.get('path', '/'))}",
                f"接口描述: {esc(item.get('description') or '')}",
                f"请求头: {esc(self._serialize_inline(item.get('headers', {})))}",
                f"路径参数: {esc(self._serialize_inline(item.get('path_params', {})))}",
                f"查询参数: {esc(self._serialize_inline(item.get('query_params', {})))}",
                f"请求体: {esc(self._serialize_inline(item.get('body')))}",
                f"请求格式: {esc(item.get('request_format', 'auto'))}",
                f"标签: {esc(', '.join(item.get('tags', [])))}",
                f"期望状态码: {esc(item.get('expected_status', 200))}",
                f"期望响应: {esc(self._serialize_inline(item.get('expected_response')))}",
            ]))
        return "\n---\n".join(blocks)

    def _build_regression_markdown(self, items: List[Dict[str, Any]], summary: Dict[str, Any]) -> str:
        esc = dev_registry.escape_markdown_cell
        lines = [
            "# 接口回归清单", "", "## 概览",
            f"- 接口总数: {summary.get('interface_count', 0)}",
            f"- 高优先级: {summary.get('high_priority_count', 0)}",
            f"- 中优先级: {summary.get('medium_priority_count', 0)}",
            f"- 低优先级: {summary.get('low_priority_count', 0)}",
            f"- 建议检查项总数: {summary.get('check_item_count', 0)}",
            "",
        ]
        for item in items:
            priority_text = {"high": "高", "medium": "中", "low": "低"}.get(item.get("priority"), "低")
            lines.append(f"## {item.get('index', 0)}. [{priority_text}] `{esc(item.get('method', 'GET'))} {esc(item.get('path', '/'))}` {esc(item.get('name', '未命名接口'))}")
            lines.append(f"- 关注点: {esc('、'.join(item.get('focus_points', [])))}")
            for check_item in item.get("checklist", []):
                lines.append(f"- [ ] {esc(check_item)}")
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
            add_change("请求格式", f"{baseline.get('request_format', 'auto')} -> {target.get('request_format', 'auto')}", "high")
        if baseline.get("expected_status") != target.get("expected_status"):
            add_change("期望状态码", f"{baseline.get('expected_status', 200)} -> {target.get('expected_status', 200)}", "high")
        for label, getter in (
            ("请求头", "headers"), ("路径参数", "path_params"), ("查询参数", "query_params"),
        ):
            message, risk = self._describe_mapping_change(baseline.get(getter), target.get(getter))
            add_change(label, message, risk)
        body_message, body_risk = self._describe_value_change(baseline.get("body"), target.get("body"))
        add_change("请求体", body_message, body_risk)
        response_message, response_risk = self._describe_value_change(
            baseline.get("expected_response"), target.get("expected_response"))
        add_change("期望响应", response_message, response_risk)
        tags_message, tags_risk = self._describe_tag_change(baseline.get("tags"), target.get("tags"))
        add_change("标签", tags_message, tags_risk)

        return changes, dev_registry.risk_level(risk_rank)

    def _describe_mapping_change(self, baseline: Any, target: Any) -> Tuple[str, str]:
        baseline_map = baseline if isinstance(baseline, dict) else {}
        target_map = target if isinstance(target, dict) else {}
        if baseline_map == target_map:
            return "", "low"
        added_keys = sorted(set(target_map) - set(baseline_map))
        removed_keys = sorted(set(baseline_map) - set(target_map))
        changed_keys = sorted(key for key in set(baseline_map) & set(target_map)
                              if baseline_map.get(key) != target_map.get(key))
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

    def _collect_field_changes(
        self, baseline: Any, target: Any, prefix: str = ""
    ) -> Tuple[List[str], bool, bool]:
        """递归收集点号字段路径差异，受注册式 max_field_paths 上限约束。

        返回 (明细, 是否含删除字段, 是否截断)。嵌套请求体只报顶层 key 会让用户
        无法定位深层破坏性变更，这里统一输出 ``user.profile.level`` 这类路径。
        """
        limit = dev_registry.get_dev_limits().max_field_paths
        parts: List[str] = []
        has_removed = False
        truncated = False

        def short(value: Any) -> str:
            text = repr(value)
            return text if len(text) <= 80 else text[:77] + "..."

        def walk(old: Any, new: Any, path: str) -> None:
            nonlocal has_removed, truncated
            if len(parts) >= limit:
                truncated = True
                return
            if isinstance(old, dict) and isinstance(new, dict):
                for key in sorted(set(map(str, old)) | set(map(str, new))):
                    child = f"{path}.{key}" if path else str(key)
                    if key not in old:
                        parts.append(f"新增字段 {child}")
                    elif key not in new:
                        parts.append(f"删除字段 {child}")
                        has_removed = True
                    else:
                        walk(old[key], new[key], child)
                return
            if type(old) is not type(new) or old != new:
                label = path or "(根节点)"
                if type(old) is not type(new):
                    parts.append(f"{label} 类型变化: {type(old).__name__}->{type(new).__name__}")
                else:
                    parts.append(f"{label}: {short(old)} -> {short(new)}")

        walk(baseline, target, prefix)
        return parts, has_removed, truncated

    def _describe_value_change(self, baseline: Any, target: Any) -> Tuple[str, str]:
        # 类型必须先判：Python 里 True == 1、0 == False、1 == 1.0 都成立，
        # 先判 == 会把布尔/数字互换这类破坏性变更静默吞掉。
        if type(baseline) is not type(target):
            return f"类型变化: {type(baseline).__name__} -> {type(target).__name__}", "high"
        if baseline == target:
            return "", "low"
        if isinstance(baseline, dict):
            parts, has_removed, truncated = self._collect_field_changes(baseline, target)
            if truncated:
                self._warn(f"字段差异路径超过上限 {dev_registry.get_dev_limits().max_field_paths}，明细已截断")
            if not parts:
                return "", "low"
            return "; ".join(parts), "high" if has_removed else "medium"
        if isinstance(baseline, list):
            if all(isinstance(item, str) for item in baseline) and all(isinstance(item, str) for item in target):
                baseline_counter = Counter(baseline)
                target_counter = Counter(target)
                added_counter = target_counter - baseline_counter
                removed_counter = baseline_counter - target_counter
                parts = []
                if added_counter:
                    parts.append("新增项: " + ", ".join(f"{item}x{count}" for item, count in sorted(added_counter.items())))
                if removed_counter:
                    parts.append("删除项: " + ", ".join(f"{item}x{count}" for item, count in sorted(removed_counter.items())))
                if parts:
                    return "; ".join(parts), "high" if removed_counter else "medium"
                if baseline != target:
                    return "数组顺序发生变化", "low"
                return "", "low"
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
        merged, warnings = dev_registry.build_mock_response_headers(headers, response_body)
        for message in warnings:
            self._warn(message)
        return merged

    def _build_full_url(self, interface: Dict[str, Any], base_url: str, include_query: bool = True) -> str:
        """构造完整 URL：path_params 编码、query 同名 append、list doseq 展开。"""
        path = interface.get("path", "/")
        path_params = deepcopy(interface.get("path_params") or {})
        for key, value in path_params.items():
            raw = "" if value is None else str(value)
            encoded = raw[4:] if raw.startswith("raw:") else quote(raw, safe="")
            path = path.replace("{" + str(key) + "}", encoded)
        unresolved = re.findall(r"\{([^}]+)\}", path)
        if unresolved:
            self._warn(f"存在未解析的路径占位符: {', '.join(sorted(set(unresolved)))}")

        if path.startswith(("http://", "https://")):
            url = path
        else:
            actual_base_url = (base_url or "").strip()
            url = actual_base_url.rstrip("/") + "/" + path.lstrip("/") if actual_base_url else path

        query_params = deepcopy(interface.get("query_params") or {})
        if not include_query or not query_params:
            return url

        parsed = urlparse(url)
        existing_query: Dict[str, List[str]] = {}
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            existing_query.setdefault(key, []).append(value)
        for key, value in query_params.items():
            name = str(key)
            values = value if isinstance(value, (list, tuple)) else [value]
            for item in values:
                existing_query.setdefault(name, []).append("" if item is None else str(item))
        return urlunparse(parsed._replace(query=urlencode(existing_query, doseq=True)))

    # ------------------------------------------------------------------
    # 兼容包装：历史调用与回归测试依赖这些私有方法名/签名
    # ------------------------------------------------------------------

    def _render_requests_snippet(self, method, full_url, headers, query_params, body) -> str:
        renderer = dev_registry.get_snippet_renderer("python_requests")
        limits = dev_registry.get_dev_limits()
        return renderer(method, full_url, headers, query_params, body, {
            "timeout_seconds": limits.default_timeout_seconds,
            "verify_ssl": limits.default_verify_ssl,
        })

    def _render_fetch_snippet(self, method, full_url, headers, query_params, body) -> str:
        renderer = dev_registry.get_snippet_renderer("javascript_fetch")
        return renderer(method, full_url, headers, query_params, body, {})

    def _render_curl_snippet(self, method, full_url, headers, body) -> str:
        renderer = dev_registry.get_snippet_renderer("curl")
        return renderer(method, full_url, headers, {}, body, {})

    def _extract_path_placeholders(self, path: str) -> set:
        return set(re.findall(r"\{([^}]+)\}", path or ""))

    def _get_content_type(self, headers: Dict[str, Any]) -> str:
        if not isinstance(headers, dict):
            return ""
        for key, value in headers.items():
            if str(key).strip().lower() == "content-type":
                return str(value).lower().strip()
        return ""

    def _serialize_inline(self, value: Any) -> str:
        if value in (None, "", {}, []):
            return "{}" if isinstance(value, dict) else "[]" if isinstance(value, list) else ""
        if isinstance(value, (dict, list)):
            return dev_registry.strict_json_dumps(value, sort_keys=True)
        return str(value)

    def _parse_sample_value(self, sample: Any) -> Any:
        limits = dev_registry.get_dev_limits()
        if isinstance(sample, str):
            text = sample.strip()
            if not text:
                raise ValueError("响应样例不能为空")
            if len(text.encode("utf-8")) > limits.max_sample_bytes:
                raise ValueError(f"响应样例超过 {limits.max_sample_bytes} 字节上限")
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return text
        parsed = self._normalize_value(sample)
        return parsed

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
            return {str(key): self._build_strict_template(item, depth + 1, max_depth)
                    for key, item in value.items()}
        if isinstance(value, list):
            if not value:
                return []
            return [self._build_strict_template(value[0], depth + 1, max_depth)]
        return self._normalize_value(value)

    def _collect_field_paths(self, value: Any, prefix: str, depth: int, max_depth: int,
                             visited: Optional[frozenset] = None) -> List[str]:
        if depth >= max_depth:
            return [prefix]
        if isinstance(value, (dict, list)):
            seen = visited or frozenset()
            if id(value) in seen:
                return [prefix]
            seen = seen | {id(value)}
            if isinstance(value, dict):
                paths: List[str] = []
                for key, item in value.items():
                    current_prefix = f"{prefix}.{key}"
                    paths.append(current_prefix)
                    paths.extend(self._collect_field_paths(item, current_prefix, depth + 1, max_depth, seen))
                return paths
            list_prefix = f"{prefix}[]"
            paths = [list_prefix]
            if value:
                paths.extend(self._collect_field_paths(value[0], list_prefix, depth + 1, max_depth, seen))
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
        if any(any(word in str(key).lower() for word in dev_registry.get_hints("auth_header"))
               for key in headers):
            return True
        candidates = [interface.get("name"), interface.get("path"), interface.get("description"),
                      " ".join(interface.get("tags") or [])]
        return any(any(word in str(candidate or "").lower() for word in dev_registry.get_hints("auth_text"))
                   for candidate in candidates)

    def _has_pagination_hint(self, interface: Dict[str, Any]) -> bool:
        query_params = interface.get("query_params") or {}
        lower_keys = {str(key).lower() for key in query_params}
        return any(key in lower_keys for key in dev_registry.get_hints("pagination"))

    def _has_sort_hint(self, interface: Dict[str, Any]) -> bool:
        query_params = interface.get("query_params") or {}
        lower_keys = {str(key).lower() for key in query_params}
        return any(key in lower_keys for key in dev_registry.get_hints("sort"))

    def _decide_regression_priority(self, interface: Dict[str, Any]) -> str:
        return dev_registry.decide_priority(interface)
