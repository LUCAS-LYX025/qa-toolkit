"""接口安全测试工具：注册式扩展点。

设计目标（不局限于当前业务）：
- 所有检测规则、词表、OWASP 清单、严重级别、角色等级、状态码分桶、探测策略、
  Nuclei 模板、导出清洗器与运行上限都通过 ``register_*`` / ``get_*`` 暴露；
- 下游项目想新增一条检查（如 Permissions-Policy）、换 OWASP 版本、加自定义
  敏感字段或自定义角色等级，只需调用注册接口，不需要改 core / page 源码；
- frozen dataclass Spec + query 返回副本 + 重复注册需 ``replace=True``，避免
  全局注册表被页面或测试意外污染；``reset_security_registry()`` 保证测试隔离。

与 ``api_performance_registry.py`` 的安全护栏语义保持一致（协议白名单、userinfo
拒绝、端口校验、内网/回环/链路本地/元数据地址拦截、默认关闭重定向、默认开启
SSL 校验），但注册表相互独立，便于各自演进。
"""
from __future__ import annotations

import copy
import ipaddress
import json
import math
import re
import threading
from dataclasses import dataclass, field, replace as _dc_replace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# 数值转换（统一拒绝非有限值 / 畸形输入）
# ---------------------------------------------------------------------------

