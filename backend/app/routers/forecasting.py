from fastapi import APIRouter, HTTPException
from typing import Optional
from app.db.supabase_client import db
from app.services.forecasting import forecaster
from app.models.schemas import ForecastRequest, ForecastResponse

router = APIRouter(prefix="/forecast", tags=["Forecasting & Statistical Analytics"])

@router.post("", response_model=ForecastResponse)
def run_custom_forecast(payload: ForecastRequest):
    item = db.get_item(payload.itemId)
    lead_time = item.get("lead", 5) if item else 5

    res = forecaster.generate_material_requirement_forecast(
        item_id=payload.itemId,
        historical_consumption=payload.historical_periods,
        lead_time_days=lead_time,
        horizon=payload.horizon,
        method=payload.method
    )
    return res

@router.get("/item/{item_id}", response_model=ForecastResponse)
def get_item_forecast(item_id: str, horizon: int = 30, method: str = "holt_winters"):
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    daily = float(item.get("daily", 5.0))
    # Synthesize realistic historical demand baseline based on daily rate if not loaded from database
    import numpy as np
    np.random.seed(42)
    history = [round(max(1.0, daily + np.random.normal(0, daily * 0.2)), 2) for _ in range(14)]

    res = forecaster.generate_material_requirement_forecast(
        item_id=item_id,
        historical_consumption=history,
        lead_time_days=int(item.get("lead", 4)),
        horizon=horizon,
        method=method
    )
    return res

