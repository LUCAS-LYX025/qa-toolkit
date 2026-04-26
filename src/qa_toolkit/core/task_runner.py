from __future__ import annotations

import datetime
import hashlib
import inspect
import json
import re
import traceback
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from qa_toolkit.paths import REPORTS_DIR

RUN_STATUS_QUEUED = "queued"
RUN_STATUS_RUNNING = "running"
RUN_STATUS_SUCCESS = "success"
RUN_STATUS_FAILED = "failed"
RUN_STATUS_CANCELED = "canceled"

TERMINAL_RUN_STATUSES = {
    RUN_STATUS_SUCCESS,
    RUN_STATUS_FAILED,
    RUN_STATUS_CANCELED,
}


class TaskRunCanceled(RuntimeError):
    """在任务执行过程中收到取消请求时抛出。"""


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _local_now_label() -> str:
    return datetime.datetime.now().strftime("%H:%M:%S")


def _stable_payload_text(payload: Any) -> str:
    try:
        return json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    except Exception:
        return repr(payload)


def _summarize_result(result: Any, max_length: int = 320) -> str:
    if result is None:
        return "任务执行完成，无返回数据。"
    if isinstance(result, dict):
        summary = result.get("summary")
        if isinstance(summary, dict):
            keys = [key for key in ["total", "passed", "failed", "errors", "finding_count", "request_count"] if key in summary]
            if keys:
                metrics = ", ".join(f"{key}={summary.get(key)}" for key in keys)
                return f"summary: {metrics}"
    text = _stable_payload_text(result)
    return text if len(text) <= max_length else f"{text[:max_length]}..."


def _sanitize_namespace(namespace: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(namespace or "").strip())
    return safe or "default"


