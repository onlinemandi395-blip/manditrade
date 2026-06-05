from __future__ import annotations

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
        creds = Credentials.from_authorized_user_info(user_token, scopes=self.SCOPES)
        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            if self.token_store_path:
                refreshed = self.serialize_credentials(creds, user_token)
                self.write_token_store(refreshed)
        return build("drive", "v3", credentials=creds, cache_discovery=False)

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

    def create_or_update_json_file(self, service, folder_id: str, file_name: str, payload: dict[str, Any]) -> dict[str, Any]:
        query = f"'{folder_id}' in parents and name = '{file_name}' and trashed = false"
        response = service.files().list(q=query, fields="files(id,name,modifiedTime)", spaces="drive", pageSize=1).execute()
        files = response.get("files", [])
        media = MediaInMemoryUpload(json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8"), mimetype="application/json", resumable=False)
        body = {"name": file_name, "parents": [folder_id], "mimeType": "application/json"}
        if files:
            return service.files().update(fileId=files[0]["id"], body=body, media_body=media, fields="id,name,modifiedTime").execute()
        return service.files().create(body=body, media_body=media, fields="id,name,modifiedTime").execute()

    def read_json_file(self, service, file_id: str) -> dict[str, Any]:
        content = service.files().get_media(fileId=file_id).execute()
        return json.loads(content.decode("utf-8"))

    def read_token_store(self) -> dict[str, Any]:
        if not self.token_store_path or not self.token_store_path.exists():
            return {}
        return json.loads(self.token_store_path.read_text(encoding="utf-8"))

    def write_token_store(self, payload: dict[str, Any]) -> None:
        if not self.token_store_path:
            return
        self.token_store_path.parent.mkdir(parents=True, exist_ok=True)
        self.token_store_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
