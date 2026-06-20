from __future__ import annotations

import streamlit as st

from components.detail_panel import render_detail_panel
from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from modules.setup_console import render_setup_console
from services.gmail_delivery_service import GmailDeliveryService
from services.gmail_queue_service import GmailQueueService
from services.integration_status_service import IntegrationStatusService
from services.payment_config_service import PaymentConfigService
from services.payment_service import PaymentService
from services.qr_service import QRService


def _render_status_cards(status: dict) -> None:
    top_cards = st.columns(5)
    top_cards[0].metric("Drive", "Connected" if status.get("google_drive_status") == "connected" else "Blocked")
    top_cards[1].metric("Root Folder", str(status.get("drive_root_status", "Missing") or "Missing"))
    top_cards[2].metric("Data Files", f"{max(int(status.get('required_files_count', 0) or 0) - int(status.get('missing_files_count', 0) or 0), 0)}/{int(status.get('required_files_count', 0) or 0)}")
    top_cards[3].metric("Mail Queue", int(status.get("queue_count", 0) or 0))
    top_cards[4].metric("Theme", str((status.get("theme_status", {}) or {}).get("status", "Missing") or "Missing"))

    data_cards = st.columns(6)
    data_cards[0].metric("Users", int(status.get("users_count", 0) or 0))
    data_cards[1].metric("Products", int(status.get("products_count", 0) or 0))
    data_cards[2].metric("Orders", int(status.get("order_count", 0) or 0))
    data_cards[3].metric("Profiles", int(status.get("user_profiles_count", 0) or 0))
    data_cards[4].metric("Alerts", int(status.get("notification_queue_count", 0) or 0))
    data_cards[5].metric("Audit Logs", int(status.get("audit_log_count", 0) or 0))


def _render_runtime_summary(status: dict, language_service, translator) -> None:
    render_table(
        [
            {"area": "Google Sign-In", "status": status.get("google_oauth_status", "missing")},
            {"area": "Drive Access", "status": status.get("google_drive_status", "disconnected")},
            {"area": "Runtime Mode", "status": status.get("drive_mode", "unknown")},
            {"area": "Admin Access", "status": status.get("admin_token_status", "missing")},
            {"area": "Drive Write Test", "status": status.get("drive_write_test", "FAIL")},
            {"area": "Mail Send Scope", "status": status.get("gmail_send_scope", "missing")},
            {"area": "Mail Sending", "status": status.get("gmail_status", "disabled")},
            {"area": "Mail Delivery", "status": "ready" if status.get("gmail_delivery_ready") else str(status.get("gmail_delivery_reason", "blocked"))},
            {"area": "Database Mapping", "status": status.get("database_config_status", {}).get("status", "MISSING")},
            {"area": "Language", "status": language_service.get_current_language()},
        ],
        caption="Runtime Overview",
    )
    with st.expander("View Runtime Details", expanded=False):
        render_table([status.get("database_config_status", {})], caption="Database Mapping")
        render_table(
            [
                {
                    "selected_language": language_service.get_current_language(),
                    "available_languages": ", ".join(language_service.get_available_languages()),
                    "loaded_key_counts": ", ".join(
                        f"{code}:{count}" for code, count in language_service.get_key_count_map().items()
                    ),
                    "missing_key_count": len(language_service.get_missing_keys_for_current_language()),
                    "sample_sidebar_products": translator.t("sidebar.products"),
                    "sample_module_products_title": translator.t("module.products.title"),
                }
            ],
            caption="Language Runtime",
        )
        render_table(
            [{"profile_path": path} for path in status.get("user_profile_sample_paths", [])],
            caption="Profile File Samples",
        )


def _render_payment_panel(
    *,
    status: dict,
    payment_config_service: PaymentConfigService,
    session_service,
) -> None:
    st.markdown("### Payment Receiver")
    payment_config_status = dict(status.get("payment_config", {}) or {})
    render_table([payment_config_status], caption="Current Payment Receiver")
    payment_cols = st.columns(2)
    payment_enabled = payment_cols[0].checkbox(
        "UPI Payments Enabled",
        value=bool(payment_config_status.get("enabled", True)),
        key="system_health_payment_enabled",
    )
    payment_currency = payment_cols[1].text_input(
        "Currency",
        value=str(payment_config_status.get("currency", "INR") or "INR"),
        key="system_health_payment_currency",
    )
    payment_upi_id = st.text_input(
        "Merchant UPI ID",
        value=str(payment_config_status.get("upi_id", "") or ""),
        key="system_health_payment_upi_id",
    )
    payment_payee_name = st.text_input(
        "Payee Name",
        value=str(payment_config_status.get("payee_name", "") or ""),
        key="system_health_payment_payee_name",
    )
    if payment_enabled and str(payment_upi_id).strip():
        payment_link = PaymentService.build_upi_link_from_values(
            upi_id=str(payment_upi_id).strip(),
            payee_name=str(payment_payee_name or "MandiTrade").strip(),
            amount=1.0,
            currency=str(payment_currency or "INR").strip() or "INR",
            reference="PREVIEW0001",
        )
        st.caption("UPI Preview")
        st.code(payment_link)
        qr_bytes = QRService().build_qr_png_bytes(payment_link)
        if qr_bytes:
            st.image(qr_bytes, width=180)
    if st.button("Save Payment Receiver", use_container_width=True, key="system_health_save_payment_config"):
        try:
            result = payment_config_service.save_payment_receiver_settings(
                enabled=bool(payment_enabled),
                currency=str(payment_currency or "INR"),
                upi_id=str(payment_upi_id or ""),
                payee_name=str(payment_payee_name or ""),
                changed_by=session_service.get_user().get("email", ""),
                source_screen="system_health",
            )
            if result.get("changed"):
                impact = result.get("impact", {}) or {}
                st.success(
                    "Payment receiver updated. "
                    f"Pending payments updated: {impact.get('pending_payments_updated', 0)} | "
                    f"Pending orders updated: {impact.get('pending_orders_updated', 0)}"
                )
            else:
                st.success("Payment receiver updated.")
            st.rerun()
        except Exception as exc:
            st.error(f"Save Payment Receiver failed: {exc}")


