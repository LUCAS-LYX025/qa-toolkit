"""BI 数据分析工具专项审计回归测试（issues #134-#151）。"""
import io
import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core import bi_registry
from qa_toolkit.tools import bi_analysis as bi_module
from qa_toolkit.tools.bi_analysis import (
    BIAnalyzer,
    cached_template_payloads,
    duration_display_value,
    filter_profile_by_keyword,
    limit_correlation_columns,
    pivot_column_overflow,
    safe_csv_bytes,
    resolve_export_frame,
)
from qa_toolkit.ui.pages import bi_analysis_page as page
from qa_toolkit.ui.pages.bi_analysis_page import dataset_signature


class FakeUploadFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data


@pytest.fixture(autouse=True)
def _clean_registry_and_caches():
    bi_registry.reset_bi_registry()
    cached_template_payloads.clear()
    page.cached_analysis_context.clear()
    yield
    bi_registry.reset_bi_registry()
    cached_template_payloads.clear()
    page.cached_analysis_context.clear()


def _tool():
    return BIAnalyzer()


# #134 HTML 报告 XSS
def test_issue_134_html_report_escapes_uploaded_content():
    payload = "<img src=x onerror=alert(1)>"
    df = pd.DataFrame({"产品": [payload], "销售额": [10]})
    report = _tool().generate_html_report(df)
    assert payload not in report
    assert "&lt;img" in report
    assert "<img" not in report


# #135 快速过滤正则崩溃
def test_issue_135_filter_uses_literal_match_with_opt_in_regex():
    tool = _tool()
    df = pd.DataFrame({"名称": ["abc", "(test)", "a*b"]})
    literal = tool.apply_quick_filter(df, "名称", "包含", "(")
    assert literal["名称"].tolist() == ["(test)"]
    assert "正则匹配" in tool.get_filter_operators(df["名称"])
    regex_hit = tool.apply_quick_filter(df, "名称", "正则匹配", "^a.*")
    assert set(regex_hit["名称"]) == {"abc", "a*b"}
    assert tool.apply_quick_filter(df, "名称", "正则匹配", "(").empty
    assert tool.apply_quick_filter(df, "数值" if "数值" in df else "名称", "包含", "a").shape[0] == 2


# #136 CSV 公式注入
def test_issue_136_csv_export_neutralizes_formula_payloads():
    df = pd.DataFrame({
        "文本": ["=1+1", "+SUM(A1:A2)", "@cmd", "normal"],
        "数值": [-5, 2, 3, 4],
    })
    output = safe_csv_bytes(df).decode("utf-8-sig")
    for payload in ("=1+1", "+SUM(A1:A2)", "@cmd"):
        assert f"'{payload}" in output
    assert "normal" in output
    assert "-5" in output


# #137 重复列名崩溃
def test_issue_137_duplicate_columns_are_renamed_on_load():
    tool = _tool()
    upload = FakeUploadFile("dup.csv", "id,id,val,val\n1,2,a,b\n".encode())
    df, message = tool.load_data(upload)
    assert df is not None
    assert df.columns.tolist() == ["id", "id__2", "val", "val__2"]
    assert "重命名重复列" in message
    assert tool.build_analysis_context(df)["overview"]["总行数"] == 1


# #138 纯数字日期识别
def test_issue_138_numeric_datetime_columns_are_detected():
    tool = _tool()
    df = pd.DataFrame({
        "dt": ["20260401", "20260402", "20260403"],
        "ts": ["20260401100000", "20260402100000", "20260403100000"],
        "uid": [1001, 1002, 1003],
    })
    context = tool.build_analysis_context(df)
    assert "dt" in context["datetime_columns"]
    assert "ts" in context["datetime_columns"]
    assert "uid" not in context["datetime_columns"]


