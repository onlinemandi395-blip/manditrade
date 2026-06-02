from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class FavoritesService:
    def __init__(self, *, favorites_root: Path, safe_drive_write_service, json_service, id_allocator_service) -> None:
        self.favorites_root = favorites_root
        self.safe_drive_write_service = safe_drive_write_service
        self.json_service = json_service
        self.id_allocator_service = id_allocator_service

    def list_favorites(self, owner_role: str, owner_id: str) -> list[dict[str, Any]]:
        path = self._path(owner_role, owner_id)
        if not path.exists():
            return []
        payload = self.json_service.read_json(path, self._default_doc(owner_role, owner_id))
        return payload.get("favorites", [])

    def save_favorite(
        self,
        owner_role: str,
        owner_id: str,
        *,
        item_type: str,
        item_id: str,
        title: str,
        subtitle: str = "",
        image_url: str = "",
    ) -> dict[str, Any]:
        if owner_role not in {"public_buyer", "manufacturer", "admin_as_manufacturer"}:
            raise PermissionError("Favorites are available only for public buyers and manufacturers.")
        path = self._path(owner_role, owner_id)
        if not path.exists():
            self.safe_drive_write_service.replace_document(path, self._default_doc(owner_role, owner_id))
        favorite: dict[str, Any] | None = None

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            nonlocal favorite
            payload.setdefault("favorites", [])
            existing = next(
                (
                    item
                    for item in payload["favorites"]
                    if item.get("item_type") == item_type and item.get("item_id") == item_id
                ),
                None,
            )
            if existing:
                existing.update(
                    {
                        "title": title,
                        "subtitle": subtitle,
                        "image_url": image_url,
                        "updated_at": datetime.now(UTC).isoformat(),
                    }
                )
                favorite = dict(existing)
                return payload
            favorite = {
                "favorite_id": self.id_allocator_service.allocate("favorite"),
                "owner_role": owner_role,
                "owner_id": owner_id,
                "item_type": item_type,
                "item_id": item_id,
                "title": title,
                "subtitle": subtitle,
                "image_url": image_url,
                "created_at": datetime.now(UTC).isoformat(),
                "updated_at": datetime.now(UTC).isoformat(),
            }
            payload["favorites"].append(favorite)
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return favorite or {}

    def remove_favorite(self, owner_role: str, owner_id: str, *, item_type: str, item_id: str) -> list[dict[str, Any]]:
        path = self._path(owner_role, owner_id)
        if not path.exists():
            return []

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            payload["favorites"] = [
                item
                for item in payload.get("favorites", [])
                if not (item.get("item_type") == item_type and item.get("item_id") == item_id)
            ]
            return payload

        self.safe_drive_write_service.mutate_json(path, mutator)
        return self.list_favorites(owner_role, owner_id)

    def _path(self, owner_role: str, owner_id: str) -> Path:
        return self.favorites_root / owner_role / owner_id / "favorites.json"

    def _default_doc(self, owner_role: str, owner_id: str) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "owner_role": owner_role,
            "owner_id": owner_id,
            "favorites": [],
        }
