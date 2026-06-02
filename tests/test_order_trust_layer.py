from __future__ import annotations

from pathlib import Path

from components.order_detail_view import build_order_detail_payload
from components.timeline import get_timeline_step_states
from services.favorites_service import FavoritesService
from services.file_lock_service import FileLockService
from services.id_allocator_service import IdAllocatorService
from services.safe_drive_write_service import SafeDriveWriteService
from services.schema_validation_service import SchemaValidationService
from services.trust_badge_service import TrustBadgeService
from tests.helpers.failure_injector import LoggingStub
from tests.helpers.fake_storage import JsonServiceStub
from tests.test_product_images_cart import build_stack, seed_public_product


def _favorites_service(tmp_path: Path):
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
    return FavoritesService(
        favorites_root=tmp_path / "favorites",
        safe_drive_write_service=safe_write,
        json_service=json_service,
        id_allocator_service=allocator,
    )


def test_order_detail_payload_builds_safely():
    detail = build_order_detail_payload(
        {"public_order_id": "PO-1", "notes": "Handle carefully"},
        order_id_key="public_order_id",
        status="DISPATCHED",
        items=[{"name": "Rice", "qty": 2, "unit_price": 500}],
        timeline_steps=["PAYMENT_PENDING", "PAID", "DISPATCHED"],
        status_history=[{"status": "PAID", "at": "2026-06-02T10:00:00+00:00", "actor": "seller@example.com"}],
        logistics={"driver_name": "Raju"},
        payment={"payment_status": "VERIFIED"},
        trust_badges=["Payment Verified"],
        next_action="Track Delivery",
    )
    assert detail["order_id"] == "PO-1"
    assert detail["payment"]["payment_status"] == "VERIFIED"
    assert detail["trust_badges"] == ["Payment Verified"]


def test_timeline_states_include_actor_and_timestamp():
    states = get_timeline_step_states(
        "PAID",
        ["PAYMENT_PENDING", "PAID", "DISPATCHED"],
        [{"status": "PAID", "at": "2026-06-02T10:00:00+00:00", "actor": "seller@example.com"}],
    )
    paid_state = states[1]
    assert paid_state["is_current"] is True
    assert paid_state["actor"] == "seller@example.com"
    assert paid_state["timestamp"] == "2026-06-02T10:00:00+00:00"


def test_payment_proof_metadata_persists_for_marketplace_order(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    updated = stack["public_order_service"].submit_payment_reference(
        order["public_order_id"],
        buyer["public_buyer_id"],
        payment_reference="UTR123",
        screenshot_placeholder="https://example.com/proof.png",
    )
    assert updated["payment_proof_url"] == "https://example.com/proof.png"
    assert updated["payment_proof_uploaded_at"]


def test_reorder_prefills_public_cart(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=2)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    for item in order.get("items", []):
        stack["public_cart_service"].add_item(
            buyer["public_buyer_id"],
            product_id=str(item.get("product_id", "")),
            qty=int(item.get("qty", 1) or 1),
        )
    cart = stack["public_cart_service"].get_cart(buyer["public_buyer_id"])
    assert cart["items"][0]["qty"] == 2


def test_favorites_work(tmp_path):
    service = _favorites_service(tmp_path)
    saved = service.save_favorite(
        "public_buyer",
        "PB001",
        item_type="PRODUCT",
        item_id="PRD-1",
        title="Rice",
        subtitle="Grain",
        image_url="https://example.com/rice.png",
    )
    assert saved["item_id"] == "PRD-1"
    assert len(service.list_favorites("public_buyer", "PB001")) == 1
    assert service.remove_favorite("public_buyer", "PB001", item_type="PRODUCT", item_id="PRD-1") == []


def test_marketplace_and_supply_ratings_persist(tmp_path):
    stack = build_stack(tmp_path)
    seed_public_product(stack)
    buyer = stack["public_buyer_service"].register_or_get(email="buyer@example.com", full_name="Buyer")
    stack["public_cart_service"].add_item(buyer["public_buyer_id"], product_id="PRD-2026-000001", qty=1)
    order = stack["public_order_service"].create_order_from_cart(buyer["public_buyer_id"])
    rated = stack["public_order_service"].submit_feedback(order["public_order_id"], rating=5, feedback="Great", submitted_by=buyer["email"])
    assert rated["ratings"][0]["rating"] == 5

    stack["governance_service"].upsert_raw_material(
        {
            "raw_material_id": "RM001",
            "mahajan_id": "MAH001",
            "name": "Cotton",
            "category": "RAW_MATERIAL",
            "unit": "kg",
            "available_qty": 100,
            "supply_price": 25,
            "status": "ACTIVE",
        }
    )
    supply_orders = stack["cart_service"].checkout(
        "manufacturer",
        "MANU101",
        cart_type="MANDIPLACE",
        checkout_context={"manufacturer_code": "MANU101", "requester_email": "owner@example.com"},
    ) if stack["cart_service"].add_item("manufacturer", "MANU101", cart_type="MANDIPLACE", item_id="RM001", qty=1) else []
    supply_order = supply_orders[0]
    feedbackd = stack["procurement_service"].submit_feedback(
        mandi_order_id=supply_order["mandi_order_id"],
        rating=4,
        feedback="Reliable dispatch",
        submitted_by="owner@example.com",
    )
    assert feedbackd["ratings"][0]["rating"] == 4


def test_trust_badges_compute():
    service = TrustBadgeService()
    marketplace_badges = service.badges_for_marketplace_order({"payment_status": "VERIFIED", "status": "DISPATCHED", "ratings": [{"rating": 5}]})
    supply_badges = service.badges_for_supply_order({"status": "MAHAJAN_DISPATCHED", "payment_verified_at": "2026-06-02T10:00:00+00:00", "ratings": [{"rating": 4}]})
    assert "Payment Verified" in marketplace_badges
    assert "Reliable Mahajan" in supply_badges


def test_notification_metadata_fields_persist(tmp_path):
    stack = build_stack(tmp_path)
    notification = stack["notification_service"].create_public_notification(
        "PB001",
        user_id="buyer@example.com",
        notification_type="PUBLIC_ORDER_DISPATCHED",
        priority="HIGH",
        title="Order Dispatched",
        message="Your order is on the way.",
        source_type="PUBLIC_ORDER",
        source_id="PO-1",
        source_route="Marketplace Orders",
        thumbnail_url="https://example.com/thumb.png",
        severity="CRITICAL",
    )
    assert notification["source_route"] == "Marketplace Orders"
    assert notification["thumbnail_url"] == "https://example.com/thumb.png"
    assert notification["severity"] == "CRITICAL"
