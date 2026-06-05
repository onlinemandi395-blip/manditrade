from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from constants.navigation_icons import NAV_ICON_MAP, get_nav_icon, normalize_nav_label
from constants.roles import ROLE_MAHAJAN, ROLE_MANUFACTURER, ROLE_PENDING_USER, ROLE_PLATFORM_ADMIN, ROLE_PUBLIC_BUYER, ROLE_UNAUTHENTICATED, ROLE_WORKER

BASE_DIR = Path(__file__).resolve().parent.parent
LOCAL_NAVIGATION_CONFIG_PATH = BASE_DIR / "configs" / "navigation_config.json"

NAV_ALIAS_MAP: dict[str, str] = {
    "Mandiplace": "MandiPlace",
    "Mandiplace Order": "Mandi Orders",
    "rfq": "Mandi Orders",
    "RFQ": "Mandi Orders",
    "Platform Commision": "Platform Commission",
    "MyProfile": "My Profile",
    "Notification": "Notifications",
    "My Action": "My Actions",
    "Marketplace Order": "Marketplace Orders",
    "Payment": "Payments",
    "Manufacturer": "Manufacturers",
    "Product Approval": "Product Approvals",
    "Supply Requests": "Mandi Orders",
    "Supply Orders": "Mandi Orders",
    "Public Orders": "Marketplace Orders",
    "System Health": "Admin Drive DB",
    "Procurement Source": "Procurement Sources",
}

ROUTE_ALIASES: dict[str, str] = {
    "dashboard": "dashboard",
    "my profile": "my_profile",
    "my_profile": "my_profile",
    "profile": "my_profile",
    "notifications": "notifications",
    "my actions": "my_actions",
    "my_actions": "my_actions",
    "manufacturers": "manufacturers",
    "mahajans": "mahajans",
    "workers": "workers",
    "products": "products",
    "procurement sources": "procurement_sources",
    "procurement_sources": "procurement_sources",
    "product approvals": "product_approvals",
    "product_approvals": "product_approvals",
    "marketplace": "marketplace",
    "marketplace orders": "my_orders",
    "marketplace_orders": "my_orders",
    "public orders": "my_orders",
    "public_orders": "my_orders",
    "mandiplace": "mandiplace",
    "mandiplace": "mandiplace",
    "mandi orders": "orders",
    "mandi_orders": "orders",
    "supply orders": "orders",
    "supply_orders": "orders",
    "supply requests": "my_orders",
    "supply_requests": "my_orders",
    "raw materials": "raw_materials",
    "raw_materials": "raw_materials",
    "suta mandi": "suta_mandi",
    "suta_mandi": "suta_mandi",
    "payments": "payments",
    "ledger": "ledger",
    "ledger / khata": "ledger",
    "platform commission": "platform_commission",
    "platform_commission": "platform_commission",
    "finance operations": "finance_operations",
    "finance_operations": "finance_operations",
    "operations center": "operations_center",
    "operations_center": "operations_center",
    "warehouses": "warehouses",
    "inventory": "inventory",
    "packaging services": "packaging_services",
    "packaging_services": "packaging_services",
    "courier services": "courier_services",
    "courier_services": "courier_services",
    "shipments": "shipments",
    "logistics": "logistics",
    "jobs": "jobs",
    "analytics": "analytics",
    "system health": "system_health",
    "system_health": "system_health",
    "admin drive db": "admin_drive_db",
    "admin_drive_db": "admin_drive_db",
    "orders": "orders",
    "my orders": "my_orders",
    "my_orders": "my_orders",
    "dispatch": "dispatch",
    "inventory summary": "inventory_summary",
    "inventory_summary": "inventory_summary",
    "onboarding": "onboarding",
}

