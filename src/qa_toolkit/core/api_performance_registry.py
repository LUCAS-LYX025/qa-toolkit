"""接口性能测试工具注册中心。

与 regex_registry / crypto_registry / json_registry / datetime_registry /
ip_lookup_registry 同风格的注册式扩展点。本模块把原先散落在
``api_performance_tool.py`` 与 2600 行页面里的硬编码策略全部收敛为可注册项：

- 断言类型（新增一种断言无需改 core 与页面）
- 分位数规格与口径（nearest-rank / linear，可增删分位）
- 监听器页签、结果导出字段、摘要指标（页面从注册表生成）
- CSV 共享模式、EOF 策略、定时器策略
- 协议白名单与 SSRF 护栏、运行上限
- 导出清洗器（CSV 公式注入降级）

约定：Spec 一律 frozen dataclass；查询返回副本；重复注册需要 ``replace=True``；
写操作用 RLock 保护。默认注册项与旧行为保持一致，保证向后兼容。
"""

from __future__ import annotations

import ipaddress
import math
import random
import threading
from dataclasses import dataclass, replace as _dc_replace
from datetime import datetime
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# 运行上限与安全默认值（统一配置，core 与页面共用同一份）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PerformanceLimits:
    # 并发与次数
    max_virtual_users: int = 1000
    ui_max_virtual_users: int = 200
    max_loop_count: int = 1000
    # 时长（秒 / 毫秒）
    max_timeout_seconds: float = 120.0
    max_duration_seconds: float = 3600.0
    max_ramp_up_seconds: float = 3600.0
    max_start_delay_seconds: float = 600.0
    max_think_time_ms: float = 60000.0
    max_jitter_ms: float = 60000.0
    max_max_response_ms: float = 300000.0
    # 截断 / 预览
    max_error_samples: int = 100
    max_html_error_rows: int = 50
    max_transaction_errors: int = 5
    max_response_preview_chars: int = 400
    max_request_preview_chars: int = 1000
    max_summary_listener_rows: int = 200
    max_timeline_buckets: int = 3600
    max_export_samples: int = 5000
    # 安全默认值
    allow_private_targets: bool = False
    follow_redirects_by_default: bool = False
    verify_ssl_by_default: bool = True


_LIMITS = PerformanceLimits()


def configure_performance_limits(**kwargs: Any) -> PerformanceLimits:
    """按关键字更新运行上限；未知字段直接报错，避免拼写错误静默失效。"""
    global _LIMITS
    allowed = set(PerformanceLimits.__dataclass_fields__)
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知的性能测试配置项: {sorted(unknown)}")
    for key, value in kwargs.items():
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)) and (not math.isfinite(float(value)) or float(value) < 0):
            raise ValueError(f"配置项 {key!r} 必须是非负有限数，收到: {value!r}")
    with _LOCK:
        _LIMITS = _dc_replace(_LIMITS, **kwargs)
        return _LIMITS


def get_performance_limits() -> PerformanceLimits:
    with _LOCK:
        return _LIMITS


# ---------------------------------------------------------------------------
# 断言类型
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AssertionOutcome:
    passed: bool
    message: str = ""


@dataclass(frozen=True)
class AssertionSpec:
    key: str
    label: str
    evaluator: Callable[[Dict[str, Any], str, int, float], Optional[AssertionOutcome]]
    description: str = ""


_ASSERTION_TYPES: Dict[str, AssertionSpec] = {}


def register_assertion_type(
    key: str, label: str,
    evaluator: Callable[[Dict[str, Any], str, int, float], Optional[AssertionOutcome]],
    *, description: str = "", replace: bool = False,
) -> None:
    """注册断言。evaluator(sampler, response_text, status_code, elapsed_ms) 返回
    ``AssertionOutcome`` 或 ``None``（表示本条不适用、跳过）。"""
    if not key or not callable(evaluator):
        raise ValueError("断言类型需要非空 key 与可调用 evaluator")
    with _LOCK:
        if key in _ASSERTION_TYPES and not replace:
            raise ValueError(f"断言类型 {key!r} 已存在，如需覆盖请传 replace=True")
        _ASSERTION_TYPES[key] = AssertionSpec(key=key, label=label, evaluator=evaluator,
                                              description=description)


def unregister_assertion_type(key: str) -> bool:
    with _LOCK:
        return _ASSERTION_TYPES.pop(key, None) is not None


