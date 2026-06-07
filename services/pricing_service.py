from __future__ import annotations


class PricingService:
    CHANNEL_FIELD_MAP = {
        "marketplace": "marketplace_price",
        "manditrade": "manditrade_price",
    }

    def resolve_sell_price(self, product: dict, channel: str) -> float:
        normalized_channel = str(channel or "").strip().lower()
        field_name = self.CHANNEL_FIELD_MAP.get(normalized_channel)
        if not field_name:
            raise ValueError(f"Unsupported pricing channel: {channel}")
        pricing = dict(product.get("pricing", {}) or {})
        value = pricing.get(field_name, None)
        if value in (None, ""):
            raise ValueError(f"Missing pricing.{field_name} for product {product.get('product_id', product.get('product_name', ''))}.")
        return float(value)

    def validate_channel_price(self, product: dict, channel: str) -> tuple[bool, str]:
        try:
            self.resolve_sell_price(product, channel)
            return True, ""
        except Exception as exc:
            return False, str(exc)
