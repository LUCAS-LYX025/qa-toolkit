"""外部 MCP 客户端：连接发现、受控调用、统一返回信封与可审计 trace。

安全策略（默认收紧）：
- HTTP 目标先复用仓库既有 SSRF 校验；私网地址需显式开启；
- 工具调用受注册项的 ``tool_allowlist`` 约束；
- 调用参数与 trace 一律脱敏，不回显任何凭据值；
- 外部返回内容只当数据，不做指令解析；超长结果截断并留告警。
"""
from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from qa_toolkit.core.api_security_registry import validate_target_url
from qa_toolkit.core.mcp_client_registry import (
    McpServerSpec,
    expand_env_args,
    get_mcp_limits,
)
from qa_toolkit.integrations.mcp.transport import (
    HttpTransport,
    McpTransport,
    StdioTransport,
    TransportError,
)

_PROTOCOL_VERSION = "2024-11-05"
_SENSITIVE_KEY_PARTS = ("token", "password", "secret", "api_key", "apikey", "credential")
_SECRET_IN_STRING_RE = re.compile(
    r"((?:token|password|secret|api[_-]?key|credential)\s*[=:]\s*)([^\s;&,]+)", re.I)
_BEARER_RE = re.compile(r"(Bearer\s+)[A-Za-z0-9._~-]{8,}", re.I)
_WRITE_HINT_RE = re.compile(r"(update|create|delete|remove|post|write|set_status)", re.I)


@dataclass
class McpCallResult:
    ok: bool
    data: Any = None
    warnings: List[str] = field(default_factory=list)
    trace: Dict[str, Any] = field(default_factory=dict)
    error: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "data": self.data,
            "warnings": list(self.warnings),
            "trace": dict(self.trace),
            "error": self.error,
        }


def redact_payload(value: Any) -> Any:
    """递归脱敏：凭据类字段名与字符串里的凭据片段都替换为掩码。"""
    if isinstance(value, dict):
        result: Dict[str, Any] = {}
        for key, item in value.items():
            text_key = str(key).lower()
            if any(part in text_key for part in _SENSITIVE_KEY_PARTS):
                result[key] = "******"
            else:
                result[key] = redact_payload(item)
        return result
    if isinstance(value, (list, tuple)):
        return [redact_payload(item) for item in value]
    if isinstance(value, str):
        redacted = _SECRET_IN_STRING_RE.sub(r"\1******", value)
        return _BEARER_RE.sub(r"\1******", redacted)
    return value


def _is_write_tool(source: str, tool_name: str) -> bool:
    """写操作判定：先看语义映射，未映射时按工具名保守识别。"""
    try:
        from qa_toolkit.integrations.mcp.capabilities import get_external_capabilities
        for spec in get_external_capabilities(source).values():
            if spec.external_tool == tool_name:
                return spec.side_effect == "write"
    except Exception:
        pass
    return bool(_WRITE_HINT_RE.search(tool_name or ""))


def _extract_content(payload: Dict[str, Any], max_chars: int) -> Tuple[Any, List[str]]:
    warnings: List[str] = []
    content = payload.get("content")
    if content is None:
        return payload.get("structuredContent"), warnings
    if not isinstance(content, list):
        return content, warnings
    texts: List[str] = []
    for item in content:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "text" and isinstance(item.get("text"), str):
            texts.append(item["text"])
    joined = "\n".join(texts)
    if len(joined) > max_chars:
        warnings.append(f"外部 MCP 返回内容超过 {max_chars} 字符，已截断")
        joined = joined[:max_chars]
    try:
        return json.loads(joined), warnings
    except (ValueError, TypeError):
        return joined, warnings