def to_float(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return float(default)
    if not math.isfinite(number):
        return float(default)
    return number


def to_int(value: Any, default: int = 0) -> int:
    if isinstance(value, bool):
        return int(default)
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return int(default)
    if not math.isfinite(number):
        return int(default)
    return int(number)


def clamp_float(value: Any, default: float, minimum: float, maximum: float) -> float:
    number = to_float(value, default)
    return min(max(number, minimum), maximum)


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    number = to_int(value, default)
    return min(max(number, minimum), maximum)


# ---------------------------------------------------------------------------
# 运行上限与安全默认值
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SecurityLimits:
    max_interfaces: int = 500
    max_roles: int = 20
    max_requests: int = 400
    max_probes_per_interface: int = 4
    max_timeout_seconds: float = 60.0
    min_timeout_seconds: float = 1.0
    max_total_seconds: float = 300.0
    max_response_bytes: int = 512_000
    max_body_preview_chars: int = 1200
    max_sample_preview_chars: int = 800
    max_template_paths: int = 25
    max_sensitive_template_paths: int = 20
    max_playbook_findings: int = 12
    max_error_samples: int = 100
    max_findings_per_group: int = 20
    # 安全默认值
    allow_private_targets: bool = False
    follow_redirects_by_default: bool = False
    verify_ssl_by_default: bool = True
    default_origin: str = "https://security-audit.local"


_LIMITS = SecurityLimits()


def configure_security_limits(**kwargs: Any) -> SecurityLimits:
    """按关键字更新运行上限；未知字段直接报错，避免拼写错误静默失效。"""
    global _LIMITS
    allowed = set(SecurityLimits.__dataclass_fields__)
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知的接口安全测试配置项: {sorted(unknown)}")
    for key, value in kwargs.items():
        if isinstance(value, bool) or isinstance(value, str):
            continue
        if isinstance(value, (int, float)) and (not math.isfinite(float(value)) or float(value) < 0):
            raise ValueError(f"配置项 {key!r} 必须是非负有限数，收到: {value!r}")
    with _LOCK:
        _LIMITS = _dc_replace(_LIMITS, **kwargs)
        return _LIMITS


def get_security_limits() -> SecurityLimits:
    with _LOCK:
        return _LIMITS


# ---------------------------------------------------------------------------
# 协议白名单 / SSRF 护栏 / Header 校验
# ---------------------------------------------------------------------------

_PROTOCOLS: Dict[str, str] = {}
_PRIVATE_NETWORKS = tuple(
    ipaddress.ip_network(cidr)
    for cidr in (
        "0.0.0.0/8", "10.0.0.0/8", "100.64.0.0/10", "127.0.0.0/8",
        "169.254.0.0/16", "172.16.0.0/12", "192.0.0.0/24", "192.0.2.0/24",
        "192.168.0.0/16", "198.18.0.0/15", "198.51.100.0/24", "203.0.113.0/24",
        "224.0.0.0/4", "240.0.0.0/4", "::1/128", "fc00::/7", "fe80::/10",
    )
)
_METADATA_HOSTS = {
    "metadata", "metadata.google.internal", "metadata.goog",
    "instance-data", "169.254.169.254",
}
_HEADER_TOKEN_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def register_protocol(scheme: str, label: str = "", *, replace: bool = False) -> None:
    key = str(scheme or "").strip().lower()
    if not key:
        raise ValueError("协议名不能为空")
    with _LOCK:
        if key in _PROTOCOLS and not replace:
            raise ValueError(f"协议 {key!r} 已注册；如需覆盖请传 replace=True")
        _PROTOCOLS[key] = label or key


def get_protocols() -> Dict[str, str]:
    with _LOCK:
        return dict(_PROTOCOLS)


def _is_private_host(host: str) -> bool:
    text = str(host or "").strip().lower().rstrip(".")
    if not text:
        return True
    if text in {"localhost", "localhost.localdomain"} or text.endswith(".localhost"):
        return True
    if text in _METADATA_HOSTS or text.endswith(".internal") or text.endswith(".local"):
        return True
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    if not address.is_global:
        return True
    return any(address in network for network in _PRIVATE_NETWORKS)


def validate_target_url(url: str, *, allow_private: Optional[bool] = None) -> Tuple[bool, str]:
    """探测前校验目标 URL；返回 (是否合法, 错误原因)。"""
    text = str(url or "").strip()
    if not text:
        return False, "目标 URL 为空"
    if _CONTROL_RE.search(text) or any(ch in text for ch in ("\r", "\n", "\t", " ")):
        return False, "目标 URL 含控制字符或空白"
    parsed = urlparse(text)
    scheme = (parsed.scheme or "").lower()
    allowed = get_protocols()
    if scheme not in allowed:
        return False, f"不支持的协议 {scheme or '(空)'}，仅允许：{'、'.join(sorted(allowed))}"
    if parsed.username or parsed.password:
        return False, "目标 URL 不允许携带 userinfo（用户名/密码）"
    if not parsed.hostname:
        return False, "目标 URL 缺少主机名"
    try:
        port = parsed.port
    except ValueError:
        return False, "目标 URL 端口非法"
    if port is not None and not (1 <= port <= 65535):
        return False, "目标 URL 端口必须在 1-65535"
    allow = get_security_limits().allow_private_targets if allow_private is None else bool(allow_private)
    if not allow and _is_private_host(parsed.hostname):
        return False, "目标为内网/回环/链路本地/元数据地址；如需压测内网服务，请显式开启「允许内网/本地目标」"
    return True, ""


def sanitize_server_name(value: str) -> Tuple[bool, str]:
    text = str(value or "").strip()
    if not text:
        return False, "主机名不能为空"
    if _CONTROL_RE.search(text) or any(ch in text for ch in (" ", "\r", "\n", "@", "/", "\\", "?", "#", ":")):
        return False, "只能填写主机名或 IP，不允许空格、@、路径、端口或协议"
    if _is_private_host(text):
        return False, "主机名指向内网/回环/本地地址，请确认授权范围"
    return True, text


def validate_port_text(value: str) -> Tuple[bool, str]:
    text = str(value or "").strip()
    if not text:
        return True, ""
    if not text.isdigit():
        return False, "端口号必须是 1-65535 的整数"
    port = int(text)
    if not (1 <= port <= 65535):
        return False, "端口号必须是 1-65535 的整数"
    return True, str(port)


def sanitize_header_name(value: Any) -> Tuple[bool, str]:
    name = str(value or "").strip()
    if not name:
        return False, "请求头名不能为空"
    if not _HEADER_TOKEN_RE.match(name):
        return False, f"请求头名 {name!r} 含非法字符（仅允许 RFC 7230 token）"
    return True, name


def sanitize_header_value(value: Any) -> Tuple[bool, str]:
    text = "" if value is None else str(value)
    if _CONTROL_RE.search(text) or "\r" in text or "\n" in text:
        return False, "请求头值含 CRLF 或控制字符，已拒绝"
    if len(text) > 8192:
        return False, "请求头值过长（超过 8192 字符），已拒绝"
    return True, text


def validate_request_headers(headers: Optional[Dict[str, Any]]) -> Tuple[Dict[str, str], List[str]]:
    """返回 (清洗后的请求头, 告警列表)。非法项直接丢弃并告警。"""
    cleaned: Dict[str, str] = {}
    warnings: List[str] = []
    for key, value in (headers or {}).items():
        ok_name, name = sanitize_header_name(key)
        if not ok_name:
            warnings.append(f"已忽略非法请求头名: {name}")
            continue
        ok_value, text = sanitize_header_value(value)
        if not ok_value:
            warnings.append(f"已忽略非法请求头值: {text}（{name}）")
            continue
        cleaned[name] = text
    return cleaned, warnings


def build_probe_headers(
    auth_headers: Optional[Dict[str, Any]],
    origin: str,
    probe_method: str = "",
    original_method: str = "GET",
) -> Tuple[Dict[str, str], List[str]]:
    """统一构造探测请求头：清洗 -> 强制设置 Origin -> OPTIONS 补 ACRM。"""
    cleaned, warnings = validate_request_headers(auth_headers)
    ok_origin, origin_error = sanitize_header_value(origin)
    if not ok_origin:
        warnings.append(f"Origin 非法，已回落到默认值: {origin_error}")
        origin = get_security_limits().default_origin
    cleaned["Origin"] = str(origin or get_security_limits().default_origin).strip()
    if probe_method == "OPTIONS":
        cleaned.setdefault("Access-Control-Request-Method", str(original_method or "GET").upper())
    return cleaned, warnings


# ---------------------------------------------------------------------------
# 词表 / 方法集合（全部可注册）
# ---------------------------------------------------------------------------

_HTTP_METHODS: Dict[str, str] = {}
_MUTATING_METHODS: set = set()
_AUTH_HEADER_NAMES: set = set()
_SENSITIVE_KEYS: Dict[str, str] = {}   # key -> level(high/medium)
_HINTS: Dict[str, set] = {}
_ERROR_MARKERS: set = set()


def register_http_method(method: str, *, mutating: bool = False, replace: bool = False) -> None:
    key = str(method or "").strip().upper()
    if not key:
        raise ValueError("HTTP 方法不能为空")
    with _LOCK:
        if key in _HTTP_METHODS and not replace:
            raise ValueError(f"HTTP 方法 {key!r} 已注册；如需覆盖请传 replace=True")
        _HTTP_METHODS[key] = key
        if mutating:
            _MUTATING_METHODS.add(key)
        elif replace and key in _MUTATING_METHODS:
            _MUTATING_METHODS.discard(key)


def get_http_methods() -> Dict[str, str]:
    with _LOCK:
        return dict(_HTTP_METHODS)


def get_mutating_methods() -> set:
    with _LOCK:
        return set(_MUTATING_METHODS)


def register_auth_header_name(name: str) -> None:
    key = str(name or "").strip().lower()
    if not key:
        raise ValueError("鉴权头名不能为空")
    with _LOCK:
        _AUTH_HEADER_NAMES.add(key)


def get_auth_header_names() -> set:
    with _LOCK:
        return set(_AUTH_HEADER_NAMES)


def register_sensitive_key(key: str, level: str = "medium", *, replace: bool = False) -> None:
    name = str(key or "").strip().lower()
    if not name:
        raise ValueError("敏感字段名不能为空")
    if level not in {"high", "medium"}:
        raise ValueError("敏感级别只能是 high 或 medium")
    with _LOCK:
        if name in _SENSITIVE_KEYS and not replace:
            raise ValueError(f"敏感字段 {name!r} 已注册；如需覆盖请传 replace=True")
        _SENSITIVE_KEYS[name] = level


def get_sensitive_keys(level: Optional[str] = None) -> set:
    with _LOCK:
        if level is None:
            return set(_SENSITIVE_KEYS)
        return {k for k, v in _SENSITIVE_KEYS.items() if v == level}


def register_hint(group: str, value: str) -> None:
    key = str(group or "").strip().lower()
    word = str(value or "").strip().lower()
    if not key or not word:
        raise ValueError("词表分组与词都不能为空")
    with _LOCK:
        _HINTS.setdefault(key, set()).add(word)


def get_hints(group: str) -> set:
    with _LOCK:
        return set(_HINTS.get(str(group or "").strip().lower(), set()))


def register_error_marker(marker: str) -> None:
    word = str(marker or "").strip().lower()
    if word:
        with _LOCK:
            _ERROR_MARKERS.add(word)


def get_error_markers() -> set:
    with _LOCK:
        return set(_ERROR_MARKERS)


# ---------------------------------------------------------------------------
# OWASP 清单（可注册、可替换版本）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class OwaspItemSpec:
    code: str
    title: str
    focus: str
    manual: str
    auto_baseline: bool = False


_OWASP_ITEMS: Dict[str, OwaspItemSpec] = {}


def register_owasp_item(
    code: str, title: str, focus: str, manual: str = "",
    *, auto_baseline: bool = False, replace: bool = False,
) -> None:
    key = str(code or "").strip()
    if not key:
        raise ValueError("OWASP 编号不能为空")
    with _LOCK:
        if key in _OWASP_ITEMS and not replace:
            raise ValueError(f"OWASP 项 {key!r} 已注册；如需覆盖请传 replace=True")
        _OWASP_ITEMS[key] = OwaspItemSpec(key, title, focus, manual or "建议结合业务场景做人机协同复核。", auto_baseline)


def get_owasp_items() -> List[OwaspItemSpec]:
    with _LOCK:
        return [copy.copy(item) for item in _OWASP_ITEMS.values()]


def get_manual_validation_text(code: str) -> str:
    with _LOCK:
        item = _OWASP_ITEMS.get(str(code or "").strip())
        return item.manual if item else "建议结合业务场景做人机协同复核。"


def match_owasp_codes(value: Any) -> List[str]:
    """支持一条 finding 标注多个 OWASP 编号（逗号/分号/空格分隔）。"""
    text = str(value or "")
    parts = re.split(r"[,;/\s]+", text)
    with _LOCK:
        return [part for part in parts if part and part in _OWASP_ITEMS]


# ---------------------------------------------------------------------------
# 严重级别 / 角色等级 / 状态码分桶 / 优先级
# ---------------------------------------------------------------------------

_SEVERITY_ORDER: Dict[str, int] = {}
_ROLE_RANKS: List[Tuple[str, int]] = []
_STATUS_BUCKETS: List[Tuple[Callable[[int], bool], str]] = []
_PRIORITY_MAP: Dict[str, str] = {}


def register_severity(name: str, rank: int, *, replace: bool = False) -> None:
    key = str(name or "").strip().lower()
    with _LOCK:
        if key in _SEVERITY_ORDER and not replace:
            raise ValueError(f"严重级别 {key!r} 已注册；如需覆盖请传 replace=True")
        _SEVERITY_ORDER[key] = int(rank)


def get_severity_order() -> Dict[str, int]:
    with _LOCK:
        return dict(_SEVERITY_ORDER)


def severity_rank(severity: Any) -> int:
    with _LOCK:
        return _SEVERITY_ORDER.get(str(severity or "info").strip().lower(), 99)


def top_severity(findings: Sequence[Dict[str, Any]]) -> str:
    if not findings:
        return "none"
    return min((str(item.get("Severity", "info")).lower() for item in findings), key=severity_rank)


def register_role_rank(keyword: str, rank: int) -> None:
    word = str(keyword or "").strip().lower()
    if not word:
        raise ValueError("角色关键字不能为空")
    with _LOCK:
        _ROLE_RANKS.append((word, int(rank)))
        _ROLE_RANKS.sort(key=lambda item: -len(item[0]))


def get_role_ranks() -> List[Tuple[str, int]]:
    with _LOCK:
        return list(_ROLE_RANKS)


def role_rank(role: Any) -> int:
    blob = str(role or "").lower()
    with _LOCK:
        for keyword, rank in _ROLE_RANKS:
            if keyword in blob:
                return rank
    return 2


def register_status_bucket(name: str, predicate: Callable[[int], bool]) -> None:
    with _LOCK:
        _STATUS_BUCKETS.append((str(name), predicate))


def status_bucket(status_code: Any) -> str:
    code = to_int(status_code, 0)
    with _LOCK:
        buckets = list(_STATUS_BUCKETS)
    for name, predicate in buckets:
        try:
            if predicate(code):
                return name
        except Exception:
            continue
    return "other"


def register_priority(severity: str, priority: str, *, replace: bool = False) -> None:
    key = str(severity or "").strip().lower()
    with _LOCK:
        if key in _PRIORITY_MAP and not replace:
            raise ValueError(f"优先级映射 {key!r} 已注册；如需覆盖请传 replace=True")
        _PRIORITY_MAP[key] = priority


def priority_from_severity(severity: Any) -> str:
    with _LOCK:
        return _PRIORITY_MAP.get(str(severity or "info").strip().lower(), "P3")


# ---------------------------------------------------------------------------
# 套件名 / 期望文案 / 结果字段 / 页签 / 摘要指标
# ---------------------------------------------------------------------------

_SUITE_NAMES: Dict[str, str] = {}
_EXPECTED_TEXTS: Dict[str, str] = {}
_RESULT_TABS: Dict[str, str] = {}
_SUMMARY_METRICS: Dict[str, str] = {}


def register_suite_name(category: str, suite: str, *, replace: bool = False) -> None:
    key = str(category or "").strip()
    with _LOCK:
        if key in _SUITE_NAMES and not replace:
            raise ValueError(f"套件映射 {key!r} 已注册；如需覆盖请传 replace=True")
        _SUITE_NAMES[key] = suite


def get_suite_name(category: Any) -> str:
    with _LOCK:
        return _SUITE_NAMES.get(str(category or "").strip(), "通用安全回归")


def register_expected_text(category: str, text: str, *, replace: bool = False) -> None:
    key = str(category or "").strip()
    with _LOCK:
        if key in _EXPECTED_TEXTS and not replace:
            raise ValueError(f"期望文案 {key!r} 已注册；如需覆盖请传 replace=True")
        _EXPECTED_TEXTS[key] = text


def get_expected_text(category: Any) -> str:
    with _LOCK:
        return _EXPECTED_TEXTS.get(str(category or "").strip(), "按安全基线和业务权限预期通过复测")


def register_result_tab(key: str, label: str, *, replace: bool = False) -> None:
    with _LOCK:
        if key in _RESULT_TABS and not replace:
            raise ValueError(f"结果页签 {key!r} 已注册；如需覆盖请传 replace=True")
        _RESULT_TABS[key] = label


def get_result_tabs() -> List[Tuple[str, str]]:
    with _LOCK:
        return list(_RESULT_TABS.items())


def register_summary_metric(key: str, label: str, *, replace: bool = False) -> None:
    with _LOCK:
        if key in _SUMMARY_METRICS and not replace:
            raise ValueError(f"摘要指标 {key!r} 已注册；如需覆盖请传 replace=True")
        _SUMMARY_METRICS[key] = label


def get_summary_metrics() -> List[Tuple[str, str]]:
    with _LOCK:
        return list(_SUMMARY_METRICS.items())


def build_text_summary(summary: Dict[str, Any], prefix: str = "本轮共") -> str:
    """生成可读的中文文字摘要（页签与报告共用），由摘要指标注册项驱动。"""
    parts = []
    with _LOCK:
        metrics = list(_SUMMARY_METRICS.items())
    for key, label in metrics:
        if key in summary:
            parts.append(f"{label} {summary.get(key, 0)}")
    if not parts:
        return "当前没有可用的汇总数据。"
    return f"{prefix} " + "、".join(parts) + "。"


# ---------------------------------------------------------------------------
# 探测方法策略
# ---------------------------------------------------------------------------

_PROBE_STRATEGIES: Dict[str, Callable[[str], List[str]]] = {}


def register_probe_strategy(key: str, builder: Callable[[str], List[str]], *, replace: bool = False) -> None:
    with _LOCK:
        if key in _PROBE_STRATEGIES and not replace:
            raise ValueError(f"探测策略 {key!r} 已注册；如需覆盖请传 replace=True")
        _PROBE_STRATEGIES[key] = builder


def get_probe_methods(method: Any, strategy: str = "safe_baseline") -> List[str]:
    name = str(method or "GET").upper()
    with _LOCK:
        builder = _PROBE_STRATEGIES.get(strategy)
    if builder is None:
        builder = lambda m: ["OPTIONS"]  # noqa: E731
    try:
        result = [str(item).upper() for item in builder(name)]
    except Exception:
        result = ["OPTIONS"]
    limits = get_security_limits()
    return result[: max(1, limits.max_probes_per_interface)]


def get_probe_strategy_labels() -> Dict[str, str]:
    with _LOCK:
        return {key: key for key in _PROBE_STRATEGIES}


# ---------------------------------------------------------------------------
# 被动审计规则（可注册）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PassiveRuleSpec:
    key: str
    category: str
    label: str
    evaluator: Callable[[Dict[str, Any], str, str], List[Dict[str, Any]]]


_PASSIVE_RULES: Dict[str, PassiveRuleSpec] = {}


def register_passive_rule(
    key: str, category: str, label: str,
    evaluator: Callable[[Dict[str, Any], str, str], List[Dict[str, Any]]],
    *, replace: bool = False,
) -> None:
    with _LOCK:
        if key in _PASSIVE_RULES and not replace:
            raise ValueError(f"被动审计规则 {key!r} 已注册；如需覆盖请传 replace=True")
        _PASSIVE_RULES[key] = PassiveRuleSpec(key, category, label, evaluator)


def get_passive_rules() -> List[PassiveRuleSpec]:
    with _LOCK:
        return [copy.copy(item) for item in _PASSIVE_RULES.values()]


def evaluate_passive_rules(item: Dict[str, Any], label: str, full_url: str) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    with _LOCK:
        rules = list(_PASSIVE_RULES.values())
    for rule in rules:
        try:
            findings.extend(rule.evaluator(item, label, full_url) or [])
        except Exception as exc:  # 单条规则异常不影响整体审计
            findings.append({
                "Severity": "info", "Category": "rule_error",
                "Title": f"被动审计规则 {rule.key} 执行失败", "Target": label,
                "Evidence": f"{type(exc).__name__}: {exc}",
                "Recommendation": "检查规则实现或接口文档结构，必要时停用该规则。",
                "OWASP": "API9:2023",
            })
    return findings


def _rule_transport(item, label, full_url):
    if str(full_url).startswith("http://"):
        return [{"Severity": "high", "Category": "transport", "Title": "接口作用域使用明文 HTTP",
                 "Evidence": full_url,
                 "Recommendation": "生产或准生产接口建议统一使用 HTTPS，并确认网关强制跳转和 HSTS 策略。",
                 "OWASP": "API8:2023"}]
    return []


def _rule_auth_review(item, label, full_url):
    method = str(item.get("method") or "GET").upper()
    if method in get_mutating_methods() and not _has_visible_auth(item.get("headers", {})):
        return [{"Severity": "medium", "Category": "auth_review", "Title": "变更类接口未在文档中体现鉴权信息",
                 "Evidence": "请求头中未发现 Authorization/Cookie/API Key 一类的显式鉴权线索。",
                 "Recommendation": "确认该接口是否通过网关、签名、环境默认头或会话态进行保护，并在测试计划中覆盖 401/403 场景。",
                 "OWASP": "API5:2023"}]
    return []


def _rule_admin_review(item, label, full_url):
    blob = _interface_blob(item)
    if any(hint in blob for hint in get_hints("admin")) and not _has_visible_auth(item.get("headers", {})):
        return [{"Severity": "high", "Category": "admin_review", "Title": "管理/内部接口缺少显式鉴权提示",
                 "Evidence": str(item.get("path") or ""),
                 "Recommendation": "优先验证角色鉴权、功能级授权和环境隔离，避免内部接口被普通账号调用。",
                 "OWASP": "API5:2023"}]
    return []


def match_sensitive_keys(*mapping_groups: Dict[str, Any]) -> List[str]:
    hits = []
    keys = get_sensitive_keys()
    for mapping in mapping_groups:
        for key in (mapping or {}).keys():
            if str(key).strip().lower() in keys:
                hits.append(str(key))
    return sorted(set(hits))


def _rule_sensitive_url(item, label, full_url):
    hits = match_sensitive_keys(item.get("query_params", {}), item.get("path_params", {}))
    if hits:
        return [{"Severity": "medium", "Category": "sensitive_url", "Title": "URL 中出现敏感参数",
                 "Evidence": ", ".join(hits),
                 "Recommendation": "避免把口令、Token、Session、密钥等敏感数据放入 path/query，优先改为安全头或请求体。",
                 "OWASP": "API8:2023"}]
    return []


def detect_sensitive_response(value: Any) -> Dict[str, List[str]]:
    keys = _extract_keys(value)
    return {
        "high_hits": sorted({k for k in keys if k.lower() in get_sensitive_keys("high")}),
        "medium_hits": sorted({k for k in keys if k.lower() in get_sensitive_keys("medium")}),
    }


def _rule_sensitive_response(item, label, full_url):
    hits = detect_sensitive_response(item.get("expected_response"))
    if hits["high_hits"] or hits["medium_hits"]:
        return [{"Severity": "high" if hits["high_hits"] else "medium",
                 "Category": "sensitive_response", "Title": "响应样例包含敏感字段",
                 "Evidence": ", ".join(hits["high_hits"] + hits["medium_hits"]),
                 "Recommendation": "复核这些字段是否应脱敏、按角色裁剪，或仅在服务端内部保留。",
                 "OWASP": "API3:2023"}]
    return []


def find_error_leaks(value: Any) -> List[str]:
    blob = _to_text(value).lower()
    return sorted(marker for marker in get_error_markers() if marker in blob)


def _rule_error_leak(item, label, full_url):
    hits = find_error_leaks(item.get("expected_response"))
    if hits:
        return [{"Severity": "medium", "Category": "error_leak",
                 "Title": "响应样例存在错误栈/调试信息泄露迹象", "Evidence": ", ".join(hits[:5]),
                 "Recommendation": "建议统一错误码和错误文案输出，不返回堆栈、SQL 语句、框架路径或调试上下文。",
                 "OWASP": "API8:2023"}]
    return []


def _rule_upload_review(item, label, full_url):
    blob = _interface_blob(item)
    if any(hint in blob for hint in get_hints("file")):
        validation_blob = " ".join([
            str(item.get("description") or ""),
            json.dumps(item.get("body", ""), ensure_ascii=False, default=str),
            json.dumps(item.get("headers", {}), ensure_ascii=False, default=str),
        ]).lower()
        if not any(hint in validation_blob for hint in get_hints("upload_validation")):
            return [{"Severity": "low", "Category": "upload_review", "Title": "上传接口未体现类型/大小校验要求",
                     "Evidence": str(item.get("description") or item.get("path") or ""),
                     "Recommendation": "建议补充 MIME、扩展名、大小、病毒扫描和存储隔离等校验要求。",
                     "OWASP": "API8:2023"}]
    return []


def _rule_ssrf_review(item, label, full_url):
    hits = []
    hints = get_hints("ssrf")
    for mapping in [item.get("query_params", {}), item.get("path_params", {})]:
        for key in (mapping or {}).keys():
            if str(key).strip().lower() in hints:
                hits.append(str(key))
    body = item.get("body")
    if isinstance(body, dict):
        for key in body.keys():
            if str(key).strip().lower() in hints:
                hits.append(str(key))
    if hits:
        return [{"Severity": "medium", "Category": "ssrf_review",
                 "Title": "接口存在 URL/回调类参数，需要做 SSRF 审计", "Evidence": ", ".join(sorted(set(hits))),
                 "Recommendation": "重点复核协议白名单、域名/IP 限制、重定向跟随、内网地址访问和 DNS 重绑定防护。",
                 "OWASP": "API7:2023"}]
    return []


def _rule_resource_control(item, label, full_url):
    blob = _interface_blob(item)
    if str(item.get("method") or "GET").upper() == "GET" and any(h in blob for h in get_hints("list")):
        query_keys = {str(k).strip().lower() for k in (item.get("query_params") or {}).keys()}
        control_blob = " ".join([
            str(item.get("description") or ""),
            json.dumps(item.get("headers", {}), ensure_ascii=False, default=str),
        ]).lower()
        if not (query_keys & get_hints("pagination")) and not any(h in control_blob for h in get_hints("resource_control")):
            return [{"Severity": "low", "Category": "resource_control",
                     "Title": "批量/列表接口未体现分页或资源控制线索", "Evidence": str(item.get("path") or ""),
                     "Recommendation": "建议补充分页、限流、速率限制、批量大小和导出权限控制要求。",
                     "OWASP": "API4:2023"}]
    return []


def _rule_inventory(item, label, full_url):
    if not str(item.get("description") or "").strip():
        return [{"Severity": "info", "Category": "inventory", "Title": "接口缺少描述信息",
                 "Evidence": str(item.get("path") or ""),
                 "Recommendation": "建议补齐接口用途、所属系统、鉴权方式和废弃状态，便于清单治理和安全回归。",
                 "OWASP": "API9:2023"}]
    return []


def _interface_blob(item: Dict[str, Any]) -> str:
    return " ".join(str(item.get(key) or "") for key in ("name", "description", "path", "method")).lower()


def _extract_keys(value: Any) -> List[str]:
    keys: List[str] = []
    if isinstance(value, dict):
        for key, item in value.items():
            keys.append(str(key))
            keys.extend(_extract_keys(item))
    elif isinstance(value, list):
        for item in value:
            keys.extend(_extract_keys(item))
    return keys


def _to_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, ensure_ascii=False)
    except Exception:
        return str(value)


