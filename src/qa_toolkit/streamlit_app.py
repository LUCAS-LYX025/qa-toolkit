from PIL import Image
from importlib import import_module
import io
import html
import json
import os
import random
import re
import time
import urllib.parse
import base64
import binascii
import codecs
import datetime
import hashlib
import hmac
import traceback
import zipfile
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import uuid
from collections import Counter
from datetime import timedelta

from Crypto.Cipher import AES, DES, DES3
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from qa_toolkit.config.constants import PROVINCES, COUNTRIES, CATEGORIES, PROVINCE_MAP, TO_SECONDS, RANDOM_STRING_TYPES, \
    PASSWORD_OPTIONS, DOMAINS_PRESET, GENDERS, TOOL_CATEGORIES, CSS_STYLES, HEADLINE_STYLES, PRESET_SIZES
from qa_toolkit.config.constants import PROVINCE_CITY_AREA_CODES
from qa_toolkit.config.constants import PLATFORM_MAPPING
from qa_toolkit.config.constants import STYLE_PREVIEWS
from qa_toolkit.config.constants import LANGUAGE_DESCRIPTIONS
from qa_toolkit.config.constants import SIMPLE_EXAMPLE, MEDIUM_EXAMPLE, COMPLEX_EXAMPLE
from qa_toolkit.config.tool_icon_assets import build_tool_icon_badge
from qa_toolkit.config.tool_routes import INLINE_TOOL_CATEGORIES, PAGE_TOOL_CONFIG, PLACEHOLDER_DOC_MAPPING
from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.bi_analysis import BIAnalyzer
from qa_toolkit.core.data_generator_registry import get_dataset_scenarios, get_boundary_fields, get_locales, get_registry_summary
from qa_toolkit.core.i18n import t, th
from qa_toolkit.core.ui_i18n import install_streamlit_i18n
from qa_toolkit.tools.data_generator import DataGenerator
from qa_toolkit.tools.ip_lookup import IPQueryTool
from qa_toolkit.tools.test_case_generator import TestCaseGenerator
from qa_toolkit.ui.components.author_profile import AuthorProfile
from qa_toolkit.ui.components.feedback_panel import FeedbackSection
from qa_toolkit.ui.components.locale_switcher import render_locale_switcher
from qa_toolkit.utils.datetime_tools import DateTimeUtils

# 导入Faker库
try:
    from faker import Faker

    fake = Faker('zh_CN')
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    st.warning("Faker库未安装，部分高级功能将受限。请运行: pip install faker")

# 设置页面
st.set_page_config(
    page_title=t("测试工程师常用工具集"),
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)


def tool_label(tool_name: str) -> str:
    """工具名只作内部路由键，这里负责展示当前语言的名称。"""
    return t(tool_name)


def tool_description(tool_name: str) -> str:
    return t(TOOL_CATEGORIES[tool_name]["description"])


def localized_headline() -> str:
    """按当前语言替换首页主视觉文案，保留原 CSS 与触发按钮结构。"""
    from qa_toolkit.config.constants import HEADLINE_STYLES as _headline

    keys = (
        "围绕测试数据、日志、正则、文本、接口与质量分析的工程化工具台，",
        "从日常排查到专项分析，常用工具和辅助流程都集中在这里。",
        "把高频测试动作收进一个统一入口。",
        "测试工程师",
        "常用工具集",
        "正则与文本",
        "日志与 JSON",
        "接口与分析",
        "一站式入口",
        "工程化提效",
        "面向测试实战",
    )
    result = _headline
    for source in keys:
        translated = t(source)
        if translated != source:
            result = result.replace(source, translated)
    return result

# 现代化CSS样式
st.markdown(CSS_STYLES, unsafe_allow_html=True)


def _build_page_renderer(module_path, function_name, page_label):
    """延迟导入页面模块，避免单个页面缺失导致整站启动失败。"""

    def _render():
        try:
            render_fn = getattr(import_module(module_path), function_name)
        except Exception as exc:
            st.error(t("{name}加载失败，当前已跳过该页面。", name=page_label))
            if isinstance(exc, ModuleNotFoundError):
                st.info(
                    t("缺少模块: `{name}`。常见原因是新文件没有提交到 GitHub，", name=exc.name)
                    + t("或 `requirements.txt` 中缺少依赖。")
                )
            else:
                st.info(t("页面模块存在，但其内部导入或初始化失败。"))
            with st.expander(t("查看详细错误")):
                st.code("".join(traceback.format_exception(type(exc), exc, exc.__traceback__)))
            return

        render_fn()

    return _render


PAGE_RENDERERS = {
    tool_name: _build_page_renderer(
        module_path=config["module_path"],
        function_name=config["function_name"],
        page_label=config["page_label"],
    )
    for tool_name, config in PAGE_TOOL_CONFIG.items()
}

HERO_TOOL_QUERY_MAP = {
    "regex": "正则测试工具",
    "json": "JSON处理工具",
    "logs": "日志分析工具",
    "api": "接口自动化测试",
}


def render_tool_placeholder_page(tool_name):
    """未迁移完成的工具页兜底，避免点击菜单后出现空白页。"""
    doc_key = PLACEHOLDER_DOC_MAPPING.get(tool_name)
    if doc_key:
        show_doc(doc_key)

    st.warning(t("{name} 当前还在迁移到独立页面，已先恢复入口和说明展示。", name=tool_name))
    st.info(t("这个工具不再是空白页了；如果你要，我可以继续把它的完整功能也迁过来。"))


def clear_hero_tool_query():
    """清理首页主视觉节点留下的查询参数，避免和手动切换工具互相覆盖。"""
    st.session_state.pop("_last_hero_tool_query", None)
    try:
        query_params = st.query_params
        if "hero_tool" in query_params:
            del query_params["hero_tool"]
    except Exception:
        pass


def apply_hero_tool_query_selection():
    """读取首页主视觉节点的查询参数，并切换到对应工具。"""
    try:
        hero_tool = st.query_params.get("hero_tool", "")
    except Exception:
        return

    if isinstance(hero_tool, list):
        hero_tool = hero_tool[0] if hero_tool else ""

    hero_tool = str(hero_tool).strip().lower()
    if not hero_tool:
        return

    if st.session_state.get("_last_hero_tool_query") == hero_tool:
        return

    mapped_tool = HERO_TOOL_QUERY_MAP.get(hero_tool)
    st.session_state["_last_hero_tool_query"] = hero_tool
    if not mapped_tool:
        return

    st.session_state.selected_tool = mapped_tool
    st.session_state.tool_picker_compact = True


