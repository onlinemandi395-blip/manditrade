from __future__ import annotations

import streamlit as st


def render_actions_dashboard(app_context: dict) -> None:
    st.subheader("My Actions")
    user = app_context["current_user"]
    if not user:
        st.info("Sign in to see pending actions.")
        return
    actions = app_context["action_center_service"].get_actions(user)
    if not actions:
        st.success("No pending actions right now.")
        return
    st.dataframe(actions, use_container_width=True)
