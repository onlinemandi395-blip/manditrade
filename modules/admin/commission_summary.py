from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_commission_summary_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    supply_orders = governance_service.list_supply_orders()
    rows: list[dict] = []
    total_sale_value = 0.0
    total_procurement_value = 0.0
    total_margin = 0.0
    for order in supply_orders:
        sale_amount = float((order.get("commission_object") or {}).get("manufacturer_bill_amount", order.get("sale_amount", 0)) or 0)
        procurement_amount = float(order.get("amount_due_to_mahajan", order.get("procurement_amount", 0)) or 0)
        margin = round(sale_amount - procurement_amount, 2)
        rows.append(
            {
                "order_id": order.get("mandi_order_id", ""),
                "channel": order.get("network", "SUPPLY"),
                "sale_amount": round(sale_amount, 2),
                "procurement_amount": round(procurement_amount, 2),
                "margin": margin,
                "status": order.get("status", ""),
            }
        )
        total_sale_value += sale_amount
        total_procurement_value += procurement_amount
        total_margin += margin

    render_page_header("Ledger Margin Summary", "Legacy commission reporting is deprecated. Use this as a simple derived view of sale amount, procurement amount, and margin.", ["Ledger Derived", "Admin Summary"])
    render_metric_grid(
        [
            render_metric_card("Sale Amount", str(round(total_sale_value, 2)), "OPEN"),
            render_metric_card("Procurement Amount", str(round(total_procurement_value, 2)), "PENDING"),
            render_metric_card("Derived Margin", str(round(total_margin, 2)), "SUCCESS"),
        ]
    )
    render_section_intro("Ledger-Derived Summary", "This screen survives only as a compatibility alias. Margin is now treated as a ledger/analytics outcome rather than a standalone commission subsystem.")
    st.dataframe(rows, use_container_width=True)
