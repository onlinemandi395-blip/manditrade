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
        self.mahajan_transaction_fee_percent = float(commission_config.get("mahajan_transaction_fee_percent", 1))
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
                "commission_status": "CALCULATED",
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
            "commission_status": "CALCULATED",
        }

    def calculate_supply_commission(
        self,
        *,
        mandi_order_id: str,
        mahajan_id: str,
        manufacturer_id: str,
        raw_material_id: str,
        qty: float,
        unit: str,
        mahajan_unit_price: float,
        manufacturer_unit_price: float,
        admin_spread_share_percent: float | None = None,
        mahajan_fee_percent: float | None = None,
    ) -> dict[str, Any]:
        qty_value = float(qty or 0)
        mahajan_price = round(float(mahajan_unit_price or 0), 2)
        manufacturer_price = round(float(manufacturer_unit_price or 0), 2)
        mahajan_bill_amount = round(qty_value * mahajan_price, 2)
        manufacturer_bill_amount = round(qty_value * manufacturer_price, 2)
        gross_spread = round(manufacturer_bill_amount - mahajan_bill_amount, 2)
        spread_share_percent = float(admin_spread_share_percent if admin_spread_share_percent is not None else self.admin_profit_share_percent)
        admin_spread_commission = round(max(gross_spread, 0) * (spread_share_percent / 100), 2)
        remaining_spread_share = round(max(gross_spread, 0) - admin_spread_commission, 2)
        supply_fee_percent = float(mahajan_fee_percent if mahajan_fee_percent is not None else self.mahajan_transaction_fee_percent)
        mahajan_transaction_fee = round(mahajan_bill_amount * (supply_fee_percent / 100), 2)
        admin_total_earning = round(admin_spread_commission + mahajan_transaction_fee, 2)
        return {
            "mandi_order_id": mandi_order_id,
            "mahajan_id": mahajan_id,
            "manufacturer_id": manufacturer_id,
            "raw_material_id": raw_material_id,
            "qty": qty_value,
            "unit": unit,
            "mahajan_unit_price": mahajan_price,
            "manufacturer_unit_price": manufacturer_price,
            "mahajan_bill_amount": mahajan_bill_amount,
            "manufacturer_bill_amount": manufacturer_bill_amount,
            "gross_spread": gross_spread,
            "admin_spread_share_percent": spread_share_percent,
            "admin_spread_commission": admin_spread_commission,
            "remaining_spread_share": remaining_spread_share,
            "mahajan_fee_percent": supply_fee_percent,
            "mahajan_transaction_fee": mahajan_transaction_fee,
            "admin_total_earning": admin_total_earning,
            "commission_status": "CALCULATED",
            "commission_status_history": [
                {"status": "CALCULATED"},
            ],
            "payment_recipient": "SUPPLIER_DIRECT",
        }
