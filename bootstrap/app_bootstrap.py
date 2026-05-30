from __future__ import annotations

from pathlib import Path

import streamlit as st

from bootstrap.route_registry import render_route
from bootstrap.service_container import build_app_context
from components.ui_shell import apply_ui_shell
from utils.session import clear_runtime_session, ensure_session_defaults, pop_flash, set_flash


BUILD_COMMIT = "ui-jobs-20260528"
BUILD_FILE = Path(__file__).resolve()
CSS_FILE = BUILD_FILE.parent.parent / "assets" / "styles" / "manditrade_3d.css"


def render_header(app_context: dict) -> None:
    st.title(app_context["system_config"]["app"]["name"])
    st.caption(app_context["system_config"]["app"]["tagline"])
    if app_context["config_issues"]:
        st.warning("Configuration issues detected: " + " | ".join(app_context["config_issues"]))
    if app_context["startup_checks"]:
        st.error("Startup blockers: " + " | ".join(app_context["startup_checks"]))
    if app_context.get("startup_warnings"):
        st.warning("Deployment warnings: " + " | ".join(app_context["startup_warnings"]))
    if app_context["effective_demo_mode"]:
        st.info("DEMO_MODE is active. Real Google runtime actions are blocked until staging secrets are complete.")
    elif not app_context.get("long_lived_admin_runtime_enabled", False):
        st.info("Long-lived admin runtime mode is not provisioned yet. Local OAuth session mode remains available.")
    flash = pop_flash()
    if flash:
        st.success(flash)


def render_auth_panel(app_context: dict) -> None:
    with st.sidebar:
        st.markdown("## Access")
        user = app_context["current_user"]
        if user:
            st.success(f"{user.name} signed in as {user.role}")
            if user.manufacturer_code:
                st.caption(f"Manufacturer: {user.manufacturer_code}")
            if st.button("Logout", use_container_width=True):
                app_context["security_service"].revoke_runtime_session()
                clear_runtime_session()
                set_flash("Session closed and runtime tokens cleared.")
                st.rerun()
            return

        st.info("Use the central login page on the homepage to continue with Google, or browse the public marketplace from the sidebar.")


def handle_oauth_callback(app_context: dict) -> None:
    query_params = st.query_params
    code_value = query_params.get("code")
    state_value = query_params.get("state")
    code = code_value[0] if isinstance(code_value, list) else code_value
    state = state_value[0] if isinstance(state_value, list) else state_value
    if not code:
        return
    if app_context["oauth_callback_service"].restore_session():
        return
    try:
        token_payload = app_context["oauth_callback_service"].exchange_code(str(code), str(state) if state else None)
        flow_type = token_payload.get("flow_type", app_context["oauth_callback_service"].LOGIN)
        if flow_type in {
            app_context["oauth_callback_service"].MANUFACTURER_DRIVE,
            app_context["oauth_callback_service"].MANUFACTURER_GMAIL,
        }:
            provider = "drive" if flow_type == app_context["oauth_callback_service"].MANUFACTURER_DRIVE else "gmail"
            credentials = app_context["auth_service"].refresh_credentials(token_payload, scopes=token_payload.get("scopes"))
            profile = app_context["auth_service"].fetch_google_profile(credentials)
            manufacturer_id = token_payload.get("manufacturer_id", "")
            app_context["connected_accounts_service"].validate_connected_email(manufacturer_id, profile.get("email", ""))
            app_context["connected_accounts_service"].complete_connection(
                manufacturer_code=manufacturer_id,
                provider=provider,
                credentials_payload=token_payload,
                connected_email=profile.get("email", ""),
            )
            app_context["oauth_callback_service"].reset_authorization_state()
            st.query_params.clear()
            set_flash(f"Google {provider.title()} connected for {manufacturer_id}.")
            st.rerun()
            return
        credentials = app_context["auth_service"].refresh_credentials(token_payload, scopes=token_payload.get("scopes"))
        profile = app_context["auth_service"].fetch_google_profile(credentials)
        email = profile.get("email", "")
        resolved_identity = app_context["access_portal_service"].resolve_identity(
            email=email,
            display_name=profile.get("name", email),
            preferred_role=st.session_state.get("requested_role"),
            manufacturer_code=st.session_state.get("manufacturer_context"),
        )
        app_context["oauth_callback_service"].initialize_session(
            user_payload={
                "email": email,
                "name": profile.get("name", email),
                "role": resolved_identity["role"],
                "subject_id": profile.get("id"),
                "granted_scopes": list(token_payload.get("scopes", [])),
                "profile": profile,
            },
            credentials_payload=token_payload,
            manufacturer_code=resolved_identity.get("manufacturer_code"),
            session_source="google_oauth",
        )
        st.session_state["requested_role"] = None
        st.session_state["client_onboarding_token"] = None
        if resolved_identity.get("manufacturer_code"):
            st.session_state["manufacturer_context"] = resolved_identity["manufacturer_code"]
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        set_flash("OAuth session initialized.")
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        app_context["logging_service"].log_error("oauth_errors", str(exc), {"state": state})
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        st.error(f"OAuth callback failed: {exc}")


