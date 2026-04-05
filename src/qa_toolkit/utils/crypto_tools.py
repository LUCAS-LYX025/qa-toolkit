from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import hmac
import html
import urllib.parse
from typing import Dict, Optional

from Crypto.Cipher import AES, DES, DES3
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC


HASH_ALGORITHMS = {
    "MD5": hashlib.md5,
    "SHA1": hashlib.sha1,
    "SHA224": hashlib.sha224,
    "SHA256": hashlib.sha256,
    "SHA384": hashlib.sha384,
    "SHA512": hashlib.sha512,
}

KDF_HASH_ALGORITHMS = {
    "SHA1": hashes.SHA1(),
    "SHA256": hashes.SHA256(),
    "SHA384": hashes.SHA384(),
    "SHA512": hashes.SHA512(),
}

SYMMETRIC_ALGORITHMS = {
    "AES": {"cipher_cls": AES, "key_lengths": {16, 24, 32}, "block_size": AES.block_size},
    "DES": {"cipher_cls": DES, "key_lengths": {8}, "block_size": DES.block_size},
    "3DES": {"cipher_cls": DES3, "key_lengths": {16, 24}, "block_size": DES3.block_size},
}


def _normalize_binary_input(value: str, input_format: str, text_encoding: str = "utf-8") -> bytes:
    raw_value = str(value or "")

    if input_format == "text":
        return raw_value.encode(text_encoding)
    if input_format == "hex":
        cleaned = "".join(raw_value.strip().split())
        if len(cleaned) % 2 != 0:
            raise ValueError("十六进制输入长度必须为偶数")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError(f"十六进制输入无效: {exc}") from exc
    if input_format == "base64":
        try:
            return base64.b64decode(raw_value.strip(), validate=True)
        except binascii.Error as exc:
            raise ValueError(f"Base64 输入无效: {exc}") from exc

    raise ValueError(f"不支持的输入格式: {input_format}")


def _encode_binary_output(data: bytes, output_format: str, text_encoding: str = "utf-8") -> str:
    if output_format == "text":
        return data.decode(text_encoding)
    if output_format == "hex":
        return data.hex()
    if output_format == "base64":
        return base64.b64encode(data).decode("ascii")
    raise ValueError(f"不支持的输出格式: {output_format}")


def base64_encode(text: str, encoding: str = "utf-8") -> str:
    return base64.b64encode(str(text).encode(encoding)).decode("ascii")


def base64_decode(text: str, encoding: str = "utf-8") -> str:
    return base64.b64decode(str(text).strip(), validate=True).decode(encoding)


def url_encode(text: str) -> str:
    return urllib.parse.quote(str(text), safe="")


def url_decode(text: str) -> str:
    return urllib.parse.unquote(str(text))


def html_encode(text: str) -> str:
    return html.escape(str(text))


def html_decode(text: str) -> str:
    return html.unescape(str(text))


def unicode_encode(text: str) -> str:
    return str(text).encode("unicode_escape").decode("ascii")


def unicode_decode(text: str) -> str:
    return codecs.decode(str(text), "unicode_escape")


def hex_encode(text: str, encoding: str = "utf-8") -> str:
    return str(text).encode(encoding).hex()


def hex_decode(text: str, encoding: str = "utf-8") -> str:
    cleaned = "".join(str(text).strip().split())
    return bytes.fromhex(cleaned).decode(encoding)


def digest_text(text: str, algorithm: str) -> str:
    normalized_algorithm = str(algorithm).upper()
    if normalized_algorithm not in HASH_ALGORITHMS:
        raise ValueError(f"不支持的哈希算法: {algorithm}")
    return HASH_ALGORITHMS[normalized_algorithm](str(text).encode("utf-8")).hexdigest()


def hmac_text(text: str, key: str, algorithm: str) -> str:
    normalized_algorithm = str(algorithm).upper()
    if normalized_algorithm not in HASH_ALGORITHMS:
        raise ValueError(f"不支持的 HMAC 算法: {algorithm}")
    digestmod = HASH_ALGORITHMS[normalized_algorithm]
    return hmac.new(str(key).encode("utf-8"), str(text).encode("utf-8"), digestmod).hexdigest()


def pbkdf2_derive(
    password: str,
    salt: str,
    iterations: int,
    key_length: int,
    algorithm: str,
    output_format: str = "hex",
) -> str:
    normalized_algorithm = str(algorithm).upper()
    if normalized_algorithm not in KDF_HASH_ALGORITHMS:
        raise ValueError(f"不支持的 PBKDF2 算法: {algorithm}")

    kdf = PBKDF2HMAC(
        algorithm=KDF_HASH_ALGORITHMS[normalized_algorithm],
        length=int(key_length),
        salt=str(salt).encode("utf-8"),
        iterations=int(iterations),
    )
    derived = kdf.derive(str(password).encode("utf-8"))
    return _encode_binary_output(derived, output_format)


