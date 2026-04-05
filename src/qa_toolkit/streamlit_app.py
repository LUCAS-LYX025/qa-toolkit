from PIL import Image
import io
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
from qa_toolkit.config.constants import LANGUAGE_TEMPLATES
from qa_toolkit.config.constants import PREDEFINED_PATTERNS
from qa_toolkit.config.constants import PROVINCE_CITY_AREA_CODES
from qa_toolkit.config.constants import PLATFORM_MAPPING
from qa_toolkit.config.constants import STYLE_PREVIEWS
from qa_toolkit.config.constants import LANGUAGE_DESCRIPTIONS
from qa_toolkit.config.constants import SIMPLE_EXAMPLE, MEDIUM_EXAMPLE, COMPLEX_EXAMPLE
from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter
from qa_toolkit.support.documentation import show_doc, show_general_guidelines
from qa_toolkit.tools.bi_analysis import BIAnalyzer
from qa_toolkit.tools.data_generator import DataGenerator
from qa_toolkit.tools.ip_lookup import IPQueryTool
from qa_toolkit.tools.test_case_generator import TestCaseGenerator
from qa_toolkit.ui.components.author_profile import AuthorProfile
from qa_toolkit.ui.components.feedback_panel import FeedbackSection
from qa_toolkit.ui.pages.api_automation_page import render_api_automation_test_page
from qa_toolkit.ui.pages.api_dev_tools_page import render_api_dev_tools_page
from qa_toolkit.ui.pages.api_performance_page import render_api_performance_test_page
from qa_toolkit.ui.pages.api_security_page import render_api_security_test_page
from qa_toolkit.ui.pages.log_analysis_page import render_log_analysis_page
from qa_toolkit.ui.pages.text_comparison_page import render_text_comparison_page
from qa_toolkit.ui.pages.word_counter_page import render_word_counter_page
from qa_toolkit.utils.datetime_tools import DateTimeUtils
from qa_toolkit.utils.json_utils import JSONFileUtils

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
    page_title="测试工程师常用工具集",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 现代化CSS样式
st.markdown(CSS_STYLES, unsafe_allow_html=True)


def generate_regex_from_examples(text, examples):
    """根据示例文本生成正则表达式"""
    if not text or not examples:
        return ""

    example_list = [ex.strip() for ex in examples.split(",") if ex.strip()]

    if not example_list:
        return ""

    # 简化的模式识别逻辑
    common_pattern = example_list[0]

    for example in example_list[1:]:
        # 找出共同前缀
        i = 0
        while i < min(len(common_pattern), len(example)) and common_pattern[i] == example[i]:
            i += 1
        common_pattern = common_pattern[:i]

    if len(common_pattern) < 2:
        return re.escape(example_list[0])

    escaped_pattern = re.escape(common_pattern)

    # 简单的模式推断
    if len(example_list) > 1:
        if all(ex.replace(common_pattern, "").isdigit() for ex in example_list):
            return escaped_pattern + r"\d+"
        elif all(ex.replace(common_pattern, "").isalpha() for ex in example_list):
            return escaped_pattern + r"[A-Za-z]+"

    return escaped_pattern + ".*"


def escape_js_string(text):
    """安全转义 JavaScript 字符串"""
    return json.dumps(text)


