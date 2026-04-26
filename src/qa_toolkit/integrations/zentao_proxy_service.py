from __future__ import annotations

import argparse
import ipaddress
import json
import os
from datetime import date, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable, Dict, Optional

import pandas as pd

from qa_toolkit.integrations.zentao_exporter import ZenTaoPerformanceExporter

MAX_JSON_BODY_BYTES = 1024 * 1024


class PayloadTooLargeError(ValueError):
    """请求体超过代理允许上限。"""


def _is_local_listen_host(host: str) -> bool:
    candidate = str(host or "").strip().lower()
    if candidate in {"localhost", "127.0.0.1", "::1"}:
        return True
    try:
        return ipaddress.ip_address(candidate).is_loopback
    except ValueError:
        return False


def _serialize_scalar(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except Exception:
        pass
    if hasattr(value, "item") and callable(getattr(value, "item")):
        try:
            value = value.item()
        except Exception:
            pass
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    return value


def _serialize_dataframe(df: Optional[pd.DataFrame]) -> Dict[str, Any]:
    if df is None:
        return {"columns": [], "records": []}

    columns = [str(column) for column in df.columns]
    records = []
    for record in df.to_dict(orient="records"):
        serialized = {}
        for key, value in record.items():
            serialized[str(key)] = _serialize_scalar(value)
        records.append(serialized)
    return {"columns": columns, "records": records}


def _json_response(handler: BaseHTTPRequestHandler, status_code: int, payload: Dict[str, Any]) -> None:
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)


