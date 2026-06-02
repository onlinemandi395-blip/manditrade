from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_commission_summary_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    order_query_service = app_context["order_query_service"]
    public_order_service = app_context["public_order_service"]
    supply_orders = app_context["governance_service"].list_supply_orders()
    rows: list[dict] = []
    total_trade_value = 0.0
    total_admin_commission = 0.0
    total_platform_fee = 0.0
    total_manufacturer_share = 0.0
    commission_states: dict[str, int] = {"CALCULATED": 0, "DUE": 0, "PAID": 0, "WAIVED": 0, "DISPUTED": 0}

    for manufacturer in governance_service.list_manufacturers():
        manufacturer_code = manufacturer.get("manufacturer_code", "")
        b2b_orders = order_query_service.list_orders(manufacturer_code)
        public_orders = public_order_service.list_orders_for_seller(manufacturer_code) if public_order_service else []
        b2b_trade_value = 0.0
        b2b_admin_commission = 0.0
        b2b_platform_fee = 0.0
        b2b_manufacturer_share = 0.0
        for order in b2b_orders:
            b2b_trade_value += sum(float(item.get("qty", 0)) * float(item.get("client_price", item.get("mrp", 0)) or 0) for item in order.get("items", []))
            for breakdown in order.get("commission_breakdown", []) or []:
                b2b_admin_commission += float(breakdown.get("admin_net_commission", breakdown.get("admin_commission", 0)) or 0)
                b2b_platform_fee += float(breakdown.get("platform_fee", 0) or 0)
                b2b_manufacturer_share += float(breakdown.get("manufacturer_profit_share", 0) or 0)
                commission_states[str(breakdown.get("commission_status", "CALCULATED")).upper()] = commission_states.get(str(breakdown.get("commission_status", "CALCULATED")).upper(), 0) + 1
        public_trade_value = sum(float(order.get("total_amount", 0) or 0) for order in public_orders)
        public_admin_commission = sum(float(breakdown.get("admin_net_commission", breakdown.get("admin_commission", 0)) or 0) for order in public_orders for breakdown in order.get("commission_breakdown", []) or [])
        public_platform_fee = sum(float(breakdown.get("platform_fee", 0) or 0) for order in public_orders for breakdown in order.get("commission_breakdown", []) or [])
        public_manufacturer_share = sum(float(breakdown.get("manufacturer_profit_share", 0) or 0) for order in public_orders for breakdown in order.get("commission_breakdown", []) or [])

        b2b_row = {
            "manufacturer_code": manufacturer_code,
            "manufacturer_name": manufacturer.get("business_name", manufacturer.get("manufacturer_name", "")),
            "channel": "B2B_MANDIPLACE",
            "gross_trade_value": round(b2b_trade_value, 2),
            "admin_commission": round(b2b_admin_commission, 2),
            "platform_fee": round(b2b_platform_fee, 2),
            "manufacturer_share": round(b2b_manufacturer_share, 2),
        }
        public_row = {
            "manufacturer_code": manufacturer_code,
            "manufacturer_name": manufacturer.get("business_name", manufacturer.get("manufacturer_name", "")),
            "channel": "PUBLIC_MARKETPLACE",
            "gross_trade_value": round(public_trade_value, 2),
            "admin_commission": round(public_admin_commission, 2),
            "platform_fee": round(public_platform_fee, 2),
            "manufacturer_share": round(public_manufacturer_share, 2),
        }
        rows.extend([b2b_row, public_row])
        total_trade_value += b2b_row["gross_trade_value"] + public_row["gross_trade_value"]
        total_admin_commission += b2b_row["admin_commission"] + public_row["admin_commission"]
        total_platform_fee += b2b_row["platform_fee"] + public_row["platform_fee"]
        total_manufacturer_share += b2b_row["manufacturer_share"] + public_row["manufacturer_share"]

    supply_commission = sum(float((item.get("commission_object") or {}).get("admin_total_earning", 0) or 0) for item in supply_orders)
    supply_trade_value = sum(float((item.get("commission_object") or {}).get("manufacturer_bill_amount", 0) or 0) for item in supply_orders)
    for item in supply_orders:
        commission_states[str((item.get("commission_object") or {}).get("commission_status", "CALCULATED")).upper()] = commission_states.get(str((item.get("commission_object") or {}).get("commission_status", "CALCULATED")).upper(), 0) + 1
    if supply_orders:
        rows.append(
            {
                "manufacturer_code": "ADMIN_SUPPLY",
                "manufacturer_name": "Admin-Mahajan Supply Channel",
                "channel": "MANDI_SUPPLY",
                "gross_trade_value": round(supply_trade_value, 2),
                "admin_commission": round(supply_commission, 2),
                "platform_fee": 0.0,
                "manufacturer_share": round(sum(float((item.get("commission_object") or {}).get("remaining_spread_share", 0) or 0) for item in supply_orders), 2),
                "commission_status": "DUE",
            }
        )
        total_trade_value += supply_trade_value
        total_admin_commission += supply_commission

    render_page_header("Commission Summary", "Read-only SuperAdmin commission analytics by manufacturer and channel without exposing private buyer identities.", ["SuperAdmin", "Commission Summary"])
    render_metric_grid(
        [
            render_metric_card("Gross Trade Value", str(round(total_trade_value, 2)), "OPEN"),
            render_metric_card("Admin Commission", str(round(total_admin_commission, 2)), "SUCCESS"),
            render_metric_card("Platform Fee", str(round(total_platform_fee, 2)), "PENDING"),
            render_metric_card("Manufacturer Share", str(round(total_manufacturer_share, 2)), "WARNING"),
        ]
    )
    render_section_intro("Channel-Level Summary", "Rows are aggregate-only and do not include buyer names, emails, mobiles, payment proposals, or private ledger notes.")
    st.caption(f"Commission states: {commission_states}")
    st.dataframe(rows, use_container_width=True)
