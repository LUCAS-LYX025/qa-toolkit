import json
import os
import tempfile
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st

from qa_toolkit.core.api_security_tool import SecurityTestTool
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore
from qa_toolkit.core.application_security_tool import ApplicationSecurityTool
from qa_toolkit.ui.components.workflow_panels import render_download_panel, render_workflow_guide


INTERFACE_FILE_TYPES = ["xlsx", "xls", "json", "har", "bru", "txt", "md", "yaml", "yml"]
RAW_FORMAT_MAP = {
    "自动检测": "auto",
    "JSON / OpenAPI / Postman / HAR / Insomnia": "json",
    "Swagger/OpenAPI": "swagger",
    "结构化文本": "text",
    "Bruno .bru": "bruno",
}
DEFAULT_STATE = {
    "api_sec_interfaces": [],
    "api_sec_source_name": "",
    "api_sec_source_type": "",
    "api_sec_raw_format": "自动检测",
    "api_sec_raw_text": "",
    "api_sec_selected_indexes": [],
    "api_sec_base_url": "",
    "api_sec_timeout": 15.0,
    "api_sec_verify_ssl": True,
    "api_sec_origin": "https://security-audit.local",
    "api_sec_auth_headers_text": "{}",
    "api_sec_roles_text": "匿名用户\n普通用户\n管理员\n跨租户用户",
    "api_sec_role_profiles_text": json.dumps(
        [
            {"role": "匿名用户", "headers": {}},
            {"role": "普通用户", "headers": {"Authorization": "Bearer <user-token>"}},
            {"role": "管理员", "headers": {"Authorization": "Bearer <admin-token>"}},
        ],
        ensure_ascii=False,
        indent=2,
    ),
    "app_sec_mobile_keywords_text": "xposed\nssl\ncertificate pinning\nroot\njailbreak\ndebug",
    "app_sec_web_url": "",
    "app_sec_web_headers_text": "{}",
    "app_sec_web_timeout": 12.0,
    "app_sec_web_verify_ssl": True,
    "app_sec_web_max_pages": 8,
    "app_sec_web_include_common_paths": True,
}


def _ensure_security_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _reset_security_outputs():
    for key in [
        "api_sec_plan",
        "api_sec_scan_policy",
        "api_sec_passive_report",
        "api_sec_probe_report",
        "api_sec_owasp_checklist",
        "api_sec_auth_matrix",
        "api_sec_nuclei_pack",
        "api_sec_risk_dashboard",
        "api_sec_regression_suite",
        "api_sec_role_regression",
        "api_sec_bundle",
        "app_sec_mobile_report",
        "app_sec_web_report",
    ]:
        st.session_state.pop(key, None)


def _reset_security_workspace():
    for key, value in DEFAULT_STATE.items():
        st.session_state[key] = value
    _reset_security_outputs()


