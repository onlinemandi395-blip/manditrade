from __future__ import annotations

from datetime import UTC, datetime

from googleapiclient.http import MediaInMemoryUpload

from services.id_service import IdService


class MediaService:
    PRODUCTS_MEDIA_PATH = "15_media/products"

    def __init__(self, admin_drive_service) -> None:
        self.admin_drive_service = admin_drive_service
        self.id_service = IdService()

    def upload_product_images(self, uploaded_files: list, *, uploaded_by: str) -> list[dict]:
        if not uploaded_files:
            return []
        resolver = self.admin_drive_service.get_path_resolver()
        folder = resolver.ensure_folder_path(self.PRODUCTS_MEDIA_PATH)
        images = []
        for index, uploaded_file in enumerate(uploaded_files):
            image_id = self.id_service.next_drive_id(self.admin_drive_service, "image", "IMG")
            file_name = uploaded_file.name or f"{image_id}.bin"
            media = MediaInMemoryUpload(
                uploaded_file.getvalue(),
                mimetype=getattr(uploaded_file, "type", None) or "application/octet-stream",
                resumable=False,
            )
            body = {"name": file_name, "parents": [folder["folder_id"]]}
            created = resolver.service.files().create(
                body=body,
                media_body=media,
                fields="id,name,mimeType,webViewLink,thumbnailLink",
            ).execute()
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
                    "mime_type": created.get("mimeType", getattr(uploaded_file, "type", "")),
                    "web_view_link": created.get("webViewLink", f"https://drive.google.com/file/d/{created.get('id', '')}/view"),
                    "thumbnail_link": created.get("thumbnailLink", ""),
                    "image_url": f"https://drive.google.com/uc?export=view&id={created.get('id', '')}",
                    "is_primary": index == 0,
                    "uploaded_at": datetime.now(UTC).isoformat(),
                    "uploaded_by": uploaded_by,
                }
            )
        return images
