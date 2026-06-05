from __future__ import annotations

import streamlit as st

from components.kpi_cards import render_kpi_cards
from components.responsive_layout import render_section_intro
from components.ui_shell import render_page_header
from utils.page_ui import render_empty_state

SOURCE_TYPES = ["MANUFACTURER", "MAHAJAN", "EXTERNAL"]
SOURCE_STATUSES = ["ACTIVE", "PENDING", "BLOCKED", "SUSPENDED", "ARCHIVED"]


def _option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _matches_search(row: dict[str, str], query: str) -> bool:
    query_key = query.strip().lower()
    if not query_key:
        return True
    haystack = " ".join(
        [
            str(row.get("source_id", "")),
            str(row.get("business_name", "")),
            str(row.get("contact_person", "")),
            str(row.get("email", "")),
            str(row.get("city", "")),
            str(row.get("state", "")),
            str(row.get("source_type", "")),
            str(row.get("legacy_entity_id", "")),
        ]
    ).lower()
    return query_key in haystack


def _render_source_directory(rows: list[dict[str, str]]) -> None:
    if not rows:
        render_empty_state("No procurement sources match the current filter.")
        return
    for row in rows:
        title = row.get("business_name", "") or row.get("source_id", "Source")
        subtitle_bits = [
            row.get("source_type", "EXTERNAL").title(),
            row.get("city", ""),
            row.get("state", ""),
        ]
        subtitle = " • ".join(bit for bit in subtitle_bits if bit)
        badges = [
            f"Status: {row.get('status', 'ACTIVE')}",
            f"Products: {len(row.get('products_supported', []) or [])}",
        ]
        if row.get("legacy_entity_type"):
            badges.append(f"Legacy: {row.get('legacy_entity_type')}")
        with st.container(border=True):
            st.markdown(f"#### {title}")
            if subtitle:
                st.caption(subtitle)
            st.write(" | ".join(badges))
            detail_cols = st.columns(3)
            detail_cols[0].write(f"Source ID: `{row.get('source_id', '')}`")
            detail_cols[1].write(f"Contact: {row.get('contact_person', '-') or '-'}")
            detail_cols[2].write(f"Mobile: {row.get('mobile', '-') or '-'}")
            st.write(f"Email: {row.get('email', '-') or '-'}")
            if row.get("products_supported"):
                st.write("Products Supported: " + ", ".join(row.get("products_supported", [])[:8]))
            if row.get("notes"):
                st.caption(row.get("notes", ""))