DEFAULT_NAVIGATION_CONFIG: dict[str, Any] = {
    "schema_version": 1,
    "updated_at": "",
    "roles": {
        ROLE_UNAUTHENTICATED: [
            {"group": "General", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}]},
        ],
        ROLE_PLATFORM_ADMIN: [
            {"group": "Platform", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}, {"label": "My Profile", "icon": "", "route": "my_profile"}, {"label": "Notifications", "icon": "", "route": "notifications"}, {"label": "My Actions", "icon": "", "route": "my_actions"}, {"label": "System Health", "icon": "", "route": "system_health"}, {"label": "Admin Drive DB", "icon": "", "route": "admin_drive_db"}]},
            {"group": "Ecosystem", "items": [{"label": "Manufacturers", "icon": "", "route": "manufacturers"}, {"label": "Mahajans", "icon": "", "route": "mahajans"}, {"label": "Workers", "icon": "", "route": "workers"}, {"label": "Products", "icon": "", "route": "products"}, {"label": "Procurement Sources", "icon": "", "route": "procurement_sources"}]},
            {"group": "Operations", "items": [{"label": "Orders", "icon": "", "route": "orders"}, {"label": "Inventory", "icon": "", "route": "inventory"}, {"label": "Warehouses", "icon": "", "route": "warehouses"}, {"label": "Shipments", "icon": "", "route": "shipments"}]},
            {"group": "Finance", "items": [{"label": "Payments", "icon": "", "route": "payments"}, {"label": "Ledger", "icon": "", "route": "ledger"}, {"label": "Platform Commission", "icon": "", "route": "platform_commission"}]},
            {"group": "Insights", "items": [{"label": "Analytics", "icon": "", "route": "analytics"}]},
        ],
        ROLE_MAHAJAN: [
            {"group": "Core", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}, {"label": "My Profile", "icon": "", "route": "my_profile"}, {"label": "Notifications", "icon": "", "route": "notifications"}, {"label": "My Actions", "icon": "", "route": "my_actions"}]},
            {"group": "Supply Network", "items": [{"label": "Warehouses", "icon": "", "route": "warehouses"}, {"label": "Raw Materials", "icon": "", "route": "raw_materials"}, {"label": "Shipments", "icon": "", "route": "shipments"}, {"label": "My Orders", "icon": "", "route": "my_orders"}]},
            {"group": "Finance", "items": [{"label": "Payments", "icon": "", "route": "payments"}, {"label": "Ledger", "icon": "", "route": "ledger"}]},
            {"group": "Operations", "items": [{"label": "Jobs", "icon": "", "route": "jobs"}]},
        ],
        ROLE_MANUFACTURER: [
            {"group": "Core", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}, {"label": "My Profile", "icon": "", "route": "my_profile"}, {"label": "Notifications", "icon": "", "route": "notifications"}, {"label": "My Actions", "icon": "", "route": "my_actions"}]},
            {"group": "Product Operations", "items": [{"label": "Products", "icon": "", "route": "products"}, {"label": "Warehouses", "icon": "", "route": "warehouses"}, {"label": "Inventory", "icon": "", "route": "inventory"}, {"label": "Shipments", "icon": "", "route": "shipments"}]},
            {"group": "Commerce", "items": [{"label": "Marketplace", "icon": "", "route": "marketplace"}, {"label": "MandiPlace", "icon": "", "route": "mandiplace"}, {"label": "Raw Materials", "icon": "", "route": "raw_materials"}, {"label": "Suta Mandi", "icon": "", "route": "suta_mandi"}, {"label": "My Orders", "icon": "", "route": "my_orders"}]},
            {"group": "Finance", "items": [{"label": "Payments", "icon": "", "route": "payments"}, {"label": "Ledger", "icon": "", "route": "ledger"}]},
            {"group": "Operations", "items": [{"label": "Jobs", "icon": "", "route": "jobs"}]},
        ],
        ROLE_PUBLIC_BUYER: [
            {"group": "Core", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}, {"label": "My Profile", "icon": "", "route": "my_profile"}, {"label": "Notifications", "icon": "", "route": "notifications"}, {"label": "My Actions", "icon": "", "route": "my_actions"}]},
            {"group": "Marketplace", "items": [{"label": "Marketplace", "icon": "", "route": "marketplace"}, {"label": "My Orders", "icon": "", "route": "my_orders"}]},
            {"group": "Operations", "items": [{"label": "Jobs", "icon": "", "route": "jobs"}]},
        ],
        ROLE_WORKER: [
            {"group": "Core", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}, {"label": "My Profile", "icon": "", "route": "my_profile"}, {"label": "Notifications", "icon": "", "route": "notifications"}, {"label": "My Actions", "icon": "", "route": "my_actions"}]},
            {"group": "Work", "items": [{"label": "Jobs", "icon": "", "route": "jobs"}]},
        ],
        ROLE_PENDING_USER: [
            {"group": "General", "items": [{"label": "Dashboard", "icon": "", "route": "dashboard"}]},
        ],
    },
    "default_routes": {
        ROLE_PLATFORM_ADMIN: "dashboard",
        ROLE_MANUFACTURER: "dashboard",
        ROLE_MAHAJAN: "dashboard",
        ROLE_PUBLIC_BUYER: "marketplace",
        ROLE_WORKER: "jobs",
        ROLE_PENDING_USER: "dashboard",
        ROLE_UNAUTHENTICATED: "dashboard",
    },
}


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def _iter_role_items(config: dict[str, Any]) -> Iterable[dict[str, Any]]:
    for groups in (config.get("roles") or {}).values():
        for group in groups or []:
            for item in group.get("items", []) or []:
                yield item


def normalize_navigation_label(label: str) -> str:
    aliased = NAV_ALIAS_MAP.get(label, label)
    return normalize_nav_label(aliased)