def _render_styles():
    st.markdown(
        """
        <style>
        .security-banner {
            background: linear-gradient(135deg, #0f172a 0%, #14532d 100%);
            border-radius: 18px;
            padding: 1.3rem 1.5rem;
            color: #f8fafc;
            margin-bottom: 1rem;
            box-shadow: 0 18px 32px rgba(15, 23, 42, 0.18);
        }
        .security-banner h3 {
            margin: 0 0 0.35rem 0;
            font-size: 1.3rem;
        }
        .security-banner p {
            margin: 0;
            color: rgba(248, 250, 252, 0.88);
            line-height: 1.6;
        }
        .security-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.85rem;
            margin: 0.9rem 0 1rem 0;
        }
        .security-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid #d9e2ec;
            border-radius: 14px;
            padding: 0.95rem 1rem;
            box-shadow: 0 10px 22px rgba(15, 23, 42, 0.06);
        }
        .security-card-title {
            font-size: 0.98rem;
            font-weight: 700;
            color: #0f172a;
            margin-bottom: 0.35rem;
        }
        .security-card-desc {
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.55;
        }
        .security-section {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 1rem 1.1rem;
            box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
            margin-bottom: 1rem;
        }
        .security-section-title {
            color: #0f172a;
            font-size: 1.05rem;
            font-weight: 700;
            margin-bottom: 0.8rem;
        }
        .security-note {
            background: #f8fafc;
            border-left: 4px solid #16a34a;
            border-radius: 10px;
            padding: 0.85rem 0.95rem;
            color: #334155;
            line-height: 1.6;
            margin: 0.75rem 0;
        }
        .security-mini-tag {
            display: inline-block;
            background: #ecfdf5;
            color: #166534;
            border: 1px solid #bbf7d0;
            border-radius: 999px;
            padding: 0.16rem 0.55rem;
            margin-right: 0.35rem;
            margin-bottom: 0.35rem;
            font-size: 0.8rem;
            font-weight: 600;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_design_cards():
    cards = [
        ("Burp Scanner", "参考范围、认证扫描和审计任务组织方式，先定授权范围，再执行有状态安全基线探测。"),
        ("OWASP ZAP", "参考被动扫描与策略思路，把头部、CORS、Cookie、错误泄露做成低风险安全基线。"),
        ("ApplicationScanner", "参考 APK/IPA 静态分析清单，把 Manifest、Info.plist、权限、组件和证书线索整合起来。"),
        ("HCL AppScan", "参考站点入口+轻量爬取+结果工作台的模式，支持直接粘贴 URL 做站点基线扫描。"),
        ("OWASP WSTG / API Top 10", "把自动发现和人工复核拆开，输出对象级授权、功能权限、业务流等清单。"),
        ("Nuclei", "参考模板化和回归思路，把发现结果沉淀为 JSON/Markdown 报告与复测清单。"),
    ]
    html_parts = ['<div class="security-grid">']
    for title, description in cards:
        html_parts.append(
            "<div class='security-card'>"
            f"<div class='security-card-title'>{title}</div>"
            f"<div class='security-card-desc'>{description}</div>"
            "</div>"
        )
    html_parts.append("</div>")
    st.markdown("".join(html_parts), unsafe_allow_html=True)


def _template_items(core: InterfaceAutoTestCore) -> List[Tuple[str, str, Any, str]]:
    return [
        ("Excel 模版", "api_security_template.xlsx", core.build_excel_template_bytes(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
        ("JSON 模版", "api_security_template.json", core.build_json_template(), "application/json"),
        ("结构化文本模版", "api_security_template.txt", core.build_text_template(), "text/plain"),
        ("OpenAPI JSON 模版", "api_security_openapi.json", core.build_openapi_template(), "application/json"),
        ("OpenAPI YAML 模版", "api_security_openapi.yaml", core.build_openapi_yaml_template(), "text/yaml"),
        ("curl 模版", "api_security_curl.txt", core.build_curl_template(), "text/plain"),
        ("Postman 模版", "api_security_postman.json", core.build_postman_template(), "application/json"),
        ("HAR 模版", "api_security.har", core.build_har_template(), "application/json"),
        ("Bruno 模版", "api_security.bru", core.build_bruno_template(), "text/plain"),
        ("Insomnia 模版", "api_security_insomnia.json", core.build_insomnia_template(), "application/json"),
    ]


def _example_items(core: InterfaceAutoTestCore) -> List[Tuple[str, str, str]]:
    return [
        ("结构化文本示例", core.build_text_template(), "结构化文本"),
        ("curl 示例", core.build_curl_template(), "结构化文本"),
        ("OpenAPI YAML 示例", core.build_openapi_yaml_template(), "Swagger/OpenAPI"),
        ("Bruno 示例", core.build_bruno_template(), "Bruno .bru"),
    ]


def _load_uploaded_interfaces(core: InterfaceAutoTestCore, uploaded_file) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    suffix = os.path.splitext(uploaded_file.name)[1] or ".txt"
    temp_path = ""
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            temp_file.write(uploaded_file.getbuffer())
            temp_path = temp_file.name
        interfaces = core.parse_document(temp_path)
        return interfaces, dict(core.last_parse_meta)
    finally:
        if temp_path and os.path.exists(temp_path):
            os.unlink(temp_path)


def _store_interfaces(interfaces: List[Dict[str, Any]], parse_meta: Dict[str, Any]):
    st.session_state.api_sec_interfaces = interfaces
    st.session_state.api_sec_source_name = parse_meta.get("source_name", "") or "inline"
    st.session_state.api_sec_source_type = parse_meta.get("source_type", "") or "auto"
    st.session_state.api_sec_selected_indexes = list(range(len(interfaces)))
    detected_base_url = parse_meta.get("detected_base_url", "")
    if detected_base_url:
        st.session_state.api_sec_base_url = detected_base_url
    _reset_security_outputs()


def _parse_json_object(text: str, label: str) -> Dict[str, Any]:
    raw_text = (text or "").strip()
    if not raw_text:
        return {}
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} JSON 解析失败: {exc}") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label}必须是 JSON 对象，例如 {{\"Authorization\": \"Bearer xxx\"}}")
    return parsed


def _parse_auth_headers(text: str) -> Dict[str, Any]:
    return _parse_json_object(text, "鉴权头")


def _parse_roles(text: str) -> List[str]:
    items = []
    for raw_line in str(text or "").replace("，", ",").splitlines():
        for piece in raw_line.split(","):
            role = piece.strip()
            if role and role not in items:
                items.append(role)
    return items or ["匿名用户", "普通用户", "管理员", "跨租户用户"]


def _parse_role_profiles(text: str) -> List[Dict[str, Any]]:
    raw_text = (text or "").strip()
    if not raw_text:
        return [{"role": "匿名用户", "headers": {}}]
    try:
        parsed = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"多角色凭证 JSON 解析失败: {exc}") from exc
    if not isinstance(parsed, list):
        raise ValueError("多角色凭证必须是 JSON 数组，例如 [{\"role\": \"普通用户\", \"headers\": {...}}]")
    profiles = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or item.get("name") or "").strip()
        headers = item.get("headers") if isinstance(item.get("headers"), dict) else {}
        if role:
            profiles.append({"role": role, "headers": headers})
    if not profiles:
        raise ValueError("多角色凭证里至少需要一个包含 role 和 headers 的对象")
    return profiles


def _parse_keyword_lines(text: str) -> List[str]:
    keywords = []
    for raw_line in str(text or "").splitlines():
        for piece in raw_line.replace("，", ",").split(","):
            keyword = piece.strip()
            if keyword and keyword not in keywords:
                keywords.append(keyword)
    return keywords


def _build_interface_labels(interfaces: List[Dict[str, Any]]) -> Dict[int, str]:
    labels = {}
    for index, item in enumerate(interfaces):
        method = str(item.get("method") or "GET").upper()
        path = str(item.get("path") or "/")
        name = str(item.get("name") or "").strip()
        labels[index] = f"[{index + 1:02d}] {method} {path} | {name or '未命名接口'}"
    return labels


def _get_quick_pick_indexes(interfaces: List[Dict[str, Any]], mode: str) -> List[int]:
    picks: List[int] = []
    for index, item in enumerate(interfaces):
        method = str(item.get("method") or "GET").upper()
        blob = " ".join(
            [
                method,
                str(item.get("path") or ""),
                str(item.get("name") or ""),
                str(item.get("description") or ""),
            ]
        ).lower()
        if mode == "write" and method in {"POST", "PUT", "PATCH", "DELETE"}:
            picks.append(index)
        elif mode == "sensitive" and any(
            hint in blob for hint in ["admin", "internal", "debug", "auth", "login", "token", "user", "payment", "pay", "order", "export", "upload"]
        ):
            picks.append(index)
    return picks


def _render_source_section(core: InterfaceAutoTestCore):
    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">1. 导入接口文档</div>', unsafe_allow_html=True)
    st.caption("支持 Excel、JSON、OpenAPI、Postman、HAR、Bruno、Insomnia、结构化文本等格式。")

    left_col, right_col = st.columns([1.05, 1.2])

    with left_col:
        template_items = _template_items(core)
        uploaded_file = st.file_uploader(
            "上传接口文档",
            type=INTERFACE_FILE_TYPES,
            key="api_sec_upload",
            help="支持导入接口清单、OpenAPI、抓包文件或调试工具导出内容。",
        )
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("📂 解析上传文档", key="api_sec_parse_upload", use_container_width=True):
                if not uploaded_file:
                    st.warning("请先选择需要上传的接口文档。")
                else:
                    try:
                        interfaces, parse_meta = _load_uploaded_interfaces(core, uploaded_file)
                        _store_interfaces(interfaces, parse_meta)
                        st.success(f"已解析 {len(interfaces)} 个接口，来源: {uploaded_file.name}")
                    except Exception as exc:
                        st.error(f"解析上传文档失败: {exc}")
        with action_col2:
            if st.button("🧹 清空安全工作台", key="api_sec_reset_workspace", use_container_width=True):
                _reset_security_workspace()
                st.rerun()

        with st.expander("⬇️ 上传模版下载", expanded=False):
            for row_start in range(0, len(template_items), 2):
                row_items = template_items[row_start:row_start + 2]
                row_cols = st.columns(len(row_items))
                for col, item in zip(row_cols, row_items):
                    label, file_name, data, mime = item
                    with col:
                        st.download_button(
                            label=label,
                            data=data,
                            file_name=file_name,
                            mime=mime,
                            use_container_width=True,
                            key=f"download_template_{file_name}",
                        )

    with right_col:
        example_items = _example_items(core)
        example_cols = st.columns(len(example_items))
        for col, (label, text, raw_format) in zip(example_cols, example_items):
            with col:
                if st.button(label, key=f"api_sec_example_{label}", use_container_width=True):
                    st.session_state.api_sec_raw_text = text
                    st.session_state.api_sec_raw_format = raw_format
                    st.rerun()

        st.selectbox(
            "原始文本格式",
            list(RAW_FORMAT_MAP.keys()),
            key="api_sec_raw_format",
            help="如果不确定格式，优先使用自动检测。",
        )
        st.text_area(
            "原始文本 / OpenAPI / curl / Bruno",
            key="api_sec_raw_text",
            height=280,
            placeholder="可直接粘贴 OpenAPI、curl、结构化文本或 Bruno 内容。",
        )
        text_action_col1, text_action_col2 = st.columns(2)
        with text_action_col1:
            if st.button("📝 解析原始文本", key="api_sec_parse_text", use_container_width=True):
                raw_text = st.session_state.get("api_sec_raw_text", "").strip()
                if not raw_text:
                    st.warning("请先粘贴需要解析的原始文本。")
                else:
                    try:
                        interfaces = core.parse_content(
                            raw_text,
                            source_type=RAW_FORMAT_MAP[st.session_state.api_sec_raw_format],
                            source_name="inline",
                        )
                        _store_interfaces(interfaces, dict(core.last_parse_meta))
                        st.success(f"已解析 {len(interfaces)} 个接口。")
                    except Exception as exc:
                        st.error(f"解析原始文本失败: {exc}")
        with text_action_col2:
            if st.button("🧾 填充鉴权头示例", key="api_sec_fill_auth_example", use_container_width=True):
                st.session_state.api_sec_auth_headers_text = json.dumps(
                    {
                        "Authorization": "Bearer <token>",
                        "Cookie": "sessionid=<session>",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                st.rerun()

    st.markdown("</div>", unsafe_allow_html=True)


def _render_scope_section(interfaces: List[Dict[str, Any]], source_name: str, source_type: str):
    labels = _build_interface_labels(interfaces)
    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">2. 范围与鉴权配置</div>', unsafe_allow_html=True)
    meta_col1, meta_col2, meta_col3, meta_col4 = st.columns(4)
    meta_col1.metric("接口数量", len(interfaces))
    meta_col2.metric("当前选择", len(st.session_state.get("api_sec_selected_indexes", [])))
    meta_col3.metric("来源", source_type or "auto")
    meta_col4.metric("文档名", source_name or "inline")

    pick_col1, pick_col2, pick_col3, pick_col4 = st.columns(4)
    with pick_col1:
        if st.button("全选接口", key="api_sec_pick_all", use_container_width=True):
            st.session_state.api_sec_selected_indexes = list(range(len(interfaces)))
            st.rerun()
    with pick_col2:
        if st.button("仅写操作", key="api_sec_pick_write", use_container_width=True):
            st.session_state.api_sec_selected_indexes = _get_quick_pick_indexes(interfaces, "write")
            st.rerun()
    with pick_col3:
        if st.button("仅敏感接口", key="api_sec_pick_sensitive", use_container_width=True):
            st.session_state.api_sec_selected_indexes = _get_quick_pick_indexes(interfaces, "sensitive")
            st.rerun()
    with pick_col4:
        if st.button("清空选择", key="api_sec_pick_none", use_container_width=True):
            st.session_state.api_sec_selected_indexes = []
            st.rerun()

    st.multiselect(
        "选择进入安全测试范围的接口",
        options=list(labels.keys()),
        format_func=lambda idx: labels[idx],
        key="api_sec_selected_indexes",
    )

    scope_col1, scope_col2 = st.columns([1.15, 1.0])
    with scope_col1:
        st.text_input(
            "Base URL",
            key="api_sec_base_url",
            placeholder="https://api.example.com",
            help="如果文档里只有相对路径，请补充 Base URL 才能执行安全基线探测。",
        )
        inner_col1, inner_col2 = st.columns(2)
        with inner_col1:
            st.number_input("超时(秒)", min_value=1.0, max_value=120.0, key="api_sec_timeout", step=1.0)
        with inner_col2:
            st.checkbox("校验证书", key="api_sec_verify_ssl")
        st.text_input(
            "Origin 头",
            key="api_sec_origin",
            help="基线探测会复用该 Origin 检查 CORS 配置。",
        )
    with scope_col2:
        st.text_area(
            "鉴权头 JSON",
            key="api_sec_auth_headers_text",
            height=166,
            help="例如 {\"Authorization\": \"Bearer xxx\"}。仅用于授权范围内的基线探测。",
        )
        st.download_button(
            label="⬇️ 下载鉴权头模版",
            data=InterfaceAutoTestCore().build_auth_template(),
            file_name="api_security_auth_template.json",
            mime="application/json",
            use_container_width=True,
            key="download_api_sec_auth_template",
        )

    st.text_area(
        "角色/身份列表",
        key="api_sec_roles_text",
        height=96,
        help="按行或逗号分隔，例如: 匿名用户、普通用户、管理员、跨租户用户。",
    )
    with st.expander("👥 多角色凭证配置", expanded=False):
        st.text_area(
            "多角色凭证 JSON",
            key="api_sec_role_profiles_text",
            height=220,
            help="用于执行多角色批量回归，只会发送低风险基线请求。",
        )
        profile_col1, profile_col2 = st.columns(2)
        with profile_col1:
            if st.button("填充多角色示例", key="api_sec_fill_role_profiles", use_container_width=True):
                st.session_state.api_sec_role_profiles_text = json.dumps(
                    [
                        {"role": "匿名用户", "headers": {}},
                        {"role": "普通用户", "headers": {"Authorization": "Bearer <user-token>"}},
                        {"role": "管理员", "headers": {"Authorization": "Bearer <admin-token>"}},
                    ],
                    ensure_ascii=False,
                    indent=2,
                )
                st.rerun()
        with profile_col2:
            st.download_button(
                label="下载多角色模版",
                data=st.session_state.get("api_sec_role_profiles_text", ""),
                file_name="api_security_role_profiles.json",
                mime="application/json",
                use_container_width=True,
                key="download_api_sec_role_profiles_template",
            )

    st.markdown(
        '<div class="security-note">当前模块默认采用安全基线模式，只做被动审计和低风险探测。不会主动发送注入、爆破、越权利用、批量 fuzz 等破坏性 payload。</div>',
        unsafe_allow_html=True,
    )

    summary_rows = []
    for index, item in enumerate(interfaces):
        summary_rows.append(
            {
                "Selected": index in st.session_state.get("api_sec_selected_indexes", []),
                "Method": str(item.get("method") or "GET").upper(),
                "Path": item.get("path", ""),
                "Name": item.get("name", ""),
                "Description": item.get("description", ""),
            }
        )
    st.dataframe(pd.DataFrame(summary_rows), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)


def _render_action_bar(tool: SecurityTestTool, interfaces: List[Dict[str, Any]]):
    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">3. 安全测试动作</div>', unsafe_allow_html=True)

    try:
        auth_headers = _parse_auth_headers(st.session_state.get("api_sec_auth_headers_text", "{}"))
    except ValueError as exc:
        st.error(str(exc))
        auth_headers = None
    try:
        role_profiles = _parse_role_profiles(st.session_state.get("api_sec_role_profiles_text", ""))
    except ValueError as exc:
        st.error(str(exc))
        role_profiles = None

    selected_indexes = st.session_state.get("api_sec_selected_indexes", [])
    base_url = str(st.session_state.get("api_sec_base_url", "") or "").strip()
    timeout_seconds = float(st.session_state.get("api_sec_timeout", 15.0) or 15.0)
    verify_ssl = bool(st.session_state.get("api_sec_verify_ssl", True))
    origin = str(st.session_state.get("api_sec_origin", "https://security-audit.local") or "https://security-audit.local").strip()
    roles = _parse_roles(st.session_state.get("api_sec_roles_text", ""))

    action_col1, action_col2, action_col3, action_col4, action_col5 = st.columns(5)

    with action_col1:
        if st.button("🧭 生成安全方案", key="api_sec_build_plan", use_container_width=True):
            if auth_headers is None:
                st.stop()
            st.session_state.api_sec_plan = tool.build_security_plan(
                interfaces=interfaces,
                base_url=base_url,
                selected_indexes=selected_indexes,
                auth_headers=auth_headers,
                timeout_seconds=timeout_seconds,
                verify_ssl=verify_ssl,
                origin=origin,
            )
            st.session_state.api_sec_scan_policy = tool.build_scan_policy(st.session_state.api_sec_plan)
            st.session_state.api_sec_bundle = None
            st.success("安全测试方案已生成。")

    with action_col2:
        if st.button("🔍 执行被动审计", key="api_sec_run_passive", use_container_width=True):
            st.session_state.api_sec_passive_report = tool.analyze_interfaces(
                interfaces=interfaces,
                base_url=base_url,
                selected_indexes=selected_indexes,
            )
            st.session_state.api_sec_owasp_checklist = tool.build_owasp_checklist(
                st.session_state.get("api_sec_passive_report"),
                st.session_state.get("api_sec_probe_report"),
            )
            if "api_sec_plan" in st.session_state:
                st.session_state.api_sec_scan_policy = tool.build_scan_policy(
                    st.session_state.api_sec_plan,
                    st.session_state.get("api_sec_passive_report"),
                    st.session_state.get("api_sec_probe_report"),
                )
            st.session_state.api_sec_bundle = None
            st.success("被动审计已完成。")

    with action_col3:
        if st.button("🛰️ 执行基线探测", key="api_sec_run_probe", use_container_width=True):
            if auth_headers is None:
                st.stop()
            with st.spinner("正在执行低风险安全基线探测..."):
                st.session_state.api_sec_probe_report = tool.run_baseline_probe(
                    interfaces=interfaces,
                    base_url=base_url,
                    selected_indexes=selected_indexes,
                    auth_headers=auth_headers,
                    verify_ssl=verify_ssl,
                    timeout_seconds=timeout_seconds,
                    origin=origin,
                )
            st.session_state.api_sec_owasp_checklist = tool.build_owasp_checklist(
                st.session_state.get("api_sec_passive_report"),
                st.session_state.get("api_sec_probe_report"),
            )
            if "api_sec_plan" in st.session_state:
                st.session_state.api_sec_scan_policy = tool.build_scan_policy(
                    st.session_state.api_sec_plan,
                    st.session_state.get("api_sec_passive_report"),
                    st.session_state.get("api_sec_probe_report"),
                )
            st.session_state.api_sec_bundle = None
            st.success("安全基线探测已完成。")

    with action_col4:
        if st.button("📚 刷新 OWASP 清单", key="api_sec_refresh_checklist", use_container_width=True):
            st.session_state.api_sec_owasp_checklist = tool.build_owasp_checklist(
                st.session_state.get("api_sec_passive_report"),
                st.session_state.get("api_sec_probe_report"),
            )
            st.session_state.api_sec_bundle = None
            st.success("OWASP 清单已刷新。")

    with action_col5:
        if st.button("📦 一键生成完整报告", key="api_sec_bundle_report", use_container_width=True):
            if auth_headers is None:
                st.stop()
            with st.spinner("正在构建安全方案、被动审计、基线探测和报告..."):
                plan = tool.build_security_plan(
                    interfaces=interfaces,
                    base_url=base_url,
                    selected_indexes=selected_indexes,
                    auth_headers=auth_headers,
                    timeout_seconds=timeout_seconds,
                    verify_ssl=verify_ssl,
                    origin=origin,
                )
                passive_report = tool.analyze_interfaces(
                    interfaces=interfaces,
                    base_url=base_url,
                    selected_indexes=selected_indexes,
                )
                probe_report = tool.run_baseline_probe(
                    interfaces=interfaces,
                    base_url=base_url,
                    selected_indexes=selected_indexes,
                    auth_headers=auth_headers,
                    verify_ssl=verify_ssl,
                    timeout_seconds=timeout_seconds,
                    origin=origin,
                )
                checklist = tool.build_owasp_checklist(passive_report, probe_report)
                role_regression = (
                    tool.run_role_batch_regression(
                        interfaces=interfaces,
                        role_profiles=role_profiles,
                        base_url=base_url,
                        selected_indexes=selected_indexes,
                        verify_ssl=verify_ssl,
                        timeout_seconds=timeout_seconds,
                        origin=origin,
                    )
                    if role_profiles is not None
                    else {}
                )
                auth_matrix = tool.build_authorization_matrix(
                    interfaces=interfaces,
                    selected_indexes=selected_indexes,
                    roles=roles,
                )
                nuclei_pack = tool.build_nuclei_template_pack(
                    interfaces=interfaces,
                    selected_indexes=selected_indexes,
                    origin=origin,
                    auth_headers=auth_headers,
                )
                risk_dashboard = tool.build_risk_dashboard(
                    passive_report=passive_report,
                    probe_report=probe_report,
                    role_regression=role_regression,
                    authorization_matrix=auth_matrix,
                )
                regression_suite = tool.build_regression_suite(
                    interfaces=interfaces,
                    selected_indexes=selected_indexes,
                    passive_report=passive_report,
                    probe_report=probe_report,
                    role_regression=role_regression,
                    authorization_matrix=auth_matrix,
                )
                bundle = tool.build_report_bundle(
                    plan,
                    passive_report,
                    probe_report,
                    role_regression,
                    checklist,
                    authorization_matrix=auth_matrix,
                    nuclei_template_pack=nuclei_pack,
                    risk_dashboard=risk_dashboard,
                    regression_suite=regression_suite,
                )
                st.session_state.api_sec_plan = plan
                st.session_state.api_sec_scan_policy = bundle.get("scan_policy", {})
                st.session_state.api_sec_passive_report = passive_report
                st.session_state.api_sec_probe_report = probe_report
                st.session_state.api_sec_role_regression = role_regression
                st.session_state.api_sec_owasp_checklist = checklist
                st.session_state.api_sec_auth_matrix = auth_matrix
                st.session_state.api_sec_nuclei_pack = nuclei_pack
                st.session_state.api_sec_risk_dashboard = risk_dashboard
                st.session_state.api_sec_regression_suite = regression_suite
                st.session_state.api_sec_bundle = bundle
            st.success("完整报告已生成。")

    extra_col1, extra_col2, extra_col3, extra_col4 = st.columns(4)
    with extra_col1:
        if st.button("🔐 生成权限矩阵", key="api_sec_build_auth_matrix", use_container_width=True):
            st.session_state.api_sec_auth_matrix = tool.build_authorization_matrix(
                interfaces=interfaces,
                selected_indexes=selected_indexes,
                roles=roles,
            )
            st.session_state.api_sec_bundle = None
            st.success("权限/角色矩阵已生成。")
    with extra_col2:
        if st.button("🧩 导出 Nuclei 模板", key="api_sec_build_nuclei_pack", use_container_width=True):
            st.session_state.api_sec_nuclei_pack = tool.build_nuclei_template_pack(
                interfaces=interfaces,
                selected_indexes=selected_indexes,
                origin=origin,
                auth_headers=auth_headers or {},
            )
            st.session_state.api_sec_bundle = None
            st.success("Nuclei 风格基线模板已生成。")
    with extra_col3:
        if st.button("📊 生成风险看板", key="api_sec_build_risk_dashboard", use_container_width=True):
            st.session_state.api_sec_risk_dashboard = tool.build_risk_dashboard(
                passive_report=st.session_state.get("api_sec_passive_report"),
                probe_report=st.session_state.get("api_sec_probe_report"),
                role_regression=st.session_state.get("api_sec_role_regression"),
                authorization_matrix=st.session_state.get("api_sec_auth_matrix"),
            )
            st.session_state.api_sec_bundle = None
            st.success("风险看板已生成。")
    with extra_col4:
        if st.button("🗂️ 生成回归套件", key="api_sec_build_regression_suite", use_container_width=True):
            st.session_state.api_sec_regression_suite = tool.build_regression_suite(
                interfaces=interfaces,
                selected_indexes=selected_indexes,
                passive_report=st.session_state.get("api_sec_passive_report"),
                probe_report=st.session_state.get("api_sec_probe_report"),
                role_regression=st.session_state.get("api_sec_role_regression"),
                authorization_matrix=st.session_state.get("api_sec_auth_matrix"),
            )
            st.session_state.api_sec_bundle = None
            st.success("安全回归套件已生成。")

    role_col1, role_col2 = st.columns(2)
    with role_col1:
        if st.button("👥 执行多角色回归", key="api_sec_run_role_regression", use_container_width=True):
            if role_profiles is None:
                st.stop()
            with st.spinner("正在执行多角色低风险回归..."):
                st.session_state.api_sec_role_regression = tool.run_role_batch_regression(
                    interfaces=interfaces,
                    role_profiles=role_profiles,
                    base_url=base_url,
                    selected_indexes=selected_indexes,
                    verify_ssl=verify_ssl,
                    timeout_seconds=timeout_seconds,
                    origin=origin,
                )
            st.session_state.api_sec_bundle = None
            st.success("多角色回归已完成。")
    with role_col2:
        st.caption("多角色回归只使用你提供的已授权凭证，并且只发送 OPTIONS/GET 这类低风险请求。")

    st.markdown("</div>", unsafe_allow_html=True)


def _render_summary_metrics(summary: Dict[str, Any], labels: List[str]):
    columns = st.columns(len(labels))
    for column, label in zip(columns, labels):
        column.metric(label, summary.get(label, summary.get(label.lower(), 0)))


def _render_results(tool: SecurityTestTool):
    plan = st.session_state.get("api_sec_plan")
    passive_report = st.session_state.get("api_sec_passive_report")
    probe_report = st.session_state.get("api_sec_probe_report")
    checklist = st.session_state.get("api_sec_owasp_checklist")
    role_regression = st.session_state.get("api_sec_role_regression")
    auth_matrix = st.session_state.get("api_sec_auth_matrix")
    nuclei_pack = st.session_state.get("api_sec_nuclei_pack")
    risk_dashboard = st.session_state.get("api_sec_risk_dashboard")
    regression_suite = st.session_state.get("api_sec_regression_suite")
    bundle = st.session_state.get("api_sec_bundle")
    scan_policy = st.session_state.get("api_sec_scan_policy")
    try:
        parsed_auth_headers = _parse_auth_headers(st.session_state.get("api_sec_auth_headers_text", "{}"))
    except ValueError:
        parsed_auth_headers = {}

    if not any([plan, passive_report, probe_report, role_regression, checklist, auth_matrix, nuclei_pack, risk_dashboard, regression_suite, bundle]):
        st.info("先导入接口文档并执行上面的安全动作，结果会在这里汇总展示。")
        return

    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">4. 安全测试结果工作台</div>', unsafe_allow_html=True)

    tab_plan, tab_policy, tab_passive, tab_probe, tab_role, tab_risk, tab_auth, tab_owasp, tab_templates, tab_suite, tab_playbook, tab_download = st.tabs(
        ["安全方案", "扫描策略", "被动审计", "基线探测", "多角色回归", "风险看板", "权限矩阵", "OWASP 清单", "Nuclei模板", "回归套件", "测试剧本", "下载导出"]
    )

    with tab_plan:
        if not plan:
            st.info("还没有生成安全方案。")
        else:
            scope = plan.get("scope", {})
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            metric_col1.metric("接口数", scope.get("interface_count", 0))
            metric_col2.metric("目标数", scope.get("target_count", 0))
            metric_col3.metric("超时(秒)", scope.get("timeout_seconds", 0))
            metric_col4.metric("校验证书", "是" if scope.get("verify_ssl", True) else "否")

            st.markdown("**测试策略**")
            for item in plan.get("strategy", []):
                st.markdown(f"- {item}")

            st.markdown("**设计来源**")
            for item in plan.get("tool_inspirations", []):
                st.markdown(f'<span class="security-mini-tag">{item}</span>', unsafe_allow_html=True)

            st.markdown("**目标清单**")
            st.dataframe(pd.DataFrame(plan.get("targets", [])), use_container_width=True, hide_index=True)
            st.caption(plan.get("safety_notice", ""))

    with tab_policy:
        policy_data = scan_policy
        if not policy_data and plan:
            policy_data = tool.build_scan_policy(plan, passive_report, probe_report)
        if not policy_data:
            st.info("先生成安全方案后才能查看扫描策略。")
        else:
            st.markdown("**策略模式**")
            st.write(f"`{policy_data.get('mode', 'safe-baseline')}`")
            st.markdown("**设计映射**")
            st.dataframe(pd.DataFrame(policy_data.get("inspirations", [])), use_container_width=True, hide_index=True)
            st.markdown("**阶段拆分**")
            st.dataframe(pd.DataFrame(policy_data.get("phases", [])), use_container_width=True, hide_index=True)
            st.markdown("**执行边界**")
            for item in policy_data.get("guardrails", []):
                st.markdown(f"- {item}")
            st.markdown("**覆盖摘要**")
            st.dataframe(pd.DataFrame(policy_data.get("coverage", [])), use_container_width=True, hide_index=True)

    with tab_passive:
        if not passive_report:
            st.info("还没有执行被动审计。")
        else:
            summary = passive_report.get("summary", {})
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            metric_col1.metric("发现总数", summary.get("finding_count", 0))
            metric_col2.metric("High", summary.get("high", 0))
            metric_col3.metric("Medium", summary.get("medium", 0))
            metric_col4.metric("Low", summary.get("low", 0))
            metric_col5.metric("Info", summary.get("info", 0))
            st.markdown("**风险发现**")
            st.dataframe(pd.DataFrame(passive_report.get("findings", [])), use_container_width=True, hide_index=True)
            st.markdown("**接口视角汇总**")
            st.dataframe(pd.DataFrame(passive_report.get("per_interface", [])), use_container_width=True, hide_index=True)

    with tab_probe:
        if not probe_report:
            st.info("还没有执行基线探测。")
        else:
            summary = probe_report.get("summary", {})
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            metric_col1.metric("请求数", summary.get("request_count", 0))
            metric_col2.metric("可达目标", summary.get("responded_count", 0))
            metric_col3.metric("成功率", f"{summary.get('success_rate', 0)}%")
            metric_col4.metric("发现总数", summary.get("finding_count", 0))
            metric_col5.metric("High", summary.get("high", 0))
            st.markdown("**探测发现**")
            st.dataframe(pd.DataFrame(probe_report.get("findings", [])), use_container_width=True, hide_index=True)
            st.markdown("**样本记录**")
            st.dataframe(pd.DataFrame(probe_report.get("samples", [])), use_container_width=True, hide_index=True)

    with tab_role:
        current_role_regression = role_regression
        if not current_role_regression and plan:
            try:
                parsed_role_profiles = _parse_role_profiles(st.session_state.get("api_sec_role_profiles_text", ""))
            except ValueError:
                parsed_role_profiles = None
            if parsed_role_profiles is not None:
                current_role_regression = tool.run_role_batch_regression(
                    interfaces=st.session_state.get("api_sec_interfaces", []),
                    role_profiles=parsed_role_profiles,
                    base_url=st.session_state.get("api_sec_base_url", ""),
                    selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                    verify_ssl=st.session_state.get("api_sec_verify_ssl", True),
                    timeout_seconds=float(st.session_state.get("api_sec_timeout", 15.0) or 15.0),
                    origin=st.session_state.get("api_sec_origin", "https://security-audit.local"),
                )
        if not current_role_regression:
            st.info("先配置多角色凭证并执行多角色回归。")
        else:
            summary = current_role_regression.get("summary", {})
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            metric_col1.metric("角色数", summary.get("role_count", 0))
            metric_col2.metric("对比数", summary.get("comparison_count", 0))
            metric_col3.metric("Findings", summary.get("finding_count", 0))
            metric_col4.metric("High", summary.get("high", 0))
            metric_col5.metric("Medium", summary.get("medium", 0))
            st.markdown("**角色摘要**")
            st.dataframe(pd.DataFrame(current_role_regression.get("role_summaries", [])), use_container_width=True, hide_index=True)
            st.markdown("**差异发现**")
            st.dataframe(pd.DataFrame(current_role_regression.get("findings", [])), use_container_width=True, hide_index=True)
            st.markdown("**对比矩阵**")
            st.dataframe(pd.DataFrame(current_role_regression.get("comparisons", [])), use_container_width=True, hide_index=True)
            st.markdown("**角色样本**")
            st.dataframe(pd.DataFrame(current_role_regression.get("samples", [])), use_container_width=True, hide_index=True)

    with tab_risk:
        current_risk_dashboard = risk_dashboard
        if not current_risk_dashboard and (passive_report or probe_report or auth_matrix):
            current_risk_dashboard = tool.build_risk_dashboard(
                passive_report=passive_report,
                probe_report=probe_report,
                role_regression=role_regression,
                authorization_matrix=auth_matrix,
            )
        if not current_risk_dashboard:
            st.info("先执行被动审计、基线探测或权限矩阵，再生成风险看板。")
        else:
            summary = current_risk_dashboard.get("summary", {})
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            metric_col1.metric("Findings", summary.get("finding_count", 0))
            metric_col2.metric("High", summary.get("high", 0))
            metric_col3.metric("Medium", summary.get("medium", 0))
            metric_col4.metric("Low", summary.get("low", 0))
            metric_col5.metric("高风险权限面", summary.get("auth_high_risk_interfaces", 0))
            st.markdown("**问题总览**")
            st.dataframe(pd.DataFrame(current_risk_dashboard.get("issue_overview", [])), use_container_width=True, hide_index=True)
            risk_col1, risk_col2 = st.columns(2)
            with risk_col1:
                st.markdown("**按问题类型分组**")
                st.dataframe(pd.DataFrame(current_risk_dashboard.get("category_groups", [])), use_container_width=True, hide_index=True)
            with risk_col2:
                st.markdown("**按 OWASP 分组**")
                st.dataframe(pd.DataFrame(current_risk_dashboard.get("owasp_groups", [])), use_container_width=True, hide_index=True)
            st.markdown("**按目标聚合**")
            st.dataframe(pd.DataFrame(current_risk_dashboard.get("target_groups", [])), use_container_width=True, hide_index=True)
            if current_risk_dashboard.get("auth_focus"):
                st.markdown("**高风险权限面**")
                st.dataframe(pd.DataFrame(current_risk_dashboard.get("auth_focus", [])), use_container_width=True, hide_index=True)

    with tab_owasp:
        current_checklist = checklist
        if not current_checklist and (passive_report or probe_report):
            current_checklist = tool.build_owasp_checklist(passive_report, probe_report)
        if not current_checklist:
            st.info("执行被动审计或基线探测后，会自动生成 OWASP API Top 10 清单。")
        else:
            st.dataframe(pd.DataFrame(current_checklist), use_container_width=True, hide_index=True)

    with tab_auth:
        current_auth_matrix = auth_matrix
        if not current_auth_matrix and plan:
            current_auth_matrix = tool.build_authorization_matrix(
                interfaces=st.session_state.get("api_sec_interfaces", []),
                selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                roles=_parse_roles(st.session_state.get("api_sec_roles_text", "")),
            )
        if not current_auth_matrix:
            st.info("先生成权限矩阵，或点击一键完整报告。")
        else:
            summary = current_auth_matrix.get("summary", {})
            metric_col1, metric_col2, metric_col3, metric_col4 = st.columns(4)
            metric_col1.metric("接口数", summary.get("interface_count", 0))
            metric_col2.metric("角色数", summary.get("role_count", 0))
            metric_col3.metric("场景数", summary.get("scenario_count", 0))
            metric_col4.metric("高风险接口", summary.get("high_risk_interfaces", 0))
            st.markdown("**接口风险视角**")
            st.dataframe(pd.DataFrame(current_auth_matrix.get("interfaces", [])), use_container_width=True, hide_index=True)
            st.markdown("**角色矩阵**")
            st.dataframe(pd.DataFrame(current_auth_matrix.get("matrix", [])), use_container_width=True, hide_index=True)

    with tab_templates:
        current_nuclei_pack = nuclei_pack
        if not current_nuclei_pack and plan:
            current_nuclei_pack = tool.build_nuclei_template_pack(
                interfaces=st.session_state.get("api_sec_interfaces", []),
                selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                origin=st.session_state.get("api_sec_origin", "https://security-audit.local"),
                auth_headers=parsed_auth_headers,
            )
        if not current_nuclei_pack:
            st.info("先生成 Nuclei 风格基线模板。")
        else:
            note_text = "；".join(current_nuclei_pack.get("notes", []))
            st.caption(note_text)
            metric_col1, metric_col2 = st.columns(2)
            metric_col1.metric("模板数", current_nuclei_pack.get("template_count", 0))
            metric_col2.metric("路径数", current_nuclei_pack.get("path_count", 0))
            for template in current_nuclei_pack.get("templates", []):
                with st.expander(template.get("name", "未命名模板"), expanded=False):
                    st.code(template.get("content", ""), language="yaml")
                    st.download_button(
                        label=f"下载 {template.get('file_name', 'template.yaml')}",
                        data=template.get("content", ""),
                        file_name=template.get("file_name", "template.yaml"),
                        mime="text/yaml",
                        use_container_width=True,
                        key=f"download_template_pack_{template.get('file_name', 'template')}",
                    )

    with tab_suite:
        current_regression_suite = regression_suite
        if not current_regression_suite and (passive_report or probe_report or auth_matrix):
            current_regression_suite = tool.build_regression_suite(
                interfaces=st.session_state.get("api_sec_interfaces", []),
                selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                passive_report=passive_report,
                probe_report=probe_report,
                role_regression=role_regression,
                authorization_matrix=auth_matrix,
            )
        if not current_regression_suite:
            st.info("先生成回归套件，或执行一键完整报告。")
        else:
            summary = current_regression_suite.get("summary", {})
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            metric_col1.metric("套件数", summary.get("suite_count", 0))
            metric_col2.metric("场景数", summary.get("scenario_count", 0))
            metric_col3.metric("P0", summary.get("p0", 0))
            metric_col4.metric("P1", summary.get("p1", 0))
            metric_col5.metric("P2/P3", f"{summary.get('p2', 0)}/{summary.get('p3', 0)}")
            st.markdown("**套件分组**")
            st.dataframe(pd.DataFrame(current_regression_suite.get("groups", [])), use_container_width=True, hide_index=True)
            st.markdown("**回归场景**")
            st.dataframe(pd.DataFrame(current_regression_suite.get("scenarios", [])), use_container_width=True, hide_index=True)

    with tab_playbook:
        if bundle:
            st.markdown(bundle.get("playbook_markdown", ""))
        elif plan:
            generated_checklist = checklist or tool.build_owasp_checklist(passive_report, probe_report)
            st.markdown(tool.generate_security_playbook(plan, passive_report, probe_report, generated_checklist))
        else:
            st.info("先生成安全方案后才能输出测试剧本。")

    with tab_download:
        generated_checklist = checklist or tool.build_owasp_checklist(passive_report, probe_report)
        generated_role_regression = role_regression
        if not generated_role_regression and plan:
            try:
                parsed_role_profiles = _parse_role_profiles(st.session_state.get("api_sec_role_profiles_text", ""))
            except ValueError:
                parsed_role_profiles = None
            if parsed_role_profiles is not None:
                generated_role_regression = tool.run_role_batch_regression(
                    interfaces=st.session_state.get("api_sec_interfaces", []),
                    role_profiles=parsed_role_profiles,
                    base_url=st.session_state.get("api_sec_base_url", ""),
                    selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                    verify_ssl=st.session_state.get("api_sec_verify_ssl", True),
                    timeout_seconds=float(st.session_state.get("api_sec_timeout", 15.0) or 15.0),
                    origin=st.session_state.get("api_sec_origin", "https://security-audit.local"),
                )
        generated_auth_matrix = auth_matrix
        if not generated_auth_matrix and plan:
            generated_auth_matrix = tool.build_authorization_matrix(
                interfaces=st.session_state.get("api_sec_interfaces", []),
                selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                roles=_parse_roles(st.session_state.get("api_sec_roles_text", "")),
            )
        generated_nuclei_pack = nuclei_pack
        if not generated_nuclei_pack and plan:
            generated_nuclei_pack = tool.build_nuclei_template_pack(
                interfaces=st.session_state.get("api_sec_interfaces", []),
                selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                origin=st.session_state.get("api_sec_origin", "https://security-audit.local"),
                auth_headers=parsed_auth_headers,
            )
        generated_risk_dashboard = risk_dashboard
        if not generated_risk_dashboard and (passive_report or probe_report or auth_matrix):
            generated_risk_dashboard = tool.build_risk_dashboard(
                passive_report=passive_report,
                probe_report=probe_report,
                role_regression=generated_role_regression,
                authorization_matrix=auth_matrix,
            )
        generated_regression_suite = regression_suite
        if not generated_regression_suite and (passive_report or probe_report or auth_matrix):
            generated_regression_suite = tool.build_regression_suite(
                interfaces=st.session_state.get("api_sec_interfaces", []),
                selected_indexes=st.session_state.get("api_sec_selected_indexes", []),
                passive_report=passive_report,
                probe_report=probe_report,
                role_regression=generated_role_regression,
                authorization_matrix=auth_matrix,
            )
        report_bundle = bundle
        if not report_bundle and plan:
            report_bundle = tool.build_report_bundle(
                plan,
                passive_report,
                probe_report,
                generated_role_regression,
                generated_checklist,
                authorization_matrix=generated_auth_matrix,
                nuclei_template_pack=generated_nuclei_pack,
                risk_dashboard=generated_risk_dashboard,
                regression_suite=generated_regression_suite,
            )

        export_items: List[Dict[str, Any]] = []
        if plan:
            export_items.append(
                {
                    "label": "下载安全方案 JSON",
                    "data": json.dumps(plan, ensure_ascii=False, indent=2),
                    "file_name": "api_security_plan.json",
                    "mime": "application/json",
                    "caption": "保留扫描方案、范围和策略基线。",
                }
            )
        if passive_report:
            export_items.append(
                {
                    "label": "下载被动审计 CSV",
                    "data": pd.DataFrame(passive_report.get("findings", [])).to_csv(index=False),
                    "file_name": "api_security_passive_findings.csv",
                    "mime": "text/csv",
                    "caption": "适合做问题分派和复测跟踪。",
                }
            )
        if probe_report:
            export_items.append(
                {
                    "label": "下载基线探测 CSV",
                    "data": pd.DataFrame(probe_report.get("findings", [])).to_csv(index=False),
                    "file_name": "api_security_probe_findings.csv",
                    "mime": "text/csv",
                }
            )
        if generated_checklist:
            export_items.append(
                {
                    "label": "下载 OWASP 清单 CSV",
                    "data": pd.DataFrame(generated_checklist).to_csv(index=False),
                    "file_name": "api_security_owasp_checklist.csv",
                    "mime": "text/csv",
                }
            )
        if generated_role_regression:
            export_items.append(
                {
                    "label": "下载多角色回归 CSV",
                    "data": pd.DataFrame(generated_role_regression.get("comparisons", [])).to_csv(index=False),
                    "file_name": "api_security_role_regression.csv",
                    "mime": "text/csv",
                }
            )
            export_items.append(
                {
                    "label": "下载多角色回归 JSON",
                    "data": json.dumps(generated_role_regression, ensure_ascii=False, indent=2),
                    "file_name": "api_security_role_regression.json",
                    "mime": "application/json",
                }
            )
        if generated_auth_matrix:
            export_items.append(
                {
                    "label": "下载权限矩阵 CSV",
                    "data": pd.DataFrame(generated_auth_matrix.get("matrix", [])).to_csv(index=False),
                    "file_name": "api_security_authorization_matrix.csv",
                    "mime": "text/csv",
                }
            )
        if generated_regression_suite:
            export_items.append(
                {
                    "label": "下载回归套件 CSV",
                    "data": pd.DataFrame(generated_regression_suite.get("scenarios", [])).to_csv(index=False),
                    "file_name": "api_security_regression_suite.csv",
                    "mime": "text/csv",
                }
            )
        if report_bundle:
            export_items.append(
                {
                    "label": "下载完整报告 JSON",
                    "data": json.dumps(report_bundle, ensure_ascii=False, indent=2),
                    "file_name": "api_security_report_bundle.json",
                    "mime": "application/json",
                    "caption": "推荐优先归档完整 bundle。",
                }
            )
            export_items.append(
                {
                    "label": "下载完整报告 Markdown",
                    "data": report_bundle.get("report_markdown", ""),
                    "file_name": "api_security_report.md",
                    "mime": "text/markdown",
                }
            )
        if generated_nuclei_pack:
            for template in generated_nuclei_pack.get("templates", []):
                export_items.append(
                    {
                        "label": f"下载 {template.get('name', 'Nuclei 模板')}",
                        "data": template.get("content", ""),
                        "file_name": template.get("file_name", "template.yaml"),
                        "mime": "text/yaml",
                    }
                )
        if generated_risk_dashboard:
            export_items.append(
                {
                    "label": "下载风险看板 JSON",
                    "data": json.dumps(generated_risk_dashboard, ensure_ascii=False, indent=2),
                    "file_name": "api_security_risk_dashboard.json",
                    "mime": "application/json",
                }
            )

        render_download_panel(
            title="统一导出区",
            description="安全结果统一收口到这里，JSON、Markdown、CSV 和模板文件保持一致的导出入口。",
            items=export_items,
            key_prefix="api_security_exports",
            metrics=[
                {"label": "接口范围", "value": str(len(st.session_state.get("api_sec_selected_indexes", [])))},
                {"label": "被动审计", "value": str(len((passive_report or {}).get("findings", [])))},
                {"label": "基线探测", "value": str(len((probe_report or {}).get("findings", [])))},
            ],
            empty_message="先生成方案、报告或套件后才能导出。",
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_mobile_security_tab(app_tool: ApplicationSecurityTool):
    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">移动包安全扫描</div>', unsafe_allow_html=True)
    st.caption("支持直接上传 .apk / .ipa 包，参考 ApplicationScanner 的清单思路扩展 Manifest/Info.plist、权限、组件、ATS、URL、密钥和关键字命中。")

    left_col, right_col = st.columns([1.1, 1.0])
    with left_col:
        uploaded_package = st.file_uploader(
            "上传 APK / IPA",
            type=["apk", "ipa"],
            key="app_sec_mobile_upload",
            help="静态扫描不会执行动态注入、运行时 Hook 或主动攻击动作。",
        )
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("📱 执行包扫描", key="app_sec_mobile_scan", use_container_width=True):
                if not uploaded_package:
                    st.warning("请先上传 .apk 或 .ipa 文件。")
                else:
                    keywords = _parse_keyword_lines(st.session_state.get("app_sec_mobile_keywords_text", ""))
                    with st.spinner("正在分析应用包结构、权限、组件和外联线索..."):
                        st.session_state.app_sec_mobile_report = app_tool.scan_mobile_package(
                            uploaded_package.name,
                            uploaded_package.getvalue(),
                            custom_keywords=keywords,
                        )
                    st.success("移动包扫描已完成。")
        with action_col2:
            if st.button("🧹 清空包结果", key="app_sec_mobile_clear", use_container_width=True):
                st.session_state.pop("app_sec_mobile_report", None)
                st.rerun()
    with right_col:
        st.text_area(
            "自定义关键字清单",
            key="app_sec_mobile_keywords_text",
            height=168,
            help="按行或逗号分隔，例如 xposed、ssl、root、jailbreak、api_key。",
        )
        st.markdown(
            '<div class="security-note">当前能力以静态分析为主，适合做上线前包检查、三方 SDK 清单梳理、调试配置和外联面初筛，不能替代真机动态测试。</div>',
            unsafe_allow_html=True,
        )

    report = st.session_state.get("app_sec_mobile_report")
    if not report:
        st.info("上传一个 APK 或 IPA 后即可执行静态安全扫描。")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    overview = report.get("overview", {})
    summary = report.get("summary", {})
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    metric_col1.metric("平台", str(report.get("platform", "")).upper())
    metric_col2.metric("发现总数", summary.get("finding_count", 0))
    metric_col3.metric("High", summary.get("high", 0))
    metric_col4.metric("Medium", summary.get("medium", 0))
    metric_col5.metric("URL/域名", overview.get("url_count", 0))

    tab_overview, tab_findings, tab_components, tab_artifacts, tab_export = st.tabs(
        ["概览", "风险发现", "权限/组件", "URL/密钥", "导出"]
    )

    with tab_overview:
        overview_rows = [{"字段": key, "值": value} for key, value in overview.items()]
        st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)
        if report.get("platform") == "android":
            st.markdown("**Manifest 摘要**")
            st.json(report.get("manifest", {}), expanded=False)
        else:
            st.markdown("**Info.plist 摘要**")
            st.json(report.get("info_plist", {}), expanded=False)
            if report.get("entitlements"):
                st.markdown("**Entitlements**")
                st.json(report.get("entitlements", {}), expanded=False)
            if report.get("macho_summary"):
                st.markdown("**Mach-O 摘要**")
                st.json(report.get("macho_summary", {}), expanded=False)
        if report.get("certificate"):
            st.markdown("**签名/证书线索**")
            st.json(report.get("certificate", {}), expanded=False)

    with tab_findings:
        if report.get("findings"):
            st.dataframe(pd.DataFrame(report.get("findings", [])), use_container_width=True, hide_index=True)
        else:
            st.info("当前没有自动发现风险项。")

    with tab_components:
        if report.get("permissions"):
            permission_rows = []
            for group, values in (report.get("permissions") or {}).items():
                if isinstance(values, list):
                    permission_rows.append({"组别": group, "数量": len(values), "内容": "；".join(str(item) for item in values[:20])})
            if permission_rows:
                st.markdown("**权限/能力清单**")
                st.dataframe(pd.DataFrame(permission_rows), use_container_width=True, hide_index=True)
        if report.get("exported_components"):
            st.markdown("**导出组件**")
            st.dataframe(pd.DataFrame(report.get("exported_components", [])), use_container_width=True, hide_index=True)
        elif report.get("url_schemes") or report.get("associated_domains"):
            ios_rows = []
            for scheme in report.get("url_schemes", []):
                ios_rows.append({"类型": "URL Scheme", "值": scheme})
            for domain in report.get("associated_domains", []):
                ios_rows.append({"类型": "Associated Domain", "值": domain})
            if ios_rows:
                st.markdown("**iOS 能力面**")
                st.dataframe(pd.DataFrame(ios_rows), use_container_width=True, hide_index=True)
        else:
            st.info("当前包中没有可展示的导出组件或 URL Scheme。")

    with tab_artifacts:
        if report.get("external_urls"):
            st.markdown("**外联 URL**")
            st.dataframe(pd.DataFrame(report.get("external_urls", [])), use_container_width=True, hide_index=True)
        if report.get("ip_hits"):
            st.markdown("**IP 线索**")
            st.dataframe(pd.DataFrame(report.get("ip_hits", [])), use_container_width=True, hide_index=True)
        if report.get("secret_hits"):
            st.markdown("**疑似密钥/令牌**")
            st.dataframe(pd.DataFrame(report.get("secret_hits", [])), use_container_width=True, hide_index=True)
        if report.get("keyword_hits"):
            st.markdown("**关键字命中**")
            st.dataframe(pd.DataFrame(report.get("keyword_hits", [])), use_container_width=True, hide_index=True)
        if report.get("sdk_inventory"):
            st.markdown("**SDK 线索**")
            st.dataframe(pd.DataFrame(report.get("sdk_inventory", [])), use_container_width=True, hide_index=True)

    with tab_export:
        render_download_panel(
            title="移动包导出区",
            description="移动包扫描结果统一提供 JSON 和 Markdown 两种格式。",
            items=[
                {
                    "label": "下载移动包报告 JSON",
                    "data": json.dumps(report, ensure_ascii=False, indent=2),
                    "file_name": f"mobile_security_{report.get('platform', 'package')}.json",
                    "mime": "application/json",
                },
                {
                    "label": "下载移动包报告 Markdown",
                    "data": report.get("report_markdown", ""),
                    "file_name": f"mobile_security_{report.get('platform', 'package')}.md",
                    "mime": "text/markdown",
                },
            ],
            key_prefix="mobile_security_exports",
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_web_security_tab(app_tool: ApplicationSecurityTool):
    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">Web 站点安全扫描</div>', unsafe_allow_html=True)
    st.caption("支持直接粘贴网站链接，做轻量爬取、头部/Cookie/CORS/表单/常见敏感路径暴露检查，风格接近 Web 端安全扫描工具。")

    config_col1, config_col2 = st.columns([1.15, 1.0])
    with config_col1:
        st.text_input(
            "站点 URL",
            key="app_sec_web_url",
            placeholder="https://example.com",
            help="支持 http/https；如果未带协议，默认按 https 处理。",
        )
        inner_col1, inner_col2, inner_col3 = st.columns(3)
        with inner_col1:
            st.number_input("超时(秒)", min_value=1.0, max_value=60.0, key="app_sec_web_timeout", step=1.0)
        with inner_col2:
            st.number_input("页面上限", min_value=1, max_value=30, key="app_sec_web_max_pages", step=1)
        with inner_col3:
            st.checkbox("校验证书", key="app_sec_web_verify_ssl")
        st.checkbox("启用常见路径探测", key="app_sec_web_include_common_paths")
    with config_col2:
        st.text_area(
            "请求头 JSON",
            key="app_sec_web_headers_text",
            height=166,
            help="例如 {\"Cookie\": \"session=...\", \"Authorization\": \"Bearer ...\"}。",
        )
        st.markdown(
            '<div class="security-note">默认只做低风险探测：GET/轻量爬取/常见路径访问，不执行注入、爆破、主动漏洞利用或高并发压测。</div>',
            unsafe_allow_html=True,
        )

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("🌐 执行站点扫描", key="app_sec_web_scan", use_container_width=True):
            try:
                request_headers = _parse_json_object(st.session_state.get("app_sec_web_headers_text", "{}"), "请求头")
            except ValueError as exc:
                st.error(str(exc))
                request_headers = None
            if request_headers is not None:
                target_url = str(st.session_state.get("app_sec_web_url", "") or "").strip()
                if not target_url:
                    st.warning("请先输入需要扫描的站点 URL。")
                else:
                    with st.spinner("正在执行轻量爬取、基线头部检查和暴露面梳理..."):
                        st.session_state.app_sec_web_report = app_tool.scan_web_target(
                            url=target_url,
                            headers=request_headers,
                            timeout_seconds=float(st.session_state.get("app_sec_web_timeout", 12.0) or 12.0),
                            verify_ssl=bool(st.session_state.get("app_sec_web_verify_ssl", True)),
                            max_pages=int(st.session_state.get("app_sec_web_max_pages", 8) or 8),
                            include_common_paths=bool(st.session_state.get("app_sec_web_include_common_paths", True)),
                        )
                    st.success("站点扫描已完成。")
    with action_col2:
        if st.button("🧹 清空站点结果", key="app_sec_web_clear", use_container_width=True):
            st.session_state.pop("app_sec_web_report", None)
            st.rerun()

    report = st.session_state.get("app_sec_web_report")
    if not report:
        st.info("粘贴一个站点链接后即可执行轻量 Web 安全扫描。")
        st.markdown("</div>", unsafe_allow_html=True)
        return

    summary = report.get("summary", {})
    crawl = report.get("crawl", {})
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    metric_col1.metric("页面数", crawl.get("pages_scanned", 0))
    metric_col2.metric("表单数", crawl.get("forms_found", 0))
    metric_col3.metric("High", summary.get("high", 0))
    metric_col4.metric("Medium", summary.get("medium", 0))
    metric_col5.metric("发现总数", summary.get("finding_count", 0))

    tab_overview, tab_findings, tab_pages, tab_forms, tab_paths, tab_export = st.tabs(
        ["概览", "风险发现", "页面样本", "表单/资源", "敏感路径", "导出"]
    )

    with tab_overview:
        overview_rows = [{"字段": key, "值": value} for key, value in report.get("crawl", {}).items() if key != "page_urls"]
        overview_rows.append({"字段": "target_url", "值": report.get("target_url", "")})
        st.dataframe(pd.DataFrame(overview_rows), use_container_width=True, hide_index=True)
        if report.get("certificate"):
            st.markdown("**TLS 证书信息**")
            st.json(report.get("certificate", {}), expanded=False)
        if report.get("robots_paths"):
            st.markdown("**robots.txt 暴露路径**")
            st.dataframe(pd.DataFrame([{"Path": item} for item in report.get("robots_paths", [])]), use_container_width=True, hide_index=True)

    with tab_findings:
        if report.get("findings"):
            st.dataframe(pd.DataFrame(report.get("findings", [])), use_container_width=True, hide_index=True)
        else:
            st.info("当前没有自动发现风险项。")

    with tab_pages:
        if report.get("pages"):
            st.dataframe(pd.DataFrame(report.get("pages", [])), use_container_width=True, hide_index=True)
        else:
            st.info("当前没有抓取到页面样本。")

    with tab_forms:
        if report.get("forms"):
            st.markdown("**表单**")
            st.dataframe(pd.DataFrame(report.get("forms", [])), use_container_width=True, hide_index=True)
        if report.get("assets"):
            st.markdown("**脚本/静态资源**")
            st.dataframe(pd.DataFrame(report.get("assets", [])), use_container_width=True, hide_index=True)
        if not report.get("forms") and not report.get("assets"):
            st.info("当前没有可展示的表单或脚本资源。")

    with tab_paths:
        if report.get("common_path_results"):
            st.dataframe(pd.DataFrame(report.get("common_path_results", [])), use_container_width=True, hide_index=True)
        else:
            st.info("当前没有常见路径探测结果。")

    with tab_export:
        render_download_panel(
            title="站点导出区",
            description="站点扫描结果统一提供 JSON 和 Markdown 两种格式。",
            items=[
                {
                    "label": "下载站点报告 JSON",
                    "data": json.dumps(report, ensure_ascii=False, indent=2),
                    "file_name": "web_security_report.json",
                    "mime": "application/json",
                },
                {
                    "label": "下载站点报告 Markdown",
                    "data": report.get("report_markdown", ""),
                    "file_name": "web_security_report.md",
                    "mime": "text/markdown",
                },
            ],
            key_prefix="web_security_exports",
        )

    st.markdown("</div>", unsafe_allow_html=True)


def render_api_security_test_page():
    _ensure_security_defaults()
    _render_styles()
    core = InterfaceAutoTestCore()
    tool = SecurityTestTool()
    app_tool = ApplicationSecurityTool()

    st.markdown(
        """
        <div class="security-banner">
            <h3>🛡️ 应用安全测试</h3>
            <p>统一的应用安全工作台，覆盖 API 文档安全、移动端 APK/IPA 静态扫描和 Web 站点基线扫描。默认坚持安全边界，只做授权范围内的低风险探测和清单化审计。</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    _render_design_cards()
    render_workflow_guide(
        title="安全页推荐使用顺序",
        description="先导入接口文档并确认范围，再生成基线方案和被动审计结果，最后按 API、移动包或 Web 入口分别导出报告。",
        steps=[
            "先明确授权范围、目标接口和角色，再导入接口文档或目标资产。",
            "优先跑安全方案、被动审计和低风险基线探测，再看权限矩阵和回归套件。",
            "统一从导出区下载 JSON、Markdown、CSV 结果，便于复测和归档。",
        ],
        tips=["默认坚持低风险探测", "适合授权环境", "自动发现后仍建议人工复核"],
        eyebrow="页面向导",
    )
    tab_api, tab_mobile, tab_web = st.tabs(["API 文档安全", "移动包(.apk/.ipa)", "Web 站点 URL"])

    with tab_api:
        _render_source_section(core)
        interfaces = st.session_state.get("api_sec_interfaces", [])
        if not interfaces:
            st.info("先导入接口文档，才能继续做 API 安全测试。")
        else:
            _render_scope_section(
                interfaces=interfaces,
                source_name=st.session_state.get("api_sec_source_name", ""),
                source_type=st.session_state.get("api_sec_source_type", ""),
            )
            _render_action_bar(tool, interfaces)
            _render_results(tool)

    with tab_mobile:
        _render_mobile_security_tab(app_tool)

    with tab_web:
        _render_web_security_tab(app_tool)
