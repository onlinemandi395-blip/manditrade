from __future__ import annotations

from pathlib import Path

import streamlit as st

from components.dashboard_renderer import render_dashboard_cards
from components.detail_panel import render_detail_panel
from components.empty_state import render_empty_state
from components.form_renderer import render_form
from components.html_renderer import inject_css
from components.sidebar import render_sidebar
from components.table_renderer import render_table
from components.topbar import render_topbar
from services.admin_drive_service import AdminDriveService
from services.auth_service import AuthService
from services.cache_service import CacheService
from services.cart_service import CartService
from services.config_loader_service import ConfigLoaderService
from services.data_service import DataService
from services.form_service import FormService
from services.language_service import LanguageService
from services.navigation_service import NavigationService
from services.notification_service import NotificationService
from services.order_service import OrderService
from services.page_service import PageService
from services.gmail_queue_service import GmailQueueService
from services.google_oauth_service import GoogleOAuthService
from services.integration_status_service import IntegrationStatusService
from services.rbac_service import RBACService
from services.session_service import SessionService
from modules.admin_configuration import render_admin_configuration
from modules.login import render_login_page
from modules.marketplace import render_marketplace_page
from modules.manditrade import render_manditrade_page
from modules.products import render_products_page


CSS_FILE = Path(__file__).resolve().parent.parent / "assets" / "styles" / "design.css"


