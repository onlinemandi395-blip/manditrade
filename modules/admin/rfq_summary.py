from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_rfq_summary_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    procurement_service = app_context["procurement_transaction_service"]
    manufacturers = governance_service.list_manufacturers()
    rows: list[dict] = []
    total_trade_value = 0.0
    open_count = 0
    responded_count = 0
    completed_count = 0
    total_rfqs = 0

    for manufacturer in manufacturers:
        manufacturer_code = manufacturer.get("manufacturer_code", "")
        rfqs = procurement_service.list_requests(manufacturer_code)
        responses = procurement_service.list_responses(manufacturer_code)
        response_map: dict[str, set[str]] = {}
        manufacturer_trade_value = 0.0
        for response in responses:
            response_map.setdefault(response.get("rfq_id", ""), set()).add(response.get("supplier_manufacturer_id", ""))
            manufacturer_trade_value += sum(float(item.get("total_price", 0) or 0) for item in response.get("available_items", []))
        for rfq in rfqs:
            total_rfqs += 1
            status = str(rfq.get("status") or "").upper()
            if status == "OPEN":
                open_count += 1
            if status == "RESPONDED":
                responded_count += 1
            if status == "BUYER_CONFIRMED":
                completed_count += 1
            rows.append(
                {
                    "buyer_manufacturer": manufacturer_code,
                    "rfq_id": rfq.get("rfq_id", ""),
                    "status": status,
                    "response_count": len([item for item in responses if item.get("rfq_id") == rfq.get("rfq_id")]),
                    "supplier_manufacturers": ", ".join(sorted(response_map.get(rfq.get("rfq_id", ""), set()))),
                    "mandi_trade_value": round(
                        sum(
                            float(item.get("total_price", 0) or 0)
                            for response in responses
                            if response.get("rfq_id") == rfq.get("rfq_id")
                            for item in response.get("available_items", [])
                        ),
                        2,
                    ),
                }
            )
        total_trade_value += manufacturer_trade_value

    render_page_header("Mandi Orders Summary", "Read-only SuperAdmin view of mandi sourcing activity with aggregate trade values and no private negotiation detail.", ["SuperAdmin", "Mandi Orders Summary"])
    render_metric_grid(
        [
            render_metric_card("Total Requests", str(total_rfqs), "OPEN"),
            render_metric_card("Open Requests", str(open_count), "PENDING"),
            render_metric_card("Responded Requests", str(responded_count), "WARNING"),
            render_metric_card("Completed Requests", str(completed_count), "SUCCESS"),
        ]
    )
    render_section_intro("Aggregate Mandi Activity", f"Total mandi trade value tracked through sourcing responses: INR {round(total_trade_value, 2)}.")
    st.dataframe(rows, use_container_width=True)
