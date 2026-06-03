from __future__ import annotations

import streamlit as st

from services.navigation_service import icon_for_navigation_label


def format_icon_nav_label(item: str) -> str:
    return f"{icon_for_navigation_label(item)}  {item}"


def render_icon_sidebar_group(group: str, items: list[str], *, selected: str) -> str | None:
    chosen: str | None = None
    for item in items:
        active = item == selected
        button_label = format_icon_nav_label(item)
        if st.button(
            button_label,
            key=f"nav_icon_{item.lower().replace(' ', '_')}",
            use_container_width=True,
            type="primary" if active else "secondary",
            help=item,
        ):
            chosen = item
    return chosen
