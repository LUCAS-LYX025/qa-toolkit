from __future__ import annotations

import streamlit as st

from qa_toolkit.core.crypto_registry import (
    get_encoders,
    get_hash_algorithms,
    get_registry_summary,
    get_symmetric_algorithms,
    get_symmetric_modes,
    get_text_encodings,
)
from qa_toolkit.support.documentation import show_doc
from qa_toolkit.ui.components.action_controls import action_download_button, primary_action_button, secondary_action_button
from qa_toolkit.ui.components.status_feedback import (
    render_error_feedback,
    render_info_feedback,
    render_success_feedback,
)
from qa_toolkit.ui.components.tool_page_shell import render_tool_page_hero, render_tool_tips
from qa_toolkit.utils.crypto_tools import (
    MAX_PBKDF2_ITERATIONS,
    build_crypto_signature,
    build_output_filename,
    describe_key_requirements,
    digest_text,
    format_crypto_error,
    generate_random_key_material,
    generate_rsa_keypair,
    hmac_text,
    key_material_status,
    pbkdf2_derive,
    rsa_decrypt_text,
    rsa_encrypt_text,
    rsa_max_plaintext_bytes,
    symmetric_decrypt,
    symmetric_encrypt,
)

DEFAULT_STATE = {
    "crypto_output_text": "",
    "crypto_output_label": "",
    "crypto_output_source": "",
    "crypto_output_signature": "",
    "crypto_rsa_public_key": "",
    "crypto_rsa_private_key": "",
    "crypto_rsa_show_private": False,
    "crypto_sym_mode": "CBC",
}


def _ensure_defaults() -> None:
    for key, value in DEFAULT_STATE.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _codec(key: str) -> str:
    return get_text_encodings().get(st.session_state.get(key), "utf-8")


def _current_signature(source: str) -> str:
    """根据当前输入计算签名，用于判定展示的结果是否已经过期。"""
    state = st.session_state
    if source == "encoder":
        payload = {
            "source": source,
            "tool": state.get("crypto_encoder_tool"),
            "text": state.get("crypto_encoder_input"),
            "encoding": state.get("crypto_encoder_encoding"),
        }
    elif source == "digest":
        payload = {
            "source": source,
            "text": state.get("crypto_digest_input"),
            "algorithm": state.get("crypto_digest_algorithm"),
            "encoding": state.get("crypto_digest_encoding"),
        }
    elif source == "hmac":
        payload = {
            "source": source,
            "text": state.get("crypto_hmac_input"),
            "secret": state.get("crypto_hmac_key"),
            "algorithm": state.get("crypto_hmac_algorithm"),
            "encoding": state.get("crypto_hmac_encoding"),
        }
    elif source == "pbkdf2":
        payload = {
            "source": source,
            "password": state.get("crypto_pbkdf2_password"),
            "salt": state.get("crypto_pbkdf2_salt"),
            "salt_format": state.get("crypto_pbkdf2_salt_format"),
            "iterations": state.get("crypto_pbkdf2_iterations"),
            "length": state.get("crypto_pbkdf2_length"),
            "algorithm": state.get("crypto_pbkdf2_algorithm"),
            "output": state.get("crypto_pbkdf2_output"),
        }
    elif source == "symmetric":
        payload = {
            "source": source,
            "text": state.get("crypto_sym_input"),
            "algorithm": state.get("crypto_sym_algorithm"),
            "mode": state.get("crypto_sym_mode"),
            "key": state.get("crypto_sym_key"),
            "key_format": state.get("crypto_sym_key_format"),
            "iv": state.get("crypto_sym_iv"),
            "iv_format": state.get("crypto_sym_iv_format"),
            "output": state.get("crypto_sym_output_format"),
        }
    elif source == "rsa":
        payload = {
            "source": source,
            "text": state.get("crypto_rsa_input"),
            "public": state.get("crypto_rsa_public_key"),
            "private": state.get("crypto_rsa_private_key"),
            "passphrase": state.get("crypto_rsa_passphrase"),
            "format": state.get("crypto_rsa_format"),
        }
    else:
        payload = {"source": source}
    return build_crypto_signature(payload)


def _set_output(source: str, label: str, content: str) -> None:
    st.session_state.crypto_output_source = source
    st.session_state.crypto_output_label = label
    st.session_state.crypto_output_text = content
    st.session_state.crypto_output_signature = _current_signature(source)


