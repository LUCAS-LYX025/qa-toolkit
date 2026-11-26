"""接口自动化测试工具：注册式扩展点。

设计目标（不局限于当前业务）：
- HTTP 方法、请求格式、执行模式与框架渲染器、鉴权方式、模板风格与断言策略、
  状态码分桶、镜像源、导入模板、报告模板、导出格式、协议白名单、Header 校验、
  URL 构造、CSV/Markdown/HTML 清洗器、凭据脱敏策略、运行上限全部通过
  ``register_*`` / ``get_*`` 暴露；
- 下游项目想新增一种执行框架（pytest/unittest/自研 runner）、一种鉴权方式
  （OAuth2 / 签名鉴权）、一种断言策略或一份导入模板，只需调用注册接口，
  不需要改 core / page / report_generator；
- frozen dataclass Spec + 查询返回副本 + 重复注册需 ``replace=True``，避免全局
  注册表被页面或测试意外污染；``reset_automation_registry()`` 保证测试隔离。

与 ``api_performance_registry.py`` / ``api_security_registry.py`` /
``api_dev_registry.py`` 的安全护栏语义保持一致（协议白名单、userinfo 拒绝、
端口校验、内网/元数据地址拦截、默认开启 SSL 校验），但注册表相互独立，
便于各自演进。
"""
from __future__ import annotations

import base64
import copy
import hashlib
import html
import ipaddress
import json
import math
import re
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlsplit, urlunsplit

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
# 运行上限与安全默认值（全部可配置）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AutomationLimits:
    max_interfaces: int = 1000
    max_upload_bytes: int = 8 * 1024 * 1024
    min_timeout_seconds: int = 1
    max_timeout_seconds: int = 120
    default_timeout_seconds: int = 30
    max_retry_times: int = 5
    max_response_body_chars: int = 200_000
    max_export_chars: int = 2_000_000
    max_script_chars: int = 2_000_000
    max_header_value_chars: int = 8_000
    max_report_files: int = 50
    subprocess_timeout_seconds: int = 300
    max_redirect_hops: int = 4
    max_recursion_depth: int = 12
    max_field_paths: int = 500
    min_status_code: int = 100
    max_status_code: int = 599
    default_verify_ssl: bool = True
    allow_private_targets: bool = False
    allow_credentials_in_artifacts: bool = False


_LIMITS = AutomationLimits()


def configure_automation_limits(**kwargs: Any) -> AutomationLimits:
    """覆盖运行上限；未知字段直接报错，避免拼写错误被静默忽略。"""
    global _LIMITS
    allowed = {f.name for f in AutomationLimits.__dataclass_fields__.values()}
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知的 AutomationLimits 字段: {sorted(unknown)}")
    with _LOCK:
        _LIMITS = AutomationLimits(**{**_LIMITS.__dict__, **kwargs})
        return _LIMITS


def get_automation_limits() -> AutomationLimits:
    with _LOCK:
        return _LIMITS


# ---------------------------------------------------------------------------
# 严格 JSON（拒绝 NaN / Infinity，导出与 manifest 共用）
# ---------------------------------------------------------------------------

def _sanitize_json_numbers(value: Any, warnings: List[str], depth: int = 0) -> Any:
    limits = get_automation_limits()
    if depth > limits.max_recursion_depth:
        warnings.append("JSON 数据超过最大递归深度，已压缩该节点")
        return None
    if isinstance(value, float) and not math.isfinite(value):
        warnings.append(f"非有限数值 {value!r} 已清洗为 null")
        return None
    if isinstance(value, dict):
        return {str(k): _sanitize_json_numbers(v, warnings, depth + 1) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_sanitize_json_numbers(v, warnings, depth + 1) for v in value]
    return value


def strict_json_dumps(value: Any, **kwargs: Any) -> str:
    """序列化为严格 JSON：非有限浮点清洗为 null，绝不允许 NaN/Infinity。"""
    warnings: List[str] = []
    cleaned = _sanitize_json_numbers(value, warnings)
    kwargs.setdefault("ensure_ascii", False)
    kwargs["allow_nan"] = False
    return json.dumps(cleaned, **kwargs)


def json_warnings(value: Any) -> List[str]:
    warnings: List[str] = []
    _sanitize_json_numbers(value, warnings)
    return warnings


def encode_json_literal(value: Any) -> str:
    """把任意结构编码成**不会与模板哨兵碰撞**的 Python 表达式。

    base64 字母表不含下划线，编码结果里不可能出现 ``__XXX_LITERAL__`` 这类
    模板占位符；生成脚本运行时解码还原。这样用户输入（base_url、接口名、
    断言文本）即使含哨兵字符串，也不会在后续 ``str.replace`` 里被二次替换，
    三种框架生成的脚本都保持可编译。
    """
    payload = strict_json_dumps(value, separators=(",", ":"))
    encoded = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    return (
        "json.loads(__import__('base64').b64decode(" + repr(encoded)
        + ").decode('utf-8'))"
    )


def normalize_test_stats(test_results: Dict[str, Any]) -> Tuple[Dict[str, int], List[str]]:
    """统计归一化：分项钳制到 total，杜绝 500% 这类不可能的结论。

    返回 ``(归一化统计, 告警)``；告警会写进报告与文字结论，不再静默展示
    失真的成功率。统计不守恒时按原比例缩放，并把余数补给最大分项。
    """
    total = max(0, to_int((test_results or {}).get("total"), 0))
    raw = {
        key: max(0, to_int((test_results or {}).get(key), 0))
        for key in ("passed", "failed", "errors")
    }
    warnings: List[str] = []
    if total <= 0:
        if any(raw.values()):
            warnings.append("统计口径异常：总数为 0 但分项非零，报告已归零")
        return {"total": 0, "passed": 0, "failed": 0, "errors": 0}, warnings

    if sum(raw.values()) > total:
        warnings.append(
            "统计口径异常：通过 {} / 失败 {} / 错误 {} 合计超过总数 {}，"
            "报告已按比例钳制，请检查执行器输出".format(
                raw["passed"], raw["failed"], raw["errors"], total
            )
        )
        denominator = sum(raw.values())
        scaled = {key: int(value * total / denominator) for key, value in raw.items()}
        remainder = total - sum(scaled.values())
        if remainder > 0:
            biggest = max(scaled, key=lambda k: scaled[k])
            scaled[biggest] += remainder
        raw = scaled
    else:
        for key, value in raw.items():
            if value > total:
                warnings.append(
                    f"统计口径异常：{key}={value} 超过总数 {total}，报告已钳制"
                )
                raw[key] = total
    return {"total": total, **raw}, warnings


# ---------------------------------------------------------------------------
# 协议白名单与目标地址护栏（执行时同样生效）
# ---------------------------------------------------------------------------

