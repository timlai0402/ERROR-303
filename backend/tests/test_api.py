import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.services.inventory_engine import inventory_engine
from app.services.forecasting import forecaster

client = TestClient(app)

def test_root():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["product"] == "StockWise AI"
    assert "FastAPI Business Logic" in data["features"]

def test_inventory_list():
    response = client.get("/api/inventory")
    assert response.status_code == 200
    items = response.json()
    assert len(items) > 0
    assert "available" in items[0]
    assert "status" in items[0]

def test_deterministic_eoq_rop():
    # Test EOQ: D=1000, S=50, H=2.0 -> sqrt(2 * 1000 * 50 / 2) = sqrt(50000) ~= 223.61
    eoq = inventory_engine.calculate_eoq(annual_demand=1000, order_setup_cost=50, unit_cost=10, holding_pct=0.20)
    assert round(eoq, 1) == 223.6

    # Test ROP: daily=10, lead=5, safety=20 -> (10 * 5) + 20 = 70
    rop = inventory_engine.calculate_rop(daily_demand=10, lead_time_days=5, safety_stock=20)
    assert rop == 70.0

def test_statistical_forecasting():
    history = [10.0, 12.0, 11.0, 13.0, 15.0, 14.0, 16.0]
    res = forecaster.generate_material_requirement_forecast(
        item_id="TEST-001",
        historical_consumption=history,
        lead_time_days=5,
        horizon=10,
        method="holt_winters"
    )
    assert res["itemId"] == "TEST-001"
    assert len(res["forecast_values"]) == 10
    assert res["safety_stock_recommended"] > 0
    assert res["reorder_point_calculated"] > 0
    assert "upper" in res["confidence_interval_95"]

def test_workspace_sync():
    response = client.get("/api/workspace")
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "items" in data["data"]
    assert "valuation" in data

def test_procurement_human_approval_flow():
    # 1. Create a draft PO
    create_res = client.post("/api/purchase-requests/action", json={
        "action": "create",
        "itemId": "RAW-001",
        "quantity": 25.0,
        "supplier": "Precision Parts Ltd",
        "reason": "Replenishment for upcoming batch"
    })
    assert create_res.status_code == 200
    po = create_res.json()["po"]
    po_id = po["id"]
    assert po["status"] == "Draft"

    # 2. Submit for manager approval
    submit_res = client.post("/api/purchase-requests/action", json={
        "id": po_id,
        "action": "submit"
    })
    assert submit_res.status_code == 200
    assert submit_res.json()["status"] == "Pending"

    # 3. Manager approves (Human gate)
    approve_res = client.post("/api/purchase-requests/action", json={
        "id": po_id,
        "action": "approve"
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "Approved"

