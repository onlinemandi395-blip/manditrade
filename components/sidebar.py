from __future__ import annotations

import streamlit as st


ICON_MAP = {
    "[DB]": "\U0001F4CA",
    "[PD]": "\U0001F4E6",
    "[MK]": "\U0001F6CD\ufe0f",
    "[MT]": "\U0001F3ED",
    "[OR]": "\U0001F9FE",
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
    current_language: str = "en",
    language_label: str = "Language",
    set_language=None,
) -> str:
    chosen = selected_route
    with st.sidebar:
        if user:
            photo_url = str(user.get("photo_url", "") or "").strip()
            if photo_url:
                st.image(photo_url, width=64)
            display_name = str(user.get("display_name", "") or "").strip()
            email = str(user.get("email", "") or "").strip()
            if display_name:
                st.markdown(f"**{display_name}**")
            if email:
                st.caption(email)
            if role_label:
                st.caption(role_label)
        if language_options and set_language is not None:
            normalized_options = [str(option or "").strip().lower() for option in language_options if str(option or "").strip()]
            normalized_current = str(current_language or "en").strip().lower() or "en"
            if normalized_options:
                language_choice = st.selectbox(
                    language_label,
                    options=normalized_options,
                    index=normalized_options.index(normalized_current) if normalized_current in normalized_options else 0,
                    key="sidebar_language_choice",
                )
                if language_choice != normalized_current:
                    set_language(language_choice)
                    st.rerun()
        if theme_service is not None:
            backgrounds = theme_service.list_available_backgrounds()
            if backgrounds:
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
    return chosen
