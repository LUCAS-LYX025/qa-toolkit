from __future__ import annotations

import io
import json
import os
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button, secondary_action_button
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
    render_warning_feedback,
)
from qa_toolkit.tools.test_case_generator import TestCaseGenerator
from qa_toolkit.ui.components.tool_page_shell import render_tool_empty_state, render_tool_page_hero, render_tool_tips


SAMPLE_REQUIREMENT = """用户可在 App 端新增收货地址，并支持将地址设为默认地址。
新增地址时姓名、手机号、省市区、详细地址为必填项，手机号需校验格式。
一个用户只能有一个默认地址；如果新增地址时勾选默认地址，原默认地址自动取消。
保存成功后返回地址列表页并立即展示最新地址。
当接口超时、服务异常或字段校验失败时，需要给出明确提示。
本次不覆盖批量导入地址。"""

PRESET_GROUPS = {
    "免费示范": "适合第一次试用和给用户做开箱演示。",
    "均衡": "兼顾速度、成本和稳定性，适合日常生成。",
    "旗舰": "优先模型上限和生成质量，适合复杂需求。",
    "推理": "更偏复杂规则、边界和深度分析场景。",
}

MODEL_PRESETS = {
    "glm_free_demo": {
        "label": "智谱 GLM-4.7-Flash | 免费示范",
        "provider": "智谱 AI",
        "platform": "glm",
        "group": "免费示范",
        "summary": "官方模型概览标注为免费模型，适合作为默认示范。中文任务稳定，接入成本低。",
        "cost": "免费模型",
        "state_updates": {
            "tcg_platform": "glm",
            "tcg_glm_model_version": "glm-4.7-flash",
            "tcg_glm_api_base": "https://open.bigmodel.cn/api/paas/v4",
        },
    },
    "qwen_flash": {
        "label": "阿里通义 Qwen-Flash | 性价比",
        "provider": "阿里云百炼",
        "platform": "ali",
        "group": "均衡",
        "summary": "Qwen3 系列里的低成本入口，适合快速生成与批量试用。",
        "cost": "新客常见有免费额度",
        "state_updates": {
            "tcg_platform": "ali",
            "tcg_ali_model_version": "qwen-flash",
        },
    },
    "qwen3_max": {
        "label": "阿里通义 Qwen3-Max | 旗舰",
        "provider": "阿里云百炼",
        "platform": "ali",
        "group": "旗舰",
        "summary": "当前旗舰强模型，复杂需求梳理和长上下文任务更稳。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "ali",
            "tcg_ali_model_version": "qwen3-max",
        },
    },
    "deepseek_chat": {
        "label": "DeepSeek-V3.2 Chat | 通用强项",
        "provider": "DeepSeek",
        "platform": "openai",
        "group": "均衡",
        "summary": "官方兼容 OpenAI 接口，适合通用测试用例生成和日常需求拆解。",
        "cost": "低成本商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "deepseek-chat",
            "tcg_openai_api_base": "https://api.deepseek.com/v1",
        },
    },
    "deepseek_reasoner": {
        "label": "DeepSeek-V3.2 Reasoner | 深度推理",
        "provider": "DeepSeek",
        "platform": "openai",
        "group": "推理",
        "summary": "适合复杂规则、边界和推理链更长的需求，但响应会更慢一些。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "deepseek-reasoner",
            "tcg_openai_api_base": "https://api.deepseek.com/v1",
        },
    },
    "kimi_k25": {
        "label": "Kimi K2.5 | 新版主力",
        "provider": "Moonshot AI",
        "platform": "openai",
        "group": "旗舰",
        "summary": "官方最新主力模型，适合长上下文、Agent 风格任务和复杂需求整理。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "kimi-k2.5",
            "tcg_openai_api_base": "https://api.moonshot.cn/v1",
        },
    },
    "kimi_k2_thinking": {
        "label": "Kimi K2 Thinking | 推理版",
        "provider": "Moonshot AI",
        "platform": "openai",
        "group": "推理",
        "summary": "更偏深度思考和复杂任务拆解，适合高约束场景。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "kimi-k2-thinking",
            "tcg_openai_api_base": "https://api.moonshot.cn/v1",
        },
    },
    "doubao_20_lite": {
        "label": "豆包 Doubao-Seed-2.0-Lite | 均衡",
        "provider": "火山引擎",
        "platform": "openai",
        "group": "均衡",
        "summary": "豆包 2.0 系列的均衡版本，适合普通业务需求生成和低成本试用。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "doubao-seed-2-0-lite-260215",
            "tcg_openai_api_base": "https://operator.las.cn-beijing.volces.com/api/v1",
        },
    },
    "openai_gpt54": {
        "label": "OpenAI GPT-5.4 | 旗舰",
        "provider": "OpenAI",
        "platform": "openai",
        "group": "旗舰",
        "summary": "OpenAI 官方当前旗舰模型，适合复杂需求理解、测试设计和高质量生成。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "gpt-5.4",
            "tcg_openai_api_base": "https://api.openai.com/v1",
        },
    },
    "openai_gpt54_mini": {
        "label": "OpenAI GPT-5.4 mini | 均衡",
        "provider": "OpenAI",
        "platform": "openai",
        "group": "均衡",
        "summary": "OpenAI 官方主推 mini 模型，适合低延迟和日常批量生成。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "gpt-5.4-mini",
            "tcg_openai_api_base": "https://api.openai.com/v1",
        },
    },
    "anthropic_claude_sonnet4": {
        "label": "Anthropic Claude Sonnet 4 | 均衡旗舰",
        "provider": "Anthropic",
        "platform": "anthropic",
        "group": "均衡",
        "summary": "Claude 当前高性能均衡模型，适合复杂业务场景、长文需求和质量优先生成。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "anthropic",
            "tcg_anthropic_model_version": "claude-sonnet-4-20250514",
            "tcg_anthropic_api_base": "https://api.anthropic.com/v1/messages",
        },
    },
    "anthropic_claude_opus41": {
        "label": "Anthropic Claude Opus 4.1 | 最强档",
        "provider": "Anthropic",
        "platform": "anthropic",
        "group": "旗舰",
        "summary": "Anthropic 当前最强模型，适合高复杂度需求拆解和更强推理场景。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "anthropic",
            "tcg_anthropic_model_version": "claude-opus-4-1-20250805",
            "tcg_anthropic_api_base": "https://api.anthropic.com/v1/messages",
        },
    },
    "gemini_25_flash": {
        "label": "Google Gemini 2.5 Flash | 兼容网关",
        "provider": "Google",
        "platform": "openai",
        "group": "均衡",
        "summary": "Gemini 官方支持 OpenAI 兼容调用，适合高性价比快速生成。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "gemini-2.5-flash",
            "tcg_openai_api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        },
    },
    "gemini_25_pro": {
        "label": "Google Gemini 2.5 Pro | 高质量",
        "provider": "Google",
        "platform": "openai",
        "group": "旗舰",
        "summary": "Gemini 高阶模型，适合长上下文、复杂推理和结构化输出场景。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "gemini-2.5-pro",
            "tcg_openai_api_base": "https://generativelanguage.googleapis.com/v1beta/openai",
        },
    },
    "xai_grok_fast": {
        "label": "xAI Grok 4.1 Fast | 快速生成",
        "provider": "xAI",
        "platform": "openai",
        "group": "均衡",
        "summary": "xAI 官方 OpenAI 兼容接口，适合快速生成和较低成本试用。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "grok-4-1-fast-non-reasoning",
            "tcg_openai_api_base": "https://api.x.ai/v1",
        },
    },
    "mistral_large": {
        "label": "Mistral Large | 通用旗舰",
        "provider": "Mistral AI",
        "platform": "openai",
        "group": "旗舰",
        "summary": "Mistral 官方聊天接口兼容当前请求格式，适合国际化文本和多语言生成。",
        "cost": "商业计费",
        "state_updates": {
            "tcg_platform": "openai",
            "tcg_openai_model_version": "mistral-large-latest",
            "tcg_openai_api_base": "https://api.mistral.ai/v1",
        },
    },
}

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
    "tcg_platform": "glm",
    "tcg_provider_preset": "glm_free_demo",
    "tcg_provider_group": "免费示范",
    "tcg_provider_group_picker": "免费示范",
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
    "tcg_ali_model_version": "qwen-flash",
    "tcg_openai_api_key": "",
    "tcg_openai_model_version": "gpt-5.4-mini",
    "tcg_openai_api_base": "",
    "tcg_anthropic_api_key": "",
    "tcg_anthropic_model_version": "claude-sonnet-4-20250514",
    "tcg_anthropic_api_base": "https://api.anthropic.com/v1/messages",
    "tcg_baidu_api_key": "",
    "tcg_baidu_secret_key": "",
    "tcg_spark_api_key": "",
    "tcg_spark_api_base": "http://maas-api.cn-huabei-1.xf-yun.com/v1",
    "tcg_spark_model_id": "",
    "tcg_glm_api_key": "",
    "tcg_glm_model_version": "glm-4.7-flash",
    "tcg_glm_api_base": "https://open.bigmodel.cn/api/paas/v4",
    "tcg_use_demo_glm_key": False,
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


