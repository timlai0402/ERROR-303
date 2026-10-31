from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from app.db.supabase_client import db
from app.services.inventory_engine import inventory_engine
from app.models.schemas import ItemResponse, ItemCreate, ItemBase

router = APIRouter(prefix="/inventory", tags=["Inventory"])

def format_item(item: Dict[str, Any]) -> Dict[str, Any]:
    avail = inventory_engine.available(item)
    st = inventory_engine.status(item)
    return {
        **item,
        "available": avail,
        "status": st
    }

@router.get("", response_model=List[ItemResponse])
def get_inventory():
    items = db.get_items()
    return [format_item(i) for i in items]

@router.get("/restock-suggestions")
def get_restock_suggestions():
    items = db.get_items()
    suggestions = [inventory_engine.evaluate_restock(i) for i in items]
    return suggestions

@router.get("/shortages")
def get_bom_shortages():
    orders = db.get_orders()
    items = db.get_items()
    return inventory_engine.evaluate_order_bom_shortages(orders, items)

@router.get("/{item_id}", response_model=ItemResponse)
def get_item_detail(item_id: str):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return format_item(item)

@router.post("", response_model=ItemResponse)
def create_item(payload: ItemBase):
    existing = db.get_item(payload.id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Item {payload.id} already exists")
    
    item_dict = payload.model_dump()
    db.items.append(item_dict)
    db.log_activity("Item Added", f"Added {payload.name} ({payload.id}) to inventory")
    return format_item(item_dict)

@router.put("/{item_id}", response_model=ItemResponse)
def update_item(item_id: str, payload: ItemBase):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    
    item.update(payload.model_dump())
    db.log_activity("Item Updated", f"Updated details for {payload.name}")
    return format_item(item)

