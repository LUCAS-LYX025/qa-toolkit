"""Chinese PDF reports derived from MobSF JSON results."""

from __future__ import annotations

from html import escape
from io import BytesIO
from typing import Any, Dict, Iterable, Mapping, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


FONT_NAME = "STSong-Light"
_PAGE_WIDTH, _PAGE_HEIGHT = A4


def _ensure_chinese_font() -> None:
    if FONT_NAME not in pdfmetrics.getRegisteredFontNames():
        pdfmetrics.registerFont(UnicodeCIDFont(FONT_NAME))


def _text(value: Any, limit: int = 600) -> str:
    normalized = " ".join(str(value or "-").replace("\r", " ").replace("\n", " ").split())
    return normalized[:limit] + ("..." if len(normalized) > limit else "")


def _paragraph(value: Any, style: ParagraphStyle, limit: int = 600) -> Paragraph:
    return Paragraph(escape(_text(value, limit)).replace("\n", "<br/>"), style)


def _report_styles() -> Dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "MobSFChineseTitle",
            parent=base["Title"],
            fontName=FONT_NAME,
            fontSize=21,
            leading=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#123047"),
            spaceAfter=8 * mm,
        ),
        "heading": ParagraphStyle(
            "MobSFChineseHeading",
            parent=base["Heading2"],
            fontName=FONT_NAME,
            fontSize=13,
            leading=19,
            textColor=colors.HexColor("#123047"),
            spaceBefore=5 * mm,
            spaceAfter=3 * mm,
        ),
        "body": ParagraphStyle(
            "MobSFChineseBody",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=8.5,
            leading=13,
            alignment=TA_LEFT,
        ),
        "small": ParagraphStyle(
            "MobSFChineseSmall",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=7.5,
            leading=11,
        ),
        "table_head": ParagraphStyle(
            "MobSFChineseTableHead",
            parent=base["BodyText"],
            fontName=FONT_NAME,
            fontSize=8,
            leading=11,
            textColor=colors.white,
            alignment=TA_CENTER,
        ),
    }


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#D7E0E7"))
    canvas.line(18 * mm, 15 * mm, _PAGE_WIDTH - 18 * mm, 15 * mm)
    canvas.setFont(FONT_NAME, 8)
    canvas.setFillColor(colors.HexColor("#657786"))
    canvas.drawString(18 * mm, 9 * mm, "由 QA Toolkit 基于 MobSF JSON 结果生成")
    canvas.drawRightString(_PAGE_WIDTH - 18 * mm, 9 * mm, f"第 {document.page} 页")
    canvas.restoreState()


def _table(rows: Iterable[Sequence[Any]], widths: Sequence[float], styles: Dict[str, ParagraphStyle], header: bool = False) -> Table:
    data = []
    for row_index, row in enumerate(rows):
        style = styles["table_head"] if header and row_index == 0 else styles["body"]
        data.append([_paragraph(value, style) for value in row])
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0, hAlign="LEFT")
    table_style = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D7E0E7")),
    ]
    if header:
        table_style.extend(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#123047")),
                ("BACKGROUND", (0, 1), (-1, -1), colors.white),
            ]
        )
    else:
        table_style.append(("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF4F7")))
    table.setStyle(TableStyle(table_style))
    return table


def build_mobsf_chinese_pdf(
    report_json: Mapping[str, Any],
    review_bundle: Mapping[str, Any] | None = None,
    file_hash: str = "",
) -> bytes:
    """Build a Chinese PDF suitable for delivery from MobSF static-analysis data."""
    _ensure_chinese_font()
    styles = _report_styles()
    review = dict(review_bundle or {})
    summary = dict(review.get("summary") or {})
    findings = list(review.get("issue_register") or [])
    regression_suite = list(review.get("regression_suite") or [])
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=22 * mm,
        title="移动应用安全测试报告",
        author="QA Toolkit",
    )
    story = [
        Paragraph("移动应用安全测试报告", styles["title"]),
        Paragraph("MobSF 静态分析中文交付版", styles["body"]),
        Spacer(1, 4 * mm),
        Paragraph("应用概览", styles["heading"]),
    ]
    overview_rows = [
        ["应用名称", report_json.get("app_name") or summary.get("app_name")],
        ["包名", report_json.get("package_name")],
        ["版本", report_json.get("version_name") or report_json.get("version")],
        ["文件名", report_json.get("file_name")],
        ["扫描 Hash", file_hash or report_json.get("md5")],
        ["扫描时间", report_json.get("timestamp")],
    ]
    story.append(_table(overview_rows, [34 * mm, 140 * mm], styles))

    story.extend([Spacer(1, 2 * mm), Paragraph("风险摘要", styles["heading"])])
    summary_rows = [
        ["问题总数", "高风险", "中风险", "低风险", "回归场景"],
        [
            summary.get("issue_count", len(findings)),
            summary.get("high", 0),
            summary.get("medium", 0),
            summary.get("low", 0),
            summary.get("regression_case_count", len(regression_suite)),
        ],
    ]
    story.append(_table(summary_rows, [34 * mm] * 5, styles, header=True))

    story.extend([Spacer(1, 2 * mm), Paragraph("问题清单", styles["heading"])])
    issue_rows = [["级别", "分类", "问题", "证据与修复建议"]]
    for finding in findings:
        issue_rows.append(
            [
                str(finding.get("Severity") or "-").upper(),
                finding.get("Category"),
                finding.get("Title"),
                f"证据: {_text(finding.get('Evidence'), 260)}\n建议: {_text(finding.get('Suggested Check'), 180)}",
            ]
        )
    if len(issue_rows) == 1:
        issue_rows.append(["-", "-", "未发现自动归类的问题", "建议结合业务流程继续人工复核。"])
    story.append(_table(issue_rows, [18 * mm, 28 * mm, 38 * mm, 86 * mm], styles, header=True))

    if regression_suite:
        story.extend([Spacer(1, 2 * mm), Paragraph("回归建议", styles["heading"])])
        regression_rows = [["优先级", "场景", "验证重点"]]
        for item in regression_suite:
            regression_rows.append(
                [item.get("Priority"), item.get("Scenario") or item.get("Title"), item.get("Check") or item.get("Focus")],
            )
        story.append(_table(regression_rows, [24 * mm, 62 * mm, 84 * mm], styles, header=True))

    story.append(Spacer(1, 4 * mm))
    story.append(Paragraph("说明：本报告由 QA Toolkit 根据 MobSF JSON 结果二次生成，保留自动发现结论并建议人工复核。", styles["small"]))
    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
