from __future__ import annotations

from typing import Any, Callable, Dict

import streamlit as st

from qa_toolkit.core.env_profile_manager import EnvProfileManager


def _profile_brief(profile: Dict[str, Any]) -> str:
    auth = profile.get("auth", {}) if isinstance(profile.get("auth"), dict) else {}
    auth_mode = str(auth.get("mode") or "none")
    return (
        f"base_url={profile.get('base_url', '') or '-'} | "
        f"timeout={profile.get('timeout_seconds', 30)}s | "
        f"retry={profile.get('retry_times', 0)} | "
        f"verify_ssl={bool(profile.get('verify_ssl', True))} | "
        f"auth={auth_mode}"
    )


def render_env_profile_panel(
    *,
    manager: EnvProfileManager,
    namespace: str,
    panel_key: str,
    capture_state: Callable[[], Dict[str, Any]],
    apply_profile: Callable[[Dict[str, Any]], None],
    title: str = "🌐 环境配置中心",
    description: str = "",
    suggested_name: str = "",
) -> None:
    with st.expander(title, expanded=False):
        if description:
            st.caption(description)
        encryption_issues = manager.list_encryption_issues()
        if encryption_issues:
            joined = "、".join(encryption_issues[:3])
            tail = "..." if len(encryption_issues) > 3 else ""
            st.warning(
                f"检测到密文解密异常配置: {joined}{tail}。请检查环境变量 `QA_TOOLKIT_ENV_PROFILE_KEY` 或本地密钥文件后再保存。",
            )

        profiles = manager.list_profiles()
        profile_names = [item.get("name", "") for item in profiles if item.get("name")]
        active_name = manager.get_active_profile_name(namespace)

        selected_key = f"{panel_key}_selected_name"
        profile_name_key = f"{panel_key}_profile_name"

        if selected_key not in st.session_state or st.session_state[selected_key] not in profile_names:
            if active_name in profile_names:
                st.session_state[selected_key] = active_name
            else:
                st.session_state[selected_key] = profile_names[0] if profile_names else ""

        if profile_name_key not in st.session_state:
            st.session_state[profile_name_key] = st.session_state.get(selected_key, "") or suggested_name

        selected_name = ""
        selected_profile: Dict[str, Any] = {}
        if profile_names:
            selected_name = st.selectbox(
                "已保存配置",
                profile_names,
                key=selected_key,
                help="保存后可在自动化/性能/安全页复用。",
            )
            selected_profile = manager.get_profile(selected_name) or {}
        else:
            st.info("当前没有已保存配置。先填写页面参数后点击“保存当前”。")

        st.text_input(
            "配置名称",
            key=profile_name_key,
            placeholder=suggested_name or "例如: staging-回归",
            help="同名保存会覆盖旧配置。",
        )

        action_col1, action_col2, action_col3, action_col4 = st.columns(4)
        with action_col1:
            apply_clicked = st.button(
                "套用配置",
                key=f"{panel_key}_apply",
                use_container_width=True,
                disabled=not bool(selected_name),
            )
        with action_col2:
            active_clicked = st.button(
                "设为默认",
                key=f"{panel_key}_active",
                use_container_width=True,
                disabled=not bool(selected_name),
            )
        with action_col3:
            save_clicked = st.button(
                "保存当前",
                key=f"{panel_key}_save",
                use_container_width=True,
            )
        with action_col4:
            delete_clicked = st.button(
                "删除配置",
                key=f"{panel_key}_delete",
                use_container_width=True,
                disabled=not bool(selected_name),
            )

        if apply_clicked:
            profile = manager.get_profile(selected_name)
            if not profile:
                st.error("未找到要套用的配置。")
            else:
                try:
                    apply_profile(profile)
                    manager.set_active(selected_name, namespace)
                    st.success(f"已套用配置: {selected_name}")
                except Exception as exc:
                    st.error(f"套用配置失败: {exc}")

        if active_clicked:
            if manager.set_active(selected_name, namespace):
                st.success(f"已设置默认配置: {selected_name}")
            else:
                st.error("设置默认配置失败。")

        if save_clicked:
            target_name = str(st.session_state.get(profile_name_key, "") or "").strip()
            if not target_name:
                st.error("请先填写配置名称。")
            else:
                try:
                    payload = capture_state()
                    saved = manager.upsert_profile(target_name, payload)
                    manager.set_active(saved.get("name", target_name), namespace)
                    st.session_state[selected_key] = saved.get("name", target_name)
                    st.session_state[profile_name_key] = saved.get("name", target_name)
                    st.success(f"配置已保存: {saved.get('name', target_name)}")
                    st.rerun()
                except Exception as exc:
                    st.error(f"保存配置失败: {exc}")

        if delete_clicked:
            if manager.delete_profile(selected_name):
                st.success(f"配置已删除: {selected_name}")
                st.session_state[selected_key] = ""
                st.rerun()
            else:
                st.error("删除配置失败。")

        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.caption(f"当前默认({namespace}): `{active_name or '未设置'}`")
        with info_col2:
            st.caption(f"已保存配置数: `{len(profile_names)}`")

        if selected_profile:
            if selected_profile.get("encryption_error"):
                st.caption("当前配置存在密文解密异常，展示的是降级数据。")
            st.caption(_profile_brief(selected_profile))
