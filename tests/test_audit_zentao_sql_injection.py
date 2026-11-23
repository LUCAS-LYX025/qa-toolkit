"""QA 审计补充：禅道 SQL 构造对所有外部参数的注入防护回归（issue #83）。"""
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter  # noqa: E402


@pytest.fixture
def exporter():
    return ZenTaoPerformanceExporter.__new__(ZenTaoPerformanceExporter)


@pytest.mark.parametrize("method", ["build_dev_query", "build_qa_query"])
@pytest.mark.parametrize("field", [
    "normal_priority_normal_hours",
    "normal_priority_overtime_hours",
    "high_priority_overtime_hours",
    "weekend_hours",
])
def test_numeric_config_fields_reject_injection(exporter, method, field):
    """数值型配置注入字符串时，不得出现在最终 SQL 中。"""
    config = {field: "1 OR 1=1; DROP TABLE zt_task; --"}
    try:
        sql = getattr(exporter, method)(1, "2026-01-01", "2026-01-31", config)
    except ValueError:
        return  # 拒绝注入是正确行为
    assert "DROP TABLE" not in sql.upper()
    assert "OR 1=1" not in sql.upper()


@pytest.mark.parametrize("method", ["build_dev_query", "build_qa_query"])
def test_date_fields_reject_injection(exporter, method):
    """日期参数注入不得进入 SQL。"""
    try:
        sql = getattr(exporter, method)(
            1, "2026-01-01' OR '1'='1", "2026-01-31", {}
        )
    except ValueError:
        return  # 拒绝注入是正确行为
    assert "OR '1'='1" not in sql.upper()
    assert "DROP TABLE" not in sql.upper()


@pytest.mark.parametrize("method", ["build_dev_query", "build_qa_query"])
def test_product_id_rejects_injection(exporter, method):
    """product_id 注入不得进入 SQL。"""
    try:
        sql = getattr(exporter, method)("1 OR 1=1", date(2026, 1, 1), date(2026, 1, 31), {})
    except (ValueError, TypeError):
        return  # 拒绝注入是正确行为
    assert "OR 1=1" not in sql.upper()
