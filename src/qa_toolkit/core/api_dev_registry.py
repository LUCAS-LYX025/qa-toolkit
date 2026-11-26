"""接口研发辅助工具：注册式扩展点。

设计目标（不局限于当前业务）：
- HTTP 方法、代码片段语言与渲染器、质量检查规则与评分口径、严重级别/风险等级、
  词表（鉴权/分页/排序）、回归清单文案、优先级策略、Mock 默认响应头与资源上限、
  协议白名单、Header 校验、CSV/Markdown 清洗器、运行上限全部通过 ``register_*`` /
  ``get_*`` 暴露；
- 下游项目想新增一种调试语言（Go / Java / PowerShell）、换一套健康分权重、
  加自定义质量规则或自定义 Mock 响应头，只需调用注册接口，不需要改 core / page；
- frozen dataclass Spec + query 返回副本 + 重复注册需 ``replace=True``，避免全局
  注册表被页面或测试意外污染；``reset_dev_registry()`` 保证测试隔离。

与 ``api_performance_registry.py`` / ``api_security_registry.py`` 的安全护栏语义
保持一致（协议白名单、userinfo 拒绝、端口校验、内网/元数据地址拦截、默认开启
SSL 校验），但注册表相互独立，便于各自演进。
"""
from __future__ import annotations

import copy
import hashlib
import ipaddress
import json
import math
import pprint
import re
import shlex
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
    return min(max(to_float(value, default), minimum), maximum)


def clamp_int(value: Any, default: int, minimum: int, maximum: int) -> int:
    return min(max(to_int(value, default), minimum), maximum)


# ---------------------------------------------------------------------------
# 运行上限与安全默认值
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DevLimits:
    max_interfaces: int = 500
    max_sample_bytes: int = 512_000
    max_mock_routes: int = 300
    max_script_chars: int = 2_000_000
    max_export_chars: int = 2_000_000
    max_recursion_depth: int = 12
    max_field_paths: int = 500
    max_delay_ms: int = 10_000
    max_request_body_bytes: int = 1_048_576
    max_response_body_chars: int = 200_000
    max_header_value_chars: int = 8_000
    max_name_chars: int = 200
    min_timeout_seconds: float = 1.0
    max_timeout_seconds: float = 60.0
    default_timeout_seconds: float = 30.0
    default_verify_ssl: bool = True
    default_mock_host: str = "127.0.0.1"
    default_mock_port: int = 8000
    min_port: int = 1
    max_port: int = 65535
    default_enable_cors: bool = True
    default_cors_origin: str = "http://localhost:3000"
    allow_private_targets: bool = False
    verify_ssl_by_default: bool = True


_LIMITS = DevLimits()


def configure_dev_limits(**kwargs: Any) -> DevLimits:
    """按关键字更新运行上限；未知字段直接报错，避免拼写错误静默失效。"""
    global _LIMITS
    allowed = set(DevLimits.__dataclass_fields__)
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知的接口研发辅助配置项: {sorted(unknown)}")
    for key, value in kwargs.items():
        if isinstance(value, (bool, str)):
            continue
        if isinstance(value, (int, float)) and (not math.isfinite(float(value)) or float(value) < 0):
            raise ValueError(f"配置项 {key!r} 必须是非负有限数，收到: {value!r}")
    with _LOCK:
        _LIMITS = _dc_replace(_LIMITS, **kwargs)
        return _LIMITS


def get_dev_limits() -> DevLimits:
    with _LOCK:
        return _LIMITS


# ---------------------------------------------------------------------------
# 协议白名单 / SSRF 护栏
# ---------------------------------------------------------------------------

_PROTOCOLS: Dict[str, str] = {"http": "HTTP", "https": "HTTPS"}
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


def register_protocol(scheme: str, label: str = "", *, replace: bool = False) -> None:
    """注册允许的目标协议；默认仅 http/https。"""
    name = str(scheme).strip().lower()
    if not name or not re.fullmatch(r"[a-z][a-z0-9+.-]*", name):
        raise ValueError(f"非法协议名: {scheme!r}")
    with _LOCK:
        if name in _PROTOCOLS and not replace:
            raise ValueError(f"协议 {name!r} 已注册；如需覆盖请传 replace=True")
        _PROTOCOLS[name] = str(label or name.upper())


def get_protocols() -> Tuple[str, ...]:
    with _LOCK:
        return tuple(sorted(_PROTOCOLS))


def _is_private_host(host: str) -> bool:
    text = (host or "").strip().lower().rstrip(".")
    if not text:
        return True
    if text in _METADATA_HOSTS or text.endswith(".internal") or text == "localhost":
        return True
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return False
    return any(address in network for network in _PRIVATE_NETWORKS) or not address.is_global


def validate_target_url(url: str, *, allow_private: Optional[bool] = None) -> Tuple[bool, str]:
    """校验 base_url / 目标地址：协议、userinfo、端口、内网与元数据地址。"""
    text = str(url or "").strip()
    if not text:
        return False, "目标地址为空，请填写以 http/https 开头的完整地址"
    parsed = urlparse(text)
    scheme = (parsed.scheme or "").lower()
    allowed = get_protocols()
    if scheme not in allowed:
        return False, f"不支持的协议 {scheme or '(空)'}，仅允许：{'、'.join(allowed)}"
    if not parsed.hostname:
        return False, "目标地址缺少主机名"
    if parsed.username or parsed.password:
        return False, "目标地址不允许携带 userinfo（user:pass@host）"
    try:
        port = parsed.port
    except ValueError:
        return False, "端口号必须是 1-65535 的整数"
    limits = get_dev_limits()
    if port is not None and not (limits.min_port <= port <= limits.max_port):
        return False, f"端口号必须是 {limits.min_port}-{limits.max_port} 的整数"
    allow = _LIMITS.allow_private_targets if allow_private is None else bool(allow_private)
    if not allow and _is_private_host(parsed.hostname):
        return False, "目标为内网/回环/链路本地/元数据地址；如需联调本地服务请显式开启「允许内网/本地目标」"
    return True, ""


# ---------------------------------------------------------------------------
# Header 校验（RFC 7230 token + CRLF / 控制字符 / 长度）
# ---------------------------------------------------------------------------

_HEADER_TOKEN_RE = re.compile(r"^[!#$%&'*+\-.^_`|~0-9A-Za-z]+$")


