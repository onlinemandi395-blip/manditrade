from __future__ import annotations

import streamlit as st


def render_client_profile(app_context: dict) -> None:
    current_user = app_context["current_user"]
    st.subheader("Client Profile")
    if not current_user or not current_user.manufacturer_code:
        st.info("Sign in with a client session linked to a manufacturer to view profile data.")
        return
    profiles = app_context["client_service"].list_client_profiles(current_user.manufacturer_code)
    profile = next((item for item in profiles if item.get("email", "").lower() == current_user.email.lower()), None)
    if not profile:
        st.info("No active client profile found yet.")
        return
    st.json(profile)
