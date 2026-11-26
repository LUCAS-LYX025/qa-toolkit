"""外部 MCP Server 注册中心（qa-toolkit 作为 MCP 客户端消费外部能力）。

设计目标（不绑定任何单一 MCP 提供商）：
- 一个外部 MCP Server 就是注册表里的一项，stdio（本地进程）与 Streamable HTTP
  （远程服务）统一为 ``McpServerSpec``；换服务商只改配置，不改工具代码；
- 凭据一律只登记**环境变量名**（``env_refs``），明文永远不进注册表、不进产物；
- 命令参数支持 ``${ENV_NAME}`` 占位符，由客户端在启动时从环境展开；
- 工具白名单默认收窄到已验证的工具，未知工具需显式登记；
- 外部返回内容统一按 ``untrusted`` 处理，写操作默认禁止，需显式开启。

与仓库既有 ``*_registry.py`` 保持一致的硬惯例：
- Spec 一律 ``@dataclass(frozen=True)``；
- ``register_mcp_server(..., replace=False)``：重复 key 抛 ``ValueError``；
- ``get_mcp_servers()`` 返回副本，绝不暴露内部可变容器；
- 写操作用 ``threading.RLock`` 保护；
- ``reset_mcp_registry()`` 清空重建默认项，保证测试隔离。
"""
from __future__ import annotations

import copy
import re
import threading
from dataclasses import dataclass, replace as _dc_replace
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

_LOCK = threading.RLock()

_ENV_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_ENV_PLACEHOLDER_RE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")
_SECRET_QUERY_KEYS = frozenset({"token", "access_token", "api_key", "apikey", "password", "secret", "key"})


@dataclass(frozen=True)
class McpLimits:
    """外部调用的硬上限与安全默认值。"""
    max_response_chars: int = 200_000
    max_tools: int = 200
    default_timeout_seconds: float = 30.0
    min_timeout_seconds: float = 1.0
    max_timeout_seconds: float = 120.0
    max_command_args: int = 64
    max_arg_chars: int = 4000
    allow_private_targets: bool = False
    allow_untrusted_write: bool = False


_LIMITS = McpLimits()


def configure_mcp_limits(**kwargs: Any) -> McpLimits:
    global _LIMITS
    allowed = set(McpLimits.__dataclass_fields__)
    unknown = set(kwargs) - allowed
    if unknown:
        raise ValueError(f"未知 MCP 上限字段：{sorted(unknown)}")
    with _LOCK:
        _LIMITS = _dc_replace(_LIMITS, **kwargs)
        return _LIMITS


def get_mcp_limits() -> McpLimits:
    with _LOCK:
        return _LIMITS


@dataclass(frozen=True)
class McpServerSpec:
    """一个外部 MCP Server 的注册项。

    ``env_refs`` 只存环境变量名；``args`` 中的 ``${NAME}`` 由客户端展开。
    ``tool_allowlist`` 为空表示不在注册层限制（仍受客户端策略约束）。
    """
    key: str
    label: str
    description: str
    transport: str                       # stdio / http
    command: str = ""
    args: Tuple[str, ...] = ()
    url: str = ""
    env_refs: Tuple[str, ...] = ()
    tool_allowlist: Tuple[str, ...] = ()
    trust: str = "untrusted"             # trusted / untrusted
    timeout_seconds: float = 30.0
    enabled: bool = True
    source: str = "builtin"              # builtin / codex / cursor / manual

    def __post_init__(self) -> None:
        if self.transport not in ("stdio", "http"):
            raise ValueError(f"MCP 传输方式必须是 stdio 或 http，收到 {self.transport!r}")
        if self.transport == "stdio" and not self.command.strip():
            raise ValueError(f"stdio 型 MCP {self.key!r} 缺少 command")
        if self.transport == "http" and not self.url.strip():
            raise ValueError(f"http 型 MCP {self.key!r} 缺少 url")
        if self.trust not in ("trusted", "untrusted"):
            raise ValueError(f"未知信任级别 {self.trust!r}")
        for name in self.env_refs:
            if not _ENV_NAME_RE.match(name):
                raise ValueError(f"非法环境变量名 {name!r}")
        for arg in self.args:
            for placeholder in _ENV_PLACEHOLDER_RE.findall(arg):
                if placeholder not in self.env_refs:
                    raise ValueError(f"参数引用了未登记的凭据 {placeholder!r}")
        limits = get_mcp_limits()
        if len(self.args) > limits.max_command_args:
            raise ValueError(f"MCP {self.key!r} 参数过多（上限 {limits.max_command_args}）")
        if any(len(arg) > limits.max_arg_chars for arg in self.args):
            raise ValueError(f"MCP {self.key!r} 单个参数过长")


