from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from services.admin_drive_service import AdminDriveService
from services.cache_service import CacheService
from services.config_loader_service import ConfigLoaderService
from services.theme_service import ThemeService


def render_admin_configuration(auth_service, data_service, notification_service, session_service, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
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

    tabs = st.tabs([t("ui.admin_users"), t("ui.required_files"), t("ui.integrations")])

    with tabs[0]:
        st.subheader(t("ui.admin_users"))
        render_table(admin_rows, caption=t("ui.admin_users"))
        editable_admins = [row for row in admin_rows if row.get("source") != "toml_primary_admin"]
        if editable_admins:
            selected_admin_email = st.selectbox(t("ui.select_admin"), options=[row["email"] for row in editable_admins])
            selected_admin = next((row for row in users if str(row.get("email", "")).strip().lower() == selected_admin_email), None)
            action_cols = st.columns(2)
            if action_cols[0].button(t("ui.activate_admin"), use_container_width=True):
                if selected_admin:
                    selected_admin["status"] = "ACTIVE"
                    try:
                        data_service.persist_collection("users")
                        st.success(t("ui.admin_activated"))
                    except Exception as exc:
                        st.error(f"Drive write failed: {exc}")
            if action_cols[1].button(t("ui.deactivate_admin"), use_container_width=True):
                if selected_admin:
                    selected_admin["status"] = "INACTIVE"
                    try:
                        data_service.persist_collection("users")
                        st.success(t("ui.admin_deactivated"))
                    except Exception as exc:
                        st.error(f"Drive write failed: {exc}")
        with st.form("add_admin_form"):
            email = st.text_input(t("ui.admin_email"))
            display_name = st.text_input(t("ui.display_name"))
            admin_type = st.selectbox(t("ui.admin_type"), ["operations", "catalog", "finance", "support", "logistics"])
            submitted = st.form_submit_button(t("ui.add_admin"), use_container_width=True)
        if submitted:
            normalized_email = email.strip().lower()
            existing = {str(row.get("email", "")).strip().lower() for row in admin_rows}
            if not normalized_email:
                st.error(t("ui.admin_email_required"))
            elif normalized_email in existing:
                st.error(t("ui.duplicate_admin_email"))
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
                        to_email=normalized_email,
                        title="New admin added",
                        message=f"{record['display_name']} was added as admin.",
                        event_type="ADMIN_ADDED",
                        source_entity="users",
                        source_id=record["user_id"],
                        created_by=session_service.get_user().get("email", ""),
                    )
                    if primary_admin.get("email"):
                        notification_service.create_notification(
                            to_email=primary_admin["email"],
                            title="Admin registry updated",
                            message=f"{record['display_name']} was added as admin.",
                            event_type="ADMIN_ADDED",
                            source_entity="users",
                            source_id=record["user_id"],
                            created_by=session_service.get_user().get("email", ""),
                        )
                    data_service.persist_collection("notifications")
                    data_service.persist_collection("gmail_queue")
                    st.success(t("ui.admin_added"))
                except Exception as exc:
                    users.pop()
                    st.error(f"Drive write failed: {exc}")

    with tabs[1]:
        manifest = admin_drive_service.get_runtime_manifest()
        render_table(manifest.get("required_files", []), caption=t("ui.required_files"))
        if manifest.get("missing_files"):
            st.error(t("ui.required_drive_files_missing"))
            if st.button(t("ui.create_missing_drive_files"), use_container_width=True):
                try:
                    result = admin_drive_service.create_missing_required_files()
                    st.success(f"{t('ui.created')} {len(result.get('created', []))} {t('ui.files_folders')}.")
                    st.rerun()
                except Exception as exc:
                    st.error(f"{t('ui.create_missing_files_failed')}: {exc}")
        else:
            st.success(t("ui.all_required_drive_files_present"))
    with tabs[2]:
        st.info(t("ui.integrations_drive_backed"))
        theme_service = ThemeService(admin_drive_service, CacheService(ConfigLoaderService()))
        render_theme_manager(theme_service, allow_set_default=True, title=t("ui.theme_background_manager"), key_prefix="admin_theme")
