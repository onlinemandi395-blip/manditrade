from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from services.admin_drive_service import AdminDriveService


def render_admin_configuration(auth_service, data_service, notification_service, session_service) -> None:
    users = data_service.get_collection_ref("users")
    primary_admin = auth_service.get_primary_admin()
    admin_drive_service = AdminDriveService()
    admin_rows = []
    if primary_admin.get("email"):
        admin_rows.append(
            {
                "email": primary_admin["email"],
                "role": "platform_admin",
                "status": "ACTIVE",
                "display_name": primary_admin.get("display_name", "Primary Admin"),
                "admin_type": "super",
                "source": "toml_primary_admin",
            }
        )
    admin_rows.extend(
        [
            user
            for user in users
            if str(user.get("role", "")).strip().lower() == "platform_admin"
            and str(user.get("email", "")).strip().lower() != primary_admin.get("email", "")
        ]
    )

    tabs = st.tabs(["Admin Users", "Required Files", "Integrations"])

    with tabs[0]:
        st.subheader("Admin Users")
        st.dataframe(admin_rows, use_container_width=True)
        editable_admins = [row for row in admin_rows if row.get("source") != "toml_primary_admin"]
        if editable_admins:
            selected_admin_email = st.selectbox("Select Admin", options=[row["email"] for row in editable_admins])
            selected_admin = next((row for row in users if str(row.get("email", "")).strip().lower() == selected_admin_email), None)
            action_cols = st.columns(2)
            if action_cols[0].button("Activate Admin", use_container_width=True):
                if selected_admin:
                    selected_admin["status"] = "ACTIVE"
                    try:
                        data_service.persist_collection("users")
                        st.success("Admin activated.")
                    except Exception as exc:
                        st.error(f"Drive write failed: {exc}")
            if action_cols[1].button("Deactivate Admin", use_container_width=True):
                if selected_admin:
                    selected_admin["status"] = "INACTIVE"
                    try:
                        data_service.persist_collection("users")
                        st.success("Admin deactivated.")
                    except Exception as exc:
                        st.error(f"Drive write failed: {exc}")
        with st.form("add_admin_form"):
            email = st.text_input("Admin Email")
            display_name = st.text_input("Display Name")
            admin_type = st.selectbox("Admin Type", ["operations", "catalog", "finance", "support", "logistics"])
            submitted = st.form_submit_button("Add Admin", use_container_width=True)
        if submitted:
            normalized_email = email.strip().lower()
            existing = {str(row.get("email", "")).strip().lower() for row in admin_rows}
            if not normalized_email:
                st.error("Admin email is required.")
            elif normalized_email in existing:
                st.error("Duplicate admin email is not allowed.")
            else:
                record = {
                    "user_id": f"USR_{len(users) + 1:04d}",
                    "email": normalized_email,
                    "role": "platform_admin",
                    "status": "ACTIVE",
                    "display_name": display_name.strip() or normalized_email.split("@")[0],
                    "admin_type": admin_type,
                    "created_at": datetime.now(UTC).isoformat(),
                    "created_by": session_service.get_user().get("email", ""),
                }
                users.append(record)
                try:
                    data_service.persist_collection("users")
                    notification_service.create_notification(
                        notification_type="ADMIN_ADDED",
                        title="New admin added",
                        message=f"{record['display_name']} was added as admin.",
                        metadata={"to_email": normalized_email},
                    )
                    if primary_admin.get("email"):
                        notification_service.create_notification(
                            notification_type="ADMIN_ADDED",
                            title="Admin registry updated",
                            message=f"{record['display_name']} was added as admin.",
                            metadata={"to_email": primary_admin["email"]},
                        )
                    st.success("Admin added.")
                except Exception as exc:
                    users.pop()
                    st.error(f"Drive write failed: {exc}")

    with tabs[1]:
        manifest = admin_drive_service.get_runtime_manifest()
        st.dataframe(manifest.get("required_files", []), use_container_width=True)
        if manifest.get("missing_files"):
            st.error("Required Drive files are missing.")
            if st.button("Create Missing Drive Files", use_container_width=True):
                try:
                    result = admin_drive_service.create_missing_required_files()
                    st.success(f"Created {len(result.get('created', []))} files/folders.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"Create Missing Files failed: {exc}")
        else:
            st.success("All required Drive files are present.")
    with tabs[2]:
        st.info("Integrations remain status-driven for now.")