def render_procurement_sources_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    product_catalog_service = app_context["product_catalog_service"]

    direct_sources = governance_service.list_procurement_sources(include_legacy=False)
    all_sources = governance_service.list_procurement_sources(include_legacy=True)
    active_sources = [item for item in all_sources if item.get("status") == "ACTIVE"]
    legacy_sources = [item for item in all_sources if item.get("legacy_entity_type")]
    products = product_catalog_service.list_products(include_pending=True, viewer_role="platform_admin")
    source_lookup = {item.get("source_id", ""): item for item in all_sources if item.get("source_id")}

    render_page_header(
        "Procurement Sources",
        "Manage the businesses that can supply finished goods, raw materials, and special sourcing lanes without forcing every supplier into a platform-login workflow.",
        ["Admin Managed", "Source Directory", "Compatibility Safe"],
        role="Platform Admin",
        kicker="Source Abstraction",
        primary_actions=["Create Source", "Map Products"],
    )
    render_kpi_cards(
        [
            {"label": "Manual Sources", "value": str(len(direct_sources)), "status": "SUCCESS"},
            {"label": "Active Sources", "value": str(len(active_sources)), "status": "OPEN"},
            {"label": "Legacy Aliases", "value": str(len(legacy_sources)), "status": "PENDING"},
            {"label": "Products With Sources", "value": str(len([item for item in products if item.get("source_ids")])), "status": "INFO"},
        ]
    )

    overview_tab, create_tab, mapping_tab = st.tabs(["Overview", "Create / Manage", "Product Mapping"])

    with overview_tab:
        render_section_intro(
            "Source Directory",
            "This is the new admin-first sourcing layer. Legacy manufacturers and mahajans still appear as compatibility aliases until downstream flows are fully migrated.",
        )
        search_query = st.text_input("Search sources", placeholder="Business name, city, email, source ID")
        status_filter = st.selectbox("Status", ["ALL"] + SOURCE_STATUSES, index=0, key="procurement_source_status_filter")
        type_filter = st.selectbox("Source Type", ["ALL"] + SOURCE_TYPES, index=0, key="procurement_source_type_filter")
        filtered = [
            item
            for item in all_sources
            if _matches_search(item, search_query)
            and (status_filter == "ALL" or item.get("status") == status_filter)
            and (type_filter == "ALL" or item.get("source_type") == type_filter)
        ]
        _render_source_directory(filtered)

    with create_tab:
        render_section_intro(
            "Manual Source Management",
            "Create lean procurement-source records for businesses that should supply orders and inventory without needing a full platform login.",
        )
        default_source_id = governance_service.generate_next_procurement_source_id()
        with st.form("procurement_source_create_form"):
            id_col, type_col = st.columns(2)
            source_id = id_col.text_input("Source ID", value=default_source_id)
            source_type = type_col.selectbox("Source Type", SOURCE_TYPES, index=2)
            business_col, contact_col = st.columns(2)
            business_name = business_col.text_input("Business Name")
            contact_person = contact_col.text_input("Contact Person")
            email_col, mobile_col = st.columns(2)
            email = email_col.text_input("Email")
            mobile = mobile_col.text_input("Mobile")
            city_col, state_col = st.columns(2)
            city = city_col.text_input("City")
            state = state_col.text_input("State")
            products_supported = st.text_input("Products Supported", placeholder="Comma separated product IDs or categories")
            status = st.selectbox("Status", SOURCE_STATUSES, index=0)
            notes = st.text_area("Notes", height=100)
            submitted = st.form_submit_button("Save Procurement Source")
        if submitted:
            governance_service.upsert_procurement_source(
                {
                    "source_id": source_id,
                    "source_type": source_type,
                    "business_name": business_name,
                    "contact_person": contact_person,
                    "mobile": mobile,
                    "email": email,
                    "city": city,
                    "state": state,
                    "products_supported": products_supported,
                    "status": status,
                    "notes": notes,
                }
            )
            st.success(f"Procurement source {source_id.strip().upper()} saved.")
            st.rerun()

        editable_sources = [item for item in direct_sources if not item.get("legacy_entity_type")]
        if not editable_sources:
            st.info("No manual procurement sources exist yet. Create one above.")
        else:
            selected_source_id = st.selectbox(
                "Manage existing source",
                [item.get("source_id", "") for item in editable_sources],
                format_func=lambda source_id: f"{source_id} - {(source_lookup.get(source_id) or {}).get('business_name', source_id)}",
            )
            selected = dict(source_lookup.get(selected_source_id) or {})
            with st.form("procurement_source_manage_form"):
                manage_type = st.selectbox("Source Type", SOURCE_TYPES, index=_option_index(SOURCE_TYPES, selected.get("source_type", "EXTERNAL")))
                manage_status = st.selectbox("Status", SOURCE_STATUSES, index=_option_index(SOURCE_STATUSES, selected.get("status", "ACTIVE")))
                manage_business = st.text_input("Business Name", value=selected.get("business_name", ""))
                manage_contact = st.text_input("Contact Person", value=selected.get("contact_person", ""))
                manage_email = st.text_input("Email", value=selected.get("email", ""))
                manage_mobile = st.text_input("Mobile", value=selected.get("mobile", ""))
                manage_city = st.text_input("City", value=selected.get("city", ""))
                manage_state = st.text_input("State", value=selected.get("state", ""))
                manage_products_supported = st.text_input("Products Supported", value=", ".join(selected.get("products_supported", []) or []))
                manage_notes = st.text_area("Notes", value=selected.get("notes", ""), height=100)
                save_manage = st.form_submit_button("Update Source")
            if save_manage:
                governance_service.upsert_procurement_source(
                    {
                        "source_id": selected_source_id,
                        "source_type": manage_type,
                        "business_name": manage_business,
                        "contact_person": manage_contact,
                        "email": manage_email,
                        "mobile": manage_mobile,
                        "city": manage_city,
                        "state": manage_state,
                        "products_supported": manage_products_supported,
                        "status": manage_status,
                        "notes": manage_notes,
                    }
                )
                st.success(f"{selected_source_id} updated.")
                st.rerun()
            if st.button("Archive Selected Source", key="archive_procurement_source", use_container_width=True):
                governance_service.archive_procurement_source(selected_source_id)
                st.warning(f"{selected_source_id} archived.")
                st.rerun()

    with mapping_tab:
        render_section_intro(
            "Product -> Source Mapping",
            "Admin can now map products directly to procurement sources. Existing manufacturer-linked fields remain in place until downstream assignment flows are fully migrated.",
        )
        if not products:
            render_empty_state("No products are available for source mapping.")
        elif not active_sources:
            render_empty_state("No active procurement sources are available yet.")
        else:
            product_options = [item.get("product_id", "") for item in products if item.get("product_id")]
            selected_product_id = st.selectbox(
                "Select Product",
                product_options,
                format_func=lambda product_id: f"{product_id} - {next((item.get('name', product_id) for item in products if item.get('product_id') == product_id), product_id)}",
            )
            product = next((item for item in products if item.get("product_id") == selected_product_id), {})
            candidate_source_ids = [item.get("source_id", "") for item in active_sources if item.get("source_id")]
            current_source_ids = [item for item in product.get("source_ids", []) or [] if item in set(candidate_source_ids)]
            with st.form("product_source_mapping_form"):
                chosen_source_ids = st.multiselect(
                    "Available Procurement Sources",
                    candidate_source_ids,
                    default=current_source_ids,
                    format_func=lambda source_id: f"{source_id} - {(source_lookup.get(source_id) or {}).get('business_name', source_id)}",
                )
                mapping_notes = st.caption("These mappings are admin-managed and sit alongside legacy manufacturer/mahajan ownership fields for now.")
                _ = mapping_notes
                save_mapping = st.form_submit_button("Save Source Mapping")
            if save_mapping:
                product_catalog_service.update_product(
                    product_id=selected_product_id,
                    updates={"source_ids": chosen_source_ids},
                    updated_by="PLATFORM_ADMIN",
                )
                st.success(f"Mapped {len(chosen_source_ids)} source(s) to {selected_product_id}.")
                st.rerun()
            if current_source_ids:
                st.write("Current Sources:")
                for source_id in current_source_ids:
                    source = source_lookup.get(source_id) or {}
                    st.write(f"- `{source_id}` - {source.get('business_name', source_id)}")
