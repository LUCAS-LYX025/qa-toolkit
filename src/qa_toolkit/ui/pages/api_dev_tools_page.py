import json
import os
import time
from typing import Any, Dict, List, Tuple

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from qa_toolkit.core.api_dev_tools import InterfaceDevTools
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.workflow_panels import render_download_panel, render_workflow_guide


INTERFACE_FILE_TYPES = ["xlsx", "xls", "json", "har", "bru", "txt", "md", "yaml", "yml"]
RAW_FORMAT_MAP = {
    "自动检测": "auto",
    "JSON / Apifox / Postman / HAR / Insomnia": "json",
    "Swagger/OpenAPI": "swagger",
    "结构化文本": "text",
    "Bruno .bru": "bruno",
}


def _escape_js_string(text: str) -> str:
    return json.dumps(text)


def _create_copy_button(text: str, button_text: str = "📋 复制到剪贴板", key: str = None) -> None:
    """创建一键复制按钮。"""
    button_key = key or f"copy_{hash(text)}"
    escaped_text = _escape_js_string(text)

    html_code = f"""
    <div style="margin: 10px 0;">
        <button
            id="{button_key}"
            onclick="copyToClipboard_{button_key}()"
            style="
                background: linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
                color: white;
                border: 1px solid rgba(250, 204, 21, 0.22);
                padding: 10px 20px;
                border-radius: 12px;
                cursor: pointer;
                font-size: 14px;
                font-weight: 700;
                box-shadow: 0 12px 22px rgba(7, 20, 39, 0.26);
                transition: all 0.3s ease;
            "
            onmouseover="this.style.transform='translateY(-1px)'"
            onmouseout="this.style.transform='translateY(0)'"
        >
            {button_text}
        </button>
        <script>
            function copyToClipboard_{button_key}() {{
                const text = {escaped_text};
                const button = document.getElementById('{button_key}');

                navigator.clipboard.writeText(text).then(function() {{
                    const originalText = button.innerHTML;
                    button.innerHTML = '✅ 复制成功！';
                    button.style.background = 'linear-gradient(135deg, #fb923c 0%, #ea580c 52%, #7c2d12 100%)';
                    button.style.color = '#ffffff';
                    button.style.fontWeight = '800';
                    button.style.textShadow = '0 1px 1px rgba(124,45,18,0.54)';
                    setTimeout(function() {{
                        button.innerHTML = originalText;
                        button.style.background = 'linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%)';
                        button.style.color = '#ffffff';
                        button.style.fontWeight = '700';
                        button.style.textShadow = '0 1px 1px rgba(7,20,39,0.34)';
                    }}, 2000);
                }}).catch(function(err) {{
                    button.innerHTML = '❌ 复制失败';
                    button.style.background = 'linear-gradient(90deg, #ef4444 0%, #dc2626 100%)';
                    button.style.color = '#ffffff';
                    button.style.fontWeight = '800';
                    button.style.textShadow = '0 1px 1px rgba(127,29,29,0.54)';
                    setTimeout(function() {{
                        button.innerHTML = '{button_text}';
                        button.style.background = 'linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%)';
                        button.style.color = '#ffffff';
                        button.style.fontWeight = '700';
                        button.style.textShadow = '0 1px 1px rgba(7,20,39,0.34)';
                    }}, 2000);
                }});
            }}
        </script>
    </div>
    """

    components.html(html_code, height=60)


def _render_interface_source_panel(prefix: str, title: str, height: int = 220) -> Dict[str, Any]:
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
    return source_data


def _parse_interface_source(
    parser: InterfaceAutoTestCore,
    source_data: Dict[str, Any],
    prefix: str,
) -> Tuple[List[Dict[str, Any]], str]:
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


def _build_interface_preview_rows(interfaces: List[Dict[str, Any]], limit: int = 10) -> List[Dict[str, Any]]:
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


