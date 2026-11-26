"""缺陷绩效分析工具：注册式扩展中心（数据源 / 连接字段 / 归因 / SLA / 绩效规则）。

设计目标（不局限于当前业务、不绑定任何单一缺陷管理平台）：
- 数据源通过 ``register_adapter(AdapterSpec)`` 接入：禅道（直连 DB / HTTP 代理）、
  JIRA、TAPD、云效、以及任何下游自建平台都只是注册表里的一项；
- 连接配置项由 ``ConnectionFieldSpec`` 声明式描述，页面据此自动渲染输入控件，
  新增数据源无需修改页面代码；
- 「测试/开发绩效」这两种写死的归因方式被抽象为 ``AttributionRuleSpec``：
  ``person_fields``（按哪些角色字段归因）、``start_field``/``end_field``（SLA 起止）；
- SLA 阈值、一级/普通优先级判定、节假日策略由 ``SlaRuleSpec`` 描述，
  计算引擎 ``integrations/tracking/rules.py`` 纯 Python 复用，与 SQL / HTTP 解耦。

与仓库既有 ``*_registry.py`` 保持一致的硬惯例：
- Spec 一律 ``@dataclass(frozen=True)``；
- ``register_*(..., *, replace=False)``：重复 key 抛 ``ValueError``；
- ``get_*`` 返回副本（dict/list/deepcopy），绝不暴露内部可变容器；
- 写操作用 ``threading.RLock`` 保护；
- ``reset_tracking_registry()`` 清空重建默认项，保证测试隔离；
- 默认注册项与旧行为一致（禅道为首个默认 adapter），保证向后兼容。
"""
from __future__ import annotations

import copy
import threading
from dataclasses import dataclass, field, replace as _dc_replace
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

_LOCK = threading.RLock()


# ---------------------------------------------------------------------------
# 运行上限与安全默认值（注册式配置）
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TrackingLimits:
    max_items: int = 20000
    max_projects: int = 500
    max_people: int = 2000
    min_hours: int = 1
    max_hours: int = 24 * 90
    min_timeout_seconds: float = 1.0
    max_timeout_seconds: float = 300.0
    default_timeout_seconds: float = 30.0
    max_export_chars: int = 2_000_000
    default_verify_ssl: bool = True
    allow_private_targets: bool = False
    allow_credentials_in_artifacts: bool = False


_LIMITS = TrackingLimits()


def configure_tracking_limits(**kwargs: Any) -> TrackingLimits:
    global _LIMITS
    allowed = set(TrackingLimits.__dataclass_fields__)
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知上限字段：{sorted(unknown)}")
    with _LOCK:
        _LIMITS = _dc_replace(_LIMITS, **kwargs)
        return _LIMITS


def get_tracking_limits() -> TrackingLimits:
    with _LOCK:
        return _LIMITS


# ---------------------------------------------------------------------------
# 统一枚举与领域模型（页面 / 规则引擎 / 适配器共用）
# ---------------------------------------------------------------------------

# 归一化状态：各平台原始状态经字段映射收敛到这组值
_WORK_ITEM_STATES = {
    "open": "OPEN",
    "active": "ACTIVE",
    "resolved": "RESOLVED",
    "closed": "CLOSED",
    "reopened": "REOPENED",
    "new": "OPEN",
    "in_progress": "ACTIVE",
    "accepted": "ACTIVE",
    "fixed": "RESOLVED",
    "verified": "RESOLVED",
    "done": "CLOSED",
    "rejected": "CLOSED",
    "invalid": "CLOSED",
}

# 绩效维度：从写死的「测试/开发绩效统计」抽象为可注册的维度
_PERFORMANCE_DIMENSIONS: Dict[str, str] = {}


@dataclass(frozen=True)
class Option:
    """统一的下拉选项 ``(value, label)``，替代禅道的 (id,name)/(key,name) 二元组。"""
    value: str
    label: str


@dataclass(frozen=True)
class ConnectionFieldSpec:
    """一个连接配置项的声明：页面据此渲染控件，无需硬编码。"""
    key: str
    label: str
    kind: str = "text"          # text / password / number / select
    required: bool = False
    default: Any = ""
    options: Tuple[str, ...] = ()
    placeholder: str = ""


