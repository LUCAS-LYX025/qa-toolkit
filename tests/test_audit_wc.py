"""字数统计工具专项审计回归测试（issues #170-#187）。

每个测试对应一个 GitHub issue，确保修复不被后续改动回退。
"""
import sys
import unicodedata
from datetime import datetime
from io import BytesIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.text_analysis_registry import (
    DEFAULT_STOPWORDS,
    configure_settings,
    configure_stopwords,
    register_character_class,
    register_tokenizer,
    reset_text_analysis_registry,
    settings,
    stopwords,
    tokenizer_names,
)
from qa_toolkit.ui.pages.word_counter_page import (
    _build_markdown_report,
    _markdown_text,
    _safe_csv_bytes,
)
from qa_toolkit.utils.text_analysis import (
    _extract_keyword_tokens,
    analyze_text,
    build_export_payload,
    build_text_report,
    export_rows,
)


@pytest.fixture(autouse=True)
def _reset_registry():
    reset_text_analysis_registry()
    yield
    reset_text_analysis_registry()


def test_issue_170_cjk_extension_ideographs_counted():
    """#170 CJK 扩展区汉字计入中文字符，不再误判为非中文字母。"""
    analysis = analyze_text("𠀀𠀁𠀂")  # 扩展 B 区
    assert analysis["char_types"]["chinese_chars"] == 3
    assert analysis["char_types"]["latin_letters"] == 0


def test_issue_171_emoji_counted_separately():
    """#171 emoji（含 ZWJ / 肤色 / 国旗）作为独立类型，不污染 other_chars。"""
    analysis = analyze_text("👍🏽👨‍👩‍👧‍👦🇨🇳")
    assert analysis["char_types"]["emoji"] == 11
    assert analysis["char_types"]["other_chars"] == 0


def test_issue_172_fullwidth_and_nbsp_spaces():
    """#172 全角空格/NBSP 计入 spaces，'不含空格'口径一致。"""
    analysis = analyze_text("a\u3000b\u00a0c")
    assert analysis["char_types"]["spaces"] == 2
    assert analysis["basic"]["total_chars_no_spaces"] == 3


def test_issue_173_unicode_nfc_nfd_consistent():
    """#173 NFC/NFD 归一化后同一词合并统计。"""
    text = unicodedata.normalize("NFC", "café") + " " + unicodedata.normalize("NFD", "café")
    assert analyze_text(text)["frequencies"]["top_keywords"] == [("café", 2)]


def test_issue_174_invisible_chars_diagnosed():
    """#174 零宽字符/BOM 单独计数并给出诊断。"""
    analysis = analyze_text("ab\u200bcd\ufeffef")
    assert analysis["char_types"]["invisible_chars"] == 2
    assert analysis["diagnostics"]["invisible_chars"] == 2
    assert any(item["title"] == "存在不可见字符" for item in analysis["suggestions"])


def test_issue_175_non_ascii_latin_words_not_truncated():
    """#175 重音字母/西里尔词完整提取，不再从非 ASCII 处截断。"""
    tokens = _extract_keyword_tokens("ÄPFEL Straße café naïve", ignore_case=True)
    assert tokens == ["äpfel", "strasse", "café", "naïve"]
    assert _extract_keyword_tokens("Русский текст", ignore_case=True) == ["русский", "текст"]


def test_issue_176_word_count_semantics_exposed():
    """#176 同时提供空格分词数与阅读单元，中文口径可解释。"""
    analysis = analyze_text("需求说明接口文档测试总结")
    assert analysis["basic"]["total_words"] == 1
    assert analysis["basic"]["reading_units"] == 12
    # 结构里同时具备两种口径供 UI 展示
    assert "reading_units" in analysis["basic"] and "total_words" in analysis["basic"]


def test_issue_177_consistent_frequency_ordering():
    """#177 top_keywords 与 repeated_keywords 同频排序一致。"""
    analysis = analyze_text("香蕉 苹果 香蕉 苹果 梨 梨")
    top = [k for k, _ in analysis["frequencies"]["top_keywords"]]
    repeated = [k for k, _ in analysis["keyword_stats"]["repeated_keywords"]]
    assert top[:2] == repeated[:2] == ["香蕉", "苹果"]


def test_issue_178_markdown_report_escaped():
    """#178 Markdown 报告来源/关键词转义，无法注入链接或反引号。"""
    payload = build_export_payload(
        analyze_text("测试 测试"), source_label="[假来源](javascript:alert(1))`x`"
    )
    report = _build_markdown_report(payload)
    # 链接语法被打断（转义的 [ 和反引号），无法渲染成可点击链接
    assert "\\[假来源\\]" in report
    assert "\\`x\\`" in report
    assert "[假来源](" not in report  # 不存在有效 Markdown 链接


