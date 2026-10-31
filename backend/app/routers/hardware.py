import csv
import io
import re
from fastapi import APIRouter, HTTPException, Query, Response
from typing import Optional, List, Dict, Any
from app.db.supabase_client import db
from app.models.hardware_schemas import (
    ProductCreate, ProductUpdate, ProductResponse, ProductListResponse,
    StockMovementCreate, StockMovementResponse, MovementListResponse,
    LowStockSummary, CSVValidateRequest, CSVValidateResponse, CSVRowError,
    CSVConfirmImportRequest, CSVImportResult, CSVReverseResponse,
    VALID_UNITS
)

router = APIRouter(prefix="/hardware", tags=["Hardware Shop Inventory"])

DEFAULT_BIZ_ID = "biz-hardware-01"

@router.get("/products", response_model=ProductListResponse)
def list_products(
    search: Optional[str] = Query(None, description="Search by SKU, Name, or Supplier"),
    status: str = Query("active", description="'active', 'archived', or 'all'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """Answers question 1: 'What stock do I have?' with pagination & search."""
    res = db.get_hardware_products(
        business_id=business_id,
        search=search,
        status=status,
        page=page,
        page_size=page_size
    )
    return res

@router.post("/products", response_model=ProductResponse)
def create_product(
    payload: ProductCreate,
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """Create a new hardware product and record its initial opening stock movement."""
    try:
        created = db.create_hardware_product(business_id, payload.model_dump())
        return created
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(
    product_id: str,
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    prod = db.get_hardware_product(business_id, product_id)
    if not prod:
        raise HTTPException(status_code=404, detail="Product not found")
    return prod

@router.put("/products/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    payload: ProductUpdate,
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """Update product details. Rejects unit changes once movements exist."""
    try:
        updated = db.update_hardware_product(
            business_id, 
            product_id, 
            payload.model_dump(exclude_unset=True)
        )
        return updated
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.patch("/products/{product_id}/archive", response_model=ProductResponse)
def archive_product(
    product_id: str,
    archive: bool = Query(True),
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """Archive or unarchive a product."""
    try:
        return db.archive_hardware_product(business_id, product_id, archive)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

# --- Stock Movements ---

@router.get("/movements", response_model=MovementListResponse)
def list_movements(
    product_id: Optional[str] = Query(None),
    movement_type: Optional[str] = Query(None, description="STOCK_IN, STOCK_OUT, CORRECTION, OPENING_STOCK, or ALL"),
    search: Optional[str] = Query(None, description="Search by SKU, product name, or staff user"),
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """Answers question 2: 'What stock came in or went out?'"""
    return db.get_hardware_movements(
        business_id=business_id,
        product_id=product_id,
        movement_type=movement_type,
        search=search,
        page=page,
        page_size=page_size
    )

@router.post("/movements", response_model=StockMovementResponse)
def record_movement(
    payload: StockMovementCreate,
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """
    Atomically records a stock movement and updates current stock.
    Rejects movements that produce negative stock.
    Idempotent when idempotency_key is supplied.
    """
    try:
        result = db.record_hardware_movement(
            business_id=business_id,
            product_id=payload.product_id,
            movement_type=payload.movement_type.value,
            quantity=payload.quantity,
            reason=payload.reason,
            user_recorded=payload.user_recorded,
            idempotency_key=payload.idempotency_key
        )
        return result
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

# --- Low Stock List ---

@router.get("/low-stock", response_model=LowStockSummary)
def get_low_stock(
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """
    Answers question 3: 'What needs restocking?'
    Returns non-archived products whose current quantity is below their minimum stock level.
    Minimum stock level of 0 disables alerts.
    """
    return db.get_hardware_low_stock(business_id=business_id)

# --- CSV Import & Export (Deterministic, Zero AI) ---

@router.post("/import/validate", response_model=CSVValidateResponse)
def validate_csv(
    payload: CSVValidateRequest
):
    """
    Step 3 & 4 of import flow: Validates CSV content thoroughly before committing.
    Preserves leading zeros in SKUs.
    Detects required field omissions, invalid numbers, unsupported units,
    file duplicates, and existing business SKUs.
    """
    content = payload.csv_content.strip()
    if not content:
        raise HTTPException(status_code=400, detail="CSV content is empty")

    business_id = payload.business_id or DEFAULT_BIZ_ID
    existing_products = db.get_hardware_products(business_id=business_id, status="all", page_size=10000)["items"]
    existing_skus = {p["sku"].lower(): p["name"] for p in existing_products}

    reader = csv.reader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=400, detail="CSV contains no rows")

    header = [h.strip().lower().replace(" ", "_") for h in rows[0]]
    
    # Map header columns
    sku_idx = -1
    name_idx = -1
    unit_idx = -1
    opening_idx = -1
    min_stock_idx = -1
    supplier_name_idx = -1
    supplier_contact_idx = -1

    for idx, col in enumerate(header):
        if col in ["sku", "product_code", "code", "item_code"]:
            sku_idx = idx
        elif col in ["name", "product_name", "item_name", "description"]:
            name_idx = idx
        elif col in ["unit", "stock_unit", "uom"]:
            unit_idx = idx
        elif col in ["opening_stock", "current_stock", "quantity", "qty", "stock"]:
            opening_idx = idx
        elif col in ["min_stock", "minimum_stock", "reorder_level", "min_level"]:
            min_stock_idx = idx
        elif col in ["supplier_name", "supplier", "vendor"]:
            supplier_name_idx = idx
        elif col in ["supplier_contact", "contact", "phone", "supplier_phone"]:
            supplier_contact_idx = idx

    errors: List[CSVRowError] = []
    preview_valid: List[Dict[str, Any]] = []
    seen_skus_in_file = {}

    if sku_idx == -1:
        errors.append(CSVRowError(row_number=1, field="header", error="Missing required header: 'sku' or 'product_code'"))
    if name_idx == -1:
        errors.append(CSVRowError(row_number=1, field="header", error="Missing required header: 'name' or 'product_name'"))

    if errors:
        return CSVValidateResponse(
            total_rows=len(rows) - 1,
            valid_count=0,
            error_count=len(errors),
            errors=errors,
            preview_valid=[],
            can_import=False
        )

    for row_num, row in enumerate(rows[1:], start=2):
        if not row or all(not cell.strip() for cell in row):
            continue # Skip blank rows safely

        row_sku = row[sku_idx].strip() if sku_idx < len(row) else ""
        row_name = row[name_idx].strip() if name_idx < len(row) else ""
        row_unit = row[unit_idx].strip().lower() if (unit_idx != -1 and unit_idx < len(row)) else "pcs"
        if not row_unit:
            row_unit = "pcs"

        row_opening_str = row[opening_idx].strip() if (opening_idx != -1 and opening_idx < len(row)) else "0"
        row_min_str = row[min_stock_idx].strip() if (min_stock_idx != -1 and min_stock_idx < len(row)) else "0"
        row_supp_name = row[supplier_name_idx].strip() if (supplier_name_idx != -1 and supplier_name_idx < len(row)) else ""
        row_supp_contact = row[supplier_contact_idx].strip() if (supplier_contact_idx != -1 and supplier_contact_idx < len(row)) else ""

        row_has_error = False

        # 1. Required SKU & preserve leading zeros
        if not row_sku:
            errors.append(CSVRowError(row_number=row_num, field="sku", error="SKU is required and cannot be empty"))
            row_has_error = True
        elif len(row_sku) > 50:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="sku", error="SKU exceeds maximum length of 50 characters"))
            row_has_error = True

        # 2. Required Name
        if not row_name:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="name", error="Product name is required"))
            row_has_error = True
        elif len(row_name) > 150:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="name", error="Product name exceeds 150 characters"))
            row_has_error = True

        # 3. Unit validation
        if row_unit not in VALID_UNITS:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="unit", error=f"Unsupported unit '{row_unit}'. Supported: {', '.join(VALID_UNITS)}"))
            row_has_error = True

        # 4. Opening stock validation (nonnegative numeric)
        opening_qty = 0.0
        try:
            opening_qty = float(row_opening_str) if row_opening_str else 0.0
            if opening_qty < 0:
                errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="opening_stock", error="Opening stock cannot be negative"))
                row_has_error = True
        except ValueError:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="opening_stock", error=f"Invalid numeric quantity: '{row_opening_str}'"))
            row_has_error = True

        # 5. Min stock validation (nonnegative numeric)
        min_qty = 0.0
        try:
            min_qty = float(row_min_str) if row_min_str else 0.0
            if min_qty < 0:
                errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="min_stock", error="Minimum stock level cannot be negative"))
                row_has_error = True
        except ValueError:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="min_stock", error=f"Invalid numeric minimum stock: '{row_min_str}'"))
            row_has_error = True

        # 6. Duplicate SKU in file
        sku_clean = row_sku.lower()
        if sku_clean in seen_skus_in_file:
            first_row = seen_skus_in_file[sku_clean]
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="sku", error=f"Duplicate SKU '{row_sku}' in CSV (first seen on row {first_row})"))
            row_has_error = True
        else:
            seen_skus_in_file[sku_clean] = row_num

        # 7. SKU already exists in business
        if sku_clean in existing_skus:
            errors.append(CSVRowError(row_number=row_num, sku=row_sku, field="sku", error=f"SKU '{row_sku}' already exists in store catalog ('{existing_skus[sku_clean]}'). Overwrites are disabled in v1."))
            row_has_error = True

        if not row_has_error:
            preview_valid.append({
                "row_number": row_num,
                "sku": row_sku, # Exact string with leading zeros preserved
                "name": row_name,
                "unit": row_unit,
                "opening_stock": opening_qty,
                "min_stock": min_qty,
                "supplier_name": row_supp_name or None,
                "supplier_contact": row_supp_contact or None
            })

    total_data_rows = len(rows) - 1
    can_import = len(errors) == 0 and len(preview_valid) > 0

    return CSVValidateResponse(
        total_rows=total_data_rows,
        valid_count=len(preview_valid),
        error_count=len(errors),
        errors=errors,
        preview_valid=preview_valid,
        can_import=can_import
    )

@router.post("/import/confirm", response_model=CSVImportResult)
def confirm_import(
    payload: CSVConfirmImportRequest
):
    """
    Step 5 & 6 of import flow: Imports valid rows and records batch ID and opening stock movements.
    """
    if not payload.valid_rows:
        raise HTTPException(status_code=400, detail="No valid rows provided for import")

    business_id = payload.business_id or DEFAULT_BIZ_ID
    result = db.batch_import_products(
        business_id=business_id,
        valid_rows=payload.valid_rows,
        filename=payload.filename or "import.csv",
        user_recorded=payload.user_recorded or "Shop Staff"
    )
    return result

@router.post("/import/reverse/{batch_id}", response_model=CSVReverseResponse)
def reverse_import(
    batch_id: str,
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """
    Reverses an import batch ONLY when its products have had no subsequent stock activity.
    If subsequent movements exist, rejects reversal and explains why.
    """
    try:
        return db.reverse_import_batch(business_id=business_id, batch_id=batch_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

@router.get("/export")
def export_products_csv(
    business_id: str = Query(DEFAULT_BIZ_ID)
):
    """Allows shop owners to export their complete product records to CSV."""
    prods = db.get_hardware_products(business_id=business_id, status="all", page_size=10000)["items"]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Product Code / SKU",
        "Product Name",
        "Stock Unit",
        "Current Stock",
        "Minimum Stock",
        "Deficit Quantity",
        "Supplier Name",
        "Supplier Contact",
        "Status"
    ])

    for p in prods:
        writer.writerow([
            f'="{p["sku"]}"', # Preserve leading zeros in spreadsheet tools (Excel/Calc)
            p["name"],
            p["unit"],
            p["current_stock"],
            p["min_stock"],
            p.get("deficit_qty", 0.0),
            p.get("supplier_name") or "",
            p.get("supplier_contact") or "",
            "Archived" if p.get("is_archived") else "Active"
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hardware_products_inventory.csv"}
    )

@router.get("/sample-template")
def download_sample_template():
    """Returns downloadable CSV template for small hardware stores."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "sku",
        "name",
        "unit",
        "opening_stock",
        "min_stock",
        "supplier_name",
        "supplier_contact"
    ])
    writer.writerow(["00142", "Flange Nut M10 Zinc-Plated", "pcs", 100, 30, "MegaFasteners Malaysia", "+6012-3334455"])
    writer.writerow(["SPK-NGK-09", "Spark Plug CR8E", "pcs", 12, 10, "AutoPro Spares", "+6019-8765432"])
    writer.writerow(["WD-40-330", "WD-40 Multi-Use Lubricant Spray 330ml", "can", 24, 6, "ChemLub Lubricants", "+6013-4567890"])
    
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=hardware_inventory_template.csv"}
    )

