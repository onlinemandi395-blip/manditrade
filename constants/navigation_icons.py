from __future__ import annotations


NAV_ICON_MAP: dict[str, str] = {
    "Dashboard": "\u2302",
    "My Profile": "\u25c9",
    "Notifications": "\u2736",
    "My Actions": "\u27a4",
    "Manufacturers": "\u25a3",
    "Mahajans": "\u2733",
    "Workers": "\u2692",
    "Products": "\u25ab",
    "Product Approvals": "\u2713",
    "Marketplace": "\u25c6",
    "Marketplace Orders": "\u25ea",
    "MandiPlace": "\u25c8",
    "Mandi Orders": "\u21c4",
    "Raw Materials": "\u25a4",
    "Supply Orders": "\u25b7",
    "Supply Requests": "\u25cc",
    "Suta Mandi": "\u25cd",
    "Payments": "\u25c7",
    "Ledger": "\u25a5",
    "Platform Commission": "\u25ce",
    "Jobs": "\u2723",
    "System Health": "\u271a",
    "Analytics": "\u25b3",
    "Operations Center": "\u2318",
    "Finance Operations": "\u25ec",
    "Packaging Services": "\u25a1",
    "Courier Services": "\u2197",
    "Logistics": "\u229e",
    "Inventory": "\u25a6",
}

NAV_ICON_ALIASES: dict[str, str] = {
    "Marketplace Order": "Marketplace Orders",
    "Mandi Order": "Mandi Orders",
    "Payment": "Payments",
    "Notification": "Notifications",
    "My Action": "My Actions",
    "MyProfile": "My Profile",
    "Manufacturer": "Manufacturers",
    "Product Approval": "Product Approvals",
    "Mandiplace": "MandiPlace",
    "Mandiplace Order": "Mandi Orders",
    "RFQ": "Mandi Orders",
    "rfq": "Mandi Orders",
    "Platform Commision": "Platform Commission",
}

NAV_ICON_FALLBACK = "\u2022"


def normalize_nav_label(label: str) -> str:
    cleaned = " ".join(str(label or "").strip().split())
    if not cleaned:
        return ""
    return NAV_ICON_ALIASES.get(cleaned, cleaned)


def get_nav_icon(label: str) -> str:
    normalized = normalize_nav_label(label)
    return NAV_ICON_MAP.get(normalized, NAV_ICON_FALLBACK)


def nav_icon_for(label: str) -> str:
    return get_nav_icon(label)
