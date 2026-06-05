from __future__ import annotations

import streamlit as st

from components.actor_card import render_actor_card
from components.filter_bar import render_filter_bar
from components.responsive_layout import render_section_intro
from components.three_d_cards import render_metric_grid
from components.ui_shell import render_metric_card, render_page_header
from services.master_data_service import MasterDataService
from utils.export_utils import export_rows_to_csv_bytes, export_rows_to_json_bytes
from utils.page_ui import render_empty_state

BUSINESS_TYPES = [
    "Manufacturer",
    "Trader",
    "Wholesaler",
    "Processor",
    "Distributor",
    "Other",
]
SUBSCRIPTION_PLANS = ["Basic", "Premium", "Premium+"]
MANUFACTURER_STATUSES = ["PENDING", "ACTIVE", "BLOCKED", "SUSPENDED", "ARCHIVED"]
MASTER_DATA = MasterDataService()


def _address_of(manufacturer: dict) -> dict:
    address = manufacturer.get("address", {}) or {}
    return {
        "line1": address.get("line1", ""),
        "line2": address.get("line2", ""),
        "city": address.get("city", manufacturer.get("city", "")),
        "state": address.get("state", ""),
        "pin_code": address.get("pin_code", ""),
    }


def _legal_of(manufacturer: dict) -> dict:
    return manufacturer.get("legal", {}) or {}


def _banking_of(manufacturer: dict) -> dict:
    return manufacturer.get("banking", {}) or {}


def _option_index(options: list[str], value: str) -> int:
    return options.index(value) if value in options else 0


def _safe_multiselect_defaults(options: list[str], values: list[str]) -> list[str]:
    allowed = set(options)
    return [item for item in values if item in allowed]


def _subscription_plan_index(value: str) -> int:
    normalized = (value or "").strip().lower()
    mapping = {"basic": "Basic", "premium": "Premium", "premium+": "Premium+"}
    return _option_index(SUBSCRIPTION_PLANS, mapping.get(normalized, value))