def _normalize_symmetric_key(algorithm: str, key_bytes: bytes) -> bytes:
    normalized_algorithm = str(algorithm).upper()
    algorithm_meta = SYMMETRIC_ALGORITHMS.get(normalized_algorithm)
    if algorithm_meta is None:
        raise ValueError(f"不支持的对称算法: {algorithm}")

    if normalized_algorithm == "3DES":
        try:
            key_bytes = DES3.adjust_key_parity(key_bytes)
        except ValueError as exc:
            raise ValueError(f"3DES 密钥无效: {exc}") from exc

    if len(key_bytes) not in algorithm_meta["key_lengths"]:
        supported_lengths = sorted(algorithm_meta["key_lengths"])
        raise ValueError(
            f"{normalized_algorithm} 密钥长度无效，当前为 {len(key_bytes)} 字节，支持 {supported_lengths}"
        )
    return key_bytes


def _build_cipher(algorithm: str, mode: str, key: bytes, iv: Optional[bytes] = None):
    normalized_algorithm = str(algorithm).upper()
    normalized_mode = str(mode).upper()

    algorithm_meta = SYMMETRIC_ALGORITHMS.get(normalized_algorithm)
    if algorithm_meta is None:
        raise ValueError(f"不支持的对称算法: {algorithm}")

    cipher_cls = algorithm_meta["cipher_cls"]
    normalized_key = _normalize_symmetric_key(normalized_algorithm, key)

    if normalized_mode == "ECB":
        return cipher_cls.new(normalized_key, cipher_cls.MODE_ECB)
    if normalized_mode == "CBC":
        if iv is None:
            raise ValueError("CBC 模式必须提供 IV")
        block_size = algorithm_meta["block_size"]
        if len(iv) != block_size:
            raise ValueError(f"{normalized_algorithm} 在 CBC 模式下的 IV 长度必须为 {block_size} 字节")
        return cipher_cls.new(normalized_key, cipher_cls.MODE_CBC, iv=iv)

    raise ValueError(f"不支持的加密模式: {mode}")


def symmetric_encrypt(
    plaintext: str,
    algorithm: str,
    mode: str,
    key: str,
    key_format: str = "text",
    iv: str = "",
    iv_format: str = "text",
    output_format: str = "base64",
    text_encoding: str = "utf-8",
) -> str:
    key_bytes = _normalize_binary_input(key, key_format, text_encoding=text_encoding)
    iv_bytes = _normalize_binary_input(iv, iv_format, text_encoding=text_encoding) if iv else None
    cipher = _build_cipher(algorithm, mode, key_bytes, iv_bytes)
    plaintext_bytes = str(plaintext).encode(text_encoding)
    ciphertext = cipher.encrypt(pad(plaintext_bytes, cipher.block_size))
    return _encode_binary_output(ciphertext, output_format)


def symmetric_decrypt(
    ciphertext: str,
    algorithm: str,
    mode: str,
    key: str,
    key_format: str = "text",
    iv: str = "",
    iv_format: str = "text",
    input_format: str = "base64",
    text_encoding: str = "utf-8",
) -> str:
    key_bytes = _normalize_binary_input(key, key_format, text_encoding=text_encoding)
    iv_bytes = _normalize_binary_input(iv, iv_format, text_encoding=text_encoding) if iv else None
    cipher = _build_cipher(algorithm, mode, key_bytes, iv_bytes)
    ciphertext_bytes = _normalize_binary_input(ciphertext, input_format)
    plaintext_bytes = unpad(cipher.decrypt(ciphertext_bytes), cipher.block_size)
    return plaintext_bytes.decode(text_encoding)


def generate_rsa_keypair(key_size: int = 2048, passphrase: str = "") -> Dict[str, str]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=int(key_size))
    public_key = private_key.public_key()

    encryption_algorithm = (
        serialization.BestAvailableEncryption(str(passphrase).encode("utf-8"))
        if passphrase
        else serialization.NoEncryption()
    )

    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm,
    ).decode("utf-8")

    public_pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    return {"private_key": private_pem, "public_key": public_pem}


def rsa_encrypt_text(plaintext: str, public_key_pem: str, output_format: str = "base64") -> str:
    public_key = serialization.load_pem_public_key(str(public_key_pem).encode("utf-8"))
    ciphertext = public_key.encrypt(
        str(plaintext).encode("utf-8"),
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return _encode_binary_output(ciphertext, output_format)


def rsa_decrypt_text(
    ciphertext: str,
    private_key_pem: str,
    passphrase: str = "",
    input_format: str = "base64",
) -> str:
    private_key = serialization.load_pem_private_key(
        str(private_key_pem).encode("utf-8"),
        password=str(passphrase).encode("utf-8") if passphrase else None,
    )
    plaintext = private_key.decrypt(
        _normalize_binary_input(ciphertext, input_format),
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return plaintext.decode("utf-8")


__all__ = [
    "HASH_ALGORITHMS",
    "SYMMETRIC_ALGORITHMS",
    "base64_encode",
    "base64_decode",
    "url_encode",
    "url_decode",
    "html_encode",
    "html_decode",
    "unicode_encode",
    "unicode_decode",
    "hex_encode",
    "hex_decode",
    "digest_text",
    "hmac_text",
    "pbkdf2_derive",
    "symmetric_encrypt",
    "symmetric_decrypt",
    "generate_rsa_keypair",
    "rsa_encrypt_text",
    "rsa_decrypt_text",
]