@router.get("/demo/operational-journey")
def get_operational_journey_summary():
    """
    Returns the step-by-step metadata for the single operational journey
    (Trigger -> Connected Data -> Decision Logic -> Human Approval -> Visible Outcome -> Scale)
    for small hardware shop live presentations.
    """
    return {
        "sme_domain": "Independent Hardware Shop & Auto-Mechanics",
        "specific_pain_point": "Mechanics running out of fast-moving maintenance items (e.g., oil filters, flange bolts) midway through customer repair jobs due to spreadsheet recount errors.",
        "journey_steps": [
            {
                "step": 1,
                "name": "Trigger",
                "description": "Mechanic consumes 8 units of oil filter FLT-02 for morning servicing orders, dropping stock from 16 to 8."
            },
            {
                "step": 2,
                "name": "Connected Data",
                "description": "System immediately connects SKU FLT-02 with its 20-unit threshold, supplier 'Huat Kee Auto Spares', and phone '+6012-8889999'."
            },
            {
                "step": 3,
                "name": "Decision Logic",
                "description": "Deterministic deficit calculation flags product as LOW STOCK with an exact replenishment deficit of 12 units."
            },
            {
                "step": 4,
                "name": "Human Approval",
                "description": "Shop manager inspects delivery DO-4481 and signs off on a 12-unit Stock In replenishment."
            },
            {
                "step": 5,
                "name": "Visible Outcome",
                "description": "Stock balance updates to 20 units atomically, audit movement is committed to ledger, and low-stock alert clears."
            },
            {
                "step": 6,
                "name": "Scale",
                "description": "Shop scales catalog to 1,000+ hardware items with column-matched CSV validation and tenant isolation."
            }
        ]
    }

