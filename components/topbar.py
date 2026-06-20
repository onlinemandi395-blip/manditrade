from __future__ import annotations

import streamlit as st

from components.html_renderer import render_template


_CONTROL_DIALOG_KEY = "mt_control_surface_dialog"
_PENDING_ROLE_VIEW_KEY = "mt_pending_role_view_selection"


def _open_control_dialog(dialog_id: str) -> None:
    st.session_state[_CONTROL_DIALOG_KEY] = str(dialog_id or "").strip().lower()


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
    render_template(
        "topbar.html",
        app_name=app_name,
    )

    current_role_value = str(current_role_view or "__self__")
    pending_role_view = st.session_state.pop(_PENDING_ROLE_VIEW_KEY, None)

    runtime_mode = str(drive_manifest.get("mode", "") or "connected").replace("_", " ").strip().title()
    runtime_source = str(drive_manifest.get("source", "") or "drive").replace("_", " ").strip().title()
    root_folder_name = str(drive_manifest.get("root_folder_name", "") or "MANDITRADE_DB").strip()
    user_name = str(user.get("display_name", "") or user.get("email", "") or "Workspace User").strip()
    user_email = str(user.get("email", "") or "").strip()

    cards = [
        {
            "id": "account",
            "label": "Account",
            "value": user_name,
            "detail": user_email or role_label,
            "button": "Open Account",
        },
        {
            "id": "role",
            "label": "Current Role",
            "value": role_label or "Workspace",
            "detail": "Switch working view",
            "button": "Change Role View",
        },
        {
            "id": "language",
            "label": language_label or "Language",
            "value": str(language or "en").upper(),
            "detail": "Choose display language",
            "button": "Change Language",
        },
        {
            "id": "release",
            "label": "Release",
            "value": f"v{version}",
            "detail": app_name,
            "button": "View Release",
        },
        {
            "id": "runtime",
            "label": "Google Drive runtime",
            "value": runtime_mode,
            "detail": root_folder_name,
            "button": "View Runtime",
        },
        {
            "id": "workspace",
            "label": "Operational workspace",
            "value": "JSON-native data",
            "detail": runtime_source,
            "button": "Configure Workspace",
        },
    ]

    card_rows = [cards[:3], cards[3:]]
    for row_index, row in enumerate(card_rows):
        cols = st.columns(len(row), gap="small")
        for col, card in zip(cols, row):
            with col:
                with st.container(border=True):
                    st.caption(card["label"])
                    st.markdown(f"**{card['value']}**")
                    st.caption(card["detail"])
                    if st.button(card["button"], key=f"topbar_card_{row_index}_{card['id']}", use_container_width=True):
                        _open_control_dialog(card["id"])

    @st.dialog("Control Surface")
    def _render_control_dialog() -> None:
        dialog_id = str(st.session_state.get(_CONTROL_DIALOG_KEY, "") or "").strip().lower()
        if dialog_id == "account":
            st.markdown("### Account")
            st.write(f"Name: {user_name}")
            st.write(f"Email: {user_email or '-'}")
            st.write(f"Role: {role_label or '-'}")
        elif dialog_id == "role":
            st.markdown("### Role View")
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
        elif dialog_id == "language":
            st.markdown(f"### {language_label or 'Language'}")
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
        elif dialog_id == "release":
            st.markdown("### Release")
            st.write(f"Application: {app_name}")
            st.write(f"Version: v{version}")
            st.caption("This control surface reflects the current application release.")
        elif dialog_id == "runtime":
            st.markdown("### Google Drive Runtime")
            st.write(f"Root Folder: {root_folder_name}")
            st.write(f"Mode: {runtime_mode}")
            st.write(f"Source: {runtime_source}")
            st.write(f"Connected: {'Yes' if drive_manifest.get('connected', False) else 'No'}")
            missing_files = list(drive_manifest.get("missing_files", []) or [])
            if missing_files:
                st.warning(f"Missing files: {len(missing_files)}")
            else:
                st.success("Required files are available.")
        elif dialog_id == "workspace":
            st.markdown("### Workspace")
            st.write("Data Layer: JSON-native data")
            st.write("Workspace: Operational workspace")
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
            st.caption("Use this area for top-level workspace preferences.")

        if st.button("Close", use_container_width=True, key="topbar_close_dialog"):
            st.session_state[_CONTROL_DIALOG_KEY] = ""
            st.rerun()

    if str(st.session_state.get(_CONTROL_DIALOG_KEY, "") or "").strip():
        _render_control_dialog()

    return pending_role_view
