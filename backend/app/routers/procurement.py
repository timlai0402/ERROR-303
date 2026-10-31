from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime
from app.db.supabase_client import db
from app.services.ai_advisor import ai_advisor
from app.services.market_news import market_news
from app.services.inventory_engine import inventory_engine
from app.models.schemas import PurchaseOrderCreate, PurchaseOrderAction, PurchaseOrderResponse

router = APIRouter(prefix="", tags=["Procurement & Governance"])

@router.get("/purchase-orders", response_model=List[PurchaseOrderResponse])
def list_purchase_orders():
    return db.get_purchase_orders()

@router.post("/purchase-orders", response_model=PurchaseOrderResponse)
async def create_purchase_order(payload: PurchaseOrderCreate):
    item = db.get_item(payload.itemId)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    po_id = f"PO-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:6].upper()}"
    unit_cost = payload.unitCost if payload.unitCost is not None else item.get("cost", 0.0)
    total = round(payload.quantity * unit_cost, 2)
    supplier = payload.supplier or item.get("supplier", "Unknown")

    # Fetch live NewsAPI context for category
    signals = await market_news.fetch_supply_chain_news(f"{item.get('category', '')} supply price", page_size=2)
    headlines = [s["title"] for s in signals]

    # Generate KrackedDevs LLM explanation fused with NewsAPI signals
    ai_eval = await ai_advisor.explain_restocking_decision(
        item=item,
        rec_quantity=payload.quantity,
        deficit=0.0,
        market_signals=headlines
    )

    po = {
        "id": po_id,
        "itemId": item["id"],
        "itemName": item["name"],
        "quantity": payload.quantity,
        "unitCost": unit_cost,
        "total": total,
        "supplier": supplier,
        "status": "Draft",
        "revision": 0,
        "createdBy": "user-01",
        "createdByName": "Inventory Manager",
        "createdAt": datetime.utcnow().isoformat(),
        "aiRationale": ai_eval.get("executive_rationale", ""),
        "aiRiskLevel": ai_eval.get("supply_risk_level", "LOW"),
        "additionalReason": payload.additionalReason or payload.reason
    }

    db.save_purchase_order(po)
    db.log_activity("Purchase Request Created", f"Drafted {po_id} for {payload.quantity} {item['unit']} of {item['name']}")
    return po

@router.post("/purchase-requests/action")
async def handle_procurement_action(action: PurchaseOrderAction):
    """
    Human-in-the-Loop Approval & Governance State Machine.
    Compatible with frontend /purchase-requests/action requests.
    """
    act = action.action.lower()
    
    # 1. Action: CREATE
    if act == "create":
        item = db.get_item(action.itemId)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")

        po_id = action.id or f"PO-{str(uuid.uuid4())[:8].upper()}"
        unit_cost = action.unitCost if action.unitCost is not None else item.get("cost", 0.0)
        qty = action.quantity or float(item.get("minOrder", 10))
        total = round(qty * unit_cost, 2)
        
        # NewsAPI signals
        signals = await market_news.fetch_supply_chain_news(f"{item.get('category', '')} supply price", page_size=2)
        headlines = [s["title"] for s in signals]

        # KrackedDevs AI decision rationale
        ai_eval = await ai_advisor.explain_restocking_decision(item, qty, market_signals=headlines)

        po = {
            "id": po_id,
            "itemId": item["id"],
            "itemName": item["name"],
            "quantity": qty,
            "unitCost": unit_cost,
            "total": total,
            "supplier": action.supplier or item.get("supplier", "Primary Vendor"),
            "status": "Draft",
            "revision": 0,
            "createdBy": "1",
            "createdByName": "Requester",
            "createdAt": datetime.utcnow().isoformat(),
            "aiRationale": ai_eval.get("executive_rationale", ""),
            "aiRiskLevel": ai_eval.get("supply_risk_level", "LOW"),
            "additionalReason": action.additionalReason or action.reason
        }
        db.save_purchase_order(po)
        db.log_activity("Purchase Draft Created", f"Drafted PO {po_id} for {qty} units")
        return {"ok": True, "po": po}

    # 2. Existing PO lookup
    pos = db.get_purchase_orders()
    po = next((p for p in pos if p["id"] == action.id), None)
    if not po:
        raise HTTPException(status_code=404, detail=f"Request {action.id} not found")

    old_status = po["status"]
    old_qty = po["quantity"]

    # 3. State Transitions
    if act == "submit":
        po["status"] = "Pending"
        po["revision"] = po.get("revision", 0) + 1
        db.log_activity("Purchase Request Submitted", f"{po['id']} submitted for owner approval")

    elif act == "approve":
        po["status"] = "Approved"
        po["revision"] = po.get("revision", 0) + 1
        db.log_activity("Human Gate: PO Approved", f"{po['id']} approved by manager. Ready for supplier dispatch.")

    elif act == "reject":
        po["status"] = "Rejected"
        po["revision"] = po.get("revision", 0) + 1
        reason = action.reason or "Does not meet capital budget constraints."
        db.log_activity("Human Gate: PO Rejected", f"{po['id']} rejected: {reason}")

    elif act == "return":
        po["status"] = "Returned"
        po["revision"] = po.get("revision", 0) + 1
        db.log_activity("PO Returned for Revision", f"{po['id']} returned to requester with notes.")

    elif act == "ordered":
        po["status"] = "Ordered"
        # Update reserved/physical stock when PO is ordered
        item = db.get_item(po["itemId"])
        if item:
            item["reserved"] = max(0.0, item.get("reserved", 0) - po["quantity"])
        db.log_activity("PO Dispatched", f"Purchase order {po['id']} sent to supplier {po['supplier']}")

    elif act == "cancel":
        po["status"] = "Cancelled"
        db.log_activity("PO Cancelled", f"{po['id']} was cancelled")

    else:
        raise HTTPException(status_code=400, detail=f"Unknown procurement action '{act}'")

    db.save_purchase_order(po)
    return {"ok": True, "status": po["status"], "po": po}