def render_api_dev_tools_page() -> None:
    show_doc("interface_dev_tools")

    if "interface_dev_parser" not in st.session_state:
        st.session_state.interface_dev_parser = InterfaceAutoTestCore()
    if "interface_dev_toolkit" not in st.session_state:
        st.session_state.interface_dev_toolkit = InterfaceDevTools()

    dev_parser = st.session_state.interface_dev_parser
    dev_toolkit = st.session_state.interface_dev_toolkit

    st.markdown('<div class="category-card">🛠️ 接口研发辅助工具</div>', unsafe_allow_html=True)
    st.caption("围绕接口测试与联调补七类高频能力: 标准化导出、回归清单、变更分析、文档体检、断言模板、Mock 服务、请求代码片段。")
    render_workflow_guide(
        title="接口研发辅助推荐使用顺序",
        description="先做标准化和体检，再决定是产出回归清单、变更报告、断言模板，还是直接生成 Mock 与调试代码。",
        steps=[
            "先导入接口文档，优先做标准化导出和接口体检，确认文档质量。",
            "如果版本有差异，再做接口变更分析和回归清单整理。",
            "需要联调或自动化支持时，再生成断言模板、Mock 服务和请求代码片段。",
        ],
        tips=["先体检再回归", "先变更分析再做影响面判断", "Mock 和代码片段更适合联调阶段"],
        eyebrow="页面向导",
    )

    normalize_tab, checklist_tab, diff_tab, quality_tab, assertion_tab, mock_tab, snippet_tab = st.tabs(
        ["标准化导出", "回归清单生成", "接口变更分析", "接口文档体检", "断言模板生成", "Mock 服务生成", "请求代码片段"]
    )

    with normalize_tab:
        normalize_source = _render_interface_source_panel("interface_normalize_source", "接口文档", height=240)
        if st.button("🧾 生成标准化清单", use_container_width=True, key="generate_normalized_interfaces"):
            try:
                interfaces, source_name = _parse_interface_source(dev_parser, normalize_source, "interface_normalize_source")
                normalize_result = dev_toolkit.export_normalized_interfaces(interfaces)
                st.session_state.interface_dev_normalize_result = normalize_result
                st.session_state.interface_dev_normalize_source_name = source_name
                st.success(f"✅ 已标准化整理 {len(interfaces)} 个接口")
            except Exception as exc:
                st.error(f"❌ 生成失败: {exc}")

        normalize_result = st.session_state.get("interface_dev_normalize_result")
        if normalize_result:
            source_name = st.session_state.get("interface_dev_normalize_source_name", "当前文档")
            summary = normalize_result.get("summary", {})
            st.info(f"当前标准化来源: `{source_name}`")

            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            with metric_col1:
                st.metric("接口数", summary.get("interface_count", 0))
            with metric_col2:
                st.metric("含请求体", summary.get("with_body_count", 0))
            with metric_col3:
                st.metric("鉴权相关", summary.get("auth_related_count", 0))
            with metric_col4:
                st.metric("缺少响应样例", summary.get("missing_expected_response_count", 0))
            with metric_col5:
                st.metric("标签数", summary.get("tag_count", 0))

            normalized_interfaces = normalize_result.get("interfaces", [])
            if normalized_interfaces:
                st.markdown("### 📋 标准化预览")
                st.dataframe(pd.DataFrame(_build_interface_preview_rows(normalized_interfaces, limit=50)), use_container_width=True)

            artifact_tab1, artifact_tab2, artifact_tab3 = st.tabs(["JSON", "Markdown", "结构化文本"])
            with artifact_tab1:
                st.code(normalize_result.get("json_artifact", ""), language="json")
            with artifact_tab2:
                st.code(normalize_result.get("markdown_artifact", ""), language="markdown")
            with artifact_tab3:
                st.code(normalize_result.get("text_artifact", ""), language="text")

            render_download_panel(
                title="标准化导出区",
                description="统一下载标准化后的 JSON、Markdown 和结构化文本清单。",
                items=[
                    {
                        "label": "📥 下载 JSON 清单",
                        "data": normalize_result.get("json_artifact", ""),
                        "file_name": "normalized_interfaces.json",
                        "mime": "application/json",
                    },
                    {
                        "label": "📥 下载 Markdown 清单",
                        "data": normalize_result.get("markdown_artifact", ""),
                        "file_name": "normalized_interfaces.md",
                        "mime": "text/markdown",
                    },
                    {
                        "label": "📥 下载结构化文本",
                        "data": normalize_result.get("text_artifact", ""),
                        "file_name": "normalized_interfaces.txt",
                        "mime": "text/plain",
                    },
                ],
                key_prefix="interface_dev_normalize_exports",
                metrics=[
                    {"label": "接口数", "value": str(summary.get("interface_count", 0))},
                    {"label": "含请求体", "value": str(summary.get("with_body_count", 0))},
                    {"label": "缺少响应样例", "value": str(summary.get("missing_expected_response_count", 0))},
                ],
            )

    with checklist_tab:
        checklist_source = _render_interface_source_panel("interface_checklist_source", "接口文档", height=240)
        checklist_opt_col1, checklist_opt_col2, checklist_opt_col3 = st.columns(3)
        with checklist_opt_col1:
            include_negative = st.checkbox("包含负向场景", value=True, key="interface_checklist_negative")
        with checklist_opt_col2:
            include_auth_checks = st.checkbox("包含鉴权检查", value=True, key="interface_checklist_auth")
        with checklist_opt_col3:
            include_performance_checks = st.checkbox("包含性能关注", value=True, key="interface_checklist_performance")

        if st.button("🧠 生成回归清单", use_container_width=True, key="generate_regression_checklist"):
            try:
                interfaces, source_name = _parse_interface_source(dev_parser, checklist_source, "interface_checklist_source")
                checklist_result = dev_toolkit.generate_regression_checklist(
                    interfaces,
                    include_negative=include_negative,
                    include_auth_checks=include_auth_checks,
                    include_performance_checks=include_performance_checks,
                )
                st.session_state.interface_dev_checklist_result = checklist_result
                st.session_state.interface_dev_checklist_source_name = source_name
                st.success("✅ 回归清单已生成")
            except Exception as exc:
                st.error(f"❌ 生成失败: {exc}")

        checklist_result = st.session_state.get("interface_dev_checklist_result")
        if checklist_result:
            source_name = st.session_state.get("interface_dev_checklist_source_name", "当前文档")
            summary = checklist_result.get("summary", {})
            st.info(f"当前回归清单来源: `{source_name}`")

            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5 = st.columns(5)
            with metric_col1:
                st.metric("接口数", summary.get("interface_count", 0))
            with metric_col2:
                st.metric("高优先级", summary.get("high_priority_count", 0))
            with metric_col3:
                st.metric("中优先级", summary.get("medium_priority_count", 0))
            with metric_col4:
                st.metric("低优先级", summary.get("low_priority_count", 0))
            with metric_col5:
                st.metric("建议检查项", summary.get("check_item_count", 0))

            checklist_rows = checklist_result.get("rows", [])
            if checklist_rows:
                st.markdown("### 📌 回归总览")
                st.dataframe(pd.DataFrame(checklist_rows), use_container_width=True)

            items = checklist_result.get("items", [])
            if items:
                st.markdown("### 🧪 逐接口回归建议")
                for item in items:
                    priority_text = {"high": "高优先级", "medium": "中优先级", "low": "低优先级"}.get(item.get("priority"), "低优先级")
                    with st.expander(
                        f"{item.get('index', 0)}. {item.get('method', 'GET')} {item.get('path', '/')} | {item.get('name', '未命名接口')} | {priority_text}",
                        expanded=False,
                    ):
                        st.write(f"**关注点:** {'、'.join(item.get('focus_points', []))}")
                        for checklist_item in item.get("checklist", []):
                            st.write(f"- [ ] {checklist_item}")

            checklist_csv = pd.DataFrame(checklist_rows).to_csv(index=False, encoding="utf-8-sig")
            render_download_panel(
                title="回归清单导出区",
                description="统一下载 Markdown、JSON 和 CSV 三种清单结果。",
                items=[
                    {
                        "label": "📥 下载 Markdown 清单",
                        "data": checklist_result.get("markdown_artifact", ""),
                        "file_name": "interface_regression_checklist.md",
                        "mime": "text/markdown",
                    },
                    {
                        "label": "📥 下载 JSON 清单",
                        "data": checklist_result.get("json_artifact", ""),
                        "file_name": "interface_regression_checklist.json",
                        "mime": "application/json",
                    },
                    {
                        "label": "📥 下载 CSV 总览",
                        "data": checklist_csv.encode("utf-8-sig"),
                        "file_name": "interface_regression_checklist.csv",
                        "mime": "text/csv",
                    },
                ],
                key_prefix="interface_dev_checklist_exports",
            )

    with diff_tab:
        diff_col1, diff_col2 = st.columns(2)
        with diff_col1:
            baseline_source = _render_interface_source_panel("interface_diff_baseline", "基线版本")
        with diff_col2:
            target_source = _render_interface_source_panel("interface_diff_target", "当前版本")

        if st.button("🔍 开始分析接口差异", use_container_width=True, key="analyze_interface_diff"):
            try:
                baseline_interfaces, baseline_name = _parse_interface_source(dev_parser, baseline_source, "interface_diff_baseline")
                target_interfaces, target_name = _parse_interface_source(dev_parser, target_source, "interface_diff_target")
                diff_result = dev_toolkit.compare_interfaces(baseline_interfaces, target_interfaces)
                st.session_state.interface_dev_diff_result = diff_result
                st.session_state.interface_dev_diff_baseline_name = baseline_name
                st.session_state.interface_dev_diff_target_name = target_name
                st.success("✅ 接口差异分析完成")
            except Exception as exc:
                st.error(f"❌ 分析失败: {exc}")

        diff_result = st.session_state.get("interface_dev_diff_result")
        if diff_result:
            summary = diff_result.get("summary", {})
            baseline_name = st.session_state.get("interface_dev_diff_baseline_name", "基线版本")
            target_name = st.session_state.get("interface_dev_diff_target_name", "当前版本")
            st.info(f"基线文档: `{baseline_name}` | 当前文档: `{target_name}`")

            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
            with metric_col1:
                st.metric("基线接口", summary.get("baseline_total", 0))
            with metric_col2:
                st.metric("当前接口", summary.get("target_total", 0))
            with metric_col3:
                st.metric("新增", summary.get("added_count", 0))
            with metric_col4:
                st.metric("删除", summary.get("removed_count", 0))
            with metric_col5:
                st.metric("变更", summary.get("changed_count", 0))
            with metric_col6:
                st.metric("高风险", summary.get("high_risk_count", 0))

            if summary.get("added_count", 0) == 0 and summary.get("removed_count", 0) == 0 and summary.get("changed_count", 0) == 0:
                st.success("✅ 两个版本未发现接口差异")
            else:
                if diff_result.get("high_risk_changes"):
                    st.markdown("### ⚠️ 高风险变更")
                    high_risk_rows = []
                    for item in diff_result.get("high_risk_changes", []):
                        high_risk_rows.append(
                            {
                                "接口": item.get("name", "未命名接口"),
                                "方法": item.get("method", "GET"),
                                "路径": item.get("path", ""),
                                "变更点": "；".join(change.get("label", "") for change in item.get("changes", [])),
                            }
                        )
                    st.dataframe(pd.DataFrame(high_risk_rows), use_container_width=True)

                if diff_result.get("changed"):
                    st.markdown("### 🔄 变更接口明细")
                    for index, item in enumerate(diff_result.get("changed", []), start=1):
                        risk_label = {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(item.get("risk_level"), "未知")
                        with st.expander(
                            f"{index}. {item.get('method', 'GET')} {item.get('path', '')} | {item.get('name', '未命名接口')} | {risk_label}",
                            expanded=False,
                        ):
                            for change in item.get("changes", []):
                                st.write(f"- {change.get('label')}: {change.get('message')}")

                added_removed_col1, added_removed_col2 = st.columns(2)
                with added_removed_col1:
                    st.markdown("### ➕ 新增接口")
                    if diff_result.get("added"):
                        st.dataframe(pd.DataFrame(diff_result.get("added", [])), use_container_width=True)
                    else:
                        st.info("当前没有新增接口")
                with added_removed_col2:
                    st.markdown("### ➖ 删除接口")
                    if diff_result.get("removed"):
                        st.dataframe(pd.DataFrame(diff_result.get("removed", [])), use_container_width=True)
                    else:
                        st.info("当前没有删除接口")

            render_download_panel(
                title="差异分析导出区",
                description="统一下载 Markdown 和 JSON 版本的差异报告。",
                items=[
                    {
                        "label": "📥 下载 Markdown 报告",
                        "data": dev_toolkit.build_markdown_report(diff_result),
                        "file_name": "interface_diff_report.md",
                        "mime": "text/markdown",
                    },
                    {
                        "label": "📥 下载 JSON 报告",
                        "data": json.dumps(diff_result, ensure_ascii=False, indent=2),
                        "file_name": "interface_diff_report.json",
                        "mime": "application/json",
                    },
                ],
                key_prefix="interface_dev_diff_exports",
            )

    with quality_tab:
        quality_source = _render_interface_source_panel("interface_quality_source", "接口文档", height=240)
        quality_col1, quality_col2 = st.columns([2, 1])
        with quality_col1:
            st.info("体检会检查重复接口、缺少响应示例、路径参数不匹配、请求格式与 Header 不一致等常见问题。")
        with quality_col2:
            if st.button("🩺 开始体检", use_container_width=True, key="analyze_interface_quality"):
                try:
                    interfaces, source_name = _parse_interface_source(dev_parser, quality_source, "interface_quality_source")
                    quality_result = dev_toolkit.analyze_interface_quality(interfaces)
                    st.session_state.interface_dev_quality_result = quality_result
                    st.session_state.interface_dev_quality_source_name = source_name
                    st.success("✅ 接口文档体检完成")
                except Exception as exc:
                    st.error(f"❌ 体检失败: {exc}")

        quality_result = st.session_state.get("interface_dev_quality_result")
        if quality_result:
            source_name = st.session_state.get("interface_dev_quality_source_name", "当前文档")
            summary = quality_result.get("summary", {})
            st.info(f"当前体检来源: `{source_name}`")

            metric_col1, metric_col2, metric_col3, metric_col4, metric_col5, metric_col6 = st.columns(6)
            with metric_col1:
                st.metric("接口数", summary.get("interface_count", 0))
            with metric_col2:
                st.metric("健康分", summary.get("health_score", 0))
            with metric_col3:
                st.metric("评级", summary.get("health_level", "未知"))
            with metric_col4:
                st.metric("高风险", summary.get("high_count", 0))
            with metric_col5:
                st.metric("中风险", summary.get("medium_count", 0))
            with metric_col6:
                st.metric("低风险", summary.get("low_count", 0))

            duplicate_groups = quality_result.get("duplicate_groups", [])
            if duplicate_groups:
                st.markdown("### 🔁 重复接口")
                duplicate_rows = []
                for item in duplicate_groups:
                    duplicate_rows.append(
                        {
                            "方法": item.get("method", "GET"),
                            "路径": item.get("path", "/"),
                            "重复次数": item.get("count", 0),
                            "序号": ", ".join(str(index) for index in item.get("indexes", [])),
                        }
                    )
                st.dataframe(pd.DataFrame(duplicate_rows), use_container_width=True)

            issues = quality_result.get("issues", [])
            if issues:
                st.markdown("### 📋 问题清单")
                selected_severities = st.multiselect(
                    "筛选风险等级",
                    ["high", "medium", "low"],
                    default=["high", "medium", "low"],
                    format_func=lambda value: {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(value, value),
                    key="interface_quality_severities",
                )
                filtered_issues = [item for item in issues if item.get("severity") in selected_severities]
                issue_rows = []
                for item in filtered_issues:
                    issue_rows.append(
                        {
                            "序号": item.get("index", 0),
                            "风险等级": {"high": "高风险", "medium": "中风险", "low": "低风险"}.get(item.get("severity"), "未知"),
                            "方法": item.get("method", "GET"),
                            "路径": item.get("path", "/"),
                            "分类": item.get("category", ""),
                            "说明": item.get("message", ""),
                        }
                    )
                st.dataframe(pd.DataFrame(issue_rows), use_container_width=True)
            else:
                st.success("✅ 文档体检未发现问题")

            render_download_panel(
                title="体检报告导出区",
                description="统一下载 Markdown 和 JSON 版本的文档体检报告。",
                items=[
                    {
                        "label": "📥 下载体检 Markdown 报告",
                        "data": dev_toolkit.build_quality_markdown_report(quality_result),
                        "file_name": "interface_quality_report.md",
                        "mime": "text/markdown",
                    },
                    {
                        "label": "📥 下载体检 JSON 报告",
                        "data": json.dumps(quality_result, ensure_ascii=False, indent=2),
                        "file_name": "interface_quality_report.json",
                        "mime": "application/json",
                    },
                ],
                key_prefix="interface_dev_quality_exports",
            )

    with assertion_tab:
        assertion_input_mode = st.radio(
            "样例来源",
            ["原始响应 JSON", "从接口文档选择接口"],
            horizontal=True,
            key="interface_assertion_input_mode",
        )

        assertion_sample_text = ""
        if assertion_input_mode == "原始响应 JSON":
            assertion_sample_text = st.text_area(
                "响应样例",
                height=260,
                placeholder='例如: {"code":0,"data":{"id":1,"name":"测试用户"}}',
                key="interface_assertion_sample_text",
            )
        else:
            assertion_source = _render_interface_source_panel("interface_assertion_source", "接口文档", height=220)
            if st.button("📥 解析接口列表", use_container_width=True, key="parse_assertion_source"):
                try:
                    interfaces, source_name = _parse_interface_source(dev_parser, assertion_source, "interface_assertion_source")
                    st.session_state.interface_dev_assertion_interfaces = interfaces
                    st.session_state.interface_dev_assertion_source_name = source_name
                    st.success(f"✅ 成功解析出 {len(interfaces)} 个接口")
                except Exception as exc:
                    st.error(f"❌ 解析失败: {exc}")

            assertion_interfaces = st.session_state.get("interface_dev_assertion_interfaces", [])
            if assertion_interfaces:
                source_name = st.session_state.get("interface_dev_assertion_source_name", "当前文档")
                st.info(f"当前断言样例来源: `{source_name}` | 接口数: {len(assertion_interfaces)}")
                selected_assertion_index = st.selectbox(
                    "选择接口",
                    range(len(assertion_interfaces)),
                    format_func=lambda idx: (
                        f"{idx + 1}. {assertion_interfaces[idx].get('method', 'GET')} "
                        f"{assertion_interfaces[idx].get('path', '')} | {assertion_interfaces[idx].get('name', '未命名接口')}"
                    ),
                    key="interface_assertion_selected_index",
                )
                selected_interface = assertion_interfaces[selected_assertion_index]
                if selected_interface.get("expected_response") in (None, "", {}, []):
                    st.warning("当前接口没有 `expected_response` 示例，无法直接生成断言模板")
                else:
                    assertion_sample_text = json.dumps(selected_interface.get("expected_response"), ensure_ascii=False, indent=2)
                    st.code(assertion_sample_text, language="json")

        assertion_col1, assertion_col2 = st.columns(2)
        with assertion_col1:
            assertion_style = st.radio(
                "断言风格",
                ["字段存在断言", "标准断言", "严格断言"],
                horizontal=True,
                key="interface_assertion_style",
            )
        with assertion_col2:
            assertion_depth = st.slider("结构展开深度", min_value=1, max_value=6, value=4, key="interface_assertion_depth")

        if st.button("🧠 生成断言模板", use_container_width=True, key="generate_assertion_template"):
            try:
                if not assertion_sample_text.strip():
                    raise ValueError("请先提供响应样例")
                assertion_result = dev_toolkit.generate_assertion_template(
                    assertion_sample_text,
                    template_style=assertion_style,
                    max_depth=assertion_depth,
                )
                st.session_state.interface_dev_assertion_result = assertion_result
                st.success("✅ 断言模板已生成")
            except Exception as exc:
                st.error(f"❌ 生成失败: {exc}")

        assertion_result = st.session_state.get("interface_dev_assertion_result")
        if assertion_result:
            info_col1, info_col2, info_col3 = st.columns(3)
            with info_col1:
                st.metric("样例类型", assertion_result.get("sample_type", "unknown"))
            with info_col2:
                st.metric("字段路径数", assertion_result.get("field_count", 0))
            with info_col3:
                st.metric("模板模式", assertion_style)

            st.markdown("### 🎯 可直接粘贴到用例中的片段")
            st.code(assertion_result.get("case_fragment_json", ""), language="json")

            st.markdown("### 📐 断言模板")
            st.code(assertion_result.get("template_json", ""), language="json")

            st.markdown("### 🧭 字段路径预览")
            field_path_rows = [{"字段路径": item} for item in assertion_result.get("field_paths", [])]
            st.dataframe(pd.DataFrame(field_path_rows), use_container_width=True)

            assertion_action_col1, assertion_action_col2 = st.columns(2)
            with assertion_action_col1:
                _create_copy_button(
                    assertion_result.get("case_fragment_json", ""),
                    button_text="📋 复制断言片段",
                    key="copy_assertion_fragment",
                )
            with assertion_action_col2:
                st.download_button(
                    label="📥 下载断言模板",
                    data=assertion_result.get("case_fragment_json", ""),
                    file_name="expected_response_template.json",
                    mime="application/json",
                    use_container_width=True,
                    key="download_assertion_template",
                )

    with mock_tab:
        mock_source = _render_interface_source_panel("interface_mock_source", "接口文档", height=240)
        mock_config_col1, mock_config_col2, mock_config_col3, mock_config_col4 = st.columns(4)
        with mock_config_col1:
            mock_host = st.text_input("监听地址", value="0.0.0.0", key="mock_server_host")
        with mock_config_col2:
            mock_port = st.number_input("监听端口", min_value=1, max_value=65535, value=8000, key="mock_server_port")
        with mock_config_col3:
            mock_delay_ms = st.number_input("固定延迟(ms)", min_value=0, value=0, key="mock_server_delay")
        with mock_config_col4:
            mock_enable_cors = st.checkbox("开启 CORS", value=True, key="mock_server_cors")

        if st.button("🧱 生成 Mock 服务脚本", use_container_width=True, key="generate_mock_server_script"):
            try:
                interfaces, source_name = _parse_interface_source(dev_parser, mock_source, "interface_mock_source")
                mock_script = dev_toolkit.generate_mock_server_script(
                    interfaces=interfaces,
                    host=mock_host,
                    port=int(mock_port),
                    enable_cors=mock_enable_cors,
                    delay_ms=int(mock_delay_ms),
                )
                st.session_state.interface_dev_mock_interfaces = interfaces
                st.session_state.interface_dev_mock_source_name = source_name
                st.session_state.interface_dev_mock_script = mock_script
                st.success(f"✅ 已根据 {len(interfaces)} 个接口生成 Mock 服务脚本")
            except Exception as exc:
                st.error(f"❌ 生成失败: {exc}")

        mock_script = st.session_state.get("interface_dev_mock_script")
        if mock_script:
            mock_interfaces = st.session_state.get("interface_dev_mock_interfaces", [])
            source_name = st.session_state.get("interface_dev_mock_source_name", "当前文档")
            st.info(f"当前 Mock 来源: `{source_name}` | 接口数: {len(mock_interfaces)}")
            if mock_interfaces:
                st.dataframe(pd.DataFrame(_build_interface_preview_rows(mock_interfaces)), use_container_width=True)

            st.code(mock_script, language="python")
            st.code(f"python mock_api_server.py --host {mock_host} --port {int(mock_port)}", language="bash")

            mock_action_col1, mock_action_col2 = st.columns(2)
            with mock_action_col1:
                _create_copy_button(mock_script, button_text="📋 复制 Mock 脚本", key="copy_mock_script")
            with mock_action_col2:
                st.download_button(
                    label="📥 下载 Mock 脚本",
                    data=mock_script,
                    file_name="mock_api_server.py",
                    mime="text/x-python",
                    use_container_width=True,
                    key="download_mock_script",
                )

    with snippet_tab:
        snippet_source = _render_interface_source_panel("interface_snippet_source", "接口文档", height=240)
        if st.button("📥 解析接口文档", use_container_width=True, key="parse_snippet_source"):
            try:
                interfaces, source_name = _parse_interface_source(dev_parser, snippet_source, "interface_snippet_source")
                st.session_state.interface_dev_snippet_interfaces = interfaces
                st.session_state.interface_dev_snippet_source_name = source_name
                st.session_state.pop("interface_dev_snippet_result", None)
                st.success(f"✅ 成功解析出 {len(interfaces)} 个接口")
            except Exception as exc:
                st.error(f"❌ 解析失败: {exc}")

        snippet_interfaces = st.session_state.get("interface_dev_snippet_interfaces", [])
        if snippet_interfaces:
            source_name = st.session_state.get("interface_dev_snippet_source_name", "当前文档")
            st.info(f"当前代码片段来源: `{source_name}` | 接口数: {len(snippet_interfaces)}")
            st.dataframe(pd.DataFrame(_build_interface_preview_rows(snippet_interfaces)), use_container_width=True)

            selected_index = st.selectbox(
                "选择接口",
                range(len(snippet_interfaces)),
                format_func=lambda idx: (
                    f"{idx + 1}. {snippet_interfaces[idx].get('method', 'GET')} "
                    f"{snippet_interfaces[idx].get('path', '')} | {snippet_interfaces[idx].get('name', '未命名接口')}"
                ),
                key="interface_snippet_selected_index",
            )

            snippet_col1, snippet_col2 = st.columns(2)
            with snippet_col1:
                snippet_language = st.radio(
                    "代码类型",
                    ["Python requests", "JavaScript fetch", "curl"],
                    horizontal=True,
                    key="interface_snippet_language",
                )
            with snippet_col2:
                snippet_base_url = st.text_input(
                    "基础URL",
                    value="https://example.com",
                    placeholder="例如: https://api.example.com",
                    key="interface_snippet_base_url",
                )

            if st.button("⚡ 生成请求代码片段", use_container_width=True, key="generate_request_snippet"):
                try:
                    snippet_result = dev_toolkit.generate_request_snippet(
                        snippet_interfaces[selected_index],
                        language=snippet_language,
                        base_url=snippet_base_url,
                    )
                    st.session_state.interface_dev_snippet_result = snippet_result
                    st.session_state.interface_dev_snippet_language_value = snippet_language
                    st.success("✅ 请求代码片段已生成")
                except Exception as exc:
                    st.error(f"❌ 生成代码片段失败: {exc}")

        snippet_result = st.session_state.get("interface_dev_snippet_result")
        if snippet_result:
            snippet_language = st.session_state.get("interface_dev_snippet_language_value", "Python requests")
            snippet_language_map = {
                "Python requests": "python",
                "JavaScript fetch": "javascript",
                "curl": "bash",
            }
            st.code(snippet_result, language=snippet_language_map.get(snippet_language, "text"))
            snippet_action_col1, snippet_action_col2 = st.columns(2)
            with snippet_action_col1:
                _create_copy_button(snippet_result, button_text="📋 复制代码片段", key="copy_request_snippet")
            with snippet_action_col2:
                st.download_button(
                    label="📥 下载代码片段",
                    data=snippet_result,
                    file_name=f"request_snippet_{snippet_language.replace(' ', '_').lower()}.txt",
                    mime="text/plain",
                    use_container_width=True,
                    key="download_request_snippet",
                )
