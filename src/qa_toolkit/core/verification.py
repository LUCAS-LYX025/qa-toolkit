"""独立验收引擎（SoduWork「AI review + 人工签字」的确定性版本）。

机器只做能客观判定的检查；语义覆盖、脱敏真实性这类判断留给提出人签字，
不假装 AI 已经确认。检查器全部是纯函数，便于单测与复用。
"""
from __future__ import annotations

import datetime
import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from qa_toolkit.core.i18n import t
from qa_toolkit.core.workflow_registry import CriterionSpec, get_workflow, list_workflows

Checker = Callable[[str, Any], Tuple[bool, str]]


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def artifact_to_text(artifact: Any) -> str:
    """把任意工具产物归一成可检查的文本。"""
    if artifact is None:
        return ""
    if isinstance(artifact, str):
        return artifact
    if isinstance(artifact, (bytes, bytearray)):
        return bytes(artifact).decode("utf-8", errors="replace")
    # DataFrame 等对象用 duck typing，避免这里硬依赖 pandas。
    if hasattr(artifact, "to_csv") and hasattr(artifact, "columns"):
        try:
            return artifact.to_csv(index=False)
        except Exception:
            pass
    try:
        return json.dumps(artifact, ensure_ascii=False, indent=2, default=str)
    except Exception:
        return str(artifact)


def _tokens(expected: Any) -> List[str]:
    if expected is None:
        return []
    if isinstance(expected, (list, tuple, set)):
        return [str(item) for item in expected if str(item)]
    return [str(expected)] if str(expected) else []


def _check_non_empty(text: str, expected: Any) -> Tuple[bool, str]:
    length = len(text.strip())
    return (length > 0, f"有效字符 {length} 个" if length else "结果为空白")


def _check_min_chars(text: str, expected: Any) -> Tuple[bool, str]:
    try:
        minimum = int(expected or 0)
    except (TypeError, ValueError):
        return False, f"阈值非法: {expected!r}"
    length = len(text.strip())
    return (length >= minimum, f"{length}/{minimum} 字符")


def _check_max_chars(text: str, expected: Any) -> Tuple[bool, str]:
    try:
        maximum = int(expected or 0)
    except (TypeError, ValueError):
        return False, f"阈值非法: {expected!r}"
    length = len(text.strip())
    return (length <= maximum, f"{length}/{maximum} 字符")


def _check_contains_all(text: str, expected: Any) -> Tuple[bool, str]:
    lowered = text.lower()
    missing = [token for token in _tokens(expected) if token.lower() not in lowered]
    return (not missing, "全部命中" if not missing else "缺少: " + "、".join(missing))


def _check_contains_any(text: str, expected: Any) -> Tuple[bool, str]:
    lowered = text.lower()
    hits = [token for token in _tokens(expected) if token.lower() in lowered]
    return (bool(hits), "命中: " + "、".join(hits) if hits else "均未命中")


def _check_not_contains(text: str, expected: Any) -> Tuple[bool, str]:
    lowered = text.lower()
    hits = [token for token in _tokens(expected) if token.lower() in lowered]
    return (not hits, "无禁用词" if not hits else "出现禁用词: " + "、".join(hits))


_PLACEHOLDER_RE = re.compile(
    r"\{\{[^}]*\}\}|\$\{[^}]*\}|<[^>\n]{1,40}>|\b(?:TODO|FIXME|TBD|待补充|待确认|待定|占位符|示例文本)\b",
    re.IGNORECASE,
)


def _check_no_placeholder(text: str, expected: Any) -> Tuple[bool, str]:
    hits = _PLACEHOLDER_RE.findall(text)
    return (not hits, "无占位符" if not hits else "残留占位符: " + "、".join(dict.fromkeys(hits))[:120])


