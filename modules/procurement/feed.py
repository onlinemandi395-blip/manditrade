from __future__ import annotations

import streamlit as st

from services.json_service import JsonService


def render_procurement_feed(app_context: dict) -> None:
    st.subheader("Procurement Feed")
    current_user = app_context["current_user"]
    if not current_user or current_user.role != "manufacturer" or not current_user.manufacturer_code:
        st.info("Procurement feed is available to signed-in manufacturers.")
        return

    drive_service = app_context["drive_service"]
    procurement_transaction_service = app_context["procurement_transaction_service"]
    json_service = JsonService()

    own_paths = drive_service.get_manufacturer_paths(current_user.manufacturer_code)
    procurement_path = own_paths.shared_zone / "procurement.json"
    procurement = json_service.read_json(procurement_path, {"requests": []})
    open_requests = [request for request in procurement.get("requests", []) if request.get("status") == "OPEN"]

    st.dataframe(open_requests, use_container_width=True)
    if not open_requests:
        return

    selected_id = st.selectbox("Open Request", [request["request_id"] for request in open_requests])
    selected = next(request for request in open_requests if request["request_id"] == selected_id)
    unit_price = st.number_input("Unit Price", min_value=0.0, step=1.0)
    advance_amount = st.number_input("Advance Amount", min_value=0.0, step=100.0)
    if st.button("Accept Procurement Request", use_container_width=True):
        with st.status("Running procurement transaction...", expanded=True) as status:
            try:
                result = procurement_transaction_service.accept_procurement_request(
                    current_user=current_user,
                    request_id=selected["request_id"],
                    unit_price=unit_price,
                    advance_amount=advance_amount,
                )
                status.update(label=f"Transaction {result['transaction_id']} committed", state="complete")
                st.success(
                    f"Request {result['request_id']} accepted under transaction {result['transaction_id']}."
                )
            except Exception as exc:  # noqa: BLE001
                status.update(label="Transaction rolled back", state="error")
                st.error(str(exc))