def _has_visible_auth(interface_headers: Dict[str, Any], extra_headers: Optional[Dict[str, Any]] = None) -> bool:
    combined: Dict[str, Any] = {}
    combined.update(interface_headers or {})
    combined.update(extra_headers or {})
    names = {str(key).strip().lower() for key in combined.keys()}
    return bool(names & get_auth_header_names())


def has_visible_auth(interface_headers: Dict[str, Any], extra_headers: Optional[Dict[str, Any]] = None) -> bool:
    """公开给 core 使用。"""
    return _has_visible_auth(interface_headers, extra_headers)


def looks_sensitive_runtime_target(label: str, url: str) -> bool:
    blob = f"{label} {url}".lower()
    return any(hint in blob for hint in get_hints("admin") | get_hints("cache"))


def interface_blob(item: Dict[str, Any]) -> str:
    return _interface_blob(item)


def has_object_reference(item: Dict[str, Any]) -> bool:
    path = str(item.get("path") or "").lower()
    path_params = {str(k).lower() for k in (item.get("path_params") or {}).keys()}
    query_params = {str(k).lower() for k in (item.get("query_params") or {}).keys()}
    if "{" in path and "}" in path:
        return True
    hints = get_hints("object_id")
    return any(key in hints or key.endswith("_id") for key in (path_params | query_params))


