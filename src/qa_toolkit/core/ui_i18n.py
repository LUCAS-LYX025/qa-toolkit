"""运行时界面国际化：包装 Streamlit 渲染函数，把显示文案统一交给 ``t()``。

页面里大量 ``st.button("开始分析")`` 这类调用没有显式走翻译函数。这里在入口处
一次性包装常用的渲染 API，对「显示文本」做翻译，但**不改变控件返回值**：

- 按钮 / 标题 / 提示 / caption / expander 的文本、metric 的 label 直接翻译；
- metric 的 value 只翻词库里整词命中的状态词（数字/百分比/文件名保持原样）；
- selectbox / radio / multiselect 只加 ``format_func``，选项内部值仍是中文，
  页面里的 ``if value == "中文"`` 逻辑不受影响；
- markdown / HTML 只翻译文本节点，保留标签、属性、代码块、URL、Markdown 标记。

未命中词条时回退原文，因此补词库是渐进式的，不会因为缺一条就报错。
"""

from __future__ import annotations

import functools
import re

import streamlit as st

from qa_toolkit.core import i18n
from qa_toolkit.core.i18n import t

_CJK = re.compile(r"[\u4e00-\u9fff]")
_INSTALLED = False


def _translation_active() -> bool:
    """当前界面是否需要翻译。

    默认语言（简体中文）的目录为空，原文即译文，翻译层在这个语言下完全是空转：
    一次 rerun 数百次 t() 调用加逐行正则解析却没有任何产出。这里一次性判断，
    中文界面直接放行，省掉整条热路径。
    """
    try:
        return i18n._runtime_locale() != i18n.DEFAULT_LOCALE
    except Exception:
        return True

# 需要整体跳过翻译的块
_RAW_BLOCK = re.compile(r"<(style|script)\b[^>]*>.*?</\1>", re.S | re.I)
# 行内需要保护、不参与翻译的片段
_PROTECT = re.compile(
    r"<[^>]+>"                 # HTML 标签
    r"|```.*?```"             # 行内代码块
    r"|`[^`]*`"               # 行内代码
    r"|!?\[[^\]]*\]\([^)]*\)"  # Markdown 链接/图片
    r"|https?://\S+"           # URL
)
_MD_PREFIX = re.compile(r"^(\s*(?:#{1,6}\s+|[-*+]\s+|\d+[.)]\s+)?)(.*)$")
_TRAILING_PUNCT = re.compile(r"^(.*?)([：:，,。.!！?？；;]+)$", re.S)


def _has_cjk(text: str) -> bool:
    return bool(text) and bool(_CJK.search(text))


def translate_text(value):
    """翻译一段纯文本；非字符串或没有中文时原样返回。

    ``st.button("开始分析")`` 这类调用通常不带标点，但 Markdown/提示语里常见
    ``"使用说明："``、``" 确定 "``。这里先按去空白后的核心文本查词条，命中后
    再把原有空白和尾标点补回去，避免因为一个冒号就回退中文。
    """
    if not isinstance(value, str) or not _translation_active() or not _has_cjk(value):
        return value
    core = value.strip()
    if not core:
        return value
    leading = value[: len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()):]
    translated = t(core)
    if translated == core:
        match = _TRAILING_PUNCT.match(core)
        if match and match.group(1).strip():
            body = match.group(1).strip()
            body_translated = t(body)
            if body_translated != body:
                translated = body_translated + match.group(2)
    return leading + translated + trailing


def _translate_segments(line: str) -> str:
    """保护标签/代码/链接，只翻译中间的纯文本片段。"""
    parts: list[str] = []
    last = 0
    for match in _PROTECT.finditer(line):
        if match.start() > last:
            parts.append(translate_text(line[last:match.start()]))
        parts.append(match.group(0))
        last = match.end()
    if last < len(line):
        parts.append(translate_text(line[last:]))
    return "".join(parts)


def _translate_line(line: str) -> str:
    prefix_match = _MD_PREFIX.match(line)
    prefix, body = prefix_match.group(1), prefix_match.group(2)
    if not _has_cjk(body):
        return line
    # 表格行按单元格翻译
    if body.lstrip().startswith("|") and body.rstrip().endswith("|"):
        cells = body.split("|")
        cells = [_translate_segments(c) for c in cells]
        return prefix + "|".join(cells)
    # 先尝试整行精确命中（保留原文变量占位符的译文）
    whole = t(body)
    if whole != body:
        return prefix + whole
    return prefix + _translate_segments(body)


