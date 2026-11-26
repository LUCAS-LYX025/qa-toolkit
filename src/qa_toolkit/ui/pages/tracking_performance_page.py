"""通用「缺陷绩效分析」页面：注册式数据源 + 统一模型 + 可插拔绩效规则。

不绑定任何单一缺陷管理平台：禅道（直连/代理）、JIRA、TAPD、云效及下游自建平台
都通过 ``tracking_registry`` 的 AdapterSpec 接入；连接字段、归因规则、SLA 规则、
绩效规则全部由注册表声明式驱动，新增数据源无需改动本页。
"""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import pandas as pd
import streamlit as st

from qa_toolkit.core import tracking_registry as registry
from qa_toolkit.core.i18n import t
from qa_toolkit.integrations.tracking import rules
from qa_toolkit.integrations.tracking.models import Option, Person, QuerySpec, WorkItem
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import primary_action_button
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
    render_warning_feedback,
)
from qa_toolkit.ui.components.tool_page_shell import (
    render_tool_empty_state,
    render_tool_page_hero,
    render_tool_tips,
)
from qa_toolkit.ui.components.workflow_panels import render_download_panel, render_workflow_guide

HOLIDAY_OPTIONS = {"仅周末（不计节假日）": None, "中国": "CN", "美国": "US", "英国": "GB", "日本": "JP"}

STATE_PREFIX = "tracking_"


def _key(name: str) -> str:
    return STATE_PREFIX + name


