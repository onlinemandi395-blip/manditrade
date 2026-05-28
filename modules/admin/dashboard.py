from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_admin_dashboard(app_context: dict) -> None:
    render_page_header("Platform Admin Dashboard", "Govern product approvals, manufacturer onboarding, and platform health without entering the old ERP agreement model.", ["Platform Admin", "Governance"])
    governance_service = app_context["governance_service"]
    manufacturer_onboarding_service = app_context["manufacturer_onboarding_service"]
    products = governance_service.list_products()
    manufacturers = governance_service.list_manufacturers()
    actions = app_context["action_center_service"].get_actions(type("User", (), {"role": "platform_admin"})())
    pending_products = [item for item in products if item.get("status") == "PENDING_APPROVAL"]
    active_products = [item for item in products if item.get("status") == "ACTIVE"]

    render_metric_grid(
        [
            render_metric_card("Manufacturers", str(len(manufacturers)), "SUCCESS"),
            render_metric_card("Products", str(len(products)), "OPEN"),
            render_metric_card("Pending Actions", str(sum(int(item.get("count", 0)) for item in actions)), "HIGH_PRIORITY"),
            render_metric_card("Approved Products", str(len(active_products)), "CONFIRMED"),
        ]
    )

    render_section_intro("Pending Product Approval", "Approve product proposals, set mandi price and MRP, then keep them visible in the all-products catalog.")
    st.dataframe(pending_products, use_container_width=True)
    if pending_products:
        selected = st.selectbox("Approve Product", [item["product_id"] for item in pending_products])
        mandi_price = st.number_input("Mandi Price", min_value=0.0, step=1.0)
        mrp = st.number_input("MRP", min_value=0.0, step=1.0)
        if st.button("Approve Selected Product", use_container_width=True):
            app_context["product_catalog_service"].approve_product(product_id=selected, approved_by="PLATFORM_ADMIN", mandi_price=mandi_price, mrp=mrp)
            st.success("Product approved.")
            st.rerun()
    else:
        st.info("No products are pending approval.")

    st.markdown("### All Products")
    st.dataframe(products, use_container_width=True)

    render_section_intro("Manufacturer Registry", "Onboard new manufacturers, issue onboarding secrets, and share admin-approved steps.")
    with st.form("create_manufacturer_onboarding"):
        col1, col2 = st.columns(2)
        manufacturer_code = col1.text_input("Manufacturer Code", placeholder="MANU101")
        manufacturer_name = col2.text_input("Manufacturer Name", placeholder="Shree Agro Traders")
        owner_email = col1.text_input("Owner Email", placeholder="owner@example.com")
        city = col2.text_input("City", placeholder="Jaipur")
        subscription_plan = st.text_input("Subscription Plan", value="basic")
        create_submit = st.form_submit_button("Create Manufacturer Onboarding")
    if create_submit and manufacturer_code and manufacturer_name:
        actor = app_context["current_user"].email if app_context.get("current_user") else "PLATFORM_ADMIN"
        created = manufacturer_onboarding_service.create_manufacturer(
            manufacturer_code=manufacturer_code,
            manufacturer_name=manufacturer_name,
            owner_email=owner_email,
            city=city,
            created_by=actor,
            subscription_plan=subscription_plan,
        )
        st.success(f"Manufacturer {created['manufacturer_code']} created with onboarding secret.")
        st.code(created["manufacturer_onboarding_steps"], language="text")
        st.rerun()

    st.dataframe(manufacturers, use_container_width=True)
    if manufacturers:
        selected_code = st.selectbox("Manage Manufacturer", [item["manufacturer_code"] for item in manufacturers])
        selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)
        with st.form("update_manufacturer_onboarding"):
            col1, col2 = st.columns(2)
            updated_name = col1.text_input("Update Name", value=selected.get("manufacturer_name", ""))
            updated_email = col2.text_input("Update Owner Email", value=selected.get("owner_email", ""))
            updated_city = col1.text_input("Update City", value=selected.get("city", ""))
            updated_status = col2.text_input("Update Status", value=selected.get("status", "pending_approval"))
            updated_plan = st.text_input("Update Subscription Plan", value=selected.get("subscription_plan", "basic"))
            update_submit = st.form_submit_button("Save Manufacturer Changes")
        if update_submit:
            updated = manufacturer_onboarding_service.update_manufacturer(
                selected_code,
                {
                    "manufacturer_name": updated_name.strip(),
                    "owner_email": updated_email.strip(),
                    "city": updated_city.strip(),
                    "status": updated_status.strip(),
                    "subscription_plan": updated_plan.strip(),
                },
            )
            st.success(f"Manufacturer {updated['manufacturer_code']} updated.")
            st.rerun()

        col_a, col_b = st.columns(2)
        if col_a.button("Regenerate Onboarding Secret", use_container_width=True):
            refreshed = manufacturer_onboarding_service.regenerate_secret(selected_code)
            st.success("Onboarding secret regenerated.")
            st.code(refreshed["manufacturer_onboarding_steps"], language="text")
            st.rerun()
        if col_b.button("Delete Manufacturer Registry Entry", use_container_width=True):
            manufacturer_onboarding_service.delete_manufacturer(selected_code, remove_workspace=False)
            st.success(f"{selected_code} removed from registry.")
            st.rerun()

        st.markdown("### Shareable Manufacturer Onboarding Packet")
        st.code(selected.get("manufacturer_onboarding_steps", ""), language="text")
