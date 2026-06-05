from __future__ import annotations

import streamlit as st


def render_sidebar(navigation_items: list[dict], selected_route: str) -> str:
    chosen = selected_route
    with st.sidebar:
        for item in navigation_items:
            label = f"{item.get('icon', '')} {item.get('label', item.get('route', ''))}".strip()
            route = str(item.get("route", "dashboard"))
            if st.button(
                label,
                key=f"sidebar_{route}",
                use_container_width=True,
                type="primary" if route == selected_route else "secondary",
            ):
                chosen = route
    return chosen
