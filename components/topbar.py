from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template


_CONTROL_DIALOG_KEY = "mt_control_surface_dialog"
_PENDING_ROLE_VIEW_KEY = "mt_pending_role_view_selection"


def _open_control_dialog() -> None:
    st.session_state[_CONTROL_DIALOG_KEY] = "open"


def render_topbar(
    *,
    app_name: str,
    version: str,
    role_label: str,
    role_key: str,
    language: str,
    language_label: str,
    translator,
    user: dict,
    drive_manifest: dict,
    role_switcher_options: list[dict] | None = None,
    current_role_view: str = "__self__",
    language_options: list[str] | None = None,
    language_option_labels: dict[str, str] | None = None,
    set_language=None,
    theme_service=None,
) -> str | None:
    pending_role_view = st.session_state.pop(_PENDING_ROLE_VIEW_KEY, None)
    current_role_value = str(current_role_view or "__self__")

    runtime_mode = str(drive_manifest.get("mode", "") or "connected").replace("_", " ").strip().title()
    runtime_source = str(drive_manifest.get("source", "") or "drive").replace("_", " ").strip().title()
    root_folder_name = str(drive_manifest.get("root_folder_name", "") or "MANDITRADE_DB").strip()
    user_name = str(user.get("display_name", "") or user.get("email", "") or "Workspace User").strip()
    user_email = str(user.get("email", "") or "").strip()

    summary_items = [
        {"label": "Current Role", "value": role_label or "Workspace"},
        {"label": language_label or "Language", "value": str(language or "en").upper()},
        {"label": "Release", "value": f"v{version}"},
        {"label": "Google Drive runtime", "value": runtime_mode},
        {"label": "Data Layer", "value": "JSON-native data"},
        {"label": "Workspace", "value": "Operational workspace"},
    ]
    summary_html = "".join(
        (
            "<div class='mt-control-surface__item'>"
            f"<span>{item['label']}</span>"
            f"<strong>{item['value']}</strong>"
            "</div>"
        )
        for item in summary_items
    )

    render_template(
        "topbar.html",
        app_name=app_name,
        summary_html=summary_html,
        user_name=user_name,
        user_email=user_email,
    )

    action_cols = st.columns([1, 1, 1.6], gap="small")
    with action_cols[0]:
        if st.button("Open Control Surface", key="topbar_open_control_surface", use_container_width=True, type="primary"):
            _open_control_dialog()
    with action_cols[1]:
        st.caption(root_folder_name)
    with action_cols[2]:
        st.caption("Google Drive runtime, role view, language, release, and workspace preferences in one place.")

    @st.dialog("MandiTrade Control Surface")
    def _render_control_dialog() -> None:
        st.markdown("### Workspace Summary")
        summary_cols = st.columns(2, gap="small")
        with summary_cols[0]:
            st.write(f"User: {user_name}")
            st.write(f"Email: {user_email or '-'}")
            st.write(f"Current Role: {role_label or '-'}")
        with summary_cols[1]:
            st.write(f"Release: v{version}")
            st.write(f"Runtime: {runtime_mode}")
            st.write(f"Root Folder: {root_folder_name}")

        section_tabs = st.tabs(["Language", "Role View", "Workspace", "Runtime", "Account"])

        with section_tabs[0]:
            normalized_options = [str(option or "").strip().lower() for option in (language_options or []) if str(option or "").strip()]
            normalized_current = str(language or "en").strip().lower() or "en"
            if normalized_options and set_language is not None:
                choice = st.selectbox(
                    language_label or "Language",
                    options=normalized_options,
                    index=normalized_options.index(normalized_current) if normalized_current in normalized_options else 0,
                    format_func=lambda code: dict(language_option_labels or {}).get(code, str(code or "").upper()),
                    key="topbar_language_choice",
                )
                if st.button("Apply Language", use_container_width=True, key="topbar_apply_language"):
                    st.session_state[_CONTROL_DIALOG_KEY] = ""
                    set_language(choice)
                    st.rerun()
            else:
                st.info("Language options are not available.")

        with section_tabs[1]:
            if role_switcher_options:
                options = [str(option.get("value", "__self__")) for option in role_switcher_options]
                choice = st.selectbox(
                    "Choose role view",
                    options=options,
                    index=options.index(current_role_value) if current_role_value in options else 0,
                    format_func=lambda value: next(
                        (
                            str(option.get("label", "Role View"))
                            for option in role_switcher_options
                            if str(option.get("value", "__self__")) == str(value)
                        ),
                        "Role View",
                    ),
                    key="topbar_role_view_choice",
                )
                if st.button("Apply Role View", use_container_width=True, key="topbar_apply_role_view"):
                    st.session_state[_PENDING_ROLE_VIEW_KEY] = choice
                    st.session_state[_CONTROL_DIALOG_KEY] = ""
                    st.rerun()
            else:
                st.info("Role view switching is available only to superadmin.")

        with section_tabs[2]:
            st.write("Data Layer: JSON-native data")
            st.write(f"Workspace Source: {runtime_source}")
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
                        key="topbar_theme_choice",
                    )
                    if st.button("Apply Theme", use_container_width=True, key="topbar_apply_theme"):
                        chosen_theme = next((row for row in backgrounds if row.get("file_id", "") == theme_choice), None)
                        if theme_choice:
                            theme_service.set_selected_background(chosen_theme)
                        else:
                            theme_service.clear_selected_background()
                        theme_service.clear_theme_cache()
                        st.session_state[_CONTROL_DIALOG_KEY] = ""
                        st.rerun()
                else:
                    st.caption("No workspace themes available.")

        with section_tabs[3]:
            st.write(f"Connected: {'Yes' if drive_manifest.get('connected', False) else 'No'}")
            st.write(f"Mode: {runtime_mode}")
            st.write(f"Source: {runtime_source}")
            st.write(f"Root Folder: {root_folder_name}")
            missing_files = list(drive_manifest.get("missing_files", []) or [])
            if missing_files:
                st.warning(f"Missing files: {len(missing_files)}")
            else:
                st.success("Required files are available.")

        with section_tabs[4]:
            st.write(f"Name: {user_name}")
            st.write(f"Email: {user_email or '-'}")
            st.write(f"Role: {role_label or '-'}")

        if st.button("Close", use_container_width=True, key="topbar_close_dialog"):
            st.session_state[_CONTROL_DIALOG_KEY] = ""
            st.rerun()

    if str(st.session_state.get(_CONTROL_DIALOG_KEY, "") or "").strip():
        _render_control_dialog()

    return pending_role_view
