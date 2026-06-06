from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from services.image_processing_service import ImageProcessingService
from services.id_service import IdService
from services.performance_service import PerformanceService


class MediaService:
    PRODUCTS_MEDIA_PATH = "15_media/products"
    IMAGE_CACHE_KEY = "image_cache"

    def __init__(self, admin_drive_service) -> None:
        self.admin_drive_service = admin_drive_service
        self.id_service = IdService()
        self.image_processing_service = ImageProcessingService()
        self.performance_service = PerformanceService()
        st.session_state.setdefault(self.IMAGE_CACHE_KEY, {})

    def upload_product_images(self, uploaded_files: list, *, uploaded_by: str, product_code: str) -> list[dict]:
        if not uploaded_files:
            return []
        resolver = self.admin_drive_service.get_path_resolver()
        folder = resolver.ensure_folder_path(self.PRODUCTS_MEDIA_PATH)
        images = []
        with self.performance_service.measure("image_upload"):
            for index, uploaded_file in enumerate(uploaded_files):
                image_id = self.id_service.next_drive_id(self.admin_drive_service, "image", "IMG")
                st.caption(f"Processing image {index + 1} of {len(uploaded_files)}")
                file_name = f"{product_code}_{image_id}.jpg"
                processed_bytes = self.image_processing_service.process_product_image(uploaded_file)
                created = resolver.google_drive_service.create_binary_file(
                    resolver.service,
                    folder["folder_id"],
                    file_name,
                    processed_bytes,
                    "image/jpeg",
                )
                try:
                    resolver.service.permissions().create(
                        fileId=created["id"],
                        body={"type": "anyone", "role": "reader"},
                    ).execute()
                except Exception:
                    pass
                images.append(
                    {
                        "image_id": image_id,
                        "file_id": created.get("id", ""),
                        "file_name": created.get("name", file_name),
                        "mime_type": created.get("mimeType", "image/jpeg"),
                        "web_view_link": created.get("webViewLink", f"https://drive.google.com/file/d/{created.get('id', '')}/view"),
                        "web_content_link": f"https://drive.google.com/uc?export=download&id={created.get('id', '')}",
                        "thumbnail_link": created.get("thumbnailLink", ""),
                        "direct_render_url": f"https://drive.google.com/uc?export=view&id={created.get('id', '')}",
                        "image_url": f"https://drive.google.com/uc?export=view&id={created.get('id', '')}",
                        "is_primary": index == 0,
                        "processed": True,
                        "size": "800x800",
                        "watermark": "MandiTrade",
                        "uploaded_at": datetime.now(UTC).isoformat(),
                        "uploaded_by": uploaded_by,
                    }
                )
        return images

    def get_renderable_image(self, product_image_metadata: dict | None) -> dict:
        image = dict(product_image_metadata or {})
        file_id = str(image.get("file_id", "")).strip()
        image_cache = st.session_state.get(self.IMAGE_CACHE_KEY, {})
        if file_id and file_id in image_cache:
            return {
                "render_mode": "bytes",
                "bytes": image_cache[file_id],
                "url": "",
                "error": "",
            }
        if file_id:
            try:
                service = self.admin_drive_service.build_client()
                with self.performance_service.measure("image_download"):
                    image_bytes = self.admin_drive_service.google_drive_service.read_file_bytes(service, file_id)
                image_cache[file_id] = image_bytes
                st.session_state[self.IMAGE_CACHE_KEY] = image_cache
                return {
                    "render_mode": "bytes",
                    "bytes": image_bytes,
                    "url": "",
                    "error": "",
                }
            except Exception as exc:
                url = str(
                    image.get("direct_render_url", "")
                    or image.get("thumbnail_link", "")
                    or image.get("web_content_link", "")
                    or ""
                ).strip()
                if url:
                    return {
                        "render_mode": "url",
                        "bytes": None,
                        "url": url,
                        "error": str(exc),
                    }
                return {
                    "render_mode": "placeholder",
                    "bytes": None,
                    "url": "",
                    "error": str(exc),
                }
        url = str(
            image.get("direct_render_url", "")
            or image.get("thumbnail_link", "")
            or image.get("web_content_link", "")
            or ""
        ).strip()
        if url:
            return {
                "render_mode": "url",
                "bytes": None,
                "url": url,
                "error": "",
            }
        return {
            "render_mode": "placeholder",
            "bytes": None,
            "url": "",
            "error": "",
        }
