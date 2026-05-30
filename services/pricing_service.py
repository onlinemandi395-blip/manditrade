from __future__ import annotations

from typing import Any


class PricingService:
    CHANNEL_MANDI = "MANDI"
    CHANNEL_PRIVATE_CLIENT = "PRIVATE_CLIENT"
    CHANNEL_PUBLIC_MARKETPLACE = "PUBLIC_MARKETPLACE"

    PLATFORM_FEE_KEYS = {
        "basic": "basic",
        "premium": "premium",
        "premium+": "premium_plus",
        "premium_plus": "premium_plus",
    }

    def __init__(self, commission_config: dict[str, Any] | None = None) -> None:
        commission_config = commission_config or {}
        self.admin_profit_share_percent = float(commission_config.get("admin_profit_share_percent", 50))
        self.manufacturer_profit_share_percent = float(commission_config.get("manufacturer_profit_share_percent", 50))
        self.platform_fee_on_admin_commission = commission_config.get(
            "platform_fee_on_admin_commission",
            {"basic": 10, "premium": 5, "premium_plus": 1},
        )

    def _normalize_product(self, product: dict[str, Any]) -> dict[str, float]:
        mandi_price = float(
            product.get("approved_mandi_price")
            if product.get("approved_mandi_price") is not None
            else product.get("mandi_price", 0)
            or 0
        )
        client_price = float(
            product.get("approved_client_price")
            if product.get("approved_client_price") is not None
            else product.get("client_price")
            if product.get("client_price") is not None
            else product.get("approved_mrp")
            if product.get("approved_mrp") is not None
            else product.get("mrp", 0)
            or 0
        )
        marketplace_price = float(
            product.get("approved_marketplace_price")
            if product.get("approved_marketplace_price") is not None
            else product.get("marketplace_price")
            if product.get("marketplace_price") is not None
            else client_price
        )
        return {
            "mandi_price": mandi_price,
            "client_price": client_price,
            "marketplace_price": marketplace_price,
        }

    def get_price_for_role(self, product: dict[str, Any], role: str, channel: str) -> dict[str, Any]:
        prices = self._normalize_product(product)
        role_key = (role or "").strip().lower()
        if role_key in {"platform_admin", "admin"}:
            return {
                **prices,
                "sale_price": self._sale_price(prices, channel),
                "visible_prices": ["mandi_price", "client_price", "marketplace_price"],
            }
        if role_key in {"manufacturer", "admin_as_manufacturer"}:
            return {
                **prices,
                "sale_price": self._sale_price(prices, channel),
                "visible_prices": ["mandi_price", "client_price", "marketplace_price"],
            }
        if role_key == "client":
            return {"client_price": prices["client_price"], "sale_price": prices["client_price"], "visible_prices": ["client_price"]}
        if role_key == "public_buyer":
            return {
                "marketplace_price": prices["marketplace_price"],
                "sale_price": prices["marketplace_price"],
                "visible_prices": ["marketplace_price"],
            }
        return {"sale_price": self._sale_price(prices, channel), "visible_prices": []}

    def _sale_price(self, prices: dict[str, float], channel: str) -> float:
        if channel == self.CHANNEL_PRIVATE_CLIENT:
            return prices["client_price"]
        if channel == self.CHANNEL_PUBLIC_MARKETPLACE:
            return prices["marketplace_price"]
        return prices["mandi_price"]

    def calculate_profit(self, product: dict[str, Any], channel: str) -> dict[str, Any]:
        prices = self._normalize_product(product)
        sale_price = self._sale_price(prices, channel)
        gross_profit = round(sale_price - prices["mandi_price"], 2) if channel != self.CHANNEL_MANDI else 0.0
        warning = ""
        if channel != self.CHANNEL_MANDI and gross_profit <= 0:
            warning = "Pricing warning: sale price is not above mandi price."
        return {
            "channel": channel,
            "mandi_price": round(prices["mandi_price"], 2),
            "sale_price": round(sale_price, 2),
            "gross_profit": round(max(gross_profit, 0.0), 2) if warning else round(gross_profit, 2),
            "pricing_warning": warning,
        }

    def calculate_commission(self, product: dict[str, Any], channel: str, subscription_plan: str | None) -> dict[str, Any]:
        profit = self.calculate_profit(product, channel)
        subscription_key = self.PLATFORM_FEE_KEYS.get((subscription_plan or "basic").strip().lower(), "basic")
        fee_rate = float(self.platform_fee_on_admin_commission.get(subscription_key, 10)) / 100
        if channel == self.CHANNEL_MANDI or profit["gross_profit"] <= 0:
            return {
                **profit,
                "admin_base_commission": 0.0,
                "platform_fee_rate": fee_rate,
                "platform_fee": 0.0,
                "admin_net_commission": 0.0,
                "manufacturer_profit_share": 0.0,
                "subscription_plan": subscription_key,
                "pricing_warning": profit["pricing_warning"] or "Pricing warning: no positive profit available for commission.",
            }
        admin_base = round(profit["gross_profit"] * (self.admin_profit_share_percent / 100), 2)
        manufacturer_share = round(profit["gross_profit"] * (self.manufacturer_profit_share_percent / 100), 2)
        platform_fee = round(admin_base * fee_rate, 2)
        admin_net = round(admin_base - platform_fee, 2)
        return {
            **profit,
            "admin_base_commission": admin_base,
            "platform_fee_rate": fee_rate,
            "platform_fee": platform_fee,
            "admin_net_commission": admin_net,
            "manufacturer_profit_share": manufacturer_share,
            "subscription_plan": subscription_key,
        }
