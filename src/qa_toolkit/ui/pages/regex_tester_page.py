from __future__ import annotations

import json
import re
from datetime import datetime
from typing import Any, Dict, List

import pandas as pd
import streamlit as st

from qa_toolkit.config.constants import LANGUAGE_TEMPLATES, PREDEFINED_PATTERNS
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.utils.regex_tools import (
    analyze_regex,
    build_regex_code,
    generate_regex_from_examples,
    parse_example_items,
    suggest_field_patterns,
)

DEFAULT_STATE = {
    "regex_tool_pattern": "",
    "regex_tool_text": "",
    "regex_tool_selected_preset": "自定义",
    "regex_tool_selected_sample": "接口响应字段提取",
    "regex_tool_global_match": True,
    "regex_tool_ignore_case": False,
    "regex_tool_multiline": False,
    "regex_tool_dotall": False,
    "regex_tool_enable_replacement": False,
    "regex_tool_replacement_text": "",
    "regex_tool_replace_all": True,
    "regex_tool_recent_patterns": [],
    "regex_tool_recent_choice": "",
    "regex_tool_favorites": [],
    "regex_tool_favorite_name": "",
    "regex_tool_favorite_note": "",
    "regex_tool_favorite_import_text": "",
    "regex_tool_test_result": None,
    "regex_tool_test_error": "",
    "regex_tool_codegen_source": "沿用测试页表达式",
    "regex_tool_codegen_preset": "邮箱地址",
    "regex_tool_codegen_custom_pattern": "",
    "regex_tool_codegen_language": "Python",
    "regex_tool_codegen_operation": "匹配",
    "regex_tool_codegen_flags": [],
    "regex_tool_codegen_replacement": "",
    "regex_tool_generated_code": None,
    "regex_tool_examples_source": "",
    "regex_tool_examples_input": "",
    "regex_tool_generated_example_result": None,
    "regex_tool_examples_error": "",
    "regex_tool_quick_field_name": "",
    "regex_tool_quick_extract_source": "",
    "regex_tool_quick_extract_result": [],
    "regex_tool_quick_extract_error": "",
}

SAMPLE_CASES: Dict[str, Dict[str, Any]] = {
    "接口响应字段提取": {
        "pattern": r'"traceId"\s*:\s*"([^"]+)"',
        "text": '{\n  "code": 0,\n  "message": "success",\n  "traceId": "trace-20260405-0001",\n  "data": {"userId": 1001}\n}',
        "replacement": "traceId: <masked>",
    },
    "日志关键字段定位": {
        "pattern": r"ERROR\s+\[(?P<trace>[A-Z0-9-]+)\]\s+(.+)",
        "text": "2026-04-05 10:23:18 INFO [TRACE-1001] start request\n2026-04-05 10:23:19 ERROR [TRACE-1002] payment timeout\n2026-04-05 10:23:20 WARN [TRACE-1003] retry scheduled",
        "replacement": r"ERROR [\g<trace>] <masked>",
    },
    "URL 参数批量清洗": {
        "pattern": r"([?&]token=)[^&]+",
        "text": "https://qa.example.com/order?id=1001&token=abc123\nhttps://qa.example.com/refund?id=1002&token=xyz999",
        "replacement": r"\1***",
    },
    "订单号规则归纳": {
        "pattern": r"ORD-\d{6}",
        "text": "待处理订单: ORD-102401, ORD-102402, ORD-102499",
        "replacement": "ORDER-******",
    },
}

CODE_LANGUAGE_MAP = {
    "JavaScript": "javascript",
    "Python": "python",
    "PHP": "php",
    "Java": "java",
    "Go": "go",
    "C#": "csharp",
    "Ruby": "ruby",
}

MAX_MATCH_PREVIEW_ROWS = 500
MAX_UNIQUE_PREVIEW_ROWS = 200


def _ensure_defaults():
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _load_selected_preset():
    preset_name = st.session_state.regex_tool_selected_preset
    if preset_name != "自定义":
        st.session_state.regex_tool_pattern = PREDEFINED_PATTERNS[preset_name]


def _load_selected_sample():
    sample = SAMPLE_CASES[st.session_state.regex_tool_selected_sample]
    st.session_state.regex_tool_pattern = sample["pattern"]
    st.session_state.regex_tool_text = sample["text"]
    st.session_state.regex_tool_enable_replacement = True
    st.session_state.regex_tool_replacement_text = sample["replacement"]
    st.session_state.regex_tool_test_error = ""


