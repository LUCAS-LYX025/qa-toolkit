from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import plotly.express as px
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.utils.log_analysis import (
    apply_json_filters,
    apply_text_filters,
    build_health_notes,
    dataframe_to_lines,
    decode_log_bytes,
    detect_json_columns,
    detect_log_level,
    extract_timestamp,
    search_lines,
    summarize_log_lines,
)


SAMPLE_LOG_TEXT = """2026-04-05 09:30:01 INFO  [gateway] GET /api/orders 200 duration=123ms ip=10.0.0.8 traceId=abc001
2026-04-05 09:30:05 WARN  [gateway] GET /api/orders 429 duration=812ms ip=10.0.0.8 traceId=abc002
2026-04-05 09:30:07 ERROR [order-service] POST /api/orders 500 duration=1820ms ip=10.0.1.16 traceId=abc003 java.lang.RuntimeException: create order failed
2026-04-05 09:30:07 ERROR [order-service] POST /api/orders 500 duration=1820ms ip=10.0.1.16 traceId=abc003 java.lang.RuntimeException: create order failed
2026-04-05 09:30:08 DEBUG [order-service] request payload={"userId": 1001, "skuId": 2001}
2026-04-05 09:30:10 INFO  [auth] POST /api/login 401 duration=66ms ip=10.0.2.5 traceId=auth001
2026-04-05 09:30:11 ERROR [auth] LoginException user login failed for user=tester ip=10.0.2.5
2026-04-05 09:31:15 INFO  [gateway] GET /health 200 duration=12ms ip=127.0.0.1
2026-04-05 09:31:17 WARN  [inventory] GET /api/stock 404 duration=95ms ip=10.0.3.9
2026-04-05 09:31:20 INFO  [report] export finished 200 duration=2450ms ip=10.0.4.22
"""

UPLOAD_TYPES = ["txt", "log", "csv", "jsonl", "ndjson"]
LOG_LEVEL_OPTIONS = ["错误", "警告", "信息", "调试", "其他"]
DEFAULT_STATE = {
    "log_analyzer_raw_text": "",
    "log_analyzer_df": None,
    "log_analyzer_source_name": "未导入",
    "log_analyzer_source_type": "text",
    "log_analyzer_csv_columns": [],
    "log_analyzer_json_fields": {},
    "log_analyzer_filter_logic": "AND",
    "log_analyzer_advanced_text_filters": [],
    "log_analyzer_json_filters": [],
    "log_analyzer_quick_levels": [],
    "log_analyzer_include_keyword": "",
    "log_analyzer_exclude_keyword": "",
    "log_analyzer_ip_filter": "",
    "log_analyzer_status_codes": "",
    "log_analyzer_only_errors": False,
    "log_analyzer_hide_debug": False,
    "log_analyzer_search_keyword": "",
    "log_analyzer_search_scope": "全部日志",
    "log_analyzer_search_case_sensitive": False,
    "log_analyzer_search_whole_word": False,
    "log_analyzer_search_use_regex": False,
    "log_analyzer_search_context": 1,
    "log_analyzer_show_charts": True,
    "log_analyzer_slow_threshold": 1000.0,
    "log_analyzer_top_n": 10,
}


def _ensure_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _clear_filters_and_search():
    st.session_state.log_analyzer_filter_logic = "AND"
    st.session_state.log_analyzer_advanced_text_filters = []
    st.session_state.log_analyzer_json_filters = []
    st.session_state.log_analyzer_quick_levels = []
    st.session_state.log_analyzer_include_keyword = ""
    st.session_state.log_analyzer_exclude_keyword = ""
    st.session_state.log_analyzer_ip_filter = ""
    st.session_state.log_analyzer_status_codes = ""
    st.session_state.log_analyzer_only_errors = False
    st.session_state.log_analyzer_hide_debug = False
    st.session_state.log_analyzer_search_keyword = ""
    st.session_state.log_analyzer_search_scope = "全部日志"
    st.session_state.log_analyzer_search_case_sensitive = False
    st.session_state.log_analyzer_search_whole_word = False
    st.session_state.log_analyzer_search_use_regex = False
    st.session_state.log_analyzer_search_context = 1


