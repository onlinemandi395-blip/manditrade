from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_procurement_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    service = app_context["procurement_transaction_service"]
    governance_service = app_context["governance_service"]

    render_page_header(
        "Mandi Orders",
        "Manage admin-controlled raw-material trade where manufacturers request through admin and mahajans supply through the admin channel.",
        ["Mandi Order", user.role.replace("_", " ").title() if user else "Role"],
    )
    if not user:
        st.info("Sign in required.")
        return

    if user.role == "platform_admin":
        orders = service.list_supply_orders()
        render_metric_grid(
            [
                render_metric_card("Manufacturer Requests", str(len([item for item in orders if item.get("status") == "REQUESTED_BY_MANUFACTURER"])), "PENDING"),
                render_metric_card("Mahajan Quotes", str(len([item for item in orders if item.get("status") == "MAHAJAN_QUOTED"])), "OPEN"),
                render_metric_card("Confirmed Orders", str(len([item for item in orders if item.get("status") == "MANUFACTURER_CONFIRMED"])), "SUCCESS"),
                render_metric_card("Dispatched", str(len([item for item in orders if item.get("status") == "MAHAJAN_DISPATCHED"])), "WARNING"),
            ]
        )
        overview_tab, requests_tab, responses_tab, orders_tab = st.tabs(["Overview", "Requests", "Responses", "Orders"])
        with overview_tab:
            render_section_intro("Admin Supply Control", "Admin receives manufacturer demand, selects mahajan supply, sets downstream price, and captures commission.")
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            pending = [item for item in orders if item.get("status") in {"REQUESTED_BY_MANUFACTURER", "ADMIN_REVIEWING"}]
            st.dataframe(pending, use_container_width=True)
            if pending:
                selected_id = st.selectbox("Assign Mahajan", [item["mandi_order_id"] for item in pending], key="admin_assign_supply")
                mahajans = governance_service.list_mahajans()
                if mahajans:
                    selected_mahajan = st.selectbox("Mahajan", [item["mahajan_id"] for item in mahajans])
                    if st.button("Send To Mahajan", use_container_width=True):
                        service.assign_supply_to_mahajan(mandi_order_id=selected_id, mahajan_id=selected_mahajan, admin_email=user.email)
                        st.success("Supply request sent to mahajan.")
                        st.rerun()
                else:
                    st.info("Create or activate a mahajan first.")
            else:
                st.info("No manufacturer supply requests are waiting for mahajan assignment.")
        with responses_tab:
            quoted = [item for item in orders if item.get("status") == "MAHAJAN_QUOTED"]
            st.dataframe(quoted, use_container_width=True)
            if quoted:
                selected_id = st.selectbox("Set Manufacturer Price", [item["mandi_order_id"] for item in quoted], key="admin_price_supply")
                selected = next(item for item in quoted if item["mandi_order_id"] == selected_id)
                manufacturer_price = st.number_input("Manufacturer Unit Price", min_value=0.0, step=1.0, value=float(selected.get("manufacturer_unit_price", selected.get("mahajan_unit_price", 0)) or 0))
                fee_percent = st.number_input("Mahajan Fee Percent", min_value=0.0, step=0.5, value=1.0)
                if st.button("Set Admin Price", use_container_width=True):
                    updated = service.set_manufacturer_supply_price(
                        mandi_order_id=selected_id,
                        manufacturer_unit_price=manufacturer_price,
                        admin_email=user.email,
                        mahajan_fee_percent=fee_percent,
                    )
                    st.success("Manufacturer supply price set.")
                    st.json(updated.get("commission_object", {}), expanded=False)
                    st.rerun()
            else:
                st.info("No mahajan quotes are waiting for downstream pricing.")
        with orders_tab:
            st.dataframe(orders, use_container_width=True)
        return

    if user.role == "mahajan":
        mahajan = governance_service.get_mahajan_by_email(user.email)
        if not mahajan:
            st.info("Your mahajan profile is not linked yet. Ask admin to activate your supplier record.")
            return
        orders = service.list_supply_orders(mahajan_id=(mahajan or {}).get("mahajan_id"))
        render_metric_grid(
            [
                render_metric_card("Supply Orders", str(len(orders)), "OPEN"),
                render_metric_card("Awaiting Quote", str(len([item for item in orders if item.get("status") == "SENT_TO_MAHAJAN"])), "PENDING"),
                render_metric_card("Dispatched", str(len([item for item in orders if item.get("status") == "MAHAJAN_DISPATCHED"])), "SUCCESS"),
            ]
        )
        overview_tab, requests_tab, responses_tab, orders_tab = st.tabs(["Overview", "Requests", "Responses", "Orders"])
        with overview_tab:
            render_section_intro("Mahajan Supply Orders", "Mahajan only sees admin-linked supply requests and never sees manufacturer private networks.")
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            awaiting = [item for item in orders if item.get("status") == "SENT_TO_MAHAJAN"]
            st.dataframe(awaiting, use_container_width=True)
        with responses_tab:
            quotable = [item for item in orders if item.get("status") == "SENT_TO_MAHAJAN"]
            if quotable:
                selected_id = st.selectbox("Quote Supply Order", [item["mandi_order_id"] for item in quotable])
                price = st.number_input("Mahajan Unit Price", min_value=0.0, step=1.0)
                note = st.text_area("Mahajan Quote Note")
                if st.button("Submit Quote", use_container_width=True):
                    service.quote_supply_order(
                        mandi_order_id=selected_id,
                        mahajan_id=(mahajan or {}).get("mahajan_id", ""),
                        mahajan_unit_price=price,
                        mahajan_email=user.email,
                        notes=note,
                    )
                    st.success("Quote submitted.")
                    st.rerun()
            else:
                st.info("No supply orders are waiting for a mahajan quote.")
        with orders_tab:
            dispatchable = [item for item in orders if item.get("status") == "MANUFACTURER_CONFIRMED"]
            if dispatchable:
                selected_id = st.selectbox("Dispatch Order", [item["mandi_order_id"] for item in dispatchable], key="mahajan_dispatch_order")
                if st.button("Mark Dispatched", use_container_width=True):
                    service.dispatch_supply_order(mandi_order_id=selected_id, mahajan_id=(mahajan or {}).get("mahajan_id", ""), actor_email=user.email)
                    st.success("Supply order marked dispatched.")
                    st.rerun()
            else:
                st.info("No confirmed supply orders are ready for dispatch.")
            st.dataframe(orders, use_container_width=True)
        return

    if user.role in {"manufacturer", "admin_as_manufacturer"}:
        orders = service.list_supply_orders(manufacturer_code=user.manufacturer_code or "")
        materials = governance_service.list_raw_materials()
        render_metric_grid(
            [
                render_metric_card("Open Requests", str(len([item for item in orders if item.get("status") in {'REQUESTED_BY_MANUFACTURER', 'ADMIN_REVIEWING', 'SENT_TO_MAHAJAN', 'MAHAJAN_QUOTED', 'ADMIN_PRICE_SET'}])), "PENDING"),
                render_metric_card("Price Set", str(len([item for item in orders if item.get("status") == 'ADMIN_PRICE_SET'])), "OPEN"),
                render_metric_card("Confirmed", str(len([item for item in orders if item.get("status") == 'MANUFACTURER_CONFIRMED'])), "SUCCESS"),
            ]
        )
        overview_tab, requests_tab, responses_tab, orders_tab = st.tabs(["Overview", "Requests", "Responses", "Orders"])
        with overview_tab:
            render_section_intro("Admin-Controlled Supply", "Raw-material procurement is requested through admin. Manufacturers do not negotiate directly with mahajans.")
            st.dataframe(orders, use_container_width=True)
        with requests_tab:
            if not materials:
                st.info("No raw materials are available yet. Ask admin to onboard a mahajan catalog first.")
            else:
                with st.form("manufacturer_supply_request"):
                    raw_material_id = st.selectbox("Raw Material", [item["raw_material_id"] for item in materials])
                    qty = st.number_input("Qty", min_value=1.0, step=1.0, value=1.0)
                    unit = st.text_input("Unit", value="kg")
                    notes = st.text_area("Requirement Note")
                    submitted = st.form_submit_button("Create Mandi Request")
                if submitted and raw_material_id:
                    service.create_supply_request(
                        manufacturer_code=user.manufacturer_code or "",
                        raw_material_id=raw_material_id,
                        qty=qty,
                        unit=unit,
                        requested_by=user.email,
                        notes=notes,
                    )
                    st.success("Mandi supply request created for admin review.")
                    st.rerun()
        with responses_tab:
            priced = [item for item in orders if item.get("status") == "ADMIN_PRICE_SET"]
            st.dataframe(priced, use_container_width=True)
            if priced:
                selected_id = st.selectbox("Confirm Priced Supply Order", [item["mandi_order_id"] for item in priced], key="manufacturer_confirm_supply")
                if st.button("Confirm Supply Order", use_container_width=True):
                    service.confirm_supply_order(mandi_order_id=selected_id, manufacturer_code=user.manufacturer_code or "", actor_email=user.email)
                    st.success("Supply order confirmed.")
                    st.rerun()
        with orders_tab:
            receivable = [item for item in orders if item.get("status") == "MAHAJAN_DISPATCHED"]
            if receivable:
                selected_id = st.selectbox("Receive Supply Order", [item["mandi_order_id"] for item in receivable], key="manufacturer_receive_supply")
                if st.button("Mark Received", use_container_width=True):
                    service.receive_supply_order(mandi_order_id=selected_id, manufacturer_code=user.manufacturer_code or "", actor_email=user.email)
                    st.success("Supply order marked received.")
                    st.rerun()
            else:
                st.info("No dispatched supply orders are waiting for receipt.")
            st.dataframe(orders, use_container_width=True)
        return

    st.info("Mandi orders are not available for this role.")
