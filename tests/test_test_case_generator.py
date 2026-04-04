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
