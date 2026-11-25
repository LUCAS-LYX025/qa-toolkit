"""加密/解码工具的核心实现。

所有算法清单来自 :mod:`qa_toolkit.core.crypto_registry`，业务方可以通过
``register_encoder`` / ``register_hash`` / ``register_symmetric_algorithm``
等扩展点新增算法，而无需改动页面代码。
"""
from __future__ import annotations

import base64
import binascii
import codecs
import hashlib
import hmac
import html
import json
import re
import secrets
import string
import urllib.parse
from datetime import datetime
from typing import Any, Dict, Optional

from Crypto.Cipher import DES3
from Crypto.Util.Padding import pad, unpad
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from qa_toolkit.core.crypto_registry import (
    EncoderSpec,
    get_encoder,
    get_encoders,
    get_hash_algorithms,
    get_hash_spec,
    get_mode_spec,
    get_symmetric_algorithms,
    get_symmetric_spec,
    register_encoder,
)

MAX_TEXT_CHARS = 1_000_000
MAX_PBKDF2_ITERATIONS = 10_000_000
MAX_PBKDF2_KEY_LENGTH = 1024
MIN_RSA_KEY_SIZE = 2048
MAX_RSA_KEY_SIZE = 8192

KDF_HASH_ALGORITHMS = {
    "SHA1": hashes.SHA1(),
    "SHA256": hashes.SHA256(),
    "SHA384": hashes.SHA384(),
    "SHA512": hashes.SHA512(),
}

_UNICODE_ESCAPE_PATTERN = re.compile(
    r"\\(?:u[0-9a-fA-F]{4}|U[0-9a-fA-F]{8}|x[0-9a-fA-F]{2}|[0-7]{1,3}|[nrt\\'\"])"
)


# ---------- 通用字节/编码帮助函数 ----------

def _decode_base64_bytes(value: str) -> bytes:
    """解码 Base64，兼容换行空白和 URL-safe 字符集。"""
    cleaned = "".join(str(value or "").split())
    if not cleaned:
        return b""
    try:
        return base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError):
        pass
    translated = cleaned.replace("-", "+").replace("_", "/")
    translated += "=" * (-len(translated) % 4)
    try:
        return base64.b64decode(translated, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError(f"Base64 输入无效: {exc}") from exc


def _normalize_binary_input(value: str, input_format: str, text_encoding: str = "utf-8") -> bytes:
    raw_value = str(value or "")

    if input_format == "text":
        return raw_value.encode(text_encoding)
    if input_format == "hex":
        cleaned = "".join(raw_value.split())
        if len(cleaned) % 2 != 0:
            raise ValueError("十六进制输入长度必须为偶数")
        try:
            return bytes.fromhex(cleaned)
        except ValueError as exc:
            raise ValueError(f"十六进制输入无效: {exc}") from exc
    if input_format == "base64":
        return _decode_base64_bytes(raw_value)

    raise ValueError(f"不支持的输入格式: {input_format}")


def _encode_binary_output(data: bytes, output_format: str, text_encoding: str = "utf-8") -> str:
    if output_format == "text":
        return data.decode(text_encoding)
    if output_format == "hex":
        return data.hex()
    if output_format == "base64":
        return base64.b64encode(data).decode("ascii")
    raise ValueError(f"不支持的输出格式: {output_format}")


def _check_text_size(value: str) -> None:
    if len(str(value)) > MAX_TEXT_CHARS:
        raise ValueError(
            f"输入文本超过 {MAX_TEXT_CHARS} 字符，请分段处理后再运行"
        )


# ---------- 编码/解码 ----------

def base64_encode(text: str, encoding: str = "utf-8", *, urlsafe: bool = False) -> str:
    data = str(text).encode(encoding)
    codec = base64.urlsafe_b64encode if urlsafe else base64.b64encode
    return codec(data).decode("ascii")


def base64_decode(text: str, encoding: str = "utf-8") -> str:
    data = _decode_base64_bytes(text)
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"Base64 解码后的字节无法按 {encoding} 解释（{exc}）。"
            "如果内容来自 GBK 系统，请切换字符编码；如果是二进制数据，请使用“十六进制 → Base64”。"
        ) from exc


def url_encode(text: str) -> str:
    return urllib.parse.quote(str(text), safe="")


def url_decode(text: str, *, plus_as_space: bool = True) -> str:
    decode = urllib.parse.unquote_plus if plus_as_space else urllib.parse.unquote
    return decode(str(text))


def html_encode(text: str) -> str:
    return html.escape(str(text))