def _get_model_preset_catalog() -> Dict[str, Dict[str, Any]]:
    return MODEL_PRESETS


def _get_preset_ids_by_group(group_name: str) -> List[str]:
    return [
        preset_id
        for preset_id, preset in MODEL_PRESETS.items()
        if preset.get("group", "均衡") == group_name
    ]


def _get_demo_glm_api_key() -> str:
    for key_name in ("TCG_DEMO_GLM_API_KEY", "QA_TOOLKIT_DEMO_GLM_API_KEY"):
        secret_value = ""
        try:
            secret_value = str(st.secrets.get(key_name, "")).strip()
        except Exception:
            secret_value = ""
        if secret_value:
            return secret_value

        env_value = os.getenv(key_name, "").strip()
        if env_value:
            return env_value
    return ""


def _apply_model_preset(preset_id: str) -> Dict[str, Any]:
    preset = MODEL_PRESETS[preset_id]
    st.session_state.tcg_provider_preset = preset_id
    st.session_state.tcg_provider_group = preset.get("group", "均衡")
    if preset_id == "glm_free_demo" and _get_demo_glm_api_key():
        st.session_state.tcg_use_demo_glm_key = True
    elif preset.get("platform") != "glm":
        st.session_state.tcg_use_demo_glm_key = False
    for key, value in preset["state_updates"].items():
        st.session_state[key] = value
    return preset


