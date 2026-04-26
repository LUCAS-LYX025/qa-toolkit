import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Sequence, Tuple

import pandas as pd
import streamlit as st

from qa_toolkit.core.env_profile_manager import get_session_env_profile_manager
from qa_toolkit.core.task_runner import get_session_task_runner
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore
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
MIRROR_URLS = {
    "清华镜像": "https://pypi.tuna.tsinghua.edu.cn/simple/",
    "阿里云镜像": "https://mirrors.aliyun.com/pypi/simple/",
    "豆瓣镜像": "https://pypi.douban.com/simple/",
    "中科大镜像": "https://pypi.mirrors.ustc.edu.cn/simple/",
}
AUTOMATION_AUTH_LABEL_TO_MODE = {
    "无": "none",
    "Bearer Token": "bearer",
    "API Key": "api_key",
    "Basic Auth": "basic",
    "自定义Header": "custom_header",
}
AUTOMATION_AUTH_MODE_TO_LABEL = {
    "none": "无",
    "bearer": "Bearer Token",
    "api_key": "API Key",
    "basic": "Basic Auth",
    "custom_header": "自定义Header",
}


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
        mirror = st.selectbox(
            "选择镜像源",
            list(MIRROR_URLS.keys()),
            key=f"interface_mirror_{selected_mode}_{'exec' if for_execution else 'page'}",
        )
        if st.button(
            "🚀 自动安装依赖",
            use_container_width=True,
            key=f"install_interface_deps_{selected_mode}_{'exec' if for_execution else 'page'}",
        ):
            with st.spinner("正在安装依赖..."):
                success = _install_missing_packages(missing_packages, MIRROR_URLS[mirror])
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


def _set_interface_state(interfaces: List[Dict[str, Any]], base_url: str = "", source_name: str = "") -> None:
    st.session_state.interface_loaded_interfaces = interfaces
    st.session_state.interface_loaded_base_url = base_url or ""
    st.session_state.interface_source_name = source_name or ""
    st.session_state.pop("interface_last_generated_files", None)
    st.session_state.pop("interface_last_test_results", None)


def _clear_interface_state() -> None:
    for key in [
        "interface_loaded_interfaces",
        "interface_loaded_base_url",
        "interface_source_name",
        "interface_last_generated_files",
        "interface_last_test_results",
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
    auth_mode = AUTOMATION_AUTH_LABEL_TO_MODE.get(auth_mode_label, "none")
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
    st.session_state.interface_auth_mode = AUTOMATION_AUTH_MODE_TO_LABEL.get(auth_mode, "无")

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
) -> Dict[str, str]:
    with st.spinner("正在生成测试用例..."):
        test_files = st.session_state.auto_test_tool.generate_test_cases(
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
        )
        st.session_state.auto_test_tool.save_test_files(test_files)
        st.session_state.interface_last_generated_files = test_files
    return test_files


def _ensure_generated_file(execution_mode: str) -> bool:
    target_file = "run_interfaces.py" if execution_mode == "requests脚本" else "test_interfaces.py"
    manifest_file = os.path.join(st.session_state.auto_test_tool.test_dir, "interface_manifest.json")
    target_path = os.path.join(st.session_state.auto_test_tool.test_dir, target_file)
    if not (os.path.exists(manifest_file) and os.path.exists(target_path)):
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