def _apply_recent_pattern():
    if st.session_state.regex_tool_recent_choice:
        st.session_state.regex_tool_pattern = st.session_state.regex_tool_recent_choice


def _clear_playground():
    st.session_state.regex_tool_pattern = ""
    st.session_state.regex_tool_text = ""
    st.session_state.regex_tool_selected_preset = "自定义"
    st.session_state.regex_tool_enable_replacement = False
    st.session_state.regex_tool_replacement_text = ""
    st.session_state.regex_tool_test_result = None
    st.session_state.regex_tool_test_error = ""


def _clear_codegen():
    st.session_state.regex_tool_generated_code = None
    st.session_state.regex_tool_codegen_custom_pattern = ""
    st.session_state.regex_tool_codegen_replacement = ""
    st.session_state.regex_tool_codegen_flags = []


def _clear_examples():
    st.session_state.regex_tool_examples_source = ""
    st.session_state.regex_tool_examples_input = ""
    st.session_state.regex_tool_generated_example_result = None
    st.session_state.regex_tool_examples_error = ""


def _add_current_favorite():
    pattern = st.session_state.regex_tool_pattern.strip()
    if not pattern:
        st.warning("当前没有可收藏的表达式。")
        return

    name = st.session_state.regex_tool_favorite_name.strip() or f"收藏表达式 {len(st.session_state.regex_tool_favorites) + 1}"
    note = st.session_state.regex_tool_favorite_note.strip()

    favorites = [item for item in st.session_state.regex_tool_favorites if item["pattern"] != pattern]
    favorites.insert(0, {"name": name, "pattern": pattern, "note": note})
    st.session_state.regex_tool_favorites = favorites[:20]
    st.session_state.regex_tool_favorite_name = ""
    st.session_state.regex_tool_favorite_note = ""
    st.success("已加入收藏夹。")


def _apply_favorite(index: int):
    favorite = st.session_state.regex_tool_favorites[index]
    st.session_state.regex_tool_pattern = favorite["pattern"]


def _delete_favorite(index: int):
    favorites = list(st.session_state.regex_tool_favorites)
    if 0 <= index < len(favorites):
        favorites.pop(index)
    st.session_state.regex_tool_favorites = favorites


def _import_favorites():
    raw_text = st.session_state.regex_tool_favorite_import_text.strip()
    if not raw_text:
        st.warning("请先粘贴收藏夹 JSON。")
        return

    try:
        payload = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        st.error(f"收藏夹 JSON 解析失败: {exc}")
        return

    if not isinstance(payload, list):
        st.error("收藏夹 JSON 需要是数组格式。")
        return

    imported_items = []
    for item in payload:
        if not isinstance(item, dict):
            continue
        pattern = str(item.get("pattern", "")).strip()
        if not pattern:
            continue
        imported_items.append(
            {
                "name": str(item.get("name", "")).strip() or f"导入表达式 {len(imported_items) + 1}",
                "pattern": pattern,
                "note": str(item.get("note", "")).strip(),
            }
        )

    if not imported_items:
        st.warning("没有导入到有效的收藏项。")
        return

    merged = imported_items + list(st.session_state.regex_tool_favorites)
    deduped: List[Dict[str, str]] = []
    seen_patterns = set()
    for item in merged:
        if item["pattern"] in seen_patterns:
            continue
        seen_patterns.add(item["pattern"])
        deduped.append(item)

    st.session_state.regex_tool_favorites = deduped[:20]
    st.session_state.regex_tool_favorite_import_text = ""
    st.success(f"已导入 {len(imported_items)} 条收藏。")


def _push_recent_pattern(pattern: str):
    normalized = pattern.strip()
    if not normalized:
        return

    history = list(st.session_state.regex_tool_recent_patterns)
    history = [item for item in history if item != normalized]
    history.insert(0, normalized)
    st.session_state.regex_tool_recent_patterns = history[:8]
    st.session_state.regex_tool_recent_choice = normalized


def _resolve_codegen_pattern() -> str:
    source = st.session_state.regex_tool_codegen_source
    if source == "沿用测试页表达式":
        return st.session_state.regex_tool_pattern.strip()
    if source == "预定义模式":
        return PREDEFINED_PATTERNS[st.session_state.regex_tool_codegen_preset]
    return st.session_state.regex_tool_codegen_custom_pattern.strip()


