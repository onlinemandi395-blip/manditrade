from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.dashboard_renderer import render_dashboard_cards
from components.detail_panel import render_detail_panel
from components.empty_state import render_empty_state
from components.form_renderer import render_form
from components.html_renderer import inject_css, inject_inline_css, render_template
from components.cart_panel import render_cart_panel
from components.checkout_steps import render_checkout_steps
from components.sidebar import render_sidebar
from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from components.topbar import render_topbar
from modules.admin_configuration import render_admin_configuration
from modules.completed_deliveries import render_completed_deliveries_page
from modules.notifications import render_notifications_page
from modules.login import render_login_page
from modules.ledger import render_ledger_page
from modules.manditrade import render_manditrade_page
from modules.marketplace import render_marketplace_page
from modules.orders import render_orders_page
from modules.payments import render_payments_page
from modules.profile import render_profile_page
from modules.products import render_products_page
from modules.shipments import render_shipments_page
from modules.setup_console import render_setup_console
from modules.system_health import render_system_health_page
from services.admin_drive_service import AdminDriveService
from services.address_book_service import AddressBookService
from services.auth_service import AuthService, get_bootstrap_primary_admin, is_bootstrap_admin
from services.cache_service import CacheService
from services.cart_service import CartService
from services.config_loader_service import ConfigLoaderService
from services.data_service import DataService
from services.form_service import FormService
from services.gmail_delivery_service import GmailDeliveryService
from services.gmail_queue_service import GmailQueueService
from services.google_oauth_service import GoogleOAuthService
from services.integration_status_service import IntegrationStatusService
from services.language_service import LanguageService
from services.navigation_service import NavigationService
from services.notification_service import NotificationService
from services.order_service import OrderService
from services.page_service import PageService
from services.payment_config_service import PaymentConfigService
from services.payment_service import PaymentService
from services.performance_service import PerformanceService
from services.product_consent_service import ProductConsentService
from services.qr_service import QRService
from services.rbac_service import RBACService
from services.session_service import SessionService
from services.media_service import MediaService
from services.theme_service import ThemeService
from services.user_profile_service import UserProfileService


CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "styles" / "design.css"
COMMERCE_CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "styles" / "commerce.css"
BOOTSTRAP_APP_CONFIG = {
    "default_role": "public_buyer",
    "default_language": "en",
    "default_landing": {
        "platform_admin": "dashboard",
        "public_buyer": "marketplace",
    },
}

_DASHBOARD_VIEWPORT_CSS = """
<style>
.stApp [data-testid="stAppViewContainer"] > .main .block-container {
  max-width: 100% !important;
  padding-top: 0.35rem !important;
  padding-bottom: 0.75rem !important;
}
.stApp [data-testid="stVerticalBlock"] [data-testid="stVerticalBlockBorderWrapper"] {
  padding-top: 0.55rem !important;
  padding-bottom: 0.55rem !important;
}
.stApp [data-testid="stHorizontalBlock"] {
  gap: 0.5rem !important;
}
.stApp [data-testid="stVerticalBlock"] h3 {
  margin-top: 0 !important;
  margin-bottom: 0.15rem !important;
}
.stApp [data-testid="stVerticalBlock"] .stCaption {
  margin-bottom: 0.15rem !important;
}
.stApp [data-testid="stButton"] button {
  min-height: 2.2rem !important;
  padding-top: 0.3rem !important;
  padding-bottom: 0.3rem !important;
}
</style>
"""

_REQUIRED_BUSINESS_FIELDS = ("business_name", "upi_id", "gst_number", "invoice_name")


def _sanitize_cart_rows(items: list[dict]) -> list[dict]:
    return [
        {
            "Product": item.get("product_name", ""),
            "Quantity": item.get("quantity", item.get("qty", 0)),
            "Marketplace Price": item.get("unit_price", item.get("price", 0)),
            "Total": item.get("line_total", 0),
        }
        for item in items
    ]


def _resolve_dataset_names(*, current_route: str, page_definition: dict, role: str, dashboard_cards: list[dict] | None = None) -> list[str]:
    page_type = str(page_definition.get("type", "") or "").strip().lower()
    data_source = str(page_definition.get("data_source", "") or "").strip()
    dataset_names: list[str] = []
    if page_type == "dashboard":
        dashboard_sources = [
            str(card.get("data_source", "")).strip()
            for card in (dashboard_cards or [])
            if str(card.get("data_source", "")).strip()
        ]
        dataset_names.extend(dashboard_sources or ["products", "orders", "payments", "notifications", "shipments", "ledger"])
    elif page_type == "product_grid":
        if data_source:
            dataset_names.append(data_source)
    elif page_type == "manditrade":
        if data_source:
            dataset_names.append(data_source)
    elif page_type == "products_admin":
        dataset_names.extend(["products", "users"])
    elif current_route == "profile":
        dataset_names.extend(["products", "users"])
    elif current_route == "notifications":
        dataset_names.append("notifications")
    elif current_route == "payments":
        dataset_names.extend(["payments", "orders"])
    elif page_type == "ledger_page":
        dataset_names.append("ledger")
    elif page_type == "completed_deliveries_page":
        dataset_names.extend(["shipments", "orders"])
    elif current_route == "shipments":
        dataset_names.extend(["shipments", "orders", "users"])
    elif page_type in {"crud_table", "table"}:
        if data_source:
            dataset_names.append(data_source)
        if current_route == "orders":
            dataset_names.extend(["products", "shipments", "payments"])
    elif page_type == "admin_configuration":
        dataset_names.append("users")
    elif page_type == "system" and role == "platform_admin":
        dataset_names.extend(["users", "products", "orders", "notifications", "gmail_queue", "audit_logs"])
    unique_names: list[str] = []
    seen = set()
    for name in dataset_names:
        normalized = str(name or "").strip()
        if normalized and normalized not in seen:
            unique_names.append(normalized)
            seen.add(normalized)
    return unique_names


def _load_route_datasets(
    data_service: DataService,
    *,
    current_route: str,
    page_definition: dict,
    role: str,
    dashboard_cards: list[dict] | None = None,
) -> dict[str, list[dict]]:
    datasets: dict[str, list[dict]] = {}
    for name in _resolve_dataset_names(
        current_route=current_route,
        page_definition=page_definition,
        role=role,
        dashboard_cards=dashboard_cards,
    ):
        datasets[name] = data_service.list_collection(name)
    return datasets


