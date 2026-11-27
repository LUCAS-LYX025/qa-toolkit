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
    assert en_doc and "Advanced Data Generator" in en_doc["title"]
    assert get_tool_doc("__missing_tool__", "en-US") is None
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
    assert "数据生成工具" in PAGE_TOOL_CONFIG
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


# ---------------------------------------------------------------------------
# 渲染回归：i18n 文案必须真正求值，不能把模板表达式原样输出到页面上
# ---------------------------------------------------------------------------
# 背景：render_back_to_top_button() 的 HTML 内含大量 CSS 大括号，是普通字符串，
# 不能改成 f-string。i18n 改造时曾把 {th(...)} 直接写进去，导致四种语言下
# 快捷操作面板都显示 Python 源码。这里从渲染结果层面守住这条底线。

_LEAK_PATTERN = re.compile(
    r"\{th\(|\{t\(|\{html\.escape\(|\{tool_label\(|\{tool_description\("
    r"|\{_\w+\}|__QA_[A-Z_]+__"
)

_FLOATING_LABELS = {
    "zh-CN": ("⚡ 快捷操作", "💬 意见反馈", "↑ 返回顶部"),
    "zh-TW": ("⚡ 快捷操作", "💬 意見回饋", "↑ 返回頂部"),
    "en-US": ("⚡ Quick actions", "💬 Feedback", "↑ Back to top"),
    "ko-KR": ("⚡ 빠른 작업", "💬 의견 보내기", "↑ 맨 위로"),
}


@pytest.mark.parametrize("lang,labels", list(_FLOATING_LABELS.items()))
def test_rendered_markdown_has_no_template_source(lang, labels):
    """页面上不允许出现 {th(...)} / {t(...)} 这类未求值的 Python 模板源码。"""
    app = _run_app(lang)
    assert not app.exception, (lang, [e.value for e in app.exception])
    rendered = "\n".join(item.value for item in app.markdown)
    leaks = _LEAK_PATTERN.findall(rendered)
    assert not leaks, (lang, leaks[:8])

    panel = next(
        (item.value for item in app.markdown if "qa-toolkit-floating-shell" in item.value),
        "",
    )
    assert panel, "悬浮快捷操作面板未渲染"
    assert "__QA_" not in panel
    for label in labels:
        assert label in panel, (lang, label, panel[-300:])


def _load_copy_button_function(overrides=None):
    """只抽取 escape_js_string / create_copy_button 执行，避免启动整页 App。"""
    import ast
    import html as html_module

    source = (
        Path(__file__).resolve().parents[1] / "src" / "qa_toolkit" / "ui" / "pages" / "data_generator_page.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    wanted = {"escape_js_string", "create_copy_button"}
    funcs = [
        node for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in wanted
    ]
    assert len(funcs) == 2

    class _Capture:
        def __init__(self):
            self.calls = []

        def html(self, content, height=None):
            self.calls.append(content)

    capture = _Capture()
    namespace = {
        "json": json,
        "html": html_module,
        "components": capture,
        "t": t,
        "th": th,
        "hash": hash,
    }
    namespace.update(overrides or {})
    exec(compile(ast.Module(body=funcs, type_ignores=[]), "<copy_button>", "exec"), namespace)
    return namespace["create_copy_button"], capture


def _js_button_literals(script):
    """提取 button.innerHTML = <字面量>;（跳过恢复态的 originalText 变量）。"""
    found = re.findall(r"button\.innerHTML = (.*?);", script)
    return [item for item in found if item.strip().startswith('"')]


@pytest.mark.parametrize("lang", list(_FLOATING_LABELS))
def test_copy_button_script_uses_valid_js_literals(lang):
    """复制按钮的三处提示文案必须是合法 JS 字符串字面量，且无模板残留。"""
    localized_t = lambda source, **kwargs: t(source, locale=lang, **kwargs)
    create_copy_button, capture = _load_copy_button_function({"t": localized_t})
    button_label = t("📋 复制结果", locale=lang)
    create_copy_button("hello", button_text=button_label, key=7)

    assert len(capture.calls) == 1
    script = capture.calls[0]
    assert "{_" not in script and "{th(" not in script and "{t(" not in script
    literals = _js_button_literals(script)
    assert len(literals) == 3, literals
    for literal in literals:
        assert isinstance(json.loads(literal), str), literal
    assert json.loads(literals[2]) == button_label


def test_copy_button_script_survives_apostrophe_in_translation():
    """译文含单引号时（英文常见）不能破坏 JS 字符串边界。"""
    create_copy_button, capture = _load_copy_button_function(
        {"t": lambda source, **kwargs: "Can't copy"}
    )
    create_copy_button("hello", button_text="Can't copy", key=9)
    literals = _js_button_literals(capture.calls[0])
    assert len(literals) == 3, literals
    for literal in literals:
        assert json.loads(literal) == "Can't copy", literal