_PROTOCOLS: Dict[str, str] = {"http": "HTTP", "https": "HTTPS"}
_TOKEN_RE = re.compile(r"^[!#$%&'*+.^_`|~0-9A-Za-z-]+$")
_CONTROL_RE = re.compile(r"[\x00-\x08\x0a-\x1f\x7f]")


def register_protocol(scheme: str, label: str = "", *, replace: bool = False) -> None:
    key = str(scheme or "").strip().lower()
    if not key or not re.fullmatch(r"[a-z][a-z0-9+.-]*", key):
        raise ValueError(f"非法协议名: {scheme!r}")
    with _LOCK:
        if key in _PROTOCOLS and not replace:
            raise ValueError(f"协议 {key!r} 已注册；如需覆盖请传 replace=True")
        _PROTOCOLS[key] = label or key.upper()


def get_protocols() -> Tuple[str, ...]:
    with _LOCK:
        return tuple(sorted(_PROTOCOLS))


def _is_private_host(host: str) -> bool:
    text = (host or "").strip().lower().rstrip(".")
    if not text:
        return True
    if text in {"localhost", "localhost.localdomain", "metadata", "metadata.google.internal"}:
        return True
    if text.endswith(".localhost") or text.endswith(".internal") or text.endswith(".local"):
        return True
    try:
        addr = ipaddress.ip_address(text.strip("[]"))
    except ValueError:
        return False
    return bool(
        addr.is_private or addr.is_loopback or addr.is_link_local
        or addr.is_reserved or addr.is_multicast or addr.is_unspecified
    )


def validate_target_url(url: str, *, allow_private: Optional[bool] = None) -> Tuple[bool, str]:
    """校验执行目标；默认拒绝内网/回环/链路本地/元数据地址。"""
    text = str(url or "").strip()
    if not text:
        return False, "目标地址为空"
    parsed = urlsplit(text)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _PROTOCOLS:
        return False, f"不支持的协议 {scheme or '(空)'}，仅允许：{'、'.join(get_protocols())}"
    if parsed.username or parsed.password:
        return False, "目标地址包含 userinfo（用户名/密码），已拒绝"
    if not parsed.hostname:
        return False, "目标地址缺少主机名"
    try:
        port = parsed.port
    except ValueError:
        return False, "目标地址端口非法"
    if port is not None and not (1 <= port <= 65535):
        return False, f"目标地址端口 {port} 越界"
    allow = get_automation_limits().allow_private_targets if allow_private is None else bool(allow_private)
    if not allow and _is_private_host(parsed.hostname):
        return False, "目标为内网/回环/链路本地/元数据地址；如需联调本地服务请显式开启「允许内网/本地目标」"
    return True, ""


def validate_header_name(name: Any) -> Tuple[bool, str]:
    text = "" if name is None else str(name)
    if not text or not _TOKEN_RE.fullmatch(text):
        return False, f"非法 Header 名 {text!r}（必须是 RFC 7230 token）"
    return True, ""


def validate_header_value(value: Any, *, max_chars: Optional[int] = None) -> Tuple[bool, str]:
    limit = get_automation_limits().max_header_value_chars if max_chars is None else max_chars
    text = "" if value is None else str(value)
    if _CONTROL_RE.search(text) or "\r" in text or "\n" in text:
        return False, "Header 值包含 CRLF 或控制字符，已拒绝"
    if len(text) > limit:
        return False, f"Header 值超过 {limit} 字符上限，已拒绝"
    return True, ""


def sanitize_headers(headers: Optional[Dict[str, Any]]) -> Tuple[Dict[str, str], List[str]]:
    """校验并清洗请求头；非法项显式告警并丢弃，绝不静默透传。"""
    cleaned: Dict[str, str] = {}
    warnings: List[str] = []
    if not isinstance(headers, dict):
        return cleaned, warnings
    for raw_name, raw_value in headers.items():
        ok, reason = validate_header_name(raw_name)
        if not ok:
            warnings.append(f"已丢弃请求头 {str(raw_name)!r}: {reason}")
            continue
        ok, reason = validate_header_value(raw_value)
        if not ok:
            warnings.append(f"已丢弃请求头 {raw_name}: {reason}")
            continue
        cleaned[str(raw_name)] = str(raw_value)
    return cleaned, warnings


# ---------------------------------------------------------------------------
# URL 构造：结构化合并，路径参数逐段编码
# ---------------------------------------------------------------------------

def quote_path_value(value: Any) -> str:
    """路径参数编码；``raw:`` 前缀显式跳过编码（可注册的显式逃生口）。"""
    text = "" if value is None else str(value)
    if text.startswith("raw:"):
        return text[4:]
    return quote(text, safe="")


def build_full_url(
    base_url: str,
    path: str,
    path_params: Optional[Dict[str, Any]] = None,
    query_params: Optional[Dict[str, Any]] = None,
) -> Tuple[str, List[str]]:
    """结构化构造 URL，返回 (url, warnings)。

    - 路径参数逐段 quote，杜绝路径穿越 / query 注入；
    - base_url 与 path 用 urlsplit 拆解后合并，不再字符串拼接；
    - 同名 query 参数 append，list/tuple 用 doseq 展开；
    - 未替换的 ``{var}`` 写入告警，避免静默发出畸形请求。
    """
    warnings: List[str] = []
    actual_path = str(path or "/")
    for key, value in dict(path_params or {}).items():
        marker = "{" + str(key) + "}"
        if marker in actual_path:
            actual_path = actual_path.replace(marker, quote_path_value(value))

    base = urlsplit(str(base_url or "").strip())
    target = urlsplit(actual_path)
    if target.scheme and target.netloc:
        merged = target
    else:
        base_path = (base.path or "").rstrip("/")
        path_only = target.path or "/"
        if not path_only.startswith("/"):
            path_only = "/" + path_only
        merged_path = (base_path + path_only) or "/"
        merged_path = re.sub(r"/{2,}", "/", merged_path)
        merged = target._replace(
            scheme=base.scheme,
            netloc=base.netloc,
            path=merged_path,
        )

    merged_query: List[Tuple[str, Any]] = list(parse_qsl(merged.query, keep_blank_values=True))
    if base.scheme and base.netloc and base.query:
        merged_query = list(parse_qsl(base.query, keep_blank_values=True)) + merged_query
    for key, value in dict(query_params or {}).items():
        values = value if isinstance(value, (list, tuple)) else [value]
        for item in values:
            merged_query.append((str(key), "" if item is None else str(item)))

    final_query = urlencode(merged_query, doseq=True)
    final_url = urlunsplit(merged._replace(query=final_query))
    unresolved = re.findall(r"\{([^{}]+)\}", final_url)
    if unresolved:
        warnings.append(f"URL 中仍有未解析的路径变量: {', '.join(sorted(set(unresolved)))}")
    ok, reason = validate_target_url(final_url)
    if not ok:
        warnings.append(f"目标地址校验失败: {reason}")
    return final_url, warnings


