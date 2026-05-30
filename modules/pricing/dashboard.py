from __future__ import annotations

import streamlit as st

def render_pricing_dashboard(app_context: dict) -> None:
    st.subheader("Pricing Governance")
    st.caption("Governed pricing preview controlled by admin policy.")

    pricing_service = app_context["pricing_service"]
    client_price = st.number_input("Client Price", min_value=0.0, value=145.0, step=1.0)
    marketplace_price = st.number_input("Marketplace Price", min_value=0.0, value=160.0, step=1.0)
    mandi_price = st.number_input("Mandi Price", min_value=0.0, value=120.0, step=1.0)
    subscription = st.selectbox("Subscription", ["basic", "premium", "premium_plus"], index=0)
    result = pricing_service.calculate_commission(
        {"mandi_price": mandi_price, "client_price": client_price, "marketplace_price": marketplace_price},
        pricing_service.CHANNEL_PRIVATE_CLIENT,
        subscription,
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Gross Profit", f"Rs {result['gross_profit']}")
    col2.metric("Admin Net", f"Rs {result['admin_net_commission']}")
    col3.metric("Manufacturer Share", f"Rs {result['manufacturer_profit_share']}")
