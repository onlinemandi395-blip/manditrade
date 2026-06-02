from __future__ import annotations

import base64
from datetime import UTC, datetime
from email.message import EmailMessage
from pathlib import Path
from typing import Any
import json

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
        id_allocator_service=None,
        drive_path_service=None,
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
        self.id_allocator_service = id_allocator_service
        self.drive_path_service = drive_path_service

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

    def enqueue_message(self, to_email: str, subject: str, body: str, notification_type: str, *, deep_link: str = "", metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.queue_path and self.drive_path_service:
            self.queue_path = self.drive_path_service.get_notification_path("email_queue")
        queue_backed_mode = bool(self.drive_path_service)
        if not queue_backed_mode and self.notification_mode == "live" and self.use_gmail_api:
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
                return {"status": "sent", "id": response.get("id", ""), "to": to_email}
            except Exception as exc:  # noqa: BLE001
                message["status"] = "failed"
                message["failed_at"] = datetime.now(UTC).isoformat()
                message["last_error"] = str(exc)
                if self.dead_letter_service:
                    self.dead_letter_service.record(
                        "gmail_runtime_send_failed",
                        dict(message),
                        str(exc),
                        correlation_id=to_email,
                    )
                return {"status": "failed", "error": str(exc)}
        if not self.queue_path or not self.safe_drive_write_service:
            return {"status": "skipped", "reason": "queue_unavailable"}
        if self.notification_mode == "disabled":
            if self.runtime_metrics_service:
                self.runtime_metrics_service.increment("gmail_suppressed", extra={"notification_type": notification_type})
            return {"status": "disabled", "notification_type": notification_type}

        queue_doc = {"schema_version": "1.0", "emails": []}
        message = {
            "email_id": self.id_allocator_service.allocate("event") if self.id_allocator_service else f"EMAIL-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            "notification_type": notification_type,
            "event_type": notification_type,
            "recipient_email": to_email,
            "subject": subject,
            "body": body,
            "deep_link": deep_link,
            "metadata": metadata or {},
            "status": "QUEUED",
            "retry_count": 0,
            "created_at": datetime.now(UTC).isoformat(),
            "last_error": "",
        }
        if not self.queue_path.exists():
            self.safe_drive_write_service.replace_document(self.queue_path, queue_doc)
        self.safe_drive_write_service.append_record(self.queue_path, "emails", message)
        if self.runtime_metrics_service:
            self.runtime_metrics_service.increment("gmail_queued", extra={"notification_type": notification_type})
        return message

    def read_queue(self) -> list[dict[str, Any]]:
        if not self.queue_path:
            return []
        if not self.queue_path.exists():
            return []
        return self.safe_drive_write_service.json_service.read_json(self.queue_path, {"emails": []}).get("emails", [])

    def process_queue(self, credentials: Any | None = None, max_messages: int = 10) -> int:
        if not self.queue_path:
            return 0
        items = self.read_queue()
        pending = [item for item in items if item.get("status") in {"QUEUED", "RETRY"}][:max_messages]
        processed = 0
        for message in pending:
            try:
                creds = credentials or self._resolve_runtime_credentials()
                if self.notification_mode == "live" and self.use_gmail_api and creds is not None:
                    self.send_message(creds, message["recipient_email"], message["subject"], message["body"])
                    delivery_mode = "live"
                else:
                    delivery_mode = "mock"
                self._write_history({**message, "status": "SENT", "sent_at": datetime.now(UTC).isoformat(), "delivery_mode": delivery_mode})
                self._update_queue_item(message["email_id"], status="SENT", last_error="")
                processed += 1
            except Exception as exc:  # noqa: BLE001
                retry_count = int(message.get("retry_count", 0) or 0) + 1
                failed_status = "FAILED" if retry_count >= 3 else "RETRY"
                self._update_queue_item(message["email_id"], status=failed_status, retry_count=retry_count, last_error=str(exc))
                if failed_status == "FAILED" and self.dead_letter_service:
                    self.dead_letter_service.record("gmail_queue_failed", dict(message), str(exc), correlation_id=message.get("recipient_email", ""))
        return processed

    def list_history(self, year_month: str | None = None) -> list[dict[str, Any]]:
        if not self.drive_path_service:
            return []
        path = self.drive_path_service.get_notification_path("email_history", year_month)
        if not path.exists():
            return []
        return self.safe_drive_write_service.json_service.read_json(path, {"emails": []}).get("emails", [])

    def retry_failed(self, email_id: str) -> dict[str, Any]:
        self._update_queue_item(email_id, status="RETRY", last_error="")
        return next((item for item in self.read_queue() if item.get("email_id") == email_id), {})

    def list_failed_dead_letters(self) -> list[dict[str, Any]]:
        if not self.dead_letter_service:
            return []
        return self.dead_letter_service.list_entries()

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

    def _write_history(self, message: dict[str, Any]) -> None:
        if not self.drive_path_service:
            return
        history_path = self.drive_path_service.get_notification_path("email_history")
        if not history_path.exists():
            self.safe_drive_write_service.replace_document(history_path, {"schema_version": "1.0", "emails": []})
        self.safe_drive_write_service.append_record(history_path, "emails", message)

    def _update_queue_item(self, email_id: str, **updates: Any) -> None:
        if not self.queue_path:
            return

        def mutator(payload: dict[str, Any]) -> dict[str, Any]:
            found = False
            for item in payload.get("emails", []):
                if item.get("email_id") == email_id:
                    item.update(updates)
                    found = True
                    break
            if not found:
                raise ValueError(f"Queued email not found: {email_id}")
            return payload

        self.safe_drive_write_service.mutate_json(self.queue_path, mutator)
