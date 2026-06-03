from __future__ import annotations


NAV_ICON_MAP: dict[str, str] = {
    "Dashboard": "\u2302",
    "My Profile": "\U0001F464",
    "Notifications": "\U0001F514",
    "My Actions": "\u26A1",
    "Manufacturers": "\U0001F3ED",
    "Mahajans": "\U0001F33E",
    "Products": "\U0001F4E6",
    "Product Approvals": "\u2705",
    "Marketplace": "\U0001F6D2",
    "Marketplace Orders": "\U0001F4CB",
    "MandiPlace": "\U0001F3EC",
    "Mandi Orders": "\U0001F501",
    "Raw Materials": "\U0001F9F1",
    "Supply Orders": "\U0001F69A",
    "Supply Requests": "\U0001F4DD",
    "Suta Mandi": "\U0001F9F5",
    "Payments": "\U0001F4B3",
    "Ledger": "\U0001F4D2",
    "Platform Commission": "\U0001F4B0",
    "Jobs": "\U0001F6E0",
    "System Health": "\U0001FA7A",
    "Analytics": "\U0001F4CA",
    "Operations Center": "\U0001F9ED",
    "Finance Operations": "\U0001F3E6",
    "Packaging Services": "\U0001F4E6",
    "Courier Services": "\U0001F69B",
    "Logistics": "\U0001F6E3",
    "Inventory": "\U0001F4DA",
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