def _reset_all():
    st.session_state.log_analyzer_raw_text = ""
    st.session_state.log_analyzer_df = None
    st.session_state.log_analyzer_source_name = "未导入"
    st.session_state.log_analyzer_source_type = "text"
    st.session_state.log_analyzer_csv_columns = []
    st.session_state.log_analyzer_json_fields = {}
    _clear_filters_and_search()


def _load_text_source(text: str, source_name: str, source_type: str = "text"):
    st.session_state.log_analyzer_raw_text = text
    st.session_state.log_analyzer_df = None
    st.session_state.log_analyzer_source_name = source_name
    st.session_state.log_analyzer_source_type = source_type
    st.session_state.log_analyzer_csv_columns = []
    st.session_state.log_analyzer_json_fields = {}
    _clear_filters_and_search()


def _load_dataframe_source(df: pd.DataFrame, source_name: str, source_type: str):
    normalized_df = df.reset_index(drop=True)
    st.session_state.log_analyzer_df = normalized_df
    st.session_state.log_analyzer_raw_text = "\n".join(dataframe_to_lines(normalized_df))
    st.session_state.log_analyzer_source_name = source_name
    st.session_state.log_analyzer_source_type = source_type
    st.session_state.log_analyzer_csv_columns = [str(column) for column in normalized_df.columns.tolist()]
    st.session_state.log_analyzer_json_fields = detect_json_columns(normalized_df)
    _clear_filters_and_search()


def _parse_jsonl_dataframe(text: str) -> pd.DataFrame:
    records: List[Dict[str, Any]] = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ValueError(f"第 {line_number} 行 JSON 解析失败: {exc}") from exc

        if isinstance(parsed, dict):
            records.append(parsed)
        else:
            records.append({"value": parsed})

    if not records:
        raise ValueError("JSONL 文件中没有可解析的记录")
    return pd.DataFrame(records)


def _get_source_lines() -> List[str]:
    if isinstance(st.session_state.log_analyzer_df, pd.DataFrame):
        return dataframe_to_lines(st.session_state.log_analyzer_df)
    text = str(st.session_state.log_analyzer_raw_text or "")
    return text.splitlines()


def _build_quick_text_filters() -> List[Dict[str, Any]]:
    filters: List[Dict[str, Any]] = []
    levels = list(st.session_state.log_analyzer_quick_levels or [])
    include_keyword = str(st.session_state.log_analyzer_include_keyword or "").strip()
    exclude_keyword = str(st.session_state.log_analyzer_exclude_keyword or "").strip()
    ip_filter_value = str(st.session_state.log_analyzer_ip_filter or "").strip()
    status_codes = str(st.session_state.log_analyzer_status_codes or "").strip()

    if levels:
        filters.append({"type": "log_level", "value": levels})
    if include_keyword:
        filters.append({"type": "keyword", "value": include_keyword})
    if exclude_keyword:
        filters.append({"type": "exclude_keyword", "value": exclude_keyword})
    if ip_filter_value:
        filters.append({"type": "ip_filter", "value": ip_filter_value})
    if status_codes:
        filters.append({"type": "status_code", "value": status_codes})
    if bool(st.session_state.log_analyzer_only_errors):
        filters.append({"type": "show_only_errors", "value": True})
    if bool(st.session_state.log_analyzer_hide_debug):
        filters.append({"type": "hide_debug", "value": True})
    return filters


def _has_active_filters() -> bool:
    return bool(
        _build_quick_text_filters()
        or st.session_state.log_analyzer_advanced_text_filters
        or st.session_state.log_analyzer_json_filters
    )