def translate_markup(text: str) -> str:
    """翻译 Markdown / HTML 文本节点，保留结构与代码块。"""
    if not isinstance(text, str) or not _translation_active() or not _has_cjk(text):
        return text
    # <style> / <script> 整体保护
    protected: dict[str, str] = {}

    def hold_block(match: re.Match) -> str:
        key = f"\x00B{len(protected)}\x00"
        protected[key] = match.group(0)
        return key

    safe = _RAW_BLOCK.sub(hold_block, text)
    in_code = False
    out_lines = []
    for line in safe.split("\n"):
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            out_lines.append(line)
            continue
        if in_code or not _has_cjk(line):
            out_lines.append(line)
            continue
        out_lines.append(_translate_line(line))
    result = "\n".join(out_lines)
    for key, value in protected.items():
        result = result.replace(key, value)
    return result


def _wrap_text(func):
    """包装只翻译第一个位置参数 + 常见文本 kwargs 的函数。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if args:
            args = list(args)
            if isinstance(args[0], str):
                args[0] = translate_text(args[0])
            args = tuple(args)
        for key in ("label", "help", "placeholder", "caption", "body", "text", "title", "description"):
            if isinstance(kwargs.get(key), str):
                kwargs[key] = translate_text(kwargs[key])
        return func(*args, **kwargs)

    return wrapper


def _translate_metric_value(value):
    """只翻译 metric 的 value 中「词库里整词命中的中文状态词」。

    ``st.metric("来源", "未导入")`` 的 value 是状态词，切语言后必须跟着翻；
    但 value 更多时候是数字、百分比、文件名或 URL（如 ``"3.5/5"``、
    ``"report.json"``、``image.mode``），套用 label 那套 ``translate_text``
    会把其中的中文片段一并翻掉，反而误伤。这里只在词库里**整词命中**时才
    替换，命中不到就原样返回，保守但不会破坏数值类展示。
    """
    if not isinstance(value, str) or not _translation_active() or not _has_cjk(value):
        return value
    core = value.strip()
    if not core:
        return value
    translated = t(core)
    if translated == core:
        return value
    leading = value[: len(value) - len(value.lstrip())]
    trailing = value[len(value.rstrip()):]
    return leading + translated + trailing


def _wrap_metric(func):
    """metric(label, value, ...) —— label 正常翻译，value 只翻命中词条的状态词。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        args = list(args)
        if args and isinstance(args[0], str):
            args[0] = translate_text(args[0])
        elif isinstance(kwargs.get("label"), str):
            kwargs["label"] = translate_text(kwargs["label"])
        if len(args) >= 2:
            args[1] = _translate_metric_value(args[1])
        elif isinstance(kwargs.get("value"), str):
            kwargs["value"] = _translate_metric_value(kwargs["value"])
        if isinstance(kwargs.get("help"), str):
            kwargs["help"] = translate_text(kwargs["help"])
        return func(*tuple(args), **kwargs)

    return wrapper