def test_issue_179_text_report_source_single_line():
    """#179 TXT 报告来源字段换行被折叠，无法伪造统计行。"""
    payload = build_export_payload(analyze_text("x"), source_label="源\n- 伪造统计: 999")
    report = build_text_report(payload)
    assert "\n- 伪造统计: 999" not in report
    source_line = [line for line in report.splitlines() if line.startswith("来源:")][0]
    assert "伪造统计: 999" in source_line  # 压在同一行，不构成独立统计行


def test_issue_180_csv_bom_and_formula_safe():
    """#180 CSV 带 UTF-8 BOM，公式前缀降级为文本。"""
    rows = [
        {"类别": "basic", "指标": "=HYPERLINK(\"evil\")", "数值": "+SUM(A1:A2)"},
        {"类别": "char", "指标": "中文", "数值": "@cmd"},
    ]
    data = _safe_csv_bytes(rows)
    assert data.startswith(b"\xef\xbb\xbf")
    text = data.decode("utf-8-sig")
    assert "'=HYPERLINK" in text
    assert "'+SUM" in text
    assert "'@cmd" in text


def test_issue_181_configurable_reading_speed():
    """#181 阅读速度可配置并影响阅读时长。"""
    configure_settings(reading_speed_per_minute=100)
    analysis = analyze_text("hello world " * 50)
    assert analysis["quality"]["reading_time_minutes"] == pytest.approx(100 / 100)
    assert settings()["reading_speed_per_minute"] == 100


def test_issue_182_configurable_long_line_threshold():
    """#182 长行阈值可配置。"""
    configure_settings(long_line_threshold=10)
    analysis = analyze_text("这是一行超过十个字符的长文本用于测试阈值配置是否生效")
    assert analysis["diagnostics"]["long_line_count"] == 1
    configure_settings(long_line_threshold=1000)
    assert analyze_text("这是一行超过十个字符的长文本") ["diagnostics"]["long_line_count"] == 0


def test_issue_183_configurable_stopwords_with_chinese():
    """#183 停用词可扩展，内置中文虚词生效。"""
    assert "的" in stopwords() and "the" in stopwords()
    assert "的" not in _extract_keyword_tokens("这的路")
    configure_stopwords(["业务词"], append=True)
    assert "业务词" in stopwords()
    assert "业务词" not in _extract_keyword_tokens("业务词 业务词")


def test_issue_184_character_types_closed_and_explainable():
    """#184 字符分类之和 = 总字符数，每类可解释。"""
    for text in ("全角　零宽\u200bemoji😀", "中文abc123。！", "𠀀𠀁𠀂 café"):
        analysis = analyze_text(text)
        char_types = analysis["char_types"]
        classified = (
            char_types["latin_letters"] + char_types["digits"] + char_types["punctuation"]
            + char_types["spaces"] + char_types["tabs"] + char_types["newlines"]
            + char_types["chinese_chars"] + char_types["emoji"] + char_types["invisible_chars"]
            + char_types["other_chars"]
        )
        assert classified == analysis["basic"]["total_chars"]


def test_issue_185_registry_extension_points():
    """#185 字符分类/分词器可注册，扩展新增统计维度无需改核心。"""
    register_character_class("hash", lambda c: c == "#", description="井号", priority=True)
    register_tokenizer("space", lambda t: t.split(), description="空格分词")
    assert "space" in tokenizer_names()
    analysis = analyze_text("a#b")
    assert analysis["char_types"]["hash"] == 1


def test_issue_186_cjk_tokenizer_replaceable():
    """#186 中文分词策略可替换，默认连续汉字块可被覆盖。"""
    register_tokenizer("cjk_block", lambda t: [c for c in t if "\u4e00" <= c <= "\u9fff"], replace=True)
    tokens = _extract_keyword_tokens("创建订单成功", min_length=1)
    assert "创" in tokens and "单" in tokens


def test_issue_187_export_payload_includes_new_dimensions():
    """#187 导出 payload 包含 emoji/不可见字符等新维度，报告结构完整。"""
    payload = build_export_payload(analyze_text("emoji😀\u200b测试"))
    assert "emoji" in payload["char_types"]
    assert "invisible_chars" in payload["char_types"]
    rows = export_rows(payload)
    assert any(row["指标"] == "emoji" for row in rows)
    report = build_text_report(payload, generated_at=datetime(2026, 4, 5, 12, 30, 0))
    assert "文本统计报告" in report