def normalize_navigation_route(route: str) -> str:
    cleaned = " ".join(str(route or "").strip().replace("-", "_").split())
    if not cleaned:
        return "dashboard"
    lowered = cleaned.lower()
    if lowered in ROUTE_ALIASES:
        return ROUTE_ALIASES[lowered]
    normalized_label = normalize_navigation_label(cleaned)
    label_key = normalized_label.lower()
    return ROUTE_ALIASES.get(label_key, label_key.replace(" ", "_"))


def icon_for_navigation_label(label: str) -> str:
    normalized = normalize_navigation_label(label)
    return get_nav_icon(normalized)


def _default_navigation_config() -> dict[str, Any]:
    config = deepcopy(DEFAULT_NAVIGATION_CONFIG)
    config["updated_at"] = _now_iso()
    for item in _iter_role_items(config):
        if not item.get("icon"):
            item["icon"] = icon_for_navigation_label(item.get("label", ""))
    return config


def _normalize_group(group: dict[str, Any]) -> dict[str, Any]:
    normalized_items: list[dict[str, str]] = []
    seen_routes: set[str] = set()
    for item in group.get("items", []) or []:
        label = normalize_navigation_label(str(item.get("label") or ""))
        route = normalize_navigation_route(str(item.get("route") or label))
        if not label or route in seen_routes:
            continue
        seen_routes.add(route)
        normalized_items.append(
            {
                "label": label,
                "icon": str(item.get("icon") or icon_for_navigation_label(label)),
                "route": route,
            }
        )
    return {"group": str(group.get("group") or "General"), "items": normalized_items}


def validate_navigation_config(config: dict[str, Any] | None) -> dict[str, Any]:
    fallback = _default_navigation_config()
    if not isinstance(config, dict):
        return fallback
    roles: dict[str, list[dict[str, Any]]] = {}
    source_roles = config.get("roles") if isinstance(config.get("roles"), dict) else {}
    for role in fallback["roles"]:
        raw_groups = source_roles.get(role, fallback["roles"][role])
        groups = [_normalize_group(group) for group in raw_groups if isinstance(group, dict)]
        groups = [group for group in groups if group["items"]]
        roles[role] = groups or deepcopy(fallback["roles"][role])
    default_routes = dict(fallback["default_routes"])
    raw_defaults = config.get("default_routes") if isinstance(config.get("default_routes"), dict) else {}
    for role, built_in_route in fallback["default_routes"].items():
        available_routes = [item["route"] for group in roles.get(role, []) for item in group["items"]]
        preferred = normalize_navigation_route(str(raw_defaults.get(role, built_in_route)))
        default_routes[role] = preferred if preferred in available_routes else (available_routes[0] if available_routes else built_in_route)
    return {
        "schema_version": int(config.get("schema_version") or fallback["schema_version"]),
        "updated_at": str(config.get("updated_at") or _now_iso()),
        "roles": roles,
        "default_routes": default_routes,
    }


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _load_json_with_error(path: Path) -> tuple[dict[str, Any] | None, str]:
    if not path.exists():
        return None, "missing"
    try:
        return json.loads(path.read_text(encoding="utf-8")), ""
    except Exception as exc:  # noqa: BLE001
        return None, str(exc)


def _drive_navigation_config_path(app_context: dict | None) -> Path | None:
    if not app_context or "drive_path_service" not in app_context:
        return None
    return app_context["drive_path_service"].get_config_path("navigation_config.json")


def _seed_drive_navigation_config_if_missing(app_context: dict | None, local_config: dict[str, Any]) -> None:
    if not app_context or "safe_drive_write_service" not in app_context:
        return
    target = _drive_navigation_config_path(app_context)
    if not target or target.exists():
        return
    app_context["safe_drive_write_service"].replace_document(target, validate_navigation_config(local_config))


def load_navigation_config(app_context: dict | None = None) -> dict[str, Any]:
    return load_navigation_bundle(app_context)["config"]