def _wrap_dg_metric(func):
    """DeltaGenerator.metric 的同款包装（``col.metric(...)``）。"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        args = list(args)
        if args and isinstance(args[0], str):
            args[0] = translate_text(args[0])
        elif isinstance(kwargs.get("label"), str):
            kwargs["label"] = translate_text(kwargs["label"])
        if len(args) >= 2:
            args[1] = _translate_metric_value(args[1])
        elif isinstance(kwargs.get("value"), str):
            kwargs["value"] = _translate_metric_value(kwargs["value"])
        if isinstance(kwargs.get("help"), str):
            kwargs["help"] = translate_text(kwargs["help"])
        return func(self, *tuple(args), **kwargs)

    return wrapper


def _wrap_markup(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if args:
            args = list(args)
            if isinstance(args[0], str):
                args[0] = translate_markup(args[0])
            args = tuple(args)
        if isinstance(kwargs.get("body"), str):
            kwargs["body"] = translate_markup(kwargs["body"])
        return func(*args, **kwargs)

    return wrapper


def _wrap_options(func):
    """选项显示翻译，但内部值保持中文（仅加 format_func）。"""

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if args:
            args = list(args)
            # 第一个参数是 label，第二个是 options
            if len(args) > 1 and isinstance(args[1], (list, tuple)):
                options = list(args[1])
                if all(isinstance(o, str) for o in options):
                    args[1] = options
                    kwargs.setdefault("format_func", translate_text)
                elif all(isinstance(o, tuple) and o and isinstance(o[0], str) for o in options):
                    # (label, value) 形式
                    kwargs.setdefault("format_func", lambda o: translate_text(o[0]))
            if isinstance(args[0], str):
                args[0] = translate_text(args[0])
            args = tuple(args)
        for key in ("label", "help", "placeholder"):
            if isinstance(kwargs.get(key), str):
                kwargs[key] = translate_text(kwargs[key])
        if "format_func" in kwargs and kwargs["format_func"] is not translate_text:
            original = kwargs["format_func"]

            def combined(value, _original=original):
                return translate_text(_original(value))

            kwargs["format_func"] = combined
        return func(*args, **kwargs)

    return wrapper


def _wrap_tabs(func):
    @functools.wraps(func)
    def wrapper(tabs, *args, **kwargs):
        if isinstance(tabs, (list, tuple)):
            tabs = [translate_text(x) for x in tabs]
        return func(tabs, *args, **kwargs)

    return wrapper


def _wrap_dg_text(func):
    """包装 DeltaGenerator 方法：第一个业务参数是 label/文本。"""

    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            args = (translate_text(args[0]), *args[1:])
        for key in ("label", "help", "placeholder", "caption", "body", "text", "title", "description"):
            if isinstance(kwargs.get(key), str):
                kwargs[key] = translate_text(kwargs[key])
        return func(self, *args, **kwargs)

    return wrapper


def _wrap_dg_markup(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        if args and isinstance(args[0], str):
            args = (translate_markup(args[0]), *args[1:])
        if isinstance(kwargs.get("body"), str):
            kwargs["body"] = translate_markup(kwargs["body"])
        return func(self, *args, **kwargs)

    return wrapper


def _wrap_dg_options(func):
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        args = list(args)
        if len(args) >= 2 and isinstance(args[1], (list, tuple)):
            options = list(args[1])
            if options and all(isinstance(o, str) for o in options):
                args[1] = options
                kwargs.setdefault("format_func", translate_text)
            elif options and all(isinstance(o, tuple) and o and isinstance(o[0], str) for o in options):
                kwargs.setdefault("format_func", lambda o: translate_text(o[0]))
        if args and isinstance(args[0], str):
            args[0] = translate_text(args[0])
        for key in ("label", "help", "placeholder"):
            if isinstance(kwargs.get(key), str):
                kwargs[key] = translate_text(kwargs[key])
        original = kwargs.get("format_func")
        if original is not None and original is not translate_text:
            def combined(value, _original=original):
                return translate_text(_original(value))

            kwargs["format_func"] = combined
        return func(self, *args, **kwargs)

    return wrapper


def _wrap_dg_tabs(func):
    @functools.wraps(func)
    def wrapper(self, tabs, *args, **kwargs):
        if isinstance(tabs, (list, tuple)):
            tabs = [translate_text(x) for x in tabs]
        return func(self, tabs, *args, **kwargs)

    return wrapper


def install_streamlit_i18n() -> None:
    """在应用入口安装一次；重复调用无副作用。

    页面里既可能写 ``st.button(...)``，也可能写 ``col.button(...)`` 或
    ``container.markdown(...)``。后两者走的是 ``DeltaGenerator`` 实例方法，
    只包装模块级函数覆盖不到，所以这里直接包装类方法。
    """
    global _INSTALLED
    if _INSTALLED:
        return
    _INSTALLED = True

    try:
        from streamlit.delta_generator import DeltaGenerator
    except Exception:  # pragma: no cover - 兼容 Streamlit 结构变化
        DeltaGenerator = None

    text_methods = (
        "button", "download_button", "form_submit_button", "checkbox", "toggle",
        "expander", "popover", "caption", "write", "subheader", "header", "title",
        "info", "warning", "error", "success", "toast",
        "text_input", "text_area", "number_input", "date_input", "time_input",
        "file_uploader", "color_picker", "slider",
    )
    option_methods = ("selectbox", "radio", "multiselect", "select_slider")

    if DeltaGenerator is not None:
        for name in text_methods:
            original = getattr(DeltaGenerator, name, None)
            if callable(original):
                setattr(DeltaGenerator, name, _wrap_dg_text(original))
        for name in option_methods:
            original = getattr(DeltaGenerator, name, None)
            if callable(original):
                setattr(DeltaGenerator, name, _wrap_dg_options(original))
        if callable(getattr(DeltaGenerator, "markdown", None)):
            DeltaGenerator.markdown = _wrap_dg_markup(DeltaGenerator.markdown)
        if callable(getattr(DeltaGenerator, "tabs", None)):
            DeltaGenerator.tabs = _wrap_dg_tabs(DeltaGenerator.tabs)
        if callable(getattr(DeltaGenerator, "metric", None)):
            DeltaGenerator.metric = _wrap_dg_metric(DeltaGenerator.metric)

    # 模块级别名（st.button 等）也保留包装，覆盖直接调用模块函数的写法。
    for name in text_methods:
        func = getattr(st, name, None)
        if callable(func):
            setattr(st, name, _wrap_text(func))
    for name in option_methods:
        func = getattr(st, name, None)
        if callable(func):
            setattr(st, name, _wrap_options(func))
    if callable(getattr(st, "markdown", None)):
        st.markdown = _wrap_markup(st.markdown)
    if callable(getattr(st, "tabs", None)):
        st.tabs = _wrap_tabs(st.tabs)
    if callable(getattr(st, "metric", None)):
        st.metric = _wrap_metric(st.metric)
