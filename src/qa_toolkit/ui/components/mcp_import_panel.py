"""外部 MCP 导入面板：把外部系统的需求/设计标注清洗后填入本地输入框。

这个组件只负责「选择外部能力 → 受控调用 → 结构化预览 → 回填」，不碰任何
工具自身的生成逻辑；``target_key`` 参数化，后续接口自动化、日志分析都能复用。
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from qa_toolkit.core import mcp_client_registry as reg
from qa_toolkit.integrations.mcp import capabilities as caps
from qa_toolkit.integrations.mcp.client import McpClient
from qa_toolkit.integrations.mcp.transport import TransportError
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
    render_warning_feedback,
)

_PREFIX = "mcp_import_"


def _state(key: str, default: Any = None) -> Any:
    return st.session_state.get(_PREFIX + key, default)


def _set(key: str, value: Any) -> None:
    st.session_state[_PREFIX + key] = value


def _clear_tool_cache() -> None:
    """切换数据源时丢弃上一家的工具与候选，避免跨源误调用。"""
    for key in ("tools", "candidate", "arguments", "tool"):
        st.session_state.pop(_PREFIX + key, None)


def _capability_for(source: str, tool_name: str) -> Optional[Any]:
    for spec in caps.get_external_capabilities(source).values():
        if spec.external_tool == tool_name:
            return spec
    inferred = caps.infer_capabilities([{"name": tool_name}], source)
    return inferred[0] if inferred else None


def _candidate_rows(payload: Any, limit: int = 10) -> Tuple[List[Dict[str, str]], int, bool]:
    if isinstance(payload, dict):
        for key in ("workitems", "items", "data", "result", "list"):
            if isinstance(payload.get(key), list):
                payload = payload[key]
                break
    if not isinstance(payload, list):
        return [], 0, False
    rows: List[Dict[str, str]] = []
    for item in payload[:limit]:
        if not isinstance(item, dict):
            continue
        rows.append({
            "id": str(item.get("id") or item.get("workItemId") or ""),
            "subject": str(item.get("subject") or item.get("title") or item.get("name") or ""),
            "status": str(item.get("statusLabel") or item.get("status") or ""),
        })
    return rows, len(payload), len(payload) > limit


def _call(spec: Any, tool_name: str, arguments: Dict[str, Any], *, allow_write: bool = False) -> Any:
    client = McpClient(spec, allow_write=allow_write)
    try:
        return client.call_tool(tool_name, arguments)
    finally:
        client.close()


def render_mcp_import_panel(target_key: str = "tcg_requirement_text") -> None:
    servers = {key: spec for key, spec in reg.get_mcp_servers().items() if spec.enabled}
    if not servers:
        render_info_feedback("当前没有已启用的外部 MCP 数据源。")
        return

    keys = list(servers)
    selected = st.selectbox(
        "外部数据源",
        keys,
        key=_PREFIX + "server",
        on_change=_clear_tool_cache,
        format_func=lambda key: f"{servers[key].label}（{servers[key].transport}）",
    )
    spec = servers[selected]
    missing_env = [name for name in spec.env_refs if not os.environ.get(name)]
    if missing_env:
        render_warning_feedback(
            "以下环境变量未设置：" + "、".join(missing_env) + "；只从环境变量读取，不会写入导出文件。"
        )
    view = reg.redact_mcp_server(spec)
    credential_text = "、".join(view["env_refs"]) or "无需凭据"
    st.caption(
        f"来源：{view['source']} · 传输：{view['transport']} · "
        f"凭据引用：{credential_text} · 工具白名单：{len(view['tool_allowlist'])} 项"
    )
    if view["env_refs"]:
        st.caption("凭据只从环境变量读取，不会写入需求文本或导出文件。")

    mode = st.radio(
        "导入方式",
        ["按语义搜索需求", "调用指定工具"],
        horizontal=True,
        key=_PREFIX + "mode",
    )

    if st.button("发现可用工具", key=_PREFIX + "discover"):
        client = McpClient(spec)
        try:
            tools = client.list_tools()
            _set("tools", tools)
            render_success_feedback(f"发现 {len(tools)} 个可用工具。")
        except TransportError as exc:
            message = str(exc)
            if "私网" in message or "内网" in message or "private" in message.lower():
                render_warning_feedback(f"{message}。如需接入内网 MCP，请在运行配置中显式允许私网地址。")
            else:
                render_error_feedback(message)
        except Exception as exc:
            render_error_feedback(f"连接外部 MCP 失败：{type(exc).__name__}")
        finally:
            client.close()

    tools: List[Dict[str, Any]] = _state("tools", []) or []
    if not tools:
        render_info_feedback("点击「发现可用工具」查看该数据源能读什么。")
        return

    tool_names = [str(tool.get("name") or "") for tool in tools if tool.get("name")]
    if mode == "按语义搜索需求":
        _render_search_mode(spec, selected, tool_names, target_key)
    else:
        _render_generic_mode(spec, selected, tool_names, target_key)


def _render_search_mode(spec: Any, source: str, tool_names: List[str], target_key: str) -> None:
    search_tool = next((name for name in tool_names if name in ("search_workitems", "search_work_items")), None)
    if not search_tool:
        render_info_feedback("该数据源未提供需求搜索工具，请切换到「调用指定工具」。")
        return
    keyword = st.text_input("需求关键词 / 编号", key=_PREFIX + "keyword", placeholder="如：马甲号不显示报价，或 ZSSJYF-2849")
    org_id = st.text_input("组织 ID（可选）", key=_PREFIX + "org")
    space_id = st.text_input("项目空间 ID（可选）", key=_PREFIX + "space")
    if not st.button("搜索需求", key=_PREFIX + "search"):
        return
    args, warnings = caps.build_search_arguments(keyword, organization_id=org_id, space_id=space_id)
    for warning in warnings:
        render_warning_feedback(warning)
    result = _call(spec, search_tool, args)
    if not result.ok:
        render_error_feedback(result.error or "外部 MCP 调用失败")
        return
    rows, total, truncated = _candidate_rows(result.data)
    if truncated:
        st.caption(f"共找到 {total} 条候选，仅显示前 {len(rows)} 条；补充更精确的产品名词可缩小范围。")
    if not rows:
        render_info_feedback("未命中需求，换个更短的产品名词试试。")
        return
    labels = [f"{row['id']} · {row['subject']}" for row in rows]
    chosen = st.radio("候选需求", labels, key=_PREFIX + "candidate")
    index = labels.index(chosen)
    selected_id = rows[index]["id"]
    st.caption(f"状态：{rows[index]['status'] or '未返回'}")
    if not st.button("读取需求详情并填入", key=_PREFIX + "fetch_detail"):
        return
    detail_tool = next((name for name in tool_names if name in ("get_work_item", "get_workitem")), None)
    if detail_tool and selected_id:
        payload = _call(spec, detail_tool, {"workItemId": selected_id}).data
    else:
        payload = rows[index]
    _fill_target(payload, source, "requirement_detail", target_key)


def _render_generic_mode(spec: Any, source: str, tool_names: List[str], target_key: str) -> None:
    tool_name = st.selectbox("工具", tool_names, key=_PREFIX + "tool")
    capability = _capability_for(source, tool_name)
    slot = capability.semantic_slot if capability else "requirement_text"
    side_effect = capability.side_effect if capability else "read"
    requires_confirmation = bool(capability and capability.requires_confirmation)
    st.caption(f"语义槽位：{slot} · 操作类型：{side_effect}")
    if side_effect == "write":
        render_warning_feedback("这是写操作。默认不执行，请先确认目标系统和数据。")
    confirmed = st.checkbox("我已确认要调用该写操作", key=_PREFIX + "confirm") if requires_confirmation else False
    if requires_confirmation and not confirmed:
        return
    raw = st.text_area("调用参数（JSON 对象）", value="{}", height=90, key=_PREFIX + "arguments")
    if not st.button("调用并预览", key=_PREFIX + "call"):
        return
    try:
        arguments = json.loads(raw or "{}")
        if not isinstance(arguments, dict):
            raise ValueError("参数必须是 JSON 对象")
    except ValueError as exc:
        render_error_feedback(f"参数不是合法 JSON：{exc}")
        return
    result = _call(spec, tool_name, arguments, allow_write=confirmed)
    if not result.ok:
        render_error_feedback(result.error or "外部 MCP 调用失败")
        return
    _fill_target(result.data, source, slot, target_key)


def _fill_target(payload: Any, source: str, slot: str, target_key: str) -> None:
    text, warnings = caps.extract_semantic_text(payload, semantic_slot=slot)
    for warning in warnings:
        render_warning_feedback(warning)
    if not text:
        render_info_feedback("外部返回里没有可读文本，未覆盖本地输入。")
        return
    st.text_area("导入预览（外部原文，仅作数据参考）", value=text[:4000], height=180, disabled=True)
    st.caption("外部内容不会作为指令执行；若含可疑指令，上方已给出告警。")
    if st.button("填入需求原文", key=_PREFIX + "fill"):
        current = target_key
        existing = st.session_state.get(current, "") or ""
        st.session_state[current] = f"{existing}\n\n{text}".strip() if existing.strip() else text
        render_success_feedback("已填入需求原文，可继续补充业务规则与验收标准。")