def _apply_active_filters() -> tuple[List[str], pd.DataFrame | None, List[int]]:
    logic = st.session_state.log_analyzer_filter_logic
    csv_columns = list(st.session_state.log_analyzer_csv_columns or [])
    text_filters = _build_quick_text_filters() + list(st.session_state.log_analyzer_advanced_text_filters or [])
    json_filters = list(st.session_state.log_analyzer_json_filters or [])

    if isinstance(st.session_state.log_analyzer_df, pd.DataFrame):
        source_df = st.session_state.log_analyzer_df
        filtered_df = apply_json_filters(source_df, json_filters, logic) if json_filters else source_df
        lines = dataframe_to_lines(filtered_df)
        indexes = list(filtered_df.index)

        if text_filters:
            kept_indexes: List[int] = []
            kept_lines: List[str] = []
            for row_index, line in zip(indexes, lines):
                if apply_text_filters(line, text_filters, logic, csv_columns=csv_columns):
                    kept_indexes.append(row_index)
                    kept_lines.append(line)
            filtered_df = filtered_df.loc[kept_indexes]
            lines = kept_lines
            indexes = kept_indexes

        return lines, filtered_df, indexes

    source_lines = _get_source_lines()
    if not text_filters:
        return source_lines, None, list(range(len(source_lines)))

    filtered_lines: List[str] = []
    filtered_indexes: List[int] = []
    for index, line in enumerate(source_lines):
        if apply_text_filters(line, text_filters, logic):
            filtered_lines.append(line)
            filtered_indexes.append(index)
    return filtered_lines, None, filtered_indexes


def _build_line_table(lines: List[str], indexes: List[int], limit: int = 500) -> pd.DataFrame:
    records = []
    for display_index, (source_index, line) in enumerate(zip(indexes, lines), start=1):
        if display_index > limit:
            break
        records.append(
            {
                "原始行号": source_index + 1,
                "级别": detect_log_level(line),
                "时间": extract_timestamp(line),
                "内容": line,
            }
        )
    return pd.DataFrame(records)


def _summary_export_payload(summary: Dict[str, Any], scope_label: str) -> str:
    return json.dumps(
        {
            "scope": scope_label,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "summary": summary,
            "notes": build_health_notes(summary),
        },
        ensure_ascii=False,
        indent=2,
    )


def _render_import_tab():
    st.markdown("### 导入方式")
    import_method = st.radio("选择来源", ["文件上传", "直接粘贴"], horizontal=True)

    action_cols = st.columns([1, 1, 3])
    with action_cols[0]:
        if st.button("载入示例", use_container_width=True):
            _load_text_source(SAMPLE_LOG_TEXT, "示例日志", "text")
            st.rerun()
    with action_cols[1]:
        if st.button("清空全部", use_container_width=True):
            _reset_all()
            st.rerun()
    with action_cols[2]:
        st.caption(
            f"当前来源: `{st.session_state.log_analyzer_source_name}` | "
            f"类型: `{st.session_state.log_analyzer_source_type}`"
        )

    if import_method == "文件上传":
        uploaded_file = st.file_uploader(
            "选择日志文件",
            type=UPLOAD_TYPES,
            help="支持 txt / log / csv / jsonl / ndjson",
        )
        if uploaded_file is not None:
            st.caption(f"已选择 `{uploaded_file.name}`，大小 {uploaded_file.size:,} bytes")
            if st.button("导入文件", use_container_width=True):
                raw_bytes = uploaded_file.getvalue()
                file_name = uploaded_file.name
                suffix = file_name.rsplit(".", 1)[-1].lower() if "." in file_name else ""

                try:
                    if suffix == "csv":
                        dataframe = pd.read_csv(io.BytesIO(raw_bytes))
                        _load_dataframe_source(dataframe, file_name, "csv")
                    elif suffix in {"jsonl", "ndjson"}:
                        text = decode_log_bytes(raw_bytes)
                        dataframe = _parse_jsonl_dataframe(text)
                        _load_dataframe_source(dataframe, file_name, "jsonl")
                    else:
                        text = decode_log_bytes(raw_bytes)
                        _load_text_source(text, file_name, "text")
                    st.success("日志数据导入成功")
                    st.rerun()
                except Exception as exc:
                    st.error(f"导入失败: {exc}")
    else:
        pasted_text = st.text_area(
            "粘贴日志内容",
            height=220,
            placeholder="请将日志内容粘贴到此处...",
            key="log_analyzer_paste_area",
        )
        if st.button("导入粘贴内容", use_container_width=True):
            if not pasted_text.strip():
                st.warning("请输入日志内容")
            else:
                _load_text_source(pasted_text, "手动粘贴", "text")
                st.success("日志数据导入成功")
                st.rerun()

    if st.session_state.log_analyzer_raw_text or isinstance(st.session_state.log_analyzer_df, pd.DataFrame):
        st.markdown("### 数据预览")
        if isinstance(st.session_state.log_analyzer_df, pd.DataFrame):
            st.dataframe(st.session_state.log_analyzer_df.head(20), use_container_width=True, height=320)
            if st.session_state.log_analyzer_json_fields:
                st.info(
                    "检测到 JSON 列: "
                    + "、".join(
                        f"{column} ({len(fields)} 个字段)"
                        for column, fields in st.session_state.log_analyzer_json_fields.items()
                    )
                )
        else:
            preview_lines = _get_source_lines()[:20]
            st.text_area(
                "预览内容",
                "\n".join(preview_lines),
                height=320,
                disabled=True,
                label_visibility="collapsed",
            )


