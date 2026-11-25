import csv
import html
import io
import json
import math
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import parse_qsl, quote, urlencode, urlparse, urlunparse

import requests

from qa_toolkit.core import api_performance_registry as perf_registry


class PerformanceTestTool:
    """JMeter 风格接口性能测试工具（策略与上限由 api_performance_registry 提供）。"""

    # 虚拟用户数硬上限；实际生效上限取 min(此值, 注册中心 configure_performance_limits)
    MAX_VIRTUAL_USERS = 1000
    # 幂等/无请求体语义的方法，避免 GET/HEAD 被误带上 body
    BODYLESS_METHODS = {"GET", "HEAD"}

    # ------------------------------------------------------------------
    # 通用护栏
    # ------------------------------------------------------------------

    def _clamp_float(self, value: Any, default: float, minimum: float, maximum: float) -> float:
        number = self._to_float(value, default)
        return max(minimum, min(number, maximum))

    def _clamp_int(self, value: Any, default: int, minimum: int, maximum: int) -> int:
        number = self._to_int(value, default)
        return int(max(minimum, min(number, maximum)))

    def _sleep_with_deadline(self, seconds: float, stop_monotonic: Optional[float]) -> None:
        """受 duration 截止时间约束的 sleep：ramp-up / think-time / jitter 都不会超期空等。"""
        delay = self._to_float(seconds, 0.0)
        if delay <= 0:
            return
        if stop_monotonic is not None:
            remaining = stop_monotonic - time.perf_counter()
            if remaining <= 0:
                return
            delay = min(delay, remaining)
        time.sleep(delay)

    @staticmethod
    def _encode_path_value(value: Any) -> str:
        """路径段/变量值的安全编码。``raw:`` 前缀供高级用户显式跳过编码。

        保留 ``$ { }`` 是为了让嵌套变量（a=${b}）仍能继续展开，
        其余会改变 URL 结构的字符（/ & = ? # 空格等）一律 percent-encode。
        """
        text = str(value)
        if text.startswith("raw:"):
            return text[4:]
        return quote(text, safe="${}")

    def _build_worker_error_sample(self, user_number: int, loop_number: int, exc: Exception) -> Dict[str, Any]:
        """把 VU 级别的未捕获异常转成一条失败样本，避免整次压测结果丢失。"""
        now = time.time()
        stamp = datetime.fromtimestamp(now).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        return {
            "sampler_id": "worker_error",
            "sampler_name": "Worker Error",
            "sampler_label": "Worker Error",
            "thread_name": f"VU-{user_number}",
            "thread_number": user_number,
            "loop_number": loop_number,
            "method": "-",
            "url": "",
            "status_code": 0,
            "success": False,
            "error_type": "worker_error",
            "elapsed_ms": 0.0,
            "response_size": 0,
            "response_preview": "",
            "response_headers": {},
            "response_message": type(exc).__name__,
            "request_headers": {},
            "request_body_preview": "",
            "error_message": f"虚拟用户执行异常: {type(exc).__name__}: {exc}",
            "assertion_results": [],
            "materialized_query_params": {},
            "materialized_body": None,
            "unresolved_variables": [],
            "csv_variables": {},
            "started_at": stamp,
            "finished_at": stamp,
            "relative_second": 0,
            "started_ts": now,
            "finished_ts": now,
        }

    def build_test_plan(
        self,
        interfaces: List[Dict[str, Any]],
        base_url: str,
        selected_indexes: Optional[List[int]] = None,
        thread_group: Optional[Dict[str, Any]] = None,
        request_defaults: Optional[Dict[str, Any]] = None,
        assertions: Optional[Dict[str, Any]] = None,
        timer_config: Optional[Dict[str, Any]] = None,
        csv_data_set: Optional[Dict[str, Any]] = None,
        transaction_controller: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """构建压测计划：时长/次数按注册中心上限钳制，目标地址做 SSRF 校验。"""
        selected_indexes = selected_indexes or list(range(len(interfaces)))
        thread_group = thread_group or {}
        request_defaults = request_defaults or {}
        assertions = assertions or {}
        timer_config = timer_config or {}
        csv_data_set = csv_data_set or {}
        transaction_controller = transaction_controller or {}
        limits = perf_registry.get_performance_limits()

        max_resp_ms = self._clamp_float(
            assertions.get("max_response_ms"), 0.0, 0.0, limits.max_max_response_ms
        )
        allow_private_targets = bool(
            request_defaults.get("allow_private_targets", limits.allow_private_targets)
        )

        samplers = []
        for index in selected_indexes:
            if index < 0 or index >= len(interfaces):
                continue
            item = self._normalize_interface(interfaces[index])
            if not base_url.strip() and not str(item.get("path") or "").startswith(("http://", "https://")):
                raise ValueError(f"接口 `{item.get('name', '未命名接口')}` 使用相对路径，必须填写基础URL")
            sampler_assertions = {
                "expected_status": self._resolve_expected_status(item, assertions),
                "contains_text": str(assertions.get("contains_text") or "").strip(),
                "max_response_ms": max_resp_ms,
            }
            preview_url = self._build_full_url(item, base_url, include_query=True)
            ok, reason = perf_registry.validate_target_url(
                preview_url, allow_private=allow_private_targets
            )
            if not ok:
                raise ValueError(
                    f"接口 `{item.get('name', '未命名接口')}` 的目标地址未通过安全校验：{reason}"
                )
            samplers.append(
                {
                    "index": index + 1,
                    "sampler_id": f"S{index + 1}",
                    "name": item.get("name", "未命名接口"),
                    "label": f"{item.get('method', 'GET')} {item.get('path', '/')}",
                    "method": item.get("method", "GET"),
                    "path": item.get("path", "/"),
                    "headers": item.get("headers", {}),
                    "path_params": item.get("path_params", {}),
                    "query_params": item.get("query_params", {}),
                    "body": item.get("body"),
                    "request_format": item.get("request_format", "auto"),
                    "expected_status": sampler_assertions["expected_status"],
                    "contains_text": sampler_assertions["contains_text"],
                    "max_response_ms": sampler_assertions["max_response_ms"],
                    "preview_url": preview_url,
                }
            )

        max_users = min(self.MAX_VIRTUAL_USERS, limits.max_virtual_users)
        users = self._clamp_int(thread_group.get("users"), 10, 1, max_users)
        ramp_up_seconds = self._clamp_float(
            thread_group.get("ramp_up_seconds"), 0.0, 0.0, limits.max_ramp_up_seconds
        )
        loop_count = self._clamp_int(thread_group.get("loop_count"), 1, 0, limits.max_loop_count)
        duration_seconds = self._clamp_float(
            thread_group.get("duration_seconds"), 0.0, 0.0, limits.max_duration_seconds
        )
        start_delay_seconds = self._clamp_float(
            thread_group.get("start_delay_seconds"), 0.0, 0.0, limits.max_start_delay_seconds
        )

        timeout_seconds = self._clamp_float(
            request_defaults.get("timeout_seconds"), 30.0, 1.0, limits.max_timeout_seconds
        )
        verify_ssl = bool(request_defaults.get("verify_ssl", limits.verify_ssl_by_default))
        follow_redirects = bool(
            request_defaults.get("follow_redirects", limits.follow_redirects_by_default)
        )
        keep_alive = bool(request_defaults.get("keep_alive", True))

        think_time_ms = self._clamp_float(
            timer_config.get("think_time_ms"), 0.0, 0.0, limits.max_think_time_ms
        )
        random_jitter_ms = self._clamp_float(
            timer_config.get("random_jitter_ms"), 0.0, 0.0, limits.max_jitter_ms
        )
        timer_strategy = str(timer_config.get("strategy") or "constant_jitter")
        if timer_strategy not in perf_registry.get_timer_strategies():
            timer_strategy = "constant_jitter"
        csv_config = self._build_csv_data_set_config(csv_data_set)
        transaction_config = self._build_transaction_controller(transaction_controller, samplers)

        if duration_seconds <= 0 and loop_count <= 0:
            loop_count = 1

        plan = {
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "thread_group": {
                "users": max(users, 1),
                "ramp_up_seconds": max(ramp_up_seconds, 0.0),
                "loop_count": max(loop_count, 0),
                "duration_seconds": max(duration_seconds, 0.0),
                "start_delay_seconds": max(start_delay_seconds, 0.0),
            },
            "http_defaults": {
                "base_url": base_url.strip(),
                "timeout_seconds": max(timeout_seconds, 1.0),
                "verify_ssl": verify_ssl,
                "follow_redirects": follow_redirects,
                "keep_alive": keep_alive,
                "allow_private_targets": allow_private_targets,
            },
            "timer": {
                "think_time_ms": max(think_time_ms, 0.0),
                "random_jitter_ms": max(random_jitter_ms, 0.0),
                "strategy": timer_strategy,
                "strategy_label": perf_registry.get_timer_strategies().get(timer_strategy, timer_strategy),
            },
            "csv_data_set": csv_config,
            "transaction_controller": transaction_config,
            "assertions": {
                "contains_text": str(assertions.get("contains_text") or "").strip(),
                "max_response_ms": max_resp_ms,
                "expected_status_mode": assertions.get("expected_status_mode", "document"),
                "custom_expected_status": self._to_int(assertions.get("custom_expected_status"), 200),
            },
            "samplers": samplers,
            "percentile_method": perf_registry.get_percentile_method(),
            "estimated_request_count": self._estimate_request_count(
                users=max(users, 1),
                loop_count=max(loop_count, 0),
                sampler_count=len(samplers),
                duration_seconds=max(duration_seconds, 0.0),
                transaction_enabled=transaction_config.get("enabled", False),
            ),
        }
        return plan

    def run_test_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """执行压测计划"""
        thread_group = deepcopy(plan.get("thread_group") or {})
        http_defaults = deepcopy(plan.get("http_defaults") or {})
        timer_config = deepcopy(plan.get("timer") or {})
        csv_data_set = deepcopy(plan.get("csv_data_set") or {})
        transaction_controller = deepcopy(plan.get("transaction_controller") or {})
        samplers = deepcopy(plan.get("samplers") or [])

        users = min(
            max(self._to_int(thread_group.get("users"), 1), 1),
            self.MAX_VIRTUAL_USERS,
            perf_registry.get_performance_limits().max_virtual_users,
        )
        start_delay_seconds = self._to_float(thread_group.get("start_delay_seconds"), 0.0)

        if not samplers:
            raise ValueError("压测计划中没有可执行的 HTTP Sampler")

        # Startup Delay 属于「测试开始前的等待」，刻意不计入 throughput 分母。
        if start_delay_seconds > 0:
            self._sleep_with_deadline(start_delay_seconds, None)

        start_monotonic = time.perf_counter()
        start_wall = time.time()
        stop_monotonic = None
        duration_seconds = self._to_float(thread_group.get("duration_seconds"), 0.0)
        if duration_seconds > 0:
            stop_monotonic = start_monotonic + duration_seconds

        worker_context = {
            "thread_group": thread_group,
            "http_defaults": http_defaults,
            "timer": timer_config,
            "csv_data_set": csv_data_set,
            "transaction_controller": transaction_controller,
            "samplers": samplers,
            "start_wall": start_wall,
            "start_monotonic": start_monotonic,
            "stop_monotonic": stop_monotonic,
            "csv_runtime": self._create_csv_runtime(csv_data_set),
        }

        all_samples: List[Dict[str, Any]] = []
        all_transaction_samples: List[Dict[str, Any]] = []
        with ThreadPoolExecutor(max_workers=users) as executor:
            futures = [
                executor.submit(self._run_virtual_user, user_index + 1, users, worker_context)
                for user_index in range(users)
            ]
            for future in futures:
                try:
                    worker_result = future.result()
                except Exception as exc:  # noqa: BLE001 - worker 异常转成失败样本，不丢整次结果
                    worker_result = {
                        "samples": [self._build_worker_error_sample(0, 0, exc)],
                        "transaction_samples": [],
                    }
                all_samples.extend(worker_result.get("samples", []))
                all_transaction_samples.extend(worker_result.get("transaction_samples", []))

        end_monotonic = time.perf_counter()
        end_wall = time.time()
        result = self._build_result(
            plan,
            all_samples,
            all_transaction_samples,
            start_wall,
            end_wall,
            start_monotonic,
            end_monotonic,
        )
        result["html_report"] = self.build_html_report(result)
        return result

    def build_html_report(self, result: Dict[str, Any]) -> str:
        """生成 HTML 报告（含测试配置快照、口径说明、告警与截断提示）。"""
        summary = result.get("summary", {})
        per_sampler = result.get("per_sampler", [])
        per_transaction = result.get("per_transaction", [])
        errors = result.get("error_samples", [])
        timeline = result.get("timeline", [])
        limits = perf_registry.get_performance_limits()
        plan = result.get("plan") or {}
        thread_group = plan.get("thread_group") or {}
        http_defaults = plan.get("http_defaults") or {}
        plan_assertions = plan.get("assertions") or {}
        csv_data_set = plan.get("csv_data_set") or {}
        config_pairs = [
            ("创建时间", plan.get("created_at", "")),
            ("虚拟用户数", thread_group.get("users", "")),
            ("Ramp-Up(s)", thread_group.get("ramp_up_seconds", "")),
            ("循环次数", thread_group.get("loop_count", "")),
            ("持续时长(s)", thread_group.get("duration_seconds", "")),
            ("基础 URL", http_defaults.get("base_url", "")),
            ("超时(s)", http_defaults.get("timeout_seconds", "")),
            ("校验 SSL", http_defaults.get("verify_ssl", "")),
            ("跟随重定向", http_defaults.get("follow_redirects", "")),
            ("断言模式", plan_assertions.get("expected_status_mode", "")),
            ("包含文本", plan_assertions.get("contains_text", "")),
            ("最大响应(ms)", plan_assertions.get("max_response_ms", "")),
            ("CSV 参数化", csv_data_set.get("enabled", False)),
            ("CSV EOF 策略", csv_data_set.get("eof_policy_label", "")),
            ("分位数口径", perf_registry.get_percentile_method_label()),
        ]
        config_rows = "\n".join(
            f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
            for key, value in config_pairs
        )
        error_total = int(summary.get("failed_requests", len(errors)) or 0)
        error_limit_note = (
            f"（仅展示前 {len(errors)} 条，共 {error_total} 条）"
            if error_total > len(errors) else ""
        )
        note_rows = "".join(
            f"<li>{html.escape(str(msg))}</li>" for msg in (result.get("warnings") or [])
        )
        warning_panel = (
            f'<div class="panel"><h2>运行告警</h2><ul>{note_rows}</ul></div>' if note_rows else ""
        )

        sampler_rows = "\n".join(
            [
                "<tr>"
                f"<td>{html.escape(item.get('sampler_name', ''))}</td>"
                f"<td>{item.get('requests', 0)}</td>"
                f"<td>{item.get('success_rate', 0):.1f}%</td>"
                f"<td>{item.get('avg_ms', 0):.2f}</td>"
                f"<td>{item.get('p90_ms', 0):.2f}</td>"
                f"<td>{item.get('p95_ms', 0):.2f}</td>"
                f"<td>{item.get('max_ms', 0):.2f}</td>"
                f"<td>{item.get('throughput_rps', 0):.2f}</td>"
                "</tr>"
                for item in per_sampler
            ]
        )

        error_rows = "\n".join(
            [
                "<tr>"
                f"<td>{html.escape(item.get('sampler_name', ''))}</td>"
                f"<td>{html.escape(item.get('thread_name', ''))}</td>"
                f"<td>{html.escape(str(item.get('status_code', '')))}</td>"
                f"<td>{item.get('elapsed_ms', 0):.2f}</td>"
                f"<td>{html.escape(item.get('error_message', '')[:300])}</td>"
                "</tr>"
                for item in errors[:limits.max_html_error_rows]
            ]
        )

        timeline_rows = "\n".join(
            [
                "<tr>"
                f"<td>{html.escape(str(item.get('second_bucket', '')))}</td>"
                f"<td>{item.get('requests', 0)}</td>"
                f"<td>{item.get('failures', 0)}</td>"
                f"<td>{item.get('avg_ms', 0):.2f}</td>"
                f"<td>{item.get('max_ms', 0):.2f}</td>"
                "</tr>"
                for item in timeline
            ]
        )

        transaction_rows = "\n".join(
            [
                "<tr>"
                f"<td>{html.escape(item.get('transaction_name', ''))}</td>"
                f"<td>{item.get('transactions', 0)}</td>"
                f"<td>{item.get('success_rate', 0):.1f}%</td>"
                f"<td>{item.get('avg_ms', 0):.2f}</td>"
                f"<td>{item.get('p90_ms', 0):.2f}</td>"
                f"<td>{item.get('p95_ms', 0):.2f}</td>"
                f"<td>{item.get('max_ms', 0):.2f}</td>"
                f"<td>{item.get('avg_sampler_count', 0):.2f}</td>"
                "</tr>"
                for item in per_transaction
            ]
        )

        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <title>性能测试报告</title>
  <style>
    body {{ font-family: Arial, sans-serif; background: #f5f7fb; margin: 0; padding: 24px; color: #1f2937; }}
    .container {{ max-width: 1280px; margin: 0 auto; }}
    .panel {{ background: #fff; border-radius: 14px; padding: 20px; margin-bottom: 20px; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.08); }}
    h1, h2 {{ margin-top: 0; }}
    .metrics {{ display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; }}
    .metric {{ background: linear-gradient(135deg, #eef2ff, #f8fafc); border-radius: 12px; padding: 14px; }}
    .metric .label {{ font-size: 12px; color: #64748b; }}
    .metric .value {{ font-size: 24px; font-weight: bold; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 12px; border-bottom: 1px solid #e5e7eb; text-align: left; vertical-align: top; }}
    th {{ background: #f8fafc; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="panel">
      <h1>JMeter 风格性能测试报告</h1>
      <p>开始时间: {html.escape(summary.get("started_at", ""))} | 结束时间: {html.escape(summary.get("finished_at", ""))}</p>
      <p>吞吐量口径: {html.escape(str(summary.get("throughput_basis", "活跃窗口")))} | 分位数口径: {html.escape(perf_registry.get_percentile_method_label())}</p>
      <div class="metrics">
        <div class="metric"><div class="label">总请求数</div><div class="value">{summary.get("total_requests", 0)}</div></div>
        <div class="metric"><div class="label">成功率</div><div class="value">{summary.get("success_rate", 0):.1f}%</div></div>
        <div class="metric"><div class="label">平均响应</div><div class="value">{summary.get("avg_ms", 0):.2f}ms</div></div>
        <div class="metric"><div class="label">P90</div><div class="value">{summary.get("p90_ms", 0):.2f}ms</div></div>
        <div class="metric"><div class="label">P95</div><div class="value">{summary.get("p95_ms", 0):.2f}ms</div></div>
        <div class="metric"><div class="label">吞吐量</div><div class="value">{summary.get("throughput_rps", 0):.2f} rps</div></div>
      </div>
    </div>
    {warning_panel}
    <div class="panel">
      <h2>测试配置快照</h2>
      <table><tbody>{config_rows or "<tr><td>无计划信息</td></tr>"}</tbody></table>
    </div>
    <div class="panel">
      <h2>Aggregate Report</h2>
      <table>
        <thead>
          <tr>
            <th>Sampler</th>
            <th>Requests</th>
            <th>Success Rate</th>
            <th>Avg(ms)</th>
            <th>P90(ms)</th>
            <th>P95(ms)</th>
            <th>Max(ms)</th>
            <th>Throughput(rps)</th>
          </tr>
        </thead>
        <tbody>{sampler_rows or "<tr><td colspan='8'>无数据</td></tr>"}</tbody>
      </table>
    </div>
    <div class="panel">
      <h2>Transaction Controller Report</h2>
      <table>
        <thead>
          <tr>
            <th>Transaction</th>
            <th>Count</th>
            <th>Success Rate</th>
            <th>Avg(ms)</th>
            <th>P90(ms)</th>
            <th>P95(ms)</th>
            <th>Max(ms)</th>
            <th>Avg Samplers</th>
          </tr>
        </thead>
        <tbody>{transaction_rows or "<tr><td colspan='8'>未启用事务控制器</td></tr>"}</tbody>
      </table>
    </div>
    <div class="panel">
      <h2>Error Samples {html.escape(error_limit_note)}</h2>
      <table>
        <thead>
          <tr>
            <th>Sampler</th>
            <th>Thread</th>
            <th>Status</th>
            <th>Elapsed(ms)</th>
            <th>Error</th>
          </tr>
        </thead>
        <tbody>{error_rows or "<tr><td colspan='5'>无错误样本</td></tr>"}</tbody>
      </table>
    </div>
    <div class="panel">
      <h2>Timeline Listener</h2>
      <table>
        <thead>
          <tr>
            <th>Second</th>
            <th>Requests</th>
            <th>Failures</th>
            <th>Avg(ms)</th>
            <th>Max(ms)</th>
          </tr>
        </thead>
        <tbody>{timeline_rows or "<tr><td colspan='5'>无时间线数据</td></tr>"}</tbody>
      </table>
    </div>
  </div>
</body>
</html>"""

    def _run_virtual_user(
        self,
        user_number: int,
        total_users: int,
        context: Dict[str, Any],
    ) -> Dict[str, List[Dict[str, Any]]]:
        thread_group = context.get("thread_group") or {}
        http_defaults = context.get("http_defaults") or {}
        timer_config = context.get("timer") or {}
        csv_data_set = context.get("csv_data_set") or {}
        transaction_controller = context.get("transaction_controller") or {}
        samplers = context.get("samplers") or []
        stop_monotonic = context.get("stop_monotonic")
        start_wall = context.get("start_wall", time.time())
        csv_runtime = context.get("csv_runtime")

        limits = perf_registry.get_performance_limits()
        ramp_up_seconds = self._to_float(thread_group.get("ramp_up_seconds"), 0.0)
        loop_count = self._to_int(thread_group.get("loop_count"), 1)
        think_time_ms = self._to_float(timer_config.get("think_time_ms"), 0.0)
        random_jitter_ms = self._to_float(timer_config.get("random_jitter_ms"), 0.0)
        timer_strategy = str(timer_config.get("strategy") or "constant_jitter")

        samples: List[Dict[str, Any]] = []
        transaction_samples: List[Dict[str, Any]] = []
        session = None
        current_loop = 0
        unlimited_loop = stop_monotonic is not None and loop_count == 0
        csv_thread_index = 0

        try:
            # ramp-up 必须在 try 内且受 duration 截止时间约束：
            # 否则尾部 VU 会空等到远超 duration，且异常会冒泡导致整次结果丢失。
            if ramp_up_seconds > 0 and total_users > 0:
                self._sleep_with_deadline(
                    ramp_up_seconds * (user_number - 1) / total_users, stop_monotonic
                )
            session = requests.Session()
            if not http_defaults.get("keep_alive", True):
                session.headers.update({"Connection": "close"})

            while True:
                if stop_monotonic is not None and time.perf_counter() >= stop_monotonic:
                    break
                if not unlimited_loop and current_loop >= max(loop_count, 0):
                    break

                current_loop += 1
                csv_row, csv_thread_index, should_stop_thread = self._next_csv_row(
                    csv_runtime=csv_runtime,
                    csv_config=csv_data_set,
                    user_number=user_number,
                    local_index=csv_thread_index,
                )
                if should_stop_thread:
                    break

                transaction_started_perf = time.perf_counter()
                transaction_started_wall = time.time()
                transaction_success = True
                transaction_errors: List[str] = []
                executed_sampler_count = 0

                for sampler in samplers:
                    if stop_monotonic is not None and time.perf_counter() >= stop_monotonic:
                        break

                    sample = self._execute_sampler(
                        session=session,
                        sampler=sampler,
                        http_defaults=http_defaults,
                        user_number=user_number,
                        loop_number=current_loop,
                        start_wall=start_wall,
                        csv_row=csv_row,
                    )
                    samples.append(sample)
                    executed_sampler_count += 1
                    if not sample.get("success"):
                        transaction_success = False
                        if sample.get("error_message"):
                            transaction_errors.append(str(sample.get("error_message")))

                    delay_ms = perf_registry.compute_timer_delay_ms(
                        think_time_ms, random_jitter_ms, timer_strategy
                    )
                    if delay_ms > 0:
                        self._sleep_with_deadline(delay_ms / 1000, stop_monotonic)

                    if transaction_controller.get("enabled") and transaction_controller.get("stop_on_error") and not sample.get("success"):
                        break

                if transaction_controller.get("enabled"):
                    transaction_elapsed_ms = (time.perf_counter() - transaction_started_perf) * 1000
                    transaction_finished_wall = time.time()
                    # duration 截断产生的「不完整事务」必须标记，避免污染事务统计。
                    complete = executed_sampler_count >= len(samplers)
                    transaction_samples.append(
                        {
                            "transaction_name": transaction_controller.get("name", "Transaction Controller"),
                            "thread_name": f"VU-{user_number}",
                            "thread_number": user_number,
                            "loop_number": current_loop,
                            "success": transaction_success,
                            "complete": complete,
                            "sampler_count": executed_sampler_count,
                            "elapsed_ms": round(transaction_elapsed_ms, 3),
                            "error_message": "; ".join(transaction_errors[:limits.max_transaction_errors]),
                            "started_at": datetime.fromtimestamp(transaction_started_wall).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "finished_at": datetime.fromtimestamp(transaction_finished_wall).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "relative_second": max(int(math.floor(transaction_started_wall - start_wall)), 0),
                            "csv_variables": csv_row or {},
                        }
                    )
        except Exception as exc:  # noqa: BLE001 - VU 级异常转成失败样本，不丢整次结果
            samples.append(self._build_worker_error_sample(user_number, current_loop, exc))
        finally:
            if session is not None:
                try:
                    session.close()
                except Exception:
                    pass

        return {
            "samples": samples,
            "transaction_samples": transaction_samples,
        }

    def _execute_sampler(
        self,
        session: requests.Session,
        sampler: Dict[str, Any],
        http_defaults: Dict[str, Any],
        user_number: int,
        loop_number: int,
        start_wall: float,
        csv_row: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        limits = perf_registry.get_performance_limits()
        materialized_sampler = self._materialize_sampler(sampler, http_defaults, csv_row or {})
        url = str(materialized_sampler.get("full_url") or "")
        headers = deepcopy(materialized_sampler.get("headers") or {})
        body = deepcopy(materialized_sampler.get("body"))
        method = str(materialized_sampler.get("method") or "GET").upper()
        request_format = str(materialized_sampler.get("request_format") or "auto")
        # GET/HEAD 不应携带请求体；需要时可通过 BODYLESS_METHODS 覆盖。
        if method in self.BODYLESS_METHODS:
            body = None
        timeout_seconds = self._to_float(http_defaults.get("timeout_seconds"), 30.0)
        verify_ssl = bool(http_defaults.get("verify_ssl", True))
        follow_redirects = bool(http_defaults.get("follow_redirects", True))

        request_kwargs: Dict[str, Any] = {
            "headers": headers,
            "timeout": timeout_seconds,
            "verify": verify_ssl,
            "allow_redirects": follow_redirects,
        }

        if body not in (None, "", {}, []):
            if request_format in {"json", "data_json", "auto"} and isinstance(body, (dict, list)):
                request_kwargs["json"] = body
            else:
                request_kwargs["data"] = body

        started_at = time.time()
        started_perf = time.perf_counter()
        success = False
        status_code = 0
        response_size = 0
        response_preview = ""
        response_headers: Dict[str, Any] = {}
        response_message = ""
        error_message = ""
        error_type = "none"
        assertion_results: List[Dict[str, Any]] = []
        request_headers = deepcopy(headers)
        request_payload = request_kwargs.get("json", request_kwargs.get("data"))
        request_body_preview = self._build_payload_preview(request_payload)
        unresolved_variables = list(materialized_sampler.get("unresolved_variables") or [])

        try:
            response = session.request(method, url, **request_kwargs)
            elapsed_ms = (time.perf_counter() - started_perf) * 1000
            status_code = int(response.status_code)
            response_text = response.text or ""
            response_size = len(response.content or b"")
            response_preview = response_text[:limits.max_response_preview_chars]
            response_headers = dict(response.headers or {})
            response_message = str(response.reason or "")
            # 断言基于全量响应；逐条明细写入样本，结果树不再用 400 字符预览反推。
            success, error_message, assertion_results = self._assert_response(
                materialized_sampler, response_text, status_code, elapsed_ms
            )
            if not success:
                error_type = self._classify_assertion_error(assertion_results)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started_perf) * 1000
            response_message = exc.__class__.__name__
            error_message = str(exc)
            error_type = "transport_error"
        finished_at = time.time()

        sample = {
            "sampler_id": sampler.get("sampler_id") or "unknown",
            "sampler_name": sampler.get("name", "未命名接口"),
            "sampler_label": sampler.get("label", ""),
            "thread_name": f"VU-{user_number}",
            "thread_number": user_number,
            "loop_number": loop_number,
            "method": method,
            "url": url,
            "status_code": status_code,
            "success": success,
            "error_type": error_type,
            "elapsed_ms": round(elapsed_ms, 3),
            "response_size": response_size,
            "response_preview": response_preview,
            "response_headers": response_headers,
            "response_message": response_message,
            "request_headers": request_headers,
            "request_body_preview": request_body_preview,
            "assertion_results": assertion_results,
            "materialized_query_params": deepcopy(materialized_sampler.get("query_params") or {}),
            "materialized_body": deepcopy(body),
            "unresolved_variables": unresolved_variables,
            "error_message": error_message,
            "csv_variables": csv_row or {},
            "started_at": datetime.fromtimestamp(started_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "finished_at": datetime.fromtimestamp(finished_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "started_ts": started_at,
            "finished_ts": finished_at,
            "relative_second": max(int(math.floor(started_at - start_wall)), 0),
        }
        if unresolved_variables:
            sample["warning"] = "存在未解析的 CSV 变量占位符: " + ", ".join(unresolved_variables[:5])
        return sample

    def _assert_response(
        self,
        sampler: Dict[str, Any],
        response_text: str,
        status_code: int,
        elapsed_ms: float,
    ) -> Tuple[bool, str, List[Dict[str, Any]]]:
        """按注册中心里的断言类型逐条判定，返回 (是否通过, 失败原因, 逐条明细)。"""
        passed, errors, details = perf_registry.evaluate_assertions(
            sampler, response_text, status_code, elapsed_ms
        )
        return passed, "; ".join(errors), details

    @staticmethod
    def _classify_assertion_error(details: List[Dict[str, Any]]) -> str:
        failed_keys = {item.get("key") for item in details if not item.get("passed")}
        if failed_keys & {"expected_status", "http_error_fallback"}:
            return "status_mismatch"
        if "max_response_ms" in failed_keys:
            return "response_time"
        if "contains_text" in failed_keys:
            return "content_assertion"
        return "assertion_failed" if failed_keys else "none"

    def _build_result(
        self,
        plan: Dict[str, Any],
        samples: List[Dict[str, Any]],
        transaction_samples: List[Dict[str, Any]],
        start_wall: float,
        end_wall: float,
        start_monotonic: float,
        end_monotonic: float,
    ) -> Dict[str, Any]:
        limits = perf_registry.get_performance_limits()
        elapsed_seconds = max(end_monotonic - start_monotonic, 0.001)
        success_samples = [item for item in samples if item.get("success")]
        failed_samples = [item for item in samples if not item.get("success")]
        elapsed_values = [float(item.get("elapsed_ms", 0.0)) for item in samples]

        # 活跃窗口 = 首末样本时间差，不含 ramp-up / startup delay / 思考时间空档。
        started_ts = [float(item.get("started_ts") or 0) for item in samples if item.get("started_ts")]
        finished_ts = [float(item.get("finished_ts") or 0) for item in samples if item.get("finished_ts")]
        if started_ts and finished_ts:
            active_window_seconds = max(max(finished_ts) - min(started_ts), 0.001)
        else:
            active_window_seconds = elapsed_seconds

        summary = {
            "started_at": datetime.fromtimestamp(start_wall).strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": datetime.fromtimestamp(end_wall).strftime("%Y-%m-%d %H:%M:%S"),
            "total_requests": len(samples),
            "success_requests": len(success_samples),
            "failed_requests": len(failed_samples),
            "success_rate": (len(success_samples) / len(samples) * 100) if samples else 0.0,
            "elapsed_seconds": elapsed_seconds,
            "active_window_seconds": active_window_seconds,
            "throughput_rps": len(samples) / active_window_seconds if active_window_seconds > 0 else 0.0,
            "wall_throughput_rps": len(samples) / elapsed_seconds if elapsed_seconds > 0 else 0.0,
            "throughput_basis": "活跃窗口（首末样本时间差，不含 ramp-up / startup delay / 思考时间空档）",
            "avg_ms": statistics.mean(elapsed_values) if elapsed_values else 0.0,
            "min_ms": min(elapsed_values) if elapsed_values else 0.0,
            "max_ms": max(elapsed_values) if elapsed_values else 0.0,
        }
        # 分位数列表与口径全部来自注册中心，新增分位无需改这里。
        for spec in perf_registry.get_percentile_specs():
            summary[spec.name] = self._percentile(elapsed_values, spec.value)

        per_sampler = self._build_per_sampler_summary(samples, active_window_seconds)
        per_transaction = self._build_per_transaction_summary(transaction_samples)
        timeline = self._build_timeline(samples)
        error_samples = failed_samples[: limits.max_error_samples]
        summary_listener = self._build_summary_listener(samples)
        expose_transaction_samples = bool((plan.get("transaction_controller") or {}).get("generate_parent_sample", True))

        truncation: Dict[str, Any] = {}
        if len(failed_samples) > len(error_samples):
            truncation["error_samples"] = {
                "total": len(failed_samples),
                "kept": len(error_samples),
                "note": f"仅保留前 {len(error_samples)} 条错误样本，共 {len(failed_samples)} 条",
            }
        if len(samples) > limits.max_summary_listener_rows:
            truncation["summary_listener"] = {
                "total": len(samples),
                "note": f"结果清单较大（{len(samples)} 条），页面分页展示",
            }

        warnings: List[str] = []
        if not samples:
            warnings.append(
                "本次压测未产生任何请求（0 样本）。常见原因：Ramp-Up 超过 Duration、"
                "目标地址不可达、Sampler 未选中，或 CSV 数据用尽后选择了停止线程。"
            )
        duration_seconds = self._to_float((plan.get("thread_group") or {}).get("duration_seconds"), 0.0)
        if duration_seconds > 0 and elapsed_seconds > duration_seconds * 1.25:
            warnings.append(
                f"实际耗时 {elapsed_seconds:.1f}s 明显超过设定时长 {duration_seconds:.1f}s，"
                "请检查 Ramp-Up / 定时器 / 单次请求耗时。"
            )
        unresolved = [item for item in samples if item.get("unresolved_variables")]
        if unresolved:
            warnings.append(
                f"{len(unresolved)} 个请求包含未解析的 CSV 变量占位符（形如 ${{var}}），"
                "请检查变量名与 EOF 策略。"
            )
        incomplete = [item for item in transaction_samples if not item.get("complete", True)]
        if incomplete:
            warnings.append(f"{len(incomplete)} 条事务在 duration 截止时被截断，已从事务统计中排除。")

        return {
            "plan": plan,
            "summary": summary,
            "per_sampler": per_sampler,
            "transaction_samples": transaction_samples if expose_transaction_samples else [],
            "per_transaction": per_transaction,
            "timeline": timeline,
            "error_samples": error_samples,
            "summary_listener": summary_listener,
            "samples": samples,
            "warnings": warnings,
            "truncation": truncation,
            "percentile_method": perf_registry.get_percentile_method(),
            "percentile_method_label": perf_registry.get_percentile_method_label(),
        }

    def _build_per_sampler_summary(self, samples: List[Dict[str, Any]], elapsed_seconds: float) -> List[Dict[str, Any]]:
        # 按稳定 sampler_id 分组；同 method+path 但不同名称的接口不再被静默合并。
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in samples:
            key = str(item.get("sampler_id") or "").strip()
            if not key:
                key = f"{item.get('sampler_label', 'unknown')}#{item.get('sampler_name', '')}"
            groups.setdefault(key, []).append(item)

        results = []
        for sampler_id, group_samples in groups.items():
            first = group_samples[0]
            label = first.get("sampler_label") or sampler_id
            name = first.get("sampler_name") or ""
            display = f"{label} | {name}" if name and name != label else label
            elapsed_values = [float(item.get("elapsed_ms", 0.0)) for item in group_samples]
            success_count = sum(1 for item in group_samples if item.get("success"))
            starts = [float(item.get("started_ts") or 0) for item in group_samples if item.get("started_ts")]
            ends = [float(item.get("finished_ts") or 0) for item in group_samples if item.get("finished_ts")]
            window = max(max(ends) - min(starts), 0.001) if starts and ends else max(elapsed_seconds, 0.001)
            row = {
                "sampler_id": sampler_id,
                "sampler_name": display,
                "requests": len(group_samples),
                "success_rate": (success_count / len(group_samples) * 100) if group_samples else 0.0,
                "avg_ms": statistics.mean(elapsed_values) if elapsed_values else 0.0,
                "min_ms": min(elapsed_values) if elapsed_values else 0.0,
                "max_ms": max(elapsed_values) if elapsed_values else 0.0,
                "throughput_rps": len(group_samples) / window if window > 0 else 0.0,
                "failed_requests": sum(1 for item in group_samples if not item.get("success")),
                "error_types": sorted({
                    str(item.get("error_type")) for item in group_samples
                    if not item.get("success") and item.get("error_type") not in (None, "none")
                }),
            }
            for spec in perf_registry.get_percentile_specs():
                row[spec.name] = self._percentile(elapsed_values, spec.value)
            results.append(row)

        results.sort(key=lambda item: item.get("sampler_name", ""))
        return results

    def _build_timeline(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        buckets: Dict[int, Dict[str, Any]] = {}
        for item in samples:
            bucket = int(item.get("relative_second", 0))
            current = buckets.setdefault(
                bucket,
                {
                    "second_bucket": bucket,
                    "requests": 0,
                    "failures": 0,
                    "elapsed_values": [],
                },
            )
            current["requests"] += 1
            if not item.get("success"):
                current["failures"] += 1
            current["elapsed_values"].append(float(item.get("elapsed_ms", 0.0)))

        rows = []
        if not buckets:
            return rows
        first_bucket, last_bucket = min(buckets), max(buckets)
        bucket_numbers = list(range(first_bucket, last_bucket + 1))
        limit = perf_registry.get_performance_limits().max_timeline_buckets
        if len(bucket_numbers) > limit:
            bucket_numbers = bucket_numbers[-limit:]
        # 补齐空档秒（0 值），否则 line_chart 会把不连续的秒画成连续曲线。
        for bucket in bucket_numbers:
            item = buckets.get(bucket)
            if item is None:
                rows.append({
                    "second_bucket": bucket, "requests": 0, "failures": 0,
                    "avg_ms": 0.0, "max_ms": 0.0,
                })
                continue
            elapsed_values = item.pop("elapsed_values", [])
            item["avg_ms"] = statistics.mean(elapsed_values) if elapsed_values else 0.0
            item["max_ms"] = max(elapsed_values) if elapsed_values else 0.0
            rows.append(item)
        return rows

    def _build_per_transaction_summary(self, transaction_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in transaction_samples:
            # duration 截断产生的不完整事务不参与事务统计，避免拉低/污染成功率与耗时。
            if not item.get("complete", True):
                continue
            groups.setdefault(item.get("transaction_name", "Transaction Controller"), []).append(item)

        rows = []
        for transaction_name, group_samples in groups.items():
            elapsed_values = [float(item.get("elapsed_ms", 0.0)) for item in group_samples]
            sampler_counts = [int(item.get("sampler_count", 0)) for item in group_samples]
            success_count = sum(1 for item in group_samples if item.get("success"))
            rows.append(
                {
                    "transaction_name": transaction_name,
                    "transactions": len(group_samples),
                    "success_rate": (success_count / len(group_samples) * 100) if group_samples else 0.0,
                    "avg_ms": statistics.mean(elapsed_values) if elapsed_values else 0.0,
                    "p90_ms": self._percentile(elapsed_values, 90),
                    "p95_ms": self._percentile(elapsed_values, 95),
                    "max_ms": max(elapsed_values) if elapsed_values else 0.0,
                    "avg_sampler_count": statistics.mean(sampler_counts) if sampler_counts else 0.0,
                    "failed_transactions": sum(1 for item in group_samples if not item.get("success")),
                }
            )

        rows.sort(key=lambda item: item.get("transaction_name", ""))
        return rows

    def _build_summary_listener(self, samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        rows = []
        for index, sample in enumerate(samples, start=1):
            rows.append(
                {
                    "序号": index,
                    "Sampler": sample.get("sampler_label", ""),
                    "Thread": sample.get("thread_name", ""),
                    "Loop": sample.get("loop_number", 0),
                    "Status": sample.get("status_code", 0),
                    "Elapsed(ms)": sample.get("elapsed_ms", 0.0),
                    "Success": "true" if sample.get("success") else "false",
                    "Error": sample.get("error_message", ""),
                }
            )
        return rows

    def _normalize_interface(self, interface: Dict[str, Any]) -> Dict[str, Any]:
        method = str(interface.get("method") or "GET").upper()
        query_params = interface.get("query_params") if isinstance(interface.get("query_params"), dict) else {}
        body = interface.get("body")
        if body is None and method != "GET" and isinstance(interface.get("parameters"), dict):
            body = interface.get("parameters")
        if method == "GET" and isinstance(interface.get("parameters"), dict):
            # parameters 与 query_params 合并（显式 query_params 优先），不再静默丢弃。
            merged = dict(interface.get("parameters") or {})
            merged.update(query_params or {})
            query_params = merged

        return {
            "name": str(interface.get("name") or "").strip() or f"{method} {interface.get('path') or interface.get('url') or '/'}",
            "method": method,
            "path": str(interface.get("path") or interface.get("url") or "/").strip() or "/",
            "headers": deepcopy(interface.get("headers") if isinstance(interface.get("headers"), dict) else {}),
            "path_params": deepcopy(interface.get("path_params") if isinstance(interface.get("path_params"), dict) else {}),
            "query_params": deepcopy(query_params),
            "body": deepcopy(body),
            "request_format": str(interface.get("request_format") or "auto").strip() or "auto",
            "expected_status": self._to_int(interface.get("expected_status"), 200),
        }

    def _build_csv_data_set_config(self, csv_data_set: Dict[str, Any]) -> Dict[str, Any]:
        enabled = bool(csv_data_set.get("enabled"))
        if not enabled:
            return {
                "enabled": False,
                "rows": [],
                "row_count": 0,
                "variable_names": [],
                "preview_rows": [],
                "delimiter": ",",
                "quotechar": '"',
                "sharing_mode": "all_threads",
                "recycle_on_eof": True,
                "stop_thread_on_eof": False,
                "eof_policy": "recycle",
                "eof_policy_label": perf_registry.get_csv_eof_policies().get("recycle", "循环复用"),
                "use_header_row": True,
                "source_name": "",
            }

        delimiter = str(csv_data_set.get("delimiter") or ",")
        quotechar = str(csv_data_set.get("quotechar") or '"')
        use_header_row = bool(csv_data_set.get("use_header_row", True))
        csv_text = str(csv_data_set.get("csv_text") or "")
        variable_names_text = str(csv_data_set.get("variable_names_text") or "")
        if not csv_text.strip():
            raise ValueError("已启用 CSV Data Set Config，但未提供 CSV 数据")

        rows = self._parse_csv_rows(
            csv_text=csv_text,
            delimiter=delimiter[0],
            quotechar=quotechar[0],
            use_header_row=use_header_row,
            variable_names_text=variable_names_text,
        )
        if not rows:
            raise ValueError("CSV Data Set Config 没有解析到有效数据行")

        variable_names = list(rows[0].keys())
        sharing_mode = str(csv_data_set.get("sharing_mode") or "all_threads")
        if not perf_registry.is_valid_csv_sharing_mode(sharing_mode):
            sharing_mode = "all_threads"
        recycle_on_eof = bool(csv_data_set.get("recycle_on_eof", True))
        stop_thread_on_eof = bool(csv_data_set.get("stop_thread_on_eof", False))
        # 两个易冲突 checkbox 归一化为唯一 EOF 策略，避免 Stop Thread 永远失效。
        eof_policy = perf_registry.normalize_csv_eof_policy(recycle_on_eof, stop_thread_on_eof)
        return {
            "enabled": True,
            "rows": rows,
            "row_count": len(rows),
            "variable_names": variable_names,
            "preview_rows": rows[:5],
            "delimiter": delimiter[0],
            "quotechar": quotechar[0],
            "sharing_mode": sharing_mode,
            "recycle_on_eof": recycle_on_eof,
            "stop_thread_on_eof": stop_thread_on_eof,
            "eof_policy": eof_policy,
            "eof_policy_label": perf_registry.get_csv_eof_policies().get(eof_policy, eof_policy),
            "use_header_row": use_header_row,
            "source_name": str(csv_data_set.get("source_name") or "inline-csv"),
        }

    def _build_transaction_controller(
        self,
        transaction_controller: Dict[str, Any],
        samplers: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        enabled = bool(transaction_controller.get("enabled")) and bool(samplers)
        return {
            "enabled": enabled,
            "name": str(transaction_controller.get("name") or "Transaction Controller").strip() or "Transaction Controller",
            "generate_parent_sample": bool(transaction_controller.get("generate_parent_sample", True)),
            "stop_on_error": bool(transaction_controller.get("stop_on_error", False)),
            "sampler_count": len(samplers),
        }

    def _resolve_expected_status(self, interface: Dict[str, Any], assertions: Dict[str, Any]) -> Optional[int]:
        mode = str(assertions.get("expected_status_mode") or "document")
        if mode == "none":
            return None
        if mode == "custom":
            return self._to_int(assertions.get("custom_expected_status"), 200)
        return self._to_int(interface.get("expected_status"), 200)

    def _build_full_url(self, interface: Dict[str, Any], base_url: str, include_query: bool = True) -> str:
        path = str(interface.get("path") or "/")
        for key, value in (interface.get("path_params") or {}).items():
            # 路径参数必须编码，否则 "../../admin?x=1" 会注入路径与额外 query。
            path = path.replace("{" + str(key) + "}", self._encode_path_value(value))

        if path.startswith(("http://", "https://")):
            url = path
        else:
            actual_base_url = base_url.strip()
            url = actual_base_url.rstrip("/") + "/" + path.lstrip("/") if actual_base_url else path

        if not include_query:
            return url

        query_params = interface.get("query_params") or {}
        if not query_params:
            return url
        parsed = urlparse(url)
        # 保留同名多值参数，避免 dict() 静默丢值。
        query_dict: Dict[str, list] = {}
        for key, value in parse_qsl(parsed.query, keep_blank_values=True):
            query_dict.setdefault(key, []).append(value)
        # 追加而非覆盖：URL 中已有的同名多值参数必须保留；list 值逐项展开。
        for key, value in query_params.items():
            target = query_dict.setdefault(str(key), [])
            if isinstance(value, (list, tuple)):
                target.extend(str(item) for item in value)
            else:
                target.append(str(value))
        return urlunparse(parsed._replace(query=urlencode(query_dict, doseq=True)))

    def _estimate_request_count(
        self,
        users: int,
        loop_count: int,
        sampler_count: int,
        duration_seconds: float,
        transaction_enabled: bool = False,
    ) -> str:
        if duration_seconds > 0 and loop_count == 0:
            return "按时长运行，理论请求数不固定"
        sampler_request_count = users * max(loop_count, 1) * max(sampler_count, 1)
        if transaction_enabled:
            transaction_count = users * max(loop_count, 1)
            return f"{sampler_request_count} 个 Sampler 请求 / {transaction_count} 个事务"
        return str(sampler_request_count)

    def _create_csv_runtime(self, csv_config: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "enabled": bool(csv_config.get("enabled")),
            "rows": deepcopy(csv_config.get("rows") or []),
            "shared_index": 0,
            "lock": threading.Lock(),
        }

    def _next_csv_row(
        self,
        csv_runtime: Optional[Dict[str, Any]],
        csv_config: Dict[str, Any],
        user_number: int,
        local_index: int,
    ) -> Tuple[Dict[str, Any], int, bool]:
        """按注册中心的 EOF 策略取下一行；返回 (row, next_local_index, should_stop)。"""
        if not csv_config.get("enabled"):
            return {}, local_index, False

        rows = csv_runtime.get("rows") if csv_runtime else []
        policy = str(csv_config.get("eof_policy") or perf_registry.normalize_csv_eof_policy(
            bool(csv_config.get("recycle_on_eof", True)),
            bool(csv_config.get("stop_thread_on_eof", False)),
        ))
        if not rows:
            return {}, local_index, policy == "stop_thread"

        sharing_mode = str(csv_config.get("sharing_mode") or "all_threads")
        if not perf_registry.is_valid_csv_sharing_mode(sharing_mode):
            sharing_mode = "all_threads"
        if sharing_mode == "current_thread":
            return self._next_csv_row_local(rows, policy, local_index)

        with csv_runtime["lock"]:
            index = int(csv_runtime.get("shared_index", 0))
            if index >= len(rows):
                if policy == "stop_thread":
                    return {}, local_index, True
                if policy == "continue_empty":
                    return {}, local_index, False
                index = 0
            row = deepcopy(rows[index])
            next_index = index + 1
            if next_index >= len(rows) and policy == "recycle":
                next_index = 0
            csv_runtime["shared_index"] = next_index
        return row, local_index, False

    @staticmethod
    def _next_csv_row_local(rows: List[Dict[str, Any]], policy: str, local_index: int) -> Tuple[Dict[str, Any], int, bool]:
        index = local_index
        if index >= len(rows):
            if policy == "stop_thread":
                return {}, local_index, True
            if policy == "continue_empty":
                return {}, local_index, False
            index = 0
        next_index = index + 1
        if next_index >= len(rows) and policy == "recycle":
            next_index = 0
        return deepcopy(rows[index]), next_index, False

    def _parse_csv_rows(
        self,
        csv_text: str,
        delimiter: str,
        quotechar: str,
        use_header_row: bool,
        variable_names_text: str,
    ) -> List[Dict[str, Any]]:
        buffer = io.StringIO(csv_text.strip())
        if use_header_row:
            reader = csv.DictReader(buffer, delimiter=delimiter, quotechar=quotechar)
            rows = []
            for row in reader:
                clean_row = {str(key).strip(): str(value).strip() for key, value in row.items() if key is not None}
                if any(value != "" for value in clean_row.values()):
                    rows.append(clean_row)
            return rows

        variable_names = [item.strip() for item in variable_names_text.split(",") if item.strip()]
        if not variable_names:
            raise ValueError("未使用表头时，必须填写变量名列表")

        reader = csv.reader(buffer, delimiter=delimiter, quotechar=quotechar)
        rows = []
        for row in reader:
            if not any(str(value).strip() for value in row):
                continue
            mapped = {}
            for index, variable_name in enumerate(variable_names):
                mapped[variable_name] = str(row[index]).strip() if index < len(row) else ""
            rows.append(mapped)
        return rows

    def _materialize_sampler(
        self,
        sampler: Dict[str, Any],
        http_defaults: Dict[str, Any],
        csv_row: Dict[str, Any],
    ) -> Dict[str, Any]:
        materialized = deepcopy(sampler)
        unresolved: List[str] = []
        # path / path_params 中的变量值做 URL 编码，防止注入路径或额外 query 参数。
        materialized["path"] = self._apply_variables(
            materialized.get("path"), csv_row, unresolved, url_encode=True
        )
        materialized["headers"] = self._apply_variables(
            materialized.get("headers"), csv_row, unresolved
        )
        materialized["path_params"] = self._apply_variables(
            materialized.get("path_params"), csv_row, unresolved, url_encode=True
        )
        materialized["query_params"] = self._apply_variables(
            materialized.get("query_params"), csv_row, unresolved
        )
        materialized["body"] = self._apply_variables(
            materialized.get("body"), csv_row, unresolved
        )
        materialized["contains_text"] = self._apply_variables(
            materialized.get("contains_text"), csv_row, unresolved
        )
        materialized["unresolved_variables"] = sorted(set(unresolved))
        materialized["full_url"] = self._build_full_url(
            materialized, str(http_defaults.get("base_url") or ""), include_query=True
        )
        return materialized

    def _apply_variables(
        self, value: Any, csv_row: Dict[str, Any],
        unresolved: Optional[List[str]] = None, *, url_encode: bool = False,
    ) -> Any:
        if isinstance(value, dict):
            return {
                str(key): self._apply_variables(item, csv_row, unresolved, url_encode=url_encode)
                for key, item in value.items()
            }
        if isinstance(value, list):
            return [
                self._apply_variables(item, csv_row, unresolved, url_encode=url_encode)
                for item in value
            ]
        if isinstance(value, str):
            return self._substitute_variables(
                value, csv_row, unresolved=unresolved, url_encode=url_encode
            )
        return value

    def _substitute_variables(
        self, text: str, csv_row: Dict[str, Any], *,
        unresolved: Optional[List[str]] = None, url_encode: bool = False,
    ) -> str:
        if not text:
            return text
        result = str(text)
        # 迭代展开嵌套占位符（如 a=${b}, b=X），最多 10 轮防止循环引用死循环。
        for _ in range(10):
            updated = result
            for key, value in csv_row.items():
                replacement = self._encode_path_value(value) if url_encode else str(value)
                updated = updated.replace("${" + str(key) + "}", replacement)
            if updated == result:
                break
            result = updated
        if "${" in result and unresolved is not None:
            unresolved.append(result[:120])
        return result

    def _build_payload_preview(self, payload: Any) -> str:
        if payload in (None, "", {}, []):
            return ""
        limit = perf_registry.get_performance_limits().max_request_preview_chars
        if isinstance(payload, (dict, list)):
            return json.dumps(payload, ensure_ascii=False, indent=2)[:limit]
        return str(payload)[:limit]

    # 分位数算法与数值转换统一定义在类前部（_percentile / _to_int / _to_float）。

    def _to_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError, OverflowError):
            return default

    def _to_float(self, value: Any, default: float) -> float:
        try:
            result = float(value)
        except (TypeError, ValueError, OverflowError):
            return default
        # inf / nan 会让 sleep 卡死或让 duration 永不结束，一律回落到默认值
        return result if math.isfinite(result) else default

    def _percentile(self, values: List[float], percentile: float) -> float:
        if not values:
            return 0.0
        # 分位数越界会直接索引越界，统一钳制到 [0, 100]
        percentile = max(0.0, min(100.0, self._to_float(percentile, 0.0)))
        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return sorted_values[0]
        if perf_registry.get_percentile_method() == "linear":
            position = (len(sorted_values) - 1) * percentile / 100
            lower_index = int(math.floor(position))
            upper_index = int(math.ceil(position))
            if lower_index == upper_index:
                return sorted_values[lower_index]
            lower_value = sorted_values[lower_index]
            upper_value = sorted_values[upper_index]
            return lower_value + (upper_value - lower_value) * (position - lower_index)
        # JMeter Aggregate Report 的 nearest-rank 口径
        rank = max(1, int(math.ceil(len(sorted_values) * percentile / 100)))
        return sorted_values[min(rank, len(sorted_values)) - 1]
