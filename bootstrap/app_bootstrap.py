from __future__ import annotations

import streamlit as st

from bootstrap.route_registry import render_route
from bootstrap.service_container import build_app_context
from utils.session import clear_runtime_session, ensure_session_defaults, pop_flash, set_flash


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
        auth_service = app_context["auth_service"]
        if user:
            st.success(f"{user.name} signed in as {user.role}")
            if user.manufacturer_code:
                st.caption(f"Manufacturer: {user.manufacturer_code}")
            if st.session_state.get("admin_runtime_unlocked"):
                st.caption("Admin runtime access is unlocked for this session.")
            if st.button("Logout", use_container_width=True):
                app_context["security_service"].revoke_runtime_session()
                clear_runtime_session()
                set_flash("Session closed and runtime tokens cleared.")
                st.rerun()
            return

        auth_url = app_context["oauth_callback_service"].build_authorization_url()
        if auth_url and app_context["google_runtime_enabled"]:
            st.link_button("Google Login", auth_url, use_container_width=True)
        else:
            st.info("Google OAuth staging is not ready yet. Demo mode is active for local setup.")

        if app_context["system_config"]["app"].get("runtime_environment", "local") == "local" and auth_service.enable_mock_auth:
            with st.expander("Mock Sign In", expanded=True):
                role = st.selectbox("Role", ["admin", "manufacturer", "client"])
                email = st.text_input("Email", value="admin@manditrade.local")
                name = st.text_input("Name", value="MandiTrade User")
                manufacturer_code = st.text_input("Manufacturer Code", value="MANU101" if role in {"manufacturer", "client"} else "")
                if st.button("Start Session", use_container_width=True):
                    user = auth_service.create_mock_user(
                        email=email.strip(),
                        name=name.strip(),
                        role=role,
                        manufacturer_code=manufacturer_code.strip().upper() or None,
                    )
                    st.session_state["user"] = auth_service.serialize_user(user)
                    set_flash(f"Signed in as {user.role}.")
                    st.rerun()


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
        credentials = app_context["auth_service"].refresh_credentials(token_payload)
        profile = app_context["auth_service"].fetch_google_profile(credentials)
        email = profile.get("email", "")
        admin_email = app_context["security_service"].get_admin_email()
        role = "admin" if admin_email and email.lower() == admin_email.lower() else "manufacturer"
        app_context["oauth_callback_service"].initialize_session(
            user_payload={"email": email, "name": profile.get("name", email), "role": role},
            credentials_payload=token_payload,
            manufacturer_code=st.session_state.get("manufacturer_context"),
        )
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        set_flash("OAuth session initialized.")
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        app_context["logging_service"].log_error("oauth_errors", str(exc), {"state": state})
        app_context["oauth_callback_service"].reset_authorization_state()
        st.query_params.clear()
        st.error(f"OAuth callback failed: {exc}")


def render_security_panel(app_context: dict) -> None:
    with st.sidebar:
        st.markdown("## Runtime Security")
        security_service = app_context["security_service"]
        current_user = app_context["current_user"]
        status = security_service.export_security_status()
        st.caption("Streamlit Cloud secrets hold only the verification layer and OAuth identifiers. Encrypted tokens stay outside TOML.")
        if current_user and current_user.role == "admin":
            with st.expander("Unlock Admin Drive Runtime", expanded=not st.session_state.get("admin_runtime_unlocked", False)):
                verification_key = st.text_input("Verification Key", type="password")
                if st.button("Validate Runtime Access", use_container_width=True):
                    try:
                        runtime_state = security_service.unlock_admin_runtime(current_user, verification_key)
                        set_flash(f"Admin runtime unlocked for {runtime_state['principal']}.")
                        st.rerun()
                    except Exception as exc:  # noqa: BLE001
                        st.error(str(exc))
        else:
            st.info("Admin runtime unlock is available only to the signed-in admin identity.")
        st.write(
            {
                "verification_configured": status["verification_configured"],
                "admin_runtime_unlocked": st.session_state.get("admin_runtime_unlocked", False),
                "token_file_present": status["admin_token_file_present"],
                "token_placeholder_detected": status["admin_token_placeholder"],
                "long_lived_admin_runtime_enabled": app_context.get("long_lived_admin_runtime_enabled", False),
            }
        )


def render_sidebar_navigation() -> str:
    sections = [
        "Dashboard",
        "Onboarding",
        "Inventory",
        "Pricing",
        "Procurement",
        "Agreements",
        "Notifications",
        "Dispatch",
        "Analytics",
        "System Health",
        "Client Onboarding",
        "Client",
    ]
    with st.sidebar:
        st.markdown("## Navigation")
        return st.radio("Go to", sections, label_visibility="collapsed")


def main() -> None:
    ensure_session_defaults()
    app_context = build_app_context()
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
    render_security_panel(app_context)
    section = render_sidebar_navigation()
    render_header(app_context)
    render_route(section, app_context)
