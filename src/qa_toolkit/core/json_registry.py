"""JSON 处理工具的注册式扩展点。

页面只从注册表读取选项，业务方可以在不改动页面和核心工具的前提下注册新的
JSONPath 函数、差异比较规则、导出格式与文本校验器。
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

JsonPathFunction = Callable[[Any], Any]
DiffRule = Callable[[Any, Any, str], Optional[str]]
Serializer = Callable[[Any], str]
Validator = Callable[[str], list[str]]


@dataclass(frozen=True)
class JsonPathFunctionSpec:
    name: str
    func: JsonPathFunction
    description: str = ""


@dataclass(frozen=True)
class DiffRuleSpec:
    name: str
    func: DiffRule
    description: str = ""


@dataclass(frozen=True)
class ExportFormatSpec:
    name: str
    extension: str
    mime: str
    serializer: Serializer
    description: str = ""


@dataclass(frozen=True)
class ValidatorSpec:
    name: str
    func: Validator
    description: str = ""


@dataclass(frozen=True)
class JsonSampleSpec:
    name: str
    text: str
    expression: str = ""
    description: str = ""


_JSONPATH_FUNCTIONS: Dict[str, JsonPathFunctionSpec] = {}
_DIFF_RULES: Dict[str, DiffRuleSpec] = {}
_EXPORT_FORMATS: Dict[str, ExportFormatSpec] = {}
_VALIDATORS: Dict[str, ValidatorSpec] = {}
_SAMPLES: Dict[str, JsonSampleSpec] = {}


def _register(mapping: Dict[str, Any], name: str, spec: Any, *, replace: bool) -> None:
    key = str(name).strip()
    if not key:
        raise ValueError("扩展点名称不能为空")
    if key in mapping and not replace:
        raise ValueError(f"扩展点已存在: {key}")
    mapping[key] = spec


def register_jsonpath_function(
    name: str,
    func: JsonPathFunction,
    *,
    description: str = "",
    replace: bool = False,
) -> None:
    """注册可在路径末尾调用的函数，例如 ``$.items.length()``。"""
    _register(
        _JSONPATH_FUNCTIONS,
        name,
        JsonPathFunctionSpec(name, func, description),
        replace=replace,
    )


def register_diff_rule(
    name: str,
    func: DiffRule,
    *,
    description: str = "",
    replace: bool = False,
) -> None:
    """注册自定义差异规则；返回 None 表示该项目无差异。"""
    _register(_DIFF_RULES, name, DiffRuleSpec(name, func, description), replace=replace)


def register_export_format(
    name: str,
    *,
    extension: str,
    mime: str,
    serializer: Serializer,
    description: str = "",
    replace: bool = False,
) -> None:
    """注册下载格式，页面会自动出现在格式选项中。"""
    _register(
        _EXPORT_FORMATS,
        name,
        ExportFormatSpec(name, extension, mime, serializer, description),
        replace=replace,
    )


def register_validator(
    name: str,
    func: Validator,
    *,
    description: str = "",
    replace: bool = False,
) -> None:
    """注册针对原始 JSON 文本的校验器，返回问题说明列表。"""
    _register(_VALIDATORS, name, ValidatorSpec(name, func, description), replace=replace)


def register_sample(
    name: str,
    *,
    text: str,
    expression: str = "",
    description: str = "",
    replace: bool = False,
) -> None:
    """注册可一键载入的示例，便于业务方沉淀自己的测试样例。"""
    _register(
        _SAMPLES,
        name,
        JsonSampleSpec(name, text, expression, description),
        replace=replace,
    )


def get_jsonpath_functions() -> Dict[str, JsonPathFunctionSpec]:
    return dict(_JSONPATH_FUNCTIONS)


def get_diff_rules() -> Dict[str, DiffRuleSpec]:
    return dict(_DIFF_RULES)


def get_export_formats() -> Dict[str, ExportFormatSpec]:
    return dict(_EXPORT_FORMATS)


def get_validators() -> Dict[str, ValidatorSpec]:
    return dict(_VALIDATORS)


def get_samples() -> Dict[str, JsonSampleSpec]:
    return dict(_SAMPLES)


def get_registry_summary() -> Dict[str, int]:
    return {
        "jsonpath_functions": len(_JSONPATH_FUNCTIONS),
        "diff_rules": len(_DIFF_RULES),
        "export_formats": len(_EXPORT_FORMATS),
        "validators": len(_VALIDATORS),
        "samples": len(_SAMPLES),
    }


def _length(value: Any) -> Any:
    if isinstance(value, (str, list, dict, tuple)):
        return len(value)
    return 1


def _keys(value: Any) -> Any:
    return list(value.keys()) if isinstance(value, dict) else []


def _values(value: Any) -> Any:
    return list(value.values()) if isinstance(value, dict) else (list(value) if isinstance(value, list) else [])


register_jsonpath_function("length", _length, description="返回字符串/数组/对象长度")
register_jsonpath_function("keys", _keys, description="返回对象的键列表")
register_jsonpath_function("values", _values, description="返回对象的值列表")


def _json_serializer(value: Any) -> str:
    from qa_toolkit.utils.json_utils import serialize_json

    return serialize_json(value, indent=2)


def _jsonl_serializer(value: Any) -> str:
    from qa_toolkit.utils.json_utils import serialize_json

    items = value if isinstance(value, list) else [value]
    return "\n".join(serialize_json(item, compact=True) for item in items)


def _text_serializer(value: Any) -> str:
    if isinstance(value, str):
        return value
    return _json_serializer(value)


register_export_format("JSON", extension="json", mime="application/json", serializer=_json_serializer)
register_export_format("JSONL", extension="jsonl", mime="application/x-ndjson", serializer=_jsonl_serializer)
register_export_format("纯文本", extension="txt", mime="text/plain", serializer=_text_serializer)

register_sample(
    "接口响应",
    text='{\n  "code": 0,\n  "data": {"userId": 1001, "tags": ["qa", "regression"]},\n  "traceId": "trace-20260405-0001"\n}',
    expression="$.data.tags[*]",
    description="嵌套对象与数组，适合练手基础路径。",
)
register_sample(
    "日志 JSONL",
    text='{"level":"INFO","trace":"T-1","cost":12}\n{"level":"ERROR","trace":"T-2","cost":300}\n{"level":"INFO","trace":"T-3","cost":20}',
    expression="$[?(@.level=='ERROR')].trace",
    description="逐行 JSON，开启 JSONL 模式后作为数组解析。",
)
register_sample(
    "店铺数据",
    text='{"store":{"book":[{"title":"A","author":"X","price":8},{"title":"B","author":"Y","price":12}]}}',
    expression="$..book[?(@.price<10)].title",
    description="递归下降与过滤表达式示例。",
)
