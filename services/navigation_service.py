from __future__ import annotations

from typing import Iterable


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
    "unauthenticated": [
        ("General", ["Dashboard"]),
    ],
    "platform_admin": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Ecosystem", ["Manufacturers", "Mahajans", "Products", "Product Approvals"]),
        ("Marketplace", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["MandiPlace", "Mandi Orders"]),
        ("Supply Network", ["Raw Materials", "Supply Orders"]),
        ("Finance", ["Payments", "Ledger", "Platform Commission"]),
        ("Operations", ["Operations Center", "Packaging Services", "Courier Services", "Logistics", "Jobs", "System Health", "Analytics"]),
    ],
    "mahajan": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Supply Network", ["Raw Materials", "Supply Orders"]),
        ("Finance", ["Payments", "Ledger"]),
        ("Operations", ["Jobs"]),
    ],
    "manufacturer": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Product Operations", ["Products", "Inventory"]),
        ("Marketplace", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["MandiPlace", "Mandi Orders", "Supply Requests", "Suta Mandi"]),
        ("Finance", ["Payments", "Ledger"]),
        ("Operations", ["Jobs"]),
    ],
    "public_buyer": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Marketplace", ["Marketplace", "Marketplace Orders"]),
        ("Operations", ["Jobs"]),
    ],
    "worker": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Work", ["Jobs"]),
    ],
    "pending_user": [
        ("General", ["Dashboard"]),
    ],
}


def get_navigation_groups(role_key: str) -> list[tuple[str, list[str]]]:
    return ROLE_NAVIGATION_MAP.get(role_key, ROLE_NAVIGATION_MAP["unauthenticated"])


def flatten_navigation_groups(groups: Iterable[tuple[str, list[str]]]) -> list[str]:
    return [item for _group, sections in groups for item in sections]


def normalize_navigation_label(label: str) -> str:
    return NAV_ALIAS_MAP.get(label, label)
