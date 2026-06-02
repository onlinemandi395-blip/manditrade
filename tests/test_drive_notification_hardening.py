from __future__ import annotations

from pathlib import Path

from services.dead_letter_service import DeadLetterService
from services.drive_path_service import DrivePathService
from services.event_notification_service import EventNotificationService
from services.file_lock_service import FileLockService
from services.gmail_service import GmailService
from services.id_allocator_service import IdAllocatorService
from services.notification_center_service import NotificationCenterService
from services.public_buyer_service import PublicBuyerService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from tests.helpers.failure_injector import LoggingStub
from tests.helpers.fake_storage import JsonServiceStub
from tests.test_product_images_cart import build_stack, seed_public_product


def _shared_stack(tmp_path: Path):
    json_service = JsonServiceStub()
    safe_write = SafeDriveWriteService(
        json_service=json_service,
        file_lock_service=FileLockService(),
        schema_validation_service=SchemaValidationService(),
        backups_root=tmp_path / "backups",
        logging_service=LoggingStub(),
        version_history_root=tmp_path / "history",
    )
    allocator = IdAllocatorService(tmp_path / "id_counters.json", FileLockService())
    path_service = DrivePathService(
        db_root=tmp_path / "MANDITRADE_DB",
        runtime_root=tmp_path / "runtime",
        governance_root=tmp_path / "governance",
        manufacturers_root=tmp_path / "manufacturers",
        public_buyers_root=tmp_path / "public_buyers",
    )
    dead_letter = DeadLetterService(tmp_path / "runtime" / "dead_letter", id_allocator_service=allocator)
    gmail = GmailService(
        sender_email="admin@example.com",
        use_gmail_api=False,
        queue_path=path_service.get_notification_path("email_queue"),
        safe_drive_write_service=safe_write,
        dead_letter_service=dead_letter,
        logging_service=LoggingStub(),
        notification_mode="mock",
        id_allocator_service=allocator,
        drive_path_service=path_service,
    )
    buyer_service = PublicBuyerService(tmp_path / "public_buyers", safe_write, json_service, allocator)
    notification_service = NotificationCenterService(
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
        domain_paths_service=type("Paths", (), {"notifications_path": lambda self, manufacturer_code: tmp_path / "manufacturers" / manufacturer_code / "notifications.json"})(),
        public_buyers_root=tmp_path / "public_buyers",
    )
    return {
        "json_service": json_service,
        "safe_write": safe_write,
        "allocator": allocator,
        "path_service": path_service,
        "dead_letter": dead_letter,
        "gmail": gmail,
        "buyer_service": buyer_service,
        "notification_service": notification_service,
    }


def test_drive_paths_generate_canonical_monthly_layout(tmp_path):
    path_service = _shared_stack(tmp_path)["path_service"]
    assert path_service.get_registry_path("manufacturers").name == "manufacturers.json"
    assert "orders" in str(path_service.get_order_path("marketplace", "2026-06"))
    assert str(path_service.get_notification_path("email_history", "2026-06")).endswith("2026-06\\sent_emails.json")


def test_gmail_queue_item_created_not_direct_send(tmp_path):
    shared = _shared_stack(tmp_path)
    queued = shared["gmail"].enqueue_message("buyer@example.com", "Subject", "Body", "PAYMENT_VERIFIED", deep_link="Marketplace Orders")
    assert queued["status"] == "QUEUED"
    assert shared["gmail"].read_queue()[0]["recipient_email"] == "buyer@example.com"


def test_email_history_written_after_send_simulation(tmp_path):
    shared = _shared_stack(tmp_path)
    shared["gmail"].enqueue_message("buyer@example.com", "Subject", "Body", "PAYMENT_VERIFIED")
    processed = shared["gmail"].process_queue()
    assert processed == 1
    history = shared["gmail"].list_history()
    assert history[0]["status"] == "SENT"


def test_dead_letter_created_on_email_failure(monkeypatch, tmp_path):
    shared = _shared_stack(tmp_path)
    shared["gmail"].notification_mode = "live"
    shared["gmail"].use_gmail_api = True
    shared["gmail"].enqueue_message("buyer@example.com", "Subject", "Body", "PAYMENT_VERIFIED")
    monkeypatch.setattr(shared["gmail"], "send_message", lambda *args, **kwargs: (_ for _ in ()).throw(ValueError("boom")))
    for _ in range(3):
        processed = shared["gmail"].process_queue(credentials=object())
        assert processed == 0
    assert shared["dead_letter"].list_entries()


def test_marketplace_order_creates_queue_and_notifications(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    notifications = stack["notification_service"].list_public_notifications(buyer["public_buyer_id"])
    assert order["public_order_id"]
    assert notifications


def test_product_approval_event_routes_to_manufacturer(tmp_path):
    shared = _shared_stack(tmp_path)
    app_stack = build_stack(tmp_path / "app")
    seed_public_product(app_stack, image_url="https://example.com/rice.png")
    buyer_service = shared["buyer_service"]
    event_service = EventNotificationService(
        notification_center_service=shared["notification_service"],
        gmail_service=shared["gmail"],
        governance_service=app_stack["governance_service"],
        public_buyer_service=buyer_service,
        notification_rules={"events": {"PRODUCT_APPROVED": {"in_app": True, "gmail": True, "severity": "MEDIUM"}}},
    )
    event_service.emit(
        "PRODUCT_APPROVED",
        {
            "entity_type": "PRODUCT_PROPOSAL",
            "entity_id": "PRD-2026-000001",
            "manufacturer_code": "MANU101",
            "manufacturer_email": "manu101@example.com",
            "title": "Product approved",
            "message": "Product approved.",
        },
    )
    manufacturer_notifications = shared["notification_service"].list_notifications("MANU101")
    assert manufacturer_notifications[0]["notification_id"]


def test_public_buyer_notification_privacy(tmp_path):
    shared = _shared_stack(tmp_path)
    buyer = shared["buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    shared["notification_service"].create_public_notification(
        buyer["public_buyer_id"],
        user_id=buyer["email"],
        notification_type="MARKETPLACE_ORDER_CREATED",
        priority="HIGH",
        title="Order created",
        message="Order created.",
        source_type="PUBLIC_ORDER",
        source_id="PO-1",
        recipient_role="public_buyer",
    )
    rows = shared["notification_service"].list_public_notifications(buyer["public_buyer_id"])
    assert all(item["recipient_role"] == "public_buyer" for item in rows)
