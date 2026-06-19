from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template


def render_login_page(
    auth_service,
    oauth_service,
    translator,
    language_options: list[str],
    current_language: str,
    set_language,
    language_option_labels: dict[str, str] | None = None,
) -> None:
    auth_config = auth_service.get_auth_config()
    login_config = auth_config.get("login_page", {})

    title = translator.t(login_config.get("title_key", "auth.title"))
    subtitle = translator.t(login_config.get("subtitle_key", "auth.subtitle"))
    render_template("login_hero.html", title=title, subtitle=subtitle)

    feature_rows = login_config.get("features", [])
    if feature_rows:
        feature_markup = "".join(
            f"<span class='mt-badge'>{item.get('icon', '')} {translator.t(item.get('label_key', ''))}</span>"
            for item in feature_rows
        )
        render_template("login_badge_row.html", feature_markup=feature_markup)
    st.caption("Choose your language and continue with Google to open your workspace.")

    if login_config.get("show_language_selector", False):
        selected_language = st.selectbox(
            translator.t("auth.language"),
            options=language_options,
            index=language_options.index(current_language) if current_language in language_options else 0,
            format_func=lambda code: dict(language_option_labels or {}).get(code, str(code or "").upper()),
            key="login_language_selector",
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
