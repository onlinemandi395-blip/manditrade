from __future__ import annotations

import streamlit as st

from components.html_renderer import render_html
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_inventory_management(app_context: dict) -> None:
    user = app_context["current_user"]
    render_page_header(
        "Inventory",
        "Run self stock and mandi stock separately, with explicit transfer controls between both buckets.",
        ["Dual Inventory", "Self -> Mandi", "Mandi -> Self"],
        role=user.role.replace("_", " ").title() if user else "Inventory View",
        metrics=[("Split Model", "Self + mandi"), ("Control Mode", "Explicit transfers")],
        kicker="Digital Manpur Stock Plane",
    )

    if not user or user.role not in {"manufacturer", "admin_as_manufacturer", "platform_admin"} or not user.manufacturer_code:
        st.info("Inventory management is available for signed-in manufacturers.")
        return

    dual_inventory_service = app_context["dual_inventory_service"]
    inventory = dual_inventory_service.list_inventory(user.manufacturer_code)
    render_metric_grid(
        [
            render_metric_card("Products Tracked", str(len(inventory.get("items", []))), "SUCCESS"),
            render_metric_card(
                "Self Available",
                str(sum(int(item.get("self_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))),
                "OPEN",
            ),
            render_metric_card(
                "Mandi Available",
                str(sum(int(item.get("mandi_inventory", {}).get("available_qty", 0)) for item in inventory.get("items", []))),
                "PENDING",
            ),
        ]
    )
    overview_tab, add_tab, transfer_tab = st.tabs(["Overview", "Add / Update Item", "Transfer Controls"])
    with overview_tab:
        render_section_intro("Transfer Controls", "Self inventory stays private for client orders until you explicitly push it into mandi inventory.")
        render_html(
            """
            <div class="mt-surface-note">
              This inventory surface separates private manufacturer stock from mandi-shareable stock. The shell is more futuristic,
              but the operational rule stays strict: nothing moves between buckets unless you do it explicitly.
            </div>
            """
        )
        st.dataframe(inventory.get("items", []), use_container_width=True)
    with add_tab:
        with st.form("add_inventory_item"):
            product_code = st.text_input("Product ID")
            product_name = st.text_input("Product Name")
            unit = st.text_input("Unit", value="kg")
            self_qty = st.number_input("Self Inventory Qty", min_value=0, step=1)
            mandi_qty = st.number_input("Mandi Inventory Qty", min_value=0, step=1)
            submit = st.form_submit_button("Add Item")

        if submit and product_code and product_name:
            dual_inventory_service.upsert_inventory_item(
                user.manufacturer_code,
                product_id=product_code.strip(),
                product_name=product_name.strip(),
                unit=unit.strip(),
                self_available_qty=int(self_qty),
                mandi_available_qty=int(mandi_qty),
            )
            st.success("Dual inventory item saved.")
            st.rerun()
    with transfer_tab:
        if inventory.get("items"):
            selected = st.selectbox("Inventory Action Product", [item["product_id"] for item in inventory["items"]])
            transfer_qty = st.number_input("Transfer Qty", min_value=1, step=1)
            col1, col2 = st.columns(2)
            if col1.button("Transfer Self -> Mandi", use_container_width=True):
                dual_inventory_service.transfer_self_to_mandi(user.manufacturer_code, selected, int(transfer_qty))
                st.rerun()
            if col2.button("Withdraw Mandi -> Self", use_container_width=True):
                dual_inventory_service.withdraw_mandi_to_self(user.manufacturer_code, selected, int(transfer_qty))
                st.rerun()
        else:
            st.info("Add an inventory item first to use transfer controls.")