def _render_manufacturer_details_form(*, prefix: str, defaults: dict, include_status: bool, submit_label: str) -> tuple[bool, dict]:
    address = _address_of(defaults)
    legal = _legal_of(defaults)
    banking = _banking_of(defaults)
    states = MASTER_DATA.get_indian_states_and_union_territories()
    categories = MASTER_DATA.get_product_categories()

    with st.form(f"{prefix}_manufacturer_admin_form"):
        code_col, plan_col = st.columns(2)
        manufacturer_code = code_col.text_input("Manufacturer Code", value=defaults.get("manufacturer_code", ""), disabled=True)
        selected_plan = plan_col.selectbox("Subscription Plan", SUBSCRIPTION_PLANS, index=_subscription_plan_index(defaults.get("subscription_plan", "basic")))

        col1, col2 = st.columns(2)
        business_name = col1.text_input("Business Name", value=defaults.get("business_name", defaults.get("manufacturer_name", "")))
        brand_name = col2.text_input("Brand Name", value=defaults.get("brand_name", ""))
        owner_name = col1.text_input("Owner Name", value=defaults.get("owner_name", ""))
        contact_person = col2.text_input("Contact Person", value=defaults.get("contact_person", defaults.get("owner_name", "")))
        owner_email = col1.text_input("Email", value=defaults.get("owner_email", ""))
        mobile = col2.text_input("Phone", value=defaults.get("mobile", ""))
        alternate_mobile = col1.text_input("Alternate Phone", value=defaults.get("alternate_mobile", ""))
        business_type = col2.selectbox("Business Type", BUSINESS_TYPES, index=_option_index(BUSINESS_TYPES, defaults.get("business_type", BUSINESS_TYPES[0])))

        st.markdown("#### Registered Address")
        line1 = st.text_input("Address Line 1", value=address.get("line1", ""))
        line2 = st.text_input("Address Line 2", value=address.get("line2", ""))
        city_col, state_col, pin_col = st.columns(3)
        city = city_col.text_input("City", value=address.get("city", ""))
        state = state_col.selectbox("State", states, index=_option_index(states, address.get("state", "")))
        pin_code = pin_col.text_input("Pincode", value=address.get("pin_code", ""))

        product_categories = st.multiselect(
            "Product Categories",
            categories,
            default=_safe_multiselect_defaults(categories, defaults.get("product_categories", []) or []),
        )

        st.markdown("#### Compliance")
        legal_col1, legal_col2 = st.columns(2)
        gstin = legal_col1.text_input("GST", value=legal.get("gstin", ""))
        pan = legal_col2.text_input("PAN", value=legal.get("pan", ""))
        udyam_id = legal_col1.text_input("Udyam", value=legal.get("udyam_id", ""))
        aadhaar = legal_col2.text_input("Aadhaar", value=legal.get("aadhaar", ""))

        st.markdown("#### Banking")
        bank_col1, bank_col2 = st.columns(2)
        account_holder_name = bank_col1.text_input("Account Holder", value=banking.get("account_holder_name", ""))
        account_number = bank_col2.text_input("Account Number", value=banking.get("account_number", ""))
        ifsc = bank_col1.text_input("IFSC", value=banking.get("ifsc", ""))
        upi_id = bank_col2.text_input("UPI", value=banking.get("upi_id", ""))

        status = defaults.get("status", "PENDING")
        selected_status = "PENDING"
        if include_status:
            selected_status = st.selectbox("Lifecycle Status", MANUFACTURER_STATUSES, index=_option_index(MANUFACTURER_STATUSES, status))

        business_description = st.text_area("Business Description", value=defaults.get("business_description", ""), height=120)
        submitted = st.form_submit_button(submit_label)

    payload = {
        "manufacturer_code": manufacturer_code.strip().upper(),
        "manufacturer_name": business_name.strip(),
        "business_name": business_name.strip(),
        "brand_name": brand_name.strip(),
        "owner_name": owner_name.strip(),
        "contact_person": contact_person.strip(),
        "owner_email": owner_email.strip(),
        "mobile": mobile.strip(),
        "alternate_mobile": alternate_mobile.strip(),
        "address": {
            "line1": line1.strip(),
            "line2": line2.strip(),
            "city": city.strip(),
            "state": state.strip(),
            "pin_code": pin_code.strip(),
        },
        "city": city.strip(),
        "state": state.strip(),
        "pin_code": pin_code.strip(),
        "business_type": business_type.strip(),
        "product_categories": product_categories,
        "legal": {
            "gstin": gstin.strip(),
            "pan": pan.strip(),
            "udyam_id": udyam_id.strip(),
            "aadhaar": aadhaar.strip(),
        },
        "banking": {
            "account_holder_name": account_holder_name.strip(),
            "account_number": account_number.strip(),
            "ifsc": ifsc.strip(),
            "upi_id": upi_id.strip(),
        },
        "business_description": business_description.strip(),
        "subscription_plan": selected_plan.strip(),
        "status": selected_status.strip(),
    }
    return submitted, payload


def _render_directory_cards(rows: list[dict], *, section_key: str) -> None:
    if not rows:
        render_empty_state("No manufacturer directory records available.")
        return
    for index in range(0, len(rows), 3):
        columns = st.columns(3)
        for column, row in zip(columns, rows[index:index + 3]):
            with column:
                selected = render_actor_card(
                    actor_id=row.get("manufacturer_code", ""),
                    title=row.get("business_name", ""),
                    subtitle=row.get("brand_name", "") or row.get("contact_person", "") or row.get("owner_name", ""),
                    status=row.get("status", "PENDING"),
                    completion_score=row.get("completion_score", 0),
                    trust_tier=row.get("trust_tier", "Bronze"),
                    location=row.get("location", ""),
                    supporting_text=", ".join(row.get("verification_badges", [])[:2]),
                    badges=(row.get("trust_badges", []) + row.get("verification_badges", []))[:4],
                    action_label="Select",
                    action_key=f"{section_key}_{row.get('manufacturer_code', '')}",
                )
                if selected:
                    st.session_state["manage_manufacturer_record"] = row.get("manufacturer_code", "")


def _render_status_bucket(title: str, rows: list[dict], *, page_key: str) -> None:
    st.markdown(f"### {title}")
    filtered = render_filter_bar(
        page_key=page_key,
        rows=rows,
        search_fields=["manufacturer_code", "business_name", "brand_name", "owner_name", "owner_email", "city"],
        status_field="status",
        date_field="updated_at",
        search_placeholder="Search manufacturer, brand, contact, email, or city",
    )
    if filtered:
        _render_directory_cards(filtered, section_key=page_key)
        st.dataframe(filtered, use_container_width=True)
    else:
        render_empty_state(f"No {title.lower()} manufacturers right now.")


