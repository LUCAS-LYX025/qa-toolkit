import json
import os
import tempfile
from pathlib import Path
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
MOBSF_LOCAL_PROFILE_PATH = Path(__file__).resolve().parents[4] / "workspace" / "mobsf_profile.local.json"
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
    "app_sec_mobsf_base_url": "http://127.0.0.1:8000",
    "app_sec_mobsf_api_key": "",
    "app_sec_mobsf_timeout": 180.0,
    "app_sec_mobsf_verify_ssl": True,
    "app_sec_mobsf_include_pdf": False,
    "app_sec_mobsf_hash_query": "",
    "app_sec_mobsf_search_query": "",
    "app_sec_mobsf_dynamic_android_hash": "",
    "app_sec_mobsf_android_dynamic_action_result": None,
    "app_sec_mobsf_dynamic_ios_instance_id": "",
    "app_sec_mobsf_dynamic_ios_bundle_id": "",
    "app_sec_mobsf_dynamic_ios_device_id": "",
    "app_sec_mobsf_dynamic_ios_device_bundle_id": "",
    "app_sec_mobsf_connection_status": None,
    "app_sec_mobsf_pending_action": None,
    "app_sec_mobsf_profile_source": "默认值",
    "app_sec_mobsf_profile_ready": False,
    "app_sec_mobsf_profile_bootstrapped": False,
    "app_sec_web_url": "",
    "app_sec_web_headers_text": "{}",
    "app_sec_web_timeout": 12.0,
    "app_sec_web_verify_ssl": True,
    "app_sec_web_max_pages": 8,
    "app_sec_web_include_common_paths": True,
}


