from __future__ import annotations

from components.table_renderer import render_table


def render_completed_deliveries_page(data_service, session_service) -> None:
    user = session_service.get_user()
    email = str(user.get("email", "")).strip().lower()
    shipments = data_service.get_collection_ref("shipments")
    completed_rows = [
        row for row in shipments
        if str(row.get("delivery_partner_email", "")).strip().lower() == email
        and str(row.get("status", "")).upper() == "DELIVERED"
    ]
    render_table(completed_rows, caption="Completed Deliveries")
