from __future__ import annotations

import streamlit as st

from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header


def render_inventory_summary_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    inventory_query_service = app_context["inventory_query_service"]
    manufacturers = governance_service.list_manufacturers()
    rows: list[dict] = []
    total_visible_items = 0
    total_low_items = 0

    for manufacturer in manufacturers:
        manufacturer_code = manufacturer.get("manufacturer_code", "")
        projection = inventory_query_service.list_inventory_snapshot(manufacturer_code)
        items = projection.get("items", [])
        visible_items = [item for item in items if (item.get("mandi_inventory", {}) or {}).get("visible_to_mandi", True)]
        low_items = [item for item in visible_items if int((item.get("mandi_inventory", {}) or {}).get("available_qty", 0)) <= 10]
        total_visible_items += len(visible_items)
        total_low_items += len(low_items)
        rows.append(
            {
                "manufacturer_code": manufacturer_code,
                "manufacturer_name": manufacturer.get("business_name", manufacturer.get("manufacturer_name", "")),
                "mandi_visible_stock_count": len(visible_items),
                "low_mandi_inventory_count": len(low_items),
                "category_summary": ", ".join(manufacturer.get("product_categories", []) or []),
            }
        )

    render_page_header("Inventory Summary", "Read-only SuperAdmin view of mandi-visible stock posture across manufacturers without exposing self inventory.", ["SuperAdmin", "Inventory Summary"])
    render_metric_grid(
        [
            render_metric_card("Manufacturers", str(len(rows)), "SUCCESS"),
            render_metric_card("Visible Mandi Items", str(total_visible_items), "OPEN"),
            render_metric_card("Low Mandi Items", str(total_low_items), "WARNING"),
        ]
    )
    render_section_intro("Mandi Projection Only", "This summary is built from shared mandi inventory projections and excludes all self inventory buckets.")
    st.dataframe(rows, use_container_width=True)
