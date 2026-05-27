from __future__ import annotations

import streamlit as st


def render_admin_dashboard(app_context: dict) -> None:
    st.subheader("Platform Admin Dashboard")
    governance_service = app_context["governance_service"]
    products = governance_service.list_products()
    manufacturers = governance_service.list_manufacturers()
    actions = app_context["action_center_service"].get_actions(type("User", (), {"role": "platform_admin"})())

    col1, col2, col3 = st.columns(3)
    col1.metric("Manufacturers", len(manufacturers))
    col2.metric("Products", len(products))
    col3.metric("Pending Actions", sum(int(item.get("count", 0)) for item in actions))

    st.markdown("### Pending Product Approval")
    pending = [item for item in products if item.get("status") == "PENDING_APPROVAL"]
    st.dataframe(pending, use_container_width=True)
    if pending:
        selected = st.selectbox("Approve Product", [item["product_id"] for item in pending])
        mandi_price = st.number_input("Mandi Price", min_value=0.0, step=1.0)
        mrp = st.number_input("MRP", min_value=0.0, step=1.0)
        if st.button("Approve Selected Product", use_container_width=True):
            app_context["product_catalog_service"].approve_product(product_id=selected, approved_by="PLATFORM_ADMIN", mandi_price=mandi_price, mrp=mrp)
            st.success("Product approved.")
            st.rerun()

    st.markdown("### Manufacturer Registry")
    st.dataframe(manufacturers, use_container_width=True)
