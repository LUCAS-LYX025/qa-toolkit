from __future__ import annotations

import json
from datetime import datetime

import pandas as pd
import streamlit as st

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
    "ip_lookup_batch_text": "",
    "ip_lookup_batch_result": None,
    "ip_lookup_asset_input": "",
    "ip_lookup_asset_result": None,
    "ip_lookup_asset_label": "",
}


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
    if source_text:
        render_info_feedback(f"本次地理数据来源: {source_text}", title="来源状态")
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
        return {"输入": target, "状态": "失败", "错误": result.get("error", "查询失败")}

    data = result["data"]
    return {
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
    }


def _render_asset_result(result: dict, label: str) -> None:
    if not result:
        return
    if not result.get("success"):
        render_error_feedback(result.get("error", f"{label} 查询失败"), title=f"{label}失败")
        return

    data = result["data"]
    st.caption(label)

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
                st.session_state["ip_lookup_single_input_pending"] = tool.get_public_ip()
                st.rerun()

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
                st.caption(f"Run ID: `{run_info['run_id']}`")
            except Exception as exc:
                render_error_feedback(str(exc), title="单个查询异常")

        _render_single_result(st.session_state.ip_lookup_single_result)

    with batch_tab:
        st.text_area(
            "批量输入目标，每行一个",
            key="ip_lookup_batch_text",
            height=180,
            placeholder="8.8.8.8\nexample.com\nhttps://www.baidu.com",
        )
        if primary_action_button("开始批量查询", key="ip_lookup_batch_button"):
            raw_lines = [line.strip() for line in st.session_state.ip_lookup_batch_text.splitlines() if line.strip()]
            unique_targets = list(dict.fromkeys(raw_lines))
            if len(unique_targets) > 50:
                render_warning_feedback("批量查询建议控制在 50 条以内，本次只会处理前 50 条。", title="批量查询提醒")
            limited_targets = unique_targets[:50]
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
                st.caption(f"Run ID: `{run_info['run_id']}`")
            except Exception as exc:
                render_error_feedback(str(exc), title="批量查询异常")

        if st.session_state.ip_lookup_batch_result:
            batch_df = pd.DataFrame(st.session_state.ip_lookup_batch_result)
            st.dataframe(batch_df, use_container_width=True, hide_index=True)
            action_download_button(
                "导出批量结果 CSV",
                data=batch_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"ip_lookup_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )

    with convert_tab:
        input_value = st.text_input("输入 IPv4 地址 / 十进制 / 十六进制 / 二进制", key="ip_lookup_convert_input")
        conversion_type = st.selectbox(
            "转换方式",
            ["自动识别并展示全部格式", "十进制 ↔ 点分十进制", "点分十进制 ↔ 十六进制", "点分十进制 ↔ 二进制"],
            key="ip_lookup_convert_type",
        )
        if primary_action_button("开始 IPv4 转换", key="ip_lookup_convert_button"):
            result = tool.convert_ip_address(input_value, conversion_type)
            if result["success"]:
                data = result["data"]
                st.dataframe(
                    pd.DataFrame({"字段": list(data.keys()), "值": [str(value) for value in data.values()]}),
                    use_container_width=True,
                    hide_index=True,
                )
            else:
                render_error_feedback(result["error"], title="IPv4 转换失败")

    with asset_tab:
        st.text_input("输入域名或 URL", key="ip_lookup_asset_input", placeholder="例如 https://www.baidu.com")
        action_col1, action_col2, action_col3 = st.columns(3)
        with action_col1:
            if primary_action_button("查询子域名", key="ip_lookup_subdomains"):
                st.session_state.ip_lookup_asset_label = "子域名查询"
                st.session_state.ip_lookup_asset_result = tool.query_subdomains(st.session_state.ip_lookup_asset_input)
        with action_col2:
            if primary_action_button("查询旁站", key="ip_lookup_reverse"):
                st.session_state.ip_lookup_asset_label = "旁站查询"
                st.session_state.ip_lookup_asset_result = tool.query_reverse_sites(st.session_state.ip_lookup_asset_input)
        with action_col3:
            if primary_action_button("查询 ICP", key="ip_lookup_icp"):
                st.session_state.ip_lookup_asset_label = "ICP备案查询"
                st.session_state.ip_lookup_asset_result = tool.query_icp_info(st.session_state.ip_lookup_asset_input)

        _render_asset_result(st.session_state.ip_lookup_asset_result, st.session_state.ip_lookup_asset_label)

    render_task_run_panel(
        run_center=run_center,
        tool_name="IP/域名查询工具",
        panel_key="ip_lookup_run_panel",
        limit=10,
    )