def _render_overview_tab(summary: Dict[str, Any], scope_label: str):
    level_counts = summary["level_counts"]
    metric_cols = st.columns(6)
    metric_cols[0].metric("总行数", f"{summary['total_lines']:,}")
    metric_cols[1].metric("错误", f"{level_counts['错误']:,}")
    metric_cols[2].metric("警告", f"{level_counts['警告']:,}")
    metric_cols[3].metric("信息", f"{level_counts['信息']:,}")
    metric_cols[4].metric("调试", f"{level_counts['调试']:,}")
    metric_cols[5].metric("重复组数", f"{summary['duplicate_line_groups']:,}")

    metric_cols2 = st.columns(5)
    metric_cols2[0].metric("唯一 IP", f"{summary['unique_ip_count']:,}")
    metric_cols2[1].metric("异常条数", f"{summary['exception_line_count']:,}")
    metric_cols2[2].metric("慢日志", f"{summary['slow_line_count']:,}")
    metric_cols2[3].metric("非空行", f"{summary['non_empty_lines']:,}")
    metric_cols2[4].metric("分析范围", scope_label)

    notes = build_health_notes(summary)
    st.info(" | ".join(notes))

    time_range = summary.get("time_range")
    if time_range:
        st.caption(f"时间范围: {time_range['start']} -> {time_range['end']}")

    if st.session_state.log_analyzer_show_charts and summary["total_lines"] > 0:
        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            level_df = pd.DataFrame(
                [{"级别": level, "数量": count} for level, count in level_counts.items() if count > 0]
            )
            if not level_df.empty:
                st.plotly_chart(
                    px.pie(level_df, values="数量", names="级别", title="日志级别分布"),
                    use_container_width=True,
                )
        with chart_col2:
            duration_stats = summary["duration_stats"]
            if duration_stats["count"]:
                duration_df = pd.DataFrame(
                    [
                        {"指标": "平均耗时", "毫秒": duration_stats["avg_ms"]},
                        {"指标": "最大耗时", "毫秒": duration_stats["max_ms"]},
                        {"指标": "P95", "毫秒": duration_stats["p95_ms"]},
                        {"指标": "P99", "毫秒": duration_stats["p99_ms"]},
                    ]
                )
                st.plotly_chart(
                    px.bar(duration_df, x="指标", y="毫秒", title="耗时概览"),
                    use_container_width=True,
                )
            else:
                st.caption("当前范围没有可提取的耗时信息。")

    export_cols = st.columns(2)
    with export_cols[0]:
        st.download_button(
            "下载统计摘要 JSON",
            data=_summary_export_payload(summary, scope_label),
            file_name=f"log_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
            use_container_width=True,
        )
    with export_cols[1]:
        st.download_button(
            "下载当前范围日志",
            data="\n".join(_get_source_lines()) if scope_label == "全部日志" else "",
            file_name=f"log_scope_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
            disabled=scope_label != "全部日志",
        )


