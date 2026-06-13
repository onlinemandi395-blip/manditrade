from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.dashboard_renderer import render_dashboard_cards
from components.detail_panel import render_detail_panel
from components.empty_state import render_empty_state
from components.form_renderer import render_form
from components.html_renderer import inject_css, inject_inline_css
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
from modules.products import render_products_page
from modules.shipments import render_shipments_page
from modules.setup_console import render_setup_console
from services.admin_drive_service import AdminDriveService
from services.auth_service import AuthService, get_bootstrap_primary_admin, is_bootstrap_admin
from services.cache_service import CacheService
from services.cart_service import CartService
from services.config_loader_service import ConfigLoaderService
from services.data_service import DataService
from services.form_service import FormService
from services.gmail_queue_service import GmailQueueService
from services.google_oauth_service import GoogleOAuthService
from services.integration_status_service import IntegrationStatusService
from services.language_service import LanguageService
from services.navigation_service import NavigationService
from services.notification_service import NotificationService
from services.order_service import OrderService
from services.page_service import PageService
from services.payment_config_service import PaymentConfigService
from services.performance_service import PerformanceService
from services.qr_service import QRService
from services.rbac_service import RBACService
from services.session_service import SessionService
from services.media_service import MediaService
from services.theme_service import ThemeService


CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "styles" / "design.css"
BOOTSTRAP_APP_CONFIG = {
    "default_role": "public_buyer",
    "default_language": "en",
    "default_landing": {
        "platform_admin": "dashboard",
        "public_buyer": "marketplace",
    },
}


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


def _render_payment_pending_panel(payment_record: dict) -> None:
    qr_service = QRService()
    st.markdown("### Payment Pending")
    st.caption(f"Order Reference: {payment_record.get('payment_reference', '')}")
    st.write(f"Amount: Rs. {payment_record.get('amount_payable', payment_record.get('amount_due', 0))}")
    st.write("Payment Method: UPI")
    qr_bytes = qr_service.build_qr_png_bytes(payment_record.get("qr_payload", "") or payment_record.get("upi_link", ""))
    if qr_bytes:
        st.image(qr_bytes, width=220)
    st.code(payment_record.get("upi_link", ""))
    st.caption("Pay using this QR/UPI link. Keep the payment note/reference unchanged.")


def _render_checkout_details_form(*, key_prefix: str, email: str, translator) -> dict:
    t = translator.t if translator else (lambda key: key)
    st.markdown(f"### {t('ui.checkout_details')}")
    st.markdown(f"#### {t('ui.buyer_contact')}")
    name = st.text_input(t("ui.full_name"), key=f"{key_prefix}_name")
    mobile = st.text_input(t("ui.mobile_number"), key=f"{key_prefix}_mobile")
    st.text_input(t("ui.email"), value=email, disabled=True, key=f"{key_prefix}_email")
    st.markdown(f"#### {t('ui.delivery_address')}")
    address_line_1 = st.text_input(t("ui.address_line_1"), key=f"{key_prefix}_address_1")
    address_line_2 = st.text_input(t("ui.address_line_2"), key=f"{key_prefix}_address_2")
    city = st.text_input(t("ui.city"), key=f"{key_prefix}_city")
    state = st.text_input(t("ui.state"), key=f"{key_prefix}_state")
    pin_code = st.text_input(t("ui.pin_code"), key=f"{key_prefix}_pin")
    landmark = st.text_input(t("ui.landmark"), key=f"{key_prefix}_landmark")
    st.markdown(f"#### {t('ui.payment_method')}")
    st.selectbox(t("ui.payment_method"), options=[t("ui.upi_qr_upi_link")], key=f"{key_prefix}_payment_method")
    return {
        "name": name.strip(),
        "mobile": mobile.strip(),
        "delivery_address": {
            "address_line_1": address_line_1.strip(),
            "address_line_2": address_line_2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
            "landmark": landmark.strip(),
        },
    }


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
    st.markdown("## Welcome to MandiTrade")
    st.caption("Google Drive powered commerce platform")
    if not oauth_service.is_configured():
        st.error("Google Single Sign-On is not configured in Streamlit secrets.")
        return
    st.link_button("Continue with Google", oauth_service.get_authorize_url(), use_container_width=True)
    if oauth_service.is_debug_enabled():
        with st.expander("OAuth Debug", expanded=False):
            st.write({**oauth_service.get_debug_snapshot(), "current_session_user": session_service.get_user()})


