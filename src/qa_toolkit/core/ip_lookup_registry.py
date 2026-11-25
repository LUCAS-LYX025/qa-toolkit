"""IP/域名查询工具的注册式扩展点。

默认能力以注册项形式提供，页面与核心逻辑只依赖查询函数，不再硬编码
数据源、转换方式、资产动作和运行参数。
"""
from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Tuple

NamePattern = re.compile(r"^[A-Za-z0-9_-]{1,48}$")
CountryPattern = re.compile(r"^[A-Za-z]{2}$")

CONVERSION_FIELDS: Tuple[str, ...] = (
    "识别格式",
    "点分十进制",
    "十进制",
    "十六进制",
    "二进制",
    "二进制(连续)",
)


@dataclass(frozen=True)
class GeoProviderSpec:
    name: str
    label: str
    url_template: str
    parser: Callable[[Mapping[str, Any], Mapping[str, Callable[..., Any]]], Dict[str, Any]]
    priority: int = 100
    enabled: bool = True


@dataclass(frozen=True)
class PublicIpServiceSpec:
    name: str
    url: str
    response_type: str = "text"
    json_path: str = "ip"
    priority: int = 100
    enabled: bool = True


@dataclass(frozen=True)
class ConversionSpec:
    label: str
    fields: Tuple[str, ...]


@dataclass(frozen=True)
class AssetActionSpec:
    key: str
    label: str
    button_key: str
    handler_name: str
    result_label: str = ""
    priority: int = 100
    enabled: bool = True


@dataclass(frozen=True)
class IpLookupLimits:
    max_batch_targets: int = 50
    subdomain_limit: int = 200
    request_timeout_seconds: int = 15
    geo_request_timeout_seconds: int = 8
    public_ip_timeout_seconds: int = 5
    asset_request_timeout_seconds: int = 20
    dns_timeout_seconds: float = 3.0
    geo_cache_ttl_seconds: float = 600.0
    public_ip_cache_ttl_seconds: float = 300.0


def _compose_location(country: Optional[str], province: Optional[str], city: Optional[str]) -> str:
    parts = [str(part).strip() for part in (country, province, city) if part]
    return " ".join(parts) if parts else "未知"


def parse_ipapi(payload: Mapping[str, Any], ctx: Mapping[str, Callable[..., Any]]) -> Dict[str, Any]:
    return {
        "country": payload.get("country_name") or "未知",
        "province": payload.get("region") or "未知",
        "city": payload.get("city") or "未知",
        "isp": payload.get("org") or "未知",
        "location": _compose_location(payload.get("country_name"), payload.get("region"), payload.get("city")),
        "asn": payload.get("asn", ""),
        "timezone": payload.get("timezone", ""),
        "currency": payload.get("currency", ""),
        "languages": payload.get("languages", ""),
    }


def parse_ipinfo(payload: Mapping[str, Any], ctx: Mapping[str, Callable[..., Any]]) -> Dict[str, Any]:
    country = ctx["country"](str(payload.get("country") or ""))
    org = str(payload.get("org") or "")
    return {
        "country": country,
        "province": payload.get("region") or "未知",
        "city": payload.get("city") or "未知",
        "isp": org or "未知",
        "location": _compose_location(country, payload.get("region"), payload.get("city")),
        "asn": org.split(" ")[0] if "AS" in org else "",
        "timezone": payload.get("timezone", ""),
        "coordinates": payload.get("loc", ""),
    }


def parse_ipwhois(payload: Mapping[str, Any], ctx: Mapping[str, Callable[..., Any]]) -> Dict[str, Any]:
    if payload.get("success") is False:
        raise ValueError(str(payload.get("message") or "ipwho.is 返回失败"))
    region = payload.get("region") or payload.get("region_name") or ""
    connection = payload.get("connection") if isinstance(payload.get("connection"), dict) else {}
    timezone = payload.get("timezone") if isinstance(payload.get("timezone"), dict) else {}
    currency = payload.get("currency") if isinstance(payload.get("currency"), dict) else {}
    return {
        "country": payload.get("country") or "未知",
        "province": region or "未知",
        "city": payload.get("city") or "未知",
        "isp": connection.get("isp") or connection.get("org") or "未知",
        "location": _compose_location(payload.get("country"), region, payload.get("city")),
        "asn": connection.get("asn", ""),
        "timezone": timezone.get("id", ""),
        "currency": currency.get("code", ""),
    }


