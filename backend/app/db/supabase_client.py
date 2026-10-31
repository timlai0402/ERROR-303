import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

# Attempt to import supabase client
try:
    from supabase import create_client, Client
    HAS_SUPABASE = True
except ImportError:
    HAS_SUPABASE = False

class SupabaseService:
    def __init__(self):
        self.client: Optional[Any] = None
        active_key = settings.SUPABASE_SECRET_KEY or settings.SUPABASE_KEY or settings.SUPABASE_PUBLISHABLE_KEY
        if HAS_SUPABASE and settings.SUPABASE_URL and active_key:
            try:
                self.client = create_client(settings.SUPABASE_URL, active_key)
                print(f"[Supabase] Connected successfully to {settings.SUPABASE_URL}")
            except Exception as e:
                print(f"[Supabase] Initialization error: {e}. Falling back to in-memory state.")
        else:
            print("[Supabase] Credentials not configured or package missing. Operating in in-memory fallback mode.")
        
        # Local in-memory seed for development/fallback
        self._init_memory_store()

    def _init_memory_store(self):
        self.suppliers: List[Dict[str, Any]] = [
            {"id": "SUP-01", "name": "Everyday Wholesale", "items": "General merchandise, drinkware", "lead": 5, "reliability": 96.0, "terms": "Net 30"},
            {"id": "SUP-02", "name": "FreshFields Foods", "items": "Fresh ingredients, perishables", "lead": 2, "reliability": 94.0, "terms": "Net 14"},
            {"id": "SUP-03", "name": "PackRight Industries", "items": "Packaging materials", "lead": 4, "reliability": 91.0, "terms": "Net 30"},
            {"id": "SUP-04", "name": "Precision Parts Ltd", "items": "Components and spare parts", "lead": 10, "reliability": 89.0, "terms": "Net 30"},
            {"id": "SUP-05", "name": "CleanWorks Supply", "items": "Cleaning and facility supplies", "lead": 4, "reliability": 93.0, "terms": "Net 14"}
        ]
        
        self.items: List[Dict[str, Any]] = [
            {"id": "RAW-001", "name": "Steel Coil 2mm", "category": "Raw metals", "physical": 45.0, "reserved": 15.0, "reorder": 30.0, "safety": 15.0, "cost": 120.0, "unit": "tonnes", "supplier": "Precision Parts Ltd", "lead": 10, "minOrder": 10.0, "daily": 2.5, "initialDemand": 75.0},
            {"id": "RAW-002", "name": "Corrugated Packaging", "category": "Packaging", "physical": 180.0, "reserved": 40.0, "reorder": 120.0, "safety": 60.0, "cost": 1.45, "unit": "boxes", "supplier": "PackRight Industries", "lead": 4, "minOrder": 200.0, "daily": 15.0, "initialDemand": 450.0},
            {"id": "RAW-003", "name": "Industrial Lubricant", "category": "Maintenance", "physical": 12.0, "reserved": 4.0, "reorder": 15.0, "safety": 8.0, "cost": 45.0, "unit": "drums", "supplier": "CleanWorks Supply", "lead": 4, "minOrder": 5.0, "daily": 0.8, "initialDemand": 24.0},
            {"id": "RAW-004", "name": "Fastener Screws M6", "category": "Hardware", "physical": 500.0, "reserved": 100.0, "reorder": 400.0, "safety": 200.0, "cost": 0.12, "unit": "packs", "supplier": "Precision Parts Ltd", "lead": 7, "minOrder": 250.0, "daily": 30.0, "initialDemand": 900.0}
        ]

        self.orders: List[Dict[str, Any]] = [
            {"id": "ORD-501", "customer": "Apex Modular Tech", "itemName": "Steel Coil 2mm", "itemId": "RAW-001", "quantity": 1.0, "demand": 25.0, "due": "2026-11-04", "type": "Customer order", "status": "Confirmed"},
            {"id": "ORD-502", "customer": "Metro Assemblers", "itemName": "Corrugated Packaging", "itemId": "RAW-002", "quantity": 1.0, "demand": 140.0, "due": "2026-11-06", "type": "Customer order", "status": "Confirmed"},
            {"id": "FC-503", "customer": "Internal Buffer Plan", "itemName": "Industrial Lubricant", "itemId": "RAW-003", "quantity": 1.0, "demand": 10.0, "due": "2026-11-12", "type": "Forecast", "status": "Planning"}
        ]

        self.pos: List[Dict[str, Any]] = []
        self.activities: List[Dict[str, Any]] = [
            {"title": "System Initialized", "detail": "StockWise backend engine running", "time": "Just now"}
        ]
        self.settings: Dict[str, Any] = {
            "business": "Northstar Manufacturing",
            "industry": "Manufacturing",
            "currency": "MYR",
            "safety": 20.0,
            "waste": 5.0
        }

    # Items CRUD
    def get_items(self) -> List[Dict[str, Any]]:
        if self.client:
            try:
                res = self.client.table("items").select("*").execute()
                if res.data:
                    return res.data
            except Exception as e:
                print(f"[Supabase] Error accessing items table: {e}. Falling back to local data.")
        return self.items

    def get_item(self, item_id: str) -> Optional[Dict[str, Any]]:
        if self.client:
            try:
                res = self.client.table("items").select("*").eq("id", item_id).execute()
                if res.data:
                    return res.data[0]
            except Exception:
                pass
        return next((i for i in self.items if i["id"] == item_id), None)

    def update_item_stock(self, item_id: str, physical_delta: float = 0, reserved_delta: float = 0):
        item = self.get_item(item_id)
        if not item:
            return None
        
        new_physical = max(0.0, item["physical"] + physical_delta)
        new_reserved = max(0.0, item["reserved"] + reserved_delta)
        
        if self.client:
            try:
                self.client.table("items").update({
                    "physical_stock": new_physical,
                    "reserved_stock": new_reserved,
                    "updated_at": datetime.utcnow().isoformat()
                }).eq("id", item_id).execute()
            except Exception:
                pass
            
        item["physical"] = new_physical
        item["reserved"] = new_reserved
        return item

    # Suppliers CRUD
    def get_suppliers(self) -> List[Dict[str, Any]]:
        if self.client:
            try:
                res = self.client.table("suppliers").select("*").execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        return self.suppliers

    # Orders CRUD
    def get_orders(self) -> List[Dict[str, Any]]:
        if self.client:
            try:
                res = self.client.table("orders").select("*").execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        return self.orders

    # Purchase Orders & Audits
    def get_purchase_orders(self) -> List[Dict[str, Any]]:
        if self.client:
            try:
                res = self.client.table("purchase_orders").select("*").execute()
                if res.data:
                    return res.data
            except Exception:
                pass
        return self.pos

    def save_purchase_order(self, po_data: Dict[str, Any]) -> Dict[str, Any]:
        existing_index = next((idx for idx, p in enumerate(self.pos) if p["id"] == po_data["id"]), -1)
        if existing_index >= 0:
            self.pos[existing_index] = po_data
        else:
            self.pos.insert(0, po_data)

        if self.client:
            try:
                self.client.table("purchase_orders").upsert(po_data).execute()
            except Exception:
                pass
        return po_data

    def log_activity(self, title: str, detail: str):
        record = {
            "title": title,
            "detail": detail,
            "time": datetime.now().strftime("%I:%M %p")
        }
        self.activities.insert(0, record)
        if self.client:
            try:
                self.client.table("audit_ledger").insert(record).execute()
            except Exception:
                pass

db = SupabaseService()

