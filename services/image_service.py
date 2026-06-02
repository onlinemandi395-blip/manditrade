from __future__ import annotations

import re
from pathlib import Path
from typing import Any
from urllib.parse import quote

from utils.paths import APP_RUNTIME_DIR


class ImageService:
    VALID_STATUSES = {"NONE", "URL", "UPLOADED", "PLACEHOLDER"}

    def __init__(self, *, uploads_root: Path | None = None) -> None:
        self.uploads_root = uploads_root or (APP_RUNTIME_DIR / "uploads" / "images")

    def normalize_image_metadata(
        self,
        payload: dict[str, Any] | None = None,
        *,
        image_url: str = "",
        image_file_ref: str = "",
        thumbnail_url: str = "",
        image_alt_text: str = "",
        image_status: str = "",
    ) -> dict[str, str]:
        source = dict(payload or {})
        normalized_url = self._sanitize_url(image_url or str(source.get("image_url", "")))
        normalized_file_ref = self._sanitize_file_ref(image_file_ref or str(source.get("image_file_ref", "")))
        normalized_thumbnail = self._sanitize_url(thumbnail_url or str(source.get("thumbnail_url", "")))
        normalized_alt = str(image_alt_text or source.get("image_alt_text", "")).strip()

        status = str(image_status or source.get("image_status", "")).strip().upper()
        if normalized_file_ref:
            status = "UPLOADED"
        elif normalized_url:
            status = "URL"
        elif status not in self.VALID_STATUSES:
            status = "NONE"
        if status == "NONE":
            normalized_thumbnail = normalized_thumbnail or self.get_placeholder_image(normalized_alt or "Catalog image")
        if status == "PLACEHOLDER":
            normalized_thumbnail = self.get_placeholder_image(normalized_alt or "Catalog image")
        return {
            "image_url": normalized_url,
            "image_file_ref": normalized_file_ref,
            "thumbnail_url": normalized_thumbnail,
            "image_alt_text": normalized_alt,
            "image_status": status,
        }

    def get_display_image(self, payload: dict[str, Any] | None, *, label: str = "Catalog image") -> dict[str, str]:
        metadata = self.normalize_image_metadata(payload or {}, image_alt_text=str((payload or {}).get("image_alt_text", "") or label))
        src = metadata["thumbnail_url"] or metadata["image_url"]
        if not src and metadata["image_file_ref"]:
            src = metadata["image_file_ref"]
        if not src:
            src = self.get_placeholder_image(metadata["image_alt_text"] or label)
        return {"src": src, "alt": metadata["image_alt_text"] or label, "status": metadata["image_status"]}

    def get_placeholder_image(self, label: str = "No image") -> str:
        safe_label = re.sub(r"\s+", " ", label.strip() or "No image")
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' width='640' height='480' viewBox='0 0 640 480'>"
            "<defs><linearGradient id='g' x1='0' y1='0' x2='1' y2='1'>"
            "<stop offset='0%' stop-color='%230d2234'/>"
            "<stop offset='100%' stop-color='%231f4a5e'/></linearGradient></defs>"
            "<rect width='640' height='480' fill='url(%23g)'/>"
            "<circle cx='160' cy='140' r='84' fill='rgba(245,158,11,0.24)'/>"
            "<circle cx='500' cy='120' r='76' fill='rgba(56,193,114,0.24)'/>"
            "<rect x='96' y='278' width='448' height='84' rx='18' fill='rgba(255,255,255,0.08)' stroke='rgba(255,255,255,0.12)'/>"
            f"<text x='320' y='326' text-anchor='middle' fill='%23f8fafc' font-size='28' font-family='Arial, sans-serif'>{safe_label}</text>"
            "</svg>"
        )
        return f"data:image/svg+xml;utf8,{quote(svg)}"

    def save_uploaded_image_if_supported(self, uploaded_file, *, folder: str = "catalog") -> str:
        if uploaded_file is None:
            return ""
        safe_name = Path(str(getattr(uploaded_file, "name", "image.bin"))).name
        target = self.uploads_root / folder
        target.mkdir(parents=True, exist_ok=True)
        destination = target / safe_name
        destination.write_bytes(uploaded_file.getbuffer())
        return str(destination)

    def _sanitize_url(self, value: str) -> str:
        normalized = str(value or "").strip()
        if normalized.startswith(("http://", "https://", "data:image/")):
            return normalized
        return ""

    def _sanitize_file_ref(self, value: str) -> str:
        normalized = str(value or "").strip()
        if not normalized:
            return ""
        path = Path(normalized)
        return str(path)
