from __future__ import annotations

import streamlit as st

from services.navigation_service import icon_for_navigation_label


def format_icon_nav_label(item: dict[str, str] | str) -> str:
    if isinstance(item, dict):
        label = str(item.get("label", ""))
        icon = str(item.get("icon") or icon_for_navigation_label(label))
        return f"{icon}  {label}"
    icon = icon_for_navigation_label(item)
    return f"{icon}  {item}"


def render_icon_sidebar_group(group: str, items: list[dict[str, str]], *, selected: str) -> str | None:
    chosen: str | None = None
    for item in items:
        route = str(item.get("route", ""))
        label = str(item.get("label", route))
        active = route == selected
        button_label = format_icon_nav_label(item)
        if st.button(
            button_label,
            key=f"nav_icon_{route}",
            use_container_width=True,
            type="primary" if active else "secondary",
            help=label,
        ):
            chosen = route
    return chosen