def _build_match_dataframe(result: Dict[str, Any], limit: int | None = None) -> pd.DataFrame:
    rows: List[Dict[str, Any]] = []
    for item in result["matches"][:limit] if limit else result["matches"]:
        group_summary = ", ".join(
            f"{group['index']}={repr(group['value'])}" for group in item["groups"]
        ) or "-"
        named_summary = json.dumps(item["named_groups"], ensure_ascii=False) if item["named_groups"] else "-"
        rows.append(
            {
                "序号": item["index"],
                "匹配文本": item["match_text"],
                "位置": f"{item['start']}-{item['end']}",
                "行:列": f"{item['line']}:{item['column']}",
                "长度": item["length"],
                "捕获组": group_summary,
                "命名分组": named_summary,
            }
        )
    return pd.DataFrame(rows)


def _build_unique_csv(result: Dict[str, Any]) -> str:
    rows = result["unique_matches"]
    if not rows:
        return "match_text,count\n"
    return pd.DataFrame(rows).to_csv(index=False)


def _render_result_summary(result: Dict[str, Any]):
    metrics = st.columns(6)
    metrics[0].metric("匹配数", result["match_count"])
    metrics[1].metric("唯一值", result["unique_match_count"])
    metrics[2].metric("捕获组", result["group_count"])
    metrics[3].metric("命名组", len(result["named_group_names"]))
    metrics[4].metric("耗时", f"{result['execution_ms']:.3f} ms")
    metrics[5].metric("模式", "全局" if result["global_match"] else "首个")

    if result["flags_display"]:
        st.caption("已启用 flags: " + " / ".join(result["flags_display"]))
    for warning_item in result.get("risk_warnings", []):
        message = f"**{warning_item['title']}**: {warning_item['message']}"
        if warning_item["level"] == "warning":
            st.warning(message)
        else:
            st.info(message)
    if result["zero_length_match_count"]:
        st.warning(
            f"检测到 {result['zero_length_match_count']} 个零宽匹配，表达式可能在空位置反复命中。"
        )
    if not result["has_match"]:
        st.info("当前文本未命中任何结果，可以切换 flags 或调小约束后重试。")