def get_assertion_types() -> Dict[str, AssertionSpec]:
    with _LOCK:
        return dict(_ASSERTION_TYPES)


def evaluate_assertions(
    sampler: Dict[str, Any], response_text: str, status_code: int, elapsed_ms: float,
) -> Tuple[bool, List[str], List[Dict[str, Any]]]:
    """按注册顺序执行全部断言，返回 (是否通过, 失败原因列表, 逐条明细)。"""
    errors: List[str] = []
    details: List[Dict[str, Any]] = []
    for spec in list(get_assertion_types().values()):
        try:
            outcome = spec.evaluator(sampler, response_text, status_code, elapsed_ms)
        except Exception as exc:  # 单个断言实现出错不应拖垮整次压测
            outcome = AssertionOutcome(False, f"断言 {spec.label} 执行异常: {exc}")
        if outcome is None:
            continue
        details.append({
            "key": spec.key,
            "label": spec.label,
            "passed": bool(outcome.passed),
            "detail": outcome.message,
        })
        if not outcome.passed:
            errors.append(outcome.message or spec.label)
    return not errors, errors, details


# ---------------------------------------------------------------------------
# 分位数规格与口径
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class PercentileSpec:
    name: str          # 结果字段名，如 "p95_ms"
    value: float       # 0-100
    label: str         # 页面展示名，如 "95% Line"


_PERCENTILES: Dict[str, PercentileSpec] = {}
_PERCENTILE_METHODS = ("nearest_rank", "linear")
_PERCENTILE_METHOD = "nearest_rank"


def register_percentile(name: str, value: float, *, label: str = "", replace: bool = False) -> None:
    """注册分位数；name 建议以 ``_ms`` 结尾以保持结果字段命名一致。"""
    numeric = float(value)
    if not math.isfinite(numeric) or not 0.0 <= numeric <= 100.0:
        raise ValueError(f"分位数必须在 [0, 100]，收到: {value!r}")
    with _LOCK:
        if name in _PERCENTILES and not replace:
            raise ValueError(f"分位数 {name!r} 已存在，如需覆盖请传 replace=True")
        _PERCENTILES[name] = PercentileSpec(name=name, value=numeric, label=label or name)


def get_percentile_specs() -> List[PercentileSpec]:
    with _LOCK:
        return sorted(_PERCENTILES.values(), key=lambda spec: spec.value)


def set_percentile_method(method: str) -> str:
    global _PERCENTILE_METHOD
    if method not in _PERCENTILE_METHODS:
        raise ValueError(f"未知分位数口径 {method!r}，可选: {_PERCENTILE_METHODS}")
    with _LOCK:
        _PERCENTILE_METHOD = method
        return _PERCENTILE_METHOD


def get_percentile_method() -> str:
    with _LOCK:
        return _PERCENTILE_METHOD


def get_percentile_method_label() -> str:
    return {
        "nearest_rank": "JMeter nearest-rank（第 ceil(p/100×N) 个样本）",
        "linear": "线性插值（numpy linear，与 JMeter 口径不同）",
    }.get(get_percentile_method(), get_percentile_method())


# ---------------------------------------------------------------------------
# 监听器页签 / 结果导出字段 / 摘要指标（页面由注册表驱动）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ListenerTabSpec:
    key: str
    label: str


_LISTENER_TABS: List[ListenerTabSpec] = []


def register_listener_tab(key: str, label: str, *, replace: bool = False) -> None:
    with _LOCK:
        if any(item.key == key for item in _LISTENER_TABS) and not replace:
            raise ValueError(f"监听器页签 {key!r} 已存在，如需覆盖请传 replace=True")
        if any(item.key == key for item in _LISTENER_TABS):
            _LISTENER_TABS[:] = [item for item in _LISTENER_TABS if item.key != key]
        _LISTENER_TABS.append(ListenerTabSpec(key=key, label=label))


def get_listener_tabs() -> List[ListenerTabSpec]:
    with _LOCK:
        return list(_LISTENER_TABS)


def get_listener_tab_labels() -> List[str]:
    return [item.label for item in get_listener_tabs()]


@dataclass(frozen=True)
class ResultFieldSpec:
    key: str            # 导出 JSON 里的键
    label: str          # 说明
    source: str         # result 里的键


_RESULT_FIELDS: List[ResultFieldSpec] = []