def apply_tool_query_selection():
    """读取工具卡片的查询参数，并切换到对应工具。"""
    try:
        tool_name = st.query_params.get("tool", "")
    except Exception:
        return

    if isinstance(tool_name, list):
        tool_name = tool_name[0] if tool_name else ""

    tool_name = urllib.parse.unquote_plus(str(tool_name).strip())
    if not tool_name:
        return

    if st.session_state.get("_last_tool_query") == tool_name:
        return

    st.session_state["_last_tool_query"] = tool_name
    if tool_name not in TOOL_CATEGORIES:
        return

    st.session_state.selected_tool = tool_name
    st.session_state.tool_picker_compact = True
    st.session_state.scroll_to_tool_workspace = True


def escape_js_string(text):
    """安全转义 JavaScript 字符串"""
    return json.dumps(text)


def create_copy_button(text, button_text=None, key=None):
    button_text = button_text or t("📋 复制到剪贴板")
    # 三处文案都用完整 JSON 字面量注入 JS：译文里若出现单引号也不会破坏脚本。
    _button_text_js = json.dumps(str(button_text), ensure_ascii=False)
    _copied_text = json.dumps(t("✅ 复制成功！"), ensure_ascii=False)
    _failed_text = json.dumps(t("❌ 复制失败"), ensure_ascii=False)
    """创建一键复制按钮"""
    if key is None:
        key = hash(text)

    escaped_text = escape_js_string(text)

    copy_script = f"""
    <script>
    function copyTextToClipboard{key}() {{
        const text = {escaped_text};
        if (!navigator.clipboard) {{
            return fallbackCopyTextToClipboard(text);
        }}
        return navigator.clipboard.writeText(text).then(function() {{
            return true;
        }}, function(err) {{
            return fallbackCopyTextToClipboard(text);
        }});
    }}

    function fallbackCopyTextToClipboard(text) {{
        const textArea = document.createElement('textarea');
        textArea.value = text;
        textArea.style.position = 'fixed';
        textArea.style.top = '0';
        textArea.style.left = '0';
        textArea.style.opacity = '0';
        document.body.appendChild(textArea);
        textArea.focus();
        textArea.select();
        try {{
            const successful = document.execCommand('copy');
            document.body.removeChild(textArea);
            return successful;
        }} catch (err) {{
            document.body.removeChild(textArea);
            return false;
        }}
    }}

    document.addEventListener('DOMContentLoaded', function() {{
        const button = document.querySelector('[data-copy-button="{key}"]');
        if (button) {{
            button.addEventListener('click', function() {{
                copyTextToClipboard{key}().then(function(success) {{
                    if (success) {{
                        const originalText = button.innerHTML;
                        button.innerHTML = {_copied_text};
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
                    }} else {{
                        button.innerHTML = {_failed_text};
                        button.style.background = 'linear-gradient(135deg, #b91c1c 0%, #dc2626 100%)';
                        button.style.color = '#ffffff';
                        button.style.fontWeight = '800';
                        button.style.textShadow = '0 1px 1px rgba(127,29,29,0.54)';
                        setTimeout(function() {{
                            button.innerHTML = {_button_text_js};
                            button.style.background = 'linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%)';
                            button.style.color = '#ffffff';
                            button.style.fontWeight = '700';
                            button.style.textShadow = '0 1px 1px rgba(7,20,39,0.34)';
                        }}, 2000);
                    }}
                }});
            }});
        }}
    }});
    </script>
    """

    button_html = f"""
    <div>
        <button data-copy-button="{key}"
                style="background:linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);color:white;border:1px solid rgba(250,204,21,0.22);padding:8px 16px;border-radius:12px;cursor:pointer;font-size:14px;margin:5px;font-weight:700;transition:all 0.3s ease;width:100%;height:42px;font-family:inherit;box-shadow:0 12px 22px rgba(7,20,39,0.26);">
            {html.escape(str(button_text))}
        </button>
    </div>
    """

    components.html(button_html + copy_script, height=60)


