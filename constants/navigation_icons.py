from __future__ import annotations


NAV_ICON_MAP: dict[str, str] = {
    "Dashboard": "🏠",
    "My Profile": "👤",
    "Notifications": "🔔",
    "My Actions": "⚡",
    "Manufacturers": "🏭",
    "Mahajans": "🌾",
    "Products": "📦",
    "Product Approvals": "✅",
    "Marketplace": "🛒",
    "Marketplace Orders": "🧾",
    "MandiPlace": "🏬",
    "Mandi Orders": "🔁",
    "Raw Materials": "🧱",
    "Supply Orders": "🚚",
    "Supply Requests": "🧾",
    "Suta Mandi": "🧵",
    "Payments": "💳",
    "Ledger": "📒",
    "Platform Commission": "💰",
    "Jobs": "🛠️",
    "System Health": "🩺",
    "Analytics": "📊",
    "Operations Center": "🧭",
    "Finance Operations": "🏦",
    "Packaging Services": "📦",
    "Courier Services": "🚛",
    "Logistics": "🛣️",
    "Inventory": "📚",
}


def nav_icon_for(label: str) -> str:
    return NAV_ICON_MAP.get(str(label or "").strip(), "•")
