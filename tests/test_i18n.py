"""国际化切换、回退与 IP 自动定位回归测试。"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

SRC_DIR = Path(__file__).resolve().parents[1] / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.config.constants import TOOL_CATEGORIES
from qa_toolkit.config.tool_routes import INLINE_TOOL_CATEGORIES, PAGE_TOOL_CONFIG
from qa_toolkit.core import i18n
from qa_toolkit.core.i18n import (
    DEFAULT_LOCALE,
    LocaleSpec,
    get_catalog,
    get_locales,
    get_tool_doc,
    normalize_locale,
    register_locale,
    register_tool_doc,
    register_translations,
    resolve_locale,
    t,
    th,
)
from qa_toolkit.core.locale_detector import (
    build_browser_locale_bootstrap,
    build_locale_persistence_script,
    detect_locale_from_ip,
    get_country_locale_map,
    locale_from_country,
    register_country_locale,
)

APP_PATH = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def _run_app(lang: str | None = None) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=25)
    if lang:
        app.query_params["lang"] = lang
    return app.run()


def test_four_locales_registered():
    locales = get_locales()
    assert set(locales) == {"zh-CN", "zh-TW", "en-US", "ko-KR"}
    assert locales["en-US"].label == "English"
    assert locales["ko-KR"].label == "한국어"


def test_normalize_locale_aliases():
    assert normalize_locale("zh_CN") == "zh-CN"
    assert normalize_locale("en_US") == "en-US"
    assert normalize_locale("zh-Hant") == "zh-TW"
    assert normalize_locale("ko") == "ko-KR"
    assert normalize_locale("fr-FR") is None
    assert normalize_locale(None) is None


def test_translate_and_format():
    assert t("测试工程师常用工具集", locale="en-US") == "QA Engineer Toolkit"
    assert t("测试工程师常用工具集", locale="ko-KR") == "QA 엔지니어 도구 모음"
    assert t("切换到{name}", name=t("正则测试工具", locale="en-US"), locale="en-US") == (
        "Switch to Regex Tester"
    )
    assert t("记录数", locale="fr-FR") == "记录数"  # 未知语言回退原文


def test_html_helper_escapes_translation():
    assert th("切换到{name}", name='<img src="x">', locale="en-US") == (
        "Switch to &lt;img src=&quot;x&quot;&gt;"
    )


def test_resolve_locale_priority():
    assert resolve_locale("ko-KR", persisted="en-US", detected="zh-TW") == "ko-KR"
    assert resolve_locale(None, persisted="zh-TW", detected="en-US") == "zh-TW"
    assert resolve_locale(None, persisted=None, detected="en-US") == "en-US"
    assert resolve_locale() == DEFAULT_LOCALE


def test_registry_rejects_silent_overwrite():
    with pytest.raises(ValueError):
        register_locale(LocaleSpec("en-US", "x", "x"))
    with pytest.raises(ValueError):
        register_translations("en-US", {"记录数": "ROWS"})
    register_translations("en-US", {"__test_only__": "ok"})
    assert t("__test_only__", locale="en-US") == "ok"
    register_translations("en-US", {"__test_only__": "updated"}, replace=True)
    assert t("__test_only__", locale="en-US") == "updated"


def test_country_mapping_and_extension():
    assert locale_from_country("us") == "en-US"
    assert locale_from_country("KR") == "ko-KR"
    assert locale_from_country("tw") == "zh-TW"
    assert locale_from_country("HK") == "zh-TW"
    assert locale_from_country("cn") == "zh-CN"
    assert locale_from_country("ZZ") is None
    with pytest.raises(ValueError):
        register_country_locale("US", "zh-TW")
    register_country_locale("ZZ", "en-US")
    assert locale_from_country("zz") == "en-US"
    assert "US" in get_country_locale_map()


def test_detect_locale_from_ip_injected():
    def fake_get(url, timeout):
        assert "1.2.3.4" in url
        return json.dumps({"country_code": "US"})

    assert detect_locale_from_ip("1.2.3.4", http_get=fake_get) == "en-US"
    assert detect_locale_from_ip("", http_get=fake_get) is None


def test_browser_bootstrap_uses_query_param_and_dedupes():
    script = build_browser_locale_bootstrap(DEFAULT_LOCALE)
    assert '"lang"' in script
    assert "qa_toolkit_locale_probe" in script
    assert "ipapi.co" in script
    assert "navigator.language" in script
    # 注入的 JSON 数据不能提前闭合 script 标签。
    assert script.count("</script>") == 1
    persisted = build_locale_persistence_script("ko-KR")
    assert "ko-KR" in persisted and "qa_toolkit_locale" in persisted


def test_tool_docs_localized_and_fallback():
    en_doc = get_tool_doc("data_generator", "en-US")
    assert en_doc and "Advanced data generator" in en_doc["title"]
    assert get_tool_doc("regex_tester", "en-US") is None
    register_tool_doc("en-US", "__test_tool__", title="T", usage="U", notes="N")
    assert get_tool_doc("__test_tool__", "en-US")["usage"] == "U"


def test_catalog_placeholders_match_source():
    """译文必须保留原文的命名占位符，否则格式化会静默丢参数。"""
    locale_dir = SRC_DIR / "qa_toolkit" / "config" / "locales"
    fields_pattern = re.compile(r"{([A-Za-z_][A-Za-z0-9_]*)}")
    for name in ("zh-TW", "en-US", "ko-KR"):
        catalog = get_catalog(name)
        assert catalog, name
        for source, translated in catalog.items():
            source_fields = set(fields_pattern.findall(source))
            if not source_fields:
                continue
            translated_fields = set(fields_pattern.findall(translated))
            assert source_fields == translated_fields, (name, source, translated)
        path = locale_dir / f"{name}.json"
        assert json.loads(path.read_text(encoding="utf-8"))["messages"]


def test_route_keys_stay_chinese_after_localization():
    # 语言切换只改显示名，路由键和 session_state 值保持不变。
    assert "数据生成工具" in INLINE_TOOL_CATEGORIES
    assert "数据生成工具" in TOOL_CATEGORIES
    assert "正则测试工具" in PAGE_TOOL_CONFIG
    assert all(isinstance(key, str) for key in PAGE_TOOL_CONFIG)


def test_app_manual_locale_switch_visible():
    app = _run_app("en-US")
    assert not app.exception
    assert [item.label for item in app.sidebar.selectbox] == ["Interface language"]
    hero = " ".join(item.value for item in app.markdown)
    assert "QA Engineer" in hero
    assert "Focus current tool" in " ".join(item.label for item in app.button)
    assert "Data region" in " ".join(item.label for item in app.selectbox)


def test_app_all_four_locales_render():
    cases = {
        "zh-CN": ("测试工程师", "界面语言"),
        "zh-TW": ("測試工程師", "介面語言"),
        "en-US": ("QA Engineer", "Interface language"),
        "ko-KR": ("QA 엔지니어", "인터페이스 언어"),
    }
    for lang, (hero_marker, switch_label) in cases.items():
        app = _run_app(lang)
        assert not app.exception, (lang, [e.value for e in app.exception])
        assert hero_marker in " ".join(item.value for item in app.markdown)
        assert switch_label in [item.label for item in app.sidebar.selectbox]


def test_app_default_falls_back_to_simplified_chinese():
    app = _run_app()
    assert not app.exception
    assert "界面语言" in [item.label for item in app.sidebar.selectbox]
