from __future__ import annotations

import streamlit as st


def render_login_page(auth_service, oauth_service, translator, language_options: list[str], current_language: str, set_language) -> None:
    auth_config = auth_service.get_auth_config()
    login_config = auth_config.get("login_page", {})

    st.markdown(f"## {translator.t(login_config.get('title_key', 'auth.title'))}")
    st.caption(translator.t(login_config.get("subtitle_key", "auth.subtitle")))

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
            index=language_options.index(current_language) if current_language in language_options else 0,
        )
        if selected_language != current_language:
            set_language(selected_language)
            st.rerun()

    if not oauth_service.is_configured():
        st.error(translator.t("auth.google_not_configured"))
        return

    provider = next((provider for provider in auth_service.get_enabled_providers() if provider.get("provider_id") == "google"), None)
    if provider:
        label = f"{provider.get('icon', '')} {translator.t(provider.get('label_key', 'auth.login_google'))}".strip()
        st.link_button(label, oauth_service.get_authorize_url(), use_container_width=True)

    st.info(translator.t("auth.unknown_user_note"))
