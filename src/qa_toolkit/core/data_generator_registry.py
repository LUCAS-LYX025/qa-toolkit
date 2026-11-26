"""数据生成工具的注册式扩展中心。

造数场景、边界字段、生成地区全部声明为 frozen Spec，新增业务场景无需修改
DataGenerator 本体。沿用项目既有注册中心惯例：replace 显式覆盖、getter 返回
副本、RLock 保护、reset 供测试隔离。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

_LOCK = threading.RLock()


@dataclass(frozen=True)
class DatasetScenarioSpec:
    """结构化造数场景。builder 优先；builder_name 指向 DataGenerator 方法。"""

    key: str
    label: str
    description: str
    fields: Tuple[str, ...]
    builder_name: str = ""
    builder: Optional[Callable[..., Dict[str, Any]]] = None
    enabled: bool = True
    source: str = "builtin"


@dataclass(frozen=True)
class BoundaryFieldSpec:
    """边界值字段。builder 优先；builder_name 指向 data_generator 模块级处理器。"""

    key: str
    label: str
    description: str
    builder_name: str = ""
    builder: Optional[Callable[..., None]] = None
    enabled: bool = True
    source: str = "builtin"


@dataclass(frozen=True)
class LocaleSpec:
    """生成地区。faker_locale 传给 Faker，label 用于页面展示。"""

    key: str
    label: str
    faker_locale: str
    enabled: bool = True


_DATASET_SCENARIOS: Dict[str, DatasetScenarioSpec] = {}
_BOUNDARY_FIELDS: Dict[str, BoundaryFieldSpec] = {}
_LOCALES: Dict[str, LocaleSpec] = {}


def _register(mapping: Dict[str, Any], spec: Any, replace: bool, kind: str) -> None:
    if not getattr(spec, "key", ""):
        raise ValueError(f"{kind} 的 key 不能为空")
    with _LOCK:
        if spec.key in mapping and not replace:
            raise ValueError(f"{kind} {spec.key!r} 已注册；覆盖请传 replace=True")
        mapping[spec.key] = spec


def register_dataset_scenario(spec: DatasetScenarioSpec, *, replace: bool = False) -> None:
    _register(_DATASET_SCENARIOS, spec, replace, "造数场景")


def register_boundary_field(spec: BoundaryFieldSpec, *, replace: bool = False) -> None:
    _register(_BOUNDARY_FIELDS, spec, replace, "边界字段")


def register_locale(spec: LocaleSpec, *, replace: bool = False) -> None:
    _register(_LOCALES, spec, replace, "生成地区")


def get_dataset_scenario(name: str) -> Optional[DatasetScenarioSpec]:
    """按 key 或 label 查找场景，未找到返回 None。"""
    with _LOCK:
        spec = _DATASET_SCENARIOS.get(str(name or ""))
        if spec is None:
            for item in _DATASET_SCENARIOS.values():
                if item.label == name:
                    return item
        return spec


def get_dataset_scenarios(*, include_disabled: bool = False) -> Dict[str, DatasetScenarioSpec]:
    with _LOCK:
        return {key: spec for key, spec in _DATASET_SCENARIOS.items()
                if include_disabled or spec.enabled}


def get_boundary_field(name: str) -> Optional[BoundaryFieldSpec]:
    with _LOCK:
        spec = _BOUNDARY_FIELDS.get(str(name or ""))
        if spec is None:
            for item in _BOUNDARY_FIELDS.values():
                if item.label == name:
                    return item
        return spec


def get_boundary_fields(*, include_disabled: bool = False) -> Dict[str, BoundaryFieldSpec]:
    with _LOCK:
        return {key: spec for key, spec in _BOUNDARY_FIELDS.items()
                if include_disabled or spec.enabled}


def get_locales(*, include_disabled: bool = False) -> Dict[str, LocaleSpec]:
    with _LOCK:
        return {key: spec for key, spec in _LOCALES.items()
                if include_disabled or spec.enabled}


def get_registry_summary() -> Dict[str, Any]:
    with _LOCK:
        return {
            "造数场景": sorted(spec.label for spec in _DATASET_SCENARIOS.values() if spec.enabled),
            "边界字段": sorted(spec.label for spec in _BOUNDARY_FIELDS.values() if spec.enabled),
            "生成地区": sorted(spec.key for spec in _LOCALES.values() if spec.enabled),
            "扩展场景数": sum(1 for spec in _DATASET_SCENARIOS.values() if spec.source != "builtin"),
            "扩展字段数": sum(1 for spec in _BOUNDARY_FIELDS.values() if spec.source != "builtin"),
        }


def reset_data_generator_registry() -> None:
    """清空后恢复内置项，供测试隔离使用。"""
    with _LOCK:
        _DATASET_SCENARIOS.clear()
        _BOUNDARY_FIELDS.clear()
        _LOCALES.clear()
        _install_defaults()


def _install_defaults() -> None:
    scenarios = (
        DatasetScenarioSpec(
            key="注册登录账号", label="注册登录账号",
            description="适合注册、登录、找回密码、账号绑定和用户中心场景。",
            fields=("username", "password", "phone", "email", "real_name", "id_card", "register_source"),
            builder_name="_build_registration_record",
        ),
        DatasetScenarioSpec(
            key="企业员工档案", label="企业员工档案",
            description="适合后台导入员工、组织架构、审批流和通讯录场景。",
            fields=("employee_no", "name", "department", "role", "phone", "email", "hire_date", "status"),
            builder_name="_build_employee_record",
        ),
        DatasetScenarioSpec(
            key="收货地址簿", label="收货地址簿",
            description="适合电商、物流、地址簿管理和联系人信息场景。",
            fields=("receiver_name", "receiver_phone", "province", "city", "address", "postcode", "label"),
            builder_name="_build_shipping_record",
        ),
        DatasetScenarioSpec(
            key="订单支付记录", label="订单支付记录",
            description="适合订单流、支付回调、账单对账和数据联调场景。",
            fields=("order_no", "user_no", "product_name", "order_amount", "discount_amount", "pay_status", "order_status"),
            builder_name="_build_order_record",
        ),
    )
    fields = (
        BoundaryFieldSpec("用户名", "用户名", "默认规则：只允许字母、数字、下划线，长度受 min/max 约束。", "用户名"),
        BoundaryFieldSpec("密码", "密码", "默认规则：需包含大小写字母、数字和特殊字符。", "密码"),
        BoundaryFieldSpec("邮箱", "邮箱", "默认规则：遵循常见邮箱格式校验。", "邮箱"),
        BoundaryFieldSpec("手机号", "手机号", "默认规则：中国大陆 11 位手机号。", "手机号"),
        BoundaryFieldSpec("身份证号", "身份证号", "默认规则：中国大陆 18 位身份证号，需满足校验位。", "身份证号"),
        BoundaryFieldSpec("金额", "金额", "默认规则：数值需在范围内，最多保留两位小数。", "金额"),
    )
    locales = (
        LocaleSpec("zh_CN", "简体中文", "zh_CN"),
        LocaleSpec("en_US", "English (US)", "en_US"),
        LocaleSpec("ja_JP", "日本語", "ja_JP"),
    )
    with _LOCK:
        for spec in scenarios:
            _DATASET_SCENARIOS[spec.key] = spec
        for spec in fields:
            _BOUNDARY_FIELDS[spec.key] = spec
        for spec in locales:
            _LOCALES[spec.key] = spec


_install_defaults()