def html_decode(text: str) -> str:
    return html.unescape(str(text))


def unicode_encode(text: str) -> str:
    return str(text).encode("unicode_escape").decode("ascii")


def unicode_decode(text: str) -> str:
    raw = str(text)
    if raw and not _UNICODE_ESCAPE_PATTERN.search(raw):
        raise ValueError(
            "未检测到 Unicode 转义序列（例如 \\u4e2d 或 \\x41）。"
            "如需把中文转成转义，请点“开始编码”。"
        )
    return codecs.decode(raw, "unicode_escape")


def hex_encode(text: str, encoding: str = "utf-8") -> str:
    if isinstance(text, (bytes, bytearray, memoryview)):
        return bytes(text).hex()
    return str(text).encode(encoding).hex()


def hex_decode(text: str, encoding: str = "utf-8", *, output_format: str = "text") -> str:
    cleaned = "".join(str(text or "").split())
    try:
        data = bytes.fromhex(cleaned)
    except ValueError as exc:
        raise ValueError(f"十六进制输入无效: {exc}") from exc
    if output_format == "base64":
        return base64.b64encode(data).decode("ascii")
    if output_format == "hex":
        return data.hex()
    if output_format != "text":
        raise ValueError(f"不支持的十六进制输出格式: {output_format}")
    try:
        return data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"这些字节无法按 {encoding} 解释为文本（{exc}）。"
            "密文/签名等二进制内容请选择“十六进制 → Base64”输出。"
        ) from exc


def _register_default_encoders() -> None:
    specs = (
        EncoderSpec("Base64", lambda text, enc: base64_encode(text, enc),
                    lambda text, enc: base64_decode(text, enc), "标准 Base64"),
        EncoderSpec("Base64 (URL-safe)", lambda text, enc: base64_encode(text, enc, urlsafe=True),
                    lambda text, enc: base64_decode(text, enc), "JWT / query 参数常用变体"),
        EncoderSpec("URL", lambda text, enc: url_encode(text),
                    lambda text, enc: url_decode(text), "解码时 + 还原为空格"),
        EncoderSpec("HTML", lambda text, enc: html_encode(text),
                    lambda text, enc: html_decode(text), "HTML 实体"),
        EncoderSpec("Unicode", lambda text, enc: unicode_encode(text),
                    lambda text, enc: unicode_decode(text), "\\uXXXX / \\xXX 转义"),
        EncoderSpec("十六进制", lambda text, enc: hex_encode(text, enc),
                    lambda text, enc: hex_decode(text, enc), "按字符编码还原为文本"),
        EncoderSpec("十六进制 → Base64", lambda text, enc: hex_encode(text, enc),
                    lambda text, enc: hex_decode(text, enc, output_format="base64"),
                    "任意二进制的可复制文本形态"),
        EncoderSpec("十六进制 → Hex", lambda text, enc: hex_encode(text, enc),
                    lambda text, enc: hex_decode(text, enc, output_format="hex"),
                    "规范化十六进制（去空白、统一小写）"),
    )
    for spec in specs:
        register_encoder(spec)


_register_default_encoders()


# ---------- 摘要 / HMAC / KDF ----------

def digest_text(text: str, algorithm: str, *, encoding: str = "utf-8") -> str:
    digest = get_hash_spec(algorithm).factory()
    digest.update(str(text).encode(encoding))
    return digest.hexdigest()


def hmac_text(text: str, key: str, algorithm: str, *, encoding: str = "utf-8") -> str:
    digestmod = get_hash_spec(algorithm).factory
    return hmac.new(str(key).encode(encoding), str(text).encode(encoding), digestmod).hexdigest()


def pbkdf2_derive(
    password: str,
    salt: str,
    iterations: int,
    key_length: int,
    algorithm: str,
    output_format: str = "hex",
    *,
    salt_format: str = "text",
    encoding: str = "utf-8",
) -> str:
    normalized_algorithm = str(algorithm).upper()
    if normalized_algorithm not in KDF_HASH_ALGORITHMS:
        raise ValueError(f"不支持的 PBKDF2 算法: {algorithm}")

    iterations = int(iterations)
    if not 1 <= iterations <= MAX_PBKDF2_ITERATIONS:
        raise ValueError(
            f"迭代次数需在 1 至 {MAX_PBKDF2_ITERATIONS} 之间，当前为 {iterations}"
        )
    key_length = int(key_length)
    if not 1 <= key_length <= MAX_PBKDF2_KEY_LENGTH:
        raise ValueError(
            f"导出长度需在 1 至 {MAX_PBKDF2_KEY_LENGTH} 字节之间，当前为 {key_length}"
        )

    salt_bytes = _normalize_binary_input(salt, salt_format, text_encoding=encoding)
    kdf = PBKDF2HMAC(
        algorithm=KDF_HASH_ALGORITHMS[normalized_algorithm],
        length=key_length,
        salt=salt_bytes,
        iterations=iterations,
    )
    derived = kdf.derive(str(password).encode(encoding))
    return _encode_binary_output(derived, output_format)


