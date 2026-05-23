from __future__ import annotations

import streamlit as st

from services.commission_service import CommissionService


def render_pricing_dashboard(app_context: dict) -> None:
    st.subheader("Pricing Governance")
    st.caption("Governed pricing preview controlled by admin policy.")

    commission_service = CommissionService(app_context["system_config"]["governance"]["admin_profit_share_ratio"])
    mrp = st.number_input("MRP", min_value=0.0, value=145.0, step=1.0)
    mandi_price = st.number_input("Mandi Price", min_value=0.0, value=120.0, step=1.0)
    result = commission_service.calculate(mrp=mrp, mandi_price=mandi_price)

    col1, col2, col3 = st.columns(3)
    col1.metric("Net Profit", f"Rs {result['net_profit']}")
    col2.metric("Admin Share", f"Rs {result['admin_share']}")
    col3.metric("Manufacturer Share", f"Rs {result['manufacturer_share']}")