DEFAULT_GEO_PROVIDERS: Tuple[GeoProviderSpec, ...] = (
    GeoProviderSpec("ipapi", "ipapi.co (HTTPS)", "https://ipapi.co/{ip}/json/", parse_ipapi, priority=10),
    GeoProviderSpec("ipinfo", "ipinfo.io (HTTPS)", "https://ipinfo.io/{ip}/json", parse_ipinfo, priority=20),
    GeoProviderSpec("ipwhois", "ipwho.is (HTTPS)", "https://ipwho.is/{ip}", parse_ipwhois, priority=30),
)

DEFAULT_PUBLIC_IP_SERVICES: Tuple[PublicIpServiceSpec, ...] = (
    PublicIpServiceSpec("ipify", "https://api64.ipify.org?format=json", "json", "ip", priority=10),
    PublicIpServiceSpec("identme", "https://ident.me", "text", priority=20),
    PublicIpServiceSpec("amazonaws", "https://checkip.amazonaws.com", "text", priority=30),
    PublicIpServiceSpec("ifconfigme", "https://ifconfig.me/ip", "text", priority=40),
)

DEFAULT_CONVERSIONS: Tuple[ConversionSpec, ...] = (
    ConversionSpec("自动识别并展示全部格式", CONVERSION_FIELDS),
    ConversionSpec("十进制 ↔ 点分十进制", ("点分十进制", "十进制")),
    ConversionSpec("点分十进制 ↔ 十六进制", ("点分十进制", "十六进制")),
    ConversionSpec("点分十进制 ↔ 二进制", ("点分十进制", "二进制", "二进制(连续)")),
)

DEFAULT_ASSET_ACTIONS: Tuple[AssetActionSpec, ...] = (
    AssetActionSpec("subdomains", "查询子域名", "ip_lookup_subdomains", "query_subdomains", "子域名查询", priority=10),
    AssetActionSpec("reverse", "查询旁站", "ip_lookup_reverse", "query_reverse_sites", "旁站查询", priority=20),
    AssetActionSpec("icp", "查询 ICP", "ip_lookup_icp", "query_icp_info", "ICP备案查询", priority=30),
)

DEFAULT_SUFFIXES: Tuple[str, ...] = (
    "com.cn", "net.cn", "org.cn", "gov.cn", "edu.cn", "ac.cn",
    "com.hk", "com.tw", "com.mo", "com.sg", "co.jp", "co.kr",
    "co.uk", "org.uk", "ac.uk",
)

DEFAULT_PORTS: Dict[int, str] = {
    20: "FTP-DATA", 21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS",
    80: "HTTP", 110: "POP3", 143: "IMAP", 443: "HTTPS", 465: "SMTPS",
    587: "SMTP Submission", 993: "IMAPS", 995: "POP3S", 3306: "MySQL",
    3389: "RDP", 5432: "PostgreSQL", 6379: "Redis", 8080: "HTTP-Alt",
    8443: "HTTPS-Alt", 27017: "MongoDB",
}

DEFAULT_COUNTRIES: Dict[str, str] = {
    "CN": "中国", "US": "美国", "JP": "日本", "KR": "韩国", "SG": "新加坡",
    "DE": "德国", "FR": "法国", "GB": "英国", "RU": "俄罗斯", "IN": "印度",
    "BR": "巴西", "CA": "加拿大", "AU": "澳大利亚", "TW": "中国台湾",
    "HK": "中国香港", "MO": "中国澳门",
}

