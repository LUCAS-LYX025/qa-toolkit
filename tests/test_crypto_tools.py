import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from qa_toolkit.utils.crypto_tools import (
    base64_decode,
    base64_encode,
    digest_text,
    generate_rsa_keypair,
    pbkdf2_derive,
    rsa_decrypt_text,
    rsa_encrypt_text,
    symmetric_decrypt,
    symmetric_encrypt,
)


def test_base64_round_trip_supports_utf8_text():
    encoded = base64_encode("测试工具")

    assert encoded == "5rWL6K+V5bel5YW3"
    assert base64_decode(encoded) == "测试工具"


def test_digest_text_returns_stable_md5_hex():
    assert digest_text("hello", "MD5") == "5d41402abc4b2a76b9719d911017c592"


def test_pbkdf2_derive_returns_expected_length():
    derived = pbkdf2_derive(
        password="secret",
        salt="salt",
        iterations=1000,
        key_length=32,
        algorithm="SHA256",
        output_format="hex",
    )

    assert len(derived) == 64
    assert derived.startswith("a8df")


def test_symmetric_encrypt_and_decrypt_round_trip_for_aes_cbc():
    ciphertext = symmetric_encrypt(
        plaintext="qa-toolkit",
        algorithm="AES",
        mode="CBC",
        key="0123456789abcdef",
        key_format="text",
        iv="abcdef9876543210",
        iv_format="text",
        output_format="base64",
    )

    plaintext = symmetric_decrypt(
        ciphertext=ciphertext,
        algorithm="AES",
        mode="CBC",
        key="0123456789abcdef",
        key_format="text",
        iv="abcdef9876543210",
        iv_format="text",
        input_format="base64",
    )

    assert plaintext == "qa-toolkit"


def test_rsa_generate_encrypt_and_decrypt_round_trip():
    keypair = generate_rsa_keypair(2048)
    ciphertext = rsa_encrypt_text("hello rsa", keypair["public_key"], output_format="base64")
    plaintext = rsa_decrypt_text(ciphertext, keypair["private_key"], input_format="base64")

    assert "BEGIN PUBLIC KEY" in keypair["public_key"]
    assert "BEGIN PRIVATE KEY" in keypair["private_key"]
    assert plaintext == "hello rsa"