def render_system_health_page(
    *,
    admin_drive_service,
    cache_service,
    data_service,
    oauth_service,
    language_service,
    translator,
    session_service,
    rbac_service,
    page_service,
    navigation_service,
    performance_service,
    theme_service,
    role: str,
    is_superadmin: bool,
    navigation_items: list[dict],
    current_route: str,
) -> None:
    gmail_queue_service = GmailQueueService(data_service)
    gmail_delivery_service = GmailDeliveryService(data_service)
    payment_config_service = PaymentConfigService(data_service, cache_service, admin_drive_service)
    integration_status_service = IntegrationStatusService(
        cache_service=cache_service,
        admin_drive_service=admin_drive_service,
        gmail_queue_service=gmail_queue_service,
        oauth_service=oauth_service,
        data_service=data_service,
    )
    status = integration_status_service.get_status()
    drive_manifest = admin_drive_service.get_runtime_manifest(force_refresh=True)

    if status.get("google_drive_status") != "connected" or status.get("required_files_status") != "ok":
        st.error("Drive-only runtime is blocked. Upload the bootstrap zip or repair Drive access before regular operations continue.")

    tab_labels = ["Overview", "Bootstrap", "Operations"]
    if is_superadmin:
        tab_labels.append("Superadmin Debug")
    tabs = st.tabs(tab_labels)
    overview_tab, bootstrap_tab, operations_tab = tabs[:3]
    debug_tab = tabs[3] if is_superadmin and len(tabs) > 3 else None

    with overview_tab:
        _render_status_cards(status)
        _render_runtime_summary(status, language_service, translator)
        with st.expander("View Drive Structure", expanded=False):
            render_table(status.get("required_folders", []), caption="Required Drive Folders")
            render_table(status.get("required_files", []), caption="Required Drive Files")
        with st.expander("View Consent and Theme", expanded=False):
            render_table([status.get("product_owner_consent_config", {})], caption="Owner Consent")
            render_table([status.get("delivery_partner_consent_config", {})], caption="Worker Consent")
            render_table([status.get("theme_status", {})], caption="Theme Background")
        _render_payment_panel(
            status=status,
            payment_config_service=payment_config_service,
            session_service=session_service,
        )

    with bootstrap_tab:
        st.caption("Use one bootstrap zip to load the root, folders, and all operating JSON data in one pass.")
        render_setup_console(admin_drive_service, drive_manifest, translator, key_prefix="system_setup")

    with operations_tab:
        action_cols = st.columns(4)
        if action_cols[0].button("Refresh Health", use_container_width=True, key="system_health_refresh_health"):
            admin_drive_service.clear_runtime_cache(clear_validation=True, clear_file_index=False)
            st.rerun()
        if action_cols[1].button("Reload Cache", use_container_width=True, key="system_health_reload_cache"):
            cache_service.refresh_cache()
            st.success("Runtime cache refreshed.")
        if action_cols[2].button(
            "Refresh Database Mapping",
            use_container_width=True,
            disabled=status.get("database_config_status", {}).get("status") == "OK",
            key="system_health_refresh_database_mapping",
        ):
            try:
                result = admin_drive_service.refresh_database_config_mapping()
                st.success(
                    f"Database mapping {str(result.get('status', 'UPDATED')).lower()}. "
                    f"Added: {', '.join(result.get('added_collections', [])) or 'none'}"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Database mapping refresh failed: {exc}")
        if action_cols[3].button("Send Pending Emails", use_container_width=True, key="system_health_send_emails"):
            try:
                result = gmail_delivery_service.process_queue(limit=50)
                st.success(
                    f"Email queue processed: {result.get('processed', 0)} | "
                    f"sent: {result.get('sent', 0)} | failed: {result.get('failed', 0)}"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Send Pending Emails failed: {exc}")
        render_theme_manager(
            theme_service,
            allow_set_default=(role == "platform_admin"),
            title="Theme Background Control",
            key_prefix="system_health_theme",
        )

    if debug_tab is not None:
        with debug_tab:
            render_detail_panel("Runtime", status.get("cache_status", {}))
            with st.expander("Auth Runtime Debug", expanded=False):
                st.write(
                    {
                        "user": session_service.get_user(),
                        "permissions": rbac_service.get_permissions(role),
                        "landing_page": page_service.get_landing_page(role, navigation_service),
                        "filtered_nav_count": len(navigation_items),
                        "current_route": current_route,
                    }
                )
            with st.expander("Performance Debug", expanded=False):
                st.write(performance_service.get_metrics())