# #139 通过率分母含空值
def test_issue_139_pass_rate_uses_valid_results_only():
    tool = _tool()
    df = pd.DataFrame({"执行结果": ["通过", "失败", None, "  "]})
    context = tool.build_analysis_context(df)
    cards = tool.build_scenario_insights(df, context)["cards"]
    card = next(item for item in cards if item["label"] == "通过率")
    assert card["value"] == "50.0%"
    assert card["detail"] == "1 / 2"


# #140 分号 CSV 单列 / 显式解析选项
def test_issue_140_csv_delimiter_sniffing_and_override():
    tool = _tool()
    semicolon = tool._load_csv_bytes("日期;产品;销售额\n2026-04-01;A;100\n".encode())
    assert semicolon.columns.tolist() == ["日期", "产品", "销售额"]
    tab = tool._load_csv_bytes("a\tb\tc\n1\t2\t3\n".encode())
    assert tab.columns.tolist() == ["a", "b", "c"]
    upload = FakeUploadFile("manual.csv", "a;b\n1;2\n".encode())
    frame, _ = tool.load_data(upload, delimiter=";")
    assert frame.columns.tolist() == ["a", "b"]


# #141 code 关键词误匹配
def test_issue_141_unrelated_code_columns_are_not_status_codes():
    tool = _tool()
    df = pd.DataFrame({
        "area_code": ["110000", "310000"],
        "zip_code": ["100000", "200000"],
        "value": [1, 2],
    })
    context = tool.build_analysis_context(df)
    assert "开发日志" not in tool.build_scenario_insights(df, context)["scenarios"]
    assert tool._column_for_scenario(df, "开发日志", ["status_code", "code"]) is None

    with_status = pd.DataFrame({"status_code": [200, 500], "value": [1, 2]})
    assert tool._column_for_scenario(with_status, "开发日志", ["status_code", "code"]) == "status_code"


# #142 透视列维度无上限
def test_issue_142_pivot_high_cardinality_is_blocked():
    df = pd.DataFrame({
        "低基数": ["a", "b"] * 40,
        "高基数": [f"c{i}" for i in range(80)],
        "值": list(range(80)),
    })
    assert pivot_column_overflow(df, "高基数") == 80
    assert pivot_column_overflow(df, "低基数") is None
    assert pivot_column_overflow(df, "无") is None


# #143 相关性无字段上限
def test_issue_143_correlation_columns_are_capped():
    columns, truncated = limit_correlation_columns([f"n{i}" for i in range(60)])
    assert len(columns) == 20
    assert truncated is True
    short, truncated = limit_correlation_columns(["a", "b"])
    assert short == ["a", "b"]
    assert truncated is False


# #144 context 无缓存
def test_issue_144_analysis_context_is_cached(monkeypatch):
    calls = []
    original = BIAnalyzer.build_analysis_context

    def counting(self, frame):
        calls.append(1)
        return original(self, frame)

    monkeypatch.setattr(BIAnalyzer, "build_analysis_context", counting)
    frame = _tool().get_template_dataframe("通用销售分析")
    first = page.cached_analysis_context("sig-1", frame)
    second = page.cached_analysis_context("sig-1", frame)
    assert len(calls) == 1
    assert first["overview"] == second["overview"]
    page.cached_analysis_context("sig-2", frame)
    assert len(calls) == 2


# #145 空数据集仍展示完整分析页
def empty_dataset_app():
    import pandas as pd
    import streamlit as st
    from qa_toolkit.ui.pages import bi_analysis_page as target

    target._ensure_defaults()
    st.session_state.bi_loaded_df = pd.DataFrame(columns=["日期", "销售额"])
    st.session_state.bi_loaded_signature = "empty-sig"
    target.render_bi_analysis_page()


def test_issue_145_empty_dataset_shows_warning_without_tabs():
    at = AppTest.from_function(empty_dataset_app).run()
    assert not at.exception
    assert any("没有数据行" in warning.value for warning in at.warning)
    assert len(at.tabs) == 0