def register_result_field(key: str, label: str, *, source: str = "", replace: bool = False) -> None:
    with _LOCK:
        if any(item.key == key for item in _RESULT_FIELDS) and not replace:
            raise ValueError(f"导出字段 {key!r} 已存在，如需覆盖请传 replace=True")
        if any(item.key == key for item in _RESULT_FIELDS):
            _RESULT_FIELDS[:] = [item for item in _RESULT_FIELDS if item.key != key]
        _RESULT_FIELDS.append(ResultFieldSpec(key=key, label=label, source=source or key))


def get_result_fields() -> List[ResultFieldSpec]:
    with _LOCK:
        return list(_RESULT_FIELDS)


def build_export_payload(result: Dict[str, Any], *, generated_at: str = "") -> Dict[str, Any]:
    """按注册的导出字段生成完整结果快照（含测试计划与原始样本）。"""
    limits = get_performance_limits()
    payload: Dict[str, Any] = {
        "generated_at": generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "percentile_method": get_percentile_method(),
    }
    for spec in get_result_fields():
        value = result.get(spec.source)
        if spec.key == "samples" and isinstance(value, list) and len(value) > limits.max_export_samples:
            payload["samples_truncated"] = {
                "total": len(value), "exported": limits.max_export_samples,
                "note": f"仅导出前 {limits.max_export_samples} 条样本",
            }
            value = value[: limits.max_export_samples]
        payload[spec.key] = value
    return payload


@dataclass(frozen=True)
class SummaryMetricSpec:
    key: str
    label: str
    formatter: Callable[[Dict[str, Any]], str]


_SUMMARY_METRICS: List[SummaryMetricSpec] = []


def register_summary_metric(
    key: str, label: str, formatter: Callable[[Dict[str, Any]], str], *, replace: bool = False,
) -> None:
    with _LOCK:
        if any(item.key == key for item in _SUMMARY_METRICS) and not replace:
            raise ValueError(f"摘要指标 {key!r} 已存在，如需覆盖请传 replace=True")
        if any(item.key == key for item in _SUMMARY_METRICS):
            _SUMMARY_METRICS[:] = [item for item in _SUMMARY_METRICS if item.key != key]
        _SUMMARY_METRICS.append(SummaryMetricSpec(key=key, label=label, formatter=formatter))


def get_summary_metrics() -> List[SummaryMetricSpec]:
    with _LOCK:
        return list(_SUMMARY_METRICS)


# ---------------------------------------------------------------------------
# CSV 共享模式 / EOF 策略 / 定时器策略
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class CsvSharingModeSpec:
    key: str
    label: str


_CSV_SHARING_MODES: Dict[str, CsvSharingModeSpec] = {}


def register_csv_sharing_mode(key: str, label: str, *, replace: bool = False) -> None:
    with _LOCK:
        if key in _CSV_SHARING_MODES and not replace:
            raise ValueError(f"CSV 共享模式 {key!r} 已存在，如需覆盖请传 replace=True")
        _CSV_SHARING_MODES[key] = CsvSharingModeSpec(key=key, label=label)


def get_csv_sharing_modes() -> Dict[str, str]:
    with _LOCK:
        return {key: spec.label for key, spec in _CSV_SHARING_MODES.items()}


def is_valid_csv_sharing_mode(key: str) -> bool:
    with _LOCK:
        return key in _CSV_SHARING_MODES


@dataclass(frozen=True)
class CsvEofPolicySpec:
    key: str
    label: str
    description: str


_CSV_EOF_POLICIES: Dict[str, CsvEofPolicySpec] = {}


def register_csv_eof_policy(key: str, label: str, *, description: str = "", replace: bool = False) -> None:
    with _LOCK:
        if key in _CSV_EOF_POLICIES and not replace:
            raise ValueError(f"CSV EOF 策略 {key!r} 已存在，如需覆盖请传 replace=True")
        _CSV_EOF_POLICIES[key] = CsvEofPolicySpec(key=key, label=label, description=description)


def get_csv_eof_policies() -> Dict[str, str]:
    with _LOCK:
        return {key: spec.label for key, spec in _CSV_EOF_POLICIES.items()}


def normalize_csv_eof_policy(recycle_on_eof: bool, stop_thread_on_eof: bool) -> str:
    """把两个易冲突的 checkbox 归一化为唯一策略，消除「Stop Thread 失效」。"""
    if recycle_on_eof:
        return "recycle"
    if stop_thread_on_eof:
        return "stop_thread"
    return "continue_empty"


@dataclass(frozen=True)
class TimerStrategySpec:
    key: str
    label: str
    compute_ms: Callable[[float, float], float]