def _render_model_preset_panel() -> Dict[str, Any]:
    presets = _get_model_preset_catalog()
    free_demo_preset_id = "glm_free_demo"
    demo_key_available = bool(_get_demo_glm_api_key())
    if st.session_state.tcg_provider_preset not in presets:
        st.session_state.tcg_provider_preset = free_demo_preset_id

    st.markdown("### 免费体验示范")
    demo_col1, demo_col2 = st.columns([2.4, 1])
    with demo_col1:
        feedback_renderer = render_success_feedback if demo_key_available else render_info_feedback
        feedback_renderer(
            (
                f"推荐模型: {presets[free_demo_preset_id]['label']}\n"
                f"提供方: {presets[free_demo_preset_id]['provider']}\n"
                f"适合场景: {presets[free_demo_preset_id]['summary']}\n"
                f"费用特征: {presets[free_demo_preset_id]['cost']}\n"
                + (
                    "当前部署端已配置服务端体验 Key，用户可以免填 API Key 直接体验。"
                    if demo_key_available
                    else "当前部署端还没有配置体验 Key；如果在 st.secrets 或环境变量里配置 TCG_DEMO_GLM_API_KEY，就能给用户免填 Key 体验。"
                )
            ),
            title="默认免费示范",
        )
    with demo_col2:
        st.caption("")
        if secondary_action_button("套用免费示范", key="tcg_apply_free_demo_preset"):
            preset = _apply_model_preset(free_demo_preset_id)
            render_success_feedback(
                f"已套用 {preset['label']}，下方平台、模型和 Base URL 已自动回填。",
                title="示范已生效",
            )

    st.markdown("### 主流模型快捷预设")
    if st.session_state.tcg_provider_group_picker not in PRESET_GROUPS:
        st.session_state.tcg_provider_group_picker = "免费示范"

    selected_group = st.radio(
        "预设分组",
        list(PRESET_GROUPS.keys()),
        key="tcg_provider_group_picker",
        horizontal=True,
    )
    st.caption(PRESET_GROUPS[selected_group])
    group_presets = _get_preset_ids_by_group(selected_group)
    picker_key = f"tcg_provider_preset_picker_{selected_group}"
    selected_preset = st.selectbox(
        "选择主流模型",
        group_presets,
        format_func=lambda key: presets[key]["label"],
        key=picker_key,
    )
    active_preset = presets[selected_preset]
    if secondary_action_button("套用所选预设", key="tcg_apply_selected_preset"):
        preset = _apply_model_preset(selected_preset)
        render_success_feedback(
            f"已套用 {preset['label']}，下方平台、模型和 Base URL 已自动回填。",
            title="预设已生效",
        )

    render_info_feedback(
        (
            f"提供方: {active_preset['provider']}\n"
            f"适合场景: {active_preset['summary']}\n"
            f"费用特征: {active_preset['cost']}\n"
            "说明: 预设只帮你填好平台、模型和地址，API Key 仍需使用你自己的账号。"
        ),
        title="当前选中预设",
    )
    return active_preset


