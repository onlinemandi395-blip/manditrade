from __future__ import annotations

from pathlib import Path

import streamlit as st


def render_login_page(auth_service, navigation_service, session_service, translator, language_options: list[str]) -> None:
    auth_config = auth_service.get_auth_config()
    login_config = auth_config.get("login_page", {})

    st.markdown(f"## {translator.t(login_config.get('title_key', 'auth.title'))}")
    st.caption(translator.t(login_config.get("subtitle_key", "auth.subtitle")))

    logo_path = Path(str(login_config.get("logo", "")))
    if logo_path.exists():
        st.image(str(logo_path), width=96)

    feature_rows = login_config.get("features", [])
    if feature_rows:
        feature_markup = "".join(
            f"<span class='mt-badge'>{item.get('icon', '')} {translator.t(item.get('label_key', ''))}</span>"
            for item in feature_rows
        )
        st.markdown(f"<div class='mt-badge-row'>{feature_markup}</div>", unsafe_allow_html=True)

    if login_config.get("show_language_selector", False):
        selected_language = st.selectbox(
            translator.t("auth.language"),
            options=language_options,
            index=language_options.index(session_service.get_language()) if session_service.get_language() in language_options else 0,
        )
        if selected_language != session_service.get_language():
            session_service.set_language(selected_language)
            st.rerun()

    email = st.text_input(
        translator.t("auth.email_label"),
        value=session_service.get_email(),
        placeholder=translator.t("auth.email_placeholder"),
    )

    for provider in auth_service.get_enabled_providers():
        label = f"{provider.get('icon', '')} {translator.t(provider.get('label_key', ''))}".strip()
        if st.button(label, use_container_width=True, key=f"login_provider_{provider.get('provider_id', 'provider')}"):
            if not email.strip():
                st.warning(translator.t("auth.email_required"))
                return
            user = auth_service.login(email, str(provider.get("provider_id", "google")))
            role = str(user.get("role", auth_service.get_unknown_user_default_role()))
            landing_page = navigation_service.get_default_route(role)
            session_service.authenticate(
                {
                    **user,
                    "landing_page": landing_page,
                }
            )
            st.success(translator.t("auth.login_success"))
            st.rerun()

    st.info(translator.t("auth.unknown_user_note"))

    if bool(auth_service.cache_service.get_config("app_config").get("debug_auth", False)):
        with st.expander("Auth Debug", expanded=False):
            st.write(
                {
                    "loaded_users_count": len(auth_service.get_registered_users()),
                    "current_email": email.strip().lower(),
                    "resolved_role": auth_service.resolve_user(email).get("role") if email.strip() else "",
                    "landing_page": navigation_service.get_default_route(auth_service.resolve_user(email).get("role", auth_service.get_unknown_user_default_role())) if email.strip() else "",
                    "filtered_nav_count": len(navigation_service.get_navigation(auth_service.resolve_user(email).get("role", auth_service.get_unknown_user_default_role())) if email.strip() else []),
                }
            )
