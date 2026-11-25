"""面向授权目标的接口安全测试工具（注册式规则引擎）。

所有检测规则、词表、OWASP 清单、严重级别、角色等级、状态码分桶、探测策略、
Nuclei 模板、导出清洗器与运行上限均来自 ``core/api_security_registry.py``。
新增一条检查/换 OWASP 版本/自定义敏感字段/自定义角色等级只需调用注册接口，
无需修改本文件。
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import requests

from qa_toolkit.core import api_security_registry as sec_registry


def _finding_kwargs(item: Dict[str, Any], default_target: str = "") -> Dict[str, Any]:
    """把注册式规则输出的大写键 finding 映射为 _make_finding 的小写参数。"""
    return {
        "severity": item.get("Severity", "info"),
        "category": item.get("Category", ""),
        "title": item.get("Title", ""),
        "target": item.get("Target", default_target),
        "evidence": item.get("Evidence", ""),
        "recommendation": item.get("Recommendation", ""),
        "owasp": item.get("OWASP", ""),
        "error_type": item.get("error_type", ""),
    }


class SecurityTestTool:
    """面向授权目标的接口安全测试工具."""

    # ------------------------------------------------------------------
    # 计划构建
    # ------------------------------------------------------------------

    def build_security_plan(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
        auth_headers: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 15.0,
        verify_ssl: bool = True,
        origin: str = "https://security-audit.local",
        allow_private_targets: Optional[bool] = None,
        probe_strategy: str = "safe_baseline",
    ) -> Dict[str, Any]:
        limits = sec_registry.get_security_limits()
        normalized, select_warnings = self._select_interfaces(interfaces, selected_indexes)
        ok_origin, origin_error = sec_registry.sanitize_header_value(origin)
        clean_origin = str(origin or "").strip() if ok_origin else limits.default_origin
        cleaned_headers, header_warnings = sec_registry.validate_request_headers(auth_headers or {})
        timeout = sec_registry.clamp_float(
            timeout_seconds, 15.0, limits.min_timeout_seconds, limits.max_timeout_seconds
        )
        warnings: List[str] = list(select_warnings) + list(header_warnings)
        if not ok_origin:
            warnings.append(f"Origin 非法，已回落到默认值: {origin_error}")

        targets = []
        for index, item in enumerate(normalized, start=1):
            url = self._build_full_url(item, base_url, include_query=True)
            probe_methods = sec_registry.get_probe_methods(item.get("method"), probe_strategy)
            url_ok, url_error = sec_registry.validate_target_url(
                url if url.startswith(("http://", "https://")) else "",
                allow_private=allow_private_targets,
            )
            unresolved = self._unresolved_template_vars(url)
            if unresolved:
                warnings.append(f"{item.get('method', 'GET')} {item.get('path', '/')} 存在未解析变量: {', '.join(unresolved)}")
            targets.append(
                {
                    "index": index,
                    "name": item.get("name", ""),
                    "label": f"{item.get('method', 'GET')} {item.get('path', '/')}",
                    "method": item.get("method", "GET"),
                    "path": item.get("path", "/"),
                    "url": url,
                    "probe_methods": probe_methods,
                    "has_visible_auth": sec_registry.has_visible_auth(item.get("headers", {}), cleaned_headers),
                    "target_valid": bool(url_ok),
                    "target_error": url_error,
                }
            )

        if not targets and str(base_url or "").strip():
            root_url = str(base_url).strip().rstrip("/") + "/"
            root_ok, root_error = sec_registry.validate_target_url(root_url, allow_private=allow_private_targets)
            targets.append(
                {
                    "index": 1,
                    "name": "Base URL Root",
                    "label": "GET /",
                    "method": "GET",
                    "path": "/",
                    "url": root_url,
                    "probe_methods": sec_registry.get_probe_methods("GET", probe_strategy),
                    "has_visible_auth": sec_registry.has_visible_auth({}, cleaned_headers),
                    "target_valid": bool(root_ok),
                    "target_error": root_error,
                }
            )

        scope = {
            "base_url": str(base_url or "").strip(),
            "interface_count": len(normalized),
            "target_count": len(targets),
            "timeout_seconds": timeout,
            "verify_ssl": bool(verify_ssl) if verify_ssl is not None else limits.verify_ssl_by_default,
            "origin": clean_origin or limits.default_origin,
            "auth_headers": cleaned_headers,
            "allow_private_targets": bool(
                limits.allow_private_targets if allow_private_targets is None else allow_private_targets
            ),
            "follow_redirects": limits.follow_redirects_by_default,
            "probe_strategy": probe_strategy,
            "limits": {
                "max_interfaces": limits.max_interfaces,
                "max_roles": limits.max_roles,
                "max_requests": limits.max_requests,
                "max_timeout_seconds": limits.max_timeout_seconds,
                "max_total_seconds": limits.max_total_seconds,
                "max_response_bytes": limits.max_response_bytes,
            },
        }
        plan = {
            "created_at": self._now(),
            "plan_name": "API Security Assessment Plan",
            "strategy": [
                "被动审计: 参考 ZAP/Burp 的被动扫描思路，对接口文档和样例做静态风险识别",
                "安全基线探测: 仅使用 OPTIONS/GET/HEAD 等低风险请求检查头部、CORS、Cookie、方法暴露和信息泄露",
                "OWASP API Top 10 清单: 结合自动发现和人工复核步骤输出测试剧本与回归清单",
            ],
            "tool_inspirations": [
                "OWASP WSTG", "OWASP API Security Top 10 2023", "OWASP ZAP Passive/Active Scan Policy",
                "Burp Scanner Crawl + Audit + 自定义检查", "Nuclei 模板化与回归思路",
            ],
            "scope": scope,
            "targets": targets,
            "safety_notice": "仅用于已获授权的目标；当前实现默认不发送破坏性 payload，也不会主动执行注入、爆破、越权利用等攻击动作。",
            "warnings": warnings,
            "config_snapshot": self._config_snapshot(base_url, selected_indexes, cleaned_headers, timeout, verify_ssl, clean_origin, probe_strategy),
        }
        plan["input_signature"] = self._signature(plan["config_snapshot"])
        return plan

    # ------------------------------------------------------------------
    # 被动审计
    # ------------------------------------------------------------------

    def analyze_interfaces(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        selected, warnings = self._select_interfaces(interfaces, selected_indexes)
        findings: List[Dict[str, Any]] = []
        per_interface: List[Dict[str, Any]] = []

        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            full_url = self._build_full_url(item, base_url, include_query=True)
            raw_findings = sec_registry.evaluate_passive_rules(item, label, full_url)
            item_findings = [self._make_finding(**_finding_kwargs(item, label)) for item in raw_findings]
            unresolved = self._unresolved_template_vars(full_url)
            if unresolved:
                warnings.append(f"{label} 存在未解析变量: {', '.join(unresolved)}")
            findings.extend(item_findings)
            per_interface.append(
                {
                    "Label": label,
                    "Method": item.get("method", "GET"),
                    "Path": item.get("path", ""),
                    "Risk Count": len(item_findings),
                    "Top Severity": sec_registry.top_severity(item_findings),
                }
            )

        deduped_findings = self._dedupe_findings(findings)
        result = {
            "generated_at": self._now(),
            "summary": self._build_summary(len(selected), deduped_findings),
            "findings": deduped_findings,
            "per_interface": per_interface,
            "warnings": warnings,
        }
        result["text_summary"] = sec_registry.build_text_summary(result["summary"])
        return result

    # ------------------------------------------------------------------
    # 基线探测
    # ------------------------------------------------------------------

    def run_baseline_probe(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
        auth_headers: Optional[Dict[str, Any]] = None,
        verify_ssl: bool = True,
        timeout_seconds: float = 15.0,
        origin: str = "https://security-audit.local",
        allow_private_targets: Optional[bool] = None,
        probe_strategy: str = "safe_baseline",
    ) -> Dict[str, Any]:
        limits = sec_registry.get_security_limits()
        selected, warnings = self._select_interfaces(interfaces, selected_indexes)
        timeout = sec_registry.clamp_float(
            timeout_seconds, 15.0, limits.min_timeout_seconds, limits.max_timeout_seconds
        )
        ok_origin, origin_error = sec_registry.sanitize_header_value(origin)
        if not ok_origin:
            warnings.append(f"Origin 非法，已回落到默认值: {origin_error}")
            origin = limits.default_origin
        _, header_warnings = sec_registry.validate_request_headers(auth_headers or {})
        warnings.extend(header_warnings)
        auth_provided = bool(auth_headers)

        if not selected and str(base_url or "").strip():
            selected = [{
                "name": "Base URL Root", "method": "GET", "path": "/", "headers": {},
                "path_params": {}, "query_params": {}, "body": None,
                "request_format": "auto", "expected_status": 200,
            }]

        findings: List[Dict[str, Any]] = []
        samples: List[Dict[str, Any]] = []
        request_count = 0
        blocked = 0
        truncated_bytes = 0
        error_counts: Dict[str, int] = {}
        session = requests.Session()
        started = time.monotonic()
        try:
            for item in selected:
                if request_count >= limits.max_requests:
                    warnings.append(f"已达到最大请求数 {limits.max_requests}，剩余目标未探测")
                    break
                if time.monotonic() - started > limits.max_total_seconds:
                    warnings.append(f"已达到总时长上限 {limits.max_total_seconds}s，剩余目标未探测")
                    break

                label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
                url = self._build_full_url(item, base_url, include_query=True)
                if not url.startswith(("http://", "https://")):
                    findings.append(self._make_finding(
                        "medium", "scope", "接口缺少可探测的绝对 URL", label,
                        url or str(item.get("path", "")),
                        "请补充 Base URL，或在接口文档中使用完整 URL，以便执行基线探测。", "API9:2023"))
                    continue
                url_ok, url_error = sec_registry.validate_target_url(url, allow_private=allow_private_targets)
                if not url_ok:
                    blocked += 1
                    findings.append(self._make_finding(
                        "high", "blocked_target", "目标地址未通过安全校验，已阻止探测", label,
                        url_error or url,
                        "仅探测已授权的公网目标；如需测试内网服务请显式开启「允许内网/本地目标」。", "API8:2023"))
                    continue

                for probe_method in sec_registry.get_probe_methods(item.get("method"), probe_strategy):
                    if request_count >= limits.max_requests:
                        break
                    if time.monotonic() - started > limits.max_total_seconds:
                        break
                    probe_headers, probe_warnings = sec_registry.build_probe_headers(
                        auth_headers, origin, probe_method, str(item.get("method") or "GET")
                    )
                    for warn in probe_warnings:
                        if warn not in warnings:
                            warnings.append(warn)
                    request_count += 1
                    try:
                        response = session.request(
                            method=probe_method, url=url, headers=probe_headers,
                            allow_redirects=limits.follow_redirects_by_default,
                            timeout=timeout,
                            verify=bool(verify_ssl) if verify_ssl is not None else limits.verify_ssl_by_default,
                            stream=True,
                        )
                        body, was_truncated = self._read_response_body(response, limits.max_response_bytes)
                        if was_truncated:
                            truncated_bytes += 1
                        body_for_rules = body[: limits.max_body_preview_chars]
                        status_code = sec_registry.to_int(getattr(response, "status_code", 0), 0)
                        headers = {str(k): str(v) for k, v in dict(getattr(response, "headers", {}) or {}).items()}
                        lower_headers = {str(k).lower(): str(v) for k, v in headers.items()}
                        ctx = sec_registry.ProbeContext(
                            headers=headers, lower_headers=lower_headers, status_code=status_code,
                            body_preview=body_for_rules, url=url, label=label,
                            probe_method=probe_method, original_method=str(item.get("method") or "GET"),
                            auth_provided=auth_provided,
                        )
                        sample_findings = [
                            self._make_finding(**_finding_kwargs(x, label))
                            for x in sec_registry.evaluate_probe_rules(ctx)
                        ]
                        findings.extend(sample_findings)
                        samples.append({
                            "Label": label, "Probe Method": probe_method,
                            "Status Code": status_code, "Risk Count": len(sample_findings),
                            "Top Severity": sec_registry.top_severity(sample_findings),
                            "URL": url,
                            "Response Headers": json.dumps(headers, ensure_ascii=False, indent=2),
                            "Body Preview": body[: limits.max_sample_preview_chars],
                            "error_type": "",
                            "truncated": bool(was_truncated),
                        })
                    except Exception as exc:
                        error_type = self._classify_probe_error(exc)
                        error_counts[error_type] = error_counts.get(error_type, 0) + 1
                        findings.append(self._make_finding(
                            "medium", "probe_error", f"基线探测请求失败（{error_type}）", label,
                            f"{probe_method} {url} -> {type(exc).__name__}: {exc}",
                            "确认目标可达、证书配置、超时参数和网络 ACL；如果是内网服务，请在授权环境中执行。",
                            "API9:2023", error_type=error_type))
                        samples.append({
                            "Label": label, "Probe Method": probe_method, "Status Code": 0,
                            "Risk Count": 1, "Top Severity": "medium", "URL": url,
                            "Response Headers": "{}", "Body Preview": str(exc),
                            "error_type": error_type, "truncated": False,
                        })
        finally:
            session.close()

        for error_type, count in sorted(error_counts.items()):
            warnings.append(
                f"探测请求失败 {count} 次（{error_type}）；失败样本已标记 error_type，"
                "请检查目标可达性、证书、超时与网络 ACL 后再复测"
            )
        if blocked:
            warnings.append(f"{blocked} 个目标未通过安全校验（内网/协议/userinfo），已阻止探测")
        deduped_findings = self._dedupe_findings(findings)
        truncation = {
            "interfaces_total": len(interfaces or []),
            "interfaces_selected": len(selected),
            "requests_sent": request_count,
            "requests_limit": limits.max_requests,
            "blocked_targets": blocked,
            "truncated_responses": truncated_bytes,
            "body_preview_chars": limits.max_body_preview_chars,
            "sample_preview_chars": limits.max_sample_preview_chars,
            "elapsed_seconds": round(time.monotonic() - started, 3),
        }
        result = {
            "generated_at": self._now(),
            "summary": self._build_probe_summary(samples, deduped_findings, request_count),
            "findings": deduped_findings,
            "samples": samples,
            "warnings": warnings,
            "truncation": truncation,
        }
        result["text_summary"] = sec_registry.build_text_summary(result["summary"])
        return result

    # ------------------------------------------------------------------
    # 多角色回归
    # ------------------------------------------------------------------

    def run_role_batch_regression(
        self,
        interfaces: List[Dict[str, Any]],
        role_profiles: Optional[List[Dict[str, Any]]] = None,
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
        verify_ssl: bool = True,
        timeout_seconds: float = 15.0,
        origin: str = "https://security-audit.local",
        allow_private_targets: Optional[bool] = None,
        probe_strategy: str = "safe_baseline",
    ) -> Dict[str, Any]:
        limits = sec_registry.get_security_limits()
        normalized_profiles, warnings = self._normalize_role_profiles(role_profiles)
        role_reports = []
        flat_samples = []
        role_summaries = []
        estimated = len(normalized_profiles) * max(1, len(interfaces or [])) * limits.max_probes_per_interface
        if estimated > limits.max_requests:
            warnings.append(
                f"预估请求数 {estimated} 超过上限 {limits.max_requests}；"
                "已按每轮请求上限截断，建议缩小接口/角色范围"
            )

        for profile in normalized_profiles:
            report = self.run_baseline_probe(
                interfaces=interfaces, base_url=base_url, selected_indexes=selected_indexes,
                auth_headers=profile.get("headers", {}), verify_ssl=verify_ssl,
                timeout_seconds=timeout_seconds, origin=origin,
                allow_private_targets=allow_private_targets, probe_strategy=probe_strategy,
            )
            role_reports.append({"role": profile.get("role", ""), "headers": profile.get("headers", {}), "report": report})
            role_summaries.append({
                "Role": profile.get("role", ""),
                "Header Keys": ", ".join(sorted((profile.get("headers") or {}).keys())) or "无",
                "Requests": report.get("summary", {}).get("request_count", 0),
                "Findings": report.get("summary", {}).get("finding_count", 0),
                "High": report.get("summary", {}).get("high", 0),
                "Medium": report.get("summary", {}).get("medium", 0),
            })
            for sample in list(report.get("samples") or []):
                flat_samples.append({
                    "Role": profile.get("role", ""),
                    "Header Keys": ", ".join(sorted((profile.get("headers") or {}).keys())) or "无",
                    **sample,
                })
            for warn in report.get("warnings", []):
                text = f"[{profile.get('role', '')}] {warn}"
                if text not in warnings:
                    warnings.append(text)

        comparison_rows = self._build_role_comparison_rows(role_reports)
        comparison_findings = self._analyze_role_comparison_rows(comparison_rows)
        deduped_findings = self._dedupe_findings(comparison_findings)
        summary = self._build_summary(len(comparison_rows), deduped_findings)
        summary.update({"role_count": len(normalized_profiles), "comparison_count": len(comparison_rows)})
        result = {
            "generated_at": self._now(),
            "roles": [
                {"Role": p.get("role", ""), "Header Keys": list(sorted((p.get("headers") or {}).keys()))}
                for p in normalized_profiles
            ],
            "summary": summary,
            "role_summaries": role_summaries,
            "samples": flat_samples,
            "comparisons": comparison_rows,
            "findings": deduped_findings,
            "warnings": warnings,
        }
        result["text_summary"] = sec_registry.build_text_summary(summary)
        return result

    # ------------------------------------------------------------------
    # OWASP 清单 / 扫描策略 / 权限矩阵
    # ------------------------------------------------------------------

    def build_owasp_checklist(
        self,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        all_findings = list((passive_report or {}).get("findings") or []) + list((probe_report or {}).get("findings") or [])
        checklist = []
        for item in sec_registry.get_owasp_items():
            related = [f for f in all_findings if item.code in sec_registry.match_owasp_codes(f.get("OWASP", ""))]
            if related:
                status = "重点关注"
            elif item.auto_baseline:
                status = "已纳入自动基线"
            else:
                status = "手工复核"
            checklist.append({
                "OWASP": item.code, "Category": item.title, "Status": status,
                "Auto Findings": len(related), "Focus": item.focus,
                "Manual Validation": item.manual,
            })
        return checklist

    def build_scan_policy(
        self,
        plan: Dict[str, Any],
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        passive_summary = (passive_report or {}).get("summary", {})
        probe_summary = (probe_report or {}).get("summary", {})
        scope = plan.get("scope") or {}
        return {
            "generated_at": self._now(),
            "policy_name": "API Security Baseline Policy",
            "mode": scope.get("probe_strategy", "safe_baseline"),
            "inspirations": [
                {"Tool": "Burp Scanner", "Capability": "基于范围、登录态和审计配置组织扫描任务",
                 "Mapped Module": "范围选择、鉴权头配置、基线探测动作编排"},
                {"Tool": "OWASP ZAP", "Capability": "被动扫描、规则阈值、扫描策略和安全基线告警",
                 "Mapped Module": "被动审计、头部/CORS/Cookie/错误泄露基线探测"},
                {"Tool": "OWASP WSTG / API Top 10", "Capability": "测试方法论、风险清单和人工复核路径",
                 "Mapped Module": "OWASP 清单、安全测试剧本、人工验证建议"},
                {"Tool": "Nuclei", "Capability": "模板化回归、批量执行、持续集成输出",
                 "Mapped Module": "报告打包、JSON/Markdown 导出、回归清单沉淀"},
            ],
            "phases": [
                {"Phase": "Passive Review", "Status": "启用",
                 "Description": "不发请求或不改变目标状态，先对接口文档、样例和参数进行静态审计。",
                 "Checks": "协议、显式鉴权、敏感字段、错误泄露、上传校验、SSRF 参数、资源控制、接口清单完整性"},
                {"Phase": "Baseline Probe", "Status": "按范围启用" if scope.get("target_count", 0) else "待配置",
                 "Description": "仅使用 OPTIONS/GET/HEAD 这类低风险请求检查安全基线。",
                 "Checks": "HSTS、X-Content-Type-Options、CSP、CORS、TRACE、Server/X-Powered-By、Cookie Flags、缓存控制、错误回显"},
                {"Phase": "Manual Validation", "Status": "建议执行",
                 "Description": "针对自动化难覆盖的权限、业务流、对象级授权进行人工复核。",
                 "Checks": "BOLA/BFLA、对象属性级授权、敏感业务流、第三方 API 信任边界、鉴权失效与会话管理"},
            ],
            "guardrails": [
                "仅用于已授权目标；默认不执行注入、爆破、越权利用、批量 fuzz 和高风险主动攻击。",
                "基线探测默认不发送破坏性 payload，仅复用目标原有 GET/HEAD/OPTIONS 能力。",
                "活动扫描不能替代人工权限测试，涉及对象级授权和业务流风险时必须人工复核。",
                "默认拦截内网/回环/链路本地/元数据地址，默认关闭重定向、默认开启 SSL 校验。",
                f"运行上限：接口 {scope.get('limits', {}).get('max_interfaces', '-')} / "
                f"角色 {scope.get('limits', {}).get('max_roles', '-')} / "
                f"请求 {scope.get('limits', {}).get('max_requests', '-')}。",
            ],
            "coverage": [
                {"Area": "被动审计发现", "Value": passive_summary.get("finding_count", 0),
                 "Notes": f"High {passive_summary.get('high', 0)} / Medium {passive_summary.get('medium', 0)}"},
                {"Area": "基线探测发现", "Value": probe_summary.get("finding_count", 0),
                 "Notes": f"Requests {probe_summary.get('request_count', 0)} / Success {probe_summary.get('success_rate', 0)}%"},
                {"Area": "OWASP API Top 10", "Value": len(sec_registry.get_owasp_items()),
                 "Notes": "结合自动发现与人工复核输出清单"},
            ],
        }

    def build_authorization_matrix(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        limits = sec_registry.get_security_limits()
        selected, warnings = self._select_interfaces(interfaces, selected_indexes)
        normalized_roles = [str(item).strip() for item in (roles or []) if str(item).strip()]
        if not normalized_roles:
            normalized_roles = ["匿名用户", "普通用户", "管理员", "跨租户用户"]
        if len(normalized_roles) > limits.max_roles:
            warnings.append(f"角色数 {len(normalized_roles)} 超过上限 {limits.max_roles}，已截断")
            normalized_roles = normalized_roles[: limits.max_roles]

        matrix_rows: List[Dict[str, Any]] = []
        interface_rows: List[Dict[str, Any]] = []
        high_risk_count = 0

        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            risk = self._classify_authorization_risk(item)
            object_related = sec_registry.has_object_reference(item)
            public_endpoint = sec_registry.looks_public_endpoint(item)
            admin_endpoint = sec_registry.looks_admin_endpoint(item)
            business_endpoint = sec_registry.looks_business_endpoint(item)
            write_endpoint = str(item.get("method", "GET")).upper() in sec_registry.get_mutating_methods()
            if risk == "high":
                high_risk_count += 1
            checks = []
            if object_related:
                checks.append("替换对象 ID/tenant_id 做越权验证")
            if admin_endpoint:
                checks.append("验证功能级权限和后台角色矩阵")
            if business_endpoint:
                checks.append("验证敏感业务流限额、审批和重复提交")
            if write_endpoint:
                checks.append("验证低权限写操作和字段级越权")
            if not checks:
                checks.append("验证匿名、普通用户和管理员的访问边界")

            interface_rows.append({
                "Label": label, "Risk": risk,
                "Public Hint": "是" if public_endpoint else "否",
                "Object Reference": "是" if object_related else "否",
                "Admin/Biz Hint": "是" if admin_endpoint or business_endpoint else "否",
                "Checks": "；".join(checks),
            })
            for role in normalized_roles:
                should_access, expected = self._role_expectation(
                    role, item, risk, public_endpoint, admin_endpoint, object_related
                )
                matrix_rows.append({
                    "Label": label, "Method": item.get("method", "GET"), "Path": item.get("path", ""),
                    "Role": role, "Risk": risk, "Should Access": should_access,
                    "Expected Result": expected, "Checks": "；".join(checks),
                })
        return {
            "generated_at": self._now(),
            "roles": normalized_roles,
            "summary": {
                "interface_count": len(selected), "role_count": len(normalized_roles),
                "scenario_count": len(matrix_rows), "high_risk_interfaces": high_risk_count,
            },
            "interfaces": interface_rows, "matrix": matrix_rows, "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # Nuclei 模板
    # ------------------------------------------------------------------

    def build_nuclei_template_pack(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
        origin: str = "https://security-audit.local",
        auth_headers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        limits = sec_registry.get_security_limits()
        selected, warnings = self._select_interfaces(interfaces, selected_indexes)
        paths: List[str] = []
        for item in selected:
            path = sec_registry.normalize_template_path(item.get("path") or "/")
            if path not in paths:
                paths.append(path)
        if not paths:
            paths = ["/"]

        options_paths = paths[: limits.max_template_paths]
        get_paths = []
        for item in selected:
            if str(item.get("method") or "GET").upper() in {"GET", "HEAD", "OPTIONS"}:
                path = sec_registry.normalize_template_path(item.get("path") or "/")
                if path not in get_paths:
                    get_paths.append(path)
        if not get_paths:
            get_paths = options_paths[: min(10, limits.max_template_paths)]
        else:
            get_paths = get_paths[: limits.max_template_paths]

        sensitive_paths = []
        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            path = sec_registry.normalize_template_path(item.get("path") or "/")
            if sec_registry.looks_sensitive_runtime_target(label, path) and path not in sensitive_paths:
                sensitive_paths.append(path)
        if not sensitive_paths:
            sensitive_paths = get_paths[: min(10, limits.max_sensitive_template_paths)]
        else:
            sensitive_paths = sensitive_paths[: limits.max_sensitive_template_paths]

        _, header_warnings = sec_registry.validate_request_headers(auth_headers or {})
        warnings.extend(header_warnings)
        clean_headers, _ = sec_registry.validate_request_headers(auth_headers or {})
        header_variables = sec_registry.build_template_header_variables(clean_headers)
        path_sets = {"headers": get_paths, "options": options_paths, "cache": sensitive_paths}
        ok_origin, origin_error = sec_registry.sanitize_header_value(origin)
        if not ok_origin:
            warnings.append(f"Origin 非法，已回落到默认值: {origin_error}")
            origin = limits.default_origin
        templates = []
        for spec in sec_registry.get_nuclei_templates():
            selected_paths = path_sets.get(spec.key, options_paths)
            templates.append({
                "file_name": spec.file_name, "name": spec.name,
                "content": spec.builder(selected_paths, origin, header_variables),
                "path_count": len(selected_paths),
            })
        truncation = {
            "paths_total": len(paths),
            "paths_kept": len(options_paths),
            "get_paths_kept": len(get_paths),
            "sensitive_paths_kept": len(sensitive_paths),
            "max_template_paths": limits.max_template_paths,
            "max_sensitive_template_paths": limits.max_sensitive_template_paths,
        }
        if len(paths) > len(options_paths):
            warnings.append(
                f"Nuclei 模板路径已截断：共 {len(paths)} 条，保留 {len(options_paths)} 条"
            )
        return {
            "generated_at": self._now(),
            "template_count": len(templates), "path_count": len(paths),
            "templates": templates,
            "notes": [
                "模板只使用 GET/OPTIONS 的低风险请求，适合做安全基线回归。",
                "默认不会写入真实 Token/Cookie；如果目标需要认证，请在执行前补充占位变量。",
                "模板更适合发现配置型问题，不能替代人工权限测试和业务流安全测试。",
                "header 名已做 RFC 7230 白名单校验，变量名带唯一后缀，避免 YAML 注入与变量覆盖。",
            ],
            "truncation": truncation, "warnings": warnings,
        }

    # ------------------------------------------------------------------
    # 风险看板 / 回归套件 / 剧本 / 报告打包
    # ------------------------------------------------------------------

    def build_risk_dashboard(
        self,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        role_regression: Optional[Dict[str, Any]] = None,
        authorization_matrix: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        sources = [
            ("被动审计", (passive_report or {}).get("findings") or []),
            ("基线探测", (probe_report or {}).get("findings") or []),
            ("多角色回归", (role_regression or {}).get("findings") or []),
        ]
        seen: Dict[Tuple[str, str, str, str], Dict[str, Any]] = {}
        duplicate_count = 0
        for source, findings in sources:
            for item in findings:
                key = (
                    str(item.get("Category", "")), str(item.get("Title", "")),
                    str(item.get("Target", "")), str(item.get("Evidence", "")),
                )
                merged = dict(item)
                merged["Sources"] = [source]
                if key in seen:
                    duplicate_count += 1
                    existing = seen[key]
                    sources_list = list(existing.get("Sources") or [])
                    if source not in sources_list:
                        sources_list.append(source)
                    existing["Sources"] = sources_list
                    existing["Source"] = " + ".join(sources_list)
                    continue
                merged["Source"] = source
                seen[key] = merged
        all_findings = list(seen.values())

        summary = {
            "finding_count": len(all_findings), "high": 0, "medium": 0, "low": 0, "info": 0,
            "role_findings": len(sources[2][1]), "duplicate_merged": duplicate_count,
            "auth_high_risk_interfaces": int((authorization_matrix or {}).get("summary", {}).get("high_risk_interfaces", 0)),
        }
        for item in all_findings:
            severity = str(item.get("Severity", "info")).lower()
            if severity in summary:
                summary[severity] += 1

        category_groups = self._group_findings(all_findings, key="Category")
        owasp_groups = self._group_findings(all_findings, key="OWASP")
        target_groups = self._group_findings(all_findings, key="Target", limit=12)
        overview = [{
            "Severity": item.get("Top Severity", "info"), "Source": item.get("Top Source", ""),
            "Category": item.get("Group", ""), "Count": item.get("Count", 0),
            "Highlights": item.get("Highlights", ""),
        } for item in category_groups[:12]]
        auth_focus = [item for item in list((authorization_matrix or {}).get("interfaces") or [])
                      if str(item.get("Risk", "")).lower() == "high"]
        result = {
            "generated_at": self._now(), "summary": summary, "issue_overview": overview,
            "category_groups": category_groups, "owasp_groups": owasp_groups,
            "target_groups": target_groups, "auth_focus": auth_focus[:12],
        }
        result["text_summary"] = sec_registry.build_text_summary(summary)
        return result

    def build_regression_suite(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        role_regression: Optional[Dict[str, Any]] = None,
        authorization_matrix: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        selected, warnings = self._select_interfaces(interfaces, selected_indexes)
        findings_by_target = self._group_findings_by_target(passive_report, probe_report)
        suite_rows: List[Dict[str, Any]] = []
        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            target_findings = findings_by_target.get(label, [])
            if not target_findings and not sec_registry.looks_sensitive_runtime_target(label, str(item.get("path", ""))):
                continue
            for finding in target_findings:
                category = str(finding.get("Category", ""))
                suite_rows.append({
                    "Suite": sec_registry.get_suite_name(category),
                    "Priority": sec_registry.priority_from_severity(str(finding.get("Severity", "info"))),
                    "Label": label, "Role": "通用",
                    "Trigger": f"{finding.get('Source', '')} / {finding.get('Title', '')}",
                    "Checks": finding.get("Recommendation", ""),
                    "Expected": sec_registry.get_expected_text(category),
                })
        for row in list((authorization_matrix or {}).get("matrix") or []):
            if str(row.get("Risk", "")).lower() not in {"high", "medium"}:
                continue
            suite_rows.append({
                "Suite": "权限矩阵回归",
                "Priority": "P0" if str(row.get("Risk", "")).lower() == "high" else "P1",
                "Label": row.get("Label", ""), "Role": row.get("Role", ""),
                "Trigger": "角色矩阵", "Checks": row.get("Checks", ""),
                "Expected": row.get("Expected Result", ""),
            })
        for finding in list((role_regression or {}).get("findings") or []):
            suite_rows.append({
                "Suite": sec_registry.get_suite_name("role_regression"),
                "Priority": sec_registry.priority_from_severity(str(finding.get("Severity", "info"))),
                "Label": finding.get("Target", ""), "Role": "多角色",
                "Trigger": f"多角色回归 / {finding.get('Title', '')}",
                "Checks": finding.get("Recommendation", ""),
                "Expected": "不同角色应符合预期访问边界，敏感接口不能对低权限角色放行",
            })
        deduped_rows = []
        seen = set()
        for row in suite_rows:
            key = (row.get("Suite", ""), row.get("Priority", ""), row.get("Label", ""),
                   row.get("Role", ""), row.get("Trigger", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped_rows.append(row)
        suite_groups: List[Dict[str, Any]] = []
        group_map: Dict[str, Dict[str, Any]] = {}
        for row in deduped_rows:
            suite_name = row.get("Suite", "未分类")
            group_item = group_map.setdefault(suite_name, {
                "Suite": suite_name, "Count": 0, "P0": 0, "P1": 0, "P2": 0, "P3": 0,
            })
            group_item["Count"] += 1
            priority = row.get("Priority", "P3")
            if priority in group_item:
                group_item[priority] += 1
        suite_groups.extend(group_map.values())
        suite_groups.sort(key=lambda item: (-item.get("P0", 0), -item.get("P1", 0), item.get("Suite", "")))
        return {
            "generated_at": self._now(),
            "summary": {
                "suite_count": len(suite_groups), "scenario_count": len(deduped_rows),
                "p0": sum(1 for i in deduped_rows if i.get("Priority") == "P0"),
                "p1": sum(1 for i in deduped_rows if i.get("Priority") == "P1"),
                "p2": sum(1 for i in deduped_rows if i.get("Priority") == "P2"),
                "p3": sum(1 for i in deduped_rows if i.get("Priority") == "P3"),
            },
            "groups": suite_groups, "scenarios": deduped_rows, "warnings": warnings,
        }

    def generate_security_playbook(
        self,
        plan: Dict[str, Any],
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        checklist: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        limits = sec_registry.get_security_limits()
        all_findings = list((passive_report or {}).get("findings") or []) + list((probe_report or {}).get("findings") or [])
        top_findings = sorted(all_findings, key=lambda i: sec_registry.severity_rank(i.get("Severity", "info")))[: limits.max_playbook_findings]
        scope = plan.get("scope") or {}
        lines = [
            "# API 安全测试剧本", "", "## 测试策略",
            "- 被动审计: 参考 ZAP/Burp 的被动扫描思路，先从接口文档、请求头、响应样例识别高价值风险。",
            "- 安全基线探测: 仅使用授权范围内的 OPTIONS/GET/HEAD 检查头部、CORS、Cookie、错误泄露和方法暴露。",
            "- 回归与清单: 参考 Nuclei 的模板化工作流，把高风险点沉淀成可复用的回归检查项。",
            "", "## 范围摘要",
            f"- 生成时间: {plan.get('created_at', self._now())}",
            f"- Base URL: {scope.get('base_url', '') or '未指定'}",
            f"- 接口数: {scope.get('interface_count', 0)}",
            f"- 目标数: {scope.get('target_count', 0)}",
            f"- 探测策略: {scope.get('probe_strategy', 'safe_baseline')}",
            f"- 超时(秒): {scope.get('timeout_seconds', 0)}",
            f"- 允许内网目标: {'是' if scope.get('allow_private_targets') else '否'}",
            "", "## 高优先级发现",
        ]
        if not top_findings:
            lines.append("- 当前没有自动发现的高优先级问题，建议继续执行 OWASP 清单中的人工复核项。")
        else:
            for index, item in enumerate(top_findings, start=1):
                lines.extend([
                    f"{index}. [{str(item.get('Severity', '')).upper()}] {item.get('Title', '')}",
                    f"   - 目标: {item.get('Target', '')}",
                    f"   - 证据: {item.get('Evidence', '')}",
                    f"   - 建议: {item.get('Recommendation', '')}",
                    f"   - OWASP: {item.get('OWASP', '')}",
                ])
        lines.extend(["", "## 回归建议",
                      "- 把高频误配项固定成安全基线检查: HTTPS、HSTS、X-Content-Type-Options、Server/X-Powered-By、CORS、Cookie Flags。",
                      "- 把权限相关场景固定成角色矩阵回归: 匿名、普通用户、管理员、越权对象 ID。",
                      "- 把 SSRF/回调/重定向参数纳入专项复核，重点看协议白名单、私网访问限制和重定向处理。",
                      "", "## OWASP API Top 10 清单摘要"])
        for item in (checklist or [])[: len(sec_registry.get_owasp_items())]:
            lines.append(f"- {item.get('OWASP', '')} {item.get('Category', '')}: {item.get('Status', '')} | {item.get('Focus', '')}")
        for warning in (plan.get("warnings") or []):
            lines.append(f"- ⚠️ {warning}")
        return "\n".join(lines)

    def build_report_bundle(
        self,
        plan: Dict[str, Any],
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        role_regression: Optional[Dict[str, Any]] = None,
        checklist: Optional[List[Dict[str, Any]]] = None,
        authorization_matrix: Optional[Dict[str, Any]] = None,
        nuclei_template_pack: Optional[Dict[str, Any]] = None,
        risk_dashboard: Optional[Dict[str, Any]] = None,
        regression_suite: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        checklist = checklist or self.build_owasp_checklist(passive_report, probe_report)
        scan_policy = self.build_scan_policy(plan, passive_report, probe_report)
        playbook = self.generate_security_playbook(plan, passive_report, probe_report, checklist)
        warnings: List[str] = []
        for source in (plan, passive_report or {}, probe_report or {}, role_regression or {},
                       nuclei_template_pack or {}, regression_suite or {}):
            for item in source.get("warnings") or []:
                if item not in warnings:
                    warnings.append(item)
        bundle = {
            "generated_at": self._now(), "plan": plan, "scan_policy": scan_policy,
            "passive_report": passive_report or {}, "probe_report": probe_report or {},
            "role_regression": role_regression or {}, "owasp_checklist": checklist,
            "authorization_matrix": authorization_matrix or {},
            "nuclei_template_pack": nuclei_template_pack or {},
            "risk_dashboard": risk_dashboard or {}, "regression_suite": regression_suite or {},
            "playbook_markdown": playbook, "warnings": warnings,
            "config_snapshot": plan.get("config_snapshot", {}),
            "input_signature": plan.get("input_signature", ""),
            "registry_summary": sec_registry.get_registry_summary(),
        }
        bundle["report_markdown"] = self._bundle_to_markdown(bundle)
        return bundle

    # ------------------------------------------------------------------
    # 内部辅助
    # ------------------------------------------------------------------

    def _select_interfaces(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
    ) -> Tuple[List[Dict[str, Any]], List[str]]:
        """区分 None（未指定=全选）与 []（明确不选）；去重、过滤越界、钳制上限。"""
        limits = sec_registry.get_security_limits()
        warnings: List[str] = []
        all_items = list(interfaces or [])
        if selected_indexes is None:
            indexes: List[int] = list(range(len(all_items)))
        else:
            indexes = list(selected_indexes)
        cleaned: List[int] = []
        seen = set()
        for raw in indexes:
            index = sec_registry.to_int(raw, -1)
            if index < 0 or index >= len(all_items):
                warnings.append(f"已忽略越界接口索引 {raw!r}")
                continue
            if index in seen:
                continue
            seen.add(index)
            cleaned.append(index)
        cleaned.sort()
        if len(cleaned) > limits.max_interfaces:
            warnings.append(f"接口数 {len(cleaned)} 超过上限 {limits.max_interfaces}，已截断")
            cleaned = cleaned[: limits.max_interfaces]
        if selected_indexes is not None and len(selected_indexes) == 0:
            warnings.append("当前未选择任何接口，不会发起任何探测请求")
        return [self._normalize_interface(all_items[index]) for index in cleaned], warnings

    def _normalize_interface(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        methods = sec_registry.get_http_methods()
        method = str(interface.get("method") or "GET").upper()
        if method not in methods:
            method = "GET"
        query_params = interface.get("query_params") if isinstance(interface.get("query_params"), dict) else {}
        path_params = interface.get("path_params") if isinstance(interface.get("path_params"), dict) else {}
        body = interface.get("body")
        if body is None and method != "GET" and isinstance(interface.get("parameters"), dict):
            body = interface.get("parameters")
        if method == "GET" and not query_params and isinstance(interface.get("parameters"), dict):
            query_params = interface.get("parameters")
        return {
            "name": str(interface.get("name") or "").strip() or f"{method} {interface.get('path') or '/'}",
            "method": method,
            "path": str(interface.get("path") or interface.get("url") or "/").strip() or "/",
            "description": str(interface.get("description") or "").strip(),
            "headers": deepcopy(interface.get("headers") if isinstance(interface.get("headers"), dict) else {}),
            "path_params": deepcopy(path_params),
            "query_params": deepcopy(query_params),
            "body": deepcopy(body),
            "expected_response": deepcopy(interface.get("expected_response") or {}),
            "request_format": str(interface.get("request_format") or "auto").strip() or "auto",
            "expected_status": sec_registry.to_int(interface.get("expected_status"), 200),
        }

    def _build_full_url(self, interface: Dict[str, Any], base_url: str, include_query: bool = True) -> str:
        path = str(interface.get("path") or "/")
        for key, value in (interface.get("path_params") or {}).items():
            raw = str(value)
            encoded = raw[4:] if raw.startswith("raw:") else quote(raw, safe="")
            path = path.replace("{" + str(key) + "}", encoded)
        if path.startswith(("http://", "https://")):
            url = path
        else:
            clean_base_url = str(base_url or "").strip()
            if not clean_base_url:
                return path
            url = clean_base_url.rstrip("/") + "/" + path.lstrip("/")
        if not include_query:
            return url
        query_params = interface.get("query_params") or {}
        if not query_params:
            return url
        parsed = urlparse(url)
        existing_query: Dict[str, list] = {}
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            existing_query.setdefault(key, []).append(value)
        for key, value in query_params.items():
            name = str(key)
            if isinstance(value, (list, tuple)):
                existing_query.setdefault(name, []).extend(str(item) for item in value)
            else:
                existing_query.setdefault(name, []).append(str(value))
        return urlunparse(parsed._replace(query=urlencode(existing_query, doseq=True)))

    def _build_probe_methods(self, interface: Dict[str, Any]) -> List[str]:
        return sec_registry.get_probe_methods(interface.get("method"))

    def _has_visible_auth(self, interface_headers: Dict[str, Any], extra_headers: Optional[Dict[str, Any]] = None) -> bool:
        return sec_registry.has_visible_auth(interface_headers, extra_headers)

    def _match_sensitive_keys(self, *mapping_groups: Dict[str, Any]) -> List[str]:
        return sec_registry.match_sensitive_keys(*mapping_groups)

    def _detect_sensitive_response(self, value: Any) -> Dict[str, List[str]]:
        return sec_registry.detect_sensitive_response(value)

    def _find_error_leaks(self, value: Any) -> List[str]:
        return sec_registry.find_error_leaks(value)

    def _looks_like_upload(self, item: Dict[str, Any]) -> bool:
        return any(h in sec_registry.interface_blob(item) for h in sec_registry.get_hints("file"))

    def _has_upload_validation_hint(self, item: Dict[str, Any]) -> bool:
        blob = " ".join([
            str(item.get("description") or ""),
            json.dumps(item.get("body", ""), ensure_ascii=False, default=str),
            json.dumps(item.get("headers", {}), ensure_ascii=False, default=str),
        ]).lower()
        return any(h in blob for h in sec_registry.get_hints("upload_validation"))

    def _match_ssrf_keys(self, item: Dict[str, Any]) -> List[str]:
        hits = []
        hints = sec_registry.get_hints("ssrf")
        for mapping in [item.get("query_params", {}), item.get("path_params", {})]:
            for key in (mapping or {}).keys():
                if str(key).strip().lower() in hints:
                    hits.append(str(key))
        body = item.get("body")
        if isinstance(body, dict):
            for key in body.keys():
                if str(key).strip().lower() in hints:
                    hits.append(str(key))
        return sorted(set(hits))

    def _looks_like_bulk_endpoint(self, item: Dict[str, Any]) -> bool:
        return (str(item.get("method") or "GET").upper() == "GET"
                and any(h in sec_registry.interface_blob(item) for h in sec_registry.get_hints("list")))

    def _has_resource_control_hint(self, item: Dict[str, Any]) -> bool:
        query_keys = {str(k).strip().lower() for k in (item.get("query_params") or {}).keys()}
        if query_keys & sec_registry.get_hints("pagination"):
            return True
        blob = " ".join([
            str(item.get("description") or ""),
            json.dumps(item.get("headers", {}), ensure_ascii=False, default=str),
        ]).lower()
        return any(h in blob for h in sec_registry.get_hints("resource_control"))

    def _analyze_probe_response(
        self,
        response: requests.Response,
        label: str,
        url: str,
        probe_method: str,
        original_method: str,
        auth_provided: bool,
    ) -> List[Dict[str, Any]]:
        limits = sec_registry.get_security_limits()
        headers = {str(k): str(v) for k, v in dict(getattr(response, "headers", {}) or {}).items()}
        lower_headers = {str(k).lower(): str(v) for k, v in headers.items()}
        body, _ = self._read_response_body(response, limits.max_response_bytes)
        ctx = sec_registry.ProbeContext(
            headers=headers, lower_headers=lower_headers,
            status_code=sec_registry.to_int(getattr(response, "status_code", 0), 0),
            body_preview=body[: limits.max_body_preview_chars], url=url, label=label,
            probe_method=probe_method, original_method=original_method, auth_provided=auth_provided,
        )
        return [self._make_finding(**_finding_kwargs(x, label)) for x in sec_registry.evaluate_probe_rules(ctx)]

    @staticmethod
    def _read_response_body(response: Any, max_bytes: int) -> Tuple[str, bool]:
        """优先按上限读取原始流，避免 response.text 全量读入内存；返回 (文本, 是否截断)。"""
        raw = getattr(response, "raw", None)
        if raw is not None and hasattr(raw, "read"):
            try:
                data = raw.read(max_bytes + 1)
                truncated = len(data) > max_bytes
                return data[:max_bytes].decode("utf-8", errors="replace"), truncated
            except Exception:
                pass
        text = str(getattr(response, "text", "") or "")
        truncated = len(text) > max_bytes
        return text[:max_bytes], truncated

    @staticmethod
    def _classify_probe_error(exc: Exception) -> str:
        name = type(exc).__name__.lower()
        text = str(exc).lower()
        if "timeout" in name or "timed out" in text:
            return "timeout"
        if "ssl" in name or "certificate" in text:
            return "ssl_error"
        if "connection" in name or "connect" in text:
            return "connection_error"
        if "dns" in text or "name resolution" in text or "getaddrinfo" in text:
            return "dns_error"
        if "invalidurl" in name or "invalid header" in text:
            return "invalid_request"
        return "unknown"

    @staticmethod
    def _unresolved_template_vars(path: str) -> List[str]:
        return sorted(set(re.findall(r"\{([A-Za-z0-9_.-]+)\}", str(path or ""))))

    def _config_snapshot(self, base_url, selected_indexes, auth_headers, timeout, verify_ssl, origin, probe_strategy) -> Dict[str, Any]:
        return {
            "base_url": str(base_url or "").strip(),
            "selected_indexes": list(selected_indexes) if selected_indexes is not None else None,
            "auth_header_keys": sorted(str(k) for k in (auth_headers or {}).keys()),
            "timeout_seconds": sec_registry.to_float(timeout, 15.0),
            "verify_ssl": bool(verify_ssl),
            "origin": str(origin or ""),
            "probe_strategy": str(probe_strategy or ""),
        }

    @staticmethod
    def _signature(snapshot: Dict[str, Any]) -> str:
        payload = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, default=str)
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]

    def _group_findings(self, findings: List[Dict[str, Any]], key: str, limit: int = 20) -> List[Dict[str, Any]]:
        limits = sec_registry.get_security_limits()
        limit = min(limit, limits.max_findings_per_group)
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in findings:
            group_key = str(item.get(key, "") or "未分类")
            bucket = grouped.setdefault(group_key, {
                "Group": group_key, "Count": 0, "Top Severity": "none",
                "Top Source": "", "Highlights": "",
            })
            bucket["Count"] += 1
            severity = str(item.get("Severity", "info")).lower()
            if sec_registry.severity_rank(severity) < sec_registry.severity_rank(bucket.get("Top Severity", "none")):
                bucket["Top Severity"] = severity
                bucket["Top Source"] = str(item.get("Source", "") or "")
                bucket["Highlights"] = str(item.get("Title", "") or "")
        rows = list(grouped.values())
        rows.sort(key=lambda i: (sec_registry.severity_rank(i.get("Top Severity", "none")), -i.get("Count", 0), i.get("Group", "")))
        return rows[:limit]

    @staticmethod
    def _group_findings_by_target(passive_report, probe_report) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for source, report in [("被动审计", passive_report or {}), ("基线探测", probe_report or {})]:
            for item in list(report.get("findings") or []):
                target = str(item.get("Target", "") or "")
                grouped.setdefault(target, []).append(dict(item, Source=source))
        return grouped

    def _normalize_role_profiles(self, role_profiles: Optional[List[Dict[str, Any]]]) -> Tuple[List[Dict[str, Any]], List[str]]:
        limits = sec_registry.get_security_limits()
        warnings: List[str] = []
        profiles = []
        raw_profiles = role_profiles if role_profiles is not None else [{"role": "匿名用户", "headers": {}}]
        for item in raw_profiles:
            if not isinstance(item, dict):
                warnings.append("已忽略非对象类型的角色配置")
                continue
            role = str(item.get("role") or item.get("name") or "").strip() or f"角色{len(profiles) + 1}"
            cleaned_headers, header_warnings = sec_registry.validate_request_headers(
                item.get("headers") if isinstance(item.get("headers"), dict) else {}
            )
            warnings.extend(f"[{role}] {w}" for w in header_warnings)
            profiles.append({"role": role, "headers": cleaned_headers})
        if not profiles:
            profiles.append({"role": "匿名用户", "headers": {}})
        if len(profiles) > limits.max_roles:
            warnings.append(f"角色数 {len(profiles)} 超过上限 {limits.max_roles}，已截断")
            profiles = profiles[: limits.max_roles]
        return profiles, warnings

    def _build_role_comparison_rows(self, role_reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """角色状态用独立的 Role Codes 结构，不再平铺到可能与元数据冲突的列名。"""
        grouped: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
        role_columns: List[str] = []
        used: Dict[str, int] = {}
        for item in role_reports:
            base_role = str(item.get("role", ""))
            used[base_role] = used.get(base_role, 0) + 1
            role_columns.append(base_role if used[base_role] == 1 else f"{base_role}#{used[base_role]}")
        # 元数据字段集合：角色名与之冲突时只写入 Role Codes，避免覆盖接口标签等（SEC-16）。
        meta_keys = {"Label", "Probe Method", "URL", "Sensitivity", "Status Pattern",
                     "Success Roles", "Diversity", "Role Codes"}
        for role_report, role in zip(role_reports, role_columns):
            report = role_report.get("report", {}) or {}
            for sample in list(report.get("samples") or []):
                key = (str(sample.get("Label", "")), str(sample.get("Probe Method", "")), str(sample.get("URL", "")))
                row = grouped.setdefault(key, {
                    "Label": key[0], "Probe Method": key[1], "URL": key[2],
                    "Role Codes": {},
                })
                code = sec_registry.to_int(sample.get("Status Code", 0), 0)
                row["Role Codes"][role] = code
                # 保留历史契约：同名角色用后缀列名平铺，供对比矩阵直接展示。
                if role not in meta_keys:
                    row[role] = code
        rows = []
        for _, row in grouped.items():
            codes = row.get("Role Codes") or {}
            status_parts = [f"{role}:{sec_registry.to_int(code, 0)}" for role, code in codes.items()]
            success_roles = [role for role, code in codes.items() if sec_registry.status_bucket(code) == "allow"]
            row["Sensitivity"] = "high" if sec_registry.looks_sensitive_runtime_target(row.get("Label", ""), row.get("URL", "")) else "medium"
            row["Status Pattern"] = " | ".join(status_parts)
            row["Success Roles"] = ", ".join(success_roles) or "无"
            row["Diversity"] = "有差异" if len({sec_registry.to_int(c, 0) for c in codes.values()}) > 1 else "一致"
            rows.append(row)
        rows.sort(key=lambda i: (i.get("Sensitivity", ""), i.get("Label", ""), i.get("Probe Method", "")))
        return rows

    def _analyze_role_comparison_rows(self, comparison_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        findings = []
        for row in comparison_rows:
            role_codes = {
                key: sec_registry.to_int(value, 0)
                for key, value in dict(row.get("Role Codes") or {}).items()
            }
            if not role_codes:
                continue
            ranked_roles = sorted(role_codes.keys(), key=sec_registry.role_rank)
            lowest_role, highest_role = ranked_roles[0], ranked_roles[-1]
            lowest_code = role_codes.get(lowest_role, 0)
            highest_code = role_codes.get(highest_role, 0)
            sensitivity = str(row.get("Sensitivity", "medium")).lower()
            label = str(row.get("Label", ""))
            evidence = row.get("Status Pattern", "")
            if sensitivity == "high" and sec_registry.status_bucket(lowest_code) == "allow":
                severity = "high" if sec_registry.role_rank(lowest_role) == 0 else "medium"
                findings.append(self._make_finding(
                    severity, "role_regression", "敏感接口在低权限角色下可访问，需要人工复核", label, evidence,
                    "建议对该接口做匿名、低权限、越权对象 ID 和跨租户场景复测，确认是否应返回 401/403/404。", "API5:2023"))
            if sensitivity == "high" and sec_registry.status_bucket(lowest_code) == sec_registry.status_bucket(highest_code) == "allow":
                findings.append(self._make_finding(
                    "medium", "role_regression", "敏感接口在低高权限角色下结果无差异", label, evidence,
                    "建议结合对象 ID、字段级权限和业务流校验该接口是否真的应对不同角色返回一致结果。", "API1:2023"))
            if (sec_registry.role_rank(highest_role) > sec_registry.role_rank(lowest_role)
                    and sec_registry.status_bucket(highest_code) == "deny"
                    and sec_registry.status_bucket(lowest_code) == "allow"):
                findings.append(self._make_finding(
                    "low", "role_regression", "高权限角色结果反而弱于低权限角色", label, evidence,
                    "建议检查角色路由、网关策略和测试凭证是否配置正确，避免出现权限映射异常。", "API5:2023"))
        return findings

    def _role_rank(self, role: str) -> int:
        return sec_registry.role_rank(role)

    def _status_bucket(self, status_code: int) -> str:
        return sec_registry.status_bucket(status_code)

    def _suite_name_for_category(self, category: str) -> str:
        return sec_registry.get_suite_name(category)

    def _expected_for_category(self, category: str) -> str:
        return sec_registry.get_expected_text(category)

    def _priority_from_severity(self, severity: str) -> str:
        return sec_registry.priority_from_severity(severity)

    def _classify_authorization_risk(self, interface: Dict[str, Any]) -> str:
        method = str(interface.get("method") or "GET").upper()
        if sec_registry.looks_admin_endpoint(interface) or sec_registry.looks_business_endpoint(interface):
            return "high"
        if method in sec_registry.get_mutating_methods() or sec_registry.has_object_reference(interface):
            return "high"
        if self._has_visible_auth(interface.get("headers", {})) or not sec_registry.looks_public_endpoint(interface):
            return "medium"
        return "low"

    def _looks_public_endpoint(self, interface: Dict[str, Any]) -> bool:
        return sec_registry.looks_public_endpoint(interface)

    def _looks_admin_endpoint(self, interface: Dict[str, Any]) -> bool:
        return sec_registry.looks_admin_endpoint(interface)

    def _looks_business_endpoint(self, interface: Dict[str, Any]) -> bool:
        return sec_registry.looks_business_endpoint(interface)

    def _has_object_reference(self, interface: Dict[str, Any]) -> bool:
        return sec_registry.has_object_reference(interface)

    def _role_expectation(self, role, interface, risk, public_endpoint, admin_endpoint, object_related) -> Tuple[str, str]:
        role_blob = str(role).lower()
        method = str(interface.get("method") or "GET").upper()
        write_endpoint = method in sec_registry.get_mutating_methods()
        rank = sec_registry.role_rank(role)
        if rank == 0:
            if public_endpoint and method in {"GET", "HEAD", "OPTIONS"}:
                return "建议允许", "200/204，确认无敏感字段泄露"
            return "建议拒绝", "401/403"
        if any(key in role_blob for key in ["跨租户", "越权", "cross", "other tenant"]):
            return "建议拒绝", "403/404，替换对象 ID 后不能越权访问"
        if rank >= 3:
            if risk == "high":
                return "建议允许", "200/204，同时验证最小权限和审批链"
            return "按业务允许", "200/204 或按环境配置"
        if admin_endpoint:
            return "建议拒绝", "403"
        if object_related:
            return "条件允许", "仅允许访问本账号/本租户数据"
        if write_endpoint:
            return "条件允许", "200/204，同时验证字段级权限"
        if public_endpoint:
            return "建议允许", "200/204"
        return "按业务允许", "200/401/403，需结合角色矩阵复核"

    def _build_template_header_variables(self, auth_headers: Dict[str, Any]) -> List[Dict[str, str]]:
        return sec_registry.build_template_header_variables(auth_headers)

    def _build_nuclei_headers_template(self, paths, origin, header_variables) -> str:
        specs = {s.key: s for s in sec_registry.get_nuclei_templates()}
        return specs["headers"].builder(paths, origin, header_variables) if "headers" in specs else ""

    def _build_nuclei_options_template(self, paths, origin, header_variables) -> str:
        specs = {s.key: s for s in sec_registry.get_nuclei_templates()}
        return specs["options"].builder(paths, origin, header_variables) if "options" in specs else ""

    def _build_nuclei_cache_template(self, paths, origin, header_variables) -> str:
        specs = {s.key: s for s in sec_registry.get_nuclei_templates()}
        return specs["cache"].builder(paths, origin, header_variables) if "cache" in specs else ""

    def _build_summary(self, interface_count: int, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {"interface_count": interface_count, "finding_count": len(findings),
                   "high": 0, "medium": 0, "low": 0, "info": 0}
        for item in findings:
            severity = str(item.get("Severity", "info")).lower()
            if severity in summary:
                summary[severity] += 1
        return summary

    def _build_probe_summary(self, samples, findings, request_count) -> Dict[str, Any]:
        summary = self._build_summary(len({item.get("Label", "") for item in samples}), findings)
        responded = [item for item in samples if sec_registry.to_int(item.get("Status Code", 0), 0) > 0]
        summary.update({
            "request_count": request_count, "responded_count": len(responded),
            "success_rate": round((len(responded) / request_count * 100) if request_count else 0.0, 2),
        })
        return summary

    def _manual_validation_text(self, owasp_code: str) -> str:
        return sec_registry.get_manual_validation_text(owasp_code)

    def _bundle_to_markdown(self, bundle: Dict[str, Any]) -> str:
        passive = bundle.get("passive_report", {}) or {}
        probe = bundle.get("probe_report", {}) or {}
        role_regression = bundle.get("role_regression", {}) or {}
        checklist = bundle.get("owasp_checklist", []) or []
        scan_policy = bundle.get("scan_policy", {}) or {}
        auth_matrix = bundle.get("authorization_matrix", {}) or {}
        nuclei_pack = bundle.get("nuclei_template_pack", {}) or {}
        dashboard = bundle.get("risk_dashboard", {}) or {}
        suite = bundle.get("regression_suite", {}) or {}
        scope = (bundle.get("plan") or {}).get("scope", {}) or {}
        ps, prs = passive.get("summary", {}) or {}, probe.get("summary", {}) or {}
        lines = [
            "# API 安全测试报告", "",
            f"- 生成时间: {bundle.get('generated_at', self._now())}",
            f"- Base URL: {scope.get('base_url', '') or '未指定'}",
            f"- 接口数: {scope.get('interface_count', 0)}",
            f"- 目标数: {scope.get('target_count', 0)}",
            f"- 输入签名: {bundle.get('input_signature', '') or '未提供'}",
            "", "## 被动审计摘要",
            f"- Findings: {ps.get('finding_count', 0)}",
            f"- High/Medium/Low/Info: {ps.get('high', 0)}/{ps.get('medium', 0)}/{ps.get('low', 0)}/{ps.get('info', 0)}",
            "", "## 基线探测摘要",
            f"- Requests: {prs.get('request_count', 0)}",
            f"- Findings: {prs.get('finding_count', 0)}",
            f"- High/Medium/Low/Info: {prs.get('high', 0)}/{prs.get('medium', 0)}/{prs.get('low', 0)}/{prs.get('info', 0)}",
        ]
        truncation = probe.get("truncation") or {}
        if truncation:
            lines += ["", "## 运行与截断信息",
                      f"- 实际请求数 / 上限: {truncation.get('requests_sent', 0)} / {truncation.get('requests_limit', 0)}",
                      f"- 被安全策略阻止的目标: {truncation.get('blocked_targets', 0)}",
                      f"- 响应体被截断次数: {truncation.get('truncated_responses', 0)}",
                      f"- 耗时(秒): {truncation.get('elapsed_seconds', 0)}"]
        if role_regression:
            lines += ["", "## 多角色回归摘要",
                      f"- 角色数: {role_regression.get('summary', {}).get('role_count', 0)}",
                      f"- 差异对比数: {role_regression.get('summary', {}).get('comparison_count', 0)}",
                      f"- Findings: {role_regression.get('summary', {}).get('finding_count', 0)}"]
        lines += ["", "## 发现项明细（按严重级别）"]
        all_findings = (list(passive.get("findings") or []) + list(probe.get("findings") or [])
                        + list(role_regression.get("findings") or []))
        if not all_findings:
            lines.append("- 本轮没有自动发现的发现项，请继续执行 OWASP 清单中的人工复核项。")
        else:
            for index, item in enumerate(sorted(all_findings, key=lambda i: sec_registry.severity_rank(i.get("Severity", "info"))), start=1):
                lines += [
                    f"### {index}. [{str(item.get('Severity', '')).upper()}] {item.get('Title', '')}",
                    f"- 目标: {item.get('Target', '')}",
                    f"- 类别: {item.get('Category', '')}",
                    f"- 证据: {item.get('Evidence', '')}",
                    f"- OWASP: {item.get('OWASP', '')}",
                    f"- 建议: {item.get('Recommendation', '')}",
                    "",
                ]
        lines += ["", "## OWASP API Top 10 清单"]
        for item in checklist:
            lines.append(f"- {item.get('OWASP', '')} {item.get('Category', '')}: {item.get('Status', '')} | {item.get('Focus', '')}")
        if auth_matrix:
            lines += ["", "## 权限矩阵摘要",
                      f"- 接口数: {auth_matrix.get('summary', {}).get('interface_count', 0)}",
                      f"- 角色数: {auth_matrix.get('summary', {}).get('role_count', 0)}",
                      f"- 场景数: {auth_matrix.get('summary', {}).get('scenario_count', 0)}",
                      f"- 高风险接口数: {auth_matrix.get('summary', {}).get('high_risk_interfaces', 0)}"]
        if nuclei_pack:
            lines += ["", "## Nuclei 模板包摘要",
                      f"- 模板数: {nuclei_pack.get('template_count', 0)}",
                      f"- 路径数: {nuclei_pack.get('path_count', 0)}",
                      f"- 路径截断: {json.dumps(nuclei_pack.get('truncation', {}), ensure_ascii=False)}"]
        if dashboard:
            lines += ["", "## 风险看板摘要",
                      f"- Findings（跨来源去重后）: {dashboard.get('summary', {}).get('finding_count', 0)}",
                      f"- 合并的重复项: {dashboard.get('summary', {}).get('duplicate_merged', 0)}",
                      f"- High/Medium/Low/Info: {dashboard.get('summary', {}).get('high', 0)}/{dashboard.get('summary', {}).get('medium', 0)}/{dashboard.get('summary', {}).get('low', 0)}/{dashboard.get('summary', {}).get('info', 0)}"]
        if suite:
            lines += ["", "## 回归套件摘要",
                      f"- 套件数: {suite.get('summary', {}).get('suite_count', 0)}",
                      f"- 场景数: {suite.get('summary', {}).get('scenario_count', 0)}",
                      f"- P0/P1/P2/P3: {suite.get('summary', {}).get('p0', 0)}/{suite.get('summary', {}).get('p1', 0)}/{suite.get('summary', {}).get('p2', 0)}/{suite.get('summary', {}).get('p3', 0)}"]
        warnings = bundle.get("warnings") or []
        if warnings:
            lines += ["", "## 告警", ""] + [f"- ⚠️ {w}" for w in warnings]
        lines += ["", "## 扫描策略", f"- 模式: {scan_policy.get('mode', 'safe-baseline')}"]
        for item in scan_policy.get("guardrails", []):
            lines.append(f"- {item}")
        lines += ["", "## 安全测试剧本", "", bundle.get("playbook_markdown", "")]
        return "\n".join(lines)

    def _make_finding(
        self,
        severity: str,
        category: str,
        title: str,
        target: str,
        evidence: str,
        recommendation: str,
        owasp: str,
        error_type: str = "",
    ) -> Dict[str, Any]:
        return {
            "Severity": severity, "Category": category, "Title": title,
            "Target": str(target or ""), "Evidence": str(evidence or "") or "（响应未提供可观测值）",
            "Recommendation": recommendation, "OWASP": owasp, "error_type": error_type,
        }

    def _dedupe_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: Dict[Tuple[Any, ...], Dict[str, Any]] = {}
        for item in findings:
            key = (item.get("Severity", ""), item.get("Category", ""), item.get("Title", ""),
                   item.get("Target", ""), item.get("Evidence", ""), item.get("OWASP", ""))
            deduped[key] = item
        sorted_items = list(deduped.values())
        sorted_items.sort(key=lambda i: (sec_registry.severity_rank(i.get("Severity", "info")), i.get("Target", "")))
        return sorted_items

    def _extract_keys(self, value: Any) -> List[str]:
        keys: List[str] = []
        if isinstance(value, dict):
            for key, item in value.items():
                keys.append(str(key))
                keys.extend(self._extract_keys(item))
        elif isinstance(value, list):
            for item in value:
                keys.extend(self._extract_keys(item))
        return keys

    def _to_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value
        try:
            return json.dumps(value, ensure_ascii=False)
        except Exception:
            return str(value)

    def _top_severity(self, findings: List[Dict[str, Any]]) -> str:
        return sec_registry.top_severity(findings)

    def _severity_rank(self, severity: str) -> int:
        return sec_registry.severity_rank(severity)

    def _normalize_template_path(self, path: Any) -> str:
        return sec_registry.normalize_template_path(path)

    def _yaml_quote(self, value: str) -> str:
        return sec_registry.yaml_quote(value)

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
