#!/usr/bin/env python3
"""通用缺陷绩效分析专项审计探针。

站在测试专家 + 产品工程师视角，对「注册中心 / 统一模型 / 规则引擎 / 5 适配器 / 通用页面」
逐条坐实问题。修复前应为 N/N 坐实，全部修复后应为 0/N。
"""
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import tracking_registry as reg  # noqa: E402
from qa_toolkit.integrations.tracking import rules  # noqa: E402
from qa_toolkit.integrations.tracking.models import QuerySpec, WorkItem  # noqa: E402

PAGE = ROOT / "src/qa_toolkit/ui/pages/tracking_performance_page.py"
PAGE_SRC = PAGE.read_text(encoding="utf-8")
DB_SRC = (ROOT / "src/qa_toolkit/integrations/tracking/adapters/zentao_db.py").read_text(encoding="utf-8")
PROXY_SRC = (ROOT / "src/qa_toolkit/integrations/tracking/adapters/zentao_proxy.py").read_text(encoding="utf-8")
JIRA_SRC = (ROOT / "src/qa_toolkit/integrations/tracking/adapters/jira.py").read_text(encoding="utf-8")

RESULTS = {}


def record(item, reproduced, note=""):
    RESULTS[item] = bool(reproduced)
    flag = "REPRODUCED" if reproduced else "resolved"
    print(f"  [{flag}] {item} {note}", flush=True)


def _item(**overrides):
    base = dict(
        id="BUG-1", title="登录缺陷", source="jira", item_type="缺陷",
        severity=3, priority=3, reporter="报告人",
        assignee="开发A", resolver="开发A", closer="测试A",
        opened_at=datetime(2026, 1, 5, 9),
        resolved_at=datetime(2026, 1, 5, 11),
        closed_at=datetime(2026, 1, 5, 13),
    )
    base.update(overrides)
    return WorkItem(**base)


def probe_01_page_missing_show_doc_import():
    """页面首屏直接 NameError，全部功能不可用。"""
    from streamlit.testing.v1 import AppTest
    script = f"""
import sys
sys.path.insert(0, {str(ROOT / 'src')!r})
from qa_toolkit.ui.pages.tracking_performance_page import render_tracking_performance_page
render_tracking_performance_page()
"""
    app = AppTest.from_string(script, default_timeout=8).run()
    messages = [str(getattr(e, "value", "")) for e in app.exception]
    record("TRACK-01", any("show_doc" in m for m in messages), f"异常={messages[:2]}")


def probe_02_sla_inclusive_hour_off_by_one():
    """9:00→12:00 应为 3 小时，实际按闭区间算成 4 小时。"""
    hours, _ = rules.compute_effective_hours(datetime(2026, 1, 5, 9), datetime(2026, 1, 5, 12))
    record("TRACK-02", hours != 3.0, f"9:00→12:00 得到 {hours} 小时")


def probe_03_role_filter_and_people_metadata_dead():
    """页面角色循环空转，rules 忽略 QuerySpec.roles，人员角色标签永远 '—'。"""
    items = [_item(id="A", assignee="开发A", resolver="开发A"),
             _item(id="B", assignee="开发B", resolver="开发B")]
    rows, _, _ = rules.compute_performance(
        items, attribution_key="dev", query=QuerySpec(roles=("开发B",)))
    ignored = len(rows) == 2 and any(r.person.display_name == "开发A" for r in rows)
    page_dead = "pass" in PAGE_SRC and "multiselect" not in PAGE_SRC and "people=" not in PAGE_SRC
    label_dead = rows[0].role_label == "—"
    record("TRACK-03", ignored and page_dead and label_dead,
           f"角色过滤后人数={len(rows)}，页面空循环={page_dead}，角色标签={rows[0].role_label!r}")


def probe_04_zentao_adapters_keep_plaintext_credentials():
    """两个禅道适配器把明文密码存进 self.config，HTTP 适配器却已脱敏。"""
    db_bad = "self.config = cfg" in DB_SRC and "redact_connection_config" not in DB_SRC
    proxy_bad = "self.config = cfg" in PROXY_SRC and "redact_connection_config" not in PROXY_SRC
    record("TRACK-04", db_bad and proxy_bad, f"db={db_bad}, proxy={proxy_bad}")


