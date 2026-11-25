from __future__ import annotations

import hashlib
import ipaddress
import json
from datetime import datetime
from typing import Any, List

import pandas as pd
import streamlit as st

from qa_toolkit.core.ip_lookup_registry import (
    get_asset_actions,
    get_conversion_types,
    get_geo_providers,
    get_ip_lookup_limits,
    get_public_ip_services,
)
from qa_toolkit.core.task_runner import get_session_task_runner
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.ip_lookup import IPQueryTool
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button, secondary_action_button
from qa_toolkit.ui.components.task_run_panel import render_task_run_panel
from qa_toolkit.ui.components.status_feedback import render_error_feedback, render_info_feedback, render_warning_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_page_hero, render_tool_tips


DEFAULT_STATE = {
    "ip_lookup_single_input": "",
    "ip_lookup_single_input_pending": None,
    "ip_lookup_single_result": None,
    "ip_lookup_single_result_signature": "",
    "ip_lookup_batch_text": "",
    "ip_lookup_batch_result": None,
    "ip_lookup_batch_result_signature": "",
    "ip_lookup_asset_input": "",
    "ip_lookup_asset_result": None,
    "ip_lookup_asset_label": "",
    "ip_lookup_asset_action": "",
    "ip_lookup_asset_result_signature": "",
}


