"""验收驱动工作流的注册中心。

设计借鉴 SoduWork 的三个对象分离：

* ``WorkflowSpec`` 是**不可变的方法定义**：做什么、按什么标准验收；
  公司地址、模型、密钥一律不写进 spec。
* 工具 + 用户输入是**绑定（binding）**，只存在于一次页面会话里。
* 每次执行产生一条 ``RunRecord``（见 ``core.task_runner``），
  携带验收报告与人工签字，成为可追溯的事实来源。

沿用本项目的注册中心惯例：frozen Spec、显式 ``replace``、getter 返回副本、
``reset`` 供测试隔离。新增一种工作方式无需改页面代码。
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

_LOCK = threading.RLock()


@dataclass(frozen=True)
class CriterionSpec:
    """一条验收标准。

    ``check`` 指向 ``core.verification.CHECKERS`` 中的确定性检查器；
    ``manual`` 表示机器无法判断，只能由请求人签字时人工确认。
    """

    key: str
    label: str
    check: str
    expected: Any = None
    required: bool = True
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "check": self.check,
            "expected": self.expected,
            "required": self.required,
            "description": self.description,
        }


@dataclass(frozen=True)
class WorkflowSpec:
    """一份可复用的工作方法：步骤 + 验收标准。"""

    key: str
    name: str
    tool: str = ""  # 空串表示通用，可套用到任意工具
    description: str = ""
    version: str = "1.0.0"
    steps: Tuple[str, ...] = ()
    criteria: Tuple[CriterionSpec, ...] = ()
    tags: Tuple[str, ...] = ()
    enabled: bool = True
    source: str = "builtin"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "name": self.name,
            "tool": self.tool,
            "description": self.description,
            "version": self.version,
            "steps": list(self.steps),
            "criteria": [item.to_dict() for item in self.criteria],
            "tags": list(self.tags),
            "enabled": self.enabled,
            "source": self.source,
        }


_WORKFLOWS: Dict[str, WorkflowSpec] = {}


def _register(spec: WorkflowSpec, *, replace: bool = False) -> None:
    if not spec.key:
        raise ValueError("工作流 key 不能为空")
    if not spec.name:
        raise ValueError(f"工作流 {spec.key!r} 的 name 不能为空")
    with _LOCK:
        if spec.key in _WORKFLOWS and not replace:
            raise ValueError(f"工作流 {spec.key!r} 已注册；覆盖请传 replace=True")
        _WORKFLOWS[spec.key] = spec


def register_workflow(spec: WorkflowSpec, *, replace: bool = False) -> None:
    """注册一份工作方法；同名覆盖必须显式 ``replace=True``。"""
    _register(spec, replace=replace)


def get_workflow(key: str) -> Optional[WorkflowSpec]:
    with _LOCK:
        return _WORKFLOWS.get(str(key or ""))


def list_workflows(*, tool: str = "", include_disabled: bool = False) -> Dict[str, WorkflowSpec]:
    """列出可用工作流；``tool`` 精确匹配时同时返回通用工作流。"""
    with _LOCK:
        result: Dict[str, WorkflowSpec] = {}
        for key, spec in _WORKFLOWS.items():
            if not include_disabled and not spec.enabled:
                continue
            if tool and spec.tool and spec.tool != tool:
                continue
            result[key] = spec
        return result


def get_workflow_summary() -> Dict[str, Any]:
    with _LOCK:
        specs = list(_WORKFLOWS.values())
        return {
            "工作流总数": len(specs),
            "启用中": sum(1 for spec in specs if spec.enabled),
            "验收标准总数": sum(len(spec.criteria) for spec in specs),
            "人工确认项": sum(1 for spec in specs for item in spec.criteria if item.check == "manual"),
            "自带工作流": sum(1 for spec in specs if spec.source == "builtin"),
            "扩展工作流": sum(1 for spec in specs if spec.source != "builtin"),
        }


def reset_workflows() -> None:
    """恢复到内置工作流，供测试隔离；自定义项被清空。"""
    with _LOCK:
        _WORKFLOWS.clear()
        for spec in _BUILTIN_WORKFLOWS:
            _WORKFLOWS[spec.key] = spec


_BUILTIN_WORKFLOWS: Tuple[WorkflowSpec, ...] = (
    WorkflowSpec(
        key="generic_output",
        name="通用交付验收",
        tool="",
        description="适用于任意工具的结果：非空、无占位符、无明文凭据。",
        steps=("生成结果", "逐条验收", "人工签字"),
        criteria=(
            CriterionSpec("non_empty", "结果非空", "non_empty", description="结果不能是空白内容。"),
            CriterionSpec("no_placeholder", "无未填占位符", "no_placeholder",
                          description="不能残留 TODO / 待补充 / {{}} 等占位内容。"),
            CriterionSpec("no_secret", "无明文凭据", "no_secret",
                          description="不能把 API Key、Token、密码明文写进产物。"),
        ),
        tags=("通用", "基线"),
    ),
    WorkflowSpec(
        key="test_case_delivery",
        name="测试用例交付验收",
        tool="测试用例生成器",
        description="生成用例后先过机器校验，再由提出人确认覆盖验收标准。",
        steps=("提出需求与验收标准", "生成用例", "独立校验", "提出人签字"),
        criteria=(
            CriterionSpec("non_empty", "用例非空", "non_empty"),
            CriterionSpec("min_chars", "内容完整度", "min_chars", expected=80),
            CriterionSpec("contains_all", "关键章节齐全", "contains_all",
                          expected=["用例", "步骤", "预期"]),
            CriterionSpec("no_placeholder", "无未填占位符", "no_placeholder"),
            CriterionSpec("no_secret", "无明文凭据", "no_secret"),
            CriterionSpec("manual", "覆盖需求验收标准", "manual",
                          description="机器无法判断语义覆盖，由提出人签字时确认。"),
        ),
        tags=("测试用例", "验收标准"),
    ),
    WorkflowSpec(
        key="json_output",
        name="结构化数据验收",
        tool="",
        description="结果必须能被解析成 JSON，且不含占位符与凭据。",
        steps=("生成数据", "解析校验", "人工签字"),
        criteria=(
            CriterionSpec("json_parseable", "JSON 可解析", "json_parseable"),
            CriterionSpec("no_placeholder", "无未填占位符", "no_placeholder"),
            CriterionSpec("no_secret", "无明文凭据", "no_secret"),
        ),
        tags=("JSON", "结构化"),
    ),
    WorkflowSpec(
        key="api_case_delivery",
        name="接口用例交付验收",
        tool="接口自动化测试",
        description="接口用例/脚本交付前的基线检查，敏感字段必须脱敏。",
        steps=("生成接口用例", "独立校验", "提出人签字"),
        criteria=(
            CriterionSpec("non_empty", "用例非空", "non_empty"),
            CriterionSpec("contains_any", "含请求或断言信息", "contains_any",
                          expected=["请求", "断言", "assert", "method", "url"]),
            CriterionSpec("no_secret", "无明文凭据", "no_secret"),
            CriterionSpec("manual", "鉴权与数据已脱敏", "manual",
                          description="由提出人确认真实环境与敏感数据未泄漏。"),
        ),
        tags=("接口", "安全"),
    ),
)

reset_workflows()