def load_navigation_bundle(app_context: dict | None = None) -> dict[str, Any]:
    fallback = _default_navigation_config()
    local_config, local_error = _load_json_with_error(LOCAL_NAVIGATION_CONFIG_PATH)
    effective_local = local_config or fallback
    metadata = {
        "source": "BUILTIN_FALLBACK",
        "path": str(LOCAL_NAVIGATION_CONFIG_PATH),
        "loaded_at": _now_iso(),
        "loaded_roles": sorted(role for role in fallback["roles"] if role != ROLE_UNAUTHENTICATED and role != ROLE_PENDING_USER),
        "errors": [],
    }
    if local_error and local_error != "missing":
        metadata["errors"].append(f"Local config parse error: {local_error}")
    drive_runtime_ready = False
    if app_context and "admin_drive_database_service" in app_context:
        runtime = app_context["admin_drive_database_service"].runtime_status()
        drive_runtime_ready = bool(runtime.get("drive_api_ready", False))
    _seed_drive_navigation_config_if_missing(app_context, local_config)
    drive_path = _drive_navigation_config_path(app_context)
    if drive_path and drive_runtime_ready:
        drive_config, drive_error = _load_json_with_error(drive_path)
        if drive_error and drive_error != "missing":
            metadata["errors"].append(f"Drive config parse error: {drive_error}")
        if isinstance(drive_config, dict) and drive_config.get("roles"):
            config = validate_navigation_config(drive_config)
            metadata["source"] = "DRIVE"
            metadata["path"] = str(drive_path)
            metadata["loaded_roles"] = sorted(role for role in config["roles"] if role not in {ROLE_UNAUTHENTICATED, ROLE_PENDING_USER})
            return {"config": config, "metadata": metadata}
        if app_context and "safe_drive_write_service" in app_context:
            app_context["safe_drive_write_service"].replace_document(drive_path, validate_navigation_config(effective_local))
            refreshed, refresh_error = _load_json_with_error(drive_path)
            if refresh_error and refresh_error != "missing":
                metadata["errors"].append(f"Drive config refresh error: {refresh_error}")
            if isinstance(refreshed, dict) and refreshed.get("roles"):
                metadata["errors"].append("Drive config was refreshed from local fallback.")
    if local_config:
        config = validate_navigation_config(local_config)
        metadata["source"] = "LOCAL_CONFIG"
        metadata["path"] = str(LOCAL_NAVIGATION_CONFIG_PATH)
        metadata["loaded_roles"] = sorted(role for role in config["roles"] if role not in {ROLE_UNAUTHENTICATED, ROLE_PENDING_USER})
        return {"config": config, "metadata": metadata}
    return {"config": fallback, "metadata": metadata}


def get_navigation_groups(role_key: str, app_context: dict | None = None) -> list[tuple[str, list[dict[str, str]]]]:
    config = load_navigation_bundle(app_context)["config"]
    groups = config["roles"].get(role_key, config["roles"][ROLE_UNAUTHENTICATED])
    return [(group["group"], list(group["items"])) for group in groups]


def get_navigation_for_role(role_key: str, app_context: dict | None = None) -> list[tuple[str, list[dict[str, str]]]]:
    return get_navigation_groups(role_key, app_context)


def flatten_navigation_groups(groups: Iterable[tuple[str, list[dict[str, str]]]]) -> list[dict[str, str]]:
    return [item for _group, sections in groups for item in sections]


def get_default_route_for_role(role_key: str, app_context: dict | None = None) -> str:
    config = load_navigation_bundle(app_context)["config"]
    default_route = normalize_navigation_route(config["default_routes"].get(role_key, "dashboard"))
    available_routes = [item["route"] for item in flatten_navigation_groups(get_navigation_groups(role_key, app_context))]
    return default_route if default_route in available_routes else (available_routes[0] if available_routes else "dashboard")


def get_navigation_label(route: str, app_context: dict | None = None) -> str:
    normalized_route = normalize_navigation_route(route)
    for item in flatten_navigation_groups(get_navigation_groups(ROLE_PLATFORM_ADMIN, app_context)):
        if item["route"] == normalized_route:
            return item["label"]
    for item in _iter_role_items(load_navigation_config(app_context)):
        if normalize_navigation_route(item.get("route", "")) == normalized_route:
            return normalize_navigation_label(item.get("label", normalized_route))
    return normalize_navigation_label(normalized_route.replace("_", " ").title())


def navigation_icon_coverage(app_context: dict | None = None) -> dict[str, str]:
    config = load_navigation_bundle(app_context)["config"]
    labels = [item["label"] for item in _iter_role_items(config)]
    return {label: icon_for_navigation_label(label) for label in sorted(set(labels))}


def get_navigation_runtime_info(role_key: str, app_context: dict | None = None) -> dict[str, Any]:
    bundle = load_navigation_bundle(app_context)
    config = bundle["config"]
    metadata = dict(bundle["metadata"])
    groups = get_navigation_for_role(role_key, app_context)
    metadata.update(
        {
            "active_role": role_key,
            "default_route": get_default_route_for_role(role_key, app_context),
            "nav_groups": [{"group": group, "items": [item["label"] for item in items]} for group, items in groups],
            "nav_item_count": len(flatten_navigation_groups(groups)),
            "config_roles": sorted(role for role in config["roles"] if role not in {ROLE_UNAUTHENTICATED, ROLE_PENDING_USER}),
        }
    )
    return metadata
