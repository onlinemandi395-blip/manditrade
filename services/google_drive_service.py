from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaInMemoryUpload


class GoogleDriveService:
    SCOPES = [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/gmail.send",
    ]

    def __init__(self, token_store_path: Path | None = None) -> None:
        self.token_store_path = token_store_path

    def build_drive_client_from_user_oauth(self, user_token: dict[str, Any]):
        token_scopes = list(user_token.get("scopes", []) or [])
        creds = Credentials.from_authorized_user_info(user_token, scopes=token_scopes or self.SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if self.token_store_path:
                refreshed = self.serialize_credentials(creds, user_token)
                self.write_token_store(refreshed)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

    def build_gmail_client_from_user_oauth(self, user_token: dict[str, Any]):
        token_scopes = list(user_token.get("scopes", []) or [])
        creds = Credentials.from_authorized_user_info(user_token, scopes=token_scopes or self.SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if self.token_store_path:
                refreshed = self.serialize_credentials(creds, user_token)
                self.write_token_store(refreshed)
        return build("gmail", "v1", credentials=creds, cache_discovery=False)

    def serialize_credentials(self, creds: Credentials, seed: dict[str, Any] | None = None) -> dict[str, Any]:
        payload = dict(seed or {})
        payload.update(
            {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
                "scopes": list(creds.scopes or self.SCOPES),
                "expiry": creds.expiry.isoformat() if creds.expiry else payload.get("expiry", ""),
            }
        )
        return payload

    def find_or_create_folder(self, service, name: str, parent_id: str | None = None) -> dict[str, Any]:
        parent_filter = f"'{parent_id}' in parents and " if parent_id else ""
        query = f"{parent_filter}name = '{name}' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        response = service.files().list(q=query, fields="files(id,name,mimeType,modifiedTime)", spaces="drive", pageSize=1).execute()
        files = response.get("files", [])
        if files:
            return files[0]
        body = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent_id:
            body["parents"] = [parent_id]
        return service.files().create(body=body, fields="id,name,mimeType,modifiedTime").execute()

    def find_child(self, service, parent_id: str, name: str) -> dict[str, Any] | None:
        query = f"'{parent_id}' in parents and name = '{name}' and trashed = false"
        response = service.files().list(
            q=query,
            fields="files(id,name,mimeType,modifiedTime)",
            spaces="drive",
            pageSize=1,
        ).execute()
        files = response.get("files", [])
        return files[0] if files else None

    def resolve_logical_path(self, service, root_folder_id: str, logical_path: str) -> dict[str, Any] | None:
        parts = [part for part in logical_path.split("/") if part]
        if not parts:
            return None
        current_parent = root_folder_id
        current_metadata: dict[str, Any] | None = None
        for part in parts:
            current_metadata = self.find_child(service, current_parent, part)
            if not current_metadata:
                return None
            current_parent = current_metadata["id"]
        return current_metadata

    def read_json_by_path(self, service, root_folder_id: str, logical_path: str) -> dict[str, Any]:
        metadata = self.resolve_logical_path(service, root_folder_id, logical_path)
        if not metadata:
            raise FileNotFoundError(logical_path)
        return self.read_json_file(service, metadata["id"])

    def create_json_file(self, service, folder_id: str, file_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        media = MediaInMemoryUpload(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"), mimetype="application/json", resumable=False)
        body = {"name": file_name, "parents": [folder_id], "mimeType": "application/json"}
        return service.files().create(body=body, media_body=media, fields="id,name,modifiedTime").execute()

    def update_json_file(self, service, file_id: str, payload: dict[str, Any], file_name: str | None = None) -> dict[str, Any]:
        media = MediaInMemoryUpload(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"), mimetype="application/json", resumable=False)
        body: dict[str, Any] = {}
        if file_name:
            body["name"] = file_name
        return service.files().update(
            fileId=file_id,
            body=body or None,
            media_body=media,
            fields="id,name,modifiedTime",
        ).execute()

    def create_binary_file(self, service, folder_id: str, file_name: str, bytes_data: bytes, mime_type: str) -> dict[str, Any]:
        media = MediaInMemoryUpload(bytes_data, mimetype=mime_type, resumable=False)
        body = {"name": file_name, "parents": [folder_id]}
        return service.files().create(
            body=body,
            media_body=media,
            fields="id,name,mimeType,webViewLink,thumbnailLink",
        ).execute()

    def update_binary_file(self, service, file_id: str, bytes_data: bytes, mime_type: str, file_name: str | None = None) -> dict[str, Any]:
        media = MediaInMemoryUpload(bytes_data, mimetype=mime_type, resumable=False)
        body: dict[str, Any] = {}
        if file_name:
            body["name"] = file_name
        return service.files().update(
            fileId=file_id,
            body=body or None,
            media_body=media,
            fields="id,name,mimeType,webViewLink,thumbnailLink",
        ).execute()

    def move_file(self, service, file_id: str, *, new_parent_id: str, old_parent_ids: str = "") -> dict[str, Any]:
        return service.files().update(
            fileId=file_id,
            addParents=new_parent_id,
            removeParents=old_parent_ids,
            fields="id,parents",
        ).execute()

    def find_named_file(self, service, folder_id: str, file_name: str) -> dict[str, Any] | None:
        query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
        response = service.files().list(q=query, fields="files(id,name,modifiedTime)", spaces="drive", pageSize=1).execute()
        files = response.get("files", [])
        return files[0] if files else None

    def list_permissions(self, service, file_id: str) -> list[dict[str, Any]]:
        response = service.permissions().list(
            fileId=file_id,
            fields="permissions(id,emailAddress,role,type)",
            pageSize=100,
        ).execute()
        return list(response.get("permissions", []))

    def ensure_user_permission(self, service, file_id: str, user_email: str, role: str = "writer") -> dict[str, Any]:
        normalized_email = str(user_email or "").strip().lower()
        if not normalized_email:
            raise ValueError("User email is required to assign Drive permission.")
        permissions = self.list_permissions(service, file_id)
        existing = next(
            (
                item for item in permissions
                if str(item.get("emailAddress", "")).strip().lower() == normalized_email
            ),
            None,
        )
        if existing:
            existing_role = str(existing.get("role", "")).strip().lower()
            if existing_role == str(role or "writer").strip().lower():
                return existing
            return service.permissions().update(
                fileId=file_id,
                permissionId=existing["id"],
                body={"role": role},
                fields="id,emailAddress,role,type",
            ).execute()
        return service.permissions().create(
            fileId=file_id,
            sendNotificationEmail=False,
            body={
                "type": "user",
                "role": role,
                "emailAddress": normalized_email,
            },
            fields="id,emailAddress,role,type",
        ).execute()

    def list_children(self, service, folder_id: str, mime_prefix: str | None = None) -> list[dict[str, Any]]:
        query = f"'{folder_id}' in parents and trashed = false"
        if mime_prefix:
            query += f" and mimeType contains '{mime_prefix}'"
        response = service.files().list(
            q=query,
            fields="files(id,name,mimeType,modifiedTime,thumbnailLink,webViewLink)",
            spaces="drive",
            pageSize=100,
        ).execute()
        return list(response.get("files", []))

    def create_or_update_json_file(self, service, folder_id: str, file_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.find_named_file(service, folder_id, file_name)
        if existing:
            return self.update_json_file(service, existing["id"], payload, file_name=file_name)
        return self.create_json_file(service, folder_id, file_name, payload)

    def read_json_file(self, service, file_id: str) -> dict[str, Any]:
        content = service.files().get_media(fileId=file_id).execute()
        return json.loads(content.decode("utf-8"))

    def read_file_bytes(self, service, file_id: str) -> bytes:
        content = service.files().get_media(fileId=file_id).execute()
        return bytes(content)

    def send_gmail_message(self, service, *, sender_email: str, to_email: str, subject: str, body: str) -> dict[str, Any]:
        mime_message = (
            f"From: {sender_email}\r\n"
            f"To: {to_email}\r\n"
            f"Subject: {subject}\r\n"
            "Content-Type: text/plain; charset=utf-8\r\n"
            "\r\n"
            f"{body}"
        ).encode("utf-8")
        encoded_message = base64.urlsafe_b64encode(mime_message).decode("utf-8")
        return service.users().messages().send(userId="me", body={"raw": encoded_message}).execute()

    def read_token_store(self) -> dict[str, Any]:
        if not self.token_store_path or not self.token_store_path.exists():
            return {}
        return json.loads(self.token_store_path.read_text(encoding="utf-8"))

    def write_token_store(self, payload: dict[str, Any]) -> None:
        if not self.token_store_path:
            return
        self.token_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_store_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
