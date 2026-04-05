import sys
from io import BytesIO
from datetime import datetime
from pathlib import Path
import zipfile

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.text_analysis import (
    analyze_text,
    build_export_payload,
    build_text_report,
    decode_uploaded_text,
    export_rows,
    preprocess_text,
    split_sentences,
)


def test_split_sentences_counts_each_sentence_once():
    text = "第一句。第二句！Third sentence?\n第四句；第五句。"

    sentences = split_sentences(text)

    assert sentences == ["第一句。", "第二句！", "Third sentence?", "第四句；", "第五句。"]


def test_preprocess_text_applies_all_cleanup_options():
    text = "  第一行  \r\n\r\n\r\n第二   行\t\t \r\n"

    result = preprocess_text(
        text,
        trim_line_edges=True,
        collapse_blank_lines=True,
        collapse_inner_spaces=True,
    )

    assert result["text"] == "第一行\n\n第二 行\n"
    assert result["changed"] is True
    assert result["normalized_line_endings"] is True
    assert result["trimmed_lines"] == 2
    assert result["collapsed_blank_line_groups"] == 1
    assert result["collapsed_space_runs"] == 1


def test_analyze_text_returns_basic_counts_and_diagnostics():
    text = "Alpha beta beta。\n\n重复行\n重复行\nLine with  two  spaces  "

    analysis = analyze_text(text)

    assert analysis["basic"]["total_sentences"] == 2
    assert analysis["basic"]["total_paragraphs"] == 2
    assert analysis["basic"]["non_empty_lines"] == 4
    assert analysis["diagnostics"]["blank_lines"] == 1
    assert analysis["diagnostics"]["repeated_line_count"] == 1
    assert analysis["diagnostics"]["double_space_runs"] == 2
    assert analysis["keyword_stats"]["repeated_keywords"][0] == ("beta", 2)
    assert any(item["title"] == "存在空白噪音" for item in analysis["suggestions"])


def test_export_payload_rows_and_report_include_key_sections():
    analysis = analyze_text("第一段。\n\nSecond paragraph with keyword keyword.")
    preprocess_result = preprocess_text("第一段。\n\nSecond paragraph with keyword keyword.")

    payload = build_export_payload(
        analysis,
        preprocess_result=preprocess_result,
        source_label="示例文本",
    )
    rows = export_rows(payload)
    report = build_text_report(payload, generated_at=datetime(2026, 4, 5, 12, 30, 0))

    assert payload["source"] == "示例文本"
    assert any(row["类别"] == "basic" and row["指标"] == "total_chars" for row in rows)
    assert "文本统计报告" in report
    assert "来源: 示例文本" in report
    assert "关键词 Top10" in report
    assert "keyword: 2 次" in report


def test_decode_uploaded_text_supports_utf8_bom():
    raw_bytes = "测试内容".encode("utf-8-sig")

    decoded = decode_uploaded_text(raw_bytes)

    assert decoded == "测试内容"


def test_decode_uploaded_text_supports_docx():
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
                <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
                <Default Extension="xml" ContentType="application/xml"/>
                <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
            </Types>""",
        )
        archive.writestr(
            "_rels/.rels",
            """<?xml version="1.0" encoding="UTF-8"?>
            <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
                <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
            </Relationships>""",
        )
        archive.writestr(
            "word/document.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
            <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
                <w:body>
                    <w:p><w:r><w:t>第一段</w:t></w:r></w:p>
                    <w:p><w:r><w:t>Second line</w:t></w:r></w:p>
                    <w:tbl>
                        <w:tr>
                            <w:tc><w:p><w:r><w:t>单元格1</w:t></w:r></w:p></w:tc>
                            <w:tc><w:p><w:r><w:t>Cell 2</w:t></w:r></w:p></w:tc>
                        </w:tr>
                    </w:tbl>
                </w:body>
            </w:document>""",
        )

    decoded = decode_uploaded_text(buffer.getvalue(), filename="sample.docx")

    assert decoded == "第一段\n\nSecond line\n\n单元格1\tCell 2"


def test_decode_uploaded_text_supports_doc_via_textutil(monkeypatch):
    captured = {}

    class FakeCompletedProcess:
        def __init__(self, stdout: bytes):
            self.stdout = stdout

    def fake_run(command, capture_output, check):
        captured["command"] = command
        assert capture_output is True
        assert check is True
        return FakeCompletedProcess("导出的 doc 内容".encode("utf-8"))

    monkeypatch.setattr("qa_toolkit.utils.text_analysis.shutil.which", lambda name: "/usr/bin/textutil")
    monkeypatch.setattr("qa_toolkit.utils.text_analysis.subprocess.run", fake_run)

    decoded = decode_uploaded_text(b"fake doc bytes", filename="legacy.doc")

    assert decoded == "导出的 doc 内容"
    assert captured["command"][:4] == ["textutil", "-convert", "txt", "-stdout"]