def validate_header_name(name: Any) -> Tuple[bool, str]:
    text = str(name or "").strip()
    if not _HEADER_TOKEN_RE.fullmatch(text):
        return False, f"请求头名 {text!r} 含非法字符（仅允许 RFC 7230 token）"
    return True, ""


def validate_header_value(value: Any, *, max_chars: Optional[int] = None) -> Tuple[bool, str]:
    text = "" if value is None else str(value)
    limit = int(max_chars or get_dev_limits().max_header_value_chars)
    if any(ord(ch) < 32 and ch not in "\t" for ch in text) or "\x7f" in text:
        return False, "请求头值含换行或控制字符，已拒绝以防止请求头注入"
    if len(text) > limit:
        return False, f"请求头值超过 {limit} 字符上限"
    return True, ""


def validate_request_headers(headers: Optional[Dict[str, Any]]) -> Tuple[Dict[str, str], List[str]]:
    """返回清洗后的请求头 + 告警；非法项直接丢弃，绝不进入代码片段或 Mock 脚本。"""
    cleaned: Dict[str, str] = {}
    warnings: List[str] = []
    if not isinstance(headers, dict):
        return cleaned, warnings
    for key, value in headers.items():
        ok_name, name_error = validate_header_name(key)
        if not ok_name:
            warnings.append(f"已跳过请求头：{name_error}")
            continue
        ok_value, value_error = validate_header_value(value)
        if not ok_value:
            warnings.append(f"已跳过请求头 {key!r}：{value_error}")
            continue
        cleaned[str(key)] = "" if value is None else str(value)
    return cleaned, warnings


# ---------------------------------------------------------------------------
# HTTP 方法白名单
# ---------------------------------------------------------------------------

_HTTP_METHODS: Dict[str, str] = {
    "GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH",
    "DELETE": "DELETE", "HEAD": "HEAD", "OPTIONS": "OPTIONS",
}


def register_http_method(method: str, label: str = "", *, replace: bool = False) -> None:
    name = str(method).strip().upper()
    if not name or not re.fullmatch(r"[A-Z][A-Z0-9_-]*", name):
        raise ValueError(f"非法 HTTP 方法: {method!r}")
    with _LOCK:
        if name in _HTTP_METHODS and not replace:
            raise ValueError(f"HTTP 方法 {name!r} 已注册；如需覆盖请传 replace=True")
        _HTTP_METHODS[name] = str(label or name)


def get_http_methods() -> Tuple[str, ...]:
    with _LOCK:
        return tuple(sorted(_HTTP_METHODS))


def normalize_method(value: Any, default: str = "GET") -> Tuple[str, str]:
    """归一化 HTTP 方法；非法值回落默认值并返回告警，杜绝代码拼接注入。"""
    text = str(value or default).strip().upper()
    if text in _HTTP_METHODS:
        return text, ""
    return default, f"非法 HTTP 方法 {str(value)!r}，已回落为 {default}（仅允许：{'、'.join(get_http_methods())}）"


# ---------------------------------------------------------------------------
# 代码片段语言与渲染器
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SnippetLanguageSpec:
    label: str
    renderer_key: str
    highlight: str = "text"
    download_suffix: str = "txt"
    aliases: Tuple[str, ...] = ()
    include_query_in_url: bool = False


_SNIPPET_LANGUAGES: Dict[str, SnippetLanguageSpec] = {
    "Python requests": SnippetLanguageSpec(
        "Python requests", "python_requests", "python", "py", ("python", "requests"),
    ),
    "JavaScript fetch": SnippetLanguageSpec(
        "JavaScript fetch", "javascript_fetch", "javascript", "js", ("js", "fetch", "javascript"),
    ),
    "curl": SnippetLanguageSpec(
        "curl", "curl", "bash", "sh", ("bash", "shell", "cURL"), include_query_in_url=True,
    ),
}


def register_snippet_language(spec: SnippetLanguageSpec, *, replace: bool = False) -> None:
    if not isinstance(spec, SnippetLanguageSpec):
        raise TypeError("spec 必须是 SnippetLanguageSpec")
    with _LOCK:
        if spec.label in _SNIPPET_LANGUAGES and not replace:
            raise ValueError(f"代码片段语言 {spec.label!r} 已注册；如需覆盖请传 replace=True")
        _SNIPPET_LANGUAGES[spec.label] = spec


def get_snippet_languages() -> List[SnippetLanguageSpec]:
    with _LOCK:
        return [copy.deepcopy(item) for item in _SNIPPET_LANGUAGES.values()]


def resolve_snippet_language(label: Any) -> Tuple[Optional[SnippetLanguageSpec], str]:
    """按标签或别名解析语言；未知语言返回 None + 明确告警，绝不静默回落。"""
    text = str(label or "").strip()
    with _LOCK:
        for key, spec in _SNIPPET_LANGUAGES.items():
            if text == key or text.lower() == key.lower() or text.lower() in {a.lower() for a in spec.aliases}:
                return copy.deepcopy(spec), ""
        return None, f"未知代码类型 {text!r}，已支持：{'、'.join(_SNIPPET_LANGUAGES)}"


# 渲染器签名： (method, full_url, headers, query_params, body, options) -> str
SnippetRenderer = Callable[[str, str, Dict[str, Any], Dict[str, Any], Any, Dict[str, Any]], str]
_SNIPPET_RENDERERS: Dict[str, SnippetRenderer] = {}


def register_snippet_renderer(key: str, renderer: SnippetRenderer, *, replace: bool = False) -> None:
    name = str(key).strip()
    if not name or not callable(renderer):
        raise ValueError("渲染器需要非空 key 与可调用对象")
    with _LOCK:
        if name in _SNIPPET_RENDERERS and not replace:
            raise ValueError(f"渲染器 {name!r} 已注册；如需覆盖请传 replace=True")
        _SNIPPET_RENDERERS[name] = renderer


def get_snippet_renderer(key: str) -> Optional[SnippetRenderer]:
    with _LOCK:
        return _SNIPPET_RENDERERS.get(key)


def _is_payload(value: Any) -> bool:
    return value not in (None, "", {}, [])


_REQUESTS_VERBS: Dict[str, str] = {
    "GET": "get", "POST": "post", "PUT": "put", "PATCH": "patch",
    "DELETE": "delete", "HEAD": "head", "OPTIONS": "options",
}


