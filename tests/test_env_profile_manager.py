import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.core.env_profile_manager import EnvProfileManager  # noqa: E402


def test_env_profile_manager_upsert_and_persist(tmp_path: Path):
    store_file = tmp_path / "env_profiles.json"
    manager = EnvProfileManager(store_file=store_file)

    saved = manager.upsert_profile(
        "staging",
        {
            "base_url": "https://api.example.com",
            "timeout_seconds": 45,
            "retry_times": 2,
            "verify_ssl": False,
            "auth": {
                "mode": "bearer",
                "token": "token-123",
            },
            "headers": {"X-Trace-ID": "qa"},
        },
    )
    assert saved["name"] == "staging"
    assert saved["base_url"] == "https://api.example.com"
    assert saved["auth"]["mode"] == "bearer"
    assert saved["auth"]["token"] == "token-123"

    assert manager.set_active("staging", "api_automation") is True
    assert manager.get_active_profile_name("api_automation") == "staging"

    reloaded = EnvProfileManager(store_file=store_file)
    active = reloaded.get_active_profile("api_automation")
    assert active is not None
    assert active["name"] == "staging"
    assert active["timeout_seconds"] == 45.0
    assert active["retry_times"] == 2
    assert active["verify_ssl"] is False


def test_env_profile_manager_normalizes_invalid_payload(tmp_path: Path):
    manager = EnvProfileManager(store_file=tmp_path / "env_profiles.json")

    saved = manager.upsert_profile(
        "invalid-case",
        {
            "base_url": "  ",
            "timeout_seconds": "not-a-number",
            "retry_times": -5,
            "verify_ssl": "0",
            "auth": {"mode": "unknown-mode"},
            "headers": ["not", "dict"],
        },
    )

    assert saved["base_url"] == ""
    assert saved["timeout_seconds"] == 30.0
    assert saved["retry_times"] == 0
    assert saved["verify_ssl"] is False
    assert saved["auth"]["mode"] == "none"
    assert saved["headers"] == {}


def test_env_profile_manager_delete_clears_active_namespaces(tmp_path: Path):
    manager = EnvProfileManager(store_file=tmp_path / "env_profiles.json")

    manager.upsert_profile("dev", {"base_url": "https://dev.example.com"})
    manager.upsert_profile("prod", {"base_url": "https://prod.example.com"})
    manager.set_active("dev", "api_automation")
    manager.set_active("dev", "api_security")
    manager.set_active("prod", "api_performance")

    assert manager.delete_profile("dev") is True
    assert manager.get_profile("dev") is None
    assert manager.get_active_profile_name("api_automation") == ""
    assert manager.get_active_profile_name("api_security") == ""
    assert manager.get_active_profile_name("api_performance") == "prod"


def test_env_profile_manager_persists_encrypted_sensitive_fields(tmp_path: Path):
    store_file = tmp_path / "env_profiles.json"
    key_file = tmp_path / ".env_profiles.key"
    manager = EnvProfileManager(store_file=store_file, key_file=key_file)

    manager.upsert_profile(
        "secure-profile",
        {
            "base_url": "https://secure.example.com",
            "timeout_seconds": 60,
            "verify_ssl": True,
            "auth": {"mode": "bearer", "token": "super-secret-token"},
            "headers": {"X-API-Key": "k-123"},
        },
    )

    text = store_file.read_text(encoding="utf-8")
    assert "super-secret-token" not in text
    assert '"X-API-Key": "k-123"' not in text
    assert "auth_encrypted" in text
    assert "headers_encrypted" in text


def test_env_profile_manager_keeps_ciphertext_when_key_changes(tmp_path: Path, monkeypatch):
    store_file = tmp_path / "env_profiles.json"
    key_file = tmp_path / ".env_profiles.key"

    manager = EnvProfileManager(store_file=store_file, key_file=key_file)
    manager.upsert_profile(
        "staging",
        {
            "base_url": "https://api.example.com",
            "auth": {"mode": "bearer", "token": "token-123"},
            "headers": {"Authorization": "Bearer token-123"},
        },
    )

    before_payload = json.loads(store_file.read_text(encoding="utf-8"))
    before_cipher = before_payload["profiles"]["staging"]["auth_encrypted"]

    monkeypatch.setenv("QA_TOOLKIT_ENV_PROFILE_KEY", "totally-different-key")
    wrong_key_manager = EnvProfileManager(store_file=store_file, key_file=key_file)
    wrong_key_profile = wrong_key_manager.get_profile("staging")
    assert wrong_key_profile is not None
    assert wrong_key_profile.get("encryption_error") is True

    wrong_key_manager.set_active("staging", "api_automation")
    after_payload = json.loads(store_file.read_text(encoding="utf-8"))
    after_cipher = after_payload["profiles"]["staging"]["auth_encrypted"]
    assert before_cipher == after_cipher

    monkeypatch.delenv("QA_TOOLKIT_ENV_PROFILE_KEY", raising=False)
    restored_manager = EnvProfileManager(store_file=store_file, key_file=key_file)
    restored_profile = restored_manager.get_profile("staging")
    assert restored_profile is not None
    assert restored_profile["encryption_error"] is False
    assert restored_profile["auth"]["mode"] == "bearer"
    assert restored_profile["auth"]["token"] == "token-123"
