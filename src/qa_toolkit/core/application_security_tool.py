import io
import ipaddress
import json
import plistlib
import re
import socket
import ssl
import struct
import subprocess
import tempfile
import zipfile
from collections import deque
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple
from urllib.parse import urljoin, urldefrag, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup


class ApplicationSecurityTool:
    """应用安全测试工具，支持 APK/IPA 静态包分析和 Web 站点基线扫描。"""

    APK_COMPONENT_TAGS = {"activity", "activity-alias", "service", "receiver", "provider"}
    APK_HIGH_RISK_PERMISSIONS = {
        "android.permission.READ_SMS",
        "android.permission.RECEIVE_SMS",
        "android.permission.SEND_SMS",
        "android.permission.READ_CONTACTS",
        "android.permission.WRITE_CONTACTS",
        "android.permission.READ_CALL_LOG",
        "android.permission.WRITE_CALL_LOG",
        "android.permission.READ_PHONE_STATE",
        "android.permission.RECORD_AUDIO",
        "android.permission.CAMERA",
        "android.permission.ACCESS_FINE_LOCATION",
        "android.permission.ACCESS_BACKGROUND_LOCATION",
        "android.permission.MANAGE_EXTERNAL_STORAGE",
        "android.permission.QUERY_ALL_PACKAGES",
    }
    APK_MEDIUM_RISK_PERMISSIONS = {
        "android.permission.ACCESS_COARSE_LOCATION",
        "android.permission.READ_EXTERNAL_STORAGE",
        "android.permission.WRITE_EXTERNAL_STORAGE",
        "android.permission.READ_MEDIA_AUDIO",
        "android.permission.READ_MEDIA_VIDEO",
        "android.permission.READ_MEDIA_IMAGES",
        "android.permission.POST_NOTIFICATIONS",
        "android.permission.BLUETOOTH_CONNECT",
        "android.permission.BLUETOOTH_SCAN",
    }
    APK_SPECIAL_PERMISSIONS = {
        "android.permission.SYSTEM_ALERT_WINDOW",
        "android.permission.REQUEST_INSTALL_PACKAGES",
        "android.permission.PACKAGE_USAGE_STATS",
        "android.permission.BIND_ACCESSIBILITY_SERVICE",
        "android.permission.WRITE_SETTINGS",
        "android.permission.REQUEST_IGNORE_BATTERY_OPTIMIZATIONS",
    }
    SDK_HINTS = {
        "Firebase": ["firebase", "googleanalytics", "crashlytics"],
        "Facebook": ["facebook", "fbsdk"],
        "Bugly": ["bugly", "com.tencent.bugly"],
        "Umeng": ["umeng", "com.umeng"],
        "Adjust": ["adjust", "com.adjust"],
        "AppsFlyer": ["appsflyer", "com.appsflyer"],
        "JPush": ["jpush", "cn.jpush"],
        "腾讯系": ["com.tencent", "wechat", "wxapi", "qqapi"],
        "支付宝": ["alipay", "com.alipay"],
        "OkHttp": ["okhttp"],
        "Retrofit": ["retrofit"],
        "Xposed": ["xposed"],
    }
    SECRET_PATTERNS = [
        ("Private Key", re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----")),
        ("AWS Access Key", re.compile(r"AKIA[0-9A-Z]{16}")),
        ("Google API Key", re.compile(r"AIza[0-9A-Za-z\-_]{35}")),
        ("Bearer Token", re.compile(r"Bearer\s+[A-Za-z0-9\-_=\.]{20,}", re.IGNORECASE)),
        (
            "Credential Assignment",
            re.compile(
                r"(?i)(api[_-]?key|client[_-]?secret|access[_-]?token|refresh[_-]?token|password|passwd|secret)"
                r"\s*[:=]\s*['\"]?[A-Za-z0-9_./+=\-]{8,}"
            ),
        ),
    ]
    URL_REGEX = re.compile(r"https?://[^\s'\"<>)]{4,}")
    IPV4_REGEX = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
    DEBUG_HOST_HINTS = ("dev", "test", "uat", "staging", "debug", "sit", "10.", "192.168.", "172.16.")
    IGNORED_URL_PREFIXES = (
        "http://www.apple.com/DTD",
        "http://www.w3.org/",
        "https://www.w3.org/",
    )
    WEB_ERROR_MARKERS = {
        "stack trace",
        "traceback",
        "exception",
        "sql syntax",
        "warning:",
        "notice:",
        "debug",
        "fatal error",
    }
    WEB_COMMON_PATHS = [
        {
            "path": "/robots.txt",
            "title": "robots.txt 可访问",
            "severity": "info",
            "category": "inventory",
            "recommendation": "可结合 robots.txt 和 sitemap.xml 继续梳理站点暴露面。",
        },
        {
            "path": "/sitemap.xml",
            "title": "sitemap.xml 可访问",
            "severity": "info",
            "category": "inventory",
            "recommendation": "建议结合该清单复核是否暴露了调试页、后台页或历史路径。",
        },
        {
            "path": "/.git/HEAD",
            "title": ".git 目录暴露",
            "severity": "high",
            "category": "exposure",
            "recommendation": "应立即禁止 Web 根目录下的 Git 元数据访问，避免源码和提交历史泄露。",
        },
        {
            "path": "/.env",
            "title": ".env 文件暴露",
            "severity": "high",
            "category": "exposure",
            "recommendation": "应禁止环境变量文件外露，并轮换可能已暴露的密钥和口令。",
        },
        {
            "path": "/phpinfo.php",
            "title": "phpinfo 页面暴露",
            "severity": "high",
            "category": "fingerprint",
            "recommendation": "移除 phpinfo 一类诊断页，避免系统路径、扩展和版本信息泄露。",
        },
        {
            "path": "/swagger-ui.html",
            "title": "Swagger UI 可访问",
            "severity": "medium",
            "category": "inventory",
            "recommendation": "确认文档环境与生产隔离，必要时加鉴权或仅允许内网访问。",
        },
        {
            "path": "/swagger-ui/",
            "title": "Swagger UI 目录可访问",
            "severity": "medium",
            "category": "inventory",
            "recommendation": "确认文档环境与生产隔离，必要时加鉴权或仅允许内网访问。",
        },
        {
            "path": "/v2/api-docs",
            "title": "Swagger/OpenAPI JSON 可访问",
            "severity": "medium",
            "category": "inventory",
            "recommendation": "确认是否应对外暴露完整 API 清单，并检查是否泄露内网地址和调试接口。",
        },
        {
            "path": "/v3/api-docs",
            "title": "OpenAPI JSON 可访问",
            "severity": "medium",
            "category": "inventory",
            "recommendation": "确认是否应对外暴露完整 API 清单，并检查是否泄露内网地址和调试接口。",
        },
        {
            "path": "/actuator",
            "title": "Actuator 根路径可访问",
            "severity": "medium",
            "category": "exposure",
            "recommendation": "建议限制 Spring Actuator 的对外访问，并移除不必要端点。",
        },
        {
            "path": "/actuator/health",
            "title": "Actuator health 可访问",
            "severity": "low",
            "category": "exposure",
            "recommendation": "确认健康检查内容是否脱敏，避免泄露依赖组件状态。",
        },
        {
            "path": "/metrics",
            "title": "metrics 端点可访问",
            "severity": "medium",
            "category": "exposure",
            "recommendation": "建议限制性能/监控端点访问范围，避免系统指标对外泄露。",
        },
        {
            "path": "/prometheus",
            "title": "Prometheus 指标可访问",
            "severity": "medium",
            "category": "exposure",
            "recommendation": "建议限制 Prometheus 指标对外访问，避免泄露服务内部指标。",
        },
        {
            "path": "/server-status",
            "title": "server-status 可访问",
            "severity": "high",
            "category": "exposure",
            "recommendation": "应关闭 Apache server-status 对公网开放。",
        },
        {
            "path": "/graphql",
            "title": "GraphQL 端点可访问",
            "severity": "info",
            "category": "inventory",
            "recommendation": "建议进一步复核 GraphQL introspection、鉴权和字段级授权策略。",
        },
        {
            "path": "/admin",
            "title": "后台路径可访问",
            "severity": "info",
            "category": "inventory",
            "recommendation": "建议确认后台路径是否做了强鉴权、MFA 和来源限制。",
        },
        {
            "path": "/debug",
            "title": "调试路径可访问",
            "severity": "medium",
            "category": "exposure",
            "recommendation": "建议关闭线上调试入口，并检查是否存在额外调试信息泄露。",
        },
    ]

    def scan_mobile_package(
        self,
        file_name: str,
        file_bytes: bytes,
        custom_keywords: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        suffix = Path(file_name or "").suffix.lower()
        keywords = self._normalize_keywords(custom_keywords)
        with tempfile.TemporaryDirectory(prefix="app-sec-") as temp_dir:
            package_path = Path(temp_dir) / (Path(file_name).name or f"package{suffix or '.bin'}")
            package_path.write_bytes(file_bytes)
            if suffix == ".apk":
                result = self._scan_apk_package(package_path, file_bytes, keywords)
            elif suffix == ".ipa":
                result = self._scan_ipa_package(package_path, file_bytes, keywords)
            else:
                raise ValueError("仅支持上传 .apk 或 .ipa 文件。")

        result["summary"] = self._build_summary(result.get("findings", []))
        result["report_markdown"] = self.build_mobile_report_markdown(result)
        return result

    def scan_web_target(
        self,
        url: str,
        headers: Optional[Dict[str, Any]] = None,
        timeout_seconds: float = 12.0,
        verify_ssl: bool = True,
        max_pages: int = 8,
        include_common_paths: bool = True,
    ) -> Dict[str, Any]:
        normalized_url = self._normalize_url(url)
        session = requests.Session()
        session.headers.update(
            {
                "User-Agent": "ApplicationSecurityTool/1.0",
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            }
        )
        for key, value in (headers or {}).items():
            session.headers[str(key)] = str(value)

        findings: List[Dict[str, Any]] = []
        pages: List[Dict[str, Any]] = []
        forms: List[Dict[str, Any]] = []
        assets: List[Dict[str, Any]] = []
        common_path_results: List[Dict[str, Any]] = []
        visited: Set[str] = set()
        discovered: Set[str] = set()
        queue: Deque[str] = deque([normalized_url])
        root = self._site_root(normalized_url)
        same_origin = self._origin(normalized_url)
        robots_paths: List[str] = []

        while queue and len(visited) < max(int(max_pages), 1):
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            try:
                response = session.get(
                    current,
                    allow_redirects=True,
                    timeout=max(float(timeout_seconds), 1.0),
                    verify=bool(verify_ssl),
                )
            except Exception as exc:
                findings.append(
                    self._make_finding(
                        "medium",
                        "connectivity",
                        "页面请求失败",
                        current,
                        str(exc),
                        "确认目标 URL、网络连通性、证书链和访问 ACL，再在授权环境中重试。",
                        "OWASP WSTG-INFO / Deployment",
                    )
                )
                continue

            final_url = self._canonicalize_url(response.url)
            parsed_final = urlparse(final_url)
            body = response.text or ""
            lower_headers = {str(key).lower(): str(value) for key, value in dict(response.headers or {}).items()}
            content_type = lower_headers.get("content-type", "").lower()
            title = self._extract_html_title(body) if "html" in content_type else ""
            internal_links: List[str] = []
            page_forms: List[Dict[str, Any]] = []
            page_assets: List[Dict[str, Any]] = []

            if "html" in content_type:
                soup = BeautifulSoup(body, "html.parser")
                internal_links = self._extract_internal_links(final_url, soup, same_origin)
                page_forms = self._extract_forms(final_url, soup)
                page_assets = self._extract_assets(final_url, soup)
                forms.extend(page_forms)
                assets.extend(page_assets)
                findings.extend(self._analyze_forms(page_forms))
                findings.extend(self._analyze_html(body, title, final_url))
                for link in internal_links:
                    if link not in visited and link not in discovered and len(visited) + len(queue) < max(int(max_pages), 1) * 3:
                        queue.append(link)
                        discovered.add(link)

            if final_url == urljoin(root + "/", "robots.txt") and response.status_code < 400:
                robots_paths = self._extract_robots_paths(body)

            findings.extend(self._analyze_web_response(response, final_url))
            pages.append(
                {
                    "URL": final_url,
                    "Status Code": response.status_code,
                    "Content Type": content_type or "unknown",
                    "Title": title or "",
                    "Forms": len(page_forms),
                    "Scripts": sum(1 for item in page_assets if item.get("Type") == "script"),
                    "Internal Links": len(internal_links),
                    "Body Preview": body[:300],
                }
            )

        if include_common_paths:
            for rule in self.WEB_COMMON_PATHS:
                target_url = self._canonicalize_url(urljoin(root + "/", rule["path"].lstrip("/")))
                if any(item.get("URL") == target_url for item in pages):
                    continue
                try:
                    response = session.get(
                        target_url,
                        allow_redirects=False,
                        timeout=max(float(timeout_seconds), 1.0),
                        verify=bool(verify_ssl),
                    )
                    content_type = str(response.headers.get("Content-Type", "")).lower()
                    body_preview = (response.text or "")[:240]
                    common_path_results.append(
                        {
                            "Path": rule["path"],
                            "URL": target_url,
                            "Status Code": response.status_code,
                            "Content Type": content_type,
                            "Body Preview": body_preview,
                        }
                    )
                    if response.status_code < 400:
                        if rule["path"] == "/robots.txt":
                            robots_paths = self._extract_robots_paths(response.text or "")
                        findings.append(
                            self._make_finding(
                                rule["severity"],
                                rule["category"],
                                rule["title"],
                                target_url,
                                f"{response.status_code} {content_type}".strip(),
                                rule["recommendation"],
                                "OWASP WSTG-INFO / Exposure Review",
                            )
                        )
                except Exception as exc:
                    common_path_results.append(
                        {
                            "Path": rule["path"],
                            "URL": target_url,
                            "Status Code": 0,
                            "Content Type": "",
                            "Body Preview": str(exc),
                        }
                    )

        certificate = self._inspect_tls_certificate(normalized_url, timeout_seconds, verify_ssl)
        page_urls = [item.get("URL", "") for item in pages]
        findings = self._dedupe_findings(findings)

        result = {
            "generated_at": self._now(),
            "scan_type": "web",
            "target_url": normalized_url,
            "site_root": root,
            "verify_ssl": bool(verify_ssl),
            "crawl": {
                "pages_scanned": len(pages),
                "forms_found": len(forms),
                "assets_found": len(assets),
                "common_paths_tested": len(common_path_results),
                "robots_disallow_count": len(robots_paths),
                "page_urls": page_urls,
            },
            "certificate": certificate,
            "pages": pages,
            "forms": forms,
            "assets": assets,
            "robots_paths": robots_paths,
            "common_path_results": common_path_results,
            "findings": findings,
        }
        result["summary"] = self._build_summary(findings)
        result["report_markdown"] = self.build_web_report_markdown(result)
        return result

    def build_mobile_report_markdown(self, report: Dict[str, Any]) -> str:
        summary = report.get("summary", {})
        overview = report.get("overview", {})
        findings = list(report.get("findings") or [])
        lines = [
            "# 移动应用安全扫描报告",
            "",
            f"- 生成时间: {report.get('generated_at', self._now())}",
            f"- 文件名: {overview.get('file_name', '')}",
            f"- 文件类型: {overview.get('package_type', '').upper()}",
            f"- 标识: {overview.get('identifier', '') or '未识别'}",
            f"- 版本: {overview.get('version_name', '') or '-'} ({overview.get('version_code', '') or '-'})",
            f"- 发现总数: {summary.get('finding_count', 0)}",
            f"- High/Medium/Low/Info: {summary.get('high', 0)}/{summary.get('medium', 0)}/{summary.get('low', 0)}/{summary.get('info', 0)}",
            "",
            "## 概览",
        ]
        for key in ["min_sdk", "target_sdk", "permissions_count", "exported_component_count", "url_count", "sdk_count"]:
            if key in overview:
                lines.append(f"- {key}: {overview.get(key)}")

        lines.extend(["", "## 高优先级发现"])
        high_findings = [item for item in findings if str(item.get("Severity", "")).lower() in {"high", "medium"}][:12]
        if not high_findings:
            lines.append("- 当前未发现高优先级问题，建议继续人工复核权限、鉴权与外联配置。")
        else:
            for index, item in enumerate(high_findings, start=1):
                lines.append(f"{index}. [{str(item.get('Severity', '')).upper()}] {item.get('Title', '')}")
                lines.append(f"   - 目标: {item.get('Target', '')}")
                lines.append(f"   - 证据: {item.get('Evidence', '')}")
                lines.append(f"   - 建议: {item.get('Recommendation', '')}")

        if report.get("permissions"):
            lines.extend(["", "## 权限/能力摘要"])
            permissions = report.get("permissions", {})
            for label in ["high_risk", "medium_risk", "special", "usage_descriptions"]:
                values = permissions.get(label) or []
                if values:
                    lines.append(f"- {label}: {', '.join(str(item) for item in values[:15])}")

        if report.get("external_urls"):
            lines.extend(["", "## 外联 URL"])
            for item in list(report.get("external_urls") or [])[:20]:
                lines.append(f"- {item.get('Value', '')} ({item.get('Source', '')})")

        return "\n".join(lines)

    def build_web_report_markdown(self, report: Dict[str, Any]) -> str:
        summary = report.get("summary", {})
        crawl = report.get("crawl", {})
        findings = list(report.get("findings") or [])
        lines = [
            "# Web 站点安全扫描报告",
            "",
            f"- 生成时间: {report.get('generated_at', self._now())}",
            f"- 目标 URL: {report.get('target_url', '')}",
            f"- 扫描页面数: {crawl.get('pages_scanned', 0)}",
            f"- 表单数: {crawl.get('forms_found', 0)}",
            f"- 常见路径探测数: {crawl.get('common_paths_tested', 0)}",
            f"- 发现总数: {summary.get('finding_count', 0)}",
            f"- High/Medium/Low/Info: {summary.get('high', 0)}/{summary.get('medium', 0)}/{summary.get('low', 0)}/{summary.get('info', 0)}",
            "",
            "## 高优先级发现",
        ]

        priority_findings = [item for item in findings if str(item.get("Severity", "")).lower() in {"high", "medium"}][:15]
        if not priority_findings:
            lines.append("- 当前未发现高优先级问题，建议继续结合业务流做人工验证。")
        else:
            for index, item in enumerate(priority_findings, start=1):
                lines.append(f"{index}. [{str(item.get('Severity', '')).upper()}] {item.get('Title', '')}")
                lines.append(f"   - 目标: {item.get('Target', '')}")
                lines.append(f"   - 证据: {item.get('Evidence', '')}")
                lines.append(f"   - 建议: {item.get('Recommendation', '')}")

        if report.get("certificate"):
            certificate = report.get("certificate") or {}
            lines.extend(["", "## TLS 证书"])
            for key in ["subject", "issuer", "not_after", "serial_number"]:
                value = certificate.get(key)
                if value:
                    lines.append(f"- {key}: {value}")

        if report.get("robots_paths"):
            lines.extend(["", "## robots.txt 路径"])
            for item in list(report.get("robots_paths") or [])[:20]:
                lines.append(f"- {item}")

        return "\n".join(lines)

    def _scan_apk_package(
        self,
        package_path: Path,
        file_bytes: bytes,
        custom_keywords: Sequence[str],
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        permissions = {
            "all": [],
            "high_risk": [],
            "medium_risk": [],
            "special": [],
        }
        exported_components: List[Dict[str, Any]] = []
        deeplinks: List[Dict[str, Any]] = []
        external_urls: List[Dict[str, Any]] = []
        ip_hits: List[Dict[str, Any]] = []
        secret_hits: List[Dict[str, Any]] = []
        keyword_hits: List[Dict[str, Any]] = []
        sdk_inventory: Set[str] = set()
        certificate: Dict[str, Any] = {}
        native_libraries: List[str] = []
        manifest_summary: Dict[str, Any] = {}
        entries_summary: List[Dict[str, Any]] = []

        with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
            names = archive.namelist()
            manifest_data = archive.read("AndroidManifest.xml") if "AndroidManifest.xml" in names else b""
            if manifest_data:
                manifest_summary = self._parse_apk_manifest(manifest_data)
                permissions = manifest_summary.get("permissions", permissions)
                exported_components = manifest_summary.get("exported_components", [])
                deeplinks = manifest_summary.get("deeplinks", [])
                findings.extend(self._apk_manifest_findings(manifest_summary))

            for name in names:
                path = PurePosixPath(name)
                if path.suffix == ".so":
                    native_libraries.append(path.name)

                scan_level = self._zip_entry_scan_level(name)
                if scan_level == "skip":
                    continue
                info = archive.getinfo(name)
                if info.file_size > 20 * 1024 * 1024:
                    entries_summary.append({"Source": name, "Note": "skipped: file too large"})
                    continue
                try:
                    data = archive.read(name)
                except Exception:
                    continue
                text_items = self._extract_text_items(data, binary_mode=scan_level == "binary")
                signal = self._harvest_text_indicators(name, text_items, custom_keywords)
                external_urls.extend(signal["urls"])
                ip_hits.extend(signal["ips"])
                secret_hits.extend(signal["secrets"])
                keyword_hits.extend(signal["keywords"])
                sdk_inventory.update(signal["sdks"])
                if signal["note"]:
                    entries_summary.append({"Source": name, "Note": signal["note"]})

            certificate = self._inspect_apk_certificate(package_path, archive)

        if permissions.get("high_risk"):
            findings.append(
                self._make_finding(
                    "high",
                    "permission",
                    "应用声明高风险 Android 权限",
                    manifest_summary.get("package_name", package_path.name),
                    ", ".join(permissions.get("high_risk", [])[:10]),
                    "建议按最小权限原则复核真实业务必要性，并在敏感权限调用处增加显式授权说明和审计。",
                    "OWASP MASVS-PLATFORM",
                )
            )
        if permissions.get("special"):
            findings.append(
                self._make_finding(
                    "medium",
                    "permission",
                    "应用声明特殊权限",
                    manifest_summary.get("package_name", package_path.name),
                    ", ".join(permissions.get("special", [])[:10]),
                    "建议重点复核悬浮窗、安装其他应用、无障碍、全量包查询等高敏能力的授权边界。",
                    "OWASP MASVS-PLATFORM",
                )
            )
        if exported_components:
            public_components = [
                item for item in exported_components if str(item.get("Permission", "")).strip() in {"", "无"} and item.get("Exported") == "true"
            ]
            if public_components:
                findings.append(
                    self._make_finding(
                        "high",
                        "component",
                        "存在未加权限保护的导出组件",
                        manifest_summary.get("package_name", package_path.name),
                        "；".join(f"{item.get('Type')} {item.get('Name')}" for item in public_components[:8]),
                        "建议逐个确认导出组件是否真的需要对外暴露，并补齐 calling permission / signature permission / 运行时校验。",
                        "OWASP MASVS-PLATFORM",
                    )
                )
        if any(item.get("Value", "").startswith("http://") for item in external_urls):
            findings.append(
                self._make_finding(
                    "medium",
                    "network",
                    "应用包内发现明文 HTTP 外联地址",
                    manifest_summary.get("package_name", package_path.name),
                    "；".join(
                        item.get("Value", "")
                        for item in external_urls
                        if item.get("Value", "").startswith("http://")
                    )[:260],
                    "建议优先切换为 HTTPS，并结合证书校验、域名固定和 Network Security Config 复核传输安全。",
                    "OWASP MASVS-NETWORK",
                )
            )
        if any(any(hint in item.get("Value", "").lower() for hint in self.DEBUG_HOST_HINTS) for item in external_urls):
            findings.append(
                self._make_finding(
                    "low",
                    "network",
                    "应用包内存在测试/内网环境地址线索",
                    manifest_summary.get("package_name", package_path.name),
                    "；".join(item.get("Value", "") for item in external_urls[:12]),
                    "建议确认是否误带入测试、预发或内网地址，并避免生产包保留调试环境切换入口。",
                    "OWASP MASVS-RESILIENCE",
                )
            )
        if secret_hits:
            findings.append(
                self._make_finding(
                    "high" if any(item.get("Type") == "Private Key" for item in secret_hits) else "medium",
                    "secret",
                    "应用包内发现疑似密钥/令牌",
                    manifest_summary.get("package_name", package_path.name),
                    "；".join(f"{item.get('Type')}@{item.get('Source')}" for item in secret_hits[:8]),
                    "建议确认这些值是否为真实生产密钥、调试凭证或固定 Token，并尽快改为服务端下发或运行时交换。",
                    "OWASP MASVS-STORAGE",
                )
            )
        if keyword_hits:
            findings.append(
                self._make_finding(
                    "info",
                    "keyword",
                    "命中自定义关键字清单",
                    manifest_summary.get("package_name", package_path.name),
                    "；".join(f"{item.get('Keyword')}@{item.get('Source')}" for item in keyword_hits[:10]),
                    "可参考命中结果继续做定向代码审计或人工逆向复核。",
                    "Checklist / Custom Review",
                )
            )

        deduped_external_urls = self._dedupe_dict_rows(external_urls, ("Source", "Value"))
        deduped_ip_hits = self._dedupe_dict_rows(ip_hits, ("Source", "Value"))
        deduped_secret_hits = self._dedupe_dict_rows(secret_hits, ("Type", "Source", "Evidence"))
        deduped_keyword_hits = self._dedupe_dict_rows(keyword_hits, ("Keyword", "Source", "Evidence"))
        overview = {
            "file_name": package_path.name,
            "package_type": "apk",
            "file_size": len(file_bytes),
            "file_count": len(names),
            "identifier": manifest_summary.get("package_name", ""),
            "version_name": manifest_summary.get("version_name", ""),
            "version_code": manifest_summary.get("version_code", ""),
            "min_sdk": manifest_summary.get("min_sdk", ""),
            "target_sdk": manifest_summary.get("target_sdk", ""),
            "permissions_count": len(permissions.get("all", [])),
            "exported_component_count": len(exported_components),
            "url_count": len(deduped_external_urls),
            "sdk_count": len(sdk_inventory),
            "native_library_count": len(native_libraries),
        }

        result = {
            "generated_at": self._now(),
            "scan_type": "mobile",
            "platform": "android",
            "overview": overview,
            "manifest": manifest_summary,
            "permissions": permissions,
            "exported_components": exported_components,
            "deeplinks": deeplinks,
            "external_urls": deduped_external_urls,
            "ip_hits": deduped_ip_hits,
            "secret_hits": deduped_secret_hits,
            "keyword_hits": deduped_keyword_hits,
            "sdk_inventory": [{"Name": item} for item in sorted(sdk_inventory)],
            "certificate": certificate,
            "native_libraries": sorted(set(native_libraries)),
            "entries_summary": entries_summary,
            "findings": self._dedupe_findings(findings),
        }
        return result

    def _scan_ipa_package(
        self,
        package_path: Path,
        file_bytes: bytes,
        custom_keywords: Sequence[str],
    ) -> Dict[str, Any]:
        findings: List[Dict[str, Any]] = []
        usage_descriptions: List[str] = []
        external_urls: List[Dict[str, Any]] = []
        ip_hits: List[Dict[str, Any]] = []
        secret_hits: List[Dict[str, Any]] = []
        keyword_hits: List[Dict[str, Any]] = []
        sdk_inventory: Set[str] = set()
        url_schemes: List[str] = []
        associated_domains: List[str] = []
        entitlements: Dict[str, Any] = {}
        otool_summary: Dict[str, Any] = {}
        info_plist_summary: Dict[str, Any] = {}

        with tempfile.TemporaryDirectory(prefix="ipa-sec-") as temp_dir:
            archive_path = Path(temp_dir) / package_path.name
            archive_path.write_bytes(file_bytes)
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as archive:
                app_root = self._locate_ipa_app_root(archive)
                if not app_root:
                    raise ValueError("IPA 包中未找到 Payload/*.app 目录。")
                info_name = f"{app_root}/Info.plist"
                plist_data = archive.read(info_name)
                plist = plistlib.loads(plist_data)
                info_plist_summary = self._summarize_info_plist(plist)
                usage_descriptions = info_plist_summary.get("usage_descriptions", [])
                url_schemes = info_plist_summary.get("url_schemes", [])
                findings.extend(self._ipa_plist_findings(info_plist_summary))

                executable_name = str(plist.get("CFBundleExecutable") or "").strip()
                executable_bytes = b""
                executable_path: Optional[Path] = None
                if executable_name:
                    executable_member = f"{app_root}/{executable_name}"
                    if executable_member in archive.namelist():
                        executable_bytes = archive.read(executable_member)
                        executable_path = Path(temp_dir) / executable_name
                        executable_path.write_bytes(executable_bytes)

                for name in archive.namelist():
                    scan_level = self._zip_entry_scan_level(name)
                    if scan_level == "skip" and not name.endswith(".mobileprovision"):
                        continue
                    info = archive.getinfo(name)
                    if info.file_size > 20 * 1024 * 1024:
                        continue
                    data = archive.read(name)
                    if name.endswith(".mobileprovision"):
                        entitlements.update(self._parse_mobileprovision_entitlements(data))
                        continue
                    text_items = self._extract_text_items(data, binary_mode=scan_level == "binary")
                    signal = self._harvest_text_indicators(name, text_items, custom_keywords)
                    external_urls.extend(signal["urls"])
                    ip_hits.extend(signal["ips"])
                    secret_hits.extend(signal["secrets"])
                    keyword_hits.extend(signal["keywords"])
                    sdk_inventory.update(signal["sdks"])

                if executable_path is not None:
                    entitlements.update(self._load_codesign_entitlements(executable_path))
                    otool_summary = self._inspect_macho(executable_path)
                    sdk_inventory.update(self._detect_sdks_from_blob(json.dumps(otool_summary, ensure_ascii=False)))

        associated_domains = self._normalize_list(entitlements.get("com.apple.developer.associated-domains"))
        if entitlements.get("get-task-allow") is True:
            findings.append(
                self._make_finding(
                    "high",
                    "entitlement",
                    "签名 Entitlement 启用了 get-task-allow",
                    info_plist_summary.get("bundle_identifier", package_path.name),
                    "get-task-allow=true",
                    "这通常意味着调试签名或可被调试构建，建议确认未将调试构建投放到正式环境。",
                    "OWASP MASVS-RESILIENCE",
                )
            )
        if associated_domains:
            findings.append(
                self._make_finding(
                    "info",
                    "entitlement",
                    "应用声明了 Associated Domains",
                    info_plist_summary.get("bundle_identifier", package_path.name),
                    ", ".join(associated_domains[:10]),
                    "建议进一步复核通用链接、Web 凭证共享和域名所有权配置。",
                    "OWASP MASVS-PLATFORM",
                )
            )
        if info_plist_summary.get("ui_file_sharing_enabled"):
            findings.append(
                self._make_finding(
                    "medium",
                    "storage",
                    "应用启用了文件共享",
                    info_plist_summary.get("bundle_identifier", package_path.name),
                    "UIFileSharingEnabled=true",
                    "建议确认应用沙盒文件是否适合通过 Finder/iTunes/Files 暴露，并检查敏感缓存是否做额外保护。",
                    "OWASP MASVS-STORAGE",
                )
            )
        if any(item.get("Value", "").startswith("http://") for item in external_urls):
            findings.append(
                self._make_finding(
                    "medium",
                    "network",
                    "IPA 中发现明文 HTTP 外联地址",
                    info_plist_summary.get("bundle_identifier", package_path.name),
                    "；".join(
                        item.get("Value", "")
                        for item in external_urls
                        if item.get("Value", "").startswith("http://")
                    )[:260],
                    "建议优先切换为 HTTPS，并结合 ATS 和证书校验策略复核传输安全。",
                    "OWASP MASVS-NETWORK",
                )
            )
        if secret_hits:
            findings.append(
                self._make_finding(
                    "high" if any(item.get("Type") == "Private Key" for item in secret_hits) else "medium",
                    "secret",
                    "IPA 中发现疑似密钥/令牌",
                    info_plist_summary.get("bundle_identifier", package_path.name),
                    "；".join(f"{item.get('Type')}@{item.get('Source')}" for item in secret_hits[:8]),
                    "建议确认这些值是否为真实密钥、调试凭证或固定 Token，并避免在包内固化敏感凭据。",
                    "OWASP MASVS-STORAGE",
                )
            )
        if keyword_hits:
            findings.append(
                self._make_finding(
                    "info",
                    "keyword",
                    "命中自定义关键字清单",
                    info_plist_summary.get("bundle_identifier", package_path.name),
                    "；".join(f"{item.get('Keyword')}@{item.get('Source')}" for item in keyword_hits[:10]),
                    "可按命中线索继续做定向逆向分析或人工复核。",
                    "Checklist / Custom Review",
                )
            )

        deduped_external_urls = self._dedupe_dict_rows(external_urls, ("Source", "Value"))
        deduped_ip_hits = self._dedupe_dict_rows(ip_hits, ("Source", "Value"))
        deduped_secret_hits = self._dedupe_dict_rows(secret_hits, ("Type", "Source", "Evidence"))
        deduped_keyword_hits = self._dedupe_dict_rows(keyword_hits, ("Keyword", "Source", "Evidence"))
        overview = {
            "file_name": package_path.name,
            "package_type": "ipa",
            "file_size": len(file_bytes),
            "identifier": info_plist_summary.get("bundle_identifier", ""),
            "version_name": info_plist_summary.get("version_name", ""),
            "version_code": info_plist_summary.get("build_version", ""),
            "min_sdk": info_plist_summary.get("minimum_os_version", ""),
            "permissions_count": len(usage_descriptions),
            "url_count": len(deduped_external_urls),
            "sdk_count": len(sdk_inventory),
            "url_scheme_count": len(url_schemes),
        }

        result = {
            "generated_at": self._now(),
            "scan_type": "mobile",
            "platform": "ios",
            "overview": overview,
            "info_plist": info_plist_summary,
            "permissions": {
                "usage_descriptions": usage_descriptions,
            },
            "url_schemes": url_schemes,
            "associated_domains": associated_domains,
            "entitlements": entitlements,
            "macho_summary": otool_summary,
            "external_urls": deduped_external_urls,
            "ip_hits": deduped_ip_hits,
            "secret_hits": deduped_secret_hits,
            "keyword_hits": deduped_keyword_hits,
            "sdk_inventory": [{"Name": item} for item in sorted(sdk_inventory)],
            "findings": self._dedupe_findings(findings),
        }
        return result

    def _parse_apk_manifest(self, manifest_data: bytes) -> Dict[str, Any]:
        events = self._parse_axml_events(manifest_data)
        manifest_attrs: Dict[str, Any] = {}
        application_attrs: Dict[str, Any] = {}
        permissions = {"all": [], "high_risk": [], "medium_risk": [], "special": []}
        exported_components: List[Dict[str, Any]] = []
        deeplinks: List[Dict[str, Any]] = []
        current_component: Optional[Dict[str, Any]] = None

        for event_type, tag_name, attrs in events:
            if event_type == "start":
                if tag_name == "manifest":
                    manifest_attrs = dict(attrs)
                elif tag_name == "uses-sdk":
                    manifest_attrs["minSdkVersion"] = attrs.get("minSdkVersion")
                    manifest_attrs["targetSdkVersion"] = attrs.get("targetSdkVersion")
                    manifest_attrs["maxSdkVersion"] = attrs.get("maxSdkVersion")
                elif tag_name in {"uses-permission", "uses-permission-sdk-23", "permission"}:
                    permission_name = str(attrs.get("name") or "").strip()
                    if permission_name and permission_name not in permissions["all"]:
                        permissions["all"].append(permission_name)
                elif tag_name == "application":
                    application_attrs = dict(attrs)
                elif tag_name in self.APK_COMPONENT_TAGS:
                    current_component = {
                        "Type": tag_name,
                        "Name": attrs.get("name", ""),
                        "Exported": str(attrs.get("exported", "")).lower() if attrs.get("exported") is not None else "",
                        "Permission": attrs.get("permission", "") or "无",
                        "Enabled": attrs.get("enabled", "true"),
                        "Intent Filters": 0,
                        "Authorities": attrs.get("authorities", ""),
                        "Deep Links": [],
                    }
                elif tag_name == "intent-filter" and current_component is not None:
                    current_component["Intent Filters"] += 1
                elif tag_name == "data" and current_component is not None:
                    link_parts = []
                    for key in ["scheme", "host", "port", "path", "pathPrefix", "pathPattern"]:
                        value = attrs.get(key)
                        if value:
                            link_parts.append(f"{key}={value}")
                    if link_parts:
                        deeplink = {
                            "Component": current_component.get("Name", ""),
                            "Component Type": current_component.get("Type", ""),
                            "Rule": ", ".join(link_parts),
                        }
                        current_component["Deep Links"].append(deeplink["Rule"])
                        deeplinks.append(deeplink)
            elif event_type == "end" and tag_name in self.APK_COMPONENT_TAGS and current_component is not None:
                exported = current_component.get("Exported", "")
                if not exported:
                    exported = "true" if int(current_component.get("Intent Filters", 0) or 0) > 0 else "unknown"
                current_component["Exported"] = exported
                exported_components.append(dict(current_component))
                current_component = None

        for permission_name in permissions["all"]:
            if permission_name in self.APK_HIGH_RISK_PERMISSIONS:
                permissions["high_risk"].append(permission_name)
            elif permission_name in self.APK_MEDIUM_RISK_PERMISSIONS:
                permissions["medium_risk"].append(permission_name)
            elif permission_name in self.APK_SPECIAL_PERMISSIONS:
                permissions["special"].append(permission_name)

        permissions["all"].sort()
        permissions["high_risk"].sort()
        permissions["medium_risk"].sort()
        permissions["special"].sort()

        return {
            "package_name": str(manifest_attrs.get("package") or ""),
            "version_name": str(manifest_attrs.get("versionName") or ""),
            "version_code": str(manifest_attrs.get("versionCode") or ""),
            "min_sdk": str(manifest_attrs.get("minSdkVersion") or ""),
            "target_sdk": str(manifest_attrs.get("targetSdkVersion") or ""),
            "max_sdk": str(manifest_attrs.get("maxSdkVersion") or ""),
            "application": application_attrs,
            "permissions": permissions,
            "exported_components": exported_components,
            "deeplinks": deeplinks,
        }

    def _apk_manifest_findings(self, manifest_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        package_name = manifest_summary.get("package_name", "") or "AndroidManifest"
        application = manifest_summary.get("application") or {}

        if str(application.get("debuggable", "")).lower() == "true":
            findings.append(
                self._make_finding(
                    "high",
                    "config",
                    "Manifest 启用了 debuggable",
                    package_name,
                    "android:debuggable=true",
                    "建议确认正式发布包未启用调试模式，避免被附加调试或运行时注入。",
                    "OWASP MASVS-RESILIENCE",
                )
            )
        if str(application.get("allowBackup", "")).lower() == "true":
            findings.append(
                self._make_finding(
                    "medium",
                    "config",
                    "Manifest 启用了 allowBackup",
                    package_name,
                    "android:allowBackup=true",
                    "如业务不需要备份，建议关闭 allowBackup，并确认敏感数据不通过 ADB/云备份泄露。",
                    "OWASP MASVS-STORAGE",
                )
            )
        if str(application.get("usesCleartextTraffic", "")).lower() == "true":
            findings.append(
                self._make_finding(
                    "high",
                    "config",
                    "Manifest 允许明文流量",
                    package_name,
                    "android:usesCleartextTraffic=true",
                    "建议优先关闭明文流量，并结合 Network Security Config 细化仅对必要域名放通。",
                    "OWASP MASVS-NETWORK",
                )
            )
        if application.get("networkSecurityConfig"):
            findings.append(
                self._make_finding(
                    "info",
                    "config",
                    "Manifest 引用了自定义 Network Security Config",
                    package_name,
                    f"android:networkSecurityConfig={application.get('networkSecurityConfig')}",
                    "建议进一步复核是否存在 debug-overrides、明文域名放通或证书校验放宽配置。",
                    "OWASP MASVS-NETWORK",
                )
            )
        return findings

    def _summarize_info_plist(self, plist: Dict[str, Any]) -> Dict[str, Any]:
        usage_descriptions = []
        for key, value in plist.items():
            if "UsageDescription" in str(key):
                if isinstance(value, dict):
                    for inner_key, inner_value in value.items():
                        usage_descriptions.append(f"{inner_key}: {inner_value}")
                else:
                    usage_descriptions.append(f"{key}: {value}")

        url_schemes: List[str] = []
        for item in plist.get("CFBundleURLTypes", []) or []:
            if not isinstance(item, dict):
                continue
            for scheme in item.get("CFBundleURLSchemes", []) or []:
                scheme_text = str(scheme).strip()
                if scheme_text:
                    url_schemes.append(scheme_text)

        ats = plist.get("NSAppTransportSecurity") if isinstance(plist.get("NSAppTransportSecurity"), dict) else {}
        return {
            "app_name": str(plist.get("CFBundleDisplayName") or plist.get("CFBundleName") or ""),
            "bundle_identifier": str(plist.get("CFBundleIdentifier") or ""),
            "version_name": str(plist.get("CFBundleShortVersionString") or ""),
            "build_version": str(plist.get("CFBundleVersion") or ""),
            "minimum_os_version": str(plist.get("MinimumOSVersion") or ""),
            "sdk_name": str(plist.get("DTSDKName") or ""),
            "usage_descriptions": usage_descriptions,
            "url_schemes": sorted(set(url_schemes)),
            "ats": ats,
            "ats_allows_arbitrary_loads": bool(ats.get("NSAllowsArbitraryLoads")),
            "ui_file_sharing_enabled": bool(plist.get("UIFileSharingEnabled")),
            "supports_opening_documents_in_place": bool(plist.get("LSSupportsOpeningDocumentsInPlace")),
            "application_queries_schemes": sorted(set(str(item).strip() for item in (plist.get("LSApplicationQueriesSchemes") or []) if str(item).strip())),
        }

    def _ipa_plist_findings(self, info: Dict[str, Any]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        identifier = info.get("bundle_identifier", "") or "Info.plist"
        if info.get("ats_allows_arbitrary_loads"):
            findings.append(
                self._make_finding(
                    "high",
                    "config",
                    "ATS 允许任意明文或弱校验流量",
                    identifier,
                    "NSAppTransportSecurity.NSAllowsArbitraryLoads=true",
                    "建议按域名粒度配置 ATS 例外，避免全局放开任意加载。",
                    "OWASP MASVS-NETWORK",
                )
            )
        if info.get("application_queries_schemes"):
            findings.append(
                self._make_finding(
                    "info",
                    "privacy",
                    "Info.plist 声明了 LSApplicationQueriesSchemes",
                    identifier,
                    ", ".join(info.get("application_queries_schemes", [])[:12]),
                    "建议确认该查询列表是否最小化，避免泄露过多设备安装应用探测能力。",
                    "OWASP MASVS-PRIVACY",
                )
            )
        if info.get("supports_opening_documents_in_place"):
            findings.append(
                self._make_finding(
                    "low",
                    "storage",
                    "应用支持原位打开文档",
                    identifier,
                    "LSSupportsOpeningDocumentsInPlace=true",
                    "建议复核共享文档访问边界，避免第三方 App 直接改写敏感文件。",
                    "OWASP MASVS-STORAGE",
                )
            )
        return findings

    def _inspect_apk_certificate(self, package_path: Path, archive: zipfile.ZipFile) -> Dict[str, Any]:
        cert_members = [name for name in archive.namelist() if name.upper().startswith("META-INF/") and name.upper().endswith((".RSA", ".DSA", ".EC"))]
        if not cert_members:
            return {}

        certificate: Dict[str, Any] = {"files": cert_members}
        try:
            with tempfile.TemporaryDirectory(prefix="apk-cert-") as temp_dir:
                cert_path = Path(temp_dir) / Path(cert_members[0]).name
                cert_path.write_bytes(archive.read(cert_members[0]))
                proc = subprocess.run(
                    ["openssl", "pkcs7", "-inform", "DER", "-in", str(cert_path), "-print_certs", "-text", "-noout"],
                    capture_output=True,
                    text=True,
                    timeout=12,
                    check=False,
                )
                output = (proc.stdout or "") + "\n" + (proc.stderr or "")
                subject = self._regex_pick(output, r"Subject:\s*(.+)")
                issuer = self._regex_pick(output, r"Issuer:\s*(.+)")
                serial = self._regex_pick(output, r"Serial Number:\s*([0-9A-Fa-f:]+)")
                certificate.update(
                    {
                        "subject": subject,
                        "issuer": issuer,
                        "serial_number": serial,
                        "sha256": self._sha256_file_bytes(cert_path.read_bytes()),
                    }
                )
        except Exception:
            certificate["sha256"] = self._sha256_file_bytes(archive.read(cert_members[0]))

        if "debug" in str(certificate.get("subject", "")).lower():
            certificate["debug_certificate"] = True
        return certificate

    def _locate_ipa_app_root(self, archive: zipfile.ZipFile) -> str:
        candidates = []
        for name in archive.namelist():
            if name.startswith("Payload/") and name.endswith(".app/Info.plist"):
                candidates.append(str(PurePosixPath(name).parent))
        return candidates[0] if candidates else ""

    def _parse_mobileprovision_entitlements(self, data: bytes) -> Dict[str, Any]:
        try:
            start = data.find(b"<?xml")
            end = data.rfind(b"</plist>")
            if start >= 0 and end > start:
                plist_data = data[start:end + len(b"</plist>")]
                plist = plistlib.loads(plist_data)
                entitlements = plist.get("Entitlements")
                return entitlements if isinstance(entitlements, dict) else {}
        except Exception:
            return {}
        return {}

    def _load_codesign_entitlements(self, executable_path: Path) -> Dict[str, Any]:
        try:
            proc = subprocess.run(
                ["codesign", "-d", "--entitlements", ":-", str(executable_path)],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            text = (proc.stdout or "") + (proc.stderr or "")
            start = text.find("<?xml")
            end = text.rfind("</plist>")
            if start >= 0 and end > start:
                return plistlib.loads(text[start:end + len("</plist>")].encode("utf-8"))
        except Exception:
            return {}
        return {}

    def _inspect_macho(self, executable_path: Path) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        try:
            proc = subprocess.run(
                ["otool", "-l", str(executable_path)],
                capture_output=True,
                text=True,
                timeout=12,
                check=False,
            )
            output = proc.stdout or ""
            summary["rpaths"] = re.findall(r"path\s+([^\s]+)\s+\(offset", output)
            crypt_id = self._regex_pick(output, r"cryptid\s+(\d+)")
            if crypt_id:
                summary["cryptid"] = crypt_id
            if "LC_ENCRYPTION_INFO" in output or "LC_ENCRYPTION_INFO_64" in output:
                summary["has_encryption_info"] = True
        except Exception:
            return summary
        return summary

    def _parse_axml_events(self, data: bytes) -> List[Tuple[str, str, Dict[str, Any]]]:
        root_type = self._u16(data, 0)
        if root_type != 0x0003:
            raise ValueError("不是有效的 Android Binary XML。")

        offset = self._u16(data, 2)
        strings: List[str] = []
        events: List[Tuple[str, str, Dict[str, Any]]] = []

        while offset + 8 <= len(data):
            chunk_type = self._u16(data, offset)
            header_size = self._u16(data, offset + 2)
            chunk_size = self._u32(data, offset + 4)
            if chunk_size <= 0:
                break

            if chunk_type == 0x0001:
                strings = self._parse_axml_string_pool(data, offset)
            elif chunk_type == 0x0102:
                tag_name = self._get_axml_string(strings, self._u32(data, offset + 20)) or ""
                attr_start = self._u16(data, offset + 24)
                attr_size = self._u16(data, offset + 26)
                attr_count = self._u16(data, offset + 28)
                attrs: Dict[str, Any] = {}
                attr_offset = offset + 16 + attr_start
                for index in range(attr_count):
                    item_offset = attr_offset + index * attr_size
                    attr_name = self._get_axml_string(strings, self._u32(data, item_offset + 4)) or f"attr_{index}"
                    raw_value = self._get_axml_string(strings, self._u32(data, item_offset + 8))
                    data_type = data[item_offset + 15]
                    data_value = self._u32(data, item_offset + 16)
                    if raw_value is not None:
                        value = raw_value
                    elif data_type == 0x03:
                        value = self._get_axml_string(strings, data_value)
                    elif data_type == 0x12:
                        value = "true" if data_value != 0 else "false"
                    elif data_type == 0x10:
                        value = str(data_value)
                    elif data_type == 0x01:
                        value = f"@0x{data_value:08x}"
                    else:
                        value = f"type=0x{data_type:02x} data=0x{data_value:x}"
                    attrs[attr_name] = value
                events.append(("start", tag_name, attrs))
            elif chunk_type == 0x0103:
                tag_name = self._get_axml_string(strings, self._u32(data, offset + 20)) or ""
                events.append(("end", tag_name, {}))

            offset += chunk_size

        return events

    def _parse_axml_string_pool(self, data: bytes, offset: int) -> List[str]:
        string_count = self._u32(data, offset + 8)
        flags = self._u32(data, offset + 16)
        strings_start = self._u32(data, offset + 20)
        is_utf8 = bool(flags & 0x00000100)
        offsets = [self._u32(data, offset + 28 + index * 4) for index in range(string_count)]
        base = offset + strings_start
        strings: List[str] = []

        for relative_offset in offsets:
            pos = base + relative_offset
            try:
                if is_utf8:
                    _, consumed = self._decode_length8(data, pos)
                    pos += consumed
                    byte_length, consumed = self._decode_length8(data, pos)
                    pos += consumed
                    strings.append(data[pos:pos + byte_length].decode("utf-8", "replace"))
                else:
                    char_length, consumed = self._decode_length16(data, pos)
                    pos += consumed
                    strings.append(data[pos:pos + char_length * 2].decode("utf-16le", "replace"))
            except Exception:
                strings.append("")
        return strings

    def _harvest_text_indicators(
        self,
        source: str,
        text_items: Sequence[str],
        custom_keywords: Sequence[str],
    ) -> Dict[str, Any]:
        urls: List[Dict[str, Any]] = []
        ips: List[Dict[str, Any]] = []
        secrets: List[Dict[str, Any]] = []
        keywords: List[Dict[str, Any]] = []
        sdks = set()
        notes = []

        for item in text_items[:20000]:
            cleaned = str(item or "").strip()
            if len(cleaned) < 4:
                continue
            for match in self.URL_REGEX.findall(cleaned):
                url = match.rstrip(").,;\"'")
                if any(url.startswith(prefix) for prefix in self.IGNORED_URL_PREFIXES):
                    continue
                urls.append({"Source": source, "Value": url})
            for match in self.IPV4_REGEX.findall(cleaned):
                try:
                    ip_obj = ipaddress.ip_address(match)
                except ValueError:
                    continue
                ips.append(
                    {
                        "Source": source,
                        "Value": str(ip_obj),
                        "Type": "private" if ip_obj.is_private else "public",
                    }
                )
            for secret_type, pattern in self.SECRET_PATTERNS:
                hit = pattern.search(cleaned)
                if hit:
                    evidence = hit.group(0)
                    secrets.append(
                        {
                            "Type": secret_type,
                            "Source": source,
                            "Evidence": evidence[:180],
                        }
                    )
            lower_cleaned = cleaned.lower()
            for keyword in custom_keywords:
                if keyword.lower() in lower_cleaned:
                    keywords.append(
                        {
                            "Keyword": keyword,
                            "Source": source,
                            "Evidence": cleaned[:180],
                        }
                    )

        blob = " ".join(text_items[:4000]).lower()
        blob += " " + source.lower()
        sdks.update(self._detect_sdks_from_blob(blob))
        if len(text_items) >= 20000:
            notes.append("string items truncated")

        return {
            "urls": self._dedupe_dict_rows(urls, ("Source", "Value")),
            "ips": self._dedupe_dict_rows(ips, ("Source", "Value")),
            "secrets": self._dedupe_dict_rows(secrets, ("Type", "Source", "Evidence")),
            "keywords": self._dedupe_dict_rows(keywords, ("Keyword", "Source", "Evidence")),
            "sdks": sdks,
            "note": ", ".join(notes),
        }

    def _extract_text_items(self, data: bytes, binary_mode: bool) -> List[str]:
        if not data:
            return []
        if not binary_mode:
            try:
                return data.decode("utf-8", "replace").splitlines()
            except Exception:
                return []

        ascii_items = [item.decode("utf-8", "ignore") for item in re.findall(rb"[ -~]{4,}", data)]
        utf16_items = []
        for item in re.findall(rb"((?:[ -~]\\x00){4,})", data):
            try:
                utf16_items.append(item.decode("utf-16le", "ignore"))
            except Exception:
                continue
        combined = []
        seen: Set[str] = set()
        for item in ascii_items + utf16_items:
            cleaned = str(item).strip()
            if not cleaned or cleaned in seen:
                continue
            seen.add(cleaned)
            combined.append(cleaned)
        return combined

    def _zip_entry_scan_level(self, name: str) -> str:
        lowered = name.lower()
        if lowered.endswith((".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp3", ".mp4", ".mov", ".ttf", ".woff", ".woff2", ".nib")):
            return "skip"
        if lowered.endswith((".dex", ".so")):
            return "binary"
        if ".app/" in lowered and "." not in PurePosixPath(lowered).name:
            return "binary"
        if lowered.endswith((".plist", ".xml", ".json", ".txt", ".html", ".js", ".properties", ".cfg", ".conf")):
            return "text"
        if "/assets/" in lowered or lowered.startswith("assets/"):
            return "binary"
        return "skip"

    def _detect_sdks_from_blob(self, blob: str) -> Set[str]:
        lower_blob = str(blob or "").lower()
        hits = set()
        for label, keywords in self.SDK_HINTS.items():
            if any(keyword.lower() in lower_blob for keyword in keywords):
                hits.add(label)
        return hits

    def _analyze_web_response(self, response: requests.Response, url: str) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        parsed = urlparse(url)
        headers = {str(key): str(value) for key, value in dict(response.headers or {}).items()}
        lower_headers = {str(key).lower(): str(value) for key, value in headers.items()}
        content_type = lower_headers.get("content-type", "").lower()
        set_cookie = headers.get("Set-Cookie", "") or headers.get("set-cookie", "")
        body_preview = (response.text or "")[:1200]

        if parsed.scheme == "http":
            findings.append(
                self._make_finding(
                    "high",
                    "transport",
                    "站点使用明文 HTTP",
                    url,
                    url,
                    "建议统一切换为 HTTPS，并确认 HSTS、证书链和跳转策略已正确配置。",
                    "OWASP ASVS V9 / WSTG-CRYP",
                )
            )
        elif "strict-transport-security" not in lower_headers:
            findings.append(
                self._make_finding(
                    "medium",
                    "headers",
                    "HTTPS 页面缺少 HSTS",
                    url,
                    f"{response.status_code} {url}",
                    "建议返回 Strict-Transport-Security，降低首次访问劫持和降级攻击风险。",
                    "OWASP ASVS V9 / WSTG-CONF",
                )
            )

        if "html" in content_type and "content-security-policy" not in lower_headers:
            findings.append(
                self._make_finding(
                    "medium",
                    "headers",
                    "HTML 页面缺少 CSP",
                    url,
                    f"{response.status_code} {content_type}",
                    "建议为 HTML 响应补充 Content-Security-Policy，并结合 nonce/hash 控制脚本来源。",
                    "OWASP ASVS V14 / WSTG-CLNT",
                )
            )
        if "x-frame-options" not in lower_headers and "frame-ancestors" not in lower_headers.get("content-security-policy", "").lower():
            findings.append(
                self._make_finding(
                    "low",
                    "headers",
                    "缺少点击劫持防护线索",
                    url,
                    "未发现 X-Frame-Options / frame-ancestors",
                    "建议通过 CSP frame-ancestors 或 X-Frame-Options 限制页面被外部站点嵌入。",
                    "OWASP ASVS V14 / WSTG-CLNT",
                )
            )
        if "x-content-type-options" not in lower_headers:
            findings.append(
                self._make_finding(
                    "low",
                    "headers",
                    "缺少 X-Content-Type-Options",
                    url,
                    "未发现 X-Content-Type-Options",
                    "建议返回 X-Content-Type-Options: nosniff，降低 MIME 嗅探风险。",
                    "OWASP ASVS V14 / WSTG-CONF",
                )
            )
        if "referrer-policy" not in lower_headers:
            findings.append(
                self._make_finding(
                    "low",
                    "headers",
                    "缺少 Referrer-Policy",
                    url,
                    "未发现 Referrer-Policy",
                    "建议根据业务选择 strict-origin-when-cross-origin 等 Referrer-Policy。",
                    "OWASP ASVS V14 / Privacy",
                )
            )
        if "server" in lower_headers:
            findings.append(
                self._make_finding(
                    "info",
                    "fingerprint",
                    "Server 头暴露服务指纹",
                    url,
                    headers.get("Server", ""),
                    "建议按内部规范隐藏或弱化 Server 指纹，减少被动信息暴露。",
                    "OWASP WSTG-INFO",
                )
            )
        if "x-powered-by" in lower_headers:
            findings.append(
                self._make_finding(
                    "info",
                    "fingerprint",
                    "X-Powered-By 暴露技术栈",
                    url,
                    headers.get("X-Powered-By", ""),
                    "建议移除 X-Powered-By 等框架指纹响应头。",
                    "OWASP WSTG-INFO",
                )
            )

        cors_origin = lower_headers.get("access-control-allow-origin", "")
        cors_credentials = lower_headers.get("access-control-allow-credentials", "").lower()
        if cors_origin == "*" and cors_credentials == "true":
            findings.append(
                self._make_finding(
                    "high",
                    "cors",
                    "CORS 允许任意来源且允许凭证",
                    url,
                    "Access-Control-Allow-Origin=* 且 Allow-Credentials=true",
                    "建议改成精确白名单并避免和凭证同时使用通配来源。",
                    "OWASP ASVS V14 / WSTG-CLNT",
                )
            )
        elif cors_origin == "*":
            findings.append(
                self._make_finding(
                    "medium",
                    "cors",
                    "CORS 允许任意来源",
                    url,
                    "Access-Control-Allow-Origin=*",
                    "确认该页面/接口是否真的需要开放给任意来源。",
                    "OWASP ASVS V14 / WSTG-CLNT",
                )
            )

        if set_cookie:
            missing_flags = []
            lower_cookie = set_cookie.lower()
            if "secure" not in lower_cookie:
                missing_flags.append("Secure")
            if "httponly" not in lower_cookie:
                missing_flags.append("HttpOnly")
            if "samesite" not in lower_cookie:
                missing_flags.append("SameSite")
            if missing_flags:
                findings.append(
                    self._make_finding(
                        "medium",
                        "cookie",
                        "Cookie 安全属性不完整",
                        url,
                        ", ".join(missing_flags),
                        "建议对会话或认证 Cookie 至少补齐 Secure、HttpOnly 和 SameSite 属性。",
                        "OWASP ASVS V3 / Session",
                    )
                )

        preview_lower = body_preview.lower()
        leaks = [item for item in self.WEB_ERROR_MARKERS if item in preview_lower]
        if leaks:
            findings.append(
                self._make_finding(
                    "medium",
                    "error",
                    "响应体存在错误泄露/调试线索",
                    url,
                    ", ".join(leaks[:5]),
                    "建议统一错误处理，不向前端暴露堆栈、SQL 语句或调试上下文。",
                    "OWASP ASVS V10 / Error Handling",
                )
            )
        if "index of /" in preview_lower or "parent directory" in preview_lower:
            findings.append(
                self._make_finding(
                    "medium",
                    "exposure",
                    "疑似目录列表暴露",
                    url,
                    body_preview[:120],
                    "建议关闭目录浏览并避免将敏感文件直接放置在可访问目录。",
                    "OWASP WSTG-CONF",
                )
            )
        return findings

    def _analyze_html(self, body: str, title: str, url: str) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        lower_title = str(title or "").strip().lower()
        lower_body = (body or "").lower()
        if any(token in lower_title for token in ["swagger", "api docs", "api documentation"]):
            findings.append(
                self._make_finding(
                    "info",
                    "inventory",
                    "页面标题显示为 API 文档/调试入口",
                    url,
                    title,
                    "建议确认该页面是否应对外公开，并评估是否需要鉴权或环境隔离。",
                    "OWASP WSTG-INFO",
                )
            )
        if "graphql playground" in lower_body or "graphiql" in lower_body:
            findings.append(
                self._make_finding(
                    "low",
                    "inventory",
                    "页面包含 GraphQL 调试控制台线索",
                    url,
                    title or url,
                    "建议确认正式环境是否需要开放 GraphQL Playground/GraphiQL。",
                    "OWASP WSTG-INFO",
                )
            )
        return findings

    def _extract_forms(self, page_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        forms: List[Dict[str, Any]] = []
        for index, form in enumerate(soup.find_all("form"), start=1):
            action = str(form.get("action") or "").strip()
            method = str(form.get("method") or "GET").upper()
            inputs = form.find_all(["input", "textarea", "select"])
            input_names = [str(item.get("name") or item.get("id") or item.get("type") or "").strip() for item in inputs]
            input_types = [str(item.get("type") or "").strip().lower() for item in inputs]
            forms.append(
                {
                    "Page": page_url,
                    "Form": index,
                    "Method": method,
                    "Action": urljoin(page_url, action) if action else page_url,
                    "Field Count": len(inputs),
                    "Has Password": "password" in input_types,
                    "Has File Upload": "file" in input_types,
                    "Has CSRF Hint": any("csrf" in item.lower() or "token" in item.lower() for item in input_names),
                    "Fields": ", ".join(item for item in input_names if item)[:260],
                }
            )
        return forms

    def _analyze_forms(self, forms: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        findings: List[Dict[str, Any]] = []
        for item in forms:
            action = str(item.get("Action", "")).strip()
            target = f"{item.get('Page', '')} -> {action}"
            if item.get("Has Password") and action.startswith("http://"):
                findings.append(
                    self._make_finding(
                        "high",
                        "form",
                        "密码表单提交到明文 HTTP",
                        target,
                        action,
                        "建议确保登录、注册、找回密码等敏感表单仅通过 HTTPS 提交。",
                        "OWASP ASVS V9 / WSTG-ATHN",
                    )
                )
            if item.get("Method") == "POST" and not item.get("Has CSRF Hint"):
                findings.append(
                    self._make_finding(
                        "low",
                        "form",
                        "POST 表单未发现显式 CSRF 令牌线索",
                        target,
                        str(item.get("Fields", ""))[:180],
                        "建议结合服务端框架确认是否存在 CSRF token、SameSite Cookie 或同源校验机制。",
                        "OWASP ASVS V4 / WSTG-SESS",
                    )
                )
            if item.get("Has File Upload"):
                findings.append(
                    self._make_finding(
                        "info",
                        "form",
                        "页面存在文件上传入口",
                        target,
                        str(item.get("Fields", ""))[:180],
                        "建议继续复核上传类型、大小、MIME、病毒扫描和存储隔离策略。",
                        "OWASP ASVS V12 / WSTG-BUSL",
                    )
                )
        return findings

    def _extract_assets(self, page_url: str, soup: BeautifulSoup) -> List[Dict[str, Any]]:
        assets: List[Dict[str, Any]] = []
        for script in soup.find_all("script"):
            src = str(script.get("src") or "").strip()
            if src:
                assets.append({"Page": page_url, "Type": "script", "URL": urljoin(page_url, src)})
        for link in soup.find_all("link"):
            href = str(link.get("href") or "").strip()
            rel = ",".join(str(item).strip() for item in (link.get("rel") or [])).lower()
            if href:
                assets.append({"Page": page_url, "Type": rel or "link", "URL": urljoin(page_url, href)})
        return assets

    def _extract_internal_links(self, page_url: str, soup: BeautifulSoup, same_origin: str) -> List[str]:
        links = []
        seen = set()
        for anchor in soup.find_all("a"):
            href = str(anchor.get("href") or "").strip()
            if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue
            absolute = self._canonicalize_url(urljoin(page_url, href))
            if self._origin(absolute) != same_origin:
                continue
            if absolute not in seen:
                seen.add(absolute)
                links.append(absolute)
        return links

    def _inspect_tls_certificate(self, url: str, timeout_seconds: float, verify_ssl: bool) -> Dict[str, Any]:
        parsed = urlparse(url)
        if parsed.scheme != "https" or not parsed.hostname:
            return {}

        host = parsed.hostname
        port = parsed.port or 443
        context = ssl.create_default_context()
        if not verify_ssl:
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

        try:
            with socket.create_connection((host, port), timeout=max(float(timeout_seconds), 1.0)) as sock:
                with context.wrap_socket(sock, server_hostname=host) as secure_sock:
                    cert = secure_sock.getpeercert()
                    if not cert:
                        return {}
                    subject = ", ".join("=".join(item) for group in cert.get("subject", []) for item in group)
                    issuer = ", ".join("=".join(item) for group in cert.get("issuer", []) for item in group)
                    return {
                        "subject": subject,
                        "issuer": issuer,
                        "serial_number": cert.get("serialNumber", ""),
                        "not_before": cert.get("notBefore", ""),
                        "not_after": cert.get("notAfter", ""),
                    }
        except Exception as exc:
            return {"error": str(exc)}

    def _extract_robots_paths(self, body: str) -> List[str]:
        paths = []
        for line in (body or "").splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            if key.strip().lower() == "disallow":
                path = value.strip()
                if path and path not in paths:
                    paths.append(path)
        return paths

    def _extract_html_title(self, body: str) -> str:
        match = re.search(r"<title[^>]*>(.*?)</title>", body or "", re.IGNORECASE | re.DOTALL)
        if not match:
            return ""
        return re.sub(r"\s+", " ", match.group(1)).strip()

    def _normalize_url(self, url: str) -> str:
        raw = str(url or "").strip()
        if not raw:
            raise ValueError("请输入需要扫描的站点 URL。")
        if "://" not in raw:
            raw = "https://" + raw
        parsed = urlparse(raw)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("请输入有效的 http/https 站点 URL。")
        return self._canonicalize_url(raw)

    def _canonicalize_url(self, url: str) -> str:
        cleaned, _ = urldefrag(url)
        parsed = urlparse(cleaned)
        path = parsed.path or "/"
        return urlunparse(
            (
                parsed.scheme.lower(),
                parsed.netloc.lower(),
                path,
                "",
                parsed.query,
                "",
            )
        )

    def _site_root(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}"

    def _origin(self, url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}".lower()

    def _make_finding(
        self,
        severity: str,
        category: str,
        title: str,
        target: str,
        evidence: str,
        recommendation: str,
        reference: str,
    ) -> Dict[str, Any]:
        return {
            "Severity": severity,
            "Category": category,
            "Title": title,
            "Target": target,
            "Evidence": evidence,
            "Recommendation": recommendation,
            "Reference": reference,
        }

    def _build_summary(self, findings: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
        summary = {"finding_count": len(findings), "high": 0, "medium": 0, "low": 0, "info": 0}
        for item in findings:
            severity = str(item.get("Severity", "info")).lower()
            if severity in summary:
                summary[severity] += 1
        return summary

    def _dedupe_findings(self, findings: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
        deduped: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        for item in findings:
            key = (
                str(item.get("Severity", "")),
                str(item.get("Category", "")),
                str(item.get("Title", "")),
                str(item.get("Target", "")),
                str(item.get("Evidence", "")),
            )
            deduped[key] = dict(item)
        rows = list(deduped.values())
        rows.sort(key=lambda item: (self._severity_rank(item.get("Severity", "info")), str(item.get("Target", ""))))
        return rows

    def _dedupe_dict_rows(self, rows: Sequence[Dict[str, Any]], keys: Sequence[str]) -> List[Dict[str, Any]]:
        deduped: Dict[Tuple[str, ...], Dict[str, Any]] = {}
        for row in rows:
            key = tuple(str(row.get(name, "")) for name in keys)
            deduped[key] = dict(row)
        return list(deduped.values())

    def _severity_rank(self, severity: Any) -> int:
        mapping = {"high": 0, "medium": 1, "low": 2, "info": 3}
        return mapping.get(str(severity).lower(), 4)

    def _normalize_keywords(self, custom_keywords: Optional[Sequence[str]]) -> List[str]:
        keywords: List[str] = []
        for item in custom_keywords or []:
            text = str(item or "").strip()
            if text and text not in keywords:
                keywords.append(text)
        return keywords

    def _normalize_list(self, value: Any) -> List[str]:
        if isinstance(value, (list, tuple, set)):
            return [str(item).strip() for item in value if str(item).strip()]
        if value is None:
            return []
        text = str(value).strip()
        return [text] if text else []

    def _regex_pick(self, text: str, pattern: str) -> str:
        match = re.search(pattern, text or "", re.IGNORECASE)
        return match.group(1).strip() if match else ""

    def _sha256_file_bytes(self, data: bytes) -> str:
        import hashlib

        return hashlib.sha256(data).hexdigest()

    def _u16(self, data: bytes, offset: int) -> int:
        return struct.unpack_from("<H", data, offset)[0]

    def _u32(self, data: bytes, offset: int) -> int:
        return struct.unpack_from("<I", data, offset)[0]

    def _decode_length8(self, data: bytes, offset: int) -> Tuple[int, int]:
        first = data[offset]
        if first & 0x80:
            return ((first & 0x7F) << 8) | data[offset + 1], 2
        return first, 1

    def _decode_length16(self, data: bytes, offset: int) -> Tuple[int, int]:
        first = self._u16(data, offset)
        if first & 0x8000:
            return ((first & 0x7FFF) << 16) | self._u16(data, offset + 2), 4
        return first, 2

    def _get_axml_string(self, strings: Sequence[str], index: int) -> Optional[str]:
        if index in {None, 0xFFFFFFFF}:
            return None
        if index < 0 or index >= len(strings):
            return None
        return strings[index]

    def _now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")