def _render_missing_files_screen(drive_manifest: dict, session_service: SessionService, admin_drive_service: AdminDriveService) -> None:
    user = session_service.get_user()
    current_email = str(user.get("email", "")).strip().lower()
    bootstrap_admin = is_bootstrap_admin(current_email)
    is_admin = bool(user.get("is_authenticated")) and (
        str(user.get("role", "")).strip().lower() == "platform_admin" or bootstrap_admin
    )
    if is_admin:
        render_setup_console(admin_drive_service, drive_manifest)
        with st.expander("Bootstrap Admin Debug", expanded=False):
            st.write(
                {
                    "current_google_email": current_email,
                    "primary_admin_email_from_toml": get_bootstrap_primary_admin().get("email", ""),
                    "is_bootstrap_admin": bootstrap_admin,
                    "current_session_role": user.get("role", ""),
                    "drive_setup_complete": not bool(drive_manifest.get("missing_files")),
                    "missing_file_count": len(drive_manifest.get("missing_files", [])),
                }
            )
    elif user.get("is_authenticated"):
        st.error("Platform setup is incomplete. Please contact admin.")
        render_table(drive_manifest.get("required_files", []), caption="Required Drive files")
    else:
        st.warning("Google Drive runtime is missing required JSON files.")
        _render_bootstrap_login(GoogleOAuthService(), session_service)


def _filter_role_rows(route: str, rows: list[dict], role: str, user_email: str) -> list[dict]:
    normalized_email = str(user_email).strip().lower()
    if role == "platform_admin":
        return rows
    if route == "orders":
        if role in {"manufacturer", "mahajan"}:
            return [
                row
                for row in rows
                if (
                    normalized_email in {
                        str(row.get("buyer_email", "")).strip().lower(),
                        str(row.get("requester_email", "")).strip().lower(),
                        str(row.get("requesting_user_email", "")).strip().lower(),
                    }
                    or (
                        str(row.get("owner_email", "")).strip().lower() == normalized_email
                        and str(row.get("status", "")).strip().upper() != "PAYMENT_PENDING"
                    )
                )
            ]
        if role == "public_buyer":
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
                    normalized_role in {"manufacturer", "mahajan"}
                    and str(row.get("to_role", "")).strip().lower() == normalized_role
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
                "root_folder_name": "MANDITRADE_DB",
                "required_folders": [],
                "missing_folders": ["MANDITRADE_DB"],
                "required_files": [],
                "missing_files": [],
            },
        )
        with st.expander("Bootstrap Admin Debug", expanded=False):
            st.write(
                {
                    "current_google_email": current_email,
                    "primary_admin_email_from_toml": get_bootstrap_primary_admin().get("email", ""),
                    "is_bootstrap_admin": bootstrap_admin,
                    "current_session_role": user.get("role", ""),
                    "drive_setup_complete": False,
                    "missing_file_count": 0,
                }
            )
    elif user.get("is_authenticated"):
        st.error("Platform setup is incomplete. Please contact admin.")
    else:
        _render_bootstrap_login(GoogleOAuthService(), session_service)


