"""QA 审计回归：代码注入 / XSS / shell 注入 / JS 注入修复验证。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.api_dev_tools import InterfaceDevTools  # noqa: E402
from qa_toolkit.core.api_test_core import InterfaceAutoTestCore  # noqa: E402


def test_pytest_script_cannot_be_injected_via_triple_single_quote():
    """issue #21: 导入文档的 ''' 不得逃逸为可执行代码。"""
    core = InterfaceAutoTestCore()
    name = "x''' + __import__('os').system('touch /tmp/pwned') + '''"
    cases = [{
        "case_id": "c1", "name": name, "method": "GET", "path": "/x",
        "headers": {}, "body": None, "expected_status": 200,
    }]
    code = core._build_runtime_helpers({"environments": {}}, cases)
    # 生成的脚本必须是合法 Python，且注入片段只能是字符串数据的一部分
    compile(code, "<generated>", "exec")
    ca_line = [line for line in code.splitlines() if line.startswith("CASES = ")][0]
    # repr(json.dumps(...)) 会让三单引号变成转义序列，不再有裸的 ''' 边界
    assert "\\'\\'\\'" in ca_line
    assert "json.loads(" in ca_line
    assert "'''" not in ca_line  # 不再使用裸三单引号包裹数据


def test_html_report_escapes_dynamic_fields():
    """issue #22: HTML 报告中的接口名/路径/framework 必须转义。"""
    core = InterfaceAutoTestCore()
    report_path = core.generate_html_report(
        {"total": 1, "passed": 1, "failed": 0, "errors": 0},
        "<script>alert(1)</script>",
    )
    report = Path(report_path).read_text(encoding="utf-8")
    assert "<script>alert(1)</script>" not in report
    assert "&lt;script&gt;" in report


def test_curl_snippet_shell_metacharacters_are_quoted():
    """issue #8: curl 片段中的 $(...) 与反引号必须被 shell 引用。"""
    tools = InterfaceDevTools()
    snippet = tools._render_curl_snippet(
        "GET", "https://h/?q=$(echo hi)", {"X-T": "`echo bye`"}, None
    )
    assert "'https://h/?q=$(echo hi)'" in snippet
    assert "'-H 'X-T: `echo bye`''" in snippet or "-H 'X-T: `echo bye`'" in snippet
