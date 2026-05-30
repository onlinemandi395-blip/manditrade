from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any

from googleapiclient.discovery import build


class GmailService:
    def __init__(
        self,
        sender_email: str,
        use_gmail_api: bool = False,
        queue_path=None,
        safe_drive_write_service=None,
        dead_letter_service=None,
        logging_service=None,
        runtime_metrics_service=None,
        notification_mode: str | None = None,
        auth_service=None,
        security_service=None,
    ) -> None:
        self.sender_email = sender_email
        self.use_gmail_api = use_gmail_api
        self.notification_mode = notification_mode or ("live" if use_gmail_api else "mock")
        self.queue_path = queue_path
        self.safe_drive_write_service = safe_drive_write_service
        self.dead_letter_service = dead_letter_service
        self.logging_service = logging_service
        self.runtime_metrics_service = runtime_metrics_service
        self.auth_service = auth_service
        self.security_service = security_service

    def describe_mode(self) -> str:
        return self.notification_mode

    def notifications_enabled(self) -> bool:
        return self.notification_mode != "disabled"

    def build_message(self, to_email: str, subject: str, body: str) -> dict[str, str]:
        message = EmailMessage()
        message["To"] = to_email
        message["From"] = self.sender_email
        message["Subject"] = subject
        message.set_content(body)
        html_body = f"<html><body><div style='font-family:Arial,sans-serif;line-height:1.6;'><p>{body}</p></div></body></html>"
        message.add_alternative(html_body, subtype="html")
        encoded = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")
        return {"raw": encoded}

    def send_message(self, credentials: Any, to_email: str, subject: str, body: str, force_live: bool = False) -> dict[str, Any]:
        payload = self.build_message(to_email, subject, body)
        if self.notification_mode == "disabled" and not force_live:
            return {"status": "disabled", "to": to_email, "subject": subject}
        if (self.notification_mode != "live" or not self.use_gmail_api) and not force_live:
            return {"status": "mocked", "to": to_email, "subject": subject}
        service = build("gmail", "v1", credentials=credentials)
        return service.users().messages().send(userId="me", body=payload).execute()

    def enqueue_message(self, to_email: str, subject: str, body: str, notification_type: str) -> None:
        if self.notification_mode == "disabled":
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("gmail_suppressed", extra={"notification_type": notification_type})
            return
        if self.notification_mode != "live" or not self.use_gmail_api:
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("gmail_mocked", extra={"notification_type": notification_type})
            if self.logging_service:
                self.logging_service.log_info(
                    "notification_runtime",
                    "Gmail notification mocked because live runtime is unavailable",
                    {"to_email": to_email, "notification_type": notification_type},
                )
            return

        message = {
            "notification_type": notification_type,
            "to_email": to_email,
            "subject": subject,
            "body": body,
            "status": "runtime_pending",
            "attempted_at": datetime.now(UTC).isoformat(),
        }
        try:
            credentials = self._resolve_runtime_credentials()
            if credentials is None:
                raise ValueError("No runtime Google credentials are available for Gmail send.")
            response = self.send_message(credentials, to_email, subject, body)
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("gmail_sent", extra={"notification_type": notification_type, "delivery_mode": "runtime"})
            if self.logging_service:
                self.logging_service.log_info(
                    "notification_runtime",
                    "Gmail notification sent immediately",
                    {"to_email": to_email, "notification_type": notification_type, "gmail_id": response.get("id", "")},
                )
        except Exception as exc:  # noqa: BLE001
            message["status"] = "failed"
            message["failed_at"] = datetime.now(UTC).isoformat()
            message["last_error"] = str(exc)
            if self.logging_service:
                self.logging_service.log_error(
                    "notification_failures",
                    "Immediate Gmail send failed without queue fallback",
                    {"message": dict(message), "error": str(exc)},
                )
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("gmail_runtime_send_failed", extra={"notification_type": notification_type})
            if self.dead_letter_service:
                self.dead_letter_service.record(
                    "gmail_runtime_send_failed",
                    dict(message),
                    str(exc),
                    correlation_id=to_email,
                )

    def read_queue(self) -> list[dict[str, Any]]:
        return []

    def process_queue(self, credentials: Any | None = None, max_messages: int = 10) -> int:
        return 0

    def _resolve_runtime_credentials(self) -> Any | None:
        if not self.auth_service or not self.security_service:
            return None
        try:
            import streamlit as st

            auth_tokens = st.session_state.get("auth_tokens") or {}
            token_file = auth_tokens.get("token_file")
            if token_file:
                refresh_token = self.security_service.decrypt_refresh_token(Path(token_file))
                payload = self.security_service.build_runtime_credentials_payload(refresh_token=refresh_token)
                return self.auth_service.refresh_credentials(payload)
        except Exception:
            return None
        return None
