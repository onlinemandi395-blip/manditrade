from __future__ import annotations

from datetime import UTC, datetime

import streamlit as st

from services.image_processing_service import ImageProcessingService
from services.id_service import IdService
from services.performance_service import PerformanceService


class MediaService:
    PRODUCTS_MEDIA_PATH = "15_media/products"

    def __init__(self, admin_drive_service) -> None:
        self.admin_drive_service = admin_drive_service
        self.id_service = IdService()
        self.image_processing_service = ImageProcessingService()
        self.performance_service = PerformanceService()

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
