from __future__ import annotations

from typing import Iterable


NAV_ALIAS_MAP: dict[str, str] = {
    "MyProfile": "My Profile",
    "Notification": "Notifications",
    "My Action": "My Actions",
    "Manufacturer": "Manufacturers",
    "Product Approval": "Product Approvals",
    "Marketplace Order": "Marketplace Orders",
    "Mandiplace": "Mandi Network",
    "Mandiplace Order": "Mandi Orders",
    "rfq": "RFQ",
    "Payment": "Payments",
}


ROLE_NAVIGATION_MAP: dict[str, list[tuple[str, list[str]]]] = {
    "unauthenticated": [
        ("General", ["Dashboard"]),
    ],
    "platform_admin": [
        ("Core", ["My Profile", "Dashboard", "Notifications", "My Actions"]),
        ("Operations", ["Manufacturers", "Products", "Product Approvals"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["Mandi Network", "Mandi Orders", "RFQ"]),
        ("Workforce", ["Jobs"]),
        ("Finance", ["Platform Commission", "Payments", "Ledger"]),
        ("Platform", ["System Health"]),
    ],
    "manufacturer": [
        ("Core", ["My Profile", "Dashboard", "Notifications", "My Actions"]),
        ("Operations", ["Products", "Product Approvals", "Clients"]),
        ("Mandi Network", ["Mandi Network", "Mandi Orders", "RFQ"]),
        ("Workforce", ["Jobs"]),
        ("Finance", ["Platform Commission", "Payments", "Ledger"]),
    ],
    "client": [
        ("Core", ["My Profile", "Dashboard", "Notifications", "My Actions"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Network", ["RFQ"]),
        ("Finance", ["Payments", "Ledger"]),
        ("Support", ["System Health"]),
    ],
    "public_buyer": [
        ("Core", ["My Profile", "Dashboard", "Notifications", "My Actions"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Workforce", ["Jobs"]),
    ],
    "worker": [
        ("Core", ["My Profile", "Dashboard", "Notifications", "My Actions"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Workforce", ["Jobs"]),
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
