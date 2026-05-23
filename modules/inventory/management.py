from __future__ import annotations

import streamlit as st

from services.json_service import JsonService


def render_inventory_management(app_context: dict) -> None:
    user = app_context["current_user"]
    st.subheader("Inventory Management")

    if not user or user.role != "manufacturer" or not user.manufacturer_code:
        st.info("Inventory management is available for signed-in manufacturers.")
        return

    drive_service = app_context["drive_service"]
    safe_drive_write_service = app_context["safe_drive_write_service"]
    json_service = JsonService()
    audit_service = app_context["audit_service"]
    paths = drive_service.get_manufacturer_paths(user.manufacturer_code)
    inventory_path = paths.shared_zone / "inventory.json"
    inventory = json_service.read_json(inventory_path, {"manufacturer_code": user.manufacturer_code, "items": []})
    movement_log_path = paths.shared_zone / "inventory_movements.json"
    movement_log = json_service.read_json(movement_log_path, {"movements": []})

    with st.form("add_inventory_item"):
        product_code = st.text_input("Product Code")
        product_name = st.text_input("Product Name")
        quantity = st.number_input("Quantity", min_value=0, step=1)
        city = st.text_input("City", value="Jaipur")
        submit = st.form_submit_button("Add Item")

    if submit and product_code and product_name:
        new_item = {
            "product_code": product_code.strip(),
            "product_name": product_name.strip(),
            "quantity": int(quantity),
            "city": city.strip(),
            "reserved_quantity": 0,
        }
        safe_drive_write_service.append_record(
            inventory_path,
            "items",
            new_item,
            schema_name="inventory",
        )
        safe_drive_write_service.append_record(
            movement_log_path,
            "movements",
            {
                "action": "add",
                "product_code": product_code.strip(),
                "quantity": int(quantity),
                "city": city.strip(),
            },
        )
        audit_service.log_event(
            "inventory_item_added",
            actor=user.email,
            details={"manufacturer_code": user.manufacturer_code, "product_code": product_code.strip(), "quantity": int(quantity)},
        )
        st.success("Inventory item saved to shared zone.")
        st.rerun()

    inventory = json_service.read_json(inventory_path, {"manufacturer_code": user.manufacturer_code, "items": []})
    movement_log = json_service.read_json(movement_log_path, {"movements": []})
    st.dataframe(inventory.get("items", []), use_container_width=True)
    st.markdown("### Inventory Movement Log")
    st.dataframe(movement_log.get("movements", []), use_container_width=True)