def looks_public_endpoint(item: Dict[str, Any]) -> bool:
    return any(h in _interface_blob(item) for h in get_hints("public"))


def looks_admin_endpoint(item: Dict[str, Any]) -> bool:
    return any(h in _interface_blob(item) for h in get_hints("admin"))


def looks_business_endpoint(item: Dict[str, Any]) -> bool:
    return any(h in _interface_blob(item) for h in get_hints("business"))


# ---------------------------------------------------------------------------
# 基线探测规则（可注册）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ProbeContext:
    headers: Dict[str, str]
    lower_headers: Dict[str, str]
    status_code: int
    body_preview: str
    url: str
    label: str
    probe_method: str
    original_method: str
    auth_provided: bool

    def header(self, name: str) -> str:
        """大小写不敏感地取响应头值，避免 HTTP/2 小写头导致证据为空。"""
        key = str(name).strip().lower()
        if key in self.lower_headers:
            return self.lower_headers[key]
        for raw_key, value in self.headers.items():
            if str(raw_key).strip().lower() == key:
                return str(value)
        return ""


@dataclass(frozen=True)
class ProbeRuleSpec:
    key: str
    category: str
    label: str
    evaluator: Callable[[ProbeContext], List[Dict[str, Any]]]


_PROBE_RULES: Dict[str, ProbeRuleSpec] = {}


