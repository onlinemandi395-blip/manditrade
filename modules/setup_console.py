from __future__ import annotations

import streamlit as st

from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from services.cache_service import CacheService
from services.config_loader_service import ConfigLoaderService
from services.qr_service import QRService
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
    database_status = admin_drive_service.get_database_config_status()
    cols = st.columns(7)
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
            st.success(f"Files created: {len(result.get('created', []))}. Database mappings updated: {len(result.get('updated', []))}")
            st.rerun()
        except Exception as exc:
            st.error(f"Create Missing JSON Files failed: {exc}")
    if cols[3].button(
        "Refresh database.json Mappings",
        use_container_width=True,
        disabled=database_status.get("status") == "OK",
    ):
        try:
            result = admin_drive_service.refresh_database_config_mapping()
            st.success(
                f"database.json {str(result.get('status', 'UPDATED')).lower()}. Added mappings: "
                f"{', '.join(result.get('added_collections', [])) or 'none'}"
            )
            st.rerun()
        except Exception as exc:
            st.error(f"database.json refresh failed: {exc}")
    if cols[4].button("Migrate Root Orders", use_container_width=True):
        try:
            result = admin_drive_service.migrate_root_orders()
            st.success(
                f"Root orders migration: {result.get('status', 'DONE')}. "
                f"Marketplace added: {result.get('marketplace_added', 0)}, "
                f"MandiTrade added: {result.get('manditrade_added', 0)}"
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Root orders migration failed: {exc}")
    if cols[5].button("Reload Cache", use_container_width=True):
        admin_drive_service.clear_runtime_cache()
        st.rerun()
    if cols[6].button("Continue to App", use_container_width=True, disabled=not setup_complete):
        admin_drive_service.clear_runtime_cache()
        st.rerun()

    st.markdown("### database.json Mapping Status")
    render_table([database_status], caption="Drive database.json status")
    st.markdown("### Merchant Payment Configuration")
    payment_config_payload = dict(CacheService(ConfigLoaderService()).get_config("payment_config") or {})
    payment_settings = dict(payment_config_payload.get("payment", {}) or payment_config_payload)
    render_table(
        [
            {
                "enabled": bool(payment_settings.get("enabled", True)),
                "upi_id": str(payment_settings.get("upi_id", "")).strip(),
                "payee_name": str(payment_settings.get("payee_name", "")).strip(),
                "currency": str(payment_settings.get("currency", "INR")).strip() or "INR",
            }
        ],
        caption="Current payment receiver settings",
    )
    payment_cols = st.columns(2)
    payment_enabled = payment_cols[0].checkbox(
        "UPI Payments Enabled",
        value=bool(payment_settings.get("enabled", True)),
        key="setup_payment_enabled",
    )
    payment_currency = payment_cols[1].text_input(
        "Currency",
        value=str(payment_settings.get("currency", "INR") or "INR"),
        key="setup_payment_currency",
    )
    payment_upi_id = st.text_input(
        "Merchant UPI ID",
        value=str(payment_settings.get("upi_id", "") or ""),
        key="setup_payment_upi_id",
    )
    payment_payee_name = st.text_input(
        "Payee Name",
        value=str(payment_settings.get("payee_name", "") or ""),
        key="setup_payment_payee_name",
    )
    if payment_enabled and str(payment_upi_id).strip():
        payment_link = (
            f"upi://pay?pa={str(payment_upi_id).strip()}&pn={str(payment_payee_name or 'MandiTrade').strip()}&am=1.00&cu={str(payment_currency or 'INR').strip() or 'INR'}&tn=MandiTradePreview"
        )
        st.caption("Live UPI Preview")
        st.code(payment_link)
        qr_bytes = QRService().build_qr_png_bytes(payment_link)
        if qr_bytes:
            st.image(qr_bytes, width=180)
    if st.button("Save Payment Receiver Settings", use_container_width=True, key="setup_save_payment_config"):
        try:
            if payment_enabled and not str(payment_upi_id).strip():
                raise ValueError("Merchant UPI ID is required when UPI payments are enabled.")
            payment_payload = {
                "schema_version": 1,
                "payment": {
                    "upi_id": str(payment_upi_id or "").strip(),
                    "payee_name": str(payment_payee_name or "").strip() or "MandiTrade",
                    "currency": str(payment_currency or "INR").strip() or "INR",
                    "enabled": bool(payment_enabled),
                },
            }
            admin_drive_service.write_json("00_config/payment_config.json", payment_payload)
            CacheService(ConfigLoaderService()).update_config("payment_config", payment_payload)
            st.success("Merchant payment receiver settings saved.")
            st.rerun()
        except Exception as exc:
            st.error(f"Save Payment Receiver Settings failed: {exc}")
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
