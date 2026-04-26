from __future__ import annotations

import base64
import datetime
import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet, InvalidToken

from qa_toolkit.paths import REPORTS_DIR


DEFAULT_TIMEOUT_SECONDS = 30.0
DEFAULT_VERIFY_SSL = True
PROFILE_KEY_ENV = "QA_TOOLKIT_ENV_PROFILE_KEY"
ENCRYPTION_PREFIX = "fernet:v1:"
VALID_AUTH_MODES = {
    "none",
    "bearer",
    "api_key",
    "basic",
    "custom_header",
    "headers_json",
}


def _utc_now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")


def _coerce_bool(value: Any, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _coerce_float(value: Any, default: float, min_value: Optional[float] = None) -> float:
    try:
        resolved = float(value)
    except (TypeError, ValueError):
        resolved = float(default)
    if min_value is not None:
        resolved = max(resolved, float(min_value))
    return resolved


def _coerce_int(value: Any, default: int, min_value: Optional[int] = None) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        resolved = int(default)
    if min_value is not None:
        resolved = max(resolved, int(min_value))
    return resolved


def _normalize_name(name: str) -> str:
    normalized = str(name or "").strip()
    if not normalized:
        raise ValueError("配置名称不能为空")
    return normalized


def _normalize_namespace(namespace: str) -> str:
    normalized = str(namespace or "").strip()
    return normalized or "default"


def _fernet_key_from_secret(secret: str) -> bytes:
    text = str(secret or "").strip()
    if not text:
        return Fernet.generate_key()

    raw = text.encode("utf-8")
    try:
        decoded = base64.urlsafe_b64decode(raw)
        if len(decoded) == 32:
            return base64.urlsafe_b64encode(decoded)
    except Exception:
        pass

    digest = hashlib.sha256(raw).digest()
    return base64.urlsafe_b64encode(digest)


class EnvProfileManager:
    """统一维护环境配置（地址/超时/重试/证书/鉴权）并持久化到本地文件。"""

    def __init__(self, store_file: Optional[Path] = None, key_file: Optional[Path] = None):
        self.store_file = Path(store_file) if store_file else (REPORTS_DIR / "env_profiles.json")
        self.store_file.parent.mkdir(parents=True, exist_ok=True)
        self.key_file = Path(key_file) if key_file else (self.store_file.parent / ".env_profiles.key")
        self.key_file.parent.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._resolve_fernet_key())
        self._store = self._load_store()

    def _resolve_fernet_key(self) -> bytes:
        env_secret = str(os.environ.get(PROFILE_KEY_ENV, "") or "").strip()
        if env_secret:
            return _fernet_key_from_secret(env_secret)

        if self.key_file.exists():
            try:
                file_secret = self.key_file.read_text(encoding="utf-8").strip()
                if file_secret:
                    return _fernet_key_from_secret(file_secret)
            except Exception:
                pass

        generated_key = Fernet.generate_key()
        try:
            self.key_file.write_text(generated_key.decode("utf-8"), encoding="utf-8")
            os.chmod(self.key_file, 0o600)
        except Exception:
            pass
        return generated_key

    def _empty_store(self) -> Dict[str, Any]:
        return {
            "version": 2,
            "profiles": {},
            "active_by_namespace": {},
        }

    def _load_store(self) -> Dict[str, Any]:
        if not self.store_file.exists():
            return self._empty_store()
        try:
            with self.store_file.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except Exception:
            return self._empty_store()
        return self._normalize_store(data)

    def _normalize_store(self, data: Any) -> Dict[str, Any]:
        store = self._empty_store()
        if not isinstance(data, dict):
            return store

        raw_profiles = data.get("profiles", {})
        if isinstance(raw_profiles, list):
            for item in raw_profiles:
                if not isinstance(item, dict):
                    continue
                name = str(item.get("name") or "").strip()
                if not name:
                    continue
                store["profiles"][name] = self._normalize_profile_payload(item)
        elif isinstance(raw_profiles, dict):
            for name, payload in raw_profiles.items():
                normalized_name = str(name or "").strip()
                if not normalized_name:
                    continue
                store["profiles"][normalized_name] = self._normalize_profile_payload(payload)

        raw_active = data.get("active_by_namespace", {})
        if isinstance(raw_active, dict):
            for namespace, active_name in raw_active.items():
                normalized_namespace = _normalize_namespace(str(namespace))
                normalized_active_name = str(active_name or "").strip()
                if normalized_active_name and normalized_active_name in store["profiles"]:
                    store["active_by_namespace"][normalized_namespace] = normalized_active_name

        return store

    def _encrypt_json_payload(self, value: Any) -> str:
        payload_text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        token = self._fernet.encrypt(payload_text.encode("utf-8")).decode("utf-8")
        return f"{ENCRYPTION_PREFIX}{token}"

    def _decrypt_json_payload(self, cipher_text: Any, default: Any) -> Tuple[Any, bool]:
        text = str(cipher_text or "").strip()
        if not text:
            return deepcopy(default), True
        token = text[len(ENCRYPTION_PREFIX) :] if text.startswith(ENCRYPTION_PREFIX) else text
        try:
            payload_text = self._fernet.decrypt(token.encode("utf-8")).decode("utf-8")
            return json.loads(payload_text), True
        except (InvalidToken, ValueError, TypeError, UnicodeDecodeError, json.JSONDecodeError):
            return deepcopy(default), False

    def _serialize_profile_for_store(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        data = deepcopy(profile)
        auth_payload = self._normalize_auth(data.pop("auth", {}))
        headers_payload = self._normalize_headers(data.pop("headers", {}))

        legacy_auth_encrypted = str(data.pop("_auth_encrypted", "") or "").strip()
        legacy_headers_encrypted = str(data.pop("_headers_encrypted", "") or "").strip()
        encryption_error = bool(data.pop("_encryption_error", False))
        auth_is_default_none = auth_payload.get("mode") == "none" and len(auth_payload) == 1

        if encryption_error and auth_is_default_none and legacy_auth_encrypted:
            data["auth_encrypted"] = legacy_auth_encrypted
        else:
            data["auth_encrypted"] = self._encrypt_json_payload(auth_payload)

        if encryption_error and not headers_payload and legacy_headers_encrypted:
            data["headers_encrypted"] = legacy_headers_encrypted
        else:
            data["headers_encrypted"] = self._encrypt_json_payload(headers_payload)

        return data

    def _save_store(self) -> None:
        serialized_profiles: Dict[str, Dict[str, Any]] = {}
        for name, payload in self._store.get("profiles", {}).items():
            serialized_profiles[name] = self._serialize_profile_for_store(payload)

        payload = {
            "version": 2,
            "encryption": {
                "scheme": "fernet-v1",
                "sensitive_fields": ["auth", "headers"],
            },
            "profiles": serialized_profiles,
            "active_by_namespace": self._store["active_by_namespace"],
        }
        temp_file = self.store_file.with_suffix(f"{self.store_file.suffix}.tmp")
        with temp_file.open("w", encoding="utf-8") as file:
            json.dump(payload, file, ensure_ascii=False, indent=2)
        temp_file.replace(self.store_file)

    @staticmethod
    def _normalize_headers(headers: Any) -> Dict[str, str]:
        if not isinstance(headers, dict):
            return {}
        normalized: Dict[str, str] = {}
        for key, value in headers.items():
            normalized_key = str(key or "").strip()
            if not normalized_key:
                continue
            normalized[normalized_key] = "" if value is None else str(value)
        return normalized

    def _normalize_auth(self, auth: Any) -> Dict[str, Any]:
        data = auth if isinstance(auth, dict) else {}
        mode = str(data.get("mode") or "none").strip().lower()
        if mode not in VALID_AUTH_MODES:
            mode = "none"

        normalized: Dict[str, Any] = {"mode": mode}
        if mode == "bearer":
            normalized["token"] = str(data.get("token") or "").strip()
        elif mode == "api_key":
            normalized["header_name"] = str(data.get("header_name") or "X-API-Key").strip() or "X-API-Key"
            normalized["api_key_value"] = str(data.get("api_key_value") or data.get("key_value") or "").strip()
        elif mode == "basic":
            normalized["username"] = str(data.get("username") or "").strip()
            normalized["password"] = str(data.get("password") or "").strip()
        elif mode == "custom_header":
            normalized["header_name"] = str(data.get("header_name") or "X-Custom-Auth").strip() or "X-Custom-Auth"
            normalized["header_value"] = str(data.get("header_value") or "").strip()
        elif mode == "headers_json":
            auth_headers = self._normalize_headers(data.get("headers"))
            if auth_headers:
                normalized["headers"] = auth_headers

        return normalized

    def _normalize_profile_payload(self, profile: Any) -> Dict[str, Any]:
        data = profile if isinstance(profile, dict) else {}
        now = _utc_now_iso()
        created_at = str(data.get("created_at") or now)
        updated_at = str(data.get("updated_at") or created_at)
        encryption_error = False

        auth_raw: Any = data.get("auth")
        headers_raw: Any = data.get("headers")
        auth_encrypted = str(data.get("auth_encrypted") or "").strip()
        headers_encrypted = str(data.get("headers_encrypted") or "").strip()

        if auth_encrypted:
            decrypted_auth, auth_ok = self._decrypt_json_payload(auth_encrypted, default={})
            auth_raw = decrypted_auth if isinstance(decrypted_auth, dict) else {}
            encryption_error = encryption_error or not auth_ok
        if headers_encrypted:
            decrypted_headers, headers_ok = self._decrypt_json_payload(headers_encrypted, default={})
            headers_raw = decrypted_headers if isinstance(decrypted_headers, dict) else {}
            encryption_error = encryption_error or not headers_ok

        normalized = {
            "base_url": str(data.get("base_url") or "").strip(),
            "timeout_seconds": _coerce_float(data.get("timeout_seconds"), DEFAULT_TIMEOUT_SECONDS, min_value=1.0),
            "retry_times": _coerce_int(data.get("retry_times"), 0, min_value=0),
            "verify_ssl": _coerce_bool(data.get("verify_ssl"), DEFAULT_VERIFY_SSL),
            "auth": self._normalize_auth(auth_raw),
            "headers": self._normalize_headers(headers_raw),
            "created_at": created_at,
            "updated_at": updated_at,
        }
        if auth_encrypted:
            normalized["_auth_encrypted"] = auth_encrypted
        if headers_encrypted:
            normalized["_headers_encrypted"] = headers_encrypted
        if encryption_error:
            normalized["_encryption_error"] = True
        return normalized

    @staticmethod
    def _public_profile(name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        row = deepcopy(payload)
        encryption_error = bool(row.pop("_encryption_error", False))
        row.pop("_auth_encrypted", None)
        row.pop("_headers_encrypted", None)
        row["name"] = name
        row["encryption_error"] = encryption_error
        return row

    def list_encryption_issues(self) -> List[str]:
        issues = []
        for name, payload in self._store.get("profiles", {}).items():
            if payload.get("_encryption_error"):
                issues.append(name)
        issues.sort(key=str.casefold)
        return issues

    def list_profiles(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        for name, payload in self._store.get("profiles", {}).items():
            rows.append(self._public_profile(name, payload))
        rows.sort(key=lambda item: (str(item.get("updated_at") or ""), str(item.get("name") or "").casefold()), reverse=True)
        return rows

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        normalized_name = str(name or "").strip()
        payload = self._store.get("profiles", {}).get(normalized_name)
        if payload is None:
            return None
        return self._public_profile(normalized_name, payload)

    def upsert_profile(self, name: str, profile: Dict[str, Any]) -> Dict[str, Any]:
        normalized_name = _normalize_name(name)
        now = _utc_now_iso()

        existing = self._store.get("profiles", {}).get(normalized_name, {})
        normalized = self._normalize_profile_payload(profile)
        normalized["created_at"] = str(existing.get("created_at") or normalized.get("created_at") or now)
        normalized["updated_at"] = now
        normalized.pop("_encryption_error", None)
        normalized.pop("_auth_encrypted", None)
        normalized.pop("_headers_encrypted", None)

        self._store["profiles"][normalized_name] = normalized
        if not self._store["active_by_namespace"].get("default"):
            self._store["active_by_namespace"]["default"] = normalized_name
        self._save_store()
        return self.get_profile(normalized_name) or {}

    def delete_profile(self, name: str) -> bool:
        normalized_name = _normalize_name(name)
        if normalized_name not in self._store.get("profiles", {}):
            return False
        self._store["profiles"].pop(normalized_name, None)
        for namespace, active_name in list(self._store.get("active_by_namespace", {}).items()):
            if active_name == normalized_name:
                self._store["active_by_namespace"][namespace] = ""
        self._save_store()
        return True

    def set_active(self, name: str, namespace: str = "default") -> bool:
        normalized_name = _normalize_name(name)
        if normalized_name not in self._store.get("profiles", {}):
            return False
        normalized_namespace = _normalize_namespace(namespace)
        self._store["active_by_namespace"][normalized_namespace] = normalized_name
        self._save_store()
        return True

    def clear_active(self, namespace: str = "default") -> None:
        normalized_namespace = _normalize_namespace(namespace)
        self._store["active_by_namespace"][normalized_namespace] = ""
        self._save_store()

    def get_active_profile_name(self, namespace: str = "default") -> str:
        normalized_namespace = _normalize_namespace(namespace)
        active_map = self._store.get("active_by_namespace", {})
        profile_name = str(active_map.get(normalized_namespace) or active_map.get("default") or "").strip()
        if profile_name and profile_name in self._store.get("profiles", {}):
            return profile_name
        return ""

    def get_active_profile(self, namespace: str = "default") -> Optional[Dict[str, Any]]:
        active_name = self.get_active_profile_name(namespace)
        if not active_name:
            return None
        return self.get_profile(active_name)


def get_session_env_profile_manager() -> EnvProfileManager:
    import streamlit as st

    session_key = "_env_profile_manager"
    if session_key not in st.session_state:
        st.session_state[session_key] = EnvProfileManager(
            store_file=REPORTS_DIR / "env_profiles.json",
            key_file=REPORTS_DIR / ".env_profiles.key",
        )
    return st.session_state[session_key]
