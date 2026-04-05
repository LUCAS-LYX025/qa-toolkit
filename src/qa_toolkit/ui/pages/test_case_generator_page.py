from __future__ import annotations

import io
import json
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.test_case_generator import TestCaseGenerator


SAMPLE_REQUIREMENT = """用户可在 App 端新增收货地址，并支持将地址设为默认地址。
新增地址时姓名、手机号、省市区、详细地址为必填项，手机号需校验格式。
一个用户只能有一个默认地址；如果新增地址时勾选默认地址，原默认地址自动取消。
保存成功后返回地址列表页并立即展示最新地址。
当接口超时、服务异常或字段校验失败时，需要给出明确提示。
本次不覆盖批量导入地址。"""

DEFAULT_STATE = {
    "tcg_requirement_text": "",
    "tcg_ocr_text": "",
    "tcg_module_name": "",
    "tcg_business_rules": "",
    "tcg_acceptance_criteria": "",
    "tcg_out_of_scope": "",
    "tcg_additional_notes": "",
    "tcg_analysis_result": None,
    "tcg_composed_requirement": "",
    "tcg_generated_cases": None,
    "tcg_generation_error": "",
    "tcg_history": [],
    "tcg_platform": "ali",
    "tcg_case_style": "标准格式",
    "tcg_language": "中文",
    "tcg_target_case_count": 12,
    "tcg_id_prefix": "TC",
    "tcg_selected_focus": [],
    "tcg_result_keyword": "",
    "tcg_result_priorities": [],
    "tcg_ocr_language_label": "中英混合",
    "tcg_ocr_preprocess_mode": "增强文本",
    "tcg_ali_api_key": "",
    "tcg_openai_api_key": "",
    "tcg_openai_model_version": "gpt-4o-mini",
    "tcg_openai_api_base": "",
    "tcg_baidu_api_key": "",
    "tcg_baidu_secret_key": "",
    "tcg_spark_api_key": "",
    "tcg_spark_api_base": "http://maas-api.cn-huabei-1.xf-yun.com/v1",
    "tcg_spark_model_id": "",
    "tcg_glm_api_key": "",
    "tcg_glm_model_version": "glm-4-flash",
    "tcg_glm_api_base": "https://open.bigmodel.cn/api/paas/v4",
}


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_example_requirement() -> None:
    st.session_state.tcg_requirement_text = SAMPLE_REQUIREMENT
    st.session_state.tcg_module_name = "用户中心 / 地址管理"
    st.session_state.tcg_business_rules = "默认地址仅允许一条；手机号必须通过格式校验。"
    st.session_state.tcg_acceptance_criteria = "保存成功后返回地址列表页并展示最新地址。"
    st.session_state.tcg_out_of_scope = "本次不覆盖批量导入与性能压测。"
    st.session_state.tcg_additional_notes = "优先输出功能、异常处理、边界值和数据校验相关用例。"


def _compose_requirement(generator: TestCaseGenerator) -> str:
    return generator.compose_requirement_context(
        requirement=st.session_state.tcg_requirement_text,
        ocr_text=st.session_state.tcg_ocr_text,
        module_name=st.session_state.tcg_module_name,
        business_rules=st.session_state.tcg_business_rules,
        acceptance_criteria=st.session_state.tcg_acceptance_criteria,
        out_of_scope=st.session_state.tcg_out_of_scope,
        additional_notes=st.session_state.tcg_additional_notes,
    )


def _record_history(entry: Dict[str, Any]) -> None:
    history = list(st.session_state.tcg_history)
    history.insert(0, entry)
    st.session_state.tcg_history = history[:6]


