from __future__ import annotations

from typing import Iterable

from constants.navigation_icons import NAV_ICON_MAP, get_nav_icon, normalize_nav_label
from constants.roles import ROLE_MAHAJAN, ROLE_MANUFACTURER, ROLE_PENDING_USER, ROLE_PLATFORM_ADMIN, ROLE_PUBLIC_BUYER, ROLE_UNAUTHENTICATED, ROLE_WORKER

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
}


ROLE_NAVIGATION_MAP: dict[str, list[tuple[str, list[str]]]] = {
    ROLE_UNAUTHENTICATED: [
        ("General", ["Dashboard"]),
    ],
    ROLE_PLATFORM_ADMIN: [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Ecosystem", ["Manufacturers", "Mahajans", "Workers", "Products", "Product Approvals"]),
        ("Marketplace", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["MandiPlace", "Mandi Orders"]),
        ("Supply Network", ["Raw Materials", "Supply Orders"]),
        ("Finance", ["Payments", "Ledger", "Platform Commission", "Finance Operations"]),
        ("Operations", ["Operations Center", "Warehouses", "Packaging Services", "Courier Services", "Shipments", "Logistics", "Jobs", "System Health", "Analytics"]),
    ],
    ROLE_MAHAJAN: [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Supply Network", ["Warehouses", "Raw Materials", "Shipments", "Supply Orders"]),
        ("Finance", ["Payments", "Ledger"]),
        ("Operations", ["Jobs"]),
    ],
    ROLE_MANUFACTURER: [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Product Operations", ["Products", "Warehouses", "Inventory", "Shipments"]),
        ("Marketplace", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["MandiPlace", "Mandi Orders", "Supply Requests", "Suta Mandi"]),
        ("Finance", ["Payments", "Ledger"]),
        ("Operations", ["Jobs"]),
    ],
    ROLE_PUBLIC_BUYER: [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Marketplace", ["Marketplace", "Marketplace Orders"]),
        ("Operations", ["Jobs"]),
    ],
    ROLE_WORKER: [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Work", ["Jobs"]),
    ],
    ROLE_PENDING_USER: [
        ("General", ["Dashboard"]),
    ],
}


def get_navigation_groups(role_key: str) -> list[tuple[str, list[str]]]:
    return ROLE_NAVIGATION_MAP.get(role_key, ROLE_NAVIGATION_MAP[ROLE_UNAUTHENTICATED])


def flatten_navigation_groups(groups: Iterable[tuple[str, list[str]]]) -> list[str]:
    return [item for _group, sections in groups for item in sections]


def normalize_navigation_label(label: str) -> str:
    aliased = NAV_ALIAS_MAP.get(label, label)
    return normalize_nav_label(aliased)


def icon_for_navigation_label(label: str) -> str:
    return get_nav_icon(normalize_navigation_label(label))


def navigation_icon_coverage() -> dict[str, str]:
    labels = [item for groups in ROLE_NAVIGATION_MAP.values() for item in flatten_navigation_groups(groups)]
    return {label: icon_for_navigation_label(label) for label in sorted(set(labels))}