def _render_playground_result():
    result = st.session_state.regex_tool_test_result
    if not result:
        return

    st.markdown("### 运行结果")
    _render_result_summary(result)
    st.markdown(result["preview_html"], unsafe_allow_html=True)

    matches_tab, unique_tab, replace_tab = st.tabs(["匹配明细", "唯一值提取", "替换预览"])
    with matches_tab:
        if result["matches"]:
            match_df = _build_match_dataframe(result, limit=MAX_MATCH_PREVIEW_ROWS)
            if result["match_count"] > MAX_MATCH_PREVIEW_ROWS:
                st.caption(f"当前仅预览前 {MAX_MATCH_PREVIEW_ROWS} 条匹配，完整数据请下载 CSV。")
            st.dataframe(match_df, use_container_width=True, hide_index=True)
            st.download_button(
                "下载匹配明细 CSV",
                data=_build_match_dataframe(result).to_csv(index=False).encode("utf-8-sig"),
                file_name=f"regex_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.info("暂无匹配明细。")

    with unique_tab:
        if result["unique_matches"]:
            unique_df = pd.DataFrame(result["unique_matches"][:MAX_UNIQUE_PREVIEW_ROWS])
            if result["unique_match_count"] > MAX_UNIQUE_PREVIEW_ROWS:
                st.caption(f"当前仅预览前 {MAX_UNIQUE_PREVIEW_ROWS} 条唯一值，完整数据请下载 CSV。")
            st.dataframe(unique_df, use_container_width=True, hide_index=True)
            st.download_button(
                "下载唯一值 CSV",
                data=_build_unique_csv(result).encode("utf-8-sig"),
                file_name=f"regex_unique_matches_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv",
            )
        else:
            st.info("当前没有可提取的唯一值。")

    with replace_tab:
        replacement_result = result.get("replacement")
        if not replacement_result:
            st.info("未启用替换预览。勾选“启用替换预览”后可查看替换结果。")
            return

        replace_cols = st.columns(3)
        replace_cols[0].metric("替换次数", replacement_result["count"])
        replace_cols[1].metric("替换范围", replacement_result["mode"])
        replace_cols[2].metric("结果长度", len(replacement_result["text"]))

        st.text_area(
            "替换后的文本",
            value=replacement_result["text"],
            height=220,
            disabled=True,
        )
        action_col1, action_col2 = st.columns(2)
        with action_col1:
            if st.button("用替换结果覆盖测试文本", key="regex_tool_apply_replaced_text", use_container_width=True):
                st.session_state.regex_tool_text = replacement_result["text"]
                st.rerun()
        with action_col2:
            st.download_button(
                "下载替换结果",
                data=replacement_result["text"],
                file_name=f"regex_replace_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True,
            )

        if replacement_result["diff"]:
            st.markdown("### 替换前后 Diff")
            st.code(replacement_result["diff"], language="diff")
        else:
            st.caption("替换结果与原文一致，没有生成 diff。")


def _render_favorites_panel():
    with st.expander("收藏夹", expanded=False):
        st.text_input("收藏名称", key="regex_tool_favorite_name", placeholder="例如: 订单号提取")
        st.text_input("备注", key="regex_tool_favorite_note", placeholder="例如: 适用于 OMS 返回 / 日志脱敏")
        if st.button("收藏当前表达式", key="regex_tool_add_favorite", use_container_width=True):
            _add_current_favorite()

        favorites = st.session_state.regex_tool_favorites
        if favorites:
            st.download_button(
                "导出收藏夹 JSON",
                data=json.dumps(favorites, ensure_ascii=False, indent=2),
                file_name=f"regex_favorites_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                mime="application/json",
                use_container_width=True,
            )
            for index, item in enumerate(favorites):
                st.markdown(f"**{item['name']}**")
                st.code(item["pattern"], language="regex")
                if item["note"]:
                    st.caption(item["note"])
                button_col1, button_col2 = st.columns(2)
                with button_col1:
                    if st.button("应用", key=f"regex_tool_apply_favorite_{index}", use_container_width=True):
                        _apply_favorite(index)
                        st.rerun()
                with button_col2:
                    if st.button("删除", key=f"regex_tool_delete_favorite_{index}", use_container_width=True):
                        _delete_favorite(index)
                        st.rerun()
        else:
            st.caption("还没有收藏的表达式。")

        st.text_area(
            "导入收藏夹 JSON",
            key="regex_tool_favorite_import_text",
            height=120,
            placeholder='例如: [{"name":"订单号","pattern":"ORD-\\\\d+","note":"OMS"}]',
        )
        if st.button("导入收藏夹", key="regex_tool_import_favorites", use_container_width=True):
            _import_favorites()


def _run_playground():
    pattern = st.session_state.regex_tool_pattern
    text = st.session_state.regex_tool_text
    if not pattern.strip():
        st.session_state.regex_tool_test_result = None
        st.session_state.regex_tool_test_error = "请输入正则表达式。"
        return
    if not text:
        st.session_state.regex_tool_test_result = None
        st.session_state.regex_tool_test_error = "请输入测试文本。"
        return

    try:
        replacement = None
        if st.session_state.regex_tool_enable_replacement:
            replacement = st.session_state.regex_tool_replacement_text

        result = analyze_regex(
            pattern,
            text,
            global_match=bool(st.session_state.regex_tool_global_match),
            ignore_case=bool(st.session_state.regex_tool_ignore_case),
            multiline=bool(st.session_state.regex_tool_multiline),
            dotall=bool(st.session_state.regex_tool_dotall),
            replacement=replacement,
            replace_all=bool(st.session_state.regex_tool_replace_all),
        )
        st.session_state.regex_tool_test_result = result
        st.session_state.regex_tool_test_error = ""
        _push_recent_pattern(pattern)
    except re.error as exc:
        st.session_state.regex_tool_test_result = None
        st.session_state.regex_tool_test_error = f"正则表达式错误: {exc}"


def _render_playground_tab():
    left_col, right_col = st.columns([1.45, 1])

    with left_col:
        preset_col1, preset_col2 = st.columns([2, 1])
        preset_col1.selectbox(
            "预定义模式",
            ["自定义"] + list(PREDEFINED_PATTERNS.keys()),
            key="regex_tool_selected_preset",
        )
        with preset_col2:
            st.write("")
            if st.button("载入模式", key="regex_tool_load_preset", use_container_width=True):
                _load_selected_preset()

        st.text_input(
            "正则表达式",
            key="regex_tool_pattern",
            placeholder=r"例如: ^[A-Za-z0-9_]+$ 或 (?P<id>ORD-\d+)",
        )

        sample_col1, sample_col2 = st.columns([2, 1])
        sample_col1.selectbox(
            "QA 场景示例",
            list(SAMPLE_CASES.keys()),
            key="regex_tool_selected_sample",
        )
        with sample_col2:
            st.write("")
            if st.button("载入示例", key="regex_tool_load_sample", use_container_width=True):
                _load_selected_sample()

        st.text_area(
            "测试文本",
            key="regex_tool_text",
            height=260,
            placeholder="粘贴接口返回、日志片段、URL、页面文本或配置内容...",
        )

    with right_col:
        st.markdown("### 运行选项")
        option_cols = st.columns(2)
        option_cols[0].checkbox("全局匹配", key="regex_tool_global_match")
        option_cols[1].checkbox("忽略大小写", key="regex_tool_ignore_case")
        option_cols[0].checkbox("多行模式", key="regex_tool_multiline")
        option_cols[1].checkbox("点号匹配换行", key="regex_tool_dotall")

        st.markdown("### 替换预览")
        st.checkbox("启用替换预览", key="regex_tool_enable_replacement")
        st.text_input(
            "替换文本",
            key="regex_tool_replacement_text",
            placeholder="留空可用于删除命中的内容",
            disabled=not st.session_state.regex_tool_enable_replacement,
        )
        st.radio(
            "替换范围",
            ["全部匹配", "仅首个匹配"],
            horizontal=True,
            index=0 if st.session_state.regex_tool_replace_all else 1,
            key="regex_tool_replace_scope",
            disabled=not st.session_state.regex_tool_enable_replacement,
        )
        st.session_state.regex_tool_replace_all = st.session_state.regex_tool_replace_scope == "全部匹配"

        st.markdown("### 最近使用")
        history = st.session_state.regex_tool_recent_patterns
        if history:
            st.selectbox(
                "最近使用过的表达式",
                history,
                key="regex_tool_recent_choice",
            )
            if st.button("应用最近表达式", key="regex_tool_apply_recent", use_container_width=True):
                _apply_recent_pattern()
        else:
            st.caption("本次会话里运行成功的表达式会出现在这里。")

        with st.expander("实用提示", expanded=False):
            st.markdown(
                "- 先用预定义模式或 QA 场景示例快速起步。\n"
                "- 命名分组建议用 `(?P<name>...)`，结果表会直接展开。\n"
                "- 替换预览支持空字符串，可直接验证脱敏和清洗规则。\n"
                "- 大文本会自动截取匹配附近上下文，避免整页卡顿。"
            )

        _render_favorites_panel()

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("运行正则测试", key="regex_tool_run", use_container_width=True):
            _run_playground()
    with action_col2:
        if st.button("清空当前输入", key="regex_tool_clear", use_container_width=True):
            _clear_playground()
            st.rerun()

    if st.session_state.regex_tool_test_error:
        st.error(st.session_state.regex_tool_test_error)

    _render_playground_result()


def _render_codegen_tab():
    left_col, right_col = st.columns([1.1, 1])

    with left_col:
        st.radio(
            "表达式来源",
            ["沿用测试页表达式", "预定义模式", "手动输入"],
            key="regex_tool_codegen_source",
        )

        if st.session_state.regex_tool_codegen_source == "预定义模式":
            st.selectbox(
                "选择预定义模式",
                list(PREDEFINED_PATTERNS.keys()),
                key="regex_tool_codegen_preset",
            )
            st.code(PREDEFINED_PATTERNS[st.session_state.regex_tool_codegen_preset])
        elif st.session_state.regex_tool_codegen_source == "手动输入":
            st.text_input(
                "输入表达式",
                key="regex_tool_codegen_custom_pattern",
                placeholder=r"例如: (?P<order_id>ORD-\d+)",
            )
        else:
            current_pattern = st.session_state.regex_tool_pattern.strip()
            st.caption("沿用测试页当前表达式")
            st.code(current_pattern or "(当前为空)")

        st.selectbox(
            "目标语言",
            list(LANGUAGE_TEMPLATES.keys()),
            key="regex_tool_codegen_language",
        )
        st.radio(
            "操作类型",
            ["匹配", "测试", "替换"],
            key="regex_tool_codegen_operation",
            horizontal=True,
        )
        st.text_input(
            "替换文本",
            key="regex_tool_codegen_replacement",
            placeholder="仅替换操作需要，可留空",
            disabled=st.session_state.regex_tool_codegen_operation != "替换",
        )

    with right_col:
        language = st.session_state.regex_tool_codegen_language
        flag_options = list(LANGUAGE_TEMPLATES[language]["flags"].keys())
        st.multiselect(
            "选择 flags",
            flag_options,
            key="regex_tool_codegen_flags",
            help="不同语言支持的正则 flags 会有差异。",
        )
        if language == "Go":
            st.info("Go 会把 flags 以内联形式拼接到表达式前缀，例如 `(?i)`。")

        if st.button("生成代码", key="regex_tool_generate_code", use_container_width=True):
            pattern = _resolve_codegen_pattern()
            if not pattern:
                st.warning("当前没有可用的表达式，请先填写或从测试页带入。")
            else:
                st.session_state.regex_tool_generated_code = build_regex_code(
                    pattern,
                    target_language=language,
                    operation_type=st.session_state.regex_tool_codegen_operation,
                    selected_flags=st.session_state.regex_tool_codegen_flags,
                    replacement=st.session_state.regex_tool_codegen_replacement,
                )

        if st.button("清空代码生成区", key="regex_tool_clear_codegen", use_container_width=True):
            _clear_codegen()
            st.rerun()

    generated = st.session_state.regex_tool_generated_code
    if generated:
        st.markdown("### 生成结果")
        st.code(generated["code"], language=CODE_LANGUAGE_MAP.get(generated["language"], "text"))
        st.download_button(
            "下载代码片段",
            data=generated["code"],
            file_name=f"regex_{generated['language'].lower()}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
        )


def _run_example_generator():
    examples = parse_example_items(st.session_state.regex_tool_examples_input)
    if not st.session_state.regex_tool_examples_source.strip():
        st.session_state.regex_tool_generated_example_result = None
        st.session_state.regex_tool_examples_error = "请输入原文内容。"
        return
    if not examples:
        st.session_state.regex_tool_generated_example_result = None
        st.session_state.regex_tool_examples_error = "请至少输入一个示例，支持逗号或换行分隔。"
        return

    pattern = generate_regex_from_examples(
        st.session_state.regex_tool_examples_source,
        st.session_state.regex_tool_examples_input,
    )
    try:
        preview_result = analyze_regex(pattern, st.session_state.regex_tool_examples_source)
        example_covered = all(re.fullmatch(pattern, item) for item in examples)
        st.session_state.regex_tool_generated_example_result = {
            "pattern": pattern,
            "example_count": len(examples),
            "examples": examples,
            "example_covered": example_covered,
            "preview_result": preview_result,
        }
        st.session_state.regex_tool_examples_error = ""
    except re.error as exc:
        st.session_state.regex_tool_generated_example_result = None
        st.session_state.regex_tool_examples_error = f"生成的表达式不可用: {exc}"


def _render_examples_tab():
    left_col, right_col = st.columns(2)
    with left_col:
        st.text_area(
            "原文内容",
            key="regex_tool_examples_source",
            height=220,
            placeholder="粘贴包含目标字段的原文，例如日志、接口响应、报表片段...",
        )
    with right_col:
        st.text_area(
            "示例文本",
            key="regex_tool_examples_input",
            height=220,
            placeholder="每行一个示例，或使用逗号分隔，例如:\nORD-102401\nORD-102402",
        )

    button_col1, button_col2 = st.columns(2)
    with button_col1:
        if st.button("生成表达式", key="regex_tool_generate_from_examples", use_container_width=True):
            _run_example_generator()
    with button_col2:
        if st.button("清空示例区", key="regex_tool_clear_examples", use_container_width=True):
            _clear_examples()
            st.rerun()

    if st.session_state.regex_tool_examples_error:
        st.error(st.session_state.regex_tool_examples_error)

    result = st.session_state.regex_tool_generated_example_result
    if not result:
        return

    st.caption("自动生成属于启发式结果，建议生成后继续在测试页里补充边界验证。")
    st.code(result["pattern"], language="regex")

    metrics = st.columns(4)
    metrics[0].metric("示例数", result["example_count"])
    metrics[1].metric("示例覆盖", "是" if result["example_covered"] else "否")
    metrics[2].metric("原文命中", result["preview_result"]["match_count"])
    metrics[3].metric("唯一结果", result["preview_result"]["unique_match_count"])

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("带回测试页继续调试", key="regex_tool_apply_generated_pattern", use_container_width=True):
            st.session_state.regex_tool_pattern = result["pattern"]
            st.session_state.regex_tool_text = st.session_state.regex_tool_examples_source
            st.success("已把生成结果带回测试页表达式和测试文本。")
    with action_col2:
        st.download_button(
            "下载生成表达式",
            data=result["pattern"],
            file_name=f"generated_regex_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            mime="text/plain",
            use_container_width=True,
        )

    st.markdown(result["preview_result"]["preview_html"], unsafe_allow_html=True)
    if result["preview_result"]["matches"]:
        preview_df = _build_match_dataframe(result["preview_result"])
        st.dataframe(preview_df, use_container_width=True, hide_index=True)


def _run_quick_extract():
    field_name = st.session_state.regex_tool_quick_field_name.strip()
    source_text = st.session_state.regex_tool_quick_extract_source
    if not field_name:
        st.session_state.regex_tool_quick_extract_result = []
        st.session_state.regex_tool_quick_extract_error = "请输入字段名。"
        return
    if not source_text:
        st.session_state.regex_tool_quick_extract_result = []
        st.session_state.regex_tool_quick_extract_error = "请输入或带入原文内容。"
        return

    suggestions = suggest_field_patterns(source_text, field_name)
    if suggestions:
        st.session_state.regex_tool_quick_extract_result = suggestions
        st.session_state.regex_tool_quick_extract_error = ""
    else:
        st.session_state.regex_tool_quick_extract_result = []
        st.session_state.regex_tool_quick_extract_error = "没有找到可用模式，建议切到示例反推页用样例生成。"


def _render_quick_extract_tab():
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if st.button("带入测试页文本", key="regex_tool_quick_use_test_text", use_container_width=True):
            st.session_state.regex_tool_quick_extract_source = st.session_state.regex_tool_text
            st.rerun()
    with action_col2:
        if st.button("带入示例页原文", key="regex_tool_quick_use_example_text", use_container_width=True):
            st.session_state.regex_tool_quick_extract_source = st.session_state.regex_tool_examples_source
            st.rerun()

    st.text_input(
        "字段名 / 参数名",
        key="regex_tool_quick_field_name",
        placeholder="例如: traceId / token / orderId",
    )
    st.text_area(
        "待分析原文",
        key="regex_tool_quick_extract_source",
        height=220,
        placeholder="粘贴 JSON、日志、URL 或表单串，向导会尝试给出字段提取表达式。",
    )

    if st.button("生成字段提取候选", key="regex_tool_quick_extract_run", use_container_width=True):
        _run_quick_extract()

    if st.session_state.regex_tool_quick_extract_error:
        st.error(st.session_state.regex_tool_quick_extract_error)

    suggestions = st.session_state.regex_tool_quick_extract_result
    if not suggestions:
        return

    st.caption("候选规则按常见 QA 文本格式生成，带回测试页后建议继续验证边界和异常输入。")
    for index, item in enumerate(suggestions):
        st.markdown(f"### 候选 {index + 1}: {item['label']}")
        st.code(item["pattern"], language="regex")
        st.caption(f"命中 {item['match_count']} 次，示例值: {', '.join(item['sample_values'])}")
        if st.button(f"应用候选 {index + 1} 到测试页", key=f"regex_tool_apply_quick_candidate_{index}", use_container_width=True):
            st.session_state.regex_tool_pattern = item["pattern"]
            st.session_state.regex_tool_text = st.session_state.regex_tool_quick_extract_source
            st.success("已带回测试页。")


def render_regex_tester_page():
    _ensure_defaults()
    show_doc("regex_tester")

    tab1, tab2, tab3, tab4 = st.tabs(["表达式测试", "代码生成", "示例反推", "字段提取向导"])
    with tab1:
        _render_playground_tab()
    with tab2:
        _render_codegen_tab()
    with tab3:
        _render_examples_tab()
    with tab4:
        _render_quick_extract_tab()