class McpClient:
    """一个外部 MCP Server 的会话；支持注入 transport 便于契约测试。"""

    def __init__(
        self,
        spec: McpServerSpec,
        *,
        transport: Optional[McpTransport] = None,
        environ: Optional[Dict[str, str]] = None,
        allow_write: bool = False,
    ) -> None:
        self.spec = spec
        self.allow_write = bool(allow_write)
        self._injected = transport
        self._environ = dict(environ if environ is not None else os.environ)
        self._transport: Optional[McpTransport] = None
        self._request_id = 0
        self._connected = False
        self.server_info: Dict[str, Any] = {}

    def _build_transport(self) -> Tuple[McpTransport, List[str]]:
        warnings: List[str] = []
        if self._injected is not None:
            return self._injected, warnings
        limits = get_mcp_limits()
        timeout = min(max(self.spec.timeout_seconds, limits.min_timeout_seconds), limits.max_timeout_seconds)
        if self.spec.transport == "stdio":
            args, missing = expand_env_args(self.spec, self._environ)
            for name in missing:
                warnings.append(f"环境变量 {name} 未设置，相关参数已留空")
            env = dict(self._environ)
            return StdioTransport(self.spec.command, args, env=env, timeout_seconds=timeout), warnings
        ok, reason = validate_target_url(self.spec.url, allow_private=limits.allow_private_targets)
        if not ok:
            raise TransportError(f"MCP 目标地址被拒绝：{reason}")
        return HttpTransport(self.spec.url, timeout_seconds=timeout), warnings

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if self._transport is None:
            raise TransportError("MCP 会话未建立，请先调用 connect()")
        request: Dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            request["params"] = params
        response = self._transport.send(request)
        if "error" in response:
            err = response.get("error") or {}
            raise TransportError(f"MCP {method} 失败：{err.get('message', '未知错误')}")
        return response

    def connect(self) -> List[str]:
        """initialize + initialized；返回启动期告警（不含凭据）。"""
        if self._connected:
            return []
        transport, warnings = self._build_transport()
        self._transport = transport
        response = self._request("initialize", {
            "protocolVersion": _PROTOCOL_VERSION,
            "capabilities": {},
            "clientInfo": {"name": "qa-toolkit", "version": "1.0"},
        })
        result = response.get("result") or {}
        self.server_info = {
            "protocolVersion": result.get("protocolVersion", ""),
            "serverInfo": redact_payload(result.get("serverInfo") or {}),
        }
        if hasattr(transport, "notify"):
            transport.notify({
                "jsonrpc": "2.0",
                "method": "notifications/initialized",
                "params": {},
            })
        self._connected = True
        return warnings

    def list_tools(self) -> List[Dict[str, Any]]:
        self.connect()
        response = self._request("tools/list", {})
        tools = (response.get("result") or {}).get("tools") or []
        if not isinstance(tools, list):
            return []
        allowed = set(self.spec.tool_allowlist)
        limits = get_mcp_limits()
        visible = [tool for tool in tools if isinstance(tool, dict) and (not allowed or tool.get("name") in allowed)]
        return visible[:limits.max_tools]

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> McpCallResult:
        started = time.monotonic()
        warnings: List[str] = []
        trace: Dict[str, Any] = {
            "server": self.spec.key,
            "tool": name,
            "arguments": redact_payload(arguments or {}),
            "write_allowed": self.allow_write,
        }
        try:
            if self.spec.tool_allowlist and name not in self.spec.tool_allowlist:
                raise TransportError(f"工具 {name!r} 不在 {self.spec.key} 的白名单内")
            if _is_write_tool(self.spec.key, name) and not self.allow_write:
                raise TransportError(
                    f"工具 {name!r} 是写操作，默认禁止；只有用户明确确认后才能调用"
                )
            warnings.extend(self.connect())
            response = self._request("tools/call", {"name": name, "arguments": arguments or {}})
            result = response.get("result") or {}
            data, content_warnings = _extract_content(result, get_mcp_limits().max_response_chars)
            warnings.extend(content_warnings)
            is_error = bool(result.get("isError"))
            trace.update({
                "ok": not is_error,
                "duration_ms": int((time.monotonic() - started) * 1000),
                "result_chars": len(json.dumps(data, ensure_ascii=False, default=str)),
            })
            if is_error:
                return McpCallResult(
                    ok=False,
                    data=data,
                    warnings=warnings,
                    trace=trace,
                    error=str(data)[:300],
                )
            return McpCallResult(ok=True, data=data, warnings=warnings, trace=trace)
        except TransportError as exc:
            trace.update({"ok": False, "duration_ms": int((time.monotonic() - started) * 1000)})
            return McpCallResult(ok=False, warnings=warnings, trace=trace, error=str(exc))
        except Exception as exc:  # 外部 server 行为不可控，统一收敛为错误信封
            trace.update({"ok": False, "duration_ms": int((time.monotonic() - started) * 1000)})
            return McpCallResult(
                ok=False, warnings=warnings, trace=trace,
                error=f"调用外部 MCP 时发生未预期错误：{type(exc).__name__}",
            )

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None
        self._connected = False