def create_copy_button(text, button_text="📋 复制到剪贴板", key=None):
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
                        button.innerHTML = '✅ 复制成功！';
                        button.style.background = '#48bb78';
                        setTimeout(function() {{
                            button.innerHTML = originalText;
                            button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
                        }}, 2000);
                    }} else {{
                        button.innerHTML = '❌ 复制失败';
                        button.style.background = '#e53e3e';
                        setTimeout(function() {{
                            button.innerHTML = '{button_text}';
                            button.style.background = 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)';
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
                style="background:linear-gradient(135deg, #667eea 0%, #764ba2 100%);color:white;border:none;padding:8px 16px;border-radius:6px;cursor:pointer;font-size:14px;margin:5px;font-weight:500;transition:all 0.3s ease;width:100%;height:42px;font-family:inherit;box-shadow:0 2px 4px rgba(0,0,0,0.1);">
            {button_text}
        </button>
    </div>
    """

    components.html(button_html + copy_script, height=60)


def render_back_to_top_button():
    """渲染固定在右下角的返回顶部按钮"""
    st.markdown(
        """
        <style>
        .qa-toolkit-back-to-top {
            position: fixed;
            right: 24px;
            bottom: 24px;
            z-index: 999;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 116px;
            padding: 11px 16px;
            border-radius: 999px;
            background: linear-gradient(135deg, #1f4b99 0%, #0f766e 100%);
            color: #ffffff !important;
            text-decoration: none !important;
            font-size: 14px;
            font-weight: 700;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.22);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .qa-toolkit-back-to-top:hover {
            transform: translateY(-2px);
            box-shadow: 0 16px 32px rgba(15, 23, 42, 0.28);
        }
        </style>
        <a class="qa-toolkit-back-to-top" href="#page-top">↑ 返回顶部</a>
        """,
        unsafe_allow_html=True,
    )


def render_tool_picker():
    """渲染工具切换器。收起时优先展示功能区，展开时展示完整工具列表。"""
    current_tool = st.session_state.selected_tool
    current_info = TOOL_CATEGORIES[current_tool]
    accent_color = current_info.get("color", "#667eea")
    banner_background = f"linear-gradient(135deg, {accent_color} 0%, #0f172a 100%)"
    st.markdown(
        f"""
        <div style="
            background: {banner_background};
            border-radius: 18px;
            padding: 18px 20px;
            color: #ffffff;
            box-shadow: 0 14px 32px rgba(15, 23, 42, 0.14);
            margin-bottom: 12px;
        ">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;">
                <div style="font-size:26px;line-height:1;">{current_info['icon']}</div>
                <div style="font-size:20px;font-weight:800;">{current_tool}</div>
                <div style="
                    margin-left:auto;
                    background: rgba(255,255,255,0.18);
                    border: 1px solid rgba(255,255,255,0.22);
                    border-radius: 999px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 700;
                ">
                    {'功能区模式' if st.session_state.tool_picker_compact else '工具切换模式'}
                </div>
            </div>
            <div style="font-size:14px;line-height:1.7;color:rgba(255,255,255,0.92);">
                {current_info['description']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    action_col1, action_col2 = st.columns([1, 1])
    with action_col1:
        primary_label = "展开工具列表" if st.session_state.tool_picker_compact else "收起工具列表"
        if st.button(primary_label, key="toggle_tool_picker", use_container_width=True):
            st.session_state.tool_picker_compact = not st.session_state.tool_picker_compact
            st.rerun()
    with action_col2:
        if st.button("仅看当前功能区", key="focus_current_tool", use_container_width=True):
            st.session_state.tool_picker_compact = True
            st.rerun()

    if st.session_state.tool_picker_compact:
        st.caption("当前已优先展示功能区。如需切换模块，点击“展开工具列表”。")
        st.markdown("---")
        return

    st.markdown('<div class="sub-header">🚀 可用工具</div>', unsafe_allow_html=True)
    cols = st.columns(3)
    col_index = 0

    for category, info in TOOL_CATEGORIES.items():
        with cols[col_index]:
            is_selected = current_tool == category
            card_class = "tool-picker-card selected" if is_selected else "tool-picker-card"
            accent_color = info.get("color", "#667eea")
            card_style = f' style="border-color: {accent_color};"' if is_selected else ""
            active_button_style = (
                f' style="border-color: {accent_color}; box-shadow: inset 1px 1px 0 rgba(255,255,255,0.88), '
                f'inset -1px -1px 0 {accent_color};"'
            )
            st.markdown(
                f"""
                <div class="{card_class}"{card_style}>
                    <div class="tool-picker-icon" style="color: {accent_color};">{info['icon']}</div>
                    <div class="tool-picker-title">{category}</div>
                    <div class="tool-picker-desc">{info['description']}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            if is_selected:
                st.markdown(
                    f'<div class="tool-picker-active-button"{active_button_style}>{info["icon"]} {category}</div>'
                    '<div class="tool-picker-status">当前已选中，可直接进入功能区</div>',
                    unsafe_allow_html=True,
                )

            button_label = "进入当前工具" if is_selected else f"{info['icon']} {category}"
            if st.button(button_label, key=f"select_{category}", use_container_width=True):
                st.session_state.selected_tool = category
                st.session_state.tool_picker_compact = True
                st.rerun()

            if not is_selected:
                st.markdown('<div class="tool-picker-status">单击进入工具</div>', unsafe_allow_html=True)

        col_index = (col_index + 1) % 3

    st.markdown("---")


def display_generated_results(title, content, filename_prefix):
    """统一展示生成结果 + 复制 + 下载"""
    st.markdown(f'<div class="category-card">📋 生成结果 - {title}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="result-box">{content}</div>', unsafe_allow_html=True)

    col1, col2 = st.columns(2)
    with col1:
        create_copy_button(content, button_text="📋 复制结果", key=f"copy_{filename_prefix}")
    with col2:
        st.download_button(
            label="💾 下载结果",
            data=content,
            file_name=f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain"
        )


def display_structured_results(title, records, filename_prefix):
    """统一展示结构化结果，支持预览和多格式导出。"""
    if not records:
        st.warning("暂无可展示的数据。")
        return

    dataframe = pd.DataFrame(records)
    json_text = json.dumps(records, ensure_ascii=False, indent=2)
    csv_bytes = dataframe.to_csv(index=False).encode("utf-8-sig")

    st.markdown(f'<div class="category-card">🗂️ 结构化结果 - {title}</div>', unsafe_allow_html=True)
    metric_col1, metric_col2, metric_col3 = st.columns(3)
    with metric_col1:
        st.metric("记录数", len(dataframe))
    with metric_col2:
        st.metric("字段数", len(dataframe.columns))
    with metric_col3:
        st.metric("导出格式", "CSV / JSON")

    preview_tab, json_tab = st.tabs(["表格预览", "JSON 预览"])
    with preview_tab:
        st.dataframe(dataframe, use_container_width=True, hide_index=True)
        st.caption(f"字段覆盖: {', '.join(dataframe.columns.tolist())}")
    with json_tab:
        st.code(json_text, language="json")

    action_col1, action_col2, action_col3 = st.columns(3)
    with action_col1:
        create_copy_button(json_text, button_text="📋 复制 JSON", key=f"copy_json_{filename_prefix}")
    with action_col2:
        st.download_button(
            label="💾 下载 CSV",
            data=csv_bytes,
            file_name=f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    with action_col3:
        st.download_button(
            label="🧾 下载 JSON",
            data=json_text.encode("utf-8"),
            file_name=f"{filename_prefix}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )


# 初始化session state
if 'selected_tool' not in st.session_state:
    st.session_state.selected_tool = "数据生成工具"
if 'tool_picker_compact' not in st.session_state:
    st.session_state.tool_picker_compact = False
if st.session_state.selected_tool not in TOOL_CATEGORIES:
    st.session_state.selected_tool = "数据生成工具"
    st.session_state.tool_picker_compact = False

# 顶部标题区域
st.markdown(HEADLINE_STYLES, unsafe_allow_html=True)
st.markdown('<div id="page-top"></div>', unsafe_allow_html=True)
render_back_to_top_button()

tool_category = st.session_state.selected_tool

st.markdown('<div id="tool-content-anchor"></div>', unsafe_allow_html=True)
render_tool_picker()

# === 工具功能实现 ===
if tool_category == "数据生成工具":
    show_doc("data_generator")
    generator = DataGenerator()
    if 'clear_data_gen_counter' not in st.session_state:
        st.session_state.clear_data_gen_counter = 0

    gen_mode = st.radio(
        "选择生成模式",
        ["Faker高级生成器", "基础数据生成器"],
        horizontal=True
    )

    if gen_mode == "Faker高级生成器":
        if not FAKER_AVAILABLE:
            st.error("❌ Faker库未安装，无法使用高级生成器")
            st.info("请运行以下命令安装: `pip install faker`")
            st.code("pip install faker", language="bash")
        else:
            st.markdown('<div class="category-card">🚀 Faker高级数据生成器</div>', unsafe_allow_html=True)

            col1, col2, col3, col4 = st.columns([2, 2, 1, 1])
            with col1:
                selected_category = st.selectbox("选择数据类别", list(CATEGORIES.keys()))
            with col2:
                selected_subcategory = st.selectbox("选择具体类型", CATEGORIES[selected_category])
            with col3:
                count = st.number_input("生成数量", min_value=1, max_value=100, value=5)
            with col4:
                st.write("")  # 占位符
                st.write("")
                if st.button("🗑️ 清空", key="clear_faker", use_container_width=True):
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
                text_length = st.slider("文本长度", min_value=10, max_value=1000, value=200)
                extra_params['length'] = text_length

            if st.button("🎯 生成数据", use_container_width=True):
                with st.spinner("正在生成数据..."):
                    results = generator.safe_generate(generator.generate_faker_data, selected_category,
                                                      selected_subcategory, count, **extra_params)
                    if results is not None:
                        result_text = "\n".join([str(r) for r in results])
                        st.session_state.faker_result = result_text
                        st.session_state.last_category = f"{selected_category} - {selected_subcategory}"

            if 'faker_result' in st.session_state:
                title = st.session_state.get("last_category", "")
                if selected_subcategory == "完整个人信息":
                    st.text_area("生成结果", st.session_state.faker_result, height=300, key="profile_result")
                else:
                    st.markdown(f'<div class="result-box">{st.session_state.faker_result}</div>',
                                unsafe_allow_html=True)
                create_copy_button(st.session_state.faker_result, button_text="📋 复制结果", key="copy_faker_result")
                st.download_button(
                    label="💾 下载结果",
                    data=st.session_state.faker_result,
                    file_name=f"faker_data_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                    mime="text/plain"
                )

    else:  # 基础数据生成器
        st.markdown('<div class="category-card">🔧 基础数据生成器</div>', unsafe_allow_html=True)
        data_gen_tool = st.radio(
            "选择生成工具",
            ["随机内容生成器", "随机邮箱生成器", "电话号码生成器", "随机地址生成器", "随机身份证生成器",
             "测试场景造数", "边界值/异常值生成器"]
        )
        st.caption("前 5 项适合快速单字段造数，后 2 项适合测试联调、批量导入和边界值设计。")

        if data_gen_tool == "随机内容生成器":
            st.markdown('<div class="category-card">🎲 随机内容生成器</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                gen_type = st.selectbox("生成类型", ["随机字符串", "随机数字", "随机密码", "UUID"])

                if gen_type in ["随机字符串", "随机密码"]:
                    length = st.slider("长度", 1, 100, 10, help="生成内容的长度（字符数）")
                if gen_type == "随机数字":
                    min_val = st.number_input("最小值", value=0)
                    max_val = st.number_input("最大值", value=100)

                count = st.number_input("生成数量", min_value=1, max_value=100, value=5)

            with col2:
                if gen_type == "随机字符串":
                    chars_type = st.multiselect("字符类型", RANDOM_STRING_TYPES, default=RANDOM_STRING_TYPES[:3],
                                                help="选择包含的字符类型")
                if gen_type == "随机密码":
                    password_options = st.multiselect("密码选项", PASSWORD_OPTIONS, default=PASSWORD_OPTIONS[:3],
                                                      help="设置密码复杂度要求")

                st.write("📋 条件说明")
                if gen_type == "随机字符串":
                    st.write(f"- 类型: 随机字符串")
                    st.write(f"- 长度: {length}字符")
                    st.write(f"- 字符类型: {', '.join(chars_type)}")
                elif gen_type == "随机数字":
                    st.write(f"- 类型: 随机数字")
                    st.write(f"- 范围: {min_val} 到 {max_val}")
                elif gen_type == "随机密码":
                    st.write(f"- 类型: 随机密码")
                    st.write(f"- 长度: {length}字符")
                    st.write(f"- 复杂度: {', '.join(password_options)}")
                else:
                    st.write(f"- 类型: UUID")

                st.write("💡 提示: 点击生成按钮后结果将保留在页面")

            if st.button("生成内容", key="gen_random_content"):
                results = []
                with st.spinner(f"正在生成{count}个{gen_type}..."):
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
                        f"类型: {gen_type}, " +
                        (f"长度: {length}, " if gen_type in ["随机字符串", "随机密码"] else "") +
                        (f"范围: {min_val}-{max_val}, " if gen_type == "随机数字" else "") +
                        (f"字符类型: {', '.join(chars_type)}" if gen_type == "随机字符串" else "") +
                        (f"复杂度: {', '.join(password_options)}" if gen_type == "随机密码" else "")
                )
                display_generated_results(conditions, result_text, "随机内容")

        elif data_gen_tool == "随机邮箱生成器":
            st.markdown('<div class="category-card">📧 随机邮箱生成器</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                count = st.number_input("邮箱数量", min_value=1, max_value=100, value=10)
                domain_option = st.selectbox("域名选项", ["随机域名", "自定义域名"])

            with col2:
                if domain_option == "自定义域名":
                    custom_domain = st.text_input("自定义域名", "example.com", placeholder="输入不带http://的域名")
                    conditions = f"域名: {custom_domain}"
                else:
                    selected_domains = st.multiselect("选择域名", DOMAINS_PRESET, default=DOMAINS_PRESET[:3])
                    conditions = f"随机域名: {', '.join(selected_domains)}"
                st.write("💡 提示: 用户名将随机生成8-12位字母数字组合")

            if st.button("生成邮箱", key="gen_emails"):
                results = []
                with st.spinner(f"正在生成{count}个邮箱地址..."):
                    for _ in range(count):
                        email = generator.safe_generate(generator.generate_random_email, domain_option,
                                                        custom_domain if domain_option == "自定义域名" else None,
                                                        selected_domains if domain_option != "自定义域名" else None)
                        if email is not None:
                            results.append(email)

                result_text = "\n".join(results)
                display_generated_results(conditions, result_text, "邮箱列表")
        elif data_gen_tool == "电话号码生成器":
            st.markdown('<div class="category-card">📞 电话号码生成器</div>', unsafe_allow_html=True)
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
                phone_type = st.selectbox("号码类型", ["手机号", "座机", "国际号码"])

                # 初始化变量
                operator = None
                country = None
                province = None
                city = None
                area_code = None

                if phone_type == "国际号码":
                    country = st.selectbox("选择国家", COUNTRIES)
                elif phone_type == "手机号":
                    operator = st.selectbox("运营商", ["随机", "移动", "联通", "电信", "广电"])
                elif phone_type == "座机":
                    # 使用本地定义的 PROVINCES - 确保是列表
                    province_options = ["随机"] + PROVINCES
                    province = st.selectbox("选择省份", province_options)

                    if province and province != "随机":
                        cities = get_cities_by_province(province)
                        city = st.selectbox("选择城市", ["随机"] + cities)

                        # 如果选择了具体城市，获取对应的区号
                        if city and city != "随机":
                            area_code = get_area_code(province, city)
                            if area_code:
                                st.success(f"✅ 所选城市区号: {area_code}")
                            else:
                                st.warning("⚠️ 未找到该城市的区号")
                    else:
                        city = "随机"
                        st.info("将随机生成区号")

                count = st.number_input("生成数量", min_value=1, max_value=100, value=10)

            with col2:
                if phone_type == "座机":
                    if province == "随机":
                        conditions = f"类型: {phone_type}, 区号: 随机"
                    elif city == "随机":
                        conditions = f"类型: {phone_type}, 省份: {province}, 区号: 随机"
                    else:
                        conditions = f"类型: {phone_type}, 城市: {city}, 区号: {area_code}"
                elif phone_type == "国际号码":
                    conditions = f"类型: {phone_type}, 国家: {country}"
                else:
                    conditions = f"运营商: {operator}, 类型: {phone_type}"

                st.write("💡 提示: 生成的号码将匹配相应的号码规则")

            if st.button("生成电话号码", key="gen_conditional_phones"):
                results = []
                selected_area_codes = []  # 用于记录实际使用的区号

                with st.spinner(f"正在生成{count}个号码..."):
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
                            st.error(f"生成第 {i + 1} 个号码时出错: {str(e)}")
                            continue

                if results:
                    result_text = "\n".join(results)

                    # 删除原来的显示代码，直接使用封装的函数
                    display_generated_results("电话号码", result_text, "电话号码")

                    # 显示调试信息（实际使用的区号）
                    if phone_type == "座机" and selected_area_codes:
                        unique_codes = list(set(selected_area_codes))
                        st.info(f"实际使用的区号: {', '.join(unique_codes)}")

                    # 显示生成统计
                    st.success(f"✅ 成功生成 {len(results)} 个电话号码")
                else:
                    st.warning("⚠️ 未能生成任何有效的电话号码，请检查参数设置")

        elif data_gen_tool == "随机地址生成器":
            st.markdown('<div class="category-card">🏠 随机地址生成器</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                province = st.selectbox("选择省份", ["随机"] + [p for p in PROVINCES.keys() if p != "随机"])
                count = st.number_input("生成数量", min_value=1, max_value=50, value=10)
                detailed = st.checkbox("生成详细地址", value=True)

            with col2:
                if province != "随机":
                    city_options = PROVINCES[province]
                    city = st.selectbox("选择城市", ["随机"] + [c for c in city_options if c != province])
                else:
                    city = "随机"

                conditions = (
                        f"省份: {province if province != '随机' else '随机选择'}, " +
                        f"城市: {city if city != '随机' else '随机选择'}, " +
                        f"详细程度: {'详细地址' if detailed else '仅省市信息'}"
                )
                st.write("💡 提示: 详细地址包含街道、门牌号等信息")

            if st.button("生成地址", key="gen_addresses"):
                results = []
                with st.spinner(f"正在生成{count}个地址..."):
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
                display_generated_results(conditions, result_text, "地址列表")

        elif data_gen_tool == "随机身份证生成器":
            st.markdown('<div class="category-card">🆔 随机身份证生成器</div>', unsafe_allow_html=True)

            col1, col2 = st.columns(2)
            with col1:
                province = st.selectbox("选择省份", ["随机"] + list(PROVINCE_MAP.keys()))
                gender = st.selectbox("选择性别", GENDERS)
                count = st.number_input("生成数量", min_value=1, max_value=100, value=10)

            with col2:
                min_age = st.number_input("最小年龄", min_value=0, max_value=100, value=18)
                max_age = st.number_input("最大年龄", min_value=0, max_value=100, value=60)
                if min_age > max_age:
                    st.error("最小年龄不能大于最大年龄")

                conditions = f"省份: {province}, 性别: {gender}, 年龄: {min_age}-{max_age}岁"
                st.write("💡 提示: 生成的身份证将严格符合选择的省份、性别和年龄条件")

            if st.button("生成身份证", key="gen_id_cards"):
                results = []
                with st.spinner(f"正在生成{count}个身份证号码..."):
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
                display_generated_results(conditions, result_text, "身份证列表")

        elif data_gen_tool == "测试场景造数":
            st.markdown('<div class="category-card">🧩 测试场景造数</div>', unsafe_allow_html=True)
            scenario_templates = generator.get_test_data_scenarios()

            col1, col2 = st.columns([2, 1])
            with col1:
                selected_scenario = st.selectbox("选择造数场景", list(scenario_templates.keys()))
                scenario_meta = scenario_templates[selected_scenario]
                st.info(scenario_meta["description"])
                st.caption(f"字段覆盖: {', '.join(scenario_meta['fields'])}")
                batch_tag = st.text_input(
                    "批次标识",
                    value=f"qa{datetime.datetime.now().strftime('%m%d')}",
                    help="会拼接进用户名、员工号、订单号等字段，便于批量清理和回溯。"
                )
                email_domain = st.text_input(
                    "邮箱域名",
                    value="example.com",
                    help="用于注册账号或员工档案中的邮箱字段。"
                )

            with col2:
                count = st.number_input("生成数量", min_value=1, max_value=200, value=10)
                scenario_seed_text = st.text_input(
                    "随机种子",
                    value="",
                    placeholder="留空则每次生成不同",
                    help="填写整数后，同一参数组合可复现同一批数据。"
                )
                st.write("💡 使用建议")
                st.write("- 联调环境建议填写批次标识")
                st.write("- 回归场景建议补随机种子")
                st.write("- 结果可直接下载 CSV/JSON")

            scenario_seed = None
            if scenario_seed_text.strip():
                try:
                    scenario_seed = int(scenario_seed_text.strip())
                except ValueError:
                    st.warning("随机种子需为整数，当前已忽略。")

            action_col1, action_col2 = st.columns([3, 1])
            with action_col1:
                if st.button("生成场景数据", key="gen_scenario_dataset", use_container_width=True):
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
                if st.button("清空结果", key="clear_scenario_dataset", use_container_width=True):
                    st.session_state.pop("scenario_dataset_records", None)
                    st.session_state.pop("scenario_dataset_title", None)
                    st.rerun()

            if st.session_state.get("scenario_dataset_records"):
                display_structured_results(
                    st.session_state.get("scenario_dataset_title", "测试场景数据"),
                    st.session_state["scenario_dataset_records"],
                    "scenario_dataset"
                )

        elif data_gen_tool == "边界值/异常值生成器":
            st.markdown('<div class="category-card">🧪 边界值/异常值生成器</div>', unsafe_allow_html=True)
            boundary_templates = generator.get_boundary_field_templates()

            col1, col2 = st.columns([2, 1])
            with col1:
                selected_field_type = st.selectbox("选择字段类型", list(boundary_templates.keys()))
                st.info(boundary_templates[selected_field_type]["description"])
                case_types = st.multiselect(
                    "包含用例类型",
                    ["正常值", "边界值", "异常值"],
                    default=["正常值", "边界值", "异常值"],
                    help="可按需要只生成某类数据，便于接口联调或测试设计。"
                )

                min_length = 2
                max_length = 20
                amount_min = 0.00
                amount_max = 99999.99
                boundary_email_domain = "example.com"

                if selected_field_type in ["用户名", "密码"]:
                    length_col1, length_col2 = st.columns(2)
                    with length_col1:
                        min_length = st.number_input("最小长度", min_value=1, max_value=128, value=2)
                    with length_col2:
                        max_length = st.number_input("最大长度", min_value=min_length, max_value=256, value=20)

                if selected_field_type == "金额":
                    amount_col1, amount_col2 = st.columns(2)
                    with amount_col1:
                        amount_min = st.number_input("最小金额", value=0.00, format="%.2f")
                    with amount_col2:
                        amount_max = st.number_input("最大金额", min_value=float(amount_min), value=99999.99,
                                                     format="%.2f")

                if selected_field_type == "邮箱":
                    boundary_email_domain = st.text_input("邮箱域名", value="example.com")

            with col2:
                boundary_seed_text = st.text_input(
                    "随机种子",
                    value="",
                    placeholder="留空则每次生成不同"
                )
                st.write("📌 适用场景")
                st.write("- 表单校验测试")
                st.write("- 接口参数边界值设计")
                st.write("- 前后端联调异常值验证")

            boundary_seed = None
            if boundary_seed_text.strip():
                try:
                    boundary_seed = int(boundary_seed_text.strip())
                except ValueError:
                    st.warning("随机种子需为整数，当前已忽略。")

            action_col1, action_col2 = st.columns([3, 1])
            with action_col1:
                if st.button("生成边界值用例", key="gen_boundary_cases", use_container_width=True):
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
                if st.button("清空结果", key="clear_boundary_cases", use_container_width=True):
                    st.session_state.pop("boundary_case_records", None)
                    st.session_state.pop("boundary_case_title", None)
                    st.rerun()

            if st.session_state.get("boundary_case_records"):
                display_structured_results(
                    f"{st.session_state.get('boundary_case_title', '字段')}边界值",
                    st.session_state["boundary_case_records"],
                    "boundary_cases"
                )

    st.markdown('</div>', unsafe_allow_html=True)

# 字数统计工具
elif tool_category == "字数统计工具":
    render_word_counter_page()

# 文本对比工具
elif tool_category == "文本对比工具":
    render_text_comparison_page()

# 正则表达式测试工具
elif tool_category == "正则测试工具":
    show_doc("regex_tester")

    # 初始化session_state
    if 'regex_clear_counter' not in st.session_state:
        st.session_state.regex_clear_counter = 0

    # 添加工具选择选项卡
    tab1, tab2, tab3 = st.tabs(["正则表达式测试", "代码生成器", "从示例生成"])

    with tab1:
        col1, col2 = st.columns(2)
        with col1:
            # 预定义模式选择
            st.markdown("**选择预定义模式**")
            selected_pattern = st.selectbox("", ["自定义"] + list(PREDEFINED_PATTERNS.keys()), key="pattern_select")

            # 使用不同的key策略来避免session_state冲突
            if selected_pattern != "自定义":
                regex_pattern = PREDEFINED_PATTERNS[selected_pattern]
                st.code(f"当前模式: {regex_pattern}")
                # 同时允许用户修改预定义模式
                custom_regex = st.text_input("或自定义正则表达式", value=regex_pattern, placeholder="可在此修改表达式",
                                             key=f"custom_regex_input_{st.session_state.regex_clear_counter}")
                if custom_regex != regex_pattern:
                    regex_pattern = custom_regex
            else:
                regex_pattern = st.text_input("正则表达式", placeholder="例如: ^[a-zA-Z0-9]+$",
                                              key=f"manual_regex_input_{st.session_state.regex_clear_counter}")

            test_text = st.text_area("测试文本", height=200, placeholder="在此输入要测试的文本...",
                                     key=f"test_text_area_{st.session_state.regex_clear_counter}")

        with col2:
            st.markdown("**匹配选项**")
            global_match = st.checkbox("全局匹配 (g)", value=True, key="global_match_check")
            ignore_case = st.checkbox("忽略大小写 (i)", key="ignore_case_check")
            multiline = st.checkbox("多行模式 (m)", key="multiline_check")
            dotall = st.checkbox("点号匹配换行 (s)", key="dotall_check")

            st.markdown("**替换功能**")
            replace_text = st.text_input("替换文本", placeholder="输入替换文本（可选）",
                                         key=f"replace_text_input_{st.session_state.regex_clear_counter}")

        button_col1, button_col2 = st.columns(2)
        with button_col1:
            if st.button("测试正则表达式", use_container_width=True, key="test_regex"):
                # 获取当前输入框的值
                current_regex = ""
                if selected_pattern != "自定义":
                    current_regex = custom_regex
                else:
                    current_regex = regex_pattern

                current_test_text = test_text

                if current_regex and current_test_text:
                    try:
                        flags = 0
                        if ignore_case:
                            flags |= re.IGNORECASE
                        if multiline:
                            flags |= re.MULTILINE
                        if dotall:
                            flags |= re.DOTALL

                        if global_match:
                            matches = list(re.finditer(current_regex, current_test_text, flags))
                            match_count = len(matches)

                            if match_count > 0:
                                st.success(f"匹配成功！找到 {match_count} 个匹配项。")

                                # 增强的匹配详情显示
                                st.markdown("**匹配详情**")
                                for i, match in enumerate(matches):
                                    with st.expander(f"匹配 {i + 1}: 位置 {match.start()}-{match.end()}"):
                                        st.write(f"匹配文本: `{match.group()}`")
                                        if match.groups():
                                            st.write("**捕获组:**")
                                            for j, group in enumerate(match.groups(), 1):
                                                st.write(f"  组 {j}: `{group}`")
                                        if match.groupdict():
                                            st.write("**命名分组:**")
                                            for name, group in match.groupdict().items():
                                                st.write(f"  {name}: `{group}`")
                            else:
                                st.warning("未找到匹配项。")
                        else:
                            match = re.search(current_regex, current_test_text, flags)
                            if match:
                                st.success("匹配成功！")
                                st.write(f"匹配文本: `{match.group()}`")
                                st.write(f"匹配位置: {match.start()}-{match.end()}")
                                if match.groups():
                                    st.write("**捕获组:**")
                                    for i, group in enumerate(match.groups(), 1):
                                        st.write(f"组 {i}: `{group}`")
                            else:
                                st.warning("未找到匹配项。")

                        if replace_text:
                            replaced_text = re.sub(current_regex, replace_text, current_test_text, flags=flags)
                            st.markdown("**替换结果**")
                            display_generated_results("替换后的文本", replaced_text, "regex_replaced")
                    except re.error as e:
                        st.error(f"正则表达式错误: {e}")
                else:
                    st.warning("请输入正则表达式和测试文本")

        with button_col2:
            if st.button("🗑️ 清空输入", use_container_width=True, key="clear_input"):
                # 通过增加计数器并重新渲染来清空
                st.session_state.regex_clear_counter += 1
                st.rerun()

    with tab2:
        st.markdown("### 正则表达式代码生成器")

        col1, col2 = st.columns(2)

        with col1:
            # 模式选择：预定义或自定义
            pattern_source = st.radio("正则表达式来源", ["预定义模式", "自定义表达式"],
                                      key=f"pattern_source_{st.session_state.regex_clear_counter}")

            if pattern_source == "预定义模式":
                code_pattern = st.selectbox("选择预定义模式", list(PREDEFINED_PATTERNS.keys()),
                                            key=f"code_pattern_{st.session_state.regex_clear_counter}")
                pattern_display = PREDEFINED_PATTERNS[code_pattern]
                st.code(f"模式: {pattern_display}")
            else:
                pattern_display = st.text_input("输入自定义正则表达式", placeholder="例如: ^[a-zA-Z0-9]+$",
                                                key=f"custom_pattern_input_{st.session_state.regex_clear_counter}")
                if pattern_display:
                    st.code(f"模式: {pattern_display}")

            # 编程语言选择
            target_language = st.selectbox("选择目标语言", list(LANGUAGE_TEMPLATES.keys()),
                                           key=f"target_lang_{st.session_state.regex_clear_counter}")

            # 操作类型
            operation_type = st.radio("选择操作类型", ["匹配", "测试", "替换"],
                                      key=f"operation_type_{st.session_state.regex_clear_counter}")

            # 替换文本
            replacement_code = ""
            if operation_type == "替换":
                replacement_code = st.text_input("替换文本", placeholder="输入替换文本",
                                                 key=f"replacement_input_{st.session_state.regex_clear_counter}")

        with col2:
            st.markdown("**代码生成选项**")

            # 标志选择
            flags_selected = []
            lang_flags = LANGUAGE_TEMPLATES[target_language]["flags"]

            for flag_name, flag_char in lang_flags.items():
                if st.checkbox(f"{flag_name} ({flag_char})",
                               key=f"flag_{flag_char}_{target_language}_{st.session_state.regex_clear_counter}"):
                    flags_selected.append(flag_name)

            # 生成代码按钮
            if st.button("生成代码", use_container_width=True, key="generate_code"):
                current_pattern = ""
                if pattern_source == "预定义模式":
                    current_pattern = PREDEFINED_PATTERNS[code_pattern]
                else:
                    current_pattern = pattern_display

                if not current_pattern:
                    st.warning("请输入或选择正则表达式")
                else:
                    # 构建标志
                    if target_language in ["Python", "Java", "C#"]:
                        flags_value = " | ".join(flags_selected) if flags_selected else "0"
                    else:
                        flags_value = "".join([lang_flags[flag] for flag in flags_selected])

                    # 获取模板
                    template_key = "match" if operation_type == "匹配" else "test" if operation_type == "测试" else "replace"
                    template = LANGUAGE_TEMPLATES[target_language][template_key]

                    # 生成代码
                    try:
                        generated_code = template.format(
                            pattern=current_pattern,
                            flags=flags_value,
                            flags_value=flags_value,
                            replacement=replacement_code
                        )

                        st.session_state.generated_code = generated_code
                        st.session_state.generated_language = target_language

                    except KeyError as e:
                        st.error(f"代码生成错误: {e}")

            # 显示已生成的代码（如果有）
            if 'generated_code' in st.session_state and st.session_state.generated_code:
                language = st.session_state.generated_language if 'generated_language' in st.session_state else target_language
                display_generated_results(
                    f"{language} 代码",
                    st.session_state.generated_code,
                    f"regex_{language.lower()}_code"
                )

        # 清空所有按钮
        button_col3, _ = st.columns(2)
        with button_col3:
            if st.button("🗑️ 清空所有", use_container_width=True, key="clear_all_code"):
                # 清除生成的代码状态
                if 'generated_code' in st.session_state:
                    del st.session_state.generated_code
                if 'generated_language' in st.session_state:
                    del st.session_state.generated_language
                # 通过增加计数器清空输入
                st.session_state.regex_clear_counter += 1
                st.rerun()

    with tab3:
        st.markdown("### 从示例生成正则表达式")

        col1, col2 = st.columns(2)

        with col1:
            source_text = st.text_area("原文内容", height=150,
                                       placeholder="输入包含要提取内容的原文...",
                                       key=f"source_text_area_{st.session_state.regex_clear_counter}")

        with col2:
            examples_text = st.text_area("示例文本（用逗号分隔）", height=150,
                                         placeholder="输入要匹配的示例，用逗号分隔...",
                                         key=f"examples_text_area_{st.session_state.regex_clear_counter}")

        button_col4, button_col5 = st.columns(2)
        with button_col4:
            if st.button("生成正则表达式", use_container_width=True, key="generate_from_examples"):
                current_source = source_text
                current_examples = examples_text

                if current_source and current_examples:
                    generated_regex = generate_regex_from_examples(current_source, current_examples)

                    if generated_regex:
                        st.success("已生成正则表达式！")

                        # 使用统一的显示函数
                        display_generated_results("生成的正则表达式", generated_regex, "generated_regex")

                        # 测试生成的正则表达式
                        try:
                            matches = re.findall(generated_regex, current_source)
                            if matches:
                                st.write(f"在原文中找到 {len(matches)} 个匹配项:")
                                for i, match in enumerate(matches):
                                    st.write(f"{i + 1}. `{match}`")
                            else:
                                st.warning("生成的正则表达式在原文中未找到匹配项")
                        except re.error as e:
                            st.error(f"生成的正则表达式有误: {e}")
                    else:
                        st.warning("无法生成合适的正则表达式，请提供更多或更明确的示例")
                else:
                    st.warning("请输入原文内容和示例文本")

        with button_col5:
            if st.button("🗑️ 清空示例", use_container_width=True, key="clear_examples"):
                # 通过增加计数器清空输入
                st.session_state.regex_clear_counter += 1
                st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
# JSON数据对比工具
elif tool_category == "JSON处理工具":
    utils = JSONFileUtils()

    # 工具选择
    tool_mode = st.radio(
        "选择处理模式",
        ["JSON解析与格式化", "JSON数据对比", "JSONPath查询"],
        horizontal=True
    )

    if tool_mode == "JSON解析与格式化":
        show_doc("json_parser")

        # 初始化session_state
        if 'json_input_content' not in st.session_state:
            st.session_state.json_input_content = '{"name": "Tom", "age": 25, "hobbies": ["reading", "swimming"]}'
        if 'parse_result' not in st.session_state:
            st.session_state.parse_result = None
        if 'parse_error' not in st.session_state:
            st.session_state.parse_error = None

        # 输入区域
        st.markdown("**JSON输入**")
        json_input = st.text_area("", height=300, key="json_input", value=st.session_state.json_input_content,
                                  placeholder='请输入JSON字符串，例如: {"name": "Tom", "age": 25}')

        # 按钮区域
        col1, col2, col3, col4 = st.columns([1, 1, 1, 1])

        with col1:
            if st.button("🚀 解析JSON", use_container_width=True, key="parse_json"):
                if json_input.strip():
                    try:
                        parsed_json = json.loads(json_input)
                        st.session_state.parse_result = parsed_json
                        st.session_state.parse_error = None
                    except json.JSONDecodeError as e:
                        st.session_state.parse_result = None
                        st.session_state.parse_error = str(e)
                else:
                    st.warning("请输入JSON字符串")

        with col2:
            if st.button("✨ 格式化", use_container_width=True, key="format_json"):
                if json_input.strip():
                    try:
                        parsed_json = json.loads(json_input)
                        formatted_json = json.dumps(parsed_json, indent=2, ensure_ascii=False)
                        st.session_state.json_input_content = formatted_json
                        st.session_state.parse_result = parsed_json
                        st.session_state.parse_error = None
                    except json.JSONDecodeError as e:
                        st.session_state.parse_error = str(e)

        with col3:
            # 使用统一的复制按钮
            if st.session_state.parse_result is not None:
                formatted_json = json.dumps(st.session_state.parse_result, indent=2, ensure_ascii=False)
                create_copy_button(
                    formatted_json,
                    button_text="📋 复制结果",
                    key="copy_json_result"
                )
            else:
                # 禁用状态的按钮
                st.button("📋 复制结果", use_container_width=True, disabled=True, key="copy_disabled")

        with col4:
            if st.button("🗑️ 清空", use_container_width=True, key="clear_json"):
                st.session_state.json_input_content = ""
                st.session_state.parse_result = None
                st.session_state.parse_error = None

        # 显示解析结果
        if st.session_state.parse_result is not None:
            st.markdown("### 📊 解析结果")
            formatted_json = json.dumps(st.session_state.parse_result, indent=2, ensure_ascii=False)

            with st.expander("📄 格式化JSON", expanded=True):
                st.code(formatted_json, language='json')

            # 显示错误信息（如果有）
            if st.session_state.parse_error:
                st.error(f"解析错误: {st.session_state.parse_error}")


    elif tool_mode == "JSON数据对比":
        show_doc("json_comparison")

        # 初始化 session_state
        if 'json1_content' not in st.session_state:
            st.session_state.json1_content = '{"name": "John", "age": 30, "city": "New York"}'
        if 'json2_content' not in st.session_state:
            st.session_state.json2_content = '{"name": "Jane", "age": 25, "country": "USA"}'
        if 'comparison_result' not in st.session_state:
            st.session_state.comparison_result = None
        if 'differences_text' not in st.session_state:
            st.session_state.differences_text = ""
        if 'clear_counter' not in st.session_state:
            st.session_state.clear_counter = 0  # 添加计数器用于强制重新渲染

        # 输入区域 - 使用计数器确保重新渲染
        input_cols = st.columns(2)
        with input_cols[0]:
            st.markdown("**JSON 1**")
            json1 = st.text_area("", height=300,
                                 key=f"json1_{st.session_state.clear_counter}",  # 使用动态key
                                 value=st.session_state.json1_content,
                                 placeholder='输入第一个JSON数据...')
        with input_cols[1]:
            st.markdown("**JSON 2**")
            json2 = st.text_area("", height=300,
                                 key=f"json2_{st.session_state.clear_counter}",  # 使用动态key
                                 value=st.session_state.json2_content,
                                 placeholder='输入第二个JSON数据...')

        # 按钮区域
        button_cols = st.columns(4)
        with button_cols[0]:
            if st.button("✨ 格式化全部", use_container_width=True, key="format_all"):
                try:
                    # 先同步当前输入的内容到 session state
                    st.session_state.json1_content = json1
                    st.session_state.json2_content = json2

                    if json1.strip():
                        parsed_json1 = json.loads(json1)
                        formatted_json1 = json.dumps(parsed_json1, indent=2, ensure_ascii=False)
                        st.session_state.json1_content = formatted_json1
                    if json2.strip():
                        parsed_json2 = json.loads(json2)
                        formatted_json2 = json.dumps(parsed_json2, indent=2, ensure_ascii=False)
                        st.session_state.json2_content = formatted_json2

                    st.session_state.clear_counter += 1  # 增加计数器强制重新渲染
                    st.rerun()
                except json.JSONDecodeError as e:
                    st.error(f"JSON格式错误: {e}")

        with button_cols[1]:
            compare_clicked = st.button("🔍 开始对比", use_container_width=True, key="compare")

        with button_cols[2]:
            if st.button("🔄 交换数据", use_container_width=True, key="swap_data"):
                # 先同步当前输入的内容到 session state
                st.session_state.json1_content = json1
                st.session_state.json2_content = json2
                # 然后交换数据
                st.session_state.json1_content, st.session_state.json2_content = \
                    st.session_state.json2_content, st.session_state.json1_content
                st.session_state.clear_counter += 1  # 增加计数器强制重新渲染
                st.rerun()

        with button_cols[3]:
            if st.button("🗑️ 清空全部", use_container_width=True, key="clear_all"):
                st.session_state.json1_content = ""
                st.session_state.json2_content = ""
                st.session_state.comparison_result = None
                st.session_state.differences_text = ""
                st.session_state.clear_counter += 1  # 增加计数器强制重新渲染
                st.rerun()

        # 处理对比结果
        if compare_clicked:
            # 同步当前输入的内容到 session state
            st.session_state.json1_content = json1
            st.session_state.json2_content = json2

            if json1 and json2:
                try:
                    obj1 = json.loads(json1)
                    obj2 = json.loads(json2)

                    st.markdown("### 📋 对比结果")

                    utils.reset_stats()
                    differences = utils.compare_json(obj1, obj2)
                    st.session_state.comparison_result = differences

                    difference_text = "\n".join([f"- {diff}" for diff in differences])
                    st.session_state.differences_text = difference_text

                    if differences:
                        st.error(f"发现 {len(differences)} 个差异:")
                        st.write(difference_text)

                        # 使用下载按钮作为复制替代方案
                        st.download_button(
                            "📋 下载差异结果",
                            difference_text,
                            file_name="json_differences.txt",
                            mime="text/plain",
                            use_container_width=True,
                            key="download_diff"
                        )

                        # 同时提供文本区域用于手动复制
                        st.text_area("差异结果", difference_text, height=200, key="diff_copy_area")
                    else:
                        st.success("✅ 两个JSON对象完全相同")

                except json.JSONDecodeError as e:
                    st.error(f"JSON格式错误: {e}")

    elif tool_mode == "JSONPath查询":
        show_doc("jsonpath_tool")

        # 初始化session_state
        if 'jsonpath_json_content' not in st.session_state:
            st.session_state.jsonpath_json_content = '{"store": {"book": [{"title": "Book 1", "author": "Author 1"}, {"title": "Book 2", "author": "Author 2"}]}}'
        if 'jsonpath_expression' not in st.session_state:
            st.session_state.jsonpath_expression = "$.store.book[*].author"
        if 'jsonpath_result' not in st.session_state:
            st.session_state.jsonpath_result = None
        if 'jsonpath_result_text' not in st.session_state:
            st.session_state.jsonpath_result_text = ""

        # 布局：左右分栏
        left_col, right_col = st.columns([1, 1])

        with left_col:
            st.markdown("**📝 JSON数据**")
            json_data_input = st.text_area("", height=400, key="jsonpath_json",
                                           value=st.session_state.jsonpath_json_content,
                                           placeholder='输入JSON数据...')

            st.markdown("**🎯 JSONPath表达式**")
            jsonpath_input = st.text_input("", key="jsonpath_expr",
                                           value=st.session_state.jsonpath_expression,
                                           placeholder='例如: $.store.book[*].author')

            # 操作按钮
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🚀 执行查询", use_container_width=True, key="execute_jsonpath"):
                    if json_data_input.strip() and jsonpath_input.strip():
                        try:
                            json_data = json.loads(json_data_input)
                            result = utils.execute_jsonpath(json_data, jsonpath_input)
                            st.session_state.jsonpath_result = result
                            result_text = "\n".join([str(item) for item in result])
                            st.session_state.jsonpath_result_text = result_text
                        except json.JSONDecodeError as e:
                            st.error(f"JSON数据格式错误: {e}")
                        except Exception as e:
                            st.error(f"JSONPath查询错误: {e}")

        with right_col:
            st.markdown("### 📋 查询结果")

            if st.session_state.jsonpath_result is not None:
                result = st.session_state.jsonpath_result
                result_text = st.session_state.jsonpath_result_text

                if result:
                    st.success(f"✅ 找到 {len(result)} 个匹配项")
                    st.metric("匹配数量", len(result))

                    st.markdown("**📄 匹配结果:**")
                    for i, item in enumerate(result):
                        with st.expander(f"结果 #{i + 1}", expanded=len(result) <= 3):
                            if isinstance(item, (dict, list)):
                                st.json(item)
                            else:
                                st.code(str(item))

                    # 使用下载按钮
                    st.download_button(
                        "📋 下载查询结果",
                        result_text,
                        file_name="jsonpath_results.txt",
                        mime="text/plain",
                        use_container_width=True,
                        key="download_jsonpath"
                    )

                    # 提供文本区域用于手动复制
                    st.text_area("查询结果", result_text, height=200, key="jsonpath_copy_area")
                else:
                    st.warning("❌ 未找到匹配项")

# 日志分析工具
if tool_category == "日志分析工具":
    render_log_analysis_page()

# 初始化并使用留言区
feedback_section = FeedbackSection()
feedback_section.render_feedback_section()

# show_general_guidelines()
author = AuthorProfile()

# 在需要显示底部作者介绍的地方调用
author.render_main_profile()

# 在需要显示侧边栏作者信息的地方调用
# author.render_sidebar_profile()
