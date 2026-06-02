from __future__ import annotations

from typing import Any


STATUS_STYLES: dict[str, dict[str, str]] = {
    "DEFAULT": {"label": "Unknown", "tone": "muted", "color": "#64748b", "background": "#f8fafc"},
    "PENDING": {"label": "Pending", "tone": "warning", "color": "#b45309", "background": "#fff7ed"},
    "OPEN": {"label": "Open", "tone": "info", "color": "#0369a1", "background": "#eff6ff"},
    "ACTIVE": {"label": "Active", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "SUCCESS": {"label": "Success", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "COMPLETED": {"label": "Completed", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "CLOSED": {"label": "Closed", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "APPROVED": {"label": "Approved", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "VERIFIED": {"label": "Verified", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "PAID": {"label": "Paid", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "DISPATCHED": {"label": "Dispatched", "tone": "info", "color": "#075985", "background": "#e0f2fe"},
    "DELIVERED": {"label": "Delivered", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "RECEIVED": {"label": "Received", "tone": "success", "color": "#166534", "background": "#ecfdf5"},
    "WARNING": {"label": "Warning", "tone": "warning", "color": "#b45309", "background": "#fff7ed"},
    "OVERDUE": {"label": "Overdue", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "FAILED": {"label": "Failed", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "REJECTED": {"label": "Rejected", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "CANCELLED": {"label": "Cancelled", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "ARCHIVED": {"label": "Archived", "tone": "muted", "color": "#475569", "background": "#f1f5f9"},
    "INACTIVE": {"label": "Inactive", "tone": "muted", "color": "#475569", "background": "#f1f5f9"},
    "BLOCKED": {"label": "Blocked", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "INVITED": {"label": "Invited", "tone": "info", "color": "#0369a1", "background": "#eff6ff"},
    "HIGH": {"label": "High", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "HIGH_PRIORITY": {"label": "High Priority", "tone": "danger", "color": "#b91c1c", "background": "#fef2f2"},
    "MEDIUM": {"label": "Medium", "tone": "warning", "color": "#b45309", "background": "#fff7ed"},
    "CRITICAL": {"label": "Critical", "tone": "danger", "color": "#7f1d1d", "background": "#fee2e2"},
    "PARTIAL": {"label": "Partial", "tone": "warning", "color": "#b45309", "background": "#fff7ed"},
}


def normalize_status_key(value: Any) -> str:
    return str(value or "DEFAULT").strip().upper().replace(" ", "_")


def get_status_style(value: Any) -> dict[str, str]:
    normalized = normalize_status_key(value)
    return STATUS_STYLES.get(normalized, {"label": str(value or "Unknown"), **STATUS_STYLES["DEFAULT"]})
