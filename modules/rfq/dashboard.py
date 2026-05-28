from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_rfq_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header("Mandi RFQ", "Raise shortage-driven RFQs and manage supplier responses with flexible terms instead of rigid agreements.", ["RFQ", "Counter Proposal", "Trade Terms"])
    if not user or not user.manufacturer_code:
        st.info("Manufacturer-linked session required.")
        return
    service = app_context["procurement_transaction_service"]
    requests = service.list_requests(user.manufacturer_code)
    responses = service.list_responses(user.manufacturer_code)
    render_metric_grid(
        [
            render_metric_card("RFQs", str(len(requests)), "OPEN"),
            render_metric_card("Responses", str(len(responses)), "PENDING"),
            render_metric_card("Buyer Confirmed", str(len([item for item in requests if item.get("status") == "BUYER_CONFIRMED"])), "WARNING"),
        ]
    )
    render_section_intro("Open RFQs", "Use mandi network only for shortages while keeping self inventory reserved for your own clients.")
    if requests:
        render_3d_panel("".join(render_mobile_record_card(item) for item in requests[:4]), "RFQ Feed")
    st.dataframe(requests, use_container_width=True)
    st.markdown("### Responses")
    st.dataframe(responses, use_container_width=True)