def _render_api_config(platform: str) -> Dict[str, Any]:
    st.markdown("### API 配置")

    if platform == "ali":
        st.text_input("阿里 API Key", key="tcg_ali_api_key", type="password")
        return {"api_key": st.session_state.tcg_ali_api_key}

    if platform == "openai":
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("OpenAI API Key", key="tcg_openai_api_key", type="password")
        with col2:
            st.text_input("模型名称", key="tcg_openai_model_version")
        st.text_input(
            "兼容 Base URL（可选）",
            key="tcg_openai_api_base",
            placeholder="留空默认使用 https://api.openai.com/v1",
        )
        return {
            "api_key": st.session_state.tcg_openai_api_key,
            "model_version": st.session_state.tcg_openai_model_version,
            "api_base": st.session_state.tcg_openai_api_base,
        }

    if platform == "baidu":
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("百度 API Key", key="tcg_baidu_api_key", type="password")
        with col2:
            st.text_input("百度 Secret Key", key="tcg_baidu_secret_key", type="password")
        return {
            "api_key": st.session_state.tcg_baidu_api_key,
            "secret_key": st.session_state.tcg_baidu_secret_key,
        }

    if platform == "spark":
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("讯飞 API Key", key="tcg_spark_api_key", type="password")
        with col2:
            st.text_input("模型 ID", key="tcg_spark_model_id")
        st.text_input("Base URL", key="tcg_spark_api_base")
        return {
            "api_key": st.session_state.tcg_spark_api_key,
            "api_base": st.session_state.tcg_spark_api_base,
            "model_id": st.session_state.tcg_spark_model_id,
        }

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("智谱 API Key", key="tcg_glm_api_key", type="password")
    with col2:
        st.text_input("模型名称", key="tcg_glm_model_version")
    st.text_input("兼容 Base URL", key="tcg_glm_api_base")
    st.caption("当前按 OpenAI 兼容协议调用，若你使用智谱兼容网关，可直接填兼容地址。")
    return {
        "api_key": st.session_state.tcg_glm_api_key,
        "model_version": st.session_state.tcg_glm_model_version,
        "api_base": st.session_state.tcg_glm_api_base,
    }


def _validate_api_config(platform: str, api_config: Dict[str, Any]) -> str:
    required_fields = {
        "ali": ["api_key"],
        "openai": ["api_key"],
        "baidu": ["api_key", "secret_key"],
        "spark": ["api_key", "model_id"],
        "glm": ["api_key", "model_version"],
    }
    missing = [field for field in required_fields[platform] if not str(api_config.get(field, "")).strip()]
    if not missing:
        return ""
    return f"请先补全 {', '.join(missing)}"


def _render_analysis_result(analysis: Dict[str, Any]) -> None:
    metric_cols = st.columns(4)
    metric_cols[0].metric("复杂度", analysis["complexity"])
    metric_cols[1].metric("识别功能点", len(analysis["feature_points"]))
    metric_cols[2].metric("识别业务规则", len(analysis["business_rules"]))
    metric_cols[3].metric("建议覆盖维度", len(analysis["suggested_focus"]))

    st.info(f"需求摘要: {analysis['summary'] or '当前暂无摘要'}")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### 功能点")
        if analysis["feature_points"]:
            for item in analysis["feature_points"]:
                st.write(f"- {item}")
        else:
            st.caption("暂无")

        st.markdown("#### 业务规则")
        if analysis["business_rules"]:
            for item in analysis["business_rules"]:
                st.write(f"- {item}")
        else:
            st.caption("暂无")

    with col2:
        st.markdown("#### 角色与推荐覆盖")
        st.write(f"识别角色: {'、'.join(analysis['roles']) if analysis['roles'] else '未识别'}")
        if analysis["suggested_focus"]:
            st.write(f"推荐覆盖: {'、'.join(analysis['suggested_focus'])}")
        else:
            st.caption("暂无")

        st.markdown("#### 待确认项")
        if analysis["unclear_points"]:
            for item in analysis["unclear_points"]:
                st.write(f"- {item}")
        else:
            st.caption("暂无")


def _build_export_buffers(cases: List[Dict[str, Any]], requirement_text: str, generator: TestCaseGenerator) -> Dict[str, bytes]:
    normalized_cases = generator.normalize_cases_for_display(cases)
    dataframe = pd.DataFrame(normalized_cases)
    json_bytes = json.dumps(normalized_cases, ensure_ascii=False, indent=2).encode("utf-8")
    csv_bytes = dataframe.to_csv(index=False).encode("utf-8-sig")
    markdown_bytes = generator.generate_markdown_report(cases, requirement_text).encode("utf-8")

    excel_buffer = io.BytesIO()
    with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="测试用例")
    excel_buffer.seek(0)

    return {
        "csv": csv_bytes,
        "json": json_bytes,
        "markdown": markdown_bytes,
        "excel": excel_buffer.getvalue(),
    }