def _resolve_effective_api_config(platform: str, api_config: Dict[str, Any]) -> Dict[str, Any]:
    effective_config = dict(api_config)
    if platform == "glm" and st.session_state.tcg_use_demo_glm_key:
        demo_key = _get_demo_glm_api_key()
        if demo_key:
            effective_config["api_key"] = demo_key
    return effective_config


def _render_api_config(platform: str, active_preset: Dict[str, Any] | None = None) -> Dict[str, Any]:
    st.markdown("### API 配置")

    if platform == "ali":
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("阿里 API Key", key="tcg_ali_api_key", type="password")
        with col2:
            st.text_input("模型名称", key="tcg_ali_model_version")
        st.caption("推荐模型: qwen-flash、qwen-plus、qwen-max、qwen3-max。")
        return {
            "api_key": st.session_state.tcg_ali_api_key,
            "model_version": st.session_state.tcg_ali_model_version,
        }

    if platform == "openai":
        provider_label = active_preset["provider"] if active_preset and active_preset.get("platform") == "openai" else "兼容网关"
        col1, col2 = st.columns(2)
        with col1:
            st.text_input(f"{provider_label} API Key", key="tcg_openai_api_key", type="password")
        with col2:
            st.text_input("模型名称", key="tcg_openai_model_version")
        st.text_input(
            "兼容 Base URL（可选）",
            key="tcg_openai_api_base",
            placeholder="留空默认使用 https://api.openai.com/v1",
        )
        st.caption("这一栏也支持 OpenAI、DeepSeek、Kimi、Gemini、Grok、Mistral、豆包等兼容网关。")
        return {
            "api_key": st.session_state.tcg_openai_api_key,
            "model_version": st.session_state.tcg_openai_model_version,
            "api_base": st.session_state.tcg_openai_api_base,
        }

    if platform == "anthropic":
        col1, col2 = st.columns(2)
        with col1:
            st.text_input("Anthropic API Key", key="tcg_anthropic_api_key", type="password")
        with col2:
            st.text_input("模型名称", key="tcg_anthropic_model_version")
        st.text_input(
            "Messages API 地址",
            key="tcg_anthropic_api_base",
            placeholder="留空默认使用 https://api.anthropic.com/v1/messages",
        )
        st.caption("Claude 走 Anthropic 原生 Messages API，不走 OpenAI 兼容层。")
        return {
            "api_key": st.session_state.tcg_anthropic_api_key,
            "model_version": st.session_state.tcg_anthropic_model_version,
            "api_base": st.session_state.tcg_anthropic_api_base,
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
        st.text_input(
            "智谱 API Key",
            key="tcg_glm_api_key",
            type="password",
            disabled=st.session_state.tcg_use_demo_glm_key and bool(_get_demo_glm_api_key()),
        )
    with col2:
        st.text_input("模型名称", key="tcg_glm_model_version")
    st.text_input("兼容 Base URL", key="tcg_glm_api_base")
    if _get_demo_glm_api_key():
        st.checkbox("使用内置体验 Key", key="tcg_use_demo_glm_key")
        if st.session_state.tcg_use_demo_glm_key:
            render_success_feedback("当前已启用服务端体验 Key，用户无需手填 API Key。", title="体验模式")
    st.caption("当前按 OpenAI 兼容协议调用，默认示范已预置为官方免费模型 glm-4.7-flash。")
    return {
        "api_key": st.session_state.tcg_glm_api_key,
        "model_version": st.session_state.tcg_glm_model_version,
        "api_base": st.session_state.tcg_glm_api_base,
    }


def _validate_api_config(platform: str, api_config: Dict[str, Any]) -> str:
    required_fields = {
        "ali": ["api_key"],
        "openai": ["api_key"],
        "anthropic": ["api_key", "model_version"],
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

    render_info_feedback(analysis["summary"] or "当前暂无可展示的需求摘要。", title="需求摘要")

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
        render_info_feedback("当前过滤条件下没有匹配的测试用例。", title="筛选结果为空")
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
        action_download_button(
            "导出 Excel",
            data=export_buffers["excel"],
            file_name=f"test_cases_{timestamp}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
    with export_col2:
        action_download_button(
            "导出 CSV",
            data=export_buffers["csv"],
            file_name=f"test_cases_{timestamp}.csv",
            mime="text/csv",
        )
    with export_col3:
        action_download_button(
            "导出 JSON",
            data=export_buffers["json"],
            file_name=f"test_cases_{timestamp}.json",
            mime="application/json",
        )
    with export_col4:
        action_download_button(
            "导出 Markdown",
            data=export_buffers["markdown"],
            file_name=f"test_cases_{timestamp}.md",
            mime="text/markdown",
        )


def render_test_case_generator_page() -> None:
    _ensure_defaults()
    generator = TestCaseGenerator()

    show_doc("test_case_generator")
    render_tool_page_hero(
        "🧪",
        "AI 测试用例生成器",
        "把需求原文、OCR 补充、业务规则和验收标准整理成模型更易理解的上下文，再输出可筛选、可导出的测试用例结果。",
        tags=["多模型", "OCR 补充", "本地需求分析", "Excel / CSV / JSON / Markdown"],
        accent="#be185d",
    )
    render_tool_tips(
        "推荐流程",
        [
            "先做“需求梳理”，确认功能点、业务规则和待澄清项，再开始生成。",
            "需求越结构化，生成质量越稳定，建议把模块、约束和验收标准补充完整。",
            "生成后先按优先级和关键词过滤，再导出到测试管理系统或评审材料里。",
        ],
    )

    top_col1, top_col2, top_col3 = st.columns([1, 1, 3])
    with top_col1:
        if secondary_action_button("载入示例", key="tcg_load_example"):
            _load_example_requirement()
            st.rerun()
    with top_col2:
        if secondary_action_button("清空输入", key="tcg_clear_input"):
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
                render_success_feedback(ocr_status["message"], title="OCR 状态")
            else:
                render_info_feedback(ocr_status["message"], title="OCR 状态")

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
            if primary_action_button("开始 OCR 识别", key="tcg_run_ocr"):
                if uploaded_image is None:
                    render_warning_feedback("请先上传一张需求截图或原型图。")
                elif not generator.is_ocr_available():
                    render_warning_feedback("当前环境 OCR 不可用，暂时无法识别图片文字。")
                else:
                    try:
                        ocr_text = generator.extract_text_from_image(
                            uploaded_image.getvalue(),
                            lang=generator.get_ocr_language_options()[st.session_state.tcg_ocr_language_label],
                            preprocess_mode=st.session_state.tcg_ocr_preprocess_mode,
                        )
                        st.session_state.tcg_ocr_text = ocr_text
                        render_success_feedback("图片文字识别完成，识别结果已自动回填到补充文本区域。")
                    except Exception as exc:
                        render_error_feedback(f"OCR 识别失败: {exc}")

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
            if primary_action_button("开始需求梳理", key="tcg_analyze_requirement"):
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
        active_preset = _render_model_preset_panel()
        platforms = generator.get_supported_platforms()
        st.selectbox(
            "模型平台",
            list(platforms.keys()),
            format_func=lambda key: platforms[key],
            key="tcg_platform",
        )
        api_config = _render_api_config(st.session_state.tcg_platform, active_preset)
        effective_api_config = _resolve_effective_api_config(st.session_state.tcg_platform, api_config)

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

        if primary_action_button("开始生成测试用例", key="tcg_generate_cases"):
            composed_requirement = _compose_requirement(generator)
            st.session_state.tcg_composed_requirement = composed_requirement
            st.session_state.tcg_generation_error = ""

            if not composed_requirement.strip():
                render_warning_feedback("请先输入需求内容，再开始生成测试用例。")
            else:
                validation_error = _validate_api_config(st.session_state.tcg_platform, effective_api_config)
                if validation_error:
                    render_warning_feedback(validation_error, title="配置不完整")
                else:
                    try:
                        with st.spinner("正在调用模型生成测试用例..."):
                            cases = generator.generate_testcases(
                                requirement=composed_requirement,
                                platform=st.session_state.tcg_platform,
                                api_config=effective_api_config,
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
                        render_success_feedback(f"测试用例生成完成，本次共输出 {len(cases)} 条结果。")
                    except Exception as exc:
                        st.session_state.tcg_generated_cases = None
                        st.session_state.tcg_generation_error = str(exc)
                        render_error_feedback(f"生成失败: {exc}")

        if st.session_state.tcg_generation_error:
            render_error_feedback(st.session_state.tcg_generation_error)

        if st.session_state.tcg_history:
            with st.expander("最近生成记录", expanded=False):
                for index, item in enumerate(st.session_state.tcg_history):
                    title = f"{item['timestamp']} | {item['platform']} | {len(item['cases'])} 条"
                    history_col1, history_col2 = st.columns([4, 1])
                    with history_col1:
                        st.write(title)
                    with history_col2:
                        if secondary_action_button("回填结果", key=f"tcg_history_apply_{index}"):
                            st.session_state.tcg_requirement_text = item["requirement"]
                            st.session_state.tcg_composed_requirement = item["requirement"]
                            st.session_state.tcg_generated_cases = item["cases"]
                            st.rerun()

    with result_tab:
        if not st.session_state.tcg_generated_cases:
            render_tool_empty_state(
                "等待生成结果",
                "完成需求分析并执行生成后，这里会展示可筛选的测试用例列表和多格式导出按钮。",
            )
        else:
            _render_generation_results(generator)
