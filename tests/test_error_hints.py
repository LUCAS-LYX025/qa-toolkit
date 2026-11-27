"""错误提示可操作性回归：异常不得裸抛，必须带上下文与可操作建议。"""
from __future__ import annotations

import json

import pytest

from qa_toolkit.ui.components.status_feedback import format_exception_hint


def test_json_error_gives_actionable_hint():
    try:
        json.loads("{bad json")
    except json.JSONDecodeError as exc:
        hint = format_exception_hint(exc, "解析接口文档")
    assert "解析接口文档失败" in hint
    assert "不是合法 JSON" in hint
    assert "JSONDecodeError" in hint


def test_value_error_keeps_original_message():
    hint = format_exception_hint(ValueError("响应样例不能为空"), "生成断言模板")
    assert "生成断言模板失败" in hint
    assert "输入内容不符合要求" in hint
    assert "响应样例不能为空" in hint


@pytest.mark.parametrize(
    "exc, keyword",
    [
        (KeyError("items"), "缺少必需的字段"),
        (TypeError("bad type"), "参数类型不匹配"),
        (FileNotFoundError("x.json"), "找不到指定的文件"),
        (PermissionError("denied"), "没有访问权限"),
        (TimeoutError(), "请求超时"),
        (ConnectionError("offline"), "网络连接失败"),
    ],
)
def test_common_exceptions_have_specific_hints(exc, keyword):
    assert keyword in format_exception_hint(exc, "执行操作")


def test_unknown_exception_still_gives_nonempty_hint():
    hint = format_exception_hint(RuntimeError("奇怪的错误"), "执行操作")
    assert "操作未能完成" in hint
    assert "奇怪的错误" in hint


def test_empty_exception_message_is_not_blank():
    hint = format_exception_hint(ValueError(), "执行操作")
    assert hint == "执行操作失败。输入内容不符合要求，请核对配置项后重试。"


def test_multiline_message_is_collapsed():
    hint = format_exception_hint(ValueError("第一行\n第二行"), "执行操作")
    assert "\n" not in hint
    assert "第一行 第二行" in hint


def test_no_action_uses_generic_prefix():
    hint = format_exception_hint(ValueError("x"))
    assert hint.startswith("操作失败。")
