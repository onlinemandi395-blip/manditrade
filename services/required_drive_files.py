from __future__ import annotations

import json
from pathlib import Path


BOOTSTRAP_ROOT = Path(__file__).resolve().parent.parent / "bootstrap_seed"
DEFAULT_BOOTSTRAP_MODE = "live"


def _load_local_seed(relative_path: str, fallback: dict, *, mode: str = DEFAULT_BOOTSTRAP_MODE) -> dict:
    path = BOOTSTRAP_ROOT / mode / relative_path
    if not path.exists():
        return fallback
    return json.loads(path.read_text(encoding="utf-8"))


def _build_default_users(primary_admin_email: str, primary_admin_name: str, *, mode: str = DEFAULT_BOOTSTRAP_MODE) -> dict:
    payload = _load_local_seed("01_identity/users.json", {"users": []}, mode=mode)
    users = list(payload.get("users", []) or [])
    normalized_email = str(primary_admin_email or "").strip().lower()
    if normalized_email and not any(str(user.get("email", "")).strip().lower() == normalized_email for user in users):
        users.append(
            {
                "user_id": f"USR_{len(users) + 1:04d}",
                "email": normalized_email,
                "role": "platform_admin",
                "status": "ACTIVE",
                "display_name": primary_admin_name or "Primary Admin",
                "source": "toml_primary_admin",
            }
        )
    payload["users"] = users
    return payload


