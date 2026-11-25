"""加密/解密工具的注册式扩展点。

页面只从注册表读取选项，业务方可以注册新的编码器、摘要算法、对称算法、
加密模式和文本编码，无需修改 ``crypto_tools_page.py`` 中的 selectbox 列表。
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, FrozenSet, Optional

from Crypto.Cipher import AES, DES, DES3


@dataclass(frozen=True)
class EncoderSpec:
    """一种文本编码/解码器。encode/decode 签名均为 (text, encoding) -> str。"""

    name: str
    encode: Callable[[str, str], str]
    decode: Callable[[str, str], str]
    description: str = ""


@dataclass(frozen=True)
class HashSpec:
    factory: Callable[[], Any]
    description: str = ""
    secure: bool = True


@dataclass(frozen=True)
class SymmetricSpec:
    cipher_cls: Any
    key_lengths: FrozenSet[int]
    block_size: int
    description: str = ""
    deprecated: bool = False


@dataclass(frozen=True)
class ModeSpec:
    builder: Callable[[SymmetricSpec, bytes, Optional[bytes]], Any]
    requires_iv: bool
    description: str = ""
    secure: bool = True


_ENCODERS: Dict[str, EncoderSpec] = {}
_HASHES: Dict[str, HashSpec] = {}
_SYMMETRIC: Dict[str, SymmetricSpec] = {}
_MODES: Dict[str, ModeSpec] = {}
_TEXT_ENCODINGS: Dict[str, str] = {}


def register_encoder(spec: EncoderSpec, *, replace: bool = False) -> None:
    if spec.name in _ENCODERS and not replace:
        raise ValueError(f"编码器已注册: {spec.name}")
    _ENCODERS[spec.name] = spec


def register_hash(name: str, factory: Callable[[], Any], *, description: str = "",
                  secure: bool = True, replace: bool = False) -> None:
    if name in _HASHES and not replace:
        raise ValueError(f"摘要算法已注册: {name}")
    _HASHES[name] = HashSpec(factory=factory, description=description, secure=secure)


def register_symmetric_algorithm(name: str, cipher_cls: Any, key_lengths: Any,
                                 block_size: int, *, description: str = "",
                                 deprecated: bool = False, replace: bool = False) -> None:
    if name in _SYMMETRIC and not replace:
        raise ValueError(f"对称算法已注册: {name}")
    _SYMMETRIC[name] = SymmetricSpec(
        cipher_cls=cipher_cls,
        key_lengths=frozenset(int(n) for n in key_lengths),
        block_size=int(block_size),
        description=description,
        deprecated=deprecated,
    )


def register_symmetric_mode(name: str, builder: Callable[[SymmetricSpec, bytes, Optional[bytes]], Any],
                            *, requires_iv: bool, description: str = "",
                            secure: bool = True, replace: bool = False) -> None:
    if name in _MODES and not replace:
        raise ValueError(f"加密模式已注册: {name}")
    _MODES[name] = ModeSpec(builder=builder, requires_iv=requires_iv,
                            description=description, secure=secure)


def register_text_encoding(name: str, codec: str, *, replace: bool = False) -> None:
    if name in _TEXT_ENCODINGS and not replace:
        raise ValueError(f"文本编码已注册: {name}")
    _TEXT_ENCODINGS[name] = codec


def get_encoders() -> Dict[str, EncoderSpec]:
    return dict(_ENCODERS)


def get_encoder(name: str) -> EncoderSpec:
    try:
        return _ENCODERS[str(name)]
    except KeyError as exc:
        raise ValueError(f"不支持的编码工具: {name}") from exc


def get_hash_algorithms() -> Dict[str, HashSpec]:
    return dict(_HASHES)


def get_hash_spec(name: str) -> HashSpec:
    try:
        return _HASHES[str(name).upper()]
    except KeyError as exc:
        raise ValueError(f"不支持的摘要算法: {name}") from exc


def get_symmetric_algorithms() -> Dict[str, SymmetricSpec]:
    return dict(_SYMMETRIC)


def get_symmetric_spec(name: str) -> SymmetricSpec:
    try:
        return _SYMMETRIC[str(name).upper()]
    except KeyError as exc:
        raise ValueError(f"不支持的对称算法: {name}") from exc


def get_symmetric_modes() -> Dict[str, ModeSpec]:
    return dict(_MODES)


def get_mode_spec(name: str) -> ModeSpec:
    try:
        return _MODES[str(name).upper()]
    except KeyError as exc:
        raise ValueError(f"不支持的加密模式: {name}") from exc


def get_text_encodings() -> Dict[str, str]:
    return dict(_TEXT_ENCODINGS)


def get_registry_summary() -> Dict[str, int]:
    return {
        "encoders": len(_ENCODERS),
        "hashes": len(_HASHES),
        "symmetric": len(_SYMMETRIC),
        "modes": len(_MODES),
        "encodings": len(_TEXT_ENCODINGS),
    }


def _build_ecb(spec: SymmetricSpec, key: bytes, _iv: Optional[bytes]):
    return spec.cipher_cls.new(key, spec.cipher_cls.MODE_ECB)


def _build_cbc(spec: SymmetricSpec, key: bytes, iv: Optional[bytes]):
    if iv is None:
        raise ValueError("CBC 模式必须提供 IV")
    if len(iv) != spec.block_size:
        raise ValueError(
            f"IV 长度无效，当前为 {len(iv)} 字节，需要 {spec.block_size} 字节"
        )
    return spec.cipher_cls.new(key, spec.cipher_cls.MODE_CBC, iv=iv)


def _register_defaults() -> None:
    for name, factory, secure in (
        ("MD5", hashlib.md5, False),
        ("SHA1", hashlib.sha1, False),
        ("SHA224", hashlib.sha224, True),
        ("SHA256", hashlib.sha256, True),
        ("SHA384", hashlib.sha384, True),
        ("SHA512", hashlib.sha512, True),
    ):
        register_hash(name, factory, secure=secure,
                      description="仅用于兼容性校验，不可用于安全场景" if not secure else "")

    register_symmetric_algorithm("AES", AES, {16, 24, 32}, AES.block_size,
                                 description="推荐用于新业务")
    register_symmetric_algorithm("DES", DES, {8}, DES.block_size,
                                 description="已废弃，仅用于兼容旧系统", deprecated=True)
    register_symmetric_algorithm("3DES", DES3, {16, 24}, DES3.block_size,
                                 description="已废弃，仅用于兼容旧系统", deprecated=True)

    register_symmetric_mode("ECB", _build_ecb, requires_iv=False,
                            description="相同明文块产生相同密文块，仅用于兼容", secure=False)
    register_symmetric_mode("CBC", _build_cbc, requires_iv=True,
                            description="需要随机且不可复用的 IV")

    for label, codec in (
        ("UTF-8", "utf-8"),
        ("GBK", "gbk"),
        ("GB18030", "gb18030"),
        ("UTF-16LE", "utf-16-le"),
    ):
        register_text_encoding(label, codec)


_register_defaults()
