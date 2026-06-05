from __future__ import annotations


class GmailQueueService:
    def enqueue(self, *, to_email: str, subject: str, body: str) -> dict:
        return {"to_email": to_email, "subject": subject, "body": body, "status": "QUEUED"}