def resolve_navigation_sections(app_context: dict) -> list[str]:
    current_user = app_context.get("current_user")
    security_service = app_context["security_service"]
    is_admin_identity = security_service.is_admin_identity(current_user)
    worker_profile = app_context["worker_service"].get_worker_by_email(current_user.email) if current_user and getattr(current_user, "email", "") else None
    role = current_user.role if current_user else None
    manufacturer_sections = [
        "Dashboard",
        "My Profile",
        "Products",
        "Inventory",
        "Clients",
        "Client Orders",
        "Ledger",
        "RFQ",
        "Marketplace",
        "My Actions",
        "Notifications",
    ]
    if role in {"manufacturer", "admin_as_manufacturer"}:
        return manufacturer_sections
    if is_admin_identity and current_user and current_user.manufacturer_code:
        return [*manufacturer_sections, "Product Approvals", "Manufacturers", "System Health"]
    if is_admin_identity:
        return ["Dashboard", "My Profile", "Products", "Product Approvals", "Manufacturers", "Marketplace", "Public Orders", "RFQ", "Inventory Summary", "Commission Summary", "Payments", "My Actions", "Notifications", "System Health"]
    if role == "public_buyer":
        return ["Marketplace", "My Orders", "My Actions", "Notifications", "My Profile"]
    if role == "client":
        sections = ["Dashboard", "Products", "My Orders", "Ledger", "My Actions", "Notifications", "Profile"]
        if worker_profile:
            sections.append("Jobs in Mandi")
            sections.append("Workers")
        return sections
    if role == "worker":
        return ["Dashboard", "My Profile", "My Actions", "Notifications", "Jobs in Mandi", "Workers"]
    if role == "pending_user":
        return ["Dashboard"]
    return ["Dashboard", "Marketplace"]


def render_sidebar_navigation(app_context: dict) -> str:
    current_user = app_context.get("current_user")
    security_service = app_context["security_service"]
    is_admin_identity = security_service.is_admin_identity(current_user)
    sections = resolve_navigation_sections(app_context)
    with st.sidebar:
        st.markdown("## Navigation")
        if is_admin_identity:
            st.caption("Admin Nav Enabled")
        return st.radio("Go to", sections, label_visibility="collapsed")


def main() -> None:
    ensure_session_defaults()
    apply_ui_shell(CSS_FILE)
    app_context = build_app_context()
    st.session_state["runtime_environment"] = app_context["system_config"]["app"].get("runtime_environment", "local")
    handle_oauth_callback(app_context)
    if not st.session_state.get("startup_recovery_ran"):
        st.session_state["startup_recovery"] = app_context["startup_recovery_service"].run_recovery_pass()
        st.session_state["startup_recovery_ran"] = True
    if app_context["security_service"].session_expired(
        st.session_state.get("session_last_seen"),
        app_context["system_config"]["security"]["session_timeout_minutes"],
    ):
        app_context["security_service"].revoke_runtime_session()
        clear_runtime_session()
        ensure_session_defaults()
        st.warning("Session expired. Please sign in again.")
        app_context = build_app_context()
    render_auth_panel(app_context)
    section = render_sidebar_navigation(app_context)
    render_header(app_context)
    render_route(section, app_context)