# #146 模板每次 rerun 重复生成
def test_issue_146_template_payloads_are_cached(monkeypatch):
    calls = []
    original = bi_registry.build_template_frame

    def counting(name):
        calls.append(name)
        return original(name)

    monkeypatch.setattr(bi_registry, "build_template_frame", counting)
    first = cached_template_payloads("通用销售分析")
    second = cached_template_payloads("通用销售分析")
    assert len(calls) == 1
    assert first == second


# #147 拓展性注册表
def test_issue_147_registry_supports_new_scenarios_charts_aggregators_and_templates():
    import plotly.express as px

    calls = []

    def builder(frame, x, y, color=None):
        calls.append((x, y))
        return px.bar(frame, x=x, y=y, color=color)

    bi_registry.register_chart("桑基图", builder)
    bi_registry.register_aggregator("p95", lambda series: series.quantile(0.95))
    bi_registry.register_template("供应链履约", "测试模板", lambda: pd.DataFrame({"a": [1]}))
    bi_registry.register_scenario(bi_registry.ScenarioRule("供应链", ["履约状态", "fulfillment"]))

    assert "桑基图" in bi_registry.chart_names()
    assert callable(bi_registry.resolve_aggregator("p95"))
    assert bi_registry.build_template_frame("供应链履约").equals(pd.DataFrame({"a": [1]}))
    figure = bi_registry.build_chart(
        "桑基图", pd.DataFrame({"x": [1], "y": [2]}), x="x", y="y"
    )
    assert calls == [("x", "y")]
    assert figure is not None

    rule = next(item for item in bi_registry.scenario_rules() if item.name == "供应链")
    frame = pd.DataFrame({"履约状态": ["完成", "延迟"], "v": [1, 2]})
    assert bi_registry.find_registered_columns(frame, rule, str) == "履约状态"


# #148 导出范围与 HTML 洞察明细
def test_issue_148_export_follows_filtered_data_and_html_keeps_insight_tables():
    tool = _tool()
    raw = pd.DataFrame({"模块": ["登录", "支付", "搜索"], "结果": ["通过", "通过", "失败"]})
    filtered = raw.head(1)
    chosen, label = resolve_export_frame("过滤结果", {"bi_filtered_preview": filtered}, raw)
    assert label == "过滤结果"
    assert len(chosen) == 1
    fallback, label = resolve_export_frame("过滤结果", {}, raw)
    assert label == "原始数据"
    assert fallback is raw

    context = tool.build_analysis_context(raw)
    insights = tool.build_scenario_insights(raw, context)
    assert insights["tables"]
    report = tool.generate_html_report(raw, context, insights=insights)
    assert "洞察明细" in report
    assert any(table["title"] in report for table in insights["tables"])


# #149 耗时单位
def test_issue_149_duration_metrics_show_units():
    assert duration_display_value("response_ms", 2752.2)[0] == "2752.20 ms"
    assert duration_display_value("耗时分钟", 12)[0] == "12.00 min"
    assert duration_display_value("duration_s", 3)[0] == "3.00 s"
    assert duration_display_value("duration", 3)[0] == "3.00"


# #150 字段搜索正则崩溃
def test_issue_150_field_search_is_literal():
    profile = pd.DataFrame({"列名": ["abc", "日期", "(test)"], "数据类型": ["object"] * 3})
    assert filter_profile_by_keyword(profile, "(")["列名"].tolist() == ["(test)"]
    assert filter_profile_by_keyword(profile, "日期")["列名"].tolist() == ["日期"]
    assert len(filter_profile_by_keyword(profile, "")) == 3


# #151 数据集签名无内容哈希
def test_issue_151_signature_includes_content_digest():
    first = FakeUploadFile("data.csv", "a,b\n1,2\n".encode())
    second = FakeUploadFile("data.csv", "a,b\n3,4\n".encode())
    assert first.size == second.size
    assert dataset_signature(first, "") != dataset_signature(second, "")
    assert dataset_signature(first, "Sheet1") != dataset_signature(first, "Sheet2")
