import io
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.tools.bi_analysis import BIAnalyzer


class FakeUploadFile:
    def __init__(self, name: str, data: bytes):
        self.name = name
        self._data = data
        self.size = len(data)

    def getvalue(self) -> bytes:
        return self._data


def build_excel_upload() -> FakeUploadFile:
    summary_df = pd.DataFrame({"name": ["overview"], "count": [1]})
    detail_df = pd.DataFrame({
        " request_time ": ["2026-04-01 10:00:01", "2026-04-01 10:00:03"],
        "status_code": [200, 500],
        "payload": ['{"channel":"ios"}', '{"channel":"web"}'],
    })
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        summary_df.to_excel(writer, sheet_name="概览", index=False)
        detail_df.to_excel(writer, sheet_name="明细", index=False)
    buffer.seek(0)
    return FakeUploadFile("bi-report.xlsx", buffer.getvalue())


def test_load_data_reads_selected_excel_sheet_and_normalizes_columns():
    tool = BIAnalyzer()
    uploaded_file = build_excel_upload()

    sheet_names = tool.get_excel_sheet_names(uploaded_file)
    df, message = tool.load_data(uploaded_file, sheet_name="明细")

    assert sheet_names == ["概览", "明细"]
    assert message == "数据加载成功"
    assert df.columns.tolist() == ["request_time", "status_code", "payload"]
    assert df["status_code"].tolist() == [200, 500]


def test_build_analysis_context_detects_datetime_and_json_columns():
    tool = BIAnalyzer()
    df = tool.get_template_dataframe("开发接口日志")

    context = tool.build_analysis_context(df)

    assert "request_time" in context["datetime_columns"]
    assert "payload" in context["json_columns"]
    assert "status_code" in context["numeric_columns"]
    assert context["quality_report"]["summary"]["JSON字段数"] == 1


def test_build_validation_report_flags_common_data_issues():
    tool = BIAnalyzer()
    df = pd.DataFrame({
        "id": [1, 1, 3],
        "amount": [100, -20, 30],
        "event_time": ["2026-04-01 10:00:00", "not-a-date", "2026-04-01 11:00:00"],
        "required_name": ["A", None, "C"],
        "mostly_null": [None, None, "x"],
    })

    report = tool.build_validation_report(
        df,
        required_columns=["required_name"],
        unique_key_columns=["id"],
        non_negative_columns=["amount"],
        datetime_columns=["event_time"],
        null_ratio_threshold=50.0,
    )

    issue_pairs = {(row["规则"], row["字段"]) for _, row in report["issues"].iterrows()}

    assert ("必填字段空值", "required_name") in issue_pairs
    assert ("唯一键重复", "id") in issue_pairs
    assert ("非负数校验", "amount") in issue_pairs
    assert ("时间格式校验", "event_time") in issue_pairs
    assert ("缺失率阈值", "mostly_null") in issue_pairs
    assert report["duplicate_sample"] is not None


def test_expand_json_column_and_apply_quick_filter_support_dev_log_data():
    tool = BIAnalyzer()
    df = tool.get_template_dataframe("开发接口日志")

    expanded_df, stats = tool.expand_json_column(df, "payload", row_limit=3)
    filtered_df = tool.apply_quick_filter(df, "status_code", "大于等于", "500")

    assert stats["成功行数"] == 3
    assert stats["展开字段数"] == 3
    assert "channel" in expanded_df.columns
    assert filtered_df["status_code"].tolist() == [500, 504]


def test_build_scenario_insights_for_testing_dataset():
    tool = BIAnalyzer()
    df = tool.get_template_dataframe("测试执行结果")
    context = tool.build_analysis_context(df)

    insights = tool.build_scenario_insights(df, context)
    card_map = {item["label"]: item["value"] for item in insights["cards"]}
    table_titles = [item["title"] for item in insights["tables"]]

    assert "测试执行" in insights["scenarios"]
    assert card_map["通过率"] == "50.0%"
    assert card_map["缺陷总数"] == "1"
    assert "模块执行概览" in table_titles


def test_build_scenario_insights_for_development_logs():
    tool = BIAnalyzer()
    df = tool.get_template_dataframe("开发接口日志")
    context = tool.build_analysis_context(df)

    insights = tool.build_scenario_insights(df, context)
    card_map = {item["label"]: item["value"] for item in insights["cards"]}
    table_titles = [item["title"] for item in insights["tables"]]

    assert "开发日志" in insights["scenarios"]
    assert card_map["错误率"] == "50.0%"
    assert "状态码分布" in table_titles
    assert "慢接口 / 服务 Top 10" in table_titles
