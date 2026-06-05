from __future__ import annotations

import streamlit as st


def render_dashboard_widget_grid(
    app_context: dict,
    page_key: str,
    widgets: list[dict[str, str]],
    *,
    columns: int = 3,
) -> None:
    if not widgets:
        return
    session_state_service = app_context["session_state_service"]
    cols = max(columns, 1)
    for index in range(0, len(widgets), cols):
        row_columns = st.columns(cols)
        for column, widget in zip(row_columns, widgets[index:index + cols]):
            route = str(widget.get("route", "dashboard"))
            title = str(widget.get("title", route.replace("_", " ").title()))
            subtitle = str(widget.get("subtitle", "")).strip()
            badge = str(widget.get("badge", "")).strip()
            tab_name = str(widget.get("tab_name", "")).strip()
            with column:
                with st.container(border=True):
                    st.markdown(f"#### {title}")
                    if subtitle:
                        st.caption(subtitle)
                    if badge:
                        st.write(badge)
                    if st.button(
                        f"Open {title}",
                        key=f"{page_key}_{route}_{index}_{title}".replace(" ", "_").lower(),
                        use_container_width=True,
                    ):
                        if tab_name:
                            session_state_service.set_active_tab(route, tab_name)
                        session_state_service.set_navigation(route)
                        st.rerun()
