"""验收与签字面板。

把 SoduWork 的「独立审核 → 请求人签字」流程接到本项目的运行记录上：
机器先跑确定性检查，逐条列出证据；语义项不假装判定，交给签字人确认。
"""
from __future__ import annotations

import html
from typing import Any, Dict, Optional, Sequence, Tuple

import streamlit as st

from qa_toolkit.core.i18n import t
from qa_toolkit.core.verification import verify_workflow, workflow_options
from qa_toolkit.core.workflow_registry import list_workflows


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        .qa-accept-card {
            border: 1px solid rgba(193, 204, 219, 0.96);
            border-radius: 16px;
            padding: 12px 14px 14px;
            margin: 10px 0;
            background: linear-gradient(145deg, rgba(250,252,255,0.98), rgba(241,246,252,0.96));
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.9), 0 8px 18px rgba(15,23,42,0.05);
        }
        .qa-accept-head {
            display: flex; flex-wrap: wrap; gap: 8px; align-items: center;
            font-size: 0.92rem; font-weight: 700; color: #17324a; margin-bottom: 8px;
        }
        .qa-accept-pill {
            padding: 3px 9px; border-radius: 999px; font-size: 0.76rem; font-weight: 700;
            background: rgba(37,99,235,0.09); border: 1px solid rgba(37,99,235,0.22); color: #1d4ed8;
        }
        .qa-accept-pill.ok { background: rgba(22,163,74,0.10); border-color: rgba(22,163,74,0.28); color: #15803d; }
        .qa-accept-pill.no { background: rgba(220,38,38,0.09); border-color: rgba(220,38,38,0.26); color: #b91c1c; }
        .qa-accept-row {
            display: flex; gap: 9px; align-items: flex-start; padding: 7px 0;
            border-top: 1px solid rgba(213,220,232,0.8); font-size: 0.88rem; line-height: 1.5;
        }
        .qa-accept-icon { flex: 0 0 auto; width: 20px; font-weight: 800; }
        .qa-accept-label { color: #17324a; font-weight: 700; }
        .qa-accept-evidence { color: #5a7186; margin-left: 6px; font-weight: 500; }
        .qa-accept-sign {
            border-left: 4px solid #15803d; border-radius: 10px; padding: 9px 12px;
            margin: 8px 0; background: rgba(240,253,244,0.92); color: #166534; font-size: 0.88rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_verification_report(report: Dict[str, Any]) -> None:
    """渲染逐条验收证据；所有动态内容先转义。"""
    _inject_styles()
    name = html.escape(str(report.get("workflow_name") or report.get("workflow_key") or ""))
    version = html.escape(str(report.get("workflow_version") or ""))
    digest = html.escape(str(report.get("artifact_digest") or ""))
    checked_at = html.escape(str(report.get("checked_at") or ""))
    automated = bool(report.get("automated_passed", False))
    results = report.get("results") or []

    rows = []
    for item in results:
        manual = bool(item.get("manual"))
        passed = bool(item.get("passed"))
        icon = "✓" if passed else ("◔" if manual else "×")
        color = "#15803d" if passed else ("#b45309" if manual else "#b91c1c")
        label = html.escape(str(item.get("label") or item.get("key") or ""))
        evidence = html.escape(str(item.get("evidence") or ""))
        tag = " · " + html.escape(t("人工确认")) if manual else ""
        # 每一行都顶格：Streamlit 的 Markdown 会把 4 空格缩进的 HTML 当成代码块。
        rows.append(
            f'<div class="qa-accept-row"><span class="qa-accept-icon" style="color:{color}">{icon}</span>'
            f'<span><span class="qa-accept-label">{label}{tag}</span>'
            f'<span class="qa-accept-evidence">{evidence}</span></span></div>'
        )

    status_class = "ok" if automated else "no"
    status_text = t("机器校验通过") if automated else t("机器校验未通过")
    manual_pending = int(report.get("manual_pending") or 0)
    manual_pill = (
        f'<span class="qa-accept-pill">'
        f'{html.escape(t("待人工确认") + " " + str(manual_pending) + " " + t("项"))}</span>'
        if manual_pending else ""
    )
    # 顶格拼接，避免 Markdown 把缩进行解析成代码块。
    parts = [
        '<div class="qa-accept-card">',
        '<div class="qa-accept-head">',
        f'<span>📋 {name} · v{version}</span>',
        f'<span class="qa-accept-pill {status_class}">{html.escape(status_text)}</span>',
        manual_pill,
        '</div>',
        '<div class="qa-accept-head" style="font-weight:500;color:#5a7186;font-size:0.78rem;">',
        f'<span>{html.escape(t("校验时间"))}: {checked_at}</span>',
        f'<span>{html.escape(t("产物指纹"))}: <code>{digest}</code></span>',
        '</div>',
        *rows,
        '</div>',
    ]
    st.markdown("\n".join(part for part in parts if part), unsafe_allow_html=True)


def _workflow_default_index(keys: Sequence[str], tool: str, current_key: str = "") -> int:
    """默认选中当前工具专属工作流，其次沿用上次校验的工作流。"""
    specs = list_workflows(tool=tool)
    for wanted in (current_key, next((k for k in keys if specs.get(k) and specs[k].tool == tool), "")):
        if wanted in keys:
            return keys.index(wanted)
    return 0


def render_run_acceptance(
    run_center: Any,
    run_detail: Dict[str, Any],
    *,
    panel_key: str,
    tool: str = "",
) -> None:
    """在运行记录详情下方渲染验收 + 签字控件。

    对简化版 runner（测试用 FakeRunner）自动降级，不影响既有页面。
    """
    if not callable(getattr(run_center, "attach_verification", None)):
        return
    if not callable(getattr(run_center, "sign_off", None)):
        return
    run_id = str(run_detail.get("run_id") or "")
    if not run_id:
        return

    _inject_styles()
    st.markdown(f"#### {t('验收与签字')}")
    report: Dict[str, Any] = dict(run_detail.get("verification") or {})
    signed_by = str(run_detail.get("signed_off_by") or "")
    signed_at = str(run_detail.get("signed_off_at") or "")

    if signed_by:
        note = html.escape(str(run_detail.get("sign_off_note") or ""))
        sign_html = (
            f'<div class="qa-accept-sign">✓ {html.escape(t("已由"))} '
            f'<strong>{html.escape(signed_by)}</strong> {html.escape(t("签字确认"))} · '
            f'{html.escape(signed_at)}'
            + (f'<br>{html.escape(t("说明"))}: {note}' if note else "")
            + "</div>"
        )
        st.markdown(sign_html, unsafe_allow_html=True)
        if st.button(t("撤销签字"), key=f"{panel_key}_revoke_sign"):
            if callable(getattr(run_center, "revoke_sign_off", None)):
                run_center.revoke_sign_off(run_id)
            st.rerun()
        return

    keys, labels = workflow_options(tool)
    if not keys:
        st.caption(t("当前没有可用的验收工作流。"))
        return

    current_key = str(report.get("workflow_key") or "")
    index = _workflow_default_index(keys, tool, current_key)
    selected_key = st.selectbox(
        t("验收工作流"),
        options=keys,
        index=index,
        format_func=lambda key: labels.get(key, key),
        key=f"{panel_key}_accept_workflow",
    )

    if st.button(t("运行验收"), key=f"{panel_key}_run_accept"):
        artifact = run_detail.get("result_preview") or run_detail.get("input_preview") or ""
        new_report = verify_workflow(selected_key, artifact, tool=tool)
        if new_report is None:
            st.error(t("验收工作流不存在或已被移除。"))
        else:
            run_center.attach_verification(run_id, new_report.to_dict())
            st.rerun()

    if report:
        render_verification_report(report)

    can_sign = (
        run_detail.get("status") == "success"
        and bool(report.get("automated_passed", False))
    )
    if not can_sign:
        st.caption(
            t("签字条件：任务执行成功，且验收报告中机器可判定项全部通过。")
        )
        return

    signer = st.text_input(
        t("签字人"),
        value=t("本机用户"),
        key=f"{panel_key}_signer",
    )
    note = st.text_input(
        t("签字说明（可选）"),
        key=f"{panel_key}_sign_note",
    )
    if st.button(t("签字确认交付"), key=f"{panel_key}_confirm_sign"):
        if run_center.sign_off(run_id, by=signer, note=note):
            st.success(t("验收签字已记录，可在运行记录中追溯。"))
            st.rerun()
        st.error(t("签字未生效，请重新运行验收。"))
