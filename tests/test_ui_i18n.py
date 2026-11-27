"""运行时 UI 翻译层回归：文本/HTML/选项值/代码块保护。"""
from __future__ import annotations

import os

import pytest

from qa_toolkit.core import i18n
from qa_toolkit.core import ui_i18n
from qa_toolkit.core.ui_i18n import translate_markup, translate_text


@pytest.fixture()
def english(monkeypatch):
    monkeypatch.setattr(i18n, "_runtime_locale", lambda: "en-US")
    i18n.register_translations(
        "en-US",
        {
            "使用说明": "Instructions",
            "开始分析": "Start analysis",
            "确定": "OK",
            "已生成": "Generated",
        },
        replace=True,
    )
    return None


def test_translate_text_exact_match(english):
    assert translate_text("使用说明") == "Instructions"
    assert translate_text("开始分析") == "Start analysis"


def test_translate_text_falls_back(english):
    assert translate_text("没有词条的文案") == "没有词条的文案"
    assert translate_text("") == ""
    assert translate_text(None) is None


def test_translate_text_skips_pure_ascii(english):
    assert translate_text("Already English") == "Already English"


def test_translate_markup_keeps_html_tags(english):
    html = '<div class="section-header">使用说明</div>'
    assert translate_markup(html) == '<div class="section-header">Instructions</div>'


def test_translate_markup_keeps_code_block(english):
    text = "```\n使用说明\n```"
    assert translate_markup(text) == text


def test_translate_markup_keeps_inline_code_and_url(english):
    text = "使用说明：`使用说明` https://example.com/使用说明"
    out = translate_markup(text)
    assert "Instructions" in out
    assert "`使用说明`" in out
    assert "https://example.com/使用说明" in out


def test_translate_markup_keeps_style_block(english):
    text = '<style>.x{content:"使用说明"}</style>'
    assert translate_markup(text) == text


def test_translate_markup_table_cells(english):
    text = "| 使用说明 | 确定 |\n| --- | --- |"
    out = translate_markup(text)
    assert "Instructions" in out
    assert "OK" in out


def test_translate_markup_markdown_list_prefix(english):
    out = translate_markup("- 使用说明")
    assert out == "- Instructions"


def test_option_wrapper_preserves_internal_values(english):
    """选项显示被翻译，但返回值仍是中文原值。"""
    from qa_toolkit.core.ui_i18n import _wrap_options

    captured = {}

    def fake_selectbox(label, options, **kwargs):
        captured["label"] = label
        captured["options"] = options
        captured["format_func"] = kwargs.get("format_func")
        return options[0]

    wrapped = _wrap_options(fake_selectbox)
    value = wrapped("请选择", ["确定", "取消"])
    assert captured["label"] == "请选择"
    assert captured["options"] == ["确定", "取消"]
    assert value == "确定"
    assert captured["format_func"]("确定") == "OK"


def test_default_locale_is_passthrough(monkeypatch):
    """默认语言下翻译层是空转：有中文也不应调用 t()，整段原样返回。"""
    monkeypatch.setattr(i18n, "_runtime_locale", lambda: i18n.DEFAULT_LOCALE)

    def boom(*args, **kwargs):
        raise AssertionError("default locale must not call t()")

    monkeypatch.setattr(ui_i18n, "t", boom)
    assert translate_text("界面语言：开始分析") == "界面语言：开始分析"
    assert translate_markup("<div>界面语言</div>`开始分析`") == "<div>界面语言</div>`开始分析`"


@pytest.fixture()
def en_builtin(monkeypatch):
    """切到英文界面，直接使用内置词库（不注入测试专用词条）。"""
    monkeypatch.setattr(i18n, "_runtime_locale", lambda: "en-US")
    return None


def _fake_metric_sink():
    captured = {}

    def fake_metric(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs

    return fake_metric, captured


def test_metric_translates_label_and_status_value(en_builtin):
    """DEF-001 回归：metric 的 label 与命中词库的 value 都要翻译。"""
    fake, captured = _fake_metric_sink()
    ui_i18n._wrap_metric(fake)("来源", "未导入")
    assert captured["args"][0] == "Source"
    assert captured["args"][1] == "Not imported"


def test_metric_value_keeps_numeric_and_formatted(en_builtin):
    """数字、百分比、带千分位的展示值绝不能被翻译层改写。"""
    for value in (42, 3.5, "3.5/5", "98.2%", "1,024"):
        fake, captured = _fake_metric_sink()
        ui_i18n._wrap_metric(fake)("来源", value)
        assert captured["args"][1] == value


def test_metric_value_keeps_ascii_and_unmatched_cjk(en_builtin):
    """英文、文件名、URL 与词库未命中的中文都原样返回。"""
    for value in ("RGB", "report.json", "https://example.com/未导入", "没有词条的中文"):
        fake, captured = _fake_metric_sink()
        ui_i18n._wrap_metric(fake)("来源", value)
        assert captured["args"][1] == value


def test_metric_value_via_keyword_arguments(en_builtin):
    """st.metric(label=..., value=...) 的关键字写法同样生效。"""
    fake, captured = _fake_metric_sink()
    ui_i18n._wrap_metric(fake)(label="来源", value="待执行", help="来源")
    assert captured["kwargs"]["label"] == "Source"
    assert captured["kwargs"]["value"] == "Pending"
    assert captured["kwargs"]["help"] == "Source"


def test_metric_value_passthrough_in_default_locale(monkeypatch):
    """默认语言下 value 不应触发 t()，保持翻译层空转。"""
    monkeypatch.setattr(i18n, "_runtime_locale", lambda: i18n.DEFAULT_LOCALE)

    def boom(*args, **kwargs):
        raise AssertionError("default locale must not call t()")

    monkeypatch.setattr(ui_i18n, "t", boom)
    fake, captured = _fake_metric_sink()
    ui_i18n._wrap_metric(fake)("来源", "未导入")
    assert captured["args"] == ("来源", "未导入")


def test_dg_metric_wrapper_translates_value(en_builtin):
    """col.metric(...) 走 DeltaGenerator 包装，value 同样翻译。"""
    captured = {}

    def fake_metric(self, label, value):
        captured["label"] = label
        captured["value"] = value

    ui_i18n._wrap_dg_metric(fake_metric)(object(), "执行模式", "未开启")
    assert captured["label"] == "Execution mode"
    assert captured["value"] == "Off"


def test_install_wraps_metric():
    """安装入口必须给 metric 挂专用包装，防止后续改动漏掉。"""
    import streamlit as st
    from streamlit.delta_generator import DeltaGenerator

    ui_i18n.install_streamlit_i18n()
    assert hasattr(st.metric, "__wrapped__")
    assert hasattr(DeltaGenerator.metric, "__wrapped__")