@dataclass(frozen=True)
class AdapterSpec:
    """一个数据源适配器的注册项。

    ``factory`` 为可调用对象，签名 ``(config: Dict[str, Any]) -> TrackingAdapter``；
    延迟解析以避免注册中心 import adapters 造成循环依赖。``transport`` 描述该
    适配器的取数通道（db / http），供状态展示与安全策略判断。
    """
    key: str
    label: str
    description: str
    transport: str                       # db / http
    fields: Tuple[ConnectionFieldSpec, ...]
    factory: Optional[Callable[[Dict[str, Any]], Any]] = None
    enabled: bool = True                 # False = 仅登记，未接入产物链


@dataclass(frozen=True)
class AttributionRuleSpec:
    """归因规则：把「测试/开发绩效」抽象为可配置的人员字段 + SLA 起止字段。"""
    key: str
    label: str
    # 参与归因的人员字段（统一模型 WorkItem 上的属性名），按顺序取第一个非空
    person_fields: Tuple[str, ...]
    start_field: str                     # 计时起点字段：opened_at / resolved_at
    end_field: Optional[str]             # 计时终点字段；None 表示用「当前时间」
    count_field: str = "submitted"       # 统计基数来源：submitted / assigned


@dataclass(frozen=True)
class SlaRuleSpec:
    """SLA 规则：阈值 + 一级判定 + 是否计入节假日。"""
    key: str
    label: str
    high_priority_fields: Tuple[str, ...] = ("severity", "priority")
    high_priority_values: Tuple[Any, ...] = (1,)
    normal_hours_key: str = "normal"
    weekend_hours_key: str = "weekend"
    count_weekend: bool = True
    count_holiday: bool = True


@dataclass(frozen=True)
class PerformanceRuleSpec:
    """绩效输出规则：率的分母与展示精度。"""
    key: str
    label: str
    rate_denominator: str = "count"      # count / timeout_only
    rate_precision: int = 2


_ADAPTERS: Dict[str, AdapterSpec] = {}
_CONNECTION_FIELDS: Dict[str, Tuple[ConnectionFieldSpec, ...]] = {}
_ATTRIBUTIONS: Dict[str, AttributionRuleSpec] = {}
_SLA_RULES: Dict[str, SlaRuleSpec] = {}
_PERFORMANCE_RULES: Dict[str, PerformanceRuleSpec] = {}


# ---------------------------------------------------------------------------
# 注册函数
# ---------------------------------------------------------------------------

