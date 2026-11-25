"""加密/解密工具专项审计回归测试（GitHub issues #209-#227）。"""
import base64
import hashlib
import hmac
import sys
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT_DIR = Path(__file__).resolve().parents[1]
SRC_DIR = ROOT_DIR / "src"
sys.path.insert(0, str(SRC_DIR))

from qa_toolkit.core.crypto_registry import (
    HashSpec,
    get_hash_algorithms,
    get_registry_summary,
    register_hash,
)
from qa_toolkit.utils.crypto_tools import (
    MAX_PBKDF2_ITERATIONS,
    base64_decode,
    base64_encode,
    build_crypto_signature,
    build_output_filename,
    describe_key_requirements,
    digest_text,
    format_crypto_error,
    generate_random_key_material,
    generate_rsa_keypair,
    get_encoder,
    get_encoders,
    hex_decode,
    hex_encode,
    hmac_text,
    key_material_status,
    pbkdf2_derive,
    rsa_encrypt_text,
    rsa_max_plaintext_bytes,
    symmetric_decrypt,
    symmetric_encrypt,
    unicode_decode,
    unicode_encode,
    url_decode,
    url_encode,
)

PAGE_SCRIPT = f"""
import sys
sys.path.insert(0, {str(SRC_DIR)!r})
from qa_toolkit.ui.pages.crypto_tools_page import render_crypto_tools_page
render_crypto_tools_page()
"""


def _app() -> AppTest:
    return AppTest.from_string(PAGE_SCRIPT, default_timeout=15).run()


def _no_exception(app: AppTest) -> None:
    assert not app.exception, [item.value for item in app.exception]


def _markdown_text(app: AppTest) -> str:
    return "\n".join(item.value for item in app.markdown)


def _caption_text(app: AppTest) -> str:
    return "\n".join(item.value for item in app.caption)


# #209 / #210 Base64 空白与 URL-safe
def test_base64_decode_accepts_wrapped_and_urlsafe_values():
    payload = "接口联调测试数据".encode("utf-8")
    standard = base64.b64encode(payload).decode("ascii")
    wrapped = "\n".join(standard[i:i + 8] for i in range(0, len(standard), 8))
    assert base64_decode(wrapped) == "接口联调测试数据"

    urlsafe = base64.urlsafe_b64encode(payload).decode("ascii")
    assert "-" in urlsafe or "_" in urlsafe or "=" in urlsafe
    assert base64_decode(urlsafe) == "接口联调测试数据"
    assert base64_encode("接口联调测试数据", urlsafe=True) == urlsafe


# #211 表单编码的加号
def test_url_decode_restores_plus_as_space():
    assert url_decode("q=hello+world") == "q=hello world"
    assert url_decode("q=hello%2Bworld") == "q=hello+world"
    assert url_encode("a b/c?") == "a%20b%2Fc%3F"


# #212 Unicode 解码对原文给出明确错误
def test_unicode_decode_rejects_plain_text_and_roundtrips_escapes():
    with pytest.raises(ValueError, match="未检测到 Unicode 转义序列"):
        unicode_decode("中文原文")
    assert unicode_encode("中文") == "\\u4e2d\\u6587"
    assert unicode_decode("\\u4e2d\\u6587") == "中文"
    assert unicode_decode(unicode_encode("😀")) == "😀"


# #213 十六进制支持任意二进制
def test_hex_roundtrip_supports_arbitrary_bytes_and_output_formats():
    binary = bytes(range(0x80, 0xa0))
    assert hex_encode(binary) == binary.hex()
    assert hex_decode(binary.hex(), output_format="hex") == binary.hex()
    assert hex_decode(binary.hex(), output_format="base64") == base64.b64encode(binary).decode()
    with pytest.raises(ValueError, match="无法按 utf-8 解释"):
        hex_decode(binary.hex())


# #214 常见字符编码可选
def test_character_encodings_change_digest_and_base64():
    gbk_bytes = "中文".encode("gbk")
    encoded = base64.b64encode(gbk_bytes).decode("ascii")
    assert base64_decode(encoded, encoding="gbk") == "中文"
    assert digest_text("中文", "MD5", encoding="gbk") == hashlib.md5(gbk_bytes).hexdigest()
    assert digest_text("中文", "MD5") == hashlib.md5("中文".encode("utf-8")).hexdigest()
    assert hmac_text("中文", "key", "SHA256", encoding="gbk") == hmac.new(
        b"key", gbk_bytes, hashlib.sha256
    ).hexdigest()