def _render_marketplace_cart_editor(cart_service: CartService, translator, *, key_prefix: str = "marketplace_editor") -> None:
    t = translator.t if translator else (lambda key: key)
    cart = cart_service.get_cart()
    for index, item in enumerate(list(cart.get("items", []))):
        product_id = str(item.get("product_id", "")).strip()
        widget_suffix = str(item.get("cart_item_key", "")).strip() or product_id or f"row_{index}"
        item_cols = st.columns([3, 1.2, 1.2, 1.2, 0.8])
        item_cols[0].markdown(f"**{item.get('product_name', '')}**")
        updated_quantity = item_cols[1].number_input(
            t("field.quantity"),
            min_value=1.0,
            step=1.0,
            value=float(item.get("quantity", 1) or 1),
            key=f"{key_prefix}_cart_quantity_{widget_suffix}_{index}",
        )
        if float(updated_quantity or 1) != float(item.get("quantity", 1) or 1):
            cart_service.set_quantity(product_id, updated_quantity)
            st.rerun()
        item_cols[2].write(f"{float(item.get('unit_price', 0) or 0):g}")
        item_cols[3].write(f"{float(item.get('line_total', 0) or 0):g}")
        if item_cols[4].button("X", key=f"{key_prefix}_cart_remove_{widget_suffix}_{index}", use_container_width=True):
            cart_service.remove_item(product_id)
            st.rerun()


def _render_payment_pending_panel(payment_record: dict) -> None:
    qr_service = QRService()
    st.markdown("### Payment Pending")
    st.caption(f"Order Reference: {payment_record.get('payment_reference', '')}")
    st.write(f"Amount: Rs. {payment_record.get('amount_payable', payment_record.get('amount_due', 0))}")
    st.write("Payment Method: UPI")
    upi_link = str(payment_record.get("upi_link", "") or "").strip()
    qr_bytes = qr_service.build_qr_png_bytes(payment_record.get("qr_payload", "") or upi_link)
    if qr_bytes:
        st.image(qr_bytes, width=220)
    if upi_link:
        st.link_button("Pay in UPI App", upi_link, use_container_width=True)
    st.code(upi_link)
    st.caption("Pay using this QR/UPI link. Keep the payment note/reference unchanged.")


def _format_saved_address(address: dict) -> str:
    label = str(address.get("label", "")).strip() or "Saved Address"
    location = ", ".join(
        part
        for part in [
            str(address.get("address_line_1", "")).strip(),
            str(address.get("city", "")).strip(),
            str(address.get("state", "")).strip(),
            str(address.get("pin_code", "")).strip(),
        ]
        if part
    )
    return f"{label} - {location}" if location else label


def _sync_checkout_address_state(*, key_prefix: str, selected_address: dict) -> None:
    field_map = {
        f"{key_prefix}_address_label": str(selected_address.get("label", "") or ""),
        f"{key_prefix}_address_1": str(selected_address.get("address_line_1", "") or ""),
        f"{key_prefix}_address_2": str(selected_address.get("address_line_2", "") or ""),
        f"{key_prefix}_city": str(selected_address.get("city", "") or ""),
        f"{key_prefix}_state": str(selected_address.get("state", "") or ""),
        f"{key_prefix}_pin": str(selected_address.get("pin_code", "") or ""),
        f"{key_prefix}_landmark": str(selected_address.get("landmark", "") or ""),
    }
    for state_key, value in field_map.items():
        st.session_state[state_key] = value


def _initialize_checkout_contact_state(*, key_prefix: str, display_name: str, mobile: str) -> None:
    st.session_state.setdefault(f"{key_prefix}_name", str(display_name or "").strip())
    st.session_state.setdefault(f"{key_prefix}_mobile", str(mobile or "").strip())


def _render_checkout_details_form(*, key_prefix: str, email: str, user_record: dict, user_profile: dict, address_book_service: AddressBookService, translator) -> dict:
    t = translator.t if translator else (lambda key: key)
    st.markdown(f"### {t('ui.checkout_details')}")
    st.markdown(f"#### {t('ui.buyer_contact')}")
    _initialize_checkout_contact_state(
        key_prefix=key_prefix,
        display_name=str(user_profile.get("display_name", "") or user_record.get("display_name", "") or "").strip(),
        mobile=str(user_profile.get("mobile", "") or user_record.get("mobile", "") or "").strip(),
    )
    saved_addresses = address_book_service.list_addresses(email)
    name = st.text_input(t("ui.full_name"), key=f"{key_prefix}_name")
    mobile = st.text_input(t("ui.mobile_number"), key=f"{key_prefix}_mobile")
    st.text_input(t("ui.email"), value=email, disabled=True, key=f"{key_prefix}_email")
    st.markdown(f"#### {t('ui.delivery_address')}")
    address_options = ["__new__"] + [str(address.get("address_id", "")).strip() for address in saved_addresses]
    selected_address_id = st.selectbox(
        t("ui.saved_addresses"),
        options=address_options,
        format_func=lambda value: (
            t("ui.add_new_address")
            if value == "__new__"
            else _format_saved_address(
                next((address for address in saved_addresses if str(address.get("address_id", "")).strip() == value), {})
            )
        ),
        key=f"{key_prefix}_saved_address",
    )
    selected_address = next(
        (address for address in saved_addresses if str(address.get("address_id", "")).strip() == selected_address_id),
        {},
    )
    last_loaded_key = f"{key_prefix}_last_loaded_address_id"
    if st.session_state.get(last_loaded_key) != selected_address_id:
        _sync_checkout_address_state(key_prefix=key_prefix, selected_address=selected_address if selected_address_id != "__new__" else {})
        st.session_state[last_loaded_key] = selected_address_id
    address_label = st.text_input(t("ui.address_label"), key=f"{key_prefix}_address_label", placeholder=t("ui.address_label_placeholder"))
    address_line_1 = st.text_input(t("ui.address_line_1"), key=f"{key_prefix}_address_1")
    address_line_2 = st.text_input(t("ui.address_line_2"), key=f"{key_prefix}_address_2")
    city = st.text_input(t("ui.city"), key=f"{key_prefix}_city")
    state = st.text_input(t("ui.state"), key=f"{key_prefix}_state")
    pin_code = st.text_input(t("ui.pin_code"), key=f"{key_prefix}_pin")
    landmark = st.text_input(t("ui.landmark"), key=f"{key_prefix}_landmark")
    save_address = st.checkbox(t("ui.save_address_for_future"), value=True, key=f"{key_prefix}_save_address")
    st.markdown(f"#### {t('ui.payment_method')}")
    st.selectbox(t("ui.payment_method"), options=[t("ui.upi_qr_upi_link")], key=f"{key_prefix}_payment_method")
    return {
        "name": name.strip(),
        "mobile": mobile.strip(),
        "address_id": "" if selected_address_id == "__new__" else selected_address_id,
        "address_label": address_label.strip(),
        "save_address": bool(save_address),
        "delivery_address": {
            "address_line_1": address_line_1.strip(),
            "address_line_2": address_line_2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
            "landmark": landmark.strip(),
        },
    }


