import html
import json
import os
import time
from urllib.parse import urlparse

import pandas as pd
import streamlit as st

from interface_auto_test import InterfaceAutoTestCore
from performance_test_tool import PerformanceTestTool


INTERFACE_FILE_TYPES = ["xlsx", "xls", "json", "har", "bru", "txt", "md", "yaml", "yml"]
RAW_FORMAT_MAP = {
    "自动检测": "auto",
    "JSON / Apifox / Postman / HAR / Insomnia": "json",
    "Swagger/OpenAPI": "swagger",
    "结构化文本": "text",
    "Bruno .bru": "bruno",
}
TREE_NODES = [
    ("test_plan", "📋 Test Plan"),
    ("thread_group", "├─ 🧵 Thread Group"),
    ("http_defaults", "│  ├─ 🌐 HTTP Request Defaults"),
    ("samplers", "│  ├─ 🔗 HTTP Request Samplers"),
    ("csv_data", "│  ├─ 🧾 CSV Data Set Config"),
    ("transaction", "│  ├─ 🎬 Transaction Controller"),
    ("assertions", "│  ├─ ✅ Response Assertion"),
    ("timer", "│  ├─ ⏱ Constant Timer"),
    ("listeners", "└─ 📊 Listeners"),
]
MENU_ITEMS = ["File", "Edit", "Search", "Run", "Options", "Tools", "Help"]
DEFAULT_STATE = {
    "api_perf_selected_node": "test_plan",
    "api_perf_active_menu": "Run",
    "api_perf_active_tree_action": "",
    "api_perf_active_example": "",
    "api_perf_active_panel_button": "",
    "api_perf_listener_tab": "Test Plan",
    "api_perf_result_detail_tab": "Sampler Result",
    "api_perf_tree_only_errors": False,
    "api_perf_tree_search": "",
    "api_perf_selected_sample_key": 0,
    "api_perf_plan_name": "API Performance Test Plan",
    "api_perf_plan_comment": "",
    "performance_sampler_indexes": [],
    "performance_users": 10,
    "performance_ramp_up": 5.0,
    "performance_loops": 1,
    "performance_duration": 0.0,
    "performance_start_delay": 0.0,
    "performance_base_url": "https://example.com",
    "performance_timeout": 30.0,
    "performance_verify_ssl": False,
    "performance_follow_redirects": True,
    "performance_keep_alive": True,
    "performance_csv_enabled": False,
    "performance_csv_source_mode": "直接粘贴",
    "performance_csv_text": "",
    "performance_csv_use_header": True,
    "performance_csv_variable_names": "user_id,token",
    "performance_csv_delimiter": ",",
    "performance_csv_quotechar": '"',
    "performance_csv_sharing_mode": "All Threads",
    "performance_csv_recycle": True,
    "performance_csv_stop_thread": False,
    "performance_transaction_enabled": False,
    "performance_transaction_name": "业务链路事务",
    "performance_transaction_stop_on_error": False,
    "performance_transaction_parent_sample": True,
    "performance_expected_status_mode": "使用文档状态码",
    "performance_custom_expected_status": 200,
    "performance_contains_text": "",
    "performance_max_response_ms": 0.0,
    "performance_think_time_ms": 0.0,
    "performance_random_jitter_ms": 0.0,
    "api_perf_protocol": "https",
    "api_perf_server_name": "example.com",
    "api_perf_port": "",
    "api_perf_base_path": "",
    "api_perf_http_fields_synced_from": "",
}
PANEL_META = {
    "test_plan": ("Test Plan", "管理测试计划名称、注释、接口文档导入和整体结构。"),
    "thread_group": ("Thread Group", "配置并发用户、Ramp-Up、循环次数和持续时长。"),
    "http_defaults": ("HTTP Request Defaults", "按 JMeter 风格配置协议、服务地址、端口和基础路径。"),
    "samplers": ("HTTP Request Samplers", "查看本次参与压测的 HTTP 请求顺序和详细参数。"),
    "csv_data": ("CSV Data Set Config", "使用 CSV 做参数化，模拟账号、订单号、Token 等不同测试数据。"),
    "transaction": ("Transaction Controller", "把多个 Sampler 串成一条业务链路，观察事务级耗时。"),
    "assertions": ("Response Assertion", "配置状态码、响应内容和最大响应时间断言。"),
    "timer": ("Constant Timer", "配置固定等待和随机抖动，模拟用户思考时间。"),
    "listeners": ("Listeners", "查看 Summary、Aggregate、Results Tree、Graph 和下载报告。"),
}


def _ensure_perf_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _sync_http_fields_from_base_url():
    base_url = st.session_state.get("performance_base_url", "")
    if not base_url:
        return
    if st.session_state.get("api_perf_http_fields_synced_from") == base_url:
        return

    parsed = urlparse(base_url)
    if not parsed.scheme or not parsed.netloc:
        return

    st.session_state.api_perf_protocol = parsed.scheme or "https"
    st.session_state.api_perf_server_name = parsed.hostname or ""
    st.session_state.api_perf_port = str(parsed.port or "")
    st.session_state.api_perf_base_path = parsed.path.strip("/")
    st.session_state.api_perf_http_fields_synced_from = base_url


def _compose_base_url_from_fields() -> str:
    protocol = str(st.session_state.get("api_perf_protocol", "https") or "https").strip()
    server_name = str(st.session_state.get("api_perf_server_name", "") or "").strip()
    port = str(st.session_state.get("api_perf_port", "") or "").strip()
    base_path = str(st.session_state.get("api_perf_base_path", "") or "").strip().strip("/")

    if not server_name:
        return str(st.session_state.get("performance_base_url", "") or "").strip()

    base_url = f"{protocol}://{server_name}"
    if port:
        base_url += f":{port}"
    if base_path:
        base_url += f"/{base_path}"
    return base_url


def _clear_results():
    st.session_state.pop("interface_perf_plan", None)
    st.session_state.pop("interface_perf_result", None)
    _reset_listener_view()


def _reset_listener_view():
    st.session_state.api_perf_listener_tab = "Test Plan"
    st.session_state.api_perf_result_detail_tab = "Sampler Result"
    st.session_state.api_perf_tree_only_errors = False
    st.session_state.api_perf_tree_search = ""
    st.session_state.performance_results_tree_index = 0
    st.session_state.api_perf_selected_sample_key = 0


def _open_listener_view(tab_name: str):
    st.session_state.api_perf_listener_tab = tab_name
    st.session_state.api_perf_selected_node = "listeners"
    if tab_name != "View Results Tree":
        st.session_state.api_perf_result_detail_tab = "Sampler Result"
        st.session_state.performance_results_tree_index = 0
        st.session_state.api_perf_selected_sample_key = 0


def _open_results_tree(detail_tab: str = "Sampler Result", only_errors: bool = False, search_text: str = ""):
    st.session_state.api_perf_listener_tab = "View Results Tree"
    st.session_state.api_perf_selected_node = "listeners"
    st.session_state.api_perf_result_detail_tab = detail_tab
    st.session_state.api_perf_tree_only_errors = only_errors
    st.session_state.api_perf_tree_search = search_text
    st.session_state.performance_results_tree_index = 0
    st.session_state.api_perf_selected_sample_key = 0


def _get_thread_group_state_key(thread_name: str) -> str:
    safe_name = "".join(ch if ch.isalnum() else "_" for ch in thread_name)[:80] or "thread"
    return f"api_perf_tree_group_open_{safe_name}"


def _set_thread_groups_expanded(thread_names, expanded: bool):
    for thread_name in thread_names:
        st.session_state[_get_thread_group_state_key(thread_name)] = expanded


def _reset_configuration():
    keep_interfaces = st.session_state.get("interface_perf_interfaces", [])
    keep_source_name = st.session_state.get("interface_perf_source_name", "")
    keep_upload = st.session_state.get("interface_perf_source_upload")
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value
    _clear_results()
    st.session_state.interface_perf_interfaces = keep_interfaces
    st.session_state.interface_perf_source_name = keep_source_name
    if keep_upload is not None:
        st.session_state.interface_perf_source_upload = keep_upload
    if keep_interfaces:
        st.session_state.performance_sampler_indexes = [0]
    st.session_state.api_perf_selected_node = "test_plan"


