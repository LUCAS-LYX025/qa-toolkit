"""外部 MCP 消费层专项审计探针（测试专家 + 产品工程师双视角）。

每项 record 的第二个参数为 True 表示问题坐实。修复前应为 N/N，修复后应为 0/N。
不输出任何凭据明文。
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from qa_toolkit.core import mcp_client_registry as reg  # noqa: E402
from qa_toolkit.core import mcp_config_import as imp  # noqa: E402
from qa_toolkit.integrations.mcp import capabilities as caps  # noqa: E402
from qa_toolkit.integrations.mcp import client as cli  # noqa: E402
from qa_toolkit.integrations.mcp import transport as tr  # noqa: E402

RESULTS = []


def record(case_id, reproduced, detail):
    RESULTS.append((case_id, reproduced, detail))
    print(f"{case_id}: {'REPRODUCED' if reproduced else 'resolved'} - {detail}", flush=True)


class FakeTransport:
    def __init__(self, responder):
        self.responder = responder

    def send(self, request):
        return self.responder(request)

    def notify(self, notification):
        return None

    def close(self):
        return None


def _ok_response(request):
    method = request["method"]
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": request["id"], "result": {"serverInfo": {"name": "fake"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": request["id"], "result": {"tools": [{"name": "search_workitems"}]}}
    return {"jsonrpc": "2.0", "id": request["id"], "result": {"content": [{"type": "text", "text": "{}"}]}}


def probe_01_duplicate_aliases():
    specs, _ = imp.import_mcp_configs()
    keys = {s.key for s in specs}
    bad = (
        ("mastergo" in keys and "mastergo-magic-mcp" in keys)
        or ("zentao" in keys and "zentao-11" in keys)
        or ("adb_mysql" in keys and "adb-mysql-mcp-server" in keys)
    )
    record("MCP-01", bad, f"导入后出现重复数据源：{sorted(k for k in keys if 'master' in k or 'zentao' in k or 'mysql' in k)}")


def probe_02_write_not_blocked_in_client():
    spec = reg.McpServerSpec(
        key="writable", label="writable", description="", transport="stdio",
        command="node", args=(), tool_allowlist=("update_work_item",),
    )
    client = cli.McpClient(spec, transport=FakeTransport(_ok_response))
    result = client.call_tool("update_work_item", {"id": "x", "status": "100085"})
    bad = result.ok
    allowed = cli.McpClient(spec, transport=FakeTransport(_ok_response), allow_write=True).call_tool(
        "update_work_item", {"id": "x", "status": "100085"})
    bad = bad or not allowed.ok
    record("MCP-02", bad, f"客户端直调写工具返回 ok={result.ok}（UI 确认可绕过）")


def probe_03_tool_cache_not_cleared():
    src = (ROOT / "src/qa_toolkit/ui/components/mcp_import_panel.py").read_text(encoding="utf-8")
    bad = '_PREFIX + "server"' not in src or "on_change" not in src
    record("MCP-03", bad, "切换数据源时未清空工具缓存（selectbox 无 on_change）")


def probe_04_candidates_silently_truncated():
    from qa_toolkit.ui.components.mcp_import_panel import _candidate_rows
    payload = [{"id": str(i), "subject": f"需求 {i}"} for i in range(25)]
    rows, total, truncated = _candidate_rows(payload)
    bad = len(rows) == 10 and not truncated
    record("MCP-04", bad, f"25 条候选只返回 {len(rows)} 条，truncated={truncated}（total={total}）")


def probe_05_serial_detection_too_broad():
    args, warnings = caps.build_search_arguments("手机号 123")
    bad = "subjectDescription" in args
    record("MCP-05", bad, f"自然语言里含数字被当精确编号：{args.get('subjectDescription')!r}，warnings={warnings}")


def probe_06_unbounded_extracted_text():
    payload = {"description": "需求描述" * 200000}
    text, warnings = caps.extract_semantic_text(payload, semantic_slot="requirement_detail")
    bad = len(text) > 100000 and not any("截断" in w for w in warnings)
    record("MCP-06", bad, f"抽取文本 {len(text)} 字符，无长度上限与告警")


def probe_07_stdio_noise_line():
    class Stream:
        def __init__(self, lines):
            self.lines = list(lines)

        def write(self, value):
            return None

        def flush(self):
            return None

        def readline(self):
            return self.lines.pop(0) if self.lines else ""

        def close(self):
            return None

    class Proc:
        def __init__(self):
            self.stdin = Stream([])
            self.stdout = Stream(["npm warn deprecated package\n", '{"jsonrpc":"2.0","id":1,"result":{}}\n'])

        def terminate(self):
            return None

        def wait(self, timeout=3):
            return 0

        def kill(self):
            return None

    transport = tr.StdioTransport("node", [], popen_factory=lambda *a, **k: Proc())
    original = tr.select.select
    tr.select.select = lambda *a, **k: ([a[0][0]], [], [])
    try:
        try:
            transport.send({"jsonrpc": "2.0", "id": 1, "method": "ping"})
            bad = False
            detail = "噪声行被自动跳过"
        except tr.TransportError as exc:
            bad = True
            detail = f"stdout 混入安装提示即失败：{str(exc)[:50]}"
    finally:
        tr.select.select = original
    record("MCP-07", bad, detail)


def probe_08_trace_string_secret():
    payload = cli.redact_payload({"note": "token=abc123secret; password=hunter2"})
    bad = "abc123secret" in json.dumps(payload) or "hunter2" in json.dumps(payload)
    record("MCP-08", bad, "字符串值里的 token/password 未脱敏，会进入 trace")


def probe_09_missing_env_not_surfaced():
    src = (ROOT / "src/qa_toolkit/ui/components/mcp_import_panel.py").read_text(encoding="utf-8")
    bad = "未设置" not in src and "缺少环境变量" not in src
    record("MCP-09", bad, "选中需要凭据的数据源时不提前提示缺哪个环境变量")


def probe_10_unfiltered_import_list():
    specs, _ = imp.import_mcp_configs()
    keys = {s.key for s in specs}
    bad = "playwright-extension" in keys and "yunxiao" in keys and len(specs) > 10
    record("MCP-10", bad, f"一次导入 {len(specs)} 项，浏览器/ GitHub 等无关服务淹没业务数据源")


def main():
    print("=== 外部 MCP 消费层专项审计探针（10 项） ===", flush=True)
    reg.reset_mcp_registry()
    caps.reset_mcp_capabilities()
    probe_01_duplicate_aliases()
    probe_02_write_not_blocked_in_client()
    probe_03_tool_cache_not_cleared()
    probe_04_candidates_silently_truncated()
    probe_05_serial_detection_too_broad()
    probe_06_unbounded_extracted_text()
    probe_07_stdio_noise_line()
    probe_08_trace_string_secret()
    probe_09_missing_env_not_surfaced()
    probe_10_unfiltered_import_list()
    reg.reset_mcp_registry()
    caps.reset_mcp_capabilities()
    reproduced = sum(1 for _, bad, _ in RESULTS if bad)
    print(f"共 {reproduced}/{len(RESULTS)} 项坐实（修复前应为 {len(RESULTS)}/{len(RESULTS)}，修复后应为 0/{len(RESULTS)}）", flush=True)


if __name__ == "__main__":
    main()