_geo_providers: Dict[str, GeoProviderSpec] = {item.name: item for item in DEFAULT_GEO_PROVIDERS}
_public_ip_services: Dict[str, PublicIpServiceSpec] = {item.name: item for item in DEFAULT_PUBLIC_IP_SERVICES}
_conversions: Dict[str, ConversionSpec] = {item.label: item for item in DEFAULT_CONVERSIONS}
_asset_actions: Dict[str, AssetActionSpec] = {item.key: item for item in DEFAULT_ASSET_ACTIONS}
_suffixes: set[str] = set(DEFAULT_SUFFIXES)
_ports: Dict[int, str] = dict(DEFAULT_PORTS)
_countries: Dict[str, str] = dict(DEFAULT_COUNTRIES)
_limits = IpLookupLimits()
_scheme_allowlist: set[str] = {"http", "https"}


def _validate_name(name: str, field: str = "name") -> str:
    value = str(name or "").strip()
    if not NamePattern.match(value):
        raise ValueError(f"{field} 只能包含字母、数字、下划线和连字符（1-48 位）")
    return value


def _validate_https_url(url: str, field: str, placeholder: str = "") -> str:
    value = str(url or "").strip()
    if not value.startswith("https://"):
        raise ValueError(f"{field} 仅允许 HTTPS 地址")
    if placeholder and placeholder not in value:
        raise ValueError(f"{field} 必须包含 {placeholder} 占位符")
    return value


def register_geo_provider(
    name: str,
    label: str,
    url_template: str,
    parser: Callable[[Mapping[str, Any], Mapping[str, Callable[..., Any]]], Dict[str, Any]],
    *,
    priority: int = 100,
    enabled: bool = True,
    replace: bool = False,
) -> None:
    safe_name = _validate_name(name)
    if not callable(parser):
        raise ValueError("parser 必须是可调用对象")
    if not str(label or "").strip():
        raise ValueError("label 不能为空")
    if safe_name in _geo_providers and not replace:
        raise ValueError(f"地理数据源 {safe_name} 已存在")
    _geo_providers[safe_name] = GeoProviderSpec(
        safe_name, str(label).strip(), _validate_https_url(url_template, "url_template", "{ip}"),
        parser, int(priority), bool(enabled),
    )


def unregister_geo_provider(name: str) -> bool:
    return _geo_providers.pop(str(name), None) is not None


def get_geo_providers() -> Tuple[GeoProviderSpec, ...]:
    return tuple(sorted((item for item in _geo_providers.values() if item.enabled), key=lambda item: (item.priority, item.name)))


def register_public_ip_service(
    name: str,
    url: str,
    *,
    response_type: str = "text",
    json_path: str = "ip",
    priority: int = 100,
    enabled: bool = True,
    replace: bool = False,
) -> None:
    safe_name = _validate_name(name)
    if response_type not in {"json", "text"}:
        raise ValueError("response_type 仅支持 json 或 text")
    if safe_name in _public_ip_services and not replace:
        raise ValueError(f"公网 IP 服务 {safe_name} 已存在")
    _public_ip_services[safe_name] = PublicIpServiceSpec(
        safe_name, _validate_https_url(url, "url"), response_type, json_path, int(priority), bool(enabled),
    )


def unregister_public_ip_service(name: str) -> bool:
    return _public_ip_services.pop(str(name), None) is not None


def get_public_ip_services() -> Tuple[PublicIpServiceSpec, ...]:
    return tuple(sorted((item for item in _public_ip_services.values() if item.enabled), key=lambda item: (item.priority, item.name)))


def register_conversion_type(label: str, fields: Iterable[str], *, replace: bool = False) -> None:
    safe_label = str(label or "").strip()
    if not safe_label:
        raise ValueError("转换方式标签不能为空")
    selected = tuple(dict.fromkeys(str(field) for field in fields))
    if not selected or any(field not in CONVERSION_FIELDS for field in selected):
        raise ValueError(f"fields 只能来自: {', '.join(CONVERSION_FIELDS)}")
    if safe_label in _conversions and not replace:
        raise ValueError(f"转换方式 {safe_label} 已存在")
    _conversions[safe_label] = ConversionSpec(safe_label, selected)


def unregister_conversion_type(label: str) -> bool:
    return _conversions.pop(str(label), None) is not None


