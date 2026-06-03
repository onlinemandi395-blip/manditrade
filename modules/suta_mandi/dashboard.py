from __future__ import annotations

from typing import Any

import streamlit as st

from components.detail_drawer import render_catalog_detail_drawer
from components.data_grid import render_data_grid
from components.filter_bar import render_filter_bar
from components.kpi_cards import render_kpi_cards
from components.platform_shell import render_platform_shell
from components.product_card import render_product_card
from components.responsive_layout import render_section_intro
from utils.page_ui import render_empty_state
from utils.page_ui import render_metric_button_row


def is_suta_material(item: dict[str, Any]) -> bool:
    category = str(item.get("category") or "").strip().upper()
    name = str(item.get("name") or "").strip().lower()
    return category == "SUTA" or "suta" in name or "yarn" in name


def list_suta_materials(materials: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in materials if is_suta_material(item) and item.get("status") == "ACTIVE"]


def render_suta_mandi_dashboard(app_context: dict) -> None:
    user = app_context["current_user"]
    governance_service = app_context["governance_service"]
    procurement_service = app_context["procurement_transaction_service"]
    page_key = "suta_mandi"

    render_platform_shell(
        title="Suta Mandi",
        subtitle="Manufacturer-only suta purchasing market curated by admin and supplied through mahajans. This is a raw-material buying surface, not a finished-product market.",
        badges=["Manufacturer Only", "Admin Curated", "Mahajan Supplied"],
        role=user.role.replace("_", " ").title() if user else "Restricted",
        metrics=[("Suta Types", "Curated"), ("Flow", "Admin routed")],
        breadcrumbs=["Workspace", "Supply", "Suta Mandi"],
        primary_actions=["Request Suta"],
    )
    if not user or user.role not in {"manufacturer", "admin_as_manufacturer"}:
        st.info("Suta Mandi is available only in manufacturer workspace context.")
        return
    if not user.manufacturer_code:
        st.info("Manufacturer code is required to place a suta mandi request.")
        return

    all_materials = governance_service.list_raw_materials()
    suta_materials = list_suta_materials(all_materials)
    orders = procurement_service.list_supply_orders(manufacturer_code=user.manufacturer_code)
    suta_orders = [item for item in orders if is_suta_material(next((mat for mat in all_materials if mat.get("raw_material_id") == item.get("raw_material_id")), {}))]
    cart_service = app_context.get("cart_service")
    image_service = app_context.get("image_service")
    trust_badge_service = app_context.get("trust_badge_service")

    render_kpi_cards(
        [
            {"label": "Suta Types", "value": str(len(suta_materials)), "status": "SUCCESS"},
            {"label": "Open Requests", "value": str(len([item for item in suta_orders if item.get("status") not in {'CLOSED', 'CANCELLED', 'MANUFACTURER_RECEIVED'}])), "status": "PENDING"},
            {"label": "Awaiting Quote", "value": str(len([item for item in suta_orders if item.get("status") == 'SENT_TO_MAHAJAN'])), "status": "OPEN"},
            {"label": "Price Ready", "value": str(len([item for item in suta_orders if item.get("status") == 'ADMIN_PRICE_SET'])), "status": "WARNING"},
        ]
    )
    render_metric_button_row(
        page_key,
        [
            {"label": "Overview", "value": str(len(suta_materials)), "tab_name": "Overview"},
            {"label": "Catalog", "value": str(len(suta_materials)), "tab_name": "Catalog"},
            {"label": "Request", "value": str(len([item for item in suta_orders if item.get('status') == 'ADMIN_PRICE_SET'])), "tab_name": "Request Suta"},
            {"label": "Orders", "value": str(len(suta_orders)), "tab_name": "My Suta Orders"},
        ],
    )
    overview_tab, catalog_tab, request_tab, orders_tab = st.tabs(["Overview", "Catalog", "Request Suta", "My Suta Orders"])
    with overview_tab:
        render_section_intro(
            "Suta Supply Market",
            "Manufacturers can browse suta varieties here and raise admin-managed mandi requests. Mahajans supply the raw material, while admin controls routing and pricing.",
        )
        if suta_materials:
            render_data_grid(
                page_key="suta_overview",
                rows=suta_materials,
                search_fields=["raw_material_id", "name", "mahajan_id", "category"],
                status_field="status",
                price_field="supply_price",
                search_placeholder="Search suta by ID, name, or mahajan",
            )
        else:
            render_empty_state("No suta materials are listed yet.")
    with catalog_tab:
        if not suta_materials:
            render_empty_state("No suta raw materials are listed yet. Ask admin or mahajan to onboard suta supply in Raw Materials.")
        else:
            catalog_rows = [
                {
                    "raw_material_id": item.get("raw_material_id", ""),
                    "name": item.get("name", ""),
                    "category": item.get("category", ""),
                    "unit": item.get("unit", ""),
                    "available_qty": item.get("available_qty", 0),
                    "supply_price": item.get("supply_price", 0),
                    "mahajan_id": item.get("mahajan_id", ""),
                    "status": item.get("status", ""),
                }
                for item in suta_materials
            ]
            filtered_rows = render_filter_bar(page_key="suta_catalog", rows=catalog_rows, search_fields=["raw_material_id", "name", "mahajan_id"], status_field="status", price_field="supply_price", search_placeholder="Search suta by ID, name, or mahajan")
            preview_cards = filtered_rows[:4]
            if preview_cards:
                card_columns = st.columns(min(len(preview_cards), 4))
                for index, item in enumerate(preview_cards):
                    with card_columns[index % len(card_columns)]:
                        image = image_service.get_display_image(item, label=str(item.get("name", "Suta"))) if image_service else {"src": "", "alt": str(item.get("name", "Suta")), "status": "NONE"}
                        if render_product_card(
                            item=item,
                            variant="SUTA_MANDI",
                            image=image,
                            title=str(item.get("name", "Suta")),
                            subtitle=str(item.get("category", "SUTA")),
                            price_label="Supply",
                            price_value=str(item.get("supply_price", 0)),
                            availability_label=f"Qty {item.get('available_qty', 0)}",
                            visibility_label=str(item.get("status", "ACTIVE")),
                            action_label="Add To Request Cart",
                            action_key=f"suta_add_{item.get('raw_material_id', index)}",
                            badges=trust_badge_service.badges_for_raw_material(item) if trust_badge_service else [],
                            supporting_text=str(item.get("description", "") or "Admin-curated yarn sourcing supply."),
                        ):
                            cart_service.add_item(
                                "manufacturer",
                                user.manufacturer_code or "",
                                cart_type="SUTA_MANDI",
                                item_id=str(item.get("raw_material_id", "")),
                                qty=1,
                            )
                            st.success("Added to Suta Mandi request cart.")
                            st.rerun()
                selected_suta = preview_cards[0]
                selected_image = image_service.get_display_image(selected_suta, label=str(selected_suta.get("name", "Suta"))) if image_service else {"src": "", "alt": str(selected_suta.get("name", "Suta")), "status": "NONE"}
                render_catalog_detail_drawer(
                    title=str(selected_suta.get("name", "Suta")),
                    subtitle=str(selected_suta.get("category", "SUTA")),
                    image=selected_image,
                    price_label="Supply",
                    price_value=str(selected_suta.get("supply_price", 0)),
                    availability_label=f"Qty {selected_suta.get('available_qty', 0)}",
                    metadata={
                        "MOQ": "1 lot",
                        "Supplier": str(selected_suta.get("mahajan_id", "Admin routed")),
                        "Packaging": "Admin coordinated",
                    },
                    badges=trust_badge_service.badges_for_raw_material(selected_suta) if trust_badge_service else [],
                    description=str(selected_suta.get("description", "") or "Yarn/raw-material sourcing lane for manufacturers."),
                )
            render_data_grid(
                page_key="suta_catalog_grid",
                rows=filtered_rows,
                search_fields=["raw_material_id", "name", "mahajan_id"],
                status_field="status",
                price_field="supply_price",
                search_placeholder="Search suta by ID, name, or mahajan",
            )
    with request_tab:
        request_cart = cart_service.get_cart("manufacturer", user.manufacturer_code or "", "SUTA_MANDI") if cart_service else {"items": []}
        if not suta_materials:
            st.info("No suta material is ready for requests right now.")
        else:
            with st.form("create_suta_request"):
                raw_material_id = st.selectbox(
                    "Suta Type",
                    [item["raw_material_id"] for item in suta_materials],
                    format_func=lambda material_id: f"{material_id} | {next((item.get('name', 'Suta') for item in suta_materials if item['raw_material_id'] == material_id), 'Suta')}",
                )
                selected = next(item for item in suta_materials if item["raw_material_id"] == raw_material_id)
                qty = st.number_input("Required Qty", min_value=1.0, step=1.0, value=1.0)
                unit = st.text_input("Unit", value=str(selected.get("unit", "kg")))
                notes = st.text_area("Requirement Note", placeholder="Count, blend, color, twist, cone details, or packing instructions")
                submitted = st.form_submit_button("Create Suta Request")
            if submitted:
                if cart_service:
                    cart_service.add_item(
                        "manufacturer",
                        user.manufacturer_code or "",
                        cart_type="SUTA_MANDI",
                        item_id=raw_material_id,
                        qty=int(qty),
                        metadata={"notes": notes},
                    )
                    st.success("Suta item added to request cart.")
                    st.rerun()
            if request_cart.get("items"):
                st.dataframe(request_cart.get("items", []), use_container_width=True)
                if st.button("Checkout Suta Request Cart", use_container_width=True, key="suta_checkout"):
                    created = cart_service.checkout(
                        "manufacturer",
                        user.manufacturer_code or "",
                        cart_type="SUTA_MANDI",
                        checkout_context={"manufacturer_code": user.manufacturer_code or "", "requester_email": user.email},
                    )
                    st.success(f"Created {len(created)} admin-routed suta request(s).")
                    st.rerun()
    with orders_tab:
        render_section_intro("My Suta Orders", "Only your manufacturer suta orders appear here. Final supply still moves through admin-managed mandi flow.")
        if suta_orders:
            render_data_grid(
                page_key="suta_orders_grid",
                rows=suta_orders,
                search_fields=["supply_order_id", "raw_material_id", "manufacturer_code", "mahajan_id"],
                status_field="status",
                date_field="updated_at",
                search_placeholder="Search by order, material, or mahajan",
            )
        else:
            render_empty_state("No suta mandi orders found for this manufacturer yet.")