def register_requests_verb(method: str, verb: str, *, replace: bool = False) -> None:
    """注册 HTTP 方法到 requests 函数名的映射；未注册的方法走参数化 request()。"""
    name = str(method).strip().upper()
    fn = str(verb).strip()
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", fn):
        raise ValueError(f"非法 requests 函数名: {verb!r}")
    with _LOCK:
        if name in _REQUESTS_VERBS and not replace:
            raise ValueError(f"方法 {name!r} 的 requests 映射已注册；如需覆盖请传 replace=True")
        _REQUESTS_VERBS[name] = fn


def get_requests_verb(method: str) -> Optional[str]:
    with _LOCK:
        return _REQUESTS_VERBS.get(str(method).strip().upper())


def format_python_literal(value: Any) -> str:
    """把接口数据渲染成**合法 Python 字面量**。

    ``json.dumps`` 会输出 ``true`` / ``false`` / ``null``，在 Python 里它们是
    未定义的变量名（compile 能过、运行必 NameError）。这里改用 ``repr`` 家族，
    同时把非有限浮点压成 None，保证片段复制即可执行、导出即是严格 JSON。
    """

    def _clean(item: Any) -> Any:
        if isinstance(item, dict):
            return {str(key): _clean(val) for key, val in item.items()}
        if isinstance(item, (list, tuple, set)):
            return [_clean(val) for val in item]
        if isinstance(item, float) and not math.isfinite(item):
            return None
        return item

    return pprint.pformat(_clean(value), width=88, sort_dicts=False)


def strict_json_dumps(value: Any, **kwargs: Any) -> str:
    """严格 JSON 序列化：非有限浮点一律清洗为 null，禁止 NaN/Infinity 字面量。"""
    kwargs.setdefault("ensure_ascii", False)
    return json.dumps(_sanitize_json_numbers(value)[0], allow_nan=False, **kwargs)


def _sanitize_json_numbers(value: Any) -> Tuple[Any, List[str]]:
    warnings: List[str] = []
    seen: set = set()

    def _walk(item: Any) -> Any:
        if isinstance(item, float) and not math.isfinite(item):
            warnings.append("检测到 NaN/Infinity 等非有限数值，已转为 null 以保证 JSON 合法")
            return None
        if isinstance(item, dict):
            if id(item) in seen:
                return {}
            seen.add(id(item))
            return {str(key): _walk(val) for key, val in item.items()}
        if isinstance(item, (list, tuple)):
            if id(item) in seen:
                return []
            seen.add(id(item))
            return [_walk(val) for val in item]
        return item

    return _walk(value), warnings


def _render_python_requests(method, full_url, headers, query_params, body, options):
    timeout = options.get("timeout_seconds", 30.0)
    verify = options.get("verify_ssl", True)
    lines = [
        "import requests",
        "",
        f"url = {format_python_literal(full_url)}",
        f"headers = {format_python_literal(headers or {})}",
    ]
    if query_params:
        lines.append(f"params = {format_python_literal(query_params)}")
    if _is_payload(body):
        lines.append(f"payload = {format_python_literal(body)}")
    lines.append("")
    verb = get_requests_verb(method)
    if verb:
        parts = [f"response = requests.{verb}(", "    url,"]
    else:
        parts = ["response = requests.request(", f"    {json.dumps(method)},", "    url,"]
    if headers:
        parts.append("    headers=headers,")
    if query_params:
        parts.append("    params=params,")
    if _is_payload(body):
        parts.append("    json=payload," if isinstance(body, (dict, list)) else "    data=payload,")
    parts.extend([
        f"    timeout={float(timeout)!r},",
        f"    verify={bool(verify)!r},",
        ")",
        "print(response.status_code)",
        "print(response.text)",
    ])
    lines.extend(parts)
    return "\n".join(lines)


def _render_javascript_fetch(method, full_url, headers, query_params, body, options):
    lines = [f"const url = {json.dumps(full_url, ensure_ascii=False)};"]
    if query_params:
        lines.extend([
            f"const params = {json.dumps(query_params, ensure_ascii=False, indent=2)};",
            "const query = new URLSearchParams(params).toString();",
            "const requestUrl = query ? `${url}${url.includes('?') ? '&' : '?'}${query}` : url;",
        ])
    else:
        lines.append("const requestUrl = url;")
    if _is_payload(body):
        lines.append(f"const payload = {json.dumps(body, ensure_ascii=False, indent=2)};")
    options_obj: Dict[str, Any] = {"method": method}
    if headers:
        options_obj["headers"] = headers
    lines.append(f"const options = {json.dumps(options_obj, ensure_ascii=False, indent=2)};")
    if _is_payload(body):
        lines.append("options.body = JSON.stringify(payload);" if isinstance(body, (dict, list)) else "options.body = payload;")
    lines.extend([
        "",
        "fetch(requestUrl, options)",
        "  .then((response) => response.text().then((text) => ({ status: response.status, text })))",
        "  .then(({ status, text }) => { console.log(status); console.log(text); });",
    ])
    return "\n".join(lines)


def _render_curl(method, full_url, headers, query_params, body, options):
    parts = [f"curl -X {shlex.quote(str(method))} {shlex.quote(full_url)}"]
    for key, value in headers.items():
        parts.append(f"  -H {shlex.quote(f'{key}: {value}')}")
    if _is_payload(body):
        payload = json.dumps(body, ensure_ascii=False) if isinstance(body, (dict, list)) else str(body)
        parts.append(f"  -d {shlex.quote(payload)}")
    return " \\\n".join(parts)


for _key, _renderer in (
    ("python_requests", _render_python_requests),
    ("javascript_fetch", _render_javascript_fetch),
    ("curl", _render_curl),
):
    _SNIPPET_RENDERERS[_key] = _renderer


# ---------------------------------------------------------------------------
# 质量规则 / 评分口径 / 严重级别 / 风险等级
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class QualityRuleSpec:
    key: str
    severity: str = "medium"
    message: str = ""
    enabled: bool = True


