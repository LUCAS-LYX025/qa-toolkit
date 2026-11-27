"""验收驱动工作流专项回归：注册中心 / 独立校验 / 签字门槛 / UI 渲染。"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.task_runner import (  # noqa: E402
    RUN_STATUS_SUCCESS,
    TaskRunCenter,
)
from qa_toolkit.core.verification import (  # noqa: E402
    artifact_to_text,
    verify_criteria,
    verify_workflow,
    workflow_options,
)
from qa_toolkit.core.workflow_registry import (  # noqa: E402
    CriterionSpec,
    WorkflowSpec,
    get_workflow,
    get_workflow_summary,
    list_workflows,
    register_workflow,
    reset_workflows,
)
from qa_toolkit.core.workflow_registry import _BUILTIN_WORKFLOWS  # noqa: E402


@pytest.fixture(autouse=True)
def _clean_registry():
    reset_workflows()
    yield
    reset_workflows()


# ---- 注册中心 ----

def test_builtin_workflows_expose_acceptance_criteria():
    summary = get_workflow_summary()
    assert summary["工作流总数"] == len(_BUILTIN_WORKFLOWS)
    assert summary["启用中"] >= 4
    assert summary["验收标准总数"] >= 16
    assert summary["人工确认项"] >= 2
    assert set(list_workflows()) == {spec.key for spec in _BUILTIN_WORKFLOWS}


def test_workflow_filter_includes_generic_for_specific_tool():
    keys = set(list_workflows(tool="测试用例生成器"))
    assert "test_case_delivery" in keys
    assert "generic_output" in keys
    assert "api_case_delivery" not in keys


def test_register_requires_explicit_replace_and_reset_restores_builtins():
    spec = WorkflowSpec(key="custom", name="自定义", criteria=(CriterionSpec("c", "非空", "non_empty"),))
    register_workflow(spec)
    with pytest.raises(ValueError):
        register_workflow(spec)
    register_workflow(WorkflowSpec(key="custom", name="改后", source="user"), replace=True)
    assert get_workflow("custom").name == "改后"
    reset_workflows()
    assert get_workflow("custom") is None
    assert get_workflow("generic_output") is not None


def test_workflow_options_are_stable_and_labeled():
    keys, labels = workflow_options("测试用例生成器")
    assert keys == sorted(keys, key=lambda k: (list_workflows(tool="测试用例生成器")[k].tool != "", k))
    assert all(labels[key] for key in keys)


# ---- 独立校验 ----

def test_checkers_cover_content_placeholders_secrets_and_json():
    specs = (
        CriterionSpec("non_empty", "非空", "non_empty"),
        CriterionSpec("min", "长度", "min_chars", expected=10),
        CriterionSpec("all", "齐全", "contains_all", expected=["步骤", "预期"]),
        CriterionSpec("any", "任一", "contains_any", expected=["步骤", "assert"]),
        CriterionSpec("no", "禁用", "not_contains", expected=["示例"]),
        CriterionSpec("ph", "占位", "no_placeholder"),
        CriterionSpec("sec", "凭据", "no_secret"),
        CriterionSpec("json", "JSON", "json_parseable"),
    )
    good = '{"步骤": "打开页面", "预期": "成功"}'
    report = verify_criteria(specs, good)
    assert report.automated_passed
    assert all(item.passed for item in report.results)

    bad = "TODO: 示例 password=abcdefghijk sk-abcdefghijklmnopqrstuvwxyz"
    failed = verify_criteria(specs, bad)
    assert not failed.automated_passed
    evidence = " ".join(item.evidence for item in failed.results)
    assert "占位符" in evidence and "泄漏" in evidence


def test_json_checker_accepts_fenced_and_embedded_json():
    fenced = '```json\n{"a": 1}\n```'
    assert verify_criteria((CriterionSpec("j", "JSON", "json_parseable"),), fenced).automated_passed
    embedded = '结果如下：\n{"a": [1, 2]}\n以上。'
    assert verify_criteria((CriterionSpec("j", "JSON", "json_parseable"),), embedded).automated_passed
    assert not verify_criteria((CriterionSpec("j", "JSON", "json_parseable"),), "not json").automated_passed


def test_manual_check_never_passes_automatically():
    report = verify_workflow("test_case_delivery", "# 用例\n步骤\n预期\n" + "x" * 100)
    assert report.automated_passed
    assert report.manual_pending == 1
    manual = [item for item in report.results if item.manual][0]
    assert not manual.passed
    assert "签字" in manual.evidence


def test_unknown_workflow_returns_none_and_artifact_normalization():
    assert verify_workflow("missing", "x") is None
    assert artifact_to_text(None) == ""
    assert artifact_to_text({"a": 1}) == '{\n  "a": 1\n}'
    assert artifact_to_text(b"abc") == "abc"


# ---- 运行中心签字门槛 ----

def _seed_run(center: TaskRunCenter, artifact: str, tool: str = "测试用例生成器") -> str:
    info = center.submit(tool, "生成用例", {"case": "demo"}, lambda: artifact)
    return info["run_id"]


def test_sign_off_requires_success_report_and_automated_pass(tmp_path: Path):
    center = TaskRunCenter(history_file=tmp_path / "runs.jsonl")
    run_id = _seed_run(center, "# 用例\n步骤\n预期\n" + "x" * 100)

    assert center.sign_off(run_id, by="雷宇兴") is False  # 还没验收
    report = verify_workflow("test_case_delivery", center.get_run(run_id)["result_preview"])
    center.attach_verification(run_id, report.to_dict())

    signed = center.sign_off(run_id, by="雷宇兴", note="语义覆盖已确认")
    assert signed is True
    record = center.get_run(run_id)
    assert record["status"] == RUN_STATUS_SUCCESS
    assert record["signed_off_by"] == "雷宇兴"
    assert record["sign_off_note"] == "语义覆盖已确认"
    assert record["signed_off_at"]

    events = [json.loads(line)["event"] for line in (tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "verification" in events and "sign_off" in events


def test_failed_automated_check_blocks_sign_off(tmp_path: Path):
    center = TaskRunCenter(history_file=tmp_path / "runs.jsonl")
    run_id = _seed_run(center, "TODO sk-abcdefghijklmnopqrstuvwxyz")
    report = verify_workflow("test_case_delivery", center.get_run(run_id)["result_preview"])
    assert not report.automated_passed
    center.attach_verification(run_id, report.to_dict())
    assert center.sign_off(run_id) is False
    assert not center.get_run(run_id)["signed_off_at"]


def test_revoke_sign_off_keeps_report_and_audit(tmp_path: Path):
    center = TaskRunCenter(history_file=tmp_path / "runs.jsonl")
    run_id = _seed_run(center, '{"a": 1}')
    report = verify_workflow("json_output", center.get_run(run_id)["result_preview"])
    center.attach_verification(run_id, report.to_dict())
    assert center.sign_off(run_id)
    assert center.revoke_sign_off(run_id) is True
    record = center.get_run(run_id)
    assert record["signed_off_at"] == ""
    assert record["verification"]["workflow_key"] == "json_output"
    events = [json.loads(line)["event"] for line in (tmp_path / "runs.jsonl").read_text(encoding="utf-8").splitlines()]
    assert "sign_off_revoked" in events


def test_result_digest_changes_with_artifact():
    center = TaskRunCenter()
    first = _seed_run(center, "结果 A")
    second = _seed_run(center, "结果 B")
    assert center.get_run(first)["result_digest"] != center.get_run(second)["result_digest"]


# ---- UI 渲染 ----

def test_acceptance_panel_renders_and_runs_check():
    from streamlit.testing.v1 import AppTest

    src = str(Path(__file__).resolve().parents[1] / "src")
    script = f'''
import sys; sys.path.insert(0, {src!r})
import streamlit as st
from qa_toolkit.core.task_runner import TaskRunCenter
from qa_toolkit.ui.components.task_run_panel import render_task_run_panel
center = st.session_state.setdefault("_center", TaskRunCenter())
if "_seeded" not in st.session_state:
    st.session_state["_seeded"] = True
    center.submit("测试用例生成器", "生成用例", {{"x": 1}}, lambda: "# 用例\\n步骤：打开\\n预期：成功\\n" + "x" * 100)
render_task_run_panel(center, "测试用例生成器", "accept_panel")
'''
    app = AppTest.from_string(script, default_timeout=15).run()
    assert not app.exception
    app.button(key="accept_panel_run_accept").click().run()
    assert not app.exception
    assert any("验收" in item.value for item in app.markdown)