def _ensure_defaults() -> None:
    adapters = registry.get_adapters()
    default_adapter = next(iter(adapters), "")
    defaults = {
        _key("adapter"): default_adapter,
        _key("attribution"): "dev",
        _key("sla"): "default",
        _key("performance"): "timeout_rate",
        _key("holiday"): "中国",
        _key("start_date"): date.today() - timedelta(days=30),
        _key("end_date"): date.today(),
        _key("exclude_types"): [],
        _key("roles"): [],
        _key("project_options"): None,
        _key("role_options"): (),
        _key("keyword"): "",
        _key("high_normal"): 24,
        _key("high_weekend"): 72,
        _key("normal_normal"): 72,
        _key("normal_weekend"): 120,
        _key("ready"): False,
        _key("rows"): [],
        _key("details"): [],
        _key("warnings"): [],
        _key("field_values"): {},
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _render_registry_summary() -> None:
    summary = registry.get_registry_summary()
    limits = registry.get_tracking_limits()
    live = summary["已接入数据源"]
    listed = summary["仅登记数据源"]
    sep = t("、")
    adapters_text = sep.join(registry.get_adapters()[k].label for k in live if k in registry.get_adapters()) or t("无")
    listed_text = sep.join(listed) or t("无")
    st.caption(
        t(
            "🧩 已接入数据源：{adapters}（共 {n} 个）；仅登记：{listed}",
            adapters=adapters_text,
            n=summary["数据源"],
            listed=listed_text,
        )
    )
    st.caption(
        t(
            "归因规则 {attr} 种 / SLA 规则 {sla} 种 / 绩效规则 {perf} 种；"
            "安全默认：校验 SSL={ssl}、产物保留凭据={keep}、单次取数上限 {limit} 条。",
            attr=len(summary["归因规则"]),
            sla=len(summary["SLA 规则"]),
            perf=len(summary["绩效规则"]),
            ssl=limits.default_verify_ssl,
            keep=limits.allow_credentials_in_artifacts,
            limit=limits.max_items,
        )
    )


def _render_connection_fields(adapter_key: str) -> Dict[str, Any]:
    """按 ConnectionFieldSpec 声明式渲染输入控件。"""
    values: Dict[str, Any] = {}
    saved = st.session_state.get(_key("field_values"), {}) or {}
    for field in registry.get_connection_fields(adapter_key):
        current = saved.get(field.key, field.default)
        if field.kind == "password":
            widget = st.text_input(field.label, value=str(current or ""), type="password",
                                   key=_key(f"f_{adapter_key}_{field.key}"),
                                   placeholder=field.placeholder)
        elif field.kind == "number":
            widget = st.number_input(field.label, value=int(current or 0),
                                     key=_key(f"f_{adapter_key}_{field.key}"))
        elif field.kind == "select" and field.options:
            widget = st.selectbox(field.label, list(field.options),
                                  index=list(field.options).index(str(current)) if str(current) in field.options else 0,
                                  key=_key(f"f_{adapter_key}_{field.key}"))
        else:
            widget = st.text_input(field.label, value=str(current or ""),
                                   key=_key(f"f_{adapter_key}_{field.key}"),
                                   placeholder=field.placeholder)
        values[field.key] = widget
    return values


def _connect() -> None:
    adapter_key = st.session_state[_key("adapter")]
    cfg = dict(st.session_state.get(_key("field_values"), {}) or {})
    try:
        adapter = registry.create_adapter(adapter_key, cfg)
    except Exception as exc:
        render_error_feedback(f"数据源连接失败：{exc}")
        st.session_state[_key("ready")] = False
        return
    projects = adapter.get_projects()
    meta_err = getattr(adapter, "last_error", "")
    if meta_err and not projects:
        render_error_feedback(f"数据源连接失败：{meta_err}")
        st.session_state[_key("ready")] = False
        return
    if meta_err:
        render_warning_feedback(meta_err)
    # 连接阶段已取过项目元数据，缓存下来避免 rerun 重复请求。
    st.session_state[_key("project_options")] = projects
    st.session_state[_key("adapter_instance")] = adapter
    st.session_state[_key("ready")] = True
    render_success_feedback(f"已连接：{registry.get_adapters()[adapter_key].label}")


def _build_spec() -> QuerySpec:
    sla = {
        "high_normal": int(st.session_state[_key("high_normal")]),
        "high_weekend": int(st.session_state[_key("high_weekend")]),
        "normal_normal": int(st.session_state[_key("normal_normal")]),
        "normal_weekend": int(st.session_state[_key("normal_weekend")]),
    }
    holiday_label = st.session_state[_key("holiday")]
    return QuerySpec(
        project_id=str(st.session_state.get(_key("selected_project"), "") or ""),
        start_date=st.session_state[_key("start_date")],
        end_date=st.session_state[_key("end_date")],
        roles=tuple(st.session_state.get(_key("roles"), ()) or ()),
        exclude_types=tuple(st.session_state.get(_key("exclude_types"), ()) or ()),
        holiday_country=HOLIDAY_OPTIONS.get(holiday_label),
        sla=sla,
        keywords=str(st.session_state.get(_key("keyword"), "") or ""),
    )


def _run() -> None:
    adapter = st.session_state.get(_key("adapter_instance"))
    if adapter is None:
        render_warning_feedback("请先连接数据源。")
        return
    spec = _build_spec()
    items: List[WorkItem] = adapter.fetch_items(spec)
    err = getattr(adapter, "last_error", "")
    if err:
        render_warning_feedback(err)
    # 角色/人员元数据来自适配器，构造 Person 供归因过滤与角色标签展示。
    people = [
        Person(id=opt.value, display_name=opt.label, account=opt.value, role_label=opt.label)
        for opt in st.session_state.get(_key("role_options"), ()) or ()
    ]
    summary_rows, details, warnings = rules.compute_performance(
        items,
        attribution_key=st.session_state[_key("attribution")],
        sla_key=st.session_state[_key("sla")],
        performance_key=st.session_state[_key("performance")],
        query=spec,
        people=people,
        now=None,
    )
    st.session_state[_key("rows")] = summary_rows
    st.session_state[_key("details")] = details
    st.session_state[_key("warnings")] = warnings
    for w in warnings:
        render_warning_feedback(w)
    if summary_rows:
        render_success_feedback(f"已分析 {len(items)} 条工作项，覆盖 {len(summary_rows)} 位人员。")
    else:
        render_info_feedback("当前条件下没有可统计的工作项，请检查数据源与筛选条件。")


def _summary_dataframe() -> pd.DataFrame:
    rows = st.session_state.get(_key("rows"), []) or []
    return pd.DataFrame([r.as_record() for r in rows])


def _detail_dataframe() -> pd.DataFrame:
    rows = st.session_state.get(_key("details"), []) or []
    return pd.DataFrame([d.as_record() for d in rows])


def _csv_bytes(df: pd.DataFrame) -> bytes:
    # 统一走注册式公式注入清洗（复用 core 的 sanitize_export_rows）。
    from qa_toolkit.core import api_automation_registry as auto_reg
    records = auto_reg.sanitize_export_rows(df.to_dict(orient="records"))
    return pd.DataFrame(records).to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")


def _text_summary() -> str:
    from qa_toolkit.core import api_automation_registry as auto_reg
    rows = st.session_state.get(_key("rows"), []) or []
    total_timeout = sum(r.total_timeout for r in rows)
    affected = sum(1 for r in rows if r.total_timeout > 0)
    return auto_reg.build_text_summary(
        "results",
        {"total": len(rows), "passed": len(rows) - affected, "failed": affected,
         "errors": 0, "rate": 100.0 * (len(rows) - affected) / len(rows) if rows else 0.0,
         "degrade": "", "failed_hint": f"；超时 {total_timeout} 次" if total_timeout else "",
         "coverage": ""},
    )


def render_tracking_performance_page() -> None:
    _ensure_defaults()
    show_doc("tracking_performance")
    render_tool_page_hero(
        "📊",
        "缺陷绩效分析",
        "连接 JIRA / TAPD / 云效 / 禅道等主流缺陷管理平台，按统一模型计算 SLA 超时与绩效。",
        tags=["多数据源", "可插拔规则", "SLA 分析", "导出友好"],
        accent="#2563eb",
    )
    render_workflow_guide(
        title="三步完成缺陷绩效分析",
        description="选数据源并连接 → 配置周期与 SLA → 生成绩效汇总与超时明细。",
        steps=["选择数据源并填写连接信息。", "设置统计周期、归因规则与 SLA 阈值。", "查看汇总/明细并导出。"],
    )
    _render_registry_summary()

    with st.expander("数据源连接配置", expanded=not st.session_state[_key("ready")]):
        adapters = registry.get_adapters()
        keys = list(adapters)
        labels = [adapters[k].label for k in keys]
        current = st.session_state[_key("adapter")]
        idx = keys.index(current) if current in keys else 0
        chosen = st.selectbox("数据源", labels, index=idx, key=_key("adapter_select"))
        chosen_key = keys[labels.index(chosen)]
        if chosen_key != current:
            st.session_state[_key("adapter")] = chosen_key
            st.session_state[_key("ready")] = False
            st.session_state[_key("project_options")] = None
            st.session_state[_key("role_options")] = ()
        spec = adapters.get(chosen_key)
        if spec:
            st.caption(spec.description)
            values = _render_connection_fields(chosen_key)
            st.session_state[_key("field_values")] = values
        if primary_action_button("连接并加载", key="tracking_connect"):
            _connect()

    if not st.session_state[_key("ready")]:
        render_tool_empty_state(
            "等待数据源连接",
            "选择 JIRA / TAPD / 云效 / 禅道等数据源并完成连接后，再配置周期与 SLA 规则开始分析。",
        )
        render_tool_tips("接入提示", ["支持 JIRA / TAPD / 云效 / 禅道；新增数据源只需注册适配器。"])
        return

    adapter = st.session_state.get(_key("adapter_instance"))
    projects = st.session_state.get(_key("project_options"))
    if projects is None or adapter is None:
        projects = adapter.get_projects() if adapter else []
    st.session_state[_key("role_options")] = adapter.get_roles() if adapter else []
    st.subheader("统计配置")
    col1, col2 = st.columns(2)
    with col1:
        proj_labels = [p.label for p in projects]
        proj_idx = 0
        st.selectbox("项目/空间", proj_labels or ["（全部）"], index=proj_idx, key=_key("selected_project_index"))
        if projects:
            st.session_state[_key("selected_project")] = projects[st.session_state[_key("selected_project_index")]].value
        st.date_input("开始日期", key=_key("start_date"))
        st.date_input("结束日期", key=_key("end_date"))
        role_options = st.session_state.get(_key("role_options"), ()) or ()
        st.multiselect("角色/人员（留空表示全部）", [o.label for o in role_options],
                       key=_key("role_labels"))
        selected_labels = st.session_state.get(_key("role_labels"), ()) or ()
        st.session_state[_key("roles")] = tuple(
            o.value for o in role_options if o.label in selected_labels)
    with col2:
        attrs = registry.get_attributions()
        # 绩效维度是归因规则的展示层注册点：注册新维度后页面可见并可参与计算。
        dimensions = registry.get_performance_dimensions()
        st.caption("已注册绩效维度：" + ("、".join(f"{k}={v}" for k, v in dimensions.items()) or "无"))
        attr_keys = [k for k in dict.fromkeys(list(dimensions) + list(attrs)) if k in attrs]
        st.selectbox("绩效维度 / 归因规则", attr_keys, key=_key("attribution"),
                     format_func=lambda k: dimensions.get(k, attrs[k].label))
        slas = registry.get_sla_rules()
        st.selectbox("SLA 规则", list(slas), key=_key("sla"), format_func=lambda k: slas[k].label)
        perfs = registry.get_performance_rules()
        st.selectbox("绩效规则", list(perfs), key=_key("performance"), format_func=lambda k: perfs[k].label)
        st.selectbox("节假日", list(HOLIDAY_OPTIONS), key=_key("holiday"))
    with st.expander("SLA 阈值（小时）", expanded=False):
        st.number_input("高优先级·工作日", min_value=1, key=_key("high_normal"))
        st.number_input("高优先级·周末", min_value=1, key=_key("high_weekend"))
        st.number_input("普通·工作日", min_value=1, key=_key("normal_normal"))
        st.number_input("普通·周末", min_value=1, key=_key("normal_weekend"))
    if primary_action_button("开始分析", key="tracking_run"):
        _run()

    st.subheader("汇总报表")
    df = _summary_dataframe()
    if not df.empty:
        st.caption(_text_summary())
        st.dataframe(df, use_container_width=True)
        render_download_panel(
            title="导出汇总",
            description="CSV 走统一公式注入清洗。",
            items=[{"label": "📥 下载汇总 CSV", "data": _csv_bytes(df),
                    "file_name": "tracking_summary.csv", "mime": "text/csv"}],
            key_prefix="tracking_summary_download",
        )
    else:
        render_info_feedback("还没有汇总结果，请先「开始分析」。")

    st.subheader("超时明细")
    detail = _detail_dataframe()
    if not detail.empty:
        st.dataframe(detail, use_container_width=True)
        render_download_panel(
            title="导出明细",
            description="按人员定位超时工作项。",
            items=[{"label": "📥 下载明细 CSV", "data": _csv_bytes(detail),
                    "file_name": "tracking_detail.csv", "mime": "text/csv"}],
            key_prefix="tracking_detail_download",
        )
    else:
        render_info_feedback("当前没有超时明细。")
