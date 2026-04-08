from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd
import requests
import streamlit as st


class ZenTaoProxyClient:
    """通过 HTTP 代理访问禅道统计能力。"""

    def __init__(
        self,
        base_url: str,
        token: str = "",
        timeout_seconds: float = 30.0,
        session: Optional[requests.sessions.Session] = None,
    ) -> None:
        self.base_url = str(base_url).strip().rstrip("/")
        self.token = str(token or "").strip()
        self.timeout_seconds = max(float(timeout_seconds), 1.0)
        self.session = session or requests.Session()
        self._metadata_cache: Optional[Dict[str, Any]] = None

    def close_connection(self) -> None:
        close = getattr(self.session, "close", None)
        if callable(close):
            close()

    def get_products(self) -> List[Tuple[int, str]]:
        payload = self._get_metadata_payload()
        return self._normalize_option_items(payload.get("products"), value_key="id", label_key="name", cast_value=int)

    def get_user_roles(self) -> List[Tuple[str, str]]:
        payload = self._get_metadata_payload()
        return self._normalize_option_items(payload.get("roles"), value_key="key", label_key="name", cast_value=str)

    def get_bug_types(self) -> List[Tuple[str, str]]:
        payload = self._get_metadata_payload()
        return self._normalize_option_items(payload.get("bug_types"), value_key="key", label_key="name", cast_value=str)

    def query_qa_stats(self, product_id: int, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        return self._request_dataframe(
            "/query/qa-summary",
            {"product_id": int(product_id), "config": dict(config)},
            "查询测试统计数据时出错",
        )

    def query_dev_stats(self, product_id: int, config: Dict[str, Any]) -> Optional[pd.DataFrame]:
        return self._request_dataframe(
            "/query/dev-summary",
            {"product_id": int(product_id), "config": dict(config)},
            "查询开发统计数据时出错",
        )

    def query_timeout_bugs_detail(
        self,
        developer_name: str,
        product_id: int,
        start_date: str,
        end_date: str,
        config: Dict[str, Any],
    ) -> Optional[pd.DataFrame]:
        return self._request_dataframe(
            "/query/dev-detail",
            {
                "person_name": str(developer_name),
                "product_id": int(product_id),
                "start_date": str(start_date),
                "end_date": str(end_date),
                "config": dict(config),
            },
            "查询开发超时明细失败",
        )

    def query_qa_timeout_bugs_detail(
        self,
        tester_name: str,
        product_id: int,
        start_date: str,
        end_date: str,
        config: Dict[str, Any],
    ) -> Optional[pd.DataFrame]:
        return self._request_dataframe(
            "/query/qa-detail",
            {
                "person_name": str(tester_name),
                "product_id": int(product_id),
                "start_date": str(start_date),
                "end_date": str(end_date),
                "config": dict(config),
            },
            "查询测试超时明细失败",
        )

    def _request_dataframe(self, path: str, payload: Dict[str, Any], error_prefix: str) -> Optional[pd.DataFrame]:
        try:
            response_payload = self._request("POST", path, payload)
            records = response_payload.get("records") or []
            columns = response_payload.get("columns") or []
            if records:
                if columns:
                    return pd.DataFrame(records, columns=columns)
                return pd.DataFrame(records)
            if columns:
                return pd.DataFrame(columns=columns)
            return pd.DataFrame()
        except Exception as exc:
            st.error(f"{error_prefix}: {exc}")
            return None

    def _request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if not self.base_url:
            raise ValueError("代理地址不能为空。")

        headers = {"Accept": "application/json"}
        if payload is not None:
            headers["Content-Type"] = "application/json"
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"

        response = self.session.request(
            method=method,
            url=f"{self.base_url}{path}",
            headers=headers,
            json=payload,
            timeout=self.timeout_seconds,
        )
        response.raise_for_status()

        try:
            data = response.json()
        except ValueError as exc:
            raise RuntimeError("代理返回的不是合法 JSON。") from exc

        if not isinstance(data, dict):
            raise RuntimeError("代理返回数据格式无效。")
        if data.get("success", True) is False:
            raise RuntimeError(str(data.get("error") or "代理请求失败。"))
        return data

    def _get_metadata_payload(self) -> Dict[str, Any]:
        if self._metadata_cache is None:
            self._metadata_cache = self._request("POST", "/metadata")
        return dict(self._metadata_cache)

    @staticmethod
    def _normalize_option_items(
        items: Optional[Iterable[Any]],
        value_key: str,
        label_key: str,
        cast_value,
    ) -> List[Tuple[Any, str]]:
        normalized: List[Tuple[Any, str]] = []
        for item in items or []:
            if isinstance(item, dict):
                raw_value = item.get(value_key)
                raw_label = item.get(label_key)
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                raw_value, raw_label = item[0], item[1]
            else:
                continue
            if raw_value in (None, ""):
                continue
            normalized.append((cast_value(raw_value), str(raw_label or raw_value)))
        return normalized
