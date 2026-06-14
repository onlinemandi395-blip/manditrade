from __future__ import annotations

from datetime import UTC, datetime


class GmailDeliveryService:
    def __init__(self, data_service) -> None:
        self.data_service = data_service
        self.admin_drive_service = data_service.admin_drive_service
        self.google_drive_service = self.admin_drive_service.google_drive_service

    def can_send(self) -> tuple[bool, str]:
        status = self.admin_drive_service.get_status()
        if not status.get("connected", False):
            return False, "Admin Google OAuth token is not connected."
        if status.get("gmail_send_scope", "missing") != "available":
            return False, "gmail.send scope is missing from the admin OAuth token."
        return True, ""

    def _sender_email(self) -> str:
        token = self.admin_drive_service._get_user_token()  # noqa: SLF001
        token_email = str(token.get("email", "") or "").strip().lower()
        return token_email or "me"

    def process_queue(self, *, limit: int = 25) -> dict:
        can_send, reason = self.can_send()
        if not can_send:
            raise ValueError(reason)
        sender_email = self._sender_email()
        gmail_service = self.google_drive_service.build_gmail_client_from_user_oauth(
            self.admin_drive_service._get_user_token()  # noqa: SLF001
        )
        queue = self.data_service.get_collection_ref("gmail_queue")
        pending_rows = [
            row for row in queue
            if str(row.get("status", "QUEUED")).strip().upper() in {"QUEUED", "RETRY"}
        ][: max(1, int(limit or 25))]
        sent = 0
        failed = 0
        for row in pending_rows:
            row["attempt_count"] = int(row.get("attempt_count", 0) or 0) + 1
            row["last_attempt_at"] = datetime.now(UTC).isoformat()
            try:
                message = self.google_drive_service.send_gmail_message(
                    gmail_service,
                    sender_email=sender_email,
                    to_email=str(row.get("to_email", "")).strip(),
                    subject=str(row.get("subject", "")).strip(),
                    body=str(row.get("body", "")).strip(),
                )
                row["status"] = "SENT"
                row["sent_at"] = datetime.now(UTC).isoformat()
                row["message_id"] = str(message.get("id", "")).strip()
                row["sender_email"] = sender_email
                row["last_error"] = ""
                sent += 1
            except Exception as exc:
                row["status"] = "FAILED"
                row["failed_at"] = datetime.now(UTC).isoformat()
                row["sender_email"] = sender_email
                row["last_error"] = str(exc)
                failed += 1
        if pending_rows:
            self.data_service.persist_collection("gmail_queue")
        return {
            "processed": len(pending_rows),
            "sent": sent,
            "failed": failed,
            "sender_email": sender_email,
        }
