"""审计问题回归测试：锁定边界修复与测试盲区类问题的正确行为。"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from PIL import Image

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))


# ---------------------------------------------------------------------------
# 74: tool_page_shell 渲染函数 HTML 转义
# ---------------------------------------------------------------------------
def test_tool_page_shell_escapes_dynamic_html():
    import qa_toolkit.ui.components.tool_page_shell as shell

    with patch.object(shell.st, "markdown") as markdown:
        shell.render_tool_page_hero(
            icon="<b>I</b>",
            title="<script>alert(1)</script>",
            description="<img src=x onerror=alert(1)>",
            tags=["<tag>", "normal"],
        )
    rendered = markdown.call_args_list[-1].args[0]
    assert "<script>" not in rendered
    assert "<img" not in rendered
    assert "&lt;script&gt;" in rendered
    assert "&lt;tag&gt;" in rendered

    with patch.object(shell.st, "markdown") as markdown:
        shell.render_tool_tips("<b>tips</b>", ["<li-item>", "ok"])
    rendered = markdown.call_args_list[-1].args[0]
    assert "<b>tips</b>" not in rendered
    assert "&lt;li-item&gt;" in rendered

    with patch.object(shell.st, "markdown") as markdown:
        shell.render_tool_empty_state("<h4>x</h4>", "<p>y</p>")
    rendered = markdown.call_args_list[-1].args[0]
    assert "<h4>x</h4>" not in rendered
    assert "&lt;p&gt;" in rendered


# ---------------------------------------------------------------------------
# 75: 报告 response_time 非数值规范化
# ---------------------------------------------------------------------------
def test_report_generator_normalizes_response_time():
    from qa_toolkit.reporting.report_generator import EnhancedReportGenerator

    generator = EnhancedReportGenerator()
    assert generator._coerce_response_time("abc") == 0.0
    assert generator._coerce_response_time(None) == 0.0
    assert generator._coerce_response_time(-5) == 0.0
    assert generator._coerce_response_time(float("nan")) == 0.0
    assert generator._coerce_response_time(float("inf")) == 0.0
    assert generator._coerce_response_time("1.5") == 1.5

    validated = generator._validate_test_details([{"response_time": "abc"}])
    assert validated[0]["response_time"] == 0.0
    detail_text = generator._format_test_detail({"response_time": "abc"})
    assert "响应时间: 0.00秒" in detail_text


# ---------------------------------------------------------------------------
# 76: feedback_store 输入校验
# ---------------------------------------------------------------------------
def test_feedback_store_tolerates_invalid_input(tmp_path):
    from qa_toolkit.support.feedback_store import FeedbackStore

    store = FeedbackStore(tmp_path / "feedback.sqlite3")
    saved = store.add_feedback({"rating": "abc", "content": None})

    assert saved["rating"] == 5
    assert saved["content"] == ""
    assert saved["type"] == "其他"
    assert saved["urgency"] == "一般"

    out_of_range = store.add_feedback({"rating": 99, "type": "问题反馈", "urgency": "重要"})
    assert out_of_range["rating"] == 5


# ---------------------------------------------------------------------------
# 77: add_watermark 失败必须可见
# ---------------------------------------------------------------------------
def test_add_watermark_surfaces_failures():
    from qa_toolkit.utils.image_processing import ImageProcessor

    processor = ImageProcessor()
    image = Image.new("RGB", (16, 16), (255, 255, 255))

    with pytest.raises(RuntimeError, match="添加水印失败"):
        processor.add_watermark(
            image=image,
            text="x",
            position="图片中心",
            font_size=12,
            color=(255, 255, 255),
            opacity="invalid",
            rotation=0,
        )


# ---------------------------------------------------------------------------
# 78: 目标文件体积边界
# ---------------------------------------------------------------------------
def test_convert_to_target_filesize_rejects_invalid_targets():
    from qa_toolkit.utils.image_processing import ImageProcessor

    processor = ImageProcessor()
    image = Image.new("RGB", (32, 32), (120, 130, 140))

    for invalid in (0, -1, "1024", 1.5):
        with pytest.raises(ValueError):
            processor.convert_to_target_filesize(image, invalid)

    result = processor.convert_to_target_filesize(image, 1, output_format="JPG")
    assert result["target_achieved"] is False
    assert result["size_bytes"] > 0
    assert result["note"]


# ---------------------------------------------------------------------------
# 79/98: json_utils 循环引用与深嵌套防护
# ---------------------------------------------------------------------------
def test_json_utils_handles_circular_references():
    from qa_toolkit.utils.json_utils import JSONFileUtils

    utils = JSONFileUtils()
    first = {"x": 1}
    first["self"] = first
    second = {"y": 2}
    second["self"] = second

    assert utils.get_json_depth(first) < utils.MAX_TRAVERSAL_DEPTH
    assert isinstance(utils.count_keys(first), int)
    assert utils.compare_json(first, first) == []
    assert isinstance(utils.compare_json(first, second), list)

    deep = {}
    cursor = deep
    for _ in range(5000):
        cursor["next"] = {}
        cursor = cursor["next"]
    assert utils.get_json_depth(deep) <= utils.MAX_TRAVERSAL_DEPTH


# ---------------------------------------------------------------------------
# 84: env_profile_manager 损坏 store_file 降级为空配置
# ---------------------------------------------------------------------------
def test_env_profile_manager_tolerates_corrupted_store(tmp_path):
    from qa_toolkit.core.env_profile_manager import EnvProfileManager

    store_file = tmp_path / "env_profiles.json"
    key_file = tmp_path / ".env_profiles.key"

    for broken in ("{not json", "[]", "123", ""):
        store_file.write_text(broken, encoding="utf-8")
        manager = EnvProfileManager(store_file=store_file, key_file=key_file)
        assert manager.list_profiles() == []


# ---------------------------------------------------------------------------
# 85: log_analysis search_lines 边界
# ---------------------------------------------------------------------------
def test_search_lines_handles_invalid_regex_and_mismatched_map():
    from qa_toolkit.utils.log_analysis import search_lines

    with pytest.raises(ValueError, match="正则表达式错误"):
        search_lines(["anything"], "[", use_regex=True)

    lines = ["error first", "middle", "error last"]
    results = search_lines(lines, "error", line_number_map=[10], context_after=1)
    assert [item["line_number"] for item in results] == [11, 3]
    assert results[0]["context_after"][0]["line"] == "middle"


# ---------------------------------------------------------------------------
# 86: regex_tools 非法正则结构化错误与匹配上限
# ---------------------------------------------------------------------------
def test_analyze_regex_returns_structured_error_for_invalid_pattern():
    from qa_toolkit.utils.regex_tools import MAX_MATCH_RECORDS, analyze_regex

    result = analyze_regex("[", "abc")
    assert result["error"]
    assert result["match_count"] == 0
    assert result["risk_warnings"][0]["level"] == "error"

    truncated = analyze_regex("a", "a" * (MAX_MATCH_RECORDS + 100))
    assert truncated["match_count"] <= MAX_MATCH_RECORDS
    assert any(item["title"] == "匹配结果已截断" for item in truncated["risk_warnings"])


# ---------------------------------------------------------------------------
# 87: ip_lookup 网络异常统一返回错误字典
# ---------------------------------------------------------------------------
def test_ip_lookup_queries_handle_network_failures():
    from qa_toolkit.tools.ip_lookup import IPQueryTool

    tool = IPQueryTool()
    with patch.object(tool, "_request_json", side_effect=TimeoutError("timeout")):
        icp = tool.query_icp_info("example.com")
    assert icp["success"] is False
    assert "error" in icp

    with patch.object(tool, "_request_json", side_effect=TimeoutError("timeout")):
        subdomains = tool.query_subdomains("example.com")
    assert subdomains["success"] is True
    assert "查询失败" in subdomains["data"]["错误信息"]

    with patch.object(tool, "_request_text", side_effect=OSError("offline")):
        reverse = tool.query_reverse_sites("8.8.8.8")
    assert reverse["success"] is False
    assert "error" in reverse


# ---------------------------------------------------------------------------
# 88: application_security_tool 损坏包返回友好错误
# ---------------------------------------------------------------------------
def test_scan_mobile_package_rejects_corrupted_packages():
    from qa_toolkit.core.application_security_tool import ApplicationSecurityTool

    tool = ApplicationSecurityTool()
    corrupted = tool.scan_mobile_package("broken.apk", b"not a zip archive")
    assert corrupted["success"] is False
    assert "error" in corrupted

    unsupported = tool.scan_mobile_package("notes.txt", b"plain text")
    assert unsupported["success"] is False


# ---------------------------------------------------------------------------
# 90: task_run_panel 稳定标识符映射
# ---------------------------------------------------------------------------
def test_task_run_panel_resolves_run_id_without_string_split():
    from qa_toolkit.ui.components.task_run_panel import _build_run_options, _resolve_run_id

    records = [
        {"run_id": "abc | def", "action": "run", "status": "success"},
        {"run_id": "second", "action": "retry", "status": "failed"},
    ]
    indexes, labels = _build_run_options(records)

    assert indexes == [0, 1]
    assert "abc | def" in labels[0]
    assert _resolve_run_id(records, 0) == "abc | def"
    assert _resolve_run_id(records, 1) == "second"
    assert _resolve_run_id(records, 99) == ""


# ---------------------------------------------------------------------------
# 91: documentation 模块回归测试
# ---------------------------------------------------------------------------
def test_documentation_module_behaviour():
    import qa_toolkit.support.documentation as documentation
    from qa_toolkit.support.documentation import ToolDocumentationManager, show_doc

    manager = ToolDocumentationManager()
    assert manager.get_tool_info("__missing__") is None
    assert manager.get_tool_info("data_generator") is not None

    manager.add_tool_documentation("__temporary__", "临时", "用法", "备注")
    assert "__temporary__" in manager.get_available_tools()

    with patch.object(documentation.st, "warning") as warning:
        manager.display_tool_documentation("__missing__")
        assert warning.called
    with patch.object(documentation.st, "warning") as warning:
        show_doc("__missing__")
        assert warning.called

    for name in manager.get_available_tools():
        info = manager.get_tool_info(name)
        assert info["title"] and info["usage"] and info["notes"]


def test_documentation_keys_match_show_doc_calls_in_pages():
    from qa_toolkit.support.documentation import ToolDocumentationManager

    doc_keys = set(ToolDocumentationManager().tool_docs)
    used_keys = set()
    pages_dir = SRC_DIR / "qa_toolkit" / "ui" / "pages"
    for path in pages_dir.glob("*.py"):
        used_keys.update(re.findall(r'show_doc\(\s*["\']([^"\']+)["\']', path.read_text(encoding="utf-8")))

    assert used_keys
    assert used_keys <= doc_keys


# ---------------------------------------------------------------------------
# 92: paths 集中式目录初始化
# ---------------------------------------------------------------------------
def test_paths_ensure_directories_creates_all_runtime_dirs(tmp_path, monkeypatch):
    import qa_toolkit.paths as paths

    names = (
        "ASSETS_DIR", "BIN_DIR", "FONTS_DIR", "IMAGES_DIR", "EXAMPLES_DIR",
        "WORKSPACE_DIR", "UPLOADS_DIR", "API_CASES_DIR", "REPORTS_DIR", "FEEDBACK_DIR",
    )
    for name in names:
        monkeypatch.setattr(paths, name, tmp_path / name)

    paths.ensure_directories()
    for name in names:
        assert (tmp_path / name).is_dir()


# ---------------------------------------------------------------------------
# 93/94: 配置文件约束
# ---------------------------------------------------------------------------
def test_streamlit_upload_limits_are_reduced():
    config = (ROOT_DIR / ".streamlit" / "config.toml").read_text(encoding="utf-8")
    assert "maxUploadSize = 50" in config
    assert "maxMessageSize = 50" in config


def test_pytest_ini_declares_markers():
    ini_text = (ROOT_DIR / "pytest.ini").read_text(encoding="utf-8")
    for marker in ("smoke", "unit", "security", "regression"):
        assert re.search(rf"^\s*{marker}:", ini_text, re.MULTILINE)


# ---------------------------------------------------------------------------
# 95: text_analysis .doc 无 textutil 时给出明确提示
# ---------------------------------------------------------------------------
def test_decode_uploaded_text_reports_missing_textutil():
    from qa_toolkit.utils.text_analysis import decode_uploaded_text

    with patch("qa_toolkit.utils.text_analysis.shutil.which", return_value=None):
        with pytest.raises(ValueError, match="textutil"):
            decode_uploaded_text(b"binary", "document.doc")
