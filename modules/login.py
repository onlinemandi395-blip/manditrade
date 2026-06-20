from __future__ import annotations

import streamlit as st

from components.frontend_layer import render_frontend_cta_link, render_frontend_section
from components.html_renderer import render_template


def render_login_page(
    oauth_service,
    translator,
    language_options: list[str],
    current_language: str,
    set_language,
    auth_service=None,
    language_option_labels: dict[str, str] | None = None,
    *,
    status_eyebrow: str = "Sign In",
    status_title: str = "Google access is ready",
    status_body: str = "Use the configured Google account to enter your workspace.",
    access_title: str = "Shared access",
    access_body: str = "All roles enter through the same secure sign-in and are routed by their account permissions.",
    show_unknown_user_note: bool = True,
) -> None:
    auth_config = auth_service.get_auth_config() if auth_service is not None else {}
    login_config = auth_config.get("login_page", {})

    title = translator.t(login_config.get("title_key", "auth.title"))
    subtitle = translator.t(login_config.get("subtitle_key", "auth.subtitle"))
    feature_rows = login_config.get("features", []) or [
        {"icon": "[MJ]", "label_key": "login.feature.merchants"},
        {"icon": "[CB]", "label_key": "login.feature.client_buyers"},
        {"icon": "[MK]", "label_key": "login.feature.marketplace"},
    ]
    feature_markup = "".join(
        f"<span class='mt-badge'>{item.get('icon', '')} {translator.t(item.get('label_key', ''))}</span>"
        for item in feature_rows
    )
    render_template(
        "login_console.html",
        brand_label="MandiTrade",
        title=title,
        subtitle=subtitle,
        feature_markup=feature_markup,
        status_eyebrow=status_eyebrow,
        status_title=status_title,
        status_body=status_body,
        access_title=access_title,
        access_body=access_body,
    )
    render_frontend_section(
        eyebrow="Access",
        title="Open your workspace",
        subtitle="Choose your language and continue with Google to enter the platform.",
    )

    if login_config.get("show_language_selector", auth_service is not None):
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

    provider = None
    if auth_service is not None:
        provider = next((provider for provider in auth_service.get_enabled_providers() if provider.get("provider_id") == "google"), None)
    label = "Continue with Google"
    if provider:
        label = f"{provider.get('icon', '')} {translator.t(provider.get('label_key', 'auth.login_google'))}".strip()
    render_frontend_cta_link(label=label, href=oauth_service.get_authorize_url())

    if show_unknown_user_note:
        st.info(translator.t("auth.unknown_user_note"))
