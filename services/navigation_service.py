from __future__ import annotations

from typing import Iterable


ROLE_NAVIGATION_MAP: dict[str, list[tuple[str, list[str]]]] = {
    "unauthenticated": [
        ("General", ["Dashboard"]),
    ],
    "platform_admin": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["Mandi Network", "RFQ", "Mandi Orders"]),
        ("Private Business", ["Manufacturers", "Products", "Product Approvals"]),
        ("Finance", ["Payments", "Ledger", "Platform Commission"]),
        ("Operations", ["Jobs", "System Health"]),
    ],
    "manufacturer": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Private Business", ["Products", "Inventory", "Clients", "Client Orders", "Ledger"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Mandi Network", ["Mandi Network", "RFQ", "Mandi Orders"]),
        ("Finance", ["Payments"]),
        ("Operations", ["Jobs"]),
    ],
    "client": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Private Business", ["Products", "My Orders", "Ledger", "Payments"]),
    ],
    "public_buyer": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Operations", ["Jobs"]),
    ],
    "worker": [
        ("Core", ["Dashboard", "My Profile", "Notifications", "My Actions"]),
        ("Commerce", ["Marketplace", "Marketplace Orders"]),
        ("Operations", ["Jobs"]),
    ],
    "pending_user": [
        ("General", ["Dashboard"]),
    ],
}


def get_navigation_groups(role_key: str) -> list[tuple[str, list[str]]]:
    return ROLE_NAVIGATION_MAP.get(role_key, ROLE_NAVIGATION_MAP["unauthenticated"])


def flatten_navigation_groups(groups: Iterable[tuple[str, list[str]]]) -> list[str]:
    return [item for _group, sections in groups for item in sections]
