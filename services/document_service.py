from __future__ import annotations


class DocumentService:
    def build_invoice_html(self, order: dict) -> str:
        order_id = order.get("order_id", "")
        buyer_email = order.get("buyer_email", "") or order.get("requester_email", "")
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Invoice {order_id}</title></head>
<body>
  <h1>MandiTrade Invoice</h1>
  <p><strong>Order ID:</strong> {order_id}</p>
  <p><strong>Product:</strong> {order.get("product_name", "")}</p>
  <p><strong>Buyer:</strong> {buyer_email}</p>
  <p><strong>Owner:</strong> {order.get("owner_email", "")}</p>
  <p><strong>Quantity:</strong> {order.get("quantity", 0)}</p>
  <p><strong>Unit Price:</strong> {order.get("unit_price", 0)}</p>
  <p><strong>Total Amount:</strong> {order.get("total_amount", 0)}</p>
  <p><strong>Status:</strong> {order.get("status", "")}</p>
  <p><strong>Payment Reference:</strong> {order.get("payment_reference", "")}</p>
</body></html>"""

    def build_delivery_slip_html(self, order: dict, shipment: dict) -> str:
        order_id = order.get("order_id", "")
        return f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Delivery Slip {order_id}</title></head>
<body>
  <h1>MandiTrade Delivery Slip</h1>
  <p><strong>Shipment ID:</strong> {shipment.get("shipment_id", "")}</p>
  <p><strong>Order ID:</strong> {order_id}</p>
  <p><strong>Product:</strong> {order.get("product_name", "")}</p>
  <p><strong>Owner:</strong> {order.get("owner_email", "")}</p>
  <p><strong>Buyer:</strong> {order.get("buyer_email", "") or order.get("requester_email", "")}</p>
  <p><strong>Delivery Partner:</strong> {shipment.get("delivery_partner_email", "")}</p>
  <p><strong>Status:</strong> {shipment.get("status", "")}</p>
  <p><strong>Quantity:</strong> {order.get("quantity", 0)}</p>
</body></html>"""
