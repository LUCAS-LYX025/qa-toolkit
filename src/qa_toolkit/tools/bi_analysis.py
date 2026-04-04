import io
import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import plotly.express as px
import streamlit as st
from pandas.api.types import (
    is_bool_dtype,
    is_datetime64_any_dtype,
    is_numeric_dtype,
    is_object_dtype,
    is_string_dtype,
)


class BIAnalyzer:
    def __init__(self):
        self.supported_formats = [".csv", ".xlsx", ".xls", ".json"]
        self.template_descriptions = {
            "通用销售分析": "适合业务报表、经营分析和透视练习。",
            "开发接口日志": "适合开发、自测和接口日志排障。",
            "测试执行结果": "适合测试结果汇总、缺陷分布和通过率分析。",
            "大数据埋点事件": "适合事件日志、用户行为和分桶聚合分析。",
        }
        self.bi_state_keys = [
            "bi_validation_report",
            "bi_filtered_preview",
            "bi_expanded_json_df",
            "bi_expanded_json_stats",
        ]

    def show_upload_section(self):
        """显示文件上传区域。"""
        st.markdown("### 📁 数据上传")
        st.caption("支持 CSV / Excel / JSON。建议先下载场景模板，再替换成自己的真实数据。")

        self.download_templates()
        st.markdown("---")

        uploaded_file = st.file_uploader(
            "上传数据文件",
            type=[item.lstrip(".") for item in self.supported_formats],
            help=f"支持的文件格式: {', '.join(self.supported_formats)}",
            key="bi_data_upload",
        )
        return uploaded_file

    def reset_runtime_state(self):
        """切换数据集时清理 BI 页面缓存结果。"""
        for state_key in self.bi_state_keys:
            st.session_state[state_key] = None

    def download_templates(self):
        """提供面向不同角色的标准模板。"""
        st.markdown("#### 📥 场景模板")
        selected_template = st.selectbox(
            "选择模板场景",
            list(self.template_descriptions.keys()),
            key="bi_template_selector",
        )
        st.caption(self.template_descriptions[selected_template])

        template_df = self.get_template_dataframe(selected_template)
        excel_buffer = io.BytesIO()
        template_df.to_excel(excel_buffer, index=False, engine="openpyxl")
        excel_buffer.seek(0)

        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📊 Excel模板",
                data=excel_buffer.getvalue(),
                file_name=f"{selected_template}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        with col2:
            st.download_button(
                label="📁 CSV模板",
                data=template_df.to_csv(index=False).encode("utf-8-sig"),
                file_name=f"{selected_template}.csv",
                mime="text/csv",
                use_container_width=True,
            )
        with col3:
            st.download_button(
                label="📋 JSON模板",
                data=template_df.to_json(orient="records", force_ascii=False, indent=2),
                file_name=f"{selected_template}.json",
                mime="application/json",
                use_container_width=True,
            )

    def get_template_dataframe(self, template_name: str) -> pd.DataFrame:
        """生成内置模板数据。"""
        if template_name == "开发接口日志":
            return pd.DataFrame({
                "request_time": [
                    "2026-04-01 10:00:01",
                    "2026-04-01 10:00:03",
                    "2026-04-01 10:00:05",
                    "2026-04-01 10:00:07",
                ],
                "service": ["user-api", "order-api", "user-api", "payment-api"],
                "endpoint": ["/api/v1/users", "/api/v1/orders", "/api/v1/users/{id}", "/api/v1/payments"],
                "status_code": [200, 500, 200, 504],
                "response_ms": [86, 1280, 93, 3012],
                "trace_id": ["T1001", "T1002", "T1003", "T1004"],
                "payload": [
                    "{\"userId\": 1001, \"channel\": \"ios\"}",
                    "{\"orderId\": 9001, \"channel\": \"web\"}",
                    "{\"userId\": 1002, \"channel\": \"android\"}",
                    "{\"paymentId\": 88, \"channel\": \"miniapp\"}",
                ],
            })

        if template_name == "测试执行结果":
            return pd.DataFrame({
                "执行日期": ["2026-04-01", "2026-04-01", "2026-04-02", "2026-04-02"],
                "模块": ["登录", "支付", "搜索", "支付"],
                "用例ID": ["TC-001", "TC-015", "TC-032", "TC-016"],
                "执行结果": ["通过", "失败", "通过", "阻塞"],
                "优先级": ["P0", "P1", "P1", "P0"],
                "执行人": ["张三", "李四", "王五", "李四"],
                "缺陷数": [0, 1, 0, 0],
                "耗时分钟": [5, 12, 4, 15],
            })

        if template_name == "大数据埋点事件":
            return pd.DataFrame({
                "event_time": [
                    "2026-04-01 08:00:00",
                    "2026-04-01 08:00:03",
                    "2026-04-01 08:00:08",
                    "2026-04-01 08:00:15",
                ],
                "event_name": ["app_start", "page_view", "click_button", "purchase"],
                "user_id": [10001, 10001, 10002, 10003],
                "session_id": ["S-001", "S-001", "S-002", "S-003"],
                "platform": ["ios", "ios", "android", "web"],
                "province": ["北京", "北京", "上海", "广东"],
                "duration_ms": [1200, 340, 95, 2210],
                "properties": [
                    "{\"page\": \"home\", \"ab_bucket\": \"A\"}",
                    "{\"page\": \"detail\", \"ab_bucket\": \"A\"}",
                    "{\"button\": \"buy_now\", \"ab_bucket\": \"B\"}",
                    "{\"sku\": \"SKU-100\", \"ab_bucket\": \"A\"}",
                ],
            })

        return pd.DataFrame({
            "日期": ["2026-04-01", "2026-04-02", "2026-04-03", "2026-04-04"],
            "产品": ["产品A", "产品B", "产品A", "产品C"],
            "销售额": [1500.0, 2300.5, 1800.0, 2788.0],
            "数量": [10, 15, 12, 20],
            "地区": ["北京", "上海", "广州", "深圳"],
            "客户评分": [4.5, 4.2, 4.7, 4.3],
            "渠道": ["直营", "代理", "直营", "电商"],
        })

    def get_excel_sheet_names(self, uploaded_file) -> List[str]:
        """读取 Excel 工作表名称。"""
        try:
            excel_file = pd.ExcelFile(io.BytesIO(uploaded_file.getvalue()))
            return excel_file.sheet_names
        except Exception:
            return []

    def load_data(self, uploaded_file, sheet_name: Optional[str] = None) -> Tuple[Optional[pd.DataFrame], str]:
        """加载数据文件。"""
        file_name = uploaded_file.name.lower()
        file_bytes = uploaded_file.getvalue()

        try:
            if file_name.endswith(".csv"):
                df = self._load_csv_bytes(file_bytes)
            elif file_name.endswith((".xlsx", ".xls")):
                df = pd.read_excel(io.BytesIO(file_bytes), sheet_name=sheet_name or 0)
            elif file_name.endswith(".json"):
                df = self._load_json_bytes(file_bytes)
            else:
                return None, "不支持的文件格式"

            df = self._normalize_dataframe(df)
            if df.empty:
                return df, "数据加载成功，但当前文件没有可分析的行记录"
            return df, "数据加载成功"
        except Exception as exc:
            return None, f"数据加载失败: {exc}"

    def _load_csv_bytes(self, file_bytes: bytes) -> pd.DataFrame:
        last_error: Optional[Exception] = None
        for encoding in ["utf-8", "utf-8-sig", "gb18030", "gbk"]:
            for read_kwargs in [
                {"encoding": encoding},
                {"encoding": encoding, "sep": None, "engine": "python"},
            ]:
                try:
                    return pd.read_csv(io.BytesIO(file_bytes), **read_kwargs)
                except Exception as exc:
                    last_error = exc
        raise last_error or ValueError("CSV 读取失败")

    def _load_json_bytes(self, file_bytes: bytes) -> pd.DataFrame:
        last_error: Optional[Exception] = None
        for read_kwargs in [{}, {"lines": True}]:
            try:
                return pd.read_json(io.BytesIO(file_bytes), **read_kwargs)
            except Exception as exc:
                last_error = exc
        raise last_error or ValueError("JSON 读取失败")

    def _normalize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        normalized = df.copy()
        normalized.columns = [str(column).strip() for column in normalized.columns]
        normalized = normalized.replace(r"^\s*$", np.nan, regex=True)
        return normalized

    def build_analysis_context(self, df: pd.DataFrame) -> Dict[str, Any]:
        """构建全局分析上下文，避免页面重复计算。"""
        overview = self.get_overview_metrics(df)
        datetime_columns = self.detect_datetime_columns(df)
        json_columns = self.detect_json_columns(df)
        dimension_columns = self.get_dimension_columns(df, datetime_columns)
        numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
        column_profile = self.build_column_profile(df, datetime_columns, json_columns)
        quality_report = self.build_quality_report(df, column_profile, datetime_columns, json_columns)

        return {
            "overview": overview,
            "datetime_columns": datetime_columns,
            "json_columns": json_columns,
            "dimension_columns": dimension_columns,
            "numeric_columns": numeric_columns,
            "column_profile": column_profile,
            "quality_report": quality_report,
        }

    def get_overview_metrics(self, df: pd.DataFrame) -> Dict[str, Any]:
        total_cells = max(len(df) * max(len(df.columns), 1), 1)
        return {
            "总行数": len(df),
            "总列数": len(df.columns),
            "缺失值": int(df.isnull().sum().sum()),
            "重复行": int(df.duplicated().sum()),
            "内存占用(MB)": round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2),
            "完整率(%)": round((df.count().sum() / total_cells) * 100, 2),
        }

    def detect_datetime_columns(self, df: pd.DataFrame, threshold: float = 0.7) -> List[str]:
        columns: List[str] = []
        for column in df.columns:
            series = df[column]
            if is_datetime64_any_dtype(series):
                columns.append(column)
                continue

            if not (is_object_dtype(series) or is_string_dtype(series)):
                continue

            non_null = series.dropna()
            if non_null.empty:
                continue

            sample = non_null.astype(str).head(200)
            if sample.str.fullmatch(r"\d+").mean() > 0.9:
                continue

            parsed = self.safe_to_datetime(sample)
            success_ratio = parsed.notna().mean()
            if success_ratio >= threshold:
                columns.append(column)
        return columns

    def safe_to_datetime(self, series: pd.Series) -> pd.Series:
        """统一处理 mixed datetime 字符串，避免推断格式时重复告警。"""
        try:
            return pd.to_datetime(series, errors="coerce", format="mixed")
        except TypeError:
            return pd.to_datetime(series, errors="coerce")

    def detect_json_columns(self, df: pd.DataFrame, threshold: float = 0.6) -> List[str]:
        columns: List[str] = []
        for column in df.columns:
            series = df[column]
            if not (is_object_dtype(series) or is_string_dtype(series)):
                continue

            sample = series.dropna().astype(str).head(50)
            if sample.empty:
                continue

            success = 0
            for value in sample:
                try:
                    parsed = json.loads(value)
                except Exception:
                    continue
                if isinstance(parsed, (dict, list)):
                    success += 1

            if success / len(sample) >= threshold:
                columns.append(column)
        return columns

    def get_dimension_columns(self, df: pd.DataFrame, datetime_columns: Optional[List[str]] = None) -> List[str]:
        datetime_set = set(datetime_columns or [])
        dimension_columns: List[str] = []
        for column in df.columns:
            series = df[column]
            unique_count = series.nunique(dropna=True)
            if column in datetime_set or is_datetime64_any_dtype(series):
                dimension_columns.append(column)
            elif is_bool_dtype(series):
                dimension_columns.append(column)
            elif not is_numeric_dtype(series):
                dimension_columns.append(column)
            elif unique_count <= 20:
                dimension_columns.append(column)
        return dimension_columns

    def normalize_lookup_name(self, value: str) -> str:
        return str(value).strip().lower().replace(" ", "").replace("_", "").replace("-", "")

    def find_first_matching_column(
        self,
        df: pd.DataFrame,
        keywords: List[str],
        numeric_only: bool = False,
    ) -> Optional[str]:
        normalized_keywords = [self.normalize_lookup_name(keyword) for keyword in keywords]

        for column in df.columns:
            if numeric_only and not is_numeric_dtype(df[column]):
                continue
            normalized_column = self.normalize_lookup_name(column)
            if normalized_column in normalized_keywords:
                return column

        for column in df.columns:
            if numeric_only and not is_numeric_dtype(df[column]):
                continue
            normalized_column = self.normalize_lookup_name(column)
            if any(keyword in normalized_column for keyword in normalized_keywords):
                return column

        return None

    def _recommend_column_role(
        self,
        df: pd.DataFrame,
        column: str,
        datetime_columns: List[str],
        json_columns: List[str],
    ) -> str:
        series = df[column]
        name = column.lower()
        non_null = max(int(series.notna().sum()), 1)
        unique_ratio = series.nunique(dropna=True) / non_null

        if column in json_columns:
            return "JSON载荷"
        if column in datetime_columns or is_datetime64_any_dtype(series):
            return "时间维度"
        if "id" in name or name.endswith("编号") or name.endswith("编码"):
            return "主键候选" if unique_ratio >= 0.9 else "标识字段"
        if is_numeric_dtype(series):
            return "维度编码" if series.nunique(dropna=True) <= 20 else "度量指标"
        return "维度字段" if unique_ratio <= 0.5 else "文本属性"

    def build_column_profile(
        self,
        df: pd.DataFrame,
        datetime_columns: Optional[List[str]] = None,
        json_columns: Optional[List[str]] = None,
    ) -> pd.DataFrame:
        datetime_columns = datetime_columns or self.detect_datetime_columns(df)
        json_columns = json_columns or self.detect_json_columns(df)
        rows: List[Dict[str, Any]] = []

        for column in df.columns:
            series = df[column]
            non_null = int(series.notna().sum())
            missing_count = int(series.isna().sum())
            unique_count = int(series.nunique(dropna=True))
            missing_ratio = round((missing_count / max(len(df), 1)) * 100, 2)
            unique_ratio = round((unique_count / max(non_null, 1)) * 100, 2)
            sample_values = " | ".join(series.dropna().astype(str).head(3).tolist()) or "-"
            memory_kb = round(series.memory_usage(deep=True) / 1024, 2)

            issues: List[str] = []
            if missing_ratio >= 20:
                issues.append("缺失较多")
            if non_null > 1 and unique_count <= 1:
                issues.append("疑似常量列")
            if column in json_columns:
                issues.append("可展开JSON")
            if column in datetime_columns and not is_datetime64_any_dtype(series):
                issues.append("建议转时间类型")
            if not is_numeric_dtype(series) and unique_ratio >= 90 and non_null >= 20:
                issues.append("高基数字段")

            rows.append({
                "列名": column,
                "数据类型": str(series.dtype),
                "建议角色": self._recommend_column_role(df, column, datetime_columns, json_columns),
                "非空值": non_null,
                "缺失值": missing_count,
                "缺失率(%)": missing_ratio,
                "唯一值": unique_count,
                "唯一率(%)": unique_ratio,
                "内存(KB)": memory_kb,
                "样例值": sample_values,
                "问题标签": "、".join(issues) if issues else "正常",
            })

        return pd.DataFrame(rows)

    def build_quality_report(
        self,
        df: pd.DataFrame,
        column_profile: pd.DataFrame,
        datetime_columns: List[str],
        json_columns: List[str],
    ) -> Dict[str, Any]:
        high_missing_df = column_profile[column_profile["缺失率(%)"] >= 20]
        constant_df = column_profile[column_profile["问题标签"].str.contains("疑似常量列", na=False)]
        high_cardinality_df = column_profile[column_profile["问题标签"].str.contains("高基数字段", na=False)]
        key_candidates = column_profile[column_profile["建议角色"] == "主键候选"]["列名"].tolist()

        issue_rows: List[Dict[str, Any]] = []
        if int(df.duplicated().sum()) > 0:
            issue_rows.append({
                "检查项": "重复行",
                "级别": "中",
                "详情": f"发现 {int(df.duplicated().sum())} 行完全重复记录",
                "建议": "检查上游去重逻辑或主键定义",
            })
        for _, row in high_missing_df.iterrows():
            issue_rows.append({
                "检查项": "高缺失字段",
                "级别": "中",
                "详情": f"{row['列名']} 缺失率 {row['缺失率(%)']}%",
                "建议": "确认是否允许为空，或补齐默认值",
            })
        for _, row in constant_df.iterrows():
            issue_rows.append({
                "检查项": "常量字段",
                "级别": "低",
                "详情": f"{row['列名']} 的非空值基本一致",
                "建议": "确认是否仍有分析价值，必要时在报表中隐藏",
            })
        for _, row in high_cardinality_df.iterrows():
            issue_rows.append({
                "检查项": "高基数字段",
                "级别": "提示",
                "详情": f"{row['列名']} 唯一率 {row['唯一率(%)']}%",
                "建议": "做维度聚合前可先分桶或截断",
            })

        suggestions: List[str] = []
        if len(df) >= 100000:
            suggestions.append("当前数据量较大，预览建议使用随机样本或先做聚合。")
        if json_columns:
            suggestions.append(f"检测到 JSON 字段: {', '.join(json_columns)}，可在开发/大数据工作台展开。")
        if datetime_columns:
            suggestions.append(f"检测到时间字段: {', '.join(datetime_columns)}，适合做趋势分析。")
        if key_candidates:
            suggestions.append(f"检测到主键候选字段: {', '.join(key_candidates[:5])}。")

        return {
            "summary": {
                "高缺失字段数": int(len(high_missing_df)),
                "常量字段数": int(len(constant_df)),
                "高基数字段数": int(len(high_cardinality_df)),
                "时间字段数": int(len(datetime_columns)),
                "JSON字段数": int(len(json_columns)),
            },
            "issues": pd.DataFrame(issue_rows),
            "suggestions": suggestions,
            "high_missing_columns": high_missing_df,
            "high_memory_columns": column_profile.sort_values("内存(KB)", ascending=False).head(10),
            "key_candidates": key_candidates,
        }

    def build_scenario_insights(self, df: pd.DataFrame, context: Dict[str, Any]) -> Dict[str, Any]:
        """面向业务、开发、测试和大数据场景生成可读洞察。"""
        cards: List[Dict[str, str]] = []
        highlights: List[str] = []
        tables: List[Dict[str, Any]] = []
        scenarios: List[str] = []

        datetime_columns = context["datetime_columns"]
        quality_report = context["quality_report"]

        result_column = self.find_first_matching_column(df, ["执行结果", "结果", "result", "case_status", "status_text"])
        defect_column = self.find_first_matching_column(df, ["缺陷数", "bug数", "缺陷", "bug_count", "defect_count"], numeric_only=True)
        module_column = self.find_first_matching_column(df, ["模块", "module", "feature", "业务线", "project"])
        duration_column = self.find_first_matching_column(
            df,
            ["耗时分钟", "耗时", "duration", "duration_ms", "response_ms", "latency_ms"],
            numeric_only=True,
        )

        if result_column:
            scenarios.append("测试执行")
            result_series = df[result_column].astype(str).str.strip().str.lower()
            pass_mask = result_series.str.contains("通过|pass|passed|success|成功", regex=True, na=False)
            fail_mask = result_series.str.contains("失败|fail|failed|error|阻塞|blocked", regex=True, na=False)
            pass_count = int(pass_mask.sum())
            fail_count = int(fail_mask.sum())
            total_count = max(int(result_series.notna().sum()), 1)
            cards.append({
                "label": "通过率",
                "value": f"{(pass_count / total_count) * 100:.1f}%",
                "detail": f"{pass_count} / {total_count}",
            })
            cards.append({
                "label": "失败或阻塞",
                "value": str(fail_count),
                "detail": result_column,
            })
            if fail_count > 0:
                highlights.append("检测到失败或阻塞记录，建议在测试校验页继续筛选失败模块和重复主键。")
            if module_column:
                summary_df = (
                    pd.DataFrame({"模块": df[module_column], "结果": result_series, "通过": pass_mask, "失败": fail_mask})
                    .groupby("模块", dropna=False)
                    .agg(执行总数=("结果", "count"), 通过数=("通过", "sum"), 失败数=("失败", "sum"))
                    .reset_index()
                    .sort_values(["失败数", "执行总数"], ascending=[False, False])
                    .head(10)
                )
                summary_df["通过率(%)"] = (
                    summary_df["通过数"] / summary_df["执行总数"].replace(0, np.nan) * 100
                ).round(2).fillna(0)
                tables.append({"title": "模块执行概览", "data": summary_df})

        if defect_column:
            defect_total = int(pd.to_numeric(df[defect_column], errors="coerce").fillna(0).sum())
            cards.append({
                "label": "缺陷总数",
                "value": str(defect_total),
                "detail": defect_column,
            })

        status_column = self.find_first_matching_column(df, ["status_code", "http_status", "状态码", "响应码", "code"])
        endpoint_column = self.find_first_matching_column(df, ["endpoint", "path", "uri", "api", "接口"])
        service_column = self.find_first_matching_column(df, ["service", "服务", "应用", "app", "system"])

        status_numeric = None
        if status_column:
            status_numeric = pd.to_numeric(df[status_column], errors="coerce")
            if status_numeric.notna().any():
                scenarios.append("开发日志")
                error_mask = status_numeric >= 400
                server_error_mask = status_numeric >= 500
                valid_status = max(int(status_numeric.notna().sum()), 1)
                cards.append({
                    "label": "错误率",
                    "value": f"{(error_mask.sum() / valid_status) * 100:.1f}%",
                    "detail": status_column,
                })
                cards.append({
                    "label": "5xx 数量",
                    "value": str(int(server_error_mask.sum())),
                    "detail": "服务端错误",
                })
                tables.append({
                    "title": "状态码分布",
                    "data": status_numeric.dropna().astype(int).value_counts().head(10).rename_axis("状态码").reset_index(name="出现次数"),
                })
                if int(server_error_mask.sum()) > 0:
                    highlights.append("存在 5xx 记录，建议结合服务/接口维度定位慢接口或异常上游。")

        if duration_column:
            duration_series = pd.to_numeric(df[duration_column], errors="coerce").dropna()
            if not duration_series.empty:
                if "开发日志" not in scenarios and self.normalize_lookup_name(duration_column) in {
                    "responsems",
                    "latencyms",
                    "durationms",
                }:
                    scenarios.append("开发日志")
                cards.append({
                    "label": "P95",
                    "value": f"{duration_series.quantile(0.95):.2f}",
                    "detail": duration_column,
                })
                cards.append({
                    "label": "P99",
                    "value": f"{duration_series.quantile(0.99):.2f}",
                    "detail": duration_column,
                })

                group_column = endpoint_column or service_column
                if group_column:
                    slow_df = (
                        df.groupby(group_column, dropna=False)[duration_column]
                        .agg(["count", "mean", "max"])
                        .reset_index()
                        .sort_values(["mean", "max"], ascending=False)
                        .head(10)
                    )
                    slow_df.columns = [group_column, "样本数", "平均耗时", "最大耗时"]
                    tables.append({"title": "慢接口 / 服务 Top 10", "data": slow_df})

        event_column = self.find_first_matching_column(df, ["event_name", "event", "事件", "action", "埋点"])
        user_column = self.find_first_matching_column(df, ["user_id", "uid", "member_id", "用户id", "userid"])
        session_column = self.find_first_matching_column(df, ["session_id", "session", "会话id", "sessionid"])
        platform_column = self.find_first_matching_column(df, ["platform", "渠道", "channel", "os", "端"])

        if event_column:
            scenarios.append("埋点事件")
            cards.append({
                "label": "事件总量",
                "value": f"{len(df):,}",
                "detail": event_column,
            })
            if user_column:
                uv = int(df[user_column].nunique(dropna=True))
                cards.append({
                    "label": "UV",
                    "value": f"{uv:,}",
                    "detail": user_column,
                })
                if uv > 0:
                    cards.append({
                        "label": "人均事件数",
                        "value": f"{len(df) / uv:.2f}",
                        "detail": "事件总量 / UV",
                    })
            if session_column:
                cards.append({
                    "label": "会话数",
                    "value": f"{int(df[session_column].nunique(dropna=True)):,}",
                    "detail": session_column,
                })

            event_distribution = (
                df[event_column]
                .astype(str)
                .value_counts()
                .head(10)
                .rename_axis(event_column)
                .reset_index(name="事件次数")
            )
            tables.append({"title": "事件分布 Top 10", "data": event_distribution})

            if platform_column:
                platform_distribution = (
                    df.groupby(platform_column, dropna=False)[event_column]
                    .count()
                    .reset_index(name="事件数")
                    .sort_values("事件数", ascending=False)
                    .head(10)
                )
                tables.append({"title": "平台事件分布", "data": platform_distribution})

        amount_column = self.find_first_matching_column(
            df,
            ["销售额", "金额", "gmv", "revenue", "amount", "total_amount"],
            numeric_only=True,
        )
        if amount_column:
            scenarios.append("业务分析")
            amount_series = pd.to_numeric(df[amount_column], errors="coerce").dropna()
            if not amount_series.empty:
                cards.append({
                    "label": "总金额",
                    "value": f"{amount_series.sum():,.2f}",
                    "detail": amount_column,
                })
                cards.append({
                    "label": "平均金额",
                    "value": f"{amount_series.mean():,.2f}",
                    "detail": amount_column,
                })

        if datetime_columns:
            date_column = datetime_columns[0]
            parsed_dates = self.safe_to_datetime(df[date_column]).dropna()
            if not parsed_dates.empty:
                span_days = max((parsed_dates.max() - parsed_dates.min()).days, 0)
                cards.append({
                    "label": "时间跨度",
                    "value": f"{span_days} 天",
                    "detail": date_column,
                })

        if quality_report["key_candidates"]:
            highlights.append(f"检测到主键候选字段: {', '.join(quality_report['key_candidates'][:3])}。")
        if quality_report["summary"]["高缺失字段数"] > 0:
            highlights.append("当前存在高缺失字段，建议先看质量诊断页再做透视或趋势分析。")
        if not scenarios:
            highlights.append("未识别出明显业务场景，建议先从数据预览和质量诊断页确认字段语义。")

        deduped_scenarios = list(dict.fromkeys(scenarios))
        deduped_cards = cards[:8]
        deduped_highlights = list(dict.fromkeys(highlights))

        return {
            "scenarios": deduped_scenarios,
            "cards": deduped_cards,
            "highlights": deduped_highlights,
            "tables": tables[:4],
        }

    def scenario_insights(self, df: pd.DataFrame, context: Dict[str, Any]):
        """展示角色化场景洞察。"""
        st.subheader("🧭 场景洞察")
        insights = self.build_scenario_insights(df, context)

        if insights["scenarios"]:
            st.caption(f"识别场景: {' / '.join(insights['scenarios'])}")

        cards = insights["cards"]
        if cards:
            for start in range(0, len(cards), 4):
                columns = st.columns(min(4, len(cards) - start))
                for card_column, card in zip(columns, cards[start:start + 4]):
                    card_column.metric(card["label"], card["value"], help=card["detail"])

        for highlight in insights["highlights"]:
            st.info(highlight)

        for table in insights["tables"]:
            st.markdown(f"**{table['title']}**")
            st.dataframe(table["data"], use_container_width=True, hide_index=True)

    def data_preview(self, df: pd.DataFrame, context: Dict[str, Any]):
        """数据预览与字段画像。"""
        st.subheader("📋 数据预览")
        overview = context["overview"]

        metric_cols = st.columns(6)
        metric_cols[0].metric("总行数", f"{overview['总行数']:,}")
        metric_cols[1].metric("总列数", overview["总列数"])
        metric_cols[2].metric("缺失值", f"{overview['缺失值']:,}")
        metric_cols[3].metric("重复行", f"{overview['重复行']:,}")
        metric_cols[4].metric("内存占用", f"{overview['内存占用(MB)']:.2f} MB")
        metric_cols[5].metric("完整率", f"{overview['完整率(%)']:.1f}%")

        control_cols = st.columns([1.1, 1, 1.6])
        with control_cols[0]:
            preview_mode = st.radio(
                "预览方式",
                ["前N行", "后N行", "随机样本"],
                horizontal=True,
                key="bi_preview_mode",
            )
        with control_cols[1]:
            preview_rows = st.slider("预览行数", 10, 200, 30, step=10, key="bi_preview_rows")
        with control_cols[2]:
            column_keyword = st.text_input("字段搜索", placeholder="按列名搜索，例如 status、日期、trace")

        filtered_columns = [
            column for column in df.columns
            if not column_keyword or column_keyword.lower() in column.lower()
        ]
        selected_columns = st.multiselect(
            "预览字段",
            df.columns.tolist(),
            default=filtered_columns[: min(12, len(filtered_columns))] if filtered_columns else df.columns.tolist()[: min(12, len(df.columns))],
            key="bi_preview_columns",
        )
        preview_df = self.sample_dataframe(df, preview_mode, preview_rows)
        preview_df = preview_df[selected_columns] if selected_columns else preview_df
        st.dataframe(preview_df, use_container_width=True, hide_index=True)

        with st.expander("字段画像", expanded=False):
            profile_df = context["column_profile"]
            display_profile = profile_df
            if column_keyword:
                display_profile = profile_df[profile_df["列名"].str.contains(column_keyword, case=False, na=False)]
            st.dataframe(display_profile, use_container_width=True, hide_index=True)

    def sample_dataframe(self, df: pd.DataFrame, preview_mode: str, preview_rows: int) -> pd.DataFrame:
        if preview_mode == "后N行":
            return df.tail(preview_rows)
        if preview_mode == "随机样本":
            return df.sample(min(preview_rows, len(df)), random_state=42) if len(df) else df
        return df.head(preview_rows)

    def data_quality_analysis(self, df: pd.DataFrame, context: Dict[str, Any]):
        """数据质量诊断。"""
        st.subheader("🩺 数据质量诊断")
        quality_report = context["quality_report"]
        summary = quality_report["summary"]

        metric_cols = st.columns(5)
        metric_cols[0].metric("高缺失字段", summary["高缺失字段数"])
        metric_cols[1].metric("常量字段", summary["常量字段数"])
        metric_cols[2].metric("高基数字段", summary["高基数字段数"])
        metric_cols[3].metric("时间字段", summary["时间字段数"])
        metric_cols[4].metric("JSON字段", summary["JSON字段数"])

        if quality_report["suggestions"]:
            for suggestion in quality_report["suggestions"]:
                st.info(suggestion)

        issues_df = quality_report["issues"]
        st.markdown("**质量问题清单**")
        if issues_df.empty:
            st.success("当前未发现明显的数据质量问题。")
        else:
            st.dataframe(issues_df, use_container_width=True, hide_index=True)

        top_col1, top_col2 = st.columns(2)
        with top_col1:
            st.markdown("**高缺失字段**")
            missing_df = quality_report["high_missing_columns"]
            if missing_df.empty:
                st.caption("暂无")
            else:
                st.dataframe(missing_df[["列名", "缺失率(%)", "样例值"]], use_container_width=True, hide_index=True)
        with top_col2:
            st.markdown("**高内存字段**")
            st.dataframe(
                quality_report["high_memory_columns"][["列名", "内存(KB)", "建议角色", "问题标签"]],
                use_container_width=True,
                hide_index=True,
            )

    def validation_workbench(self, df: pd.DataFrame, context: Dict[str, Any]):
        """测试/验数工作台。"""
        st.subheader("🧪 测试校验工作台")
        all_columns = df.columns.tolist()
        numeric_columns = context["numeric_columns"]
        datetime_columns = context["datetime_columns"]
        key_candidates = context["quality_report"]["key_candidates"]

        with st.expander("配置校验规则", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                required_columns = st.multiselect(
                    "必填字段",
                    all_columns,
                    default=all_columns[: min(2, len(all_columns))],
                    key="bi_required_columns",
                )
                unique_key_columns = st.multiselect(
                    "唯一键字段",
                    all_columns,
                    default=key_candidates[:1],
                    key="bi_unique_key_columns",
                    help="用于检查重复主键或重复业务数据。",
                )
            with col2:
                non_negative_columns = st.multiselect(
                    "非负数校验字段",
                    numeric_columns,
                    default=numeric_columns[:1],
                    key="bi_non_negative_columns",
                )
                datetime_check_columns = st.multiselect(
                    "时间格式校验字段",
                    [column for column in all_columns if column in datetime_columns or column not in numeric_columns],
                    default=datetime_columns[:1],
                    key="bi_datetime_check_columns",
                )

            null_ratio_threshold = st.slider("字段缺失率告警阈值 (%)", 0, 100, 20, key="bi_null_ratio_threshold")

        if st.button("执行数据校验", use_container_width=True, key="bi_run_validation"):
            validation_report = self.build_validation_report(
                df,
                required_columns=required_columns,
                unique_key_columns=unique_key_columns,
                non_negative_columns=non_negative_columns,
                datetime_columns=datetime_check_columns,
                null_ratio_threshold=float(null_ratio_threshold),
            )
            st.session_state.bi_validation_report = validation_report

        validation_report = st.session_state.get("bi_validation_report")
        if validation_report:
            summary = validation_report["summary"]
            metric_cols = st.columns(4)
            metric_cols[0].metric("规则总数", summary["规则总数"])
            metric_cols[1].metric("通过规则", summary["通过规则"])
            metric_cols[2].metric("告警规则", summary["告警规则"])
            metric_cols[3].metric("异常记录数", summary["异常记录数"])

            issues_df = validation_report["issues"]
            if issues_df.empty:
                st.success("所有已配置规则均通过。")
            else:
                st.dataframe(issues_df, use_container_width=True, hide_index=True)

            duplicate_sample = validation_report["duplicate_sample"]
            if duplicate_sample is not None and not duplicate_sample.empty:
                st.markdown("**重复键样例**")
                st.dataframe(duplicate_sample, use_container_width=True, hide_index=True)

    def build_validation_report(
        self,
        df: pd.DataFrame,
        required_columns: Optional[List[str]] = None,
        unique_key_columns: Optional[List[str]] = None,
        non_negative_columns: Optional[List[str]] = None,
        datetime_columns: Optional[List[str]] = None,
        null_ratio_threshold: float = 20.0,
    ) -> Dict[str, Any]:
        required_columns = required_columns or []
        unique_key_columns = unique_key_columns or []
        non_negative_columns = non_negative_columns or []
        datetime_columns = datetime_columns or []

        issues: List[Dict[str, Any]] = []
        duplicate_sample = None
        total_rules = 0
        passed_rules = 0
        affected_records = 0

        if required_columns:
            total_rules += 1
            missing_columns = [column for column in required_columns if column not in df.columns]
            if missing_columns:
                issues.append({
                    "规则": "必填字段存在性",
                    "状态": "失败",
                    "字段": "、".join(missing_columns),
                    "详情": "数据中缺少这些字段",
                    "异常记录数": "-",
                })
            else:
                passed_rules += 1

            for column in [item for item in required_columns if item in df.columns]:
                total_rules += 1
                null_count = int(df[column].isna().sum())
                if null_count > 0:
                    issues.append({
                        "规则": "必填字段空值",
                        "状态": "失败",
                        "字段": column,
                        "详情": f"{column} 存在 {null_count} 个空值",
                        "异常记录数": null_count,
                    })
                    affected_records += null_count
                else:
                    passed_rules += 1

        for column in df.columns:
            total_rules += 1
            null_ratio = float(df[column].isna().mean() * 100)
            if null_ratio > null_ratio_threshold:
                issues.append({
                    "规则": "缺失率阈值",
                    "状态": "告警",
                    "字段": column,
                    "详情": f"缺失率 {null_ratio:.2f}% 超过阈值 {null_ratio_threshold:.2f}%",
                    "异常记录数": int(df[column].isna().sum()),
                })
            else:
                passed_rules += 1

        if unique_key_columns:
            existing_key_columns = [column for column in unique_key_columns if column in df.columns]
            total_rules += 1
            if len(existing_key_columns) != len(unique_key_columns):
                missing_keys = [column for column in unique_key_columns if column not in df.columns]
                issues.append({
                    "规则": "唯一键字段存在性",
                    "状态": "失败",
                    "字段": "、".join(missing_keys),
                    "详情": "数据中缺少这些唯一键字段",
                    "异常记录数": "-",
                })
            else:
                duplicate_count = int(df.duplicated(subset=existing_key_columns).sum())
                if duplicate_count > 0:
                    issues.append({
                        "规则": "唯一键重复",
                        "状态": "失败",
                        "字段": "、".join(existing_key_columns),
                        "详情": f"发现 {duplicate_count} 行重复键",
                        "异常记录数": duplicate_count,
                    })
                    affected_records += duplicate_count
                    duplicate_sample = df[df.duplicated(subset=existing_key_columns, keep=False)].head(50)
                else:
                    passed_rules += 1

        for column in non_negative_columns:
            if column not in df.columns:
                continue
            total_rules += 1
            series = pd.to_numeric(df[column], errors="coerce")
            negative_count = int((series < 0).sum())
            if negative_count > 0:
                issues.append({
                    "规则": "非负数校验",
                    "状态": "失败",
                    "字段": column,
                    "详情": f"{column} 存在 {negative_count} 个负数值",
                    "异常记录数": negative_count,
                })
                affected_records += negative_count
            else:
                passed_rules += 1

        for column in datetime_columns:
            if column not in df.columns:
                continue
            total_rules += 1
            series = df[column]
            non_null = series.dropna()
            if non_null.empty:
                passed_rules += 1
                continue

            parsed = self.safe_to_datetime(non_null.astype(str))
            invalid_count = int((~parsed.notna()).sum())
            if invalid_count > 0:
                issues.append({
                    "规则": "时间格式校验",
                    "状态": "失败",
                    "字段": column,
                    "详情": f"{column} 有 {invalid_count} 个值无法解析为时间",
                    "异常记录数": invalid_count,
                })
                affected_records += invalid_count
            else:
                passed_rules += 1

        issues_df = pd.DataFrame(issues)
        return {
            "summary": {
                "规则总数": total_rules,
                "通过规则": passed_rules,
                "告警规则": len(issues),
                "异常记录数": affected_records,
            },
            "issues": issues_df,
            "duplicate_sample": duplicate_sample,
        }

    def developer_workbench(self, df: pd.DataFrame, context: Dict[str, Any]):
        """开发/大数据辅助工作台。"""
        st.subheader("🧩 开发 / 大数据工作台")
        quality_report = context["quality_report"]
        json_columns = context["json_columns"]

        metric_cols = st.columns(4)
        metric_cols[0].metric("JSON字段", len(json_columns))
        metric_cols[1].metric("主键候选", len(quality_report["key_candidates"]))
        metric_cols[2].metric("大于10万行", "是" if len(df) >= 100000 else "否")
        metric_cols[3].metric("字段数", len(df.columns))

        filter_tab, json_tab = st.tabs(["快速过滤", "JSON字段展开"])

        with filter_tab:
            col1, col2, col3, col4 = st.columns([1.2, 1, 1.2, 0.8])
            with col1:
                filter_column = st.selectbox("筛选字段", df.columns.tolist(), key="bi_filter_column")
            with col2:
                filter_operators = self.get_filter_operators(df[filter_column])
                filter_operator = st.selectbox("操作符", filter_operators, key="bi_filter_operator")
            with col3:
                if filter_operator in {"为空", "不为空"}:
                    filter_value = ""
                    st.caption("当前操作符不需要输入值")
                else:
                    filter_value = st.text_input("筛选值", key="bi_filter_value")
            with col4:
                preview_rows = st.slider("预览条数", 10, 200, 50, step=10, key="bi_filter_preview_rows")

            if st.button("执行过滤", use_container_width=True, key="bi_run_filter"):
                filtered_df = self.apply_quick_filter(df, filter_column, filter_operator, filter_value)
                st.session_state.bi_filtered_preview = filtered_df

            filtered_df = st.session_state.get("bi_filtered_preview")
            if filtered_df is not None:
                st.success(f"过滤后共 {len(filtered_df):,} 行")
                st.dataframe(filtered_df.head(preview_rows), use_container_width=True, hide_index=True)
                st.download_button(
                    label="下载过滤结果 CSV",
                    data=filtered_df.to_csv(index=False).encode("utf-8-sig"),
                    file_name="bi_filtered_result.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="download_bi_filtered_result",
                )

        with json_tab:
            if not json_columns:
                st.info("当前未检测到 JSON 字段。")
            else:
                col1, col2 = st.columns([1.5, 1])
                with col1:
                    json_column = st.selectbox("选择 JSON 字段", json_columns, key="bi_json_column")
                with col2:
                    expand_limit = st.slider("展开样本行数", 10, 500, 100, step=10, key="bi_json_expand_limit")

                if st.button("展开 JSON 字段", use_container_width=True, key="bi_expand_json"):
                    expanded_df, stats = self.expand_json_column(df, json_column, row_limit=expand_limit)
                    st.session_state.bi_expanded_json_df = expanded_df
                    st.session_state.bi_expanded_json_stats = stats

                expanded_df = st.session_state.get("bi_expanded_json_df")
                expanded_stats = st.session_state.get("bi_expanded_json_stats")
                if expanded_df is not None and expanded_stats is not None:
                    stat_cols = st.columns(3)
                    stat_cols[0].metric("成功展开", expanded_stats["成功行数"])
                    stat_cols[1].metric("失败行数", expanded_stats["失败行数"])
                    stat_cols[2].metric("展开字段数", expanded_stats["展开字段数"])
                    st.dataframe(expanded_df, use_container_width=True, hide_index=True)
                    st.download_button(
                        label="下载展开结果 CSV",
                        data=expanded_df.to_csv(index=False).encode("utf-8-sig"),
                        file_name="bi_expanded_json.csv",
                        mime="text/csv",
                        use_container_width=True,
                        key="download_bi_expanded_json",
                    )

    def get_filter_operators(self, series: pd.Series) -> List[str]:
        if is_numeric_dtype(series):
            return ["等于", "大于", "大于等于", "小于", "小于等于", "为空", "不为空"]
        return ["包含", "等于", "开头为", "结尾为", "为空", "不为空"]

    def apply_quick_filter(
        self,
        df: pd.DataFrame,
        column: str,
        operator: str,
        raw_value: str,
    ) -> pd.DataFrame:
        series = df[column]
        if operator == "为空":
            return df[series.isna()]
        if operator == "不为空":
            return df[series.notna()]

        if is_numeric_dtype(series):
            numeric_series = pd.to_numeric(series, errors="coerce")
            try:
                numeric_value = float(raw_value)
            except Exception:
                return df.iloc[0:0]

            if operator == "等于":
                mask = numeric_series == numeric_value
            elif operator == "大于":
                mask = numeric_series > numeric_value
            elif operator == "大于等于":
                mask = numeric_series >= numeric_value
            elif operator == "小于":
                mask = numeric_series < numeric_value
            else:
                mask = numeric_series <= numeric_value
            return df[mask.fillna(False)]

        string_series = series.astype(str)
        if operator == "等于":
            mask = string_series == raw_value
        elif operator == "开头为":
            mask = string_series.str.startswith(raw_value, na=False)
        elif operator == "结尾为":
            mask = string_series.str.endswith(raw_value, na=False)
        else:
            mask = string_series.str.contains(raw_value, case=False, na=False)
        return df[mask.fillna(False)]

    def expand_json_column(
        self,
        df: pd.DataFrame,
        column: str,
        row_limit: int = 100,
    ) -> Tuple[pd.DataFrame, Dict[str, int]]:
        records: List[Dict[str, Any]] = []
        row_indexes: List[int] = []
        failed_rows = 0

        for row_index, raw_value in df[column].dropna().head(row_limit).items():
            parsed_value = raw_value
            if isinstance(raw_value, str):
                try:
                    parsed_value = json.loads(raw_value)
                except Exception:
                    failed_rows += 1
                    continue

            if isinstance(parsed_value, list):
                parsed_value = {"items": json.dumps(parsed_value, ensure_ascii=False)}
            if not isinstance(parsed_value, dict):
                failed_rows += 1
                continue

            row_indexes.append(row_index)
            records.append(parsed_value)

        if not records:
            return pd.DataFrame(), {"成功行数": 0, "失败行数": failed_rows, "展开字段数": 0}

        expanded_df = pd.json_normalize(records, sep=".")
        expanded_df.insert(0, "原始行号", row_indexes)
        return expanded_df, {
            "成功行数": len(expanded_df),
            "失败行数": failed_rows,
            "展开字段数": max(len(expanded_df.columns) - 1, 0),
        }

    def basic_statistics(self, df: pd.DataFrame, context: Dict[str, Any]):
        """基础统计分析。"""
        st.subheader("📊 基础统计分析")
        numeric_columns = context["numeric_columns"]
        dimension_columns = context["dimension_columns"]

        if not numeric_columns:
            st.warning("当前数据集中没有数值列。")
            return

        col1, col2 = st.columns([1, 1])
        with col1:
            metric_column = st.selectbox("数值指标", numeric_columns, key="bi_stats_metric")
            aggregation_dimension = st.selectbox(
                "对比维度",
                ["无"] + dimension_columns,
                key="bi_stats_dimension",
            )
        with col2:
            top_n = st.slider("维度 Top N", 3, 30, 10, key="bi_stats_top_n")

        numeric_series = pd.to_numeric(df[metric_column], errors="coerce")
        stats_cols = st.columns(5)
        stats_cols[0].metric("平均值", f"{numeric_series.mean():.2f}" if numeric_series.notna().any() else "-")
        stats_cols[1].metric("中位数", f"{numeric_series.median():.2f}" if numeric_series.notna().any() else "-")
        stats_cols[2].metric("P90", f"{numeric_series.quantile(0.9):.2f}" if numeric_series.notna().any() else "-")
        stats_cols[3].metric("零值数量", int((numeric_series == 0).sum()))
        stats_cols[4].metric("空值数量", int(numeric_series.isna().sum()))

        chart_col1, chart_col2 = st.columns(2)
        with chart_col1:
            hist_fig = px.histogram(
                df,
                x=metric_column,
                nbins=30,
                title=f"{metric_column} 分布直方图",
            )
            st.plotly_chart(hist_fig, use_container_width=True)
        with chart_col2:
            box_fig = px.box(df, y=metric_column, title=f"{metric_column} 箱线图")
            st.plotly_chart(box_fig, use_container_width=True)

        if aggregation_dimension != "无":
            grouped = (
                df.groupby(aggregation_dimension, dropna=False)[metric_column]
                .agg(["count", "sum", "mean"])
                .reset_index()
                .sort_values("sum", ascending=False)
                .head(top_n)
            )
            st.markdown("**按维度聚合**")
            st.dataframe(grouped, use_container_width=True, hide_index=True)
            grouped_fig = px.bar(
                grouped,
                x=aggregation_dimension,
                y="sum",
                title=f"{metric_column} 按 {aggregation_dimension} 聚合",
            )
            st.plotly_chart(grouped_fig, use_container_width=True)

    def correlation_analysis(self, df: pd.DataFrame, context: Dict[str, Any]):
        """相关性分析。"""
        st.subheader("🔗 相关性分析")
        numeric_columns = context["numeric_columns"]

        if len(numeric_columns) < 2:
            st.warning("至少需要 2 个数值列才能进行相关性分析。")
            return

        selected_columns = st.multiselect(
            "选择相关性分析字段",
            numeric_columns,
            default=numeric_columns[: min(6, len(numeric_columns))],
            key="bi_corr_columns",
        )
        corr_method = st.selectbox("相关系数方法", ["pearson", "spearman", "kendall"], key="bi_corr_method")
        if len(selected_columns) < 2:
            st.info("请至少选择 2 个字段。")
            return

        corr_matrix = df[selected_columns].corr(method=corr_method)
        fig = px.imshow(
            corr_matrix,
            title=f"相关性热力图 ({corr_method})",
            aspect="auto",
            color_continuous_scale="RdBu_r",
            text_auto=".2f",
        )
        st.plotly_chart(fig, use_container_width=True)
        st.dataframe(corr_matrix, use_container_width=True)

    def create_pivot_table(self, df: pd.DataFrame, context: Dict[str, Any]):
        """创建数据透视分析。"""
        st.subheader("🔍 透视聚合分析")
        dimension_columns = context["dimension_columns"]
        numeric_columns = context["numeric_columns"]

        if not dimension_columns:
            st.warning("当前没有适合做维度聚合的字段。")
            return

        col1, col2, col3 = st.columns(3)
        with col1:
            row_dimensions = st.multiselect(
                "行维度",
                dimension_columns,
                default=dimension_columns[:1],
                key="bi_pivot_rows",
            )
        with col2:
            column_dimension = st.selectbox(
                "列维度",
                ["无"] + dimension_columns,
                key="bi_pivot_columns",
            )
        with col3:
            value_column = st.selectbox(
                "指标列",
                ["记录数"] + numeric_columns,
                key="bi_pivot_value",
            )

        agg_func = st.selectbox("聚合函数", ["sum", "mean", "count", "min", "max"], key="bi_pivot_agg")

        if not row_dimensions:
            st.info("请至少选择一个行维度。")
            return

        try:
            working_df = df.copy()
            metric_name = value_column
            if value_column == "记录数":
                working_df["__record_count__"] = 1
                metric_name = "__record_count__"
                effective_agg = "sum"
            else:
                effective_agg = agg_func

            pivot_df = pd.pivot_table(
                working_df,
                values=metric_name,
                index=row_dimensions,
                columns=None if column_dimension == "无" else column_dimension,
                aggfunc=effective_agg,
                fill_value=0,
            )
            st.dataframe(pivot_df, use_container_width=True)

            if column_dimension != "无":
                heatmap_fig = px.imshow(
                    pivot_df,
                    title="透视热力图",
                    aspect="auto",
                    color_continuous_scale="Blues",
                )
                st.plotly_chart(heatmap_fig, use_container_width=True)
            else:
                chart_df = pivot_df.reset_index()
                if len(row_dimensions) == 1:
                    bar_fig = px.bar(
                        chart_df.sort_values(chart_df.columns[-1], ascending=False).head(20),
                        x=row_dimensions[0],
                        y=chart_df.columns[-1],
                        title="透视聚合柱状图",
                    )
                    st.plotly_chart(bar_fig, use_container_width=True)
        except Exception as exc:
            st.error(f"生成透视分析失败: {exc}")

    def time_series_analysis(self, df: pd.DataFrame, context: Dict[str, Any]):
        """时间序列分析。"""
        st.subheader("📈 趋势分析")
        datetime_columns = context["datetime_columns"]
        numeric_columns = context["numeric_columns"]
        dimension_columns = context["dimension_columns"]

        if not datetime_columns:
            st.warning("当前没有可识别的时间字段。")
            return

        value_options = ["记录数"] + numeric_columns
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            date_column = st.selectbox("时间字段", datetime_columns, key="bi_ts_date")
        with col2:
            value_column = st.selectbox("指标字段", value_options, key="bi_ts_value")
        with col3:
            freq = st.selectbox("聚合频率", ["D", "W", "M", "Q", "Y"], key="bi_ts_freq")
        with col4:
            agg_func = st.selectbox("聚合方式", ["sum", "mean", "count", "max", "min"], key="bi_ts_agg")

        split_options = ["无"] + [column for column in dimension_columns if column != date_column]
        split_by = st.selectbox("分组维度", split_options, key="bi_ts_split")

        try:
            working_df = df.copy()
            working_df[date_column] = self.safe_to_datetime(working_df[date_column])
            working_df = working_df.dropna(subset=[date_column]).sort_values(date_column)
            if working_df.empty:
                st.warning("时间字段全部无法解析。")
                return

            if value_column == "记录数":
                working_df["__record_count__"] = 1
                value_name = "__record_count__"
                effective_agg = "sum"
            else:
                value_name = value_column
                effective_agg = agg_func

            if split_by == "无":
                resampled = (
                    working_df.set_index(date_column)[value_name]
                    .resample(freq)
                    .agg(effective_agg)
                    .reset_index()
                )
                fig = px.line(resampled, x=date_column, y=value_name, markers=True, title="时间趋势")
                st.plotly_chart(fig, use_container_width=True)
            else:
                grouped = (
                    working_df.groupby([pd.Grouper(key=date_column, freq=freq), split_by])[value_name]
                    .agg(effective_agg)
                    .reset_index()
                )
                top_groups = (
                    grouped.groupby(split_by)[value_name]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                    .index.tolist()
                )
                grouped = grouped[grouped[split_by].isin(top_groups)]
                fig = px.line(
                    grouped,
                    x=date_column,
                    y=value_name,
                    color=split_by,
                    markers=True,
                    title="分组时间趋势",
                )
                st.plotly_chart(fig, use_container_width=True)

            series_for_metric = working_df[value_name] if value_name in working_df else pd.Series(dtype="float64")
            metric_cols = st.columns(4)
            metric_cols[0].metric("数据点数", len(working_df))
            metric_cols[1].metric("平均值", f"{pd.to_numeric(series_for_metric, errors='coerce').mean():.2f}" if value_column != "记录数" else "-")
            metric_cols[2].metric("最大值", f"{pd.to_numeric(series_for_metric, errors='coerce').max():.2f}" if value_column != "记录数" else "-")
            metric_cols[3].metric("最小值", f"{pd.to_numeric(series_for_metric, errors='coerce').min():.2f}" if value_column != "记录数" else "-")
        except Exception as exc:
            st.error(f"时间趋势分析失败: {exc}")

    def create_dashboard(self, df: pd.DataFrame, context: Dict[str, Any]):
        """交互式图表工作台。"""
        st.subheader("🎯 图表工作台")
        numeric_columns = context["numeric_columns"]
        dimension_columns = context["dimension_columns"]

        if not dimension_columns and not numeric_columns:
            st.warning("当前数据不适合生成图表。")
            return

        chart_type = st.selectbox(
            "图表类型",
            ["柱状图", "折线图", "散点图", "箱线图", "面积图", "饼图"],
            key="bi_chart_type",
        )
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            x_axis = st.selectbox("X轴", dimension_columns + numeric_columns, key="bi_chart_x")
        with col2:
            y_axis = st.selectbox("Y轴", ["记录数"] + numeric_columns, key="bi_chart_y")
        with col3:
            color_axis = st.selectbox("颜色分组", ["无"] + dimension_columns, key="bi_chart_color")
        with col4:
            agg_func = st.selectbox("聚合方式", ["sum", "mean", "count", "max", "min"], key="bi_chart_agg")

        top_n = st.slider("展示 Top N", 3, 50, 15, key="bi_chart_top_n")

        try:
            chart_df, plot_x, plot_y = self.prepare_chart_data(
                df,
                x_axis=x_axis,
                y_axis=y_axis,
                color_axis=None if color_axis == "无" else color_axis,
                agg_func=agg_func,
                top_n=top_n,
                chart_type=chart_type,
            )

            if chart_type == "柱状图":
                fig = px.bar(chart_df, x=plot_x, y=plot_y, color=color_axis if color_axis != "无" else None)
            elif chart_type == "折线图":
                fig = px.line(chart_df, x=plot_x, y=plot_y, color=color_axis if color_axis != "无" else None, markers=True)
            elif chart_type == "散点图":
                fig = px.scatter(chart_df, x=plot_x, y=plot_y, color=color_axis if color_axis != "无" else None)
            elif chart_type == "箱线图":
                fig = px.box(chart_df, x=plot_x, y=plot_y, color=color_axis if color_axis != "无" else None)
            elif chart_type == "面积图":
                fig = px.area(chart_df, x=plot_x, y=plot_y, color=color_axis if color_axis != "无" else None)
            else:
                fig = px.pie(chart_df, names=plot_x, values=plot_y, color=color_axis if color_axis != "无" else None)

            fig.update_layout(title=f"{plot_y} 按 {plot_x} 分析")
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(chart_df.head(100), use_container_width=True, hide_index=True)
        except Exception as exc:
            st.error(f"生成图表失败: {exc}")

    def prepare_chart_data(
        self,
        df: pd.DataFrame,
        x_axis: str,
        y_axis: str,
        color_axis: Optional[str],
        agg_func: str,
        top_n: int,
        chart_type: str,
    ) -> Tuple[pd.DataFrame, str, str]:
        working_df = df.copy()
        if y_axis == "记录数":
            working_df["__record_count__"] = 1
            y_name = "__record_count__"
            effective_agg = "sum"
        else:
            y_name = y_axis
            effective_agg = agg_func

        if chart_type == "散点图" and y_axis != "记录数":
            sampled_df = working_df[[x_axis, y_name] + ([color_axis] if color_axis else [])].dropna().head(5000)
            return sampled_df, x_axis, y_name

        group_columns = [x_axis] + ([color_axis] if color_axis else [])
        chart_df = (
            working_df.groupby(group_columns, dropna=False)[y_name]
            .agg(effective_agg)
            .reset_index()
            .sort_values(y_name, ascending=False)
            .head(top_n)
        )
        return chart_df, x_axis, y_name

    def export_report(self, df: pd.DataFrame, context: Dict[str, Any]):
        """导出分析报告。"""
        st.subheader("💾 导出分析报告")
        report_type = st.selectbox("报告格式", ["Excel", "CSV", "HTML"], key="bi_report_type")

        if st.button("生成报告", key="bi_generate_report"):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            insights = self.build_scenario_insights(df, context)
            if report_type == "Excel":
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine="openpyxl") as writer:
                    df.to_excel(writer, sheet_name="原始数据", index=False)
                    context["column_profile"].to_excel(writer, sheet_name="字段画像", index=False)
                    quality_issues = context["quality_report"]["issues"]
                    if not quality_issues.empty:
                        quality_issues.to_excel(writer, sheet_name="质量问题", index=False)
                    numeric_columns = context["numeric_columns"]
                    if numeric_columns:
                        df[numeric_columns].describe().to_excel(writer, sheet_name="统计信息")
                        if len(numeric_columns) >= 2:
                            df[numeric_columns].corr().to_excel(writer, sheet_name="相关性分析")
                    if insights["cards"]:
                        pd.DataFrame(insights["cards"]).to_excel(writer, sheet_name="场景洞察", index=False)
                    if insights["tables"]:
                        for index, table in enumerate(insights["tables"][:2], start=1):
                            table["data"].to_excel(
                                writer,
                                sheet_name=f"洞察明细{index}",
                                index=False,
                            )

                output.seek(0)
                st.download_button(
                    label="📥 下载 Excel 报告",
                    data=output.getvalue(),
                    file_name=f"BI分析报告_{timestamp}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
            elif report_type == "CSV":
                st.download_button(
                    label="📥 下载 CSV 数据",
                    data=df.to_csv(index=False).encode("utf-8-sig"),
                    file_name=f"BI原始数据_{timestamp}.csv",
                    mime="text/csv",
                    use_container_width=True,
                )
            else:
                html_report = self.generate_html_report(df, context, insights=insights)
                st.download_button(
                    label="📥 下载 HTML 报告",
                    data=html_report,
                    file_name=f"BI分析报告_{timestamp}.html",
                    mime="text/html",
                    use_container_width=True,
                )

    def generate_html_report(
        self,
        df: pd.DataFrame,
        context: Optional[Dict[str, Any]] = None,
        insights: Optional[Dict[str, Any]] = None,
    ) -> str:
        """生成 HTML 报告。"""
        context = context or self.build_analysis_context(df)
        insights = insights or self.build_scenario_insights(df, context)
        overview = context["overview"]
        profile_df = context["column_profile"].head(20)
        issues_df = context["quality_report"]["issues"].head(20)

        profile_html = profile_df.to_html(index=False, escape=False) if not profile_df.empty else "<p>暂无字段画像。</p>"
        issues_html = issues_df.to_html(index=False, escape=False) if not issues_df.empty else "<p>暂无明显质量问题。</p>"
        cards_html = "".join(
            f"<div class='metric'><div class='label'>{card['label']}</div><div class='value'>{card['value']}</div><div class='detail'>{card['detail']}</div></div>"
            for card in insights["cards"]
        ) or "<p>暂无场景洞察。</p>"
        scenario_tags = " / ".join(insights["scenarios"]) if insights["scenarios"] else "未识别"
        highlights_html = "".join(
            f"<li>{highlight}</li>" for highlight in insights["highlights"]
        ) or "<li>暂无额外建议。</li>"

        return f"""
        <!DOCTYPE html>
        <html lang="zh-CN">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>BI 数据分析报告</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 0; background: #f5f7fb; color: #1f2937; }}
                .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}
                .hero {{ background: linear-gradient(135deg, #1d4ed8, #0f172a); color: #fff; padding: 32px; border-radius: 16px; }}
                .hero h1 {{ margin: 0 0 8px; }}
                .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin: 24px 0; }}
                .metric {{ background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08); }}
                .metric .label {{ color: #64748b; font-size: 13px; }}
                .metric .value {{ font-size: 28px; font-weight: 700; margin-top: 6px; }}
                .metric .detail {{ color: #94a3b8; font-size: 12px; margin-top: 8px; }}
                .section {{ background: #fff; border-radius: 16px; padding: 24px; margin-bottom: 20px; box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08); }}
                .chips {{ margin-top: 12px; color: #dbeafe; font-size: 14px; }}
                ul {{ margin: 0; padding-left: 20px; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 12px; }}
                th, td {{ border: 1px solid #e2e8f0; padding: 10px 12px; text-align: left; font-size: 14px; }}
                th {{ background: #eff6ff; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="hero">
                    <h1>BI 数据分析报告</h1>
                    <p>生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                    <div class="chips">识别场景: {scenario_tags}</div>
                </div>

                <div class="metrics">
                    <div class="metric"><div class="label">总行数</div><div class="value">{overview['总行数']:,}</div></div>
                    <div class="metric"><div class="label">总列数</div><div class="value">{overview['总列数']}</div></div>
                    <div class="metric"><div class="label">缺失值</div><div class="value">{overview['缺失值']:,}</div></div>
                    <div class="metric"><div class="label">重复行</div><div class="value">{overview['重复行']:,}</div></div>
                    <div class="metric"><div class="label">完整率</div><div class="value">{overview['完整率(%)']:.1f}%</div></div>
                    <div class="metric"><div class="label">内存占用</div><div class="value">{overview['内存占用(MB)']:.2f} MB</div></div>
                </div>

                <div class="section">
                    <h2>场景洞察</h2>
                    <div class="metrics">{cards_html}</div>
                    <ul>{highlights_html}</ul>
                </div>

                <div class="section">
                    <h2>字段画像（前 20 条）</h2>
                    {profile_html}
                </div>

                <div class="section">
                    <h2>质量问题（前 20 条）</h2>
                    {issues_html}
                </div>

                <div class="section">
                    <h2>原始数据预览（前 10 行）</h2>
                    {df.head(10).to_html(index=False, escape=False)}
                </div>
            </div>
        </body>
        </html>
        """
