from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from services.commission_service import CommissionService


def render_admin_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    audit_service = app_context["audit_service"]
    subscription_plans = app_context["subscription_plans"]["plans"]

    st.subheader("Admin Governance Dashboard")
    st.caption("Pricing governance, manufacturer approvals, and platform visibility without private-zone access.")

    commission_service = CommissionService(app_context["system_config"]["governance"]["admin_profit_share_ratio"])
    sample = commission_service.calculate(mrp=145, mandi_price=120)
    manufacturers = governance_service.list_manufacturers()
    products = governance_service.list_products()
    pending_count = len([item for item in manufacturers if item.get("status") == "pending_approval"])

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Manufacturers", len(app_context["drive_service"].list_manufacturer_workspaces()))
    col2.metric("Default MRP Sample", f"Rs {sample['mrp']}")
    col3.metric("Admin Share Sample", f"Rs {sample['admin_share']}")
    col4.metric("Pending Approvals", pending_count)

    st.markdown("### Governance Scope")
    st.table(
        [
            {"Control": "Product registry", "Access": "Allowed"},
            {"Control": "Mandi pricing", "Access": "Allowed"},
            {"Control": "Feature flags", "Access": "Allowed"},
            {"Control": "Private clients.json", "Access": "Denied"},
            {"Control": "Invoices and API keys", "Access": "Denied"},
        ]
    )

    st.markdown("### Product Registry")
    with st.form("product_registry_form"):
        product_code = st.text_input("Product Code", placeholder="WHEAT-001")
        product_name = st.text_input("Product Name", placeholder="Premium Wheat")
        category = st.text_input("Category", placeholder="Grains")
        mandi_price = st.number_input("Mandi Price", min_value=0.0, step=1.0)
        mrp = st.number_input("MRP", min_value=0.0, step=1.0)
        save_product = st.form_submit_button("Save Product")

    if save_product and product_code and product_name:
        governance_service.upsert_product(
            {
                "product_code": product_code.strip().upper(),
                "product_name": product_name.strip(),
                "category": category.strip(),
                "mandi_price": mandi_price,
                "mrp": mrp,
                "updated_at": datetime.now(UTC).isoformat(),
            }
        )
        audit_service.log_event(
            "product_registry_updated",
            actor=user.email,
            details={"product_code": product_code.strip().upper(), "product_name": product_name.strip()},
        )
        st.success("Product registry updated.")

    st.dataframe(products, use_container_width=True)

    st.markdown("### Manufacturer Approval Workflow")
    if manufacturers:
        manufacturer_options = {
            f"{item['manufacturer_code']} - {item['manufacturer_name']} ({item.get('status', 'unknown')})": item["manufacturer_code"]
            for item in manufacturers
        }
        selected_label = st.selectbox("Select Manufacturer", list(manufacturer_options.keys()))
        selected_code = manufacturer_options[selected_label]
        selected_record = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)
        selected_plan = st.selectbox("Subscription Plan", [plan["code"] for plan in subscription_plans], index=0)

        col_a, col_b = st.columns(2)
        if col_a.button("Approve Manufacturer", use_container_width=True):
            governance_service.update_manufacturer_status(selected_code, "approved", selected_plan)
            audit_service.log_event(
                "manufacturer_approved",
                actor=user.email,
                details={"manufacturer_code": selected_code, "subscription_plan": selected_plan},
            )
            st.success(f"{selected_code} approved.")
            st.rerun()
        if col_b.button("Activate Subscription", use_container_width=True):
            governance_service.update_manufacturer_status(selected_code, selected_record.get("status", "approved"), selected_plan)
            audit_service.log_event(
                "subscription_activated",
                actor=user.email,
                details={"manufacturer_code": selected_code, "subscription_plan": selected_plan},
            )
            st.success(f"Subscription updated for {selected_code}.")
            st.rerun()

        st.dataframe(manufacturers, use_container_width=True)
    else:
        st.info("No manufacturers registered yet.")

    st.markdown("### Recent Audit Log")
    st.dataframe(audit_service.read_recent(limit=10), use_container_width=True)
