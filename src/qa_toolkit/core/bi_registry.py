"""BI 分析工具的可扩展注册表。

场景识别规则、模板、图表类型、聚合函数都通过这里注册，新增业务能力不需要改动
``bi_analysis.py`` 里的 if/elif。默认注册项与历史行为保持一致。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple

import pandas as pd
import plotly.express as px


@dataclass(frozen=True)
class ScenarioRule:
    """一类业务场景的识别规则。

    ``excluded_keywords`` 用于排除名字里带有干扰词的列，例如 area_code / zip_code
    不应该被 ``code`` 关键词识别成状态码。
    """

    name: str
    keywords: Sequence[str]
    numeric_only: bool = False
    excluded_keywords: Sequence[str] = field(default_factory=tuple)
    priority: int = 100


@dataclass(frozen=True)
class TemplateSpec:
    """一个内置模板的说明与数据生成函数。"""

    description: str
    provider: Callable[[], pd.DataFrame]


ChartBuilder = Callable[..., Any]
Aggregator = Any  # pandas aggfunc 接受的字符串或可调用对象


def _default_scenario_rules() -> List[ScenarioRule]:
    return [
        ScenarioRule("测试执行", ["执行结果", "结果", "result", "case_status", "status_text"]),
        ScenarioRule(
            "开发日志",
            ["status_code", "http_status", "状态码", "响应码", "code"],
            excluded_keywords=("area", "zip", "postal", "region", "country", "地区", "邮编", "区域"),
            priority=10,
        ),
        ScenarioRule("埋点事件", ["event_name", "event", "事件", "action", "埋点"]),
        ScenarioRule("业务分析", ["销售额", "金额", "gmv", "revenue", "amount", "total_amount"], numeric_only=True),
    ]


def _default_templates() -> Dict[str, TemplateSpec]:
    # 延迟导入避免 core <-> tools 的循环依赖；provider 在调用时才真正构造 DataFrame。
    from qa_toolkit.tools.bi_analysis import default_template_frames

    frames = default_template_frames()
    return {
        name: TemplateSpec(description, (lambda frame=frame: frame.copy()))
        for name, (description, frame) in frames.items()
    }


def _default_charts() -> Dict[str, ChartBuilder]:
    return {
        "柱状图": px.bar,
        "折线图": lambda df, x, y, color=None: px.line(df, x=x, y=y, color=color, markers=True),
        "散点图": px.scatter,
        "箱线图": px.box,
        "面积图": px.area,
        "饼图": lambda df, x, y, color=None: px.pie(df, names=x, values=y, color=color),
    }


def _default_aggregators() -> Dict[str, Aggregator]:
    return {name: name for name in ("sum", "mean", "count", "min", "max")}


_SCENARIO_RULES: List[ScenarioRule] = _default_scenario_rules()
# 模板 provider 需要导入 tools.bi_analysis，放到首次使用时再加载，避免循环依赖。
_TEMPLATES: Optional[Dict[str, TemplateSpec]] = None
_CHARTS: Dict[str, ChartBuilder] = _default_charts()
_AGGREGATORS: Dict[str, Aggregator] = _default_aggregators()


def _ensure_templates() -> Dict[str, TemplateSpec]:
    global _TEMPLATES
    if _TEMPLATES is None:
        _TEMPLATES = _default_templates()
    return _TEMPLATES


def register_scenario(rule: ScenarioRule) -> None:
    """注册或替换一条场景识别规则（按 name 覆盖）。"""
    if not rule.name or not rule.keywords:
        raise ValueError("场景规则需要 name 与 keywords")
    global _SCENARIO_RULES
    _SCENARIO_RULES = [item for item in _SCENARIO_RULES if item.name != rule.name]
    _SCENARIO_RULES.append(rule)
    _SCENARIO_RULES.sort(key=lambda item: item.priority)


def scenario_rules() -> Tuple[ScenarioRule, ...]:
    return tuple(_SCENARIO_RULES)


def register_template(name: str, description: str, provider: Callable[[], pd.DataFrame]) -> None:
    if not name or not callable(provider):
        raise ValueError("模板需要名称与可调用的 provider")
    _ensure_templates()[name] = TemplateSpec(description, provider)


def template_names() -> List[str]:
    return list(_ensure_templates())


def template_description(name: str) -> str:
    templates = _ensure_templates()
    return templates[name].description if name in templates else ""


def build_template_frame(name: str) -> pd.DataFrame:
    templates = _ensure_templates()
    if name not in templates:
        raise KeyError(f"未注册的模板: {name}")
    return templates[name].provider()


def register_chart(name: str, builder: ChartBuilder) -> None:
    if not name or not callable(builder):
        raise ValueError("图表需要名称与可调用的 builder")
    _CHARTS[name] = builder


def chart_names() -> List[str]:
    return list(_CHARTS)


def build_chart(name: str, frame: pd.DataFrame, x: str, y: str, color: Optional[str] = None) -> Any:
    if name not in _CHARTS:
        raise KeyError(f"未注册的图表类型: {name}")
    return _CHARTS[name](frame, x=x, y=y, color=color)


def register_aggregator(name: str, aggregator: Aggregator) -> None:
    if not name or not (isinstance(aggregator, str) or callable(aggregator)):
        raise ValueError("聚合函数需要名称与字符串或可调用对象")
    _AGGREGATORS[name] = aggregator


def aggregator_names() -> List[str]:
    return list(_AGGREGATORS)


def resolve_aggregator(name: str) -> Aggregator:
    if name not in _AGGREGATORS:
        raise KeyError(f"未注册的聚合函数: {name}")
    return _AGGREGATORS[name]


def reset_bi_registry() -> None:
    """恢复默认注册项，主要供测试隔离使用。"""
    global _SCENARIO_RULES, _TEMPLATES, _CHARTS, _AGGREGATORS
    _SCENARIO_RULES = _default_scenario_rules()
    _TEMPLATES = None
    _CHARTS = _default_charts()
    _AGGREGATORS = _default_aggregators()


def find_registered_columns(
    frame: pd.DataFrame,
    rule: ScenarioRule,
    normalize,
) -> Optional[str]:
    """按规则查找列：先精确匹配，再子串匹配，并跳过排除词命中的列。"""
    keywords = [normalize(word) for word in rule.keywords]
    excluded = [normalize(word) for word in rule.excluded_keywords]

    def acceptable(column: Any) -> bool:
        normalized = normalize(column)
        if any(word in normalized for word in excluded):
            return False
        if rule.numeric_only and not pd.api.types.is_numeric_dtype(frame[column]):
            return False
        return True

    columns = [column for column in frame.columns if acceptable(column)]
    for column in columns:
        if normalize(column) in keywords:
            return column
    for column in columns:
        if any(word in normalize(column) for word in keywords):
            return column
    return None
