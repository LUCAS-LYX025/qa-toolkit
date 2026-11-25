"""JSON 解析、比较与 JSONPath 查询工具。

对外保留 :class:`JSONFileUtils` 兼容接口，同时提供无 UI 依赖的纯函数，
供页面、测试和第三方扩展复用。
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple, Union

from qa_toolkit.core.json_registry import get_jsonpath_functions

MAX_INPUT_CHARS = 2_000_000
MAX_TRAVERSAL_DEPTH = 200
MAX_STRUCTURE_NODES = 20_000
MAX_JSONPATH_RESULTS = 10_000
MAX_DIFF_FRAGMENT = 120

_NUMBER_TYPES = (int, float)


class JsonParseError(ValueError):
    """带行列定位的 JSON 解析错误。"""

    def __init__(self, message: str, *, lineno: int = 1, colno: int = 1, kind: str = "json"):
        super().__init__(message)
        self.message = message
        self.lineno = lineno
        self.colno = colno
        self.kind = kind


@dataclass
class ParseResult:
    value: Any
    warnings: List[str] = field(default_factory=list)
    jsonl: bool = False


@dataclass
class ComparisonStats:
    differences_count: int = 0
    keys_compared: int = 0


# ---------------------------------------------------------------------------
# 解析与序列化
# ---------------------------------------------------------------------------
def _normalize_input(text: str) -> Tuple[str, List[str]]:
    warnings: List[str] = []
    if text is None:
        return "", warnings
    raw = str(text)
    if len(raw) > MAX_INPUT_CHARS:
        raise JsonParseError(
            f"输入超过 {MAX_INPUT_CHARS:,} 字符上限，请拆分后再处理。", kind="limit"
        )
    if raw.startswith("\ufeff"):
        raw = raw.lstrip("\ufeff")
        warnings.append("已自动剥离 UTF-8 BOM。")
    return raw, warnings


def _make_hooks(strict: bool, warnings: List[str]) -> Tuple[Callable[[List[Tuple[str, Any]]], Dict[str, Any]], Callable[[str], Any]]:
    def object_pairs_hook(pairs: Sequence[Tuple[str, Any]]) -> Dict[str, Any]:
        seen: set = set()
        for key, _ in pairs:
            if key in seen:
                warnings.append(f"检测到重复键 `{key}`，已保留最后一个值。")
            seen.add(key)
        return dict(pairs)

    def parse_constant(token: str) -> Any:
        if strict:
            raise JsonParseError(
                f"`{token}` 不是标准 JSON 数值，严格模式下已拒绝。", kind="non_standard"
            )
        warnings.append(f"包含非标准数值 `{token}`，导出为 JSON 时可能不被其他语言接受。")
        return json.loads(token) if token != "NaN" else float("nan")

    return object_pairs_hook, parse_constant


def parse_json_text(
    text: str,
    *,
    strict: bool = True,
    allow_jsonl: bool = True,
    max_chars: int = MAX_INPUT_CHARS,
) -> ParseResult:
    """解析 JSON/JSONL，默认拒绝重复键之外的非标准语法风险。

    ``strict=True`` 时拒绝 NaN/Infinity；重复键总会以警告形式返回，
    因为静默覆盖是配置比对场景的高频陷阱。
    """
    normalized, warnings = _normalize_input(text)
    if max_chars != MAX_INPUT_CHARS and len(normalized) > max_chars:
        raise JsonParseError(
            f"输入超过 {max_chars:,} 字符上限，请拆分后再处理。", kind="limit"
        )
    if not normalized.strip():
        raise JsonParseError("输入为空，请输入 JSON 内容。", kind="empty")

    pairs_hook, constant_hook = _make_hooks(strict, warnings)
    decode_kwargs = {"object_pairs_hook": pairs_hook, "parse_constant": constant_hook}
    try:
        return ParseResult(json.loads(normalized, **decode_kwargs), warnings, False)
    except JsonParseError:
        raise
    except json.JSONDecodeError as exc:
        first_error = exc

    if allow_jsonl:
        lines = [line for line in normalized.splitlines() if line.strip()]
        if len(lines) > 1:
            parsed: List[Any] = []
            for index, line in enumerate(lines, 1):
                try:
                    parsed.append(json.loads(line, **decode_kwargs))
                except (json.JSONDecodeError, JsonParseError) as exc:
                    if isinstance(exc, JsonParseError):
                        raise
                    break
            else:
                warnings.insert(0, f"按 JSONL 解析了 {len(parsed)} 行，作为数组处理。")
                return ParseResult(parsed, warnings, True)

    raise JsonParseError(
        first_error.msg,
        lineno=first_error.lineno,
        colno=first_error.colno,
        kind="syntax",
    )


def format_parse_error(error: Exception, source: str = "") -> str:
    """把解析异常转成带行列与上下文的可读中文说明。"""
    if isinstance(error, JsonParseError):
        if error.kind == "syntax":
            lines = source.splitlines()
            line = lines[error.lineno - 1] if 0 < error.lineno <= len(lines) else ""
            start = max(0, error.colno - 30)
            snippet = line[start : error.colno + 30].strip() or "(空)"
            hint = _error_hint(error.message)
            return (
                f"第 {error.lineno} 行第 {error.colno} 列：{error.message}\n"
                f"附近内容：`{snippet}`\n{hint}"
            )
        return error.message
    if isinstance(error, json.JSONDecodeError):
        return format_parse_error(
            JsonParseError(error.msg, lineno=error.lineno, colno=error.colno, kind="syntax"),
            source,
        )
    return str(error)


def _error_hint(message: str) -> str:
    if "property name" in message:
        return "常见原因：键名没用双引号、使用了单引号，或对象末尾多了一个逗号。"
    if "Expecting value" in message:
        return "常见原因：值缺少引号、使用了未加引号的字符串，或数组/对象中途截断。"
    if "Extra data" in message:
        return "常见原因：存在多个根节点；日志流请使用 JSONL 模式。"
    if "Unterminated string" in message:
        return "常见原因：字符串缺少结束引号，或反斜杠未转义。"
    return "请检查括号、引号和逗号是否成对。"


def serialize_json(
    value: Any,
    *,
    indent: Optional[int] = 2,
    ensure_ascii: bool = False,
    sort_keys: bool = False,
    compact: bool = False,
    allow_nan: bool = False,
) -> str:
    separators = (",", ":") if compact else None
    return json.dumps(
        value,
        indent=None if compact else indent,
        ensure_ascii=ensure_ascii,
        sort_keys=sort_keys,
        separators=separators,
        allow_nan=allow_nan,
    )


# ---------------------------------------------------------------------------
# 比较与结构分析
# ---------------------------------------------------------------------------
def _safe_fragment(value: Any) -> str:
    try:
        text = json.dumps(value, ensure_ascii=False, default=str, allow_nan=False)
    except (TypeError, ValueError):
        text = str(value)
    if len(text) > MAX_DIFF_FRAGMENT:
        text = text[:MAX_DIFF_FRAGMENT] + "…"
    return text.replace("`", "'")


def _value_kind(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, _NUMBER_TYPES):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, dict):
        return "dict"
    if isinstance(value, list):
        return "list"
    return type(value).__name__


def _is_number(value: Any) -> bool:
    return isinstance(value, _NUMBER_TYPES) and not isinstance(value, bool)


def compare_json_values(
    obj1: Any,
    obj2: Any,
    *,
    path: str = "",
    numeric_equivalent: bool = True,
    max_depth: int = MAX_TRAVERSAL_DEPTH,
    _visited: Optional[set] = None,
    _depth: int = 0,
    _stats: Optional[ComparisonStats] = None,
) -> Tuple[List[str], ComparisonStats]:
    """稳定顺序地比较两个 JSON 值，返回差异列表与统计。"""
    stats = _stats if _stats is not None else ComparisonStats()
    visited = set() if _visited is None else _visited
    differences: List[str] = []
    if _depth > max_depth:
        return [f"嵌套层级超过上限 {max_depth}: {path or '$'}"], stats

    stats.keys_compared += 1
    kind1, kind2 = _value_kind(obj1), _value_kind(obj2)
    same_kind = kind1 == kind2
    if numeric_equivalent and {kind1, kind2} == {"number", "number"}:
        same_kind = True

    if not same_kind:
        message = f"类型不同: {path or '$'} ({kind1} vs {kind2})"
        differences.append(message)
        stats.differences_count += 1
        return differences, stats

    if isinstance(obj1, (dict, list)):
        pair_key = (id(obj1), id(obj2))
        if pair_key in visited:
            return differences, stats
        visited = visited | {pair_key}

    if isinstance(obj1, dict):
        for key in sorted(set(obj1) | set(obj2), key=str):
            new_path = f"{path}.{key}" if path else str(key)
            if key not in obj2:
                differences.append(f"键缺失于 JSON2: {new_path}")
                stats.differences_count += 1
            elif key not in obj1:
                differences.append(f"键缺失于 JSON1: {new_path}")
                stats.differences_count += 1
            else:
                child, _ = compare_json_values(
                    obj1[key], obj2[key], path=new_path,
                    numeric_equivalent=numeric_equivalent, max_depth=max_depth,
                    _visited=visited, _depth=_depth + 1, _stats=stats,
                )
                differences.extend(child)
    elif isinstance(obj1, list):
        if len(obj1) != len(obj2):
            differences.append(f"数组长度不同: {path or '$'} ({len(obj1)} vs {len(obj2)})")
            stats.differences_count += 1
        for index, (left, right) in enumerate(zip(obj1, obj2)):
            child, _ = compare_json_values(
                left, right, path=f"{path}[{index}]",
                numeric_equivalent=numeric_equivalent, max_depth=max_depth,
                _visited=visited, _depth=_depth + 1, _stats=stats,
            )
            differences.extend(child)
    else:
        equal = obj1 == obj2
        if _is_number(obj1) and _is_number(obj2) and numeric_equivalent:
            equal = float(obj1) == float(obj2)
        if not equal:
            differences.append(
                f"值不同: {path or '$'} (`{_safe_fragment(obj1)}` vs `{_safe_fragment(obj2)}`)"
            )
            stats.differences_count += 1

    return differences, stats


def analyze_json_structure_safe(
    obj: Any,
    *,
    max_depth: int = MAX_TRAVERSAL_DEPTH,
    max_nodes: int = MAX_STRUCTURE_NODES,
) -> Dict[str, Any]:
    """迭代式结构分析，深层对象安全截断而不是抛 RecursionError。"""
    root: Dict[str, Any] = {"type": _value_kind(obj), "level": 0, "children": []}
    stack: List[Tuple[Any, Dict[str, Any], int]] = [(obj, root, 0)]
    visited: set = set()
    node_count = 0
    truncated = False
    reason = ""

    while stack:
        current, target, level = stack.pop()
        node_count += 1
        if node_count > max_nodes:
            truncated = True
            reason = f"节点数超过上限 {max_nodes}"
            break
        if isinstance(current, (dict, list)):
            if id(current) in visited:
                target["value"] = "(循环引用)"
                continue
            visited.add(id(current))
        target["size"] = len(current) if hasattr(current, "__len__") else 1
        if not isinstance(current, (dict, list)):
            target["value"] = _safe_fragment(current)
            continue
        if level >= max_depth:
            target["truncated"] = True
            truncated = True
            reason = f"嵌套层级超过上限 {max_depth}"
            continue
        if isinstance(current, dict):
            items: Iterable[Tuple[str, Any]] = sorted(current.items(), key=lambda pair: str(pair[0]))
        else:
            items = list(enumerate(current))
        for key, value in items:
            child: Dict[str, Any] = {"type": _value_kind(value), "level": level + 1, "children": []}
            if isinstance(key, str):
                child["key"] = key
            else:
                child["index"] = key
            target["children"].append(child)
            stack.append((value, child, level + 1))

    root["truncated"] = truncated
    if reason:
        root["truncation_reason"] = reason
    return root


def get_json_depth_safe(obj: Any, *, max_depth: int = MAX_TRAVERSAL_DEPTH) -> int:
    """容器层级：标量 0、空容器 1、``{\"a\":{}}`` 为 2。"""
    visited: set = set()

    def walk(value: Any, depth: int) -> int:
        if depth >= max_depth:
            return depth
        if not isinstance(value, (dict, list)):
            return depth
        if id(value) in visited:
            return depth
        visited.add(id(value))
        children = value.values() if isinstance(value, dict) else value
        if not children:
            return depth + 1
        return max(walk(child, depth + 1) for child in children)

    return walk(obj, 0)


# ---------------------------------------------------------------------------
# JSONPath
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class _Token:
    kind: str
    value: str


def _find_closing_bracket(path: str, start: int) -> int:
    depth = 0
    quote = ""
    escaped = False
    for index in range(start, len(path)):
        char = path[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
        elif char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return index
    return -1


def _tokenize_jsonpath(expression: str) -> List[_Token]:
    path = (expression or "").strip()
    if not path:
        raise JsonParseError("JSONPath 表达式不能为空。", kind="jsonpath")
    if not path.startswith("$"):
        raise JsonParseError("JSONPath 表达式需以 `$` 开头。", kind="jsonpath")

    tokens: List[_Token] = []
    index = 1
    while index < len(path):
        char = path[index]
        if path.startswith("..", index):
            index += 2
            if index < len(path) and path[index] == "[":
                close = _find_closing_bracket(path, index)
                if close == -1:
                    raise JsonParseError("JSONPath 括号未闭合。", kind="jsonpath")
                tokens.append(_Token("recursive_bracket", path[index + 1 : close]))
                index = close + 1
                continue
            match = re.match(r"[A-Za-z_][\w\-]*|\*", path[index:])
            if not match:
                raise JsonParseError("`..` 后需要属性名或 `*`。", kind="jsonpath")
            tokens.append(_Token("recursive", match.group(0)))
            index += len(match.group(0))
            continue
        if char == ".":
            index += 1
            match = re.match(r"([A-Za-z_]\w*)\s*\(\s*\)", path[index:])
            if match:
                tokens.append(_Token("function", match.group(1)))
                index += len(match.group(0))
                continue
            match = re.match(r"[A-Za-z_][\w\-]*|\*", path[index:])
            if not match:
                raise JsonParseError("`.` 后需要属性名或 `*`。", kind="jsonpath")
            tokens.append(_Token("child", match.group(0)))
            index += len(match.group(0))
            continue
        if char == "[":
            close = _find_closing_bracket(path, index)
            if close == -1:
                raise JsonParseError("JSONPath 括号未闭合。", kind="jsonpath")
            content = path[index + 1 : close].strip()
            if not content:
                raise JsonParseError("JSONPath 括号内不能为空。", kind="jsonpath")
            tokens.append(_Token("bracket", content))
            index = close + 1
            continue
        raise JsonParseError(f"无法解析的 JSONPath 片段: `{path[index:index + 12]}`", kind="jsonpath")
    return tokens


def _unquote(text: str) -> Optional[str]:
    text = text.strip()
    if len(text) >= 2 and text[0] == text[-1] and text[0] in "\"'":
        try:
            return json.loads(text) if text[0] == '"' else text[1:-1]
        except json.JSONDecodeError:
            return text[1:-1]
    return None


def _parse_index_expression(expr: str) -> Tuple[str, Any]:
    quoted = _unquote(expr)
    if quoted is not None:
        return "child", quoted
    if expr == "*":
        return "wildcard", None
    if expr.startswith("?(") and expr.endswith(")"):
        return "filter", expr[2:-1].strip()
    if ":" in expr:
        parts = expr.split(":")
        if len(parts) > 3 or any(part and not re.fullmatch(r"-?\d+", part.strip()) for part in parts):
            raise JsonParseError(f"无效的切片表达式: `{expr}`", kind="jsonpath")
        numbers = [int(part.strip()) if part.strip() else None for part in parts]
        if len(numbers) >= 3 and numbers[2] == 0:
            raise JsonParseError("切片步长不能为 0。", kind="jsonpath")
        return "slice", tuple(numbers + [None] * (3 - len(numbers)))
    if "," in expr:
        indices = expr.split(",")
        if any(not re.fullmatch(r"-?\d+", part.strip()) for part in indices):
            raise JsonParseError(f"无效的索引列表: `{expr}`", kind="jsonpath")
        return "indices", [int(part.strip()) for part in indices]
    if re.fullmatch(r"-?\d+", expr):
        return "index", int(expr)
    raise JsonParseError(f"暂不支持的括号表达式: `{expr}`", kind="jsonpath")


def _descendants(node: Any, max_nodes: int = MAX_JSONPATH_RESULTS * 4) -> List[Any]:
    result: List[Any] = []
    stack = [node]
    seen: set = set()
    while stack and len(result) < max_nodes:
        current = stack.pop()
        if not isinstance(current, (dict, list)) or id(current) in seen:
            continue
        seen.add(id(current))
        children = list(current.values()) if isinstance(current, dict) else list(current)
        result.extend(children[: max_nodes - len(result)])
        stack.extend(reversed(children))
    return result


def _child_values(node: Any, name: str) -> List[Any]:
    if name == "*":
        if isinstance(node, dict):
            return list(node.values())
        if isinstance(node, list):
            return list(node)
        return []
    if isinstance(node, dict) and name in node:
        return [node[name]]
    if isinstance(node, list):
        return [item[name] for item in node if isinstance(item, dict) and name in item]
    return []


def _apply_bracket(node: Any, expr: str) -> List[Any]:
    kind, parsed = _parse_index_expression(expr)
    if kind == "child":
        return _child_values(node, parsed)
    if kind == "filter":
        return [item for item in node if _matches_filter(item, parsed)] if isinstance(node, list) else []
    if not isinstance(node, list):
        return []
    if kind == "wildcard":
        return list(node)
    if kind == "index":
        index = parsed
        if -len(node) <= index < len(node):
            return [node[index]]
        return []
    if kind == "indices":
        return [node[index] for index in parsed if -len(node) <= index < len(node)]
    if kind == "slice":
        start, end, step = parsed
        return list(node[slice(start, end, step)])
    return []


def _split_filter(expr: str) -> List[str]:
    parts: List[str] = []
    current: List[str] = []
    quote = ""
    for char in expr:
        if quote:
            current.append(char)
            if char == quote:
                quote = ""
            continue
        if char in "\"'":
            quote = char
            current.append(char)
            continue
        if char in "&|":
            parts.append("".join(current).strip())
            current = []
            continue
        current.append(char)
    parts.append("".join(current).strip())
    return [part for part in parts if part]


def _coerce_filter_value(raw: str) -> Tuple[Any, str]:
    text = raw.strip()
    quoted = _unquote(text)
    if quoted is not None:
        return quoted, "string"
    lowered = text.lower()
    if lowered == "true":
        return True, "bool"
    if lowered == "false":
        return False, "bool"
    if lowered == "null":
        return None, "null"
    if re.fullmatch(r"-?\d+", text):
        return int(text), "number"
    if re.fullmatch(r"-?\d*\.\d+", text):
        return float(text), "number"
    return text, "raw"


def _matches_filter(item: Any, expr: str) -> bool:
    if not isinstance(item, (dict, list)):
        return False
    results = [_evaluate_condition(item, condition) for condition in _split_filter(expr)]
    return all(results) if results else False


def _evaluate_condition(item: Any, condition: str) -> bool:
    match = re.match(r"^(@[^\s=<>!~]+)\s*(==|!=|<=|>=|<|>|=~)?\s*(.*)$", condition.strip())
    if not match:
        return False
    prop, operator, raw_value = match.groups()
    candidates: List[Any] = []
    try:
        tokens = _tokenize_jsonpath("$" + prop[1:])
        candidates = _evaluate_tokens([item], tokens, max_results=1000)
    except (JsonParseError, ValueError):
        return False

    if not operator:
        return bool(candidates)
    if not candidates:
        return False

    value, value_kind = _coerce_filter_value(raw_value)
    if operator == "=~":
        pattern = value.strip("/")
        flags_value = re.IGNORECASE if raw_value.strip().rstrip("/").endswith("/i") else 0
        try:
            return any(re.search(pattern, str(candidate), flags_value) for candidate in candidates)
        except re.error:
            return False

    def compare(candidate: Any) -> bool:
        if operator == "==":
            return candidate == value or (isinstance(candidate, bool) is False and isinstance(value, bool) is False and str(candidate) == str(value))
        if operator == "!=":
            return not compare_equal(candidate, value)
        if value_kind == "number" and _is_number(candidate):
            number = float(candidate)
            target = float(value)
        else:
            try:
                number, target = str(candidate), str(value)
            except TypeError:
                return False
        if operator == "<":
            return number < target
        if operator == "<=":
            return number <= target
        if operator == ">":
            return number > target
        if operator == ">=":
            return number >= target
        return False

    def compare_equal(left: Any, right: Any) -> bool:
        return left == right or (not isinstance(left, bool) and not isinstance(right, bool) and str(left) == str(right))

    return any(compare(candidate) for candidate in candidates)


def _evaluate_tokens(nodes: List[Any], tokens: Sequence[_Token], *, max_results: int) -> List[Any]:
    current = nodes
    for token in tokens:
        results: List[Any] = []
        if token.kind == "child":
            for node in current:
                results.extend(_child_values(node, token.value))
        elif token.kind == "recursive":
            for node in current:
                for descendant in _descendants(node):
                    if token.value == "*":
                        results.append(descendant)
                    elif isinstance(descendant, dict) and token.value in descendant:
                        results.append(descendant[token.value])
        elif token.kind in {"bracket", "recursive_bracket"}:
            if token.kind == "recursive_bracket":
                for node in current:
                    for descendant in _descendants(node):
                        results.extend(_apply_bracket(descendant, token.value))
            else:
                for node in current:
                    results.extend(_apply_bracket(node, token.value))
        elif token.kind == "filter":
            for node in current:
                if not isinstance(node, list):
                    continue
                results.extend(item for item in node if _matches_filter(item, token.value))
        elif token.kind == "function":
            spec = get_jsonpath_functions().get(token.value)
            if not spec:
                raise JsonParseError(f"未注册的 JSONPath 函数: `{token.value}()`", kind="jsonpath")
            for node in current:
                results.append(spec.func(node))
        if len(results) > max_results:
            raise JsonParseError(
                f"匹配结果超过 {max_results:,} 条，请缩小查询范围。", kind="limit"
            )
        current = results
    return current


def execute_jsonpath(
    json_data: Any,
    expression: str,
    *,
    max_results: int = MAX_JSONPATH_RESULTS,
) -> List[Any]:
    tokens = _tokenize_jsonpath(expression)
    return _evaluate_tokens([json_data], tokens, max_results=max_results)


def format_jsonpath_result(values: Sequence[Any]) -> str:
    """JSONPath 结果导出为合法 JSON 数组。"""
    return serialize_json(list(values), indent=2)


def build_input_signature(*parts: Any) -> str:
    payload = json.dumps(parts, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class JSONFileUtils:
    """旧版兼容接口：方法签名保持，内部委托给纯函数实现。"""

    MAX_TRAVERSAL_DEPTH = MAX_TRAVERSAL_DEPTH

    def __init__(self) -> None:
        self.comparison_stats: Dict[str, int] = {
            "differences_count": 0,
            "keys_compared": 0,
        }
        self.last_parse_result: Optional[ParseResult] = None

    @staticmethod
    def get_filename(filepath: Union[str, "object"], with_extension: bool = True) -> str:
        import os

        basename = os.path.basename(str(filepath))
        return basename if with_extension else os.path.splitext(basename)[0]

    def get_filename_advanced(
        self,
        filepath: Union[str, "object"],
        with_extension: bool = True,
        clean_special_chars: bool = False,
    ) -> str:
        filename = self.get_filename(filepath, with_extension)
        if not clean_special_chars:
            return filename
        import os

        if with_extension:
            name, ext = os.path.splitext(filename)
            return re.sub(r"[^\w\-]", "_", name) + ext
        return re.sub(r"[^\w\-]", "_", filename)

    def parse_json(self, text: str, *, strict: bool = True) -> ParseResult:
        self.last_parse_result = parse_json_text(text, strict=strict)
        return self.last_parse_result

    def parse_and_serialize(self, text: str, *, strict: bool = True, **kwargs: Any) -> str:
        return serialize_json(self.parse_json(text, strict=strict).value, **kwargs)

    def compare_json(
        self,
        obj1: Any,
        obj2: Any,
        path: str = "",
        _visited: Any = None,
        _depth: int = 0,
    ) -> List[str]:
        differences, stats = compare_json_values(
            obj1, obj2, path=path, _visited=_visited, _depth=_depth
        )
        self.comparison_stats = {
            "differences_count": stats.differences_count,
            "keys_compared": stats.keys_compared,
        }
        return differences

    def count_keys(self, obj: Any, _visited: Any = None, _depth: int = 0) -> int:
        visited = set() if _visited is None else set(_visited)
        if not isinstance(obj, (dict, list)):
            return 0
        if id(obj) in visited or _depth > self.MAX_TRAVERSAL_DEPTH:
            return 0
        visited.add(id(obj))
        if isinstance(obj, dict):
            return len(obj) + sum(
                self.count_keys(value, visited, _depth + 1) for value in obj.values()
            )
        return sum(self.count_keys(item, visited, _depth + 1) for item in obj)

    def get_comparison_stats(self) -> Dict[str, int]:
        return self.comparison_stats.copy()

    def reset_stats(self) -> None:
        self.comparison_stats = {"differences_count": 0, "keys_compared": 0}

    def analyze_json_structure(self, obj: Any, current_level: int = 0) -> Dict[str, Any]:
        result = analyze_json_structure_safe(obj)
        result["level"] = current_level
        return result

    def get_json_depth(self, obj: Any, current_depth: int = 0, _visited: Any = None) -> int:
        return current_depth + get_json_depth_safe(obj)

    def display_json_structure(self, structure: Dict[str, Any], level: int = 0) -> None:
        import streamlit as st

        indent = "  " * level
        node_type = structure.get("type", "")
        if structure.get("truncated"):
            st.text(f"{indent}⚠️ 结构已截断：{structure.get('truncation_reason', '')}")
        if node_type == "dict":
            st.text(f"{indent}📁 对象 (键数量: {structure.get('size', 0)})")
            for child in structure.get("children", []):
                st.text(f"{indent}  🔑 {child.get('key', '')}:")
                self.display_json_structure(child, level + 1)
        elif node_type == "list":
            st.text(f"{indent}📋 数组 (元素数量: {structure.get('size', 0)})")
            for child in structure.get("children", []):
                st.text(f"{indent}  📍 [{child.get('index', 0)}]:")
                self.display_json_structure(child, level + 1)
        else:
            st.text(f"{indent}📄 {node_type}: {structure.get('value', '')}")

    def execute_jsonpath(self, json_data: Any, expression: str) -> List[Any]:
        try:
            return execute_jsonpath(json_data, expression)
        except JsonParseError as exc:
            raise Exception(f"JSONPath执行错误: {exc.message}") from exc