# ---------- 对称加解密 ----------

def _normalize_symmetric_key(algorithm: str, key_bytes: bytes) -> bytes:
    spec = get_symmetric_spec(algorithm)
    key_bytes = bytes(key_bytes)

    if str(algorithm).upper() == "3DES":
        try:
            key_bytes = DES3.adjust_key_parity(key_bytes)
        except ValueError as exc:
            raise ValueError(f"3DES 密钥无效: {exc}") from exc

    if len(key_bytes) not in spec.key_lengths:
        raise ValueError(
            f"{algorithm} 密钥长度无效，当前为 {len(key_bytes)} 字节，"
            f"支持 {sorted(spec.key_lengths)}"
        )
    return key_bytes


def _build_cipher(algorithm: str, mode: str, key: bytes, iv: Optional[bytes] = None):
    spec = get_symmetric_spec(algorithm)
    normalized_key = _normalize_symmetric_key(algorithm, key)
    return get_mode_spec(mode).builder(spec, normalized_key, iv)


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
    _check_text_size(plaintext)
    key_bytes = _normalize_binary_input(key, key_format, text_encoding=text_encoding)
    mode_spec = get_mode_spec(mode)
    iv_bytes = (
        _normalize_binary_input(iv, iv_format, text_encoding=text_encoding)
        if mode_spec.requires_iv and iv else None
    )
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
    mode_spec = get_mode_spec(mode)
    iv_bytes = (
        _normalize_binary_input(iv, iv_format, text_encoding=text_encoding)
        if mode_spec.requires_iv and iv else None
    )
    cipher = _build_cipher(algorithm, mode, key_bytes, iv_bytes)
    ciphertext_bytes = _normalize_binary_input(ciphertext, input_format)
    plaintext_bytes = unpad(cipher.decrypt(ciphertext_bytes), cipher.block_size)
    return plaintext_bytes.decode(text_encoding)


def describe_key_requirements(algorithm: str, mode: str) -> str:
    spec = get_symmetric_spec(algorithm)
    mode_spec = get_mode_spec(mode)
    lengths = sorted(spec.key_lengths)
    iv_part = (
        f"{mode} 需要 {spec.block_size} 字节 IV" if mode_spec.requires_iv
        else f"{mode} 不需要 IV"
    )
    notes = " ".join(part for part in (spec.description, mode_spec.description) if part)
    return (
        f"{algorithm} 密钥长度支持 {lengths} 字节；{iv_part}。"
        + (f" 提示：{notes}" if notes else "")
    )


def key_material_status(algorithm: str, mode: str, key: str, key_format: str,
                        iv: str = "", iv_format: str = "text") -> Dict[str, Any]:
    spec = get_symmetric_spec(algorithm)
    mode_spec = get_mode_spec(mode)
    try:
        key_length = len(_normalize_binary_input(key, key_format))
    except ValueError:
        key_length = None
    if mode_spec.requires_iv:
        try:
            iv_length = len(_normalize_binary_input(iv, iv_format))
        except ValueError:
            iv_length = None
    else:
        iv_length = 0
    return {
        "key_current": key_length,
        "key_expected": sorted(spec.key_lengths),
        "key_ok": key_length in spec.key_lengths,
        "iv_current": iv_length,
        "iv_expected": spec.block_size if mode_spec.requires_iv else 0,
        "iv_ok": (not mode_spec.requires_iv) or iv_length == spec.block_size,
    }


def generate_random_key_material(algorithm: str, mode: str, key_format: str = "base64",
                                 iv_format: str = "base64") -> Dict[str, str]:
    spec = get_symmetric_spec(algorithm)
    mode_spec = get_mode_spec(mode)
    key_length = max(spec.key_lengths)

    def _encode_material(data: bytes, fmt: str) -> str:
        if fmt == "text":
            alphabet = string.ascii_letters + string.digits
            return "".join(secrets.choice(alphabet) for _ in range(len(data)))
        return _encode_binary_output(data, fmt)

    key_bytes = secrets.token_bytes(key_length)
    iv_bytes = secrets.token_bytes(spec.block_size) if mode_spec.requires_iv else b""
    return {
        "key": _encode_material(key_bytes, key_format),
        "iv": _encode_material(iv_bytes, iv_format),
    }