def get_conversion_types() -> Tuple[ConversionSpec, ...]:
    return tuple(_conversions.values())


def register_asset_action(
    key: str,
    label: str,
    button_key: str,
    handler_name: str,
    *,
    result_label: str = "",
    priority: int = 100,
    enabled: bool = True,
    replace: bool = False,
) -> None:
    safe_key = _validate_name(key, "key")
    if not str(label or "").strip() or not str(button_key or "").strip():
        raise ValueError("label 与 button_key 不能为空")
    _validate_name(handler_name, "handler_name")
    if safe_key in _asset_actions and not replace:
        raise ValueError(f"资产动作 {safe_key} 已存在")
    _asset_actions[safe_key] = AssetActionSpec(
        safe_key, str(label).strip(), str(button_key).strip(), str(handler_name),
        str(result_label or label).strip(), int(priority), bool(enabled),
    )


def unregister_asset_action(key: str) -> bool:
    return _asset_actions.pop(str(key), None) is not None


def get_asset_actions() -> Tuple[AssetActionSpec, ...]:
    return tuple(sorted((item for item in _asset_actions.values() if item.enabled), key=lambda item: (item.priority, item.key)))


def register_registrable_suffix(suffix: str) -> None:
    value = str(suffix or "").strip().lower().lstrip(".")
    if not value or ".." in value or any(not part or not part.isalnum() for part in value.split(".")):
        raise ValueError("suffix 格式无效")
    _suffixes.add(value)


def get_registrable_suffixes() -> Tuple[str, ...]:
    return tuple(sorted(_suffixes, key=lambda item: (-len(item.split(".")), item)))


# 兼容issue中的简短命名。
register_suffix = register_registrable_suffix


def register_service_name(port: int, name: str) -> None:
    value = int(port)
    if not 1 <= value <= 65535:
        raise ValueError("端口必须在 1-65535 之间")
    if not str(name or "").strip():
        raise ValueError("服务名不能为空")
    _ports[value] = str(name).strip()


def get_service_names() -> Dict[int, str]:
    return dict(_ports)


def register_country_name(code: str, name: str) -> None:
    value = str(code or "").strip().upper()
    if not CountryPattern.match(value):
        raise ValueError("国家代码必须是两位字母")
    if not str(name or "").strip():
        raise ValueError("国家名称不能为空")
    _countries[value] = str(name).strip()


def get_country_names() -> Dict[str, str]:
    return dict(_countries)


def configure_ip_lookup_limits(**kwargs: Any) -> IpLookupLimits:
    global _limits
    allowed = set(IpLookupLimits.__dataclass_fields__)
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知配置项: {', '.join(sorted(unknown))}")
    updates = {}
    for key, value in kwargs.items():
        number = float(value)
        if number <= 0:
            raise ValueError(f"{key} 必须为正数")
        updates[key] = int(number) if isinstance(getattr(_limits, key), int) else number
    _limits = replace(_limits, **updates)
    return _limits


def get_ip_lookup_limits() -> IpLookupLimits:
    return _limits


def get_scheme_allowlist() -> Tuple[str, ...]:
    return tuple(sorted(_scheme_allowlist))


def reset_ip_lookup_registry() -> None:
    """仅供测试使用：恢复全部默认注册项与配置。"""
    global _geo_providers, _public_ip_services, _conversions, _asset_actions
    global _suffixes, _ports, _countries, _limits, _scheme_allowlist
    _geo_providers = {item.name: item for item in DEFAULT_GEO_PROVIDERS}
    _public_ip_services = {item.name: item for item in DEFAULT_PUBLIC_IP_SERVICES}
    _conversions = {item.label: item for item in DEFAULT_CONVERSIONS}
    _asset_actions = {item.key: item for item in DEFAULT_ASSET_ACTIONS}
    _suffixes = set(DEFAULT_SUFFIXES)
    _ports = dict(DEFAULT_PORTS)
    _countries = dict(DEFAULT_COUNTRIES)
    _limits = IpLookupLimits()
    _scheme_allowlist = {"http", "https"}
