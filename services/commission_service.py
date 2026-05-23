from __future__ import annotations


class CommissionService:
    def __init__(self, admin_share_ratio: float) -> None:
        self.admin_share_ratio = admin_share_ratio

    def calculate(self, mrp: float, mandi_price: float) -> dict[str, float]:
        net_profit = max(mrp - mandi_price, 0)
        admin_share = round(net_profit * self.admin_share_ratio, 2)
        manufacturer_share = round(net_profit - admin_share, 2)
        return {
            "mrp": round(mrp, 2),
            "mandi_price": round(mandi_price, 2),
            "net_profit": round(net_profit, 2),
            "admin_share": admin_share,
            "manufacturer_share": manufacturer_share,
        }