_TIMER_STRATEGIES: Dict[str, TimerStrategySpec] = {}


def register_timer_strategy(
    key: str, label: str, compute_ms: Callable[[float, float], float], *, replace: bool = False,
) -> None:
    if not callable(compute_ms):
        raise ValueError("定时器策略需要可调用 compute_ms")
    with _LOCK:
        if key in _TIMER_STRATEGIES and not replace:
            raise ValueError(f"定时器策略 {key!r} 已存在，如需覆盖请传 replace=True")
        _TIMER_STRATEGIES[key] = TimerStrategySpec(key=key, label=label, compute_ms=compute_ms)


def get_timer_strategies() -> Dict[str, str]:
    with _LOCK:
        return {key: spec.label for key, spec in _TIMER_STRATEGIES.items()}


def compute_timer_delay_ms(think_time_ms: float, jitter_ms: float, strategy: str = "constant_jitter") -> float:
    with _LOCK:
        spec = _TIMER_STRATEGIES.get(strategy) or _TIMER_STRATEGIES.get("constant_jitter")
    if spec is None:
        return max(float(think_time_ms or 0.0), 0.0)
    try:
        return max(float(spec.compute_ms(float(think_time_ms or 0.0), float(jitter_ms or 0.0))), 0.0)
    except Exception:
        return max(float(think_time_ms or 0.0), 0.0)


# ---------------------------------------------------------------------------
# 协议白名单 / SSRF 护栏
# ---------------------------------------------------------------------------

_PROTOCOLS: Dict[str, str] = {}


def register_protocol(scheme: str, label: str = "", *, replace: bool = False) -> None:
    normalized = str(scheme or "").strip().lower()
    if not normalized:
        raise ValueError("协议名不能为空")
    with _LOCK:
        if normalized in _PROTOCOLS and not replace:
            raise ValueError(f"协议 {normalized!r} 已存在，如需覆盖请传 replace=True")
        _PROTOCOLS[normalized] = label or normalized


def get_protocols() -> Dict[str, str]:
    with _LOCK:
        return dict(_PROTOCOLS)


def _is_private_host(host: str) -> bool:
    lowered = host.strip().lower().rstrip(".")
    if lowered in {"localhost", "localhost.localdomain"} or lowered.endswith(".localhost"):
        return True
    try:
        address = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return bool(
        address.is_private or address.is_loopback or address.is_link_local
        or address.is_reserved or address.is_multicast or address.is_unspecified
    )


def validate_target_url(url: str, *, allow_private: Optional[bool] = None) -> Tuple[bool, str]:
    """校验压测目标：协议白名单、端口范围、内网/回环/元数据地址。"""
    text = str(url or "").strip()
    if not text:
        return False, "URL 不能为空"
    parsed = urlparse(text)
    scheme = (parsed.scheme or "").lower()
    if scheme not in get_protocols():
        allowed = "、".join(sorted(get_protocols()))
        return False, f"不支持的协议 {scheme or '(空)'}，仅允许：{allowed}"
    if not parsed.netloc or not parsed.hostname:
        return False, "URL 缺少主机名"
    try:
        port = parsed.port
    except ValueError:
        return False, "端口号不是合法整数（应为 1-65535）"
    if port is not None and not (1 <= port <= 65535):
        return False, f"端口号 {port} 超出 1-65535"
    if "@" in parsed.netloc:
        return False, "URL 不允许携带 userinfo（用户名密码），避免主机混淆与凭据外泄"
    allow = get_performance_limits().allow_private_targets if allow_private is None else bool(allow_private)
    if not allow and _is_private_host(parsed.hostname):
        return False, "目标为内网/回环/链路本地/元数据地址；如需压测内网服务，请显式开启「允许内网/本地目标」"
    return True, ""


def sanitize_server_name(value: str) -> Tuple[bool, str]:
    """校验 HTTP Request Defaults 的 Server Name 字段，拒绝 userinfo/路径分隔符。"""
    text = str(value or "").strip()
    if not text:
        return False, "Server Name 不能为空"
    if any(ch in text for ch in ("@", "/", "\\", "?", "#", " ", ":")):
        return False, "Server Name 只能填写主机名或 IP，不能包含 @ / : 等字符"
    return True, text


def validate_port_text(value: str) -> Tuple[bool, str]:
    text = str(value or "").strip()
    if not text:
        return True, ""
    if not text.isdigit():
        return False, "端口号必须是 1-65535 的整数"
    port = int(text)
    if not (1 <= port <= 65535):
        return False, f"端口号 {port} 超出 1-65535"
    return True, text


