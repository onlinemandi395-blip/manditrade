from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from services.cache_service import CacheService
from services.config_loader_service import ConfigLoaderService
from services.theme_service import ThemeService


def render_setup_console(admin_drive_service, drive_manifest: dict) -> None:
    st.markdown("## MandiTrade First-Time Setup")
    st.caption("Google Drive Database Initialization")

    status_cards = st.columns(6)
    status_cards[0].metric("Google OAuth", "Ready" if drive_manifest.get("connected") else "Missing")
    status_cards[1].metric("Google Drive", "Connected" if drive_manifest.get("connected") else "Disconnected")
    status_cards[2].metric("Root Folder", drive_manifest.get("root_folder_name", "Missing"))
    status_cards[3].metric("Required Folders", f"{len(drive_manifest.get('required_folders', [])) - len(drive_manifest.get('missing_folders', []))}/{len(drive_manifest.get('required_folders', []))}")
    status_cards[4].metric("Required JSON Files", f"{len(drive_manifest.get('required_files', [])) - len(drive_manifest.get('missing_files', []))}/{len(drive_manifest.get('required_files', []))}")
    status_cards[5].metric("Cache Status", "Loaded" if st.session_state.get("mt_next_cache") else "Empty")

    root_missing = not drive_manifest.get("root_folder_id")
    setup_complete = not drive_manifest.get("missing_files") and not drive_manifest.get("missing_folders") and not root_missing
    cols = st.columns(5)
    if cols[0].button("Create Root Folder", use_container_width=True, disabled=not root_missing):
        try:
            result = admin_drive_service.ensure_root_folder()
            st.success(f"Root folder {result['status'].lower()}.")
            admin_drive_service.clear_runtime_cache()
            st.rerun()
        except Exception as exc:
            st.error(f"Create Root Folder failed: {exc}")
    if cols[1].button("Create Missing Folders", use_container_width=True, disabled=not drive_manifest.get("missing_folders")):
        try:
            result = admin_drive_service.create_missing_required_folders()
            st.success(f"Folders created: {len(result.get('created', []))}")
            st.rerun()
        except Exception as exc:
            st.error(f"Create Missing Folders failed: {exc}")
    if cols[2].button("Create Missing JSON Files", use_container_width=True, disabled=not drive_manifest.get("missing_files")):
        try:
            result = admin_drive_service.create_missing_required_files()
            st.success(f"Files created: {len(result.get('created', []))}")
            st.rerun()
        except Exception as exc:
            st.error(f"Create Missing JSON Files failed: {exc}")
    if cols[3].button("Reload Cache", use_container_width=True):
        admin_drive_service.clear_runtime_cache()
        st.rerun()
    if cols[4].button("Continue to App", use_container_width=True, disabled=not setup_complete):
        admin_drive_service.clear_runtime_cache()
        st.rerun()

    st.markdown("### Required Folders")
    render_table(drive_manifest.get("required_folders", []), caption="Required Drive folders")
    st.markdown("### Required JSON Files")
    render_table(drive_manifest.get("required_files", []), caption="Required Drive files")
    theme_file = next(
        (row for row in drive_manifest.get("required_files", []) if str(row.get("logical_path", "")) == "00_config/theme.json"),
        None,
    )
    if theme_file:
        st.markdown("### Theme Config Trace")
        render_table([theme_file], caption="theme.json status")
    theme_service = ThemeService(admin_drive_service, CacheService(ConfigLoaderService()))
    render_theme_manager(theme_service, allow_set_default=True, title="Theme Background Setup")