def _apply_filter_preset(preset: str):
    if preset == "only_errors":
        st.session_state.log_analyzer_quick_levels = ["错误"]
        st.session_state.log_analyzer_only_errors = True
        st.session_state.log_analyzer_hide_debug = False
        st.session_state.log_analyzer_include_keyword = ""
        st.session_state.log_analyzer_exclude_keyword = ""
        st.session_state.log_analyzer_status_codes = ""
        st.session_state.log_analyzer_ip_filter = ""
    elif preset == "server_failures":
        st.session_state.log_analyzer_quick_levels = []
        st.session_state.log_analyzer_only_errors = False
        st.session_state.log_analyzer_hide_debug = True
        st.session_state.log_analyzer_status_codes = "500,502,503,504"
        st.session_state.log_analyzer_include_keyword = ""
        st.session_state.log_analyzer_exclude_keyword = ""
    elif preset == "auth_failures":
        st.session_state.log_analyzer_quick_levels = ["错误", "警告"]
        st.session_state.log_analyzer_status_codes = "401,403"
        st.session_state.log_analyzer_include_keyword = "login"
        st.session_state.log_analyzer_hide_debug = True
    elif preset == "hide_debug":
        st.session_state.log_analyzer_hide_debug = True
    elif preset == "clear":
        _clear_filters_and_search()


def _render_active_conditions(
    quick_text_filters: List[Dict[str, Any]],
    advanced_text_filters: List[Dict[str, Any]],
    json_filters: List[Dict[str, Any]],
):
    st.markdown("### 当前条件")
    if not quick_text_filters and not advanced_text_filters and not json_filters:
        st.info("当前没有活动过滤条件。")
        return

    for index, filter_config in enumerate(quick_text_filters):
        label = f"{filter_config['type']} {filter_config.get('value', '')}".strip()
        st.caption(f"快速条件 {index + 1}: {label}")

    for index, filter_config in enumerate(advanced_text_filters):
        if filter_config.get("column"):
            label = f"{filter_config['column']} {filter_config.get('operator', '包含')} {filter_config.get('value', '')}".strip()
        else:
            label = f"{filter_config['type']} {filter_config.get('value', '')}".strip()
        cols = st.columns([4, 1])
        with cols[0]:
            st.caption(f"高级文本条件 {index + 1}: {label}")
        with cols[1]:
            if st.button("删除", key=f"remove_text_filter_{index}", use_container_width=True):
                st.session_state.log_analyzer_advanced_text_filters.pop(index)
                st.rerun()

    for index, filter_config in enumerate(json_filters):
        if filter_config.get("value_range"):
            value_text = f"{filter_config['value_range'][0]} - {filter_config['value_range'][1]}"
        else:
            value_text = str(filter_config.get("value", ""))
        cols = st.columns([4, 1])
        with cols[0]:
            st.caption(
                f"JSON条件 {index + 1}: {filter_config['column']}.{filter_config['field']} "
                f"{filter_config.get('operator', '包含')} {value_text}".strip()
            )
        with cols[1]:
            if st.button("删除", key=f"remove_json_filter_{index}", use_container_width=True):
                st.session_state.log_analyzer_json_filters.pop(index)
                st.rerun()