def build_required_drive_files(primary_admin_email: str, primary_admin_name: str, *, mode: str = DEFAULT_BOOTSTRAP_MODE) -> list[dict]:
    return [
        {"logical_path": "00_config/app_config.json", "type": "config", "default_payload": _load_local_seed("00_config/app_config.json", {"app_name": "MandiTrade Next"}, mode=mode)},
        {"logical_path": "00_config/auth.json", "type": "config", "default_payload": _load_local_seed("00_config/auth.json", {"authentication": {}}, mode=mode)},
        {"logical_path": "00_config/permissions.json", "type": "config", "default_payload": _load_local_seed("00_config/permissions.json", {"permissions": {}}, mode=mode)},
        {"logical_path": "00_config/role_views.json", "type": "config", "default_payload": _load_local_seed("00_config/role_views.json", {"role_views": {}}, mode=mode)},
        {"logical_path": "00_config/navigation.json", "type": "config", "default_payload": _load_local_seed("00_config/navigation.json", {"navigation": {"items": []}}, mode=mode)},
        {"logical_path": "00_config/modules.json", "type": "config", "default_payload": _load_local_seed("00_config/modules.json", {"modules": {}}, mode=mode)},
        {"logical_path": "00_config/dashboards.json", "type": "config", "default_payload": _load_local_seed("00_config/dashboards.json", {"dashboards": {}}, mode=mode)},
        {"logical_path": "00_config/forms.json", "type": "config", "default_payload": _load_local_seed("00_config/forms.json", {"forms": {}}, mode=mode)},
        {"logical_path": "00_config/categories.json", "type": "config", "default_payload": _load_local_seed("00_config/categories.json", {"schema_version": 1, "categories": []}, mode=mode)},
        {
            "logical_path": "00_config/payment_config.json",
            "type": "config",
            "default_payload": _load_local_seed(
                "00_config/payment_config.json",
                {"schema_version": 1, "payment": {"upi_id": "manditrade@upi", "payee_name": "MandiTrade", "currency": "INR", "enabled": True}},
                mode=mode,
            ),
        },
        {
            "logical_path": "00_config/product_owner_consent.json",
            "type": "config",
            "default_payload": _load_local_seed(
                "00_config/product_owner_consent.json",
                {
                    "schema_version": 1,
                    "product_owner_consent": {
                        "enabled": True,
                        "otp_length": 6,
                        "otp_expiry_minutes": 15,
                        "agreement_title": "Product Onboarding Consent Agreement",
                        "agreement_body": (
                            "This agreement confirms that the product owner {owner_email} authorizes MandiTrade admin "
                            "{requested_by} to onboard the product '{product_name}' on the MandiTrade platform."
                        ),
                        "email_subject": "Consent OTP for product onboarding on MandiTrade",
                        "email_body_template": (
                            "{agreement_title}\n\n{agreement_body}\n\nProduct: {product_name}\nOwner Email: {owner_email}\n"
                            "Requested By: {requested_by}\nConsent OTP: {otp_code}\n"
                        ),
                    },
                    "delivery_partner_consent": {
                        "enabled": True,
                        "otp_length": 6,
                        "otp_expiry_minutes": 15,
                        "agreement_title": "Worker Pickup and Safe Delivery Consent Agreement",
                        "agreement_body": (
                            "This agreement confirms that the worker {owner_email} authorizes MandiTrade admin "
                            "{requested_by} to assign pickup and delivery for the product '{product_name}'."
                        ),
                        "email_subject": "Consent OTP for worker onboarding on MandiTrade",
                        "email_body_template": (
                            "{agreement_title}\n\n{agreement_body}\n\nProduct: {product_name}\nWorker Email: {owner_email}\n"
                            "Requested By: {requested_by}\nConsent OTP: {otp_code}\n"
                        ),
                    },
                },
                mode=mode,
            ),
        },
        {"logical_path": "00_config/database.json", "type": "config", "default_payload": _load_local_seed("00_config/database.json", {"root": "MANDITRADE_DB", "collections": {}}, mode=mode)},
        {"logical_path": "00_config/theme.json", "type": "config", "default_payload": _load_local_seed("00_config/theme.json", {"schema_version": 1, "theme": {}}, mode=mode)},
        {
            "logical_path": "00_config/id_counters.json",
            "type": "config",
            "default_payload": _load_local_seed(
                "00_config/id_counters.json",
                {
                    "schema_version": 1,
                    "counters": {
                        "product": 0,
                        "user": 0,
                        "image": 0,
                        "payment_reference": 0,
                        "marketplace_order": 0,
                        "manditrade_order": 0,
                    },
                },
                mode=mode,
            ),
        },
        {"logical_path": "00_config/actions.json", "type": "config", "default_payload": _load_local_seed("00_config/actions.json", {"actions": {}}, mode=mode)},
        {"logical_path": "00_config/notifications.json", "type": "config", "default_payload": _load_local_seed("00_config/notifications.json", {"notifications": {}}, mode=mode)},
        {"logical_path": "00_config/roles.json", "type": "config", "default_payload": _load_local_seed("00_config/roles.json", {"roles": {}}, mode=mode)},
        {"logical_path": "00_config/workflows.json", "type": "config", "default_payload": _load_local_seed("00_config/workflows.json", {"workflows": {}}, mode=mode)},
        {"logical_path": "00_config/languages/en.json", "type": "language", "default_payload": _load_local_seed("00_config/languages/en.json", {"translations": {}}, mode=mode)},
        {"logical_path": "00_config/languages/hi.json", "type": "language", "default_payload": _load_local_seed("00_config/languages/hi.json", {"translations": {}}, mode=mode)},
        {"logical_path": "00_config/languages/mr.json", "type": "language", "default_payload": _load_local_seed("00_config/languages/mr.json", {"translations": {}}, mode=mode)},
        {"logical_path": "00_config/languages/bn.json", "type": "language", "default_payload": _load_local_seed("00_config/languages/bn.json", {"translations": {}}, mode=mode)},
        {"logical_path": "01_identity/users.json", "type": "data", "default_payload": _build_default_users(primary_admin_email, primary_admin_name, mode=mode)},
        {"logical_path": "02_catalog/products.json", "type": "data", "default_payload": _load_local_seed("02_catalog/products.json", {"products": []}, mode=mode)},
        {"logical_path": "05_orders/marketplace/orders.json", "type": "data", "default_payload": _load_local_seed("05_orders/marketplace/orders.json", {"schema_version": 1, "orders": []}, mode=mode)},
        {"logical_path": "05_orders/mandiplace/orders.json", "type": "data", "default_payload": _load_local_seed("05_orders/mandiplace/orders.json", {"schema_version": 1, "orders": []}, mode=mode)},
        {"logical_path": "06_shipments/shipments.json", "type": "data", "default_payload": _load_local_seed("06_shipments/shipments.json", {"shipments": []}, mode=mode)},
        {"logical_path": "07_ledger/ledger.json", "type": "data", "default_payload": _load_local_seed("07_ledger/ledger.json", {"ledger": []}, mode=mode)},
        {"logical_path": "07_ledger/payments.json", "type": "data", "default_payload": _load_local_seed("07_ledger/payments.json", {"payments": []}, mode=mode)},
        {"logical_path": "09_notifications/notifications.json", "type": "data", "default_payload": _load_local_seed("09_notifications/notifications.json", {"notifications": []}, mode=mode)},
        {"logical_path": "09_notifications/gmail_queue.json", "type": "data", "default_payload": _load_local_seed("09_notifications/gmail_queue.json", {"gmail_queue": []}, mode=mode)},
        {"logical_path": "10_audit/audit_logs.json", "type": "data", "default_payload": _load_local_seed("10_audit/audit_logs.json", {"audit_logs": []}, mode=mode)},
        {"logical_path": "14_runtime/product_owner_consents.json", "type": "data", "default_payload": _load_local_seed("14_runtime/product_owner_consents.json", {"schema_version": 1, "consents": []}, mode=mode)},
    ]
