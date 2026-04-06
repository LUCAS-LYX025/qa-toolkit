import sys
from pathlib import Path
from unittest.mock import patch

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.ui.pages.test_case_generator_page import (
    DEFAULT_STATE,
    MODEL_PRESETS,
    PRESET_GROUPS,
    _get_demo_glm_api_key,
    _get_preset_ids_by_group,
    _resolve_effective_api_config,
)


def test_glm_free_demo_preset_is_present_and_marked_as_default_example():
    preset = MODEL_PRESETS["glm_free_demo"]

    assert preset["platform"] == "glm"
    assert preset["group"] == "免费示范"
    assert preset["state_updates"]["tcg_glm_model_version"] == "glm-4.7-flash"
    assert "免费" in preset["label"]
    assert "免费" in preset["cost"]


def test_mainland_model_presets_cover_mainstream_openai_compatible_providers():
    expected_presets = {"deepseek_chat", "deepseek_reasoner", "kimi_k25", "kimi_k2_thinking", "doubao_20_lite"}

    assert expected_presets.issubset(MODEL_PRESETS.keys())
    assert MODEL_PRESETS["deepseek_chat"]["state_updates"]["tcg_openai_api_base"] == "https://api.deepseek.com/v1"
    assert MODEL_PRESETS["kimi_k25"]["state_updates"]["tcg_openai_api_base"] == "https://api.moonshot.cn/v1"
    assert MODEL_PRESETS["deepseek_reasoner"]["group"] == "推理"


def test_global_model_presets_cover_mainstream_overseas_providers():
    expected_presets = {
        "openai_gpt54",
        "openai_gpt54_mini",
        "anthropic_claude_sonnet4",
        "anthropic_claude_opus41",
        "gemini_25_flash",
        "gemini_25_pro",
        "xai_grok_fast",
        "mistral_large",
    }

    assert expected_presets.issubset(MODEL_PRESETS.keys())
    assert MODEL_PRESETS["anthropic_claude_sonnet4"]["platform"] == "anthropic"
    assert MODEL_PRESETS["gemini_25_flash"]["state_updates"]["tcg_openai_api_base"] == (
        "https://generativelanguage.googleapis.com/v1beta/openai"
    )
    assert MODEL_PRESETS["xai_grok_fast"]["state_updates"]["tcg_openai_api_base"] == "https://api.x.ai/v1"


def test_model_presets_all_have_supported_group_and_default_group_is_free_demo():
    assert DEFAULT_STATE["tcg_provider_group"] == "免费示范"
    assert DEFAULT_STATE["tcg_provider_group_picker"] == "免费示范"
    assert set(PRESET_GROUPS.keys()) == {"免费示范", "均衡", "旗舰", "推理"}
    assert all(preset["group"] in PRESET_GROUPS for preset in MODEL_PRESETS.values())


def test_get_preset_ids_by_group_returns_grouped_choices():
    assert _get_preset_ids_by_group("免费示范") == ["glm_free_demo"]
    assert "deepseek_chat" in _get_preset_ids_by_group("均衡")
    assert "qwen3_max" in _get_preset_ids_by_group("旗舰")
    assert "deepseek_reasoner" in _get_preset_ids_by_group("推理")


def test_demo_glm_api_key_can_be_loaded_from_environment():
    with patch.dict("os.environ", {"TCG_DEMO_GLM_API_KEY": "demo-key-123"}, clear=False):
        assert _get_demo_glm_api_key() == "demo-key-123"


def test_resolve_effective_api_config_uses_demo_key_when_enabled():
    st.session_state.tcg_use_demo_glm_key = True
    with patch.dict("os.environ", {"TCG_DEMO_GLM_API_KEY": "demo-key-456"}, clear=False):
        effective = _resolve_effective_api_config(
            "glm",
            {"api_key": "", "model_version": "glm-4.7-flash", "api_base": "https://open.bigmodel.cn/api/paas/v4"},
        )

    assert effective["api_key"] == "demo-key-456"
