import json
import hashlib
import os
import shutil
import subprocess
import sys
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from qa_toolkit.core.env_profile_manager import get_session_env_profile_manager
from qa_toolkit.core.i18n import t
from qa_toolkit.core.task_runner import get_session_task_runner
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore
from qa_toolkit.core import api_automation_registry as auto_reg
from qa_toolkit.reporting.report_generator import EnhancedReportGenerator
from qa_toolkit.reporting.test_runner import EnhancedTestRunner
from qa_toolkit.ui.components.env_profile_panel import render_env_profile_panel
from qa_toolkit.ui.components.task_run_panel import render_task_run_panel
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.workflow_panels import render_download_panel, render_workflow_guide


INTERFACE_FILE_TYPES = ["xlsx", "xls", "json", "har", "bru", "txt", "md", "yaml", "yml"]
IMPORT_FORMAT_MAP = {
    "自动检测": "auto",
    "JSON / Apifox / Postman / HAR / Insomnia": "json",
    "Swagger/OpenAPI": "swagger",
    "结构化文本": "text",
    "Bruno .bru": "bruno",
}


def get_mirror_urls() -> Dict[str, str]:
    """镜像源来自注册式扩展点，下游可注册企业内部源。"""
    return auto_reg.get_mirrors()


def get_auth_mode_map() -> Dict[str, str]:
    return {spec.label: spec.mode for spec in auto_reg.get_auth_modes().values() if spec.mode != "none"}


def get_auth_label_map() -> Dict[str, str]:
    return {spec.mode: spec.label for spec in auto_reg.get_auth_modes().values() if spec.mode != "none"}


# ---------------------------------------------------------------------------
# 统一导出 / 文字结论 / 配置签名
# ---------------------------------------------------------------------------

def _csv_bytes(rows: Sequence[Dict[str, Any]]) -> bytes:
    """所有 CSV 导出统一走注册式公式注入清洗器。"""
    return auto_reg.csv_bytes(rows)


def _build_download_payload(
    result: Dict[str, Any],
    *,
    config_snapshot: Optional[Dict[str, Any]] = None,
    input_signature: str = "",
    warnings: Optional[Sequence[str]] = None,
    truncation: Optional[Dict[str, Any]] = None,
) -> str:
    """导出件统一附配置快照 / 输入签名 / 能力摘要 / 告警 / 截断信息。"""
    payload = auto_reg.build_export_payload(
        result,
        config_snapshot=config_snapshot,
        input_signature=input_signature,
        warnings=warnings,
        truncation=truncation,
    )
    return auto_reg.strict_json_dumps(payload, indent=2)


def _render_registry_summary() -> None:
    """首屏直接展示注册能力与安全默认值，不藏进折叠面板。"""
    summary = auto_reg.get_registry_summary()
    limits = auto_reg.get_automation_limits()
    st.caption(
        t(
            "🧩 当前注册的能力：HTTP 方法 {m} 个 / 请求格式 {f} 种 / 执行模式 {e} 种 / "
            "鉴权方式 {a} 种 / 模板风格 {ts} 种 / 断言策略 {ast} 种 / "
            "状态码分桶 {sb} 类 / 导入模板 {it} 份 / 报告模板 {rt} 种 / 导出格式 {ef} 种 / 镜像源 {mi} 个。",
            m=summary["HTTP 方法"], f=summary["请求格式"], e=summary["执行模式"],
            a=summary["鉴权方式"], ts=summary["模板风格"], ast=summary["断言策略"],
            sb=summary["状态码分桶"], it=summary["导入模板"], rt=summary["报告模板"],
            ef=summary["导出格式"], mi=summary["镜像源"],
        )
    )
    # 接入状态：只把真正接入产物链的项当成可用能力，仅登记项单独标注（#423/R3-09）。
    _access = summary.get("接入状态", {})
    st.caption(
        t(
            "🔌 接入状态：报告模板可用 {r1}/{rt}、导出格式可用 {e1}/{ef}、"
            "框架渲染器 {fw} 种；仅登记（暂不可用）：报告 {only_r}、导出 {only_e}。",
            r1=len(_access.get("已接入报告模板", [])), rt=summary["报告模板"],
            e1=len(_access.get("已接入导出格式", [])), ef=summary["导出格式"],
            fw=len(_access.get("已接入框架渲染器", [])),
            only_r=_access.get("仅登记报告模板", []) or t("无"),
            only_e=_access.get("仅登记导出格式", []) or t("无"),
        )
    )
    st.caption(
        t(
            "安全默认：仅允许 {proto}；默认校验 SSL={ssl}；默认允许内网目标={priv}；"
            "默认产物保留凭据={keep}；运行上限：接口 {mi} / 上传 {mb} bytes / "
            "超时 {mt}s / 重试 {rt} / 响应体 {rb} 字符。",
            proto="/".join(auto_reg.get_protocols()), ssl=limits.default_verify_ssl,
            priv=limits.allow_private_targets, keep=limits.allow_credentials_in_artifacts,
            mi=limits.max_interfaces, mb=limits.max_upload_bytes,
            mt=limits.max_timeout_seconds, rt=limits.max_retry_times,
            rb=limits.max_response_body_chars,
        )
    )


def _render_warnings_panel(warnings: Sequence[str], truncation: Optional[Dict[str, Any]] = None) -> None:
    items = [str(w) for w in (warnings or []) if str(w).strip()]
    if items:
        with st.expander(f"⚠️ 生成/执行告警（{len(items)}）", expanded=True):
            for item in items:
                st.caption(f"- {item}")
    if truncation:
        st.warning(f"存在截断，导出件已标注 truncation：{truncation}")


def _render_text_summary(test_results: Dict[str, Any]) -> None:
    """把结论渲染成纯文本（dataframe 是 canvas，读屏/e2e 读不到）。"""
    total = int(test_results.get("total", 0) or 0)
    passed = int(test_results.get("passed", 0) or 0)
    failed = int(test_results.get("failed", 0) or 0)
    errors = int(test_results.get("errors", 0) or 0)
    details = list(test_results.get("test_details") or [])
    failed_items = [d for d in details if d.get("status") in ("failed", "error")]
    degrade = f" 执行说明：{test_results['runner_note']}" if test_results.get("runner_note") else ""
    coverage = ""
    if len(details) < total:
        coverage = f" 注意：{total - len(details)} 个用例未采集到明细。"
    text = auto_reg.build_text_summary("results", {
        "total": total, "passed": passed, "failed": failed, "errors": errors,
        "rate": (passed / total * 100) if total else 0.0,
        "degrade": degrade,
        "failed_hint": f" 失败/错误接口：{'、'.join(str(d.get('name') or d.get('path') or '未命名') for d in failed_items[:8])}。" if failed_items else " 无失败接口。",
        "coverage": coverage,
    })
    st.markdown("#### 📝 本轮测试结论")
    st.write(text)
    for detail in failed_items[:10]:
        st.caption(
            f"- {detail.get('method', 'GET')} {detail.get('path', '')} {detail.get('name', '未知接口')} | "
            f"{detail.get('status', 'unknown')} | 状态码 {detail.get('status_code', 'N/A')} | "
            f"{str(detail.get('error') or '无错误信息')[:200]}"
        )


