import sys
from datetime import date, datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter  # noqa: E402


class _RecordingCursor:
    def __init__(self):
        self.last_query = ""
        self.last_params = None

    def execute(self, query, params=None):
        self.last_query = str(query)
        self.last_params = params


class _FakeMysqlDB:
    def __init__(self):
        self.cur = _RecordingCursor()

    @staticmethod
    def fetchall_to_dict():
        return []


def _build_config(**overrides):
    config = {
        "exclude_types": ["codeerror"],
        "roles": ["qa"],
        "high_priority_normal_hours": 4,
        "high_priority_weekend_hours": 48,
        "normal_priority_normal_hours": 24,
        "normal_priority_weekend_hours": 72,
        "holiday_country": None,
    }
    config.update(overrides)
    return config


def test_build_qa_query_rejects_injected_start_date():
    exporter = ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)

    with pytest.raises(ValueError, match="start_date"):
        exporter.build_qa_query(
            1,
            "2026-01-01' OR 1=1 --",
            "2026-01-31",
            _build_config(),
        )


def test_build_dev_query_rejects_non_numeric_threshold():
    exporter = ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)

    with pytest.raises(ValueError, match="high_priority_normal_hours"):
        exporter.build_dev_query(
            1,
            "2026-01-01",
            "2026-01-31",
            _build_config(high_priority_normal_hours="1 OR 1=1"),
        )


def test_build_qa_query_normalizes_date_inputs():
    exporter = ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)

    query = exporter.build_qa_query(
        1,
        datetime(2026, 1, 1, 8, 30),
        date(2026, 1, 31),
        _build_config(),
    )

    assert "openedDate BETWEEN '2026-01-01' AND '2026-01-31'" in query


def test_build_qa_query_rejects_reversed_date_range():
    exporter = ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)

    with pytest.raises(ValueError, match="start_date 不能晚于 end_date"):
        exporter.build_qa_query(
            1,
            "2026-02-01",
            "2026-01-31",
            _build_config(),
        )


def test_query_timeout_detail_uses_realname_or_account_filter():
    exporter = ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)
    exporter.mysql_db = _FakeMysqlDB()

    result = exporter.query_timeout_bugs_detail(
        developer_name="dev.account",
        product_id=1,
        start_date="2026-01-01",
        end_date="2026-01-31",
        config=_build_config(),
    )

    assert result is not None
    assert "(u.realname = %s OR u.account = %s)" in exporter.mysql_db.cur.last_query
    assert exporter.mysql_db.cur.last_params == ("dev.account", "dev.account", 1, "2026-01-01", "2026-01-31")


def test_query_qa_timeout_detail_uses_realname_or_account_filter():
    exporter = ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)
    exporter.mysql_db = _FakeMysqlDB()

    result = exporter.query_qa_timeout_bugs_detail(
        tester_name="qa.account",
        product_id=1,
        start_date="2026-01-01",
        end_date="2026-01-31",
        config=_build_config(),
    )

    assert result is not None
    assert "(u.realname = %s OR u.account = %s)" in exporter.mysql_db.cur.last_query
    assert exporter.mysql_db.cur.last_params == ("qa.account", "qa.account", 1, "2026-01-01", "2026-01-31")
