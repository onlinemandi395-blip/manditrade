from __future__ import annotations

import streamlit as st

from services.json_service import JsonService


def render_inventory_management(app_context: dict) -> None:
    user = app_context["current_user"]
    st.subheader("Inventory")

    if not user or user.role not in {"manufacturer", "admin_as_manufacturer"} or not user.manufacturer_code:
        st.info("Inventory management is available for signed-in manufacturers.")
        return

    dual_inventory_service = app_context["dual_inventory_service"]
    inventory = dual_inventory_service.list_inventory(user.manufacturer_code)

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
    st.dataframe(inventory.get("items", []), use_container_width=True)
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
