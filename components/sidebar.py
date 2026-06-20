from __future__ import annotations

from html import escape

import streamlit as st

from components.html_renderer import render_template


ICON_MAP = {
    "[DB]": "\U0001F4CA",
    "[PD]": "\U0001F4E6",
    "[MK]": "\U0001F6CD\ufe0f",
    "[MT]": "\U0001F3ED",
    "[OR]": "\U0001F9FE",
    "[PF]": "\U0001F464",
    "[PY]": "\U0001F4B3",
    "[SH]": "\U0001F69A",
    "[LG]": "\U0001F4DA",
    "[CD]": "\u2705",
    "[NT]": "\U0001F514",
    "[CF]": "\u2699\ufe0f",
    "[HL]": "\U0001FA7A",
}


def _resolve_icon(icon: str) -> str:
    normalized = str(icon or "").strip()
    return ICON_MAP.get(normalized, normalized)


def render_sidebar(
    navigation_items: list[dict],
    selected_route: str,
    user: dict | None = None,
    role_label: str = "",
    theme_service=None,
    language_options: list[str] | None = None,
    language_option_labels: dict[str, str] | None = None,
    current_language: str = "en",
    language_label: str = "Language",
    set_language=None,
    role_switcher_options: list[dict] | None = None,
    current_role_view: str = "__self__",
) -> tuple[str, str]:
    chosen = selected_route
    selected_view = str(current_role_view or "__self__")
    with st.sidebar:
        render_template("sidebar_brand.html")
        if user:
            photo_url = str(user.get("photo_url", "") or "").strip()
            if photo_url:
                st.image(photo_url, width=64)
            display_name = str(user.get("display_name", "") or "").strip()
            email = str(user.get("email", "") or "").strip()
            render_template(
                "sidebar_user_card.html",
                name_html=f"<div class='mt-sidebar-user__name'>{escape(display_name)}</div>" if display_name else "",
                email_html=f"<div class='mt-sidebar-user__email'>{escape(email)}</div>" if email else "",
                role_html=f"<div class='mt-sidebar-user__role'>{escape(role_label)}</div>" if role_label else "",
            )
        if language_options and set_language is not None:
            normalized_options = [str(option or "").strip().lower() for option in language_options if str(option or "").strip()]
            normalized_current = str(current_language or "en").strip().lower() or "en"
            if normalized_options:
                render_template("sidebar_section_label.html", label="Language")
                language_choice = st.selectbox(
                    language_label,
                    options=normalized_options,
                    index=normalized_options.index(normalized_current) if normalized_current in normalized_options else 0,
                    format_func=lambda code: dict(language_option_labels or {}).get(code, str(code or "").upper()),
                    key="sidebar_language_choice",
                )
                if language_choice != normalized_current:
                    set_language(language_choice)
                    st.rerun()
        if role_switcher_options:
            render_template("sidebar_section_label.html", label="Role View")
            selected_view = st.selectbox(
                "Role View",
                options=[str(option.get("value", "__self__")) for option in role_switcher_options],
                index=next(
                    (
                        idx
                        for idx, option in enumerate(role_switcher_options)
                        if str(option.get("value", "__self__")) == str(current_role_view or "__self__")
                    ),
                    0,
                ),
                format_func=lambda value: next(
                    (
                        str(option.get("label", "Role View"))
                        for option in role_switcher_options
                        if str(option.get("value", "__self__")) == str(value)
                    ),
                    "Role View",
                ),
                key="sidebar_role_view_choice",
            )
        if theme_service is not None:
            backgrounds = theme_service.list_available_backgrounds()
            if backgrounds:
                render_template("sidebar_section_label.html", label="Theme")
                options = [{"label": "Default Theme", "value": ""}] + [
                    {"label": row.get("file_name", row.get("file_id", "Theme")), "value": row.get("file_id", "")}
                    for row in backgrounds
                ]
                selected_background = theme_service.get_selected_background()
                selected_value = selected_background.get("file_id", "") if selected_background.get("file_id") else ""
                theme_choice = st.selectbox(
                    "Theme",
                    options=[row["value"] for row in options],
                    format_func=lambda value: next((row["label"] for row in options if row["value"] == value), "Default Theme"),
                    index=next((idx for idx, row in enumerate(options) if row["value"] == selected_value), 0),
                    key="sidebar_theme_choice",
                )
                if theme_choice != selected_value:
                    chosen_theme = next((row for row in backgrounds if row.get("file_id", "") == theme_choice), None)
                    if theme_choice:
                        theme_service.set_selected_background(chosen_theme)
                    else:
                        theme_service.clear_selected_background()
                    theme_service.clear_theme_cache()
                    st.rerun()
        render_template("sidebar_section_label.html", label="Navigation")
        for item in navigation_items:
            icon = _resolve_icon(str(item.get("icon", "")))
            label = f"{icon} {item.get('label', item.get('route', ''))}".strip()
            route = str(item.get("route", "dashboard"))
            if st.button(
                label,
                key=f"sidebar_{route}",
                use_container_width=True,
                type="primary" if route == selected_route else "secondary",
            ):
                chosen = route
    return chosen, selected_view
