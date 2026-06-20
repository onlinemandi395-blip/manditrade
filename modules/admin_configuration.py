from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from components.table_renderer import render_table
from components.theme_manager import render_theme_manager
from services.admin_drive_service import AdminDriveService
from services.cache_service import CacheService
from services.config_loader_service import ConfigLoaderService
from services.theme_service import ThemeService


def _available_navigation_options(cache_service, translator) -> list[dict]:
    navigation_rows = list(cache_service.get_config("navigation").get("navigation", {}).get("items", []) or [])
    seen_routes: set[str] = set()
    options: list[dict] = []
    for item in navigation_rows:
        route = str(item.get("route", "")).strip()
        if not route or route in seen_routes:
            continue
        seen_routes.add(route)
        options.append(
            {
                "route": route,
                "label": str(translator.t(item.get("label_key", route)) if translator else item.get("label_key", route) or route),
            }
        )
    return sorted(options, key=lambda row: row["label"].lower())


def _normalize_admin_types(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and str(value).strip():
        return [str(value).strip()]
    return []


def _normalize_admin_routes(value) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and str(value).strip():
        return [str(value).strip()]
    return []


def render_admin_configuration(auth_service, data_service, notification_service, session_service, cache_service, translator=None) -> None:
    t = translator.t if translator else (lambda key: key)
    users = data_service.get_collection_ref("users")
    primary_admin = auth_service.get_primary_admin()
    admin_drive_service = AdminDriveService()
    navigation_options = _available_navigation_options(cache_service, translator)
    navigation_route_map = {row["route"]: row["label"] for row in navigation_options}
    profile_options = ["operations", "catalog", "finance", "support", "logistics", "custom"]
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
                "admin_navigation_routes": ["*"],
                "admin_navigation_labels": ["Full Access"],
            }
        )
    admin_rows.extend(
        [
            {
                **user,
                "admin_type": ", ".join(_normalize_admin_types(user.get("admin_types", user.get("admin_type", [])))) or str(user.get("admin_type", "")).strip(),
                "admin_navigation_labels": ", ".join(
                    navigation_route_map.get(route, route)
                    for route in _normalize_admin_routes(user.get("admin_navigation_routes", []))
                ),
            }
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
            if selected_admin:
                st.markdown("### Manage Selected Admin")
                selected_admin.setdefault("admin_types", _normalize_admin_types(selected_admin.get("admin_type", [])))
                selected_admin.setdefault("admin_navigation_routes", _normalize_admin_routes(selected_admin.get("admin_navigation_routes", [])))
                with st.form("edit_admin_form"):
                    edit_email = st.text_input("Admin Email", value=str(selected_admin.get("email", "")).strip(), disabled=True)
                    edit_display_name = st.text_input("Display Name", value=str(selected_admin.get("display_name", "")).strip())
                    edit_status = st.selectbox("Status", options=["ACTIVE", "INACTIVE"], index=0 if str(selected_admin.get("status", "ACTIVE")).upper() == "ACTIVE" else 1)
                    edit_admin_types = st.multiselect(
                        "Admin Profile",
                        options=profile_options,
                        default=_normalize_admin_types(selected_admin.get("admin_types", selected_admin.get("admin_type", []))),
                    )
                    edit_admin_routes = st.multiselect(
                        "Admin Type / Navigation Access",
                        options=[row["route"] for row in navigation_options],
                        default=_normalize_admin_routes(selected_admin.get("admin_navigation_routes", [])),
                        format_func=lambda route: navigation_route_map.get(route, route),
                        help="Only these sidebar navigations will be visible for this admin.",
                    )
                    action_cols = st.columns(4)
                    update_clicked = action_cols[0].form_submit_button("Update Admin", use_container_width=True)
                    activate_clicked = action_cols[1].form_submit_button(t("ui.activate_admin"), use_container_width=True)
                    deactivate_clicked = action_cols[2].form_submit_button(t("ui.deactivate_admin"), use_container_width=True)
                    delete_clicked = action_cols[3].form_submit_button("Delete Admin", use_container_width=True)
                if update_clicked or activate_clicked or deactivate_clicked or delete_clicked:
                    previous_snapshot = dict(selected_admin)
                    try:
                        if delete_clicked:
                            users.remove(selected_admin)
                            data_service.persist_collection("users")
                            st.success("Secondary admin deleted.")
                            st.rerun()
                        if activate_clicked:
                            selected_admin["status"] = "ACTIVE"
                        elif deactivate_clicked:
                            selected_admin["status"] = "INACTIVE"
                        else:
                            selected_admin["status"] = edit_status
                        selected_admin["display_name"] = edit_display_name.strip() or str(selected_admin.get("email", "")).split("@")[0]
                        selected_admin["admin_types"] = edit_admin_types
                        selected_admin["admin_type"] = edit_admin_types[0] if edit_admin_types else "custom"
                        selected_admin["admin_navigation_routes"] = edit_admin_routes
                        selected_admin["updated_at"] = datetime.now(UTC).isoformat()
                        selected_admin["updated_by"] = session_service.get_user().get("email", "")
                        if not selected_admin.get("admin_navigation_routes"):
                            raise ValueError("Select at least one navigation for this admin.")
                        data_service.persist_collection("users")
                        st.success("Admin updated.")
                        st.rerun()
                    except Exception as exc:
                        selected_admin.clear()
                        selected_admin.update(previous_snapshot)
                        st.error(f"Drive write failed: {exc}")
        with st.form("add_admin_form"):
            email = st.text_input(t("ui.admin_email"))
            display_name = st.text_input(t("ui.display_name"))
            admin_profiles = st.multiselect("Admin Profile", options=profile_options, default=["operations"])
            admin_navigation_routes = st.multiselect(
                "Admin Type / Navigation Access",
                options=[row["route"] for row in navigation_options],
                default=[],
                format_func=lambda route: navigation_route_map.get(route, route),
                help="Only these sidebar navigations will be visible for this admin.",
            )
            submitted = st.form_submit_button(t("ui.add_admin"), use_container_width=True)
        if submitted:
            normalized_email = email.strip().lower()
            existing = {str(row.get("email", "")).strip().lower() for row in admin_rows}
            if not normalized_email:
                st.error(t("ui.admin_email_required"))
            elif normalized_email in existing:
                st.error(t("ui.duplicate_admin_email"))
            elif not admin_navigation_routes:
                st.error("Select at least one navigation for this admin.")
            else:
                record = {
                    "user_id": f"USR_{len(users) + 1:04d}",
                    "email": normalized_email,
                    "role": "platform_admin",
                    "status": "ACTIVE",
                    "display_name": display_name.strip() or normalized_email.split("@")[0],
                    "admin_type": admin_profiles[0] if admin_profiles else "custom",
                    "admin_types": admin_profiles,
                    "admin_navigation_routes": admin_navigation_routes,
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