def register_adapter(spec: AdapterSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _ADAPTERS and not replace:
            raise ValueError(f"数据源 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _ADAPTERS[spec.key] = spec
        _CONNECTION_FIELDS[spec.key] = tuple(spec.fields)


def unregister_adapter(key: str) -> None:
    with _LOCK:
        _ADAPTERS.pop(key, None)
        _CONNECTION_FIELDS.pop(key, None)


def get_adapters() -> Dict[str, AdapterSpec]:
    with _LOCK:
        return copy.deepcopy(_ADAPTERS)


def get_adapter(key: str) -> Optional[AdapterSpec]:
    with _LOCK:
        spec = _ADAPTERS.get(key)
        return copy.deepcopy(spec) if spec else None


def get_adapter_labels() -> List[str]:
    return [s.label for s in get_adapters().values()]


def create_adapter(key: str, config: Dict[str, Any]) -> Any:
    """解析适配器实例：factory 延迟 import，未接入（enabled=False）时抛错。"""
    spec = get_adapter(key)
    if spec is None:
        raise ValueError(f"未知数据源 {key!r}；已注册：{'、'.join(get_adapter_labels())}")
    if not spec.enabled or spec.factory is None:
        raise ValueError(f"数据源 {spec.label!r} 仅登记、尚未接入产物链")
    return spec.factory(dict(config or {}))


def get_connection_fields(adapter_key: str) -> Tuple[ConnectionFieldSpec, ...]:
    with _LOCK:
        return tuple(copy.deepcopy(f) for f in _CONNECTION_FIELDS.get(adapter_key, ()))


def register_attribution(spec: AttributionRuleSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _ATTRIBUTIONS and not replace:
            raise ValueError(f"归因规则 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _ATTRIBUTIONS[spec.key] = spec


def get_attributions() -> Dict[str, AttributionRuleSpec]:
    with _LOCK:
        return copy.deepcopy(_ATTRIBUTIONS)


def get_attribution(key: str) -> Optional[AttributionRuleSpec]:
    with _LOCK:
        spec = _ATTRIBUTIONS.get(key)
        return copy.deepcopy(spec) if spec else None


def register_sla_rule(spec: SlaRuleSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _SLA_RULES and not replace:
            raise ValueError(f"SLA 规则 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _SLA_RULES[spec.key] = spec


def get_sla_rules() -> Dict[str, SlaRuleSpec]:
    with _LOCK:
        return copy.deepcopy(_SLA_RULES)


def get_sla_rule(key: str) -> Optional[SlaRuleSpec]:
    with _LOCK:
        spec = _SLA_RULES.get(key)
        return copy.deepcopy(spec) if spec else None


def register_performance_rule(spec: PerformanceRuleSpec, *, replace: bool = False) -> None:
    with _LOCK:
        if spec.key in _PERFORMANCE_RULES and not replace:
            raise ValueError(f"绩效规则 {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _PERFORMANCE_RULES[spec.key] = spec


def get_performance_rules() -> Dict[str, PerformanceRuleSpec]:
    with _LOCK:
        return copy.deepcopy(_PERFORMANCE_RULES)


def get_performance_rule(key: str) -> Optional[PerformanceRuleSpec]:
    with _LOCK:
        spec = _PERFORMANCE_RULES.get(key)
        return copy.deepcopy(spec) if spec else None


def register_performance_dimension(key: str, label: str, *, replace: bool = False) -> None:
    with _LOCK:
        if key in _PERFORMANCE_DIMENSIONS and not replace:
            raise ValueError(f"绩效维度 {key!r} 已注册；如需覆盖请传 replace=True")
        _PERFORMANCE_DIMENSIONS[key] = label


def get_performance_dimensions() -> Dict[str, str]:
    with _LOCK:
        return dict(_PERFORMANCE_DIMENSIONS)


# ---------------------------------------------------------------------------
# 状态归一化 / 数值工具（供适配器与规则引擎复用）
# ---------------------------------------------------------------------------

def normalize_work_item_state(value: Any) -> str:
    text = "" if value is None else str(value).strip().lower()
    return _WORK_ITEM_STATES.get(text, text.upper() or "UNKNOWN")


def normalize_option_items(items: Any, value_key: str = "value",
                           label_key: str = "label") -> List[Option]:
    """把 dict / (v, l) 二元组 / 标量统一成 Option 列表。"""
    result: List[Option] = []
    for item in items or []:
        if isinstance(item, Option):
            result.append(item)
        elif isinstance(item, dict):
            v = item.get(value_key, item.get("id", item.get("key", "")))
            l = item.get(label_key, item.get("name", v))
            result.append(Option(str(v), str(l)))
        elif isinstance(item, (tuple, list)) and len(item) >= 2:
            result.append(Option(str(item[0]), str(item[1])))
        else:
            result.append(Option(str(item), str(item)))
    return result


def clamp_hours(value: Any, key: str) -> int:
    limits = get_tracking_limits()
    try:
        num = int(value)
    except (TypeError, ValueError):
        num = 24
    return max(limits.min_hours, min(limits.max_hours, num))


def redact_connection_config(adapter_key: str, config: Dict[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """按 ConnectionFieldSpec 的 password 字段脱敏，供日志/产物/展示使用。"""
    warnings: List[str] = []
    cleaned = dict(config or {})
    for f in get_connection_fields(adapter_key):
        if f.kind == "password" and cleaned.get(f.key):
            cleaned[f.key] = ""
            warnings.append(f"连接凭据 {f.label} 已从产物中脱敏")
    return cleaned, warnings


def get_registry_summary() -> Dict[str, Any]:
    with _LOCK:
        return {
            "数据源": len(_ADAPTERS),
            "已接入数据源": sorted(k for k, s in _ADAPTERS.items() if s.enabled and s.factory),
            "仅登记数据源": sorted(k for k, s in _ADAPTERS.items() if not s.enabled or not s.factory),
            "归因规则": sorted(_ATTRIBUTIONS),
            "SLA 规则": sorted(_SLA_RULES),
            "绩效规则": sorted(_PERFORMANCE_RULES),
            "绩效维度": dict(_PERFORMANCE_DIMENSIONS),
            "最大工作项数": _LIMITS.max_items,
            "默认校验 SSL": _LIMITS.default_verify_ssl,
            "默认允许内网目标": _LIMITS.allow_private_targets,
            "默认产物保留凭据": _LIMITS.allow_credentials_in_artifacts,
        }


# ---------------------------------------------------------------------------
# 默认注册（禅道为首个默认项，保持旧行为；其余平台 label + 连接字段已登记）
# ---------------------------------------------------------------------------

_ZENTAO_DB_FIELDS = (
    ConnectionFieldSpec("host", "数据库主机", default="127.0.0.1", required=True),
    ConnectionFieldSpec("port", "端口", kind="number", default=3306, required=True),
    ConnectionFieldSpec("database", "数据库名", default="zentao", required=True),
    ConnectionFieldSpec("user", "用户名", default="", required=True),
    ConnectionFieldSpec("password", "密码", kind="password", default="", required=True),
)

_ZENTAO_PROXY_FIELDS = (
    ConnectionFieldSpec("url", "代理地址", default="http://127.0.0.1:18080", required=True),
    ConnectionFieldSpec("token", "访问令牌", kind="password", default=""),
    ConnectionFieldSpec("timeout_seconds", "请求超时（秒）", kind="number",
                        default=TrackingLimits.default_timeout_seconds),
)

_JIRA_FIELDS = (
    ConnectionFieldSpec("base_url", "JIRA 地址", default="", required=True,
                        placeholder="https://jira.example.com"),
    ConnectionFieldSpec("project_key", "项目 Key", default="",
                        placeholder="留空时取项目列表第一项"),
    ConnectionFieldSpec("username", "用户名", default=""),
    ConnectionFieldSpec("token", "API Token", kind="password", default="", required=True),
    ConnectionFieldSpec("timeout_seconds", "请求超时（秒）", kind="number",
                        default=TrackingLimits.default_timeout_seconds),
    ConnectionFieldSpec("verify_ssl", "校验 SSL", kind="select", default="true",
                        options=("true", "false")),
)

_TAPD_FIELDS = (
    ConnectionFieldSpec("base_url", "TAPD 地址", default="https://api.tapd.cn", required=True),
    ConnectionFieldSpec("workspace_id", "空间 ID", default="", required=True),
    ConnectionFieldSpec("api_user", "API User", default=""),
    ConnectionFieldSpec("api_password", "API Password", kind="password", default="", required=True),
    ConnectionFieldSpec("timeout_seconds", "请求超时（秒）", kind="number",
                        default=TrackingLimits.default_timeout_seconds),
    ConnectionFieldSpec("verify_ssl", "校验 SSL", kind="select", default="true",
                        options=("true", "false")),
)

_YUNXIAO_FIELDS = (
    ConnectionFieldSpec("base_url", "云效地址", default="https://openapi-rdc.aliyuncs.com", required=True),
    ConnectionFieldSpec("organization_id", "组织 ID", default="", required=True),
    ConnectionFieldSpec("access_token", "访问令牌", kind="password", default="", required=True),
    ConnectionFieldSpec("timeout_seconds", "请求超时（秒）", kind="number",
                        default=TrackingLimits.default_timeout_seconds),
    ConnectionFieldSpec("verify_ssl", "校验 SSL", kind="select", default="true",
                        options=("true", "false")),
)


def _factory_zentao_db(config: Dict[str, Any]) -> Any:
    from qa_toolkit.integrations.tracking.adapters.zentao_db import ZentaoDbAdapter
    return ZentaoDbAdapter(config)


def _factory_zentao_proxy(config: Dict[str, Any]) -> Any:
    from qa_toolkit.integrations.tracking.adapters.zentao_proxy import ZentaoProxyAdapter
    return ZentaoProxyAdapter(config)


def _factory_jira(config: Dict[str, Any]) -> Any:
    from qa_toolkit.integrations.tracking.adapters.jira import JiraAdapter
    return JiraAdapter(config)


def _factory_tapd(config: Dict[str, Any]) -> Any:
    from qa_toolkit.integrations.tracking.adapters.tapd import TapdAdapter
    return TapdAdapter(config)


def _factory_yunxiao(config: Dict[str, Any]) -> Any:
    from qa_toolkit.integrations.tracking.adapters.yunxiao import YunxiaoAdapter
    return YunxiaoAdapter(config)


def _bootstrap_defaults() -> None:
    global _LIMITS
    _LIMITS = TrackingLimits()
    with _LOCK:
        _ADAPTERS.clear()
        _CONNECTION_FIELDS.clear()
        # 禅道两个接入方式保持旧行为，作为默认且首个注册项。
        register_adapter(AdapterSpec(
            "zentao_db", "禅道（直连数据库）", "直连禅道 MySQL，复用既有 SQL 取数逻辑（行为等价）。",
            "db", _ZENTAO_DB_FIELDS, _factory_zentao_db, True))
        register_adapter(AdapterSpec(
            "zentao_proxy", "禅道（HTTP 代理）", "经内网 HTTP 代理连接禅道，适合云上部署。",
            "http", _ZENTAO_PROXY_FIELDS, _factory_zentao_proxy, True))
        # JIRA / TAPD / 云效：factory 已实现，默认接入。
        register_adapter(AdapterSpec(
            "jira", "JIRA", "通过 JIRA REST API 拉取问题并按统一模型计算绩效。",
            "http", _JIRA_FIELDS, _factory_jira, True))
        register_adapter(AdapterSpec(
            "tapd", "TAPD", "通过 TAPD Open API 拉取缺陷并按统一模型计算绩效。",
            "http", _TAPD_FIELDS, _factory_tapd, True))
        register_adapter(AdapterSpec(
            "yunxiao", "阿里云效", "通过云效 OpenAPI 拉取缺陷并按统一模型计算绩效。",
            "http", _YUNXIAO_FIELDS, _factory_yunxiao, True))

        _ATTRIBUTIONS.clear()
        register_attribution(AttributionRuleSpec(
            "qa", "测试绩效", ("closer", "assignee"), "resolved_at", "closed_at", "submitted"))
        register_attribution(AttributionRuleSpec(
            "dev", "开发绩效", ("resolver", "assignee"), "opened_at", "resolved_at", "assigned"))
        register_attribution(AttributionRuleSpec(
            "custom", "自定义（仅起止）", ("assignee",), "opened_at", "closed_at", "assigned"))

        _SLA_RULES.clear()
        register_sla_rule(SlaRuleSpec("default", "默认 SLA（一级 severity/pri=1）"))
        register_sla_rule(SlaRuleSpec(
            "severity_only", "仅按严重程度（severity=1 为一级）",
            high_priority_fields=("severity",)))

        _PERFORMANCE_RULES.clear()
        register_performance_rule(PerformanceRuleSpec("timeout_rate", "超时响应率（超时/基数）"))
        register_performance_rule(PerformanceRuleSpec(
            "timeout_share", "超时占比（超时/超时合计）", rate_denominator="timeout_only"))

        _PERFORMANCE_DIMENSIONS.clear()
        _PERFORMANCE_DIMENSIONS.update({"qa": "测试绩效", "dev": "开发绩效"})


def reset_tracking_registry() -> None:
    """恢复默认注册表；测试之间调用，避免全局状态污染。"""
    with _LOCK:
        _bootstrap_defaults()


_bootstrap_defaults()
