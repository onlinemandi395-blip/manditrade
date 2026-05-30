from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class ConnectedAccountsService:
    DRIVE_FLOW = "manufacturer_drive_connect"
    GMAIL_FLOW = "manufacturer_gmail_connect"

    def __init__(
        self,
        *,
        drive_service,
        security_service,
        auth_service,
        oauth_callback_service,
        json_service,
        safe_drive_write_service,
    ) -> None:
        self.drive_service = drive_service
        self.security_service = security_service
        self.auth_service = auth_service
        self.oauth_callback_service = oauth_callback_service
        self.json_service = json_service
        self.safe_drive_write_service = safe_drive_write_service

    def _private_zone(self, manufacturer_code: str) -> Path:
        return self.drive_service.get_manufacturer_paths(manufacturer_code).private_zone

    def _tokens_dir(self, manufacturer_code: str) -> Path:
        return self._private_zone(manufacturer_code) / "tokens"

    def _metadata_path(self, manufacturer_code: str) -> Path:
        return self._private_zone(manufacturer_code) / "connected_accounts.json"

    def _default_metadata(self, manufacturer_code: str) -> dict[str, Any]:
        return {
            "manufacturer_id": manufacturer_code,
            "drive": {
                "connected": False,
                "provider": "google_drive",
                "connected_email": "",
                "encrypted_refresh_token_ref": "",
                "scopes": [],
                "connected_at": "",
                "last_validated_at": "",
            },
            "gmail": {
                "connected": False,
                "provider": "platform_gmail",
                "connected_email": "",
                "encrypted_refresh_token_ref": "",
                "scopes": [],
                "connected_at": "",
                "last_validated_at": "",
            },
        }

    def get_metadata(self, manufacturer_code: str) -> dict[str, Any]:
        path = self._metadata_path(manufacturer_code)
        return self.json_service.read_json(path, self._default_metadata(manufacturer_code))

    def get_status(self, manufacturer_code: str) -> dict[str, Any]:
        metadata = self.get_metadata(manufacturer_code)
        gmail = metadata.get("gmail", {}) or {}
        if not gmail.get("connected"):
            gmail["provider"] = "platform_gmail"
        metadata["gmail"] = gmail
        return metadata

    def build_connect_url(self, manufacturer_code: str, provider: str) -> str | None:
        flow_type = self.DRIVE_FLOW if provider == "drive" else self.GMAIL_FLOW
        return self.oauth_callback_service.build_authorization_url(
            flow_type=flow_type,
            role_context="manufacturer",
            manufacturer_id=manufacturer_code,
        )

    def _store_provider_refresh_token(self, manufacturer_code: str, provider: str, refresh_token: str) -> str:
        tokens_dir = self._tokens_dir(manufacturer_code)
        tokens_dir.mkdir(parents=True, exist_ok=True)
        target = tokens_dir / f"google_{provider}.enc"
        self.security_service.encrypt_refresh_token(refresh_token, target=target)
        return str(target)

    def complete_connection(self, *, manufacturer_code: str, provider: str, credentials_payload: dict[str, Any], connected_email: str) -> dict[str, Any]:
        metadata = self.get_metadata(manufacturer_code)
        record = metadata["drive" if provider == "drive" else "gmail"]
        token_ref = self._store_provider_refresh_token(manufacturer_code, provider, credentials_payload["refresh_token"])
        now = datetime.now(UTC).isoformat()
        record.update(
            {
                "connected": True,
                "provider": "google_drive" if provider == "drive" else "google_gmail",
                "connected_email": connected_email.strip().lower(),
                "encrypted_refresh_token_ref": token_ref,
                "scopes": list(credentials_payload.get("scopes", []) or []),
                "connected_at": record.get("connected_at") or now,
                "last_validated_at": now,
            }
        )
        if provider == "gmail":
            record["provider"] = "google_gmail"
        metadata["manufacturer_id"] = manufacturer_code
        self.safe_drive_write_service.replace_document(self._metadata_path(manufacturer_code), metadata)
        return metadata

    def disconnect(self, manufacturer_code: str, provider: str) -> dict[str, Any]:
        metadata = self.get_metadata(manufacturer_code)
        key = "drive" if provider == "drive" else "gmail"
        provider_name = "google_drive" if provider == "drive" else "platform_gmail"
        metadata[key] = {
            "connected": False,
            "provider": provider_name,
            "connected_email": "",
            "encrypted_refresh_token_ref": "",
            "scopes": [],
            "connected_at": "",
            "last_validated_at": "",
        }
        self.safe_drive_write_service.replace_document(self._metadata_path(manufacturer_code), metadata)
        return metadata

    def validate_connected_email(self, manufacturer_code: str, connected_email: str) -> None:
        manufacturer_config = self.json_service.read_json(self._private_zone(manufacturer_code) / "manufacturer_config.json", {})
        owner_email = str(manufacturer_config.get("owner_email") or "").strip().lower()
        if owner_email and owner_email != connected_email.strip().lower():
            raise PermissionError("Connected Google account email does not match the manufacturer owner email.")

    def build_runtime_credentials_payload(self, manufacturer_code: str, provider: str) -> dict[str, Any]:
        metadata = self.get_status(manufacturer_code)
        key = "drive" if provider == "drive" else "gmail"
        token_ref = metadata.get(key, {}).get("encrypted_refresh_token_ref", "")
        if not token_ref:
            raise FileNotFoundError(f"No connected token found for {provider}.")
        refresh_token = self.security_service.decrypt_refresh_token(Path(token_ref))
        return self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)

    def refresh_runtime_credentials(self, manufacturer_code: str, provider: str):
        metadata = self.get_status(manufacturer_code)
        key = "drive" if provider == "drive" else "gmail"
        scopes = metadata.get(key, {}).get("scopes", []) or []
        credentials = self.auth_service.refresh_credentials(self.build_runtime_credentials_payload(manufacturer_code, provider), scopes=scopes)
        metadata[key]["last_validated_at"] = datetime.now(UTC).isoformat()
        self.safe_drive_write_service.replace_document(self._metadata_path(manufacturer_code), metadata)
        return credentials

    def summarize_connections(self, manufacturer_codes: list[str]) -> dict[str, int]:
        connected = 0
        disconnected = 0
        failed = 0
        for manufacturer_code in manufacturer_codes:
            metadata = self.get_status(manufacturer_code)
            if metadata.get("drive", {}).get("connected"):
                connected += 1
                try:
                    self.refresh_runtime_credentials(manufacturer_code, "drive")
                except Exception:
                    failed += 1
            else:
                disconnected += 1
        return {
            "connected_manufacturers_count": connected,
            "disconnected_manufacturers_count": disconnected,
            "failed_token_validations": failed,
        }