_QUALITY_RULES: Dict[str, QualityRuleSpec] = {
    "missing_name": QualityRuleSpec("missing_name", "medium", "接口名称为空"),
    "missing_description": QualityRuleSpec("missing_description", "low", "接口描述为空，后续维护成本会偏高"),
    "missing_expected_response": QualityRuleSpec("missing_expected_response", "medium", "缺少期望响应示例，自动断言会偏弱"),
    "path_param_missing": QualityRuleSpec("path_param_missing", "high", "路径占位符缺少参数: {detail}"),
    "path_param_extra": QualityRuleSpec("path_param_extra", "medium", "存在未在路径中使用的 path 参数: {detail}"),
    "path_param_empty": QualityRuleSpec("path_param_empty", "medium", "路径参数值为空: {detail}"),
    "get_with_body": QualityRuleSpec("get_with_body", "medium", "GET 请求携带 body，兼容性风险较高"),
    "empty_request_body": QualityRuleSpec("empty_request_body", "low", "{method} 请求未提供 body，请确认是否符合接口设计"),
    "missing_content_type": QualityRuleSpec("missing_content_type", "medium", "请求体存在但未声明 Content-Type"),
    "json_content_type_mismatch": QualityRuleSpec("json_content_type_mismatch", "medium", "请求格式为 JSON，但 Content-Type 不是 application/json"),
    "form_content_type_mismatch": QualityRuleSpec("form_content_type_mismatch", "medium", "请求格式为 form，但 Content-Type 不是 form 类型"),
    "missing_tags": QualityRuleSpec("missing_tags", "low", "未配置标签，后续分组与筛选不方便"),
    "duplicate_endpoint": QualityRuleSpec("duplicate_endpoint", "high", "与其他接口重复定义，重复序号: {detail}"),
    "invalid_expected_status": QualityRuleSpec("invalid_expected_status", "high", "期望状态码 {detail} 不在合法 HTTP 范围（100-599）"),
    "unexpected_status_bucket": QualityRuleSpec("unexpected_status_bucket", "medium", "期望状态码落在{detail}分桶，请确认接口契约是否刻意为错误场景"),
}

_SEVERITY_ORDER: Dict[str, int] = {"high": 0, "medium": 1, "low": 2}
_SCORE_WEIGHTS: Dict[str, int] = {"high": 18, "medium": 8, "low": 3}
_HEALTH_BANDS: List[Tuple[int, str]] = [(90, "优秀"), (75, "良好"), (60, "一般"), (0, "需整改")]
_RISK_LEVELS: Dict[int, str] = {0: "low", 1: "low", 2: "medium", 3: "high"}


# ---------------------------------------------------------------------------
# 状态码分桶（注册式，下游可自定义分桶边界与文案）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StatusCodeBucketSpec:
    key: str
    label: str
    min_code: int
    max_code: int
    warn: bool = False


_STATUS_CODE_BUCKETS: Dict[str, StatusCodeBucketSpec] = {
    "informational": StatusCodeBucketSpec("informational", "1xx 信息响应", 100, 199),
    "success": StatusCodeBucketSpec("success", "2xx 成功", 200, 299),
    "redirect": StatusCodeBucketSpec("redirect", "3xx 重定向", 300, 399),
    "client_error": StatusCodeBucketSpec("client_error", "4xx 客户端错误", 400, 499, True),
    "server_error": StatusCodeBucketSpec("server_error", "5xx 服务端错误", 500, 599, True),
}


