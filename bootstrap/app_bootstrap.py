from __future__ import annotations

from pathlib import Path

import streamlit as st

from bootstrap.route_registry import render_route
from bootstrap.service_container import build_app_context
from components.html_renderer import render_html
from components.ui_shell import render_configurable_link_button
from components.ui_shell import apply_ui_shell
from services.navigation_service import flatten_navigation_groups, get_navigation_groups
from utils.session import clear_runtime_session, ensure_session_defaults, pop_flash, set_flash


BUILD_FILE = Path(__file__).resolve()
CSS_FILE = BUILD_FILE.parent.parent / "assets" / "styles" / "manditrade_3d.css"
ADMIN_CONTEXT_OPTIONS = {
    "platform_admin": "Platform Admin",
    "mahajan": "Mahajan",
    "manufacturer": "Manufacturer",
    "public_buyer": "Public Buyer",
    "worker": "Worker",
}


def _resolve_navigation_role(app_context: dict) -> str:
    current_user = app_context.get("current_user")
    session_user = app_context.get("session_user") or current_user
    security_service = app_context["security_service"]

    if not current_user:
        return "unauthenticated"

    role = (current_user.role or "").strip().lower()
    normalized_role = "manufacturer" if role == "admin_as_manufacturer" else role

    if security_service.is_admin_identity(session_user) and normalized_role == "platform_admin":
        return "platform_admin"
    if normalized_role in {"mahajan", "manufacturer", "public_buyer", "worker", "pending_user"}:
        return normalized_role
    return "manufacturer"


def _resolve_login_navigation_mode(app_context: dict) -> str:
    configured = str(app_context["system_config"].get("oauth", {}).get("login_navigation_mode", "new_tab")).strip().lower()
    return configured if configured in {"same_tab", "new_tab"} else "new_tab"


def _show_admin_debug_text(app_context: dict) -> bool:
    session_user = app_context.get("session_user") or app_context.get("current_user")
    return bool(
        app_context["system_config"].get("ui", {}).get("show_debug_text", False)
        and app_context["security_service"].is_admin_identity(session_user)
    )


def render_header(app_context: dict) -> None:
    if not app_context.get("current_user"):
        render_html(
            f"""
            <section class="mt-top-login-bar">
              <div class="mt-top-login-bar__brand">
                <strong>{app_context["system_config"]["app"]["name"]}</strong>
                <span>{app_context["system_config"]["app"]["tagline"]}</span>
              </div>
            </section>
            """
        )
    else:
        st.title(app_context["system_config"]["app"]["name"])
        st.caption(app_context["system_config"]["app"]["tagline"])
    if app_context["startup_checks"]:
        st.error("Some services are temporarily unavailable. Please try again shortly.")
    elif app_context.get("startup_warnings") and _show_admin_debug_text(app_context):
        st.warning("Deployment warnings: " + " | ".join(app_context["startup_warnings"]))
    if app_context["config_issues"] and _show_admin_debug_text(app_context):
        st.warning("Configuration issues detected: " + " | ".join(app_context["config_issues"]))
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
                set_flash("Signed out successfully.")
                st.rerun()
            return
        login_navigation_mode = _resolve_login_navigation_mode(app_context)
        st.session_state["oauth_login_navigation_mode"] = login_navigation_mode
        login_blocked_for_cloud_fallback = (
            app_context["system_config"]["app"].get("runtime_environment") == "staging_cloud"
            and app_context.get("oauth_config_fallback_active", False)
        )
        auth_url = None if login_blocked_for_cloud_fallback else app_context["oauth_callback_service"].build_authorization_url(flow_type=app_context["oauth_callback_service"].LOGIN)
        if login_blocked_for_cloud_fallback:
            render_html("<span class='mt-sidebar-google-login mt-sidebar-google-login--disabled'>Sign-in temporarily unavailable</span>")
        elif auth_url and app_context["google_runtime_enabled"]:
            render_html(
                render_configurable_link_button(
                    "Continue with Google",
                    auth_url,
                    navigation_mode=login_navigation_mode,
                    class_name="mt-sidebar-google-login",
                )
            )
        else:
            render_html("<span class='mt-sidebar-google-login mt-sidebar-google-login--disabled'>Sign-in temporarily unavailable</span>")


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
        app_context["oauth_callback_service"].generate_same_tab_rca_report(
            login_navigation_mode=_resolve_login_navigation_mode(app_context),
            failure_reason=str(error_description or error or ""),
        )
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
        app_context["oauth_callback_service"].generate_same_tab_rca_report(
            login_navigation_mode=_resolve_login_navigation_mode(app_context),
        )
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
        set_flash("Signed in successfully.")
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        app_context["logging_service"].log_error("oauth_errors", str(exc), {"state": state})
        app_context["oauth_callback_service"].generate_same_tab_rca_report(
            login_navigation_mode=_resolve_login_navigation_mode(app_context),
            failure_reason=str(exc),
        )
        app_context["oauth_callback_service"].capture_failure(
            error="oauth_callback_failed",
            error_description=str(exc),
            state=str(state or ""),
        )
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        st.error(f"OAuth callback failed: {exc}")


def resolve_navigation_sections(app_context: dict) -> list[str]:
    return flatten_navigation_groups(get_navigation_groups(_resolve_navigation_role(app_context)))


def render_sidebar_navigation(app_context: dict) -> str:
    current_user = app_context.get("current_user")
    session_user = app_context.get("session_user") or current_user
    is_admin_identity = app_context["security_service"].is_admin_identity(session_user)
    navigation_role = _resolve_navigation_role(app_context)
    groups = get_navigation_groups(navigation_role)
    sections = flatten_navigation_groups(groups)
    selected = app_context["session_state_service"].get_navigation(sections[0] if sections else "Dashboard")
    if selected not in sections:
        selected = sections[0] if sections else "Dashboard"
        app_context["session_state_service"].set_navigation(selected)
    with st.sidebar:
        st.markdown("## Navigation")
        if is_admin_identity:
            st.caption(f"SuperUser context: {ADMIN_CONTEXT_OPTIONS.get(app_context.get('active_context', 'platform_admin'), 'Platform Admin')}")
        for group, items in groups:
            st.caption(group.upper())
            for item in items:
                if st.button(item, key=f"nav_{item.lower().replace(' ', '_')}", use_container_width=True, type="primary" if selected == item else "secondary"):
                    selected = item
                    app_context["session_state_service"].set_navigation(item)
        return selected


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
