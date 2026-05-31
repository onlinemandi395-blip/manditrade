from __future__ import annotations

from pathlib import Path

import streamlit as st

from bootstrap.route_registry import render_route
from bootstrap.service_container import build_app_context
from components.html_renderer import render_html
from components.ui_shell import render_same_tab_link_button
from components.ui_shell import apply_ui_shell
from utils.session import clear_runtime_session, ensure_session_defaults, pop_flash, set_flash


BUILD_COMMIT = "ui-jobs-20260528"
BUILD_FILE = Path(__file__).resolve()
CSS_FILE = BUILD_FILE.parent.parent / "assets" / "styles" / "manditrade_3d.css"
ADMIN_CONTEXT_OPTIONS = {
    "platform_admin": "Platform Admin",
    "manufacturer": "Manufacturer",
    "client": "Client",
    "public_buyer": "Public Buyer",
    "worker": "Worker",
}


def render_header(app_context: dict) -> None:
    if not app_context.get("current_user"):
        login_blocked_for_cloud_fallback = (
            app_context["system_config"]["app"].get("runtime_environment") == "staging_cloud"
            and app_context.get("oauth_config_fallback_active", False)
        )
        auth_url = None if login_blocked_for_cloud_fallback else app_context["oauth_callback_service"].build_authorization_url(flow_type=app_context["oauth_callback_service"].LOGIN)
        login_cta = ""
        if login_blocked_for_cloud_fallback:
            login_cta = "<span class='mt-google-login-btn mt-google-login-btn--disabled'>Configure Streamlit secrets</span>"
        elif auth_url and app_context["google_runtime_enabled"]:
            login_cta = render_same_tab_link_button("Continue with Google", auth_url, class_name="mt-google-login-btn")
        else:
            login_cta = "<span class='mt-google-login-btn mt-google-login-btn--disabled'>Google OAuth unavailable</span>"
        render_html(
            f"""
            <section class="mt-top-login-bar">
              <div class="mt-top-login-bar__brand">
                <strong>{app_context["system_config"]["app"]["name"]}</strong>
                <span>{app_context["system_config"]["app"]["tagline"]}</span>
              </div>
              <div class="mt-top-login-bar__cta">{login_cta}</div>
            </section>
            """
        )
    else:
        st.title(app_context["system_config"]["app"]["name"])
        st.caption(app_context["system_config"]["app"]["tagline"])
    if app_context["config_issues"]:
        st.warning("Configuration issues detected: " + " | ".join(app_context["config_issues"]))
    if app_context["startup_checks"]:
        st.error("Startup blockers: " + " | ".join(app_context["startup_checks"]))
    if app_context.get("startup_warnings"):
        st.warning("Deployment warnings: " + " | ".join(app_context["startup_warnings"]))
    if (
        app_context["system_config"]["app"].get("runtime_environment") == "staging_cloud"
        and app_context.get("oauth_config_fallback_active", False)
    ):
        st.error("Cloud runtime requires Streamlit secrets Google credentials.")
    if app_context["effective_demo_mode"]:
        st.info("DEMO_MODE is active. Real Google runtime actions are blocked until staging secrets are complete.")
    elif not app_context.get("long_lived_admin_runtime_enabled", False):
        st.info("Long-lived admin runtime mode is not provisioned yet. Local OAuth session mode remains available.")
    flash = pop_flash()
    if flash:
        st.success(flash)


def render_auth_panel(app_context: dict) -> None:
    with st.sidebar:
        st.markdown("## Session")
        user = app_context["current_user"]
        session_user = app_context.get("session_user")
        if user:
            if app_context["security_service"].is_admin_identity(session_user or user):
                active_context = app_context.get("active_context", "platform_admin")
                st.success(f"{user.name} signed in as SuperUser")
                st.caption(f"View as: {ADMIN_CONTEXT_OPTIONS.get(active_context, active_context.replace('_', ' ').title())}")
                selected_context = st.selectbox(
                    "View as",
                    options=list(ADMIN_CONTEXT_OPTIONS),
                    index=list(ADMIN_CONTEXT_OPTIONS).index(active_context if active_context in ADMIN_CONTEXT_OPTIONS else "platform_admin"),
                    format_func=lambda key: ADMIN_CONTEXT_OPTIONS[key],
                    key="admin_context_switcher",
                )
                if selected_context != active_context and session_user:
                    session_user.active_context = selected_context
                    st.session_state["admin_active_context"] = selected_context
                    st.session_state["user"] = app_context["auth_service"].serialize_user(session_user)
                    st.rerun()
            else:
                st.success(f"{user.name} signed in as {user.role}")
            if user.manufacturer_code:
                st.caption(f"Manufacturer: {user.manufacturer_code}")
            if st.button("Logout", use_container_width=True):
                app_context["security_service"].revoke_runtime_session()
                clear_runtime_session()
                set_flash("Session closed and runtime tokens cleared.")
                st.rerun()
            return

        st.info("Use the central MandiTrade login page to continue with Google. The app will route you to the correct workspace after sign-in.")


def handle_oauth_callback(app_context: dict) -> None:
    query_params = st.query_params
    error_value = query_params.get("error")
    error_description_value = query_params.get("error_description")
    code_value = query_params.get("code")
    state_value = query_params.get("state")
    error = error_value[0] if isinstance(error_value, list) else error_value
    error_description = error_description_value[0] if isinstance(error_description_value, list) else error_description_value
    code = code_value[0] if isinstance(code_value, list) else code_value
    state = state_value[0] if isinstance(state_value, list) else state_value
    if error:
        report = app_context["oauth_callback_service"].capture_failure(
            error=str(error),
            error_description=str(error_description or ""),
            state=str(state or ""),
        )
        app_context["logging_service"].log_error("oauth_errors", str(error), report)
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        st.error(app_context["oauth_callback_service"].friendly_error_message(str(error), str(error_description or "")))
        return
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
                "client_id": resolved_identity.get("client_id"),
                "public_buyer_id": resolved_identity.get("public_buyer_id"),
                "worker_id": resolved_identity.get("worker_id"),
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
        app_context["oauth_callback_service"].capture_failure(
            error="oauth_callback_failed",
            error_description=str(exc),
            state=str(state or ""),
        )
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        st.error(f"OAuth callback failed: {exc}")


def resolve_navigation_sections(app_context: dict) -> list[str]:
    current_user = app_context.get("current_user")
    if not current_user:
        return ["Dashboard"]
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
    if is_admin_identity:
        return [
            "Dashboard",
            "My Profile",
            "Products",
            "Product Approvals",
            "Manufacturers",
            "Marketplace",
            "Public Orders",
            "Client Orders",
            "RFQ",
            "Inventory Summary",
            "Commission Summary",
            "Payments",
            "Clients Preview",
            "Ledger Summary",
            "My Actions",
            "Notifications",
            "System Health",
        ]
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
    return ["Dashboard"]


def render_sidebar_navigation(app_context: dict) -> str:
    current_user = app_context.get("current_user")
    security_service = app_context["security_service"]
    is_admin_identity = security_service.is_admin_identity(current_user)
    sections = resolve_navigation_sections(app_context)
    with st.sidebar:
        st.markdown("## Navigation")
        if is_admin_identity:
            st.caption(f"SuperUser context: {ADMIN_CONTEXT_OPTIONS.get(app_context.get('active_context', 'platform_admin'), 'Platform Admin')}")
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
