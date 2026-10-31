from pydantic import BaseModel, Field, field_validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum

class MovementType(str, Enum):
    OPENING_STOCK = "OPENING_STOCK"
    STOCK_IN = "STOCK_IN"
    STOCK_OUT = "STOCK_OUT"
    CORRECTION = "CORRECTION"

VALID_UNITS = [
    "pcs", "box", "set", "kg", "meter", "roll", 
    "pack", "pair", "can", "bottle", "drum", "carton"
]

# --- Product Models ---
class ProductBase(BaseModel):
    sku: str = Field(..., min_length=1, max_length=50, description="Product code / SKU, unique per business")
    name: str = Field(..., min_length=1, max_length=150, description="Product name")
    unit: str = Field(default="pcs", description="Fixed stock unit")
    min_stock: float = Field(default=0.0, ge=0.0, description="Minimum stock level. 0 disables alerts.")
    supplier_name: Optional[str] = Field(None, max_length=150, description="Optional supplier name")
    supplier_contact: Optional[str] = Field(None, max_length=150, description="Optional supplier contact information")

    @field_validator("sku")
    @classmethod
    def validate_sku(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("SKU cannot be empty")
        return s

    @field_validator("unit")
    @classmethod
    def validate_unit(cls, v: str) -> str:
        clean = v.strip().lower()
        if clean not in VALID_UNITS:
            raise ValueError(f"Invalid unit '{v}'. Supported units: {', '.join(VALID_UNITS)}")
        return clean

class ProductCreate(ProductBase):
    opening_stock: float = Field(default=0.0, ge=0.0, description="Initial stock quantity to record as OPENING_STOCK")
    user_recorded: Optional[str] = Field(default="Shop Manager", description="User recording the initial product creation")

class ProductUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=150)
    min_stock: Optional[float] = Field(None, ge=0.0)
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None
    # Note: unit is deliberately omitted to prevent changing units once movements exist!

class ProductResponse(ProductBase):
    id: str
    business_id: str
    current_stock: float
    is_archived: bool = False
    is_low_stock: bool = False
    is_zero_stock: bool = False
    deficit_qty: float = 0.0
    created_at: str
    updated_at: str

class ProductListResponse(BaseModel):
    items: List[ProductResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

# --- Stock Movement Models ---
class StockMovementCreate(BaseModel):
    product_id: str
    movement_type: MovementType
    quantity: float = Field(..., description="Quantity to move (must be > 0 for IN/OUT, >= 0 for CORRECTION)")
    reason: Optional[str] = Field(None, max_length=250, description="Reason or note for this movement")
    user_recorded: str = Field(..., min_length=1, max_length=100, description="Name or ID of user who recorded it")
    idempotency_key: Optional[str] = Field(None, description="Client-provided unique key to prevent duplicate submissions")

class StockMovementResponse(BaseModel):
    id: str
    business_id: str
    product_id: str
    product_sku: str
    product_name: str
    product_unit: str
    movement_type: str
    quantity_change: float
    previous_stock: float
    resulting_stock: float
    reason: Optional[str] = None
    user_recorded: str
    idempotency_key: Optional[str] = None
    batch_id: Optional[str] = None
    created_at: str

class MovementListResponse(BaseModel):
    items: List[StockMovementResponse]
    total: int
    page: int
    page_size: int
    total_pages: int

# --- Low Stock Models ---
class LowStockItem(BaseModel):
    product_id: str
    sku: str
    name: str
    current_stock: float
    unit: str
    min_stock: float
    deficit_qty: float
    is_zero_stock: bool
    supplier_name: Optional[str] = None
    supplier_contact: Optional[str] = None

class LowStockSummary(BaseModel):
    items: List[LowStockItem]
    total_low_stock: int
    total_zero_stock: int

# --- CSV Import & Export Models ---
class CSVRowError(BaseModel):
    row_number: int
    sku: Optional[str] = None
    field: str
    error: str

class CSVValidateRequest(BaseModel):
    csv_content: str
    business_id: Optional[str] = "biz-hardware-01"

class CSVValidateResponse(BaseModel):
    total_rows: int
    valid_count: int
    error_count: int
    errors: List[CSVRowError]
    preview_valid: List[Dict[str, Any]]
    can_import: bool

class CSVConfirmImportRequest(BaseModel):
    valid_rows: List[Dict[str, Any]]
    filename: Optional[str] = "products_import.csv"
    user_recorded: Optional[str] = "Shop Manager"
    business_id: Optional[str] = "biz-hardware-01"

class CSVImportResult(BaseModel):
    batch_id: str
    imported_count: int
    total_processed: int
    message: str
    can_reverse: bool = True

class CSVReverseResponse(BaseModel):
    batch_id: str
    reversed: bool
    deleted_products_count: int
    message: str