# ---------------------------------------------------------------------------
# 导出清洗器（CSV 公式注入降级）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ExportSanitizerSpec:
    key: str
    label: str
    sanitize: Callable[[Any], Any]


_EXPORT_SANITIZERS: List[ExportSanitizerSpec] = []


def register_export_sanitizer(
    key: str, label: str, sanitize: Callable[[Any], Any], *, replace: bool = False,
) -> None:
    with _LOCK:
        if any(item.key == key for item in _EXPORT_SANITIZERS) and not replace:
            raise ValueError(f"导出清洗器 {key!r} 已存在，如需覆盖请传 replace=True")
        if any(item.key == key for item in _EXPORT_SANITIZERS):
            _EXPORT_SANITIZERS[:] = [item for item in _EXPORT_SANITIZERS if item.key != key]
        _EXPORT_SANITIZERS.append(ExportSanitizerSpec(key=key, label=label, sanitize=sanitize))


def get_export_sanitizers() -> List[ExportSanitizerSpec]:
    with _LOCK:
        return list(_EXPORT_SANITIZERS)


def sanitize_csv_value(value: Any) -> Any:
    """依次应用注册的清洗器；默认对公式前缀做降级。"""
    for spec in get_export_sanitizers():
        value = spec.sanitize(value)
    return value


def _csv_formula_guard(value: Any) -> Any:
    if isinstance(value, str) and value and value[0] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value


# ---------------------------------------------------------------------------
# 摘要
# ---------------------------------------------------------------------------

def get_registry_summary() -> Dict[str, Any]:
    limits = get_performance_limits()
    with _LOCK:
        return {
            "assertion_types": len(_ASSERTION_TYPES),
            "percentiles": len(_PERCENTILES),
            "percentile_method": _PERCENTILE_METHOD,
            "listener_tabs": len(_LISTENER_TABS),
            "result_fields": len(_RESULT_FIELDS),
            "summary_metrics": len(_SUMMARY_METRICS),
            "csv_sharing_modes": len(_CSV_SHARING_MODES),
            "csv_eof_policies": len(_CSV_EOF_POLICIES),
            "timer_strategies": len(_TIMER_STRATEGIES),
            "protocols": len(_PROTOCOLS),
            "export_sanitizers": len(_EXPORT_SANITIZERS),
            "max_virtual_users": limits.max_virtual_users,
            "max_duration_seconds": limits.max_duration_seconds,
            "max_error_samples": limits.max_error_samples,
            "allow_private_targets": limits.allow_private_targets,
        }


# ---------------------------------------------------------------------------
# 默认注册（旧行为等价 + 补齐安全默认值）
# ---------------------------------------------------------------------------

def _assert_expected_status(sampler, response_text, status_code, elapsed_ms):
    expected = sampler.get("expected_status")
    if expected is None:
        return None
    if int(status_code) == int(expected):
        return AssertionOutcome(True, f"状态码 {status_code} 符合期望")
    return AssertionOutcome(False, f"状态码断言失败，期望 {expected}，实际 {status_code}")


def _assert_contains_text(sampler, response_text, status_code, elapsed_ms):
    keyword = str(sampler.get("contains_text") or "").strip()
    if not keyword:
        return None
    if keyword in response_text:
        return AssertionOutcome(True, f"响应包含断言文本 {keyword!r}")
    return AssertionOutcome(False, f"响应内容未包含断言文本: {keyword}")


def _assert_max_response_ms(sampler, response_text, status_code, elapsed_ms):
    limit = float(sampler.get("max_response_ms") or 0.0)
    if limit <= 0:
        return None
    if elapsed_ms <= limit:
        return AssertionOutcome(True, f"响应时间 {elapsed_ms:.2f}ms 未超阈值")
    return AssertionOutcome(False, f"响应时间超过阈值，期望 <= {limit:.2f}ms，实际 {elapsed_ms:.2f}ms")


def _assert_http_error_fallback(sampler, response_text, status_code, elapsed_ms):
    if sampler.get("expected_status") is not None:
        return None
    if status_code >= 400:
        return AssertionOutcome(False, f"HTTP 请求失败，状态码 {status_code}")
    return None


