from __future__ import annotations

from datetime import date, datetime
from typing import Any, Iterable


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, dict):
        return " ".join(_normalize_text(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return " ".join(_normalize_text(item) for item in value)
    return str(value)


def _parse_date(value: Any) -> date | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None


def _coerce_float(value: Any) -> float | None:
    if value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def collect_status_options(records: Iterable[dict[str, Any]], *, status_field: str = "status") -> list[str]:
    options = sorted(
        {
            str(item.get(status_field) or "").strip()
            for item in records
            if str(item.get(status_field) or "").strip()
        }
    )
    return ["All"] + options


def filter_records(
    records: Iterable[dict[str, Any]],
    *,
    search_query: str = "",
    search_fields: list[str] | None = None,
    status_field: str = "status",
    status_value: str = "All",
    date_field: str = "",
    date_from: date | None = None,
    date_to: date | None = None,
    price_field: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
) -> list[dict[str, Any]]:
    rows = list(records)
    normalized_query = search_query.strip().lower()
    filtered: list[dict[str, Any]] = []
    for row in rows:
        if normalized_query:
            haystack = " ".join(_normalize_text(row.get(field)) for field in (search_fields or row.keys())).lower()
            if normalized_query not in haystack:
                continue
        if status_value and status_value != "All":
            if str(row.get(status_field) or "").strip() != status_value:
                continue
        if date_field:
            row_date = _parse_date(row.get(date_field))
            if date_from and (row_date is None or row_date < date_from):
                continue
            if date_to and (row_date is None or row_date > date_to):
                continue
        if price_field:
            row_price = _coerce_float(row.get(price_field))
            if min_price is not None and (row_price is None or row_price < min_price):
                continue
            if max_price is not None and (row_price is None or row_price > max_price):
                continue
        filtered.append(row)
    return filtered