@dataclass
class RunRecord:
    run_id: str
    tool: str
    action: str
    status: str
    created_at: str
    started_at: str = ""
    finished_at: str = ""
    input_digest: str = ""
    input_preview: str = ""
    retry_of: str = ""
    attempt: int = 1
    summary: str = ""
    error: str = ""
    cancel_requested: bool = False
    logs: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class TaskRunCenter:
    """统一维护页面任务运行记录，支持状态追踪和重试。"""

    def __init__(self, history_file: Optional[Path] = None, max_records: int = 200, max_logs: int = 200):
        self.history_file = Path(history_file) if history_file else None
        self.max_records = max(20, int(max_records))
        self.max_logs = max(20, int(max_logs))
        self._records: Dict[str, RunRecord] = {}
        self._order: List[str] = []
        if self.history_file:
            self.history_file.parent.mkdir(parents=True, exist_ok=True)

    def _build_run_id(self) -> str:
        ts = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        suffix = uuid.uuid4().hex[:8]
        return f"run_{ts}_{suffix}"

    def _trim_records(self) -> None:
        while len(self._order) > self.max_records:
            oldest = self._order.pop(0)
            self._records.pop(oldest, None)

    def _persist_event(self, event: str, record: RunRecord) -> None:
        if not self.history_file:
            return
        payload = {
            "event": event,
            "event_time": _utc_now_iso(),
            "record": record.to_dict(),
        }
        try:
            with self.history_file.open("a", encoding="utf-8") as file:
                file.write(json.dumps(payload, ensure_ascii=False, default=str) + "\n")
        except Exception:
            pass

    def _get_record(self, run_id: str) -> RunRecord:
        record = self._records.get(run_id)
        if not record:
            raise KeyError(f"任务 {run_id} 不存在")
        return record

    def create_run(self, tool: str, action: str, payload: Any = None, retry_of: str = "") -> str:
        payload_text = _stable_payload_text(payload or {})
        digest = hashlib.sha256(payload_text.encode("utf-8")).hexdigest()[:16]
        preview = payload_text if len(payload_text) <= 1000 else f"{payload_text[:1000]}..."

        attempt = 1
        if retry_of and retry_of in self._records:
            attempt = max(1, int(self._records[retry_of].attempt) + 1)

        run_id = self._build_run_id()
        record = RunRecord(
            run_id=run_id,
            tool=str(tool or "").strip() or "未知工具",
            action=str(action or "").strip() or "未命名动作",
            status=RUN_STATUS_QUEUED,
            created_at=_utc_now_iso(),
            input_digest=digest,
            input_preview=preview,
            retry_of=retry_of,
            attempt=attempt,
        )
        record.logs.append(f"[{_local_now_label()}] 任务已创建，等待执行。")
        self._records[run_id] = record
        self._order.append(run_id)
        self._trim_records()
        self._persist_event("created", record)
        return run_id

    def append_log(self, run_id: str, message: str) -> None:
        record = self._get_record(run_id)
        line = f"[{_local_now_label()}] {str(message)}"
        record.logs.append(line)
        if len(record.logs) > self.max_logs:
            record.logs = record.logs[-self.max_logs :]
        self._persist_event("log", record)

    def mark_running(self, run_id: str) -> None:
        record = self._get_record(run_id)
        if record.status in TERMINAL_RUN_STATUSES:
            return
        record.status = RUN_STATUS_RUNNING
        record.started_at = _utc_now_iso()
        self.append_log(run_id, "任务开始执行。")
        self._persist_event("running", record)

    def mark_success(self, run_id: str, summary: str = "") -> None:
        record = self._get_record(run_id)
        record.status = RUN_STATUS_SUCCESS
        record.finished_at = _utc_now_iso()
        record.summary = summary
        record.error = ""
        self.append_log(run_id, "任务执行完成。")
        self._persist_event("success", record)

    def mark_failed(self, run_id: str, error: str) -> None:
        record = self._get_record(run_id)
        record.status = RUN_STATUS_FAILED
        record.finished_at = _utc_now_iso()
        record.error = str(error or "未知错误")
        self.append_log(run_id, f"任务执行失败: {record.error}")
        self._persist_event("failed", record)

    def mark_canceled(self, run_id: str, reason: str = "用户取消任务") -> None:
        record = self._get_record(run_id)
        if record.status in TERMINAL_RUN_STATUSES:
            return
        record.status = RUN_STATUS_CANCELED
        record.finished_at = _utc_now_iso()
        record.cancel_requested = True
        self.append_log(run_id, reason)
        self._persist_event("canceled", record)

    def cancel(self, run_id: str, reason: str = "用户取消任务") -> bool:
        try:
            record = self._get_record(run_id)
        except KeyError:
            return False
        if record.status in TERMINAL_RUN_STATUSES:
            return False
        record.cancel_requested = True
        if record.status == RUN_STATUS_QUEUED:
            self.mark_canceled(run_id, reason)
        else:
            self.append_log(run_id, f"收到取消请求: {reason}")
        return True

    def ensure_not_canceled(self, run_id: str) -> None:
        record = self._get_record(run_id)
        if record.cancel_requested:
            raise TaskRunCanceled("任务已取消")

    def _invoke_executor(self, executor: Callable[..., Any], logger: Callable[[str], None]) -> Any:
        try:
            signature = inspect.signature(executor)
            if len(signature.parameters) == 0:
                return executor()
            return executor(logger)
        except ValueError:
            return executor()

    def run(self, run_id: str, executor: Callable[..., Any]) -> Any:
        self.ensure_not_canceled(run_id)
        self.mark_running(run_id)
        try:
            result = self._invoke_executor(executor, lambda message: self.append_log(run_id, message))
            if self._get_record(run_id).cancel_requested:
                self.mark_canceled(run_id, "任务在执行过程中收到取消请求。")
                return result
            self.mark_success(run_id, _summarize_result(result))
            return result
        except TaskRunCanceled as exc:
            self.mark_canceled(run_id, str(exc))
            return None
        except Exception as exc:
            self.mark_failed(run_id, str(exc))
            self.append_log(run_id, traceback.format_exc(limit=6))
            raise

    def submit(
        self,
        tool: str,
        action: str,
        payload: Any,
        executor: Callable[..., Any],
        retry_of: str = "",
    ) -> Dict[str, Any]:
        run_id = self.create_run(tool=tool, action=action, payload=payload, retry_of=retry_of)
        result = self.run(run_id, executor)
        return {"run_id": run_id, "status": self._get_record(run_id).status, "result": result}

    def retry(self, run_id: str, payload: Any, executor: Callable[..., Any]) -> Dict[str, Any]:
        record = self._get_record(run_id)
        return self.submit(
            tool=record.tool,
            action=record.action,
            payload=payload,
            executor=executor,
            retry_of=record.run_id,
        )

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        record = self._records.get(run_id)
        return record.to_dict() if record else None

    def list_runs(self, tool: str = "", limit: int = 20) -> List[Dict[str, Any]]:
        limit = max(1, int(limit))
        rows: List[Dict[str, Any]] = []
        for run_id in reversed(self._order):
            record = self._records.get(run_id)
            if not record:
                continue
            if tool and record.tool != tool:
                continue
            rows.append(record.to_dict())
            if len(rows) >= limit:
                break
        return rows


def get_session_task_runner(namespace: str = "default") -> TaskRunCenter:
    import streamlit as st

    safe_namespace = _sanitize_namespace(namespace)
    session_key = f"_task_run_center_{safe_namespace}"
    if session_key not in st.session_state:
        history_file = REPORTS_DIR / "task_runs" / f"{safe_namespace}.jsonl"
        st.session_state[session_key] = TaskRunCenter(history_file=history_file)
    return st.session_state[session_key]