def _render_generation_results(generator: TestCaseGenerator) -> None:
    cases = st.session_state.tcg_generated_cases
    if not cases:
        return

    normalized_cases = generator.normalize_cases_for_display(cases)
    dataframe = pd.DataFrame(normalized_cases)

    priorities = sorted({str(item.get("优先级", "")).strip() for item in normalized_cases if item.get("优先级")})
    if priorities and not st.session_state.tcg_result_priorities:
        st.session_state.tcg_result_priorities = priorities

    metric_cols = st.columns(4)
    metric_cols[0].metric("生成用例数", len(normalized_cases))
    metric_cols[1].metric("高优先级", sum(1 for item in normalized_cases if item.get("优先级") == "高"))
    metric_cols[2].metric("测试类型", dataframe["测试类型"].nunique() if "测试类型" in dataframe.columns else 0)
    metric_cols[3].metric("覆盖维度", len(st.session_state.tcg_selected_focus))

    filter_col1, filter_col2 = st.columns([1.5, 2])
    with filter_col1:
        selected_priorities = st.multiselect(
            "按优先级过滤",
            priorities,
            default=st.session_state.tcg_result_priorities or priorities,
            key="tcg_result_priorities",
        )
    with filter_col2:
        keyword = st.text_input("关键词过滤", key="tcg_result_keyword", placeholder="按用例名称、步骤或预期结果过滤")

    filtered_rows = []
    normalized_keyword = keyword.strip().lower()
    for row in normalized_cases:
        if selected_priorities and row.get("优先级") not in selected_priorities:
            continue
        haystack = "\n".join(
            [
                str(row.get("用例名称", "")),
                str(row.get("测试步骤", "")),
                str(row.get("预期结果", "")),
                str(row.get("备注", "")),
            ]
        ).lower()
        if normalized_keyword and normalized_keyword not in haystack:
            continue
        filtered_rows.append(row)

    if not filtered_rows:
        st.info("当前过滤条件下没有匹配的测试用例。")
        return

    st.dataframe(pd.DataFrame(filtered_rows), use_container_width=True, hide_index=True)

    with st.expander("逐条查看测试用例", expanded=False):
        for item in filtered_rows:
            title = f"{item.get('用例ID', '-') } | {item.get('用例名称', '未命名用例')}"
            with st.container(border=True):
                st.markdown(f"**{title}**")
                st.write(f"前置条件: {item.get('前置条件', '-') or '-'}")
                st.write(f"测试步骤: {item.get('测试步骤', '-') or '-'}")
                st.write(f"预期结果: {item.get('预期结果', '-') or '-'}")
                st.write(f"优先级 / 类型: {item.get('优先级', '-') or '-'} / {item.get('测试类型', '-') or '-'}")
                if item.get("备注"):
                    st.write(f"备注: {item['备注']}")

    export_buffers = _build_export_buffers(
        st.session_state.tcg_generated_cases,
        st.session_state.tcg_composed_requirement,
        generator,
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_col1, export_col2, export_col3, export_col4 = st.columns(4)
    with export_col1:
        st.download_button(
            "下载 Excel",
            data=export_buffers["excel"],
            file_name=f"test_cases_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )
    with export_col2:
        st.download_button(
            "下载 CSV",
            data=export_buffers["csv"],
            file_name=f"test_cases_{timestamp}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with export_col3:
        st.download_button(
            "下载 JSON",
            data=export_buffers["json"],
            file_name=f"test_cases_{timestamp}.json",
            mime="application/json",
            use_container_width=True,
        )
    with export_col4:
        st.download_button(
            "下载 Markdown",
            data=export_buffers["markdown"],
            file_name=f"test_cases_{timestamp}.md",
            mime="text/markdown",
            use_container_width=True,
        )


def render_test_case_generator_page() -> None:
    _ensure_defaults()
    generator = TestCaseGenerator()

    show_doc("test_case_generator")
    st.markdown('<div class="category-card">🧪 AI 测试用例生成器</div>', unsafe_allow_html=True)

    top_col1, top_col2, top_col3 = st.columns([1, 1, 3])
    with top_col1:
        if st.button("载入示例需求", use_container_width=True, key="tcg_load_example"):
            _load_example_requirement()
            st.rerun()
    with top_col2:
        if st.button("清空当前内容", use_container_width=True, key="tcg_clear_input"):
            for key in [
                "tcg_requirement_text",
                "tcg_ocr_text",
                "tcg_module_name",
                "tcg_business_rules",
                "tcg_acceptance_criteria",
                "tcg_out_of_scope",
                "tcg_additional_notes",
            ]:
                st.session_state[key] = ""
            st.session_state.tcg_analysis_result = None
            st.session_state.tcg_composed_requirement = ""
            st.session_state.tcg_generated_cases = None
            st.session_state.tcg_generation_error = ""
            st.rerun()
    with top_col3:
        st.caption("先做本地需求梳理，再生成测试用例，结果会更稳定。")

    input_tab, config_tab, result_tab = st.tabs(["需求输入", "生成配置", "结果导出"])

    with input_tab:
        left_col, right_col = st.columns([1.3, 1])
        with left_col:
            st.text_area(
                "需求原文",
                key="tcg_requirement_text",
                height=260,
                placeholder="粘贴 PRD、接口说明、聊天记录、验收标准或需求摘要...",
            )
        with right_col:
            ocr_status = generator.get_ocr_status()
            status_type = ocr_status["status"]
            if status_type == "available":
                st.success(ocr_status["message"])
            else:
                st.info(ocr_status["message"])

            uploaded_image = st.file_uploader(
                "上传需求截图 / 原型图",
                type=["png", "jpg", "jpeg", "webp", "bmp"],
                key="tcg_requirement_image",
            )
            ocr_col1, ocr_col2 = st.columns(2)
            with ocr_col1:
                st.selectbox(
                    "OCR 语言",
                    list(generator.get_ocr_language_options().keys()),
                    key="tcg_ocr_language_label",
                )
            with ocr_col2:
                st.selectbox(
                    "预处理模式",
                    generator.get_ocr_preprocess_modes(),
                    key="tcg_ocr_preprocess_mode",
                )
            if st.button("识别图片文字", use_container_width=True, key="tcg_run_ocr"):
                if uploaded_image is None:
                    st.warning("请先上传图片。")
                elif not generator.is_ocr_available():
                    st.warning("当前环境 OCR 不可用，无法识别图片文字。")
                else:
                    try:
                        ocr_text = generator.extract_text_from_image(
                            uploaded_image.getvalue(),
                            lang=generator.get_ocr_language_options()[st.session_state.tcg_ocr_language_label],
                            preprocess_mode=st.session_state.tcg_ocr_preprocess_mode,
                        )
                        st.session_state.tcg_ocr_text = ocr_text
                        st.success("图片文字识别完成。")
                    except Exception as exc:
                        st.error(f"OCR 识别失败: {exc}")

        with st.expander("结构化补充说明", expanded=True):
            field_col1, field_col2 = st.columns(2)
            with field_col1:
                st.text_input("所属模块 / 页面", key="tcg_module_name")
                st.text_area("业务规则 / 字段约束", key="tcg_business_rules", height=120)
                st.text_area("验收标准 / 成功条件", key="tcg_acceptance_criteria", height=120)
            with field_col2:
                st.text_area("OCR 识别补充文本", key="tcg_ocr_text", height=120)
                st.text_area("本次不覆盖范围", key="tcg_out_of_scope", height=120)
                st.text_area("额外说明", key="tcg_additional_notes", height=120)

        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("梳理需求并推荐覆盖维度", use_container_width=True, key="tcg_analyze_requirement"):
                composed_requirement = _compose_requirement(generator)
                analysis = generator.analyze_requirement(composed_requirement)
                st.session_state.tcg_composed_requirement = composed_requirement
                st.session_state.tcg_analysis_result = analysis
                st.session_state.tcg_selected_focus = analysis["suggested_focus"]
        with action_col2:
            st.caption("需求分析为本地静态梳理，不会调用外部模型。")

        if st.session_state.tcg_analysis_result:
            _render_analysis_result(st.session_state.tcg_analysis_result)

        if st.session_state.tcg_composed_requirement:
            with st.expander("本次发送给模型的需求上下文", expanded=False):
                st.code(st.session_state.tcg_composed_requirement, language="markdown")

    with config_tab:
        platforms = generator.get_supported_platforms()
        st.selectbox(
            "模型平台",
            list(platforms.keys()),
            format_func=lambda key: platforms[key],
            key="tcg_platform",
        )
        api_config = _render_api_config(st.session_state.tcg_platform)

        option_col1, option_col2, option_col3, option_col4 = st.columns(4)
        with option_col1:
            st.text_input("用例 ID 前缀", key="tcg_id_prefix")
        with option_col2:
            st.selectbox("用例风格", list(generator.get_case_styles().keys()), key="tcg_case_style")
        with option_col3:
            st.selectbox("输出语言", generator.get_languages(), key="tcg_language")
        with option_col4:
            st.number_input("目标用例数", min_value=1, max_value=60, key="tcg_target_case_count")

        focus_options = generator.get_coverage_focus_options()
        st.multiselect(
            "重点覆盖维度",
            list(focus_options.keys()),
            default=st.session_state.tcg_selected_focus,
            format_func=lambda key: f"{key} | {focus_options[key]}",
            key="tcg_selected_focus",
        )

        if st.button("生成测试用例", use_container_width=True, key="tcg_generate_cases"):
            composed_requirement = _compose_requirement(generator)
            st.session_state.tcg_composed_requirement = composed_requirement
            st.session_state.tcg_generation_error = ""

            if not composed_requirement.strip():
                st.warning("请先输入需求内容。")
            else:
                validation_error = _validate_api_config(st.session_state.tcg_platform, api_config)
                if validation_error:
                    st.warning(validation_error)
                else:
                    try:
                        with st.spinner("正在调用模型生成测试用例..."):
                            cases = generator.generate_testcases(
                                requirement=composed_requirement,
                                platform=st.session_state.tcg_platform,
                                api_config=api_config,
                                id_prefix=st.session_state.tcg_id_prefix.strip() or "TC",
                                case_style=st.session_state.tcg_case_style,
                                language=st.session_state.tcg_language,
                                target_case_count=int(st.session_state.tcg_target_case_count),
                                coverage_focus=list(st.session_state.tcg_selected_focus),
                            )
                        st.session_state.tcg_generated_cases = cases
                        _record_history(
                            {
                                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                "platform": platforms[st.session_state.tcg_platform],
                                "requirement": composed_requirement,
                                "cases": generator.normalize_cases_for_display(cases),
                            }
                        )
                        st.success(f"已生成 {len(cases)} 条测试用例。")
                    except Exception as exc:
                        st.session_state.tcg_generated_cases = None
                        st.session_state.tcg_generation_error = str(exc)
                        st.error(f"生成失败: {exc}")

        if st.session_state.tcg_generation_error:
            st.error(st.session_state.tcg_generation_error)

        if st.session_state.tcg_history:
            with st.expander("最近生成记录", expanded=False):
                for index, item in enumerate(st.session_state.tcg_history):
                    title = f"{item['timestamp']} | {item['platform']} | {len(item['cases'])} 条"
                    history_col1, history_col2 = st.columns([4, 1])
                    with history_col1:
                        st.write(title)
                    with history_col2:
                        if st.button("回填", key=f"tcg_history_apply_{index}", use_container_width=True):
                            st.session_state.tcg_requirement_text = item["requirement"]
                            st.session_state.tcg_composed_requirement = item["requirement"]
                            st.session_state.tcg_generated_cases = item["cases"]
                            st.rerun()

    with result_tab:
        if not st.session_state.tcg_generated_cases:
            st.info("生成完成后，这里会展示可筛选的用例列表和多格式导出按钮。")
        else:
            _render_generation_results(generator)
