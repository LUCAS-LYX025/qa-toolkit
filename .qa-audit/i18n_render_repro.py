#!/usr/bin/env python3
"""i18n 渲染回归探针：坐实「模板表达式被原样渲染到页面」缺陷。

背景
----
国际化改造时，把 ``{th(...)}`` 直接写进了 ``render_back_to_top_button()``
的 HTML 字符串。该字符串内含大量 CSS 大括号，是普通字符串（不能改成
f-string），因此模板表达式不会被求值，四种语言下悬浮「快捷操作」面板
都会直接显示 Python 源码。

用法
----
    # 1) 静态分析指定版本的主入口源码
    python .qa-audit/i18n_render_repro.py --source /tmp/streamlit_app_before.py

    # 2) 对当前工作区跑四语言运行时扫描
    python .qa-audit/i18n_render_repro.py --runtime

判定
----
* 静态：markdown 块为普通字符串且含 ``{th(`` / ``{t(`` → 会泄漏源码。
* 运行时：四语言 st.markdown 渲染结果中不得出现 ``{th(`` / ``{t(`` /
  ``__QA_`` 占位符，且三条快捷操作文案必须是当前语言的译文。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC_APP = ROOT / "src" / "qa_toolkit" / "streamlit_app.py"
ENTRY = ROOT / "streamlit_app.py"

LEAK = re.compile(r"\{th\(|\{t\(|\{html\.escape\(|\{_\w+\}|__QA_[A-Z_]+__")
LABELS = {
    "zh-CN": ("⚡ 快捷操作", "💬 意见反馈", "↑ 返回顶部"),
    "zh-TW": ("⚡ 快捷操作", "💬 意見回饋", "↑ 返回頂部"),
    "en-US": ("⚡ Quick actions", "💬 Feedback", "↑ Back to top"),
    "ko-KR": ("⚡ 빠른 작업", "💬 의견 보내기", "↑ 맨 위로"),
}


def static_check(source_path: Path) -> dict:
    text = source_path.read_text(encoding="utf-8")
    start = text.index("def render_back_to_top_button")
    nxt = text.find("\ndef ", start + 1)
    body = text[start:nxt if nxt > 0 else len(text)]

    # 只看 HTML 字符串块内部：跳过函数 docstring 与注释。
    open_tag = re.search(
        r"(?:st\.markdown\(\s*|floating_html\s*=\s*)(f?)\"\"\"", body
    )
    if not open_tag:
        raise ValueError("render_back_to_top_button() 中未找到 HTML 字符串块")
    close_at = body.find('"""', open_tag.end())
    html_block = body[open_tag.end():close_at]
    is_fstring = open_tag.group(1) == "f"
    markers = re.findall(r"\{(?:th|t)\(", html_block)
    placeholders = re.findall(r"__QA_[A-Z_]+__", html_block)

    # 普通字符串里的 {th( / {t( 不会被求值，必然原样渲染。
    would_leak = (not is_fstring) and bool(markers)
    return {
        "source": str(source_path),
        "markdown_is_fstring": is_fstring,
        "unevaluated_template_markers": len(markers),
        "markers": markers,
        "injection_placeholders": len(placeholders),
        "would_leak_source_to_page": would_leak,
    }


def runtime_check() -> dict:
    if str(ROOT / "src") not in sys.path:
        sys.path.insert(0, str(ROOT / "src"))
    from streamlit.testing.v1 import AppTest

    results = {}
    for lang, labels in LABELS.items():
        app = AppTest.from_file(str(ENTRY), default_timeout=60)
        app.query_params["lang"] = lang
        app.run()
        rendered = "\n".join(m.value for m in app.markdown)
        panel = next(
            (m.value for m in app.markdown if "qa-toolkit-floating-shell" in m.value),
            "",
        )
        leaks = LEAK.findall(rendered)
        results[lang] = {
            "exceptions": len(app.exception),
            "template_leaks": len(leaks),
            "leak_samples": leaks[:5],
            "translated_labels_present": all(label in panel for label in labels),
            "placeholder_left": "__QA_" in panel,
        }
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=SRC_APP, help="待静态分析的主入口源码")
    parser.add_argument("--runtime", action="store_true", help="额外跑四语言 AppTest 运行时扫描")
    args = parser.parse_args()

    static = static_check(args.source)
    print("== 静态分析 ==")
    print(json.dumps(static, ensure_ascii=False, indent=2))

    failed = static["would_leak_source_to_page"]
    if args.runtime:
        runtime = runtime_check()
        print("== 运行时扫描（四语言）==")
        print(json.dumps(runtime, ensure_ascii=False, indent=2))
        failed = failed or any(
            r["exceptions"] or r["template_leaks"] or not r["translated_labels_present"]
            or r["placeholder_left"]
            for r in runtime.values()
        )
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