def _render_styles():
    st.markdown(
        """
        <style>
        .main .block-container {
            background: #efefef;
            border: 1px solid #a0a0a0;
            border-radius: 0;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #c0c0c0;
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        .jmeter-caption {
            background: #d4d0c8;
            border: 1px solid #808080;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #7f7f7f;
            padding: 10px 14px;
            color: #222;
            margin-bottom: 12px;
        }
        .jmeter-menubar {
            display: flex;
            gap: 2px;
            background: #d4d0c8;
            border: 1px solid #808080;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #7f7f7f;
            padding: 4px 6px;
            margin-bottom: 6px;
        }
        .jmeter-menuitem {
            padding: 3px 10px;
            border: 1px solid transparent;
            color: #111;
            font-size: 13px;
        }
        .jmeter-menuitem.active {
            border-color: #7f7f7f;
            box-shadow: inset 1px 1px 0 #ffffff;
            background: #efefef;
        }
        .jmeter-toolbar-icons {
            display: flex;
            gap: 4px;
            align-items: center;
            background: #dadada;
            border: 1px solid #808080;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #7f7f7f;
            padding: 4px 6px;
            margin-bottom: 6px;
        }
        .jmeter-toolbar-icons .hint {
            margin-left: auto;
            font-size: 12px;
            color: #333;
        }
        .jmeter-tree-tip {
            background: #ece9d8;
            border: 1px solid #a0a0a0;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #c0c0c0;
            padding: 10px 12px;
            font-size: 13px;
            color: #333;
            margin-bottom: 10px;
        }
        .jmeter-toolbar {
            background: #d4d0c8;
            border: 1px solid #808080;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #7f7f7f;
            padding: 10px 14px;
            margin: 8px 0 14px 0;
        }
        .jmeter-panel-title {
            font-weight: 700;
            color: #1f1f1f;
            margin-bottom: 4px;
        }
        .jmeter-section {
            background: #f3f3f3;
            border: 1px solid #a0a0a0;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #c0c0c0;
            padding: 10px 12px;
            margin-bottom: 10px;
        }
        .jmeter-section h3 {
            margin: 0 0 4px 0;
            font-size: 18px;
        }
        .jmeter-node-actions {
            background: #ece9d8;
            border: 1px solid #a0a0a0;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #c0c0c0;
            padding: 8px 10px;
            margin-bottom: 10px;
        }
        .jmeter-guide-banner {
            background: linear-gradient(180deg, #f7f2d7 0%, #ece5be 100%);
            border: 1px solid #a49863;
            box-shadow: inset 1px 1px 0 #fffbe8, inset -1px -1px 0 #c0b37a;
            padding: 10px 12px;
            margin: 8px 0 10px 0;
            color: #3f3a22;
        }
        .jmeter-guide-subtitle {
            font-weight: 700;
            margin-bottom: 4px;
        }
        .jmeter-guide-hint {
            background: #eef4ff;
            border: 1px solid #8aa7d3;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #a7bddd;
            padding: 8px 10px;
            margin: 8px 0;
            color: #274266;
        }
        .jmeter-dock {
            background: #e6e6e6;
            border: 1px solid #8f8f8f;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #c0c0c0;
            padding: 8px 12px;
            margin-top: 12px;
        }
        .jmeter-splitter-horizontal {
            background: linear-gradient(180deg, #dedede 0%, #f9f9f9 50%, #c4c4c4 100%);
            border: 1px solid #8b8b8b;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #767676;
            color: #303030;
            font-size: 12px;
            padding: 2px 10px;
            margin: 8px 0;
            text-transform: uppercase;
            letter-spacing: 0.4px;
        }
        .jmeter-splitter-vertical {
            min-height: 760px;
            height: 100%;
            border: 1px solid #8b8b8b;
            background: linear-gradient(90deg, #c4c4c4 0%, #f8f8f8 50%, #b5b5b5 100%);
            box-shadow: inset 1px 0 0 #ffffff, inset -1px 0 0 #767676;
            position: relative;
        }
        .jmeter-splitter-vertical::after {
            content: ":::";
            position: absolute;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(90deg);
            color: #555;
            font-weight: 700;
            letter-spacing: 2px;
        }
        .jmeter-mini-toolbar {
            background: #d9d9d9;
            border: 1px solid #8f8f8f;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #b0b0b0;
            padding: 8px 10px;
            margin-bottom: 10px;
            color: #242424;
            font-size: 13px;
        }
        .jmeter-toolbar-note {
            color: #4a4a4a;
            font-size: 12px;
            margin-top: 4px;
        }
        .jmeter-sample-browser {
            background: #fbfbfb;
            border: 1px solid #9d9d9d;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #d4d4d4;
            padding: 8px 10px;
            margin-bottom: 8px;
        }
        .jmeter-field-card {
            background: #fafafa;
            border: 1px solid #a6a6a6;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #d5d5d5;
            padding: 8px 10px;
            margin-bottom: 8px;
        }
        .jmeter-report-toolbar {
            background: #efefef;
            border: 1px solid #9c9c9c;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #c8c8c8;
            padding: 8px 10px;
            margin-bottom: 8px;
        }
        .jmeter-report-status {
            background: #f8f8f8;
            border: 1px solid #b4b4b4;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #dcdcdc;
            padding: 8px 10px;
            margin-bottom: 8px;
            color: #3b3b3b;
            font-size: 12px;
        }
        .jmeter-sample-tree-shell {
            background: #fbfbfb;
            border: 1px solid #9d9d9d;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #d8d8d8;
            padding: 8px 10px;
            margin-bottom: 8px;
        }
        .jmeter-sample-tree-meta {
            color: #4b5563;
            font-size: 12px;
            margin: 4px 0 8px 0;
        }
        .jmeter-sample-group {
            background: #edf2f7;
            border: 1px solid #b8c2cc;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #d4dce3;
            color: #1f2937;
            font-weight: 700;
            font-size: 12px;
            padding: 6px 8px;
            margin: 8px 0 6px 0;
        }
        .jmeter-sample-subnote {
            color: #4b5563;
            font-size: 12px;
            margin: 2px 0 6px 18px;
        }
        .jmeter-assertion-tree {
            background: #ffffff;
            border: 1px solid #9d9d9d;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #d5d5d5;
            padding: 8px 10px;
        }
        .jmeter-assertion-row {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 5px 6px;
            border-bottom: 1px solid #ececec;
            font-size: 13px;
        }
        .jmeter-assertion-row:last-child {
            border-bottom: none;
        }
        .jmeter-assertion-row.pass .icon {
            color: #1c6a27;
            font-weight: 700;
        }
        .jmeter-assertion-row.fail .icon {
            color: #a62525;
            font-weight: 700;
        }
        .jmeter-assertion-row .label {
            min-width: 150px;
            font-weight: 700;
            color: #232323;
        }
        .jmeter-assertion-row .detail {
            color: #4e4e4e;
        }
        .jmeter-statusbar {
            display: flex;
            justify-content: space-between;
            gap: 12px;
            background: #d4d0c8;
            border: 1px solid #808080;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #7f7f7f;
            padding: 4px 8px;
            margin-top: 8px;
            font-size: 12px;
            color: #222;
        }
        .stButton > button, .stDownloadButton > button {
            border-radius: 0 !important;
            border: 1px solid #808080 !important;
            background: #d4d0c8 !important;
            color: #111 !important;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #7f7f7f !important;
        }
        .stButton > button[kind="primary"] {
            background: linear-gradient(180deg, #d9eaff 0%, #a9c8ef 100%) !important;
            border: 1px solid #5f84b3 !important;
            color: #10233f !important;
            box-shadow: inset 1px 1px 0 #ffffff, inset -1px -1px 0 #5f84b3 !important;
        }
        .stButton > button[kind="primary"]:active {
            background: linear-gradient(180deg, #a9c8ef 0%, #d9eaff 100%) !important;
            box-shadow: inset -1px -1px 0 #ffffff, inset 1px 1px 0 #4a6f99 !important;
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 2px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 0 !important;
            background: #d4d0c8 !important;
            border: 1px solid #9f9f9f !important;
            color: #222 !important;
            padding: 6px 10px !important;
        }
        .stTabs [aria-selected="true"] {
            background: #f8f8f8 !important;
            box-shadow: inset 1px 1px 0 #ffffff !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _load_raw_example(prefix: str, raw_format_label: str, content: str):
    st.session_state[f"{prefix}_input_mode"] = "原始文本"
    st.session_state[f"{prefix}_raw_format"] = raw_format_label
    st.session_state[f"{prefix}_raw_content"] = content


def _render_horizontal_splitter(label: str):
    st.markdown(f'<div class="jmeter-splitter-horizontal">{html.escape(label)}</div>', unsafe_allow_html=True)


def _render_vertical_splitter():
    st.markdown('<div class="jmeter-splitter-vertical"></div>', unsafe_allow_html=True)


def _render_button_tab_bar(options, state_key: str, key_prefix: str, title: str, subtitle: str):
    if not options:
        return ""

    active_value = st.session_state.get(state_key, options[0])
    if active_value not in options:
        active_value = options[0]
        st.session_state[state_key] = active_value

    st.markdown(
        f'<div class="jmeter-mini-toolbar"><div class="jmeter-panel-title">{html.escape(title)}</div><div class="jmeter-toolbar-note">{html.escape(subtitle)}</div></div>',
        unsafe_allow_html=True,
    )
    row_size = 4
    for offset in range(0, len(options), row_size):
        row = options[offset: offset + row_size]
        columns = st.columns(len(row))
        for column, option in zip(columns, row):
            with column:
                if st.button(
                    option,
                    key=f"{key_prefix}_{offset}_{option}",
                    use_container_width=True,
                    type="primary" if active_value == option else "secondary",
                ):
                    st.session_state[state_key] = option
                    st.rerun()
    return st.session_state.get(state_key, active_value)


def _filter_report_dataframe(df: pd.DataFrame, query: str) -> pd.DataFrame:
    if df.empty or not query:
        return df

    keyword = query.strip().lower()
    if not keyword:
        return df

    mask = df.apply(lambda row: any(keyword in str(value).lower() for value in row), axis=1)
    return df[mask].reset_index(drop=True)


def _render_report_table_workbench(
    report_key: str,
    title: str,
    df: pd.DataFrame,
    file_name: str,
    empty_hint: str = "当前没有可展示的数据",
    default_columns=None,
    default_sort=None,
) -> pd.DataFrame:
    search_key = f"{report_key}_table_search"
    display_key = f"{report_key}_display_mode"
    columns_key = f"{report_key}_visible_columns"
    sort_key = f"{report_key}_sort_column"
    sort_order_key = f"{report_key}_sort_order"
    second_sort_key = f"{report_key}_second_sort_column"
    second_sort_order_key = f"{report_key}_second_sort_order"
    pin_columns_key = f"{report_key}_pin_columns"
    page_size_key = f"{report_key}_page_size"
    page_number_key = f"{report_key}_page_number"

    st.markdown(
        f'<div class="jmeter-report-toolbar"><div class="jmeter-panel-title">{html.escape(title)}</div><div class="jmeter-toolbar-note">支持关键字筛选、列方案切换、自定义列、排序和导出当前表数据。</div></div>',
        unsafe_allow_html=True,
    )
    ctrl_col1, ctrl_col2, ctrl_col3, ctrl_col4 = st.columns([2.2, 1.1, 2.2, 1])
    with ctrl_col1:
        query = st.text_input(
            "Filter",
            key=search_key,
            placeholder="按 Label、状态码、错误信息等关键字筛选",
        )
    with ctrl_col2:
        display_mode = st.selectbox(
            "列方案",
            ["核心列", "全部列", "自定义"],
            key=display_key,
        )
    all_columns = list(df.columns)
    preferred_columns = [col for col in (default_columns or all_columns[: min(6, len(all_columns))]) if col in all_columns]
    if not preferred_columns:
        preferred_columns = all_columns

    if page_size_key not in st.session_state:
        st.session_state[page_size_key] = 20
    if page_number_key not in st.session_state:
        st.session_state[page_number_key] = 1

    stored_columns = st.session_state.get(columns_key, preferred_columns)
    stored_columns = [col for col in stored_columns if col in all_columns]
    if not stored_columns:
        stored_columns = preferred_columns
        st.session_state[columns_key] = stored_columns

    with ctrl_col3:
        if display_mode == "核心列":
            visible_columns = preferred_columns
            st.text_input(
                "显示列",
                value=", ".join(preferred_columns),
                disabled=True,
                key=f"{report_key}_preferred_columns_preview",
            )
        elif display_mode == "全部列":
            visible_columns = all_columns
            st.text_input(
                "显示列",
                value=", ".join(all_columns),
                disabled=True,
                key=f"{report_key}_all_columns_preview",
            )
        else:
            visible_columns = st.multiselect(
                "显示列",
                all_columns,
                default=stored_columns,
                key=columns_key,
            )
            if not visible_columns:
                visible_columns = preferred_columns
                st.session_state[columns_key] = preferred_columns
    with ctrl_col4:
        if st.button("重置视图", key=f"{report_key}_reset_view", use_container_width=True):
            st.session_state[search_key] = ""
            st.session_state[display_key] = "核心列"
            st.session_state[columns_key] = preferred_columns
            st.session_state[sort_key] = default_sort if default_sort in all_columns else "默认顺序"
            st.session_state[sort_order_key] = "降序" if default_sort else "升序"
            st.session_state[second_sort_key] = "无"
            st.session_state[second_sort_order_key] = "升序"
            st.session_state[pin_columns_key] = preferred_columns[: min(2, len(preferred_columns))]
            st.session_state[page_size_key] = 20
            st.session_state[page_number_key] = 1
            st.rerun()
    filtered_df = _filter_report_dataframe(df, query)

    preset_items = []
    if "Average" in all_columns:
        preset_items.append(("平均耗时降序", "Average", "降序"))
    if "Error %" in all_columns:
        preset_items.append(("错误率降序", "Error %", "降序"))
    if "Throughput" in all_columns:
        preset_items.append(("吞吐降序", "Throughput", "降序"))
    if "Label" in all_columns:
        preset_items.append(("Label升序", "Label", "升序"))

    if preset_items:
        preset_cols = st.columns(len(preset_items) + 1)
        for idx, (label, preset_column, preset_order) in enumerate(preset_items):
            with preset_cols[idx]:
                if st.button(label, key=f"{report_key}_preset_{idx}", use_container_width=True):
                    st.session_state[sort_key] = preset_column
                    st.session_state[sort_order_key] = preset_order
                    st.session_state[second_sort_key] = "无"
                    st.session_state[second_sort_order_key] = "升序"
                    st.session_state[page_number_key] = 1
                    st.rerun()
        with preset_cols[-1]:
            if st.button("恢复默认排序", key=f"{report_key}_preset_default", use_container_width=True):
                st.session_state[sort_key] = default_sort if default_sort in all_columns else "默认顺序"
                st.session_state[sort_order_key] = "降序" if default_sort else "升序"
                st.session_state[second_sort_key] = "无"
                st.session_state[second_sort_order_key] = "升序"
                st.session_state[page_number_key] = 1
                st.rerun()

    sort_col1, sort_col2, sort_col3, sort_col4, sort_col5 = st.columns([1.35, 0.9, 1.35, 0.9, 2.2])
    with sort_col1:
        sort_column = st.selectbox(
            "排序列",
            ["默认顺序"] + all_columns,
            index=(["默认顺序"] + all_columns).index(default_sort) if default_sort in all_columns else 0,
            key=sort_key,
        )
    with sort_col2:
        sort_order = st.selectbox(
            "顺序",
            ["升序", "降序"],
            index=1 if default_sort else 0,
            key=sort_order_key,
        )
    with sort_col3:
        second_sort_column = st.selectbox(
            "次排序列",
            ["无"] + all_columns,
            key=second_sort_key,
        )
    with sort_col4:
        second_sort_order = st.selectbox(
            "次顺序",
            ["升序", "降序"],
            key=second_sort_order_key,
        )
    with sort_col5:
        pinned_columns = st.multiselect(
            "前置列",
            visible_columns,
            default=[col for col in st.session_state.get(pin_columns_key, preferred_columns[: min(2, len(preferred_columns))]) if col in visible_columns],
            key=pin_columns_key,
        )

    prepared_df = filtered_df
    sort_columns = []
    sort_orders = []
    if sort_column != "默认顺序" and sort_column in prepared_df.columns:
        sort_columns.append(sort_column)
        sort_orders.append(sort_order == "升序")
    if second_sort_column != "无" and second_sort_column in prepared_df.columns and second_sort_column not in sort_columns:
        sort_columns.append(second_sort_column)
        sort_orders.append(second_sort_order == "升序")
    if sort_columns:
        prepared_df = prepared_df.sort_values(
            by=sort_columns,
            ascending=sort_orders,
            kind="mergesort",
            na_position="last",
        ).reset_index(drop=True)

    download_col1, download_col2 = st.columns([4.4, 1])
    with download_col2:
        st.download_button(
            label="保存表数据",
            data=prepared_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
            file_name=file_name,
            mime="text/csv",
            use_container_width=True,
            key=f"{report_key}_download_filtered_csv",
            disabled=prepared_df.empty,
        )

    if prepared_df.empty:
        st.info(empty_hint)
        return filtered_df

    filtered_df = prepared_df

    visible_columns = [col for col in visible_columns if col in filtered_df.columns] or list(filtered_df.columns)
    pinned_columns = [col for col in pinned_columns if col in visible_columns]
    ordered_columns = pinned_columns + [col for col in visible_columns if col not in pinned_columns]
    visible_df = filtered_df[ordered_columns]

    page_ctrl1, page_ctrl2, page_ctrl3 = st.columns([1.2, 1.2, 2.6])
    with page_ctrl1:
        page_size = st.selectbox(
            "每页行数",
            [10, 20, 50, 100],
            index=[10, 20, 50, 100].index(int(st.session_state.get(page_size_key, 20))),
            key=page_size_key,
        )
    total_pages = max((len(visible_df) - 1) // int(page_size) + 1, 1)
    current_page_value = int(st.session_state.get(page_number_key, 1) or 1)
    if current_page_value > total_pages:
        st.session_state[page_number_key] = total_pages
        current_page_value = total_pages
    elif current_page_value < 1:
        st.session_state[page_number_key] = 1
        current_page_value = 1
    with page_ctrl2:
        page_number = st.number_input(
            "页码",
            min_value=1,
            max_value=total_pages,
            step=1,
            key=page_number_key,
        )
    with page_ctrl3:
        st.text_input(
            "分页说明",
            value=f"共 {len(visible_df)} 行，当前第 {int(page_number)} / {total_pages} 页",
            disabled=True,
            key=f"{report_key}_page_summary",
        )

    nav_col1, nav_col2, nav_col3, nav_col4 = st.columns(4)
    with nav_col1:
        if st.button("首页", key=f"{report_key}_page_first", use_container_width=True, disabled=int(page_number) <= 1):
            st.session_state[page_number_key] = 1
            st.rerun()
    with nav_col2:
        if st.button("上一页", key=f"{report_key}_page_prev", use_container_width=True, disabled=int(page_number) <= 1):
            st.session_state[page_number_key] = max(int(page_number) - 1, 1)
            st.rerun()
    with nav_col3:
        if st.button("下一页", key=f"{report_key}_page_next", use_container_width=True, disabled=int(page_number) >= total_pages):
            st.session_state[page_number_key] = min(int(page_number) + 1, total_pages)
            st.rerun()
    with nav_col4:
        if st.button("末页", key=f"{report_key}_page_last", use_container_width=True, disabled=int(page_number) >= total_pages):
            st.session_state[page_number_key] = total_pages
            st.rerun()

    start_index = (int(page_number) - 1) * int(page_size)
    end_index = start_index + int(page_size)
    paged_df = visible_df.iloc[start_index:end_index].reset_index(drop=True)

    st.markdown(
        f'<div class="jmeter-report-status">Rows: {len(filtered_df)} | Columns: {len(visible_df.columns)} | Display: {html.escape(display_mode)} | Sort: {html.escape(", ".join(sort_columns) if sort_columns else "默认顺序")} | Page: {int(page_number)}/{total_pages}</div>',
        unsafe_allow_html=True,
    )
    st.dataframe(paged_df, use_container_width=True)
    return filtered_df


def _render_upload_template_section(prefix: str, parser: InterfaceAutoTestCore):
    st.markdown(
        '<div class="jmeter-guide-banner"><div class="jmeter-guide-subtitle">上传模版下载</div>推荐先下载模版，按字段填好后再上传，最省理解成本。</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="jmeter-guide-hint">推荐优先使用 `Excel模版` 或 `OpenAPI JSON`。如果只是想快速试一把，也可以直接下载 `文本模版` 或 `curl示例`。</div>',
        unsafe_allow_html=True,
    )

    row1_col1, row1_col2, row1_col3, row1_col4 = st.columns(4)
    with row1_col1:
        st.caption("最适合手工整理")
        st.download_button(
            label="📥 Excel模版",
            data=parser.build_excel_template_bytes(),
            file_name="api-performance-template.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
            key=f"{prefix}_download_excel_template",
        )
    with row1_col2:
        st.caption("适合结构化导入")
        st.download_button(
            label="📥 JSON模版",
            data=parser.build_json_template(),
            file_name="api-performance-template.json",
            mime="application/json",
            use_container_width=True,
            key=f"{prefix}_download_json_template",
        )
    with row1_col3:
        st.caption("标准接口定义")
        st.download_button(
            label="📥 OpenAPI JSON",
            data=parser.build_openapi_template(),
            file_name="openapi-performance-template.json",
            mime="application/json",
            use_container_width=True,
            key=f"{prefix}_download_openapi_template",
        )
    with row1_col4:
        st.caption("YAML 风格项目")
        st.download_button(
            label="📥 OpenAPI YAML",
            data=parser.build_openapi_yaml_template(),
            file_name="openapi-performance-template.yaml",
            mime="text/yaml",
            use_container_width=True,
            key=f"{prefix}_download_openapi_yaml_template",
        )

    row2_col1, row2_col2, row2_col3 = st.columns(3)
    with row2_col1:
        st.caption("适合直接阅读")
        st.download_button(
            label="📥 文本模版",
            data=parser.build_text_template(),
            file_name="api-performance-template.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"{prefix}_download_text_template",
        )
    with row2_col2:
        st.caption("联调常见格式")
        st.download_button(
            label="📥 curl示例",
            data=parser.build_curl_template(),
            file_name="api-performance-curl-example.txt",
            mime="text/plain",
            use_container_width=True,
            key=f"{prefix}_download_curl_template",
        )
    with row2_col3:
        st.caption("现成集合格式")
        st.download_button(
            label="📥 Postman模版",
            data=parser.build_postman_template(),
            file_name="api-performance-postman-template.json",
            mime="application/json",
            use_container_width=True,
            key=f"{prefix}_download_postman_template",
        )


def _render_raw_example_section(prefix: str, parser: InterfaceAutoTestCore):
    st.markdown(
        '<div class="jmeter-guide-banner"><div class="jmeter-guide-subtitle">原始文本示例</div>支持结构化文本、OpenAPI、curl 等格式。先点一个示例看结构，再一键加载到编辑区。</div>',
        unsafe_allow_html=True,
    )
    examples = [
        ("text", "结构化文本示例", "结构化文本", parser.build_text_template(), "text", "最容易上手，适合人工编辑"),
        ("curl", "curl 示例", "自动检测", parser.build_curl_template(), "bash", "适合直接从接口调试命令复制"),
        ("openapi", "OpenAPI 示例", "Swagger/OpenAPI", parser.build_openapi_template(), "json", "适合标准接口文档导入"),
    ]
    active_example = st.session_state.get("api_perf_active_example", "")
    btn_cols = st.columns(3)
    for col, (example_key, title, _, _, _, desc) in zip(btn_cols, examples):
        with col:
            if st.button(
                title,
                key=f"{prefix}_pick_example_{example_key}",
                use_container_width=True,
                type="primary" if active_example == example_key else "secondary",
            ):
                st.session_state.api_perf_active_example = example_key
                st.rerun()
            st.caption(desc)

    selected = next((item for item in examples if item[0] == active_example), examples[0])
    if not active_example:
        st.session_state.api_perf_active_example = selected[0]
    _, title, raw_format_label, content, language, desc = selected
    st.markdown(
        f'<div class="jmeter-guide-hint"><strong>{title}</strong>：{desc}。点击下面按钮会自动填充到原始文本输入区，并切换到 `{raw_format_label}` 解析模式。</div>',
        unsafe_allow_html=True,
    )
    st.code(content, language=language)
    if st.button(
        f"⬇️ 加载 {title} 到编辑区",
        key=f"{prefix}_use_example_{selected[0]}",
        use_container_width=True,
        type="primary",
    ):
        _load_raw_example(prefix, raw_format_label, content)
        st.rerun()


def _render_source_guides(prefix: str, parser: InterfaceAutoTestCore, input_mode: str):
    st.markdown("#### 使用辅助")
    if input_mode == "文件上传":
        _render_upload_template_section(prefix, parser)
        return

    _render_raw_example_section(prefix, parser)


def _render_interface_source_panel(prefix: str, title: str, parser: InterfaceAutoTestCore, height: int = 220):
    st.markdown(f"#### {title}")
    input_mode = st.radio(
        "导入方式",
        ["文件上传", "原始文本"],
        horizontal=True,
        key=f"{prefix}_input_mode",
    )
    source_data = {"mode": input_mode}
    if input_mode == "文件上传":
        source_data["uploaded_file"] = st.file_uploader(
            "选择接口文档",
            type=INTERFACE_FILE_TYPES,
            key=f"{prefix}_upload",
            help="支持 Excel、JSON、Swagger/OpenAPI、Postman、HAR、Bruno、Insomnia、文本等格式",
        )
    else:
        source_data["raw_format"] = st.selectbox(
            "文本格式",
            list(RAW_FORMAT_MAP.keys()),
            key=f"{prefix}_raw_format",
        )
        source_data["raw_content"] = st.text_area(
            "粘贴接口定义",
            height=height,
            placeholder="可粘贴 JSON、OpenAPI 文本、结构化文本或 curl 命令",
            key=f"{prefix}_raw_content",
        )
    _render_source_guides(prefix, parser, input_mode)
    return source_data


def _render_menu_bar():
    active_menu = st.session_state.get("api_perf_active_menu", "Run")
    menu_html = "".join(
        [
            f'<div class="jmeter-menuitem{" active" if item == active_menu else ""}">{item}</div>'
            for item in MENU_ITEMS
        ]
    )
    st.markdown(f'<div class="jmeter-menubar">{menu_html}</div>', unsafe_allow_html=True)


def _parse_interface_source(source_data, prefix: str, parser: InterfaceAutoTestCore):
    if source_data.get("mode") == "文件上传":
        uploaded_file = source_data.get("uploaded_file")
        if uploaded_file is None:
            raise ValueError("请先上传接口文档")
        temp_filename = f"{prefix}_{int(time.time() * 1000)}_{uploaded_file.name}"
        file_path = os.path.join(parser.upload_dir, temp_filename)
        with open(file_path, "wb") as file:
            file.write(uploaded_file.getbuffer())
        interfaces = parser.parse_document(file_path)
        return interfaces, uploaded_file.name

    raw_content = source_data.get("raw_content", "")
    if not raw_content.strip():
        raise ValueError("请输入原始接口定义")

    raw_format = source_data.get("raw_format", "自动检测")
    interfaces = parser.parse_content(
        raw_content,
        source_type=RAW_FORMAT_MAP[raw_format],
        source_name=f"{prefix}-inline",
    )
    return interfaces, f"{raw_format} 文本"


def _build_interface_preview_rows(interfaces, limit: int = 10):
    rows = []
    for item in interfaces[:limit]:
        rows.append(
            {
                "接口名称": item.get("name", "未命名接口"),
                "请求方法": item.get("method", "GET"),
                "接口路径": item.get("path", ""),
                "状态码": item.get("expected_status", 200),
                "请求格式": item.get("request_format", "auto"),
            }
        )
    return rows


def _get_sampler_label(interfaces, idx: int) -> str:
    item = interfaces[idx]
    return (
        f"{idx + 1}. {item.get('method', 'GET')} "
        f"{item.get('path', '')} | {item.get('name', '未命名接口')}"
    )


def _build_plan_from_state(interfaces, performance_tool: PerformanceTestTool):
    expected_status_mode_map = {
        "使用文档状态码": "document",
        "自定义状态码": "custom",
        "不校验状态码": "none",
    }
    sharing_mode_map = {
        "All Threads": "all_threads",
        "Current Thread": "current_thread",
    }

    selected_sampler_indexes = st.session_state.get("performance_sampler_indexes") or []
    if not selected_sampler_indexes:
        raise ValueError("请至少选择一个 HTTP Sampler")

    csv_source_name = "inline-csv"
    perf_csv_file = st.session_state.get("performance_csv_upload")
    perf_csv_text = st.session_state.get("performance_csv_text", "")
    if perf_csv_file is not None:
        perf_csv_text = perf_csv_file.getvalue().decode("utf-8-sig", errors="ignore")
        csv_source_name = perf_csv_file.name

    base_url = _compose_base_url_from_fields()
    st.session_state.performance_base_url = base_url
    st.session_state.api_perf_http_fields_synced_from = base_url

    plan = performance_tool.build_test_plan(
        interfaces=interfaces,
        base_url=base_url,
        selected_indexes=selected_sampler_indexes,
        thread_group={
            "users": st.session_state.get("performance_users", 10),
            "ramp_up_seconds": st.session_state.get("performance_ramp_up", 5.0),
            "loop_count": st.session_state.get("performance_loops", 1),
            "duration_seconds": st.session_state.get("performance_duration", 0.0),
            "start_delay_seconds": st.session_state.get("performance_start_delay", 0.0),
        },
        request_defaults={
            "timeout_seconds": st.session_state.get("performance_timeout", 30.0),
            "verify_ssl": st.session_state.get("performance_verify_ssl", False),
            "follow_redirects": st.session_state.get("performance_follow_redirects", True),
            "keep_alive": st.session_state.get("performance_keep_alive", True),
        },
        assertions={
            "expected_status_mode": expected_status_mode_map[st.session_state.get("performance_expected_status_mode", "使用文档状态码")],
            "custom_expected_status": st.session_state.get("performance_custom_expected_status", 200),
            "contains_text": st.session_state.get("performance_contains_text", ""),
            "max_response_ms": st.session_state.get("performance_max_response_ms", 0.0),
        },
        timer_config={
            "think_time_ms": st.session_state.get("performance_think_time_ms", 0.0),
            "random_jitter_ms": st.session_state.get("performance_random_jitter_ms", 0.0),
        },
        csv_data_set={
            "enabled": st.session_state.get("performance_csv_enabled", False),
            "csv_text": perf_csv_text,
            "source_name": csv_source_name,
            "use_header_row": st.session_state.get("performance_csv_use_header", True),
            "variable_names_text": st.session_state.get("performance_csv_variable_names", ""),
            "delimiter": st.session_state.get("performance_csv_delimiter", ","),
            "quotechar": st.session_state.get("performance_csv_quotechar", '"'),
            "sharing_mode": sharing_mode_map[st.session_state.get("performance_csv_sharing_mode", "All Threads")],
            "recycle_on_eof": st.session_state.get("performance_csv_recycle", True),
            "stop_thread_on_eof": st.session_state.get("performance_csv_stop_thread", False),
        },
        transaction_controller={
            "enabled": st.session_state.get("performance_transaction_enabled", False),
            "name": st.session_state.get("performance_transaction_name", "业务链路事务"),
            "stop_on_error": st.session_state.get("performance_transaction_stop_on_error", False),
            "generate_parent_sample": st.session_state.get("performance_transaction_parent_sample", True),
        },
    )
    plan["ui_metadata"] = {
        "plan_name": st.session_state.get("api_perf_plan_name", "API Performance Test Plan"),
        "comment": st.session_state.get("api_perf_plan_comment", ""),
        "selected_node": st.session_state.get("api_perf_selected_node", "test_plan"),
    }
    return plan


def _build_jmeter_summary_row(perf_result):
    summary = perf_result.get("summary", {})
    total_requests = int(summary.get("total_requests", 0) or 0)
    success_requests = int(summary.get("success_requests", 0) or 0)
    failed_requests = max(total_requests - success_requests, 0)
    return {
        "Label": "TOTAL",
        "# Samples": total_requests,
        "Average": round(float(summary.get("avg_ms", 0.0) or 0.0), 2),
        "Median": round(float(summary.get("p50_ms", 0.0) or 0.0), 2),
        "90% Line": round(float(summary.get("p90_ms", 0.0) or 0.0), 2),
        "95% Line": round(float(summary.get("p95_ms", 0.0) or 0.0), 2),
        "99% Line": round(float(summary.get("p99_ms", 0.0) or 0.0), 2),
        "Min": round(float(summary.get("min_ms", 0.0) or 0.0), 2),
        "Max": round(float(summary.get("max_ms", 0.0) or 0.0), 2),
        "Error %": round((failed_requests / total_requests * 100) if total_requests else 0.0, 2),
        "Throughput": round(float(summary.get("throughput_rps", 0.0) or 0.0), 2),
    }


def _build_jmeter_aggregate_rows(perf_result):
    rows = []
    for item in perf_result.get("per_sampler", []):
        requests = int(item.get("requests", 0) or 0)
        failed_requests = int(item.get("failed_requests", 0) or 0)
        rows.append(
            {
                "Label": item.get("sampler_name", ""),
                "# Samples": requests,
                "Average": round(float(item.get("avg_ms", 0.0) or 0.0), 2),
                "90% Line": round(float(item.get("p90_ms", 0.0) or 0.0), 2),
                "95% Line": round(float(item.get("p95_ms", 0.0) or 0.0), 2),
                "Min": round(float(item.get("min_ms", 0.0) or 0.0), 2),
                "Max": round(float(item.get("max_ms", 0.0) or 0.0), 2),
                "Error %": round((failed_requests / requests * 100) if requests else 0.0, 2),
                "Throughput": round(float(item.get("throughput_rps", 0.0) or 0.0), 2),
            }
        )
    return rows


def _build_results_tree_rows(perf_result):
    rows = []
    for index, sample in enumerate(perf_result.get("samples", []), start=1):
        success = bool(sample.get("success"))
        rows.append(
            {
                "sample_index": index - 1,
                "display": f"{index}. {sample.get('sampler_label', '')} [{'OK' if success else 'FAIL'}]",
                "Label": sample.get("sampler_label", ""),
                "Sample Time(ms)": sample.get("elapsed_ms", 0.0),
                "Status": "Success" if success else "Failure",
                "Response Code": sample.get("status_code", 0),
                "Response Message": sample.get("response_message", ""),
                "Thread Name": sample.get("thread_name", ""),
                "Bytes": sample.get("response_size", 0),
            }
        )
    return rows


def _find_sampler_config(plan, sample):
    for sampler in (plan or {}).get("samplers", []):
        if sampler.get("label") == sample.get("sampler_label"):
            return sampler
    return {}


def _build_sampler_request_preview(plan, sample):
    sampler = _find_sampler_config(plan, sample)
    payload = {
        "method": sample.get("method", ""),
        "url": sample.get("url", ""),
        "headers": sampler.get("headers", {}),
        "path_params": sampler.get("path_params", {}),
        "query_params": sampler.get("query_params", {}),
        "body": sampler.get("body"),
        "csv_variables": sample.get("csv_variables", {}),
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _build_request_headers_preview(sample):
    return json.dumps(sample.get("request_headers", {}) or {}, ensure_ascii=False, indent=2)


def _build_response_headers_preview(sample):
    return json.dumps(sample.get("response_headers", {}) or {}, ensure_ascii=False, indent=2)


def _build_assertion_result_rows(sample):
    success = bool(sample.get("success"))
    return [
        {
            "Assertion": "HTTP Sample Result",
            "Result": "PASS" if success else "FAIL",
            "Response Message": sample.get("response_message", ""),
            "Failure Message": sample.get("error_message", "") if not success else "",
        }
    ]


def _render_sampler_result_summary(sample):
    top_col1, top_col2, top_col3, top_col4 = st.columns(4)
    with top_col1:
        st.text_input("Thread Name", value=sample.get("thread_name", ""), disabled=True, key=f"perf_sampler_thread_{sample.get('started_at', '')}")
    with top_col2:
        st.text_input("Sample Label", value=sample.get("sampler_label", ""), disabled=True, key=f"perf_sampler_label_{sample.get('started_at', '')}")
    with top_col3:
        st.text_input("Response Code", value=str(sample.get("status_code", 0)), disabled=True, key=f"perf_sampler_code_{sample.get('started_at', '')}")
    with top_col4:
        st.text_input("Response Message", value=sample.get("response_message", ""), disabled=True, key=f"perf_sampler_message_{sample.get('started_at', '')}")

    mid_col1, mid_col2, mid_col3, mid_col4 = st.columns(4)
    with mid_col1:
        st.text_input("Elapsed(ms)", value=str(sample.get("elapsed_ms", 0.0)), disabled=True, key=f"perf_sampler_elapsed_{sample.get('started_at', '')}")
    with mid_col2:
        st.text_input("Bytes", value=str(sample.get("response_size", 0)), disabled=True, key=f"perf_sampler_bytes_{sample.get('started_at', '')}")
    with mid_col3:
        st.text_input("Loop #", value=str(sample.get("loop_number", 0)), disabled=True, key=f"perf_sampler_loop_{sample.get('started_at', '')}")
    with mid_col4:
        st.text_input("Success", value="true" if sample.get("success") else "false", disabled=True, key=f"perf_sampler_success_{sample.get('started_at', '')}")

    bottom_col1, bottom_col2 = st.columns(2)
    with bottom_col1:
        st.text_input("Started", value=sample.get("started_at", ""), disabled=True, key=f"perf_sampler_started_{sample.get('started_at', '')}")
    with bottom_col2:
        st.text_input("Finished", value=sample.get("finished_at", ""), disabled=True, key=f"perf_sampler_finished_{sample.get('started_at', '')}")


def _render_property_toolbar(selected_node: str, perf_interfaces):
    node_ids = [node_id for node_id, _ in TREE_NODES]
    current_index = node_ids.index(selected_node) if selected_node in node_ids else 0
    active_button = st.session_state.get("api_perf_active_panel_button", "")

    st.markdown(
        '<div class="jmeter-mini-toolbar"><div class="jmeter-panel-title">Property Actions</div><div class="jmeter-toolbar-note">模拟 JMeter 右侧属性区的快捷动作，方便在树节点之间切换。</div></div>',
        unsafe_allow_html=True,
    )
    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    with action_col1:
        if st.button(
            "◀ Prev Node",
            key="api_perf_panel_prev_node",
            use_container_width=True,
            disabled=current_index == 0,
            type="primary" if active_button == "prev_node" else "secondary",
        ):
            st.session_state.api_perf_active_panel_button = "prev_node"
            st.session_state.api_perf_selected_node = node_ids[current_index - 1]
            st.rerun()
    with action_col2:
        if st.button(
            "Next Node ▶",
            key="api_perf_panel_next_node",
            use_container_width=True,
            disabled=current_index >= len(node_ids) - 1,
            type="primary" if active_button == "next_node" else "secondary",
        ):
            st.session_state.api_perf_active_panel_button = "next_node"
            st.session_state.api_perf_selected_node = node_ids[current_index + 1]
            st.rerun()
    with action_col3:
        if st.button(
            "🔗 Go Samplers",
            key="api_perf_panel_go_samplers",
            use_container_width=True,
            disabled=not perf_interfaces,
            type="primary" if active_button == "go_samplers" else "secondary",
        ):
            st.session_state.api_perf_active_panel_button = "go_samplers"
            st.session_state.api_perf_selected_node = "samplers"
            if perf_interfaces and not st.session_state.get("performance_sampler_indexes"):
                st.session_state.performance_sampler_indexes = [0]
            st.rerun()
    with action_col4:
        if st.button(
            "📊 Go Listener",
            key="api_perf_panel_go_listener",
            use_container_width=True,
            type="primary" if active_button == "go_listener" else "secondary",
        ):
            st.session_state.api_perf_active_panel_button = "go_listener"
            preferred_tab = "Summary Report" if st.session_state.get("interface_perf_result") else "Test Plan"
            _open_listener_view(preferred_tab)
            st.rerun()


def _build_assertion_result_nodes(perf_plan, sample):
    plan_assertions = (perf_plan or {}).get("assertions", {})
    sampler = _find_sampler_config(perf_plan, sample)
    nodes = [
        {
            "level": 0,
            "passed": bool(sample.get("success")),
            "label": "HTTP Sample Result",
            "detail": sample.get("response_message", "") or ("Success" if sample.get("success") else "Failure"),
        }
    ]

    expected_status_mode = plan_assertions.get("expected_status_mode", "document")
    if expected_status_mode != "none":
        if expected_status_mode == "custom":
            expected_status = int(plan_assertions.get("custom_expected_status", 200) or 200)
        else:
            expected_status = int(sampler.get("expected_status", 200) or 200)
        actual_status = int(sample.get("status_code", 0) or 0)
        nodes.append(
            {
                "level": 1,
                "passed": actual_status == expected_status,
                "label": "Response Code",
                "detail": f"expected={expected_status}, actual={actual_status}",
            }
        )

    contains_text = str(plan_assertions.get("contains_text", "") or "").strip()
    if contains_text:
        response_preview = str(sample.get("response_preview", "") or "")
        nodes.append(
            {
                "level": 1,
                "passed": contains_text in response_preview,
                "label": "Response Contains",
                "detail": f"keyword={contains_text}",
            }
        )

    max_response_ms = float(plan_assertions.get("max_response_ms", 0.0) or 0.0)
    if max_response_ms > 0:
        elapsed_ms = float(sample.get("elapsed_ms", 0.0) or 0.0)
        nodes.append(
            {
                "level": 1,
                "passed": elapsed_ms <= max_response_ms,
                "label": "Response Time",
                "detail": f"limit={round(max_response_ms, 2)} ms, actual={round(elapsed_ms, 2)} ms",
            }
        )

    if not sample.get("success") and sample.get("error_message"):
        nodes.append(
            {
                "level": 1,
                "passed": False,
                "label": "Failure Message",
                "detail": sample.get("error_message", ""),
            }
        )
    return nodes


def _render_assertion_result_tree(perf_plan, sample):
    nodes = _build_assertion_result_nodes(perf_plan, sample)
    rows = ['<div class="jmeter-assertion-tree">']
    for node in nodes:
        css_class = "pass" if node["passed"] else "fail"
        icon = "PASS" if node["passed"] else "FAIL"
        margin = node["level"] * 22
        rows.append(
            (
                f'<div class="jmeter-assertion-row {css_class}" style="margin-left:{margin}px">'
                f'<span class="icon">{icon}</span>'
                f'<span class="label">{html.escape(node["label"])}</span>'
                f'<span class="detail">{html.escape(str(node["detail"]))}</span>'
                "</div>"
            )
        )
    rows.append("</div>")
    st.markdown("".join(rows), unsafe_allow_html=True)


def _filter_result_tree_rows(tree_rows):
    filter_col1, filter_col2, filter_col3 = st.columns([2, 1, 1])
    with filter_col1:
        search_text = st.text_input(
            "Search Samples",
            key="api_perf_tree_search",
            placeholder="按 Label / Method / Path 过滤样本",
        ).strip().lower()
    with filter_col2:
        only_errors = st.checkbox("Errors Only", key="api_perf_tree_only_errors")
    with filter_col3:
        if st.button("Reset Filter", key="api_perf_tree_reset_filter", use_container_width=True):
            st.session_state.api_perf_tree_search = ""
            st.session_state.api_perf_tree_only_errors = False
            st.rerun()

    filtered_rows = []
    for row in tree_rows:
        if only_errors and row["Status"] != "Failure":
            continue
        if search_text and search_text not in row["display"].lower() and search_text not in row["Response Message"].lower():
            continue
        filtered_rows.append(row)
    return filtered_rows


def _render_results_tree_sidebar(filtered_rows, perf_result):
    st.markdown(
        '<div class="jmeter-report-toolbar"><div class="jmeter-panel-title">Result Tree Browser</div><div class="jmeter-toolbar-note">左侧改成树状样本节点列表，点击节点可切换右侧详情视图。</div></div>',
        unsafe_allow_html=True,
    )

    samples = perf_result.get("samples", [])
    available_keys = [row["sample_index"] for row in filtered_rows]
    selected_sample_key = st.session_state.get("api_perf_selected_sample_key", available_keys[0] if available_keys else 0)
    if selected_sample_key not in available_keys and available_keys:
        selected_sample_key = available_keys[0]
        st.session_state.api_perf_selected_sample_key = selected_sample_key

    sample_browser_df = pd.DataFrame(
        [
            {
                "Node": row["display"],
                "Label": row["Label"],
                "Sample Time(ms)": row["Sample Time(ms)"],
                "Status": row["Status"],
                "Response Code": row["Response Code"],
                "Response Message": row["Response Message"],
            }
            for row in filtered_rows
        ]
    )
    rendered_rows = filtered_rows[:200]

    st.download_button(
        label="保存当前树节点",
        data=sample_browser_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig"),
        file_name="results_tree_samples.csv",
        mime="text/csv",
        use_container_width=True,
        key="results_tree_download_filtered_samples",
    )
    st.markdown(
        f'<div class="jmeter-sample-tree-shell"><div class="jmeter-sample-tree-meta">Nodes: {len(filtered_rows)} | Showing: {len(rendered_rows)} | 当前选中样本索引: {selected_sample_key + 1}</div></div>',
        unsafe_allow_html=True,
    )

    grouped_rows = {}
    for row in rendered_rows:
        sample = samples[row["sample_index"]]
        thread_name = sample.get("thread_name", "") or "Unknown Thread"
        grouped_rows.setdefault(thread_name, []).append((row, sample))

    detail_nodes = [
        ("Sampler Result", "Sampler Result"),
        ("Request", "Request"),
        ("Request Headers", "Request Headers"),
        ("Request Body", "Request Body"),
        ("Response Headers", "Response Headers"),
        ("Response Data", "Response Data"),
        ("Assertion Result", "Assertion Result"),
    ]
    active_detail_tab = st.session_state.get("api_perf_result_detail_tab", "Sampler Result")

    thread_names = list(grouped_rows.keys())
    current_thread_name = ""
    if available_keys:
        current_thread_name = samples[selected_sample_key].get("thread_name", "") or "Unknown Thread"

    browser_ctrl1, browser_ctrl2, browser_ctrl3, browser_ctrl4 = st.columns([1, 1, 1.2, 1.8])
    with browser_ctrl1:
        if st.button("全部展开", key="results_tree_expand_all", use_container_width=True):
            _set_thread_groups_expanded(thread_names, True)
            st.rerun()
    with browser_ctrl2:
        if st.button("全部折叠", key="results_tree_collapse_all", use_container_width=True):
            _set_thread_groups_expanded(thread_names, False)
            st.rerun()
    with browser_ctrl3:
        if st.button("仅展开当前组", key="results_tree_expand_current", use_container_width=True, disabled=not current_thread_name):
            _set_thread_groups_expanded(thread_names, False)
            st.session_state[_get_thread_group_state_key(current_thread_name)] = True
            st.rerun()
    with browser_ctrl4:
        st.text_input(
            "树状态",
            value=f"线程组 {len(thread_names)} 个，当前选中 detail: {active_detail_tab}",
            disabled=True,
            key="results_tree_browser_status",
        )

    for thread_index, thread_name in enumerate(thread_names):
        thread_rows = grouped_rows[thread_name]
        thread_branch = "└─" if thread_index == len(thread_names) - 1 else "├─"
        group_state_key = _get_thread_group_state_key(thread_name)
        selected_in_group = any(row["sample_index"] == selected_sample_key for row, _ in thread_rows)
        if group_state_key not in st.session_state:
            st.session_state[group_state_key] = selected_in_group or thread_index == 0
        if selected_in_group and not st.session_state.get(group_state_key):
            st.session_state[group_state_key] = True
        is_expanded = bool(st.session_state.get(group_state_key, True))
        group_toggle = "[-]" if is_expanded else "[+]"
        if st.button(
            f"{thread_branch} {group_toggle} {thread_name} ({len(thread_rows)} samples)",
            key=f"results_tree_group_{thread_index}",
            use_container_width=True,
            type="primary" if selected_in_group else "secondary",
        ):
            st.session_state[group_state_key] = not is_expanded
            st.rerun()
        if not st.session_state.get(group_state_key, True):
            st.markdown('<div class="jmeter-sample-subnote">组已折叠，点击上面的线程组可展开。</div>', unsafe_allow_html=True)
            continue

        for row_index, (row, sample) in enumerate(thread_rows):
            branch = "└─" if row_index == len(thread_rows) - 1 else "├─"
            status_icon = "✓" if sample.get("success") else "✕"
            button_label = f"    {branch} {status_icon} {row['Label']}"
            if st.button(
                button_label,
                key=f"results_tree_item_{row['sample_index']}",
                use_container_width=True,
                type="primary" if selected_sample_key == row["sample_index"] else "secondary",
            ):
                st.session_state.api_perf_selected_sample_key = row["sample_index"]
                st.session_state.api_perf_result_detail_tab = "Sampler Result"
                st.rerun()
            st.markdown(
                f'<div class="jmeter-sample-subnote">code={sample.get("status_code", "")} | '
                f'{round(float(sample.get("elapsed_ms", 0.0) or 0.0), 2)} ms</div>',
                unsafe_allow_html=True,
            )

            if selected_sample_key == row["sample_index"]:
                quick_col1, quick_col2, quick_col3 = st.columns(3)
                with quick_col1:
                    if st.button(
                        "查看请求",
                        key=f"results_tree_quick_request_{row['sample_index']}",
                        use_container_width=True,
                        type="primary" if active_detail_tab == "Request" else "secondary",
                    ):
                        st.session_state.api_perf_selected_sample_key = row["sample_index"]
                        st.session_state.api_perf_result_detail_tab = "Request"
                        st.rerun()
                with quick_col2:
                    if st.button(
                        "查看响应",
                        key=f"results_tree_quick_response_{row['sample_index']}",
                        use_container_width=True,
                        type="primary" if active_detail_tab == "Response Data" else "secondary",
                    ):
                        st.session_state.api_perf_selected_sample_key = row["sample_index"]
                        st.session_state.api_perf_result_detail_tab = "Response Data"
                        st.rerun()
                with quick_col3:
                    if st.button(
                        "查看断言",
                        key=f"results_tree_quick_assert_{row['sample_index']}",
                        use_container_width=True,
                        type="primary" if active_detail_tab == "Assertion Result" else "secondary",
                    ):
                        st.session_state.api_perf_selected_sample_key = row["sample_index"]
                        st.session_state.api_perf_result_detail_tab = "Assertion Result"
                        st.rerun()
                for detail_index, (detail_label, detail_tab) in enumerate(detail_nodes):
                    child_branch = "└─" if detail_index == len(detail_nodes) - 1 else "├─"
                    child_label = f"        {child_branch} {detail_label}"
                    if st.button(
                        child_label,
                        key=f"results_tree_item_{row['sample_index']}_{detail_tab}",
                        use_container_width=True,
                        type="primary" if active_detail_tab == detail_tab else "secondary",
                    ):
                        st.session_state.api_perf_selected_sample_key = row["sample_index"]
                        st.session_state.api_perf_result_detail_tab = detail_tab
                        st.rerun()

    return st.session_state.get("api_perf_selected_sample_key", selected_sample_key)


def _render_tree_action_bar(perf_interfaces):
    st.markdown('<div class="jmeter-node-actions"><div class="jmeter-panel-title">Tree Actions</div>模拟 JMeter 右键动作，做一些高频节点操作。</div>', unsafe_allow_html=True)
    action_col1, action_col2 = st.columns(2)
    active_tree_action = st.session_state.get("api_perf_active_tree_action", "")
    with action_col1:
        if st.button(
            "➕ Enable CSV",
            key="api_perf_action_enable_csv",
            use_container_width=True,
            type="primary" if active_tree_action == "enable_csv" else "secondary",
        ):
            st.session_state.api_perf_active_tree_action = "enable_csv"
            st.session_state.performance_csv_enabled = True
            st.session_state.api_perf_selected_node = "csv_data"
            st.rerun()
        if st.button(
            "🧪 Go Assertions",
            key="api_perf_action_assertions",
            use_container_width=True,
            type="primary" if active_tree_action == "assertions" else "secondary",
        ):
            st.session_state.api_perf_active_tree_action = "assertions"
            st.session_state.api_perf_selected_node = "assertions"
            st.rerun()
        if st.button(
            "🎬 Enable Tx",
            key="api_perf_action_enable_tx",
            use_container_width=True,
            type="primary" if active_tree_action == "enable_tx" else "secondary",
        ):
            st.session_state.api_perf_active_tree_action = "enable_tx"
            st.session_state.performance_transaction_enabled = True
            st.session_state.api_perf_selected_node = "transaction"
            st.rerun()
    with action_col2:
        if st.button(
            "✅ Select All",
            key="api_perf_action_select_all",
            use_container_width=True,
            disabled=not perf_interfaces,
            type="primary" if active_tree_action == "select_all" else "secondary",
        ):
            st.session_state.api_perf_active_tree_action = "select_all"
            st.session_state.performance_sampler_indexes = list(range(len(perf_interfaces)))
            st.session_state.api_perf_selected_node = "samplers"
            st.rerun()
        if st.button(
            "🗑️ Clear Samplers",
            key="api_perf_action_clear_samplers",
            use_container_width=True,
            disabled=not perf_interfaces,
            type="primary" if active_tree_action == "clear_samplers" else "secondary",
        ):
            st.session_state.api_perf_active_tree_action = "clear_samplers"
            st.session_state.performance_sampler_indexes = []
            st.session_state.api_perf_selected_node = "samplers"
            st.rerun()
        if st.button(
            "📊 Go Listeners",
            key="api_perf_action_listeners",
            use_container_width=True,
            type="primary" if active_tree_action == "listeners" else "secondary",
        ):
            st.session_state.api_perf_active_tree_action = "listeners"
            preferred_tab = "Summary Report" if st.session_state.get("interface_perf_result") else "Test Plan"
            _open_listener_view(preferred_tab)
            st.rerun()


def _render_tree_panel(perf_interfaces):
    selected_node = st.session_state.get("api_perf_selected_node", "test_plan")

    st.markdown("#### Test Plan Tree")
    for node_id, label in TREE_NODES:
        is_selected = selected_node == node_id
        button_label = f"▶ {label}" if is_selected else f"  {label}"
        if st.button(
            button_label,
            key=f"api_perf_tree_{node_id}",
            use_container_width=True,
            type="primary" if is_selected else "secondary",
        ):
            if node_id == "listeners":
                preferred_tab = "Summary Report" if st.session_state.get("interface_perf_result") else "Test Plan"
                _open_listener_view(preferred_tab)
            else:
                st.session_state.api_perf_selected_node = node_id
            st.rerun()

    st.markdown('<div class="jmeter-tree-tip">左侧按 JMeter 的测试计划树组织，右侧按节点配置。</div>', unsafe_allow_html=True)
    _render_tree_action_bar(perf_interfaces)

    source_name = st.session_state.get("interface_perf_source_name", "未导入")
    selected_indexes = st.session_state.get("performance_sampler_indexes", [])
    result = st.session_state.get("interface_perf_result")
    selected_count = len(selected_indexes) if perf_interfaces else 0

    metric_col1, metric_col2 = st.columns(2)
    with metric_col1:
        st.metric("接口数", len(perf_interfaces))
    with metric_col2:
        st.metric("已选 Sampler", selected_count)

    st.caption(f"当前文档: `{source_name}`")
    if result:
        st.success("最近一次压测结果已生成")
    else:
        st.info("当前还没有执行结果")

    return st.session_state.get("api_perf_selected_node", "test_plan")


def _render_test_plan_panel(parser: InterfaceAutoTestCore, perf_interfaces):
    name_col1, name_col2 = st.columns([2, 1])
    with name_col1:
        st.text_input("Name", key="api_perf_plan_name")
    with name_col2:
        st.text_input("Comments", key="api_perf_plan_comment", placeholder="可选备注")

    perf_source = _render_interface_source_panel("interface_perf_source", "Source / Interface Document", parser, height=220)
    if st.button("📥 Add From Interface Document", use_container_width=True, key="parse_performance_source"):
        try:
            interfaces, source_name = _parse_interface_source(perf_source, "interface_perf_source", parser)
            _clear_results()
            st.session_state.interface_perf_interfaces = interfaces
            st.session_state.interface_perf_source_name = source_name
            if interfaces and not st.session_state.get("performance_sampler_indexes"):
                st.session_state.performance_sampler_indexes = [0]
            st.session_state.api_perf_selected_node = "samplers"
            st.success(f"✅ 已解析 {len(interfaces)} 个可压测接口")
            st.rerun()
        except Exception as exc:
            st.error(f"❌ 解析失败: {exc}")

    if perf_interfaces:
        st.markdown("#### Imported HTTP Samplers")
        st.dataframe(pd.DataFrame(_build_interface_preview_rows(perf_interfaces, limit=30)), use_container_width=True)


def _render_thread_group_panel():
    tg_col1, tg_col2, tg_col3, tg_col4, tg_col5 = st.columns(5)
    with tg_col1:
        st.number_input("Number of Threads (users)", min_value=1, max_value=200, key="performance_users")
    with tg_col2:
        st.number_input("Ramp-Up Period (seconds)", min_value=0.0, step=1.0, key="performance_ramp_up")
    with tg_col3:
        st.number_input("Loop Count", min_value=0, max_value=1000, key="performance_loops")
    with tg_col4:
        st.number_input("Duration (seconds)", min_value=0.0, step=5.0, key="performance_duration")
    with tg_col5:
        st.number_input("Startup Delay (seconds)", min_value=0.0, step=1.0, key="performance_start_delay")


def _render_http_defaults_panel():
    request_col1, request_col2, request_col3, request_col4 = st.columns(4)
    with request_col1:
        st.selectbox("Protocol [http]", ["http", "https"], key="api_perf_protocol")
    with request_col2:
        st.text_input("Server Name or IP", key="api_perf_server_name", placeholder="api.example.com")
    with request_col3:
        st.text_input("Port Number", key="api_perf_port", placeholder="443")
    with request_col4:
        st.text_input("Base Path", key="api_perf_base_path", placeholder="例如: api/v1")

    ext_col1, ext_col2, ext_col3, ext_col4 = st.columns(4)
    with ext_col1:
        st.number_input("Connect Timeout (seconds)", min_value=1.0, step=1.0, key="performance_timeout")
    with ext_col2:
        st.checkbox("Follow Redirects", key="performance_follow_redirects")
    with ext_col3:
        st.checkbox("Use KeepAlive", key="performance_keep_alive")
    with ext_col4:
        st.checkbox("Validate SSL", key="performance_verify_ssl")

    computed_base_url = _compose_base_url_from_fields()
    st.session_state.performance_base_url = computed_base_url
    st.session_state.api_perf_http_fields_synced_from = computed_base_url
    st.code(computed_base_url or "请先填写 Server Name or IP", language="text")


def _render_samplers_panel(perf_interfaces):
    sampler_indexes = list(range(len(perf_interfaces)))
    st.multiselect(
        "HTTP Request 列表",
        sampler_indexes,
        format_func=lambda idx: _get_sampler_label(perf_interfaces, idx),
        key="performance_sampler_indexes",
    )

    selected_indexes = st.session_state.get("performance_sampler_indexes") or []
    if not selected_indexes:
        st.warning("请至少选择一个 HTTP Sampler")
        return

    detail_index = st.selectbox(
        "查看 Sampler 配置",
        selected_indexes,
        format_func=lambda idx: _get_sampler_label(perf_interfaces, idx),
        key="performance_sampler_detail_index",
    )
    item = perf_interfaces[detail_index]

    tab_basic, tab_headers, tab_params, tab_body = st.tabs(["Basic", "Headers", "Parameters", "Body"])
    with tab_basic:
        basic_col1, basic_col2 = st.columns(2)
        with basic_col1:
            st.text_input("Name", value=item.get("name", "未命名接口"), disabled=True, key=f"performance_sampler_name_preview_{detail_index}")
            st.text_input("Method", value=item.get("method", "GET"), disabled=True, key=f"performance_sampler_method_preview_{detail_index}")
        with basic_col2:
            st.text_input("Path", value=item.get("path", ""), disabled=True, key=f"performance_sampler_path_preview_{detail_index}")
            st.text_input("Request Format", value=item.get("request_format", "auto"), disabled=True, key=f"performance_sampler_format_preview_{detail_index}")
        st.text_input("Expected Status", value=str(item.get("expected_status", 200)), disabled=True, key=f"performance_sampler_status_preview_{detail_index}")
    with tab_headers:
        st.code(json.dumps(item.get("headers", {}), ensure_ascii=False, indent=2), language="json")
    with tab_params:
        st.code(
            json.dumps(
                {
                    "path_params": item.get("path_params", {}),
                    "query_params": item.get("query_params", {}),
                },
                ensure_ascii=False,
                indent=2,
            ),
            language="json",
        )
    with tab_body:
        st.code(json.dumps(item.get("body"), ensure_ascii=False, indent=2), language="json")


def _render_csv_panel():
    csv_enable_col1, csv_enable_col2 = st.columns([1, 2])
    with csv_enable_col1:
        st.checkbox("Enabled", key="performance_csv_enabled")
    with csv_enable_col2:
        st.caption("变量占位符使用 `${变量名}`，效果和 JMeter 的 CSV Data Set Config 类似。")

    if not st.session_state.get("performance_csv_enabled", False):
        st.info("当前未启用 CSV Data Set Config")
        return

    csv_col1, csv_col2 = st.columns(2)
    with csv_col1:
        st.radio("CSV Source", ["文件上传", "直接粘贴"], horizontal=True, key="performance_csv_source_mode")
        if st.session_state.get("performance_csv_source_mode") == "文件上传":
            st.file_uploader("Filename", type=["csv", "txt"], key="performance_csv_upload")
        else:
            st.text_area("File Content", height=180, key="performance_csv_text", placeholder="user_id,token\n1,token_a")
        st.checkbox("Variable Names in First Line", key="performance_csv_use_header")
        if not st.session_state.get("performance_csv_use_header", True):
            st.text_input("Variable Names", key="performance_csv_variable_names", placeholder="例如: user_id,token")
    with csv_col2:
        st.text_input("Delimiter", max_chars=1, key="performance_csv_delimiter")
        st.text_input("Quote Char", max_chars=1, key="performance_csv_quotechar")
        st.selectbox("Sharing Mode", ["All Threads", "Current Thread"], key="performance_csv_sharing_mode")
        st.checkbox("Recycle on EOF", key="performance_csv_recycle")
        st.checkbox("Stop Thread on EOF", key="performance_csv_stop_thread")

        preview_text = st.session_state.get("performance_csv_text", "")
        upload_file = st.session_state.get("performance_csv_upload")
        if upload_file is not None:
            preview_text = upload_file.getvalue().decode("utf-8-sig", errors="ignore")
        if preview_text.strip():
            st.text_area("Preview", "\n".join(preview_text.strip().splitlines()[:5]), height=140, disabled=True)


def _render_transaction_panel():
    trans_col1, trans_col2, trans_col3 = st.columns(3)
    with trans_col1:
        st.checkbox("Enabled", key="performance_transaction_enabled")
    with trans_col2:
        st.text_input("Name", key="performance_transaction_name", disabled=not st.session_state.get("performance_transaction_enabled", False))
    with trans_col3:
        st.checkbox(
            "Stop on Sampler Error",
            key="performance_transaction_stop_on_error",
            disabled=not st.session_state.get("performance_transaction_enabled", False),
        )

    st.checkbox(
        "Generate Parent Sample",
        key="performance_transaction_parent_sample",
        disabled=not st.session_state.get("performance_transaction_enabled", False),
    )
    if st.session_state.get("performance_transaction_enabled", False):
        st.caption("当前所选 HTTP Sampler 会按顺序组成一条事务链路。")


def _render_assertion_panel():
    assert_col1, assert_col2, assert_col3 = st.columns(3)
    with assert_col1:
        st.selectbox("Response Code Assertion", ["使用文档状态码", "自定义状态码", "不校验状态码"], key="performance_expected_status_mode")
        st.number_input(
            "Custom Response Code",
            min_value=100,
            max_value=599,
            key="performance_custom_expected_status",
            disabled=st.session_state.get("performance_expected_status_mode") != "自定义状态码",
        )
    with assert_col2:
        st.text_input("Response Contains", key="performance_contains_text", placeholder="例如: success / code / token")
    with assert_col3:
        st.number_input("Max Response Time (ms)", min_value=0.0, step=50.0, key="performance_max_response_ms")


def _render_timer_panel():
    timer_col1, timer_col2, timer_col3 = st.columns(3)
    with timer_col1:
        st.number_input("Constant Timer (ms)", min_value=0.0, step=10.0, key="performance_think_time_ms")
    with timer_col2:
        st.number_input("Random Jitter (ms)", min_value=0.0, step=10.0, key="performance_random_jitter_ms")
    with timer_col3:
        users = max(int(st.session_state.get("performance_users", 1)), 1)
        loops = max(int(st.session_state.get("performance_loops", 1)), 1)
        sampler_count = max(len(st.session_state.get("performance_sampler_indexes") or []), 1)
        duration = float(st.session_state.get("performance_duration", 0.0))
        estimated_request_count = "按时长运行，理论请求数不固定" if duration > 0 and int(st.session_state.get("performance_loops", 1)) == 0 else str(users * loops * sampler_count)
        st.metric("Estimated Requests", estimated_request_count)


def _render_execution_status(perf_interfaces):
    status_col1, status_col2, status_col3, status_col4, status_col5 = st.columns(5)
    selected_samplers = len(st.session_state.get("performance_sampler_indexes") or [])
    source_name = st.session_state.get("interface_perf_source_name", "未导入")
    source_label = source_name if len(source_name) <= 18 else f"{source_name[:18]}..."
    with status_col1:
        st.metric("当前文档", source_label)
    with status_col2:
        st.metric("已选 Sampler", selected_samplers)
    with status_col3:
        st.metric("CSV 参数化", "已开启" if st.session_state.get("performance_csv_enabled", False) else "未开启")
    with status_col4:
        st.metric("事务链路", "已开启" if st.session_state.get("performance_transaction_enabled", False) else "未开启")
    with status_col5:
        if st.session_state.get("interface_perf_result"):
            st.metric("运行状态", "已有结果")
        elif st.session_state.get("interface_perf_plan"):
            st.metric("运行状态", "计划已生成")
        else:
            st.metric("运行状态", "待执行")

    if perf_interfaces:
        st.caption(f"当前共导入 {len(perf_interfaces)} 个接口，点击工具条后会自动切到对应节点或结果页签。")
    else:
        st.caption("先导入接口文档，再生成 Test Plan 或直接开始压测。")


def _render_listener_shortcuts(perf_plan, perf_result):
    active_tab = st.session_state.get("api_perf_listener_tab", "Test Plan")
    error_count = len((perf_result or {}).get("error_samples", []))
    has_transactions = bool((perf_result or {}).get("per_transaction") or (perf_result or {}).get("transaction_samples"))
    has_result = perf_result is not None
    has_plan = perf_plan is not None

    st.markdown(
        '<div class="jmeter-mini-toolbar"><div class="jmeter-panel-title">Listener Shortcuts</div><div class="jmeter-toolbar-note">常用查看动作直接跳到对应结果工作台，不需要在下方来回找页签。</div></div>',
        unsafe_allow_html=True,
    )
    row1 = st.columns(4)
    with row1[0]:
        if st.button(
            "📄 Plan",
            key="listener_shortcut_plan",
            use_container_width=True,
            disabled=not has_plan,
            type="primary" if active_tab == "Test Plan" else "secondary",
        ):
            _open_listener_view("Test Plan")
            st.rerun()
    with row1[1]:
        if st.button(
            "📈 Summary",
            key="listener_shortcut_summary",
            use_container_width=True,
            disabled=not has_result,
            type="primary" if active_tab == "Summary Report" else "secondary",
        ):
            _open_listener_view("Summary Report")
            st.rerun()
    with row1[2]:
        if st.button(
            "📊 Aggregate",
            key="listener_shortcut_aggregate",
            use_container_width=True,
            disabled=not has_result,
            type="primary" if active_tab == "Aggregate Report" else "secondary",
        ):
            _open_listener_view("Aggregate Report")
            st.rerun()
    with row1[3]:
        if st.button(
            "🧾 Downloads",
            key="listener_shortcut_downloads",
            use_container_width=True,
            disabled=not has_result,
            type="primary" if active_tab == "Downloads" else "secondary",
        ):
            _open_listener_view("Downloads")
            st.rerun()

    row2 = st.columns(4)
    with row2[0]:
        if st.button(
            "🌲 Results Tree",
            key="listener_shortcut_tree",
            use_container_width=True,
            disabled=not has_result,
            type="primary" if active_tab == "View Results Tree" and not st.session_state.get("api_perf_tree_only_errors", False) else "secondary",
        ):
            _open_results_tree()
            st.rerun()
    with row2[1]:
        if st.button(
            f"❌ Failed Samples ({error_count})",
            key="listener_shortcut_failed",
            use_container_width=True,
            disabled=not has_result,
            type="primary" if active_tab == "View Results Tree" and st.session_state.get("api_perf_tree_only_errors", False) else "secondary",
        ):
            _open_results_tree(only_errors=True)
            st.rerun()
    with row2[2]:
        if st.button(
            "🚨 Errors",
            key="listener_shortcut_errors",
            use_container_width=True,
            disabled=not has_result,
            type="primary" if active_tab == "Errors" else "secondary",
        ):
            _open_listener_view("Errors")
            st.rerun()
    with row2[3]:
        if st.button(
            "🎬 Transactions",
            key="listener_shortcut_transactions",
            use_container_width=True,
            disabled=not has_transactions,
            type="primary" if active_tab == "Transactions" else "secondary",
        ):
            _open_listener_view("Transactions")
            st.rerun()


def _render_execution_toolbar(perf_interfaces, performance_tool: PerformanceTestTool):
    st.markdown('<div class="jmeter-toolbar"><div class="jmeter-panel-title">Toolbar / Execute</div>只保留一套真正可执行的操作按钮，避免同类功能重复展示。</div>', unsafe_allow_html=True)
    action_col1, action_col2, action_col3, action_col4, action_col5, action_col6 = st.columns(6)
    with action_col1:
        goto_test_plan = st.button(
            "📄 Test Plan",
            use_container_width=True,
            key="goto_test_plan",
        )
    with action_col2:
        build_clicked = st.button(
            "🧩 Generate Test Plan",
            use_container_width=True,
            key="build_performance_plan",
            disabled=not perf_interfaces,
        )
    with action_col3:
        run_clicked = st.button(
            "🚀 Start",
            use_container_width=True,
            key="run_performance_test",
            disabled=not perf_interfaces,
        )
    with action_col4:
        clear_clicked = st.button(
            "🧹 Clear Results",
            use_container_width=True,
            key="clear_performance_results",
        )
    with action_col5:
        reset_clicked = st.button(
            "♻️ Reset Config",
            use_container_width=True,
            key="reset_performance_config",
        )
    with action_col6:
        current_plan = st.session_state.get("interface_perf_plan")
        st.download_button(
            label="📥 Save Test Plan",
            data=json.dumps(current_plan, ensure_ascii=False, indent=2) if current_plan else "",
            file_name="performance_test_plan.json",
            mime="application/json",
            use_container_width=True,
            key="download_performance_plan",
            disabled=current_plan is None,
        )

    if goto_test_plan:
        st.session_state.api_perf_active_menu = "File"
        st.session_state.api_perf_selected_node = "test_plan"
        st.rerun()

    if clear_clicked:
        st.session_state.api_perf_active_menu = "Run"
        _clear_results()
        _open_listener_view("Test Plan")
        st.rerun()

    if reset_clicked:
        st.session_state.api_perf_active_menu = "Options"
        _reset_configuration()
        st.rerun()

    if build_clicked:
        try:
            st.session_state.api_perf_active_menu = "File"
            plan = _build_plan_from_state(perf_interfaces, performance_tool)
            st.session_state.interface_perf_plan = plan
            _open_listener_view("Test Plan")
            st.success("✅ Test Plan 已生成")
        except Exception as exc:
            st.error(f"❌ 生成测试计划失败: {exc}")

    if run_clicked:
        try:
            st.session_state.api_perf_active_menu = "Run"
            plan = _build_plan_from_state(perf_interfaces, performance_tool)
            st.session_state.interface_perf_plan = plan
            with st.spinner("正在执行性能测试，请稍候..."):
                result = performance_tool.run_test_plan(plan)
            st.session_state.interface_perf_result = result
            _open_listener_view("Summary Report")
            st.success("✅ 性能测试执行完成")
        except Exception as exc:
            st.error(f"❌ 性能测试执行失败: {exc}")


def _render_listener_panel():
    perf_plan = st.session_state.get("interface_perf_plan")
    perf_result = st.session_state.get("interface_perf_result")

    if not perf_plan and not perf_result:
        st.info("先生成 Test Plan 或执行压测，Listener 区域才会显示内容。")
        return

    _render_listener_shortcuts(perf_plan, perf_result)

    listener_tabs = ["Test Plan", "Summary Report", "Aggregate Report", "View Results Tree", "Graph Results", "Errors", "Transactions", "Downloads"]
    active_listener_tab = _render_button_tab_bar(
        listener_tabs,
        "api_perf_listener_tab",
        "api_perf_listener_tab_button",
        "Listener Tabs",
        "模拟 JMeter 底部 Listener 切换，当前仅高亮正在查看的监听器页签。",
    )

    if active_listener_tab == "Test Plan":
        if perf_plan:
            st.markdown('<div class="jmeter-field-card"><strong>Plan JSON</strong> 这里保留完整测试计划，便于核对线程组、事务和断言配置。</div>', unsafe_allow_html=True)
            st.code(json.dumps(perf_plan, ensure_ascii=False, indent=2), language="json")
            csv_plan_config = perf_plan.get("csv_data_set", {})
            if csv_plan_config.get("enabled"):
                st.markdown("#### CSV Data Set Preview")
                st.dataframe(pd.DataFrame(csv_plan_config.get("preview_rows", [])), use_container_width=True)
        else:
            st.info("当前没有可展示的 Test Plan")
        return

    if active_listener_tab == "Summary Report":
        if not perf_result:
            st.info("当前没有执行结果")
        else:
            summary = perf_result.get("summary", {})
            summary_df = pd.DataFrame([_build_jmeter_summary_row(perf_result)])
            st.markdown('<div class="jmeter-field-card"><strong>Summary Listener</strong> 汇总总样本数、成功率、吞吐和分位耗时。</div>', unsafe_allow_html=True)
            summary_action_col1, summary_action_col2, summary_action_col3 = st.columns(3)
            with summary_action_col1:
                if st.button("查看全部样本", key="summary_open_all_samples", use_container_width=True):
                    _open_results_tree()
                    st.rerun()
            with summary_action_col2:
                if st.button("查看失败样本", key="summary_open_failed_samples", use_container_width=True):
                    _open_results_tree(only_errors=True)
                    st.rerun()
            with summary_action_col3:
                if st.button("打开下载中心", key="summary_open_downloads", use_container_width=True):
                    _open_listener_view("Downloads")
                    st.rerun()
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
            with metric_col1:
                st.metric("Samples", summary.get("total_requests", 0))
            with metric_col2:
                st.metric("Success %", f"{summary.get('success_rate', 0):.1f}%")
            with metric_col3:
                st.metric("Average", f"{summary.get('avg_ms', 0):.2f} ms")
            with metric_col4:
                st.metric("P90", f"{summary.get('p90_ms', 0):.2f} ms")
            with metric_col5:
                st.metric("P95", f"{summary.get('p95_ms', 0):.2f} ms")
            with metric_col6:
                st.metric("Throughput", f"{summary.get('throughput_rps', 0):.2f} rps")
            _render_report_table_workbench(
                "summary_report",
                "Summary Table",
                summary_df,
                "summary_report.csv",
                empty_hint="当前没有 Summary 数据",
                default_columns=["Label", "# Samples", "Average", "90% Line", "Error %", "Throughput"],
                default_sort="Average",
            )
        return

    if active_listener_tab == "Aggregate Report":
        if perf_result:
            aggregate_df = pd.DataFrame(_build_jmeter_aggregate_rows(perf_result))
            st.markdown('<div class="jmeter-field-card"><strong>Aggregate Listener</strong> 按 Sampler 聚合耗时、错误率和吞吐。</div>', unsafe_allow_html=True)
            agg_col1, agg_col2 = st.columns(2)
            with agg_col1:
                if st.button("查看样本树", key="aggregate_open_tree", use_container_width=True):
                    _open_results_tree()
                    st.rerun()
            with agg_col2:
                if st.button("查看错误列表", key="aggregate_open_errors", use_container_width=True):
                    _open_listener_view("Errors")
                    st.rerun()
            _render_report_table_workbench(
                "aggregate_report",
                "Aggregate Table",
                aggregate_df,
                "aggregate_report.csv",
                empty_hint="当前没有 Aggregate 数据",
                default_columns=["Label", "# Samples", "Average", "90% Line", "Error %", "Throughput"],
                default_sort="Average",
            )
        else:
            st.info("当前没有执行结果")
        return

    if active_listener_tab == "View Results Tree":
        if not perf_result:
            st.info("当前没有执行结果")
            return
        tree_rows = _build_results_tree_rows(perf_result)
        filtered_rows = _filter_result_tree_rows(tree_rows)
        if not filtered_rows:
            st.info("过滤后没有样本结果")
            return

        st.markdown(
            '<div class="jmeter-sample-browser"><strong>Sample Browser</strong> 左侧样本列表支持过滤失败项，右侧按 JMeter 思路查看请求、响应和断言结果。</div>',
            unsafe_allow_html=True,
        )
        tree_col1, tree_col2 = st.columns([1.15, 2.05])
        with tree_col1:
            selected_sample_key = _render_results_tree_sidebar(filtered_rows, perf_result)
        with tree_col2:
            sample = perf_result.get("samples", [])[selected_sample_key]
            detail_tabs = ["Sampler Result", "Request", "Request Headers", "Request Body", "Response Headers", "Response Data", "Assertion Result"]
            active_detail_tab = _render_button_tab_bar(
                detail_tabs,
                "api_perf_result_detail_tab",
                "api_perf_result_detail_tab_button",
                "Result Detail Tabs",
                "模拟 JMeter 的 View Results Tree 详情页签。",
            )
            if active_detail_tab == "Sampler Result":
                _render_sampler_result_summary(sample)
            elif active_detail_tab == "Request":
                st.code(_build_sampler_request_preview(perf_plan, sample), language="json")
            elif active_detail_tab == "Request Headers":
                st.code(_build_request_headers_preview(sample), language="json")
            elif active_detail_tab == "Request Body":
                request_body_preview = sample.get("request_body_preview", "")
                if request_body_preview:
                    st.code(request_body_preview, language="json")
                else:
                    st.info("当前样本没有请求体")
            elif active_detail_tab == "Response Headers":
                response_headers_preview = _build_response_headers_preview(sample)
                if response_headers_preview and response_headers_preview != "{}":
                    st.code(response_headers_preview, language="json")
                else:
                    st.info("当前样本没有可展示的响应头")
            elif active_detail_tab == "Response Data":
                response_preview = sample.get("response_preview", "")
                if response_preview:
                    st.code(response_preview, language="json")
                else:
                    st.info("当前样本没有可展示的响应预览")
            else:
                _render_assertion_result_tree(perf_plan, sample)
        return

    if active_listener_tab == "Graph Results":
        if perf_result and perf_result.get("timeline"):
            st.markdown('<div class="jmeter-field-card"><strong>Graph Results</strong> 展示每秒请求量、失败数和时延变化。</div>', unsafe_allow_html=True)
            timeline_df = pd.DataFrame(perf_result.get("timeline", []))
            if not timeline_df.empty:
                chart_col1, chart_col2 = st.columns(2)
                with chart_col1:
                    st.line_chart(timeline_df.set_index("second_bucket")[["requests", "failures"]])
                with chart_col2:
                    st.line_chart(timeline_df.set_index("second_bucket")[["avg_ms", "max_ms"]])
        else:
            st.info("当前没有可视化结果")
        return

    if active_listener_tab == "Errors":
        if perf_result:
            error_samples = perf_result.get("error_samples", [])
            if error_samples:
                errors_df = pd.DataFrame(error_samples)
                st.markdown('<div class="jmeter-field-card"><strong>Error Samples</strong> 这里集中查看失败样本，方便快速定位接口或断言问题。</div>', unsafe_allow_html=True)
                error_col1, error_col2 = st.columns(2)
                with error_col1:
                    if st.button("跳到失败样本树", key="errors_open_tree", use_container_width=True):
                        _open_results_tree(only_errors=True)
                        st.rerun()
                with error_col2:
                    if st.button("打开响应详情", key="errors_open_response_data", use_container_width=True):
                        _open_results_tree(detail_tab="Response Data", only_errors=True)
                        st.rerun()
                _render_report_table_workbench(
                    "errors_report",
                    "Error Table",
                    errors_df,
                    "error_samples.csv",
                    empty_hint="当前没有错误样本",
                    default_columns=list(errors_df.columns[: min(6, len(errors_df.columns))]),
                )
            else:
                st.success("✅ 本次压测未出现失败样本")
        else:
            st.info("当前没有执行结果")
        return

    if active_listener_tab == "Transactions":
        if perf_result:
            transaction_rows = perf_result.get("per_transaction", [])
            if transaction_rows:
                transaction_df = pd.DataFrame(
                    [
                        {
                            "Label": row.get("transaction_name", ""),
                            "# Samples": row.get("transactions", 0),
                            "Average": row.get("avg_ms", 0.0),
                            "90% Line": row.get("p90_ms", 0.0),
                            "95% Line": row.get("p95_ms", 0.0),
                            "Max": row.get("max_ms", 0.0),
                            "Error %": round(
                                (float(row.get("failed_transactions", 0) or 0) / float(row.get("transactions", 1) or 1)) * 100,
                                2,
                            ),
                        }
                        for row in transaction_rows
                    ]
                )
                st.markdown('<div class="jmeter-field-card"><strong>Transaction Controller Report</strong> 查看事务级吞吐、分位耗时和错误率。</div>', unsafe_allow_html=True)
                tx_col1, tx_col2 = st.columns(2)
                with tx_col1:
                    if st.button("查看汇总报表", key="transactions_open_summary", use_container_width=True):
                        _open_listener_view("Summary Report")
                        st.rerun()
                with tx_col2:
                    if st.button("查看样本树", key="transactions_open_tree", use_container_width=True):
                        _open_results_tree()
                        st.rerun()
                _render_report_table_workbench(
                    "transactions_report",
                    "Transaction Table",
                    transaction_df,
                    "transaction_report.csv",
                    empty_hint="当前没有事务报表数据",
                    default_columns=["Label", "# Samples", "Average", "90% Line", "Error %"],
                    default_sort="Average",
                )
            transaction_samples = perf_result.get("transaction_samples", [])
            if transaction_samples:
                st.markdown("#### Transaction Samples")
                _render_report_table_workbench(
                    "transaction_samples_report",
                    "Transaction Sample Table",
                    pd.DataFrame(transaction_samples[:200]),
                    "transaction_samples.csv",
                    empty_hint="当前没有事务样本数据",
                    default_columns=list(pd.DataFrame(transaction_samples[:200]).columns[: min(6, len(pd.DataFrame(transaction_samples[:200]).columns))]),
                )
            if not transaction_rows and not transaction_samples:
                st.info("当前未启用 Transaction Controller 或没有事务结果")
        else:
            st.info("当前没有执行结果")
        return

    if not perf_result:
        st.info("执行压测后可下载报告")
        return

    result_json = json.dumps(
        {
            "summary": perf_result.get("summary", {}),
            "per_sampler": perf_result.get("per_sampler", []),
            "per_transaction": perf_result.get("per_transaction", []),
            "timeline": perf_result.get("timeline", []),
            "error_samples": perf_result.get("error_samples", []),
            "summary_listener": perf_result.get("summary_listener", []),
        },
        ensure_ascii=False,
        indent=2,
    )
    result_csv = pd.DataFrame(perf_result.get("samples", [])).to_csv(index=False, encoding="utf-8-sig")
    html_report = perf_result.get("html_report", "")
    st.markdown('<div class="jmeter-field-card"><strong>Downloads</strong> 保留 HTML、JSON 和样本 CSV 三种导出。</div>', unsafe_allow_html=True)
    download_col1, download_col2, download_col3 = st.columns(3)
    with download_col1:
        st.download_button(
            label="📥 HTML Report",
            data=html_report,
            file_name="performance_report.html",
            mime="text/html",
            use_container_width=True,
            key="download_performance_html",
        )
    with download_col2:
        st.download_button(
            label="📥 JSON Report",
            data=result_json,
            file_name="performance_report.json",
            mime="application/json",
            use_container_width=True,
            key="download_performance_json",
        )
    with download_col3:
        st.download_button(
            label="📥 CSV Samples",
            data=result_csv.encode("utf-8-sig"),
            file_name="performance_samples.csv",
            mime="text/csv",
            use_container_width=True,
            key="download_performance_csv",
        )


def _render_active_panel(selected_node, parser: InterfaceAutoTestCore, perf_interfaces):
    panel_title, panel_desc = PANEL_META[selected_node]
    st.markdown(f"### {panel_title}")
    st.caption(panel_desc)
    _render_property_toolbar(selected_node, perf_interfaces)

    if selected_node == "test_plan":
        _render_test_plan_panel(parser, perf_interfaces)
        return
    if selected_node == "thread_group":
        _render_thread_group_panel()
        return
    if selected_node == "http_defaults":
        _render_http_defaults_panel()
        return
    if selected_node == "samplers":
        if perf_interfaces:
            _render_samplers_panel(perf_interfaces)
        else:
            st.info("请先在 Test Plan 中导入接口文档。")
        return
    if selected_node == "csv_data":
        _render_csv_panel()
        return
    if selected_node == "transaction":
        _render_transaction_panel()
        return
    if selected_node == "assertions":
        _render_assertion_panel()
        return
    if selected_node == "timer":
        _render_timer_panel()
        return
    st.info("Listener 结果区固定显示在页面底部，便于像 JMeter 一样随时查看执行结果。")


def render_api_performance_test_page():
    _ensure_perf_defaults()
    _sync_http_fields_from_base_url()
    _render_styles()

    if "interface_perf_parser" not in st.session_state:
        st.session_state.interface_perf_parser = InterfaceAutoTestCore()
    if "performance_test_tool" not in st.session_state:
        st.session_state.performance_test_tool = PerformanceTestTool()

    parser = st.session_state.interface_perf_parser
    performance_tool = st.session_state.performance_test_tool
    perf_interfaces = st.session_state.get("interface_perf_interfaces", [])
    perf_result = st.session_state.get("interface_perf_result")

    st.markdown('<div class="category-card">🚀 接口性能测试</div>', unsafe_allow_html=True)
    _render_menu_bar()
    st.markdown(
        '<div class="jmeter-caption">按 JMeter 的思路组织页面: 左侧测试计划树，右侧节点配置，底部 Listener 结果区。</div>',
        unsafe_allow_html=True,
    )

    _render_execution_toolbar(perf_interfaces, performance_tool)
    _render_execution_status(perf_interfaces)
    _render_horizontal_splitter("Workspace")

    tree_col, splitter_col, panel_col = st.columns([1, 0.08, 2.5])
    with tree_col:
        st.markdown('<div class="jmeter-section"><div class="jmeter-panel-title">Tree</div></div>', unsafe_allow_html=True)
        selected_node = _render_tree_panel(perf_interfaces)

    with splitter_col:
        _render_vertical_splitter()

    with panel_col:
        st.markdown('<div class="jmeter-section"><div class="jmeter-panel-title">Property Panel</div>当前选中节点的配置属性会显示在这里。</div>', unsafe_allow_html=True)
        _render_active_panel(selected_node, parser, perf_interfaces)

    _render_horizontal_splitter("Listener Dock")
    st.markdown('<div class="jmeter-dock"><div class="jmeter-panel-title">Listener Dock</div>模拟 JMeter 底部 Listener 区，执行后可切换查看不同报表。</div>', unsafe_allow_html=True)
    _render_listener_panel()

    status_text = "Ready"
    result_text = "No samples"
    if perf_result:
        summary = perf_result.get("summary", {})
        status_text = f"Last Run: {summary.get('finished_at', '')}"
        result_text = f"Samples={summary.get('total_requests', 0)} | Error%={100 - float(summary.get('success_rate', 0.0) or 0.0):.1f}"
    st.markdown(
        f'<div class="jmeter-statusbar"><span>{status_text}</span><span>{result_text}</span></div>',
        unsafe_allow_html=True,
    )
