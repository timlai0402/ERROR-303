from fastapi import APIRouter
from typing import Dict, Any
from app.db.supabase_client import db
from app.services.inventory_engine import inventory_engine

router = APIRouter(prefix="", tags=["Workspace Synchronization"])

@router.get("/auth/me")
def get_current_user():
    return {
        "user": {
            "id": 1,
            "name": "Production Manager",
            "login": "manager@stockwise.internal",
            "role": "owner",
            "active": True
        },
        "company": {
            "id": 1,
            "name": db.settings["business"],
            "industry": db.settings["industry"],
            "currency": db.settings["currency"],
            "completion": 100
        }
    }

@router.get("/suppliers")
def get_suppliers():
    return db.get_suppliers()

@router.get("/orders")
def get_orders():
    return db.get_orders()

@router.get("/workspace")
def get_workspace():
    items = db.get_items()
    orders = db.get_orders()
    suppliers = db.get_suppliers()
    pos = db.get_purchase_orders()
    activities = db.activities
    settings = db.settings

    # Calculate valuation
    by_category: Dict[str, float] = {}
    total_val = 0.0

    formatted_items = []
    for item in items:
        avail = inventory_engine.available(item)
        val = float(item.get("physical", 0)) * float(item.get("cost", 0))
        total_val += val
        cat = item.get("category", "General")
        by_category[cat] = round(by_category.get(cat, 0.0) + val, 2)

        formatted_items.append({
            **item,
            "available": avail,
            "status": inventory_engine.status(item)
        })

    return {
        "version": 1,
        "data": {
            "items": formatted_items,
            "orders": orders,
            "suppliers": suppliers,
            "pos": pos,
            "activities": activities,
            "settings": settings
        },
        "costsHidden": False,
        "valuation": {
            "total": round(total_val, 2),
            "byCategory": by_category
        }
    }