_SECRET_PATTERNS: Tuple[Tuple[str, re.Pattern], ...] = (
    ("OpenAI Key", re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b")),
    ("GitHub Token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("AWS Key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("Bearer 凭据", re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]{20,}", re.IGNORECASE)),
    ("明文密码", re.compile(r"\b(?:password|passwd|pwd)\s*[:=]\s*\S{6,}", re.IGNORECASE)),
    ("明文 API Key", re.compile(r"\bapi[_-]?key\s*[:=]\s*\S{8,}", re.IGNORECASE)),
    ("私钥", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
)


def _check_no_secret(text: str, expected: Any) -> Tuple[bool, str]:
    hits = [name for name, pattern in _SECRET_PATTERNS if pattern.search(text)]
    return (not hits, "无明文凭据" if not hits else "疑似泄漏: " + "、".join(hits))


def _check_json_parseable(text: str, expected: Any) -> Tuple[bool, str]:
    candidate = text.strip()
    if candidate.startswith("```"):
        candidate = re.sub(r"^```[a-zA-Z0-9]*\s*", "", candidate)
        candidate = re.sub(r"\s*```$", "", candidate).strip()
    try:
        json.loads(candidate)
        return True, "JSON 解析通过"
    except Exception:
        first_error = "JSON 解析失败"
    starts = [pos for pos in (candidate.find("{"), candidate.find("[")) if pos >= 0]
    if starts:
        begin = min(starts)
        closes = [pos for pos in (candidate.rfind("}"), candidate.rfind("]")) if pos > begin]
        if closes:
            try:
                json.loads(candidate[begin : max(closes) + 1])
                return True, "从文本中提取到合法 JSON 块"
            except Exception:
                pass
    return False, first_error


def _check_manual(text: str, expected: Any) -> Tuple[bool, str]:
    return False, "需提出人签字确认"


CHECKERS: Dict[str, Checker] = {
    "non_empty": _check_non_empty,
    "min_chars": _check_min_chars,
    "max_chars": _check_max_chars,
    "contains_all": _check_contains_all,
    "contains_any": _check_contains_any,
    "not_contains": _check_not_contains,
    "no_placeholder": _check_no_placeholder,
    "no_secret": _check_no_secret,
    "json_parseable": _check_json_parseable,
    "manual": _check_manual,
}


@dataclass(frozen=True)
class CriterionResult:
    key: str
    label: str
    check: str
    passed: bool
    required: bool
    evidence: str
    manual: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "check": self.check,
            "passed": self.passed,
            "required": self.required,
            "evidence": self.evidence,
            "manual": self.manual,
        }


@dataclass(frozen=True)
class VerificationReport:
    workflow_key: str
    workflow_name: str
    workflow_version: str
    tool: str
    checked_at: str
    artifact_digest: str
    results: Tuple[CriterionResult, ...]
    automated_passed: bool
    manual_pending: int
    passed_count: int
    total_count: int

    @property
    def score(self) -> float:
        return self.passed_count / self.total_count if self.total_count else 1.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "workflow_key": self.workflow_key,
            "workflow_name": self.workflow_name,
            "workflow_version": self.workflow_version,
            "tool": self.tool,
            "checked_at": self.checked_at,
            "artifact_digest": self.artifact_digest,
            "results": [item.to_dict() for item in self.results],
            "automated_passed": self.automated_passed,
            "manual_pending": self.manual_pending,
            "passed_count": self.passed_count,
            "total_count": self.total_count,
            "score": round(self.score, 3),
        }


def verify_criteria(
    criteria: Sequence[CriterionSpec],
    artifact: Any,
    *,
    workflow_key: str = "custom",
    workflow_name: str = "自定义验收",
    workflow_version: str = "1.0.0",
    tool: str = "",
) -> VerificationReport:
    """对任意一组验收标准执行确定性校验。"""
    text = artifact_to_text(artifact)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    results: List[CriterionResult] = []
    for criterion in criteria:
        checker = CHECKERS.get(criterion.check)
        if checker is None:
            passed, evidence = False, f"未知检查器: {criterion.check}"
        else:
            passed, evidence = checker(text, criterion.expected)
        results.append(
            CriterionResult(
                key=criterion.key,
                label=criterion.label,
                check=criterion.check,
                passed=bool(passed),
                required=bool(criterion.required),
                evidence=str(evidence),
                manual=criterion.check == "manual",
            )
        )

    automated_passed = all(
        item.passed for item in results if item.required and not item.manual
    )
    manual_pending = sum(1 for item in results if item.required and item.manual)
    return VerificationReport(
        workflow_key=workflow_key,
        workflow_name=workflow_name,
        workflow_version=workflow_version,
        tool=tool,
        checked_at=_utc_now_iso(),
        artifact_digest=digest,
        results=tuple(results),
        automated_passed=automated_passed,
        manual_pending=manual_pending,
        passed_count=sum(1 for item in results if item.passed),
        total_count=len(results),
    )


def verify_workflow(workflow_key: str, artifact: Any, *, tool: str = "") -> Optional[VerificationReport]:
    """按注册的工作方法验收；工作流不存在时返回 None。"""
    spec = get_workflow(workflow_key)
    if spec is None:
        return None
    return verify_criteria(
        spec.criteria,
        artifact,
        workflow_key=spec.key,
        workflow_name=spec.name,
        workflow_version=spec.version,
        tool=tool or spec.tool,
    )


def workflow_options(tool: str = "") -> Tuple[List[str], Dict[str, str]]:
    """给下拉框用的稳定选项：返回 key 列表与 key→标签映射。"""
    specs = list_workflows(tool=tool)
    keys = sorted(specs.keys(), key=lambda key: (specs[key].tool != "", key))
    labels = {key: f"{t(specs[key].name)} · v{specs[key].version}" for key in keys}
    return keys, labels
