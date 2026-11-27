from PIL import Image
from importlib import import_module
import io
import os
import re
import time
import urllib.parse
import base64
import binascii
import codecs
import hashlib
import hmac
import traceback
import zipfile
import streamlit as st
import streamlit.components.v1 as components
from collections import Counter
from datetime import timedelta

from Crypto.Cipher import AES, DES, DES3
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from qa_toolkit.config.constants import TOOL_CATEGORIES, CSS_STYLES, HEADLINE_STYLES, PRESET_SIZES
from qa_toolkit.config.constants import PLATFORM_MAPPING
from qa_toolkit.config.constants import STYLE_PREVIEWS
from qa_toolkit.config.constants import LANGUAGE_DESCRIPTIONS
from qa_toolkit.config.constants import SIMPLE_EXAMPLE, MEDIUM_EXAMPLE, COMPLEX_EXAMPLE
from qa_toolkit.config.tool_icon_assets import build_tool_icon_badge
from qa_toolkit.config.tool_routes import INLINE_TOOL_CATEGORIES, PAGE_TOOL_CONFIG, PLACEHOLDER_DOC_MAPPING
from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.bi_analysis import BIAnalyzer
from qa_toolkit.core.i18n import t, th
from qa_toolkit.core.ui_i18n import install_streamlit_i18n
from qa_toolkit.tools.ip_lookup import IPQueryTool
from qa_toolkit.tools.test_case_generator import TestCaseGenerator
from qa_toolkit.ui.components.author_profile import AuthorProfile
from qa_toolkit.ui.components.feedback_panel import FeedbackSection
from qa_toolkit.ui.components.locale_switcher import render_locale_switcher
from qa_toolkit.utils.datetime_tools import DateTimeUtils

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

if tool_category in PAGE_RENDERERS:
    PAGE_RENDERERS[tool_category]()
    if tool_category == "正则测试工具":
        st.markdown('</div>', unsafe_allow_html=True)

else:
    render_tool_placeholder_page(tool_category)

feedback_section.render_tool_feedback_bar(tool_category)