def _current_config_signature(
    interfaces: Sequence[Dict[str, Any]],
    execution_mode: str,
    base_url: str,
    timeout: int,
    retry_times: int,
    verify_ssl: bool,
    request_format: str,
    template_style: str,
    environment_config: Optional[Dict[str, Any]],
    auth_config: Dict[str, Any],
    allow_private_targets: bool,
    include_credentials: bool,
) -> str:
    """接口清单 + 全部执行配置一起签名，改任何一项都会让旧产物过期。"""
    auth_fingerprint = hashlib.sha256(
        json.dumps(auth_config or {}, sort_keys=True, default=str, ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    return auto_reg.compute_signature({
        "interfaces": _interfaces_signature(interfaces),
        "execution_mode": execution_mode,
        "base_url": str(base_url or "").strip(),
        "timeout": int(timeout),
        "retry_times": int(retry_times),
        "verify_ssl": bool(verify_ssl),
        "request_format": request_format,
        "template_style": template_style,
        "environment_config": environment_config,
        "auth_fingerprint": auth_fingerprint,
        "allow_private_targets": bool(allow_private_targets),
        "include_credentials": bool(include_credentials),
    })


def _install_missing_packages(packages: Sequence[str], mirror_url: str) -> bool:
    """安装缺失的包。"""
    try:
        for package in packages:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    package,
                    "-i",
                    mirror_url,
                    "--trusted-host",
                    mirror_url.split("/")[2],
                    "--timeout",
                    "60",
                ],
                capture_output=True,
                text=True,
                check=False,
            )

            if result.returncode != 0:
                st.error(f"安装 {package} 失败: {result.stderr}")
                return False
        return True
    except Exception as exc:
        st.error(f"安装过程中出错: {exc}")
        return False


def _check_interface_dependencies(selected_mode: str, for_execution: bool = False) -> bool:
    """检查接口测试工具依赖。"""
    required_packages = {
        "requests": "requests",
        "pandas": "pandas",
        "openpyxl": "openpyxl",
    }
    if selected_mode == "pytest" and for_execution:
        required_packages["pytest"] = "pytest"

    missing_packages = []
    for package_name, import_name in required_packages.items():
        try:
            __import__(import_name)
        except ImportError:
            missing_packages.append(package_name)

    if for_execution and selected_mode == "pytest" and missing_packages == ["pytest"]:
        st.info("当前环境未安装 `pytest`，执行时会自动降级为 `requests脚本`，不影响本次运行。")
        return True

    if not missing_packages:
        return True

    title = "当前执行模式运行时缺少依赖包" if for_execution else "当前页面缺少基础依赖包"
    st.warning(f"⚠️ {title}: {', '.join(missing_packages)}")

    col1, col2 = st.columns([2, 1])
    with col1:
        st.markdown("**缺失的依赖:**")
        for dep in missing_packages:
            st.write(f"- {dep}")

    with col2:
        mirror_options = get_mirror_urls()
        mirror = st.selectbox(
            "选择镜像源",
            list(mirror_options.keys()),
            key=f"interface_mirror_{selected_mode}_{'exec' if for_execution else 'page'}",
        )
        if st.button(
            "🚀 自动安装依赖",
            use_container_width=True,
            key=f"install_interface_deps_{selected_mode}_{'exec' if for_execution else 'page'}",
        ):
            with st.spinner("正在安装依赖..."):
                success = _install_missing_packages(missing_packages, mirror_options[mirror])
            if success:
                st.success("✅ 依赖安装成功，请刷新页面后重试")
            else:
                st.error("❌ 依赖安装失败，请手动安装")

    with st.expander("📋 手动安装指南", expanded=True):
        st.code(f"pip install {' '.join(missing_packages)} -i https://pypi.tuna.tsinghua.edu.cn/simple/")

    return False


def _create_jsonplaceholder_test_data() -> Tuple[str, List[Dict[str, Any]]]:
    """创建 JSONPlaceholder 测试数据。"""
    base_url = "https://jsonplaceholder.typicode.com"
    interfaces = [
        {
            "name": "获取所有帖子",
            "method": "GET",
            "path": "/posts",
            "description": "获取所有帖子列表",
            "expected_status": 200,
            "expected_response": ["userId", "id", "title", "body"],
        },
        {
            "name": "获取单个帖子",
            "method": "GET",
            "path": "/posts/1",
            "description": "获取 ID 为 1 的帖子详情",
            "expected_status": 200,
            "expected_response": ["userId", "id", "title", "body"],
        },
        {
            "name": "获取用户帖子",
            "method": "GET",
            "path": "/posts",
            "description": "按用户查询帖子",
            "query_params": {"userId": 1},
            "expected_status": 200,
            "expected_response": ["userId", "id", "title", "body"],
        },
        {
            "name": "创建新帖子",
            "method": "POST",
            "path": "/posts",
            "description": "创建新的帖子",
            "headers": {"Content-Type": "application/json"},
            "body": {
                "title": "自动化测试帖子",
                "body": "这是通过自动化测试工具创建的帖子",
                "userId": 1,
            },
            "expected_status": 201,
            "expected_response": ["id"],
        },
    ]
    return base_url, interfaces


def _create_reqres_test_data() -> Tuple[str, List[Dict[str, Any]]]:
    """创建 ReqRes 测试数据。"""
    base_url = "https://reqres.in/api"
    interfaces = [
        {
            "name": "获取用户列表",
            "method": "GET",
            "path": "/users",
            "description": "获取分页用户列表",
            "query_params": {"page": 2},
            "expected_status": 200,
            "expected_response": ["page", "per_page", "total", "data"],
        },
        {
            "name": "获取单个用户",
            "method": "GET",
            "path": "/users/2",
            "description": "获取用户详情",
            "expected_status": 200,
            "expected_response": ["data"],
        },
        {
            "name": "用户登录",
            "method": "POST",
            "path": "/login",
            "description": "用户登录接口",
            "headers": {"Content-Type": "application/json"},
            "body": {
                "email": "eve.holt@reqres.in",
                "password": "cityslicka",
            },
            "expected_status": 200,
            "expected_response": ["token"],
        },
    ]
    return base_url, interfaces


