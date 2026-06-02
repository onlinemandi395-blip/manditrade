from __future__ import annotations

from typing import Any, Iterable

from utils.filtering import filter_records


class QueryEngine:
    def query(
        self,
        rows: Iterable[dict[str, Any]],
        *,
        search_query: str = "",
        search_fields: list[str] | None = None,
        status_field: str = "status",
        status_value: str = "All",
        date_field: str = "",
        date_from=None,
        date_to=None,
        price_field: str = "",
        min_price=None,
        max_price=None,
        sort_by: str = "",
        descending: bool = False,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        filtered = filter_records(
            rows,
            search_query=search_query,
            search_fields=search_fields,
            status_field=status_field,
            status_value=status_value,
            date_field=date_field,
            date_from=date_from,
            date_to=date_to,
            price_field=price_field,
            min_price=min_price,
            max_price=max_price,
        )
        if sort_by:
            filtered = sorted(filtered, key=lambda item: str(item.get(sort_by, "")), reverse=descending)
        total = len(filtered)
        start = max((page - 1) * page_size, 0)
        end = start + page_size
        return {
            "rows": filtered[start:end],
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max((total + page_size - 1) // page_size, 1),
        }
