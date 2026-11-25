import datetime
import hashlib
import ipaddress
import json
import re
import socket
import threading
import time
import urllib.parse
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests

from qa_toolkit.core.ip_lookup_registry import (
    get_asset_actions,
    get_conversion_types,
    get_country_names,
    get_geo_providers,
    get_ip_lookup_limits,
    get_public_ip_services,
    get_registrable_suffixes,
    get_scheme_allowlist,
    get_service_names,
)


class IPQueryTool:
    """IP/域名查询与 IPv4 格式转换工具。"""

    HOSTNAME_LABEL_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,63}$")
    DEFAULT_HEADERS = {
        "User-Agent": "Mozilla/5.0 QA-Toolkit/1.0",
        "Accept": "*/*",
    }
    PUBLIC_IP_SERVICES = (
        ("json", "https://api64.ipify.org?format=json"),
        ("text", "https://ident.me"),
        ("text", "https://checkip.amazonaws.com"),
        ("text", "https://ifconfig.me/ip"),
    )
    SUBDOMAIN_CRTSH_URL = "https://crt.sh/?q=%25.{domain}&output=json"
    SUBDOMAIN_HOSTSEARCH_URL = "https://api.hackertarget.com/hostsearch/?q={domain}"
    REVERSE_IP_LOOKUP_URL = "https://api.hackertarget.com/reverseiplookup/?q={ip}"
    ICP_LOOKUP_URL = "https://api.mmp.cc/api/icp?domain={domain}"
    MIIT_ICP_VERIFY_URL = "https://beian.miit.gov.cn/"
    COMMON_MULTI_LABEL_SUFFIXES = {
        "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn", "ac.cn",
        "com.hk", "com.tw", "com.mo", "com.sg", "co.jp", "co.kr",
        "co.uk", "org.uk", "ac.uk",
    }
    SOURCE_PRIORITY = ["ipapi", "ipinfo", "ipwhois"]
    SOURCE_LABELS = {
        "ipapi": "ipapi.co (HTTPS)",
        "ipinfo": "ipinfo.io (HTTPS)",
        "ipwhois": "ipwho.is (HTTPS)",
    }

    def __init__(self):
        self.data_source = "HTTPS多源IP地理接口"
        names = [spec.name for spec in get_geo_providers()]
        self._source_failures: Dict[str, int] = {name: 0 for name in names}
        self._source_block_until: Dict[str, float] = {name: 0.0 for name in names}
        self._source_last_error: Dict[str, str] = {name: "" for name in names}
        self._geo_cache: Dict[Tuple[str, str], Tuple[float, Dict[str, Any]]] = {}
        self._public_ip_cache: Tuple[float, str] | None = None
        self._failure_threshold = 2
        self._cooldown_seconds = 120.0

    @property
    def ip_apis(self) -> Dict[str, str]:
        """兼容旧调用：返回注册中心当前的提供者 URL 快照。"""
        return {spec.name: spec.url_template for spec in get_geo_providers()}

    def _limits(self):
        return get_ip_lookup_limits()

    def _provider_label(self, api_name: str) -> str:
        for spec in get_geo_providers():
            if spec.name == api_name:
                return spec.label
        return self.SOURCE_LABELS.get(api_name, api_name)

    @staticmethod
    def _cache_read(cache: Dict[Any, Tuple[float, Any]], key: Any, ttl_seconds: float) -> Optional[Any]:
        cached = cache.get(key)
        if not cached:
            return None
        stamped_at, value = cached
        if time.monotonic() - float(stamped_at) <= ttl_seconds:
            return dict(value) if isinstance(value, dict) else value
        cache.pop(key, None)
        return None

    @staticmethod
    def _cache_write(cache: Dict[Any, Tuple[float, Any]], key: Any, value: Any) -> None:
        cache[key] = (time.monotonic(), dict(value) if isinstance(value, dict) else value)

    def clear_cache(self) -> None:
        self._geo_cache.clear()
        self._public_ip_cache = None

    @staticmethod
    def _run_with_timeout(
        func: Callable[[], Any],
        timeout_seconds: float,
        default: Any,
        label: str,
    ) -> Tuple[Any, str]:
        """用守护线程给无原生超时的 DNS 调用加护栏，不阻塞解释器退出。"""
        box: Dict[str, Any] = {}

        def worker() -> None:
            try:
                box["value"] = func()
            except BaseException as exc:  # noqa: BLE001 - 线程内必须吞掉所有异常
                box["error"] = str(exc)

        thread = threading.Thread(target=worker, name=f"ip-lookup-{label}", daemon=True)
        thread.start()
        thread.join(max(0.05, float(timeout_seconds)))
        if thread.is_alive():
            return default, f"{label}超时"
        if "error" in box:
            return default, ""
        return box.get("value", default), ""

    def _is_source_blocked(self, api_name: str, now: Optional[float] = None) -> bool:
        now = time.time() if now is None else now
        return now < float(self._source_block_until.get(api_name, 0.0))

    def _mark_source_success(self, api_name: str) -> None:
        self._source_failures[api_name] = 0
        self._source_block_until[api_name] = 0.0
        self._source_last_error[api_name] = ""

    def _mark_source_failure(self, api_name: str, error: str) -> None:
        fail_count = int(self._source_failures.get(api_name, 0)) + 1
        self._source_failures[api_name] = fail_count
        self._source_last_error[api_name] = str(error or "未知错误")
        if fail_count >= self._failure_threshold:
            self._source_block_until[api_name] = time.time() + self._cooldown_seconds

    def _build_source_skip_reason(self, api_name: str) -> str:
        label = self._provider_label(api_name)
        if self._is_source_blocked(api_name):
            seconds = int(max(self._source_block_until.get(api_name, 0.0) - time.time(), 0))
            return f"{label} 熔断中({seconds}s)"
        error = str(self._source_last_error.get(api_name, "") or "").strip()
        if error:
            return f"{label} 失败: {error}"
        return f"{label} 暂不可用"

    def _query_ip_api(self, ip_address: str, api_name: str) -> Optional[Dict[str, Any]]:
        """按注册中心配置查询单个 IP 的地理位置与 ASN 信息。"""
        spec = next((item for item in get_geo_providers() if item.name == api_name), None)
        if spec is None or not spec.enabled or self._is_source_blocked(api_name):
            return None

        cache_key = (api_name, ip_address)
        cached = self._cache_read(self._geo_cache, cache_key, self._limits().geo_cache_ttl_seconds)
        if cached is not None:
            self._mark_source_success(api_name)
            return cached

        try:
            url = spec.url_template.format(ip=ip_address)
            response = requests.get(
                url,
                timeout=self._limits().geo_request_timeout_seconds,
                headers=self.DEFAULT_HEADERS,
                allow_redirects=False,
            )
            if response.status_code != 200:
                self._mark_source_failure(api_name, f"HTTP {response.status_code}")
                return None
            data = response.json()
            if not isinstance(data, dict):
                self._mark_source_failure(api_name, "返回内容无效")
                return None
            context = {
                "compose": self._compose_location,
                "country": self._get_country_name,
            }
            result = dict(spec.parser(data, context))
            result["_provider"] = spec.name
            self._mark_source_success(api_name)
            self._cache_write(self._geo_cache, cache_key, result)
            return dict(result)
        except Exception as exc:
            self._mark_source_failure(api_name, str(exc))
            return None

    def _compose_location(self, country: Optional[str], province: Optional[str], city: Optional[str]) -> str:
        parts = [part for part in [country, province, city] if part]
        return " ".join(parts) if parts else "未知"

    def _get_country_name(self, country_code: str) -> str:
        """将国家代码转换为国家名称，支持注册中心扩展。"""
        code = str(country_code or "").strip().upper()
        return get_country_names().get(code, code or "未知")

    def get_detailed_location(self, ip_address: str) -> Dict[str, Any]:
        """获取详细的 IP 地理位置信息。"""
        try:
            ip = ipaddress.ip_address(ip_address)
        except ValueError:
            return {
                "country": "未知",
                "province": "未知",
                "city": "未知",
                "isp": "未知",
                "location": "未知",
                "ip_type": "未知",
                "_source": "输入无效",
                "_status": "invalid",
            }

        local_details = None
        if ip.is_loopback:
            local_details = ("本机地址", "回环网络", "本机", "Loopback", "回环地址")
        elif ip.is_link_local:
            local_details = ("本地网络", "链路本地", "当前网段", "局域网", "链路本地地址")
        elif ip.is_unspecified:
            local_details = ("本地网络", "未指定地址", "未知", "未知", "未指定地址")
        elif ip.is_multicast:
            local_details = ("本地网络", "组播地址", "未知", "未知", "组播地址")
        elif ip.is_reserved:
            local_details = ("本地网络", "保留地址", "未知", "未知", "保留地址")
        elif ip.is_private:
            local_details = ("本地网络", "私有IP", "内网地址", "局域网", "私有网络地址")
        if local_details:
            country, province, city, isp, location = local_details
            return {
                "country": country,
                "province": province,
                "city": city,
                "isp": isp,
                "location": location,
                "ip_type": self._get_ip_type(str(ip)),
                "_source": "本地判断",
                "_status": "local",
            }

        fallback_notes: List[str] = []
        for spec in get_geo_providers():
            api_name = spec.name
            if self._is_source_blocked(api_name):
                fallback_notes.append(self._build_source_skip_reason(api_name))
                continue
            result = self._query_ip_api(str(ip), api_name)
            if result and result.get("country") not in {"", "未知"}:
                result["_source"] = spec.label
                result["_status"] = "ok"
                if fallback_notes:
                    result["_fallback_notes"] = "；".join(fallback_notes)
                return result
            fallback_notes.append(self._build_source_skip_reason(api_name))

        unknown_result = {
            "country": "未知",
            "province": "未知",
            "city": "未知",
            "isp": "未知",
            "location": "未知",
            "ip_type": self._get_ip_type(str(ip)),
            "_source": "无可用HTTPS源",
            "_status": "failed",
        }
        if fallback_notes:
            unknown_result["_fallback_notes"] = "；".join(fallback_notes)
        return unknown_result

    def get_public_ip(self) -> str:
        """获取当前机器的公网 IP，带短 TTL 缓存与注册式服务列表。"""
        ttl = self._limits().public_ip_cache_ttl_seconds
        cached = self._cache_read({self._public_ip_cache_key(): self._public_ip_cache} if self._public_ip_cache else {}, self._public_ip_cache_key(), ttl)
        if cached:
            return str(cached)

        for spec in get_public_ip_services():
            try:
                response = requests.get(
                    spec.url,
                    timeout=self._limits().public_ip_timeout_seconds,
                    headers=self.DEFAULT_HEADERS,
                    allow_redirects=False,
                )
                if response.status_code != 200:
                    continue
                if spec.response_type == "json":
                    payload = response.json()
                    ip_text = str(payload.get(spec.json_path, "") if isinstance(payload, dict) else "").strip()
                else:
                    ip_text = response.text.strip()
                ip_obj = ipaddress.ip_address(ip_text)
                result = ip_obj.compressed
                self._public_ip_cache = (time.monotonic(), result)
                return result
            except Exception:
                continue
        return "获取公网IP失败"

    @staticmethod
    def _public_ip_cache_key() -> str:
        return "public-ip"

    def _request_json(self, url: str, timeout: Optional[int] = None) -> Any:
        response = requests.get(
            url,
            timeout=timeout or self._limits().asset_request_timeout_seconds,
            headers=self.DEFAULT_HEADERS,
            allow_redirects=False,
        )
        response.raise_for_status()
        return response.json()

    def _request_text(self, url: str, timeout: Optional[int] = None) -> str:
        response = requests.get(
            url,
            timeout=timeout or self._limits().asset_request_timeout_seconds,
            headers=self.DEFAULT_HEADERS,
            allow_redirects=False,
        )
        response.raise_for_status()
        return response.text

    def parse_target_input(self, raw_target: str) -> Dict[str, Any]:
        """标准化输入并识别是 IP、域名还是 URL。"""
        original_input = str(raw_target or "").strip()
        if not original_input:
            return {"success": False, "error": "请输入 IP、域名或 URL"}

        notes: List[str] = []
        scheme = ""
        path = ""
        query = ""
        fragment = ""
        port: Any = ""
        host_candidate = original_input
        is_url = False

        parsed_value = self._try_parse_ip_literal(original_input)
        if not parsed_value:
            scheme_error = self._validate_scheme_input(original_input)
            if scheme_error:
                return {"success": False, "error": scheme_error}
            try:
                parsed = self._try_split_host(original_input)
                if parsed:
                    scheme = (parsed.scheme or "").lower()
                    if scheme and scheme not in get_scheme_allowlist():
                        return {"success": False, "error": f"仅支持 http/https URL，不支持 {scheme} 协议"}
                    if parsed.username is not None or parsed.password is not None:
                        original_input = self._redact_url_userinfo(original_input, parsed)
                        notes.append("已隐藏 URL 中的认证信息。")
                    if parsed.port is not None:
                        if not 1 <= int(parsed.port) <= 65535:
                            return {"success": False, "error": "端口必须在 1-65535 之间"}
                        port = int(parsed.port)
                    host_candidate = parsed.hostname or host_candidate
                    path = parsed.path or ""
                    query = parsed.query or ""
                    fragment = parsed.fragment or ""
                    is_url = bool(scheme or path or query or fragment or parsed.netloc)
                host_candidate = host_candidate.strip().strip("[]").strip()
            except ValueError:
                return {"success": False, "error": "端口格式无效，请输入 1-65535 的整数"}
            except Exception:
                host_candidate = original_input.strip().strip("[]").strip()

            parsed_value = self._try_parse_ip_literal(host_candidate)

        if parsed_value:
            ip_obj = ipaddress.ip_address(parsed_value)
            return {
                "success": True,
                "data": {
                    "original_input": original_input,
                    "normalized_target": ip_obj.compressed,
                    "display_target": ip_obj.compressed,
                    "target_type": "IP地址",
                    "is_ip": True,
                    "is_domain": False,
                    "is_url": is_url,
                    "scheme": scheme,
                    "port": port,
                    "path": path,
                    "query": query,
                    "fragment": fragment,
                    "notes": notes,
                },
            }

        normalized_domain = self._normalize_domain(host_candidate)
        if not normalized_domain or not self._is_valid_hostname(normalized_domain):
            return {"success": False, "error": "请输入有效的 IP、域名或 URL"}

        return {
            "success": True,
            "data": {
                "original_input": original_input,
                "normalized_target": normalized_domain,
                "display_target": normalized_domain,
                "target_type": "域名",
                "is_ip": False,
                "is_domain": True,
                "is_url": is_url,
                "scheme": scheme,
                "port": port,
                "path": path,
                "query": query,
                "fragment": fragment,
                "notes": notes,
            },
        }

    def _validate_scheme_input(self, value: str) -> str:
        """拦截 javascript:/mailto: 等伪协议，避免被误解析成域名。"""
        allowed = set(get_scheme_allowlist())
        if "://" in value:
            scheme = value.split("://", 1)[0].lower()
            if not re.fullmatch(r"[a-z][a-z0-9+.-]*", scheme):
                return "URL 协议格式无效"
            return "" if scheme in allowed else f"仅支持 http/https URL，不支持 {scheme} 协议"
        if value.startswith("["):
            return ""
        head, separator, _ = value.partition(":")
        if separator and re.fullmatch(r"[A-Za-z][A-Za-z0-9+-]*", head):
            if head.lower() not in allowed:
                return f"仅支持 http/https URL，不支持 {head} 协议"
            return "http/https URL 必须包含 //"
        return ""

    @staticmethod
    def _redact_url_userinfo(text: str, parsed: urllib.parse.SplitResult) -> str:
        netloc = parsed.netloc or ""
        if "@" not in netloc:
            return text
        userinfo, host_part = netloc.rsplit("@", 1)
        return text.replace(f"{userinfo}@", "***@", 1)

    def _try_split_host(self, input_value: str) -> Optional[urllib.parse.SplitResult]:
        candidate = input_value.strip()
        if not candidate:
            return None

        if "://" in candidate:
            return urllib.parse.urlsplit(candidate)

        if candidate.startswith("[") and "]" in candidate:
            return urllib.parse.urlsplit(f"//{candidate}")

        if any(separator in candidate for separator in "/?#"):
            return urllib.parse.urlsplit(f"//{candidate}")

        if candidate.count(":") == 1 and not self._looks_like_ipv6(candidate):
            return urllib.parse.urlsplit(f"//{candidate}")

        return None

    def _try_parse_ip_literal(self, value: str) -> Optional[str]:
        candidate = str(value or "").strip().strip("[]")
        if not candidate:
            return None
        try:
            return ipaddress.ip_address(candidate).compressed
        except ValueError:
            return None

    def _looks_like_ipv6(self, value: str) -> bool:
        return ":" in value and value.count(":") >= 2

    def _normalize_domain(self, domain: str) -> str:
        try:
            return domain.strip().rstrip(".").lower().encode("idna").decode("ascii")
        except Exception:
            return ""

    def get_registered_domain(self, domain: str) -> str:
        """尽量提取可注册主域名，用于 ICP 等按主域查询的场景。"""
        normalized = self._normalize_domain(domain)
        if not normalized or not self._is_valid_hostname(normalized):
            return ""

        labels = normalized.split(".")
        for suffix in get_registrable_suffixes():
            suffix_labels = suffix.split(".")
            if len(labels) > len(suffix_labels) and normalized.endswith(f".{suffix}"):
                return ".".join(labels[-(len(suffix_labels) + 1):])
        return normalized if len(labels) <= 2 else ".".join(labels[-2:])

    def _is_valid_hostname(self, hostname: str) -> bool:
        if not hostname or len(hostname) > 253 or ".." in hostname:
            return False
        if hostname.endswith("-") or hostname.startswith("-"):
            return False

        labels = hostname.split(".")
        for label in labels:
            if not label or not self.HOSTNAME_LABEL_PATTERN.match(label):
                return False
            if label.startswith("-") or label.endswith("-"):
                return False
        return True

    def resolve_domain_records(self, domain: str) -> Dict[str, Any]:
        """解析域名的 A/AAAA 记录与别名信息，每个 DNS 调用带超时护栏。"""
        ipv4_records: List[str] = []
        ipv6_records: List[str] = []
        aliases: List[str] = []
        canonical_candidates: List[str] = []
        notes: List[str] = []
        timeout = self._limits().dns_timeout_seconds

        gethost_result, timed_out = self._run_with_timeout(
            lambda: socket.gethostbyname_ex(domain), timeout, None, "gethostbyname_ex"
        )
        if timed_out:
            notes.append("gethostbyname_ex 查询超时")
        elif gethost_result:
            host, alias_list, ipv4_list = gethost_result
            if host:
                canonical_candidates.append(str(host).rstrip("."))
            for alias in alias_list or []:
                alias_value = str(alias).strip().rstrip(".")
                if alias_value and alias_value not in aliases:
                    aliases.append(alias_value)
            for ip in ipv4_list or []:
                if ip not in ipv4_records:
                    ipv4_records.append(ip)

        addr_info, timed_out = self._run_with_timeout(
            lambda: socket.getaddrinfo(domain, None), timeout, [], "getaddrinfo"
        )
        if timed_out:
            notes.append("getaddrinfo 查询超时")
        for family, _, _, canonname, sockaddr in addr_info or []:
            ip_text = sockaddr[0]
            if family == socket.AF_INET and ip_text not in ipv4_records:
                ipv4_records.append(ip_text)
            elif family == socket.AF_INET6 and ip_text not in ipv6_records:
                ipv6_records.append(ip_text)
            if canonname:
                canon_value = str(canonname).strip().rstrip(".")
                if canon_value and canon_value not in canonical_candidates:
                    canonical_candidates.append(canon_value)

        fqdn, timed_out = self._run_with_timeout(
            lambda: socket.getfqdn(domain), timeout, "", "getfqdn"
        )
        if timed_out:
            notes.append("getfqdn 查询超时")
        fqdn = str(fqdn or "").strip().rstrip(".")
        if fqdn and fqdn not in canonical_candidates and fqdn != domain:
            canonical_candidates.append(fqdn)

        all_ips = ipv4_records + [ip for ip in ipv6_records if ip not in ipv4_records]
        preferred_ip = ipv4_records[0] if ipv4_records else (ipv6_records[0] if ipv6_records else "")

        return {
            "canonical_name": canonical_candidates[0] if canonical_candidates else domain,
            "aliases": aliases,
            "ipv4_records": ipv4_records,
            "ipv6_records": ipv6_records,
            "all_ips": all_ips,
            "preferred_ip": preferred_ip,
            "address_count": len(all_ips),
            "解析提示": "；".join(notes),
        }

    def _extract_subdomain_names_from_ct_entry(self, entry: Dict[str, Any], domain: str) -> List[str]:
        names: List[str] = []
        for field_name in ("common_name", "name_value"):
            raw_value = str(entry.get(field_name, "") or "")
            if not raw_value:
                continue
            for line in raw_value.splitlines():
                candidate = self._normalize_domain(line.replace("*.", "").strip())
                if (
                    candidate
                    and candidate != domain
                    and candidate.endswith(f".{domain}")
                    and self._is_valid_hostname(candidate)
                ):
                    names.append(candidate)
        return names

    def query_subdomains(self, target: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """查询域名的常见子域名，显式暴露来源降级状态。"""
        parsed_result = self.parse_target_input(target)
        if not parsed_result["success"]:
            return {"success": False, "error": parsed_result["error"]}

        meta = parsed_result["data"]
        if meta.get("is_ip"):
            return {"success": False, "error": "子域名查询仅支持域名或 URL"}

        try:
            requested_limit = int(limit) if limit is not None else self._limits().subdomain_limit
        except (TypeError, ValueError):
            requested_limit = self._limits().subdomain_limit
        if not 1 <= requested_limit <= 1000:
            requested_limit = self._limits().subdomain_limit

        domain = meta["normalized_target"]
        source_names: List[str] = []
        merged_items: Dict[str, Dict[str, Any]] = {}
        errors: List[str] = []

        try:
            ct_payload = self._request_json(self.SUBDOMAIN_CRTSH_URL.format(domain=domain))
            source_names.append("crt.sh")
            for entry in ct_payload or []:
                for subdomain in self._extract_subdomain_names_from_ct_entry(entry, domain):
                    item = merged_items.setdefault(subdomain, {
                        "子域名": subdomain,
                        "解析IP": "",
                        "来源": set(),
                    })
                    item["来源"].add("crt.sh")
        except Exception as exc:
            errors.append(f"crt.sh 查询失败: {exc}")

        try:
            hostsearch_text = self._request_text(self.SUBDOMAIN_HOSTSEARCH_URL.format(domain=domain))
            if hostsearch_text and "error check your search parameter" not in hostsearch_text.lower():
                source_names.append("HackerTarget HostSearch")
                for line in hostsearch_text.splitlines():
                    parts = [part.strip() for part in line.split(",", 1)]
                    if len(parts) != 2:
                        continue
                    subdomain, ip_address = parts
                    subdomain = self._normalize_domain(subdomain)
                    if (
                        subdomain
                        and subdomain != domain
                        and subdomain.endswith(f".{domain}")
                        and self._is_valid_hostname(subdomain)
                    ):
                        item = merged_items.setdefault(subdomain, {
                            "子域名": subdomain,
                            "解析IP": "",
                            "来源": set(),
                        })
                        if ip_address and not item["解析IP"]:
                            item["解析IP"] = ip_address
                        item["来源"].add("HackerTarget")
        except Exception as exc:
            errors.append(f"HackerTarget HostSearch 查询失败: {exc}")

        results = sorted(
            (
                {
                    "子域名": item["子域名"],
                    "解析IP": item["解析IP"] or "-",
                    "来源": ", ".join(sorted(item["来源"])),
                }
                for item in merged_items.values()
            ),
            key=lambda row: row["子域名"],
        )[:requested_limit]

        status = "ok" if source_names and not errors else ("partial" if source_names else "failed")
        error_text = " | ".join(errors)
        return {
            "success": bool(source_names),
            "status": status,
            "error": "" if source_names else f"子域名查询所有数据源均失败: {error_text}",
            "data": {
                "查询目标": domain,
                "可注册主域": self.get_registered_domain(domain),
                "子域名数量": len(results),
                "结果": results,
                "数据来源": " / ".join(source_names) if source_names else "无可用来源",
                "查询状态": status,
                "备注": "结果来自证书透明日志与公开 DNS 资产接口，可能存在遗漏或历史记录。",
                "错误信息": error_text,
            },
        }

    def _resolve_ip_for_reverse_lookup(self, target: str) -> Dict[str, Any]:
        parsed_result = self.parse_target_input(target)
        if not parsed_result["success"]:
            return {"success": False, "error": parsed_result["error"]}

        meta = parsed_result["data"]
        if meta.get("is_ip"):
            return {
                "success": True,
                "data": {
                    "输入目标": meta["normalized_target"],
                    "查询IP": meta["normalized_target"],
                    "输入类型": "IP地址",
                },
            }

        dns_info = self.resolve_domain_records(meta["normalized_target"])
        preferred_ip = dns_info.get("preferred_ip", "")
        if not preferred_ip:
            return {"success": False, "error": "域名未解析到可用 IP，无法执行旁站查询"}

        return {
            "success": True,
            "data": {
                "输入目标": meta["normalized_target"],
                "查询IP": preferred_ip,
                "输入类型": "域名",
            },
        }

    def query_reverse_sites(self, target: str, limit: Optional[int] = None) -> Dict[str, Any]:
        """按 IP 查询同服站点（旁站）。"""
        resolved_result = self._resolve_ip_for_reverse_lookup(target)
        if not resolved_result["success"]:
            return resolved_result

        try:
            requested_limit = int(limit) if limit is not None else self._limits().subdomain_limit
        except (TypeError, ValueError):
            requested_limit = self._limits().subdomain_limit
        if not 1 <= requested_limit <= 1000:
            requested_limit = self._limits().subdomain_limit

        resolved_meta = resolved_result["data"]
        ip_address = resolved_meta["查询IP"]
        try:
            response_text = self._request_text(self.REVERSE_IP_LOOKUP_URL.format(ip=ip_address))
        except Exception as exc:
            return {"success": False, "status": "failed", "error": f"旁站查询失败: {exc}"}

        lowered_text = response_text.lower()
        if "api count exceeded" in lowered_text:
            return {"success": False, "status": "failed", "error": "旁站查询接口达到速率限制，请稍后重试"}
        if "no records found" in lowered_text:
            sites: List[Dict[str, Any]] = []
        else:
            seen = set()
            sites = []
            for line in response_text.splitlines():
                hostname = self._normalize_domain(line.strip())
                if not hostname or hostname in seen or not self._is_valid_hostname(hostname):
                    continue
                seen.add(hostname)
                sites.append({"站点域名": hostname})

        sites = sites[:requested_limit]
        return {
            "success": True,
            "status": "ok",
            "error": "",
            "data": {
                "输入目标": resolved_meta["输入目标"],
                "查询IP": ip_address,
                "旁站数量": len(sites),
                "结果": sites,
                "数据来源": "HackerTarget Reverse IP Lookup",
                "备注": "旁站结果来自公开反查接口，仅供测试排查参考，不代表真实完整托管关系。",
            },
        }

    def query_icp_info(self, target: str) -> Dict[str, Any]:
        """查询域名的 ICP 备案信息。"""
        parsed_result = self.parse_target_input(target)
        if not parsed_result["success"]:
            return {"success": False, "error": parsed_result["error"]}

        meta = parsed_result["data"]
        if meta.get("is_ip"):
            return {"success": False, "error": "ICP备案查询仅支持域名或 URL"}

        domain = meta["normalized_target"]
        registered_domain = self.get_registered_domain(domain)
        if not registered_domain:
            return {"success": False, "error": "无法识别可注册主域名"}

        try:
            payload = self._request_json(self.ICP_LOOKUP_URL.format(domain=registered_domain))
        except Exception as exc:
            return {"success": False, "status": "failed", "error": f"ICP备案查询失败: {exc}"}

        if isinstance(payload, dict) and "code" in payload:
            raw_code = str(payload.get("code", "")).strip()
            if raw_code not in {"0", "200"}:
                message = str(payload.get("message") or payload.get("error") or "第三方接口返回失败").strip()
                return {"success": False, "status": "failed", "error": f"ICP备案接口返回 {raw_code}: {message}"}

        record = payload.get("data") if isinstance(payload, dict) else None
        if not record:
            return {"success": False, "status": "failed", "error": "未查询到备案信息"}

        icp_info = {
            "查询域名": domain,
            "备案主域": registered_domain,
            "备案号": record.get("DomainIcpNum", "未知"),
            "主办单位": record.get("CompanyName", "未知"),
            "单位性质": record.get("CompanyType", "未知"),
            "网站名称": record.get("WebsiteName", "未知"),
            "网站首页": record.get("WebsiteHomeUrl", "未知"),
            "审核时间": record.get("AuditTime", "未知"),
            "腾讯云标记": "是" if record.get("InTencent") else "否",
            "数据来源": "api.mmp.cc (第三方公开接口)",
            "官方核验": self.MIIT_ICP_VERIFY_URL,
            "备注": "ICP备案结果来自第三方公开接口，实际核验请以工信部官网为准。",
        }
        cache_source = payload.get("from") if isinstance(payload, dict) else ""
        if cache_source:
            icp_info["返回来源"] = cache_source

        return {"success": True, "status": "ok", "error": "", "data": icp_info}

    def get_ip_domain_info(
        self,
        target: str,
        is_ip: Optional[bool] = None,
        parsed_target: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """获取 IP/域名详细信息。"""
        try:
            if parsed_target is None:
                parsed_result = self.parse_target_input(target)
                if not parsed_result["success"]:
                    return {"success": False, "error": parsed_result["error"]}
                parsed_target = parsed_result["data"]

            normalized_target = parsed_target.get("normalized_target", str(target).strip())
            is_ip = parsed_target.get("is_ip", False) if is_ip is None else is_ip

            info_dict: Dict[str, Any] = {
                "输入类型": parsed_target.get("target_type", "未知"),
                "查询时间": datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z"),
                "数据来源": self.data_source,
                "结果状态": "成功",
            }

            original_input = parsed_target.get("original_input", "")
            if original_input and original_input != normalized_target:
                info_dict["原始输入"] = original_input

            if parsed_target.get("scheme"):
                info_dict["协议"] = parsed_target["scheme"]
            if parsed_target.get("port") not in ("", None):
                info_dict["端口"] = parsed_target["port"]
                info_dict["端口服务"] = self._get_service_name(int(parsed_target["port"]))
            if parsed_target.get("path"):
                info_dict["路径"] = parsed_target["path"]
            if parsed_target.get("query"):
                info_dict["查询参数"] = parsed_target["query"]
            if parsed_target.get("fragment"):
                info_dict["片段"] = parsed_target["fragment"]
            if parsed_target.get("notes"):
                info_dict["输入备注"] = " ".join(parsed_target["notes"])

            location_info: Dict[str, Any] = {}
            primary_ip = normalized_target

            if is_ip:
                ip_obj = ipaddress.ip_address(normalized_target)
                location_info = self.get_detailed_location(normalized_target)
                info_dict["IP地址"] = normalized_target
                info_dict["IP版本"] = f"IPv{ip_obj.version}"
                info_dict["IP类型"] = self._get_ip_type(normalized_target)
                info_dict["反向解析指针"] = ip_obj.reverse_pointer
                if ip_obj.version == 6:
                    info_dict["压缩格式"] = ip_obj.compressed
                    info_dict["展开格式"] = ip_obj.exploded

                rdns_result = self.get_rdns_info(normalized_target)
                if rdns_result["success"]:
                    info_dict["rDNS"] = rdns_result["data"].get("rDNS", "未知")

                fqdn, fqdn_timeout = self._run_with_timeout(
                    lambda: socket.getfqdn(normalized_target),
                    self._limits().dns_timeout_seconds,
                    "",
                    "getfqdn",
                )
                if fqdn_timeout:
                    info_dict["解析提示"] = "主机名反查超时"
                if fqdn and fqdn != normalized_target:
                    info_dict["主机名"] = fqdn
            else:
                info_dict["域名"] = normalized_target
                dns_info = self.resolve_domain_records(normalized_target)
                primary_ip = dns_info.get("preferred_ip", "")

                info_dict["解析状态"] = "成功" if primary_ip else "失败"
                if dns_info.get("canonical_name") and dns_info["canonical_name"] != normalized_target:
                    info_dict["规范主机名"] = dns_info["canonical_name"]
                if dns_info.get("aliases"):
                    info_dict["别名"] = ", ".join(dns_info["aliases"])
                info_dict["地址数量"] = dns_info.get("address_count", 0)
                info_dict["首选IP"] = primary_ip or "解析失败"
                if dns_info.get("ipv4_records"):
                    info_dict["A记录"] = ", ".join(dns_info["ipv4_records"])
                if dns_info.get("ipv6_records"):
                    info_dict["AAAA记录"] = ", ".join(dns_info["ipv6_records"])
                if dns_info.get("all_ips") and len(dns_info["all_ips"]) > 1:
                    info_dict["所有IP"] = ", ".join(dns_info["all_ips"])

                if primary_ip:
                    location_info = self.get_detailed_location(primary_ip)
                    info_dict["解析IP"] = primary_ip
                    info_dict["首选IP类型"] = self._get_ip_type(primary_ip)
                else:
                    info_dict["解析IP"] = "解析失败"
                    info_dict["结果状态"] = "解析失败"
                    info_dict.update(self._default_location())

            if location_info:
                info_dict.update({
                    "国家": location_info.get("country", "未知"),
                    "省份": location_info.get("province", "未知"),
                    "城市": location_info.get("city", "未知"),
                    "运营商": location_info.get("isp", "未知"),
                    "地理位置": location_info.get("location", "未知"),
                })
                if location_info.get("_source"):
                    info_dict["地理数据来源"] = location_info["_source"]
                if location_info.get("_status") == "failed":
                    info_dict["结果状态"] = "地理数据降级"
                if location_info.get("_fallback_notes"):
                    info_dict["来源降级说明"] = location_info["_fallback_notes"]

                if location_info.get("timezone"):
                    info_dict["时区"] = location_info["timezone"]
                if location_info.get("coordinates"):
                    info_dict["坐标"] = location_info["coordinates"]
                if location_info.get("currency"):
                    info_dict["货币"] = location_info["currency"]
                if location_info.get("languages"):
                    info_dict["语言"] = location_info["languages"]
            else:
                info_dict.update(self._default_location())
                info_dict["地理数据来源"] = "无可用来源"

            asn_target = normalized_target if is_ip else (primary_ip or normalized_target)
            info_dict["ASN信息"] = self.get_asn_info(asn_target, location_info=location_info)
            info_dict["网络段"] = self._get_network_segment(primary_ip if primary_ip else normalized_target)

            return {"success": True, "data": info_dict}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def _get_ip_type(self, ip_address: str) -> str:
        """获取 IP 类型。"""
        try:
            ip = ipaddress.ip_address(ip_address)
            if ip.is_loopback:
                return "回环IP"
            if ip.is_private:
                return "私有IP"
            if ip.is_link_local:
                return "链路本地IP"
            if ip.is_multicast:
                return "组播IP"
            if ip.is_reserved:
                return "保留IP"
            if ip.is_unspecified:
                return "未指定IP"
            if ip.is_global:
                return "公网IPv4" if ip.version == 4 else "公网IPv6"
            return "IPv4" if ip.version == 4 else "IPv6"
        except ValueError:
            return "IPv4" if "." in ip_address else "IPv6"

    def _get_network_segment(self, target: str) -> str:
        """获取网络段信息。"""
        try:
            ip_obj = ipaddress.ip_address(target)
            prefix_length = 24 if ip_obj.version == 4 else 64
            network = ipaddress.ip_network(f"{ip_obj}/{prefix_length}", strict=False)
            return str(network)
        except ValueError:
            return "未知"

    def get_asn_info(self, target: str, location_info: Optional[Dict[str, Any]] = None) -> str:
        """获取 ASN 信息。"""
        try:
            ip_value = self._try_parse_ip_literal(target)
            if ip_value:
                location_info = location_info or self.get_detailed_location(ip_value)
                asn = location_info.get("asn", "")
                isp = location_info.get("isp", "")

                if asn:
                    return f"{asn} ({isp})" if isp and isp not in asn else asn
                if isp:
                    return isp
                return self._get_asn_from_local(ip_value)

            return self._get_asn_from_domain(target)
        except Exception as exc:
            return f"AS未知 (错误: {exc})"

    def _get_asn_from_local(self, ip_address: str) -> str:
        """本地常见公网/私网 ASN 映射。"""
        ip_value = self._try_parse_ip_literal(ip_address)
        if not ip_value:
            return "AS未知"

        ip_obj = ipaddress.ip_address(ip_value)
        if ip_obj.is_private:
            return "AS0 (私有网络)"
        if ip_obj.is_loopback:
            return "AS0 (回环网络)"
        if ip_obj.is_link_local:
            return "AS0 (链路本地)"
        if ip_obj.version != 4:
            return "AS未知"

        ip_parts = ip_value.split(".")
        ip_prefix = f"{ip_parts[0]}.{ip_parts[1]}"
        asn_mapping = {
            "8.8": "AS15169 (Google LLC)",
            "1.1": "AS13335 (Cloudflare, Inc.)",
            "9.9": "AS19281 (Quad9)",
            "64.6": "AS36692 (OpenDNS)",
            "208.67": "AS36692 (OpenDNS)",
        }
        inferred = asn_mapping.get(ip_prefix, "")
        return f"{inferred} [根据IP段推断]" if inferred else "AS未知"

    def _get_asn_from_domain(self, domain: str) -> str:
        """根据常见域名关键字回退 ASN 信息。"""
        domain_lower = domain.lower()
        asn_mapping = {
            "google": "AS15169 (Google LLC)",
            "cloudflare": "AS13335 (Cloudflare, Inc.)",
            "baidu": "AS55990 (Baidu)",
            "aliyun": "AS45102 (Alibaba Cloud)",
            "alibaba": "AS45102 (Alibaba Cloud)",
            "tencent": "AS45090 (Tencent Cloud)",
            "qq.com": "AS45090 (Tencent Cloud)",
            "huawei": "AS136907 (Huawei Cloud)",
            "amazon": "AS16509 (Amazon.com, Inc.)",
            "aws": "AS16509 (Amazon.com, Inc.)",
            "microsoft": "AS8075 (Microsoft Corporation)",
            "azure": "AS8075 (Microsoft Corporation)",
            "facebook": "AS32934 (Meta Platforms)",
            "twitter": "AS13414 (X Corp.)",
            "apple": "AS714 (Apple Inc.)",
        }
        for keyword, value in asn_mapping.items():
            if keyword in domain_lower:
                return f"{value} [根据域名推断]"
        return "AS未知"

    def _default_location(self) -> Dict[str, str]:
        return {
            "国家": "未知",
            "省份": "未知",
            "城市": "未知",
            "运营商": "未知",
            "地理位置": "未知",
        }

    def get_rdns_info(self, ip_address: str) -> Dict[str, Any]:
        """获取 rDNS 信息。"""
        ip_value = self._try_parse_ip_literal(ip_address)
        if not ip_value:
            return {"success": False, "error": "无效IP地址"}

        result, timed_out = self._run_with_timeout(
            lambda: socket.gethostbyaddr(ip_value),
            self._limits().dns_timeout_seconds,
            None,
            "gethostbyaddr",
        )
        if timed_out:
            return {"success": False, "error": "rDNS 查询超时"}
        try:
            hostname = result[0]
            return {"success": True, "data": {"rDNS": hostname}}
        except Exception:
            return {"success": False, "error": "无法获取rDNS信息"}

    def get_ipv4_conversions(self, input_value: str) -> Dict[str, str]:
        """自动识别 IPv4 格式并输出全部常见表示。"""
        value = str(input_value or "").strip().lower()
        if not value:
            raise ValueError("请输入 IPv4 地址、十进制、十六进制或二进制值")

        format_name = ""
        if self._is_valid_ipv4(value):
            ip_obj = ipaddress.IPv4Address(value)
            format_name = "点分十进制"
        elif re.fullmatch(r"\d+", value):
            decimal_value = int(value)
            if decimal_value < 0 or decimal_value > 0xFFFFFFFF:
                raise ValueError("十进制数超出 IPv4 范围")
            ip_obj = ipaddress.IPv4Address(decimal_value)
            format_name = "十进制"
        elif value.startswith("0x") or re.fullmatch(r"[0-9a-f]{1,8}", value):
            hex_value = value[2:] if value.startswith("0x") else value
            if not re.fullmatch(r"[0-9a-f]{1,8}", hex_value):
                raise ValueError("十六进制格式无效")
            ip_obj = ipaddress.IPv4Address(int(hex_value, 16))
            format_name = "十六进制"
        else:
            if "." in value and not re.fullmatch(r"([01]{8}\.){3}[01]{8}", value):
                raise ValueError("二进制格式无效，应为 32 位连续值或 4 段 8 位二进制")
            binary_value = value.replace(".", "")
            if not re.fullmatch(r"[01]{32}", binary_value):
                raise ValueError("无法识别输入格式，请输入有效的 IPv4 地址/十进制/十六进制/二进制")
            ip_obj = ipaddress.IPv4Address(int(binary_value, 2))
            format_name = "二进制"

        integer_value = int(ip_obj)
        dotted_binary = ".".join(f"{part:08b}" for part in ip_obj.packed)
        return {
            "识别格式": format_name,
            "点分十进制": str(ip_obj),
            "十进制": str(integer_value),
            "十六进制": f"0x{integer_value:08x}",
            "二进制": dotted_binary,
            "二进制(连续)": f"{integer_value:032b}",
        }

    def _is_valid_ipv4(self, value: str) -> bool:
        try:
            ipaddress.IPv4Address(value)
            return True
        except ValueError:
            return False

    def convert_ip_address(self, input_value: str, conversion_type: str) -> Dict[str, Any]:
        """IPv4 地址格式转换，转换方式由注册中心驱动。"""
        try:
            spec = next((item for item in get_conversion_types() if item.label == conversion_type), None)
            if spec is None:
                raise ValueError("不支持的转换类型")
            conversions = self.get_ipv4_conversions(input_value)
            result = {"识别格式": conversions["识别格式"]}
            for field in spec.fields:
                result[field] = conversions[field]
            return {"success": True, "data": result}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    def set_data_source(self, source: str) -> None:
        value = str(source or "").strip()
        if not value:
            raise ValueError("数据来源不能为空")
        self.data_source = value

    def run_asset_action(self, key: str, target: str) -> Dict[str, Any]:
        """按注册中心配置执行资产扩展动作。"""
        spec = next((item for item in get_asset_actions() if item.key == key), None)
        if spec is None:
            return {"success": False, "status": "failed", "error": f"未注册的资产动作: {key}"}
        handler = getattr(self, spec.handler_name, None)
        if not callable(handler):
            return {"success": False, "status": "failed", "error": f"资产动作处理器不存在: {spec.handler_name}"}
        return handler(target)

    def get_tool_info(self) -> Dict[str, Any]:
        return {
            "name": "改进的IP地址查询工具",
            "version": "3.3",
            "author": "IP Query Tool",
            "functions": [
                "IP/域名信息查询（支持 URL 提取）",
                "公网 IP 获取",
                "ASN 信息查询",
                "rDNS 查询",
                "A/AAAA 域名解析",
                "HTTPS 多源地理查询与熔断降级",
                "子域名查询",
                "旁站查询",
                "ICP备案查询",
                "IPv4 地址格式转换",
            ],
        }

    def _get_service_name(self, port: int) -> str:
        return get_service_names().get(int(port), "未知")