def _default_servers() -> Dict[str, McpServerSpec]:
    """默认登记用户机器上真实存在的 MCP Server；不含任何凭据明文。"""
    specs = (
        McpServerSpec(
            key="yunxiao",
            label="云效",
            description="阿里云 Devops MCP（项目管理工具集）：需求、缺陷、任务、评论与状态流转。",
            transport="stdio",
            command="npx",
            args=("-y", "alibabacloud-devops-mcp-server", "--toolsets=project-management"),
            env_refs=("YUNXIAO_ACCESS_TOKEN", "YUNXIAO_API_BASE_URL"),
            tool_allowlist=(
                "get_current_organization_info", "search_workitems", "get_work_item",
                "list_work_item_comments", "list_workitem_activities", "update_work_item",
            ),
            source="codex",
        ),
        McpServerSpec(
            key="lanhu",
            label="蓝湖",
            description="蓝湖设计稿 MCP：读取设计标注与交互说明；内网服务，需显式允许私网地址。",
            transport="http",
            url="http://10.0.6.111:8000/mcp?role=测试&name=Lucas",
            env_refs=(),
            source="codex",
        ),
        McpServerSpec(
            key="zentao",
            label="禅道",
            description="禅道 11 MCP：读取需求、任务与缺陷；连接信息走环境变量。",
            transport="stdio",
            command="/usr/local/bin/mcp-zentao-11-3",
            env_refs=("ZENTAO_URL", "ZENTAO_USERNAME", "ZENTAO_PASSWORD"),
            source="cursor",
        ),
        McpServerSpec(
            key="mastergo",
            label="MasterGo",
            description="MasterGo 设计稿 MCP：与蓝湖同类，用于补充 UI 校验点。",
            transport="stdio",
            command="npx",
            args=("-y", "@mastergo/magic-mcp", "--token=${MASTERGO_TOKEN}", "--url=https://mastergo.com"),
            env_refs=("MASTERGO_TOKEN",),
            source="codex",
        ),
        McpServerSpec(
            key="adb_mysql",
            label="数据仓库（只读）",
            description="只读 MySQL MCP：用于缺陷证据复核；默认只读，禁止写操作。",
            transport="stdio",
            command="npx",
            args=("-y", "@imrieul/mysql-mcp-server", "--readonly"),
            env_refs=(
                "MYSQL_HOST", "MYSQL_PORT", "MYSQL_USER", "MYSQL_PASSWORD",
                "MYSQL_DATABASE", "MYSQL_MAX_ROWS", "MYSQL_QUERY_TIMEOUT",
            ),
            source="codex",
        ),
    )
    return {spec.key: spec for spec in specs}


_SERVERS: Dict[str, McpServerSpec] = _default_servers()


def register_mcp_server(spec: McpServerSpec, *, replace: bool = False) -> McpServerSpec:
    with _LOCK:
        if spec.key in _SERVERS and not replace:
            raise ValueError(f"MCP Server {spec.key!r} 已注册；如需覆盖请传 replace=True")
        _SERVERS[spec.key] = spec
        return spec


def get_mcp_server(key: str) -> Optional[McpServerSpec]:
    with _LOCK:
        return _SERVERS.get(key)


def get_mcp_servers() -> Dict[str, McpServerSpec]:
    with _LOCK:
        return copy.deepcopy(_SERVERS)


def get_mcp_server_keys() -> List[str]:
    with _LOCK:
        return list(_SERVERS)


def unregister_mcp_server(key: str) -> bool:
    with _LOCK:
        return _SERVERS.pop(key, None) is not None


def reset_mcp_registry() -> None:
    global _LIMITS
    with _LOCK:
        _SERVERS.clear()
        _SERVERS.update(_default_servers())
        _LIMITS = McpLimits()


def expand_env_args(spec: McpServerSpec, environ: Optional[Dict[str, str]] = None) -> Tuple[List[str], List[str]]:
    """展开 ``${ENV}`` 占位符；返回 ``(参数, 缺失的环境变量)``，不回显任何值。"""
    env = dict(environ or {})
    missing: List[str] = []
    expanded: List[str] = []
    for arg in spec.args:
        def _sub(match: Any) -> str:
            name = match.group(1)
            value = env.get(name)
            if value is None or value == "":
                if name not in missing:
                    missing.append(name)
                return ""
            return str(value)
        expanded.append(_ENV_PLACEHOLDER_RE.sub(_sub, arg))
    return expanded, missing


def _redact_url(url: str) -> str:
    try:
        parts = urlsplit(url)
        if not parts.query:
            return url
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        safe = [
            (k, "******" if k.lower() in _SECRET_QUERY_KEYS else v)
            for k, v in pairs
        ]
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(safe), parts.fragment))
    except Exception:
        return "<invalid-url>"


def redact_mcp_server(spec: McpServerSpec) -> Dict[str, Any]:
    """页面/日志专用的脱敏视图：只显示环境变量名，不显示任何值。"""
    return {
        "key": spec.key,
        "label": spec.label,
        "description": spec.description,
        "transport": spec.transport,
        "command": spec.command,
        "args": [_ENV_PLACEHOLDER_RE.sub(lambda m: f"<env:{m.group(1)}>", a) for a in spec.args],
        "url": _redact_url(spec.url) if spec.url else "",
        "env_refs": list(spec.env_refs),
        "tool_allowlist": list(spec.tool_allowlist),
        "trust": spec.trust,
        "timeout_seconds": spec.timeout_seconds,
        "enabled": spec.enabled,
        "source": spec.source,
    }


def get_mcp_registry_summary() -> Dict[str, Any]:
    with _LOCK:
        specs = list(_SERVERS.values())
    return {
        "总数": len(specs),
        "按传输": {
            "stdio": sum(1 for s in specs if s.transport == "stdio"),
            "http": sum(1 for s in specs if s.transport == "http"),
        },
        "已接入": sorted(s.key for s in specs if s.enabled),
        "仅登记": sorted(s.key for s in specs if not s.enabled),
        "需要凭据": sorted(s.key for s in specs if s.env_refs),
        "来源": sorted({s.source for s in specs}),
        "默认拒绝私网": not get_mcp_limits().allow_private_targets,
    }
