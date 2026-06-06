from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table


def render_theme_manager(theme_service, *, allow_set_default: bool = False, title: str = "Theme Backgrounds") -> None:
    st.markdown(f"### {title}")
    status = theme_service.get_background_status()
    backgrounds = theme_service.list_available_backgrounds()
    selected_background = theme_service.get_selected_background()
    active_file_id = theme_service.get_active_background_file_id()

    summary_cols = st.columns(4)
    summary_cols[0].metric("Theme Status", status.get("status", "MISSING"))
    summary_cols[1].metric("Available Backgrounds", str(len(backgrounds)))
    summary_cols[2].metric("Default File", status.get("background_file_name", "") or "Missing")
    summary_cols[3].metric("Active Theme", "Session Override" if selected_background.get("file_id") else "Default")

    action_cols = st.columns(3 if allow_set_default else 2)
    if action_cols[0].button("Refresh Theme Backgrounds", use_container_width=True):
        theme_service.clear_background_list_cache()
        theme_service.clear_theme_cache()
        st.rerun()
    if action_cols[1].button("Use Default Theme", use_container_width=True, disabled=not selected_background.get("file_id")):
        theme_service.clear_selected_background()
        theme_service.clear_theme_cache()
        st.rerun()

    if backgrounds:
        options = [{"label": "Default Theme", "value": ""}] + [
            {"label": row.get("file_name", row.get("file_id", "Background")), "value": row.get("file_id", "")}
            for row in backgrounds
        ]
        current_value = selected_background.get("file_id", "") if selected_background.get("file_id") else ""
        selected_value = st.selectbox(
            "Choose Background",
            options=[row["value"] for row in options],
            format_func=lambda value: next((row["label"] for row in options if row["value"] == value), value or "Default Theme"),
            index=next((idx for idx, row in enumerate(options) if row["value"] == current_value), 0),
            key=f"theme_background_selector_{title}",
        )
        chosen = next((row for row in backgrounds if row.get("file_id", "") == selected_value), None)

        if selected_value:
            preview_cols = st.columns(2 if allow_set_default else 1)
            if preview_cols[0].button("Apply Theme For My Session", use_container_width=True):
                theme_service.set_selected_background(chosen)
                theme_service.clear_theme_cache()
                st.rerun()
            if allow_set_default and preview_cols[1].button("Set As Default Theme", use_container_width=True):
                theme_service.save_default_background(chosen or {})
                st.success("Default theme updated.")
                st.rerun()
            preview_bytes = theme_service.get_background_preview_bytes(
                {
                    "file_id": chosen.get("file_id", ""),
                    "file_name": chosen.get("file_name", ""),
                    "local_cache_key": f"theme_{chosen.get('file_id', '')}",
                }
            ) if chosen else b""
            if preview_bytes:
                st.image(preview_bytes, caption=chosen.get("file_name", "Theme background"), use_container_width=True)
        elif allow_set_default and len(action_cols) > 2:
            action_cols[2].button("Set As Default Theme", use_container_width=True, disabled=True)
    else:
        st.warning("No background images found in Drive under 15_media/app_assets/backgrounds.")

    render_table([status], caption="Theme trace")
    if backgrounds:
        enriched_rows = []
        for row in backgrounds:
            enriched_rows.append(
                {
                    "file_name": row.get("file_name", ""),
                    "file_id": row.get("file_id", ""),
                    "mime_type": row.get("mime_type", ""),
                    "modified_time": row.get("modified_time", ""),
                    "is_active": "Yes" if row.get("file_id", "") == active_file_id else "No",
                    "is_default": "Yes" if row.get("file_id", "") == status.get("background_file_id", "") else "No",
                }
            )
        render_table(enriched_rows, caption="Available theme backgrounds")