def _render_filter_tab(source_lines: List[str]):
    st.markdown("### 快速过滤")
    preset_cols = st.columns(5)
    if preset_cols[0].button("仅错误", use_container_width=True):
        _apply_filter_preset("only_errors")
        st.rerun()
    if preset_cols[1].button("5xx 问题", use_container_width=True):
        _apply_filter_preset("server_failures")
        st.rerun()
    if preset_cols[2].button("认证失败", use_container_width=True):
        _apply_filter_preset("auth_failures")
        st.rerun()
    if preset_cols[3].button("隐藏调试", use_container_width=True):
        _apply_filter_preset("hide_debug")
        st.rerun()
    if preset_cols[4].button("清空过滤", use_container_width=True):
        _apply_filter_preset("clear")
        st.rerun()

    row1 = st.columns(3)
    row1[0].multiselect(
        "日志级别",
        LOG_LEVEL_OPTIONS,
        default=list(st.session_state.log_analyzer_quick_levels),
        key="log_analyzer_quick_levels",
    )
    row1[1].text_input("包含关键词", key="log_analyzer_include_keyword", placeholder="例如 timeout / orderId")
    row1[2].text_input("排除关键词", key="log_analyzer_exclude_keyword", placeholder="例如 health / heartbeat")

    row2 = st.columns(4)
    row2[0].text_input("状态码", key="log_analyzer_status_codes", placeholder="200,404,500")
    row2[1].text_input("IP / CIDR", key="log_analyzer_ip_filter", placeholder="10.0.0.8 或 10.0.0.0/24")
    row2[2].checkbox("仅显示错误", key="log_analyzer_only_errors")
    row2[3].checkbox("隐藏调试", key="log_analyzer_hide_debug")

    st.radio(
        "条件逻辑",
        ["AND", "OR"],
        horizontal=True,
        key="log_analyzer_filter_logic",
        help="AND 表示所有条件都满足，OR 表示任一条件满足即可",
    )

    with st.expander("高级条件", expanded=False):
        csv_columns = list(st.session_state.log_analyzer_csv_columns or [])
        if csv_columns:
            st.markdown("#### CSV 列条件")
            col1, col2, col3, col4 = st.columns([1.6, 1.4, 1.8, 1])
            column = col1.selectbox("列", csv_columns, key="log_csv_filter_column")
            operator = col2.selectbox("操作符", ["包含", "等于", "开头为", "结尾为", "有值", "没有值"], key="log_csv_filter_operator")
            if operator in {"有值", "没有值"}:
                value = ""
                col3.info("当前操作符无需输入值")
            else:
                value = col3.text_input("值", key="log_csv_filter_value")
            if col4.button("添加 CSV 条件", use_container_width=True):
                if operator not in {"有值", "没有值"} and not value:
                    st.warning("请输入条件值")
                else:
                    st.session_state.log_analyzer_advanced_text_filters.append(
                        {
                            "type": "keyword",
                            "column": column,
                            "operator": operator,
                            "value": value,
                        }
                    )
                    st.rerun()

        if st.session_state.log_analyzer_json_fields:
            st.markdown("#### JSON 字段条件")
            json_cols = list(st.session_state.log_analyzer_json_fields.keys())
            col1, col2, col3, col4, col5 = st.columns([1.5, 1.5, 1.4, 1.6, 1])
            json_column = col1.selectbox("JSON 列", json_cols, key="log_json_filter_column")
            json_field = col2.selectbox(
                "字段",
                st.session_state.log_analyzer_json_fields.get(json_column, []),
                key="log_json_filter_field",
            )
            json_operator = col3.selectbox(
                "操作符",
                ["包含", "等于", "开头为", "结尾为", "有值", "没有值", "数值范围"],
                key="log_json_filter_operator",
            )
            range_value = None
            if json_operator == "数值范围":
                min_val = col4.number_input("最小值", key="log_json_filter_range_min", value=0.0)
                max_val = col4.number_input("最大值", key="log_json_filter_range_max", value=1000.0)
                range_value = [float(min_val), float(max_val)]
                json_value = None
            elif json_operator in {"有值", "没有值"}:
                json_value = None
                col4.info("当前操作符无需输入值")
            else:
                json_value = col4.text_input("字段值", key="log_json_filter_value")
            if col5.button("添加 JSON 条件", use_container_width=True):
                if json_operator not in {"有值", "没有值", "数值范围"} and not json_value:
                    st.warning("请输入字段值")
                else:
                    st.session_state.log_analyzer_json_filters.append(
                        {
                            "column": json_column,
                            "field": json_field,
                            "operator": json_operator,
                            "value": json_value,
                            "value_range": range_value,
                        }
                    )
                    st.rerun()

    advanced_text_filters = list(st.session_state.log_analyzer_advanced_text_filters or [])
    quick_text_filters = _build_quick_text_filters()
    active_json_filters = list(st.session_state.log_analyzer_json_filters or [])
    _render_active_conditions(quick_text_filters, advanced_text_filters, active_json_filters)

    filtered_lines, filtered_df, filtered_indexes = _apply_active_filters()
    scope_label = "过滤结果" if _has_active_filters() else "全部日志"
    st.markdown(f"### {scope_label}")
    st.caption(f"当前结果 {len(filtered_lines):,} 行 / 原始 {len(source_lines):,} 行")

    if not filtered_lines:
        st.warning("当前条件下没有匹配结果。")
        return

    if filtered_df is not None:
        st.dataframe(filtered_df.head(500), use_container_width=True, height=360)
        export_data = filtered_df.to_csv(index=False)
        export_mime = "text/csv"
        export_name = "filtered_logs.csv"
    else:
        preview_df = _build_line_table(filtered_lines, filtered_indexes)
        st.dataframe(preview_df, use_container_width=True, height=360, hide_index=True)
        export_data = "\n".join(filtered_lines)
        export_mime = "text/plain"
        export_name = "filtered_logs.txt"

    st.download_button(
        "导出当前结果",
        data=export_data,
        file_name=export_name,
        mime=export_mime,
        use_container_width=True,
    )


