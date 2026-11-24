"""测试用例生成器专项审计回归测试（issues #119-#132）。"""
import json
import subprocess
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.tools import test_case_generator as tcg_module
from qa_toolkit.tools.test_case_generator import TestCaseGenerator


def _generator():
    return TestCaseGenerator()


def _case(case_id="TC001", name="登录成功", priority="高"):
    return {
        "用例ID": case_id,
        "用例名称": name,
        "前置条件": "账号正常",
        "测试步骤": "1. 输入账号",
        "预期结果": "进入首页",
        "优先级": priority,
        "测试类型": "功能",
    }


def result_app_stale():
    import streamlit as st
    from qa_toolkit.tools.test_case_generator import TestCaseGenerator
    from qa_toolkit.ui.pages import test_case_generator_page as page

    page._ensure_defaults()
    st.session_state.tcg_generated_cases = [{
        "用例ID": "TC001", "用例名称": "新用例", "前置条件": "-",
        "测试步骤": "打开", "预期结果": "成功", "优先级": "低", "测试类型": "功能",
    }]
    st.session_state.tcg_result_priorities = ["高", "中"]
    page._render_generation_results(TestCaseGenerator())


def result_app_normal():
    import streamlit as st
    from qa_toolkit.tools.test_case_generator import TestCaseGenerator
    from qa_toolkit.ui.pages import test_case_generator_page as page

    page._ensure_defaults()
    st.session_state.tcg_generated_cases = [
        {
            "用例ID": "TC001", "用例名称": "登录成功", "前置条件": "账号正常",
            "测试步骤": "输入账号", "预期结果": "进入首页", "优先级": "高", "测试类型": "功能",
        },
        {
            "用例ID": "TC002", "用例名称": "密码错误", "前置条件": "账号锁定",
            "测试步骤": "输入错误密码", "预期结果": "提示错误", "优先级": "中", "测试类型": "异常",
        },
    ]
    page._render_generation_results(TestCaseGenerator())


def test_issue_119_stale_priorities_do_not_break_results_page():
    at = AppTest.from_function(result_app_stale).run()
    assert not at.exception
    assert at.multiselect[0].value == ["低"]


def test_issue_120_empty_priority_filter_shows_no_cases():
    at = AppTest.from_function(result_app_normal).run()
    assert not at.exception
    at.multiselect[0].set_value([]).run()
    assert not at.exception
    assert any("请至少选择一个优先级" in item.value for item in at.markdown)


def test_issue_121_parse_skips_malformed_records():
    cases = _generator()._parse_testcases('[null, "x", 3, {"用例名称":"ok"}]', "TC", "中文")
    assert len(cases) == 1
    assert cases[0]["用例名称"] == "ok"


def test_issue_122_baidu_token_is_encoded_and_has_timeout(monkeypatch):
    calls = []

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            if "oauth/2.0/token" in calls[-1]["url"]:
                return {"access_token": "fake-token"}
            return {"result": '[{"用例名称":"登录"}]'}

    def fake_post(url, **kwargs):
        calls.append({"url": url, "timeout": kwargs.get("timeout")})
        return FakeResponse()

    monkeypatch.setattr(tcg_module.requests, "post", fake_post)
    gen = _generator()
    cases = gen._call_baidu_api(
        requirement="登录",
        api_config={"api_key": "a&b", "secret_key": "c=d"},
        id_prefix="TC", case_style="标准格式", language="中文",
        target_case_count=3, coverage_focus=[],
    )
    assert cases[0]["用例名称"] == "登录"
    assert "client_id=a%26b" in calls[0]["url"]
    assert "client_secret=c%3Dd" in calls[0]["url"]
    assert calls[0]["timeout"] is not None


def test_issue_123_missing_api_key_raises_clear_value_error():
    with pytest.raises(ValueError, match="缺少必要配置: api_key"):
        _generator().generate_testcases("登录", "ali", {})


def test_issue_124_target_count_type_is_validated():
    gen = _generator()
    assert tcg_module._coerce_target_case_count("12") == 12
    with pytest.raises(ValueError, match="目标用例数必须是整数"):
        gen.generate_testcases("登录", "ali", {"api_key": "x"}, target_case_count=None)


def test_issue_125_prompt_target_count_is_clamped():
    prompt = _generator()._build_prompt("登录", "TC", "标准格式", "中文", target_case_count=10 ** 9)
    assert "约60条" in prompt
    assert "1000000000" not in prompt


def test_issue_126_compose_accepts_none_optional_fields():
    result = _generator().compose_requirement_context("需求", None, None, None, None, None, None)
    assert result == "需求原文:\n需求"


def test_issue_127_markdown_cells_escape_pipe_and_newline():
    md = _generator().generate_markdown_report(
        [_case(name="a|b") | {"前置条件": "x\ny"}], "需求"
    )
    row = [line for line in md.splitlines() if "TC001" in line][0]
    assert "a\\|b" in row
    assert "x<br>y" in row
    assert row.replace("\\|", "").count("|") == 8  # 7 单元格 → 8 个分隔符，转义后不再多列


def test_issue_128_export_follows_filtered_rows(monkeypatch):
    at = AppTest.from_function(result_app_normal).run()
    at.text_input[0].set_value("TC002").run()
    assert not at.exception
    assert any("当前导出 1 / 2 条" in item.value for item in at.caption)


def test_issue_129_ocr_subprocess_timeout_wrapped(monkeypatch):
    from PIL import Image
    from io import BytesIO

    gen = _generator()
    gen.pytesseract = None
    gen.ocr_backend = "tesseract-cli"
    gen.tesseract_cmd = "/bin/false"

    def raise_timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0] if args else "tesseract", 1)

    monkeypatch.setattr(tcg_module.subprocess, "run", raise_timeout)
    buffer = BytesIO()
    Image.new("RGB", (8, 8), "white").save(buffer, format="PNG")
    with pytest.raises(RuntimeError, match="OCR 识别超时"):
        gen.extract_text_from_image(buffer.getvalue())


def test_issue_130_keyword_filter_searches_case_id():
    at = AppTest.from_function(result_app_normal).run()
    at.text_input[0].set_value("TC002").run()
    assert not at.exception
    assert any("当前导出 1 / 2 条" in item.value for item in at.caption)


def test_issue_131_priority_list_is_human_readable():
    normalized = _generator().normalize_case_record({"优先级": ["高", "中"]})
    assert normalized["优先级"] == "高、中"


def test_issue_132_spark_client_uses_timeout(monkeypatch):
    captured = {}

    class FakeCompletions:
        def create(self, **kwargs):
            captured["create"] = kwargs

            class Choice:
                message = type("Msg", (), {"content": '[{"用例名称":"登录"}]'})()

            return type("Resp", (), {"choices": [Choice()]})()

    class FakeOpenAI:
        def __init__(self, **kwargs):
            captured["init"] = kwargs
            self.chat = type("Chat", (), {"completions": FakeCompletions()})()

    monkeypatch.setattr("openai.OpenAI", FakeOpenAI)
    cases = _generator()._call_spark_api(
        requirement="登录", api_config={"api_key": "key", "model_id": "model"},
        id_prefix="TC", case_style="标准格式", language="中文",
        target_case_count=3, coverage_focus=[],
    )
    assert cases[0]["用例名称"] == "登录"
    assert captured["init"]["timeout"] == 60
    assert captured["create"]["timeout"] == 60
