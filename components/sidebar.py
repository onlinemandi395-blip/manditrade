from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template

SECTION_GROUPS = {
    "shop": {"marketplace", "manditrade", "orders"},
    "work": {"dashboard", "products", "shipments", "payments", "ledger", "completed_deliveries"},
    "account": {"profile", "admin_configuration", "system_health", "notifications"},
}

SECTION_LABELS = {
    "shop": "Browse",
    "work": "Work",
    "account": "Account",
}


def _group_navigation_items(navigation_items: list[dict]) -> list[tuple[str, list[dict]]]:
    grouped: dict[str, list[dict]] = {"shop": [], "work": [], "account": []}
    for item in navigation_items:
        route = str(item.get("route", "")).strip()
        section = next((name for name, routes in SECTION_GROUPS.items() if route in routes), "work")
        grouped.setdefault(section, []).append(item)
    return [(section, grouped.get(section, [])) for section in ("shop", "work", "account") if grouped.get(section)]


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
        for section_name, items in _group_navigation_items(navigation_items):
            render_template("sidebar_section_label.html", label=SECTION_LABELS.get(section_name, "Navigation"))
            for item in items:
                label = str(item.get("label", item.get("route", ""))).strip()
                route = str(item.get("route", "dashboard"))
                if st.button(
                    label,
                    key=f"sidebar_{route}",
                    use_container_width=True,
                    type="primary" if route == selected_route else "secondary",
                ):
                    chosen = route
    return chosen, selected_view