def _interfaces_signature(interfaces: Sequence[Dict[str, Any]]) -> str:
    """生成接口清单的稳定指纹，用于判定磁盘上的测试产物是否对应当前清单。"""
    payload = json.dumps(interfaces or [], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _set_interface_state(interfaces: List[Dict[str, Any]], base_url: str = "", source_name: str = "") -> None:
    st.session_state.interface_loaded_interfaces = interfaces
    st.session_state.interface_loaded_base_url = base_url or ""
    st.session_state.interface_source_name = source_name or ""
    st.session_state.interface_loaded_signature = _interfaces_signature(interfaces)
    st.session_state.pop("interface_last_generated_files", None)
    st.session_state.pop("interface_last_test_results", None)
    # 接口清单已变更，磁盘上旧产物不再对应当前清单
    st.session_state.pop("interface_generated_signature", None)


def _clear_interface_state() -> None:
    for key in [
        "interface_loaded_interfaces",
        "interface_loaded_base_url",
        "interface_source_name",
        "interface_last_generated_files",
        "interface_last_test_results",
        "interface_loaded_signature",
        "interface_generated_signature",
        "interface_upload_signature",
    ]:
        st.session_state.pop(key, None)


def _render_interface_preview(interfaces: List[Dict[str, Any]]) -> None:
    st.markdown("### Step 2. 预览接口清单")
    st.caption("先确认方法、路径、请求体和期望状态码，再进入生成与执行。")
    for index, interface in enumerate(interfaces, start=1):
        with st.expander(f"{index}. {interface.get('name', '未命名接口')}", expanded=False):
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**方法:** `{interface.get('method', 'GET')}`")
                st.write(f"**路径:** `{interface.get('path', '')}`")
                st.write(f"**期望状态码:** `{interface.get('expected_status', 200)}`")
                if interface.get("tags"):
                    st.write(f"**标签:** {', '.join(interface.get('tags', []))}")
            with col2:
                st.write(f"**描述:** {interface.get('description', '无描述')}")
                if interface.get("headers"):
                    st.write("**请求头:**")
                    st.json(interface["headers"])
                if interface.get("path_params"):
                    st.write("**路径参数:**")
                    st.json(interface["path_params"])
                if interface.get("query_params"):
                    st.write("**查询参数:**")
                    st.json(interface["query_params"])
                if interface.get("body") not in [None, {}, []]:
                    st.write("**请求体:**")
                    st.json(interface["body"])
                elif interface.get("parameters"):
                    st.write("**请求参数:**")
                    if isinstance(interface["parameters"], (dict, list)):
                        st.json(interface["parameters"])
                    else:
                        st.write(interface["parameters"])


def _build_env_template_with_base_url(base_url: str) -> str:
    template = json.loads(st.session_state.auto_test_tool.build_environment_template())
    normalized_base_url = base_url.strip()
    if normalized_base_url:
        template["environments"]["dev"]["base_url"] = normalized_base_url
    return json.dumps(template, ensure_ascii=False, indent=2)


def _capture_interface_env_profile() -> Dict[str, Any]:
    auth_mode_label = str(st.session_state.get("interface_auth_mode", "无") or "无")
    auth_mode = get_auth_mode_map().get(auth_mode_label, "none")
    auth: Dict[str, Any] = {"mode": auth_mode}

    if auth_mode == "bearer":
        auth["token"] = str(st.session_state.get("interface_bearer_token", "") or "").strip()
    elif auth_mode == "api_key":
        auth["header_name"] = str(st.session_state.get("interface_api_key_name", "X-API-Key") or "X-API-Key").strip() or "X-API-Key"
        auth["api_key_value"] = str(st.session_state.get("interface_api_key_value", "") or "").strip()
    elif auth_mode == "basic":
        auth["username"] = str(st.session_state.get("interface_basic_username", "") or "").strip()
        auth["password"] = str(st.session_state.get("interface_basic_password", "") or "").strip()
    elif auth_mode == "custom_header":
        auth["header_name"] = str(st.session_state.get("interface_custom_header_name", "X-Custom-Auth") or "X-Custom-Auth").strip() or "X-Custom-Auth"
        auth["header_value"] = str(st.session_state.get("interface_custom_header_value", "") or "").strip()

    base_url = str(
        st.session_state.get(
            "interface_base_url_input_v2",
            st.session_state.get("interface_loaded_base_url", ""),
        )
        or ""
    ).strip()
    return {
        "base_url": base_url,
        "timeout_seconds": int(st.session_state.get("interface_timeout_v2", 30) or 30),
        "retry_times": int(st.session_state.get("interface_retry_times_v2", 0) or 0),
        "verify_ssl": bool(st.session_state.get("interface_verify_ssl_v2", False)),
        "auth": auth,
        "headers": {},
    }


def _apply_interface_env_profile(profile: Dict[str, Any]) -> None:
    base_url = str(profile.get("base_url") or "").strip()
    st.session_state.interface_base_url_input_v2 = base_url
    st.session_state.interface_loaded_base_url = base_url
    st.session_state.interface_timeout_v2 = max(1, int(profile.get("timeout_seconds") or 30))
    st.session_state.interface_retry_times_v2 = max(0, int(profile.get("retry_times") or 0))
    st.session_state.interface_verify_ssl_v2 = bool(profile.get("verify_ssl", False))

    auth = profile.get("auth") if isinstance(profile.get("auth"), dict) else {}
    auth_mode = str(auth.get("mode") or "none").strip().lower()
    st.session_state.interface_auth_mode = get_auth_label_map().get(auth_mode, "无")

    st.session_state.interface_bearer_token = str(auth.get("token") or "").strip()
    st.session_state.interface_api_key_name = str(auth.get("header_name") or "X-API-Key").strip() or "X-API-Key"
    st.session_state.interface_api_key_value = str(auth.get("api_key_value") or "").strip()
    st.session_state.interface_basic_username = str(auth.get("username") or "").strip()
    st.session_state.interface_basic_password = str(auth.get("password") or "").strip()
    st.session_state.interface_custom_header_name = str(auth.get("header_name") or "X-Custom-Auth").strip() or "X-Custom-Auth"
    st.session_state.interface_custom_header_value = str(auth.get("header_value") or "").strip()


def _generate_artifacts(
    interfaces: List[Dict[str, Any]],
    execution_mode: str,
    base_url: str,
    timeout: int,
    retry_times: int,
    verify_ssl: bool,
    request_format: str,
    template_style: str,
    environment_config: Optional[Dict[str, Any]] = None,
    auth_config: Optional[Dict[str, Any]] = None,
    config_signature: str = "",
    allow_private_targets: bool = False,
    include_credentials: bool = False,
) -> Dict[str, str]:
    tool = st.session_state.auto_test_tool
    tool.set_allow_private_targets(bool(allow_private_targets))
    with st.spinner("正在生成测试用例..."):
        test_files = tool.generate_test_cases(
            interfaces=interfaces,
            framework=execution_mode,
            base_url=base_url,
            timeout=timeout,
            retry_times=retry_times,
            verify_ssl=verify_ssl,
            request_format=request_format,
            template_style=template_style,
            environment_config=environment_config,
            auth_config=auth_config,
            include_credentials=bool(include_credentials),
        )
        tool.save_test_files(test_files)
        manifest = json.loads(test_files["interface_manifest.json"])
        st.session_state.interface_last_generated_files = test_files
        st.session_state.interface_generated_signature = _interfaces_signature(interfaces)
        # 配置也纳入签名：改 base_url / 鉴权 / 模板风格 / 执行模式都会让旧产物过期。
        st.session_state.interface_generated_config_signature = config_signature
        st.session_state.interface_generated_config_snapshot = manifest.get("config_snapshot", {})
        st.session_state.interface_generated_warnings = tool.get_warnings()
        st.session_state.interface_generated_truncation = manifest.get("truncation", {})
        st.session_state.interface_result_config_signature = config_signature
        st.session_state.pop("api_auto_download_items_cache", None)
    return test_files


def _ensure_generated_file(execution_mode: str, current_signature: str = "") -> bool:
    spec = auto_reg.get_execution_modes().get(auto_reg.normalize_execution_mode(execution_mode)[0])
    target_file = spec.target_file if spec else "test_interfaces.py"
    manifest_file = os.path.join(st.session_state.auto_test_tool.test_dir, "interface_manifest.json")
    target_path = os.path.join(st.session_state.auto_test_tool.test_dir, target_file)
    if not (os.path.exists(manifest_file) and os.path.exists(target_path)):
        return False
    # 磁盘产物可能来自上一次加载的接口清单（清单切换只清了 session_state）
    loaded_signature = st.session_state.get("interface_loaded_signature")
    generated_signature = st.session_state.get("interface_generated_signature")
    if not loaded_signature or generated_signature != loaded_signature:
        return False
    # 配置变更同样让磁盘产物失效，避免用旧脚本跑新配置。
    if current_signature and st.session_state.get("interface_generated_config_signature") != current_signature:
        return False
    try:
        with open(manifest_file, "r", encoding="utf-8") as file:
            manifest = json.load(file)
    except Exception:
        return False
    expected_mode = st.session_state.auto_test_tool._normalize_execution_mode(execution_mode)
    return manifest.get("mode") == expected_mode


def _build_result_markdown(test_results: Dict[str, Any], execution_mode: str) -> str:
    actual_mode = test_results.get("executed_mode") or execution_mode
    total = int(test_results.get("total", 0) or 0)
    passed = int(test_results.get("passed", 0) or 0)
    failed = int(test_results.get("failed", 0) or 0)
    errors = int(test_results.get("errors", 0) or 0)
    success_rate = (passed / total * 100) if total else 0
    lines = [
        "# 接口自动化测试结果",
        "",
        f"- 执行模式: {actual_mode}",
        f"- 总用例数: {total}",
        f"- 通过: {passed}",
        f"- 失败: {failed}",
        f"- 错误: {errors}",
        f"- 成功率: {success_rate:.1f}%",
        "",
        "## 失败与错误摘要",
    ]
    if test_results.get("runner_note"):
        lines.insert(2, f"- 执行说明: {test_results['runner_note']}")
    details = list(test_results.get("test_details") or [])
    failed_items = [detail for detail in details if detail.get("status") in {"failed", "error"}]
    if not failed_items:
        lines.append("- 无")
    else:
        for detail in failed_items:
            lines.append(
                f"- `{detail.get('method', 'GET')} {detail.get('path', '')}` {detail.get('name', '未知接口')} | "
                f"状态: {detail.get('status', 'unknown')} | 状态码: {detail.get('status_code', 'N/A')} | "
                f"错误: {detail.get('error', '无错误信息')}"
            )
    return "\n".join(lines).strip() + "\n"


def _ensure_report_path(test_results: Dict[str, Any], execution_mode: str, interfaces: List[Dict[str, Any]]) -> str:
    """报告只在结果签名变化时生成一次（惰性），避免每次 rerun 都写盘。"""
    signature = auto_reg.compute_signature({
        "results": test_results,
        "interfaces": interfaces,
        "execution_mode": execution_mode,
    })
    cached = st.session_state.get("api_auto_report_cache")
    if cached and cached.get("signature") == signature and cached.get("path") and os.path.exists(cached["path"]):
        return cached["path"]
    path = st.session_state.enhanced_report.generate_detailed_report(
        test_results=test_results,
        framework=execution_mode,
        interfaces=interfaces,
        test_details=test_results.get("test_details", []),
    )
    st.session_state.api_auto_report_cache = {"signature": signature, "path": path or ""}
    return path or ""


def _render_test_results(test_results: Dict[str, Any], execution_mode: str, interfaces: List[Dict[str, Any]]) -> None:
    st.markdown("### Step 4. 查看执行结果")
    _render_text_summary(test_results)
    _render_warnings_panel(
        list(test_results.get("warnings") or [])
        + list(st.session_state.get("interface_generated_warnings") or []),
        test_results.get("truncation") or st.session_state.get("interface_generated_truncation"),
    )
    actual_mode = test_results.get("executed_mode") or execution_mode
    total = test_results.get("total", 0)
    passed = test_results.get("passed", 0)
    failed = test_results.get("failed", 0)
    errors = test_results.get("errors", 0)
    success_rate = (passed / total * 100) if total > 0 else 0

    if test_results.get("runner_note"):
        st.info(test_results["runner_note"])

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        st.metric("总用例数", total)
    with col2:
        st.metric("通过", passed)
    with col3:
        st.metric("失败", failed)
    with col4:
        st.metric("错误", errors)
    with col5:
        st.metric("成功率", f"{success_rate:.1f}%")

    if test_results.get("output"):
        with st.expander("🧾 执行日志", expanded=False):
            st.code(test_results["output"], language="text")

    download_items: List[Dict[str, Any]] = []
    if total > 0:
        report_path = _ensure_report_path(test_results, execution_mode, interfaces)
        if report_path and os.path.exists(report_path):
            with open(report_path, "rb") as file:
                report_data = file.read()
            download_items.append(
                {
                    "label": "📥 下载 HTML 报告",
                    "data": report_data,
                    "file_name": f"api_automation_report_{actual_mode}.html",
                    "mime": "text/html",
                    "caption": "适合直接归档或在浏览器中查看。",
                }
            )

    test_details = test_results.get("test_details", [])
    summary_rows: List[Dict[str, Any]] = []
    if test_details:
        st.markdown("### 📋 测试详情摘要")
        for detail in test_details:
            status_icon = "✅" if detail.get("status") == "passed" else "❌" if detail.get("status") == "failed" else "⚠️"
            summary_rows.append(
                {
                    "接口": detail.get("name", "未知"),
                    "环境": detail.get("environment", ""),
                    "方法": detail.get("method", "GET"),
                    "路径": detail.get("path", ""),
                    "状态": f"{status_icon} {detail.get('status', 'unknown')}",
                    "状态码": detail.get("status_code", "N/A"),
                    "响应时间": f"{detail.get('response_time', 0):.2f}s",
                }
            )
        st.dataframe(pd.DataFrame(summary_rows), use_container_width=True)

        failed_tests = [detail for detail in test_details if detail.get("status") in ["failed", "error"]]
        if failed_tests:
            st.markdown("#### ❌ 失败和错误详情")
            for detail in failed_tests:
                with st.expander(f"{detail.get('name', '未知接口')} - {detail.get('status', 'error')}", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**环境:** {detail.get('environment', '')}")
                        st.write(f"**方法:** {detail.get('method', 'GET')}")
                        st.write(f"**路径:** {detail.get('path', '')}")
                        st.write(f"**状态码:** {detail.get('status_code', 'N/A')}")
                        st.write(f"**响应时间:** {detail.get('response_time', 0):.2f}s")
                    with col2:
                        st.write("**错误信息:**")
                        st.error(detail.get("error", "无错误信息"))
                    if detail.get("assertions"):
                        st.write("**断言结果:**")
                        for assertion in detail.get("assertions", []):
                            if assertion.get("passed"):
                                st.success(f"✅ {assertion.get('description')}: {assertion.get('message')}")
                            else:
                                st.error(f"❌ {assertion.get('description')}: {assertion.get('message')}")

    # 下载数据按结果签名缓存：只有结果变化时才重建 JSON/CSV/Markdown，
    # 避免每次 rerun 都急切构造全量导出件（callable / lazy 语义）。
    result_signature = auto_reg.compute_signature({"results": test_results, "mode": actual_mode})
    cache = st.session_state.get("api_auto_download_items_cache")
    if cache and cache.get("signature") == result_signature:
        download_items = cache["items"]
    else:
        config_snapshot = st.session_state.get("interface_generated_config_snapshot", {})
        input_signature = st.session_state.get("interface_generated_config_signature", "")
        warnings = list(test_results.get("warnings") or []) + list(
            st.session_state.get("interface_generated_warnings") or []
        )
        truncation = test_results.get("truncation") or st.session_state.get("interface_generated_truncation") or {}
        markdown_text = _build_result_markdown(test_results, execution_mode)
        markdown_text += (
            "\n\n## 导出快照\n\n"
            f"- 输入签名: `{input_signature}`\n"
            f"- 配置快照: `{auto_reg.strict_json_dumps(config_snapshot, sort_keys=True)}`\n"
            f"- 告警数: {len(warnings)}\n"
        )
        # 导出项由注册中心统一生成：新增一种导出格式只需 register_export_format，
        # 下载区会自动出现，不再硬编码 JSON/CSV/Markdown 三项（#421/R3-07）。
        json_payload = _build_download_payload(
            test_results,
            config_snapshot=config_snapshot,
            input_signature=input_signature,
            warnings=warnings,
            truncation=truncation,
        )
        export_ctx = {
            "test_results": test_results,
            "payload": json_payload,
            "summary_rows": summary_rows,
            "markdown_text": markdown_text,
            "config_snapshot": config_snapshot,
            "input_signature": input_signature,
            "warnings": warnings,
            "truncation": truncation,
        }
        _emoji = {"json": "🧾", "csv": "📥", "markdown": "📝", "html": "📄"}
        for item in auto_reg.get_export_items(export_ctx):
            key = item["file_name"].rsplit(".", 1)[-1] if "." in item["file_name"] else ""
            label = f"{_emoji.get(key, '📥')} 下载 {item['label']}"
            # 保持既有文件名带执行模式后缀，方便历史脚本比对。
            item["label"] = label
            item["file_name"] = item["file_name"].replace(
                ".", f"_{actual_mode}.", 1
            )
            download_items.append(item)
        st.session_state.api_auto_download_items_cache = {
            "signature": result_signature,
            "items": download_items,
        }

    render_download_panel(
        title="统一导出区",
        description="自动化结果统一保留 HTML、Markdown、JSON、CSV，便于和性能、安全模块保持一致。",
        items=download_items,
        key_prefix=f"api_auto_results_{actual_mode}",
        metrics=[
            {"label": "通过率", "value": f"{success_rate:.1f}%"},
            {"label": "失败/错误", "value": f"{failed + errors}"},
            {"label": "详情记录", "value": f"{len(test_details)}"},
        ],
        empty_message="当前还没有可下载的结果，请先执行测试。",
    )

    if test_results.get("success", False):
        st.success("✅ 所有测试用例执行成功")
    elif total > 0:
        st.error(f"❌ 存在 {failed + errors} 个失败或错误")


def _build_template_download_items(auto_test_tool: InterfaceAutoTestCore) -> List[Dict[str, Any]]:
    """导入模板清单由注册式扩展点驱动，新增模板只需 register_import_template。"""
    items: List[Dict[str, Any]] = []
    for spec in auto_reg.get_import_templates().values():
        builder = getattr(auto_test_tool, spec.builder_key, None)
        if builder is None:
            continue
        try:
            data = builder()
        except Exception as exc:
            st.caption(f"模板 {spec.label} 暂不可用: {type(exc).__name__}: {exc}")
            continue
        items.append({
            "label": spec.label,
            "data": data,
            "file_name": spec.file_name,
            "mime": spec.mime,
            "caption": spec.caption,
        })
    return items


def _render_generated_files(generated_files: Dict[str, str]) -> None:
    st.markdown("### 📄 最近一次生成结果")
    for filename, content in generated_files.items():
        language = "json" if filename.endswith(".json") else "python"
        with st.expander(f"查看 {filename}", expanded=filename.endswith(".py")):
            st.code(content, language=language)

    download_items = []
    for filename, content in generated_files.items():
        if filename.endswith(".json"):
            mime = "application/json"
        else:
            mime = "text/plain"
        download_items.append(
            {
                "label": f"📥 下载 {filename}",
                "data": content,
                "file_name": f"api_automation_{filename}",
                "mime": mime,
            }
        )

    render_download_panel(
        title="生成产物导出",
        description="统一下载最近一次生成的脚本、清单和配置产物。",
        items=download_items,
        key_prefix="api_auto_generated_files",
        metrics=[{"label": "文件数", "value": f"{len(generated_files)}"}],
        empty_message="当前没有可下载的生成产物。",
    )


def _load_uploaded_document(uploaded_file) -> None:
    """安全导入：大小上限 + 后缀白名单 + uuid 文件名 + finally 删除临时文件。"""
    limits = auto_reg.get_automation_limits()
    file_bytes = uploaded_file.getbuffer()
    if len(file_bytes) > limits.max_upload_bytes:
        raise ValueError(
            f"上传文件 {len(file_bytes)} bytes 超过上限 {limits.max_upload_bytes} bytes，请先精简文档"
        )
    upload_signature = f"{uploaded_file.name}:{hashlib.sha256(file_bytes).hexdigest()}"
    if st.session_state.get("interface_upload_signature") == upload_signature:
        return

    original_name = os.path.basename(str(uploaded_file.name or "upload.json"))
    safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-") or "upload.json"
    suffix = os.path.splitext(safe_name)[1].lower().lstrip(".")
    if suffix and suffix not in INTERFACE_FILE_TYPES:
        raise ValueError(f"不支持的文件后缀: .{suffix}（仅允许 {', '.join(INTERFACE_FILE_TYPES)}）")
    file_path = os.path.join(
        st.session_state.auto_test_tool.upload_dir,
        f"upload_{uuid.uuid4().hex[:12]}_{safe_name}",
    )
    try:
        with open(file_path, "wb") as file:
            file.write(file_bytes)
        with st.spinner("正在解析接口文档..."):
            interfaces = st.session_state.auto_test_tool.parse_document(file_path)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

    detected_base_url = st.session_state.auto_test_tool.last_parse_meta.get("detected_base_url", "")
    _set_interface_state(interfaces, detected_base_url, uploaded_file.name)
    st.session_state.interface_upload_signature = upload_signature
    st.success(f"✅ 成功解析出 {len(interfaces)} 个接口")
    if detected_base_url:
        st.info(f"已从文档中识别基础地址: `{detected_base_url}`")


def render_api_automation_test_page() -> None:
    show_doc("interface_auto_test")
    run_center = get_session_task_runner("api_automation")

    if "auto_test_tool" not in st.session_state:
        st.session_state.auto_test_tool = InterfaceAutoTestCore()
    if "enhanced_runner" not in st.session_state:
        st.session_state.enhanced_runner = EnhancedTestRunner()
    if "enhanced_report" not in st.session_state:
        st.session_state.enhanced_report = EnhancedReportGenerator()
    if "interface_loaded_interfaces" not in st.session_state:
        st.session_state.interface_loaded_interfaces = []
    if "interface_loaded_base_url" not in st.session_state:
        st.session_state.interface_loaded_base_url = ""
    if "interface_source_name" not in st.session_state:
        st.session_state.interface_source_name = ""

    auto_test_tool = st.session_state.auto_test_tool

    st.markdown('<div class="category-card">🤖 接口自动化测试工具</div>', unsafe_allow_html=True)
    _render_registry_summary()
    render_workflow_guide(
        title="三步完成接口自动化回归",
        description="先导入接口定义，再配置环境与鉴权，最后生成脚本并执行。页面会统一保留生成产物和执行结果，方便回看与导出。",
        steps=[
            "导入接口文档，可选文件上传、Swagger/OpenAPI URL 或原始文本。",
            "确认基础 URL、环境配置、鉴权方式和模板风格。",
            "生成测试脚本，必要时直接执行并导出 HTML/Markdown/JSON/CSV 结果。",
        ],
        tips=["先用模板校准格式", "先冒烟再严格断言", "多环境回归优先用 JSON 环境模板"],
    )

    execution_mode = st.radio(
        "选择执行模式",
        auto_reg.get_execution_mode_labels(),
        horizontal=True,
        key="interface_execution_mode",
    )

    # 安全默认值与 SSRF 护栏放在首屏，导入与执行共用同一套策略。
    st.checkbox(
        "允许内网/本地目标（导入 Swagger 与执行测试共用同一 SSRF 护栏，默认关闭）",
        key="api_auto_allow_private_targets",
        value=False,
        help="默认仅允许公网 http/https 地址。联调本机或内网服务时再开启；开启后仍会校验协议、userinfo、端口与重定向目标。",
    )
    st.checkbox(
        "在生成产物中保留鉴权凭据（默认脱敏，仅限本地调试）",
        key="api_auto_include_credentials",
        value=False,
        help="默认把 token/密码从 manifest、生成脚本、页面展示与下载件里移除，执行时改从环境变量读取。",
    )
    allow_private_targets = bool(st.session_state.get("api_auto_allow_private_targets", False))
    include_credentials = bool(st.session_state.get("api_auto_include_credentials", False))
    auto_test_tool.set_allow_private_targets(allow_private_targets)

    if not _check_interface_dependencies(execution_mode, for_execution=False):
        st.stop()

    st.markdown("### Step 1. 载入示例或模板")
    quick_col1, quick_col2, quick_col3 = st.columns(3)
    with quick_col1:
        if st.button("📝 JSONPlaceholder", use_container_width=True, key="load_jsonplaceholder"):
            base_url, interfaces = _create_jsonplaceholder_test_data()
            _set_interface_state(interfaces, base_url, "内置 JSONPlaceholder 示例")
            st.success("✅ 已加载 JSONPlaceholder 示例")
    with quick_col2:
        if st.button("👥 ReqRes", use_container_width=True, key="load_reqres"):
            base_url, interfaces = _create_reqres_test_data()
            _set_interface_state(interfaces, base_url, "内置 ReqRes 示例")
            st.success("✅ 已加载 ReqRes 示例")
    with quick_col3:
        if st.button("🔄 清空导入数据", use_container_width=True, key="clear_interface_inputs"):
            _clear_interface_state()
            st.success("✅ 已清空接口数据和生成产物缓存")

    with st.expander("📚 模板与导入说明", expanded=not st.session_state.interface_loaded_interfaces):
        template_items = st.session_state.get("api_auto_template_items_cache")
        if template_items is None:
            template_items = _build_template_download_items(auto_test_tool)
            st.session_state.api_auto_template_items_cache = template_items
        render_download_panel(
            title="导入模板下载",
            description="模板统一收口到这里，避免文件入口分散。优先使用 Excel、JSON 或 OpenAPI 模板，对齐字段后再导入最稳。",
            items=template_items,
            key_prefix="api_auto_templates",
            metrics=[{"label": "模板数", "value": f"{len(template_items)}"}],
        )
        st.markdown(
            """
            **支持的导入方式**

            - 文件上传: `xlsx/xls/json/har/bru/txt/md/yaml/yml`
            - Swagger/OpenAPI URL: 直接输入 JSON 或 YAML 地址
            - 原始文本: 支持结构化文本、JSON 文本、Swagger 文本、`curl` 命令、`Bruno .bru`
            - JSON 导入兼容 `OpenAPI / Apifox / Postman Collection / HAR / Insomnia / 自定义接口列表`

            **执行模板建议**

            - `pytest`: 适合接入现有自动化仓库或 CI
            - `unittest`: 适合偏传统 Python 项目
            - `requests脚本`: 适合临时联调、快速回放和脚本化验收

            **模板风格建议**

            - `冒烟模板`: 只校验状态码，先跑通
            - `标准模板`: 校验状态码和关键响应字段
            - `严格模板`: 按期望响应做更严格的字段和值校验
            """
        )

    st.markdown("### Step 1. 导入接口文档")
    import_mode = st.radio(
        "导入方式",
        ["文件上传", "Swagger/OpenAPI URL", "原始文本"],
        horizontal=True,
        key="interface_import_mode",
    )

    if import_mode == "文件上传":
        uploaded_file = st.file_uploader(
            "选择接口文档文件",
            type=INTERFACE_FILE_TYPES,
            help="支持 Excel、JSON、Swagger/OpenAPI、Apifox、Postman、HAR、Bruno、Insomnia、文本等格式",
            key="interface_doc_upload_v2",
        )
        if uploaded_file is not None:
            try:
                _load_uploaded_document(uploaded_file)
            except Exception as exc:
                st.error(f"❌ 处理文件时出错: {exc}")

    elif import_mode == "Swagger/OpenAPI URL":
        swagger_url = st.text_input(
            "Swagger / OpenAPI 地址",
            placeholder="例如: https://example.com/openapi.json",
            key="swagger_spec_url",
        )
        if st.button("🔍 解析 Swagger / OpenAPI", use_container_width=True, key="parse_swagger_url"):
            if not swagger_url.strip():
                st.error("❌ 请输入 Swagger/OpenAPI 地址")
            else:
                try:
                    with st.spinner("正在拉取并解析远程文档..."):
                        interfaces = auto_test_tool.parse_content(
                            swagger_url,
                            source_type="swagger",
                            source_name="remote-swagger",
                        )
                    detected_base_url = auto_test_tool.last_parse_meta.get("detected_base_url", "")
                    _set_interface_state(interfaces, detected_base_url, swagger_url)
                    st.success(f"✅ 成功解析出 {len(interfaces)} 个接口")
                    if detected_base_url:
                        st.info(f"已从文档中识别基础地址: `{detected_base_url}`")
                except Exception as exc:
                    st.error(f"❌ 解析 Swagger/OpenAPI 失败: {exc}")

    else:
        raw_format = st.selectbox(
            "文本格式",
            list(IMPORT_FORMAT_MAP.keys()),
            key="raw_interface_format",
        )
        raw_content = st.text_area(
            "粘贴接口定义",
            height=260,
            placeholder="可粘贴 JSON、OpenAPI 文本、结构化文本，或 curl 命令",
            key="raw_interface_content",
        )
        if st.button("🧩 解析文本内容", use_container_width=True, key="parse_raw_interface_content"):
            if not raw_content.strip():
                st.error("❌ 请输入要解析的文本内容")
            else:
                try:
                    with st.spinner("正在解析文本内容..."):
                        interfaces = auto_test_tool.parse_content(
                            raw_content,
                            source_type=IMPORT_FORMAT_MAP[raw_format],
                            source_name="inline-text",
                        )
                    detected_base_url = auto_test_tool.last_parse_meta.get("detected_base_url", "")
                    _set_interface_state(interfaces, detected_base_url, f"{raw_format} 文本")
                    st.success(f"✅ 成功解析出 {len(interfaces)} 个接口")
                    if detected_base_url:
                        st.info(f"已从内容中识别基础地址: `{detected_base_url}`")
                except Exception as exc:
                    st.error(f"❌ 解析文本失败: {exc}")

    interfaces = st.session_state.interface_loaded_interfaces
    if not interfaces:
        st.info("📝 请先导入接口文档，支持 Excel、Swagger/OpenAPI、JSON、文本和 curl")
        return

    source_name = st.session_state.interface_source_name or "当前导入结果"
    summary_col1, summary_col2, summary_col3 = st.columns(3)
    with summary_col1:
        st.metric("当前接口数", len(interfaces))
    with summary_col2:
        st.metric("来源", source_name)
    with summary_col3:
        st.metric("执行模式", execution_mode)

    _render_interface_preview(interfaces)
    env_profile_manager = get_session_env_profile_manager()
    render_env_profile_panel(
        manager=env_profile_manager,
        namespace="api_automation",
        panel_key="api_automation_env_profile_panel",
        capture_state=_capture_interface_env_profile,
        apply_profile=_apply_interface_env_profile,
        description="保存并复用基础 URL、超时、重试、SSL 和统一鉴权参数。",
        suggested_name="api-auto-dev",
    )

    st.markdown("### Step 3. 测试配置")
    limits = auto_reg.get_automation_limits()
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        base_url = st.text_input(
            "基础 URL 或默认 URL",
            value=st.session_state.interface_loaded_base_url,
            placeholder="例如: https://api.example.com",
            key="interface_base_url_input_v2",
        )
        timeout = st.number_input(
            "请求超时时间(秒)",
            min_value=limits.min_timeout_seconds,
            max_value=limits.max_timeout_seconds,
            value=limits.default_timeout_seconds,
            key="interface_timeout_v2",
        )
        request_format = st.selectbox(
            "请求格式",
            auto_reg.get_request_format_labels(),
            index=0,
            key="interface_request_format_v2",
        )
    with config_col2:
        retry_times = st.number_input(
            "重试次数",
            min_value=0,
            max_value=limits.max_retry_times,
            value=0,
            key="interface_retry_times_v2",
        )
        verify_ssl = st.checkbox("验证 SSL 证书", value=limits.default_verify_ssl, key="interface_verify_ssl_v2")
        style_labels = auto_reg.get_template_style_labels()
        template_style = st.selectbox(
            "模板风格",
            style_labels,
            index=min(1, len(style_labels) - 1),
            key="interface_template_style_v2",
        )

    st.markdown("### Step 3. 环境与鉴权")
    render_workflow_guide(
        title="环境和鉴权建议",
        description="单环境适合快速联调，多环境 JSON 模板适合回归。统一鉴权只会在生成与执行时附加，不会改动原始接口定义。",
        steps=[
            "单环境直接填写基础 URL，适合本地或预发验证。",
            "多环境模式维护 dev/staging/prod，执行时按 active_env 生效。",
            "统一鉴权适合 Bearer、API Key、Basic Auth 或自定义 Header。",
        ],
        tips=["环境配置错误会阻断生成", "接口自带 headers 仍会保留", "先跑匿名/弱鉴权接口再补鉴权回归"],
        eyebrow="配置建议",
    )

    env_auth_col1, env_auth_col2 = st.columns(2)
    environment_config: Optional[Dict[str, Any]] = None
    auth_config: Dict[str, Any] = {"enabled": False, "type": "none"}

    with env_auth_col1:
        env_mode = st.radio(
            "环境模式",
            ["单环境", "多环境(JSON模板)"],
            horizontal=True,
            key="interface_env_mode",
        )
        if env_mode == "多环境(JSON模板)":
            env_default_text = _build_env_template_with_base_url(base_url or st.session_state.interface_loaded_base_url)
            env_config_text = st.text_area(
                "环境配置 JSON",
                value=st.session_state.get("interface_env_config_text", env_default_text),
                height=220,
                key="interface_env_config_text",
                help="定义 dev/staging/prod 的 base_url 和公共 headers，运行时按所选环境生效",
            )
            try:
                environment_config = json.loads(env_config_text)
                if not isinstance(environment_config, dict):
                    st.error("❌ 环境配置必须是 JSON 对象")
                    environment_config = None
                    raise ValueError("环境配置不是 JSON 对象")
                env_names = list((environment_config.get("environments") or {}).keys())
                if env_names:
                    default_env = environment_config.get("active_env")
                    default_index = env_names.index(default_env) if default_env in env_names else 0
                    selected_env = st.selectbox("当前环境", env_names, index=default_index, key="interface_active_env")
                    environment_config["active_env"] = selected_env
                else:
                    st.error("❌ 环境配置缺少 environments 节点")
                    environment_config = None
            except (json.JSONDecodeError, ValueError) as exc:
                if "不是 JSON 对象" not in str(exc):
                    st.error(f"❌ 环境配置 JSON 格式错误: {exc}")
                environment_config = None
        else:
            st.info("当前使用单环境模式，执行时直接使用上面的基础 URL。")

    with env_auth_col2:
        auth_mode = st.selectbox(
            "鉴权方式",
            ["无"] + auto_reg.get_auth_labels(),
            key="interface_auth_mode",
        )
        if auth_mode == "Bearer Token":
            token = st.text_input("Bearer Token", type="password", key="interface_bearer_token")
            auth_config = {
                "enabled": bool(token),
                "type": "bearer",
                "header_name": "Authorization",
                "prefix": "Bearer ",
                "token": token,
            }
        elif auth_mode == "API Key":
            api_key_name = st.text_input("Header名称", value="X-API-Key", key="interface_api_key_name")
            api_key_value = st.text_input("API Key", type="password", key="interface_api_key_value")
            auth_config = {
                "enabled": bool(api_key_value),
                "type": "api_key",
                "api_key_name": api_key_name,
                "api_key_value": api_key_value,
            }
        elif auth_mode == "Basic Auth":
            username = st.text_input("用户名", key="interface_basic_username")
            password = st.text_input("密码", type="password", key="interface_basic_password")
            auth_config = {
                "enabled": bool(username),
                "type": "basic",
                "username": username,
                "password": password,
            }
        elif auth_mode == "自定义Header":
            custom_header_name = st.text_input("Header名称", value="X-Custom-Auth", key="interface_custom_header_name")
            custom_header_value = st.text_input("Header值", type="password", key="interface_custom_header_value")
            auth_config = {
                "enabled": bool(custom_header_value),
                "type": "custom_header",
                "custom_header_name": custom_header_name,
                "custom_header_value": custom_header_value,
            }
        else:
            st.info("不附加统一鉴权头，接口自身 headers 保持不变。")

    st.markdown("### Step 3. 生成与执行")
    # 接口清单 + 全部执行配置一起签名：改任何一项，旧产物与旧结果都标记过期。
    current_sig = _current_config_signature(
        interfaces, execution_mode, base_url, timeout, retry_times, verify_ssl,
        request_format, template_style, environment_config, auth_config,
        allow_private_targets, include_credentials,
    )
    generated_config_sig = st.session_state.get("interface_generated_config_signature")
    artifacts_stale = bool(generated_config_sig and generated_config_sig != current_sig)
    if artifacts_stale:
        st.warning("⚠️ 配置已变更，当前生成产物与执行结果已过期，请重新生成测试用例后再执行。")
    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        if st.button("🧪 生成测试用例", use_container_width=True, key="generate_tests_v2"):
            try:
                if env_mode == "多环境(JSON模板)" and environment_config is None:
                    raise RuntimeError("多环境配置无效，请先修正环境配置 JSON")

                def _generate_task(logger):
                    logger(f"开始生成测试文件，接口数量={len(interfaces)}。")
                    generated = _generate_artifacts(
                        interfaces,
                        execution_mode,
                        base_url,
                        timeout,
                        retry_times,
                        verify_ssl,
                        request_format,
                        template_style,
                        environment_config,
                        auth_config,
                        config_signature=current_sig,
                        allow_private_targets=allow_private_targets,
                        include_credentials=include_credentials,
                    )
                    logger(f"测试文件生成完成，文件数量={len(generated)}。")
                    return {"file_count": len(generated)}

                run_info = run_center.submit(
                    tool="接口自动化测试",
                    action="生成测试用例",
                    payload={
                        "execution_mode": execution_mode,
                        "interface_count": len(interfaces),
                        "template_style": template_style,
                    },
                    executor=_generate_task,
                )
                st.success(f"✅ 测试文件已生成（Run ID: `{run_info['run_id']}`）")
            except Exception as exc:
                st.error(f"❌ 生成测试用例失败: {exc}")

    with action_col2:
        if st.button("▶️ 执行测试", use_container_width=True, key="run_tests_v2"):
            if not _ensure_generated_file(execution_mode, current_sig):
                st.error("❌ 当前接口清单与已生成的测试文件不一致，请先重新生成测试用例")
            elif _check_interface_dependencies(execution_mode, for_execution=True):
                try:
                    def _run_task(logger):
                        logger(f"开始执行测试，模式={execution_mode}。")
                        with st.spinner("正在执行测试并收集结果..."):
                            test_results = st.session_state.enhanced_runner.run_tests_with_details(execution_mode, interfaces)
                        st.session_state.interface_last_test_results = test_results
                        logger(
                            "执行完成，"
                            f"total={test_results.get('total', 0)}, "
                            f"passed={test_results.get('passed', 0)}, "
                            f"failed={test_results.get('failed', 0)}。"
                        )
                        return {
                            "total": test_results.get("total", 0),
                            "passed": test_results.get("passed", 0),
                            "failed": test_results.get("failed", 0),
                            "errors": test_results.get("errors", 0),
                        }

                    run_info = run_center.submit(
                        tool="接口自动化测试",
                        action="执行测试",
                        payload={
                            "execution_mode": execution_mode,
                            "interface_count": len(interfaces),
                        },
                        executor=_run_task,
                    )
                    st.success(f"✅ 测试执行完成（Run ID: `{run_info['run_id']}`）")
                except Exception as exc:
                    st.error(f"❌ 执行测试失败: {exc}")

    with action_col3:
        if st.button("⚡ 生成并执行", use_container_width=True, key="generate_and_run_tests_v2"):
            try:
                if env_mode == "多环境(JSON模板)" and environment_config is None:
                    raise RuntimeError("多环境配置无效，请先修正环境配置 JSON")

                def _generate_and_run_task(logger):
                    logger("开始生成测试文件。")
                    _generate_artifacts(
                        interfaces,
                        execution_mode,
                        base_url,
                        timeout,
                        retry_times,
                        verify_ssl,
                        request_format,
                        template_style,
                        environment_config,
                        auth_config,
                        config_signature=current_sig,
                        allow_private_targets=allow_private_targets,
                        include_credentials=include_credentials,
                    )
                    logger("测试文件生成完成，准备执行。")
                    if not _check_interface_dependencies(execution_mode, for_execution=True):
                        raise RuntimeError("当前执行模式缺少运行依赖，请先安装后再执行")
                    with st.spinner("正在执行测试并收集结果..."):
                        test_results = st.session_state.enhanced_runner.run_tests_with_details(execution_mode, interfaces)
                    st.session_state.interface_last_test_results = test_results
                    logger(
                        "生成并执行完成，"
                        f"total={test_results.get('total', 0)}, "
                        f"passed={test_results.get('passed', 0)}, "
                        f"failed={test_results.get('failed', 0)}。"
                    )
                    return {
                        "total": test_results.get("total", 0),
                        "passed": test_results.get("passed", 0),
                        "failed": test_results.get("failed", 0),
                        "errors": test_results.get("errors", 0),
                    }

                run_info = run_center.submit(
                    tool="接口自动化测试",
                    action="生成并执行",
                    payload={
                        "execution_mode": execution_mode,
                        "interface_count": len(interfaces),
                        "template_style": template_style,
                    },
                    executor=_generate_and_run_task,
                )
                st.success(f"✅ 生成并执行完成（Run ID: `{run_info['run_id']}`）")
            except Exception as exc:
                st.error(f"❌ 生成并执行失败: {exc}")

    generated_files = st.session_state.get("interface_last_generated_files", {})
    if generated_files:
        _render_generated_files(generated_files)
        # 生成阶段就展示告警（目标地址护栏、凭据脱敏、上限钳制等），
        # 不必等到执行出结果才看得见。
        _render_warnings_panel(
            st.session_state.get("interface_generated_warnings") or [],
            st.session_state.get("interface_generated_truncation"),
        )

    cached_results = st.session_state.get("interface_last_test_results")
    if cached_results:
        result_sig = st.session_state.get("interface_result_config_signature")
        if result_sig and result_sig != current_sig:
            st.warning("⚠️ 当前展示的是上一次配置的执行结果（已过期），请重新生成并执行后再看结论。")
        _render_test_results(cached_results, execution_mode, interfaces)

    st.markdown("---")
    clean_col = st.columns([1, 2, 1])[1]
    with clean_col:
        # 只删除本工具已知的产物文件，绝不 rmtree 整个共享 test_dir。
        known_generated_files = auto_reg.get_known_generated_files()
        existing = [
            name for name in known_generated_files
            if os.path.exists(os.path.join(auto_test_tool.test_dir, name))
        ]
        st.caption(f"待清理产物：{', '.join(existing) or '无'}")
        confirm_clean = st.checkbox(
            f"确认删除上述 {len(existing)} 个产物文件（不会删除目录里的其它文件）",
            key="api_auto_clean_confirm",
            value=False,
        )
        if st.button("🗑️ 清理生成文件", use_container_width=True, key="clean_generated_interface_files"):
            if not confirm_clean:
                st.warning("请先勾选确认，再执行清理")
            else:
                removed = []
                for name in existing:
                    path = os.path.join(auto_test_tool.test_dir, name)
                    try:
                        os.remove(path)
                        removed.append(name)
                    except OSError as exc:
                        st.error(f"删除 {name} 失败: {exc}")
                for key in [
                    "interface_last_generated_files",
                    "interface_last_test_results",
                    "interface_generated_signature",
                    "interface_generated_config_signature",
                    "api_auto_download_items_cache",
                    "api_auto_report_cache",
                ]:
                    st.session_state.pop(key, None)
                st.success(f"✅ 已清理 {len(removed)} 个产物：{', '.join(removed) or '无'}")

    render_task_run_panel(
        run_center=run_center,
        tool_name="接口自动化测试",
        panel_key="api_automation_run_panel",
        limit=10,
    )