# ---------------------------------------------------------------------------
# HTTP 方法
# ---------------------------------------------------------------------------

_HTTP_METHODS: Dict[str, str] = {
    "GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH",
    "DELETE": "DELETE", "HEAD": "HEAD", "OPTIONS": "OPTIONS",
}


def register_http_method(method: str, label: str = "", *, replace: bool = False) -> None:
    key = str(method or "").strip().upper()
    if not key or not re.fullmatch(r"[A-Z]+", key):
        raise ValueError(f"非法 HTTP 方法: {method!r}")
    with _LOCK:
        if key in _HTTP_METHODS and not replace:
            raise ValueError(f"HTTP 方法 {key!r} 已注册；如需覆盖请传 replace=True")
        _HTTP_METHODS[key] = label or key


def get_http_methods() -> Tuple[str, ...]:
    with _LOCK:
        return tuple(sorted(_HTTP_METHODS))


def normalize_method(value: Any, default: str = "GET") -> Tuple[str, str]:
    """归一化 HTTP 方法；非法值回落默认值并**返回告警**（不再静默）。"""
    text = str(value or default).strip().upper()
    if text in _HTTP_METHODS:
        return text, ""
    return default, f"非法 HTTP 方法 {str(value)!r}，已回落为 {default}（仅允许：{'、'.join(get_http_methods())}）"


# ---------------------------------------------------------------------------
# 请求格式
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class RequestFormatSpec:
    key: str
    label: str
    aliases: Tuple[str, ...] = ()


_REQUEST_FORMATS: Dict[str, RequestFormatSpec] = {}


