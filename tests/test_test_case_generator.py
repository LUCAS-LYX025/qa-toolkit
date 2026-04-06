import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.tools.test_case_generator import TestCaseGenerator


def test_clean_requirement_text_collapses_spaces_and_blank_lines():
    generator = TestCaseGenerator()

    raw_text = "需求一  \r\n\r\n  支持新增地址\t\t\r\n\r\n\r\n必填手机号  "
    cleaned = generator.clean_requirement_text(raw_text)

    assert cleaned == "需求一\n\n支持新增地址\n\n必填手机号"


def test_compose_requirement_context_merges_multiple_sources():
    generator = TestCaseGenerator()

    composed = generator.compose_requirement_context(
        requirement="用户可以新增地址",
        ocr_text="[图片] 地址列表页支持编辑",
        module_name="用户中心-地址管理",
        business_rules="默认地址只能有1个",
        acceptance_criteria="保存成功后列表立即刷新",
        out_of_scope="本次不覆盖性能压测",
        additional_notes="当前仅支持 App 端",
    )

    assert "需求原文" in composed
    assert "图片识别补充需求" in composed
    assert "默认地址只能有1个" in composed
    assert "当前仅支持 App 端" in composed


def test_analyze_requirement_returns_focus_and_unclear_points():
    generator = TestCaseGenerator()

    analysis = generator.analyze_requirement(
        "用户登录功能支持账号密码登录，管理员可查看登录日志。"
        "用户名长度限制 6-20 位，密码错误时需要提示。"
    )

    assert analysis["complexity"] in {"中", "高"}
    assert "权限角色" in analysis["suggested_focus"]
    assert any("长度" in item for item in analysis["business_rules"])
    assert "管理员" in analysis["roles"]


def test_parse_testcases_supports_markdown_code_block_and_wrapper_dict():
    generator = TestCaseGenerator()

    response_text = """```json
    {
      "test_cases": [
        {
          "用例ID": "TC001",
          "用例名称": "登录成功",
          "前置条件": "用户已注册",
          "测试步骤": "1. 输入账号\\n2. 输入密码\\n3. 点击登录",
          "预期结果": "进入首页",
          "优先级": "高",
          "测试类型": "功能"
        }
      ]
    }
    ```"""

    cases = generator._parse_testcases(response_text, "TC", "中文")

    assert len(cases) == 1
    assert cases[0]["用例ID"] == "TC001"
    assert cases[0]["测试类型"] == "功能"


def test_generate_markdown_report_handles_english_case_keys():
    generator = TestCaseGenerator()

    markdown = generator.generate_markdown_report(
        [
            {
                "Case ID": "TC001",
                "Case Name": "Login with valid account",
                "Precondition": "User account exists",
                "Test Steps": "1. Open page",
                "Expected Result": "Login succeeds",
                "Priority": "High",
                "Test Type": "Functional",
            }
        ],
        "User can login with account and password",
    )

    assert "TC001" in markdown
    assert "Login with valid account" in markdown
    assert "Functional" in markdown


def test_normalize_case_record_maps_english_fields_and_priority():
    generator = TestCaseGenerator()

    normalized = generator.normalize_case_record(
        {
            "Case ID": "TC100",
            "Case Name": "Upload avatar",
            "Precondition": "User logged in",
            "Test Steps": "1. Open profile",
            "Expected Result": "Avatar updated",
            "Priority": "High",
            "Test Type": "Functional",
            "Notes": "covers happy path",
        }
    )

    assert normalized["用例ID"] == "TC100"
    assert normalized["用例名称"] == "Upload avatar"
    assert normalized["优先级"] == "高"
    assert normalized["备注"] == "covers happy path"


def test_analyze_requirement_returns_default_hint_for_empty_text():
    generator = TestCaseGenerator()

    analysis = generator.analyze_requirement(" \n\t ")

    assert analysis["complexity"] == "低"
    assert analysis["line_count"] == 0
    assert "当前没有可分析的需求文本" in analysis["unclear_points"]