def _profile_business_completion_status(user_profile: dict) -> tuple[bool, list[str]]:
    details = dict((user_profile or {}).get("details", {}) or {})
    missing = [field for field in _REQUIRED_BUSINESS_FIELDS if not str(details.get(field, "")).strip()]
    return (not missing, missing)


def _render_checkout_business_profile_form(*, key_prefix: str, user_profile: dict) -> dict:
    details = dict((user_profile or {}).get("details", {}) or {})
    st.markdown("#### Business Details")
    st.caption("Complete your business profile to continue with this B2B checkout.")
    business_name = st.text_input("Business Name", key=f"{key_prefix}_business_name", value=str(details.get("business_name", "") or ""))
    gst_number = st.text_input("GST Number", key=f"{key_prefix}_gst_number", value=str(details.get("gst_number", "") or ""))
    upi_id = st.text_input("UPI ID", key=f"{key_prefix}_upi_id", value=str(details.get("upi_id", "") or ""))
    invoice_name = st.text_input("Invoice Name", key=f"{key_prefix}_invoice_name", value=str(details.get("invoice_name", "") or ""))
    invoice_address = st.text_area("Invoice Address", key=f"{key_prefix}_invoice_address", value=str(details.get("invoice_address", "") or ""), height=80)
    invoice_phone = st.text_input("Invoice Contact Phone", key=f"{key_prefix}_invoice_phone", value=str(details.get("invoice_phone", "") or ""))
    bank_account_name = st.text_input("Bank Account Name", key=f"{key_prefix}_bank_account_name", value=str(details.get("bank_account_name", "") or ""))
    bank_account_number = st.text_input("Bank Account Number", key=f"{key_prefix}_bank_account_number", value=str(details.get("bank_account_number", "") or ""))
    bank_ifsc = st.text_input("Bank IFSC", key=f"{key_prefix}_bank_ifsc", value=str(details.get("bank_ifsc", "") or ""))
    other_details = st.text_area("Other Details", key=f"{key_prefix}_other_details", value=str(details.get("other_details", "") or ""), height=80)
    business_details = {
        "business_name": business_name.strip(),
        "gst_number": gst_number.strip(),
        "upi_id": upi_id.strip(),
        "invoice_name": invoice_name.strip(),
        "invoice_address": invoice_address.strip(),
        "invoice_phone": invoice_phone.strip(),
        "bank_account_name": bank_account_name.strip(),
        "bank_account_number": bank_account_number.strip(),
        "bank_ifsc": bank_ifsc.strip(),
        "other_details": other_details.strip(),
    }
    missing = [field for field in _REQUIRED_BUSINESS_FIELDS if not business_details.get(field, "").strip()]
    business_details["profile_completed"] = not missing
    return {"details": business_details, "missing": missing}


def _get_bootstrap_primary_admin() -> dict:
    primary_admin = get_bootstrap_primary_admin()
    return {
        "email": primary_admin.get("email", ""),
        "display_name": primary_admin.get("display_name", "Primary Admin"),
    }


def _resolve_bootstrap_user(email: str) -> dict:
    primary_admin = _get_bootstrap_primary_admin()
    normalized_email = str(email).strip().lower()
    if primary_admin["email"] and normalized_email == primary_admin["email"]:
        return {
            "email": normalized_email,
            "role": "platform_admin",
            "status": "ACTIVE",
            "display_name": primary_admin["display_name"],
            "known_user": True,
            "is_primary_admin": True,
        }
    return {
        "email": normalized_email,
        "role": "public_buyer",
        "status": "ACTIVE",
        "display_name": normalized_email.split("@")[0] if normalized_email else "",
        "known_user": False,
        "is_primary_admin": False,
    }


def _resolve_authenticated_user(email: str) -> dict:
    normalized_email = str(email or "").strip().lower()
    bootstrap_user = _resolve_bootstrap_user(normalized_email)
    try:
        bootstrap_loader = ConfigLoaderService()
        bootstrap_cache = CacheService(bootstrap_loader)
        bootstrap_cache.refresh_cache()
        resolved = AuthService(bootstrap_cache).resolve_user(normalized_email)
        return {
            **resolved,
            "landing_page": "dashboard" if resolved.get("role") == "platform_admin" else "marketplace",
        }
    except Exception:
        return {
            **bootstrap_user,
            "landing_page": "dashboard" if bootstrap_user.get("role") == "platform_admin" else "marketplace",
        }


def _render_bootstrap_login(oauth_service: GoogleOAuthService, session_service: SessionService) -> None:
    render_login_page(
        auth_service=None,
        oauth_service=oauth_service,
        translator=type("BootstrapTranslator", (), {"t": staticmethod(lambda key: key)})(),
        language_options=["en"],
        current_language=session_service.get_language(),
        set_language=session_service.set_language,
        language_option_labels={"en": "English"},
        status_eyebrow="Bootstrap",
        status_title="Platform setup is waiting for the primary admin",
        status_body="The fixed Google Drive root and seed package must be available before the workspace opens for everyone else.",
        access_title="Admin-first access",
        access_body="The configured superadmin signs in through this same page, uploads the seed, and activates the runtime for all users.",
        show_unknown_user_note=False,
    )

def _render_missing_files_screen(drive_manifest: dict, session_service: SessionService, admin_drive_service: AdminDriveService) -> None:
    user = session_service.get_user()
    current_email = str(user.get("email", "")).strip().lower()
    bootstrap_admin = is_bootstrap_admin(current_email)
    is_admin = bool(user.get("is_authenticated")) and (
        str(user.get("role", "")).strip().lower() == "platform_admin" or bootstrap_admin
    )
    root_missing = not str(drive_manifest.get("root_folder_id", "") or "").strip()
    admin_email = str(get_bootstrap_primary_admin().get("email", "") or "").strip().lower()
    if is_admin:
        if root_missing:
            st.warning(
                "Google Drive root is not initialized yet. "
                "Use the setup console below to create the root and load the bootstrap seed in live or dummy mode."
            )
        render_setup_console(admin_drive_service, drive_manifest, translator=None)
    elif user.get("is_authenticated"):
        st.error(
            "Platform is initializing and is currently available only to the superadmin. "
            f"Please contact {admin_email or 'the configured admin'} after bootstrap is completed."
        )
        if root_missing:
            st.info("Waiting for Google Drive root setup and bootstrap seed sync.")
        else:
            render_table(drive_manifest.get("required_files", []), caption="Required Drive files")
    else:
        if root_missing:
            st.warning(
                "Platform bootstrap is pending. "
                f"Only the configured superadmin ({admin_email or 'admin'}) can complete first-time setup."
            )
        else:
            st.warning("Google Drive runtime is missing required JSON files.")
        _render_bootstrap_login(GoogleOAuthService(), session_service)


