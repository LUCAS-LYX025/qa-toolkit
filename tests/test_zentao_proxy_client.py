import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.integrations.zentao_proxy_client import ZenTaoProxyClient


class _FakeResponse:
    def __init__(self, payload: Dict[str, Any], status_code: int = 200) -> None:
        self.payload = payload
        self.status_code = status_code

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"status={self.status_code}")

    def json(self) -> Dict[str, Any]:
        return self.payload


class _RecordingSession:
    def __init__(self, responses: List[_FakeResponse]) -> None:
        self.responses = list(responses)
        self.calls: List[Dict[str, Any]] = []
        self.closed = False

    def request(self, **kwargs: Any) -> _FakeResponse:
        self.calls.append(kwargs)
        if not self.responses:
            raise AssertionError("unexpected request")
        return self.responses.pop(0)

    def close(self) -> None:
        self.closed = True


def test_proxy_client_adds_bearer_token_and_parses_summary_dataframe() -> None:
    session = _RecordingSession(
        [
            _FakeResponse(
                {
                    "success": True,
                    "columns": ["测试人员", "提交bug数量"],
                    "records": [{"测试人员": "Alice", "提交bug数量": 3}],
                }
            )
        ]
    )

    client = ZenTaoProxyClient(
        base_url="https://proxy.example.com/",
        token="demo-token",
        timeout_seconds=12,
        session=session,
    )
    dataframe = client.query_qa_stats(7, {"start_date": "2026-04-01", "end_date": "2026-04-08"})

    assert list(dataframe.columns) == ["测试人员", "提交bug数量"]
    assert dataframe.iloc[0]["测试人员"] == "Alice"
    assert int(dataframe.iloc[0]["提交bug数量"]) == 3
    assert session.calls[0]["url"] == "https://proxy.example.com/query/qa-summary"
    assert session.calls[0]["headers"]["Authorization"] == "Bearer demo-token"
    assert session.calls[0]["timeout"] == 12.0
    assert session.calls[0]["json"]["product_id"] == 7


def test_proxy_client_caches_metadata_and_normalizes_option_items() -> None:
    session = _RecordingSession(
        [
            _FakeResponse(
                {
                    "success": True,
                    "products": [{"id": 1, "name": "乘客服务"}],
                    "roles": [["qa", "测试人员"]],
                    "bug_types": [{"key": "codeerror", "name": "代码错误"}],
                }
            )
        ]
    )

    client = ZenTaoProxyClient(base_url="https://proxy.example.com", session=session)

    assert client.get_products() == [(1, "乘客服务")]
    assert client.get_user_roles() == [("qa", "测试人员")]
    assert client.get_bug_types() == [("codeerror", "代码错误")]
    assert len(session.calls) == 1

    client.close_connection()
    assert session.closed is True
