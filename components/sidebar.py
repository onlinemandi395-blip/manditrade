from __future__ import annotations

import streamlit as st


def render_sidebar(navigation_items: list[dict], selected_route: str, user: dict | None = None, role_label: str = "") -> str:
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
