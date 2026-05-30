from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_clients_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Clients", "Maintain your private client network, not a public ecommerce checkout funnel.", ["Private Clients", "Manufacturer Workspace"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    clients = app_context["client_service"].list_clients(user.manufacturer_code)
    render_metric_grid([render_metric_card("Clients", str(len(clients)), "SUCCESS")])
    overview_tab, registry_tab = st.tabs(["Overview", "Client Registry"])
    with overview_tab:
        render_section_intro("Client Network", "This view remains private to each manufacturer and stays outside the shared mandi layer.")
        if clients:
            render_3d_panel("".join(render_mobile_record_card(item) for item in clients[:4]), "Recent Clients")
        else:
            st.info("No private clients are linked yet.")
    with registry_tab:
        st.dataframe(clients, use_container_width=True)
