from __future__ import annotations

import streamlit as st

from services.navigation_service import icon_for_navigation_label


def format_icon_nav_label(item: str) -> str:
    return icon_for_navigation_label(item)


def render_icon_sidebar_group(group: str, items: list[str], *, selected: str) -> str | None:
    chosen: str | None = None
    columns_per_row = 3 if len(items) >= 3 else max(len(items), 1)
    for start in range(0, len(items), columns_per_row):
        row_items = items[start : start + columns_per_row]
        columns = st.columns(columns_per_row, gap="small")
        for index, item in enumerate(row_items):
            active = item == selected
            button_label = format_icon_nav_label(item)
            with columns[index]:
                if st.button(
                    button_label,
                    key=f"nav_icon_{item.lower().replace(' ', '_')}",
                    use_container_width=True,
                    type="primary" if active else "secondary",
                    help=item,
                ):
                    chosen = item
    return chosen