def register_request_format(spec: RequestFormatSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _REQUEST_FORMATS and not replace:
            raise ValueError(f"请求格式 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _REQUEST_FORMATS[spec.key] = spec


def get_request_formats() -> Dict[str, RequestFormatSpec]:
    with _LOCK:
        return dict(_REQUEST_FORMATS)


def get_request_format_labels() -> List[str]:
    return [spec.label for spec in get_request_formats().values()]


def normalize_request_format(value: Any) -> Tuple[str, str]:
    """归一化请求格式；未知取值回落 ``auto`` 并返回告警。"""
    text = str(value or "auto").strip()
    for spec in _REQUEST_FORMATS.values():
        if text == spec.key or text == spec.label or text.lower() in [a.lower() for a in spec.aliases]:
            return spec.key, ""
    return "auto", f"未知请求格式 {str(value)!r}，已回落为「自动检测」（已注册：{'、'.join(get_request_format_labels())}）"


# ---------------------------------------------------------------------------
# 执行模式与框架渲染器
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExecutionModeSpec:
    key: str
    label: str
    renderer_key: str
    target_file: str
    aliases: Tuple[str, ...] = ()


_EXECUTION_MODES: Dict[str, ExecutionModeSpec] = {}
_FRAMEWORK_RENDERERS: Dict[str, Callable[..., str]] = {}


def register_execution_mode(spec: ExecutionModeSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _EXECUTION_MODES and not replace:
            raise ValueError(f"执行模式 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _EXECUTION_MODES[spec.key] = spec


def register_framework_renderer(key: str, renderer: Callable[..., str], *, replace: bool = False) -> None:
    with _LOCK:
        if key in _FRAMEWORK_RENDERERS and not replace:
            raise ValueError(f"框架渲染器 {key!r} 已注册；如需覆盖请传 replace=True")
        _FRAMEWORK_RENDERERS[key] = renderer


def get_framework_renderer(key: str) -> Optional[Callable[..., str]]:
    with _LOCK:
        return _FRAMEWORK_RENDERERS.get(key)


def get_execution_modes() -> Dict[str, ExecutionModeSpec]:
    with _LOCK:
        return dict(_EXECUTION_MODES)


def get_execution_mode_labels() -> List[str]:
    return [spec.label for spec in get_execution_modes().values()]


def normalize_execution_mode(value: Any) -> Tuple[str, str]:
    """归一化执行模式；未知取值回落 ``pytest`` 并返回告警。"""
    text = str(value or "pytest").strip()
    for spec in _EXECUTION_MODES.values():
        if text == spec.key or text == spec.label or text.lower() in [a.lower() for a in spec.aliases]:
            return spec.key, ""
    return "pytest", f"未知执行模式 {str(value)!r}，已回落为 pytest（已注册：{'、'.join(get_execution_mode_labels())}）"


def get_known_generated_files() -> Tuple[str, ...]:
    files = {"interface_manifest.json"}
    files.update(spec.target_file for spec in get_execution_modes().values())
    return tuple(sorted(files))


# ---------------------------------------------------------------------------
# 鉴权方式（可注册 + 凭据脱敏）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthModeSpec:
    mode: str
    label: str
    builder: Callable[[Dict[str, Any]], Dict[str, str]]
    sensitive_fields: Tuple[str, ...] = ()


_AUTH_MODES: Dict[str, AuthModeSpec] = {}
SENSITIVE_AUTH_FIELDS: Tuple[str, ...] = ("token", "password", "api_key_value", "custom_header_value")


def _bearer_builder(cfg: Dict[str, Any]) -> Dict[str, str]:
    if not cfg.get("token"):
        return {}
    return {str(cfg.get("header_name") or "Authorization"): f"{cfg.get('prefix') or 'Bearer '}{cfg['token']}"}


def _api_key_builder(cfg: Dict[str, Any]) -> Dict[str, str]:
    if not cfg.get("api_key_value"):
        return {}
    return {str(cfg.get("api_key_name") or "X-API-Key"): str(cfg["api_key_value"])}


def _basic_builder(cfg: Dict[str, Any]) -> Dict[str, str]:
    import base64
    if not cfg.get("username"):
        return {}
    raw = f"{cfg.get('username','')}:{cfg.get('password','')}"
    return {"Authorization": "Basic " + base64.b64encode(raw.encode("utf-8")).decode("utf-8")}


def _custom_header_builder(cfg: Dict[str, Any]) -> Dict[str, str]:
    if not cfg.get("custom_header_value") or not cfg.get("custom_header_name"):
        return {}
    return {str(cfg["custom_header_name"]): str(cfg["custom_header_value"])}


def register_auth_mode(spec: AuthModeSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.mode in _AUTH_MODES and not replace:
            raise ValueError(f"鉴权方式 {spec.mode!r} 已注册；如需覆盖请传 replace=True")
        _AUTH_MODES[spec.mode] = spec


def get_auth_modes() -> Dict[str, AuthModeSpec]:
    with _LOCK:
        return dict(_AUTH_MODES)


def get_auth_labels() -> List[str]:
    return [spec.label for spec in get_auth_modes().values() if spec.mode != "none"]


def label_to_auth_mode(label: Any) -> Tuple[str, str]:
    text = str(label or "无").strip()
    for spec in get_auth_modes().values():
        if text == spec.label or text.lower() == spec.mode.lower():
            return spec.mode, ""
    return "none", f"未知鉴权方式 {str(label)!r}，已回落为「无」（已注册：{'、'.join(get_auth_labels())}）"


def normalize_auth_config(auth_config: Any) -> Dict[str, Any]:
    """归一化鉴权配置；未知方式显式写入 ``mode_warning``，不再静默失效。"""
    parsed = auth_config
    if isinstance(auth_config, str) and auth_config.strip():
        try:
            parsed = json.loads(auth_config)
        except json.JSONDecodeError:
            parsed = {}
    if not isinstance(parsed, dict):
        parsed = {}
    raw_mode = str(parsed.get("type") or parsed.get("mode") or "none").strip()
    # 同时接受已注册的 mode key 与中文 label；未知取值显式告警，不静默失效。
    mode, warning = label_to_auth_mode(raw_mode)
    return {
        "enabled": bool(parsed.get("enabled")) and mode != "none",
        "type": mode,
        "mode_warning": warning,
        "header_name": str(parsed.get("header_name") or "Authorization").strip(),
        "prefix": str(parsed.get("prefix") if parsed.get("prefix") is not None else "Bearer "),
        "token": str(parsed.get("token") or "").strip(),
        "api_key_name": str(parsed.get("api_key_name") or "X-API-Key").strip(),
        "api_key_value": str(parsed.get("api_key_value") or "").strip(),
        "username": str(parsed.get("username") or "").strip(),
        "password": str(parsed.get("password") or "").strip(),
        "custom_header_name": str(parsed.get("custom_header_name") or "").strip(),
        "custom_header_value": str(parsed.get("custom_header_value") or "").strip(),
    }


def build_auth_headers(auth_config: Dict[str, Any]) -> Tuple[Dict[str, str], List[str]]:
    """构建鉴权头；Header 名/值走统一校验，非法项显式告警。"""
    warnings: List[str] = []
    if not isinstance(auth_config, dict) or not auth_config.get("enabled"):
        return {}, warnings
    warning = auth_config.get("mode_warning")
    if warning:
        warnings.append(warning)
    spec = get_auth_modes().get(str(auth_config.get("type") or "none"))
    if spec is None:
        warnings.append(f"鉴权方式 {auth_config.get('type')!r} 未注册，已跳过统一鉴权")
        return {}, warnings
    try:
        headers = dict(spec.builder(auth_config) or {})
    except Exception as exc:  # pragma: no cover - 第三方 builder 兜底
        warnings.append(f"鉴权头构建失败: {type(exc).__name__}: {exc}")
        return {}, warnings
    cleaned, header_warnings = sanitize_headers(headers)
    warnings.extend(header_warnings)
    return cleaned, warnings


def credential_env_var_name(mode: str, header_name: str) -> str:
    """凭据环境变量名；生成的脚本运行时从这里读取，产物里不落明文。"""
    slug = re.sub(r"[^A-Za-z0-9]+", "_", str(header_name or "AUTH")).strip("_").upper() or "AUTH"
    return f"QA_API_{str(mode).upper()}_{slug}"


def redact_auth_config(
    auth_config: Dict[str, Any], *, include_credentials: Optional[bool] = None
) -> Tuple[Dict[str, Any], Dict[str, str], List[str]]:
    """脱敏鉴权配置。

    返回 ``(脱敏配置, {header_name: env_var}, warnings)``。生成的脚本运行时
    从环境变量读取凭据并注入请求头；产物、页面展示、下载件默认不含明文。
    """
    limits = get_automation_limits()
    include = limits.allow_credentials_in_artifacts if include_credentials is None else bool(include_credentials)
    cleaned = copy.deepcopy(dict(auth_config or {}))
    warnings: List[str] = []
    if include:
        return cleaned, {}, ["已显式开启「产物中保留凭据」：token/密码会写入生成脚本与下载件，仅限本地调试"]
    # 先算出需要注入的 Header 名（此时凭据尚未清空），再无条件脱敏。
    env_map: Dict[str, str] = {}
    spec = get_auth_modes().get(str(cleaned.get("type") or "none"))
    try:
        probe = dict(spec.builder(cleaned)) if spec else {}
    except Exception:
        probe = {}
    # 无论是否启用鉴权，敏感字段一律脱敏：用户填了凭据却没勾「启用」，
    # 或切换鉴权方式后残留的旧 token，都不允许明文写进产物。
    for field in SENSITIVE_AUTH_FIELDS:
        if cleaned.get(field):
            cleaned[field] = ""
            warnings.append(f"鉴权字段 {field} 已从生成产物中脱敏")
    if cleaned.get("enabled"):
        for header_name in probe:
            env_map[str(header_name)] = credential_env_var_name(
                str(cleaned.get("type") or "none"), header_name
            )
    if env_map:
        warnings.append(
            "凭据未写入产物；执行时请通过环境变量提供："
            + "、".join(sorted(set(env_map.values())))
        )
    return cleaned, env_map, warnings


# ---------------------------------------------------------------------------
# 模板风格与断言策略（递归结构化比对）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TemplateStyleSpec:
    key: str
    label: str
    strategy: str
    description: str = ""


_TEMPLATE_STYLES: Dict[str, TemplateStyleSpec] = {}


def register_template_style(spec: TemplateStyleSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _TEMPLATE_STYLES and not replace:
            raise ValueError(f"模板风格 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _TEMPLATE_STYLES[spec.key] = spec


def get_template_styles() -> Dict[str, TemplateStyleSpec]:
    with _LOCK:
        return dict(_TEMPLATE_STYLES)


def get_template_style_labels() -> List[str]:
    return [spec.label for spec in get_template_styles().values()]


def resolve_template_style(value: Any) -> Tuple[str, str]:
    text = str(value or "标准模板").strip()
    for spec in get_template_styles().values():
        if text == spec.key or text == spec.label:
            return spec.key, ""
    default = "standard"
    return default, f"未知模板风格 {str(value)!r}，已回落为「标准模板」（已注册：{'、'.join(get_template_style_labels())}）"


_ASSERTION_STRATEGIES: Dict[str, str] = {}
# 注册的比较器会被 compare_response() 真正分发；未注册 comparator 的策略
# 回落到内置递归比对实现。下游项目新增断言风格不必改 core / 生成脚本。
_ASSERTION_COMPARATORS: Dict[str, Callable[..., List[str]]] = {}


def register_assertion_strategy(
    key: str,
    label: str,
    comparator: Optional[Callable[..., List[str]]] = None,
    *,
    replace: bool = False,
) -> None:
    """注册断言策略；``comparator(expected, actual, prefix=...) -> List[str]``。

    旧的两参数调用 ``register_assertion_strategy(key, label)`` 仍然兼容，
    此时该策略使用内置递归比对实现。
    """
    with _LOCK:
        if key in _ASSERTION_STRATEGIES and not replace:
            raise ValueError(f"断言策略 {key!r} 已注册；如需覆盖请传 replace=True")
        _ASSERTION_STRATEGIES[key] = label
        if comparator is not None:
            _ASSERTION_COMPARATORS[key] = comparator
        else:
            _ASSERTION_COMPARATORS.pop(key, None)


def get_assertion_strategies() -> Dict[str, str]:
    with _LOCK:
        return dict(_ASSERTION_STRATEGIES)


def get_assertion_comparator(key: str) -> Optional[Callable[..., List[str]]]:
    with _LOCK:
        return _ASSERTION_COMPARATORS.get(key)


def normalize_assertion_strategy(value: Any) -> Tuple[str, str]:
    """归一化断言策略；未知值回落 standard 但返回显式告警，不静默失效。"""
    strategies = get_assertion_strategies()
    text = str(value if value is not None else "").strip()
    for key, label in strategies.items():
        if text == key or text == label:
            return key, ""
    return (
        "standard",
        f"未知断言策略 {str(value)!r}，已回落为「标准模板」"
        f"（已注册：{'、'.join(strategies.values())}）",
    )


def compare_response(expected: Any, actual: Any, strategy: str, prefix: str = "response") -> List[str]:
    """递归结构化比对，输出点号/索引路径，受深度与字段数上限约束。

    ``smoke`` 跳过响应体；``standard`` 只校验期望中出现的字段；
    ``strict`` 还要求 dict 键集合与 list 长度一致。
    """
    strategy_key, warning = normalize_assertion_strategy(strategy)
    # 注册的自定义比较器优先分发，注册点不再是「只登记 label」。
    comparator = get_assertion_comparator(strategy_key)
    if comparator is not None:
        try:
            return list(comparator(expected, actual, prefix=prefix) or [])
        except TypeError:
            return list(comparator(expected, actual) or [])
    failures: List[str] = []
    if warning:
        failures.append(warning)
    if strategy_key == "smoke":
        return failures
    limits = get_automation_limits()
    counter = [0]

    def walk(exp: Any, act: Any, path: str, depth: int, strict: bool) -> None:
        counter[0] += 1
        if counter[0] > limits.max_field_paths:
            if len(failures) < 1:
                failures.append(f"比对字段数超过上限 {limits.max_field_paths}，结果已截断")
            return
        if depth > limits.max_recursion_depth:
            failures.append(f"{path} 超过最大递归深度 {limits.max_recursion_depth}，已跳过")
            return
        if isinstance(exp, dict):
            if not isinstance(act, dict):
                failures.append(f"{path} 应为对象，实际为 {type(act).__name__}")
                return
            for key, value in exp.items():
                child = f"{path}.{key}"
                if key not in act:
                    failures.append(f"{child} 缺少字段")
                    continue
                # bool/int/float 互不相等：先比类型再比值
                if type(value) is not type(act[key]) and not (
                    isinstance(value, (int, float)) and isinstance(act[key], (int, float))
                    and not isinstance(value, bool) and not isinstance(act[key], bool)
                ):
                    failures.append(f"{child} 类型变化: {type(value).__name__} -> {type(act[key]).__name__}")
                    continue
                walk(value, act[key], child, depth + 1, strict)
            if strict:
                for key in act:
                    if key not in exp:
                        failures.append(f"{path}.{key} 为多余字段（严格模板）")
            return
        if isinstance(exp, list):
            if not isinstance(act, list):
                failures.append(f"{path} 应为数组，实际为 {type(act).__name__}")
                return
            # 字符串列表可作为「字段存在性清单」的兼容语义
            if exp and all(isinstance(item, str) for item in exp):
                target = act[0] if act and isinstance(act[0], dict) else (act if isinstance(act, dict) else None)
                if isinstance(target, dict):
                    for key in exp:
                        if key not in target:
                            failures.append(f"{path}[0] 缺少字段 {key}")
                    return
            if len(act) < len(exp):
                failures.append(f"{path} 长度不足，期望至少 {len(exp)}，实际 {len(act)}")
            if strict and len(act) != len(exp):
                failures.append(f"{path} 长度不一致（严格模板）：期望 {len(exp)}，实际 {len(act)}")
            for index, value in enumerate(exp):
                if index >= len(act):
                    break
                walk(value, act[index], f"{path}[{index}]", depth + 1, strict)
            return
        if isinstance(exp, str) and not isinstance(act, str):
            if exp not in str(act):
                failures.append(f"{path} 未包含期望文本 {exp!r}")
            return
        if exp != act or type(exp) is not type(act):
            failures.append(f"{path} 期望 {exp!r}，实际 {act!r}")

    walk(expected, actual, prefix, 0, strategy_key == "strict")
    return failures


# ---------------------------------------------------------------------------
# 状态码分桶与合法性
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StatusCodeBucketSpec:
    key: str
    label: str
    low: int
    high: int
    warn: bool = False


_STATUS_BUCKETS: Dict[str, StatusCodeBucketSpec] = {}


def register_status_bucket(spec: StatusCodeBucketSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _STATUS_BUCKETS and not replace:
            raise ValueError(f"状态码分桶 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _STATUS_BUCKETS[spec.key] = spec


def get_status_buckets() -> Dict[str, StatusCodeBucketSpec]:
    with _LOCK:
        return dict(_STATUS_BUCKETS)


def classify_status_code(value: Any, default: int = 200) -> Dict[str, Any]:
    limits = get_automation_limits()
    code = to_int(value, default)
    valid = limits.min_status_code <= code <= limits.max_status_code
    bucket = "unknown"
    label = "未分类"
    warn = False
    for spec in get_status_buckets().values():
        if spec.low <= code <= spec.high:
            bucket, label, warn = spec.key, spec.label, spec.warn
            break
    return {"code": code, "valid": valid, "bucket": bucket, "label": label, "warn": warn}


# ---------------------------------------------------------------------------
# 镜像源 / 导入模板 / 报告模板 / 导出格式
# ---------------------------------------------------------------------------

_MIRRORS: Dict[str, str] = {}


def register_mirror(label: str, url: str, *, replace: bool = False) -> None:
    key = str(label or "").strip()
    if not key or not str(url or "").startswith(("http://", "https://")):
        raise ValueError(f"非法镜像源: {label!r} -> {url!r}")
    with _LOCK:
        if key in _MIRRORS and not replace:
            raise ValueError(f"镜像源 {key!r} 已注册；如需覆盖请传 replace=True")
        _MIRRORS[key] = str(url)


def get_mirrors() -> Dict[str, str]:
    with _LOCK:
        return dict(_MIRRORS)


@dataclass(frozen=True)
class ImportTemplateSpec:
    label: str
    builder_key: str
    file_name: str
    mime: str
    caption: str = ""


_IMPORT_TEMPLATES: Dict[str, ImportTemplateSpec] = {}


def register_import_template(spec: ImportTemplateSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.label in _IMPORT_TEMPLATES and not replace:
            raise ValueError(f"导入模板 {spec.label!r} 已注册；如需覆盖请传 replace=True")
        _IMPORT_TEMPLATES[spec.label] = spec


def get_import_templates() -> Dict[str, ImportTemplateSpec]:
    with _LOCK:
        return dict(_IMPORT_TEMPLATES)


@dataclass(frozen=True)
class ReportTemplateSpec:
    """报告模板注册项：label 供下拉展示，renderer 真正参与产物渲染。

    ``renderer`` 签名为 ``(ctx) -> str``；未提供的模板只登记 label，会在
    ``get_registry_summary()['接入状态']`` 里标注为「仅登记」，不再让用户误以为
    它已经接入产物链（#423/R3-09）。
    """
    key: str
    label: str
    renderer: Optional[Callable[[Dict[str, Any]], str]] = None


@dataclass(frozen=True)
class ExportFormatSpec:
    """导出格式注册项：serializer 真正把结果序列化成下载项。

    ``serializer`` 签名为 ``(ctx) -> bytes | str | None``；返回 None 表示该格式
    在当前上下文不可用（例如没有数据），下载面板应跳过。
    """
    key: str
    label: str
    file_name: str = ""
    mime: str = "application/octet-stream"
    caption: str = ""
    serializer: Optional[Callable[[Dict[str, Any]], Any]] = None


_REPORT_TEMPLATES: Dict[str, ReportTemplateSpec] = {}
_EXPORT_FORMATS: Dict[str, ExportFormatSpec] = {}


def register_report_template(
    key: str,
    label: str,
    *,
    renderer: Optional[Callable[[Dict[str, Any]], str]] = None,
    replace: bool = False,
) -> None:
    with _LOCK:
        if key in _REPORT_TEMPLATES and not replace:
            raise ValueError(f"报告模板 {key!r} 已注册；如需覆盖请传 replace=True")
        _REPORT_TEMPLATES[key] = ReportTemplateSpec(key, label, renderer)


def get_report_templates() -> Dict[str, str]:
    """兼容旧签名：返回 ``{key: label}``。"""
    with _LOCK:
        return {key: spec.label for key, spec in _REPORT_TEMPLATES.items()}


def get_report_specs() -> Dict[str, ReportTemplateSpec]:
    with _LOCK:
        return dict(_REPORT_TEMPLATES)


def get_report_renderer(key: str) -> Optional[Callable[[Dict[str, Any]], str]]:
    with _LOCK:
        spec = _REPORT_TEMPLATES.get(key)
        return spec.renderer if spec else None


def register_export_format(
    key: str,
    label: str,
    *,
    renderer: Optional[Callable[[Dict[str, Any]], Any]] = None,
    file_name: str = "",
    mime: str = "application/octet-stream",
    caption: str = "",
    replace: bool = False,
) -> None:
    with _LOCK:
        if key in _EXPORT_FORMATS and not replace:
            raise ValueError(f"导出格式 {key!r} 已注册；如需覆盖请传 replace=True")
        _EXPORT_FORMATS[key] = ExportFormatSpec(
            key, label, file_name or f"export_{key}.{key}", mime, caption, renderer
        )


def get_export_formats() -> Dict[str, str]:
    """兼容旧签名：返回 ``{key: label}``。"""
    with _LOCK:
        return {key: spec.label for key, spec in _EXPORT_FORMATS.items()}


def get_export_specs() -> Dict[str, ExportFormatSpec]:
    with _LOCK:
        return dict(_EXPORT_FORMATS)


def get_export_items(ctx: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """按注册的导出格式生成下载项，真正让新增格式进入产物链。

    每个格式的 serializer 接收 ctx，返回数据（bytes/str）；返回 None/空表示
    当前无数据、跳过。页面下载区应直接消费本函数，而不是硬编码三项。
    """
    context = dict(ctx or {})
    items: List[Dict[str, Any]] = []
    with _LOCK:
        specs = list(_EXPORT_FORMATS.values())
    for spec in specs:
        data = None
        if spec.serializer is not None:
            try:
                data = spec.serializer(context)
            except Exception:  # 单个导出失败不应阻断其它格式
                data = None
        if data is None:
            continue
        items.append({
            "label": spec.label,
            "data": data,
            "file_name": spec.file_name or f"export_{spec.key}.{spec.key}",
            "mime": spec.mime,
            "caption": spec.caption,
        })
    return items


# ---------------------------------------------------------------------------
# 清洗器：CSV 公式注入 / Markdown / HTML
# ---------------------------------------------------------------------------

# Excel/表格软件会跳过前导空白与控制字符再执行公式，只判断首字符不够：
# \n / \r / \t / NUL / 零宽字符 / Unicode 空白 + 公式同样危险。
_CSV_FORMULA_PREFIX_RE = re.compile(
    r"^[\s\x00-\x1f\u200b-\u200f\u2028\u2029\ufeff]*[=+\-@]"
)


def sanitize_csv_value(value: Any) -> Any:
    text = "" if value is None else str(value)
    if _CSV_FORMULA_PREFIX_RE.match(text):
        return "'" + text
    return value


def sanitize_export_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [
        {str(k): sanitize_csv_value(v) for k, v in dict(row or {}).items()}
        for row in rows
    ]


def csv_bytes(rows: Sequence[Dict[str, Any]]) -> bytes:
    """统一的 CSV 编码（调用方需自行 import pandas）。"""
    import pandas as pd
    cleaned = sanitize_export_rows(list(rows or []))
    return pd.DataFrame(cleaned).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def escape_html(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def escape_markdown_cell(value: Any) -> str:
    text = "" if value is None else str(value)
    text = text.replace("\r\n", " ⏎ ").replace("\n", " ⏎ ").replace("\r", " ⏎ ")
    text = text.replace("|", "\\|").replace("`", "\\`")
    return text


# ---------------------------------------------------------------------------
# 文字摘要 / 配置签名 / 导出快照
# ---------------------------------------------------------------------------

_SUMMARY_TEMPLATES: Dict[str, str] = {
    "results": (
        "本轮共执行 {total} 个用例：通过 {passed}、失败 {failed}、错误 {errors}，成功率 {rate:.1f}%。"
        "{degrade}{failed_hint}{coverage}"
    ),
    "generated": "已生成 {count} 个产物：{files}。{credential_hint}",
}


def register_summary_template(kind: str, template: str, *, replace: bool = False) -> None:
    with _LOCK:
        if kind in _SUMMARY_TEMPLATES and not replace:
            raise ValueError(f"文字摘要模板 {kind!r} 已注册；如需覆盖请传 replace=True")
        _SUMMARY_TEMPLATES[kind] = template


def build_text_summary(kind: str, values: Dict[str, Any]) -> str:
    template = _SUMMARY_TEMPLATES.get(kind, "")
    if not template:
        return ""
    try:
        return template.format(**values)
    except (KeyError, ValueError, TypeError):
        return ""


def compute_signature(payload: Any) -> str:
    try:
        raw = strict_json_dumps(payload, sort_keys=True, separators=(",", ":"))
    except (TypeError, ValueError):
        raw = repr(payload)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_export_payload(
    result: Dict[str, Any],
    *,
    config_snapshot: Optional[Dict[str, Any]] = None,
    input_signature: str = "",
    warnings: Optional[Sequence[str]] = None,
    truncation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    payload = copy.deepcopy(dict(result or {}))
    payload["config_snapshot"] = copy.deepcopy(config_snapshot or {})
    payload["input_signature"] = str(input_signature or "")
    payload["registry_summary"] = get_registry_summary()
    payload["warnings"] = list(warnings or [])
    payload["truncation"] = copy.deepcopy(truncation or {})
    return payload


def get_registry_summary() -> Dict[str, Any]:
    limits = get_automation_limits()
    # 接入状态：区分「真正接入产物链」与「仅登记 label」，避免把不可用能力
    # 当成用户可选项展示（#423/R3-09）。
    live_reports = [s.label for s in _REPORT_TEMPLATES.values() if s.renderer is not None]
    listed_only_reports = [s.label for s in _REPORT_TEMPLATES.values() if s.renderer is None]
    live_exports = [s.label for s in _EXPORT_FORMATS.values() if s.serializer is not None]
    listed_only_exports = [s.label for s in _EXPORT_FORMATS.values() if s.serializer is None]
    return {
        "HTTP 方法": len(_HTTP_METHODS),
        "请求格式": len(_REQUEST_FORMATS),
        "执行模式": len(_EXECUTION_MODES),
        "框架渲染器": len(_FRAMEWORK_RENDERERS),
        "鉴权方式": len(_AUTH_MODES),
        "模板风格": len(_TEMPLATE_STYLES),
        "断言策略": len(_ASSERTION_STRATEGIES),
        "状态码分桶": len(_STATUS_BUCKETS),
        "镜像源": len(_MIRRORS),
        "导入模板": len(_IMPORT_TEMPLATES),
        "报告模板": len(_REPORT_TEMPLATES),
        "导出格式": len(_EXPORT_FORMATS),
        "协议": len(_PROTOCOLS),
        "最大接口数": limits.max_interfaces,
        "最大上传字节": limits.max_upload_bytes,
        "最大超时秒": limits.max_timeout_seconds,
        "最大重试次数": limits.max_retry_times,
        "最大响应体字符": limits.max_response_body_chars,
        "默认校验 SSL": limits.default_verify_ssl,
        "默认允许内网目标": limits.allow_private_targets,
        "默认产物保留凭据": limits.allow_credentials_in_artifacts,
        "接入状态": {
            "已接入报告模板": live_reports,
            "仅登记报告模板": listed_only_reports,
            "已接入导出格式": live_exports,
            "仅登记导出格式": listed_only_exports,
            "已接入框架渲染器": sorted(_FRAMEWORK_RENDERERS),
        },
    }


# ---------------------------------------------------------------------------
# 报告模板 / 导出格式的默认 serializer（产物链真正消费注册点）
# ---------------------------------------------------------------------------

def _default_json_exporter(ctx: Dict[str, Any]) -> str:
    payload = ctx.get("payload")
    if payload is None:
        payload = build_export_payload(
            ctx.get("test_results") or {},
            config_snapshot=ctx.get("config_snapshot"),
            input_signature=ctx.get("input_signature", ""),
            warnings=ctx.get("warnings"),
            truncation=ctx.get("truncation"),
        )
    return strict_json_dumps(payload, indent=2)


def _default_csv_exporter(ctx: Dict[str, Any]) -> Any:
    rows = ctx.get("summary_rows") or []
    if not rows:
        return None
    return csv_bytes(rows)


def _default_markdown_exporter(ctx: Dict[str, Any]) -> Any:
    text = ctx.get("markdown_text")
    return text if text else None


def _default_html_exporter(ctx: Dict[str, Any]) -> Any:
    data = ctx.get("html_bytes")
    return data if data else None


def _default_html_report_renderer(ctx: Dict[str, Any]) -> str:
    """html 报告模板的默认渲染器：把执行结果渲染成完整 HTML 文件。"""
    from qa_toolkit.reporting.report_generator import EnhancedReportGenerator
    gen = EnhancedReportGenerator()
    return gen.generate_detailed_report(
        ctx.get("test_results") or {},
        ctx.get("framework", "pytest"),
        ctx.get("interfaces") or [],
        ctx.get("test_details") or [],
    )


# ---------------------------------------------------------------------------
# 默认注册
# ---------------------------------------------------------------------------

def _install_defaults() -> None:
    global _LIMITS
    _LIMITS = AutomationLimits()

    _PROTOCOLS.clear()
    _PROTOCOLS.update({"http": "HTTP", "https": "HTTPS"})

    _HTTP_METHODS.clear()
    _HTTP_METHODS.update({
        "GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH",
        "DELETE": "DELETE", "HEAD": "HEAD", "OPTIONS": "OPTIONS",
    })

    _REQUEST_FORMATS.clear()
    for spec in [
        RequestFormatSpec("auto", "自动检测", ("auto", "自动", "自动检测")),
        RequestFormatSpec("json", "json=参数", ("json", "json=参数")),
        RequestFormatSpec("data_json", "data=json.dumps()", ("data", "data_json", "json格式(data)", "data=json.dumps()")),
        RequestFormatSpec("form", "form-urlencoded", ("form", "form-urlencoded")),
        RequestFormatSpec("raw", "raw", ("raw", "text", "raw文本")),
    ]:
        _REQUEST_FORMATS[spec.key] = spec

    _EXECUTION_MODES.clear()
    for spec in [
        ExecutionModeSpec("pytest", "pytest", "pytest", "test_interfaces.py", ("pytest",)),
        ExecutionModeSpec("unittest", "unittest", "unittest", "test_interfaces.py", ("unittest",)),
        ExecutionModeSpec("requests_script", "requests脚本", "requests_script", "run_interfaces.py",
                          ("requests_script", "requests脚本", "requests")),
    ]:
        _EXECUTION_MODES[spec.key] = spec
    # 内置三种执行模式的渲染器就地注册，产物链统一消费注册表，
    # 不再依赖 core.generate_test_cases 里的硬编码 if/elif 兜底（#422/R3-08）。
    # 延迟 import 断开 core <-> registry 循环依赖。
    _FRAMEWORK_RENDERERS.clear()
    for mode_key, method_name in (
        ("pytest", "_render_pytest_file"),
        ("unittest", "_render_unittest_file"),
        ("requests_script", "_render_requests_script"),
    ):
        def _builtin_renderer(cases: List[Dict[str, Any]], config: Dict[str, Any],
                              _method: str = method_name) -> str:
            from qa_toolkit.core.api_test_core import InterfaceAutoTestCore
            return getattr(InterfaceAutoTestCore(), _method)(cases, config)
        _FRAMEWORK_RENDERERS[mode_key] = _builtin_renderer

    _AUTH_MODES.clear()
    for spec in [
        AuthModeSpec("none", "无", lambda cfg: {}, ()),
        AuthModeSpec("bearer", "Bearer Token", _bearer_builder, ("token",)),
        AuthModeSpec("api_key", "API Key", _api_key_builder, ("api_key_value",)),
        AuthModeSpec("basic", "Basic Auth", _basic_builder, ("password",)),
        AuthModeSpec("custom_header", "自定义Header", _custom_header_builder, ("custom_header_value",)),
    ]:
        _AUTH_MODES[spec.mode] = spec

    _TEMPLATE_STYLES.clear()
    for spec in [
        TemplateStyleSpec("smoke", "冒烟模板", "smoke", "只校验状态码，先跑通"),
        TemplateStyleSpec("standard", "标准模板", "standard", "递归校验期望响应中出现的字段"),
        TemplateStyleSpec("strict", "严格模板", "strict", "递归校验且要求键集合/数组长度一致"),
    ]:
        _TEMPLATE_STYLES[spec.key] = spec
    _ASSERTION_STRATEGIES.clear()
    _ASSERTION_STRATEGIES.update({"smoke": "冒烟", "standard": "标准", "strict": "严格"})

    _STATUS_BUCKETS.clear()
    for spec in [
        StatusCodeBucketSpec("informational", "1xx 信息响应", 100, 199),
        StatusCodeBucketSpec("success", "2xx 成功", 200, 299),
        StatusCodeBucketSpec("redirect", "3xx 重定向", 300, 399),
        StatusCodeBucketSpec("client_error", "4xx 客户端错误", 400, 499, True),
        StatusCodeBucketSpec("server_error", "5xx 服务端错误", 500, 599, True),
    ]:
        _STATUS_BUCKETS[spec.key] = spec

    _MIRRORS.clear()
    _MIRRORS.update({
        "清华镜像": "https://pypi.tuna.tsinghua.edu.cn/simple/",
        "阿里云镜像": "https://mirrors.aliyun.com/pypi/simple/",
        "豆瓣镜像": "https://pypi.douban.com/simple/",
        "中科大镜像": "https://pypi.mirrors.ustc.edu.cn/simple/",
    })

    _IMPORT_TEMPLATES.clear()
    for spec in [
        ImportTemplateSpec("📥 Excel 模板", "build_excel_template_bytes", "api_automation_template.xlsx",
                           "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "适合表格方式维护接口清单。"),
        ImportTemplateSpec("📥 JSON 模板", "build_json_template", "api_automation_template.json", "application/json", "适合结构化接口列表导入。"),
        ImportTemplateSpec("📥 文本模板", "build_text_template", "api_automation_template.txt", "text/plain", "适合快速手工拼装接口块。"),
        ImportTemplateSpec("📥 curl 模板", "build_curl_template", "api_automation_curl_template.txt", "text/plain", "适合终端命令或抓包回放。"),
        ImportTemplateSpec("📥 OpenAPI JSON", "build_openapi_template", "api_automation_openapi.json", "application/json", "适合 Swagger/OpenAPI 文档导入。"),
        ImportTemplateSpec("📥 OpenAPI YAML", "build_openapi_yaml_template", "api_automation_openapi.yaml", "text/yaml", "适合 YAML 版 OpenAPI 文档。"),
        ImportTemplateSpec("📥 Postman 模板", "build_postman_template", "api_automation_postman.json", "application/json", "适合集合导出后直接导入。"),
        ImportTemplateSpec("📥 HAR 模板", "build_har_template", "api_automation_sample.har", "application/json", "适合浏览器抓包回放。"),
        ImportTemplateSpec("📥 Apifox 模板", "build_apifox_template", "api_automation_apifox.json", "application/json", "提供 Apifox 兼容骨架。"),
        ImportTemplateSpec("📥 Bruno 模板", "build_bruno_template", "api_automation_sample.bru", "text/plain", "适合 Bruno 单接口文件导入。"),
        ImportTemplateSpec("📥 Insomnia 模板", "build_insomnia_template", "api_automation_insomnia.json", "application/json", "适合 Insomnia 导出 JSON 回放。"),
        ImportTemplateSpec("📥 环境配置模板", "build_environment_template", "api_automation_environment.json", "application/json", "维护 dev/staging/prod 基础地址和公共头。"),
        ImportTemplateSpec("📥 鉴权模板", "build_auth_template", "api_automation_auth.json", "application/json", "统一配置 Bearer / API Key / Basic / 自定义 Header。"),
    ]:
        _IMPORT_TEMPLATES[spec.label] = spec

    _REPORT_TEMPLATES.clear()
    # html 模板绑定真实 renderer（消费报告模板注册点）；simple_html 只登记 label，
    # 在「接入状态」里显式标注为仅登记，避免误导（#423/R3-09）。
    _REPORT_TEMPLATES["html"] = ReportTemplateSpec("html", "HTML 详细报告", _default_html_report_renderer)
    _REPORT_TEMPLATES["simple_html"] = ReportTemplateSpec("simple_html", "HTML 简要报告", None)
    _EXPORT_FORMATS.clear()
    _EXPORT_FORMATS["json"] = ExportFormatSpec(
        "json", "JSON 结果", "api_automation_result.json", "application/json",
        "附配置快照与输入签名。", _default_json_exporter)
    _EXPORT_FORMATS["csv"] = ExportFormatSpec(
        "csv", "CSV 摘要", "api_automation_summary.csv", "text/csv",
        "统一走注册式公式注入清洗。", _default_csv_exporter)
    _EXPORT_FORMATS["markdown"] = ExportFormatSpec(
        "markdown", "Markdown 摘要", "api_automation_summary.md", "text/markdown",
        "附配置快照与输入签名。", _default_markdown_exporter)
    _EXPORT_FORMATS["html"] = ExportFormatSpec(
        "html", "HTML 报告", "api_automation_report.html", "text/html",
        "适合直接归档或浏览器查看。", _default_html_exporter)

    _SUMMARY_TEMPLATES.clear()
    _SUMMARY_TEMPLATES.update({
        "results": "本轮共执行 {total} 个用例：通过 {passed}、失败 {failed}、错误 {errors}，成功率 {rate:.1f}%。{degrade}{failed_hint}{coverage}",
        "generated": "已生成 {count} 个产物：{files}。{credential_hint}",
    })


def reset_automation_registry() -> None:
    """恢复默认注册表与上限；测试之间调用，避免全局状态污染。"""
    with _LOCK:
        _install_defaults()


_install_defaults()