def register_probe_rule(
    key: str, category: str, label: str,
    evaluator: Callable[[ProbeContext], List[Dict[str, Any]]],
    *, replace: bool = False,
) -> None:
    with _LOCK:
        if key in _PROBE_RULES and not replace:
            raise ValueError(f"基线探测规则 {key!r} 已注册；如需覆盖请传 replace=True")
        _PROBE_RULES[key] = ProbeRuleSpec(key, category, label, evaluator)


def get_probe_rules() -> List[ProbeRuleSpec]:
    with _LOCK:
        return [copy.copy(item) for item in _PROBE_RULES.values()]


def evaluate_probe_rules(ctx: ProbeContext) -> List[Dict[str, Any]]:
    findings: List[Dict[str, Any]] = []
    with _LOCK:
        rules = list(_PROBE_RULES.values())
    for rule in rules:
        try:
            findings.extend(rule.evaluator(ctx) or [])
        except Exception as exc:
            findings.append({
                "Severity": "info", "Category": "rule_error",
                "Title": f"基线探测规则 {rule.key} 执行失败", "Target": ctx.label,
                "Evidence": f"{type(exc).__name__}: {exc}",
                "Recommendation": "检查规则实现或响应结构，必要时停用该规则。",
                "OWASP": "API8:2023",
            })
    return findings


def _f(severity, category, title, ctx, evidence, recommendation, owasp):
    return {"Severity": severity, "Category": category, "Title": title,
            "Target": ctx.label, "Evidence": evidence, "Recommendation": recommendation,
            "OWASP": owasp}


def _pr_transport(ctx):
    if urlparse(ctx.url).scheme == "http":
        return [_f("high", "transport", "基线探测发现目标使用 HTTP", ctx, ctx.url,
                   "建议统一走 HTTPS，并在网关层配置 301/308 跳转和 HSTS。", "API8:2023")]
    return []


def _pr_hsts(ctx):
    if urlparse(ctx.url).scheme == "https" and "strict-transport-security" not in ctx.lower_headers:
        return [_f("medium", "headers", "缺少 HSTS", ctx, f"{ctx.probe_method} {ctx.url}",
                   "建议在 HTTPS 响应中下发 Strict-Transport-Security，避免降级和首次访问劫持。", "API8:2023")]
    return []


def _pr_xcto(ctx):
    if "x-content-type-options" not in ctx.lower_headers:
        return [_f("low", "headers", "缺少 X-Content-Type-Options", ctx, f"{ctx.probe_method} {ctx.url}",
                   "建议返回 X-Content-Type-Options: nosniff，降低 MIME 混淆风险。", "API8:2023")]
    return []


def _pr_csp(ctx):
    if "text/html" in ctx.header("Content-Type").lower() and "content-security-policy" not in ctx.lower_headers:
        return [_f("low", "headers", "HTML 响应缺少 Content-Security-Policy", ctx, f"{ctx.probe_method} {ctx.url}",
                   "如果接口网关或门户返回 HTML，建议评估 CSP、frame-ancestors 等前端安全策略。", "API8:2023")]
    return []


def _pr_cors(ctx):
    origin = ctx.header("Access-Control-Allow-Origin").strip()
    credentials = ctx.header("Access-Control-Allow-Credentials").strip().lower()
    trusted = get_hints("cors_trusted")
    if not origin or origin.lower() in trusted:
        return []
    low = origin.lower()
    evidence = f"Access-Control-Allow-Origin={origin}"
    if credentials == "true":
        evidence += " 且 Allow-Credentials=true"
    if low in {"*", "null"}:
        severity = "high" if credentials == "true" else "medium"
        title = "CORS 配置存在高风险通配/反射" if severity == "high" else "CORS 允许任意/不可信来源"
        recommendation = "建议改为精确白名单并避免和凭证同时使用通配或 null 来源。"
    else:
        # 精确格式但不在白名单：可能是反射了请求的 Origin，同样需要提示。
        severity = "high" if credentials == "true" else "medium"
        title = "CORS 反射了非白名单来源"
        recommendation = "确认服务端是否按白名单校验 Origin；反射任意来源会放大跨域数据泄露风险。"
    return [_f(severity, "cors", title, ctx, evidence, recommendation, "API8:2023")]


def _is_exact_origin(value: str) -> bool:
    parsed = urlparse(str(value or "").strip())
    return parsed.scheme in get_protocols() and bool(parsed.hostname)


def _pr_methods(ctx):
    allow = ctx.header("Allow")
    if "trace" in allow.lower():
        return [_f("high", "methods", "Allow 头暴露 TRACE 方法", ctx, allow,
                   "建议关闭 TRACE 等不必要方法，并仅暴露接口实际需要的 HTTP 方法。", "API8:2023")]
    return []


def _pr_fingerprint(ctx):
    out = []
    for header_name, title in (("Server", "Server 头暴露服务指纹"), ("X-Powered-By", "X-Powered-By 暴露技术栈")):
        value = ctx.header(header_name)
        if value:
            out.append(_f("info", "fingerprint", title, ctx, value,
                          f"建议移除或弱化 {header_name} 等服务端指纹响应头。", "API8:2023"))
    return out


def _pr_cookie(ctx):
    raw = ctx.header("Set-Cookie")
    if not raw:
        return []
    cookies = _split_set_cookie(raw)
    missing = []
    for cookie in cookies:
        low = cookie.lower()
        absent = [flag for flag in ("secure", "httponly", "samesite") if flag not in low]
        if absent:
            name = cookie.split("=", 1)[0].strip() or "(匿名)"
            missing.append(f"{name}: 缺 {'/'.join(x.capitalize() for x in absent)}")
    if missing:
        return [_f("medium", "cookie", "Cookie 安全属性不完整", ctx, "; ".join(missing[:5]),
                   "对会话 Cookie 建议至少补齐 Secure、HttpOnly 和 SameSite 属性。", "API8:2023")]
    return []


def _split_set_cookie(raw: str) -> List[str]:
    """按逗号拆分合并的 Set-Cookie，但不破坏 Expires 里的逗号日期。"""
    parts = []
    current = ""
    for chunk in str(raw).split(","):
        candidate = (current + "," + chunk).strip() if current else chunk.strip()
        if re.search(r"(?i)expires\s*=\s*[A-Za-z]{3},", candidate) and not re.search(r"(?i)expires\s*=\s*[A-Za-z]{3},\s*\d", candidate):
            current = candidate
            continue
        parts.append(candidate)
        current = ""
    if current:
        parts.append(current)
    return [p for p in parts if p]