def _render_search_tab(source_lines: List[str]):
    active_filters = _has_active_filters()
    filtered_lines, _, filtered_indexes = _apply_active_filters()

    scope_options = ["全部日志"] if not active_filters else ["全部日志", "过滤结果"]
    if st.session_state.log_analyzer_search_scope not in scope_options:
        st.session_state.log_analyzer_search_scope = scope_options[0]

    search_cols = st.columns([2.5, 1, 1, 1])
    search_cols[0].text_input("搜索关键词", key="log_analyzer_search_keyword", placeholder="支持普通文本或正则表达式")
    search_cols[1].checkbox("区分大小写", key="log_analyzer_search_case_sensitive")
    search_cols[2].checkbox("全词匹配", key="log_analyzer_search_whole_word")
    search_cols[3].checkbox("正则表达式", key="log_analyzer_search_use_regex")

    option_cols = st.columns([1.4, 1, 2.6])
    option_cols[0].radio("搜索范围", scope_options, horizontal=True, key="log_analyzer_search_scope")
    option_cols[1].slider("上下文行数", 0, 3, key="log_analyzer_search_context")
    option_cols[2].caption("支持在过滤结果内二次定位，适合先缩小范围再看上下文。")

    keyword = str(st.session_state.log_analyzer_search_keyword or "").strip()
    if not keyword:
        st.info("请输入搜索关键词后查看结果。")
        return

    if st.session_state.log_analyzer_search_scope == "过滤结果" and active_filters:
        target_lines = filtered_lines
        line_number_map = filtered_indexes
    else:
        target_lines = source_lines
        line_number_map = list(range(len(source_lines)))

    try:
        results = search_lines(
            target_lines,
            keyword,
            case_sensitive=bool(st.session_state.log_analyzer_search_case_sensitive),
            whole_word=bool(st.session_state.log_analyzer_search_whole_word),
            use_regex=bool(st.session_state.log_analyzer_search_use_regex),
            context_before=int(st.session_state.log_analyzer_search_context),
            context_after=int(st.session_state.log_analyzer_search_context),
            line_number_map=line_number_map,
            max_results=200,
        )
    except ValueError as exc:
        st.error(str(exc))
        return

    if not results:
        st.warning("未找到匹配结果。")
        return

    metric_cols = st.columns(4)
    metric_cols[0].metric("匹配行数", len(results))
    metric_cols[1].metric("唯一级别数", len({item["level"] for item in results}))
    metric_cols[2].metric("首个匹配位置", results[0]["position"])
    metric_cols[3].metric("搜索范围", st.session_state.log_analyzer_search_scope)

    result_df = pd.DataFrame(
        [
            {
                "原始行号": item["line_number"],
                "级别": item["level"],
                "时间": item["timestamp"],
                "匹配次数": item["match_count"],
                "位置": item["position"],
                "内容": item["line"],
            }
            for item in results
        ]
    )
    st.dataframe(result_df, use_container_width=True, height=360, hide_index=True)

    st.markdown("### 上下文预览")
    for item in results[:20]:
        with st.expander(f"第 {item['line_number']} 行 | {item['level']} | {item['position']}"):
            for context_item in item["context_before"]:
                st.code(f"{context_item['line_number']}: {context_item['line']}", language="text")
            st.code(f"{item['line_number']}: {item['line']}", language="text")
            for context_item in item["context_after"]:
                st.code(f"{context_item['line_number']}: {context_item['line']}", language="text")

    st.download_button(
        "导出搜索结果",
        data="\n".join(item["line"] for item in results),
        file_name=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
        use_container_width=True,
    )


