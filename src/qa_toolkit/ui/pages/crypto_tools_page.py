from __future__ import annotations

from datetime import datetime

import streamlit as st

from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button, secondary_action_button
from qa_toolkit.ui.components.status_feedback import render_error_feedback, render_success_feedback
from qa_toolkit.ui.components.tool_page_shell import render_tool_page_hero, render_tool_tips
from qa_toolkit.utils.crypto_tools import (
    HASH_ALGORITHMS,
    base64_decode,
    base64_encode,
    digest_text,
    generate_rsa_keypair,
    hex_decode,
    hex_encode,
    hmac_text,
    html_decode,
    html_encode,
    pbkdf2_derive,
    rsa_decrypt_text,
    rsa_encrypt_text,
    symmetric_decrypt,
    symmetric_encrypt,
    unicode_decode,
    unicode_encode,
    url_decode,
    url_encode,
)


DEFAULT_STATE = {
    "crypto_output_text": "",
    "crypto_output_label": "",
    "crypto_rsa_public_key": "",
    "crypto_rsa_private_key": "",
}

ENCODER_MAPPING = {
    "Base64": {"encode": base64_encode, "decode": base64_decode},
    "URL": {"encode": url_encode, "decode": url_decode},
    "HTML": {"encode": html_encode, "decode": html_decode},
    "Unicode": {"encode": unicode_encode, "decode": unicode_decode},
    "十六进制": {"encode": hex_encode, "decode": hex_decode},
}


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _set_output(label: str, content: str) -> None:
    st.session_state.crypto_output_label = label
    st.session_state.crypto_output_text = content


def _render_output_panel() -> None:
    output_text = st.session_state.crypto_output_text
    if not output_text:
        return

    st.markdown("### 输出结果")
    if st.session_state.crypto_output_label:
        st.caption(st.session_state.crypto_output_label)
    st.code(output_text)
    action_download_button(
        "导出结果",
        data=output_text.encode("utf-8"),
        file_name=f"crypto_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain",
    )


def _render_encoder_tab() -> None:
    st.markdown("### 编码 / 解码")
    tool_name = st.selectbox("选择工具", list(ENCODER_MAPPING.keys()), key="crypto_encoder_tool")
    input_text = st.text_area("输入内容", height=180, key="crypto_encoder_input")

    col1, col2 = st.columns(2)
    with col1:
        if primary_action_button("开始编码", key="crypto_encode"):
            try:
                result = ENCODER_MAPPING[tool_name]["encode"](input_text)
                _set_output(f"{tool_name} 编码结果", result)
            except Exception as exc:
                render_error_feedback(f"{tool_name} 编码失败: {exc}")
    with col2:
        if secondary_action_button("开始解码", key="crypto_decode"):
            try:
                result = ENCODER_MAPPING[tool_name]["decode"](input_text)
                _set_output(f"{tool_name} 解码结果", result)
            except Exception as exc:
                render_error_feedback(f"{tool_name} 解码失败: {exc}")


def _render_hash_tab() -> None:
    digest_subtab, hmac_subtab, pbkdf2_subtab = st.tabs(["摘要", "HMAC", "PBKDF2"])

    with digest_subtab:
        input_text = st.text_area("摘要输入", height=160, key="crypto_digest_input")
        algorithm = st.selectbox("摘要算法", list(HASH_ALGORITHMS.keys()), key="crypto_digest_algorithm")
        if primary_action_button("生成摘要", key="crypto_digest_button"):
            try:
                digest_value = digest_text(input_text, algorithm)
                if algorithm == "MD5":
                    middle_16 = digest_value[8:24]
                    _set_output(
                        "MD5 摘要结果",
                        "\n".join(
                            [
                                f"32位小写: {digest_value}",
                                f"32位大写: {digest_value.upper()}",
                                f"16位小写: {middle_16}",
                                f"16位大写: {middle_16.upper()}",
                            ]
                        ),
                    )
                else:
                    _set_output(f"{algorithm} 摘要结果", digest_value)
            except Exception as exc:
                render_error_feedback(f"{algorithm} 摘要生成失败: {exc}")

    with hmac_subtab:
        input_text = st.text_area("消息内容", height=140, key="crypto_hmac_input")
        key_text = st.text_input("HMAC 密钥", key="crypto_hmac_key", type="password")
        algorithm = st.selectbox("HMAC 算法", list(HASH_ALGORITHMS.keys()), key="crypto_hmac_algorithm")
        if primary_action_button("生成 HMAC", key="crypto_hmac_button"):
            try:
                _set_output(f"HMAC-{algorithm} 结果", hmac_text(input_text, key_text, algorithm))
            except Exception as exc:
                render_error_feedback(f"HMAC 生成失败: {exc}")

    with pbkdf2_subtab:
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("口令", key="crypto_pbkdf2_password", type="password")
            salt = st.text_input("盐值", key="crypto_pbkdf2_salt")
            iterations = st.number_input("迭代次数", min_value=1, value=10000, key="crypto_pbkdf2_iterations")
        with col2:
            key_length = st.number_input("导出长度(字节)", min_value=16, max_value=128, value=32, key="crypto_pbkdf2_length")
            algorithm = st.selectbox("KDF 算法", ["SHA1", "SHA256", "SHA384", "SHA512"], key="crypto_pbkdf2_algorithm")
            output_format = st.selectbox("输出格式", ["hex", "base64"], key="crypto_pbkdf2_output")
        if primary_action_button("生成派生密钥", key="crypto_pbkdf2_button"):
            try:
                result = pbkdf2_derive(password, salt, iterations, key_length, algorithm, output_format)
                _set_output("PBKDF2 派生结果", result)
            except Exception as exc:
                render_error_feedback(f"PBKDF2 派生失败: {exc}")


