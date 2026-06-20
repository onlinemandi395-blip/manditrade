from __future__ import annotations

from pathlib import Path
import json

import streamlit as st

from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from services.cache_service import CacheService
from services.config_loader_service import ConfigLoaderService
from services.data_service import DataService
from services.payment_service import PaymentService
from services.payment_config_service import PaymentConfigService
from services.product_consent_service import ProductConsentService
from services.qr_service import QRService
from services.theme_service import ThemeService


def _read_seed_payload(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _build_seed_summary(mode: str) -> list[dict]:
    seed_root = Path("bootstrap_seed") / mode
    users = _read_seed_payload(seed_root / "01_identity" / "users.json").get("users", [])
    products = _read_seed_payload(seed_root / "02_catalog" / "products.json").get("products", [])
    marketplace_orders = _read_seed_payload(seed_root / "05_orders" / "marketplace" / "orders.json").get("orders", [])
    manditrade_orders = _read_seed_payload(seed_root / "05_orders" / "mandiplace" / "orders.json").get("orders", [])
    shipments = _read_seed_payload(seed_root / "06_shipments" / "shipments.json").get("shipments", [])
    payments = _read_seed_payload(seed_root / "07_ledger" / "payments.json").get("payments", [])
    ledger = _read_seed_payload(seed_root / "07_ledger" / "ledger.json").get("ledger", [])
    notifications = _read_seed_payload(seed_root / "09_notifications" / "notifications.json").get("notifications", [])
    role_counts: dict[str, int] = {}
    for user in users:
        role = str(user.get("role", "")).strip().lower()
        if role:
            role_counts[role] = role_counts.get(role, 0) + 1
    return [
        {"area": "Users", "count": len(users), "detail": ", ".join(f"{role}: {count}" for role, count in sorted(role_counts.items()))},
        {"area": "Products", "count": len(products), "detail": "Catalog ready"},
        {"area": "Marketplace Orders", "count": len(marketplace_orders), "detail": "B2C order simulation"},
        {"area": "MandiTrade Orders", "count": len(manditrade_orders), "detail": "B2B order simulation"},
        {"area": "Shipments", "count": len(shipments), "detail": "Pickup to delivery stages"},
        {"area": "Payments", "count": len(payments), "detail": "Pending and verified payment records"},
        {"area": "Ledger", "count": len(ledger), "detail": "Runtime accounting entries"},
        {"area": "Notifications", "count": len(notifications), "detail": "System and role updates"},
    ]


def _get_bootstrap_payment_settings(admin_drive_service) -> dict:
    definition = admin_drive_service._get_required_file_definition("00_config/payment_config.json")  # noqa: SLF001
    default_payload = dict((definition or {}).get("default_payload", {}) or {})
    fallback_settings = dict(default_payload.get("payment", {}) or default_payload)
    try:
        payload = dict(admin_drive_service.read_json("00_config/payment_config.json") or {})
        settings = dict(payload.get("payment", {}) or payload)
        return {
            "enabled": bool(settings.get("enabled", fallback_settings.get("enabled", True))),
            "upi_id": str(settings.get("upi_id", fallback_settings.get("upi_id", ""))).strip(),
            "payee_name": str(settings.get("payee_name", fallback_settings.get("payee_name", ""))).strip(),
            "currency": str(settings.get("currency", fallback_settings.get("currency", "INR"))).strip() or "INR",
        }
    except Exception:
        return {
            "enabled": bool(fallback_settings.get("enabled", True)),
            "upi_id": str(fallback_settings.get("upi_id", "")).strip(),
            "payee_name": str(fallback_settings.get("payee_name", "")).strip(),
            "currency": str(fallback_settings.get("currency", "INR")).strip() or "INR",
        }


def _get_bootstrap_consent_settings(admin_drive_service) -> list[dict]:
    definition = admin_drive_service._get_required_file_definition("00_config/product_owner_consent.json")  # noqa: SLF001
    default_payload = dict((definition or {}).get("default_payload", {}) or {})
    owner_config = dict(default_payload.get("product_owner_consent", {}) or {})
    delivery_partner_config = dict(default_payload.get("delivery_partner_consent", {}) or {})
    try:
        payload = dict(admin_drive_service.read_json("00_config/product_owner_consent.json") or {})
        owner_config = dict(payload.get("product_owner_consent", owner_config) or owner_config)
        delivery_partner_config = dict(payload.get("delivery_partner_consent", delivery_partner_config) or delivery_partner_config)
    except Exception:
        pass
    return [owner_config, delivery_partner_config]


def render_setup_console(admin_drive_service, drive_manifest: dict, translator=None, key_prefix: str = "setup") -> None:
    t = translator.t if translator else (lambda key: key)
    st.markdown(f"## {t('ui.first_time_setup')}")
    st.caption(t("ui.google_drive_database_initialization"))
    bootstrap_mode = st.radio(
        "Bootstrap Mode",
        options=["live", "dummy"],
        index=1 if admin_drive_service.get_selected_bootstrap_mode() == "dummy" else 0,
        horizontal=True,
        key=f"{key_prefix}_bootstrap_mode",
        format_func=lambda value: "Dummy Simulation" if value == "dummy" else "Live",
    )
    st.session_state["mt_bootstrap_mode"] = bootstrap_mode
    st.caption("Use Dummy Simulation to initialize the app with realistic demo products, orders, payments, shipments, and notifications.")
    render_table(_build_seed_summary(bootstrap_mode), caption="Bootstrap seed summary")
    st.markdown("### Bootstrap Seed Import")
    st.caption(
        "Upload a zip of the selected bootstrap folder structure. "
        "The system will create `MANDITRADE_DB`, required folders, and JSON files in one pass from this archive."
    )
    bootstrap_archive = st.file_uploader(
        "Upload Bootstrap Zip",
        type=["zip"],
        key=f"{key_prefix}_bootstrap_archive",
    )
    seed_folder_hint = Path("bootstrap_seed") / bootstrap_mode
    st.code(str(seed_folder_hint))
    st.caption("Zip the full selected seed folder so the archive contains the config, identity, catalog, orders, shipments, ledger, notifications, and runtime folders together.")

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
    cols = st.columns(3)
    if cols[0].button("Import Bootstrap Seed", use_container_width=True, disabled=bootstrap_archive is None, key=f"{key_prefix}_import_bootstrap_seed"):
        try:
            result = admin_drive_service.import_bootstrap_archive(
                bootstrap_archive.getvalue(),
                mode=bootstrap_mode,
            )
            st.success(
                f"Bootstrap imported: {len(result.get('imported', []))} files. "
                f"Skipped: {len(result.get('skipped', []))}."
            )
            st.rerun()
        except Exception as exc:
            st.error(f"Bootstrap import failed: {exc}")
    if cols[1].button("Reload Cache", use_container_width=True, key=f"{key_prefix}_reload_cache"):
        admin_drive_service.clear_runtime_cache()
        st.rerun()
    if cols[2].button("Continue to App", use_container_width=True, disabled=not setup_complete, key=f"{key_prefix}_continue_to_app"):
        admin_drive_service.clear_runtime_cache()
        st.rerun()

    st.markdown("### database.json Mapping Status")
    render_table([database_status], caption="Drive database.json status")
    st.markdown("### Merchant Payment Configuration")
    payment_settings = _get_bootstrap_payment_settings(admin_drive_service)
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
        key=f"{key_prefix}_payment_enabled",
    )
    payment_currency = payment_cols[1].text_input(
        "Currency",
        value=str(payment_settings.get("currency", "INR") or "INR"),
        key=f"{key_prefix}_payment_currency",
    )
    payment_upi_id = st.text_input(
        "Merchant UPI ID",
        value=str(payment_settings.get("upi_id", "") or ""),
        key=f"{key_prefix}_payment_upi_id",
    )
    payment_payee_name = st.text_input(
        "Payee Name",
        value=str(payment_settings.get("payee_name", "") or ""),
        key=f"{key_prefix}_payment_payee_name",
    )
    if payment_enabled and str(payment_upi_id).strip():
        payment_link = PaymentService.build_upi_link_from_values(
            upi_id=str(payment_upi_id).strip(),
            payee_name=str(payment_payee_name or "MandiTrade").strip(),
            amount=1.0,
            currency=str(payment_currency or "INR").strip() or "INR",
            reference="PREVIEW0001",
        )
        st.caption("Live UPI Preview")
        st.code(payment_link)
        qr_bytes = QRService().build_qr_png_bytes(payment_link)
        if qr_bytes:
            st.image(qr_bytes, width=180)
    if st.button("Save Payment Receiver Settings", use_container_width=True, key=f"{key_prefix}_save_payment_config"):
        try:
            cache_service = CacheService(ConfigLoaderService())
            result = PaymentConfigService(
                DataService(cache_service),
                cache_service,
                admin_drive_service,
            ).save_payment_receiver_settings(
                enabled=bool(payment_enabled),
                currency=str(payment_currency or "INR"),
                upi_id=str(payment_upi_id or ""),
                payee_name=str(payment_payee_name or ""),
                changed_by=str((st.session_state.get("mt_next_user", {}) or {}).get("email", "") or ""),
                source_screen="first_time_setup",
            )
            if result.get("changed"):
                impact = result.get("impact", {}) or {}
                st.success(
                    "Merchant payment receiver settings saved. "
                    f"Pending payments updated: {impact.get('pending_payments_updated', 0)} | "
                    f"Pending orders updated: {impact.get('pending_orders_updated', 0)}"
                )
            else:
                st.success("Merchant payment receiver settings saved. No live queue updates were required.")
            st.rerun()
        except Exception as exc:
            st.error(f"Save Payment Receiver Settings failed: {exc}")
    st.markdown("### Required Folders")
    render_table(drive_manifest.get("required_folders", []), caption="Required Drive folders")
    st.markdown("### Required JSON Files")
    render_table(drive_manifest.get("required_files", []), caption="Required Drive files")
    st.markdown("### Product Owner Consent Configuration")
    render_table(
        _get_bootstrap_consent_settings(admin_drive_service),
        caption="Onboarding consent config",
    )
    theme_file = next(
        (row for row in drive_manifest.get("required_files", []) if str(row.get("logical_path", "")) == "00_config/theme.json"),
        None,
    )
    if theme_file:
        st.markdown("### Theme Config Trace")
        render_table([theme_file], caption="theme.json status")
    if not root_missing:
        theme_service = ThemeService(admin_drive_service, CacheService(ConfigLoaderService()))
        render_theme_manager(theme_service, allow_set_default=True, title="Theme Background Setup", key_prefix=f"{key_prefix}_theme")
    else:
        st.info("Theme background setup will be available after the active Drive root is created.")
