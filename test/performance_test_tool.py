import csv
import html
import io
import json
import math
import random
import statistics
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

import requests


class PerformanceTestTool:
    """JMeter 风格接口性能测试工具"""

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
        """构建压测计划"""
        selected_indexes = selected_indexes or list(range(len(interfaces)))
        thread_group = thread_group or {}
        request_defaults = request_defaults or {}
        assertions = assertions or {}
        timer_config = timer_config or {}
        csv_data_set = csv_data_set or {}
        transaction_controller = transaction_controller or {}

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
                "max_response_ms": self._to_float(assertions.get("max_response_ms"), 0.0),
            }
            samplers.append(
                {
                    "index": index + 1,
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
                    "preview_url": self._build_full_url(item, base_url, include_query=True),
                }
            )

        users = self._to_int(thread_group.get("users"), 10)
        ramp_up_seconds = self._to_float(thread_group.get("ramp_up_seconds"), 0.0)
        loop_count = self._to_int(thread_group.get("loop_count"), 1)
        duration_seconds = self._to_float(thread_group.get("duration_seconds"), 0.0)
        start_delay_seconds = self._to_float(thread_group.get("start_delay_seconds"), 0.0)

        timeout_seconds = self._to_float(request_defaults.get("timeout_seconds"), 30.0)
        verify_ssl = bool(request_defaults.get("verify_ssl", True))
        follow_redirects = bool(request_defaults.get("follow_redirects", True))
        keep_alive = bool(request_defaults.get("keep_alive", True))

        think_time_ms = self._to_float(timer_config.get("think_time_ms"), 0.0)
        random_jitter_ms = self._to_float(timer_config.get("random_jitter_ms"), 0.0)
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
            },
            "timer": {
                "think_time_ms": max(think_time_ms, 0.0),
                "random_jitter_ms": max(random_jitter_ms, 0.0),
            },
            "csv_data_set": csv_config,
            "transaction_controller": transaction_config,
            "assertions": {
                "contains_text": str(assertions.get("contains_text") or "").strip(),
                "max_response_ms": self._to_float(assertions.get("max_response_ms"), 0.0),
                "expected_status_mode": assertions.get("expected_status_mode", "document"),
                "custom_expected_status": self._to_int(assertions.get("custom_expected_status"), 200),
            },
            "samplers": samplers,
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

        users = max(self._to_int(thread_group.get("users"), 1), 1)
        start_delay_seconds = self._to_float(thread_group.get("start_delay_seconds"), 0.0)

        if not samplers:
            raise ValueError("压测计划中没有可执行的 HTTP Sampler")

        if start_delay_seconds > 0:
            time.sleep(start_delay_seconds)

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
                worker_result = future.result()
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
        """生成 HTML 报告"""
        summary = result.get("summary", {})
        per_sampler = result.get("per_sampler", [])
        per_transaction = result.get("per_transaction", [])
        errors = result.get("error_samples", [])
        timeline = result.get("timeline", [])

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
                f"<td>{item.get('status_code', '')}</td>"
                f"<td>{item.get('elapsed_ms', 0):.2f}</td>"
                f"<td>{html.escape(item.get('error_message', '')[:300])}</td>"
                "</tr>"
                for item in errors[:50]
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
      <div class="metrics">
        <div class="metric"><div class="label">总请求数</div><div class="value">{summary.get("total_requests", 0)}</div></div>
        <div class="metric"><div class="label">成功率</div><div class="value">{summary.get("success_rate", 0):.1f}%</div></div>
        <div class="metric"><div class="label">平均响应</div><div class="value">{summary.get("avg_ms", 0):.2f}ms</div></div>
        <div class="metric"><div class="label">P90</div><div class="value">{summary.get("p90_ms", 0):.2f}ms</div></div>
        <div class="metric"><div class="label">P95</div><div class="value">{summary.get("p95_ms", 0):.2f}ms</div></div>
        <div class="metric"><div class="label">吞吐量</div><div class="value">{summary.get("throughput_rps", 0):.2f} rps</div></div>
      </div>
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
      <h2>Error Samples</h2>
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

        ramp_up_seconds = self._to_float(thread_group.get("ramp_up_seconds"), 0.0)
        loop_count = self._to_int(thread_group.get("loop_count"), 1)
        think_time_ms = self._to_float(timer_config.get("think_time_ms"), 0.0)
        random_jitter_ms = self._to_float(timer_config.get("random_jitter_ms"), 0.0)

        if ramp_up_seconds > 0 and total_users > 0:
            time.sleep(ramp_up_seconds * (user_number - 1) / total_users)

        session = requests.Session()
        if not http_defaults.get("keep_alive", True):
            session.headers.update({"Connection": "close"})

        samples: List[Dict[str, Any]] = []
        transaction_samples: List[Dict[str, Any]] = []
        current_loop = 0
        unlimited_loop = stop_monotonic is not None and loop_count == 0
        csv_thread_index = 0

        try:
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

                    if think_time_ms > 0 or random_jitter_ms > 0:
                        actual_sleep_ms = think_time_ms
                        if random_jitter_ms > 0:
                            actual_sleep_ms += random.uniform(0, random_jitter_ms)
                        if actual_sleep_ms > 0:
                            time.sleep(actual_sleep_ms / 1000)

                    if transaction_controller.get("enabled") and transaction_controller.get("stop_on_error") and not sample.get("success"):
                        break

                if transaction_controller.get("enabled"):
                    transaction_elapsed_ms = (time.perf_counter() - transaction_started_perf) * 1000
                    transaction_finished_wall = time.time()
                    transaction_samples.append(
                        {
                            "transaction_name": transaction_controller.get("name", "Transaction Controller"),
                            "thread_name": f"VU-{user_number}",
                            "thread_number": user_number,
                            "loop_number": current_loop,
                            "success": transaction_success,
                            "sampler_count": executed_sampler_count,
                            "elapsed_ms": round(transaction_elapsed_ms, 3),
                            "error_message": "; ".join(transaction_errors[:5]),
                            "started_at": datetime.fromtimestamp(transaction_started_wall).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "finished_at": datetime.fromtimestamp(transaction_finished_wall).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
                            "relative_second": max(int(math.floor(transaction_started_wall - start_wall)), 0),
                            "csv_variables": csv_row or {},
                        }
                    )
        finally:
            session.close()

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
        materialized_sampler = self._materialize_sampler(sampler, http_defaults, csv_row or {})
        url = str(materialized_sampler.get("full_url") or "")
        headers = deepcopy(materialized_sampler.get("headers") or {})
        body = deepcopy(materialized_sampler.get("body"))
        method = str(materialized_sampler.get("method") or "GET").upper()
        request_format = str(materialized_sampler.get("request_format") or "auto")
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
        request_headers = deepcopy(headers)
        request_payload = request_kwargs.get("json", request_kwargs.get("data"))
        request_body_preview = self._build_payload_preview(request_payload)

        try:
            response = session.request(method, url, **request_kwargs)
            elapsed_ms = (time.perf_counter() - started_perf) * 1000
            status_code = int(response.status_code)
            response_text = response.text or ""
            response_size = len(response.content or b"")
            response_preview = response_text[:400]
            response_headers = dict(response.headers or {})
            response_message = str(response.reason or "")
            success, error_message = self._assert_response(materialized_sampler, response_text, status_code, elapsed_ms)
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - started_perf) * 1000
            response_message = exc.__class__.__name__
            error_message = str(exc)
        finished_at = time.time()

        return {
            "sampler_name": sampler.get("name", "未命名接口"),
            "sampler_label": sampler.get("label", ""),
            "thread_name": f"VU-{user_number}",
            "thread_number": user_number,
            "loop_number": loop_number,
            "method": method,
            "url": url,
            "status_code": status_code,
            "success": success,
            "elapsed_ms": round(elapsed_ms, 3),
            "response_size": response_size,
            "response_preview": response_preview,
            "response_headers": response_headers,
            "response_message": response_message,
            "request_headers": request_headers,
            "request_body_preview": request_body_preview,
            "error_message": error_message,
            "csv_variables": csv_row or {},
            "started_at": datetime.fromtimestamp(started_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "finished_at": datetime.fromtimestamp(finished_at).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3],
            "relative_second": max(int(math.floor(started_at - start_wall)), 0),
        }

    def _assert_response(
        self,
        sampler: Dict[str, Any],
        response_text: str,
        status_code: int,
        elapsed_ms: float,
    ) -> (bool, str):
        expected_status = sampler.get("expected_status")
        contains_text = str(sampler.get("contains_text") or "").strip()
        max_response_ms = self._to_float(sampler.get("max_response_ms"), 0.0)

        errors = []
        if expected_status is not None and int(status_code) != int(expected_status):
            errors.append(f"状态码断言失败，期望 {expected_status}，实际 {status_code}")
        if contains_text and contains_text not in response_text:
            errors.append(f"响应内容未包含断言文本: {contains_text}")
        if max_response_ms > 0 and elapsed_ms > max_response_ms:
            errors.append(f"响应时间超过阈值，期望 <= {max_response_ms:.2f}ms，实际 {elapsed_ms:.2f}ms")

        if not errors and expected_status is None and status_code >= 400:
            errors.append(f"HTTP 请求失败，状态码 {status_code}")

        return len(errors) == 0, "; ".join(errors)

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
        elapsed_seconds = max(end_monotonic - start_monotonic, 0.001)
        success_samples = [item for item in samples if item.get("success")]
        failed_samples = [item for item in samples if not item.get("success")]
        elapsed_values = [float(item.get("elapsed_ms", 0.0)) for item in samples]

        summary = {
            "started_at": datetime.fromtimestamp(start_wall).strftime("%Y-%m-%d %H:%M:%S"),
            "finished_at": datetime.fromtimestamp(end_wall).strftime("%Y-%m-%d %H:%M:%S"),
            "total_requests": len(samples),
            "success_requests": len(success_samples),
            "failed_requests": len(failed_samples),
            "success_rate": (len(success_samples) / len(samples) * 100) if samples else 0.0,
            "elapsed_seconds": elapsed_seconds,
            "throughput_rps": len(samples) / elapsed_seconds if elapsed_seconds > 0 else 0.0,
            "avg_ms": statistics.mean(elapsed_values) if elapsed_values else 0.0,
            "min_ms": min(elapsed_values) if elapsed_values else 0.0,
            "max_ms": max(elapsed_values) if elapsed_values else 0.0,
            "p50_ms": self._percentile(elapsed_values, 50),
            "p90_ms": self._percentile(elapsed_values, 90),
            "p95_ms": self._percentile(elapsed_values, 95),
            "p99_ms": self._percentile(elapsed_values, 99),
        }

        per_sampler = self._build_per_sampler_summary(samples, elapsed_seconds)
        per_transaction = self._build_per_transaction_summary(transaction_samples)
        timeline = self._build_timeline(samples)
        error_samples = failed_samples[:100]
        summary_listener = self._build_summary_listener(samples)
        expose_transaction_samples = bool((plan.get("transaction_controller") or {}).get("generate_parent_sample", True))

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
        }

    def _build_per_sampler_summary(self, samples: List[Dict[str, Any]], elapsed_seconds: float) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in samples:
            groups.setdefault(item.get("sampler_label", "unknown"), []).append(item)

        results = []
        for sampler_label, group_samples in groups.items():
            elapsed_values = [float(item.get("elapsed_ms", 0.0)) for item in group_samples]
            success_count = sum(1 for item in group_samples if item.get("success"))
            results.append(
                {
                    "sampler_name": sampler_label,
                    "requests": len(group_samples),
                    "success_rate": (success_count / len(group_samples) * 100) if group_samples else 0.0,
                    "avg_ms": statistics.mean(elapsed_values) if elapsed_values else 0.0,
                    "min_ms": min(elapsed_values) if elapsed_values else 0.0,
                    "max_ms": max(elapsed_values) if elapsed_values else 0.0,
                    "p90_ms": self._percentile(elapsed_values, 90),
                    "p95_ms": self._percentile(elapsed_values, 95),
                    "throughput_rps": len(group_samples) / elapsed_seconds if elapsed_seconds > 0 else 0.0,
                    "failed_requests": sum(1 for item in group_samples if not item.get("success")),
                }
            )

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
        for bucket in sorted(buckets.keys()):
            item = buckets[bucket]
            elapsed_values = item.pop("elapsed_values", [])
            item["avg_ms"] = statistics.mean(elapsed_values) if elapsed_values else 0.0
            item["max_ms"] = max(elapsed_values) if elapsed_values else 0.0
            rows.append(item)
        return rows

    def _build_per_transaction_summary(self, transaction_samples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for item in transaction_samples:
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
        if method == "GET" and not query_params and isinstance(interface.get("parameters"), dict):
            query_params = interface.get("parameters")

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
        return {
            "enabled": True,
            "rows": rows,
            "row_count": len(rows),
            "variable_names": variable_names,
            "preview_rows": rows[:5],
            "delimiter": delimiter[0],
            "quotechar": quotechar[0],
            "sharing_mode": str(csv_data_set.get("sharing_mode") or "all_threads"),
            "recycle_on_eof": bool(csv_data_set.get("recycle_on_eof", True)),
            "stop_thread_on_eof": bool(csv_data_set.get("stop_thread_on_eof", False)),
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
            path = path.replace("{" + str(key) + "}", str(value))

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
        query_dict = dict(parse_qsl(parsed.query, keep_blank_values=True))
        query_dict.update({str(key): str(value) for key, value in query_params.items()})
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
    ) -> (Dict[str, Any], int, bool):
        if not csv_config.get("enabled"):
            return {}, local_index, False

        rows = csv_runtime.get("rows") if csv_runtime else []
        if not rows:
            return {}, local_index, bool(csv_config.get("stop_thread_on_eof"))

        sharing_mode = str(csv_config.get("sharing_mode") or "all_threads")
        recycle_on_eof = bool(csv_config.get("recycle_on_eof", True))
        stop_thread_on_eof = bool(csv_config.get("stop_thread_on_eof", False))

        if sharing_mode == "current_thread":
            index = local_index
            if index >= len(rows):
                if stop_thread_on_eof and not recycle_on_eof:
                    return {}, local_index, True
                if not recycle_on_eof:
                    return {}, local_index, False
                index = 0
            next_index = index + 1
            if next_index >= len(rows) and recycle_on_eof:
                next_index = 0
            return deepcopy(rows[index]), next_index, False

        with csv_runtime["lock"]:
            index = int(csv_runtime.get("shared_index", 0))
            if index >= len(rows):
                if stop_thread_on_eof and not recycle_on_eof:
                    return {}, local_index, True
                if not recycle_on_eof:
                    return {}, local_index, False
                index = 0
            row = deepcopy(rows[index])
            next_index = index + 1
            if next_index >= len(rows):
                if recycle_on_eof:
                    next_index = 0
            csv_runtime["shared_index"] = next_index
        return row, local_index, False

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
        materialized["path"] = self._apply_variables(materialized.get("path"), csv_row)
        materialized["headers"] = self._apply_variables(materialized.get("headers"), csv_row)
        materialized["path_params"] = self._apply_variables(materialized.get("path_params"), csv_row)
        materialized["query_params"] = self._apply_variables(materialized.get("query_params"), csv_row)
        materialized["body"] = self._apply_variables(materialized.get("body"), csv_row)
        materialized["contains_text"] = self._apply_variables(materialized.get("contains_text"), csv_row)
        materialized["full_url"] = self._build_full_url(materialized, str(http_defaults.get("base_url") or ""), include_query=True)
        return materialized

    def _apply_variables(self, value: Any, csv_row: Dict[str, Any]) -> Any:
        if isinstance(value, dict):
            return {str(key): self._apply_variables(item, csv_row) for key, item in value.items()}
        if isinstance(value, list):
            return [self._apply_variables(item, csv_row) for item in value]
        if isinstance(value, str):
            return self._substitute_variables(value, csv_row)
        return value

    def _substitute_variables(self, text: str, csv_row: Dict[str, Any]) -> str:
        if not text:
            return text
        result = str(text)
        for key, value in csv_row.items():
            result = result.replace("${" + str(key) + "}", str(value))
        return result

    def _build_payload_preview(self, payload: Any) -> str:
        if payload in (None, "", {}, []):
            return ""
        if isinstance(payload, (dict, list)):
            return json.dumps(payload, ensure_ascii=False, indent=2)[:1000]
        return str(payload)[:1000]

    def _percentile(self, values: List[float], percentile: float) -> float:
        if not values:
            return 0.0
        sorted_values = sorted(values)
        if len(sorted_values) == 1:
            return sorted_values[0]
        position = (len(sorted_values) - 1) * percentile / 100
        lower_index = int(math.floor(position))
        upper_index = int(math.ceil(position))
        if lower_index == upper_index:
            return sorted_values[lower_index]
        lower_value = sorted_values[lower_index]
        upper_value = sorted_values[upper_index]
        return lower_value + (upper_value - lower_value) * (position - lower_index)

    def _to_int(self, value: Any, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _to_float(self, value: Any, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