def _render_symmetric_tab() -> None:
    st.markdown("### 对称加解密")
    col1, col2, col3 = st.columns(3)
    with col1:
        algorithm = st.selectbox("算法", ["AES", "DES", "3DES"], key="crypto_sym_algorithm")
    with col2:
        mode = st.selectbox("模式", ["ECB", "CBC"], key="crypto_sym_mode")
    with col3:
        output_format = st.selectbox("密文格式", ["base64", "hex"], key="crypto_sym_output_format")

    field_col1, field_col2 = st.columns(2)
    with field_col1:
        key_text = st.text_area("密钥", height=100, key="crypto_sym_key")
        key_format = st.selectbox("密钥格式", ["text", "hex", "base64"], key="crypto_sym_key_format")
    with field_col2:
        iv_text = st.text_area("IV / 偏移量", height=100, key="crypto_sym_iv", disabled=mode == "ECB")
        iv_format = st.selectbox("IV 格式", ["text", "hex", "base64"], key="crypto_sym_iv_format", disabled=mode == "ECB")

    input_text = st.text_area("输入内容", height=180, key="crypto_sym_input")
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if primary_action_button("开始加密", key="crypto_sym_encrypt"):
            try:
                result = symmetric_encrypt(
                    plaintext=input_text,
                    algorithm=algorithm,
                    mode=mode,
                    key=key_text,
                    key_format=key_format,
                    iv=iv_text,
                    iv_format=iv_format,
                    output_format=output_format,
                )
                _set_output(f"{algorithm}-{mode} 加密结果", result)
            except Exception as exc:
                render_error_feedback(f"{algorithm}-{mode} 加密失败: {exc}")
    with action_col2:
        if secondary_action_button("开始解密", key="crypto_sym_decrypt"):
            try:
                result = symmetric_decrypt(
                    ciphertext=input_text,
                    algorithm=algorithm,
                    mode=mode,
                    key=key_text,
                    key_format=key_format,
                    iv=iv_text,
                    iv_format=iv_format,
                    input_format=output_format,
                )
                _set_output(f"{algorithm}-{mode} 解密结果", result)
            except Exception as exc:
                render_error_feedback(f"{algorithm}-{mode} 解密失败: {exc}")

    st.caption("常见密钥长度: AES 16/24/32 字节，DES 8 字节，3DES 16/24 字节；CBC 模式下还需要对应长度的 IV。")


def _render_rsa_tab() -> None:
    key_col1, key_col2 = st.columns([1, 2])
    with key_col1:
        key_size = st.selectbox("密钥长度", [2048, 3072, 4096], key="crypto_rsa_key_size")
        passphrase = st.text_input("私钥口令（可选）", key="crypto_rsa_passphrase", type="password")
        if primary_action_button("生成 RSA 密钥对", key="crypto_rsa_generate"):
            try:
                keypair = generate_rsa_keypair(key_size=key_size, passphrase=passphrase)
                st.session_state.crypto_rsa_public_key = keypair["public_key"]
                st.session_state.crypto_rsa_private_key = keypair["private_key"]
                render_success_feedback("RSA 密钥对已生成，公钥和私钥已经回填到下方文本框。")
            except Exception as exc:
                render_error_feedback(f"RSA 密钥生成失败: {exc}")
    with key_col2:
        st.text_area("公钥", height=160, key="crypto_rsa_public_key")
        st.text_area("私钥", height=200, key="crypto_rsa_private_key")

    input_text = st.text_area("待处理内容", height=160, key="crypto_rsa_input")
    cipher_format = st.selectbox("密文格式", ["base64", "hex"], key="crypto_rsa_format")
    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if primary_action_button("开始公钥加密", key="crypto_rsa_encrypt"):
            try:
                result = rsa_encrypt_text(input_text, st.session_state.crypto_rsa_public_key, cipher_format)
                _set_output("RSA 加密结果", result)
            except Exception as exc:
                render_error_feedback(f"RSA 公钥加密失败: {exc}")
    with action_col2:
        if secondary_action_button("开始私钥解密", key="crypto_rsa_decrypt"):
            try:
                result = rsa_decrypt_text(
                    input_text,
                    st.session_state.crypto_rsa_private_key,
                    passphrase=st.session_state.crypto_rsa_passphrase,
                    input_format=cipher_format,
                )
                _set_output("RSA 解密结果", result)
            except Exception as exc:
                render_error_feedback(f"RSA 私钥解密失败: {exc}")

    st.caption("RSA 更适合短文本、密钥交换和签名场景。超长内容建议先做对称加密，再用 RSA 保护对称密钥。")


def render_crypto_tools_page() -> None:
    _ensure_defaults()

    show_doc("crypto_tools")
    render_tool_page_hero(
        "🔐",
        "加密 / 解密工具集",
        "统一处理编码转换、摘要派生、对称加解密和 RSA 密钥操作，适合接口联调、签名排查和测试数据加工。",
        tags=["编码转换", "PBKDF2", "AES / DES / 3DES", "RSA"],
        accent="#b45309",
    )
    render_tool_tips(
        "使用建议",
        [
            "摘要和编码工具适合做签名校验、回调验签和接口参数排查。",
            "对称加解密优先确认密钥长度、模式和 IV 格式，错误大多出在这三个参数。",
            "RSA 更适合短文本和密钥封装，长文本建议先做对称加密。",
        ],
    )

    encoder_tab, hash_tab, symmetric_tab, rsa_tab = st.tabs(["编码转换", "摘要与派生", "对称加解密", "RSA 工具"])

    with encoder_tab:
        _render_encoder_tab()
    with hash_tab:
        _render_hash_tab()
    with symmetric_tab:
        _render_symmetric_tab()
    with rsa_tab:
        _render_rsa_tab()

    _render_output_panel()