def _read_json_body(handler: BaseHTTPRequestHandler, max_body_bytes: int = MAX_JSON_BODY_BYTES) -> Dict[str, Any]:
    content_length = int(handler.headers.get("Content-Length", "0") or "0")
    if content_length <= 0:
        return {}
    if content_length > max(int(max_body_bytes), 0):
        raise PayloadTooLargeError(f"请求体过大，最大允许 {max_body_bytes} 字节。")
    raw_body = handler.rfile.read(content_length)
    if not raw_body:
        return {}
    if len(raw_body) > max(int(max_body_bytes), 0):
        raise PayloadTooLargeError(f"请求体过大，最大允许 {max_body_bytes} 字节。")
    payload = json.loads(raw_body.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("请求体必须是 JSON 对象。")
    return payload


def _require_token(handler: BaseHTTPRequestHandler, expected_token: str) -> bool:
    if not expected_token:
        return True

    auth_header = str(handler.headers.get("Authorization", "")).strip()
    raw_token = str(handler.headers.get("X-Zentao-Proxy-Token", "")).strip()
    if auth_header == "Bearer " + expected_token or raw_token == expected_token:
        return True

    _json_response(
        handler,
        401,
        {"success": False, "error": "未授权，请提供有效的代理访问令牌。"},
    )
    return False


def _build_server_config(args: argparse.Namespace) -> Dict[str, Any]:
    db_host = args.db_host or os.getenv("ZENTAO_DB_HOST", "").strip()
    db_port = int(args.db_port or os.getenv("ZENTAO_DB_PORT", "3306"))
    db_user = args.db_user or os.getenv("ZENTAO_DB_USER", "").strip()
    db_password = args.db_password or os.getenv("ZENTAO_DB_PASSWORD", "")
    db_name = args.db_name or os.getenv("ZENTAO_DB_NAME", "zentao").strip()
    if not db_host or not db_user or not db_name:
        raise ValueError("请提供完整的数据库连接信息：db-host、db-user、db-name。")

    listen_host = str(args.host or os.getenv("ZENTAO_PROXY_LISTEN_HOST", "127.0.0.1")).strip()
    listen_port = int(args.port or os.getenv("ZENTAO_PROXY_LISTEN_PORT", "18080"))
    token = str(args.token if args.token is not None else os.getenv("ZENTAO_PROXY_TOKEN", "")).strip()
    if not _is_local_listen_host(listen_host) and not token:
        raise ValueError("监听非本机地址时必须设置代理访问令牌（--token 或 ZENTAO_PROXY_TOKEN）。")

    return {
        "listen_host": listen_host,
        "listen_port": listen_port,
        "token": token,
        "db_config": {
            "host": db_host,
            "port": db_port,
            "user": db_user,
            "password": db_password,
            "database": db_name,
        },
    }


def _with_exporter(db_config: Dict[str, Any], callback: Callable[[ZenTaoPerformanceExporter], Dict[str, Any]]) -> Dict[str, Any]:
    exporter = ZenTaoPerformanceExporter(db_config)
    if getattr(exporter, "mysql_db", None) is None:
        raise RuntimeError("代理服务无法连接到禅道数据库。")
    try:
        return callback(exporter)
    finally:
        exporter.close_connection()


def _require_payload_fields(payload: Dict[str, Any], *field_names: str) -> None:
    missing = [field_name for field_name in field_names if field_name not in payload]
    if missing:
        raise ValueError("请求缺少必要字段: " + ", ".join(missing))


def _make_handler(server_config: Dict[str, Any]):
    class ZentaoProxyHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            return

        def do_GET(self) -> None:
            if self.path == "/health":
                _json_response(self, 200, {"success": True, "message": "ok"})
                return
            _json_response(self, 404, {"success": False, "error": "未找到请求路径。"})

        def do_POST(self) -> None:
            if not _require_token(self, str(server_config.get("token", ""))):
                return

            try:
                payload = _read_json_body(self)
                response_payload = self._dispatch(self.path, payload)
                _json_response(self, 200, {"success": True, **response_payload})
            except PayloadTooLargeError as exc:
                _json_response(self, 413, {"success": False, "error": str(exc)})
            except ValueError as exc:
                _json_response(self, 400, {"success": False, "error": str(exc)})
            except Exception as exc:
                _json_response(self, 500, {"success": False, "error": str(exc)})

        def _dispatch(self, path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
            db_config = dict(server_config["db_config"])
            if path == "/metadata":
                return _with_exporter(db_config, self._handle_metadata)
            if path == "/query/qa-summary":
                _require_payload_fields(payload, "product_id", "config")
                return _with_exporter(
                    db_config,
                    lambda exporter: self._handle_dataframe_query(
                        exporter.query_qa_stats(
                            int(payload["product_id"]),
                            dict(payload.get("config") or {}),
                        )
                    ),
                )
            if path == "/query/dev-summary":
                _require_payload_fields(payload, "product_id", "config")
                return _with_exporter(
                    db_config,
                    lambda exporter: self._handle_dataframe_query(
                        exporter.query_dev_stats(
                            int(payload["product_id"]),
                            dict(payload.get("config") or {}),
                        )
                    ),
                )
            if path == "/query/qa-detail":
                _require_payload_fields(payload, "person_name", "product_id", "start_date", "end_date", "config")
                return _with_exporter(
                    db_config,
                    lambda exporter: self._handle_dataframe_query(
                        exporter.query_qa_timeout_bugs_detail(
                            str(payload["person_name"]),
                            int(payload["product_id"]),
                            str(payload["start_date"]),
                            str(payload["end_date"]),
                            dict(payload.get("config") or {}),
                        )
                    ),
                )
            if path == "/query/dev-detail":
                _require_payload_fields(payload, "person_name", "product_id", "start_date", "end_date", "config")
                return _with_exporter(
                    db_config,
                    lambda exporter: self._handle_dataframe_query(
                        exporter.query_timeout_bugs_detail(
                            str(payload["person_name"]),
                            int(payload["product_id"]),
                            str(payload["start_date"]),
                            str(payload["end_date"]),
                            dict(payload.get("config") or {}),
                        )
                    ),
                )
            raise ValueError("未找到请求路径。")

        @staticmethod
        def _handle_metadata(exporter: ZenTaoPerformanceExporter) -> Dict[str, Any]:
            products = [{"id": product_id, "name": product_name} for product_id, product_name in exporter.get_products()]
            roles = [{"key": role_key, "name": role_name} for role_key, role_name in exporter.get_user_roles()]
            bug_types = [{"key": type_key, "name": type_name} for type_key, type_name in exporter.get_bug_types()]
            return {
                "products": products,
                "roles": roles,
                "bug_types": bug_types,
            }

        @staticmethod
        def _handle_dataframe_query(dataframe: Optional[pd.DataFrame]) -> Dict[str, Any]:
            return _serialize_dataframe(dataframe)

    return ZentaoProxyHandler


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="在内网环境启动禅道统计 HTTP 代理服务。")
    parser.add_argument("--host", default="", help="监听地址，默认读取 ZENTAO_PROXY_LISTEN_HOST 或 127.0.0.1")
    parser.add_argument("--port", type=int, default=0, help="监听端口，默认读取 ZENTAO_PROXY_LISTEN_PORT 或 18080")
    parser.add_argument("--db-host", default="", help="禅道数据库主机")
    parser.add_argument("--db-port", type=int, default=0, help="禅道数据库端口")
    parser.add_argument("--db-user", default="", help="禅道数据库用户名")
    parser.add_argument("--db-password", default="", help="禅道数据库密码")
    parser.add_argument("--db-name", default="", help="禅道数据库名")
    parser.add_argument("--token", default=None, help="代理访问令牌，可选")
    return parser


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    server_config = _build_server_config(args)

    server = ThreadingHTTPServer(
        (str(server_config["listen_host"]), int(server_config["listen_port"])),
        _make_handler(server_config),
    )
    print(
        "Zentao proxy listening on "
        + str(server_config["listen_host"])
        + ":"
        + str(server_config["listen_port"])
    )
    if server_config.get("token"):
        print("Bearer token authentication enabled.")
    else:
        print("Warning: token authentication is disabled.")
    server.serve_forever()


if __name__ == "__main__":
    main()
