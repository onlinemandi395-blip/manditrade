from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from dataclasses import replace

import streamlit as st

from constants.roles import ADMIN_BASE_ROLES, ROLE_ADMIN_AS_MANUFACTURER, ROLE_PLATFORM_ADMIN, ROLE_PUBLIC_BUYER, ROLE_WORKER, normalize_runtime_role
from services.auth_service import AuthService, AuthUser
from services.encryption_service import EncryptionService
from services.json_service import JsonService


class SecurityService:
    PLACEHOLDER_ADMIN_TOKEN = "REPLACE_WITH_ENCRYPTED_ADMIN_REFRESH_TOKEN"
    ADMIN_MANUFACTURER_CODE = "ADMIN_MANU"

    def __init__(
        self,
        encryption_service: EncryptionService,
        auth_service: AuthService,
        admin_token_file: Path,
        manufacturer_token_dir: Path,
        runtime_tokens_dir: Path,
        require_verification_for_admin_runtime: bool = True,
    ) -> None:
        self.encryption_service = encryption_service
        self.auth_service = auth_service
        self.admin_token_file = admin_token_file
        self.manufacturer_token_dir = manufacturer_token_dir
        self.runtime_tokens_dir = runtime_tokens_dir
        self.require_verification_for_admin_runtime = require_verification_for_admin_runtime
        self.json_service = JsonService()

    def load_streamlit_secrets(self) -> dict[str, Any]:
        secrets = {}
        for section in ("security", "google", "admin", "admin_token", "google_drive"):
            if section in st.secrets:
                secrets[section] = dict(st.secrets[section])
        return secrets

    def get_public_verification_key(self) -> str | None:
        return self.load_streamlit_secrets().get("security", {}).get("public_verification_key")

    def get_streamlit_google_config(self) -> dict[str, str]:
        return self.load_streamlit_secrets().get("google", {})

    def get_admin_email(self) -> str | None:
        return self.load_streamlit_secrets().get("admin", {}).get("admin_email")

    def get_admin_refresh_token_plain(self) -> str | None:
        secrets = self.load_streamlit_secrets()
        admin_token_section = secrets.get("admin_token", {})
        admin_section = secrets.get("admin", {})
        google_drive_section = secrets.get("google_drive", {})
        return (
            admin_token_section.get("refresh_token")
            or admin_token_section.get("admin_refresh_token")
            or admin_section.get("admin_refresh_token")
            or google_drive_section.get("admin_refresh_token")
        )

    def get_admin_token_secret(self) -> str | None:
        secrets = self.load_streamlit_secrets()
        admin_token_section = secrets.get("admin_token", {})
        admin_section = secrets.get("admin", {})
        google_drive_section = secrets.get("google_drive", {})
        return (
            admin_token_section.get("encrypted_token")
            or admin_token_section.get("encrypted_admin_refresh_token")
            or admin_section.get("encrypted_admin_refresh_token")
            or admin_section.get("admin_refresh_token_encrypted")
            or google_drive_section.get("encrypted_admin_refresh_token")
        )

    def is_admin_identity(self, user: AuthUser | None) -> bool:
        if not user:
            return False
        expected_email = (self.get_admin_email() or "").strip().lower()
        return bool(
            self.get_base_role(user) in ADMIN_BASE_ROLES
            or (expected_email and user.email.strip().lower() == expected_email)
        )

    def get_base_role(self, user: AuthUser | None) -> str:
        if not user:
            return ""
        return str(getattr(user, "base_role", None) or user.role or "").strip().lower()

    def get_active_context(self, user: AuthUser | None) -> str:
        if not user:
            return ""
        base_role = self.get_base_role(user)
        active_context = str(getattr(user, "active_context", None) or "").strip().lower()
        if self.is_admin_identity(user):
            return active_context or ROLE_PLATFORM_ADMIN
        if base_role == ROLE_ADMIN_AS_MANUFACTURER:
            return normalize_runtime_role(base_role)
        return active_context or base_role

    def build_effective_user(self, user: AuthUser | None) -> AuthUser | None:
        if not user:
            return None
        base_role = self.get_base_role(user)
        active_context = self.get_active_context(user)
        if not self.is_admin_identity(user):
            if user.base_role is None or user.active_context is None:
                return replace(user, base_role=base_role, active_context=active_context)
            return user
        effective_role = ROLE_PLATFORM_ADMIN if active_context in {"", ROLE_PLATFORM_ADMIN, "superuser"} else active_context
        manufacturer_code = user.manufacturer_code
        if active_context == normalize_runtime_role("manufacturer"):
            manufacturer_code = self.ADMIN_MANUFACTURER_CODE
        elif active_context in {ROLE_PUBLIC_BUYER, ROLE_WORKER, ROLE_PLATFORM_ADMIN}:
            manufacturer_code = None
        return replace(
            user,
            role=effective_role,
            base_role=base_role or ROLE_PLATFORM_ADMIN,
            active_context=active_context or ROLE_PLATFORM_ADMIN,
            manufacturer_code=manufacturer_code,
        )

    @property
    def admin_vault_path(self) -> Path:
        return self.runtime_tokens_dir.parent / "admin_vault.json"

    def read_admin_vault(self) -> dict[str, Any]:
        return self.json_service.read_json(self.admin_vault_path, {})

    def admin_vault_ready(self) -> bool:
        vault = self.read_admin_vault()
        return bool(vault.get("initialized") and vault.get("admin_email"))

    def initialize_admin_vault(self, user: AuthUser, verification_key: str) -> Path:
        payload = {
            "initialized": True,
            "admin_email": user.email.strip().lower(),
            "verification_key_encrypted": self.encryption_service.encrypt(verification_key.strip()),
            "initialized_at": datetime.now(UTC).isoformat(),
        }
        self.admin_vault_path.parent.mkdir(parents=True, exist_ok=True)
        self.admin_vault_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return self.admin_vault_path

    def admin_vault_matches_user(self, user: AuthUser | None) -> bool:
        if not user:
            return False
        vault = self.read_admin_vault()
        return bool(vault.get("initialized") and vault.get("admin_email", "").strip().lower() == user.email.strip().lower())

    def verification_is_configured(self) -> bool:
        return bool(self.get_public_verification_key() and self.get_admin_email())

    def validate_admin_runtime_request(self, user: AuthUser | None, submitted_key: str) -> tuple[bool, str]:
        if not user:
            return False, "Sign in before requesting admin runtime access."
        if self.get_base_role(user) not in ADMIN_BASE_ROLES:
            return False, "Only admin users can unlock admin runtime access."

        expected_email = self.get_admin_email()
        if not expected_email:
            return False, "Admin email is not configured in Streamlit secrets."
        if user.email.strip().lower() != expected_email.strip().lower():
            return False, "Signed-in email is not authorized for admin Drive runtime access."

        if self.admin_vault_matches_user(user):
            return True, "Admin runtime validation succeeded through vault."

        if self.require_verification_for_admin_runtime:
            expected_key = self.get_public_verification_key()
            if not expected_key:
                return False, "Public verification key is not configured in Streamlit secrets."
            if submitted_key.strip() != expected_key.strip():
                return False, "Verification key did not match the deployed verification layer."
        return True, "Admin runtime validation succeeded."

    def encrypt_refresh_token(self, refresh_token: str, target: Path | None = None) -> Path:
        output = target or self.admin_token_file
        self.encryption_service.encrypt_to_file(output, refresh_token)
        return output

    def decrypt_refresh_token(self, source: Path | None = None) -> str:
        token_file = source or self.admin_token_file
        if source is None:
            plain_refresh_token = self.get_admin_refresh_token_plain()
            if plain_refresh_token and plain_refresh_token.strip():
                return plain_refresh_token.strip()
            secret_token = self.get_admin_token_secret()
            if secret_token and secret_token.strip() != self.PLACEHOLDER_ADMIN_TOKEN:
                return self.encryption_service.decrypt(secret_token.strip())
        if not token_file.exists():
            raise FileNotFoundError(f"Encrypted token file not found: {token_file}")
        return self.encryption_service.decrypt_from_file(token_file)

    def admin_token_exists(self) -> bool:
        plain_refresh_token = self.get_admin_refresh_token_plain()
        secret_token = self.get_admin_token_secret()
        return bool(plain_refresh_token and plain_refresh_token.strip()) or bool(secret_token and secret_token.strip()) or self.admin_token_file.exists()

    def admin_token_is_placeholder(self) -> bool:
        plain_refresh_token = self.get_admin_refresh_token_plain()
        if plain_refresh_token and plain_refresh_token.strip():
            return plain_refresh_token.strip() == self.PLACEHOLDER_ADMIN_TOKEN
        secret_token = self.get_admin_token_secret()
        if secret_token and secret_token.strip():
            return secret_token.strip() == self.PLACEHOLDER_ADMIN_TOKEN
        if not self.admin_token_file.exists():
            return False
        return self.admin_token_file.read_text(encoding="utf-8").strip() == self.PLACEHOLDER_ADMIN_TOKEN

    def admin_token_ready(self) -> bool:
        return self.admin_token_exists() and not self.admin_token_is_placeholder()

    def restore_runtime_refresh_token(self, principal_key: str) -> str:
        token_file = self.runtime_tokens_dir / f"{principal_key}.enc"
        return self.decrypt_refresh_token(token_file)

    def build_runtime_credentials_payload(
        self,
        refresh_token: str,
        access_token: str = "",
        token_uri: str | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
    ) -> dict[str, Any]:
        google_cfg = self.get_streamlit_google_config()
        return {
            "refresh_token": refresh_token,
            "token": access_token,
            "token_uri": token_uri or google_cfg.get("token_uri", "https://oauth2.googleapis.com/token"),
            "client_id": client_id or google_cfg.get("client_id", ""),
            "client_secret": client_secret or google_cfg.get("client_secret", ""),
        }

    def unlock_admin_runtime(self, user: AuthUser, submitted_key: str) -> dict[str, Any]:
        valid, message = self.validate_admin_runtime_request(user, submitted_key)
        if not valid:
            raise PermissionError(message)
        if not self.admin_token_ready():
            raise PermissionError("Long-lived admin runtime mode is not provisioned yet. Run the admin token provisioning step first.")
        if submitted_key.strip() and not self.admin_vault_matches_user(user):
            self.initialize_admin_vault(user, submitted_key)

        refresh_token = self.decrypt_refresh_token(self.admin_token_file)
        credentials_payload = self.build_runtime_credentials_payload(refresh_token=refresh_token)
        credentials = self.auth_service.refresh_credentials(credentials_payload)
        runtime_state = {
            "principal": user.email,
            "role": user.role,
            "scope": "admin_drive_runtime",
            "access_token_present": bool(credentials.token),
            "vault_enabled": self.admin_vault_matches_user(user),
        }
        st.session_state["auth_tokens"] = {
            "role": user.role,
            "principal": user.email,
            "scope": "admin_drive_runtime",
        }
        st.session_state["admin_runtime_unlocked"] = True
        st.session_state["runtime_drive_access"] = runtime_state
        return runtime_state

    def revoke_runtime_session(self) -> None:
        st.session_state["auth_tokens"] = None
        st.session_state["runtime_drive_access"] = None
        st.session_state["admin_runtime_unlocked"] = False

    def store_manufacturer_token_reference(self, manufacturer_code: str, encrypted_refresh_token: str) -> Path:
        self.manufacturer_token_dir.mkdir(parents=True, exist_ok=True)
        target = self.manufacturer_token_dir / f"{manufacturer_code.lower()}.json"
        target.write_text(
            json.dumps(
                {
                    "manufacturer_code": manufacturer_code,
                    "encrypted_refresh_token": encrypted_refresh_token,
                }
            ),
            encoding="utf-8",
        )
        return target

    def read_manufacturer_token_reference(self, manufacturer_code: str) -> dict[str, Any]:
        target = self.manufacturer_token_dir / f"{manufacturer_code.lower()}.json"
        return self.json_service.read_json(target, {})

    def export_security_status(self) -> dict[str, Any]:
        google_cfg = self.get_streamlit_google_config()
        return {
            "verification_configured": self.verification_is_configured(),
            "admin_token_file_present": self.admin_token_file.exists(),
            "admin_plain_refresh_token_present": bool((self.get_admin_refresh_token_plain() or "").strip()),
            "admin_token_secret_present": bool((self.get_admin_token_secret() or "").strip()),
            "admin_token_placeholder": self.admin_token_is_placeholder(),
            "admin_token_ready": self.admin_token_ready(),
            "admin_vault_ready": self.admin_vault_ready(),
            "manufacturer_token_dir": str(self.manufacturer_token_dir),
            "runtime_tokens_dir": str(self.runtime_tokens_dir),
            "oauth_configured": bool(google_cfg.get("client_id") and google_cfg.get("client_secret") and google_cfg.get("redirect_uri")),
        }

    def validate_drive_session(self, role: str, actor_manufacturer_code: str | None, target_manufacturer_code: str) -> None:
        if role == "admin":
            raise PermissionError("Admin cannot access manufacturer private zones.")
        if actor_manufacturer_code != target_manufacturer_code:
            raise PermissionError("Cross-manufacturer private zone access is not allowed.")

    def session_expired(self, last_seen_epoch: float | None, timeout_minutes: int) -> bool:
        if last_seen_epoch is None:
            return False
        import time

        return (time.time() - last_seen_epoch) > (timeout_minutes * 60)