# ---------- RSA ----------

def _validate_rsa_key_size(key_size: int) -> int:
    key_size = int(key_size)
    if not MIN_RSA_KEY_SIZE <= key_size <= MAX_RSA_KEY_SIZE:
        raise ValueError(
            f"RSA 密钥长度需在 {MIN_RSA_KEY_SIZE} 至 {MAX_RSA_KEY_SIZE} 位之间，当前为 {key_size}"
        )
    return key_size


def generate_rsa_keypair(key_size: int = 2048, passphrase: str = "") -> Dict[str, str]:
    key_size = _validate_rsa_key_size(key_size)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=key_size)
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


def rsa_max_plaintext_bytes(public_key: Any) -> int:
    """OAEP(MGF1-SHA256, SHA256) 下单次可加密的最大明文字节数。"""
    if isinstance(public_key, str):
        public_key = serialization.load_pem_public_key(public_key.encode("utf-8"))
    overhead = 2 * hashes.SHA256.digest_size + 2
    return max(0, public_key.key_size // 8 - overhead)


def rsa_encrypt_text(plaintext: str, public_key_pem: str, output_format: str = "base64",
                     *, encoding: str = "utf-8") -> str:
    public_key = serialization.load_pem_public_key(str(public_key_pem).encode("utf-8"))
    data = str(plaintext).encode(encoding)
    limit = rsa_max_plaintext_bytes(public_key)
    if len(data) > limit:
        raise ValueError(
            f"明文长度 {len(data)} 字节超过 {public_key.key_size} 位 RSA (OAEP-SHA256) 的"
            f"上限 {limit} 字节；请缩短内容，或改用对称加密后用 RSA 保护密钥。"
        )
    ciphertext = public_key.encrypt(
        data,
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


# ---------- 错误提示 / 导出 / 结果签名 ----------

def format_crypto_error(exc: Exception, operation: str = "操作") -> str:
    """把底层加密异常翻译成可操作的中文诊断。"""
    message = str(exc)
    lowered = message.lower()
    if "base64" in lowered or "non-base64" in lowered:
        detail = "密文不是合法的 Base64，请检查格式选择与复制是否完整"
    elif "padding is incorrect" in lowered or "decryption failed" in lowered:
        detail = "填充校验失败：通常是密钥、IV、模式与加密时不一致"
    elif "iv" in lowered and ("长度" in message or "length" in lowered):
        detail = "IV 长度不符合当前算法要求"
    elif "密钥长度" in message or "key size" in lowered:
        detail = "密钥长度不符合当前算法要求"
    elif "cbc 模式必须提供 iv" in message:
        detail = "CBC 模式必须提供 IV"
    elif "明文长度" in message:
        detail = message
    elif "迭代次数" in message or "导出长度" in message:
        detail = message
    else:
        detail = message
    return f"{operation}失败：{detail}（原始错误：{message}）"


def build_output_filename(source: str, label: str = "", ext: str = "txt") -> str:
    slug = re.sub(r"[^0-9A-Za-z\u4e00-\u9fff]+", "-", str(label or "")).strip("-")[:48]
    slug = slug or str(source or "result")
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"crypto_{source}_{slug}_{stamp}.{ext.lstrip('.')}"


def build_crypto_signature(payload: Dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


# ---------- 兼容别名 ----------

HASH_ALGORITHMS = {
    name: spec.factory for name, spec in get_hash_algorithms().items()
}
SYMMETRIC_ALGORITHMS = {
    name: {"cipher_cls": spec.cipher_cls, "key_lengths": set(spec.key_lengths),
           "block_size": spec.block_size}
    for name, spec in get_symmetric_algorithms().items()
}


__all__ = [
    "HASH_ALGORITHMS",
    "SYMMETRIC_ALGORITHMS",
    "MAX_TEXT_CHARS",
    "MAX_PBKDF2_ITERATIONS",
    "MIN_RSA_KEY_SIZE",
    "MAX_RSA_KEY_SIZE",
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
    "describe_key_requirements",
    "key_material_status",
    "generate_random_key_material",
    "generate_rsa_keypair",
    "rsa_max_plaintext_bytes",
    "rsa_encrypt_text",
    "rsa_decrypt_text",
    "format_crypto_error",
    "build_output_filename",
    "build_crypto_signature",
    "get_encoder",
    "get_encoders",
    "EncoderSpec",
]