def test_get_ocr_status_reports_backend_when_available(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()
    generator.ocr_available = True
    generator.ocr_backend = "tesseract-cli"
    generator.tesseract_cmd = "/usr/local/bin/tesseract"

    status = generator.get_ocr_status()

    assert status["status"] == "available"
    assert "tesseract-cli" in status["message"]
    assert "tesseract" in status["message"]


def test_resolve_tesseract_command_skips_embedded_binary_on_linux(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()

    monkeypatch.setattr("qa_toolkit.tools.test_case_generator.shutil.which", lambda _: None)
    monkeypatch.setattr("qa_toolkit.tools.test_case_generator.platform.system", lambda: "Linux")
    monkeypatch.setattr("qa_toolkit.tools.test_case_generator.Path.exists", lambda self: self.name == "tesseract")
    monkeypatch.setattr(generator, "_is_usable_tesseract_command", lambda candidate: False)

    assert generator._resolve_tesseract_command() == ""


def test_resolve_tesseract_command_prefers_usable_system_binary(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()

    monkeypatch.setattr("qa_toolkit.tools.test_case_generator.shutil.which", lambda _: "/usr/bin/tesseract")
    monkeypatch.setattr(generator, "_is_usable_tesseract_command", lambda candidate: candidate == "/usr/bin/tesseract")

    assert generator._resolve_tesseract_command() == "/usr/bin/tesseract"


def test_resolve_chat_completion_url_supports_default_and_custom_base(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()

    assert generator._resolve_chat_completion_url() == "https://api.openai.com/v1/chat/completions"
    assert generator._resolve_chat_completion_url("https://gateway.example.com/v1") == (
        "https://gateway.example.com/v1/chat/completions"
    )
    assert generator._resolve_chat_completion_url("https://gateway.example.com/v1/chat/completions") == (
        "https://gateway.example.com/v1/chat/completions"
    )


def test_resolve_anthropic_messages_url_supports_default_and_custom_base(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()

    assert generator._resolve_anthropic_messages_url() == "https://api.anthropic.com/v1/messages"
    assert generator._resolve_anthropic_messages_url("https://gateway.example.com/v1") == (
        "https://gateway.example.com/v1/messages"
    )
    assert generator._resolve_anthropic_messages_url("https://api.anthropic.com") == (
        "https://api.anthropic.com/v1/messages"
    )
    assert generator._resolve_anthropic_messages_url("https://gateway.example.com/v1/messages") == (
        "https://gateway.example.com/v1/messages"
    )


def test_call_ali_api_uses_configured_model_version(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()
    captured = {}

    class _DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "output": {
                    "text": (
                        '[{"用例ID":"TC001","用例名称":"登录成功","前置条件":"账号存在",'
                        '"测试步骤":"1. 输入账号","预期结果":"登录成功","优先级":"高","测试类型":"功能"}]'
                    )
                }
            }

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _DummyResponse()

    monkeypatch.setattr("qa_toolkit.tools.test_case_generator.requests.post", _fake_post)

    cases = generator._call_ali_api(
        requirement="用户可以登录系统",
        api_config={"api_key": "test-key", "model_version": "qwen3-max"},
        id_prefix="TC",
        case_style="标准格式",
        language="中文",
        target_case_count=3,
        coverage_focus=["核心功能"],
    )

    assert captured["json"]["model"] == "qwen3-max"
    assert captured["url"].endswith("/generation")
    assert cases[0]["用例ID"] == "TC001"


def test_call_anthropic_api_uses_messages_endpoint_and_model_version(monkeypatch):
    monkeypatch.setattr(TestCaseGenerator, "_configure_ocr", lambda self: None)
    generator = TestCaseGenerator()
    captured = {}

    class _DummyResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "content": [
                    {
                        "type": "text",
                        "text": (
                            '[{"用例ID":"TC001","用例名称":"登录失败提示","前置条件":"账号存在",'
                            '"测试步骤":"1. 输入错误密码","预期结果":"提示密码错误","优先级":"高","测试类型":"异常"}]'
                        ),
                    }
                ]
            }

    def _fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        captured["timeout"] = timeout
        return _DummyResponse()

    monkeypatch.setattr("qa_toolkit.tools.test_case_generator.requests.post", _fake_post)

    cases = generator._call_anthropic_api(
        requirement="用户登录失败时需要给出提示",
        api_config={"api_key": "test-key", "model_version": "claude-sonnet-4-20250514"},
        id_prefix="TC",
        case_style="标准格式",
        language="中文",
        target_case_count=3,
        coverage_focus=["异常处理"],
    )

    assert captured["url"].endswith("/messages")
    assert captured["json"]["model"] == "claude-sonnet-4-20250514"
    assert captured["headers"]["anthropic-version"] == "2023-06-01"
    assert cases[0]["测试类型"] == "异常"