# #215 PBKDF2 迭代上限
def test_pbkdf2_iteration_cap_prevents_runaway_computation():
    with pytest.raises(ValueError, match="迭代次数需在 1 至"):
        pbkdf2_derive("p", "s", 10 ** 9, 32, "SHA256")
    assert len(pbkdf2_derive("p", "s", 1000, 32, "SHA256")) == 64
    assert MAX_PBKDF2_ITERATIONS == 10_000_000


# #216 盐值格式与参数回显
def test_pbkdf2_accepts_hex_and_base64_salt():
    expected = pbkdf2_derive("p", "00112233", 1000, 16, "SHA256", salt_format="hex")
    actual = pbkdf2_derive("p", base64.b64encode(bytes.fromhex("00112233")).decode(),
                           1000, 16, "SHA256", salt_format="base64")
    assert expected == actual
    assert expected != pbkdf2_derive("p", "00112233", 1000, 16, "SHA256")


# #217 #218 #223 页面结果签名、空输出、跨 Tab 隔离
def test_app_result_expires_and_empty_output_is_visible():
    app = _app()
    _no_exception(app)
    assert app.session_state.crypto_sym_mode == "CBC"

    app.selectbox(key="crypto_encoder_tool").set_value("Base64").run()
    app.text_area(key="crypto_encoder_input").set_value("hello").run()
    app.button(key="crypto_encode").click().run()
    _no_exception(app)
    assert app.session_state.crypto_output_text == "aGVsbG8="
    assert app.session_state.crypto_output_source == "encoder"

    app.text_area(key="crypto_encoder_input").set_value("world").run()
    assert "结果已过期" in _markdown_text(app)
    assert "### 输出结果" not in _markdown_text(app)

    app.selectbox(key="crypto_encoder_tool").set_value("URL").run()
    app.text_area(key="crypto_encoder_input").set_value("").run()
    app.button(key="crypto_encode").click().run()
    assert "输出为空" in _markdown_text(app)

    app.session_state.crypto_output_source = "symmetric"
    app.run()
    assert "### 输出结果" not in _markdown_text(app)


# #219 RSA 长度限制
def test_rsa_plaintext_limit_is_explicit():
    keypair = generate_rsa_keypair(2048)
    limit = rsa_max_plaintext_bytes(keypair["public_key"])
    assert limit == 190
    with pytest.raises(ValueError, match="上限 190 字节"):
        rsa_encrypt_text("x" * 300, keypair["public_key"])
    assert rsa_encrypt_text("短文本", keypair["public_key"])


# #220 覆盖密钥需确认
def test_app_rsa_overwrite_requires_explicit_checkbox():
    app = _app()
    _no_exception(app)
    app.text_area(key="crypto_rsa_public_key").set_value("MY-PUBLIC").run()
    app.session_state.crypto_rsa_private_key = "MY-PRIVATE"
    app.button(key="crypto_rsa_generate").click().run()
    assert app.session_state.crypto_rsa_public_key == "MY-PUBLIC"
    assert "允许覆盖已有密钥" in _markdown_text(app)

    app.checkbox(key="crypto_rsa_allow_overwrite").set_value(True).run()
    app.button(key="crypto_rsa_generate").click().run()
    assert "BEGIN PUBLIC KEY" in app.session_state.crypto_rsa_public_key
    _no_exception(app)


# #221 默认 CBC 与安全提示
def test_default_mode_is_cbc_with_requirements_hint():
    assert "CBC" in describe_key_requirements("AES", "CBC")
    assert "不需要 IV" in describe_key_requirements("AES", "ECB")
    app = _app()
    _no_exception(app)
    assert app.session_state.crypto_sym_mode == "CBC"
    assert "AES 密钥长度支持" in _caption_text(app)
    app.selectbox(key="crypto_sym_mode").set_value("ECB").run()
    assert "相同明文块产生相同密文块" in _markdown_text(app)  # ECB 可选但带风险提示


