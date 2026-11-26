"""运行时 UI 翻译层回归：文本/HTML/选项值/代码块保护。"""
from __future__ import annotations

import os

import pytest

from qa_toolkit.core import i18n
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