def _read_mobsf_local_profile() -> Dict[str, Any]:
    if not MOBSF_LOCAL_PROFILE_PATH.exists():
        return {}
    try:
        with MOBSF_LOCAL_PROFILE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _normalize_streamlit_secret_mapping(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if value is None:
        return {}
    try:
        return value.to_dict()
    except Exception:
        pass
    try:
        return {key: value[key] for key in value.keys()}
    except Exception:
        return {}


def _read_streamlit_mobsf_secrets() -> Dict[str, Any]:
    try:
        root_secrets = _normalize_streamlit_secret_mapping(st.secrets)
    except Exception:
        return {}

    section_secrets = _normalize_streamlit_secret_mapping(root_secrets.get("mobsf"))

    def pick_value(*keys: str):
        for key in keys:
            if key in section_secrets and section_secrets.get(key) not in (None, ""):
                return section_secrets.get(key)
            if key in root_secrets and root_secrets.get(key) not in (None, ""):
                return root_secrets.get(key)
        return None

    resolved = {
        "base_url": pick_value("base_url", "MOBSF_BASE_URL"),
        "api_key": pick_value("api_key", "MOBSF_API_KEY"),
        "timeout_seconds": pick_value("timeout_seconds", "MOBSF_TIMEOUT"),
        "verify_ssl": pick_value("verify_ssl", "MOBSF_VERIFY_SSL"),
        "include_pdf": pick_value("include_pdf", "MOBSF_INCLUDE_PDF"),
    }
    return {key: value for key, value in resolved.items() if value not in (None, "")}


def _build_mobsf_secrets_toml_example() -> str:
    return (
        "[mobsf]\n"
        'base_url = "https://your-mobsf.example.com"\n'
        'api_key = "replace-with-your-mobsf-api-key"\n'
        "timeout_seconds = 180\n"
        "verify_ssl = true\n"
        "include_pdf = false\n"
    )


def _write_mobsf_local_profile(profile: Dict[str, Any]):
    MOBSF_LOCAL_PROFILE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MOBSF_LOCAL_PROFILE_PATH.open("w", encoding="utf-8") as file:
        json.dump(profile, file, ensure_ascii=False, indent=2)


def _delete_mobsf_local_profile():
    if MOBSF_LOCAL_PROFILE_PATH.exists():
        MOBSF_LOCAL_PROFILE_PATH.unlink()


def _resolve_mobsf_profile() -> Dict[str, Any]:
    return ApplicationSecurityTool().resolve_mobsf_profile(
        secrets=_read_streamlit_mobsf_secrets(),
        local_profile=_read_mobsf_local_profile(),
    )


def _apply_resolved_mobsf_profile(profile: Dict[str, Any]):
    st.session_state.app_sec_mobsf_base_url = str(profile.get("base_url") or "http://127.0.0.1:8000").strip()
    st.session_state.app_sec_mobsf_api_key = str(profile.get("api_key") or "").strip()
    st.session_state.app_sec_mobsf_timeout = float(profile.get("timeout_seconds") or 180.0)
    st.session_state.app_sec_mobsf_verify_ssl = bool(profile.get("verify_ssl", True))
    st.session_state.app_sec_mobsf_include_pdf = bool(profile.get("include_pdf", False))
    st.session_state.app_sec_mobsf_profile_source = str(profile.get("source") or "默认值")
    st.session_state.app_sec_mobsf_profile_ready = bool(profile.get("ready"))


def _ensure_security_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value
    if not st.session_state.get("app_sec_mobsf_profile_bootstrapped"):
        _apply_resolved_mobsf_profile(_resolve_mobsf_profile())
        st.session_state.app_sec_mobsf_profile_bootstrapped = True


def _queue_mobsf_action(action_name: str, payload: Dict[str, Any] = None):
    st.session_state.app_sec_mobsf_pending_action = {
        "action": action_name,
        "payload": payload or {},
    }


def _apply_mobsf_pending_action():
    pending_action = st.session_state.get("app_sec_mobsf_pending_action")
    if not pending_action:
        return

    st.session_state.app_sec_mobsf_pending_action = None
    action_name = str(pending_action.get("action") or "").strip()
    payload = pending_action.get("payload") or {}

    if action_name == "fill_static_hash":
        hash_value = str(payload.get("hash") or "").strip()
        if hash_value:
            st.session_state.app_sec_mobsf_hash_query = hash_value
    elif action_name == "fill_android_hash":
        hash_value = str(payload.get("hash") or "").strip()
        if hash_value:
            st.session_state.app_sec_mobsf_dynamic_android_hash = hash_value
    elif action_name == "fill_ios_bundle":
        bundle_id = str(payload.get("bundle_id") or "").strip()
        if bundle_id:
            st.session_state.app_sec_mobsf_dynamic_ios_bundle_id = bundle_id
            st.session_state.app_sec_mobsf_dynamic_ios_device_bundle_id = bundle_id
    elif action_name == "fill_ios_instance_id":
        instance_id = str(payload.get("instance_id") or "").strip()
        if instance_id:
            st.session_state.app_sec_mobsf_dynamic_ios_instance_id = instance_id
    elif action_name == "fill_ios_device_id":
        device_id = str(payload.get("device_id") or "").strip()
        if device_id:
            st.session_state.app_sec_mobsf_dynamic_ios_device_id = device_id
    elif action_name == "reload_profile":
        _apply_resolved_mobsf_profile(_resolve_mobsf_profile())
    elif action_name == "clear_local_profile":
        _delete_mobsf_local_profile()
        _apply_resolved_mobsf_profile(_resolve_mobsf_profile())


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
        "app_sec_mobsf_bundle",
        "app_sec_mobsf_recent_scans",
        "app_sec_mobsf_search_result",
        "app_sec_mobsf_hash_report",
        "app_sec_mobsf_hash_scorecard",
        "app_sec_mobsf_hash_pdf_bytes",
        "app_sec_mobsf_android_dynamic_apps",
        "app_sec_mobsf_android_dynamic_action_result",
        "app_sec_mobsf_android_dynamic_bundle",
        "app_sec_mobsf_ios_dynamic_bundle",
        "app_sec_mobsf_ios_device_dynamic_bundle",
        "app_sec_mobsf_connection_status",
        "app_sec_mobsf_pending_action",
        "app_sec_mobsf_profile_source",
        "app_sec_mobsf_profile_ready",
        "app_sec_mobsf_profile_bootstrapped",
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
        ("MobSF", "参考官方静态/动态分析能力，把 APK、IPA、APPX 与 REST API 工作流整合到安全工作台里。"),
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


def _render_structured_payload(payload: Any, empty_message: str = "暂无数据。"):
    if not payload:
        st.info(empty_message)
        return
    if isinstance(payload, list) and payload and all(isinstance(item, dict) for item in payload):
        st.dataframe(pd.DataFrame(payload), use_container_width=True, hide_index=True)
        return
    st.json(payload, expanded=False)


def _render_mobsf_review_bundle(review_bundle: Dict[str, Any], empty_message: str = "暂无二次整理结果。"):
    if not review_bundle:
        st.info(empty_message)
        return

    summary = review_bundle.get("summary", {})
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    metric_col1.metric("问题数", summary.get("issue_count", 0))
    metric_col2.metric("High", summary.get("high", 0))
    metric_col3.metric("Medium", summary.get("medium", 0))
    metric_col4.metric("回归场景", summary.get("regression_case_count", 0))
    metric_col5.metric("Score", summary.get("security_score", "-") if summary.get("security_score") is not None else "-")

    if review_bundle.get("focus_areas"):
        st.markdown("**重点方向**")
        for item in review_bundle.get("focus_areas", []):
            st.markdown(f"- {item}")

    review_tab1, review_tab2, review_tab3, review_tab4 = st.tabs(["问题清单", "分类汇总", "回归套件", "Markdown"])
    with review_tab1:
        _render_structured_payload(review_bundle.get("issue_register"), "暂无问题清单。")
    with review_tab2:
        group_col1, group_col2 = st.columns(2)
        with group_col1:
            st.markdown("**按分类分组**")
            _render_structured_payload(review_bundle.get("category_groups"), "暂无分类汇总。")
        with group_col2:
            st.markdown("**按严重级别分组**")
            _render_structured_payload(review_bundle.get("severity_groups"), "暂无严重级别汇总。")
    with review_tab3:
        _render_structured_payload(review_bundle.get("regression_suite"), "暂无回归套件。")
    with review_tab4:
        st.code(review_bundle.get("markdown", ""), language="markdown")


def _render_mobsf_runtime_bundle(bundle: Dict[str, Any], empty_message: str = "暂无动态分析结果。"):
    if not bundle:
        st.info(empty_message)
        return

    summary = bundle.get("summary", {})
    review_bundle = bundle.get("review_bundle", {})
    metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
    metric_col1.metric("平台", summary.get("platform", "-"))
    metric_col2.metric("模式", summary.get("analysis_mode", "-"))
    metric_col3.metric("标识", str(summary.get("identifier", "-"))[:18] or "-")
    metric_col4.metric("报告字段数", summary.get("report_keys", 0))
    metric_col5.metric("问题数", summary.get("issue_count", 0))
    if summary.get("runtime_target") and summary.get("runtime_target") != "-":
        st.caption(f"运行时目标: {summary.get('runtime_target')}")

    bundle_tab1, bundle_tab2 = st.tabs(["动态报告", "二次整理"])
    with bundle_tab1:
        _render_structured_payload(bundle.get("json_report"), "MobSF 尚未返回动态分析报告。")
    with bundle_tab2:
        _render_mobsf_review_bundle(review_bundle, "动态分析报告暂未整理出复核清单。")


def _get_mobsf_request_options() -> Dict[str, Any]:
    return {
        "base_url": st.session_state.get("app_sec_mobsf_base_url", ""),
        "api_key": st.session_state.get("app_sec_mobsf_api_key", ""),
        "timeout_seconds": float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
        "verify_ssl": bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
    }


def _load_mobsf_static_bundle_by_hash(app_tool: ApplicationSecurityTool, file_hash: str):
    options = _get_mobsf_request_options()
    bundle = app_tool.build_mobsf_static_bundle_from_hash(
        file_hash=file_hash,
        include_pdf=bool(st.session_state.get("app_sec_mobsf_include_pdf", False)),
        **options,
    )
    st.session_state.app_sec_mobsf_hash_query = str(file_hash or "").strip()
    st.session_state.app_sec_mobsf_hash_report = bundle.get("json_report", {})
    st.session_state.app_sec_mobsf_hash_scorecard = bundle.get("scorecard", {})
    st.session_state.app_sec_mobsf_hash_pdf_bytes = bundle.get("pdf_bytes", b"")
    return bundle


def _load_mobsf_android_dynamic_bundle(app_tool: ApplicationSecurityTool, file_hash: str):
    options = _get_mobsf_request_options()
    normalized_hash = str(file_hash or "").strip()
    report_json = app_tool.mobsf_get_android_dynamic_report(file_hash=normalized_hash, **options)
    bundle = app_tool.build_mobsf_dynamic_bundle(
        report_json=report_json,
        platform="android",
        analysis_mode="android_dynamic",
        identifier=normalized_hash,
        runtime_target=normalized_hash,
    )
    st.session_state.app_sec_mobsf_dynamic_android_hash = normalized_hash
    st.session_state.app_sec_mobsf_android_dynamic_bundle = bundle
    return bundle


def _render_mobsf_android_dynamic_report_unavailable_hint(app_tool: ApplicationSecurityTool, file_hash: str):
    normalized_hash = str(file_hash or "").strip()
    st.warning("MobSF 侧还没有这个 Hash 的 Android 动态报告。先完成动态分析并收集结果，再回来拉报告。")

    apps_payload = st.session_state.get("app_sec_mobsf_android_dynamic_apps")
    candidates = app_tool.mobsf_extract_reference_candidates(apps_payload, source_name="Android 可分析应用")
    if candidates:
        hash_in_apps = any(str(item.get("Hash") or "").strip() == normalized_hash for item in candidates if normalized_hash)
        if hash_in_apps:
            st.info("当前 `获取 Android 可分析应用` 列表里已经找到这个 Hash，可以直接启动动态分析。")
        else:
            st.info("当前 `获取 Android 可分析应用` 列表里还没看到这个 Hash。先确认 MobSF 动态环境、模拟器/设备和目标应用已准备好。")
    else:
        st.info("建议先点一次“获取 Android 可分析应用”，确认 MobSF 动态环境已经准备好。")

    st.markdown("**下一步建议**")
    steps = [
        f"使用同一个 Hash `{normalized_hash or '<hash>'}` 启动 Android 动态分析。",
        "在模拟器或设备里完成需要覆盖的业务路径和风险操作。",
        "点击“停止并收集结果”，让 MobSF 生成动态报告。",
        "再点击“拉 Android 动态报告”获取结果并自动整理。",
    ]
    for step in steps:
        st.markdown(f"- {step}")


def _render_mobsf_android_dynamic_environment_hint(app_tool: ApplicationSecurityTool, error: Exception, action_label: str):
    if app_tool.is_mobsf_android_dynamic_analysis_failed_error(error):
        st.warning(f"{action_label}没有成功。通常是 MobSF 动态环境、模拟器/真机、Frida 或代理证书还没准备好。")
        st.markdown("**建议检查**")
        steps = [
            "先点“获取 Android 可分析应用”，确认列表能正常返回且目标应用在列表中。",
            "确认 MobSF Web UI 的 Dynamic Analyzer 页面里设备或模拟器已经就绪。",
            "确认目标应用已安装并允许被动态分析，必要时先在 MobSF Web UI 手动走一遍动态分析准备。",
            "如果刚停止分析，稍等几秒再拉报告，避免结果还在收集过程中。",
        ]
        for step in steps:
            st.markdown(f"- {step}")
        return
    st.error(f"{action_label}失败: {error}")


def _handle_mobsf_android_dynamic_report_exception(
    app_tool: ApplicationSecurityTool,
    file_hash: str,
    exc: Exception,
    action_label: str,
):
    if app_tool.is_mobsf_dynamic_report_unavailable_error(exc):
        _render_mobsf_android_dynamic_report_unavailable_hint(app_tool, file_hash)
        return
    st.error(f"{action_label}失败: {exc}")


def _render_mobsf_android_dynamic_apps_hint(apps_payload: Dict[str, Any]):
    if not isinstance(apps_payload, dict):
        return
    if not apps_payload.get("android_version"):
        st.info("当前 MobSF 没有返回 Android 设备版本信息，通常表示动态设备/模拟器还没完全就绪。")
    apps = apps_payload.get("apps")
    if isinstance(apps, list) and any(isinstance(item, dict) and item.get("DYNAMIC_REPORT_EXISTS") is False for item in apps):
        st.info("列表里 `DYNAMIC_REPORT_EXISTS = false` 表示该应用可用于动态分析，但动态报告尚未生成。")


def _load_mobsf_ios_dynamic_bundle(app_tool: ApplicationSecurityTool, instance_id: str, bundle_id: str):
    options = _get_mobsf_request_options()
    normalized_instance_id = str(instance_id or "").strip()
    normalized_bundle_id = str(bundle_id or "").strip()
    report_json = app_tool.mobsf_get_ios_dynamic_report(
        instance_id=normalized_instance_id,
        bundle_id=normalized_bundle_id,
        **options,
    )
    bundle = app_tool.build_mobsf_dynamic_bundle(
        report_json=report_json,
        platform="ios",
        analysis_mode="ios_dynamic",
        identifier=normalized_bundle_id,
        runtime_target=normalized_instance_id,
        app_name=normalized_bundle_id,
    )
    st.session_state.app_sec_mobsf_dynamic_ios_instance_id = normalized_instance_id
    st.session_state.app_sec_mobsf_dynamic_ios_bundle_id = normalized_bundle_id
    st.session_state.app_sec_mobsf_ios_dynamic_bundle = bundle
    return bundle


def _load_mobsf_ios_device_dynamic_bundle(app_tool: ApplicationSecurityTool, device_id: str, bundle_id: str):
    options = _get_mobsf_request_options()
    normalized_device_id = str(device_id or "").strip()
    normalized_bundle_id = str(bundle_id or "").strip()
    report_json = app_tool.mobsf_get_ios_device_dynamic_report(
        device_id=normalized_device_id,
        bundle_id=normalized_bundle_id,
        **options,
    )
    bundle = app_tool.build_mobsf_dynamic_bundle(
        report_json=report_json,
        platform="ios",
        analysis_mode="ios_device_dynamic",
        identifier=normalized_bundle_id,
        runtime_target=normalized_device_id,
        app_name=normalized_bundle_id,
    )
    st.session_state.app_sec_mobsf_dynamic_ios_device_id = normalized_device_id
    st.session_state.app_sec_mobsf_dynamic_ios_device_bundle_id = normalized_bundle_id
    st.session_state.app_sec_mobsf_ios_device_dynamic_bundle = bundle
    return bundle


def _render_mobsf_prefill_candidates(
    app_tool: ApplicationSecurityTool,
    payload: Any,
    source_name: str,
    key_prefix: str,
):
    candidates = app_tool.mobsf_extract_reference_candidates(payload, source_name=source_name)
    if not candidates:
        st.info("当前结果里没有可用于回填的 hash / bundle_id / instance_id / device_id。")
        return

    st.caption("可从这里把常用标识一键回填到静态查询、Android 动态或 iOS 动态输入框。")
    st.dataframe(pd.DataFrame(candidates), use_container_width=True, hide_index=True)

    options = {item["Label"]: item for item in candidates}
    selected_label = st.selectbox(
        "选择一条记录用于回填",
        options=list(options.keys()),
        key=f"{key_prefix}_selected_label",
    )
    selected = options[selected_label]

    st.caption(
        "iOS Bundle 会同时回填到 Corellium 和真机两个 bundle 输入框；"
        "Instance ID 和 Device ID 会分别回填到对应动态分析入口。"
    )
    fill_col1, fill_col2, fill_col3, fill_col4, fill_col5 = st.columns(5)
    with fill_col1:
        st.button(
            "回填静态 Hash",
            key=f"{key_prefix}_fill_static_hash",
            use_container_width=True,
            disabled=not bool(selected.get("Hash")),
            on_click=_queue_mobsf_action,
            kwargs={
                "action_name": "fill_static_hash",
                "payload": {"hash": selected.get("Hash", "")},
            },
        )
    with fill_col2:
        st.button(
            "回填Android Hash",
            key=f"{key_prefix}_fill_android_hash",
            use_container_width=True,
            disabled=not bool(selected.get("Hash")),
            on_click=_queue_mobsf_action,
            kwargs={
                "action_name": "fill_android_hash",
                "payload": {"hash": selected.get("Hash", "")},
            },
        )
    with fill_col3:
        st.button(
            "回填iOS Bundle",
            key=f"{key_prefix}_fill_ios_bundle",
            use_container_width=True,
            disabled=not bool(selected.get("Bundle ID") or selected.get("Package Name")),
            on_click=_queue_mobsf_action,
            kwargs={
                "action_name": "fill_ios_bundle",
                "payload": {"bundle_id": selected.get("Bundle ID") or selected.get("Package Name") or ""},
            },
        )
    with fill_col4:
        st.button(
            "回填Instance ID",
            key=f"{key_prefix}_fill_instance_id",
            use_container_width=True,
            disabled=not bool(selected.get("Instance ID")),
            on_click=_queue_mobsf_action,
            kwargs={
                "action_name": "fill_ios_instance_id",
                "payload": {"instance_id": selected.get("Instance ID", "")},
            },
        )
    with fill_col5:
        st.button(
            "回填Device ID",
            key=f"{key_prefix}_fill_device_id",
            use_container_width=True,
            disabled=not bool(selected.get("Device ID")),
            on_click=_queue_mobsf_action,
            kwargs={
                "action_name": "fill_ios_device_id",
                "payload": {"device_id": selected.get("Device ID", "")},
            },
        )

    fetch_col1, fetch_col2, fetch_col3, fetch_col4 = st.columns(4)
    with fetch_col1:
        if st.button(
            "直拉静态结果",
            key=f"{key_prefix}_fetch_static_bundle",
            use_container_width=True,
            disabled=not bool(selected.get("Hash")),
        ):
            try:
                _load_mobsf_static_bundle_by_hash(app_tool, selected.get("Hash", ""))
                st.success("已根据所选记录拉取静态报告。")
            except Exception as exc:
                st.error(f"拉取静态报告失败: {exc}")
    with fetch_col2:
        if st.button(
            "直拉Android动态",
            key=f"{key_prefix}_fetch_android_dynamic_bundle",
            use_container_width=True,
            disabled=not bool(selected.get("Hash")),
        ):
            try:
                _load_mobsf_android_dynamic_bundle(app_tool, selected.get("Hash", ""))
                st.success("已根据所选记录拉取 Android 动态报告。")
            except Exception as exc:
                _handle_mobsf_android_dynamic_report_exception(
                    app_tool,
                    selected.get("Hash", ""),
                    exc,
                    "拉取 Android 动态报告",
                )
    with fetch_col3:
        if st.button(
            "直拉iOS动态",
            key=f"{key_prefix}_fetch_ios_dynamic_bundle",
            use_container_width=True,
            disabled=not bool(selected.get("Instance ID")) or not bool(selected.get("Bundle ID") or selected.get("Package Name")),
        ):
            try:
                bundle_id = selected.get("Bundle ID") or selected.get("Package Name") or ""
                _load_mobsf_ios_dynamic_bundle(app_tool, selected.get("Instance ID", ""), bundle_id)
                st.success("已根据所选记录拉取 iOS Corellium 动态报告。")
            except Exception as exc:
                st.error(f"拉取 iOS Corellium 动态报告失败: {exc}")
    with fetch_col4:
        if st.button(
            "直拉iOS真机动态",
            key=f"{key_prefix}_fetch_ios_device_dynamic_bundle",
            use_container_width=True,
            disabled=not bool(selected.get("Device ID")) or not bool(selected.get("Bundle ID") or selected.get("Package Name")),
        ):
            try:
                bundle_id = selected.get("Bundle ID") or selected.get("Package Name") or ""
                _load_mobsf_ios_device_dynamic_bundle(app_tool, selected.get("Device ID", ""), bundle_id)
                st.success("已根据所选记录拉取 iOS 真机动态报告。")
            except Exception as exc:
                st.error(f"拉取 iOS 真机动态报告失败: {exc}")


def _render_local_mobile_security_tab(app_tool: ApplicationSecurityTool):
    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">移动包安全扫描</div>', unsafe_allow_html=True)
    st.caption("支持直接上传 .apk / .ipa / .appx 包，适合先做本地静态预检；更重的静态/动态能力可切到 MobSF 集成页。")

    left_col, right_col = st.columns([1.1, 1.0])
    with left_col:
        uploaded_package = st.file_uploader(
            "上传 APK / IPA / APPX",
            type=["apk", "ipa", "appx"],
            key="app_sec_mobile_upload",
            help="静态扫描不会执行动态注入、运行时 Hook 或主动攻击动作。",
        )
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("📱 执行包扫描", key="app_sec_mobile_scan", use_container_width=True):
                if not uploaded_package:
                    st.warning("请先上传 .apk、.ipa 或 .appx 文件。")
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
        st.info("上传一个 APK、IPA 或 APPX 后即可执行静态安全扫描。")
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
        elif report.get("platform") == "ios":
            st.markdown("**Info.plist 摘要**")
            st.json(report.get("info_plist", {}), expanded=False)
            if report.get("entitlements"):
                st.markdown("**Entitlements**")
                st.json(report.get("entitlements", {}), expanded=False)
            if report.get("macho_summary"):
                st.markdown("**Mach-O 摘要**")
                st.json(report.get("macho_summary", {}), expanded=False)
        else:
            st.markdown("**AppxManifest 摘要**")
            st.json(report.get("appx_manifest", {}), expanded=False)
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
        elif report.get("protocols") or report.get("app_services"):
            windows_rows = []
            for protocol in report.get("protocols", []):
                windows_rows.append({"类型": "Protocol", "值": protocol})
            for app_service in report.get("app_services", []):
                windows_rows.append({"类型": "App Service", "值": app_service})
            if windows_rows:
                st.markdown("**Windows 能力面**")
                st.dataframe(pd.DataFrame(windows_rows), use_container_width=True, hide_index=True)
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


def _render_mobsf_mobile_security_tab(app_tool: ApplicationSecurityTool):
    _apply_mobsf_pending_action()

    st.markdown('<div class="security-section">', unsafe_allow_html=True)
    st.markdown('<div class="security-section-title">MobSF 官方集成</div>', unsafe_allow_html=True)
    st.caption("基于 MobSF 官方仓库和 REST API，支持 APK / IPA / APPX 静态分析接入，以及 Android / iOS 动态报告拉取、二次整理和导出。")

    quick_start = app_tool.build_mobsf_quick_start(st.session_state.get("app_sec_mobsf_base_url", "http://127.0.0.1:8000"))

    st.markdown(
        f"""
        <div class="security-note">
            官方来源:
            <a href="{app_tool.MOBSF_OFFICIAL_REPO}" target="_blank">GitHub 仓库</a> |
            <a href="{app_tool.MOBSF_STATIC_API_SOURCE}" target="_blank">静态 API 源码</a> |
            <a href="{app_tool.MOBSF_DYNAMIC_API_SOURCE}" target="_blank">动态 API 源码</a>
        </div>
        """,
        unsafe_allow_html=True,
    )

    current_base_url = str(st.session_state.get("app_sec_mobsf_base_url", "") or "").strip()
    current_api_key = str(st.session_state.get("app_sec_mobsf_api_key", "") or "").strip()
    current_profile_ready = bool(current_base_url and current_api_key)
    profile_source = str(st.session_state.get("app_sec_mobsf_profile_source", "默认值") or "默认值")

    profile_col1, profile_col2, profile_col3, profile_col4 = st.columns(4)
    profile_col1.metric("使用模式", "极速模式" if current_profile_ready else "待配置")
    profile_col2.metric("配置来源", profile_source)
    profile_col3.metric("服务地址", current_base_url.replace("http://", "").replace("https://", "") or "-")
    profile_col4.metric("API Key", "已配置" if current_api_key else "未配置")

    if current_profile_ready:
        st.success(f"已从 {profile_source} 加载 MobSF 预配置。正常使用只需要上传文件并点击扫描。")
    else:
        st.warning("还没有可用的 MobSF 预配置。展开下面的“一次性设置”填一次；部署到 Streamlit Community Cloud 时，优先使用 Secrets。")

    with st.expander("⚙️ MobSF 高级配置 / 一次性设置", expanded=not current_profile_ready):
        st.info("本地运行可保存到本地配置文件；部署到 Streamlit Community Cloud 时，建议把 MobSF 配置写入 `secrets.toml` 或 Cloud Secrets，避免临时文件丢失。")
        config_col1, config_col2 = st.columns([1.05, 1.0])
        with config_col1:
            st.text_input(
                "MobSF 服务地址",
                key="app_sec_mobsf_base_url",
                placeholder="http://127.0.0.1:8000",
                help="例如本地 Docker 启动后的 http://127.0.0.1:8000",
            )
            inner_col1, inner_col2 = st.columns(2)
            with inner_col1:
                st.number_input("超时(秒)", min_value=10.0, max_value=600.0, step=10.0, key="app_sec_mobsf_timeout")
            with inner_col2:
                st.checkbox("校验证书", key="app_sec_mobsf_verify_ssl")
            st.checkbox("拉取 PDF 报告", key="app_sec_mobsf_include_pdf", help="启用后会在静态分析完成后额外拉取 PDF 报告。")
        with config_col2:
            st.text_input(
                "MobSF API Key",
                key="app_sec_mobsf_api_key",
                type="password",
                help="MobSF REST API 默认通过 X-Mobsf-Api-Key 头鉴权。",
            )
            st.text_input(
                "按 Hash 拉取报告",
                key="app_sec_mobsf_hash_query",
                placeholder="输入 MobSF 返回的 hash",
            )
            st.text_input(
                "搜索历史扫描",
                key="app_sec_mobsf_search_query",
                placeholder="输入 hash 或关键字",
            )

        setup_col1, setup_col2, setup_col3 = st.columns(3)
        with setup_col1:
            if st.button("💾 保存当前配置到本地", key="app_sec_mobsf_save_local_profile", use_container_width=True):
                _write_mobsf_local_profile(
                    {
                        "base_url": str(st.session_state.get("app_sec_mobsf_base_url", "") or "").strip(),
                        "api_key": str(st.session_state.get("app_sec_mobsf_api_key", "") or "").strip(),
                        "timeout_seconds": float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                        "verify_ssl": bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                        "include_pdf": bool(st.session_state.get("app_sec_mobsf_include_pdf", False)),
                    }
                )
                st.session_state.app_sec_mobsf_profile_source = "本地配置"
                st.session_state.app_sec_mobsf_profile_ready = bool(
                    str(st.session_state.get("app_sec_mobsf_base_url", "") or "").strip()
                    and str(st.session_state.get("app_sec_mobsf_api_key", "") or "").strip()
                )
                st.success(f"已保存到 {MOBSF_LOCAL_PROFILE_PATH}.")
        with setup_col2:
            st.button(
                "🔄 重新读取预配置",
                key="app_sec_mobsf_reload_profile",
                use_container_width=True,
                on_click=_queue_mobsf_action,
                kwargs={"action_name": "reload_profile"},
            )
        with setup_col3:
            st.button(
                "🗑️ 清除本地配置",
                key="app_sec_mobsf_clear_local_profile",
                use_container_width=True,
                on_click=_queue_mobsf_action,
                kwargs={"action_name": "clear_local_profile"},
            )

        st.download_button(
            "☁️ 下载 Streamlit Secrets 模板",
            data=_build_mobsf_secrets_toml_example(),
            file_name="secrets.toml.example",
            mime="text/plain",
            use_container_width=True,
        )

        st.caption(
            "支持优先从环境变量、Streamlit Secrets、本地配置自动读取: "
            "`MOBSF_BASE_URL`、`MOBSF_API_KEY`、`MOBSF_TIMEOUT`、`MOBSF_VERIFY_SSL`、`MOBSF_INCLUDE_PDF`。"
        )
        st.caption(f"本地配置文件: `{MOBSF_LOCAL_PROFILE_PATH}`。仅建议在本机可信环境使用；Community Cloud 中它不是长期持久配置。")

    current_base_url = str(st.session_state.get("app_sec_mobsf_base_url", "") or "").strip()
    current_api_key = str(st.session_state.get("app_sec_mobsf_api_key", "") or "").strip()
    current_profile_ready = bool(current_base_url and current_api_key)

    connection_col1, connection_col2 = st.columns([0.9, 2.1])
    with connection_col1:
        if st.button("🔌 检查连通性", key="app_sec_mobsf_check_connection", use_container_width=True):
            try:
                st.session_state.app_sec_mobsf_connection_status = app_tool.mobsf_check_connection(
                    base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                    api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                    timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                    verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                )
                payload = st.session_state.app_sec_mobsf_connection_status.get("payload")
                if payload:
                    st.session_state.app_sec_mobsf_recent_scans = payload
            except Exception as exc:
                st.session_state.app_sec_mobsf_connection_status = {
                    "success": False,
                    "reachable": False,
                    "authenticated": False,
                    "status_code": None,
                    "recent_scan_count": 0,
                    "message": str(exc),
                }
    with connection_col2:
        connection_status = st.session_state.get("app_sec_mobsf_connection_status")
        if connection_status:
            message = str(connection_status.get("message", "") or "").strip()
            if connection_status.get("success"):
                st.success(message)
            elif connection_status.get("reachable"):
                st.warning(message)
            else:
                st.error(message)
            status_cols = st.columns(3)
            status_cols[0].metric("HTTP状态", connection_status.get("status_code") or "-")
            status_cols[1].metric("最近扫描候选", connection_status.get("recent_scan_count", 0))
            status_cols[2].metric("鉴权", "通过" if connection_status.get("authenticated") else "未通过")

    with st.expander("🚀 MobSF 快速启动 / 官方能力", expanded=False):
        st.markdown("**Docker 启动命令**")
        st.code("\n".join(quick_start.get("docker_commands", [])), language="bash")
        st.markdown("**静态分析 API**")
        st.dataframe(pd.DataFrame(quick_start.get("static_endpoints", [])), use_container_width=True, hide_index=True)
        dynamic_col1, dynamic_col2, dynamic_col3 = st.columns(3)
        with dynamic_col1:
            st.markdown("**Android 动态分析 API**")
            st.dataframe(pd.DataFrame(quick_start.get("android_dynamic_endpoints", [])), use_container_width=True, hide_index=True)
        with dynamic_col2:
            st.markdown("**iOS Corellium 动态 API**")
            st.dataframe(pd.DataFrame(quick_start.get("ios_dynamic_endpoints", [])), use_container_width=True, hide_index=True)
        with dynamic_col3:
            st.markdown("**iOS 越狱设备动态 API**")
            st.dataframe(pd.DataFrame(quick_start.get("ios_device_dynamic_endpoints", [])), use_container_width=True, hide_index=True)
        st.markdown("**curl 示例**")
        for label, command in quick_start.get("curl_examples", {}).items():
            st.code(command, language="bash")

    uploaded_package = st.file_uploader(
        "上传到 MobSF 的安装包 / 二进制",
        type=["apk", "apks", "xapk", "aab", "ipa", "jar", "aar", "so", "zip", "dylib", "a", "appx"],
        key="app_sec_mobsf_upload",
        help="这里不会在本机解包分析，而是直接把文件上传到你配置的 MobSF 服务。当前按官方静态分析接口支持 apk、apks、xapk、aab、ipa、jar、aar、so、zip、dylib、a、appx。",
    )

    action_col1, action_col2, action_col3, action_col4 = st.columns(4)
    with action_col1:
        if st.button(
            "🚀 上传文件并自动扫描",
            key="app_sec_mobsf_run_static",
            use_container_width=True,
            disabled=not current_profile_ready,
        ):
            if not uploaded_package:
                st.warning("请先选择要上传到 MobSF 的安装包。")
            else:
                try:
                    with st.spinner("正在调用 MobSF 上传、扫描并拉取报告..."):
                        st.session_state.app_sec_mobsf_bundle = app_tool.run_mobsf_static_analysis(
                            base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                            api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                            file_name=uploaded_package.name,
                            file_bytes=uploaded_package.getvalue(),
                            timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                            verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                            include_pdf=bool(st.session_state.get("app_sec_mobsf_include_pdf", False)),
                        )
                    st.success("MobSF 静态分析已完成。")
                except Exception as exc:
                    st.error(f"MobSF 静态分析失败: {exc}")
    with action_col2:
        if st.button("🕘 获取最近扫描", key="app_sec_mobsf_recent", use_container_width=True, disabled=not current_profile_ready):
            try:
                st.session_state.app_sec_mobsf_recent_scans = app_tool.mobsf_get_recent_scans(
                    base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                    api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                    timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                    verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                )
                st.success("最近扫描记录已刷新。")
            except Exception as exc:
                st.error(f"获取最近扫描失败: {exc}")
    with action_col3:
        if st.button("🔎 搜索历史扫描", key="app_sec_mobsf_search", use_container_width=True, disabled=not current_profile_ready):
            query = str(st.session_state.get("app_sec_mobsf_search_query", "") or "").strip()
            if not query:
                st.warning("请先输入搜索关键字或 hash。")
            else:
                try:
                    st.session_state.app_sec_mobsf_search_result = app_tool.mobsf_search(
                        base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                        api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                        query=query,
                        timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                        verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                    )
                    st.success("MobSF 搜索已完成。")
                except Exception as exc:
                    st.error(f"搜索历史扫描失败: {exc}")
    with action_col4:
        if st.button("🧹 清空 MobSF 结果", key="app_sec_mobsf_clear", use_container_width=True):
            for state_key in [
                "app_sec_mobsf_bundle",
                "app_sec_mobsf_recent_scans",
                "app_sec_mobsf_search_result",
                "app_sec_mobsf_hash_report",
                "app_sec_mobsf_hash_scorecard",
                "app_sec_mobsf_hash_pdf_bytes",
                "app_sec_mobsf_android_dynamic_apps",
                "app_sec_mobsf_android_dynamic_action_result",
                "app_sec_mobsf_android_dynamic_bundle",
                "app_sec_mobsf_ios_dynamic_bundle",
                "app_sec_mobsf_ios_device_dynamic_bundle",
            ]:
                st.session_state.pop(state_key, None)
            st.rerun()

    hash_action_col1, hash_action_col2, hash_action_col3 = st.columns(3)
    with hash_action_col1:
        if st.button("📄 按 Hash 拉静态 JSON", key="app_sec_mobsf_get_report", use_container_width=True, disabled=not current_profile_ready):
            query_hash = str(st.session_state.get("app_sec_mobsf_hash_query", "") or "").strip()
            if not query_hash:
                st.warning("请先输入需要查询的 hash。")
            else:
                try:
                    bundle_from_hash = _load_mobsf_static_bundle_by_hash(app_tool, query_hash)
                    st.session_state.app_sec_mobsf_hash_pdf_bytes = b""
                    st.session_state.app_sec_mobsf_hash_report = bundle_from_hash.get("json_report", {})
                    st.session_state.app_sec_mobsf_hash_scorecard = bundle_from_hash.get("scorecard", {})
                    st.success("MobSF JSON 报告已拉取。")
                except Exception as exc:
                    st.error(f"获取 JSON 报告失败: {exc}")
    with hash_action_col2:
        if st.button("📊 按 Hash 拉静态 Scorecard", key="app_sec_mobsf_get_scorecard", use_container_width=True, disabled=not current_profile_ready):
            query_hash = str(st.session_state.get("app_sec_mobsf_hash_query", "") or "").strip()
            if not query_hash:
                st.warning("请先输入需要查询的 hash。")
            else:
                try:
                    bundle_from_hash = _load_mobsf_static_bundle_by_hash(app_tool, query_hash)
                    st.session_state.app_sec_mobsf_hash_report = bundle_from_hash.get("json_report", {})
                    st.session_state.app_sec_mobsf_hash_scorecard = bundle_from_hash.get("scorecard", {})
                    st.session_state.app_sec_mobsf_hash_pdf_bytes = b""
                    st.success("MobSF Scorecard 已拉取。")
                except Exception as exc:
                    st.error(f"获取 Scorecard 失败: {exc}")
    with hash_action_col3:
        if st.button("🧾 按 Hash 拉静态 PDF", key="app_sec_mobsf_get_pdf", use_container_width=True, disabled=not current_profile_ready):
            query_hash = str(st.session_state.get("app_sec_mobsf_hash_query", "") or "").strip()
            if not query_hash:
                st.warning("请先输入需要查询的 hash。")
            else:
                try:
                    bundle_from_hash = _load_mobsf_static_bundle_by_hash(app_tool, query_hash)
                    st.session_state.app_sec_mobsf_hash_report = bundle_from_hash.get("json_report", {})
                    st.session_state.app_sec_mobsf_hash_scorecard = bundle_from_hash.get("scorecard", {})
                    st.session_state.app_sec_mobsf_hash_pdf_bytes = bundle_from_hash.get("pdf_bytes", b"")
                    st.success("MobSF PDF 已拉取。")
                except Exception as exc:
                    st.error(f"获取 PDF 报告失败: {exc}")

    bundle = st.session_state.get("app_sec_mobsf_bundle")
    recent_scans = st.session_state.get("app_sec_mobsf_recent_scans")
    search_result = st.session_state.get("app_sec_mobsf_search_result")
    hash_report = st.session_state.get("app_sec_mobsf_hash_report")
    hash_scorecard = st.session_state.get("app_sec_mobsf_hash_scorecard")
    hash_pdf_bytes = st.session_state.get("app_sec_mobsf_hash_pdf_bytes", b"")
    android_dynamic_apps = st.session_state.get("app_sec_mobsf_android_dynamic_apps")
    android_dynamic_action_result = st.session_state.get("app_sec_mobsf_android_dynamic_action_result")
    android_dynamic_bundle = st.session_state.get("app_sec_mobsf_android_dynamic_bundle")
    ios_dynamic_bundle = st.session_state.get("app_sec_mobsf_ios_dynamic_bundle")
    ios_device_dynamic_bundle = st.session_state.get("app_sec_mobsf_ios_device_dynamic_bundle")
    hash_review_bundle = (
        app_tool.build_mobsf_review_bundle(
            report_json=hash_report,
            scorecard=hash_scorecard,
            file_hash=st.session_state.get("app_sec_mobsf_hash_query", ""),
            analysis_mode="static",
        )
        if hash_report
        else {}
    )

    tab_bundle, tab_review, tab_recent, tab_search, tab_dynamic, tab_export = st.tabs(
        ["静态扫描结果", "二次整理", "最近扫描", "搜索结果", "动态分析", "导出"]
    )

    with tab_bundle:
        if bundle:
            summary = bundle.get("summary", {})
            review_bundle = bundle.get("review_bundle", {})
            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            metric_col1.metric("Hash", summary.get("hash", "")[:12] or "-")
            metric_col2.metric("类型", summary.get("scan_type", "") or "-")
            metric_col3.metric("报告字段数", summary.get("report_keys", 0))
            metric_col4.metric("Scorecard字段数", summary.get("scorecard_keys", 0))
            metric_col5.metric("PDF", "已拉取" if summary.get("has_pdf") else "未拉取")
            if review_bundle:
                st.caption(
                    f"二次整理: {review_bundle.get('summary', {}).get('issue_count', 0)} 个问题, "
                    f"{review_bundle.get('summary', {}).get('regression_case_count', 0)} 条回归建议"
                )

            st.markdown("**上传结果**")
            st.json(bundle.get("upload", {}), expanded=False)
            st.markdown("**扫描结果**")
            st.json(bundle.get("scan", {}), expanded=False)
            st.markdown("**JSON 报告**")
            _render_structured_payload(bundle.get("json_report"), "MobSF 尚未返回 JSON 报告。")
            st.markdown("**Scorecard**")
            _render_structured_payload(bundle.get("scorecard"), "MobSF 尚未返回 Scorecard。")
            st.markdown("**当前静态结果快捷复用**")
            _render_mobsf_prefill_candidates(app_tool, bundle, "当前静态扫描", "mobsf_bundle_prefill")
        else:
            st.info("还没有执行上传并静态扫描。")

        if hash_report:
            st.markdown("**按 Hash 拉取的 JSON 报告**")
            _render_structured_payload(hash_report, "暂无按 Hash 拉取的报告。")
        if hash_scorecard:
            st.markdown("**按 Hash 拉取的 Scorecard**")
            _render_structured_payload(hash_scorecard, "暂无按 Hash 拉取的 Scorecard。")
        if not any([bundle, hash_report, hash_scorecard]):
            st.info("还没有静态分析结果。可先上传安装包静态扫描，或按 Hash 拉取静态报告。")

    with tab_review:
        if bundle and bundle.get("review_bundle") and hash_review_bundle:
            review_tab_current, review_tab_hash = st.tabs(["当前静态扫描", "按 Hash 拉取"])
            with review_tab_current:
                _render_mobsf_review_bundle(bundle.get("review_bundle", {}))
            with review_tab_hash:
                _render_mobsf_review_bundle(hash_review_bundle)
        elif bundle and bundle.get("review_bundle"):
            st.markdown("**当前静态扫描的二次整理**")
            _render_mobsf_review_bundle(bundle.get("review_bundle", {}))
        elif hash_review_bundle:
            st.markdown("**按 Hash 拉取结果的二次整理**")
            _render_mobsf_review_bundle(hash_review_bundle)
        else:
            st.info("先获取一份 MobSF JSON 报告，才能生成测试视角的二次整理结果。")

    with tab_recent:
        _render_structured_payload(recent_scans, "还没有获取最近扫描记录。")
        if recent_scans:
            st.markdown("**最近扫描回填助手**")
            _render_mobsf_prefill_candidates(app_tool, recent_scans, "最近扫描", "mobsf_recent_prefill")

    with tab_search:
        _render_structured_payload(search_result, "还没有执行 MobSF 搜索。")
        if search_result:
            st.markdown("**搜索结果回填助手**")
            _render_mobsf_prefill_candidates(app_tool, search_result, "搜索结果", "mobsf_search_prefill")

    with tab_dynamic:
        st.markdown(
            '<div class="security-note">动态分析结果仍依赖 MobSF 侧已经准备好的模拟器、真机、Frida、Corellium 或越狱设备环境。当前页面负责按官方 REST API 拉取动态报告，并整理为测试视角的问题清单和复测建议。</div>',
            unsafe_allow_html=True,
        )
        dyn_tab1, dyn_tab2, dyn_tab3 = st.tabs(["Android", "iOS Corellium", "iOS 越狱设备"])

        with dyn_tab1:
            st.caption("Android 动态报告官方要求 `hash`。可直接复用静态分析阶段返回的 hash。")
            st.text_input(
                "Android 动态报告 Hash",
                key="app_sec_mobsf_dynamic_android_hash",
                placeholder="输入 MobSF 动态分析对应的 hash",
            )
            android_action_col1, android_action_col2, android_action_col3, android_action_col4 = st.columns(4)
            with android_action_col1:
                if st.button(
                    "📱 获取 Android 可分析应用",
                    key="app_sec_mobsf_get_android_apps",
                    use_container_width=True,
                    disabled=not current_profile_ready,
                ):
                    try:
                        st.session_state.app_sec_mobsf_android_dynamic_apps = app_tool.mobsf_get_android_dynamic_apps(
                            base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                            api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                            timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                            verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                        )
                        st.success("Android 可分析应用列表已刷新。")
                    except Exception as exc:
                        st.error(f"获取 Android 应用列表失败: {exc}")
            with android_action_col2:
                if st.button(
                    "▶️ 启动动态分析",
                    key="app_sec_mobsf_start_android_dynamic_report",
                    use_container_width=True,
                    disabled=not current_profile_ready,
                ):
                    android_hash = str(st.session_state.get("app_sec_mobsf_dynamic_android_hash", "") or "").strip()
                    if not android_hash:
                        st.warning("请先输入 Android 动态分析对应的 hash。")
                    else:
                        try:
                            st.session_state.app_sec_mobsf_android_dynamic_action_result = app_tool.mobsf_start_android_dynamic_analysis(
                                base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                                api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                                file_hash=android_hash,
                                timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                                verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                            )
                            st.success("Android 动态分析已启动。请在设备或模拟器里操作目标应用，完成后点“停止并收集结果”。")
                        except Exception as exc:
                            _render_mobsf_android_dynamic_environment_hint(app_tool, exc, "启动 Android 动态分析")
            with android_action_col3:
                if st.button(
                    "⏹️ 停止并收集结果",
                    key="app_sec_mobsf_stop_android_dynamic_report",
                    use_container_width=True,
                    disabled=not current_profile_ready,
                ):
                    android_hash = str(st.session_state.get("app_sec_mobsf_dynamic_android_hash", "") or "").strip()
                    if not android_hash:
                        st.warning("请先输入 Android 动态分析对应的 hash。")
                    else:
                        try:
                            st.session_state.app_sec_mobsf_android_dynamic_action_result = app_tool.mobsf_stop_android_dynamic_analysis(
                                base_url=st.session_state.get("app_sec_mobsf_base_url", ""),
                                api_key=st.session_state.get("app_sec_mobsf_api_key", ""),
                                file_hash=android_hash,
                                timeout_seconds=float(st.session_state.get("app_sec_mobsf_timeout", 180.0) or 180.0),
                                verify_ssl=bool(st.session_state.get("app_sec_mobsf_verify_ssl", True)),
                            )
                            try:
                                _load_mobsf_android_dynamic_bundle(app_tool, android_hash)
                                st.success("Android 动态分析已停止，报告已拉取。")
                            except Exception as report_exc:
                                if app_tool.is_mobsf_dynamic_report_unavailable_error(report_exc):
                                    st.success("Android 动态分析已停止，MobSF 正在收集结果。")
                                    _render_mobsf_android_dynamic_report_unavailable_hint(app_tool, android_hash)
                                else:
                                    st.warning(f"Android 动态分析已停止，但自动拉报告失败: {report_exc}")
                        except Exception as exc:
                            _render_mobsf_android_dynamic_environment_hint(app_tool, exc, "停止 Android 动态分析")
            with android_action_col4:
                if st.button(
                    "📥 拉 Android 动态报告",
                    key="app_sec_mobsf_get_android_dynamic_report",
                    use_container_width=True,
                    disabled=not current_profile_ready,
                ):
                    android_hash = str(st.session_state.get("app_sec_mobsf_dynamic_android_hash", "") or "").strip()
                    if not android_hash:
                        st.warning("请先输入 Android 动态分析对应的 hash。")
                    else:
                        try:
                            _load_mobsf_android_dynamic_bundle(app_tool, android_hash)
                            st.success("Android 动态报告已拉取。")
                        except Exception as exc:
                            _handle_mobsf_android_dynamic_report_exception(
                                app_tool,
                                android_hash,
                                exc,
                                "获取 Android 动态报告",
                            )
            if android_dynamic_apps:
                st.markdown("**Android 可分析应用**")
                _render_structured_payload(android_dynamic_apps, "暂无 Android 可分析应用数据。")
                _render_mobsf_android_dynamic_apps_hint(android_dynamic_apps)
                _render_mobsf_prefill_candidates(app_tool, android_dynamic_apps, "Android 可分析应用", "mobsf_android_apps_prefill")
            if android_dynamic_action_result:
                st.markdown("**Android 动态执行状态**")
                _render_structured_payload(android_dynamic_action_result, "暂无 Android 动态执行状态。")
            _render_mobsf_runtime_bundle(android_dynamic_bundle, "还没有拉取 Android 动态报告。")

        with dyn_tab2:
            st.caption("iOS Corellium 动态报告官方要求 `instance_id + bundle_id`。")
            ios_col1, ios_col2 = st.columns(2)
            with ios_col1:
                st.text_input(
                    "Corellium Instance ID",
                    key="app_sec_mobsf_dynamic_ios_instance_id",
                    placeholder="输入 MobSF / Corellium instance_id",
                )
            with ios_col2:
                st.text_input(
                    "iOS Bundle ID",
                    key="app_sec_mobsf_dynamic_ios_bundle_id",
                    placeholder="例如 com.demo.app",
                )
            if st.button("🍎 拉 iOS Corellium 动态报告", key="app_sec_mobsf_get_ios_dynamic_report", use_container_width=True):
                instance_id = str(st.session_state.get("app_sec_mobsf_dynamic_ios_instance_id", "") or "").strip()
                bundle_id = str(st.session_state.get("app_sec_mobsf_dynamic_ios_bundle_id", "") or "").strip()
                if not instance_id or not bundle_id:
                    st.warning("请先输入 instance_id 和 bundle_id。")
                else:
                    try:
                        _load_mobsf_ios_dynamic_bundle(app_tool, instance_id, bundle_id)
                        st.success("iOS Corellium 动态报告已拉取。")
                    except Exception as exc:
                        st.error(f"获取 iOS Corellium 动态报告失败: {exc}")
            _render_mobsf_runtime_bundle(ios_dynamic_bundle, "还没有拉取 iOS Corellium 动态报告。")

        with dyn_tab3:
            st.caption("越狱 iOS 真机动态报告官方要求 `device_id + bundle_id`。")
            ios_device_col1, ios_device_col2 = st.columns(2)
            with ios_device_col1:
                st.text_input(
                    "iOS Device ID",
                    key="app_sec_mobsf_dynamic_ios_device_id",
                    placeholder="输入越狱 iOS 设备 device_id",
                )
            with ios_device_col2:
                st.text_input(
                    "iOS Device Bundle ID",
                    key="app_sec_mobsf_dynamic_ios_device_bundle_id",
                    placeholder="例如 com.demo.app",
                )
            if st.button("📲 拉 iOS 真机动态报告", key="app_sec_mobsf_get_ios_device_dynamic_report", use_container_width=True):
                device_id = str(st.session_state.get("app_sec_mobsf_dynamic_ios_device_id", "") or "").strip()
                bundle_id = str(st.session_state.get("app_sec_mobsf_dynamic_ios_device_bundle_id", "") or "").strip()
                if not device_id or not bundle_id:
                    st.warning("请先输入 device_id 和 bundle_id。")
                else:
                    try:
                        _load_mobsf_ios_device_dynamic_bundle(app_tool, device_id, bundle_id)
                        st.success("iOS 真机动态报告已拉取。")
                    except Exception as exc:
                        st.error(f"获取 iOS 真机动态报告失败: {exc}")
            _render_mobsf_runtime_bundle(ios_device_dynamic_bundle, "还没有拉取 iOS 真机动态报告。")

        st.markdown("**准备建议**")
        for note in quick_start.get("notes", []):
            st.markdown(f"- {note}")

    with tab_export:
        def append_review_exports(export_items: List[Dict[str, Any]], label_prefix: str, file_prefix: str, review_bundle: Dict[str, Any]):
            if not review_bundle:
                return
            export_items.append(
                {
                    "label": f"下载 {label_prefix}二次整理 JSON",
                    "data": json.dumps(review_bundle, ensure_ascii=False, indent=2),
                    "file_name": f"{file_prefix}_review.json",
                    "mime": "application/json",
                }
            )
            export_items.append(
                {
                    "label": f"下载 {label_prefix}问题清单 CSV",
                    "data": pd.DataFrame(review_bundle.get("issue_register", [])).to_csv(index=False),
                    "file_name": f"{file_prefix}_issue_register.csv",
                    "mime": "text/csv",
                }
            )
            export_items.append(
                {
                    "label": f"下载 {label_prefix}回归套件 CSV",
                    "data": pd.DataFrame(review_bundle.get("regression_suite", [])).to_csv(index=False),
                    "file_name": f"{file_prefix}_regression_suite.csv",
                    "mime": "text/csv",
                }
            )
            export_items.append(
                {
                    "label": f"下载 {label_prefix}二次整理 Markdown",
                    "data": review_bundle.get("markdown", ""),
                    "file_name": f"{file_prefix}_review.md",
                    "mime": "text/markdown",
                }
            )

        def append_runtime_bundle_exports(export_items: List[Dict[str, Any]], label_prefix: str, file_prefix: str, runtime_bundle: Dict[str, Any]):
            if not runtime_bundle:
                return
            export_items.append(
                {
                    "label": f"下载 {label_prefix}Bundle JSON",
                    "data": json.dumps(runtime_bundle, ensure_ascii=False, indent=2),
                    "file_name": f"{file_prefix}_bundle.json",
                    "mime": "application/json",
                }
            )
            export_items.append(
                {
                    "label": f"下载 {label_prefix}动态报告 JSON",
                    "data": json.dumps(runtime_bundle.get("json_report", {}), ensure_ascii=False, indent=2),
                    "file_name": f"{file_prefix}_report.json",
                    "mime": "application/json",
                }
            )
            append_review_exports(export_items, label_prefix, file_prefix, runtime_bundle.get("review_bundle", {}))

        export_items = [
            {
                "label": "下载 MobSF 快速上手 Markdown",
                "data": "\n".join([
                    "# MobSF 集成说明",
                    "",
                    f"- 官方仓库: {quick_start.get('official_repo', '')}",
                    "",
                    "## Docker 启动",
                    *[f"- `{command}`" for command in quick_start.get("docker_commands", [])],
                    "",
                    "## 静态分析 API",
                    *[
                        f"- {item['method']} {item['path']} : {item['description']}"
                        for item in quick_start.get("static_endpoints", [])
                    ],
                    "",
                    "## Android 动态分析 API",
                    *[
                        f"- {item['method']} {item['path']} : {item['description']}"
                        for item in quick_start.get("android_dynamic_endpoints", [])
                    ],
                    "",
                    "## iOS 动态分析 API",
                    *[
                        f"- {item['method']} {item['path']} : {item['description']}"
                        for item in quick_start.get("ios_dynamic_endpoints", [])
                    ],
                    "",
                    "## iOS 越狱设备动态 API",
                    *[
                        f"- {item['method']} {item['path']} : {item['description']}"
                        for item in quick_start.get("ios_device_dynamic_endpoints", [])
                    ],
                ]),
                "file_name": "mobsf_quick_start.md",
                "mime": "text/markdown",
            },
        ]
        if bundle:
            export_items.append(
                {
                    "label": "下载 MobSF 静态分析 Bundle JSON",
                    "data": json.dumps({k: v for k, v in bundle.items() if k != "pdf_bytes"}, ensure_ascii=False, indent=2),
                    "file_name": "mobsf_static_bundle.json",
                    "mime": "application/json",
                }
            )
            export_items.append(
                {
                    "label": "下载 MobSF JSON 报告",
                    "data": json.dumps(bundle.get("json_report", {}), ensure_ascii=False, indent=2),
                    "file_name": f"mobsf_report_{bundle.get('hash', 'latest')}.json",
                    "mime": "application/json",
                }
            )
            export_items.append(
                {
                    "label": "下载 MobSF Scorecard",
                    "data": json.dumps(bundle.get("scorecard", {}), ensure_ascii=False, indent=2),
                    "file_name": f"mobsf_scorecard_{bundle.get('hash', 'latest')}.json",
                    "mime": "application/json",
                }
            )
            if bundle.get("review_bundle"):
                append_review_exports(
                    export_items,
                    "MobSF 静态分析",
                    f"mobsf_static_{bundle.get('hash', 'latest')}",
                    bundle.get("review_bundle", {}),
                )
            if bundle.get("pdf_bytes"):
                export_items.append(
                    {
                        "label": "下载 MobSF PDF 报告",
                        "data": bundle.get("pdf_bytes", b""),
                        "file_name": f"mobsf_report_{bundle.get('hash', 'latest')}.pdf",
                        "mime": "application/pdf",
                    }
                )
        if hash_report:
            export_items.append(
                {
                    "label": "下载按 Hash 拉取的 JSON 报告",
                    "data": json.dumps(hash_report, ensure_ascii=False, indent=2),
                    "file_name": "mobsf_hash_report.json",
                    "mime": "application/json",
                }
            )
            if hash_review_bundle:
                append_review_exports(export_items, "按 Hash 静态结果", "mobsf_hash_static", hash_review_bundle)
        if hash_scorecard:
            export_items.append(
                {
                    "label": "下载按 Hash 拉取的 Scorecard",
                    "data": json.dumps(hash_scorecard, ensure_ascii=False, indent=2),
                    "file_name": "mobsf_hash_scorecard.json",
                    "mime": "application/json",
                }
            )
        if hash_pdf_bytes:
            export_items.append(
                {
                    "label": "下载按 Hash 拉取的 PDF",
                    "data": hash_pdf_bytes,
                    "file_name": "mobsf_hash_report.pdf",
                    "mime": "application/pdf",
                }
            )
        if android_dynamic_apps:
            export_items.append(
                {
                    "label": "下载 Android 可分析应用 JSON",
                    "data": json.dumps(android_dynamic_apps, ensure_ascii=False, indent=2),
                    "file_name": "mobsf_android_dynamic_apps.json",
                    "mime": "application/json",
                }
            )
        append_runtime_bundle_exports(export_items, "Android 动态", "mobsf_android_dynamic", android_dynamic_bundle)
        append_runtime_bundle_exports(export_items, "iOS Corellium 动态", "mobsf_ios_dynamic", ios_dynamic_bundle)
        append_runtime_bundle_exports(export_items, "iOS 真机动态", "mobsf_ios_device_dynamic", ios_device_dynamic_bundle)

        render_download_panel(
            title="MobSF 导出区",
            description="统一导出 MobSF 快速上手说明、静态/动态分析结果和按 Hash 拉取的报告。",
            items=export_items,
            key_prefix="mobsf_security_exports",
            metrics=[
                {"label": "最近扫描", "value": str(len(recent_scans) if isinstance(recent_scans, list) else int(bool(recent_scans)))},
                {"label": "搜索结果", "value": str(len(search_result) if isinstance(search_result, list) else int(bool(search_result)))},
                {
                    "label": "动态结果",
                    "value": str(
                        sum(
                            1
                            for item in [android_dynamic_bundle, ios_dynamic_bundle, ios_device_dynamic_bundle]
                            if item
                        )
                    ),
                },
            ],
            empty_message="先执行 MobSF 上传扫描、拉取静态或动态报告后才能导出。",
        )

    st.markdown("</div>", unsafe_allow_html=True)


def _render_mobile_security_tab(app_tool: ApplicationSecurityTool):
    mobile_tab1, mobile_tab2 = st.tabs(["本地静态扫描", "MobSF 集成"])
    with mobile_tab1:
        _render_local_mobile_security_tab(app_tool)
    with mobile_tab2:
        _render_mobsf_mobile_security_tab(app_tool)


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
            <p>统一的应用安全工作台，覆盖 API 文档安全、移动端 APK/IPA/APPX 静态扫描、MobSF 官方集成和 Web 站点基线扫描。默认坚持安全边界，只做授权范围内的低风险探测和清单化审计。</p>
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
    tab_api, tab_mobile, tab_web = st.tabs(["API 文档安全", "移动包 / MobSF", "Web 站点 URL"])

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