def render_app() -> None:
    inject_css(CSS_FILE)
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
            cache_service.load_all_configs()
    app_config = cache_service.get_config("app_config")

    session_service = SessionService(app_config)
    language = session_service.get_language()
    language_service = LanguageService(cache_service, language)
    translator = language_service.get_translator()
    auth_service = AuthService(cache_service)
    rbac_service = RBACService(cache_service)
    navigation_service = NavigationService(cache_service, translator, rbac_service)
    page_service = PageService(cache_service, translator, rbac_service)

    if session_service.is_authenticated():
        current_user = session_service.get_user()
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
            language_options=list(cache_service.get_config("languages").keys()),
            current_language=language,
            set_language=session_service.set_language,
        )
        if oauth_service.is_debug_enabled() or bool(app_config.get("debug_auth", False)):
            with st.expander("OAuth Debug", expanded=False):
                st.write({**oauth_service.get_debug_snapshot(), "current_session_user": session_service.get_user()})
        return

    role = session_service.get_user_role()
    user = session_service.get_user()
    theme_service = ThemeService(admin_drive_service, cache_service)
    theme_css = theme_service.build_background_css()
    if theme_css:
        inject_inline_css(theme_css)
    else:
        theme_warning = theme_service.get_background_style().get("warning", "")
        if theme_warning and role == "platform_admin":
            st.warning(theme_warning)
    data_service = DataService(cache_service)
    media_service = MediaService(admin_drive_service)
    notification_service = NotificationService(data_service)
    order_service = OrderService(data_service, notification_service)
    payment_config_service = PaymentConfigService(data_service, cache_service, admin_drive_service)
    cart_service = CartService()
    gmail_queue_service = GmailQueueService(data_service)
    integration_status_service = IntegrationStatusService(
        cache_service=cache_service,
        admin_drive_service=admin_drive_service,
        gmail_queue_service=gmail_queue_service,
        oauth_service=oauth_service,
        data_service=data_service,
    )
    form_service = FormService(cache_service)

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
    chosen = render_sidebar(
        navigation_items,
        current_route,
        user=user,
        role_label=translator.t(f"role.{role}"),
        theme_service=theme_service,
        language_options=language_service.get_available_languages(),
        current_language=session_service.get_language(),
        language_label=translator.t("auth.language"),
        set_language=session_service.set_language,
    )
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
    st.markdown(f"<div class='mt-shell'><h2 class='mt-page-title'>{translator.t(page_definition.get('title_key', ''))}</h2><p class='mt-page-subtitle'>{translator.t(page_definition.get('subtitle_key', ''))}</p></div>", unsafe_allow_html=True)

    datasets = {
        "products": data_service.list_collection("products"),
        "orders": data_service.list_collection("orders"),
        "payments": data_service.list_collection("payments"),
        "notifications": data_service.list_collection("notifications"),
        "shipments": data_service.list_collection("shipments"),
        "ledger": data_service.list_collection("ledger"),
    }

    if page_definition.get("type") == "dashboard":
        cards = cache_service.get_config("dashboards").get("dashboards", {}).get(role, {}).get("cards", [])
        render_dashboard_cards(cards, datasets, translator, current_user=user)
        render_detail_panel("Runtime", cache_service.get_cache_status())
    elif page_definition.get("type") == "product_grid":
        products = page_service.filter_rows(datasets.get(page_definition.get("data_source", ""), []), page_definition.get("filters", {}))
        payment_config = order_service.payment_service.get_payment_config()

        def on_add_to_cart(product: dict) -> None:
            try:
                cart_service.add_to_cart(product)
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
                st.success(f"Added {product.get('product_name', product.get('product_id', 'product'))} to cart.")
            except Exception as exc:
                st.error(str(exc))

        render_marketplace_page(products, on_add_to_cart=on_add_to_cart, media_service=media_service, translator=translator)
        cart = cart_service.get_cart()
        if cart.get("items"):
            with st.container(border=True):
                st.subheader(translator.t("ui.cart"))
                render_table(_sanitize_cart_rows(cart["items"]), caption="Public cart view")
                st.write(f"Total: {cart_service.calculate_total()}")
                if not payment_config.get("enabled", False):
                    st.error("Payment config missing or disabled. Checkout is unavailable.")
                else:
                    if st.button(translator.t("ui.checkout"), use_container_width=True, key="marketplace_checkout_open"):
                        st.session_state["mt_marketplace_checkout_open"] = True
                    if st.session_state.get("mt_marketplace_checkout_open", False):
                        checkout = _render_checkout_details_form(
                            key_prefix="marketplace_checkout",
                            email=session_service.get_user().get("email", ""),
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
                                    order_service.persist_order_storage(order)
                                    data_service.persist_collection("payments")
                                    data_service.persist_collection("notifications")
                                    data_service.persist_collection("gmail_queue")
                                    cart_service.clear_cart()
                                    st.session_state["mt_marketplace_checkout_open"] = False
                                    st.session_state["mt_last_payment_record_id"] = order.get("payment_id", "")
                                    st.success(f"Order {order.get('order_id', '')} created.")
                                    payment_record = next(
                                        (row for row in data_service.get_collection_ref("payments") if str(row.get("payment_id", "")).strip() == str(order.get("payment_id", "")).strip()),
                                        {},
                                    )
                                    _render_payment_pending_panel(payment_record)
                                except Exception as exc:
                                    st.error(str(exc))
    elif page_definition.get("type") == "manditrade":
        products = page_service.filter_rows(datasets.get(page_definition.get("data_source", ""), []), page_definition.get("filters", {}))
        payment_config = order_service.payment_service.get_payment_config()

        def on_request(product: dict) -> None:
            try:
                st.session_state["mt_manditrade_checkout_product_id"] = product.get("product_id", "")
            except Exception as exc:
                st.error(str(exc))

        render_manditrade_page(products, on_request=on_request, media_service=media_service, translator=translator)
        selected_product_id = str(st.session_state.get("mt_manditrade_checkout_product_id", "") or "").strip()
        if selected_product_id:
            selected_product = next((row for row in products if str(row.get("product_id", "")).strip() == selected_product_id), None)
            if selected_product:
                with st.container(border=True):
                    st.subheader(f"{translator.t('ui.manditrade_checkout')}: {selected_product.get('product_name', '')}")
                    if not payment_config.get("enabled", False):
                        st.error("Payment config missing or disabled. Checkout is unavailable.")
                    else:
                        checkout = _render_checkout_details_form(
                            key_prefix=f"manditrade_checkout_{selected_product_id}",
                            email=session_service.get_user().get("email", ""),
                            translator=translator,
                        )
                        if st.button(translator.t("ui.confirm_order"), use_container_width=True, key=f"manditrade_confirm_order_{selected_product_id}"):
                            if not checkout["name"] or not checkout["mobile"] or not checkout["delivery_address"]["address_line_1"] or not checkout["delivery_address"]["city"] or not checkout["delivery_address"]["state"] or not checkout["delivery_address"]["pin_code"]:
                                st.error(translator.t("ui.complete_contact_address"))
                            else:
                                try:
                                    order = order_service.create_manditrade_order_with_checkout(
                                        product=selected_product,
                                        requesting_user_email=session_service.get_user().get("email", ""),
                                        requester_name=checkout["name"],
                                        requester_mobile=checkout["mobile"],
                                        delivery_address=checkout["delivery_address"],
                                    )
                                    order_service.persist_order_storage(order)
                                    data_service.persist_collection("payments")
                                    data_service.persist_collection("notifications")
                                    data_service.persist_collection("gmail_queue")
                                    st.session_state["mt_manditrade_checkout_product_id"] = ""
                                    st.success(f"MandiTrade order {order.get('order_id', '')} created.")
                                    payment_record = next(
                                        (row for row in data_service.get_collection_ref("payments") if str(row.get("payment_id", "")).strip() == str(order.get("payment_id", "")).strip()),
                                        {},
                                    )
                                    _render_payment_pending_panel(payment_record)
                                except Exception as exc:
                                    st.error(str(exc))
    elif page_definition.get("type") == "products_admin":
        render_products_page(data_service, notification_service, session_service, cache_service, translator)
    elif current_route == "notifications":
        render_notifications_page(notification_service, data_service, session_service, translator)
    elif current_route == "payments":
        render_payments_page(data_service, order_service, notification_service, session_service, translator)
    elif page_definition.get("type") == "ledger_page":
        render_ledger_page(data_service, notification_service, session_service, translator)
    elif page_definition.get("type") == "completed_deliveries_page":
        render_completed_deliveries_page(data_service, session_service)
    elif current_route == "shipments":
        render_shipments_page(data_service, order_service, notification_service, session_service)
    elif page_definition.get("type") == "admin_configuration":
        render_admin_configuration(auth_service, data_service, notification_service, session_service)
    elif page_definition.get("type") in {"crud_table", "table"}:
        source_name = str(page_definition.get("data_source", ""))
        filtered_rows = _filter_role_rows(current_route, datasets.get(source_name, []), role, user.get("email", ""))
        if current_route == "orders":
            render_orders_page(
                filtered_rows,
                role,
                data_service=data_service,
                order_service=order_service,
                notification_service=notification_service,
                session_service=session_service,
            )
        elif current_route == "completed_deliveries":
            render_completed_deliveries_page(data_service, session_service)
        else:
            render_table(filtered_rows, caption=f"{source_name} collection")
        form_id = page_definition.get("form_id")
        if form_id:
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
        status = integration_status_service.get_status()
        if status["google_drive_status"] != "connected" or status["required_files_status"] != "ok":
            st.error("Drive-only runtime is blocked. Required Google Drive files are missing or unavailable.")
        refresh_cols = st.columns(6)
        if refresh_cols[0].button("Create Missing Drive Files", use_container_width=True):
            try:
                result = admin_drive_service.create_missing_required_files()
                st.success(
                    f"Created {len(result.get('created', []))} missing files. "
                    f"database.json updates: {len(result.get('updated', []))}"
                )
                st.rerun()
            except Exception as exc:
                st.error(f"Create Missing Drive Files failed: {exc}")
        if refresh_cols[1].button(
            "Refresh database.json Mappings",
            use_container_width=True,
            disabled=status["database_config_status"].get("status") == "OK",
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
        if refresh_cols[2].button("Migrate Root Orders", use_container_width=True):
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
        if refresh_cols[3].button("Refresh Validation", use_container_width=True):
            admin_drive_service.clear_runtime_cache(clear_validation=True, clear_file_index=False)
            st.rerun()
        if refresh_cols[4].button("Refresh Data Cache", use_container_width=True):
            cache_service.refresh_cache()
            st.success("Data cache refreshed.")
        if refresh_cols[5].button("Clear Cache and Reload", use_container_width=True):
            admin_drive_service.clear_runtime_cache(clear_validation=True, clear_file_index=True)
            st.rerun()
        render_table(
            [
                {"key": "google_oauth_status", "value": status["google_oauth_status"]},
                {"key": "drive_mode", "value": status["drive_mode"]},
                {"key": "google_drive_status", "value": status["google_drive_status"]},
                {"key": "drive_root_status", "value": status["drive_root_status"]},
                {"key": "admin_token_status", "value": status["admin_token_status"]},
                {"key": "drive_write_test", "value": status["drive_write_test"]},
                {"key": "gmail_send_scope", "value": status["gmail_send_scope"]},
                {"key": "required_files_status", "value": status["required_files_status"]},
                {"key": "gmail_status", "value": status["gmail_status"]},
                {"key": "loaded_collection_count", "value": status["loaded_collection_count"]},
                {"key": "users_count", "value": status["users_count"]},
                {"key": "products_count", "value": status["products_count"]},
                {"key": "order_count", "value": status["order_count"]},
                {"key": "required_folders_count", "value": status["required_folders_count"]},
                {"key": "required_files_count", "value": status["required_files_count"]},
                {"key": "missing_files_count", "value": status["missing_files_count"]},
                {"key": "notifications_count", "value": status["notification_queue_count"]},
                {"key": "audit_log_count", "value": status["audit_log_count"]},
                {"key": "queue_count", "value": status["queue_count"]},
                {"key": "language_files_loaded", "value": status["language_files_loaded"]},
                {"key": "language_selected", "value": status["language_selected"]},
                {"key": "available_languages", "value": ", ".join(status["available_languages"])},
                {"key": "primary_admin_email", "value": status["primary_admin_email"]},
                {"key": "database_config_status", "value": status["database_config_status"].get("status", "MISSING")},
                {
                    "key": "database_mapping_missing_count",
                    "value": len(status["database_config_status"].get("missing_collections", [])),
                },
                {"key": "theme_background_status", "value": status["theme_status"].get("status", "MISSING")},
                {"key": "theme_background_message", "value": status["theme_status"].get("message", "")},
                {"key": "theme_background_count", "value": status.get("theme_background_count", 0)},
                {"key": "theme_active_background_id", "value": status.get("theme_active_background_id", "")},
            ],
            caption="Integration status",
        )
        render_table([status["database_config_status"]], caption="database.json mapping status")
        render_table(status["required_folders"], caption="Required Drive folders")
        render_table(status["required_files"], caption="Required Drive files")
        render_table([status["theme_status"]], caption="Theme background trace")
        render_table(
            [
                {
                    "selected_language": language_service.get_current_language(),
                    "available_languages": ", ".join(language_service.get_available_languages()),
                    "loaded_key_counts": ", ".join(f"{code}:{count}" for code, count in language_service.get_key_count_map().items()),
                    "missing_key_count": len(language_service.get_missing_keys_for_current_language()),
                    "sample_sidebar_products": translator.t("sidebar.products"),
                    "sample_module_products_title": translator.t("module.products.title"),
                    "sample_auth_title": translator.t("auth.title"),
                }
            ],
            caption="Language Runtime",
        )
        st.markdown("### Merchant Payment Configuration")
        payment_config_status = dict(status.get("payment_config", {}) or {})
        render_table([payment_config_status], caption="Current payment receiver settings")
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
            payment_link = (
                f"upi://pay?pa={str(payment_upi_id).strip()}&pn={str(payment_payee_name or 'MandiTrade').strip()}&am=1.00&cu={str(payment_currency or 'INR').strip() or 'INR'}&tn=MandiTradePreview"
            )
            st.caption("Live UPI Preview")
            st.code(payment_link)
            qr_bytes = QRService().build_qr_png_bytes(payment_link)
            if qr_bytes:
                st.image(qr_bytes, width=180)
        if st.button("Save Payment Receiver Settings", use_container_width=True, key="system_health_save_payment_config"):
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
                        "Merchant payment receiver settings saved. "
                        f"Pending payments updated: {impact.get('pending_payments_updated', 0)} | "
                        f"Pending orders updated: {impact.get('pending_orders_updated', 0)}"
                    )
                else:
                    st.success("Merchant payment receiver settings saved. No live queue updates were required.")
                st.rerun()
            except Exception as exc:
                st.error(f"Save Payment Receiver Settings failed: {exc}")
        render_theme_manager(theme_service, allow_set_default=(role == "platform_admin"), title="Theme Background Control")
        render_detail_panel("Cache Status", status["cache_status"])
    else:
        render_empty_state("Unsupported page type.")

    if bool(app_config.get("debug_auth", False)):
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