def _render_counter_table(title: str, pairs: List[tuple[Any, Any]], first_col: str, second_col: str):
    st.markdown(f"### {title}")
    if not pairs:
        st.info("当前范围暂无相关数据。")
        return
    st.dataframe(
        pd.DataFrame([{first_col: key, second_col: value} for key, value in pairs]),
        use_container_width=True,
        hide_index=True,
    )


def _render_insights_tab(summary: Dict[str, Any], scope_label: str):
    st.caption(f"当前洞察范围: `{scope_label}`")
    top_n = int(st.session_state.log_analyzer_top_n)

    row1 = st.columns(2)
    with row1[0]:
        _render_counter_table("状态码 Top", summary["status_code_counts"][:top_n], "状态码", "次数")
    with row1[1]:
        _render_counter_table("异常 Top", summary["exception_counts"][:top_n], "异常类型", "次数")

    row2 = st.columns(2)
    with row2[0]:
        _render_counter_table("IP Top", summary["ip_counts"][:top_n], "IP", "次数")
    with row2[1]:
        _render_counter_table("接口路径 Top", summary["path_counts"][:top_n], "路径", "次数")

    st.markdown("### 重复日志 Top")
    if summary["duplicate_lines"]:
        st.dataframe(pd.DataFrame(summary["duplicate_lines"]), use_container_width=True, hide_index=True)
    else:
        st.success("当前范围没有重复日志。")

    if st.session_state.log_analyzer_show_charts and summary["timeline"]:
        timeline_df = pd.DataFrame(summary["timeline"])
        st.plotly_chart(
            px.line(timeline_df, x="bucket", y="count", markers=True, title="日志时间线"),
            use_container_width=True,
        )


def render_log_analysis_page():
    _ensure_defaults()
    show_doc("log_analyzer")

    st.sidebar.markdown("---")
    st.sidebar.markdown("### 展示设置")
    st.sidebar.checkbox("显示图表", key="log_analyzer_show_charts")
    st.sidebar.number_input("慢日志阈值(ms)", min_value=0.0, step=100.0, key="log_analyzer_slow_threshold")
    st.sidebar.slider("Top N", min_value=5, max_value=20, key="log_analyzer_top_n")

    tabs = st.tabs(["导入", "概览", "过滤", "搜索", "洞察"])

    with tabs[0]:
        _render_import_tab()

    source_lines = _get_source_lines()
    if not source_lines:
        for tab in tabs[1:]:
            with tab:
                st.info("请先导入日志数据。")
        return

    filtered_lines, _, _ = _apply_active_filters()
    active_scope_label = "过滤结果" if _has_active_filters() else "全部日志"
    summary_lines = filtered_lines if _has_active_filters() else source_lines
    summary = summarize_log_lines(
        summary_lines,
        slow_threshold_ms=float(st.session_state.log_analyzer_slow_threshold),
        top_n=int(st.session_state.log_analyzer_top_n),
    )

    with tabs[1]:
        _render_overview_tab(summary, active_scope_label)

    with tabs[2]:
        _render_filter_tab(source_lines)

    with tabs[3]:
        _render_search_tab(source_lines)

    with tabs[4]:
        _render_insights_tab(summary, active_scope_label)
