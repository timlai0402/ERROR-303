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

<<<<<<< HEAD
    def _init_hardware_store(self):
        """Seed data specifically for hardware shops and mechanics (non-expiry inventory)"""
        self.default_business_id = "biz-hardware-01"
        self.businesses: Dict[str, Dict[str, Any]] = {
            "biz-hardware-01": {
                "id": "biz-hardware-01",
                "name": "Ah Huat Hardware & Auto Parts",
                "currency": "MYR",
                "created_at": datetime.utcnow().isoformat()
            }
        }

        # Seed hardware products with realistic hardware shop inventory
        now_str = datetime.utcnow().isoformat()
        self.hardware_products: Dict[str, Dict[str, Any]] = {}
        self.hardware_movements: List[Dict[str, Any]] = []
        self.hardware_import_batches: Dict[str, Dict[str, Any]] = {}
        self.processed_idempotency_keys: Dict[str, Dict[str, Any]] = {}
        self.hardware_staff: Dict[str, Dict[str, Any]] = {
            "staff-01": {
                "id": "staff-01",
                "business_id": self.default_business_id,
                "name": "Ah Seng (Head Counter)",
                "username": "ahseng",
                "role": "Counter Staff",
                "is_active": True,
                "created_at": now_str
            },
            "staff-02": {
                "id": "staff-02",
                "business_id": self.default_business_id,
                "name": "Muthu (Workshop Mechanic)",
                "username": "muthu",
                "role": "Mechanic",
                "is_active": True,
                "created_at": now_str
            }
        }

        initial_products = [
            {
                "sku": "BLT-08-040",
                "name": "Hex Flange Bolt M8x40 High-Tensile 8.8",
                "unit": "pcs",
                "current_stock": 120.0,
                "min_stock": 50.0,
                "supplier_name": "MegaFasteners Malaysia",
                "supplier_contact": "+6012-3334455"
            },
            {
                "sku": "FLT-02",
                "name": "Oil Filter Spin-On (Proton/Perodua OEM)",
                "unit": "pcs",
                "current_stock": 8.0,
                "min_stock": 20.0, # LOW STOCK (Deficit: 12)
                "supplier_name": "Huat Kee Auto Spares",
                "supplier_contact": "+6012-8889999"
            },
            {
                "sku": "BRK-CLN-450",
                "name": "Aerosol Brake Cleaner 450ml",
                "unit": "can",
                "current_stock": 0.0,
                "min_stock": 10.0, # ZERO STOCK / OUT OF STOCK!
                "supplier_name": "ChemLub Lubricants",
                "supplier_contact": "+6013-4567890"
            },
            {
                "sku": "BRG-6204-2RS",
                "name": "Deep Groove Ball Bearing 6204-2RS Rubber Sealed",
                "unit": "pcs",
                "current_stock": 4.0,
                "min_stock": 15.0, # LOW STOCK (Deficit: 11)
                "supplier_name": "Koyo Bearings MY",
                "supplier_contact": "+6016-1122334"
            },
            {
                "sku": "WSH-M14",
                "name": "Copper Oil Sump Drain Plug Washers M14 (100pk)",
                "unit": "pack",
                "current_stock": 2.0,
                "min_stock": 8.0, # LOW STOCK (Deficit: 6)
                "supplier_name": "MegaFasteners Malaysia",
                "supplier_contact": "+6012-3334455"
            },
            {
                "sku": "TL-BLU-50",
                "name": "Removable Threadlocking Adhesive Blue 50ml",
                "unit": "bottle",
                "current_stock": 25.0,
                "min_stock": 5.0,
                "supplier_name": "ChemLub Lubricants",
                "supplier_contact": "+6013-4567890"
            },
            {
                "sku": "BLD-HS-300",
                "name": "Bi-Metal High-Speed Hacksaw Blade 300mm 24TPI",
                "unit": "pcs",
                "current_stock": 45.0,
                "min_stock": 20.0,
                "supplier_name": "SolidTool Hardware",
                "supplier_contact": "+6018-9988776"
            },
            {
                "sku": "SKT-SET-24",
                "name": "1/2\" Drive Metric Socket Set 24-Piece (10-32mm)",
                "unit": "set",
                "current_stock": 5.0,
                "min_stock": 2.0,
                "supplier_name": "SolidTool Hardware",
                "supplier_contact": "+6018-9988776"
            },
            {
                "sku": "TP-TF-12",
                "name": "PTFE Thread Seal Teflon Tape 12mm x 10m",
                "unit": "roll",
                "current_stock": 80.0,
                "min_stock": 30.0,
                "supplier_name": "MegaFasteners Malaysia",
                "supplier_contact": "+6012-3334455"
            },
            {
                "sku": "GRS-CRT-400",
                "name": "Multi-Purpose Lithium Grease Cartridge 400g",
                "unit": "can",
                "current_stock": 18.0,
                "min_stock": 10.0,
                "supplier_name": "ChemLub Lubricants",
                "supplier_contact": "+6013-4567890"
            }
        ]

        for p in initial_products:
            prod_id = f"prd-{p['sku'].lower()}"
            self.hardware_products[prod_id] = {
                "id": prod_id,
                "business_id": self.default_business_id,
                "sku": p["sku"],
                "name": p["name"],
                "unit": p["unit"],
                "current_stock": float(p["current_stock"]),
                "min_stock": float(p["min_stock"]),
                "supplier_name": p["supplier_name"],
                "supplier_contact": p["supplier_contact"],
                "is_archived": False,
                "created_at": now_str,
                "updated_at": now_str
            }
            # Add initial OPENING_STOCK movement
            mov_id = f"mov-{uuid.uuid4().hex[:8]}"
            self.hardware_movements.append({
                "id": mov_id,
                "business_id": self.default_business_id,
                "product_id": prod_id,
                "product_sku": p["sku"],
                "product_name": p["name"],
                "product_unit": p["unit"],
                "movement_type": "OPENING_STOCK",
                "quantity_change": float(p["current_stock"]),
                "previous_stock": 0.0,
                "resulting_stock": float(p["current_stock"]),
                "reason": "Initial inventory baseline",
                "user_recorded": "System Setup",
                "idempotency_key": f"init-{prod_id}",
                "batch_id": None,
                "created_at": now_str
            })

    # --- Hardware SME API Methods ---

    def get_hardware_products(
        self, 
        business_id: str, 
        search: Optional[str] = None, 
        status: str = "active", # "active", "archived", "all"
        page: int = 1, 
        page_size: int = 10
    ) -> Dict[str, Any]:
        with self.lock:
            prods = [p for p in self.hardware_products.values() if p["business_id"] == business_id]
            
            # Status filter
            if status == "active":
                prods = [p for p in prods if not p.get("is_archived", False)]
            elif status == "archived":
                prods = [p for p in prods if p.get("is_archived", False)]

            # Search filter
            if search:
                s_lower = search.lower().strip()
                prods = [
                    p for p in prods 
                    if s_lower in p["sku"].lower() 
                    or s_lower in p["name"].lower() 
                    or (p.get("supplier_name") and s_lower in p["supplier_name"].lower())
                ]

            # Sort by name
            prods.sort(key=lambda x: x["name"])

            total = len(prods)
            total_pages = max(1, (total + page_size - 1) // page_size)
            start = (page - 1) * page_size
            end = start + page_size
            sliced = prods[start:end]

            # Enrich items with computed low stock indicators
            enriched = []
            for item in sliced:
                cur = float(item["current_stock"])
                min_s = float(item["min_stock"])
                is_low = (min_s > 0) and (cur < min_s)
                is_zero = (cur == 0.0)
                deficit = max(0.0, min_s - cur) if is_low else 0.0
                enriched.append({
                    **item,
                    "is_low_stock": is_low,
                    "is_zero_stock": is_zero,
                    "deficit_qty": deficit
                })

            return {
                "items": enriched,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    def get_hardware_product(self, business_id: str, product_id: str) -> Optional[Dict[str, Any]]:
        with self.lock:
            p = self.hardware_products.get(product_id)
            if p and p["business_id"] == business_id:
                cur = float(p["current_stock"])
                min_s = float(p["min_stock"])
                is_low = (min_s > 0) and (cur < min_s)
                is_zero = (cur == 0.0)
                deficit = max(0.0, min_s - cur) if is_low else 0.0
                return {
                    **p,
                    "is_low_stock": is_low,
                    "is_zero_stock": is_zero,
                    "deficit_qty": deficit
                }
            return None

    def create_hardware_product(self, business_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            sku = str(data["sku"]).strip()
            # Check unique SKU in this business
            for p in self.hardware_products.values():
                if p["business_id"] == business_id and p["sku"].lower() == sku.lower():
                    raise ValueError(f"SKU '{sku}' already exists in this business")

            prod_id = f"prd-{uuid.uuid4().hex[:12]}"
            now_str = datetime.utcnow().isoformat()
            opening_stock = float(data.get("opening_stock", 0.0))
            if opening_stock < 0:
                raise ValueError("Opening stock cannot be negative")

            record = {
                "id": prod_id,
                "business_id": business_id,
                "sku": sku,
                "name": str(data["name"]).strip(),
                "unit": str(data.get("unit", "pcs")).lower().strip(),
                "current_stock": opening_stock,
                "min_stock": float(data.get("min_stock", 0.0)),
                "supplier_name": data.get("supplier_name"),
                "supplier_contact": data.get("supplier_contact"),
                "is_archived": False,
                "created_at": now_str,
                "updated_at": now_str
            }
            self.hardware_products[prod_id] = record

            # Record initial OPENING_STOCK movement
            mov_id = f"mov-{uuid.uuid4().hex[:8]}"
            user = data.get("user_recorded", "Shop Staff")
            self.hardware_movements.insert(0, {
                "id": mov_id,
                "business_id": business_id,
                "product_id": prod_id,
                "product_sku": sku,
                "product_name": record["name"],
                "product_unit": record["unit"],
                "movement_type": "OPENING_STOCK",
                "quantity_change": opening_stock,
                "previous_stock": 0.0,
                "resulting_stock": opening_stock,
                "reason": "Opening stock on product creation",
                "user_recorded": user,
                "idempotency_key": f"init-{prod_id}",
                "batch_id": None,
                "created_at": now_str
            })

            cur = record["current_stock"]
            min_s = record["min_stock"]
            is_low = (min_s > 0) and (cur < min_s)
            is_zero = (cur == 0.0)
            deficit = max(0.0, min_s - cur) if is_low else 0.0

            return {
                **record,
                "is_low_stock": is_low,
                "is_zero_stock": is_zero,
                "deficit_qty": deficit
            }

    def update_hardware_product(self, business_id: str, product_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            p = self.hardware_products.get(product_id)
            if not p or p["business_id"] != business_id:
                raise KeyError(f"Product '{product_id}' not found")

            # Check if attempting to change unit when movements exist
            if "unit" in data and data["unit"] and data["unit"].lower().strip() != p["unit"].lower().strip():
                # Count movements for this product
                movs = [m for m in self.hardware_movements if m["product_id"] == product_id]
                if len(movs) > 0:
                    raise ValueError("Cannot change unit once stock movements exist without migration")
                p["unit"] = data["unit"].lower().strip()

            if "name" in data and data["name"]:
                p["name"] = str(data["name"]).strip()
            if "min_stock" in data and data["min_stock"] is not None:
                min_s = float(data["min_stock"])
                if min_s < 0:
                    raise ValueError("Minimum stock level cannot be negative")
                p["min_stock"] = min_s
            if "supplier_name" in data:
                p["supplier_name"] = data["supplier_name"]
            if "supplier_contact" in data:
                p["supplier_contact"] = data["supplier_contact"]

            p["updated_at"] = datetime.utcnow().isoformat()

            cur = float(p["current_stock"])
            min_s = float(p["min_stock"])
            is_low = (min_s > 0) and (cur < min_s)
            is_zero = (cur == 0.0)
            deficit = max(0.0, min_s - cur) if is_low else 0.0

            return {
                **p,
                "is_low_stock": is_low,
                "is_zero_stock": is_zero,
                "deficit_qty": deficit
            }

    def archive_hardware_product(self, business_id: str, product_id: str, archive_status: bool = True) -> Dict[str, Any]:
        with self.lock:
            p = self.hardware_products.get(product_id)
            if not p or p["business_id"] != business_id:
                raise KeyError(f"Product '{product_id}' not found")
            p["is_archived"] = archive_status
            p["updated_at"] = datetime.utcnow().isoformat()
            return p

    def record_hardware_movement(
        self,
        business_id: str,
        product_id: str,
        movement_type: str,
        quantity: float,
        reason: Optional[str],
        user_recorded: str,
        idempotency_key: Optional[str] = None
    ) -> Dict[str, Any]:
        with self.lock:
            # 1. Idempotency Check: Prevent duplicate submissions
            if idempotency_key and idempotency_key in self.processed_idempotency_keys:
                print(f"[Idempotency] Returning previously processed movement for key {idempotency_key}")
                return self.processed_idempotency_keys[idempotency_key]

            # 2. Lock & Validate Product
            p = self.hardware_products.get(product_id)
            if not p or p["business_id"] != business_id:
                raise KeyError(f"Product '{product_id}' not found")
            if p.get("is_archived", False):
                raise ValueError(f"Cannot record movements for archived product '{p['sku']}'")

            prev_stock = float(p["current_stock"])
            m_type = movement_type.upper().strip()

            # 3. Decision Logic & Negative Stock Protection
            if m_type == "STOCK_IN":
                if quantity <= 0:
                    raise ValueError("Stock In quantity must be strictly greater than 0")
                change = float(quantity)
                new_stock = prev_stock + change

            elif m_type == "STOCK_OUT":
                if quantity <= 0:
                    raise ValueError("Stock Out quantity must be strictly greater than 0")
                if prev_stock < quantity:
                    raise ValueError(f"Movement rejected: Insufficient stock. Current stock is {prev_stock} {p['unit']}, requested out is {quantity} {p['unit']}")
                change = -float(quantity)
                new_stock = prev_stock - float(quantity)

            elif m_type == "CORRECTION":
                if quantity < 0:
                    raise ValueError("Stock correction quantity cannot be negative")
                change = float(quantity) - prev_stock
                new_stock = float(quantity)

            elif m_type == "OPENING_STOCK":
                if quantity < 0:
                    raise ValueError("Opening stock quantity cannot be negative")
                change = float(quantity)
                new_stock = float(quantity)
            else:
                raise ValueError(f"Invalid movement type '{movement_type}'")

            # 4. Atomic Update
            p["current_stock"] = new_stock
            now_str = datetime.utcnow().isoformat()
            p["updated_at"] = now_str

            mov_id = f"mov-{uuid.uuid4().hex[:10]}"
            movement_record = {
                "id": mov_id,
                "business_id": business_id,
                "product_id": product_id,
                "product_sku": p["sku"],
                "product_name": p["name"],
                "product_unit": p["unit"],
                "movement_type": m_type,
                "quantity_change": change,
                "previous_stock": prev_stock,
                "resulting_stock": new_stock,
                "reason": reason or "",
                "user_recorded": user_recorded.strip(),
                "idempotency_key": idempotency_key,
                "batch_id": None,
                "created_at": now_str
            }
            self.hardware_movements.insert(0, movement_record)

            if idempotency_key:
                self.processed_idempotency_keys[idempotency_key] = movement_record

            return movement_record

    def get_hardware_movements(
        self,
        business_id: str,
        product_id: Optional[str] = None,
        movement_type: Optional[str] = None,
        search: Optional[str] = None,
        page: int = 1,
        page_size: int = 15
    ) -> Dict[str, Any]:
        with self.lock:
            movs = [m for m in self.hardware_movements if m["business_id"] == business_id]

            if product_id:
                movs = [m for m in movs if m["product_id"] == product_id]

            if movement_type and movement_type != "ALL":
                movs = [m for m in movs if m["movement_type"] == movement_type.upper().strip()]

            if search:
                s_lower = search.lower().strip()
                movs = [
                    m for m in movs
                    if s_lower in m["product_sku"].lower()
                    or s_lower in m["product_name"].lower()
                    or s_lower in m.get("user_recorded", "").lower()
                    or s_lower in m.get("reason", "").lower()
                ]

            total = len(movs)
            total_pages = max(1, (total + page_size - 1) // page_size)
            start = (page - 1) * page_size
            end = start + page_size
            sliced = movs[start:end]

            return {
                "items": sliced,
                "total": total,
                "page": page,
                "page_size": page_size,
                "total_pages": total_pages
            }

    def get_hardware_low_stock(self, business_id: str) -> Dict[str, Any]:
        with self.lock:
            low_items = []
            zero_count = 0
            for p in self.hardware_products.values():
                if p["business_id"] != business_id or p.get("is_archived", False):
                    continue
                cur = float(p["current_stock"])
                min_s = float(p["min_stock"])
                
                # Rule: Minimum stock level of 0 disables low-stock alert
                if min_s > 0 and cur < min_s:
                    is_zero = (cur == 0.0)
                    if is_zero:
                        zero_count += 1
                    low_items.append({
                        "product_id": p["id"],
                        "sku": p["sku"],
                        "name": p["name"],
                        "current_stock": cur,
                        "unit": p["unit"],
                        "min_stock": min_s,
                        "deficit_qty": round(min_s - cur, 2),
                        "is_zero_stock": is_zero,
                        "supplier_name": p.get("supplier_name"),
                        "supplier_contact": p.get("supplier_contact")
                    })

            # Sort: zero-stock first, then highest deficit
            low_items.sort(key=lambda x: (not x["is_zero_stock"], -x["deficit_qty"]))

            return {
                "items": low_items,
                "total_low_stock": len(low_items),
                "total_zero_stock": zero_count
            }

    def batch_import_products(
        self,
        business_id: str,
        valid_rows: List[Dict[str, Any]],
        filename: str = "import.csv",
        user_recorded: str = "Shop Manager"
    ) -> Dict[str, Any]:
        with self.lock:
            batch_id = f"batch-{uuid.uuid4().hex[:10]}"
            now_str = datetime.utcnow().isoformat()
            imported_ids = []

            for row in valid_rows:
                sku = str(row["sku"]).strip()
                # Double check no collision
                existing = any(p["business_id"] == business_id and p["sku"].lower() == sku.lower() for p in self.hardware_products.values())
                if existing:
                    continue

                prod_id = f"prd-{uuid.uuid4().hex[:12]}"
                opening_stock = float(row.get("opening_stock", 0.0))
                min_stock = float(row.get("min_stock", 0.0))

                product = {
                    "id": prod_id,
                    "business_id": business_id,
                    "sku": sku,
                    "name": str(row["name"]).strip(),
                    "unit": str(row.get("unit", "pcs")).lower().strip(),
                    "current_stock": opening_stock,
                    "min_stock": min_stock,
                    "supplier_name": row.get("supplier_name") or None,
                    "supplier_contact": row.get("supplier_contact") or None,
                    "is_archived": False,
                    "created_at": now_str,
                    "updated_at": now_str,
                    "import_batch_id": batch_id
                }
                self.hardware_products[prod_id] = product
                imported_ids.append(prod_id)

                # Record OPENING_STOCK movement linked to this batch
                mov_id = f"mov-{uuid.uuid4().hex[:8]}"
                self.hardware_movements.insert(0, {
                    "id": mov_id,
                    "business_id": business_id,
                    "product_id": prod_id,
                    "product_sku": sku,
                    "product_name": product["name"],
                    "product_unit": product["unit"],
                    "movement_type": "OPENING_STOCK",
                    "quantity_change": opening_stock,
                    "previous_stock": 0.0,
                    "resulting_stock": opening_stock,
                    "reason": f"Bulk CSV import [{filename}]",
                    "user_recorded": user_recorded,
                    "idempotency_key": f"import-{batch_id}-{prod_id}",
                    "batch_id": batch_id,
                    "created_at": now_str
                })

            batch_record = {
                "id": batch_id,
                "business_id": business_id,
                "filename": filename,
                "total_rows": len(valid_rows),
                "imported_count": len(imported_ids),
                "imported_product_ids": imported_ids,
                "reversed": False,
                "reversed_at": None,
                "created_at": now_str
            }
            self.hardware_import_batches[batch_id] = batch_record

            return {
                "batch_id": batch_id,
                "imported_count": len(imported_ids),
                "total_processed": len(valid_rows),
                "message": f"Successfully imported {len(imported_ids)} hardware products",
                "can_reverse": True
            }

    def reverse_import_batch(self, business_id: str, batch_id: str) -> Dict[str, Any]:
        with self.lock:
            batch = self.hardware_import_batches.get(batch_id)
            if not batch or batch["business_id"] != business_id:
                raise KeyError(f"Import batch '{batch_id}' not found")

            if batch.get("reversed", False):
                raise ValueError("This import batch has already been reversed")

            product_ids = batch.get("imported_product_ids", [])
            
            # Check subsequent stock activity for ANY of these products
            # Rule: Reversal allowed ONLY when products have no subsequent stock activity
            subsequent_movements = [
                m for m in self.hardware_movements
                if m["product_id"] in product_ids and m.get("batch_id") != batch_id
            ]

            if subsequent_movements:
                conflict_prod = subsequent_movements[0]["product_sku"]
                conflict_type = subsequent_movements[0]["movement_type"]
                raise ValueError(
                    f"Import batch cannot be reversed: Product '{conflict_prod}' has subsequent stock activity ({conflict_type}). "
                    f"Reversing this import would cause historical ledger inconsistency."
                )

            # Perform safe reversal: Delete products and their initial opening stock movements
            for pid in product_ids:
                if pid in self.hardware_products:
                    del self.hardware_products[pid]

            # Remove batch movements
            self.hardware_movements = [m for m in self.hardware_movements if m.get("batch_id") != batch_id]

            batch["reversed"] = True
            batch["reversed_at"] = datetime.utcnow().isoformat()

            return {
                "batch_id": batch_id,
                "reversed": True,
                "deleted_products_count": len(product_ids),
                "message": f"Import batch successfully reversed. {len(product_ids)} products and opening movements rolled back."
            }

    # --- Hardware Staff Management (Owner Access Only) ---
    def get_hardware_staff(self, business_id: str) -> Dict[str, Any]:
        with self.lock:
            staff_list = [s for s in self.hardware_staff.values() if s.get("business_id") == business_id]
            staff_list.sort(key=lambda x: x["created_at"])
            return {
                "staff": staff_list,
                "total": len(staff_list)
            }

    def create_hardware_staff(self, business_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        with self.lock:
            username = data["username"].strip().lower()
            # Check unique username per business
            for s in self.hardware_staff.values():
                if s.get("business_id") == business_id and s["username"].lower() == username:
                    raise ValueError(f"Staff username '{data['username']}' already exists.")

            staff_id = f"staff-{uuid.uuid4().hex[:8]}"
            record = {
                "id": staff_id,
                "business_id": business_id,
                "name": data["name"].strip(),
                "username": username,
                "role": data.get("role", "Floor Staff"),
                "is_active": True,
                "created_at": datetime.utcnow().isoformat()
            }
            self.hardware_staff[staff_id] = record
            return record

    def toggle_hardware_staff_status(self, business_id: str, staff_id: str, is_active: Optional[bool] = None) -> Dict[str, Any]:
        with self.lock:
            staff = self.hardware_staff.get(staff_id)
            if not staff or staff.get("business_id") != business_id:
                raise ValueError("Staff member not found")
            if is_active is not None:
                staff["is_active"] = is_active
            else:
                staff["is_active"] = not staff["is_active"]
            return staff

    def delete_hardware_staff(self, business_id: str, staff_id: str) -> bool:
        with self.lock:
            staff = self.hardware_staff.get(staff_id)
            if not staff or staff.get("business_id") != business_id:
                raise ValueError("Staff member not found")
            del self.hardware_staff[staff_id]
            return True

    # --- Legacy Compatibility Methods ---
=======
    # Items CRUD
>>>>>>> parent of e10ef376 (617)
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

