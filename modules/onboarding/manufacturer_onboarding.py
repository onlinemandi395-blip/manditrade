from __future__ import annotations

import streamlit as st


def render_manufacturer_onboarding(app_context: dict) -> None:
    current_user = app_context["current_user"]
    if not current_user or current_user.role not in {"admin", "platform_admin"}:
        st.subheader("Manufacturer Onboarding")
        st.info("Only platform admin can access manufacturer onboarding.")
        return

    onboarding_service = app_context["manufacturer_onboarding_service"]
    governance_service = app_context["governance_service"]

    st.subheader("Manufacturer Onboarding")
    st.caption("Create, update, and share first-time onboarding packets for manufacturers.")

    with st.form("manufacturer_onboarding_create"):
        col1, col2 = st.columns(2)
        manufacturer_code = col1.text_input("Manufacturer Code", placeholder="MANU101")
        manufacturer_name = col2.text_input("Manufacturer Name", placeholder="Shree Agro Traders")
        owner_email = col1.text_input("Owner Email", placeholder="owner@example.com")
        city = col2.text_input("City", placeholder="Jaipur")
        subscription_plan = st.text_input("Subscription Plan", value="basic")
        submit = st.form_submit_button("Create Manufacturer Onboarding")

    if submit and manufacturer_code and manufacturer_name:
        created = onboarding_service.create_manufacturer(
            manufacturer_code=manufacturer_code,
            manufacturer_name=manufacturer_name,
            owner_email=owner_email,
            city=city,
            created_by=current_user.email,
            subscription_plan=subscription_plan,
        )
        st.success(f"Manufacturer {created['manufacturer_code']} created.")
        st.code(created["manufacturer_onboarding_steps"], language="text")
        st.rerun()

    manufacturers = governance_service.list_manufacturers()
    st.markdown("### Registered Manufacturers")
    st.dataframe(manufacturers, use_container_width=True)

    if not manufacturers:
        return

    selected_code = st.selectbox("Manage Manufacturer", [item["manufacturer_code"] for item in manufacturers])
    selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)

    with st.form("manufacturer_onboarding_update"):
        col1, col2 = st.columns(2)
        updated_name = col1.text_input("Update Name", value=selected.get("manufacturer_name", ""))
        updated_email = col2.text_input("Update Owner Email", value=selected.get("owner_email", ""))
        updated_city = col1.text_input("Update City", value=selected.get("city", ""))
        updated_status = col2.text_input("Update Status", value=selected.get("status", "pending_approval"))
        updated_plan = st.text_input("Update Subscription Plan", value=selected.get("subscription_plan", "basic"))
        save_submit = st.form_submit_button("Save Changes")

    if save_submit:
        onboarding_service.update_manufacturer(
            selected_code,
            {
                "manufacturer_name": updated_name.strip(),
                "owner_email": updated_email.strip(),
                "city": updated_city.strip(),
                "status": updated_status.strip(),
                "subscription_plan": updated_plan.strip(),
            },
        )
        st.success(f"{selected_code} updated.")
        st.rerun()

    col_a, col_b = st.columns(2)
    if col_a.button("Regenerate Onboarding Secret", use_container_width=True):
        refreshed = onboarding_service.regenerate_secret(selected_code)
        st.success("Onboarding secret regenerated.")
        st.code(refreshed["manufacturer_onboarding_steps"], language="text")
        st.rerun()
    if col_b.button("Delete Manufacturer Registry Entry", use_container_width=True):
        onboarding_service.delete_manufacturer(selected_code, remove_workspace=False)
        st.success(f"{selected_code} removed from registry.")
        st.rerun()

    st.markdown("### Shareable Onboarding Packet")
    st.code(selected.get("manufacturer_onboarding_steps", ""), language="text")
