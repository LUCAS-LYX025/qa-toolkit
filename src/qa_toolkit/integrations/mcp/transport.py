"""MCP 传输层：stdio 子进程与 Streamable HTTP，统一为 JSON-RPC 2.0 请求/响应。

两个关键安全约束：
- stdio 绝不使用 ``shell=True``，参数逐项传入，且只执行注册项声明的 command；
- HTTP 目标在客户端层先过 ``validate_target_url``，本层只负责协议与解析。
"""
from __future__ import annotations

import json
import os
import select
import subprocess
import threading
import urllib.error
import urllib.request
from typing import Any, Callable, Dict, Optional, Protocol


class McpTransport(Protocol):
    def send(self, request: Dict[str, Any]) -> Dict[str, Any]: ...

    def notify(self, notification: Dict[str, Any]) -> None: ...

    def close(self) -> None: ...


class TransportError(RuntimeError):
    pass


class StdioTransport:
    """按行读写的 stdio JSON-RPC 传输；请求串行，读超时受控。"""

    def __init__(
        self,
        command: str,
        args: Any,
        *,
        env: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
        popen_factory: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.command = command
        self.args = list(args or ())
        self.env = env
        self.timeout_seconds = float(timeout_seconds)
        self._popen = popen_factory or subprocess.Popen
        self._proc: Any = None
        self._lock = threading.RLock()

    def start(self) -> None:
        with self._lock:
            if self._proc is not None:
                return
            try:
                self._proc = self._popen(
                    [self.command, *self.args],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.DEVNULL,
                    text=True,
                    bufsize=1,
                    env=self.env,
                )
            except OSError as exc:
                raise TransportError(f"启动 MCP 进程失败：{exc}") from exc

    def send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        self.start()
        with self._lock:
            payload = json.dumps(request, ensure_ascii=False) + "\n"
            try:
                assert self._proc is not None
                self._proc.stdin.write(payload)
                self._proc.stdin.flush()
            except (OSError, ValueError, AttributeError) as exc:
                raise TransportError(f"写入 MCP 进程失败：{exc}") from exc
            # npx 首次拉包提示、server 调试日志都可能混进 stdout：
            # 逐行跳过非 JSON-RPC 内容，只接受与本次请求 id 匹配的响应。
            for _ in range(20):
                ready, _, _ = select.select([self._proc.stdout], [], [], self.timeout_seconds)
                if not ready:
                    raise TransportError(f"等待 MCP 响应超时（{self.timeout_seconds} 秒）")
                line = self._proc.stdout.readline()
                if not line:
                    raise TransportError("MCP 进程已关闭输出流")
                try:
                    parsed = json.loads(line)
                except ValueError:
                    continue
                if not isinstance(parsed, dict):
                    continue
                if not any(key in parsed for key in ("jsonrpc", "result", "error", "id")):
                    continue
                if "id" in request and parsed.get("id") != request["id"]:
                    continue
                return parsed
            raise TransportError("连续 20 行都没有匹配的 JSON-RPC 响应")

    def notify(self, notification: Dict[str, Any]) -> None:
        """发送无 id 的通知（如 initialized），不等待响应。"""
        self.start()
        with self._lock:
            try:
                assert self._proc is not None
                self._proc.stdin.write(json.dumps(notification, ensure_ascii=False) + "\n")
                self._proc.stdin.flush()
            except (OSError, ValueError, AttributeError) as exc:
                raise TransportError(f"写入 MCP 通知失败：{exc}") from exc

    def close(self) -> None:
        with self._lock:
            proc = self._proc
            self._proc = None
            if proc is None:
                return
            try:
                proc.stdin.close()
            except Exception:
                pass
            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass


class HttpTransport:
    """Streamable HTTP 传输；同时兼容纯 JSON 响应与 ``text/event-stream``。"""

    def __init__(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        timeout_seconds: float = 30.0,
        opener: Optional[Callable[..., Any]] = None,
    ) -> None:
        self.url = url
        self.headers = dict(headers or {})
        self.timeout_seconds = float(timeout_seconds)
        self._opener = opener or urllib.request.urlopen

    def send(self, request: Dict[str, Any]) -> Dict[str, Any]:
        body = json.dumps(request, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self.headers,
        }
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with self._opener(req, timeout=self.timeout_seconds) as response:
                content_type = response.headers.get("Content-Type", "")
                raw = response.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:200]
            raise TransportError(f"MCP HTTP {exc.code}：{detail}") from exc
        except urllib.error.URLError as exc:
            raise TransportError(f"MCP HTTP 连接失败：{exc.reason}") from exc
        if "text/event-stream" in content_type:
            return _parse_sse(raw)
        try:
            parsed = json.loads(raw)
        except ValueError as exc:
            raise TransportError(f"MCP HTTP 响应不是合法 JSON：{raw[:120]}") from exc
        if not isinstance(parsed, dict):
            raise TransportError("MCP HTTP 响应不是 JSON 对象")
        return parsed

    def notify(self, notification: Dict[str, Any]) -> None:
        body = json.dumps(notification, ensure_ascii=False).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            **self.headers,
        }
        req = urllib.request.Request(self.url, data=body, headers=headers, method="POST")
        try:
            with self._opener(req, timeout=self.timeout_seconds):
                return None
        except urllib.error.HTTPError as exc:
            if exc.code in (200, 202, 204):
                return None
            raise TransportError(f"MCP HTTP 通知失败：{exc.code}") from exc
        except urllib.error.URLError as exc:
            raise TransportError(f"MCP HTTP 通知连接失败：{exc.reason}") from exc

    def close(self) -> None:
        return None


def _parse_sse(raw: str) -> Dict[str, Any]:
    """从 SSE 流里取最后一条可解析的 data 事件。"""
    last: Dict[str, Any] = {}
    for line in raw.splitlines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            last = parsed
    if not last:
        raise TransportError("MCP SSE 流中没有可解析的 data 事件")
    return last