def _pr_error_leak(ctx):
    hits = find_error_leaks(ctx.body_preview)
    if hits:
        return [_f("medium", "error_leak", "响应体存在错误泄露迹象", ctx, ", ".join(hits[:5]),
                   "建议统一错误处理和错误码输出，不向调用方暴露调试栈、SQL 语句或内部类名。", "API8:2023")]
    return []


def _pr_auth_runtime(ctx):
    if not ctx.auth_provided and ctx.status_code < 400 and looks_sensitive_runtime_target(ctx.label, ctx.url):
        return [_f("medium", "auth_runtime_review", "敏感接口在未显式携带鉴权头时可访问，需要人工复核", ctx,
                   f"{ctx.probe_method} {ctx.url} -> {ctx.status_code}",
                   "请人工确认该接口是否本应公开；如果不是，建议补测匿名/低权限用户下的 401/403 场景。", "API1:2023")]
    return []


def _pr_cache_review(ctx):
    if ctx.status_code < 400 and looks_sensitive_runtime_target(ctx.label, ctx.url) and "cache-control" not in ctx.lower_headers:
        return [_f("low", "cache_review", "敏感接口未体现缓存控制头", ctx, f"{ctx.probe_method} {ctx.url}",
                   "建议对认证、用户、Token、个人资料等接口评估 Cache-Control/Pragma/Expires 策略。", "API8:2023")]
    return []


# ---------------------------------------------------------------------------
# Nuclei 模板（可注册）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class NucleiTemplateSpec:
    key: str
    file_name: str
    name: str
    builder: Callable[[List[str], str, List[Dict[str, str]]], str]


_NUCLEI_TEMPLATES: Dict[str, NucleiTemplateSpec] = {}


def register_nuclei_template(
    key: str, file_name: str, name: str,
    builder: Callable[[List[str], str, List[Dict[str, str]]], str],
    *, replace: bool = False,
) -> None:
    with _LOCK:
        if key in _NUCLEI_TEMPLATES and not replace:
            raise ValueError(f"Nuclei 模板 {key!r} 已注册；如需覆盖请传 replace=True")
        _NUCLEI_TEMPLATES[key] = NucleiTemplateSpec(key, file_name, name, builder)


def get_nuclei_templates() -> List[NucleiTemplateSpec]:
    with _LOCK:
        return [copy.copy(item) for item in _NUCLEI_TEMPLATES.values()]


def yaml_quote(value: Any) -> str:
    return (str(value)
            .replace("\\", "\\\\")
            .replace('"', '\\"')
            .replace("\n", "\\n")
            .replace("\r", "\\r")
            .replace("\t", "\\t"))


def normalize_template_path(path: Any) -> str:
    text = str(path or "/").strip() or "/"
    text = text.replace("\r", " ").replace("\n", " ")
    if text.startswith(("http://", "https://")):
        parsed = urlparse(text)
        text = parsed.path or "/"
        if parsed.query:
            text += f"?{parsed.query}"
    if not text.startswith("/"):
        text = "/" + text.lstrip("/")
    return text


def build_template_header_variables(auth_headers: Dict[str, Any]) -> List[Dict[str, str]]:
    """header 名做白名单校验，变量名带序号保证唯一。"""
    variables = []
    used: Dict[str, int] = {}
    for raw_key in (auth_headers or {}).keys():
        ok, name = sanitize_header_name(raw_key)
        if not ok:
            continue
        normalized = "".join(ch.lower() if ch.isascii() and ch.isalnum() else "_" for ch in name)
        normalized = re.sub(r"_+", "_", normalized).strip("_") or "custom_header"
        used[normalized] = used.get(normalized, 0) + 1
        variable = f"auth_{normalized}" if used[normalized] == 1 else f"auth_{normalized}_{used[normalized]}"
        variables.append({"header": name, "variable": variable, "value": f"<fill-{normalized}>"})
    return variables


def _nuclei_headers_template(paths, origin, header_variables):
    lines = ["id: api-security-headers-baseline", "", "info:",
             "  name: API Security Headers Baseline", "  author: test-toolkit",
             "  severity: info",
             "  description: Safe baseline checks for missing HSTS, missing X-Content-Type-Options and banner leakage.",
             "  tags: api,security,baseline,headers", "", "variables:",
             f'  audit_origin: "{yaml_quote(origin or get_security_limits().default_origin)}"']
    for item in header_variables:
        lines.append(f'  {item["variable"]}: "{yaml_quote(item["value"])}"')
    lines.extend(["", "http:", "  - method: GET", "    path:"])
    for path in paths:
        lines.append(f'      - "{{{{BaseURL}}}}{normalize_template_path(path)}"')
    lines.extend(["    headers:", '      Accept: "application/json, text/plain, */*"',
                  '      Origin: "{{audit_origin}}"'])
    for item in header_variables:
        lines.append(f'      {item["header"]}: "{{{{{item["variable"]}}}}}"')
    lines.extend(["    stop-at-first-match: false", "    matchers-condition: or", "    matchers:",
                  "      - type: dsl", "        name: missing-hsts", "        dsl:",
                  "          - '!contains(tolower(all_headers), \"strict-transport-security\")'",
                  "      - type: dsl", "        name: missing-x-content-type-options", "        dsl:",
                  "          - '!contains(tolower(all_headers), \"x-content-type-options\")'",
                  "      - type: dsl", "        name: tech-banner", "        dsl:",
                  "          - 'contains(tolower(all_headers), \"server:\") || contains(tolower(all_headers), \"x-powered-by:\")'"])
    return "\n".join(lines)


def _nuclei_options_template(paths, origin, header_variables):
    lines = ["id: api-cors-methods-exposure", "", "info:",
             "  name: API CORS And Method Exposure", "  author: test-toolkit",
             "  severity: info",
             "  description: Safe baseline checks for wildcard/null CORS and exposed TRACE/unsafe methods.",
             "  tags: api,security,cors,methods", "", "variables:",
             f'  audit_origin: "{yaml_quote(origin or get_security_limits().default_origin)}"']
    for item in header_variables:
        lines.append(f'  {item["variable"]}: "{yaml_quote(item["value"])}"')
    lines.extend(["", "http:", "  - method: OPTIONS", "    path:"])
    for path in paths:
        lines.append(f'      - "{{{{BaseURL}}}}{normalize_template_path(path)}"')
    lines.extend(["    headers:", '      Origin: "{{audit_origin}}"',
                  '      Access-Control-Request-Method: "GET"'])
    for item in header_variables:
        lines.append(f'      {item["header"]}: "{{{{{item["variable"]}}}}}"')
    lines.extend(["    stop-at-first-match: false", "    matchers-condition: or", "    matchers:",
                  "      - type: dsl", "        name: cors-wildcard-with-creds", "        dsl:",
                  "          - 'contains(tolower(all_headers), \"access-control-allow-origin: *\") && contains(tolower(all_headers), \"access-control-allow-credentials: true\")'",
                  "      - type: dsl", "        name: cors-null-origin", "        dsl:",
                  "          - 'contains(tolower(all_headers), \"access-control-allow-origin: null\")'",
                  "      - type: dsl", "        name: trace-enabled", "        dsl:",
                  "          - 'contains(tolower(all_headers), \"allow:\") && contains(tolower(all_headers), \"trace\")'"])
    return "\n".join(lines)


def _nuclei_cache_template(paths, origin, header_variables):
    lines = ["id: api-sensitive-cache-review", "", "info:",
             "  name: API Sensitive Cache Review", "  author: test-toolkit",
             "  severity: info",
             "  description: Safe baseline checks for sensitive surfaces missing cache-control guidance or returning debug markers.",
             "  tags: api,security,cache,sensitive", "", "variables:",
             f'  audit_origin: "{yaml_quote(origin or get_security_limits().default_origin)}"']
    for item in header_variables:
        lines.append(f'  {item["variable"]}: "{yaml_quote(item["value"])}"')
    lines.extend(["", "http:", "  - method: GET", "    path:"])
    for path in paths:
        lines.append(f'      - "{{{{BaseURL}}}}{normalize_template_path(path)}"')
    lines.extend(["    headers:", '      Accept: "application/json, text/plain, */*"',
                  '      Origin: "{{audit_origin}}"'])
    for item in header_variables:
        lines.append(f'      {item["header"]}: "{{{{{item["variable"]}}}}}"')
    lines.extend(["    stop-at-first-match: false", "    matchers-condition: or", "    matchers:",
                  "      - type: dsl", "        name: missing-cache-control", "        dsl:",
                  "          - '!contains(tolower(all_headers), \"cache-control\")'",
                  "      - type: dsl", "        name: debug-marker", "        dsl:",
                  "          - 'contains(tolower(body), \"traceback\") || contains(tolower(body), \"stack trace\") || contains(tolower(body), \"exception\")'"])
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 导出清洗与统一 payload
# ---------------------------------------------------------------------------

