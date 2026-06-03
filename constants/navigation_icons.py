from __future__ import annotations


NAV_ICON_MAP: dict[str, str] = {
    "Dashboard": "⌂",
    "My Profile": "◉",
    "Notifications": "✦",
    "My Actions": "➤",
    "Manufacturers": "▣",
    "Mahajans": "✳",
    "Products": "◫",
    "Product Approvals": "✓",
    "Marketplace": "◆",
    "Marketplace Orders": "◪",
    "MandiPlace": "◈",
    "Mandi Orders": "⇄",
    "Raw Materials": "▤",
    "Supply Orders": "▷",
    "Supply Requests": "◌",
    "Suta Mandi": "◍",
    "Payments": "◇",
    "Ledger": "▥",
    "Platform Commission": "◎",
    "Jobs": "✣",
    "System Health": "✚",
    "Analytics": "△",
    "Operations Center": "⌘",
    "Finance Operations": "◬",
    "Packaging Services": "□",
    "Courier Services": "↗",
    "Logistics": "⊞",
    "Inventory": "▦",
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

NAV_ICON_FALLBACK = "•"


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