def _render_output_panel(source: str) -> None:
    if st.session_state.crypto_output_source != source:
        return

    signature = st.session_state.crypto_output_signature
    if signature and signature != _current_signature(source):
        render_info_feedback("输入已变更，请重新点击对应的操作按钮。", title="结果已过期")
        return

    output_text = st.session_state.crypto_output_text
    label = st.session_state.crypto_output_label
    st.markdown("### 输出结果")
    if label:
        st.caption(label)
    if output_text:
        st.code(output_text)
    else:
        render_info_feedback("本次操作成功，但输出为空字符串。", title="输出为空")

    action_download_button(
        "导出结果",
        data=output_text.encode("utf-8"),
        file_name=build_output_filename(source, label),
        mime="text/plain",
    )


def _render_encoder_tab() -> None:
    st.markdown("### 编码 / 解码")
    encoders = get_encoders()
    tool_name = st.selectbox("选择工具", list(encoders.keys()), key="crypto_encoder_tool")
    encoding_label = st.selectbox("字符编码", list(get_text_encodings().keys()), key="crypto_encoder_encoding")
    input_text = st.text_area("输入内容", height=180, key="crypto_encoder_input")

    col1, col2 = st.columns(2)
    with col1:
        if primary_action_button("开始编码", key="crypto_encode"):
            try:
                result = encoders[tool_name].encode(input_text, _codec("crypto_encoder_encoding"))
                _set_output("encoder", f"{tool_name} 编码结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, f"{tool_name} 编码"))
    with col2:
        if secondary_action_button("开始解码", key="crypto_decode"):
            try:
                result = encoders[tool_name].decode(input_text, _codec("crypto_encoder_encoding"))
                _set_output("encoder", f"{tool_name} 解码结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, f"{tool_name} 解码"))

    st.caption(
        f"Base64 解码兼容换行与 URL-safe 字符；URL 解码会把 `+` 还原为空格。"
        f"当前注册编码器：{len(encoders)} 种。"
    )
    _render_output_panel("encoder")


def _render_hash_tab() -> None:
    digest_subtab, hmac_subtab, pbkdf2_subtab = st.tabs(["摘要", "HMAC", "PBKDF2"])

    with digest_subtab:
        input_text = st.text_area("摘要输入", height=160, key="crypto_digest_input")
        algorithm = st.selectbox("摘要算法", list(get_hash_algorithms().keys()), key="crypto_digest_algorithm")
        encoding = st.selectbox("字符编码", list(get_text_encodings().keys()), key="crypto_digest_encoding")
        if algorithm in {"MD5", "SHA1"}:
            render_info_feedback(
                f"{algorithm} 仅适合兼容性校验或文件指纹，不可用于口令存储与安全签名；"
                "安全场景请选择 SHA256 及以上，或使用 PBKDF2 派生。",
                title="算法安全性提示",
            )
        if primary_action_button("生成摘要", key="crypto_digest_button"):
            try:
                digest_value = digest_text(
                    input_text, algorithm, encoding=_codec("crypto_digest_encoding")
                )
                if algorithm == "MD5":
                    middle_16 = digest_value[8:24]
                    _set_output(
                        "digest",
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
                    _set_output("digest", f"{algorithm} 摘要结果", digest_value)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, f"{algorithm} 摘要生成"))
        _render_output_panel("digest")

    with hmac_subtab:
        input_text = st.text_area("消息内容", height=140, key="crypto_hmac_input")
        key_text = st.text_input("HMAC 密钥", key="crypto_hmac_key", type="password")
        algorithm = st.selectbox("HMAC 算法", list(get_hash_algorithms().keys()), key="crypto_hmac_algorithm")
        encoding = st.selectbox("字符编码", list(get_text_encodings().keys()), key="crypto_hmac_encoding")
        if primary_action_button("生成 HMAC", key="crypto_hmac_button"):
            try:
                result = hmac_text(
                    input_text, key_text, algorithm,
                    encoding=_codec("crypto_hmac_encoding"),
                )
                _set_output("hmac", f"HMAC-{algorithm} 结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, "HMAC 生成"))
        _render_output_panel("hmac")

    with pbkdf2_subtab:
        col1, col2 = st.columns(2)
        with col1:
            password = st.text_input("口令", key="crypto_pbkdf2_password", type="password")
            salt = st.text_input("盐值", key="crypto_pbkdf2_salt")
            salt_format = st.selectbox(
                "盐值格式", ["text", "hex", "base64"], key="crypto_pbkdf2_salt_format"
            )
            iterations = st.number_input(
                "迭代次数", min_value=1, max_value=MAX_PBKDF2_ITERATIONS,
                value=10000, key="crypto_pbkdf2_iterations",
            )
        with col2:
            key_length = st.number_input(
                "导出长度(字节)", min_value=16, max_value=128, value=32,
                key="crypto_pbkdf2_length",
            )
            algorithm = st.selectbox("KDF 算法", ["SHA1", "SHA256", "SHA384", "SHA512"], key="crypto_pbkdf2_algorithm")
            output_format = st.selectbox("输出格式", ["hex", "base64"], key="crypto_pbkdf2_output")
        st.caption(f"迭代次数上限 {MAX_PBKDF2_ITERATIONS}，避免误填超大值导致页面无响应。")
        if primary_action_button("生成派生密钥", key="crypto_pbkdf2_button"):
            try:
                result = pbkdf2_derive(
                    password, salt, iterations, key_length, algorithm, output_format,
                    salt_format=salt_format,
                )
                label = (
                    f"PBKDF2 派生结果（{algorithm} / 盐格式 {salt_format} / "
                    f"{iterations} 次 / {key_length} 字节）"
                )
                _set_output("pbkdf2", label, result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, "PBKDF2 派生"))
        _render_output_panel("pbkdf2")


def _render_symmetric_tab() -> None:
    st.markdown("### 对称加解密")
    algorithms = get_symmetric_algorithms()
    modes = get_symmetric_modes()
    col1, col2, col3 = st.columns(3)
    with col1:
        algorithm = st.selectbox("算法", list(algorithms.keys()), key="crypto_sym_algorithm")
    with col2:
        mode = st.selectbox("模式", list(modes.keys()), key="crypto_sym_mode")
    with col3:
        output_format = st.selectbox("密文格式", ["base64", "hex"], key="crypto_sym_output_format")

    st.caption(describe_key_requirements(algorithm, mode))
    if not modes[mode].secure:
        render_info_feedback(
            f"{mode} 会让相同明文块产生相同密文块，仅建议用于兼容旧系统；新业务请选择 CBC。",
            title="安全提示",
        )
    if algorithms[algorithm].deprecated:
        render_info_feedback(
            f"{algorithm} 已被现代标准废弃，仅用于复现旧系统问题，不建议在新业务中使用。",
            title="算法兼容性提示",
        )

    field_col1, field_col2 = st.columns(2)
    with field_col1:
        key_text = st.text_area("密钥", height=100, key="crypto_sym_key")
        key_format = st.selectbox("密钥格式", ["text", "base64", "hex"], key="crypto_sym_key_format")
    with field_col2:
        iv_disabled = not modes[mode].requires_iv
        iv_text = st.text_area("IV / 偏移量", height=100, key="crypto_sym_iv", disabled=iv_disabled)
        iv_format = st.selectbox("IV 格式", ["text", "base64", "hex"], key="crypto_sym_iv_format", disabled=iv_disabled)

    status = key_material_status(algorithm, mode, key_text, key_format, iv_text, iv_format)
    key_current = status["key_current"] if status["key_current"] is not None else "解析失败"
    st.caption(
        f"密钥长度：当前 {key_current} 字节 / 支持 {status['key_expected']} 字节 — "
        f"{'符合' if status['key_ok'] else '不符合'}"
    )
    if modes[mode].requires_iv:
        iv_current = status["iv_current"] if status["iv_current"] is not None else "解析失败"
        st.caption(
            f"IV 长度：当前 {iv_current} 字节 / 需要 {status['iv_expected']} 字节 — "
            f"{'符合' if status['iv_ok'] else '不符合'}"
        )
    if secondary_action_button("生成随机密钥与 IV", key="crypto_sym_generate"):
        material = generate_random_key_material(algorithm, mode, key_format, iv_format)
        st.session_state.crypto_sym_key = material["key"]
        st.session_state.crypto_sym_iv = material["iv"]
        st.rerun()

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
                _set_output("symmetric", f"{algorithm}-{mode} 加密结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, f"{algorithm}-{mode} 加密"))
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
                _set_output("symmetric", f"{algorithm}-{mode} 解密结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, f"{algorithm}-{mode} 解密"))

    _render_output_panel("symmetric")


def _render_rsa_tab() -> None:
    key_col1, key_col2 = st.columns([1, 2])
    with key_col1:
        key_size = st.selectbox("密钥长度", [2048, 3072, 4096], key="crypto_rsa_key_size")
        passphrase = st.text_input("私钥口令（可选）", key="crypto_rsa_passphrase", type="password")
        has_keys = bool(
            st.session_state.crypto_rsa_public_key and st.session_state.crypto_rsa_private_key
        )
        st.checkbox("允许覆盖已有密钥", key="crypto_rsa_allow_overwrite", value=False)
        if primary_action_button("生成 RSA 密钥对", key="crypto_rsa_generate"):
            if has_keys and not st.session_state.crypto_rsa_allow_overwrite:
                render_error_feedback("已有公钥/私钥，请先勾选“允许覆盖已有密钥”再生成。")
            else:
                try:
                    keypair = generate_rsa_keypair(key_size=key_size, passphrase=passphrase)
                    st.session_state.crypto_rsa_public_key = keypair["public_key"]
                    st.session_state.crypto_rsa_private_key = keypair["private_key"]
                    render_success_feedback("RSA 密钥对已生成，公钥和私钥已经回填到下方文本框。")
                except Exception as exc:
                    render_error_feedback(format_crypto_error(exc, "RSA 密钥生成"))
    with key_col2:
        st.text_area("公钥", height=160, key="crypto_rsa_public_key")
        if st.session_state.crypto_rsa_show_private:
            st.text_area("私钥", height=200, key="crypto_rsa_private_key")
            if secondary_action_button("隐藏私钥", key="crypto_rsa_hide_private"):
                st.session_state.crypto_rsa_show_private = False
                st.rerun()
        else:
            st.text_input(
                "私钥（已隐藏）", value=st.session_state.crypto_rsa_private_key,
                key="crypto_rsa_private_key_masked", type="password", disabled=True,
            )
            if secondary_action_button("显示私钥", key="crypto_rsa_show_private_button"):
                st.session_state.crypto_rsa_show_private = True
                st.rerun()
        st.caption("私钥默认隐藏，避免共享屏幕或录屏时泄露。")
        col_pub, col_priv = st.columns(2)
        with col_pub:
            action_download_button(
                "下载公钥", data=st.session_state.crypto_rsa_public_key.encode("utf-8"),
                file_name="crypto_rsa_public.pem", mime="application/x-pem-file",
            )
        with col_priv:
            action_download_button(
                "下载私钥", data=st.session_state.crypto_rsa_private_key.encode("utf-8"),
                file_name="crypto_rsa_private.pem", mime="application/x-pem-file",
            )

    input_text = st.text_area("待处理内容", height=160, key="crypto_rsa_input")
    cipher_format = st.selectbox("密文格式", ["base64", "hex"], key="crypto_rsa_format")
    public_key = st.session_state.crypto_rsa_public_key
    if public_key:
        try:
            st.caption(
                f"当前公钥单次可加密上限：{rsa_max_plaintext_bytes(public_key)} 字节"
                "（OAEP / MGF1-SHA256）。"
            )
        except Exception:
            st.caption("当前公钥内容无法解析，请检查 PEM 是否完整。")

    action_col1, action_col2 = st.columns(2)
    with action_col1:
        if primary_action_button("开始公钥加密", key="crypto_rsa_encrypt"):
            try:
                result = rsa_encrypt_text(
                    input_text, public_key, cipher_format
                )
                _set_output("rsa", "RSA 加密结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, "RSA 公钥加密"))
    with action_col2:
        if secondary_action_button("开始私钥解密", key="crypto_rsa_decrypt"):
            try:
                result = rsa_decrypt_text(
                    input_text,
                    st.session_state.crypto_rsa_private_key,
                    passphrase=passphrase,
                    input_format=cipher_format,
                )
                _set_output("rsa", "RSA 解密结果", result)
            except Exception as exc:
                render_error_feedback(format_crypto_error(exc, "RSA 私钥解密"))

    st.caption("RSA 更适合短文本、密钥交换和签名场景。超长内容建议先做对称加密，再用 RSA 保护对称密钥。")
    _render_output_panel("rsa")


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

    summary = get_registry_summary()
    st.caption(
        f"当前扩展点：编码器 {summary['encoders']} 种 / 摘要算法 {summary['hashes']} 种 / "
        f"对称算法 {summary['symmetric']} 种 / 加密模式 {summary['modes']} 种 / "
        f"字符编码 {summary['encodings']} 种。"
    )
