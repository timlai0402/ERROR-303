import math
from typing import Dict, Any, List

class InventoryEngine:
    @staticmethod
    def available(item: Dict[str, Any]) -> float:
        return max(0.0, float(item.get("physical", 0)) - float(item.get("reserved", 0)))

    @staticmethod
    def status(item: Dict[str, Any]) -> str:
        avail = InventoryEngine.available(item)
        safety = float(item.get("safety", 0))
        reorder = float(item.get("reorder", 0))

        if avail <= 0:
            return "OUT_OF_STOCK"
        if avail <= safety:
            return "CRITICAL"
        if avail <= reorder:
            return "REORDER"
        return "HEALTHY"

    @staticmethod
    def calculate_rop(daily_demand: float, lead_time_days: int, safety_stock: float) -> float:
        """
        Deterministic Reorder Point:
        ROP = (Lead Time Demand) + Safety Stock = (d * L) + SS
        """
        return round((daily_demand * lead_time_days) + safety_stock, 2)

    @staticmethod
    def calculate_eoq(annual_demand: float, order_setup_cost: float = 50.0, unit_cost: float = 10.0, holding_pct: float = 0.20) -> float:
        """
        Wilson Economic Order Quantity:
        EOQ = sqrt((2 * D * S) / H)
        where:
        D = Annual demand
        S = Fixed order transaction cost
        H = Unit holding cost per year (unit_cost * holding_pct)
        """
        h = max(0.01, unit_cost * holding_pct)
        if annual_demand <= 0 or order_setup_cost <= 0:
            return 0.0
        val = math.sqrt((2.0 * annual_demand * order_setup_cost) / h)
        return round(val, 2)

    @staticmethod
    def evaluate_restock(item: Dict[str, Any], order_cost: float = 50.0) -> Dict[str, Any]:
        avail = InventoryEngine.available(item)
        reorder = float(item.get("reorder", 0))
        min_order = float(item.get("minOrder", 1))
        unit_cost = float(item.get("cost", 1))
        daily = float(item.get("daily", 1))
        annual_demand = daily * 365.0

        eoq = InventoryEngine.calculate_eoq(annual_demand, order_cost, unit_cost)
        needs_restock = avail <= reorder

        # Reorder quantity: target replenishment up to (ROP + EOQ), rounded to min order multiple
        target_qty = max(min_order, eoq)
        if needs_restock:
            shortfall = (reorder + eoq) - avail
            recommended_qty = max(min_order, round(shortfall))
        else:
            recommended_qty = 0.0

        return {
            "itemId": item["id"],
            "name": item["name"],
            "available": avail,
            "reorderPoint": reorder,
            "safetyStock": float(item.get("safety", 0)),
            "eoq": eoq,
            "needsRestock": needs_restock,
            "recommendedQuantity": recommended_qty,
            "estimatedCost": round(recommended_qty * unit_cost, 2),
            "supplier": item.get("supplier", "Unknown"),
            "leadDays": item.get("lead", 1)
        }

    @staticmethod
    def evaluate_order_bom_shortages(orders: List[Dict[str, Any]], items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        BOM & Allocation Engine:
        Maps incoming demand against available physical reserves and flags stock deficits.
        """
        item_map = {i["id"]: i for i in items}
        shortages = []

        for ord in orders:
            item_id = ord.get("itemId")
            demand = float(ord.get("demand", 0))
            if item_id and item_id in item_map:
                target_item = item_map[item_id]
                avail = InventoryEngine.available(target_item)
                if demand > avail:
                    shortages.append({
                        "orderId": ord.get("id"),
                        "customer": ord.get("customer"),
                        "itemId": item_id,
                        "itemName": target_item["name"],
                        "demand": demand,
                        "available": avail,
                        "deficit": round(demand - avail, 2),
                        "dueDate": ord.get("due"),
                        "severity": "CRITICAL" if avail == 0 else "WARNING"
                    })
        return shortages

inventory_engine = InventoryEngine()

