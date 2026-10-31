from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import date, datetime

# --- Inventory Item Models ---
class ItemBase(BaseModel):
    id: str = Field(..., examples=["BLD-001"])
    name: str = Field(..., examples=["Portland Cement 50kg"])
    category: str = Field(..., examples=["Building materials"])
    physical: float = Field(..., ge=0, examples=[45.0])
    reserved: float = Field(..., ge=0, examples=[15.0])
    reorder: float = Field(..., ge=0, examples=[30.0])
    safety: float = Field(..., ge=0, examples=[15.0])
    cost: float = Field(..., ge=0, examples=[21.50])
    unit: str = Field(..., examples=["bags"])
    supplier: str = Field(..., examples=["SolidBuild Materials"])
    lead: int = Field(..., ge=1, examples=[3])
    minOrder: float = Field(..., ge=1, examples=[20.0])
    daily: float = Field(..., ge=0, examples=[2.5])
    initialDemand: Optional[float] = Field(None, examples=[75.0])

class ItemCreate(ItemBase):
    pass

class ItemResponse(ItemBase):
    available: float
    status: str # 'OUT_OF_STOCK', 'CRITICAL', 'REORDER', 'HEALTHY'
    holding_cost_pct: Optional[float] = 0.20

# --- Supplier Models ---
class SupplierBase(BaseModel):
    id: str = Field(..., examples=["SUP-01"])
    name: str = Field(..., examples=["SolidBuild Materials"])
    items: str = Field(..., examples=["Cement, aggregate, bricks"])
    lead: int = Field(..., ge=1, examples=[3])
    reliability: float = Field(..., ge=0, le=100, examples=[96.0])
    terms: str = Field(..., examples=["Net 30"])

# --- Order / Demand Models ---
class OrderBase(BaseModel):
    id: str = Field(..., examples=["ORD-101"])
    customer: str = Field(..., examples=["Riverside Apartments"])
    itemName: str = Field(..., examples=["Cement"])
    itemId: Optional[str] = Field(None, examples=["BLD-001"])
    quantity: float = Field(..., ge=1, examples=[1.0])
    demand: float = Field(..., ge=1, examples=[25.0])
    due: str = Field(..., examples=["2026-11-05"])
    type: str = Field("Customer order", examples=["Customer order"])
    status: str = Field("Confirmed", examples=["Confirmed"])

# --- Procurement & Purchase Order Models ---
class PurchaseOrderCreate(BaseModel):
    itemId: str
    quantity: float = Field(..., gt=0)
    unitCost: Optional[float] = None
    supplier: Optional[str] = None
    reason: Optional[str] = None
    additionalReason: Optional[str] = None

class PurchaseOrderAction(BaseModel):
    id: Optional[str] = None
    action: str = Field(..., examples=["approve"]) # create, submit, approve, reject, return, cancel
    itemId: Optional[str] = None
    quantity: Optional[float] = None
    unitCost: Optional[float] = None
    supplier: Optional[str] = None
    reason: Optional[str] = None
    additionalReason: Optional[str] = None
    expectedRevision: Optional[int] = None
    version: Optional[int] = None

class PurchaseOrderResponse(BaseModel):
    id: str
    itemId: str
    itemName: str
    quantity: float
    unitCost: float
    total: float
    supplier: str
    status: str # Draft, Pending, Approved, Rejected, Returned, Ordered
    revision: int = 0
    createdBy: str
    createdByName: str
    createdAt: str
    aiRationale: Optional[str] = None
    aiRiskLevel: Optional[str] = "Low"

# --- Human-in-the-Loop Audit ---
class ActivityLog(BaseModel):
    title: str
    detail: str
    time: str = "Just now"

# --- Statistical Forecasting Models ---
class ForecastRequest(BaseModel):
    itemId: str
    historical_periods: List[float] = Field(..., description="Chronological sales/usage quantities")
    horizon: int = Field(default=30, ge=1, le=180, description="Forecast horizon in days")
    method: str = Field(default="holt_winters", examples=["holt_winters"]) # sma, exponential_smoothing, holt_winters

class ForecastResponse(BaseModel):
    itemId: str
    method_used: str
    forecast_values: List[float]
    projected_daily_demand: float
    safety_stock_recommended: float
    reorder_point_calculated: float
    confidence_interval_95: Dict[str, List[float]]

# --- GenAI Decision Support ---
class AIAdvisorRequest(BaseModel):
    itemId: str
    current_stock: float
    reserved_stock: float
    reorder_point: float
    supplier_lead_time_days: int
    pending_demand: float
    unit_cost: float
    recent_market_news: Optional[List[str]] = []

class AIAdvisorResponse(BaseModel):
    action_recommendation: str # 'ORDER_NOW', 'DEFER', 'URGENT_SURCHARGE_CHECK'
    recommended_quantity: float
    plain_language_rationale: str
    supply_risk_assessment: str
    suggested_negotiation_point: str

# --- Market Intelligence Models ---
class NewsItem(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    publishedAt: Optional[str] = None
    category: str
    sentiment: float
    supply_risk: str
    impact_summary: str

# --- Workspace Synchronizer ---
class CompanySettings(BaseModel):
    business: str = "Northstar Manufacturing"
    industry: str = "Manufacturing"
    currency: str = "MYR"
    safety: float = 20.0
    waste: float = 5.0

class WorkspaceState(BaseModel):
    items: List[ItemResponse]
    orders: List[OrderBase]
    suppliers: List[SupplierBase]
    pos: List[PurchaseOrderResponse]
    activities: List[ActivityLog]
    settings: CompanySettings