def _signature(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _csv_safe_cell(value: Any) -> Any:
    """避免导出结果在 Excel/WPS 中被当作公式执行。"""
    if not isinstance(value, str):
        return value
    text = value.strip()
    if text[:1] in {"=", "+", "-", "@", "\t", "\r"}:
        return "'" + value
    return value


def _render_stale_warning(current: str, saved: str, subject: str) -> None:
    if saved and current != saved:
        render_warning_feedback(
            f"当前{subject}已变化，下面展示的是上一次查询结果，请重新查询。",
            title="结果可能已过期",
        )


def _is_valid_ip_address(value: str) -> bool:
    """校验获取到的公网 IP 文本，失败文案等非 IP 内容不应回填输入框。"""
    try:
        ipaddress.ip_address(str(value or "").strip())
        return True
    except ValueError:
        return False


def _parse_batch_targets(raw_text: str, limit: int = 50) -> List[str]:
    """解析批量输入：逐行去空白、去重，可选截断。"""
    lines = [line.strip() for line in str(raw_text or "").splitlines() if line.strip()]
    targets = list(dict.fromkeys(lines))
    return targets[:limit] if limit > 0 else targets


def _prepare_batch_targets(raw_text: str) -> List[str]:
    """批量查询前置校验：空输入给出提示并返回空列表，不创建运行记录。"""
    max_targets = max(1, int(get_ip_lookup_limits().max_batch_targets))
    unique_targets = _parse_batch_targets(raw_text, limit=0)
    if not unique_targets:
        render_warning_feedback("请输入至少一个查询目标后再开始批量查询。", title="批量查询输入为空")
        return []
    if len(unique_targets) > max_targets:
        render_warning_feedback(
            f"批量查询建议控制在 {max_targets} 条以内，本次只会处理前 {max_targets} 条。",
            title="批量查询提醒",
        )
    return unique_targets[:max_targets]


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _render_single_result(result: dict) -> None:
    if not result:
        return
    if not result.get("success"):
        render_error_feedback(result.get("error", "查询失败"), title="单个查询失败")
        return

    data = result["data"]
    source_text = str(data.get("地理数据来源", "") or "").strip()
    downgrade_note = str(data.get("来源降级说明", "") or "").strip()
    status_text = str(data.get("结果状态", "") or "").strip()
    if source_text:
        render_info_feedback(f"本次地理数据来源: {source_text}", title="来源状态")
    if status_text and status_text != "成功":
        render_warning_feedback(f"本次查询状态: {status_text}", title="结果状态")
    if downgrade_note:
        render_warning_feedback(downgrade_note, title="降级说明")

    display_df = pd.DataFrame({"字段": list(data.keys()), "值": [str(value) for value in data.values()]})
    st.dataframe(display_df, use_container_width=True, hide_index=True)
    action_download_button(
        "导出查询结果 JSON",
        data=json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"ip_lookup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )


def _build_batch_row(target: str, result: dict) -> dict:
    if not result.get("success"):
        row = {"输入": target, "状态": "失败", "错误": result.get("error", "查询失败")}
    else:
        data = result["data"]
        row = {
            "输入": target,
            "状态": "成功",
            "类型": data.get("输入类型", ""),
            "目标": data.get("IP地址") or data.get("域名") or data.get("解析IP", ""),
            "国家": data.get("国家", ""),
            "省份": data.get("省份", ""),
            "城市": data.get("城市", ""),
            "运营商": data.get("运营商", ""),
            "ASN": data.get("ASN信息", ""),
            "首选IP": data.get("解析IP", data.get("IP地址", "")),
            "地理源": data.get("地理数据来源", ""),
            "降级说明": data.get("来源降级说明", ""),
            "结果状态": data.get("结果状态", ""),
        }
    return {key: _csv_safe_cell(value) for key, value in row.items()}


def _render_asset_result(result: dict, label: str) -> None:
    if not result:
        return
    if not result.get("success"):
        render_error_feedback(result.get("error", f"{label} 查询失败"), title=f"{label}失败")
        return

    data = result["data"]
    st.caption(label)
    status_text = str(result.get("status") or (data.get("查询状态") if isinstance(data, dict) else "") or "").strip()
    if status_text == "partial":
        render_warning_feedback(
            f"{label}部分数据源失败，结果可能不完整。{data.get('错误信息', '') if isinstance(data, dict) else ''}",
            title="结果降级",
        )
    elif status_text not in {"", "ok"}:
        render_warning_feedback(f"{label}状态: {status_text}", title="结果状态")

    if isinstance(data, dict) and isinstance(data.get("结果"), list):
        results = data["结果"]
        if results:
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)
        else:
            render_info_feedback("当前没有查询到可展示的结果。", title=f"{label}无结果")
        export_payload = data
    else:
        st.dataframe(
            pd.DataFrame({"字段": list(data.keys()), "值": [str(value) for value in data.values()]}),
            use_container_width=True,
            hide_index=True,
        )
        export_payload = data

    action_download_button(
        f"导出{label} JSON",
        data=json.dumps(export_payload, ensure_ascii=False, indent=2).encode("utf-8"),
        file_name=f"{label}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
    )


def render_ip_lookup_page() -> None:
    _ensure_defaults()
    tool = IPQueryTool()
    run_center = get_session_task_runner("ip_lookup")

    pending_single_input = st.session_state.pop("ip_lookup_single_input_pending", None)
    if pending_single_input is not None:
        st.session_state["ip_lookup_single_input"] = pending_single_input

    show_doc("ip_domain_query")
    render_tool_page_hero(
        "🌐",
        "IP / 域名查询工具",
        "统一处理 IP、域名、URL 和 IPv4 格式转换，并补上子域名、旁站、ICP 等资产扩展能力，适合联调、验网和安全排查。",
        tags=["单个查询", "批量查询", "IPv4 转换", "子域名 / 旁站 / ICP"],
        accent="#1d4ed8",
    )
    limits = get_ip_lookup_limits()
    st.caption(
        "当前注册的能力: "
        f"地理数据源 {len(get_geo_providers())} 个 | "
        f"公网 IP 服务 {len(get_public_ip_services())} 个 | "
        f"转换方式 {len(get_conversion_types())} 种 | "
        f"资产动作 {len(get_asset_actions())} 项 | "
        f"批量上限 {limits.max_batch_targets} 条 | "
        f"地理缓存 {limits.geo_cache_ttl_seconds:.0f}s"
    )
    render_tool_tips(
        "排查建议",
        [
            "URL 场景直接粘完整地址，工具会自动提取 host、端口、路径和查询参数。",
            "批量排查时建议先去重并控制在 50 条以内，避免第三方公开接口限流。",
            "ICP 和资产扩展结果来自公开接口，正式结论建议再做人工复核。",
        ],
    )

    single_tab, batch_tab, convert_tab, asset_tab = st.tabs(["单个查询", "批量查询", "IPv4 转换", "资产扩展"])

    with single_tab:
        input_col1, input_col2 = st.columns([3, 1])
        with input_col1:
            st.text_input(
                "输入 IP / 域名 / URL",
                key="ip_lookup_single_input",
                placeholder="例如 8.8.8.8 / example.com / https://example.com:8443/login",
            )
        with input_col2:
            if secondary_action_button("获取当前公网 IP", key="ip_lookup_public_ip"):
                public_ip = tool.get_public_ip()
                if _is_valid_ip_address(public_ip):
                    st.session_state["ip_lookup_single_input_pending"] = public_ip
                    st.rerun()
                else:
                    render_error_feedback(
                        "获取当前公网 IP 失败，请检查网络或稍后重试；原输入内容已保留。",
                        title="获取公网 IP 失败",
                    )

        if primary_action_button("开始单个查询", key="ip_lookup_single_button"):
            single_target = str(st.session_state.ip_lookup_single_input or "").strip()
            try:
                def _single_query_task(logger):
                    logger(f"开始单个查询: {single_target}")
                    result = tool.get_ip_domain_info(single_target)
                    st.session_state.ip_lookup_single_result = result
                    if result.get("success"):
                        logger("单个查询成功。")
                    else:
                        logger(f"单个查询失败: {result.get('error', '未知错误')}")
                        raise RuntimeError(result.get("error", "查询失败"))
                    return {"success": True, "target": single_target}

                run_info = run_center.submit(
                    tool="IP/域名查询工具",
                    action="单个查询",
                    payload={"target": single_target},
                    executor=_single_query_task,
                )
                st.session_state.ip_lookup_single_result_signature = _signature({"target": single_target})
                st.caption(f"Run ID: `{run_info['run_id']}`")
            except Exception as exc:
                render_error_feedback(str(exc), title="单个查询异常")

        current_signature = _signature({"target": str(st.session_state.ip_lookup_single_input or "").strip()})
        _render_stale_warning(current_signature, st.session_state.ip_lookup_single_result_signature, "单个查询输入")
        _render_single_result(st.session_state.ip_lookup_single_result)

    with batch_tab:
        st.text_area(
            "批量输入目标，每行一个",
            key="ip_lookup_batch_text",
            height=180,
            placeholder="8.8.8.8\nexample.com\nhttps://www.baidu.com",
        )
        if primary_action_button("开始批量查询", key="ip_lookup_batch_button") and (limited_targets := _prepare_batch_targets(st.session_state.ip_lookup_batch_text)):
            try:
                def _batch_query_task(logger):
                    logger(f"开始批量查询，目标数量={len(limited_targets)}。")
                    rows = []
                    progress = st.progress(0)
                    total = max(len(limited_targets), 1)
                    for index, target in enumerate(limited_targets, start=1):
                        result = tool.get_ip_domain_info(target)
                        rows.append(_build_batch_row(target, result))
                        progress.progress(index / total)
                    st.session_state.ip_lookup_batch_result = rows
                    success_count = sum(1 for row in rows if row.get("状态") == "成功")
                    logger(f"批量查询完成，成功={success_count}，失败={len(rows) - success_count}。")
                    return {"total": len(rows), "success": success_count, "failed": len(rows) - success_count}

                run_info = run_center.submit(
                    tool="IP/域名查询工具",
                    action="批量查询",
                    payload={"target_count": len(limited_targets)},
                    executor=_batch_query_task,
                )
                st.session_state.ip_lookup_batch_result_signature = _signature({"targets": limited_targets})
                st.caption(f"Run ID: `{run_info['run_id']}`")
            except Exception as exc:
                render_error_feedback(str(exc), title="批量查询异常")

        current_batch_targets = _parse_batch_targets(
            st.session_state.ip_lookup_batch_text,
            limit=max(1, int(get_ip_lookup_limits().max_batch_targets)),
        )
        _render_stale_warning(
            _signature({"targets": current_batch_targets}),
            st.session_state.ip_lookup_batch_result_signature,
            "批量查询输入",
        )
        if st.session_state.ip_lookup_batch_result:
            batch_df = pd.DataFrame(st.session_state.ip_lookup_batch_result)
            success_count = sum(1 for row in st.session_state.ip_lookup_batch_result if row.get("状态") == "成功")
            st.caption(
                f"批量查询汇总: 共 {len(batch_df)} 条，成功 {success_count} 条，失败 {len(batch_df) - success_count} 条。"
            )
            st.dataframe(batch_df, use_container_width=True, hide_index=True)
            action_download_button(
                "导出批量结果 CSV",
                data=batch_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"ip_lookup_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    with convert_tab:
        input_value = st.text_input("输入 IPv4 地址 / 十进制 / 十六进制 / 二进制", key="ip_lookup_convert_input")
        conversion_labels = [spec.label for spec in get_conversion_types()]
        if st.session_state.get("ip_lookup_convert_type") not in conversion_labels:
            st.session_state["ip_lookup_convert_type"] = conversion_labels[0]
        conversion_type = st.selectbox(
            "转换方式",
            conversion_labels,
            key="ip_lookup_convert_type",
        )
        if primary_action_button("开始 IPv4 转换", key="ip_lookup_convert_button"):
            result = tool.convert_ip_address(input_value, conversion_type)
            if result["success"]:
                data = result["data"]
                summary_parts = [f"{key}: {value}" for key, value in data.items()]
                st.caption("转换结果: " + " | ".join(summary_parts))
                st.dataframe(
                    pd.DataFrame({"字段": list(data.keys()), "值": [str(value) for value in data.values()]}),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                render_error_feedback(result["error"], title="IPv4 转换失败")

    with asset_tab:
        st.text_input("输入域名或 URL", key="ip_lookup_asset_input", placeholder="例如 https://www.baidu.com")
        actions = get_asset_actions()
        action_columns = st.columns(max(1, len(actions)))
        for action, column in zip(actions, action_columns):
            with column:
                if primary_action_button(action.label, key=action.button_key):
                    target = str(st.session_state.ip_lookup_asset_input or "").strip()
                    st.session_state.ip_lookup_asset_action = action.key
                    st.session_state.ip_lookup_asset_label = action.result_label or action.label
                    st.session_state.ip_lookup_asset_result = tool.run_asset_action(action.key, target)
                    st.session_state.ip_lookup_asset_result_signature = _signature(
                        {"target": target, "action": action.key}
                    )

        saved_action = st.session_state.ip_lookup_asset_action
        current_asset_signature = _signature(
            {"target": str(st.session_state.ip_lookup_asset_input or "").strip(), "action": saved_action}
        )
        _render_stale_warning(current_asset_signature, st.session_state.ip_lookup_asset_result_signature, "资产查询输入")
        _render_asset_result(st.session_state.ip_lookup_asset_result, st.session_state.ip_lookup_asset_label)

    render_task_run_panel(
        run_center=run_center,
        tool_name="IP/域名查询工具",
        panel_key="ip_lookup_run_panel",
        limit=10,
    )
