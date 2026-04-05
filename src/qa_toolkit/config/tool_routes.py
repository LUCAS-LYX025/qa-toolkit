from __future__ import annotations

from typing import Dict, Set


INLINE_TOOL_CATEGORIES: Set[str] = {
    "数据生成工具",
    "JSON处理工具",
}


PAGE_TOOL_CONFIG: Dict[str, Dict[str, str]] = {
    "测试用例生成器": {
        "module_path": "qa_toolkit.ui.pages.test_case_generator_page",
        "function_name": "render_test_case_generator_page",
        "page_label": "测试用例生成页面",
    },
    "禅道绩效统计": {
        "module_path": "qa_toolkit.ui.pages.zentao_performance_page",
        "function_name": "render_zentao_performance_page",
        "page_label": "禅道绩效统计页面",
    },
    "日志分析工具": {
        "module_path": "qa_toolkit.ui.pages.log_analysis_page",
        "function_name": "render_log_analysis_page",
        "page_label": "日志分析页面",
    },
    "BI数据分析工具": {
        "module_path": "qa_toolkit.ui.pages.bi_analysis_page",
        "function_name": "render_bi_analysis_page",
        "page_label": "BI 数据分析页面",
    },
    "文本对比工具": {
        "module_path": "qa_toolkit.ui.pages.text_comparison_page",
        "function_name": "render_text_comparison_page",
        "page_label": "文本对比页面",
    },
    "字数统计工具": {
        "module_path": "qa_toolkit.ui.pages.word_counter_page",
        "function_name": "render_word_counter_page",
        "page_label": "字数统计页面",
    },
    "正则测试工具": {
        "module_path": "qa_toolkit.ui.pages.regex_tester_page",
        "function_name": "render_regex_tester_page",
        "page_label": "正则测试页面",
    },
    "加密/解密工具": {
        "module_path": "qa_toolkit.ui.pages.crypto_tools_page",
        "function_name": "render_crypto_tools_page",
        "page_label": "加密解密页面",
    },
    "时间处理工具": {
        "module_path": "qa_toolkit.ui.pages.time_processor_page",
        "function_name": "render_time_processor_page",
        "page_label": "时间处理页面",
    },
    "图片处理工具": {
        "module_path": "qa_toolkit.ui.pages.image_processor_page",
        "function_name": "render_image_processor_page",
        "page_label": "图片处理页面",
    },
    "IP/域名查询工具": {
        "module_path": "qa_toolkit.ui.pages.ip_lookup_page",
        "function_name": "render_ip_lookup_page",
        "page_label": "IP 域名查询页面",
    },
    "接口性能测试": {
        "module_path": "qa_toolkit.ui.pages.api_performance_page",
        "function_name": "render_api_performance_test_page",
        "page_label": "API 性能测试页面",
    },
    "接口安全测试": {
        "module_path": "qa_toolkit.ui.pages.api_security_page",
        "function_name": "render_api_security_test_page",
        "page_label": "API 安全测试页面",
    },
    "接口研发辅助": {
        "module_path": "qa_toolkit.ui.pages.api_dev_tools_page",
        "function_name": "render_api_dev_tools_page",
        "page_label": "API 开发工具页面",
    },
    "接口自动化测试": {
        "module_path": "qa_toolkit.ui.pages.api_automation_page",
        "function_name": "render_api_automation_test_page",
        "page_label": "API 自动化测试页面",
    },
}


PLACEHOLDER_DOC_MAPPING: Dict[str, str] = {}