def register_status_bucket(spec: StatusCodeBucketSpec, *, replace: bool = False) -> None:
    if not isinstance(spec, StatusCodeBucketSpec):
        raise TypeError("spec 必须是 StatusCodeBucketSpec")
    if spec.min_code > spec.max_code:
        raise ValueError("状态码分桶下界不能大于上界")
    with _LOCK:
        if spec.key in _STATUS_CODE_BUCKETS and not replace:
            raise ValueError(f"状态码分桶 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _STATUS_CODE_BUCKETS[spec.key] = spec


def get_status_buckets() -> Dict[str, StatusCodeBucketSpec]:
    with _LOCK:
        return {key: copy.deepcopy(spec) for key, spec in _STATUS_CODE_BUCKETS.items()}


def classify_status_code(value: Any, default: int = 200) -> Dict[str, Any]:
    """返回状态码是否合法、所属分桶与是否应告警，供体检/清单/报告共用。"""
    code = to_int(value, default)
    if not 100 <= code <= 599:
        return {"valid": False, "code": code, "bucket": "invalid", "label": "非法状态码", "warn": True}
    with _LOCK:
        buckets = list(_STATUS_CODE_BUCKETS.values())
    for spec in buckets:
        if spec.min_code <= code <= spec.max_code:
            return {"valid": True, "code": code, "bucket": spec.key,
                    "label": spec.label, "warn": spec.warn}
    return {"valid": True, "code": code, "bucket": "unclassified",
            "label": "未分类", "warn": False}


def register_quality_rule(spec: QualityRuleSpec, *, replace: bool = False) -> None:
    if not isinstance(spec, QualityRuleSpec):
        raise TypeError("spec 必须是 QualityRuleSpec")
    with _LOCK:
        if spec.key in _QUALITY_RULES and not replace:
            raise ValueError(f"质量规则 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _QUALITY_RULES[spec.key] = spec


def get_quality_rules() -> Dict[str, QualityRuleSpec]:
    with _LOCK:
        return {key: copy.deepcopy(spec) for key, spec in _QUALITY_RULES.items()}


def build_quality_issue(key: str, *, detail: str = "", method: str = "") -> Tuple[str, str]:
    """返回 (severity, message)；规则被禁用时返回空消息，调用方跳过该条。"""
    with _LOCK:
        spec = _QUALITY_RULES.get(key)
        if spec is None or not spec.enabled:
            return "", ""
        return spec.severity, spec.message.format(detail=detail, method=method)


def register_severity(name: str, rank: int, *, replace: bool = False) -> None:
    key = str(name).strip().lower()
    with _LOCK:
        if key in _SEVERITY_ORDER and not replace:
            raise ValueError(f"严重级别 {key!r} 已注册；如需覆盖请传 replace=True")
        _SEVERITY_ORDER[key] = int(rank)


def get_severity_order() -> Dict[str, int]:
    with _LOCK:
        return dict(_SEVERITY_ORDER)


def configure_score_weights(**weights: int) -> Dict[str, int]:
    with _LOCK:
        for key, value in weights.items():
            if key not in _SCORE_WEIGHTS:
                raise ValueError(f"未知严重级别 {key!r}，请先 register_severity()")
            _SCORE_WEIGHTS[key] = max(0, int(value))
        return dict(_SCORE_WEIGHTS)


def get_score_weights() -> Dict[str, int]:
    with _LOCK:
        return dict(_SCORE_WEIGHTS)


def register_health_band(threshold: int, label: str, *, replace: bool = False) -> None:
    with _LOCK:
        for index, (value, _) in enumerate(_HEALTH_BANDS):
            if value == int(threshold):
                if not replace:
                    raise ValueError(f"健康分阈值 {threshold} 已注册；如需覆盖请传 replace=True")
                _HEALTH_BANDS[index] = (int(threshold), str(label))
                _HEALTH_BANDS.sort(key=lambda item: item[0], reverse=True)
                return
        _HEALTH_BANDS.append((int(threshold), str(label)))
        _HEALTH_BANDS.sort(key=lambda item: item[0], reverse=True)


def health_level(score: int) -> str:
    with _LOCK:
        for threshold, label in _HEALTH_BANDS:
            if score >= threshold:
                return label
        return _HEALTH_BANDS[-1][1] if _HEALTH_BANDS else "未知"


def register_risk_level(rank: int, level: str, *, replace: bool = False) -> None:
    with _LOCK:
        if int(rank) in _RISK_LEVELS and not replace:
            raise ValueError(f"风险等级 {rank} 已注册；如需覆盖请传 replace=True")
        _RISK_LEVELS[int(rank)] = str(level)


def risk_level(rank: int) -> str:
    with _LOCK:
        return _RISK_LEVELS.get(int(rank), _RISK_LEVELS.get(0, "low"))


# ---------------------------------------------------------------------------
# 词表 / 回归清单文案 / 优先级策略
# ---------------------------------------------------------------------------

_HINTS: Dict[str, Tuple[str, ...]] = {
    "auth_header": ("authorization", "token", "api-key", "apikey", "x-auth", "access-key"),
    "auth_text": ("auth", "login", "logout", "token", "signin", "sign-in", "鉴权", "登录", "认证"),
    "pagination": ("page", "pagenum", "pageno", "size", "pagesize", "limit", "offset"),
    "sort": ("sort", "order", "orderby", "sortby", "direction", "filter", "keyword"),
}


def register_hint(group: str, *values: str) -> None:
    key = str(group).strip()
    with _LOCK:
        merged = list(_HINTS.get(key, ()))
        for value in values:
            text = str(value).strip().lower()
            if text and text not in merged:
                merged.append(text)
        _HINTS[key] = tuple(merged)


def get_hints(group: str) -> Tuple[str, ...]:
    with _LOCK:
        return tuple(_HINTS.get(group, ()))


_CHECKLIST_TEMPLATES: Dict[str, str] = {
    "status": "校验状态码为 {expected_status}",
    "response_fields": "校验关键响应字段和业务码",
    "response_missing": "补充最小可用响应断言",
    "performance": "关注响应时间是否在可接受范围内",
    "query_normal": "覆盖查询参数正常组合",
    "query_negative": "验证查询参数缺失、非法值、边界值",
    "path_normal": "验证路径参数替换后的资源是否正确",
    "path_negative": "验证无效路径参数、越权访问或不存在资源",
    "body_normal": "覆盖请求体必填字段、类型和边界值",
    "body_negative": "验证请求体字段缺失、超长、非法格式",
    "auth_normal": "验证有效鉴权下接口可正常访问",
    "auth_negative": "验证缺少鉴权、鉴权失效、权限不足场景",
    "mutation_normal": "确认接口对数据的新增、更新或删除结果正确",
    "mutation_negative": "验证重复提交、幂等性或回滚处理",
    "pagination": "验证分页参数、总数、页码边界和空列表场景",
    "sort": "验证排序字段和筛选条件组合",
}


def register_checklist_template(key: str, text: str, *, replace: bool = False) -> None:
    with _LOCK:
        if key in _CHECKLIST_TEMPLATES and not replace:
            raise ValueError(f"清单文案 {key!r} 已注册；如需覆盖请传 replace=True")
        _CHECKLIST_TEMPLATES[key] = str(text)


def get_checklist_templates() -> Dict[str, str]:
    with _LOCK:
        return dict(_CHECKLIST_TEMPLATES)


PriorityPredicate = Callable[[Dict[str, Any]], bool]
_PRIORITY_RULES: List[Tuple[str, str, PriorityPredicate]] = [
    ("mutation", "high", lambda item: item.get("method") in {"POST", "PUT", "PATCH", "DELETE"}),
    ("auth_or_path", "high", lambda item: bool(item.get("path_params")) or _auth_related(item)),
    ("body", "high", lambda item: item.get("body") not in (None, "", {}, [])),
    ("query", "medium", lambda item: bool(item.get("query_params"))),
]


def _auth_related(item: Dict[str, Any]) -> bool:
    headers = item.get("headers") or {}
    if any(any(word in str(key).lower() for word in get_hints("auth_header")) for key in headers):
        return True
    candidates = [item.get("name"), item.get("path"), item.get("description"), " ".join(item.get("tags") or [])]
    return any(
        any(word in str(candidate or "").lower() for word in get_hints("auth_text"))
        for candidate in candidates
    )


def register_priority_rule(name: str, priority: str, predicate: PriorityPredicate, *, replace: bool = False) -> None:
    with _LOCK:
        for index, (existing, _, _) in enumerate(_PRIORITY_RULES):
            if existing == name:
                if not replace:
                    raise ValueError(f"优先级规则 {name!r} 已注册；如需覆盖请传 replace=True")
                _PRIORITY_RULES[index] = (name, str(priority), predicate)
                return
        _PRIORITY_RULES.append((name, str(priority), predicate))


def decide_priority(item: Dict[str, Any]) -> str:
    with _LOCK:
        rules = list(_PRIORITY_RULES)
    for _, priority, predicate in rules:
        try:
            if predicate(item):
                return priority
        except Exception:
            continue
    return "low"


# ---------------------------------------------------------------------------
# Mock 默认响应头 / 资源上限
# ---------------------------------------------------------------------------

_MOCK_DEFAULT_HEADERS: Dict[str, str] = {"Cache-Control": "no-store"}
_MOCK_HEADER_ALLOWLIST: Tuple[str, ...] = ("Set-Cookie", "X-Trace-Id")


def register_mock_default_header(name: str, value: str, *, replace: bool = False) -> None:
    ok, error = validate_header_name(name)
    if not ok:
        raise ValueError(error)
    with _LOCK:
        if name in _MOCK_DEFAULT_HEADERS and not replace:
            raise ValueError(f"Mock 默认响应头 {name!r} 已注册；如需覆盖请传 replace=True")
        _MOCK_DEFAULT_HEADERS[name] = str(value)


def register_mock_header_allowlist(*names: str) -> None:
    global _MOCK_HEADER_ALLOWLIST
    with _LOCK:
        merged = list(_MOCK_HEADER_ALLOWLIST)
        for name in names:
            ok, error = validate_header_name(name)
            if not ok:
                raise ValueError(error)
            if name not in merged:
                merged.append(name)
        _MOCK_HEADER_ALLOWLIST = tuple(merged)


def get_mock_headers_config() -> Tuple[Dict[str, str], Tuple[str, ...]]:
    with _LOCK:
        return dict(_MOCK_DEFAULT_HEADERS), tuple(_MOCK_HEADER_ALLOWLIST)


_COMMON_REQUEST_HEADERS = {
    "content-type", "accept", "accept-encoding", "accept-language", "authorization",
    "user-agent", "host", "connection", "cookie", "referer", "origin", "content-length",
}


def build_mock_response_headers(interface_headers: Optional[Dict[str, Any]], response_body: Any) -> Tuple[Dict[str, str], List[str]]:
    """响应头与请求头分离：默认集合 + 白名单透传，被过滤字段写入 warnings。"""
    defaults, allowlist = get_mock_headers_config()
    merged: Dict[str, str] = dict(defaults)
    if isinstance(response_body, (dict, list)):
        merged["Content-Type"] = "application/json; charset=utf-8"
    elif isinstance(response_body, str):
        merged["Content-Type"] = "text/plain; charset=utf-8"
    warnings: List[str] = []
    source = interface_headers if isinstance(interface_headers, dict) else {}
    allowed_lower = {str(name).lower() for name in allowlist}
    for key, value in source.items():
        name = str(key)
        if name.lower() in allowed_lower:
            ok_name, _ = validate_header_name(key)
            ok_value, value_error = validate_header_value(value)
            if ok_name and ok_value:
                merged[name] = str(value)
            else:
                warnings.append(f"Mock 响应头 {name!r} 已跳过：{value_error or '非法头名'}")
        elif name.lower() not in _COMMON_REQUEST_HEADERS:
            warnings.append(
                f"请求头 {name!r} 不会自动成为 Mock 响应头；如需透传请配置 mock_response_headers "
                "或调用 register_mock_header_allowlist()"
            )
    return merged, warnings


# ---------------------------------------------------------------------------
# 清洗器：CSV 公式注入 / Markdown 单元格 / 结构化文本字段
# ---------------------------------------------------------------------------

_CSV_SANITIZERS: Dict[str, Callable[[Any], Any]] = {}


def _csv_formula_guard(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    if value.startswith(("=", "+", "-", "@", "\t", "\r")):
        return "'" + value
    return value


_CSV_SANITIZERS["formula_guard"] = _csv_formula_guard


def register_csv_sanitizer(name: str, fn: Callable[[Any], Any], *, replace: bool = False) -> None:
    with _LOCK:
        if name in _CSV_SANITIZERS and not replace:
            raise ValueError(f"CSV 清洗器 {name!r} 已注册；如需覆盖请传 replace=True")
        _CSV_SANITIZERS[name] = fn


def sanitize_csv_value(value: Any) -> Any:
    with _LOCK:
        sanitizers = list(_CSV_SANITIZERS.values())
    result = value
    for fn in sanitizers:
        try:
            result = fn(result)
        except Exception:
            continue
    return result


def sanitize_export_rows(rows: Sequence[Dict[str, Any]]) -> List[Dict[str, Any]]:
    cleaned: List[Dict[str, Any]] = []
    for row in rows or []:
        cleaned.append({str(key): sanitize_csv_value(value) for key, value in dict(row).items()})
    return cleaned


def escape_markdown_cell(value: Any) -> str:
    """表格单元格转义：竖线、换行、反引号、CR。"""
    text = "" if value is None else str(value)
    text = text.replace("\r", " ").replace("\n", " ⏎ ")
    text = text.replace("|", "\\|").replace("`", "\\`")
    return text


def escape_structured_field(value: Any) -> str:
    """结构化文本字段值转义：换行/回车/分隔符，保证导出可往返解析。"""
    if isinstance(value, (dict, list)):
        text = json.dumps(value, ensure_ascii=False, sort_keys=True)
    else:
        text = "" if value is None else str(value)
    return text.replace("\r", "\\r").replace("\n", "\\n")


# ---------------------------------------------------------------------------
# 断言模板风格
# ---------------------------------------------------------------------------

_ASSERTION_STYLES: Dict[str, str] = {
    "字段存在断言": "presence",
    "标准断言": "standard",
    "严格断言": "strict",
}
_ASSERTION_STYLE_KEYS = {"presence", "standard", "strict"}


def register_assertion_style(label: str, key: str, *, replace: bool = False) -> None:
    name = str(label).strip()
    if not name or not str(key).strip():
        raise ValueError("断言风格标签与 key 不能为空")
    with _LOCK:
        if name in _ASSERTION_STYLES and not replace:
            raise ValueError(f"断言风格 {name!r} 已注册；如需覆盖请传 replace=True")
        _ASSERTION_STYLES[name] = str(key).strip()


def get_assertion_styles() -> Dict[str, str]:
    with _LOCK:
        return dict(_ASSERTION_STYLES)


def resolve_assertion_style(label: Any) -> Tuple[str, str]:
    """返回 (style_key, warning)；中文标签、内部 key 均可解析，未知风格明确告警。"""
    text = str(label or "").strip()
    with _LOCK:
        if text in _ASSERTION_STYLES:
            return _ASSERTION_STYLES[text], ""
        if text.lower() in _ASSERTION_STYLE_KEYS:
            return text.lower(), ""
        return "standard", f"未知断言风格 {text!r}，已回落为「标准断言」；可通过 register_assertion_style() 扩展"


# ---------------------------------------------------------------------------
# 文字摘要 / 结果签名 / 统一导出
# ---------------------------------------------------------------------------

_SUMMARY_TEMPLATES: Dict[str, str] = {
    "normalize": "本轮共标准化 {interface_count} 个接口，含请求体 {with_body_count} 个、鉴权相关 {auth_related_count} 个，缺少响应样例 {missing_expected_response_count} 个。",
    "checklist": "本轮共生成 {interface_count} 个接口的回归清单，高优先级 {high_priority_count} 个、建议检查项 {check_item_count} 条。",
    "diff": "基线 {baseline_total} 个、当前 {target_total} 个接口：新增 {added_count}、删除 {removed_count}、变更 {changed_count}，其中高风险变更 {high_risk_count} 个。",
    "quality": "本轮体检 {interface_count} 个接口，发现 {issue_count} 个问题（高 {high_count} / 中 {medium_count} / 低 {low_count}），健康分 {health_score}（{health_level}）。",
    "assertion": "本轮生成 {template_style} 断言模板，样例类型 {sample_type}，字段路径 {field_count} 条。",
    "mock": "本轮为 {interface_count} 个接口生成 Mock 服务脚本，监听 {host}:{port}，延迟 {delay_ms}ms。",
    "snippet": "本轮生成 {language} 调试代码片段，方法 {method}，路径 {path}。",
}


def register_summary_template(kind: str, template: str, *, replace: bool = False) -> None:
    with _LOCK:
        if kind in _SUMMARY_TEMPLATES and not replace:
            raise ValueError(f"文字摘要 {kind!r} 已注册；如需覆盖请传 replace=True")
        _SUMMARY_TEMPLATES[kind] = str(template)


def build_text_summary(kind: str, values: Dict[str, Any]) -> str:
    with _LOCK:
        template = _SUMMARY_TEMPLATES.get(kind, "")
    if not template:
        return ""
    try:
        return template.format(**{key: values.get(key, "-") for key in re.findall(r"\{(\w+)\}", template)})
    except (KeyError, ValueError, IndexError):
        return ""


def compute_signature(payload: Any) -> str:
    """对配置/输入做稳定签名，用于结果过期检测。"""
    try:
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except (TypeError, ValueError):
        encoded = repr(payload)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


def build_export_payload(
    result: Dict[str, Any],
    *,
    config_snapshot: Optional[Dict[str, Any]] = None,
    input_signature: str = "",
    warnings: Optional[Sequence[str]] = None,
    truncation: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """统一导出结构：结果 + 配置快照 + 输入签名 + 能力摘要 + 告警 + 截断明细。"""
    payload = copy.deepcopy(dict(result or {}))
    payload["config_snapshot"] = copy.deepcopy(config_snapshot or {})
    payload["input_signature"] = str(input_signature or "")
    payload["registry_summary"] = get_registry_summary()
    payload["warnings"] = list(warnings or [])
    payload["truncation"] = copy.deepcopy(truncation or {})
    return payload


# ---------------------------------------------------------------------------
# 能力摘要与测试隔离
# ---------------------------------------------------------------------------

def get_registry_summary() -> Dict[str, Any]:
    limits = get_dev_limits()
    return {
        "HTTP 方法": len(_HTTP_METHODS),
        "代码片段语言": len(_SNIPPET_LANGUAGES),
        "代码渲染器": len(_SNIPPET_RENDERERS),
        "断言风格": len(_ASSERTION_STYLES),
        "质量规则": len(_QUALITY_RULES),
        "状态码分桶": len(_STATUS_CODE_BUCKETS),
        "严重级别": len(_SEVERITY_ORDER),
        "健康分档": len(_HEALTH_BANDS),
        "词表分组": len(_HINTS),
        "清单文案": len(_CHECKLIST_TEMPLATES),
        "优先级规则": len(_PRIORITY_RULES),
        "Mock 默认响应头": len(_MOCK_DEFAULT_HEADERS),
        "CSV 清洗器": len(_CSV_SANITIZERS),
        "协议白名单": ", ".join(get_protocols()),
        "默认校验 SSL": str(limits.verify_ssl_by_default),
        "默认监听地址": limits.default_mock_host,
        "默认 CORS 来源": limits.default_cors_origin,
        "允许内网目标": str(limits.allow_private_targets),
        "最大接口数": limits.max_interfaces,
        "最大 Mock 路由": limits.max_mock_routes,
        "最大递归深度": limits.max_recursion_depth,
        "最大延迟(ms)": limits.max_delay_ms,
        "最大请求体(bytes)": limits.max_request_body_bytes,
    }


def reset_dev_registry() -> None:
    """恢复全部默认值，供 pytest 用例之间隔离。"""
    global _LIMITS, _MOCK_HEADER_ALLOWLIST
    with _LOCK:
        _LIMITS = DevLimits()
        _PROTOCOLS.clear()
        _PROTOCOLS.update({"http": "HTTP", "https": "HTTPS"})
        _HTTP_METHODS.clear()
        _HTTP_METHODS.update({
            "GET": "GET", "POST": "POST", "PUT": "PUT", "PATCH": "PATCH",
            "DELETE": "DELETE", "HEAD": "HEAD", "OPTIONS": "OPTIONS",
        })
        _SNIPPET_LANGUAGES.clear()
        _SNIPPET_LANGUAGES.update({
            "Python requests": SnippetLanguageSpec("Python requests", "python_requests", "python", "py", ("python", "requests")),
            "JavaScript fetch": SnippetLanguageSpec("JavaScript fetch", "javascript_fetch", "javascript", "js", ("js", "fetch", "javascript")),
            "curl": SnippetLanguageSpec("curl", "curl", "bash", "sh", ("bash", "shell", "cURL"), True),
        })
        _SNIPPET_RENDERERS.clear()
        _SNIPPET_RENDERERS.update({
            "python_requests": _render_python_requests,
            "javascript_fetch": _render_javascript_fetch,
            "curl": _render_curl,
        })
        _REQUESTS_VERBS.clear()
        _REQUESTS_VERBS.update({
            "GET": "get", "POST": "post", "PUT": "put", "PATCH": "patch",
            "DELETE": "delete", "HEAD": "head", "OPTIONS": "options",
        })
        _ASSERTION_STYLES.clear()
        _ASSERTION_STYLES.update({
            "字段存在断言": "presence", "标准断言": "standard", "严格断言": "strict",
        })
        _QUALITY_RULES.clear()
        _QUALITY_RULES.update({
            "missing_name": QualityRuleSpec("missing_name", "medium", "接口名称为空"),
            "missing_description": QualityRuleSpec("missing_description", "low", "接口描述为空，后续维护成本会偏高"),
            "missing_expected_response": QualityRuleSpec("missing_expected_response", "medium", "缺少期望响应示例，自动断言会偏弱"),
            "path_param_missing": QualityRuleSpec("path_param_missing", "high", "路径占位符缺少参数: {detail}"),
            "path_param_extra": QualityRuleSpec("path_param_extra", "medium", "存在未在路径中使用的 path 参数: {detail}"),
            "path_param_empty": QualityRuleSpec("path_param_empty", "medium", "路径参数值为空: {detail}"),
            "get_with_body": QualityRuleSpec("get_with_body", "medium", "GET 请求携带 body，兼容性风险较高"),
            "empty_request_body": QualityRuleSpec("empty_request_body", "low", "{method} 请求未提供 body，请确认是否符合接口设计"),
            "missing_content_type": QualityRuleSpec("missing_content_type", "medium", "请求体存在但未声明 Content-Type"),
            "json_content_type_mismatch": QualityRuleSpec("json_content_type_mismatch", "medium", "请求格式为 JSON，但 Content-Type 不是 application/json"),
            "form_content_type_mismatch": QualityRuleSpec("form_content_type_mismatch", "medium", "请求格式为 form，但 Content-Type 不是 form 类型"),
            "missing_tags": QualityRuleSpec("missing_tags", "low", "未配置标签，后续分组与筛选不方便"),
            "duplicate_endpoint": QualityRuleSpec("duplicate_endpoint", "high", "与其他接口重复定义，重复序号: {detail}"),
            "invalid_expected_status": QualityRuleSpec("invalid_expected_status", "high", "期望状态码 {detail} 不在合法 HTTP 范围（100-599）"),
            "unexpected_status_bucket": QualityRuleSpec("unexpected_status_bucket", "medium", "期望状态码落在{detail}分桶，请确认接口契约是否刻意为错误场景"),
        })
        _STATUS_CODE_BUCKETS.clear()
        _STATUS_CODE_BUCKETS.update({
            "informational": StatusCodeBucketSpec("informational", "1xx 信息响应", 100, 199),
            "success": StatusCodeBucketSpec("success", "2xx 成功", 200, 299),
            "redirect": StatusCodeBucketSpec("redirect", "3xx 重定向", 300, 399),
            "client_error": StatusCodeBucketSpec("client_error", "4xx 客户端错误", 400, 499, True),
            "server_error": StatusCodeBucketSpec("server_error", "5xx 服务端错误", 500, 599, True),
        })
        _SEVERITY_ORDER.clear()
        _SEVERITY_ORDER.update({"high": 0, "medium": 1, "low": 2})
        _SCORE_WEIGHTS.clear()
        _SCORE_WEIGHTS.update({"high": 18, "medium": 8, "low": 3})
        _HEALTH_BANDS[:] = [(90, "优秀"), (75, "良好"), (60, "一般"), (0, "需整改")]
        _RISK_LEVELS.clear()
        _RISK_LEVELS.update({0: "low", 1: "low", 2: "medium", 3: "high"})
        _HINTS.clear()
        _HINTS.update({
            "auth_header": ("authorization", "token", "api-key", "apikey", "x-auth", "access-key"),
            "auth_text": ("auth", "login", "logout", "token", "signin", "sign-in", "鉴权", "登录", "认证"),
            "pagination": ("page", "pagenum", "pageno", "size", "pagesize", "limit", "offset"),
            "sort": ("sort", "order", "orderby", "sortby", "direction", "filter", "keyword"),
        })
        _CHECKLIST_TEMPLATES.clear()
        _CHECKLIST_TEMPLATES.update({
            "status": "校验状态码为 {expected_status}",
            "response_fields": "校验关键响应字段和业务码",
            "response_missing": "补充最小可用响应断言",
            "performance": "关注响应时间是否在可接受范围内",
            "query_normal": "覆盖查询参数正常组合",
            "query_negative": "验证查询参数缺失、非法值、边界值",
            "path_normal": "验证路径参数替换后的资源是否正确",
            "path_negative": "验证无效路径参数、越权访问或不存在资源",
            "body_normal": "覆盖请求体必填字段、类型和边界值",
            "body_negative": "验证请求体字段缺失、超长、非法格式",
            "auth_normal": "验证有效鉴权下接口可正常访问",
            "auth_negative": "验证缺少鉴权、鉴权失效、权限不足场景",
            "mutation_normal": "确认接口对数据的新增、更新或删除结果正确",
            "mutation_negative": "验证重复提交、幂等性或回滚处理",
            "pagination": "验证分页参数、总数、页码边界和空列表场景",
            "sort": "验证排序字段和筛选条件组合",
        })
        _PRIORITY_RULES[:] = [
            ("mutation", "high", lambda item: item.get("method") in {"POST", "PUT", "PATCH", "DELETE"}),
            ("auth_or_path", "high", lambda item: bool(item.get("path_params")) or _auth_related(item)),
            ("body", "high", lambda item: item.get("body") not in (None, "", {}, [])),
            ("query", "medium", lambda item: bool(item.get("query_params"))),
        ]
        _MOCK_DEFAULT_HEADERS.clear()
        _MOCK_DEFAULT_HEADERS.update({"Cache-Control": "no-store"})
        _MOCK_HEADER_ALLOWLIST = ("Set-Cookie", "X-Trace-Id")
        _CSV_SANITIZERS.clear()
        _CSV_SANITIZERS["formula_guard"] = _csv_formula_guard
        _SUMMARY_TEMPLATES.clear()
        _SUMMARY_TEMPLATES.update({
            "normalize": "本轮共标准化 {interface_count} 个接口，含请求体 {with_body_count} 个、鉴权相关 {auth_related_count} 个，缺少响应样例 {missing_expected_response_count} 个。",
            "checklist": "本轮共生成 {interface_count} 个接口的回归清单，高优先级 {high_priority_count} 个、建议检查项 {check_item_count} 条。",
            "diff": "基线 {baseline_total} 个、当前 {target_total} 个接口：新增 {added_count}、删除 {removed_count}、变更 {changed_count}，其中高风险变更 {high_risk_count} 个。",
            "quality": "本轮体检 {interface_count} 个接口，发现 {issue_count} 个问题（高 {high_count} / 中 {medium_count} / 低 {low_count}），健康分 {health_score}（{health_level}）。",
            "assertion": "本轮生成 {template_style} 断言模板，样例类型 {sample_type}，字段路径 {field_count} 条。",
            "mock": "本轮为 {interface_count} 个接口生成 Mock 服务脚本，监听 {host}:{port}，延迟 {delay_ms}ms。",
            "snippet": "本轮生成 {language} 调试代码片段，方法 {method}，路径 {path}。",
        })
