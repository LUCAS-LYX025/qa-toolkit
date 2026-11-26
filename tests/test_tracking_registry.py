"""统一缺陷绩效分析：注册中心契约测试（frozen Spec / 返回副本 / replace / reset / 隔离）。"""
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import tracking_registry as reg  # noqa: E402


@pytest.fixture(autouse=True)
def _reset():
    reg.reset_tracking_registry()
    yield
    reg.reset_tracking_registry()


def test_defaults_include_zentao_first_and_three_cloud_platforms():
    adapters = reg.get_adapters()
    assert "zentao_db" in adapters and "zentao_proxy" in adapters
    assert {"jira", "tapd", "yunxiao"}.issubset(adapters)
    assert list(adapters)[0] == "zentao_db"  # 禅道保持首个默认项，向后兼容
    assert adapters["jira"].factory is not None


def test_specs_are_frozen():
    spec = reg.AdapterSpec("x", "X", "d", "http", ())
    with pytest.raises(FrozenInstanceError):
        spec.key = "y"


def test_getters_return_copies():
    adapters = reg.get_adapters()
    adapters.clear()
    assert "zentao_db" in reg.get_adapters()  # 内部未被外部改动
    fields = list(reg.get_connection_fields("jira"))
    fields.clear()
    assert len(reg.get_connection_fields("jira")) >= 3


def test_duplicate_registration_requires_replace():
    with pytest.raises(ValueError, match="replace=True"):
        reg.register_adapter(reg.AdapterSpec("jira", "J", "d", "http", ()))
    reg.register_adapter(reg.AdapterSpec("jira", "J2", "d", "http", ()), replace=True)
    assert reg.get_adapter("jira").label == "J2"


def test_connection_fields_are_declarative_and_password_marked():
    fields = {f.key: f for f in reg.get_connection_fields("jira")}
    assert fields["token"].kind == "password"
    creds, warnings = reg.redact_connection_config("jira", {"base_url": "https://x", "token": "SECRET"})
    assert creds["token"] == "" and warnings


def test_attribution_sla_performance_rules_registerable_and_isolated():
    reg.register_attribution(reg.AttributionRuleSpec("custom_t", "自定义", ("assignee",), "opened_at", "closed_at"))
    assert "custom_t" in reg.get_attributions()
    reg.register_sla_rule(reg.SlaRuleSpec("sla_t", "SLA T", high_priority_values=(3,)))
    assert reg.get_sla_rule("sla_t").high_priority_values == (3,)
    reg.register_performance_rule(reg.PerformanceRuleSpec("perf_t", "P", rate_denominator="timeout_only"))
    assert reg.get_performance_rule("perf_t").rate_denominator == "timeout_only"


def test_reset_restores_defaults():
    reg.unregister_adapter("jira")
    assert "jira" not in reg.get_adapters()
    reg.reset_tracking_registry()
    assert "jira" in reg.get_adapters()


def test_create_adapter_rejects_unknown_and_listed_only():
    with pytest.raises(ValueError, match="未知数据源"):
        reg.create_adapter("nope", {})
    reg.register_adapter(reg.AdapterSpec("listed", "仅登记", "d", "http", (), None, False))
    with pytest.raises(ValueError, match="仅登记"):
        reg.create_adapter("listed", {})


def test_work_item_state_normalization():
    assert reg.normalize_work_item_state("Closed") == "CLOSED"
    assert reg.normalize_work_item_state("in_progress") == "ACTIVE"
    assert reg.normalize_work_item_state(None) == "UNKNOWN"


def test_http_connection_fields_cover_project_timeout_and_ssl():
    jira = {f.key: f for f in reg.get_connection_fields("jira")}
    assert "project_key" in jira and "timeout_seconds" in jira
    for key in ("tapd", "yunxiao"):
        fields = {f.key: f for f in reg.get_connection_fields(key)}
        assert "timeout_seconds" in fields and "verify_ssl" in fields
        assert fields["verify_ssl"].kind == "select"


def test_registry_summary_distinguishes_live_capabilities():
    summary = reg.get_registry_summary()
    assert isinstance(summary["已接入数据源"], list)
    assert "jira" in summary["已接入数据源"]
    assert summary["默认校验 SSL"] is True
    assert summary["默认产物保留凭据"] is False
