import json
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


class SecurityTestTool:
    """面向授权目标的接口安全测试工具."""

    HTTP_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"}
    MUTATING_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    AUTH_HEADER_NAMES = {
        "authorization",
        "cookie",
        "x-api-key",
        "api-key",
        "token",
        "access-token",
        "x-token",
        "jwt",
    }
    HIGH_SENSITIVE_KEYS = {
        "password",
        "pwd",
        "secret",
        "private_key",
        "privatekey",
        "client_secret",
    }
    MEDIUM_SENSITIVE_KEYS = {
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "apikey",
        "session",
        "cookie",
        "credential",
        "authorization",
    }
    ADMIN_HINTS = {"admin", "internal", "debug", "system", "ops", "manage", "config"}
    FILE_HINTS = {"upload", "file", "image", "avatar", "attachment", "import"}
    SSRF_HINTS = {"url", "uri", "callback", "redirect", "returnurl", "return_url", "webhook", "endpoint"}
    LIST_HINTS = {"list", "search", "query", "export", "all", "batch", "report"}
    CACHE_HINTS = {"login", "token", "session", "profile", "user", "me", "auth", "password"}
    PUBLIC_HINTS = {"login", "signin", "signup", "register", "health", "ping", "captcha", "public", "openapi", "swagger"}
    OBJECT_ID_HINTS = {"id", "user_id", "tenant_id", "account_id", "order_id", "resource_id", "item_id"}
    BUSINESS_HINTS = {"payment", "pay", "refund", "withdraw", "coupon", "order", "invoice", "wallet", "settlement"}
    ERROR_MARKERS = {
        "exception",
        "traceback",
        "stack trace",
        "sql syntax",
        "syntax error",
        "mysql",
        "postgres",
        "ora-",
        "nullpointerexception",
        "debug",
        " at ",
    }
    OWASP_ITEMS = [
        ("API1:2023", "Broken Object Level Authorization", "校验对象 ID、资源 ID、租户 ID 访问是否越权"),
        ("API2:2023", "Broken Authentication", "复核登录、Token、会话续期和失效机制"),
        ("API3:2023", "Broken Object Property Level Authorization", "检查响应和请求对象字段是否存在越权读写"),
        ("API4:2023", "Unrestricted Resource Consumption", "确认分页、限流、批量接口和导出接口的资源控制"),
        ("API5:2023", "Broken Function Level Authorization", "检查高权限功能接口是否做角色/功能级鉴权"),
        ("API6:2023", "Unrestricted Access to Sensitive Business Flows", "复核注册、登录、找回密码、领券等关键业务流"),
        ("API7:2023", "Server Side Request Forgery", "检查 URL、回调、Webhook、跳转类参数是否可被滥用"),
        ("API8:2023", "Security Misconfiguration", "检查协议、头部、CORS、Cookie、错误泄露和方法暴露"),
        ("API9:2023", "Improper Inventory Management", "确认接口清单、版本、测试环境和废弃接口治理"),
        ("API10:2023", "Unsafe Consumption of APIs", "检查第三方 API、上游依赖、Webhook 和外部服务调用"),
    ]

    def build_security_plan(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
        auth_headers: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 15.0,
        verify_ssl: bool = True,
        origin: str = "https://security-audit.local",
    ) -> Dict[str, Any]:
        normalized = self._select_interfaces(interfaces, selected_indexes)
        targets = []
        for index, item in enumerate(normalized, start=1):
            url = self._build_full_url(item, base_url, include_query=True)
            probe_methods = self._build_probe_methods(item)
            targets.append(
                {
                    "index": index,
                    "name": item.get("name", ""),
                    "label": f"{item.get('method', 'GET')} {item.get('path', '/')}",
                    "method": item.get("method", "GET"),
                    "path": item.get("path", "/"),
                    "url": url,
                    "probe_methods": probe_methods,
                    "has_visible_auth": self._has_visible_auth(item.get("headers", {}), auth_headers or {}),
                }
            )

        if not targets and base_url.strip():
            targets.append(
                {
                    "index": 1,
                    "name": "Base URL Root",
                    "label": "GET /",
                    "method": "GET",
                    "path": "/",
                    "url": base_url.strip().rstrip("/") + "/",
                    "probe_methods": ["OPTIONS", "GET"],
                    "has_visible_auth": self._has_visible_auth({}, auth_headers or {}),
                }
            )

        return {
            "created_at": self._now(),
            "plan_name": "API Security Assessment Plan",
            "strategy": [
                "被动审计: 参考 ZAP/Burp 的被动扫描思路，对接口文档和样例做静态风险识别",
                "安全基线探测: 仅使用 OPTIONS/GET/HEAD 等低风险请求检查头部、CORS、Cookie、方法暴露和信息泄露",
                "OWASP API Top 10 清单: 结合自动发现和人工复核步骤输出测试剧本与回归清单",
            ],
            "tool_inspirations": [
                "OWASP WSTG",
                "OWASP API Security Top 10 2023",
                "OWASP ZAP Passive/Active Scan Policy",
                "Burp Scanner Crawl + Audit + 自定义检查",
                "Nuclei 模板化与回归思路",
            ],
            "scope": {
                "base_url": base_url.strip(),
                "interface_count": len(normalized),
                "target_count": len(targets),
                "timeout_seconds": max(float(timeout_seconds), 1.0),
                "verify_ssl": bool(verify_ssl),
                "origin": origin.strip() or "https://security-audit.local",
                "auth_headers": auth_headers or {},
            },
            "targets": targets,
            "safety_notice": "仅用于已获授权的目标；当前实现默认不发送破坏性 payload，也不会主动执行注入、爆破、越权利用等攻击动作。",
        }

    def analyze_interfaces(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        selected = self._select_interfaces(interfaces, selected_indexes)
        findings: List[Dict[str, Any]] = []
        per_interface: List[Dict[str, Any]] = []

        for item in selected:
            item_findings: List[Dict[str, Any]] = []
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            full_url = self._build_full_url(item, base_url, include_query=True)
            method = item.get("method", "GET")
            description_blob = " ".join(
                [
                    str(item.get("name", "") or ""),
                    str(item.get("description", "") or ""),
                    str(item.get("path", "") or ""),
                ]
            ).lower()

            if full_url.startswith("http://"):
                item_findings.append(
                    self._make_finding(
                        "high",
                        "transport",
                        "接口作用域使用明文 HTTP",
                        label,
                        full_url,
                        "生产或准生产接口建议统一使用 HTTPS，并确认网关强制跳转和 HSTS 策略。",
                        "API8:2023",
                    )
                )

            if method in self.MUTATING_METHODS and not self._has_visible_auth(item.get("headers", {})):
                item_findings.append(
                    self._make_finding(
                        "medium",
                        "auth_review",
                        "变更类接口未在文档中体现鉴权信息",
                        label,
                        "请求头中未发现 Authorization/Cookie/API Key 一类的显式鉴权线索。",
                        "确认该接口是否通过网关、签名、环境默认头或会话态进行保护，并在测试计划中覆盖 401/403 场景。",
                        "API5:2023",
                    )
                )

            if any(hint in description_blob for hint in self.ADMIN_HINTS) and not self._has_visible_auth(item.get("headers", {})):
                item_findings.append(
                    self._make_finding(
                        "high",
                        "admin_review",
                        "管理/内部接口缺少显式鉴权提示",
                        label,
                        item.get("path", ""),
                        "优先验证角色鉴权、功能级授权和环境隔离，避免内部接口被普通账号调用。",
                        "API5:2023",
                    )
                )

            sensitive_url_keys = self._match_sensitive_keys(item.get("query_params", {}), item.get("path_params", {}))
            if sensitive_url_keys:
                item_findings.append(
                    self._make_finding(
                        "medium",
                        "sensitive_url",
                        "URL 中出现敏感参数",
                        label,
                        ", ".join(sensitive_url_keys),
                        "避免把口令、Token、Session、密钥等敏感数据放入 path/query，优先改为安全头或请求体。",
                        "API8:2023",
                    )
                )

            response_sensitive = self._detect_sensitive_response(item.get("expected_response"))
            if response_sensitive:
                severity = "high" if response_sensitive["high_hits"] else "medium"
                item_findings.append(
                    self._make_finding(
                        severity,
                        "sensitive_response",
                        "响应样例包含敏感字段",
                        label,
                        ", ".join(response_sensitive["high_hits"] + response_sensitive["medium_hits"]),
                        "复核这些字段是否应脱敏、按角色裁剪，或仅在服务端内部保留。",
                        "API3:2023",
                    )
                )

            error_leak_markers = self._find_error_leaks(item.get("expected_response"))
            if error_leak_markers:
                item_findings.append(
                    self._make_finding(
                        "medium",
                        "error_leak",
                        "响应样例存在错误栈/调试信息泄露迹象",
                        label,
                        ", ".join(error_leak_markers[:5]),
                        "建议统一错误码和错误文案输出，不返回堆栈、SQL 语句、框架路径或调试上下文。",
                        "API8:2023",
                    )
                )

            if self._looks_like_upload(item) and not self._has_upload_validation_hint(item):
                item_findings.append(
                    self._make_finding(
                        "low",
                        "upload_review",
                        "上传接口未体现类型/大小校验要求",
                        label,
                        item.get("description", "") or item.get("path", ""),
                        "建议补充 MIME、扩展名、大小、病毒扫描和存储隔离等校验要求。",
                        "API8:2023",
                    )
                )

            ssrf_keys = self._match_ssrf_keys(item)
            if ssrf_keys:
                item_findings.append(
                    self._make_finding(
                        "medium",
                        "ssrf_review",
                        "接口存在 URL/回调类参数，需要做 SSRF 审计",
                        label,
                        ", ".join(ssrf_keys),
                        "重点复核协议白名单、域名/IP 限制、重定向跟随、内网地址访问和 DNS 重绑定防护。",
                        "API7:2023",
                    )
                )

            if self._looks_like_bulk_endpoint(item) and not self._has_resource_control_hint(item):
                item_findings.append(
                    self._make_finding(
                        "low",
                        "resource_control",
                        "批量/列表接口未体现分页或资源控制线索",
                        label,
                        item.get("path", ""),
                        "建议补充分页、限流、速率限制、批量大小和导出权限控制要求。",
                        "API4:2023",
                    )
                )

            if not str(item.get("description", "") or "").strip():
                item_findings.append(
                    self._make_finding(
                        "info",
                        "inventory",
                        "接口缺少描述信息",
                        label,
                        item.get("path", ""),
                        "建议补齐接口用途、所属系统、鉴权方式和废弃状态，便于清单治理和安全回归。",
                        "API9:2023",
                    )
                )

            findings.extend(item_findings)
            per_interface.append(
                {
                    "Label": label,
                    "Method": method,
                    "Path": item.get("path", ""),
                    "Risk Count": len(item_findings),
                    "Top Severity": self._top_severity(item_findings),
                }
            )

        deduped_findings = self._dedupe_findings(findings)
        return {
            "generated_at": self._now(),
            "summary": self._build_summary(len(selected), deduped_findings),
            "findings": deduped_findings,
            "per_interface": per_interface,
        }

    def run_baseline_probe(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
        auth_headers: Optional[Dict[str, Any]] = None,
        verify_ssl: bool = True,
        timeout_seconds: float = 15.0,
        origin: str = "https://security-audit.local",
    ) -> Dict[str, Any]:
        selected = self._select_interfaces(interfaces, selected_indexes)
        request_headers = deepcopy(auth_headers or {})
        request_headers.setdefault("Origin", origin.strip() or "https://security-audit.local")
        session = requests.Session()

        findings: List[Dict[str, Any]] = []
        samples: List[Dict[str, Any]] = []
        request_count = 0

        if not selected and base_url.strip():
            selected = [
                {
                    "name": "Base URL Root",
                    "method": "GET",
                    "path": "/",
                    "headers": {},
                    "path_params": {},
                    "query_params": {},
                    "body": None,
                    "request_format": "auto",
                    "expected_status": 200,
                }
            ]

        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            url = self._build_full_url(item, base_url, include_query=True)
            if not url.startswith(("http://", "https://")):
                findings.append(
                    self._make_finding(
                        "medium",
                        "scope",
                        "接口缺少可探测的绝对 URL",
                        label,
                        url or item.get("path", ""),
                        "请补充 Base URL，或在接口文档中使用完整 URL，以便执行基线探测。",
                        "API9:2023",
                    )
                )
                continue

            for probe_method in self._build_probe_methods(item):
                probe_headers = deepcopy(request_headers)
                if probe_method == "OPTIONS":
                    probe_headers.setdefault("Access-Control-Request-Method", item.get("method", "GET"))
                request_count += 1
                try:
                    response = session.request(
                        method=probe_method,
                        url=url,
                        headers=probe_headers,
                        allow_redirects=False,
                        timeout=max(float(timeout_seconds), 1.0),
                        verify=bool(verify_ssl),
                    )
                    sample_findings = self._analyze_probe_response(
                        response=response,
                        label=label,
                        url=url,
                        probe_method=probe_method,
                        original_method=item.get("method", "GET"),
                        auth_provided=bool(auth_headers),
                    )
                    findings.extend(sample_findings)
                    samples.append(
                        {
                            "Label": label,
                            "Probe Method": probe_method,
                            "Status Code": response.status_code,
                            "Risk Count": len(sample_findings),
                            "Top Severity": self._top_severity(sample_findings),
                            "URL": url,
                            "Response Headers": json.dumps(dict(response.headers or {}), ensure_ascii=False, indent=2),
                            "Body Preview": (response.text or "")[:800],
                        }
                    )
                except Exception as exc:
                    findings.append(
                        self._make_finding(
                            "medium",
                            "probe_error",
                            "基线探测请求失败",
                            label,
                            f"{probe_method} {url} -> {exc}",
                            "确认目标可达、证书配置、超时参数和网络 ACL；如果是内网服务，请在授权环境中执行。",
                            "API9:2023",
                        )
                    )
                    samples.append(
                        {
                            "Label": label,
                            "Probe Method": probe_method,
                            "Status Code": 0,
                            "Risk Count": 1,
                            "Top Severity": "medium",
                            "URL": url,
                            "Response Headers": "{}",
                            "Body Preview": str(exc),
                        }
                    )

        deduped_findings = self._dedupe_findings(findings)
        return {
            "generated_at": self._now(),
            "summary": self._build_probe_summary(samples, deduped_findings, request_count),
            "findings": deduped_findings,
            "samples": samples,
        }

    def run_role_batch_regression(
        self,
        interfaces: List[Dict[str, Any]],
        role_profiles: Optional[List[Dict[str, Any]]] = None,
        base_url: str = "",
        selected_indexes: Optional[List[int]] = None,
        verify_ssl: bool = True,
        timeout_seconds: float = 15.0,
        origin: str = "https://security-audit.local",
    ) -> Dict[str, Any]:
        normalized_profiles = self._normalize_role_profiles(role_profiles)
        role_reports = []
        flat_samples = []
        role_summaries = []

        for profile in normalized_profiles:
            report = self.run_baseline_probe(
                interfaces=interfaces,
                base_url=base_url,
                selected_indexes=selected_indexes,
                auth_headers=profile.get("headers", {}),
                verify_ssl=verify_ssl,
                timeout_seconds=timeout_seconds,
                origin=origin,
            )
            role_reports.append({"role": profile.get("role", ""), "headers": profile.get("headers", {}), "report": report})
            role_summaries.append(
                {
                    "Role": profile.get("role", ""),
                    "Header Keys": ", ".join(sorted((profile.get("headers") or {}).keys())) or "无",
                    "Requests": report.get("summary", {}).get("request_count", 0),
                    "Findings": report.get("summary", {}).get("finding_count", 0),
                    "High": report.get("summary", {}).get("high", 0),
                    "Medium": report.get("summary", {}).get("medium", 0),
                }
            )
            for sample in list(report.get("samples") or []):
                flat_samples.append(
                    {
                        "Role": profile.get("role", ""),
                        "Header Keys": ", ".join(sorted((profile.get("headers") or {}).keys())) or "无",
                        **sample,
                    }
                )

        comparison_rows = self._build_role_comparison_rows(role_reports)
        comparison_findings = self._analyze_role_comparison_rows(comparison_rows)
        deduped_findings = self._dedupe_findings(comparison_findings)
        summary = self._build_summary(len(comparison_rows), deduped_findings)
        summary.update(
            {
                "role_count": len(normalized_profiles),
                "comparison_count": len(comparison_rows),
            }
        )
        return {
            "generated_at": self._now(),
            "roles": [
                {
                    "Role": profile.get("role", ""),
                    "Header Keys": list(sorted((profile.get("headers") or {}).keys())),
                }
                for profile in normalized_profiles
            ],
            "summary": summary,
            "role_summaries": role_summaries,
            "samples": flat_samples,
            "comparisons": comparison_rows,
            "findings": deduped_findings,
        }

    def build_owasp_checklist(
        self,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        passive_findings = list((passive_report or {}).get("findings") or [])
        probe_findings = list((probe_report or {}).get("findings") or [])
        all_findings = passive_findings + probe_findings

        checklist = []
        for code, title, focus in self.OWASP_ITEMS:
            related = [item for item in all_findings if str(item.get("OWASP", "")).startswith(code)]
            if related:
                status = "重点关注"
            elif code in {"API7:2023", "API8:2023", "API9:2023"}:
                status = "已纳入自动基线"
            else:
                status = "手工复核"
            checklist.append(
                {
                    "OWASP": code,
                    "Category": title,
                    "Status": status,
                    "Auto Findings": len(related),
                    "Focus": focus,
                    "Manual Validation": self._manual_validation_text(code),
                }
            )
        return checklist

    def build_scan_policy(
        self,
        plan: Dict[str, Any],
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        passive_report = passive_report or {}
        probe_report = probe_report or {}
        passive_summary = passive_report.get("summary", {})
        probe_summary = probe_report.get("summary", {})
        return {
            "generated_at": self._now(),
            "policy_name": "API Security Baseline Policy",
            "mode": "safe-baseline",
            "inspirations": [
                {
                    "Tool": "Burp Scanner",
                    "Capability": "基于范围、登录态和审计配置组织扫描任务",
                    "Mapped Module": "范围选择、鉴权头配置、基线探测动作编排",
                },
                {
                    "Tool": "OWASP ZAP",
                    "Capability": "被动扫描、规则阈值、扫描策略和安全基线告警",
                    "Mapped Module": "被动审计、头部/CORS/Cookie/错误泄露基线探测",
                },
                {
                    "Tool": "OWASP WSTG / API Top 10",
                    "Capability": "测试方法论、风险清单和人工复核路径",
                    "Mapped Module": "OWASP 清单、安全测试剧本、人工验证建议",
                },
                {
                    "Tool": "Nuclei",
                    "Capability": "模板化回归、批量执行、持续集成输出",
                    "Mapped Module": "报告打包、JSON/Markdown 导出、回归清单沉淀",
                },
            ],
            "phases": [
                {
                    "Phase": "Passive Review",
                    "Status": "启用",
                    "Description": "不发请求或不改变目标状态，先对接口文档、样例和参数进行静态审计。",
                    "Checks": "协议、显式鉴权、敏感字段、错误泄露、上传校验、SSRF 参数、资源控制、接口清单完整性",
                },
                {
                    "Phase": "Baseline Probe",
                    "Status": "按范围启用" if plan.get("scope", {}).get("target_count", 0) else "待配置",
                    "Description": "仅使用 OPTIONS/GET/HEAD 这类低风险请求检查安全基线。",
                    "Checks": "HSTS、X-Content-Type-Options、CSP、CORS、TRACE、Server/X-Powered-By、Cookie Flags、缓存控制、错误回显",
                },
                {
                    "Phase": "Manual Validation",
                    "Status": "建议执行",
                    "Description": "针对自动化难覆盖的权限、业务流、对象级授权进行人工复核。",
                    "Checks": "BOLA/BFLA、对象属性级授权、敏感业务流、第三方 API 信任边界、鉴权失效与会话管理",
                },
            ],
            "guardrails": [
                "仅用于已授权目标；默认不执行注入、爆破、越权利用、批量 fuzz 和高风险主动攻击。",
                "基线探测默认不发送破坏性 payload，仅复用目标原有 GET/HEAD/OPTIONS 能力。",
                "活动扫描不能替代人工权限测试，涉及对象级授权和业务流风险时必须人工复核。",
            ],
            "coverage": [
                {
                    "Area": "被动审计发现",
                    "Value": passive_summary.get("finding_count", 0),
                    "Notes": f"High {passive_summary.get('high', 0)} / Medium {passive_summary.get('medium', 0)}",
                },
                {
                    "Area": "基线探测发现",
                    "Value": probe_summary.get("finding_count", 0),
                    "Notes": f"Requests {probe_summary.get('request_count', 0)} / Success {probe_summary.get('success_rate', 0)}%",
                },
                {
                    "Area": "OWASP API Top 10",
                    "Value": len(self.OWASP_ITEMS),
                    "Notes": "结合自动发现与人工复核输出清单",
                },
            ],
        }

    def build_authorization_matrix(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
        roles: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        selected = self._select_interfaces(interfaces, selected_indexes)
        normalized_roles = [item for item in (roles or ["匿名用户", "普通用户", "管理员", "跨租户用户"]) if str(item).strip()]
        if not normalized_roles:
            normalized_roles = ["匿名用户", "普通用户", "管理员", "跨租户用户"]

        matrix_rows: List[Dict[str, Any]] = []
        interface_rows: List[Dict[str, Any]] = []
        high_risk_count = 0

        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            risk = self._classify_authorization_risk(item)
            object_related = self._has_object_reference(item)
            public_endpoint = self._looks_public_endpoint(item)
            admin_endpoint = self._looks_admin_endpoint(item)
            business_endpoint = self._looks_business_endpoint(item)
            write_endpoint = str(item.get("method", "GET")).upper() in self.MUTATING_METHODS

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

            interface_rows.append(
                {
                    "Label": label,
                    "Risk": risk,
                    "Public Hint": "是" if public_endpoint else "否",
                    "Object Reference": "是" if object_related else "否",
                    "Admin/Biz Hint": "是" if admin_endpoint or business_endpoint else "否",
                    "Checks": "；".join(checks),
                }
            )

            for role in normalized_roles:
                should_access, expected = self._role_expectation(
                    role,
                    item,
                    risk,
                    public_endpoint,
                    admin_endpoint,
                    object_related,
                )
                matrix_rows.append(
                    {
                        "Label": label,
                        "Method": item.get("method", "GET"),
                        "Path": item.get("path", ""),
                        "Role": role,
                        "Risk": risk,
                        "Should Access": should_access,
                        "Expected Result": expected,
                        "Checks": "；".join(checks),
                    }
                )

        return {
            "generated_at": self._now(),
            "roles": normalized_roles,
            "summary": {
                "interface_count": len(selected),
                "role_count": len(normalized_roles),
                "scenario_count": len(matrix_rows),
                "high_risk_interfaces": high_risk_count,
            },
            "interfaces": interface_rows,
            "matrix": matrix_rows,
        }

    def build_nuclei_template_pack(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
        origin: str = "https://security-audit.local",
        auth_headers: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        selected = self._select_interfaces(interfaces, selected_indexes)
        paths: List[str] = []
        for item in selected:
            path = self._normalize_template_path(item.get("path") or "/")
            if path not in paths:
                paths.append(path)

        if not paths:
            paths = ["/"]

        options_paths = paths[:25]
        get_paths = []
        for item in selected:
            if str(item.get("method") or "GET").upper() in {"GET", "HEAD", "OPTIONS"}:
                path = self._normalize_template_path(item.get("path") or "/")
                if path not in get_paths:
                    get_paths.append(path)
        if not get_paths:
            get_paths = options_paths[:10]
        else:
            get_paths = get_paths[:25]

        sensitive_paths = []
        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            path = self._normalize_template_path(item.get("path") or "/")
            if self._looks_sensitive_runtime_target(label, path) and path not in sensitive_paths:
                sensitive_paths.append(path)
        if not sensitive_paths:
            sensitive_paths = get_paths[:10]
        else:
            sensitive_paths = sensitive_paths[:20]

        header_variables = self._build_template_header_variables(auth_headers or {})
        templates = [
            {
                "file_name": "api-security-headers-baseline.yaml",
                "name": "API Security Headers Baseline",
                "content": self._build_nuclei_headers_template(get_paths, origin, header_variables),
            },
            {
                "file_name": "api-cors-methods-exposure.yaml",
                "name": "API CORS And Method Exposure",
                "content": self._build_nuclei_options_template(options_paths, origin, header_variables),
            },
            {
                "file_name": "api-sensitive-cache-review.yaml",
                "name": "API Sensitive Cache Review",
                "content": self._build_nuclei_cache_template(sensitive_paths, origin, header_variables),
            },
        ]
        return {
            "generated_at": self._now(),
            "template_count": len(templates),
            "path_count": len(paths),
            "templates": templates,
            "notes": [
                "模板只使用 GET/OPTIONS 的低风险请求，适合做安全基线回归。",
                "默认不会写入真实 Token/Cookie；如果目标需要认证，请在执行前补充占位变量。",
                "模板更适合发现配置型问题，不能替代人工权限测试和业务流安全测试。",
            ],
        }

    def build_risk_dashboard(
        self,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        role_regression: Optional[Dict[str, Any]] = None,
        authorization_matrix: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        passive_findings = [dict(item, Source="被动审计") for item in list((passive_report or {}).get("findings") or [])]
        probe_findings = [dict(item, Source="基线探测") for item in list((probe_report or {}).get("findings") or [])]
        role_findings = [dict(item, Source="多角色回归") for item in list((role_regression or {}).get("findings") or [])]
        all_findings = passive_findings + probe_findings + role_findings

        summary = {
            "finding_count": len(all_findings),
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
            "role_findings": len(role_findings),
            "auth_high_risk_interfaces": int((authorization_matrix or {}).get("summary", {}).get("high_risk_interfaces", 0)),
        }
        for item in all_findings:
            severity = str(item.get("Severity", "info")).lower()
            if severity in summary:
                summary[severity] += 1

        category_groups = self._group_findings(all_findings, key="Category")
        owasp_groups = self._group_findings(all_findings, key="OWASP")
        target_groups = self._group_findings(all_findings, key="Target", limit=12)

        overview = []
        for item in category_groups[:12]:
            overview.append(
                {
                    "Severity": item.get("Top Severity", "info"),
                    "Source": item.get("Top Source", ""),
                    "Category": item.get("Group", ""),
                    "Count": item.get("Count", 0),
                    "Highlights": item.get("Highlights", ""),
                }
            )

        auth_focus = []
        for item in list((authorization_matrix or {}).get("interfaces") or []):
            if str(item.get("Risk", "")).lower() == "high":
                auth_focus.append(item)

        return {
            "generated_at": self._now(),
            "summary": summary,
            "issue_overview": overview,
            "category_groups": category_groups,
            "owasp_groups": owasp_groups,
            "target_groups": target_groups,
            "auth_focus": auth_focus[:12],
        }

    def build_regression_suite(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        role_regression: Optional[Dict[str, Any]] = None,
        authorization_matrix: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        selected = self._select_interfaces(interfaces, selected_indexes)
        findings_by_target = self._group_findings_by_target(passive_report, probe_report)
        suite_rows: List[Dict[str, Any]] = []

        for item in selected:
            label = f"{item.get('method', 'GET')} {item.get('path', '/')}"
            target_findings = findings_by_target.get(label, [])
            if not target_findings and not self._looks_sensitive_runtime_target(label, item.get("path", "")):
                continue

            for finding in target_findings:
                suite_rows.append(
                    {
                        "Suite": self._suite_name_for_category(str(finding.get("Category", ""))),
                        "Priority": self._priority_from_severity(str(finding.get("Severity", "info"))),
                        "Label": label,
                        "Role": "通用",
                        "Trigger": f"{finding.get('Source', '')} / {finding.get('Title', '')}",
                        "Checks": finding.get("Recommendation", ""),
                        "Expected": self._expected_for_category(str(finding.get("Category", ""))),
                    }
                )

        for row in list((authorization_matrix or {}).get("matrix") or []):
            if str(row.get("Risk", "")).lower() not in {"high", "medium"}:
                continue
            suite_rows.append(
                {
                    "Suite": "权限矩阵回归",
                    "Priority": "P0" if str(row.get("Risk", "")).lower() == "high" else "P1",
                    "Label": row.get("Label", ""),
                    "Role": row.get("Role", ""),
                    "Trigger": "角色矩阵",
                    "Checks": row.get("Checks", ""),
                    "Expected": row.get("Expected Result", ""),
                }
                )

        for finding in list((role_regression or {}).get("findings") or []):
            suite_rows.append(
                {
                    "Suite": "多角色差异回归",
                    "Priority": self._priority_from_severity(str(finding.get("Severity", "info"))),
                    "Label": finding.get("Target", ""),
                    "Role": "多角色",
                    "Trigger": f"多角色回归 / {finding.get('Title', '')}",
                    "Checks": finding.get("Recommendation", ""),
                    "Expected": "不同角色应符合预期访问边界，敏感接口不能对低权限角色放行",
                }
            )

        deduped_rows = []
        seen = set()
        for row in suite_rows:
            key = (row.get("Suite", ""), row.get("Priority", ""), row.get("Label", ""), row.get("Role", ""), row.get("Trigger", ""))
            if key in seen:
                continue
            seen.add(key)
            deduped_rows.append(row)

        suite_groups = []
        group_map: Dict[str, Dict[str, Any]] = {}
        for row in deduped_rows:
            suite_name = row.get("Suite", "未分类")
            group_item = group_map.setdefault(
                suite_name,
                {"Suite": suite_name, "Count": 0, "P0": 0, "P1": 0, "P2": 0, "P3": 0},
            )
            group_item["Count"] += 1
            priority = row.get("Priority", "P3")
            if priority in group_item:
                group_item[priority] += 1
        suite_groups.extend(group_map.values())
        suite_groups.sort(key=lambda item: (-item.get("P0", 0), -item.get("P1", 0), item.get("Suite", "")))

        return {
            "generated_at": self._now(),
            "summary": {
                "suite_count": len(suite_groups),
                "scenario_count": len(deduped_rows),
                "p0": sum(1 for item in deduped_rows if item.get("Priority") == "P0"),
                "p1": sum(1 for item in deduped_rows if item.get("Priority") == "P1"),
                "p2": sum(1 for item in deduped_rows if item.get("Priority") == "P2"),
                "p3": sum(1 for item in deduped_rows if item.get("Priority") == "P3"),
            },
            "groups": suite_groups,
            "scenarios": deduped_rows,
        }

    def generate_security_playbook(
        self,
        plan: Dict[str, Any],
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
        checklist: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        passive_findings = list((passive_report or {}).get("findings") or [])
        probe_findings = list((probe_report or {}).get("findings") or [])
        checklist = checklist or []
        all_findings = passive_findings + probe_findings
        top_findings = sorted(all_findings, key=lambda item: self._severity_rank(item.get("Severity", "info")))[:12]

        lines = [
            "# API 安全测试剧本",
            "",
            "## 测试策略",
            "- 被动审计: 参考 ZAP/Burp 的被动扫描思路，先从接口文档、请求头、响应样例识别高价值风险。",
            "- 安全基线探测: 仅使用授权范围内的 OPTIONS/GET/HEAD 检查头部、CORS、Cookie、错误泄露和方法暴露。",
            "- 回归与清单: 参考 Nuclei 的模板化工作流，把高风险点沉淀成可复用的回归检查项。",
            "",
            "## 范围摘要",
            f"- 生成时间: {plan.get('created_at', self._now())}",
            f"- Base URL: {plan.get('scope', {}).get('base_url', '') or '未指定'}",
            f"- 接口数: {plan.get('scope', {}).get('interface_count', 0)}",
            f"- 目标数: {plan.get('scope', {}).get('target_count', 0)}",
            "",
            "## 高优先级发现",
        ]

        if not top_findings:
            lines.append("- 当前没有自动发现的高优先级问题，建议继续执行 OWASP 清单中的人工复核项。")
        else:
            for index, item in enumerate(top_findings, start=1):
                lines.extend(
                    [
                        f"{index}. [{item.get('Severity', '').upper()}] {item.get('Title', '')}",
                        f"   - 目标: {item.get('Target', '')}",
                        f"   - 证据: {item.get('Evidence', '')}",
                        f"   - 建议: {item.get('Recommendation', '')}",
                    ]
                )

        lines.extend(
            [
                "",
                "## 回归建议",
                "- 把高频误配项固定成安全基线检查: HTTPS、HSTS、X-Content-Type-Options、Server/X-Powered-By、CORS、Cookie Flags。",
                "- 把权限相关场景固定成角色矩阵回归: 匿名、普通用户、管理员、越权对象 ID。",
                "- 把 SSRF/回调/重定向参数纳入专项复核，重点看协议白名单、私网访问限制和重定向处理。",
                "",
                "## OWASP API Top 10 清单摘要",
            ]
        )
        for item in checklist[:10]:
            lines.append(
                f"- {item.get('OWASP', '')} {item.get('Category', '')}: {item.get('Status', '')} | {item.get('Focus', '')}"
            )
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
        bundle = {
            "generated_at": self._now(),
            "plan": plan,
            "scan_policy": scan_policy,
            "passive_report": passive_report or {},
            "probe_report": probe_report or {},
            "role_regression": role_regression or {},
            "owasp_checklist": checklist,
            "authorization_matrix": authorization_matrix or {},
            "nuclei_template_pack": nuclei_template_pack or {},
            "risk_dashboard": risk_dashboard or {},
            "regression_suite": regression_suite or {},
            "playbook_markdown": playbook,
        }
        bundle["report_markdown"] = self._bundle_to_markdown(bundle)
        return bundle

    def _select_interfaces(
        self,
        interfaces: List[Dict[str, Any]],
        selected_indexes: Optional[List[int]] = None,
    ) -> List[Dict[str, Any]]:
        selected_indexes = selected_indexes or list(range(len(interfaces)))
        selected = []
        for index in selected_indexes:
            if index < 0 or index >= len(interfaces):
                continue
            selected.append(self._normalize_interface(interfaces[index]))
        return selected

    def _normalize_interface(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        method = str(interface.get("method") or "GET").upper()
        if method not in self.HTTP_METHODS:
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
            "expected_status": int(interface.get("expected_status") or 200),
        }

    def _build_full_url(self, interface: Dict[str, Any], base_url: str, include_query: bool = True) -> str:
        path = str(interface.get("path") or "/")
        for key, value in (interface.get("path_params") or {}).items():
            path = path.replace("{" + str(key) + "}", str(value))

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
        existing_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
        existing_query.update({str(key): str(value) for key, value in query_params.items()})
        return urlunparse(parsed._replace(query=urlencode(existing_query, doseq=True)))

    def _build_probe_methods(self, interface: Dict[str, Any]) -> List[str]:
        method = str(interface.get("method") or "GET").upper()
        if method in {"GET", "HEAD"}:
            return ["OPTIONS", "GET"]
        if method == "OPTIONS":
            return ["OPTIONS"]
        return ["OPTIONS"]

    def _has_visible_auth(self, interface_headers: Dict[str, Any], extra_headers: Optional[Dict[str, Any]] = None) -> bool:
        combined = {}
        combined.update(interface_headers or {})
        combined.update(extra_headers or {})
        header_names = {str(key).strip().lower() for key in combined.keys()}
        return bool(header_names & self.AUTH_HEADER_NAMES)

    def _match_sensitive_keys(self, *mapping_groups: Dict[str, Any]) -> List[str]:
        hits = []
        sensitive_keys = self.HIGH_SENSITIVE_KEYS | self.MEDIUM_SENSITIVE_KEYS
        for mapping in mapping_groups:
            for key in (mapping or {}).keys():
                normalized = str(key).strip().lower()
                if normalized in sensitive_keys:
                    hits.append(str(key))
        return sorted(set(hits))

    def _detect_sensitive_response(self, value: Any) -> Dict[str, List[str]]:
        keys = self._extract_keys(value)
        high_hits = [key for key in keys if key.lower() in self.HIGH_SENSITIVE_KEYS]
        medium_hits = [key for key in keys if key.lower() in self.MEDIUM_SENSITIVE_KEYS]
        return {
            "high_hits": sorted(set(high_hits)),
            "medium_hits": sorted(set(medium_hits)),
        }

    def _find_error_leaks(self, value: Any) -> List[str]:
        blob = self._to_text(value).lower()
        return sorted([marker for marker in self.ERROR_MARKERS if marker in blob])

    def _looks_like_upload(self, item: Dict[str, Any]) -> bool:
        blob = " ".join(
            [
                str(item.get("name", "") or ""),
                str(item.get("description", "") or ""),
                str(item.get("path", "") or ""),
            ]
        ).lower()
        return any(hint in blob for hint in self.FILE_HINTS)

    def _has_upload_validation_hint(self, item: Dict[str, Any]) -> bool:
        blob = " ".join(
            [
                str(item.get("description", "") or ""),
                json.dumps(item.get("body", ""), ensure_ascii=False),
                json.dumps(item.get("headers", {}), ensure_ascii=False),
            ]
        ).lower()
        validation_hints = {"multipart", "size", "mime", "content-type", "virus", "extension", "limit"}
        return any(hint in blob for hint in validation_hints)

    def _match_ssrf_keys(self, item: Dict[str, Any]) -> List[str]:
        hits = []
        for mapping in [item.get("query_params", {}), item.get("path_params", {})]:
            for key in mapping.keys():
                normalized = str(key).strip().lower()
                if normalized in self.SSRF_HINTS:
                    hits.append(str(key))

        body = item.get("body")
        if isinstance(body, dict):
            for key in body.keys():
                normalized = str(key).strip().lower()
                if normalized in self.SSRF_HINTS:
                    hits.append(str(key))
        return sorted(set(hits))

    def _looks_like_bulk_endpoint(self, item: Dict[str, Any]) -> bool:
        blob = " ".join(
            [
                str(item.get("name", "") or ""),
                str(item.get("description", "") or ""),
                str(item.get("path", "") or ""),
            ]
        ).lower()
        return item.get("method") == "GET" and any(hint in blob for hint in self.LIST_HINTS)

    def _has_resource_control_hint(self, item: Dict[str, Any]) -> bool:
        query_keys = {str(key).strip().lower() for key in (item.get("query_params") or {}).keys()}
        if query_keys & {"page", "size", "limit", "offset", "cursor"}:
            return True
        blob = " ".join(
            [
                str(item.get("description", "") or ""),
                json.dumps(item.get("headers", {}), ensure_ascii=False),
            ]
        ).lower()
        return any(hint in blob for hint in {"rate", "limit", "throttle", "quota", "pagination"})

    def _analyze_probe_response(
        self,
        response: requests.Response,
        label: str,
        url: str,
        probe_method: str,
        original_method: str,
        auth_provided: bool,
    ) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        headers = {str(key): str(value) for key, value in dict(response.headers or {}).items()}
        lower_headers = {str(key).lower(): str(value) for key, value in headers.items()}
        parsed = urlparse(url)
        body_preview = (response.text or "")[:1200]
        content_type = lower_headers.get("content-type", "").lower()
        allow_header = lower_headers.get("allow", "")

        if parsed.scheme == "http":
            findings.append(
                self._make_finding(
                    "high",
                    "transport",
                    "基线探测发现目标使用 HTTP",
                    label,
                    url,
                    "建议统一走 HTTPS，并在网关层配置 301/308 跳转和 HSTS。",
                    "API8:2023",
                )
            )

        if parsed.scheme == "https" and "strict-transport-security" not in lower_headers:
            findings.append(
                self._make_finding(
                    "medium",
                    "headers",
                    "缺少 HSTS",
                    label,
                    f"{probe_method} {url}",
                    "建议在 HTTPS 响应中下发 Strict-Transport-Security，避免降级和首次访问劫持。",
                    "API8:2023",
                )
            )

        if "x-content-type-options" not in lower_headers:
            findings.append(
                self._make_finding(
                    "low",
                    "headers",
                    "缺少 X-Content-Type-Options",
                    label,
                    f"{probe_method} {url}",
                    "建议返回 X-Content-Type-Options: nosniff，降低 MIME 混淆风险。",
                    "API8:2023",
                )
            )

        if "text/html" in content_type and "content-security-policy" not in lower_headers:
            findings.append(
                self._make_finding(
                    "low",
                    "headers",
                    "HTML 响应缺少 Content-Security-Policy",
                    label,
                    f"{probe_method} {url}",
                    "如果接口网关或门户返回 HTML，建议评估 CSP、frame-ancestors 等前端安全策略。",
                    "API8:2023",
                )
            )

        cors_origin = lower_headers.get("access-control-allow-origin", "")
        cors_credentials = lower_headers.get("access-control-allow-credentials", "").lower()
        if cors_origin == "*" and cors_credentials == "true":
            findings.append(
                self._make_finding(
                    "high",
                    "cors",
                    "CORS 配置存在高风险通配",
                    label,
                    "Access-Control-Allow-Origin=* 且 Allow-Credentials=true",
                    "这会造成高风险跨域配置，建议改为精确白名单并避免和凭证同时使用通配。",
                    "API8:2023",
                )
            )
        elif cors_origin == "*":
            findings.append(
                self._make_finding(
                    "medium",
                    "cors",
                    "CORS 允许任意来源",
                    label,
                    "Access-Control-Allow-Origin=*",
                    "确认该接口是否真的允许所有来源访问；对于鉴权接口，建议改成精确白名单。",
                    "API8:2023",
                )
            )

        if "trace" in allow_header.lower():
            findings.append(
                self._make_finding(
                    "high",
                    "methods",
                    "Allow 头暴露 TRACE 方法",
                    label,
                    allow_header,
                    "建议关闭 TRACE 等不必要方法，并仅暴露接口实际需要的 HTTP 方法。",
                    "API8:2023",
                )
            )

        if "server" in lower_headers:
            findings.append(
                self._make_finding(
                    "info",
                    "fingerprint",
                    "Server 头暴露服务指纹",
                    label,
                    headers.get("Server", ""),
                    "可按内部规范隐藏或弱化服务端指纹，减少被动指纹信息暴露。",
                    "API8:2023",
                )
            )
        if "x-powered-by" in lower_headers:
            findings.append(
                self._make_finding(
                    "info",
                    "fingerprint",
                    "X-Powered-By 暴露技术栈",
                    label,
                    headers.get("X-Powered-By", ""),
                    "建议移除 X-Powered-By 等框架指纹响应头。",
                    "API8:2023",
                )
            )

        set_cookie = lower_headers.get("set-cookie", "")
        if set_cookie:
            cookie_issues = []
            if "secure" not in set_cookie.lower():
                cookie_issues.append("Secure")
            if "httponly" not in set_cookie.lower():
                cookie_issues.append("HttpOnly")
            if "samesite" not in set_cookie.lower():
                cookie_issues.append("SameSite")
            if cookie_issues:
                findings.append(
                    self._make_finding(
                        "medium",
                        "cookie",
                        "Cookie 安全属性不完整",
                        label,
                        ", ".join(cookie_issues),
                        "对会话 Cookie 建议至少补齐 Secure、HttpOnly 和 SameSite 属性。",
                        "API8:2023",
                    )
                )

        error_leaks = self._find_error_leaks(body_preview)
        if error_leaks:
            findings.append(
                self._make_finding(
                    "medium",
                    "error_leak",
                    "响应体存在错误泄露迹象",
                    label,
                    ", ".join(error_leaks[:5]),
                    "建议统一错误处理和错误码输出，不向调用方暴露调试栈、SQL 语句或内部类名。",
                    "API8:2023",
                )
            )

        if not auth_provided and response.status_code < 400 and self._looks_sensitive_runtime_target(label, url):
            findings.append(
                self._make_finding(
                    "medium",
                    "auth_runtime_review",
                    "敏感接口在未显式携带鉴权头时可访问，需要人工复核",
                    label,
                    f"{probe_method} {url} -> {response.status_code}",
                    "请人工确认该接口是否本应公开；如果不是，建议补测匿名/低权限用户下的 401/403 场景。",
                    "API1:2023",
                )
            )

        if response.status_code < 400 and self._looks_sensitive_runtime_target(label, url) and "cache-control" not in lower_headers:
            findings.append(
                self._make_finding(
                    "low",
                    "cache_review",
                    "敏感接口未体现缓存控制头",
                    label,
                    f"{probe_method} {url}",
                    "建议对认证、用户、Token、个人资料等接口评估 Cache-Control/Pragma/Expires 策略。",
                    "API8:2023",
                )
            )

        return findings

    def _looks_sensitive_runtime_target(self, label: str, url: str) -> bool:
        blob = f"{label} {url}".lower()
        return any(hint in blob for hint in self.ADMIN_HINTS | self.CACHE_HINTS)

    def _interface_blob(self, interface: Dict[str, Any]) -> str:
        return " ".join(
            [
                str(interface.get("name", "") or ""),
                str(interface.get("description", "") or ""),
                str(interface.get("path", "") or ""),
                str(interface.get("method", "") or ""),
            ]
        ).lower()

    def _group_findings(self, findings: List[Dict[str, Any]], key: str, limit: int = 20) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, Any]] = {}
        for item in findings:
            group_key = str(item.get(key, "") or "未分类")
            bucket = grouped.setdefault(
                group_key,
                {
                    "Group": group_key,
                    "Count": 0,
                    "Top Severity": "none",
                    "Top Source": "",
                    "Highlights": "",
                },
            )
            bucket["Count"] += 1
            severity = str(item.get("Severity", "info")).lower()
            if self._severity_rank(severity) < self._severity_rank(bucket.get("Top Severity", "none")):
                bucket["Top Severity"] = severity
                bucket["Top Source"] = str(item.get("Source", "") or "")
                bucket["Highlights"] = str(item.get("Title", "") or "")
        rows = list(grouped.values())
        rows.sort(key=lambda item: (self._severity_rank(item.get("Top Severity", "none")), -item.get("Count", 0), item.get("Group", "")))
        return rows[:limit]

    def _group_findings_by_target(
        self,
        passive_report: Optional[Dict[str, Any]] = None,
        probe_report: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, List[Dict[str, Any]]]:
        grouped: Dict[str, List[Dict[str, Any]]] = {}
        for source, report in [("被动审计", passive_report or {}), ("基线探测", probe_report or {})]:
            for item in list(report.get("findings") or []):
                target = str(item.get("Target", "") or "")
                grouped.setdefault(target, []).append(dict(item, Source=source))
        return grouped

    def _normalize_role_profiles(self, role_profiles: Optional[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
        profiles = []
        raw_profiles = role_profiles or [{"role": "匿名用户", "headers": {}}]
        for item in raw_profiles:
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or item.get("name") or "").strip() or f"角色{len(profiles) + 1}"
            headers = item.get("headers") if isinstance(item.get("headers"), dict) else {}
            profiles.append({"role": role, "headers": deepcopy(headers)})
        if not profiles:
            profiles.append({"role": "匿名用户", "headers": {}})
        return profiles

    def _build_role_comparison_rows(self, role_reports: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        grouped: Dict[tuple[str, str, str], Dict[str, Any]] = {}
        role_names = [str(item.get("role", "")) for item in role_reports]

        for role_report in role_reports:
            role = str(role_report.get("role", ""))
            report = role_report.get("report", {}) or {}
            for sample in list(report.get("samples") or []):
                key = (
                    str(sample.get("Label", "")),
                    str(sample.get("Probe Method", "")),
                    str(sample.get("URL", "")),
                )
                row = grouped.setdefault(
                    key,
                    {
                        "Label": key[0],
                        "Probe Method": key[1],
                        "URL": key[2],
                    },
                )
                row[role] = int(sample.get("Status Code", 0) or 0)

        rows = []
        for _, row in grouped.items():
            status_parts = []
            success_roles = []
            for role in role_names:
                code = int(row.get(role, 0) or 0)
                status_parts.append(f"{role}:{code}")
                if self._status_bucket(code) == "allow":
                    success_roles.append(role)
            sensitivity = "high" if self._looks_sensitive_runtime_target(row.get("Label", ""), row.get("URL", "")) else "medium"
            row["Sensitivity"] = sensitivity
            row["Status Pattern"] = " | ".join(status_parts)
            row["Success Roles"] = ", ".join(success_roles) or "无"
            row["Diversity"] = "有差异" if len({int(row.get(role, 0) or 0) for role in role_names}) > 1 else "一致"
            rows.append(row)

        rows.sort(key=lambda item: (item.get("Sensitivity", ""), item.get("Label", ""), item.get("Probe Method", "")))
        return rows

    def _analyze_role_comparison_rows(self, comparison_rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        findings = []
        for row in comparison_rows:
            role_codes = {
                key: int(value)
                for key, value in row.items()
                if key not in {"Label", "Probe Method", "URL", "Sensitivity", "Status Pattern", "Success Roles", "Diversity"}
            }
            if not role_codes:
                continue

            ranked_roles = sorted(role_codes.keys(), key=self._role_rank)
            lowest_role = ranked_roles[0]
            highest_role = ranked_roles[-1]
            lowest_code = role_codes.get(lowest_role, 0)
            highest_code = role_codes.get(highest_role, 0)
            sensitivity = str(row.get("Sensitivity", "medium")).lower()
            label = str(row.get("Label", ""))
            evidence = row.get("Status Pattern", "")

            if sensitivity == "high" and self._status_bucket(lowest_code) == "allow":
                severity = "high" if self._role_rank(lowest_role) == 0 else "medium"
                findings.append(
                    self._make_finding(
                        severity,
                        "role_regression",
                        "敏感接口在低权限角色下可访问，需要人工复核",
                        label,
                        evidence,
                        "建议对该接口做匿名、低权限、越权对象 ID 和跨租户场景复测，确认是否应返回 401/403/404。",
                        "API5:2023",
                    )
                )

            if sensitivity == "high" and self._status_bucket(lowest_code) == self._status_bucket(highest_code) == "allow":
                findings.append(
                    self._make_finding(
                        "medium",
                        "role_regression",
                        "敏感接口在低高权限角色下结果无差异",
                        label,
                        evidence,
                        "建议结合对象 ID、字段级权限和业务流校验该接口是否真的应对不同角色返回一致结果。",
                        "API1:2023",
                    )
                )

            if self._role_rank(highest_role) > self._role_rank(lowest_role) and self._status_bucket(highest_code) == "deny" and self._status_bucket(lowest_code) == "allow":
                findings.append(
                    self._make_finding(
                        "low",
                        "role_regression",
                        "高权限角色结果反而弱于低权限角色",
                        label,
                        evidence,
                        "建议检查角色路由、网关策略和测试凭证是否配置正确，避免出现权限映射异常。",
                        "API5:2023",
                    )
                )

        return findings

    def _role_rank(self, role: str) -> int:
        blob = str(role or "").lower()
        if any(item in blob for item in ["匿名", "anonymous", "guest"]):
            return 0
        if any(item in blob for item in ["普通", "user", "member", "customer"]):
            return 1
        if any(item in blob for item in ["管理员", "admin", "ops", "operator", "root"]):
            return 3
        if any(item in blob for item in ["跨租户", "越权", "cross", "other tenant"]):
            return 1
        return 2

    def _status_bucket(self, status_code: int) -> str:
        code = int(status_code or 0)
        if 200 <= code < 400:
            return "allow"
        if code in {401, 403, 404}:
            return "deny"
        if code <= 0:
            return "error"
        return "other"

    def _suite_name_for_category(self, category: str) -> str:
        mapping = {
            "transport": "传输与协议回归",
            "headers": "安全头基线回归",
            "cors": "跨域配置回归",
            "methods": "方法暴露回归",
            "fingerprint": "指纹暴露回归",
            "cookie": "Cookie 安全回归",
            "auth_review": "鉴权回归",
            "admin_review": "功能权限回归",
            "auth_runtime_review": "匿名访问回归",
            "sensitive_url": "敏感参数回归",
            "sensitive_response": "敏感数据泄露回归",
            "error_leak": "错误泄露回归",
            "upload_review": "上传安全回归",
            "ssrf_review": "SSRF 参数回归",
            "resource_control": "资源控制回归",
            "cache_review": "缓存控制回归",
            "probe_error": "可达性与环境回归",
            "inventory": "接口清单回归",
        }
        return mapping.get(category, "通用安全回归")

    def _expected_for_category(self, category: str) -> str:
        mapping = {
            "transport": "统一使用 HTTPS，且网关具备强制跳转/HSTS 策略",
            "headers": "返回安全头且满足内部基线",
            "cors": "仅允许白名单来源，且不与凭证通配组合",
            "methods": "仅暴露必要 HTTP 方法，不返回 TRACE",
            "fingerprint": "不暴露敏感指纹头或弱化版本信息",
            "cookie": "Cookie 至少具备 Secure/HttpOnly/SameSite",
            "auth_review": "未授权返回 401/403，授权后按角色放行",
            "admin_review": "普通用户不可访问管理功能，管理员按最小权限放行",
            "auth_runtime_review": "匿名访问敏感接口应被拒绝",
            "sensitive_url": "敏感凭据不出现在 path/query 中",
            "sensitive_response": "响应字段按角色裁剪或脱敏",
            "error_leak": "错误返回不包含堆栈、SQL、内部类名",
            "upload_review": "上传接口具备类型/大小/病毒扫描等限制",
            "ssrf_review": "URL/回调参数具备协议白名单和内网访问限制",
            "resource_control": "列表/批量/导出接口具备分页、限流和大小控制",
            "cache_review": "敏感接口具备合理 Cache-Control 策略",
        }
        return mapping.get(category, "按安全基线和业务权限预期通过复测")

    def _priority_from_severity(self, severity: str) -> str:
        mapping = {"high": "P0", "medium": "P1", "low": "P2", "info": "P3"}
        return mapping.get(str(severity).lower(), "P3")

    def _classify_authorization_risk(self, interface: Dict[str, Any]) -> str:
        method = str(interface.get("method") or "GET").upper()
        if self._looks_admin_endpoint(interface) or self._looks_business_endpoint(interface):
            return "high"
        if method in self.MUTATING_METHODS or self._has_object_reference(interface):
            return "high"
        if self._has_visible_auth(interface.get("headers", {})) or not self._looks_public_endpoint(interface):
            return "medium"
        return "low"

    def _looks_public_endpoint(self, interface: Dict[str, Any]) -> bool:
        blob = self._interface_blob(interface)
        return any(hint in blob for hint in self.PUBLIC_HINTS)

    def _looks_admin_endpoint(self, interface: Dict[str, Any]) -> bool:
        return any(hint in self._interface_blob(interface) for hint in self.ADMIN_HINTS)

    def _looks_business_endpoint(self, interface: Dict[str, Any]) -> bool:
        return any(hint in self._interface_blob(interface) for hint in self.BUSINESS_HINTS)

    def _has_object_reference(self, interface: Dict[str, Any]) -> bool:
        path = str(interface.get("path") or "").lower()
        path_params = set(str(key).lower() for key in (interface.get("path_params") or {}).keys())
        query_params = set(str(key).lower() for key in (interface.get("query_params") or {}).keys())
        if "{" in path and "}" in path:
            return True
        all_keys = path_params | query_params
        return any(key in self.OBJECT_ID_HINTS or key.endswith("_id") for key in all_keys)

    def _role_expectation(
        self,
        role: str,
        interface: Dict[str, Any],
        risk: str,
        public_endpoint: bool,
        admin_endpoint: bool,
        object_related: bool,
    ) -> tuple[str, str]:
        role_blob = str(role).lower()
        method = str(interface.get("method") or "GET").upper()
        write_endpoint = method in self.MUTATING_METHODS

        if any(key in role_blob for key in ["匿名", "anonymous", "guest"]):
            if public_endpoint and method in {"GET", "HEAD", "OPTIONS"}:
                return "建议允许", "200/204，确认无敏感字段泄露"
            return "建议拒绝", "401/403"

        if any(key in role_blob for key in ["跨租户", "越权", "cross", "other tenant"]):
            return "建议拒绝", "403/404，替换对象 ID 后不能越权访问"

        if any(key in role_blob for key in ["管理员", "admin", "ops", "operator"]):
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
        variables = []
        for key in auth_headers:
            normalized = "".join(ch.lower() if ch.isalnum() else "_" for ch in str(key))
            normalized = normalized.strip("_") or "custom_header"
            placeholder = f"<fill-{normalized}>"
            variables.append({"header": str(key), "variable": f"auth_{normalized}", "value": placeholder})
        return variables

    def _build_nuclei_headers_template(
        self,
        paths: List[str],
        origin: str,
        header_variables: List[Dict[str, str]],
    ) -> str:
        lines = [
            "id: api-security-headers-baseline",
            "",
            "info:",
            "  name: API Security Headers Baseline",
            "  author: test-toolkit",
            "  severity: info",
            "  description: Safe baseline checks for missing HSTS, missing X-Content-Type-Options and banner leakage.",
            "  tags: api,security,baseline,headers",
            "",
            "variables:",
            f'  audit_origin: "{self._yaml_quote(origin or "https://security-audit.local")}"',
        ]
        for item in header_variables:
            lines.append(f'  {item["variable"]}: "{self._yaml_quote(item["value"])}"')
        lines.extend(["", "http:", "  - method: GET", "    path:"])
        for path in paths:
            lines.append(f'      - "{{{{BaseURL}}}}{self._normalize_template_path(path)}"')
        lines.extend(
            [
                "    headers:",
                '      Accept: "application/json, text/plain, */*"',
                '      Origin: "{{audit_origin}}"',
            ]
        )
        for item in header_variables:
            lines.append(f'      {item["header"]}: "{{{{{item["variable"]}}}}}"')
        lines.extend(
            [
                "    stop-at-first-match: false",
                "    matchers-condition: or",
                "    matchers:",
                "      - type: dsl",
                "        name: missing-hsts",
                "        dsl:",
                "          - '!contains(tolower(all_headers), \"strict-transport-security\")'",
                "      - type: dsl",
                "        name: missing-x-content-type-options",
                "        dsl:",
                "          - '!contains(tolower(all_headers), \"x-content-type-options\")'",
                "      - type: dsl",
                "        name: tech-banner",
                "        dsl:",
                "          - 'contains(tolower(all_headers), \"server:\") || contains(tolower(all_headers), \"x-powered-by:\")'",
            ]
        )
        return "\n".join(lines)

    def _build_nuclei_options_template(
        self,
        paths: List[str],
        origin: str,
        header_variables: List[Dict[str, str]],
    ) -> str:
        lines = [
            "id: api-cors-methods-exposure",
            "",
            "info:",
            "  name: API CORS And Method Exposure",
            "  author: test-toolkit",
            "  severity: info",
            "  description: Safe baseline checks for wildcard CORS and exposed TRACE/unsafe methods.",
            "  tags: api,security,cors,methods",
            "",
            "variables:",
            f'  audit_origin: "{self._yaml_quote(origin or "https://security-audit.local")}"',
        ]
        for item in header_variables:
            lines.append(f'  {item["variable"]}: "{self._yaml_quote(item["value"])}"')
        lines.extend(["", "http:", "  - method: OPTIONS", "    path:"])
        for path in paths:
            lines.append(f'      - "{{{{BaseURL}}}}{self._normalize_template_path(path)}"')
        lines.extend(
            [
                "    headers:",
                '      Origin: "{{audit_origin}}"',
                '      Access-Control-Request-Method: "GET"',
            ]
        )
        for item in header_variables:
            lines.append(f'      {item["header"]}: "{{{{{item["variable"]}}}}}"')
        lines.extend(
            [
                "    stop-at-first-match: false",
                "    matchers-condition: or",
                "    matchers:",
                "      - type: dsl",
                "        name: cors-wildcard-with-creds",
                "        dsl:",
                "          - 'contains(tolower(all_headers), \"access-control-allow-origin: *\") && contains(tolower(all_headers), \"access-control-allow-credentials: true\")'",
                "      - type: dsl",
                "        name: trace-enabled",
                "        dsl:",
                "          - 'contains(tolower(all_headers), \"allow:\") && contains(tolower(all_headers), \"trace\")'",
            ]
        )
        return "\n".join(lines)

    def _build_nuclei_cache_template(
        self,
        paths: List[str],
        origin: str,
        header_variables: List[Dict[str, str]],
    ) -> str:
        lines = [
            "id: api-sensitive-cache-review",
            "",
            "info:",
            "  name: API Sensitive Cache Review",
            "  author: test-toolkit",
            "  severity: info",
            "  description: Safe baseline checks for sensitive surfaces missing cache-control guidance or returning debug markers.",
            "  tags: api,security,cache,sensitive",
            "",
            "variables:",
            f'  audit_origin: "{self._yaml_quote(origin or "https://security-audit.local")}"',
        ]
        for item in header_variables:
            lines.append(f'  {item["variable"]}: "{self._yaml_quote(item["value"])}"')
        lines.extend(["", "http:", "  - method: GET", "    path:"])
        for path in paths:
            lines.append(f'      - "{{{{BaseURL}}}}{self._normalize_template_path(path)}"')
        lines.extend(
            [
                "    headers:",
                '      Accept: "application/json, text/plain, */*"',
                '      Origin: "{{audit_origin}}"',
            ]
        )
        for item in header_variables:
            lines.append(f'      {item["header"]}: "{{{{{item["variable"]}}}}}"')
        lines.extend(
            [
                "    stop-at-first-match: false",
                "    matchers-condition: or",
                "    matchers:",
                "      - type: dsl",
                "        name: missing-cache-control",
                "        dsl:",
                "          - '!contains(tolower(all_headers), \"cache-control\")'",
                "      - type: dsl",
                "        name: debug-marker",
                "        dsl:",
                "          - 'contains(tolower(body), \"traceback\") || contains(tolower(body), \"stack trace\") || contains(tolower(body), \"exception\")'",
            ]
        )
        return "\n".join(lines)

    def _build_summary(self, interface_count: int, findings: List[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {
            "interface_count": interface_count,
            "finding_count": len(findings),
            "high": 0,
            "medium": 0,
            "low": 0,
            "info": 0,
        }
        for item in findings:
            severity = str(item.get("Severity", "info")).lower()
            if severity in summary:
                summary[severity] += 1
        return summary

    def _build_probe_summary(
        self,
        samples: List[Dict[str, Any]],
        findings: List[Dict[str, Any]],
        request_count: int,
    ) -> Dict[str, Any]:
        summary = self._build_summary(len({item.get("Label", "") for item in samples}), findings)
        responded = [item for item in samples if int(item.get("Status Code", 0) or 0) > 0]
        summary.update(
            {
                "request_count": request_count,
                "responded_count": len(responded),
                "success_rate": round((len(responded) / request_count * 100) if request_count else 0.0, 2),
            }
        )
        return summary

    def _manual_validation_text(self, owasp_code: str) -> str:
        manual_steps = {
            "API1:2023": "切换不同对象 ID、租户 ID、历史订单 ID 做越权验证。",
            "API2:2023": "验证 Token 过期、注销、并发登录、弱口令和多因子流程。",
            "API3:2023": "检查响应字段裁剪、只读字段写入和批量对象属性越权。",
            "API4:2023": "验证分页上限、批量导出、并发速率、超大请求体和超时控制。",
            "API5:2023": "针对普通用户、管理员、客服、运营角色做功能级权限矩阵测试。",
            "API6:2023": "重点审计注册、登录、找回密码、领券、支付、提现等关键业务流。",
            "API7:2023": "尝试不同协议、内网 IP、回环地址和 DNS 变体，确认服务端限制策略。",
            "API8:2023": "复核头部、Cookie、CORS、调试开关、默认配置和多余方法暴露。",
            "API9:2023": "核对接口清单、版本、环境、废弃接口和影子接口治理情况。",
            "API10:2023": "复核第三方 API 调用、Webhook、回调信任边界和上游错误处理。",
        }
        return manual_steps.get(owasp_code, "建议结合业务场景做人机协同复核。")

    def _bundle_to_markdown(self, bundle: Dict[str, Any]) -> str:
        passive_summary = bundle.get("passive_report", {}).get("summary", {})
        probe_summary = bundle.get("probe_report", {}).get("summary", {})
        role_regression = bundle.get("role_regression", {})
        checklist = bundle.get("owasp_checklist", [])
        scan_policy = bundle.get("scan_policy", {})
        auth_matrix = bundle.get("authorization_matrix", {})
        nuclei_pack = bundle.get("nuclei_template_pack", {})
        risk_dashboard = bundle.get("risk_dashboard", {})
        regression_suite = bundle.get("regression_suite", {})
        playbook = bundle.get("playbook_markdown", "")
        lines = [
            "# API 安全测试报告",
            "",
            f"- 生成时间: {bundle.get('generated_at', self._now())}",
            f"- 接口数: {bundle.get('plan', {}).get('scope', {}).get('interface_count', 0)}",
            f"- 目标数: {bundle.get('plan', {}).get('scope', {}).get('target_count', 0)}",
            "",
            "## 被动审计摘要",
            f"- Findings: {passive_summary.get('finding_count', 0)}",
            f"- High/Medium/Low/Info: {passive_summary.get('high', 0)}/{passive_summary.get('medium', 0)}/{passive_summary.get('low', 0)}/{passive_summary.get('info', 0)}",
            "",
            "## 基线探测摘要",
            f"- Requests: {probe_summary.get('request_count', 0)}",
            f"- Findings: {probe_summary.get('finding_count', 0)}",
            f"- High/Medium/Low/Info: {probe_summary.get('high', 0)}/{probe_summary.get('medium', 0)}/{probe_summary.get('low', 0)}/{probe_summary.get('info', 0)}",
        ]
        if role_regression:
            lines.extend(
                [
                    "",
                    "## 多角色回归摘要",
                    f"- 角色数: {role_regression.get('summary', {}).get('role_count', 0)}",
                    f"- 差异对比数: {role_regression.get('summary', {}).get('comparison_count', 0)}",
                    f"- Findings: {role_regression.get('summary', {}).get('finding_count', 0)}",
                ]
            )
        lines.extend(["", "## OWASP API Top 10 清单"])
        for item in checklist:
            lines.append(
                f"- {item.get('OWASP', '')} {item.get('Category', '')}: {item.get('Status', '')} | {item.get('Focus', '')}"
            )
        if auth_matrix:
            lines.extend(
                [
                    "",
                    "## 权限矩阵摘要",
                    f"- 接口数: {auth_matrix.get('summary', {}).get('interface_count', 0)}",
                    f"- 角色数: {auth_matrix.get('summary', {}).get('role_count', 0)}",
                    f"- 场景数: {auth_matrix.get('summary', {}).get('scenario_count', 0)}",
                    f"- 高风险接口数: {auth_matrix.get('summary', {}).get('high_risk_interfaces', 0)}",
                ]
            )
        if nuclei_pack:
            lines.extend(
                [
                    "",
                    "## Nuclei 模板包摘要",
                    f"- 模板数: {nuclei_pack.get('template_count', 0)}",
                    f"- 路径数: {nuclei_pack.get('path_count', 0)}",
                ]
            )
        if risk_dashboard:
            lines.extend(
                [
                    "",
                    "## 风险看板摘要",
                    f"- Findings: {risk_dashboard.get('summary', {}).get('finding_count', 0)}",
                    f"- High/Medium/Low/Info: {risk_dashboard.get('summary', {}).get('high', 0)}/{risk_dashboard.get('summary', {}).get('medium', 0)}/{risk_dashboard.get('summary', {}).get('low', 0)}/{risk_dashboard.get('summary', {}).get('info', 0)}",
                ]
            )
        if regression_suite:
            lines.extend(
                [
                    "",
                    "## 回归套件摘要",
                    f"- 套件数: {regression_suite.get('summary', {}).get('suite_count', 0)}",
                    f"- 场景数: {regression_suite.get('summary', {}).get('scenario_count', 0)}",
                    f"- P0/P1/P2/P3: {regression_suite.get('summary', {}).get('p0', 0)}/{regression_suite.get('summary', {}).get('p1', 0)}/{regression_suite.get('summary', {}).get('p2', 0)}/{regression_suite.get('summary', {}).get('p3', 0)}",
                ]
            )
        lines.extend(["", "## 扫描策略", f"- 模式: {scan_policy.get('mode', 'safe-baseline')}"])
        for item in scan_policy.get("guardrails", []):
            lines.append(f"- {item}")
        lines.extend(["", "## 安全测试剧本", "", playbook])
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
    ) -> Dict[str, Any]:
        return {
            "Severity": severity,
            "Category": category,
            "Title": title,
            "Target": target,
            "Evidence": evidence,
            "Recommendation": recommendation,
            "OWASP": owasp,
        }

    def _dedupe_findings(self, findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped = {}
        for item in findings:
            key = (
                item.get("Severity", ""),
                item.get("Category", ""),
                item.get("Title", ""),
                item.get("Target", ""),
                item.get("Evidence", ""),
            )
            deduped[key] = item
        sorted_items = list(deduped.values())
        sorted_items.sort(key=lambda item: (self._severity_rank(item.get("Severity", "info")), item.get("Target", "")))
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
        if not findings:
            return "none"
        return min((str(item.get("Severity", "info")).lower() for item in findings), key=self._severity_rank)

    def _severity_rank(self, severity: str) -> int:
        order = {"high": 0, "medium": 1, "low": 2, "info": 3, "none": 4}
        return order.get(str(severity).lower(), 5)

    def _normalize_template_path(self, path: Any) -> str:
        text = str(path or "/").strip() or "/"
        if text.startswith(("http://", "https://")):
            parsed = urlparse(text)
            text = parsed.path or "/"
            if parsed.query:
                text += f"?{parsed.query}"
        if not text.startswith("/"):
            text = "/" + text.lstrip("/")
        return text

    def _yaml_quote(self, value: str) -> str:
        return str(value).replace("\\", "\\\\").replace('"', '\\"')

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
