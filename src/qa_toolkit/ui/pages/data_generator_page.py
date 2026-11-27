"""数据生成工具页面：Faker 高级造数 + 基础数据生成器 + 测试场景/边界值造数。

从主入口 streamlit_app.py 拆出，保持原有 session_state 键、路由键与文案不变。
"""
from __future__ import annotations

import datetime
import html
import json
import random
import uuid

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from qa_toolkit.config.constants import (
    CATEGORIES,
    COUNTRIES,
    DOMAINS_PRESET,
    GENDERS,
    PASSWORD_OPTIONS,
    PROVINCE_CITY_AREA_CODES,
    PROVINCE_MAP,
    PROVINCES,
    RANDOM_STRING_TYPES,
)
from qa_toolkit.core.data_generator_registry import get_locales, get_registry_summary
from qa_toolkit.core.i18n import t, th
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.tools.data_generator import DataGenerator

# 导入Faker库
try:
    from faker import Faker

    Faker("zh_CN")
    FAKER_AVAILABLE = True
except ImportError:
    FAKER_AVAILABLE = False
    st.warning("Faker库未安装，部分高级功能将受限。请运行: pip install faker")


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


def render_data_generator_page() -> None:
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
                # 电话号码分支需要一个「省份 key 列表」，与全局 PROVINCES（dict）区分，
                # 避免函数内把 PROVINCES 判定为局部变量导致地址/身份证分支 UnboundLocalError。
                province_list = list(PROVINCE_CITY_AREA_CODES.keys())


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
                        province_options = ["随机"] + province_list
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