def render_app() -> None:
    inject_css(CSS_FILE)
    config_loader = ConfigLoaderService()
    drive_manifest = config_loader.validate_runtime()
    if not drive_manifest.get("connected", False):
        st.error("Google Drive is not connected.\n\nExpected:\nMANDITRADE_DB root folder from Google Drive.\n\nFix:\nCheck Google OAuth token and Drive permissions.")
        for error in drive_manifest.get("errors", []):
            st.code(error)
        st.stop()
    if drive_manifest.get("missing_files"):
        st.error("Google Drive runtime is missing required JSON files.")
        render_table(
            [
                {
                    "logical_path": path,
                    "status": "MISSING",
                }
                for path in drive_manifest["missing_files"]
            ],
            caption="Missing required Drive files",
        )
        st.stop()
    cache_service = CacheService(config_loader)
    cache_service.load_all_configs()
    app_config = cache_service.get_config("app_config")
    session_service = SessionService(app_config)
    language = session_service.get_language()
    language_service = LanguageService(cache_service, language)
    translator = language_service.get_translator()
    auth_service = AuthService(cache_service)
    oauth_service = GoogleOAuthService()
    rbac_service = RBACService(cache_service)
    navigation_service = NavigationService(cache_service, translator, rbac_service)
    page_service = PageService(cache_service, translator, rbac_service)

    callback_error = oauth_service.get_callback_error()
    if callback_error:
        st.error(translator.t("auth.oauth_failed"))
        oauth_service.clear_callback_params()

    if oauth_service.has_callback() and not session_service.is_authenticated():
        try:
            identity = oauth_service.exchange_code_for_identity()
            if not identity.get("email_verified", False):
                raise ValueError(translator.t("auth.email_not_verified"))
            resolved_user = auth_service.resolve_user(str(identity.get("email", "")))
            role = str(resolved_user.get("role", auth_service.get_unknown_user_default_role()))
            landing_page = navigation_service.get_default_route(role)
            oauth_service.persist_admin_token(identity, resolved_user)
            session_service.authenticate(
                {
                    **resolved_user,
                    "display_name": identity.get("display_name") or resolved_user.get("display_name", ""),
                    "photo_url": identity.get("photo_url", ""),
                    "oauth_token": identity.get("oauth_token", {}),
                    "landing_page": landing_page,
                }
            )
            oauth_service.clear_callback_params()
            st.rerun()
        except Exception as exc:
            st.error(f"{translator.t('auth.oauth_failed')}: {exc}")
            oauth_service.clear_callback_params()

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
                st.write(
                    {
                        **oauth_service.get_debug_snapshot(),
                        "current_session_user": session_service.get_user(),
                    }
                )
        return

    role = session_service.get_user_role()
    user = session_service.get_user()
    data_service = DataService(cache_service)
    notification_service = NotificationService(data_service)
    order_service = OrderService(data_service, notification_service)
    cart_service = CartService()
    admin_drive_service = AdminDriveService()
    gmail_queue_service = GmailQueueService(data_service)
    integration_status_service = IntegrationStatusService(
        cache_service=cache_service,
        admin_drive_service=admin_drive_service,
        gmail_queue_service=gmail_queue_service,
        oauth_service=oauth_service,
        data_service=data_service,
    )
    form_service = FormService(cache_service)

    navigation_items = navigation_service.get_navigation(role)
    current_route = session_service.get_current_route_or_landing()
    valid_routes = [item.get("route", "") for item in navigation_items]
    if not navigation_items:
        st.error(translator.t("auth.access_denied"))
        return
    if current_route not in valid_routes or not rbac_service.can_access(role, current_route):
        current_route = page_service.get_landing_page(role, navigation_service)
        session_service.set_route(current_route)
    chosen = render_sidebar(navigation_items, current_route, user=user, role_label=translator.t(f"role.{role}"))
    if chosen != current_route:
        current_route = chosen
        session_service.set_route(current_route)
    with st.sidebar:
        if st.button(translator.t("auth.logout"), use_container_width=True):
            session_service.logout()
            st.rerun()

    render_topbar(
        app_name=app_config.get("app_name", "MandiTrade Next"),
        version=app_config.get("version", "0.1.0"),
        role_label=translator.t(f"role.{role}"),
        language=language,
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
        "raw_materials": data_service.list_collection("raw_materials"),
        "orders": data_service.list_collection("orders"),
        "notifications": data_service.list_collection("notifications"),
        "shipments": data_service.list_collection("shipments"),
        "ledger": data_service.list_collection("ledger"),
    }

    if page_definition.get("type") == "dashboard":
        cards = cache_service.get_config("dashboards").get("dashboards", {}).get(role, {}).get("cards", [])
        render_dashboard_cards(cards, datasets, translator)
        render_detail_panel("Runtime", cache_service.get_cache_status())
    elif page_definition.get("type") == "product_grid":
        products = page_service.filter_rows(datasets.get(page_definition.get("data_source", ""), []), page_definition.get("filters", {}))

        def on_add_to_cart(product: dict) -> None:
            cart_service.add_to_cart(product)
            notification_service.create_notification(
                notification_type="PRODUCT_ADDED",
                title=translator.t("notification.product_added.title"),
                message=translator.t("notification.product_added.message"),
                metadata={"product_id": product.get("product_id", "")},
            )
            st.success(f"Added {product.get('product_name', product.get('product_id', 'product'))} to cart.")

        render_marketplace_page(products, on_add_to_cart=on_add_to_cart)
        cart = cart_service.get_cart()
        if cart.get("items"):
            with st.container(border=True):
                st.subheader("Cart")
                render_table(cart["items"])
                st.write(f"Total: {cart_service.calculate_total()}")
                if st.button("Checkout", use_container_width=True):
                    order = order_service.create_order(
                        items=cart["items"],
                        source_channel=current_route,
                        role=role,
                    )
                    cart_service.clear_cart()
                    st.success(f"Order {order.get('order_id', '')} created.")
    elif page_definition.get("type") == "manditrade":
        products = page_service.filter_rows(datasets.get(page_definition.get("data_source", ""), []), page_definition.get("filters", {}))
        render_manditrade_page(products)
    elif page_definition.get("type") == "products_admin":
        render_products_page(data_service, notification_service, session_service)
    elif page_definition.get("type") == "admin_configuration":
        render_admin_configuration(auth_service, data_service, notification_service, session_service)
    elif page_definition.get("type") in {"crud_table", "table"}:
        source_name = str(page_definition.get("data_source", ""))
        render_table(datasets.get(source_name, []), caption=f"{source_name} collection")
        form_id = page_definition.get("form_id")
        if form_id:
            form_definition = form_service.get_form(form_id)

            def _handle_submit(values: dict) -> None:
                created = data_service.create_record(form_definition.get("collection", source_name), values)
                notification_service.create_notification(
                    notification_type="RAW_MATERIAL_ADDED" if form_definition.get("collection") == "raw_materials" else "PRODUCT_ADDED",
                    title=translator.t("notification.raw_material_added.title" if form_definition.get("collection") == "raw_materials" else "notification.product_added.title"),
                    message=translator.t("notification.raw_material_added.message" if form_definition.get("collection") == "raw_materials" else "notification.product_added.message"),
                    metadata={"record_id": created.get("id", "")},
                )
                st.success("Saved.")

            render_form(form_definition, translator, _handle_submit)
    elif page_definition.get("type") == "system":
        status = integration_status_service.get_status()
        if status["google_drive_status"] != "connected" or status["required_files_status"] != "ok":
            st.error("Drive-only runtime is blocked. Required Google Drive files are missing or unavailable.")
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
                {"key": "notifications_count", "value": status["notification_queue_count"]},
                {"key": "queue_count", "value": status["queue_count"]},
                {"key": "language_files_loaded", "value": status["language_files_loaded"]},
                {"key": "language_selected", "value": status["language_selected"]},
                {"key": "available_languages", "value": ", ".join(status["available_languages"])},
                {"key": "primary_admin_email", "value": status["primary_admin_email"]},
            ],
            caption="Integration status",
        )
        render_table(status["required_files"], caption="Required Drive files")
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