def render_back_to_top_button():
    """渲染固定在右下角的悬浮操作按钮。"""
    # 这段 HTML 内含大量 CSS 大括号，必须保持普通字符串，不能改成 f-string。
    # 多语言文案通过占位符注入；切勿直接写模板表达式，否则会原样渲染成源码。
    floating_html = """
        <style>
        .qa-toolkit-floating-shell {
            position: fixed;
            right: 24px;
            bottom: calc(24px + 56px);
            z-index: 999;
            opacity: 1;
            transform: translateY(0);
            transition: opacity 0.24s ease, transform 0.24s ease;
            pointer-events: auto;
        }
        .qa-toolkit-floating-shell.is-dimmed {
            opacity: 1;
            transform: translateY(0);
        }
        .qa-toolkit-floating-shell.is-hidden {
            opacity: 0;
            transform: translateY(12px);
            pointer-events: none;
        }
        .qa-toolkit-floating-menu {
            position: relative;
        }
        .qa-toolkit-floating-summary {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 128px;
            padding: 12px 18px;
            border-radius: 999px;
            color: #ffffff !important;
            text-decoration: none !important;
            font-size: 14px;
            font-weight: 700;
            cursor: pointer;
            user-select: none;
            list-style: none;
            background: linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
            border: 1px solid rgba(250, 204, 21, 0.22);
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.12),
                0 14px 30px rgba(7, 20, 39, 0.26);
            transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
        }
        .qa-toolkit-floating-summary::-webkit-details-marker {
            display: none;
        }
        .qa-toolkit-floating-summary:hover {
            transform: translateY(-2px);
            border-color: rgba(250, 204, 21, 0.30);
        }
        .qa-toolkit-floating-menu[open] .qa-toolkit-floating-summary {
            background: linear-gradient(135deg, #fff6d5 0%, #f5edd0 50%, #e7eef8 100%);
            color: #17324a !important;
            border-color: rgba(250, 204, 21, 0.24);
            box-shadow: 0 16px 34px rgba(250, 204, 21, 0.18);
        }
        .qa-toolkit-floating-items {
            position: absolute;
            right: 0;
            bottom: calc(100% + 12px);
            display: flex;
            flex-direction: column;
            gap: 10px;
            align-items: flex-end;
        }
        .qa-toolkit-floating-link {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 116px;
            padding: 11px 16px;
            border-radius: 999px;
            color: #ffffff !important;
            text-decoration: none !important;
            font-size: 14px;
            font-weight: 700;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            white-space: nowrap;
        }
        .qa-toolkit-feedback-link {
            background: linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
            border: 1px solid rgba(250, 204, 21, 0.22);
            box-shadow: 0 12px 28px rgba(7, 20, 39, 0.26);
        }
        .qa-toolkit-back-to-top {
            background: linear-gradient(135deg, #071427 0%, #13294b 62%, #224d79 100%);
            color: #ffffff !important;
            border: 1px solid rgba(250, 204, 21, 0.22);
            box-shadow:
                inset 0 1px 0 rgba(255,255,255,0.12),
                0 12px 24px rgba(7, 20, 39, 0.26);
        }
        .qa-toolkit-feedback-link:hover {
            box-shadow: 0 16px 32px rgba(7, 20, 39, 0.30);
        }
        .qa-toolkit-back-to-top:hover {
            box-shadow: 0 16px 32px rgba(7, 20, 39, 0.30);
        }
        .qa-toolkit-floating-link:active,
        .qa-toolkit-floating-summary:active,
        .qa-toolkit-back-to-top:active,
        .qa-toolkit-feedback-link:active {
            background: linear-gradient(135deg, #fff6d5 0%, #f5edd0 50%, #e7eef8 100%);
            color: #17324a !important;
            border-color: rgba(250, 204, 21, 0.24);
            box-shadow: 0 12px 24px rgba(250, 204, 21, 0.16);
        }
        @media (max-width: 768px) {
            .qa-toolkit-floating-shell {
                right: 14px;
                bottom: calc(14px + 52px);
            }
            .qa-toolkit-floating-items {
                gap: 8px;
                bottom: calc(100% + 10px);
            }
            .qa-toolkit-floating-summary {
                min-width: 118px;
                padding: 11px 16px;
                font-size: 13px;
            }
            .qa-toolkit-floating-link {
                min-width: 102px;
                padding: 10px 14px;
                font-size: 13px;
            }
        }
        </style>
        <div class="qa-toolkit-floating-shell">
            <details class="qa-toolkit-floating-menu">
                <summary class="qa-toolkit-floating-summary">__QA_QUICK_ACTIONS__</summary>
                <div class="qa-toolkit-floating-items">
                    <a class="qa-toolkit-floating-link qa-toolkit-feedback-link" href="#tool-feedback-anchor">__QA_FEEDBACK__</a>
                    <a class="qa-toolkit-floating-link qa-toolkit-back-to-top" href="#page-top">__QA_BACK_TO_TOP__</a>
                </div>
            </details>
        </div>
        """
    floating_html = (
        floating_html.replace("__QA_QUICK_ACTIONS__", th("⚡ 快捷操作"))
        .replace("__QA_FEEDBACK__", th("💬 意见反馈"))
        .replace("__QA_BACK_TO_TOP__", th("↑ 返回顶部"))
    )
    st.markdown(floating_html, unsafe_allow_html=True)
    components.html(
        """
        <script>
        (function() {
            const THRESHOLD_SHOW = 220;
            const THRESHOLD_DIM = 80;
            let lastScrollTop = 0;

            function getShell() {
                try {
                    return window.parent.document.querySelector('.qa-toolkit-floating-shell');
                } catch (error) {
                    return null;
                }
            }

            function getMenu() {
                try {
                    return window.parent.document.querySelector('.qa-toolkit-floating-menu');
                } catch (error) {
                    return null;
                }
            }

            function getScrollTop() {
                try {
                    const doc = window.parent.document.documentElement;
                    const body = window.parent.document.body;
                    return (doc && doc.scrollTop) || (body && body.scrollTop) || 0;
                } catch (error) {
                    return 0;
                }
            }

            function updateFloatingActions() {
                const shell = getShell();
                if (!shell) {
                    return;
                }
                const scrollTop = getScrollTop();
                const delta = scrollTop - lastScrollTop;
                shell.classList.remove('is-hidden', 'is-dimmed');

                if (scrollTop < THRESHOLD_DIM) {
                    shell.classList.add('is-dimmed');
                    lastScrollTop = scrollTop;
                    return;
                }
                if (scrollTop < THRESHOLD_SHOW) {
                    shell.classList.add('is-hidden');
                    lastScrollTop = scrollTop;
                    return;
                }

                if (delta > 6) {
                    shell.classList.remove('is-hidden', 'is-dimmed');
                } else if (delta < -6) {
                    shell.classList.add('is-dimmed');
                }

                lastScrollTop = scrollTop;
            }

            function bindMenuLinks() {
                try {
                    const menu = getMenu();
                    if (!menu) {
                        return;
                    }
                    menu.querySelectorAll('a').forEach((link) => {
                        link.addEventListener('click', function() {
                            menu.removeAttribute('open');
                        });
                    });
                } catch (error) {
                    // ignore
                }
            }

            function bindScrollListener() {
                try {
                    const targetWindow = window.parent;
                    targetWindow.removeEventListener('scroll', updateFloatingActions);
                    targetWindow.addEventListener('scroll', updateFloatingActions, { passive: true });
                    updateFloatingActions();
                } catch (error) {
                    // 保持默认可见，避免脚本能力异常时按钮消失。
                }
            }

            bindScrollListener();
            bindMenuLinks();
            setTimeout(updateFloatingActions, 120);
            setTimeout(updateFloatingActions, 600);
        })();
        </script>
        """,
        height=0,
    )


def render_tool_workspace_scroll_handler():
    """切换工具后自动滚动到功能区。"""
    if not st.session_state.get("scroll_to_tool_workspace"):
        return

    components.html(
        """
        <script>
        (function() {
            const targetId = "tool-workspace-anchor";

            function scrollToTarget() {
                try {
                    const parentWindow = window.parent;
                    const target = parentWindow.document.getElementById(targetId);
                    if (!target) {
                        return;
                    }

                    target.scrollIntoView({ behavior: "smooth", block: "start" });
                } catch (error) {
                    // ignore
                }
            }

            setTimeout(scrollToTarget, 60);
            setTimeout(scrollToTarget, 240);
        })();
        </script>
        """,
        height=0,
    )
    st.session_state.scroll_to_tool_workspace = False


def render_tool_card_click_bridge():
    """将工具卡片和首页主视觉节点点击桥接到隐藏的 Streamlit 按钮。"""
    components.html(
        """
        <script>
        (function() {
            try {
                const hostWindow = window.parent;
                const doc = hostWindow.document;
                if (hostWindow.__qaToolkitToolCardBridgeInstalled) {
                    return;
                }
                hostWindow.__qaToolkitToolCardBridgeInstalled = true;

                const selector = '.tool-picker-linklike[data-trigger-key], .qa-app-hero__node[data-trigger-key]';
                const findTrigger = (target) => {
                    if (!(target instanceof hostWindow.Element)) {
                        return null;
                    }
                    return target.closest(selector);
                };
                const resolveTriggerButton = (trigger) => {
                    if (!trigger) {
                        return null;
                    }
                    const triggerKey = trigger.getAttribute('data-trigger-key');
                    if (!triggerKey) {
                        return null;
                    }
                    return doc.querySelector(`.st-key-${triggerKey} button`);
                };
                const activateTrigger = (event, trigger) => {
                    if (trigger.dataset.bridgePending === '1') {
                        return;
                    }
                    event.preventDefault();
                    event.stopPropagation();
                    trigger.dataset.bridgePending = '1';
                    let attempts = 0;
                    const clickWhenReady = () => {
                        const button = resolveTriggerButton(trigger);
                        if (button) {
                            delete trigger.dataset.bridgePending;
                            button.click();
                            return;
                        }
                        // 隐藏按钮随 Streamlit rerun 重建；短重试避免点击被渲染时序吞掉。
                        if (attempts++ < 20) {
                            setTimeout(clickWhenReady, 60);
                        } else {
                            delete trigger.dataset.bridgePending;
                        }
                    };
                    clickWhenReady();
                };

                doc.addEventListener('click', (event) => {
                    const trigger = findTrigger(event.target);
                    if (!trigger) {
                        return;
                    }
                    activateTrigger(event, trigger);
                });

                doc.addEventListener('keydown', (event) => {
                    if (event.key !== 'Enter' && event.key !== ' ') {
                        return;
                    }
                    const trigger = findTrigger(event.target);
                    if (!trigger) {
                        return;
                    }
                    activateTrigger(event, trigger);
                });
            } catch (error) {
                // ignore
            }
        })();
        </script>
        """,
        height=0,
    )


