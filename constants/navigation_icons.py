from __future__ import annotations


NAV_ICON_MAP: dict[str, str] = {
    "Dashboard": "[DB]",
    "My Profile": "[ME]",
    "Notifications": "[NT]",
    "My Actions": "[AC]",
    "Manufacturers": "[MF]",
    "Mahajans": "[MJ]",
    "Products": "[PD]",
    "Product Approvals": "[PA]",
    "Marketplace": "[MK]",
    "Marketplace Orders": "[MO]",
    "MandiPlace": "[MP]",
    "Mandi Orders": "[MD]",
    "Raw Materials": "[RM]",
    "Supply Orders": "[SO]",
    "Supply Requests": "[SR]",
    "Suta Mandi": "[SM]",
    "Payments": "[PY]",
    "Ledger": "[LG]",
    "Platform Commission": "[PC]",
    "Jobs": "[JB]",
    "System Health": "[SH]",
    "Analytics": "[AN]",
    "Operations Center": "[OC]",
    "Finance Operations": "[FO]",
    "Packaging Services": "[PK]",
    "Courier Services": "[CR]",
    "Logistics": "[LO]",
    "Inventory": "[IV]",
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

NAV_ICON_FALLBACK = "[--]"


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
