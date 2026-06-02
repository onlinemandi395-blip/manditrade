from __future__ import annotations

import streamlit as st

from services.json_service import JsonService


def render_agreements_dashboard(app_context: dict) -> None:
    st.subheader("Agreements")
    current_user = app_context["current_user"]
    if not current_user or not current_user.manufacturer_code:
        st.info("Sign in with a manufacturer-linked session to view agreements.")
        return
    json_service = JsonService()
    paths = app_context["drive_service"].get_manufacturer_paths(current_user.manufacturer_code)
    agreements = json_service.read_json(paths.shared_zone / "agreements.json", {"agreements": []}).get("agreements", [])
    st.dataframe(agreements, use_container_width=True)