_EXPORT_SANITIZERS: List[Tuple[str, Callable[[Any], Any]]] = []


def register_export_sanitizer(key: str, sanitizer: Callable[[Any], Any]) -> None:
    with _LOCK:
        _EXPORT_SANITIZERS.append((key, sanitizer))


def _csv_formula_guard(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


def sanitize_csv_value(value: Any) -> Any:
    result = value
    with _LOCK:
        sanitizers = list(_EXPORT_SANITIZERS)
    for _, sanitizer in sanitizers:
        try:
            result = sanitizer(result)
        except Exception:
            continue
    return result


def sanitize_export_rows(rows: Any) -> Any:
    """对 list[dict] / dict 递归应用 CSV 清洗，供页面统一调用。"""
    if isinstance(rows, list):
        return [sanitize_export_rows(item) for item in rows]
    if isinstance(rows, dict):
        return {key: sanitize_csv_value(value) if isinstance(value, (str, int, float)) else sanitize_export_rows(value)
                for key, value in rows.items()}
    return sanitize_csv_value(rows)


def build_export_payload(bundle: Dict[str, Any], *, config_snapshot: Optional[Dict[str, Any]] = None,
                         generated_at: str = "") -> Dict[str, Any]:
    """统一下载 payload：所有导出项从同一份数据派生，字段口径一致、可复现归档。"""
    payload = copy.deepcopy(bundle or {})
    payload["config_snapshot"] = copy.deepcopy(config_snapshot or {})
    payload["input_signature"] = str((config_snapshot or {}).get("input_signature", ""))
    if generated_at:
        payload["exported_at"] = generated_at
    payload["registry_summary"] = get_registry_summary()
    return payload


# ---------------------------------------------------------------------------
# 能力摘要（页面首屏展示）
# ---------------------------------------------------------------------------

def get_registry_summary() -> Dict[str, Any]:
    with _LOCK:
        return {
            "HTTP 方法": len(_HTTP_METHODS),
            "鉴权头名": len(_AUTH_HEADER_NAMES),
            "敏感字段": len(_SENSITIVE_KEYS),
            "词表分组": len(_HINTS),
            "错误标记": len(_ERROR_MARKERS),
            "OWASP 条目": len(_OWASP_ITEMS),
            "被动审计规则": len(_PASSIVE_RULES),
            "基线探测规则": len(_PROBE_RULES),
            "Nuclei 模板": len(_NUCLEI_TEMPLATES),
            "结果页签": len(_RESULT_TABS),
            "摘要指标": len(_SUMMARY_METRICS),
            "协议白名单": ", ".join(sorted(_PROTOCOLS)) or "无",
            "默认校验 SSL": str(_LIMITS.verify_ssl_by_default),
            "默认跟随重定向": str(_LIMITS.follow_redirects_by_default),
            "默认允许内网目标": str(_LIMITS.allow_private_targets),
            "最大接口数": _LIMITS.max_interfaces,
            "最大角色数": _LIMITS.max_roles,
            "最大请求数": _LIMITS.max_requests,
        }


# ---------------------------------------------------------------------------
# 默认注册
# ---------------------------------------------------------------------------

def _bootstrap_defaults() -> None:
    for scheme in ("http", "https"):
        register_protocol(scheme)
    for method in ("GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"):
        register_http_method(method, mutating=method in {"POST", "PUT", "PATCH", "DELETE"})
    for name in ("authorization", "cookie", "x-api-key", "api-key", "token",
                 "access-token", "x-token", "jwt"):
        register_auth_header_name(name)
    for key in ("password", "pwd", "secret", "private_key", "privatekey", "client_secret"):
        register_sensitive_key(key, "high")
    for key in ("token", "access_token", "refresh_token", "api_key", "apikey",
                "session", "cookie", "credential", "authorization"):
        register_sensitive_key(key, "medium")
    hint_groups = {
        "admin": ["admin", "internal", "debug", "system", "ops", "manage", "config"],
        "file": ["upload", "file", "image", "avatar", "attachment", "import"],
        "upload_validation": ["multipart", "size", "mime", "content-type", "virus", "extension", "limit"],
        "ssrf": ["url", "uri", "callback", "redirect", "returnurl", "return_url", "webhook", "endpoint"],
        "list": ["list", "search", "query", "export", "all", "batch", "report"],
        "pagination": ["page", "size", "limit", "offset", "cursor"],
        "resource_control": ["rate", "limit", "throttle", "quota", "pagination"],
        "cache": ["login", "token", "session", "profile", "user", "me", "auth", "password"],
        "public": ["login", "signin", "signup", "register", "health", "ping", "captcha", "public", "openapi", "swagger"],
        "object_id": ["id", "user_id", "tenant_id", "account_id", "order_id", "resource_id", "item_id"],
        "business": ["payment", "pay", "refund", "withdraw", "coupon", "order", "invoice", "wallet", "settlement"],
        "cors_trusted": ["https://trusted.example.com"],
    }
    for group, words in hint_groups.items():
        for word in words:
            register_hint(group, word)
    for marker in ("exception", "traceback", "stack trace", "sql syntax", "syntax error",
                   "mysql", "postgres", "ora-", "nullpointerexception", "debug", " at "):
        register_error_marker(marker)
    owasp = [
        ("API1:2023", "Broken Object Level Authorization", "校验对象 ID、资源 ID、租户 ID 访问是否越权", "切换不同对象 ID、租户 ID、历史订单 ID 做越权验证。"),
        ("API2:2023", "Broken Authentication", "复核登录、Token、会话续期和失效机制", "验证 Token 过期、注销、并发登录、弱口令和多因子流程。"),
        ("API3:2023", "Broken Object Property Level Authorization", "检查响应和请求对象字段是否存在越权读写", "检查响应字段裁剪、只读字段写入和批量对象属性越权。"),
        ("API4:2023", "Unrestricted Resource Consumption", "确认分页、限流、批量接口和导出接口的资源控制", "验证分页上限、批量导出、并发速率、超大请求体和超时控制。"),
        ("API5:2023", "Broken Function Level Authorization", "检查高权限功能接口是否做角色/功能级鉴权", "针对普通用户、管理员、客服、运营角色做功能级权限矩阵测试。"),
        ("API6:2023", "Unrestricted Access to Sensitive Business Flows", "复核注册、登录、找回密码、领券等关键业务流", "重点审计注册、登录、找回密码、领券、支付、提现等关键业务流。"),
        ("API7:2023", "Server Side Request Forgery", "检查 URL、回调、Webhook、跳转类参数是否可被滥用", "尝试不同协议、内网 IP、回环地址和 DNS 变体，确认服务端限制策略。"),
        ("API8:2023", "Security Misconfiguration", "检查协议、头部、CORS、Cookie、错误泄露和方法暴露", "复核头部、Cookie、CORS、调试开关、默认配置和多余方法暴露。", True),
        ("API9:2023", "Improper Inventory Management", "确认接口清单、版本、测试环境和废弃接口治理", "核对接口清单、版本、环境、废弃接口和影子接口治理情况。", True),
        ("API10:2023", "Unsafe Consumption of APIs", "检查第三方 API、上游依赖、Webhook 和外部服务调用", "复核第三方 API 调用、Webhook、回调信任边界和上游错误处理。"),
    ]
    for entry in owasp:
        if len(entry) == 5:
            register_owasp_item(entry[0], entry[1], entry[2], entry[3], auto_baseline=entry[4])
        else:
            register_owasp_item(entry[0], entry[1], entry[2], entry[3])
    for name, rank in (("high", 0), ("medium", 1), ("low", 2), ("info", 3), ("none", 4)):
        register_severity(name, rank)
    for keyword, rank in (("匿名", 0), ("anonymous", 0), ("guest", 0),
                          ("普通", 1), ("user", 1), ("member", 1), ("customer", 1),
                          ("跨租户", 1), ("越权", 1), ("cross", 1), ("other tenant", 1),
                          ("管理员", 3), ("admin", 3), ("ops", 3), ("operator", 3), ("root", 3)):
        register_role_rank(keyword, rank)
    register_status_bucket("error", lambda code: code <= 0)
    register_status_bucket("allow", lambda code: 200 <= code < 400)
    register_status_bucket("deny", lambda code: code in (401, 403, 404))
    for severity, priority in (("high", "P0"), ("medium", "P1"), ("low", "P2"), ("info", "P3")):
        register_priority(severity, priority)
    suite_names = {
        "transport": "传输与协议回归", "headers": "安全头基线回归", "cors": "跨域配置回归",
        "methods": "方法暴露回归", "fingerprint": "指纹暴露回归", "cookie": "Cookie 安全回归",
        "auth_review": "鉴权回归", "admin_review": "功能权限回归", "auth_runtime_review": "匿名访问回归",
        "sensitive_url": "敏感参数回归", "sensitive_response": "敏感数据泄露回归",
        "error_leak": "错误泄露回归", "upload_review": "上传安全回归", "ssrf_review": "SSRF 参数回归",
        "resource_control": "资源控制回归", "cache_review": "缓存控制回归",
        "probe_error": "可达性与环境回归", "inventory": "接口清单回归", "role_regression": "多角色差异回归",
    }
    for key, name in suite_names.items():
        register_suite_name(key, name)
    expected = {
        "transport": "统一使用 HTTPS，且网关具备强制跳转/HSTS 策略",
        "headers": "返回安全头且满足内部基线", "cors": "仅允许白名单来源，且不与凭证通配组合",
        "methods": "仅暴露必要 HTTP 方法，不返回 TRACE", "fingerprint": "不暴露敏感指纹头或弱化版本信息",
        "cookie": "每个 Cookie 至少具备 Secure/HttpOnly/SameSite", "auth_review": "未授权返回 401/403，授权后按角色放行",
        "admin_review": "普通用户不可访问管理功能，管理员按最小权限放行", "auth_runtime_review": "匿名访问敏感接口应被拒绝",
        "sensitive_url": "敏感凭据不出现在 path/query 中", "sensitive_response": "响应字段按角色裁剪或脱敏",
        "error_leak": "错误返回不包含堆栈、SQL、内部类名", "upload_review": "上传接口具备类型/大小/病毒扫描等限制",
        "ssrf_review": "URL/回调参数具备协议白名单和内网访问限制", "resource_control": "列表/批量/导出接口具备分页、限流和大小控制",
        "cache_review": "敏感接口具备合理 Cache-Control 策略",
    }
    for key, text in expected.items():
        register_expected_text(key, text)
    for key, label in (("plan", "安全方案"), ("policy", "扫描策略"), ("passive", "被动审计"),
                       ("probe", "基线探测"), ("role", "多角色回归"), ("risk", "风险看板"),
                       ("auth", "权限矩阵"), ("owasp", "OWASP 清单"), ("templates", "Nuclei模板"),
                       ("suite", "回归套件"), ("playbook", "测试剧本"), ("download", "下载导出")):
        register_result_tab(key, label)
    for key, label in (("finding_count", "发现项"), ("high", "High"), ("medium", "Medium"),
                       ("low", "Low"), ("info", "Info"), ("request_count", "请求数")):
        register_summary_metric(key, label)
    register_probe_strategy("safe_baseline", lambda method: ["OPTIONS", "GET"] if method in {"GET", "HEAD"}
                            else (["OPTIONS"] if method == "OPTIONS" else ["OPTIONS"]))
    register_probe_strategy("options_only", lambda method: ["OPTIONS"])
    passive_rules = [
        ("transport", "transport", "明文 HTTP", _rule_transport),
        ("auth_review", "auth_review", "变更类接口鉴权", _rule_auth_review),
        ("admin_review", "admin_review", "管理接口鉴权", _rule_admin_review),
        ("sensitive_url", "sensitive_url", "URL 敏感参数", _rule_sensitive_url),
        ("sensitive_response", "sensitive_response", "响应敏感字段", _rule_sensitive_response),
        ("error_leak", "error_leak", "错误泄露", _rule_error_leak),
        ("upload_review", "upload_review", "上传校验", _rule_upload_review),
        ("ssrf_review", "ssrf_review", "SSRF 参数", _rule_ssrf_review),
        ("resource_control", "resource_control", "资源控制", _rule_resource_control),
        ("inventory", "inventory", "接口清单完整性", _rule_inventory),
    ]
    for key, category, label, fn in passive_rules:
        register_passive_rule(key, category, label, fn)
    probe_rules = [
        ("transport", "transport", "明文 HTTP", _pr_transport),
        ("hsts", "headers", "HSTS", _pr_hsts),
        ("xcto", "headers", "X-Content-Type-Options", _pr_xcto),
        ("csp", "headers", "CSP", _pr_csp),
        ("cors", "cors", "CORS 配置", _pr_cors),
        ("methods", "methods", "TRACE 方法", _pr_methods),
        ("fingerprint", "fingerprint", "服务指纹", _pr_fingerprint),
        ("cookie", "cookie", "Cookie 属性", _pr_cookie),
        ("error_leak", "error_leak", "响应错误泄露", _pr_error_leak),
        ("auth_runtime", "auth_runtime_review", "匿名访问敏感接口", _pr_auth_runtime),
        ("cache_review", "cache_review", "敏感接口缓存控制", _pr_cache_review),
    ]
    for key, category, label, fn in probe_rules:
        register_probe_rule(key, category, label, fn)
    register_nuclei_template("headers", "api-security-headers-baseline.yaml",
                             "API Security Headers Baseline", _nuclei_headers_template)
    register_nuclei_template("options", "api-cors-methods-exposure.yaml",
                             "API CORS And Method Exposure", _nuclei_options_template)
    register_nuclei_template("cache", "api-sensitive-cache-review.yaml",
                             "API Sensitive Cache Review", _nuclei_cache_template)
    register_export_sanitizer("csv_formula_guard", _csv_formula_guard)


def reset_security_registry() -> None:
    """清空全部注册表并重新装载默认值，供 pytest 用例隔离使用。"""
    global _LIMITS
    with _LOCK:
        _PROTOCOLS.clear()
        _HTTP_METHODS.clear()
        _MUTATING_METHODS.clear()
        _AUTH_HEADER_NAMES.clear()
        _SENSITIVE_KEYS.clear()
        _HINTS.clear()
        _ERROR_MARKERS.clear()
        _OWASP_ITEMS.clear()
        _SEVERITY_ORDER.clear()
        _ROLE_RANKS.clear()
        _STATUS_BUCKETS.clear()
        _PRIORITY_MAP.clear()
        _SUITE_NAMES.clear()
        _EXPECTED_TEXTS.clear()
        _RESULT_TABS.clear()
        _SUMMARY_METRICS.clear()
        _PROBE_STRATEGIES.clear()
        _PASSIVE_RULES.clear()
        _PROBE_RULES.clear()
        _NUCLEI_TEMPLATES.clear()
        _EXPORT_SANITIZERS.clear()
        _LIMITS = SecurityLimits()
    _bootstrap_defaults()


_bootstrap_defaults()
