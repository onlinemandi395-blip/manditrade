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