def _filter_role_rows(route: str, rows: list[dict], role: str, user_email: str) -> list[dict]:
    normalized_email = str(user_email).strip().lower()
    if role == "platform_admin":
        return rows
    if route == "orders":
        if role == "merchant":
            return [
                row
                for row in rows
                if (
                    normalized_email in {
                        str(row.get("buyer_email", "")).strip().lower(),
                        str(row.get("requester_email", "")).strip().lower(),
                        str(row.get("requesting_user_email", "")).strip().lower(),
                    }
                    or str(row.get("owner_email", "")).strip().lower() == normalized_email
                )
            ]
        if role in {"public_buyer", "client_buyer"}:
            return [
                row
                for row in rows
                if normalized_email in {
                    str(row.get("buyer_email", "")).strip().lower(),
                    str(row.get("requester_email", "")).strip().lower(),
                    str(row.get("requesting_user_email", "")).strip().lower(),
                }
            ]
        return [
            row
            for row in rows
            if normalized_email in {
                str(row.get("buyer_email", "")).strip().lower(),
                str(row.get("requester_email", "")).strip().lower(),
                str(row.get("requesting_user_email", "")).strip().lower(),
                str(row.get("owner_email", "")).strip().lower(),
            }
        ]
    if route == "ledger":
        return [
            row
            for row in rows
            if normalized_email in {
                str(((row.get("party_a") or {}).get("email", ""))).strip().lower(),
                str(((row.get("party_b") or {}).get("email", ""))).strip().lower(),
                str(((row.get("party_admin") or {}).get("email", ""))).strip().lower(),
                str(((row.get("party_owner") or {}).get("email", ""))).strip().lower(),
            }
        ]
    if route == "notifications":
        normalized_role = str(role or "").strip().lower()
        return [
            row
            for row in rows
            if (
                str(row.get("to_email", "")).strip().lower() == normalized_email
                or normalized_email in {
                    str(recipient or "").strip().lower()
                    for recipient in (row.get("recipients", []) or [])
                    if str(recipient or "").strip()
                }
                or (
                    normalized_role == "merchant"
                    and str(row.get("to_role", "")).strip().lower() == "merchant"
                    and str(row.get("owner_email", "")).strip().lower() == normalized_email
                )
            )
        ]
    if route == "shipments":
        return [
            row
            for row in rows
            if normalized_email in {
                str(row.get("owner_email", "")).strip().lower(),
                str(row.get("buyer_email", "")).strip().lower(),
                str(row.get("requester_email", "")).strip().lower(),
                str(row.get("delivery_partner_email", "")).strip().lower(),
            }
        ]
    return rows


def _build_superadmin_role_switcher_options(*, cache_service: CacheService, translator, navigation_service: NavigationService) -> list[dict]:
    users_payload = cache_service.get_config("users")
    user_rows = list(users_payload.get("users", []))
    seen_roles: set[str] = set()
    options: list[dict] = [
        {
            "label": "My Superadmin View",
            "value": "__self__",
            "role": "platform_admin",
            "email": "",
            "display_name": "My Superadmin View",
            "landing_page": navigation_service.get_default_route("platform_admin"),
        }
    ]
    for row in user_rows:
        role = str(row.get("role", "")).strip().lower()
        email = str(row.get("email", "")).strip().lower()
        if not role or not email or role == "platform_admin" or role in seen_roles:
            continue
        seen_roles.add(role)
        options.append(
            {
                "label": f"{translator.t(f'role.{role}')} View",
                "value": email,
                "role": role,
                "email": email,
                "display_name": str(row.get("display_name", email.split("@")[0])),
                "landing_page": navigation_service.get_default_route(role),
            }
        )
    return options


def _render_root_setup_console(session_service: SessionService, admin_drive_service: AdminDriveService, errors: list[str]) -> None:
    user = session_service.get_user()
    current_email = str(user.get("email", "")).strip().lower()
    bootstrap_admin = is_bootstrap_admin(current_email)
    is_admin = bool(user.get("is_authenticated")) and (
        str(user.get("role", "")).strip().lower() == "platform_admin" or bootstrap_admin
    )
    if is_admin:
        st.warning("Drive setup incomplete. Root folder is missing or unreachable.")
        for error in errors:
            st.caption(error)
        render_setup_console(
            admin_drive_service,
            {
                "connected": True,
                "root_folder_id": "",
                "root_folder_name": admin_drive_service.FIXED_ROOT_FOLDER_NAME,
                "required_folders": [],
                "missing_folders": [admin_drive_service.FIXED_ROOT_FOLDER_NAME],
                "required_files": [],
                "missing_files": [],
            },
            translator=None,
        )
    elif user.get("is_authenticated"):
        st.error("Platform setup is incomplete. Please contact admin.")
    else:
        _render_bootstrap_login(GoogleOAuthService(), session_service)


