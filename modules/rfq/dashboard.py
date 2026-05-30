from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_3d_panel, render_metric_card, render_mobile_record_card, render_page_header


def render_rfq_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header(
        "Mandi RFQ",
        "Raise shortage-driven RFQs and manage supplier responses with flexible terms instead of rigid agreements.",
        ["RFQ", "Counter Proposal", "Trade Terms"],
        role=user.role.replace("_", " ").title() if user else "Manufacturer View",
        metrics=[("Negotiation Surface", "Request + response"), ("Trade Model", "Flexible terms")],
        kicker="Digital Manpur Negotiation Board",
    )
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
    overview_tab, requests_tab, responses_tab = st.tabs(["Overview", "RFQ Requests", "Responses"])
    with overview_tab:
        render_section_intro("Open RFQs", "Use mandi network only for shortages while keeping self inventory reserved for your own clients.")
        render_html(
            """
            <div class="mt-grid mt-grid--panels">
              <article class="mt-panel mt-rfq-card">
                <h3 class="mt-panel__title">Request Board</h3>
                <p>Buyer-side shortage requests stay visible with trade terms, delivery intent, and quantity context.</p>
                <div class="mt-chip-row">
                  <span class="mt-chip">Buyer intent</span>
                  <span class="mt-chip">Trade terms</span>
                  <span class="mt-chip">Delivery location</span>
                </div>
              </article>
              <article class="mt-panel mt-market-card">
                <h3 class="mt-panel__title">Response Board</h3>
                <p>Supplier responses remain separated so price, available quantity, and notes feel like a negotiation lane.</p>
                <div class="mt-chip-row">
                  <span class="mt-chip">Supplier terms</span>
                  <span class="mt-chip">Availability</span>
                  <span class="mt-chip">Freestyle notes</span>
                </div>
              </article>
            </div>
            """
        )
        if requests:
            render_3d_panel("".join(render_mobile_record_card(item) for item in requests[:4]), "RFQ Feed", tone="subtle")
        else:
            st.info("No RFQ requests are active right now.")
    with requests_tab:
        st.dataframe(requests, use_container_width=True)
    with responses_tab:
        invalid_responses = [
            response
            for response in responses
            if any(
                float(item.get("offered_unit_price", item.get("unit_price", 0)) or 0) <= 0
                or int(item.get("qty", 0) or 0) <= 0
                for item in response.get("available_items", [])
            )
        ]
        if invalid_responses:
            st.error("One or more RFQ responses are missing valid offered pricing. Buyer acceptance stays blocked until supplier pricing is corrected.")
        st.dataframe(responses, use_container_width=True)
