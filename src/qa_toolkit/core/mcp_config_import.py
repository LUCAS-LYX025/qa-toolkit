"""从已有 MCP 客户端配置只读导入 server 定义（不复制任何凭据明文）。

支持两种真实存在的配置：
- Codex ``~/.codex/config.toml`` 的 ``[mcp_servers.*]`` 段；
- Cursor / 通用编辑器 ``mcp.json`` 的 ``mcpServers`` 节点。

导入原则（安全优先）：
1. 只读，不修改原文件；
2. 只取 command / args / url / 环境变量**名**，绝不把值带出来；
3. 命令参数里形如 ``--token=明文`` 的一律替换为 ``--token=${ENV_NAME}``；
4. 文件大小超限直接拒绝，避免误读同目录下的大 SQLite 文件。
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from qa_toolkit.core.mcp_client_registry import McpServerSpec, get_mcp_server, register_mcp_server

_MAX_CONFIG_BYTES = 1_000_000
_SECTION_RE = re.compile(r"^\[([^\]]+)\]")
_ARRAY_ITEM_RE = re.compile(r'"([^"]*)"|\'([^\']*)\'')
_SECRET_ARG_RE = re.compile(r"^(--)?(token|api[-_]?key|password|secret|access[-_]?token)(=|:)(.+)$", re.I)
_ENV_HINT = {
    "token": "TOKEN", "api_key": "API_KEY", "apikey": "API_KEY",
    "password": "PASSWORD", "secret": "SECRET", "access_token": "ACCESS_TOKEN",
}

_LABELS = {
    "yunxiao": "云效",
    "lanhu": "蓝湖",
    "zentao": "禅道",
    "mastergo": "MasterGo",
    "adb_mysql": "数据仓库（只读）",
}

# 同一服务在不同客户端里的名字不同，导入时归并，避免页面出现重复数据源。
_ALIASES = {
    "mastergo-magic-mcp": "mastergo",
    "zentao-11": "zentao",
    "adb-mysql-mcp-server": "adb_mysql",
    "adb-mysql": "adb_mysql",
}

# 默认只导入与测试工作直接相关的业务数据源；浏览器/Excel 等工具按需手动登记。
_BUSINESS_KEYS = frozenset({"yunxiao", "lanhu", "zentao", "mastergo", "adb_mysql"})


def _unquote(raw: str) -> str:
    value = raw.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def _parse_array(raw: str) -> List[str]:
    value = raw.strip()
    if value.startswith("["):
        items = []
        for double, single in _ARRAY_ITEM_RE.findall(value):
            items.append(double if double else single)
        return items
    return []


def _sanitize_args(args: List[str], env_refs: List[str], key: str) -> List[str]:
    """把参数里的明文凭据换成 ``${ENV}`` 引用；返回清洗后的参数。"""
    sanitized: List[str] = []
    for arg in args:
        match = _SECRET_ARG_RE.match(arg)
        if not match:
            sanitized.append(arg)
            continue
        prefix, name, separator, _value = match.groups()
        normalized = re.sub(r"[-_]", "_", name).lower()
        env_name = _ENV_HINT.get(normalized)
        if env_name is None:
            for candidate in env_refs:
                if "TOKEN" in candidate.upper():
                    env_name = candidate
                    break
        if env_name is None:
            env_name = f"{re.sub(r'[^A-Za-z0-9_]', '_', key).upper()}_{_ENV_HINT.get(normalized, 'SECRET')}"
        if env_name not in env_refs:
            env_refs.append(env_name)
        sanitized.append(f"{prefix or '--'}{name}{separator}${{{env_name}}}")
    return sanitized


def _make_spec(key: str, data: Dict[str, Any], source: str) -> Optional[McpServerSpec]:
    key = _ALIASES.get(key, key)
    command = str(data.get("command") or "").strip()
    url = str(data.get("url") or "").strip()
    if not command and not url:
        return None
    existing = get_mcp_server(key)
    if existing is not None:
        # 已登记的数据源保留更完整的默认定义（含工具白名单与语义化凭据名），
        # 只把来源标记为「多客户端已配置」，绝不新增一个同义注册项。
        from dataclasses import replace as _dc_replace
        return _dc_replace(existing, source=f"{existing.source}+{source}")
    transport = "http" if url and not command else "stdio"
    env_refs = [str(name) for name in (data.get("env_keys") or [])]
    args = _sanitize_args([str(a) for a in (data.get("args") or [])], env_refs, key)
    return McpServerSpec(
        key=key,
        label=_LABELS.get(key, key),
        description=f"从 {source} 配置导入的 MCP Server；凭据仅以环境变量名登记。",
        transport=transport,
        command=command,
        args=tuple(args),
        url=url,
        env_refs=tuple(env_refs),
        tool_allowlist=(),
        trust="untrusted",
        timeout_seconds=30.0,
        source=source,
    )


def parse_codex_config(text: str) -> List[McpServerSpec]:
    """解析 Codex TOML 中的 mcp_servers 段；忽略环境变量值与工具审批配置。"""
    servers: Dict[str, Dict[str, Any]] = {}
    current: Optional[Tuple[str, str]] = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        section = _SECTION_RE.match(line)
        if section:
            parts = [p.strip().strip('"') for p in section.group(1).split(".")]
            if len(parts) >= 2 and parts[0] == "mcp_servers":
                key = parts[1]
                sub = ".".join(parts[2:])
                current = (key, sub)
                servers.setdefault(key, {"command": "", "args": [], "url": "", "env_keys": []})
            else:
                current = None
            continue
        if current is None or "=" not in line:
            continue
        key, sub = current
        name, value = line.split("=", 1)
        name = name.strip().strip('"')
        if sub == "":
            if name == "command":
                servers[key]["command"] = _unquote(value)
            elif name == "args":
                servers[key]["args"] = _parse_array(value)
            elif name == "url":
                servers[key]["url"] = _unquote(value)
        elif sub == "env":
            if name not in servers[key]["env_keys"]:
                servers[key]["env_keys"].append(name)
    result: List[McpServerSpec] = []
    for key, data in servers.items():
        spec = _make_spec(key, data, "codex")
        if spec is not None:
            result.append(spec)
    return result


def parse_cursor_config(text: str) -> List[McpServerSpec]:
    """解析 mcp.json 的 mcpServers 节点；同样不导出凭据值。"""
    try:
        payload = json.loads(text)
    except (ValueError, TypeError):
        return []
    servers = payload.get("mcpServers") if isinstance(payload, dict) else None
    if not isinstance(servers, dict):
        return []
    result: List[McpServerSpec] = []
    for key, raw in servers.items():
        if not isinstance(raw, dict):
            continue
        data = {
            "command": raw.get("command", ""),
            "args": raw.get("args", []),
            "url": raw.get("url", ""),
            "env_keys": list((raw.get("env") or {}).keys()),
        }
        spec = _make_spec(str(key), data, "cursor")
        if spec is not None:
            result.append(spec)
    return result


def _read_text(path: str) -> str:
    target = Path(path).expanduser()
    if not target.is_file():
        return ""
    if target.stat().st_size > _MAX_CONFIG_BYTES:
        return ""
    return target.read_text(encoding="utf-8", errors="ignore")


def import_mcp_configs(
    paths: Tuple[str, ...] = ("~/.codex/config.toml", "~/.cursor/mcp.json"),
    *,
    register: bool = False,
    replace: bool = False,
    business_only: bool = True,
    allowed_keys: Optional[frozenset] = None,
) -> Tuple[List[McpServerSpec], List[str]]:
    """只读导入多个客户端配置；返回 ``(导入项, 告警)``。

    默认只导入与测试工作直接相关的业务数据源，避免浏览器/Excel 等工具
    淹没下拉框；需要其它服务时传 ``business_only=False`` 或 ``allowed_keys``。
    """
    specs: List[McpServerSpec] = []
    warnings: List[str] = []
    seen: set = set()
    accepted = frozenset(allowed_keys) if allowed_keys is not None else _BUSINESS_KEYS
    for path in paths:
        text = _read_text(path)
        if not text:
            warnings.append(f"未读取到配置或文件过大：{path}")
            continue
        if path.endswith(".json"):
            parsed = parse_cursor_config(text)
        else:
            parsed = parse_codex_config(text)
        for spec in parsed:
            if spec.key in seen:
                continue
            if business_only and spec.key not in accepted:
                continue
            seen.add(spec.key)
            specs.append(spec)
            if register:
                try:
                    register_mcp_server(spec, replace=replace)
                except ValueError as exc:
                    warnings.append(f"{spec.key} 未覆盖注册：{exc}")
    return specs, warnings