def render_app() -> None:
    inject_css(CSS_FILE)
    inject_css(COMMERCE_CSS_FILE)
    session_service = SessionService(BOOTSTRAP_APP_CONFIG)
    oauth_service = GoogleOAuthService()
    admin_drive_service = AdminDriveService()
    performance_service = PerformanceService()

    callback_error = oauth_service.get_callback_error()
    if callback_error:
        st.error("Google sign-in failed.")
        oauth_service.clear_callback_params(preserve={"lang": session_service.get_language()})

    if oauth_service.has_callback() and not session_service.is_authenticated():
        try:
            identity = oauth_service.exchange_code_for_identity()
            if not identity.get("email_verified", False):
                raise ValueError("Google account email is not verified.")
            selected_language = str(identity.get("selected_language", "") or session_service.get_language() or "en").strip().lower() or "en"
            session_service.set_language(selected_language)
            resolved_user = _resolve_authenticated_user(str(identity.get("email", "")))
            oauth_service.persist_admin_token(identity, resolved_user)
            session_service.authenticate(
                {
                    **resolved_user,
                    "display_name": identity.get("display_name") or resolved_user.get("display_name", ""),
                    "photo_url": identity.get("photo_url", ""),
                    "oauth_token": identity.get("oauth_token", {}),
                    "language": selected_language,
                    "landing_page": resolved_user.get("landing_page", "marketplace"),
                }
            )
            admin_drive_service.clear_runtime_cache(clear_validation=True, clear_file_index=False)
            oauth_service.clear_callback_params(preserve={"lang": selected_language})
            st.rerun()
        except Exception as exc:
            st.error(f"Google sign-in failed: {exc}")
            oauth_service.clear_callback_params(preserve={"lang": session_service.get_language()})

    with performance_service.measure("drive_validation"):
        drive_manifest = admin_drive_service.get_runtime_manifest()
    if session_service.is_authenticated() and (drive_manifest.get("missing_files") or not drive_manifest.get("connected", False)):
        drive_manifest = admin_drive_service.get_runtime_manifest(force_refresh=True)
    if not drive_manifest.get("connected", False):
        if not session_service.is_authenticated():
            _render_bootstrap_login(oauth_service, session_service)
            return
        errors = drive_manifest.get("errors", [])
        if any("root folder" in str(error).lower() for error in errors):
            _render_root_setup_console(session_service, admin_drive_service, errors)
            return
        st.error("Google Drive is not connected.\n\nExpected:\nMANDITRADE_DB root folder from Google Drive.\n\nFix:\nCheck Google OAuth token and Drive permissions.")
        for error in errors:
            st.code(error)
        return

    if drive_manifest.get("missing_files"):
        _render_missing_files_screen(drive_manifest, session_service, admin_drive_service)
        return

    config_loader = ConfigLoaderService()
    cache_service = CacheService(config_loader)
    if not st.session_state.get(cache_service.cache_key):
        with performance_service.measure("cache_load"):
            cache_service.load_core_configs()
    app_config = cache_service.get_config("app_config")
    ui_config = dict((app_config.get("ui") or {}))

    session_service = SessionService(app_config)
    language = session_service.get_language()
    language_service = LanguageService(cache_service, language)
    translator = language_service.get_translator()
    auth_service = AuthService(cache_service)
    rbac_service = RBACService(cache_service)
    navigation_service = NavigationService(cache_service, translator, rbac_service)
    page_service = PageService(cache_service, translator, rbac_service)

    if session_service.is_authenticated():
        current_user = session_service.get_authenticated_user()
        resolved_user = auth_service.resolve_user(current_user.get("email", ""))
        resolved_role = str(resolved_user.get("role", auth_service.get_unknown_user_default_role()))
        landing_page = navigation_service.get_default_route(resolved_role)
        if resolved_role != current_user.get("role") or current_user.get("landing_page") != landing_page:
            session_service.authenticate(
                {
                    **resolved_user,
                    "display_name": current_user.get("display_name") or resolved_user.get("display_name", ""),
                    "photo_url": current_user.get("photo_url", ""),
                    "oauth_token": current_user.get("oauth_token", {}),
                    "landing_page": landing_page,
                }
            )

    if not session_service.is_authenticated():
        render_login_page(
            auth_service=auth_service,
            oauth_service=oauth_service,
            translator=translator,
            language_options=language_service.get_available_languages(),
            current_language=language,
            set_language=session_service.set_language,
            language_option_labels=language_service.get_language_option_labels(),
        )
        return

    authenticated_user = session_service.get_authenticated_user()
    role = session_service.get_user_role()
    user = session_service.get_user()
    current_user_email = str(user.get("email", "") or "").strip().lower()
    authenticated_email = str(authenticated_user.get("email", "") or "").strip().lower()
    is_superadmin = is_bootstrap_admin(authenticated_email)
    role_switcher_options: list[dict] = []
    current_role_view = "__self__"
    theme_service = ThemeService(admin_drive_service, cache_service)
    theme_css = theme_service.build_background_css()
    if theme_css:
        inject_inline_css(theme_css)
    else:
        theme_warning = theme_service.get_background_style().get("warning", "")
        if theme_warning and role == "platform_admin":
            st.warning(theme_warning)
    with performance_service.measure("navigation_render"):
        navigation_items = navigation_service.get_navigation(role)
    current_route = session_service.get_current_route_or_landing()
    valid_routes = [item.get("route", "") for item in navigation_items]
    if not navigation_items:
        st.error(translator.t("auth.access_denied"))
        return
    if current_route not in valid_routes or not rbac_service.can_access(role, current_route):
        current_route = page_service.get_landing_page(role, navigation_service)
        session_service.set_route(current_route)
    if str(authenticated_user.get("role", "")).strip().lower() == "platform_admin" or is_superadmin:
        role_switcher_options = _build_superadmin_role_switcher_options(
            cache_service=cache_service,
            translator=translator,
            navigation_service=navigation_service,
        )
        effective_user = st.session_state.get(SessionService.EFFECTIVE_USER_KEY)
        if isinstance(effective_user, dict) and effective_user.get("is_authenticated"):
            current_role_view = str(effective_user.get("email", "") or "__self__").strip().lower() or "__self__"
    chosen, selected_role_view = render_sidebar(
        navigation_items,
        current_route,
        user=user,
        role_label=translator.t(f"role.{role}"),
        theme_service=theme_service,
        language_options=language_service.get_available_languages(),
        language_option_labels=language_service.get_language_option_labels(),
        current_language=session_service.get_language(),
        language_label=translator.t("auth.language"),
        set_language=session_service.set_language,
        role_switcher_options=role_switcher_options,
        current_role_view=current_role_view,
    )
    if role_switcher_options and str(selected_role_view or "__self__") != str(current_role_view or "__self__"):
        if selected_role_view == "__self__":
            session_service.clear_effective_user()
        else:
            selected_option = next(
                (option for option in role_switcher_options if str(option.get("value", "__self__")) == str(selected_role_view)),
                None,
            )
            if selected_option:
                session_service.set_effective_user(
                    {
                        "email": selected_option.get("email", ""),
                        "role": selected_option.get("role", "public_buyer"),
                        "status": "ACTIVE",
                        "display_name": selected_option.get("display_name", ""),
                        "landing_page": selected_option.get("landing_page", "marketplace"),
                    }
                )
        st.rerun()
    if chosen != current_route:
        session_service.set_route(chosen)
        st.rerun()
    with st.sidebar:
        if st.button(translator.t("auth.logout"), use_container_width=True):
            session_service.logout()
            st.rerun()

    render_topbar(
        app_name=app_config.get("app_name", "MandiTrade Next"),
        version=app_config.get("version", "0.1.0"),
        role_label=translator.t(f"role.{role}"),
        language=language,
        translator=translator,
    )

    page_definition = page_service.get_page_definition(current_route, role)
    if not rbac_service.can_access(role, current_route):
        current_route = page_service.get_landing_page(role, navigation_service)
        session_service.set_route(current_route)
        page_definition = page_service.get_page_definition(current_route, role)
        st.warning(translator.t("auth.access_denied"))
    dashboard_cards = []
    if page_definition.get("type") == "dashboard":
        inject_inline_css(_DASHBOARD_VIEWPORT_CSS)
        dashboard_cards = cache_service.get_config("dashboards").get("dashboards", {}).get(role, {}).get("cards", [])
        render_template(
            "page_hero.html",
            role_label=translator.t(f"role.{role}"),
            title=translator.t(page_definition.get("title_key", "")),
            subtitle="",
            variant_class="mt-page-hero--dashboard",
        )
    else:
        render_template(
            "page_hero.html",
            role_label=translator.t(f"role.{role}"),
            title=translator.t(page_definition.get("title_key", "")),
            subtitle=translator.t(page_definition.get("subtitle_key", "")),
            variant_class="",
        )

    data_service = DataService(cache_service)
    datasets = _load_route_datasets(
        data_service,
        current_route=current_route,
        page_definition=page_definition,
        role=role,
        dashboard_cards=dashboard_cards,
    )

    if page_definition.get("type") == "dashboard":
        render_dashboard_cards(dashboard_cards, datasets, translator, current_user=user)
    elif page_definition.get("type") == "product_grid":
        media_service = MediaService(admin_drive_service)
        notification_service = NotificationService(data_service)
        order_service = OrderService(data_service, notification_service)
        address_book_service = AddressBookService(data_service)
        user_profile_service = UserProfileService(data_service)
        cart_service = CartService()
        user_profile = user_profile_service.get_profile(user.get("email", ""))
        products = page_service.filter_rows(datasets.get(page_definition.get("data_source", ""), []), page_definition.get("filters", {}))
        payment_config = order_service.payment_service.get_payment_config()
        st.session_state.setdefault("mt_marketplace_stage", "browse")

        def on_add_to_cart(product: dict) -> None:
            try:
                cart_service.add_to_cart(product)
                st.session_state["mt_marketplace_stage"] = "browse"
                notification_service.create_notification(
                    to_email=session_service.get_user().get("email", ""),
                    title=translator.t("notification.product_added.title"),
                    message=translator.t("notification.product_added.message"),
                    event_type="PRODUCT_ADDED",
                    source_entity="product",
                    source_id=product.get("product_id", ""),
                    created_by=session_service.get_user().get("email", ""),
                )
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.session_state["mt_marketplace_notice"] = (
                    f"Added {product.get('product_name', product.get('product_id', 'product'))} to cart."
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        cart = cart_service.get_cart()
        notice_message = str(st.session_state.pop("mt_marketplace_notice", "") or "").strip()
        if notice_message:
            st.success(notice_message)
        current_stage = str(st.session_state.get("mt_marketplace_stage", "browse") or "browse")
        if not cart.get("items"):
            st.session_state["mt_marketplace_stage"] = "browse"
            st.session_state["mt_marketplace_checkout_open"] = False
            current_stage = "browse"

        if cart.get("items"):
            flow_cols = st.columns([2.2, 1, 1], gap="small")
            flow_cols[0].caption(
                f"Shopping Flow: {len(cart.get('items', []))} items in cart | Total Rs. {cart_service.calculate_total():g}"
            )
            if flow_cols[1].button("View Cart", use_container_width=True, key="marketplace_view_cart"):
                st.session_state["mt_marketplace_stage"] = "cart"
                st.rerun()
            if current_stage != "browse" and flow_cols[2].button("Continue Shopping", use_container_width=True, key="marketplace_continue_shopping"):
                st.session_state["mt_marketplace_stage"] = "browse"
                st.session_state["mt_marketplace_checkout_open"] = False
                st.rerun()

        if current_stage == "browse":
            render_marketplace_page(products, on_add_to_cart=on_add_to_cart, media_service=media_service, translator=translator, ui_config=ui_config)

        if cart.get("items") and current_stage in {"cart", "checkout"}:
            st.markdown("### Cart and Checkout")
            cart_cols = st.columns([2.5, 1], gap="large")
            with cart_cols[0]:
                with st.container(border=True):
                    st.subheader(translator.t("ui.cart"))
                    _render_marketplace_cart_editor(cart_service, translator, key_prefix=f"marketplace_{current_stage}")
                if st.session_state.get("mt_marketplace_checkout_open", False):
                    with st.container(border=True):
                        render_checkout_steps(
                            title="Checkout",
                            item_count=len(cart.get("items", [])),
                            total_amount=cart_service.calculate_total(),
                        )
                        checkout = _render_checkout_details_form(
                            key_prefix="marketplace_checkout",
                            email=session_service.get_user().get("email", ""),
                            user_record=user,
                            user_profile=user_profile,
                            address_book_service=address_book_service,
                            translator=translator,
                        )
                        if st.button(translator.t("ui.confirm_order"), use_container_width=True, key="marketplace_confirm_order"):
                            if not checkout["name"] or not checkout["mobile"] or not checkout["delivery_address"]["address_line_1"] or not checkout["delivery_address"]["city"] or not checkout["delivery_address"]["state"] or not checkout["delivery_address"]["pin_code"]:
                                st.error(translator.t("ui.complete_contact_address"))
                            else:
                                try:
                                    product_lookup = {str(product.get("product_id", "")).strip(): product for product in products}
                                    order = order_service.create_marketplace_order_with_checkout(
                                        items=cart["items"],
                                        buyer_email=session_service.get_user().get("email", ""),
                                        buyer_name=checkout["name"],
                                        buyer_mobile=checkout["mobile"],
                                        delivery_address=checkout["delivery_address"],
                                        product_lookup=product_lookup,
                                    )
                                    address_book_service.get_or_create_user_record(
                                        email=session_service.get_user().get("email", ""),
                                        role=user.get("role", "public_buyer"),
                                        display_name=checkout["name"],
                                        mobile=checkout["mobile"],
                                    )
                                    user_profile_service.get_or_create_profile(
                                        email=session_service.get_user().get("email", ""),
                                        role=user.get("role", "public_buyer"),
                                        display_name=checkout["name"],
                                        mobile=checkout["mobile"],
                                    )
                                    if checkout.get("save_address", False):
                                        address_book_service.save_address(
                                            email=session_service.get_user().get("email", ""),
                                            role=user.get("role", "public_buyer"),
                                            display_name=checkout["name"],
                                            mobile=checkout["mobile"],
                                            address=checkout["delivery_address"],
                                            address_id=checkout.get("address_id", ""),
                                            label=checkout.get("address_label", ""),
                                        )
                                    else:
                                        user_profile_service.save_profile(
                                            actor_email=session_service.get_user().get("email", ""),
                                            actor_role=user.get("role", "public_buyer"),
                                            target_email=session_service.get_user().get("email", ""),
                                            updates={
                                                "display_name": checkout["name"],
                                                "mobile": checkout["mobile"],
                                            },
                                        )
                                    order_service.persist_order_storage(order)
                                    user_profile_service.sync_order_record(order=order)
                                    data_service.persist_collection("users")
                                    data_service.persist_collection("payments")
                                    data_service.persist_collection("notifications")
                                    data_service.persist_collection("gmail_queue")
                                    cart_service.clear_cart()
                                    st.session_state["mt_marketplace_checkout_open"] = False
                                    st.session_state["mt_marketplace_stage"] = "browse"
                                    st.session_state["mt_last_payment_record_id"] = order.get("payment_id", "")
                                    st.success(f"Order {order.get('order_id', '')} created.")
                                    payment_record = next(
                                        (row for row in data_service.get_collection_ref("payments") if str(row.get("payment_id", "")).strip() == str(order.get("payment_id", "")).strip()),
                                        {},
                                    )
                                    _render_payment_pending_panel(payment_record)
                                except Exception as exc:
                                    st.error(str(exc))
            with cart_cols[1]:
                checkout_requested = render_cart_panel(cart, cart_service=cart_service, route="marketplace", translator=translator)
                if not payment_config.get("enabled", False):
                    st.error("Payment config missing or disabled. Checkout is unavailable.")
                else:
                    if checkout_requested:
                        st.session_state["mt_marketplace_checkout_open"] = True
                        st.session_state["mt_marketplace_stage"] = "checkout"
                        st.rerun()
    elif page_definition.get("type") == "manditrade":
        media_service = MediaService(admin_drive_service)
        notification_service = NotificationService(data_service)
        order_service = OrderService(data_service, notification_service)
        address_book_service = AddressBookService(data_service)
        user_profile_service = UserProfileService(data_service)
        cart_service = CartService("mt_next_manditrade_cart")
        user_profile = user_profile_service.get_profile(user.get("email", ""))
        products = page_service.filter_rows(datasets.get(page_definition.get("data_source", ""), []), page_definition.get("filters", {}))
        payment_config = order_service.payment_service.get_payment_config()

        def on_request(product: dict) -> None:
            try:
                rules = order_service.get_channel_quantity_rules(product, "manditrade")
                cart_service.add_to_cart(product, channel="manditrade", quantity=float(rules.get("minimum_quantity", 1) or 1))
                st.session_state["mt_manditrade_stage"] = "browse"
                st.session_state["mt_manditrade_notice"] = (
                    f"Added {product.get('product_name', product.get('product_id', 'product'))} to bulk cart."
                )
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        render_manditrade_page(products, on_request=on_request, media_service=media_service, translator=translator, ui_config=ui_config)
        cart = cart_service.get_cart()
        notice_message = str(st.session_state.pop("mt_manditrade_notice", "") or "").strip()
        if notice_message:
            st.success(notice_message)
        current_manditrade_stage = str(st.session_state.get("mt_manditrade_stage", "browse") or "browse")
        if not cart.get("items"):
            st.session_state["mt_manditrade_stage"] = "browse"
            current_manditrade_stage = "browse"
        if cart.get("items"):
            flow_cols = st.columns([2.2, 1, 1], gap="small")
            flow_cols[0].caption(
                f"Bulk cart: {len(cart.get('items', []))} products | Total Rs. {cart_service.calculate_total():g}"
            )
            if flow_cols[1].button("View Cart", use_container_width=True, key="manditrade_view_cart"):
                st.session_state["mt_manditrade_stage"] = "cart"
                st.rerun()
            if current_manditrade_stage != "browse" and flow_cols[2].button("Continue Shopping", use_container_width=True, key="manditrade_continue_shopping"):
                st.session_state["mt_manditrade_stage"] = "browse"
                st.session_state["mt_manditrade_checkout_open"] = False
                st.rerun()

        if cart.get("items") and current_manditrade_stage in {"cart", "checkout"}:
            st.markdown("### Bulk Cart and Checkout")
            cart_cols = st.columns([2.5, 1], gap="large")
            with cart_cols[0]:
                with st.container(border=True):
                    st.subheader("Bulk Cart")
                    _render_marketplace_cart_editor(cart_service, translator, key_prefix=f"manditrade_{current_manditrade_stage}")
                if st.session_state.get("mt_manditrade_checkout_open", False):
                    with st.container(border=True):
                        render_checkout_steps(
                            title="Bulk order checkout",
                            item_count=len(cart.get("items", [])),
                            total_amount=cart_service.calculate_total(),
                        )
                        checkout = _render_checkout_details_form(
                            key_prefix="manditrade_checkout",
                            email=session_service.get_user().get("email", ""),
                            user_record=user,
                            user_profile=user_profile,
                            address_book_service=address_book_service,
                            translator=translator,
                        )
                        profile_complete, missing_profile_fields = _profile_business_completion_status(user_profile)
                        business_profile = {"details": {}, "missing": []}
                        if not profile_complete:
                            business_profile = _render_checkout_business_profile_form(
                                key_prefix="manditrade_business_profile",
                                user_profile=user_profile,
                            )
                        if st.button(translator.t("ui.confirm_order"), use_container_width=True, key="manditrade_confirm_order"):
                            if not checkout["name"] or not checkout["mobile"] or not checkout["delivery_address"]["address_line_1"] or not checkout["delivery_address"]["city"] or not checkout["delivery_address"]["state"] or not checkout["delivery_address"]["pin_code"]:
                                st.error(translator.t("ui.complete_contact_address"))
                            elif not profile_complete and business_profile["missing"]:
                                st.error(f"Complete business profile fields: {', '.join(business_profile['missing'])}")
                            else:
                                try:
                                    latest_profile = user_profile_service.get_or_create_profile(
                                        email=session_service.get_user().get("email", ""),
                                        role=user.get("role", "public_buyer"),
                                        display_name=checkout["name"],
                                        mobile=checkout["mobile"],
                                    )
                                    if not profile_complete:
                                        updated_profile = dict(latest_profile)
                                        updated_profile["display_name"] = checkout["name"]
                                        updated_profile["mobile"] = checkout["mobile"]
                                        merged_details = dict((latest_profile.get("details", {}) or {}))
                                        merged_details.update(business_profile["details"])
                                        updated_profile["details"] = merged_details
                                        user_profile_service.save_profile(
                                            actor_email=session_service.get_user().get("email", ""),
                                            actor_role=user.get("role", "public_buyer"),
                                            target_email=session_service.get_user().get("email", ""),
                                            updates=updated_profile,
                                        )
                                    if checkout.get("save_address", False):
                                        address_book_service.save_address(
                                            email=session_service.get_user().get("email", ""),
                                            role=user.get("role", "public_buyer"),
                                            display_name=checkout["name"],
                                            mobile=checkout["mobile"],
                                            address=checkout["delivery_address"],
                                            address_id=checkout.get("address_id", ""),
                                            label=checkout.get("address_label", ""),
                                        )
                                    else:
                                        user_profile_service.save_profile(
                                            actor_email=session_service.get_user().get("email", ""),
                                            actor_role=user.get("role", "public_buyer"),
                                            target_email=session_service.get_user().get("email", ""),
                                            updates={
                                                "display_name": checkout["name"],
                                                "mobile": checkout["mobile"],
                                            },
                                        )
                                    product_lookup = {str(product.get("product_id", "")).strip(): product for product in products}
                                    created_orders = []
                                    for item in cart.get("items", []):
                                        product = product_lookup.get(str(item.get("product_id", "")).strip())
                                        if not product:
                                            raise ValueError(f"Product not found for bulk cart item: {item.get('product_id', '')}")
                                        order = order_service.create_manditrade_order_with_checkout(
                                            product=product,
                                            requesting_user_email=session_service.get_user().get("email", ""),
                                            requester_name=checkout["name"],
                                            requester_mobile=checkout["mobile"],
                                            delivery_address=checkout["delivery_address"],
                                            requested_quantity=float(item.get("quantity", 1) or 1),
                                        )
                                        order_service.persist_order_storage(order)
                                        user_profile_service.sync_order_record(order=order)
                                        created_orders.append(order)
                                    data_service.persist_collection("users")
                                    data_service.persist_collection("payments")
                                    data_service.persist_collection("notifications")
                                    data_service.persist_collection("gmail_queue")
                                    cart_service.clear_cart()
                                    st.session_state["mt_manditrade_checkout_open"] = False
                                    st.session_state["mt_manditrade_stage"] = "browse"
                                    st.success(f"MandiTrade orders created: {len(created_orders)}")
                                    if created_orders:
                                        payment_record = next(
                                            (
                                                row for row in data_service.get_collection_ref("payments")
                                                if str(row.get("payment_id", "")).strip() == str(created_orders[0].get("payment_id", "")).strip()
                                            ),
                                            {},
                                        )
                                        _render_payment_pending_panel(payment_record)
                                except Exception as exc:
                                    st.error(str(exc))
            with cart_cols[1]:
                checkout_requested = render_cart_panel(cart, cart_service=cart_service, route="manditrade", translator=translator)
                if not payment_config.get("enabled", False):
                    st.error("Payment config missing or disabled. Checkout is unavailable.")
                else:
                    if checkout_requested:
                        st.session_state["mt_manditrade_checkout_open"] = True
                        st.session_state["mt_manditrade_stage"] = "checkout"
                        st.rerun()
    elif page_definition.get("type") == "products_admin":
        notification_service = NotificationService(data_service)
        render_products_page(data_service, notification_service, session_service, cache_service, translator)
    elif current_route == "profile":
        render_profile_page(data_service, session_service)
    elif current_route == "notifications":
        notification_service = NotificationService(data_service)
        render_notifications_page(notification_service, data_service, session_service, translator)
    elif current_route == "payments":
        notification_service = NotificationService(data_service)
        order_service = OrderService(data_service, notification_service)
        render_payments_page(data_service, order_service, notification_service, session_service, translator)
    elif page_definition.get("type") == "ledger_page":
        notification_service = NotificationService(data_service)
        render_ledger_page(data_service, notification_service, session_service, translator)
    elif page_definition.get("type") == "completed_deliveries_page":
        render_completed_deliveries_page(data_service, session_service)
    elif current_route == "shipments":
        notification_service = NotificationService(data_service)
        order_service = OrderService(data_service, notification_service)
        render_shipments_page(data_service, order_service, notification_service, session_service, translator)
    elif page_definition.get("type") == "admin_configuration":
        notification_service = NotificationService(data_service)
        render_admin_configuration(auth_service, data_service, notification_service, session_service, translator)
    elif page_definition.get("type") in {"crud_table", "table"}:
        notification_service = NotificationService(data_service)
        source_name = str(page_definition.get("data_source", ""))
        filtered_rows = _filter_role_rows(current_route, datasets.get(source_name, []), role, user.get("email", ""))
        if current_route == "orders":
            media_service = MediaService(admin_drive_service)
            order_service = OrderService(data_service, notification_service)
            render_orders_page(
                filtered_rows,
                role,
                data_service=data_service,
                order_service=order_service,
                notification_service=notification_service,
                session_service=session_service,
                translator=translator,
                media_service=media_service,
            )
        elif current_route == "completed_deliveries":
            render_completed_deliveries_page(data_service, session_service)
        else:
            render_table(filtered_rows, caption=f"{source_name} collection")
        form_id = page_definition.get("form_id")
        if form_id:
            form_service = FormService(cache_service)
            form_definition = form_service.get_form(form_id)

            def _handle_submit(values: dict) -> None:
                created = data_service.create_record(form_definition.get("collection", source_name), values)
                data_service.persist_collection(form_definition.get("collection", source_name))
                notification_service.create_notification(
                    to_email=session_service.get_user().get("email", ""),
                    title=translator.t("notification.product_added.title"),
                    message=translator.t("notification.product_added.message"),
                    event_type="PRODUCT_ADDED",
                    source_entity=form_definition.get("collection", source_name),
                    source_id=created.get("id", ""),
                    created_by=session_service.get_user().get("email", ""),
                )
                data_service.persist_collection("notifications")
                data_service.persist_collection("gmail_queue")
                st.success("Saved.")

            render_form(form_definition, translator, _handle_submit)
    elif page_definition.get("type") == "system":
        render_system_health_page(
            admin_drive_service=admin_drive_service,
            cache_service=cache_service,
            data_service=data_service,
            oauth_service=oauth_service,
            language_service=language_service,
            translator=translator,
            session_service=session_service,
            rbac_service=rbac_service,
            page_service=page_service,
            navigation_service=navigation_service,
            performance_service=performance_service,
            theme_service=theme_service,
            role=role,
            is_superadmin=is_superadmin,
            navigation_items=navigation_items,
            current_route=current_route,
        )
    else:
        render_empty_state("Unsupported page type.")
