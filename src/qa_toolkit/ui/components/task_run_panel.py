from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qa_toolkit.core.task_runner import TaskRunCenter


def _build_table_rows(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    for item in records:
        rows.append(
            {
                "Run ID": item.get("run_id", ""),
                "动作": item.get("action", ""),
                "状态": item.get("status", ""),
                "开始时间": item.get("started_at", ""),
                "结束时间": item.get("finished_at", ""),
                "摘要": item.get("summary", ""),
            }
        )
    return rows


def render_task_run_panel(
    run_center: TaskRunCenter,
    tool_name: str,
    panel_key: str,
    limit: int = 8,
) -> None:
    with st.expander("📚 运行记录", expanded=False):
        records = run_center.list_runs(tool=tool_name, limit=limit)
        if not records:
            st.caption("当前工具暂无运行记录。")
            return

        st.dataframe(pd.DataFrame(_build_table_rows(records)), use_container_width=True, hide_index=True)

        options = [f"{item.get('run_id', '')} | {item.get('action', '')} | {item.get('status', '')}" for item in records]
        selected = st.selectbox("查看日志详情", options=options, key=f"{panel_key}_run_selector")
        selected_run_id = selected.split(" | ", 1)[0].strip()
        run_detail = run_center.get_run(selected_run_id) or {}

        if run_detail.get("error"):
            st.error(run_detail["error"])
        if run_detail.get("retry_of"):
            st.caption(f"重试来源: `{run_detail.get('retry_of')}`")
        st.caption(f"输入摘要哈希: `{run_detail.get('input_digest', '')}`")

        logs = run_detail.get("logs") or []
        if logs:
            st.code("\n".join(logs[-40:]), language="text")
        else:
            st.caption("该任务暂无日志。")