def probe_05_performance_dimension_registration_has_no_consumer():
    """绩效维度可注册，但全仓库没有任何消费者，注册点空转。"""
    reg.reset_tracking_registry()
    reg.register_performance_dimension("track_dim", "审计自定义维度")
    registered = "track_dim" in reg.get_performance_dimensions()
    consumers = []
    for path in (ROOT / "src").rglob("*.py"):
        if path.name == "tracking_registry.py":
            continue
        try:
            if "get_performance_dimensions" in path.read_text(encoding="utf-8"):
                consumers.append(str(path.relative_to(ROOT)))
        except (OSError, UnicodeDecodeError):
            continue
    record("TRACK-05", registered and not consumers, f"消费者={consumers}")


def probe_06_jira_project_key_not_declarative():
    """JIRA roles 路径依赖 project_key，但该字段未声明，页面无法配置。"""
    keys = {f.key for f in reg.get_connection_fields("jira")}
    bad = "project_key" not in keys and "project_key" in JIRA_SRC
    record("TRACK-06", bool(bad), f"连接字段={sorted(keys)}")


def probe_07_custom_sla_hours_key_shadowed_by_legacy_keys():
    """自定义 SLA 的 hours_key 被页面固定下发的 legacy 键遮蔽。"""
    reg.reset_tracking_registry()
    reg.register_sla_rule(reg.SlaRuleSpec(
        "track_custom_sla", "自定义阈值键", normal_hours_key="custom_normal"), replace=True)
    rows, details, _ = rules.compute_performance(
        [_item(resolved_at=datetime(2026, 1, 5, 13))],
        attribution_key="dev", sla_key="track_custom_sla",
        query=QuerySpec(sla={"custom_normal": 1, "normal_normal": 72}))
    record("TRACK-07", not details,
           f"自定义阈值=1h、legacy=72h、实际耗时4h、超时明细={len(details)}")


def probe_08_http_adapters_missing_timeout_and_ssl_fields():
    """TAPD / 云效连接字段没有超时与 SSL 开关，内网自签/慢服务无法配置。"""
    missing = []
    for key in ("tapd", "yunxiao"):
        fields = {f.key for f in reg.get_connection_fields(key)}
        if "timeout_seconds" not in fields or "verify_ssl" not in fields:
            missing.append(key)
    record("TRACK-08", bool(missing), f"缺失字段的数据源={missing}")


def probe_09_submitted_column_always_zero():
    """qa/dev 归因下，'提交数' 恒为 0，因为 reporter 与归因人员不同。"""
    rows, _, _ = rules.compute_performance([_item()], attribution_key="qa")
    bad = hasattr(rows[0], "submitted") or "提交数" in rows[0].as_record()
    record("TRACK-09", bad,
           f"归因人={rows[0].person.display_name}，导出列={list(rows[0].as_record())}")


def probe_10_generic_page_shows_zentao_only_docs():
    """通用页面仍复用禅道专属文档，多数据源用户被误导。"""
    doc_src = (ROOT / "src/qa_toolkit/support/documentation.py").read_text(encoding="utf-8")
    bad = 'show_doc("tracking_performance")' not in PAGE_SRC or '"tracking_performance"' not in doc_src
    record("TRACK-10", bad, "通用页面仍展示禅道专属文档" if bad else "已切换到通用文档")


def probe_11_connection_error_feedback_is_explicit():
    """连接失败必须给出明确结论，而不是通用「请先确认」警告。"""
    bad = 'render_error_feedback(f"数据源连接失败：{meta_err}")' not in PAGE_SRC
    record("TRACK-11", bad, "连接失败仅展示通用警告" if bad else "已展示明确连接失败结论")


def main():
    print("=== 通用缺陷绩效分析专项审计探针（11 项） ===", flush=True)
    reg.reset_tracking_registry()
    probe_01_page_missing_show_doc_import()
    probe_02_sla_inclusive_hour_off_by_one()
    probe_03_role_filter_and_people_metadata_dead()
    probe_04_zentao_adapters_keep_plaintext_credentials()
    probe_05_performance_dimension_registration_has_no_consumer()
    probe_06_jira_project_key_not_declarative()
    probe_07_custom_sla_hours_key_shadowed_by_legacy_keys()
    probe_08_http_adapters_missing_timeout_and_ssl_fields()
    probe_09_submitted_column_always_zero()
    probe_10_generic_page_shows_zentao_only_docs()
    probe_11_connection_error_feedback_is_explicit()
    reg.reset_tracking_registry()
    reproduced = sum(1 for v in RESULTS.values() if v)
    total = len(RESULTS)
    print(f"共 {reproduced}/{total} 项坐实（修复前应为 {total}/{total}，修复后应为 0/{total}）", flush=True)
    for item, flag in RESULTS.items():
        if flag:
            print(f"  - 待修: {item}", flush=True)


if __name__ == "__main__":
    main()