def render_hero_tool_triggers():
    """渲染首页主视觉节点的隐藏触发按钮。"""
    hero_tool_actions = [
        ("hero_tool_trigger_regex", "正则测试工具"),
        ("hero_tool_trigger_json", "JSON处理工具"),
        ("hero_tool_trigger_logs", "日志分析工具"),
        ("hero_tool_trigger_api", "接口自动化测试"),
    ]

    for trigger_key, tool_name in hero_tool_actions:
        if st.button(t("切换到{name}", name=tool_label(tool_name)), key=trigger_key, use_container_width=True):
            clear_hero_tool_query()
            st.session_state.selected_tool = tool_name
            st.session_state.tool_picker_compact = True
            st.session_state.scroll_to_tool_workspace = True
            st.rerun()


def render_tool_picker():
    """渲染工具切换器。收起时优先展示功能区，展开时展示完整工具列表。"""
    current_tool = st.session_state.selected_tool
    current_info = TOOL_CATEGORIES[current_tool]
    accent_color = current_info.get("color", "#667eea")
    current_tool_icon = build_tool_icon_badge(current_tool, accent_color, variant="banner")
    banner_background = f"linear-gradient(135deg, {accent_color} 0%, #0f172a 100%)"
    st.markdown(
        f"""
        <div style="
            background: {banner_background};
            border-radius: 18px;
            padding: 16px 18px;
            color: #ffffff;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.14);
            margin-bottom: 8px;
        ">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px;">
                {current_tool_icon}
                <div style="font-size:20px;font-weight:800;">{th(tool_label(current_tool))}</div>
                <div style="
                    margin-left:auto;
                    background: rgba(255,255,255,0.18);
                    border: 1px solid rgba(255,255,255,0.22);
                    border-radius: 999px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 700;
                ">
                    {th(t('功能区模式' if st.session_state.tool_picker_compact else '工具切换模式'))}
                </div>
            </div>
            <div style="font-size:14px;line-height:1.7;color:rgba(255,255,255,0.92);">
                {th(tool_description(current_tool))}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_col1, action_col2 = st.columns([1, 1])
    with action_col1:
        primary_label = t("展开工具列表" if st.session_state.tool_picker_compact else "收起工具列表")
        if st.button(primary_label, key="toggle_tool_picker", use_container_width=True):
            st.session_state.tool_picker_compact = not st.session_state.tool_picker_compact
            st.rerun()
    with action_col2:
        if st.button(t("仅看当前功能区"), key="focus_current_tool", use_container_width=True):
            st.session_state.tool_picker_compact = True
            st.rerun()

    if st.session_state.tool_picker_compact:
        st.caption(t("当前已优先展示功能区。如需切换模块，点击“展开工具列表”。"))
        st.markdown("---")
        return

    st.markdown(f'<div class="sub-header">{th(t("🚀 可用工具"))}</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    col_index = 0

    for category, info in TOOL_CATEGORIES.items():
        with cols[col_index]:
            is_selected = current_tool == category
            card_class = "tool-picker-card selected" if is_selected else "tool-picker-card"
            accent_color = info.get("color", "#667eea")
            trigger_key = f"tool_picker_card_trigger_{col_index}_{abs(hash(category))}"
            status_class = "tool-picker-status selected" if is_selected else "tool-picker-status"
            status_text = t("当前已选中，点击卡片定位到功能区" if is_selected else "点击卡片进入功能区")
            tool_icon_markup = build_tool_icon_badge(category, accent_color)
            st.markdown(
                f"""
                <div class="tool-picker-linklike" data-trigger-key="{trigger_key}" role="button" tabindex="0" aria-label="{th(t("切换到{name}", name=tool_label(category)))}">
                    <div class="{card_class}">
                        <div class="tool-picker-icon">{tool_icon_markup}</div>
                        <div class="tool-picker-title">{th(tool_label(category))}</div>
                        <div class="tool-picker-desc">{th(tool_description(category))}</div>
                    </div>
                </div>
                <div class="{status_class}">{status_text}</div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(t("切换到{name}", name=tool_label(category)), key=trigger_key, use_container_width=True):
                clear_hero_tool_query()
                st.session_state.selected_tool = category
                st.session_state.tool_picker_compact = True
                st.session_state.scroll_to_tool_workspace = True
                st.rerun()

        col_index = (col_index + 1) % 3

    st.markdown("---")


def display_generated_results(title, content, filename_prefix):
    """统一展示生成结果 + 复制 + 下载"""
    st.markdown(f'<div class="category-card">{th(t("📋 生成结果 - {title}", title=title))}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-box">{html.escape(str(content))}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        create_copy_button(content, button_text=t("📋 复制结果"), key=f"copy_{filename_prefix}")
    with col2:
        st.download_button(
            label=t("💾 下载结果"),
            data=content,
            file_name=f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )


def display_structured_results(title, records, filename_prefix):
    """统一展示结构化结果，支持预览和多格式导出。"""
    if not records:
        st.warning(t("暂无可展示的数据。"))
        return

    dataframe = pd.DataFrame(records)
    json_text = json.dumps(records, ensure_ascii=False, indent=2)
    csv_bytes = dataframe.to_csv(index=False).encode("utf-8-sig")

    st.markdown(f'<div class="category-card">{th(t("🗂️ 结构化结果 - {title}", title=title))}</div>', unsafe_allow_html=True)
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric(t("记录数"), len(dataframe))
    with metric_col2:
        st.metric(t("字段数"), len(dataframe.columns))
    with metric_col3:
        st.metric(t("导出格式"), "CSV / JSON")

    preview_tab, json_tab = st.tabs([t("表格预览"), t("JSON 预览")])
    with preview_tab:
        st.dataframe(dataframe, use_container_width=True, hide_index=True)
        st.caption(t("字段覆盖: {fields}", fields=", ".join(dataframe.columns.tolist())))
    with json_tab:
        st.code(json_text, language="json")

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        create_copy_button(json_text, button_text=t("📋 复制 JSON"), key=f"copy_json_{filename_prefix}")
    with action_col2:
        st.download_button(
            label=t("💾 下载 CSV"),
            data=csv_bytes,
            file_name=f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    with action_col3:
        st.download_button(
            label=t("🧾 下载 JSON"),
            data=json_text.encode("utf-8"),
            file_name=f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


# 初始化session state
if 'selected_tool' not in st.session_state:
    st.session_state.selected_tool = "数据生成工具"
if 'tool_picker_compact' not in st.session_state:
    st.session_state.tool_picker_compact = False
if 'scroll_to_tool_workspace' not in st.session_state:
    st.session_state.scroll_to_tool_workspace = False
if st.session_state.selected_tool not in TOOL_CATEGORIES:
    st.session_state.selected_tool = "数据生成工具"
    st.session_state.tool_picker_compact = False
apply_hero_tool_query_selection()
apply_tool_query_selection()

# 顶部标题区域（语言切换必须先于任何依赖语言的渲染）
install_streamlit_i18n()
render_locale_switcher()
st.markdown(localized_headline(), unsafe_allow_html=True)
render_hero_tool_triggers()
render_tool_card_click_bridge()
st.markdown('<div id="page-top"></div>', unsafe_allow_html=True)
render_back_to_top_button()

tool_category = st.session_state.selected_tool

st.markdown('<div id="tool-content-anchor"></div>', unsafe_allow_html=True)
render_tool_picker()
author = AuthorProfile()
author.render_sidebar_compact_profile()
feedback_section = FeedbackSection()
st.markdown('<div id="tool-workspace-anchor"></div>', unsafe_allow_html=True)
render_tool_workspace_scroll_handler()

# === 工具功能实现 ===
if tool_category == "数据生成工具":
    show_doc("data_generator")
    locales = get_locales()
    locale_key = st.selectbox(
        t("生成地区"), list(locales),
        format_func=lambda key: locales[key].label,
        key="data_gen_locale",
        help=t("切换地区后，Faker 生成的姓名、地址等数据会按当地规则生成。"),
    )
    generator = DataGenerator(locale=locales[locale_key].faker_locale)
    registry_summary = get_registry_summary()
    st.caption(
        t("注册式扩展：{scenarios} 个造数场景 / {fields} 个边界字段 / {locales} 个地区",
          scenarios=len(registry_summary['造数场景']),
          fields=len(registry_summary['边界字段']),
          locales=len(registry_summary['生成地区']))
        + (t("含 {count} 项外部扩展",
             count=registry_summary['扩展场景数'] + registry_summary['扩展字段数'])
           if registry_summary['扩展场景数'] + registry_summary['扩展字段数'] else "")
    )
    if 'clear_data_gen_counter' not in st.session_state:
        st.session_state.clear_data_gen_counter = 0

    gen_mode = st.radio(
        t("选择生成模式"),
        ["Faker高级生成器", "基础数据生成器"],
        format_func=t,
        horizontal=True
    )

    if gen_mode == "Faker高级生成器":
        if not FAKER_AVAILABLE:
            st.error(t("❌ Faker库未安装，无法使用高级生成器"))
            st.info(t("请运行以下命令安装: `pip install faker`"))
            st.code("pip install faker", language="bash")
        else:
            st.markdown(f'<div class="category-card">{th(t("🚀 Faker高级数据生成器"))}</div>', unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                selected_category = st.selectbox(t("选择数据类别"), list(CATEGORIES.keys()), format_func=t)
            with col2:
                selected_subcategory = st.selectbox(t("选择具体类型"), CATEGORIES[selected_category], format_func=t)
            with col3:
                count = st.number_input(t("生成数量"), min_value=1, max_value=100, value=5)
            with col4:
                st.write("")  # 占位符
                st.write("")
                if st.button(t("🗑️ 清空"), key="clear_faker", use_container_width=True):
                    if 'faker_result' in st.session_state:
                        del st.session_state.faker_result
                    if 'last_category' in st.session_state:
                        del st.session_state.last_category
                    # 确保计数器存在
                    if 'clear_data_gen_counter' not in st.session_state:
                        st.session_state.clear_data_gen_counter = 0
                    st.session_state.clear_data_gen_counter += 1
                    st.rerun()

            extra_params = {}
            if selected_subcategory == "随机文本":
                text_length = st.slider(t("文本长度"), min_value=10, max_value=1000, value=200)
                extra_params['length'] = text_length
            faker_seed_text = st.text_input(
                t("随机种子"), value="", placeholder=t("留空则每次生成不同"),
                help=t("填写整数后，同一组参数可复现同一批 Faker 数据。"),
                key="faker_seed",
            )
            faker_seed = None
            if faker_seed_text.strip():
                try:
                    faker_seed = int(faker_seed_text.strip())
                except ValueError:
                    st.warning(t("随机种子需为整数，当前已忽略。"))
            if faker_seed is not None:
                extra_params['seed'] = faker_seed

            current_faker_key = f"{locale_key}|{selected_category}|{selected_subcategory}|{faker_seed}|{extra_params.get('length')}"
            if st.session_state.get("faker_result_key") != current_faker_key:
                st.session_state.pop("faker_result", None)
                st.session_state.pop("last_category", None)
                st.session_state.faker_result_key = current_faker_key

            if st.button(t("🎯 生成数据"), use_container_width=True):
                with st.spinner(t("正在生成数据...")):
                    results = generator.safe_generate(generator.generate_faker_data, selected_category,
                                                      selected_subcategory, count, **extra_params)
                    if results is not None:
                        result_text = "\n".join([str(r) for r in results])
                        st.session_state.faker_result = result_text
                        st.session_state.last_category = f"{selected_category} - {selected_subcategory}"

            if 'faker_result' in st.session_state:
                title = st.session_state.get("last_category", "")
                if title.endswith("完整个人信息"):
                    st.text_area(t("生成结果"), st.session_state.faker_result, height=300, key="profile_result")
                else:
                    st.markdown(
                        f'<div class="result-box">{html.escape(str(st.session_state.faker_result))}</div>',
                        unsafe_allow_html=True,
                    )
                create_copy_button(st.session_state.faker_result, button_text=t("📋 复制结果"), key="copy_faker_result")
                st.download_button(
                    label=t("💾 下载结果"),
                    data=st.session_state.faker_result,
                    file_name=f"faker_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

    else:  # 基础数据生成器
        st.markdown(f'<div class="category-card">{th(t("🔧 基础数据生成器"))}</div>', unsafe_allow_html=True)
        data_gen_tool = st.radio(
            t("选择生成工具"),
            ["随机内容生成器", "随机邮箱生成器", "电话号码生成器", "随机地址生成器", "随机身份证生成器",
             "测试场景造数", "边界值/异常值生成器"],
            format_func=t,
        )
        st.caption(t("前 5 项适合快速单字段造数，后 2 项适合测试联调、批量导入和边界值设计。"))

        if data_gen_tool == "随机内容生成器":
            st.markdown(f'<div class="category-card">🎲 {th(t("随机内容生成器"))}</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                gen_type = st.selectbox(t("生成类型"), ["随机字符串", "随机数字", "随机密码", "UUID"], format_func=t)

                if gen_type in ["随机字符串", "随机密码"]:
                    length = st.slider(t("长度"), 1, 100, 10, help=t("生成内容的长度（字符数）"))
                if gen_type == "随机数字":
                    min_val = st.number_input(t("最小值"), value=0)
                    max_val = st.number_input(t("最大值"), value=100)

                count = st.number_input(t("生成数量"), min_value=1, max_value=100, value=5)

            with col2:
                if gen_type == "随机字符串":
                    chars_type = st.multiselect(t("字符类型"), RANDOM_STRING_TYPES, default=RANDOM_STRING_TYPES[:3],
                                                help=t("选择包含的字符类型"), format_func=t)
                if gen_type == "随机密码":
                    password_options = st.multiselect(t("密码选项"), PASSWORD_OPTIONS, default=PASSWORD_OPTIONS[:3],
                                                      help=t("设置密码复杂度要求"), format_func=t)

                st.write(t("📋 条件说明"))
                if gen_type == "随机字符串":
                    st.write(t("- 类型: {value}", value=t(gen_type)))
                    st.write(t("- 长度: {value}字符", value=length))
                    st.write(t("- 字符类型: {value}", value=", ".join(t(item) for item in chars_type)))
                elif gen_type == "随机数字":
                    st.write(t("- 类型: {value}", value=t(gen_type)))
                    st.write(t("- 范围: {min} 到 {max}", min=min_val, max=max_val))
                elif gen_type == "随机密码":
                    st.write(t("- 类型: {value}", value=t(gen_type)))
                    st.write(t("- 长度: {value}字符", value=length))
                    st.write(t("- 复杂度: {value}", value=", ".join(t(item) for item in password_options)))
                else:
                    st.write(t("- 类型: {value}", value=t(gen_type)))

                st.write(t("💡 提示: 点击生成按钮后结果将保留在页面"))

            if st.button(t("生成内容"), key="gen_random_content"):
                if gen_type == "随机数字" and min_val > max_val:
                    st.error(t("最小值（{min}）不能大于最大值（{max}）。", min=min_val, max=max_val))
                    st.stop()
                results = []
                with st.spinner(t("正在生成{count}个{name}...", count=count, name=t(gen_type))):
                    for _ in range(count):
                        if gen_type == "随机字符串":
                            res = generator.safe_generate(generator.generate_random_string, length, chars_type)
                        elif gen_type == "随机数字":
                            res = str(random.randint(min_val, max_val))
                        elif gen_type == "随机密码":
                            res = generator.safe_generate(generator.generate_random_password, length, password_options)
                        elif gen_type == "UUID":
                            res = str(uuid.uuid4())
                        if res is not None:
                            results.append(res)

                result_text = "\n".join(results)
                conditions = (
                        t("类型: {value}", value=t(gen_type)) + ", " +
                        (t("长度: {value}字符", value=length) + ", " if gen_type in ["随机字符串", "随机密码"] else "") +
                        (t("范围: {min}-{max}", min=min_val, max=max_val) + ", " if gen_type == "随机数字" else "") +
                        (t("字符类型: {value}", value=", ".join(t(item) for item in chars_type)) if gen_type == "随机字符串" else "") +
                        (t("复杂度: {value}", value=", ".join(t(item) for item in password_options)) if gen_type == "随机密码" else "")
                )
                display_generated_results(conditions, result_text, t("随机内容"))

        elif data_gen_tool == "随机邮箱生成器":
            st.markdown(f'<div class="category-card">{th(t("📧 随机邮箱生成器"))}</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                count = st.number_input(t("邮箱数量"), min_value=1, max_value=100, value=10)
                domain_option = st.selectbox(t("域名选项"), ["随机域名", "自定义域名"], format_func=t)

            with col2:
                if domain_option == "自定义域名":
                    custom_domain = st.text_input(t("自定义域名"), "example.com", placeholder=t("输入不带http://的域名"))
                    conditions = t("域名: {value}", value=custom_domain)
                else:
                    selected_domains = st.multiselect(t("选择域名"), DOMAINS_PRESET, default=DOMAINS_PRESET[:3])
                    conditions = t("随机域名: {value}", value=", ".join(selected_domains))
                st.write(t("💡 提示: 用户名将随机生成8-12位字母数字组合"))

            if st.button(t("生成邮箱"), key="gen_emails"):
                results = []
                with st.spinner(t("正在生成{count}个邮箱地址...", count=count)):
                    for _ in range(count):
                        email = generator.safe_generate(generator.generate_random_email, domain_option,
                                                        custom_domain if domain_option == "自定义域名" else None,
                                                        selected_domains if domain_option != "自定义域名" else None)
                        if email is not None:
                            results.append(email)

                result_text = "\n".join(results)
                display_generated_results(conditions, result_text, t("邮箱列表"))
        elif data_gen_tool == "电话号码生成器":
            st.markdown(f'<div class="category-card">{th(t("📞 电话号码生成器"))}</div>', unsafe_allow_html=True)
            # 确保PROVINCES是列表类型
            PROVINCES = list(PROVINCE_CITY_AREA_CODES.keys())


            def get_cities_by_province(province):
                """根据省份获取城市列表"""
                return list(PROVINCE_CITY_AREA_CODES.get(province, {}).keys())


            def get_area_code(province, city):
                """根据省份和城市获取区号"""
                return PROVINCE_CITY_AREA_CODES.get(province, {}).get(city, "")


            col1, col2 = st.columns(2)
            with col1:
                phone_type = st.selectbox(t("号码类型"), ["手机号", "座机", "国际号码"], format_func=t)

                # 初始化变量
                operator = None
                country = None
                province = None
                city = None
                area_code = None

                if phone_type == "国际号码":
                    country = st.selectbox(t("选择国家"), COUNTRIES)
                elif phone_type == "手机号":
                    operator = st.selectbox(t("运营商"), ["随机", "移动", "联通", "电信", "广电"], format_func=t)
                elif phone_type == "座机":
                    # 使用本地定义的 PROVINCES - 确保是列表
                    province_options = ["随机"] + PROVINCES
                    province = st.selectbox(t("选择省份"), province_options, format_func=t)

                    if province and province != "随机":
                        cities = get_cities_by_province(province)
                        city = st.selectbox(t("选择城市"), ["随机"] + cities, format_func=t)

                        # 如果选择了具体城市，获取对应的区号
                        if city and city != "随机":
                            area_code = get_area_code(province, city)
                            if area_code:
                                st.success(t("✅ 所选城市区号: {code}", code=area_code))
                            else:
                                st.warning(t("⚠️ 未找到该城市的区号"))
                    else:
                        city = "随机"
                        st.info(t("将随机生成区号"))

                count = st.number_input("生成数量", min_value=1, max_value=100, value=10)

            with col2:
                phone_type_label = t(phone_type)
                random_label = t("随机")
                if phone_type == "座机":
                    if province == "随机":
                        conditions = f"{t('类型: {value}', value=phone_type_label)}, {t('区号: {value}', value=random_label)}"
                    elif city == "随机":
                        conditions = (
                            f"{t('类型: {value}', value=phone_type_label)}, "
                            f"{t('省份: {value}', value=province)}, {t('区号: {value}', value=random_label)}"
                        )
                    else:
                        conditions = (
                            f"{t('类型: {value}', value=phone_type_label)}, "
                            f"{t('城市: {value}', value=city)}, {t('区号: {value}', value=area_code)}"
                        )
                elif phone_type == "国际号码":
                    conditions = f"{t('类型: {value}', value=phone_type_label)}, {t('国家: {value}', value=country)}"
                else:
                    conditions = f"{t('运营商: {value}', value=t(operator))}, {t('类型: {value}', value=phone_type_label)}"

                st.write(t("💡 提示: 生成的号码将匹配相应的号码规则"))

            if st.button(t("生成电话号码"), key="gen_conditional_phones"):
                results = []
                selected_area_codes = []  # 用于记录实际使用的区号

                with st.spinner(t("正在生成{count}个号码...", count=count)):
                    for i in range(count):
                        try:
                            if phone_type == "座机":
                                # 根据选择确定最终的区号
                                final_area_code = None

                                if province != "随机":
                                    if city != "随机" and area_code:
                                        # 使用具体城市的区号
                                        final_area_code = area_code
                                    else:
                                        # 随机选择该省份下的一个城市区号
                                        cities = get_cities_by_province(province)
                                        if cities:
                                            random_city = random.choice(cities)
                                            final_area_code = get_area_code(province, random_city)

                                # 记录实际使用的区号
                                if final_area_code:
                                    selected_area_codes.append(final_area_code)

                                # 调用生成函数
                                phone = generator.generate_landline_number(area_code=final_area_code)

                            elif phone_type == "国际号码":
                                phone = generator.generate_international_phone(country)
                            else:  # 手机号
                                phone = generator.generate_conditional_phone(operator)

                            if phone is not None:
                                results.append(phone)

                        except Exception as e:
                            # 处理可能的生成错误，继续生成其他号码
                            st.error(t("生成第 {index} 个号码时出错: {error}", index=i + 1, error=str(e)))
                            continue

                if results:
                    result_text = "\n".join(results)

                    # 删除原来的显示代码，直接使用封装的函数
                    display_generated_results(t("电话号码"), result_text, t("电话号码"))

                    # 显示调试信息（实际使用的区号）
                    if phone_type == "座机" and selected_area_codes:
                        unique_codes = list(set(selected_area_codes))
                        st.info(t("实际使用的区号: {codes}", codes=", ".join(unique_codes)))

                    # 显示生成统计
                    st.success(t("✅ 成功生成 {count} 个电话号码", count=len(results)))
                else:
                    st.warning(t("⚠️ 未能生成任何有效的电话号码，请检查参数设置"))

        elif data_gen_tool == "随机地址生成器":
            st.markdown(f'<div class="category-card">{th(t("🏠 随机地址生成器"))}</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                province = st.selectbox(t("选择省份"), ["随机"] + [p for p in PROVINCES.keys() if p != "随机"], format_func=t)
                count = st.number_input(t("生成数量"), min_value=1, max_value=50, value=10)
                detailed = st.checkbox(t("生成详细地址"), value=True)

            with col2:
                if province != "随机":
                    city_options = PROVINCES[province]
                    city = st.selectbox(t("选择城市"), ["随机"] + [c for c in city_options if c != province], format_func=t)
                else:
                    city = "随机"

                conditions = (
                        t("省份: {value}", value=t(province) if province != "随机" else t("随机选择")) + ", " +
                        t("城市: {value}", value=t(city) if city != "随机" else t("随机选择")) + ", " +
                        t("详细程度: {value}", value=t("详细地址" if detailed else "仅省市信息"))
                )
                st.write(t("💡 提示: 详细地址包含街道、门牌号等信息"))

            if st.button(t("生成地址"), key="gen_addresses"):
                results = []
                with st.spinner(t("正在生成{count}个地址...", count=count)):
                    for _ in range(count):
                        selected_province = province
                        if province == "随机":
                            selected_province = random.choice([p for p in PROVINCES.keys() if p != "随机"])

                        selected_city = city
                        if city == "随机":
                            if selected_province in PROVINCES:
                                city_options = [c for c in PROVINCES[selected_province] if c != selected_province]
                                selected_city = random.choice(city_options) if city_options else selected_province

                        addr = generator.safe_generate(generator.generate_random_address, selected_province,
                                                       selected_city, detailed)
                        if addr is not None:
                            results.append(addr)

                result_text = "\n".join(results)
                display_generated_results(conditions, result_text, t("地址列表"))

        elif data_gen_tool == "随机身份证生成器":
            st.markdown(f'<div class="category-card">{th(t("🆔 随机身份证生成器"))}</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                province = st.selectbox(t("选择省份"), ["随机"] + list(PROVINCE_MAP.keys()), format_func=t)
                gender = st.selectbox(t("选择性别"), GENDERS, format_func=t)
                count = st.number_input(t("生成数量"), min_value=1, max_value=100, value=10)

            with col2:
                min_age = st.number_input(t("最小年龄"), min_value=0, max_value=100, value=18)
                max_age = st.number_input(t("最大年龄"), min_value=0, max_value=100, value=60)
                if min_age > max_age:
                    st.error(t("最小年龄不能大于最大年龄"))
                    st.stop()

                conditions = (
                    f"{t('省份: {value}', value=t(province))}, "
                    f"{t('性别: {value}', value=t(gender))}, "
                    f"{t('年龄: {min}-{max}岁', min=min_age, max=max_age)}"
                )
                st.write(t("💡 提示: 生成的身份证将严格符合选择的省份、性别和年龄条件"))

            if st.button(t("生成身份证"), key="gen_id_cards"):
                results = []
                with st.spinner(t("正在生成{count}个身份证号码...", count=count)):
                    for _ in range(count):
                        id_card = generator.safe_generate(generator.generate_random_id_card,
                                                          province if province != "随机" else random.choice(
                                                              list(PROVINCE_MAP.keys())),
                                                          gender,
                                                          min_age,
                                                          max_age)
                        if id_card is not None:
                            results.append(id_card)

                result_text = "\n".join(results)
                display_generated_results(conditions, result_text, t("身份证列表"))

        elif data_gen_tool == "测试场景造数":
            st.markdown(f'<div class="category-card">{th(t("🧩 测试场景造数"))}</div>', unsafe_allow_html=True)
            scenario_templates = generator.get_test_data_scenarios()

            col1, col2 = st.columns([2, 1])
            with col1:
                selected_scenario = st.selectbox(t("选择造数场景"), list(scenario_templates.keys()), format_func=t)
                scenario_meta = scenario_templates[selected_scenario]
                st.info(t(scenario_meta["description"]))
                st.caption(t("字段覆盖: {fields}", fields=", ".join(t(field) for field in scenario_meta['fields'])))
                batch_tag = st.text_input(
                    t("批次标识"),
                    value=f"qa{datetime.datetime.now().strftime('%m%d')}",
                    help=t("会拼接进用户名、员工号、订单号等字段，便于批量清理和回溯。")
                )
                email_domain = st.text_input(
                    t("邮箱域名"),
                    value="example.com",
                    help=t("用于注册账号或员工档案中的邮箱字段。")
                )

            with col2:
                count = st.number_input("生成数量", min_value=1, max_value=200, value=10)
                scenario_seed_text = st.text_input(
                    t("随机种子"),
                    value="",
                    placeholder=t("留空则每次生成不同"),
                    help=t("填写整数后，同一参数组合可复现同一批数据。")
                )
                st.write(t("💡 使用建议"))
                st.write(t("- 联调环境建议填写批次标识"))
                st.write(t("- 回归场景建议补随机种子"))
                st.write(t("- 结果可直接下载 CSV/JSON"))

            scenario_seed = None
            if scenario_seed_text.strip():
                try:
                    scenario_seed = int(scenario_seed_text.strip())
                except ValueError:
                    st.warning(t("随机种子需为整数，当前已忽略。"))

            action_col1, action_col2 = st.columns([3, 1])
            with action_col1:
                if st.button(t("生成场景数据"), key="gen_scenario_dataset", use_container_width=True):
                    dataset = generator.safe_generate(
                        generator.generate_test_dataset,
                        selected_scenario,
                        count,
                        scenario_seed,
                        batch_tag,
                        email_domain,
                    )
                    if dataset is not None:
                        st.session_state.scenario_dataset_records = dataset
                        st.session_state.scenario_dataset_title = selected_scenario
            with action_col2:
                if st.button(t("清空结果"), key="clear_scenario_dataset", use_container_width=True):
                    st.session_state.pop("scenario_dataset_records", None)
                    st.session_state.pop("scenario_dataset_title", None)
                    st.rerun()

            if st.session_state.get("scenario_dataset_records"):
                display_structured_results(
                    t(st.session_state.get("scenario_dataset_title", "测试场景数据")),
                    st.session_state["scenario_dataset_records"],
                    "scenario_dataset"
                )

        elif data_gen_tool == "边界值/异常值生成器":
            st.markdown(f'<div class="category-card">{th(t("🧪 边界值/异常值生成器"))}</div>', unsafe_allow_html=True)
            boundary_templates = generator.get_boundary_field_templates()

            col1, col2 = st.columns([2, 1])
            with col1:
                selected_field_type = st.selectbox(t("选择字段类型"), list(boundary_templates.keys()), format_func=t)
                st.info(t(boundary_templates[selected_field_type]["description"]))
                case_types = st.multiselect(
                    t("包含用例类型"),
                    ["正常值", "边界值", "异常值"],
                    default=["正常值", "边界值", "异常值"],
                    help=t("可按需要只生成某类数据，便于接口联调或测试设计。"),
                    format_func=t,
                )

                min_length = 2
                max_length = 20
                amount_min = 0.00
                amount_max = 99999.99
                boundary_email_domain = "example.com"

                if selected_field_type in ["用户名", "密码"]:
                    length_col1, length_col2 = st.columns(2)
                    with length_col1:
                        min_length = st.number_input(t("最小长度"), min_value=1, max_value=128, value=2)
                    with length_col2:
                        max_length = st.number_input(t("最大长度"), min_value=min_length, max_value=256, value=20)

                if selected_field_type == "金额":
                    amount_col1, amount_col2 = st.columns(2)
                    with amount_col1:
                        amount_min = st.number_input(t("最小金额"), value=0.00, format="%.2f")
                    with amount_col2:
                        amount_max = st.number_input(t("最大金额"), min_value=float(amount_min), value=99999.99,
                                                     format="%.2f")

                if selected_field_type == "邮箱":
                    boundary_email_domain = st.text_input(t("邮箱域名"), value="example.com")

            with col2:
                boundary_seed_text = st.text_input(
                    t("随机种子"),
                    value="",
                    placeholder=t("留空则每次生成不同")
                )
                st.write(t("📌 适用场景"))
                st.write(t("- 表单校验测试"))
                st.write(t("- 接口参数边界值设计"))
                st.write(t("- 前后端联调异常值验证"))

            boundary_seed = None
            if boundary_seed_text.strip():
                try:
                    boundary_seed = int(boundary_seed_text.strip())
                except ValueError:
                    st.warning(t("随机种子需为整数，当前已忽略。"))

            action_col1, action_col2 = st.columns([3, 1])
            with action_col1:
                if st.button(t("生成边界值用例"), key="gen_boundary_cases", use_container_width=True):
                    cases = generator.safe_generate(
                        generator.generate_boundary_test_cases,
                        selected_field_type,
                        boundary_seed,
                        min_length,
                        max_length,
                        amount_min,
                        amount_max,
                        boundary_email_domain,
                        "正常值" in case_types,
                        "边界值" in case_types,
                        "异常值" in case_types,
                    )
                    if cases is not None:
                        st.session_state.boundary_case_records = cases
                        st.session_state.boundary_case_title = selected_field_type
            with action_col2:
                if st.button(t("清空结果"), key="clear_boundary_cases", use_container_width=True):
                    st.session_state.pop("boundary_case_records", None)
                    st.session_state.pop("boundary_case_title", None)
                    st.rerun()

            if st.session_state.get("boundary_case_records"):
                display_structured_results(
                    t("{name}边界值", name=t(st.session_state.get('boundary_case_title', '字段'))),
                    st.session_state["boundary_case_records"],
                    "boundary_cases"
                )

    st.markdown('</div>', unsafe_allow_html=True)

elif tool_category in PAGE_RENDERERS:
    PAGE_RENDERERS[tool_category]()
    if tool_category == "正则测试工具":
        st.markdown('</div>', unsafe_allow_html=True)

else:
    render_tool_placeholder_page(tool_category)

feedback_section.render_tool_feedback_bar(tool_category)
