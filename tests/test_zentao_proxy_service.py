import argparse
import io
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.integrations.zentao_proxy_service import (  # noqa: E402
    MAX_JSON_BODY_BYTES,
    PayloadTooLargeError,
    _build_server_config,
    _read_json_body,
)


def _build_args(**overrides):
    base = {
        "host": "",
        "port": 0,
        "db_host": "127.0.0.1",
        "db_port": 3306,
        "db_user": "qa",
        "db_password": "secret",
        "db_name": "zentao",
        "token": None,
    }
    base.update(overrides)
    return argparse.Namespace(**base)


def test_build_server_config_defaults_to_localhost():
    config = _build_server_config(_build_args())

    assert config["listen_host"] == "127.0.0.1"
    assert config["listen_port"] == 18080
    assert config["token"] == ""


def test_build_server_config_requires_token_for_non_local_bind():
    with pytest.raises(ValueError, match="必须设置代理访问令牌"):
        _build_server_config(_build_args(host="0.0.0.0", token=""))


def test_read_json_body_rejects_oversized_payload():
    handler = type(
        "Handler",
        (),
        {
            "headers": {"Content-Length": str(MAX_JSON_BODY_BYTES + 1)},
            "rfile": io.BytesIO(b"{}"),
        },
    )()

    with pytest.raises(PayloadTooLargeError):
        _read_json_body(handler)

