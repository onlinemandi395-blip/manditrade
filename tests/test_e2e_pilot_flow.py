from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from bootstrap.app_bootstrap import resolve_navigation_sections
from scripts.seed_pilot_flow import seed_pilot_flow


def _seed(tmp_path: Path) -> dict:
    return seed_pilot_flow(tmp_path / "pilot_seed", safe_mode=True)


def test_seeded_pilot_flow_consistency(tmp_path):
    seeded = _seed(tmp_path)
    summary = seeded["summary"]
    assert summary["manufacturers"] == ["PILOT_TEST_MANU001", "PILOT_TEST_MANU002"]
    assert len(summary["clients"]) == 2
    assert len(summary["products"]) == 3
    assert summary["private_order_id"].startswith("PILOT_TEST_ORDER_")
    assert summary["rfq_id"].startswith("PILOT_TEST_RFQ_")
    assert summary["public_order_id"].startswith("PILOT_TEST_PUBLIC_ORDER_")


def test_private_client_rbac_and_pricing_visibility(tmp_path):
    seeded = _seed(tmp_path)
    stack = seeded["stack"]
    product_service = stack["product_service"]
    order_query_service = stack["order_query_service"]
    ledger_service = stack["ledger_service"]
    client_service = stack["client_service"]

    client_products = product_service.list_products(include_pending=False, viewer_role="client")
    client_orders = order_query_service.list_orders_for_client("PILOT_TEST_MANU001", "pilot_test_client1@example.com")
    client_ledgers = ledger_service.list_ledgers_for_role("PILOT_TEST_MANU001", "client")
    manufacturer_client = client_service.get_client_by_email("PILOT_TEST_MANU001", "pilot_test_client1@example.com")

    assert all("mandi_price" not in item for item in client_products)
    assert all("marketplace_price" not in item for item in client_products)
    assert all("your_price" in item for item in client_products)
    assert client_orders
    assert "mandi_price" not in str(client_orders)
    assert "marketplace_price" not in str(client_orders)
    assert "commission_breakdown" not in str(client_ledgers)
    assert manufacturer_client is not None
    assert manufacturer_client["owner_name"] == "PILOT_TEST Amit Kumar"


def test_public_buyer_rbac_and_public_order_flow(tmp_path):
    seeded = _seed(tmp_path)
    stack = seeded["stack"]
    product_service = stack["product_service"]
    public_order_service = stack["public_order_service"]
    public_buyer_service = stack["public_buyer_service"]
    public_products = product_service.list_products(include_pending=False, viewer_role="public_buyer")
    buyer = public_buyer_service.get_by_email("pilot_test_public@example.com")
    orders = public_order_service.list_orders_for_buyer(buyer["public_buyer_id"])
    public_sections = resolve_navigation_sections(
        {
            "current_user": SimpleNamespace(role="public_buyer", email="pilot_test_public@example.com", manufacturer_code=None),
            "security_service": SimpleNamespace(is_admin_identity=lambda _user: False),
            "worker_service": SimpleNamespace(get_worker_by_email=lambda _email: None),
        }
    )

    assert buyer is not None
    assert any(item["product_id"] == "PILOT_TEST_PRODUCT_0002" for item in public_products)
    assert all("marketplace_price" in item or "price" in item for item in public_products)
    assert all("mandi_price" not in item for item in public_products)
    assert orders and orders[0]["payment_status"] == "VERIFIED"
    assert "Inventory" not in public_sections
    assert "RFQ" not in public_sections
    assert "Ledger" not in public_sections
    assert stack["json_service"].read_json(stack["domain_paths"].ledger_path("PILOT_TEST_MANU001"), {"ledgers": []}).get("ledgers")
    assert not any("PUBLIC_ORDER" in entry.get("entry_type", "") for ledger in stack["ledger_service"].list_ledgers("PILOT_TEST_MANU001") for entry in ledger.get("entries", []))


def test_rfq_priced_acceptance_and_inventory_separation(tmp_path):
    seeded = _seed(tmp_path)
    stack = seeded["stack"]
    procurement_service = stack["procurement_service"]
    rfq_doc = stack["json_service"].read_json(stack["domain_paths"].rfq_path("PILOT_TEST_MANU001"), {})
    accepted = next(item for item in rfq_doc["responses"] if item["response_id"] == seeded["summary"]["rfq_response_id"])
    buyer_ledgers = stack["ledger_service"].list_ledgers("PILOT_TEST_MANU001")
    private_inventory = stack["json_service"].read_json(stack["domain_paths"].private_self_inventory_path("PILOT_TEST_MANU001"), {})
    shared_inventory = stack["json_service"].read_json(stack["domain_paths"].shared_mandi_inventory_projection_path("PILOT_TEST_MANU001"), {})

    assert accepted["available_items"][0]["offered_unit_price"] == 42.0
    assert accepted["available_items"][0]["total_price"] == 2520.0
    assert any(entry["amount"] == 2520.0 for ledger in buyer_ledgers for entry in ledger.get("entries", []))
    assert "self_inventory" in private_inventory["items"][0]
    assert "self_inventory" not in shared_inventory["items"][0]

    try:
        procurement_service.respond_to_rfq(
            SimpleNamespace(manufacturer_code="PILOT_TEST_MANU002", email="pilot_test_beta_owner@example.com", role="manufacturer"),
            "PILOT_TEST_MANU001",
            seeded["summary"]["rfq_id"],
            [{"product_id": "PILOT_TEST_PRODUCT_0003", "qty": 10, "unit": "bag", "offered_unit_price": 0}],
            {"upfront_percentage": 20, "ledger_days": 7, "freestyle_note": "bad"},
        )
        assert False, "Expected zero-price RFQ rejection"
    except ValueError as exc:
        assert "offered unit price" in str(exc)


def test_superadmin_privacy_and_summary_artifacts(tmp_path):
    seeded = _seed(tmp_path)
    summary = seeded["summary"]

    assert "PILOT_TEST Amit Kumar" not in str(summary["private_order_projection"])
    assert "pilot_test_client1@example.com" not in str(summary["private_order_projection"])
    assert "payment_proposal" not in str(summary["private_order_projection"])
    assert "PILOT_TEST_MANU001" in str(summary["shared_inventory_projection"])
    assert all("pilot_test_client" not in str(action) for action in summary["superadmin_actions"])


def test_notifications_actions_and_gmail_runtime_stay_working(tmp_path):
    seeded = _seed(tmp_path)
    summary = seeded["summary"]
    stack = seeded["stack"]
    manufacturer_notifications = stack["notification_service"].list_notifications("PILOT_TEST_MANU001")
    public_buyer = stack["public_buyer_service"].get_by_email("pilot_test_public@example.com")
    public_notifications = stack["notification_service"].list_public_notifications(public_buyer["public_buyer_id"])

    assert manufacturer_notifications
    assert public_notifications
    assert any(item["type"] == "VERIFY_PUBLIC_PAYMENT" for item in summary["manufacturer_actions_before_public_verify"])
    assert any(item["type"] == "COMPLETE_PUBLIC_PAYMENT" for item in summary["public_buyer_actions_before_payment"])
    assert summary["gmail_messages"]
