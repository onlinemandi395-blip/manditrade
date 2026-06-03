from __future__ import annotations

ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_MANUFACTURER = "manufacturer"
ROLE_MAHAJAN = "mahajan"
ROLE_PUBLIC_BUYER = "public_buyer"
ROLE_WORKER = "worker"
ROLE_PENDING_USER = "pending_user"
ROLE_ADMIN_AS_MANUFACTURER = "admin_as_manufacturer"
ROLE_UNAUTHENTICATED = "unauthenticated"

CANONICAL_ROLES = {
    ROLE_PLATFORM_ADMIN,
    ROLE_MANUFACTURER,
    ROLE_MAHAJAN,
    ROLE_PUBLIC_BUYER,
    ROLE_WORKER,
    ROLE_PENDING_USER,
}

ADMIN_BASE_ROLES = {"admin", ROLE_PLATFORM_ADMIN, "superuser"}

ROLE_DISPLAY_NAMES = {
    ROLE_PLATFORM_ADMIN: "Platform Admin",
    ROLE_MANUFACTURER: "Manufacturer",
    ROLE_MAHAJAN: "Mahajan",
    ROLE_PUBLIC_BUYER: "Public Buyer",
    ROLE_WORKER: "Worker",
    ROLE_PENDING_USER: "Pending User",
    ROLE_ADMIN_AS_MANUFACTURER: "Admin as Manufacturer",
}


def normalize_runtime_role(role: str) -> str:
    normalized = str(role or "").strip().lower()
    if normalized == ROLE_ADMIN_AS_MANUFACTURER:
        return ROLE_MANUFACTURER
    return normalized
