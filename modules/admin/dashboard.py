from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_dual_panel, render_metric_card, render_mobile_record_card, render_page_header, render_showcase_strip


def _build_supervisory_rows(app_context: dict) -> list[dict]:
    governance_service = app_context["governance_service"]
    products = governance_service.list_products()
    manufacturers = governance_service.list_manufacturers()
    actions = app_context["action_center_service"].get_actions(type("User", (), {"role": "platform_admin"})())
    pending_products = [item for item in products if item.get("status") == "PROPOSED"]
    active_products = [item for item in products if item.get("status") == "ACTIVE"]
    public_orders = app_context["public_order_service"].list_all_orders() if app_context.get("public_order_service") else []
    rfq_service = app_context.get("procurement_transaction_service")
    client_service = app_context.get("client_service")
    order_query_service = app_context.get("order_query_service")
    ledger_service = app_context.get("ledger_service")

    rows = []
    for manufacturer in manufacturers:
        manufacturer_code = manufacturer.get("manufacturer_code", "")
        client_summary = client_service.summarize_clients(manufacturer_code) if client_service else {"total_clients": 0, "active_clients": 0}
        private_order_summary = order_query_service.summarize_orders(manufacturer_code) if order_query_service else {"total_orders": 0, "total_value": 0.0}
        ledger_summary = ledger_service.summarize_ledgers(manufacturer_code) if ledger_service else {"total_entries": 0, "pending_entries": 0, "total_balance_due": 0.0}
        rfq_requests = rfq_service.list_requests(manufacturer_code) if rfq_service else []
        rfq_responses = rfq_service.list_responses(manufacturer_code) if rfq_service else []
        manufacturer_public_orders = [item for item in public_orders if item.get("assigned_seller_manufacturer_id") == manufacturer_code]
        rows.append(
            {
                "manufacturer_code": manufacturer_code,
                "status": manufacturer.get("status", "ACTIVE"),
                "subscription_plan": manufacturer.get("subscription_plan", "basic"),
                "product_categories": ", ".join(manufacturer.get("product_categories", []) or []),
                "client_count": client_summary["total_clients"],
                "active_client_count": client_summary["active_clients"],
                "private_order_count": private_order_summary["total_orders"],
                "private_order_value": private_order_summary["total_value"],
                "rfq_request_count": len(rfq_requests),
                "rfq_response_count": len(rfq_responses),
                "public_order_count": len(manufacturer_public_orders),
                "public_order_value": round(sum(float(item.get("grand_total", 0) or 0) for item in manufacturer_public_orders), 2),
                "ledger_entry_count": ledger_summary["total_entries"],
                "pending_ledger_entries": ledger_summary["pending_entries"],
                "ledger_balance_due": ledger_summary["total_balance_due"],
            }
        )
    return rows, pending_products, active_products, actions, public_orders


def render_admin_dashboard(app_context: dict, section: str = "Dashboard") -> None:
    active_context = app_context.get("active_context", "platform_admin")
    render_page_header("SuperUser Control Center", "One admin identity with context-aware previews, platform controls, and privacy-safe manufacturer supervision.", ["SuperUser", "Context Switch"])
    rows, pending_products, active_products, actions, public_orders = _build_supervisory_rows(app_context)

    render_metric_grid(
        [
            render_metric_card("Manufacturers", str(len(rows)), "SUCCESS"),
            render_metric_card("Products", str(len(pending_products) + len(active_products)), "OPEN"),
            render_metric_card("Pending Actions", str(sum(int(item.get("count", 0)) for item in actions)), "HIGH_PRIORITY"),
            render_metric_card("Public Orders", str(len(public_orders)), "CONFIRMED"),
        ]
    )
    render_showcase_strip(
        [
            ("Platform Control", "Enabled", "SUCCESS"),
            ("Context View", active_context.replace("_", " ").title(), "OPEN"),
            ("System Health", "Available", "PENDING"),
        ]
    )
    render_dual_panel(
        "Approval Focus",
        render_mobile_record_card({"Pending Products": len(pending_products), "Active Products": len(active_products)}),
        "Supervision Focus",
        render_mobile_record_card({"Manufacturers": len(rows), "Actions": sum(int(item.get("count", 0)) for item in actions), "Public Orders": len(public_orders)}),
    )
    if section == "Inventory Summary":
        render_section_intro("Inventory Summary", "SuperAdmin sees manufacturer-level inventory impact through private-order and RFQ activity summaries only.")
        st.dataframe(rows, use_container_width=True)
    elif section == "Commission Summary":
        render_section_intro("Commission Summary", "Commission supervision is limited to aggregate public order values and manufacturer-level balances, never raw client ledgers.")
        st.dataframe(rows, use_container_width=True)
    elif section == "RFQ":
        render_section_intro("RFQ Summary", "Cross-manufacturer RFQ supervision stays aggregate and operational, without exposing private negotiation threads or client records.")
        st.dataframe(rows, use_container_width=True)
    elif section == "Payments":
        render_section_intro("Payments Summary", "Payments supervision shows aggregate manufacturer receivable load and public-order throughput, not private client notes.")
        st.dataframe(rows, use_container_width=True)
    elif section == "Clients Preview":
        render_section_intro("Clients Preview", "Client supervision is aggregate-only by manufacturer. Raw client names, emails, phones, and addresses are intentionally hidden.")
        st.dataframe([{k: row[k] for k in ("manufacturer_code", "status", "subscription_plan", "client_count", "active_client_count")} for row in rows], use_container_width=True)
    elif section == "Ledger Summary":
        render_section_intro("Ledger Summary", "Ledger supervision shows pending counts and due totals only. Private notes and proposal detail stay hidden.")
        st.dataframe([{k: row[k] for k in ("manufacturer_code", "ledger_entry_count", "pending_ledger_entries", "ledger_balance_due")} for row in rows], use_container_width=True)
    elif section == "Client Orders":
        render_section_intro("Client Orders Summary", "Private client order supervision remains aggregate-only outside the ADMIN_MANU operating context.")
        st.dataframe([{k: row[k] for k in ("manufacturer_code", "private_order_count", "private_order_value", "rfq_request_count", "rfq_response_count")} for row in rows], use_container_width=True)
    else:
        render_section_intro("Governance Overview", "Dashboard is summary-only in supervisor mode. Switch context to preview manufacturer, client, public-buyer, or worker surfaces while preserving admin authority.")
        st.dataframe(rows, use_container_width=True)
    st.info("SuperAdmin visibility is aggregate-only for manufacturer private business. Raw client names, emails, notes, delivery addresses, and negotiation comments stay hidden.")