def render_manufacturers_dashboard(app_context: dict) -> None:
    governance_service = app_context["governance_service"]
    onboarding_service = app_context["manufacturer_onboarding_service"]
    access_portal_service = app_context["access_portal_service"]
    identity_service = app_context["identity_governance_service"]
    current_user = app_context["current_user"]

    manufacturers = governance_service.list_manufacturers()
    summaries = [identity_service.summarize_manufacturer(item) for item in manufacturers]
    counts = identity_service.readiness_counts("manufacturer", manufacturers)

    render_page_header(
        "Manufacturers",
        "Admin controls manufacturer invitations, profile completeness, trust readiness, and role activation from one governance workspace.",
        ["Platform Admin", "Identity Governance"],
    )
    render_metric_grid(
        [
            render_metric_card("Pending Approvals", str(counts["pending"]), "PENDING"),
            render_metric_card("Active", str(counts["active"]), "SUCCESS"),
            render_metric_card("Blocked / Suspended", str(counts["blocked"]), "WARNING"),
            render_metric_card("Trusted", str(counts["trusted"]), "OPEN"),
        ]
    )

    tabs = st.tabs(["Overview", "Directory", "Pending Approvals", "Active", "Blocked", "Archived", "Analytics", "Create", "Manage"])
    overview_tab, directory_tab, pending_tab, active_tab, blocked_tab, archived_tab, analytics_tab, create_tab, manage_tab = tabs

    with overview_tab:
        render_section_intro("Network Governance", "Manufacturers should move through invite -> login -> profile completion -> admin approval -> ACTIVE access.")
        if summaries:
            st.dataframe(summaries, use_container_width=True)
        else:
            render_empty_state("No manufacturers registered yet.")

    with directory_tab:
        _render_status_bucket("Manufacturer Directory", summaries, page_key="manufacturer_directory")

    with pending_tab:
        pending_rows = [row for row in summaries if row.get("status") == "PENDING"]
        _render_status_bucket("Pending Manufacturers", pending_rows, page_key="manufacturer_pending")

    with active_tab:
        active_rows = [row for row in summaries if row.get("status") == "ACTIVE"]
        _render_status_bucket("Active Manufacturers", active_rows, page_key="manufacturer_active")

    with blocked_tab:
        blocked_rows = [row for row in summaries if row.get("status") in {"BLOCKED", "SUSPENDED"}]
        _render_status_bucket("Blocked Manufacturers", blocked_rows, page_key="manufacturer_blocked")

    with archived_tab:
        archived_rows = [row for row in summaries if row.get("status") == "ARCHIVED"]
        _render_status_bucket("Archived Manufacturers", archived_rows, page_key="manufacturer_archived")

    with analytics_tab:
        render_section_intro("Completion Analytics", "Profile quality and verification readiness directly influence trust surfaces used later in commerce flows.")
        if summaries:
            st.bar_chart(
                {
                    "Pending": counts["pending"],
                    "Active": counts["active"],
                    "Blocked": counts["blocked"],
                    "Trusted": counts["trusted"],
                }
            )
            st.dataframe(
                [
                    {
                        "manufacturer_code": row.get("manufacturer_code", ""),
                        "business_name": row.get("business_name", ""),
                        "completion_score": row.get("completion_score", 0),
                        "trust_tier": row.get("trust_tier", "Bronze"),
                        "status": row.get("status", "PENDING"),
                    }
                    for row in summaries
                ],
                use_container_width=True,
            )
        else:
            render_empty_state("No manufacturer analytics available yet.")

    with create_tab:
        render_section_intro("Invite Manufacturer", "Create a manufacturer profile first, then let the invited email complete sign-in and profile details before approval.")
        generated_code = onboarding_service.generate_next_manufacturer_code()
        submitted, payload = _render_manufacturer_details_form(
            prefix="manufacturer_create",
            defaults={"manufacturer_code": generated_code, "status": "PENDING"},
            include_status=True,
            submit_label="Create Manufacturer Invitation",
        )
        if submitted:
            try:
                created = onboarding_service.create_manufacturer(
                    manufacturer_code=payload["manufacturer_code"],
                    manufacturer_name=payload["business_name"],
                    business_name=payload["business_name"],
                    brand_name=payload["brand_name"],
                    owner_name=payload["owner_name"],
                    contact_person=payload["contact_person"],
                    owner_email=payload["owner_email"],
                    mobile=payload["mobile"],
                    alternate_mobile=payload["alternate_mobile"],
                    address_line1=payload["address"]["line1"],
                    address_line2=payload["address"]["line2"],
                    city=payload["address"]["city"],
                    state=payload["address"]["state"],
                    pin_code=payload["address"]["pin_code"],
                    business_type=payload["business_type"],
                    product_categories=payload["product_categories"],
                    udyam_id=payload["legal"]["udyam_id"],
                    gstin=payload["legal"]["gstin"],
                    pan=payload["legal"]["pan"],
                    aadhaar=payload["legal"]["aadhaar"],
                    bank_account_holder_name=payload["banking"]["account_holder_name"],
                    bank_account_number=payload["banking"]["account_number"],
                    ifsc_code=payload["banking"]["ifsc"],
                    upi_id=payload["banking"]["upi_id"],
                    business_description=payload["business_description"],
                    created_by=current_user.email if current_user else "system",
                    subscription_plan=payload["subscription_plan"],
                    status=payload["status"],
                )
                access_portal_service.submit_signup_request(
                    requested_role="manufacturer",
                    email=created["owner_email"],
                    full_name=created.get("contact_person") or created.get("owner_name") or created.get("business_name", ""),
                    manufacturer_code=created["manufacturer_code"],
                    manufacturer_name=created.get("business_name", ""),
                    city=(created.get("address") or {}).get("city", ""),
                    mobile=created.get("mobile", ""),
                    onboarding_secret=created.get("manufacturer_onboarding_secret", ""),
                    business_name=created.get("business_name", ""),
                    note="Admin-created manufacturer invitation",
                )
            except ValueError as exc:
                st.error(str(exc))
            else:
                st.success(f"Manufacturer {created['manufacturer_code']} invited.")
                st.code(created.get("manufacturer_onboarding_steps", ""), language="text")
                st.rerun()

    with manage_tab:
        if not manufacturers:
            st.info("No manufacturers available to manage yet.")
        else:
            selected_code = st.selectbox("Manage Manufacturer", [item["manufacturer_code"] for item in manufacturers], key="manage_manufacturer_record")
            selected = next(item for item in manufacturers if item["manufacturer_code"] == selected_code)
            selected_summary = identity_service.summarize_manufacturer(selected)
            st.json(selected_summary, expanded=False)
            submitted, payload = _render_manufacturer_details_form(
                prefix=f"manufacturer_manage_{selected_code}",
                defaults=selected,
                include_status=True,
                submit_label="Save Manufacturer",
            )
            if submitted:
                try:
                    onboarding_service.update_manufacturer(selected_code, payload)
                except ValueError as exc:
                    st.error(str(exc))
                else:
                    st.success(f"{selected_code} updated.")
                    st.rerun()

            action_col1, action_col2, action_col3, action_col4 = st.columns(4)
            if action_col1.button("Approve", key=f"approve_{selected_code}", use_container_width=True):
                onboarding_service.update_manufacturer(selected_code, {"status": "ACTIVE"})
                st.success(f"{selected_code} approved.")
                st.rerun()
            if action_col2.button("Block", key=f"block_{selected_code}", use_container_width=True):
                onboarding_service.update_manufacturer(selected_code, {"status": "BLOCKED"})
                st.warning(f"{selected_code} blocked.")
                st.rerun()
            if action_col3.button("Suspend", key=f"suspend_{selected_code}", use_container_width=True):
                onboarding_service.update_manufacturer(selected_code, {"status": "SUSPENDED"})
                st.warning(f"{selected_code} suspended.")
                st.rerun()
            if action_col4.button("Archive", key=f"archive_{selected_code}", use_container_width=True):
                onboarding_service.update_manufacturer(selected_code, {"status": "ARCHIVED"})
                st.warning(f"{selected_code} archived.")
                st.rerun()

            st.markdown("### Onboarding Packet")
            st.code(selected.get("manufacturer_onboarding_steps", ""), language="text")

    if summaries:
        st.download_button(
            "Export Manufacturer Directory JSON",
            export_rows_to_json_bytes(summaries),
            file_name="manufacturer_directory.json",
            mime="application/json",
            use_container_width=True,
        )
        st.download_button(
            "Export Manufacturer Directory CSV",
            export_rows_to_csv_bytes(summaries),
            file_name="manufacturer_directory.csv",
            mime="text/csv",
            use_container_width=True,
        )