def _render_test_results(test_results: Dict[str, Any], execution_mode: str, interfaces: List[Dict[str, Any]]) -> None:
    st.markdown("### Step 4. 查看执行结果")
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
        report_path = st.session_state.enhanced_report.generate_detailed_report(
            test_results=test_results,
            framework=execution_mode,
            interfaces=interfaces,
            test_details=test_results.get("test_details", []),
        )
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

    download_items.extend(
        [
            {
                "label": "🧾 下载 JSON 结果",
                "data": json.dumps(test_results, ensure_ascii=False, indent=2),
                "file_name": f"api_automation_result_{actual_mode}.json",
                "mime": "application/json",
                "caption": "适合后续二次分析或排查执行细节。",
            },
            {
                "label": "📥 下载 CSV 摘要",
                "data": pd.DataFrame(summary_rows).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                if summary_rows
                else None,
                "file_name": f"api_automation_summary_{actual_mode}.csv",
                "mime": "text/csv",
                "caption": "适合给测试日报或结果汇总直接引用。",
            },
            {
                "label": "📝 下载 Markdown 摘要",
                "data": _build_result_markdown(test_results, execution_mode),
                "file_name": f"api_automation_summary_{actual_mode}.md",
                "mime": "text/markdown",
                "caption": "适合发评审记录或同步到文档系统。",
            },
        ]
    )

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
    return [
        {
            "label": "📥 Excel 模板",
            "data": auto_test_tool.build_excel_template_bytes(),
            "file_name": "api_automation_template.xlsx",
            "mime": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "caption": "适合表格方式维护接口清单。",
        },
        {
            "label": "📥 JSON 模板",
            "data": auto_test_tool.build_json_template(),
            "file_name": "api_automation_template.json",
            "mime": "application/json",
            "caption": "适合结构化接口列表导入。",
        },
        {
            "label": "📥 文本模板",
            "data": auto_test_tool.build_text_template(),
            "file_name": "api_automation_template.txt",
            "mime": "text/plain",
            "caption": "适合快速手工拼装接口块。",
        },
        {
            "label": "📥 curl 模板",
            "data": auto_test_tool.build_curl_template(),
            "file_name": "api_automation_curl_template.txt",
            "mime": "text/plain",
            "caption": "适合终端命令或抓包回放。",
        },
        {
            "label": "📥 OpenAPI JSON",
            "data": auto_test_tool.build_openapi_template(),
            "file_name": "api_automation_openapi.json",
            "mime": "application/json",
            "caption": "适合 Swagger/OpenAPI 文档导入。",
        },
        {
            "label": "📥 OpenAPI YAML",
            "data": auto_test_tool.build_openapi_yaml_template(),
            "file_name": "api_automation_openapi.yaml",
            "mime": "text/yaml",
            "caption": "适合 YAML 版 OpenAPI 文档。",
        },
        {
            "label": "📥 Postman 模板",
            "data": auto_test_tool.build_postman_template(),
            "file_name": "api_automation_postman.json",
            "mime": "application/json",
            "caption": "适合集合导出后直接导入。",
        },
        {
            "label": "📥 HAR 模板",
            "data": auto_test_tool.build_har_template(),
            "file_name": "api_automation_sample.har",
            "mime": "application/json",
            "caption": "适合浏览器抓包回放。",
        },
        {
            "label": "📥 Apifox 模板",
            "data": auto_test_tool.build_apifox_template(),
            "file_name": "api_automation_apifox.json",
            "mime": "application/json",
            "caption": "提供 Apifox 兼容骨架。",
        },
        {
            "label": "📥 Bruno 模板",
            "data": auto_test_tool.build_bruno_template(),
            "file_name": "api_automation_sample.bru",
            "mime": "text/plain",
            "caption": "适合 Bruno 单接口文件导入。",
        },
        {
            "label": "📥 Insomnia 模板",
            "data": auto_test_tool.build_insomnia_template(),
            "file_name": "api_automation_insomnia.json",
            "mime": "application/json",
            "caption": "适合 Insomnia 导出 JSON 回放。",
        },
        {
            "label": "📥 环境配置模板",
            "data": auto_test_tool.build_environment_template(),
            "file_name": "api_automation_environment.json",
            "mime": "application/json",
            "caption": "维护 dev/staging/prod 基础地址和公共头。",
        },
        {
            "label": "📥 鉴权模板",
            "data": auto_test_tool.build_auth_template(),
            "file_name": "api_automation_auth.json",
            "mime": "application/json",
            "caption": "统一配置 Bearer / API Key / Basic / 自定义 Header。",
        },
    ]


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
    upload_signature = f"{uploaded_file.name}:{uploaded_file.size}"
    if st.session_state.get("interface_upload_signature") == upload_signature:
        return

    file_path = os.path.join(st.session_state.auto_test_tool.upload_dir, uploaded_file.name)
    with open(file_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    with st.spinner("正在解析接口文档..."):
        interfaces = st.session_state.auto_test_tool.parse_document(file_path)

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
        ["pytest", "unittest", "requests脚本"],
        horizontal=True,
        key="interface_execution_mode",
    )

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
        render_download_panel(
            title="导入模板下载",
            description="模板统一收口到这里，避免文件入口分散。优先使用 Excel、JSON 或 OpenAPI 模板，对齐字段后再导入最稳。",
            items=_build_template_download_items(auto_test_tool),
            key_prefix="api_auto_templates",
            metrics=[{"label": "模板数", "value": "13"}],
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
    config_col1, config_col2 = st.columns(2)
    with config_col1:
        base_url = st.text_input(
            "基础 URL 或默认 URL",
            value=st.session_state.interface_loaded_base_url,
            placeholder="例如: http://10.0.3.54:3000",
            key="interface_base_url_input_v2",
        )
        timeout = st.number_input("请求超时时间(秒)", min_value=1, value=30, key="interface_timeout_v2")
        request_format = st.selectbox(
            "请求格式",
            ["自动检测", "json=参数", "data=json.dumps()", "form-urlencoded"],
            index=0,
            key="interface_request_format_v2",
        )
    with config_col2:
        retry_times = st.number_input("重试次数", min_value=0, value=0, key="interface_retry_times_v2")
        verify_ssl = st.checkbox("验证 SSL 证书", value=False, key="interface_verify_ssl_v2")
        template_style = st.selectbox(
            "模板风格",
            ["冒烟模板", "标准模板", "严格模板"],
            index=1,
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
                env_names = list((environment_config.get("environments") or {}).keys())
                if env_names:
                    default_env = environment_config.get("active_env")
                    default_index = env_names.index(default_env) if default_env in env_names else 0
                    selected_env = st.selectbox("当前环境", env_names, index=default_index, key="interface_active_env")
                    environment_config["active_env"] = selected_env
                else:
                    st.error("❌ 环境配置缺少 environments 节点")
                    environment_config = None
            except json.JSONDecodeError as exc:
                st.error(f"❌ 环境配置 JSON 格式错误: {exc}")
                environment_config = None
        else:
            st.info("当前使用单环境模式，执行时直接使用上面的基础 URL。")

    with env_auth_col2:
        auth_mode = st.selectbox(
            "鉴权方式",
            ["无", "Bearer Token", "API Key", "Basic Auth", "自定义Header"],
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
            if not _ensure_generated_file(execution_mode):
                st.error("❌ 请先生成当前执行模式对应的测试文件")
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

    cached_results = st.session_state.get("interface_last_test_results")
    if cached_results:
        _render_test_results(cached_results, execution_mode, interfaces)

    st.markdown("---")
    clean_col = st.columns([1, 2, 1])[1]
    with clean_col:
        if st.button("🗑️ 清理生成文件", use_container_width=True, key="clean_generated_interface_files"):
            try:
                if os.path.exists(auto_test_tool.test_dir):
                    shutil.rmtree(auto_test_tool.test_dir)
                os.makedirs(auto_test_tool.test_dir)
                st.session_state.pop("interface_last_generated_files", None)
                st.session_state.pop("interface_last_test_results", None)
                st.success("✅ 生成文件已清理")
            except Exception as exc:
                st.error(f"❌ 清理失败: {exc}")

    render_task_run_panel(
        run_center=run_center,
        tool_name="接口自动化测试",
        panel_key="api_automation_run_panel",
        limit=10,
    )
