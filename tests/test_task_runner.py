import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.task_runner import (  # noqa: E402
    RUN_STATUS_CANCELED,
    RUN_STATUS_FAILED,
    RUN_STATUS_SUCCESS,
    TaskRunCenter,
)


def test_task_run_center_submit_success_tracks_status_and_logs(tmp_path: Path):
    history_file = tmp_path / "task_runs.jsonl"
    center = TaskRunCenter(history_file=history_file)

    def _job(logger):
        logger("准备执行")
        logger("执行完成")
        return {"summary": {"total": 3, "passed": 3, "failed": 0}}

    run_info = center.submit(
        tool="接口自动化测试",
        action="执行测试",
        payload={"mode": "pytest"},
        executor=_job,
    )

    record = center.get_run(run_info["run_id"])
    assert record is not None
    assert record["status"] == RUN_STATUS_SUCCESS
    assert record["input_digest"]
    assert any("准备执行" in log for log in record["logs"])
    assert history_file.exists()
    assert history_file.read_text(encoding="utf-8").strip()


def test_task_run_center_submit_failure_marks_failed(tmp_path: Path):
    center = TaskRunCenter(history_file=tmp_path / "task_runs.jsonl")

    def _job(logger):
        logger("开始")
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        center.submit(
            tool="接口性能测试",
            action="执行压测",
            payload={"users": 10},
            executor=_job,
        )

    runs = center.list_runs(tool="接口性能测试", limit=1)
    assert runs
    assert runs[0]["status"] == RUN_STATUS_FAILED
    assert "boom" in runs[0]["error"]


def test_task_run_center_cancel_and_retry(tmp_path: Path):
    center = TaskRunCenter(history_file=tmp_path / "task_runs.jsonl")
    run_id = center.create_run(tool="接口安全测试", action="扫描", payload={"target": "https://example.com"})

    canceled = center.cancel(run_id, reason="测试取消")
    canceled_record = center.get_run(run_id)
    assert canceled is True
    assert canceled_record is not None
    assert canceled_record["status"] == RUN_STATUS_CANCELED

    retry_info = center.retry(
        run_id,
        payload={"target": "https://example.com"},
        executor=lambda logger: {"ok": True},
    )
    retry_record = center.get_run(retry_info["run_id"])
    assert retry_record is not None
    assert retry_record["status"] == RUN_STATUS_SUCCESS
    assert retry_record["retry_of"] == run_id
    assert retry_record["attempt"] == canceled_record["attempt"] + 1