# #222 中文错误诊断
def test_crypto_errors_are_actionable():
    message = format_crypto_error(ValueError("Base64 输入无效: Non-base64 digit found"), "AES-CBC 解密")
    assert "密文不是合法的 Base64" in message
    padded = format_crypto_error(ValueError("Padding is incorrect."), "AES-CBC 解密")
    assert "密钥、IV、模式" in padded
    long_text = format_crypto_error(
        ValueError("明文长度 300 字节超过 2048 位 RSA (OAEP-SHA256) 的上限 190 字节"), "RSA 加密"
    )
    assert "明文长度 300 字节" in long_text


# #224 注册式扩展点
def test_registry_extension_points_are_usable():
    before = get_registry_summary()
    assert before["encoders"] >= 8
    assert "Base64 (URL-safe)" in get_encoders()
    assert get_encoder("十六进制 → Base64").decode("fffb", "utf-8").startswith("//")

    register_hash("TEST-SHA256", lambda: hashlib.sha256(), description="测试用", replace=True)
    assert "TEST-SHA256" in get_hash_algorithms()
    assert digest_text("abc", "TEST-SHA256") == hashlib.sha256(b"abc").hexdigest()
    assert get_registry_summary()["hashes"] == before["hashes"] + 1


# #225 密钥/IV 实时校验与随机生成
def test_key_material_status_and_generation():
    status = key_material_status("AES", "CBC", "0123456789abcdef", "text", "abcdefghijklmnop", "text")
    assert status["key_ok"] and status["iv_ok"]
    assert status["key_current"] == 16 and status["iv_current"] == 16

    bad = key_material_status("AES", "CBC", "short", "text", "", "text")
    assert not bad["key_ok"] and not bad["iv_ok"]

    material = generate_random_key_material("AES", "CBC", "base64", "base64")
    generated = key_material_status("AES", "CBC", material["key"], "base64", material["iv"], "base64")
    assert generated["key_ok"] and generated["iv_ok"]


# #226 私钥默认隐藏与单独导出
def test_app_private_key_hidden_by_default_and_downloads_available():
    app = _app()
    _no_exception(app)
    assert app.session_state.crypto_rsa_show_private is False
    assert app.text_input(key="crypto_rsa_private_key_masked").value == ""
    assert "私钥默认隐藏" in _caption_text(app)
    app.button(key="crypto_rsa_show_private_button").click().run()
    assert app.session_state.crypto_rsa_show_private is True
    assert app.text_area(key="crypto_rsa_private_key") is not None
    page_source = (ROOT_DIR / "src/qa_toolkit/ui/pages/crypto_tools_page.py").read_text(encoding="utf-8")
    assert '"下载公钥"' in page_source and '"下载私钥"' in page_source


# #227 弱摘要算法提示
def test_app_warns_about_weak_digests():
    app = _app()
    _no_exception(app)
    app.selectbox(key="crypto_digest_algorithm").set_value("MD5").run()
    assert "算法安全性提示" in _markdown_text(app)
    app.selectbox(key="crypto_digest_algorithm").set_value("SHA256").run()
    assert "算法安全性提示" not in _markdown_text(app)


# 通用回归
def test_symmetric_cbc_roundtrip_still_works():
    data = {"plaintext": "加密/解密回归 😀", "algorithm": "AES", "mode": "CBC",
            "key": "0123456789abcdef", "key_format": "text",
            "iv": "abcdefghijklmnop", "iv_format": "text"}
    ciphertext = symmetric_encrypt(output_format="base64", **data)
    assert symmetric_decrypt(ciphertext=ciphertext, input_format="base64", **{
        k: v for k, v in data.items() if k != "plaintext"
    }) == data["plaintext"]


def test_output_filename_and_signature_are_deterministic():
    name = build_output_filename("symmetric", "AES-CBC 解密结果")
    assert name.startswith("crypto_symmetric_AES-CBC")
    assert name.endswith(".txt")
    assert build_crypto_signature({"a": 1}) == build_crypto_signature({"a": 1})
    assert build_crypto_signature({"a": 1}) != build_crypto_signature({"a": 2})
