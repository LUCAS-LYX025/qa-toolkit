"""JSON 处理工具页面：解析/格式化、差异对比、JSONPath 查询。"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict

import streamlit as st

from qa_toolkit.core.json_registry import (
    get_export_formats,
    get_registry_summary,
    get_samples,
)
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_button
from qa_toolkit.ui.components.status_feedback import render_info_feedback
from qa_toolkit.utils.json_utils import (
    MAX_INPUT_CHARS,
    JsonParseError,
    build_input_signature,
    compare_json_values,
    execute_jsonpath,
    format_parse_error,
    format_jsonpath_result,
    parse_json_text,
    serialize_json,
)

DEFAULT_STATE: Dict[str, Any] = {
    "json_parser_text": '{"name": "Tom", "age": 25, "hobbies": ["reading", "swimming"]}',
    "json_parser_version": 0,
    "json_parser_result": None,
    "json_parser_error": "",
    "json_compare_left": '{"name": "John", "age": 30, "city": "New York"}',
    "json_compare_right": '{"name": "Jane", "age": 25, "country": "USA"}',
    "json_compare_version": 0,
    "json_compare_result": None,
    "json_compare_error": "",
    "json_query_text": '{"store": {"book": [{"title": "Book 1", "author": "Author 1"}, {"title": "Book 2", "author": "Author 2"}]}}',
    "json_query_expression": "$.store.book[*].author",
    "json_query_version": 0,
    "json_query_result": None,
    "json_query_error": "",
    "json_strict": True,
    "json_allow_jsonl": True,
    "json_numeric_equivalent": True,
    "json_indent": "2 空格",
    "json_sort_keys": False,
    "json_escape_unicode": False,
    "json_max_chars": MAX_INPUT_CHARS,
    "json_export_format": "JSON",
}

JSONPATH_CHEATSHEET = [
    ("`$.store.book[0].title`", "按属性与下标取值"),
    ("`$..author`", "递归查找所有 author（每个节点只返回一次）"),
    ("`$.store.*`", "取 store 下的所有值"),
    ("`$..book[?(@.price<10)].title`", "过滤：价格低于 10 的书名"),
    ("`$['store']['book'][0]['title']`", "标准括号字符串索引"),
    ("`$.items.length()`", "调用注册的函数（支持 length/keys/values）"),
]


def _ensure_state() -> None:
    for key, value in DEFAULT_STATE.items():
        st.session_state.setdefault(key, value)


def _serialize_options() -> Dict[str, Any]:
    indent = st.session_state.json_indent
    return {
        "indent": 4 if indent == "4 空格" else 2,
        "compact": indent == "紧凑",
        "ensure_ascii": bool(st.session_state.json_escape_unicode),
        "sort_keys": bool(st.session_state.json_sort_keys),
        "allow_nan": False,
    }


def _parse_options() -> Dict[str, Any]:
    return {
        "strict": bool(st.session_state.json_strict),
        "allow_jsonl": bool(st.session_state.json_allow_jsonl),
        "max_chars": int(st.session_state.json_max_chars),
    }


def _export(value: Any, *, label: str, default_name: str) -> None:
    formats = get_export_formats()
    selected = st.session_state.json_export_format
    spec = formats.get(selected)
    if spec is None:
        selected, spec = next(iter(formats.items()))
    if selected == "JSON" and label == "result":
        data = serialize_json(value, **_serialize_options())
    else:
        data = spec.serializer(value)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.download_button(
        f"⬇️ 下载{default_name}（{selected}）",
        data=data.encode("utf-8"),
        file_name=f"{label}_{stamp}.{spec.extension}",
        mime=spec.mime,
        use_container_width=True,
        key=f"json_download_{default_name}_{stamp}",
    )


def _render_options() -> None:
    with st.expander("解析与导出选项", expanded=False):
        st.checkbox("严格 JSON（拒绝 NaN / Infinity）", key="json_strict")
        st.checkbox("尝试按 JSONL 逐行解析", key="json_allow_jsonl")
        st.checkbox("数值等价（1 与 1.0 视为相同）", key="json_numeric_equivalent")
        st.selectbox("缩进", ["2 空格", "4 空格", "紧凑"], key="json_indent")
        st.checkbox("键排序", key="json_sort_keys")
        st.checkbox("转义中文为 \\uXXXX", key="json_escape_unicode")
        st.number_input(
            "输入字符上限", min_value=1_000, max_value=20_000_000,
            step=100_000, key="json_max_chars",
        )
        st.selectbox("导出格式", list(get_export_formats().keys()), key="json_export_format")
        summary = get_registry_summary()
        st.caption(
            f"当前扩展点：JSONPath 函数 {summary['jsonpath_functions']} 个 / "
            f"导出格式 {summary['export_formats']} 种 / "
            f"示例 {summary['samples']} 个 / 校验器 {summary['validators']} 条。"
        )


def _render_sample_loader(target: str) -> None:
    samples = get_samples()
    choice = st.selectbox("载入示例", ["不载入"] + list(samples.keys()), key=f"json_sample_{target}")
    if choice == "不载入":
        return
    sample = samples[choice]
    if target == "query":
        st.session_state.json_query_text = sample.text
        st.session_state.json_query_expression = sample.expression
        st.session_state.json_query_version += 1
    else:
        st.session_state.json_parser_text = sample.text
        st.session_state.json_parser_version += 1
    st.session_state[f"json_{target}_result"] = None
    st.session_state[f"json_{target}_error"] = ""
    st.rerun()


def _render_parser() -> None:
    show_doc("json_parser")
    _render_options()
    _render_sample_loader("parser")
    text = st.text_area(
        "JSON 输入",
        value=st.session_state.json_parser_text,
        height=300,
        key=f"json_parser_input_{st.session_state.json_parser_version}",
        placeholder='请输入 JSON，例如 {"name": "Tom"}',
    )
    cols = st.columns(4)
    parse_clicked = action_button("🚀 解析 JSON", key="json_parse")
    format_clicked = action_button("✨ 格式化", key="json_format")
    clear_clicked = action_button("🗑️ 清空", key="json_parser_clear")

    if format_clicked:
        try:
            parsed = parse_json_text(text, **_parse_options())
            st.session_state.json_parser_text = serialize_json(parsed.value, **_serialize_options())
            st.session_state.json_parser_version += 1
            st.session_state.json_parser_result = None
            st.session_state.json_parser_error = ""
            st.rerun()
        except Exception as exc:
            st.session_state.json_parser_error = format_parse_error(exc, text)

    if clear_clicked:
        st.session_state.json_parser_text = ""
        st.session_state.json_parser_version += 1
        st.session_state.json_parser_result = None
        st.session_state.json_parser_error = ""
        st.rerun()

    if parse_clicked:
        signature = build_input_signature(text, _parse_options())
        try:
            parsed = parse_json_text(text, **_parse_options())
            st.session_state.json_parser_result = {
                "value": parsed.value,
                "warnings": parsed.warnings,
                "jsonl": parsed.jsonl,
                "signature": signature,
            }
            st.session_state.json_parser_error = ""
        except Exception as exc:
            st.session_state.json_parser_result = None
            st.session_state.json_parser_error = format_parse_error(exc, text)

    if st.session_state.json_parser_error:
        st.error(f"解析失败：{st.session_state.json_parser_error}")

    result = st.session_state.json_parser_result
    if not result:
        return
    if result.get("signature") != build_input_signature(text, _parse_options()):
        render_info_feedback("输入已变更，请重新点击“解析 JSON”。", title="结果已过期")
        return

    st.markdown("### 📊 解析结果")
    for warning in result.get("warnings", []):
        st.warning(warning)
    st.code(serialize_json(result["value"], **_serialize_options()), language="json")
    _export(result["value"], label="result", default_name="解析结果")


def _render_comparison() -> None:
    show_doc("json_comparison")
    _render_options()
    cols = st.columns(2)
    with cols[0]:
        left = st.text_area(
            "JSON 1",
            value=st.session_state.json_compare_left,
            height=300,
            key=f"json_compare_left_{st.session_state.json_compare_version}",
        )
    with cols[1]:
        right = st.text_area(
            "JSON 2",
            value=st.session_state.json_compare_right,
            height=300,
            key=f"json_compare_right_{st.session_state.json_compare_version}",
        )

    buttons = st.columns(4)
    format_clicked = action_button("✨ 格式化全部", key="json_format_all")
    compare_clicked = action_button("🔍 开始对比", key="json_compare")
    swap_clicked = action_button("🔄 交换数据", key="json_swap")
    clear_clicked = action_button("🗑️ 清空全部", key="json_compare_clear")

    if format_clicked:
        try:
            left_text = serialize_json(parse_json_text(left, **_parse_options()).value, **_serialize_options()) if left.strip() else ""
            right_text = serialize_json(parse_json_text(right, **_parse_options()).value, **_serialize_options()) if right.strip() else ""
            st.session_state.json_compare_left = left_text
            st.session_state.json_compare_right = right_text
            st.session_state.json_compare_version += 1
            st.session_state.json_compare_result = None
            st.session_state.json_compare_error = ""
            st.rerun()
        except Exception as exc:
            st.session_state.json_compare_error = format_parse_error(exc, left or right)

    if swap_clicked:
        st.session_state.json_compare_left, st.session_state.json_compare_right = right, left
        st.session_state.json_compare_version += 1
        st.session_state.json_compare_result = None
        st.session_state.json_compare_error = ""
        st.rerun()

    if clear_clicked:
        st.session_state.json_compare_left = ""
        st.session_state.json_compare_right = ""
        st.session_state.json_compare_version += 1
        st.session_state.json_compare_result = None
        st.session_state.json_compare_error = ""
        st.rerun()

    if compare_clicked:
        signature = build_input_signature(
            left, right, bool(st.session_state.json_numeric_equivalent)
        )
        if not left.strip() or not right.strip():
            st.session_state.json_compare_result = None
            st.session_state.json_compare_error = "两侧都需要输入 JSON 内容。"
        else:
            try:
                obj1 = parse_json_text(left, **_parse_options()).value
                obj2 = parse_json_text(right, **_parse_options()).value
                differences, stats = compare_json_values(
                    obj1, obj2,
                    numeric_equivalent=bool(st.session_state.json_numeric_equivalent),
                )
                st.session_state.json_compare_result = {
                    "differences": differences,
                    "stats": {"differences_count": stats.differences_count, "keys_compared": stats.keys_compared},
                    "signature": signature,
                }
                st.session_state.json_compare_error = ""
            except Exception as exc:
                st.session_state.json_compare_result = None
                st.session_state.json_compare_error = format_parse_error(exc, left if "left" in str(exc) else right)

    if st.session_state.json_compare_error:
        st.error(st.session_state.json_compare_error)

    result = st.session_state.json_compare_result
    if not result:
        return
    if result.get("signature") != build_input_signature(
        left, right, bool(st.session_state.json_numeric_equivalent)
    ):
        render_info_feedback("输入已变更，请重新点击“开始对比”。", title="结果已过期")
        return

    st.markdown("### 📋 对比结果")
    metrics = st.columns(2)
    metrics[0].metric("差异数", result["stats"]["differences_count"])
    metrics[1].metric("已比较节点", result["stats"]["keys_compared"])
    report = "\n".join(f"- {item}" for item in result["differences"]) or "- 两个 JSON 对象完全相同"
    st.code(report, language="text")
    _export(result["differences"], label="diff", default_name="差异结果")


def _render_jsonpath() -> None:
    show_doc("jsonpath_tool")
    _render_options()
    left, right = st.columns([1, 1])
    with left:
        st.markdown("**📝 JSON 数据**")
        data_text = st.text_area(
            "JSON 数据",
            value=st.session_state.json_query_text,
            height=360,
            key=f"json_query_input_{st.session_state.json_query_version}",
            placeholder="输入 JSON 数据，可开启 JSONL 模式",
        )
        st.markdown("**🎯 JSONPath 表达式**")
        expression = st.text_input(
            "JSONPath 表达式",
            value=st.session_state.json_query_expression,
            key=f"json_query_expr_{st.session_state.json_query_version}",
            placeholder="例如 $.store.book[*].author",
        )
        run_clicked = action_button("🚀 执行查询", key="json_query_run")

    _render_sample_loader("query")

    with st.expander("JSONPath 速查", expanded=False):
        for expression_text, description in JSONPATH_CHEATSHEET:
            st.markdown(f"- {expression_text}：{description}")

    if run_clicked:
        signature = build_input_signature(data_text, expression)
        try:
            parsed = parse_json_text(data_text, **_parse_options())
            values = execute_jsonpath(parsed.value, expression)
            st.session_state.json_query_result = {
                "values": values,
                "warnings": parsed.warnings,
                "signature": signature,
            }
            st.session_state.json_query_error = ""
        except Exception as exc:
            st.session_state.json_query_result = None
            if isinstance(exc, JsonParseError):
                st.session_state.json_query_error = (
                    f"JSON 数据格式错误：{format_parse_error(exc, data_text)}"
                    if exc.kind != "jsonpath"
                    else exc.message
                )
            else:
                st.session_state.json_query_error = str(exc)

    with right:
        st.markdown("### 📋 查询结果")
        if st.session_state.json_query_error:
            st.error(st.session_state.json_query_error)
        result = st.session_state.json_query_result
        if not result:
            return
        if result.get("signature") != build_input_signature(data_text, expression):
            render_info_feedback("输入或表达式已变更，请重新执行查询。", title="结果已过期")
            return
        for warning in result.get("warnings", []):
            st.warning(warning)
        values = result["values"]
        st.success(f"✅ 找到 {len(values)} 个匹配项")
        st.metric("匹配数量", len(values))
        if not values:
            st.info("没有匹配项，可检查属性名或使用 `$..` 递归查找。")
        for index, item in enumerate(values, 1):
            with st.expander(f"结果 #{index}", expanded=len(values) <= 3):
                if isinstance(item, (dict, list)):
                    st.json(item)
                else:
                    st.code(serialize_json(item, compact=True), language="text")
        _export(values, label="jsonpath", default_name="查询结果")


def render_json_tools_page() -> None:
    _ensure_state()
    st.markdown('<div class="qa-tool-content">', unsafe_allow_html=True)
    mode = st.radio(
        "选择处理模式",
        ["JSON解析与格式化", "JSON数据对比", "JSONPath查询"],
        horizontal=True,
        key="json_tool_mode",
    )
    if mode == "JSON解析与格式化":
        _render_parser()
    elif mode == "JSON数据对比":
        _render_comparison()
    else:
        _render_jsonpath()
    st.markdown("</div>", unsafe_allow_html=True)