def _bootstrap_defaults() -> None:
    """恢复全部默认注册项（旧行为等价 + 安全默认值）。"""
    register_assertion_type("expected_status", "Response Code", _assert_expected_status,
                            description="校验 HTTP 状态码")
    register_assertion_type("contains_text", "Response Contains", _assert_contains_text,
                            description="校验响应全文是否包含指定文本（不再用 400 字符预览）")
    register_assertion_type("max_response_ms", "Response Time", _assert_max_response_ms,
                            description="校验单请求耗时上限")
    register_assertion_type("http_error_fallback", "HTTP Status Fallback", _assert_http_error_fallback,
                            description="未配置期望状态码时，4xx/5xx 视为失败")

    register_percentile("p50_ms", 50, label="50% Line")
    register_percentile("p90_ms", 90, label="90% Line")
    register_percentile("p95_ms", 95, label="95% Line")
    register_percentile("p99_ms", 99, label="99% Line")

    for key, label in [
        ("test_plan", "Test Plan"),
        ("summary", "Summary Report"),
        ("aggregate", "Aggregate Report"),
        ("results_tree", "View Results Tree"),
        ("graph", "Graph Results"),
        ("errors", "Errors"),
        ("transactions", "Transactions"),
        ("downloads", "Downloads"),
    ]:
        register_listener_tab(key, label)

    for key, label, source in [
        ("summary", "汇总指标", "summary"),
        ("per_sampler", "按 Sampler 聚合", "per_sampler"),
        ("per_transaction", "按事务聚合", "per_transaction"),
        ("timeline", "时间线", "timeline"),
        ("error_samples", "错误样本", "error_samples"),
        ("summary_listener", "结果清单", "summary_listener"),
        ("plan", "测试计划配置（可复现）", "plan"),
        ("samples", "原始样本明细", "samples"),
        ("html_report", "HTML 报告正文", "html_report"),
        ("warnings", "运行告警", "warnings"),
        ("truncation", "截断说明", "truncation"),
    ]:
        register_result_field(key, label, source=source)

    register_summary_metric("total_requests", "总请求数", lambda s: str(s.get("total_requests", 0)))
    register_summary_metric("success_rate", "成功率", lambda s: f"{float(s.get('success_rate', 0.0)):.1f}%")
    register_summary_metric("avg_ms", "平均响应", lambda s: f"{float(s.get('avg_ms', 0.0)):.2f}ms")
    register_summary_metric("p90_ms", "P90", lambda s: f"{float(s.get('p90_ms', 0.0)):.2f}ms")
    register_summary_metric("p95_ms", "P95", lambda s: f"{float(s.get('p95_ms', 0.0)):.2f}ms")
    register_summary_metric("throughput_rps", "吞吐量（活跃窗口）",
                            lambda s: f"{float(s.get('throughput_rps', 0.0)):.2f} rps")

    register_csv_sharing_mode("all_threads", "All Threads")
    register_csv_sharing_mode("current_thread", "Current Thread")

    register_csv_eof_policy("recycle", "循环复用", description="数据用尽后回到第一行继续")
    register_csv_eof_policy("stop_thread", "停止线程", description="数据用尽后该虚拟用户停止发请求")
    register_csv_eof_policy("continue_empty", "空行继续并告警",
                            description="数据用尽后继续发请求，但变量不替换并写入告警")

    register_timer_strategy("constant_jitter", "Constant Timer + Uniform Jitter",
                            lambda think, jitter: think + (random.uniform(0, jitter) if jitter > 0 else 0.0))
    register_timer_strategy("constant_only", "仅固定等待", lambda think, jitter: think)

    register_protocol("http")
    register_protocol("https")

    register_export_sanitizer("csv_formula_guard", "CSV 公式注入降级", _csv_formula_guard)


def reset_performance_registry() -> None:
    """清空并重建默认注册，供测试隔离与「恢复出厂设置」使用。"""
    global _LIMITS, _PERCENTILE_METHOD
    with _LOCK:
        _ASSERTION_TYPES.clear()
        _PERCENTILES.clear()
        _LISTENER_TABS.clear()
        _RESULT_FIELDS.clear()
        _SUMMARY_METRICS.clear()
        _CSV_SHARING_MODES.clear()
        _CSV_EOF_POLICIES.clear()
        _TIMER_STRATEGIES.clear()
        _PROTOCOLS.clear()
        _EXPORT_SANITIZERS.clear()
        _LIMITS = PerformanceLimits()
        _PERCENTILE_METHOD = "nearest_rank"
    _bootstrap_defaults()


_bootstrap_defaults()
