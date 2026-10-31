import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db.supabase_client import db

client = TestClient(app)

def test_hardware_product_list():
    """Verify Question 1: What stock do I have?"""
    res = client.get("/api/hardware/products")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 10
    assert "page" in data
    assert "page_size" in data

    # Check structure of products
    first = data["items"][0]
    assert "sku" in first
    assert "name" in first
    assert "unit" in first
    assert "current_stock" in first
    assert "min_stock" in first

def test_hardware_create_product_and_opening_stock():
    """Verify creating a product records initial opening stock as a movement."""
    payload = {
        "sku": "TST-BOLT-001",
        "name": "M10 Zinc Hex Bolt 50mm",
        "unit": "pcs",
        "opening_stock": 75.0,
        "min_stock": 25.0,
        "supplier_name": "Test Fasteners Sdn Bhd",
        "supplier_contact": "+6012-1112233",
        "user_recorded": "Tester Alex"
    }
    res = client.post("/api/hardware/products", json=payload)
    assert res.status_code == 200
    prod = res.json()
    assert prod["sku"] == "TST-BOLT-001"
    assert prod["current_stock"] == 75.0
    prod_id = prod["id"]

    # Verify opening stock was recorded in movements history
    mov_res = client.get(f"/api/hardware/movements?product_id={prod_id}")
    assert mov_res.status_code == 200
    movs = mov_res.json()["items"]
    assert len(movs) == 1
    assert movs[0]["movement_type"] == "OPENING_STOCK"
    assert movs[0]["quantity_change"] == 75.0
    assert movs[0]["resulting_stock"] == 75.0
    assert movs[0]["user_recorded"] == "Tester Alex"

def test_hardware_duplicate_sku_rejected():
    """SKU must be unique per business."""
    payload = {
        "sku": "BLT-08-040", # Already in seed data
        "name": "Duplicate Hex Bolt",
        "unit": "pcs",
        "opening_stock": 10.0,
        "min_stock": 5.0
    }
    res = client.post("/api/hardware/products", json=payload)
    assert res.status_code == 400
    assert "already exists" in res.json()["detail"].lower()

def test_hardware_unit_change_disallowed_after_movements():
    """Unit cannot be changed once stock movements exist."""
    prods = client.get("/api/hardware/products").json()["items"]
    target = prods[0]
    prod_id = target["id"]

    # Try changing unit from pcs to kg
    update_res = client.put(f"/api/hardware/products/{prod_id}", json={
        "unit": "kg",
        "name": target["name"]
    })
    # Since model excludes unit or rejects unit change when movements exist:
    # Notice ProductUpdate doesn't even accept unit (deliberately omitted)
    # If sent to the db client:
    with pytest.raises(ValueError, match="Cannot change unit once stock movements exist"):
        db.update_hardware_product(
            business_id="biz-hardware-01",
            product_id=prod_id,
            data={"unit": "box"}
        )

def test_hardware_stock_in_and_history():
    """Verify Question 2: What stock came in or went out? Test Stock In."""
    prods = client.get("/api/hardware/products").json()["items"]
    target = prods[0]
    prod_id = target["id"]
    prev_stock = target["current_stock"]

    res = client.post("/api/hardware/movements", json={
        "product_id": prod_id,
        "movement_type": "STOCK_IN",
        "quantity": 30.0,
        "reason": "Replenishment delivery DO-9981",
        "user_recorded": "Warehouse Lead Lim"
    })
    assert res.status_code == 200
    movement = res.json()
    assert movement["movement_type"] == "STOCK_IN"
    assert movement["quantity_change"] == 30.0
    assert movement["previous_stock"] == prev_stock
    assert movement["resulting_stock"] == prev_stock + 30.0

    # Verify updated product stock
    updated_prod = client.get(f"/api/hardware/products/{prod_id}").json()
    assert updated_prod["current_stock"] == prev_stock + 30.0

def test_hardware_stock_out_negative_stock_rejected():
    """Reject movements that would produce negative stock."""
    prods = client.get("/api/hardware/products").json()["items"]
    target = prods[0]
    prod_id = target["id"]
    cur_stock = target["current_stock"]

    # Attempt to stock out more than current stock
    excess_qty = cur_stock + 500.0
    res = client.post("/api/hardware/movements", json={
        "product_id": prod_id,
        "movement_type": "STOCK_OUT",
        "quantity": excess_qty,
        "reason": "Massive sale attempt",
        "user_recorded": "Counter Staff"
    })
    assert res.status_code == 400
    assert "insufficient stock" in res.json()["detail"].lower()

def test_hardware_movement_idempotency():
    """Prevent duplicate submissions from applying the same movement twice."""
    prods = client.get("/api/hardware/products").json()["items"]
    target = next(p for p in prods if p["current_stock"] >= 10)
    prod_id = target["id"]
    initial_stock = target["current_stock"]

    key = "idem-test-key-12345"
    payload = {
        "product_id": prod_id,
        "movement_type": "STOCK_OUT",
        "quantity": 5.0,
        "reason": "Counter sale order #5512",
        "user_recorded": "Counter Ah Meng",
        "idempotency_key": key
    }

    # First submission
    res1 = client.post("/api/hardware/movements", json=payload)
    assert res1.status_code == 200
    m1 = res1.json()

    # Second repeated submission with same key (simulating double click or network retry)
    res2 = client.post("/api/hardware/movements", json=payload)
    assert res2.status_code == 200
    m2 = res2.json()

    # Must return same movement ID and resulting stock without subtracting again
    assert m1["id"] == m2["id"]
    assert m1["resulting_stock"] == m2["resulting_stock"]

    # Verify stock was only deducted once
    prod = client.get(f"/api/hardware/products/{prod_id}").json()
    assert prod["current_stock"] == initial_stock - 5.0

def test_hardware_low_stock_list():
    """Verify Question 3: What needs restocking?"""
    res = client.get("/api/hardware/low-stock")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total_low_stock" in data
    assert "total_zero_stock" in data
    assert data["total_low_stock"] >= 2

    # Check zero stock labeling and deficit calculation
    zero_stock_items = [i for i in data["items"] if i["is_zero_stock"]]
    assert len(zero_stock_items) >= 1
    assert zero_stock_items[0]["current_stock"] == 0.0
    assert zero_stock_items[0]["deficit_qty"] == zero_stock_items[0]["min_stock"]

    # Test that min_stock of 0 disables alert
    res_all = client.get("/api/hardware/products?status=all").json()["items"]
    assert not any(i["min_stock"] == 0 for i in data["items"])

def test_hardware_csv_validation_and_leading_zeros():
    """Verify CSV validation rules and leading zero preservation without AI."""
    csv_content = """sku,name,unit,opening_stock,min_stock,supplier_name,supplier_contact
00491,Hex Nut M6 Stainless Steel,pcs,150,50,MegaFasteners,+6012-3334455
00492,Brake Fluid DOT4 500ml,bottle,20,10,ChemLub,+6013-4567890
00493,Heavy Duty Cable Tie 300mm,pack,50,20,SolidTool,+6018-9988776
"""
    res = client.post("/api/hardware/import/validate", json={"csv_content": csv_content})
    assert res.status_code == 200
    data = res.json()
    assert data["can_import"] is True
    assert data["valid_count"] == 3
    assert data["error_count"] == 0
    # Verify exact string preserved with leading zero!
    assert data["preview_valid"][0]["sku"] == "00491"

def test_hardware_csv_validation_errors():
    """Verify CSV validation catches invalid rows and returns row numbers."""
    csv_content = """sku,name,unit,opening_stock,min_stock
,Missing SKU Bolt,pcs,10,5
00999,Valid Socket,pcs,10,5
00888,Negative Stock Plug,pcs,-15,5
00777,Invalid Unit Tool,invalid_unit,10,5
BLT-08-040,Existing SKU in catalog,pcs,10,5
00999,Duplicate SKU in file,pcs,20,5
"""
    res = client.post("/api/hardware/import/validate", json={"csv_content": csv_content})
    assert res.status_code == 200
    data = res.json()
    assert data["can_import"] is False
    assert data["error_count"] >= 5

    # Check row number reporting
    error_rows = [e["row_number"] for e in data["errors"]]
    assert 2 in error_rows # Missing SKU
    assert 4 in error_rows # Negative stock
    assert 5 in error_rows # Invalid unit
    assert 6 in error_rows # Existing catalog SKU
    assert 7 in error_rows # Duplicate in file

def test_hardware_csv_import_and_safe_reversal():
    """Verify CSV import and safe reversal when no subsequent activity exists."""
    csv_content = """sku,name,unit,opening_stock,min_stock,supplier_name
REV-01,Test Reversible Bearing,pcs,40,10,Test Supplier
REV-02,Test Reversible Gasket,pcs,30,5,Test Supplier
"""
    val_res = client.post("/api/hardware/import/validate", json={"csv_content": csv_content})
    assert val_res.status_code == 200
    valid_rows = val_res.json()["preview_valid"]

    # Confirm import
    import_res = client.post("/api/hardware/import/confirm", json={
        "valid_rows": valid_rows,
        "filename": "test_batch.csv",
        "user_recorded": "Import Operator"
    })
    assert import_res.status_code == 200
    batch_id = import_res.json()["batch_id"]
    assert import_res.json()["imported_count"] == 2

    # Verify products exist
    p1 = client.get(f"/api/hardware/products?search=REV-01").json()["items"]
    assert len(p1) == 1
    p1_id = p1[0]["id"]

    # Reversal Scenario 1: Reverse before any movements occur -> Must SUCCEED
    rev_res = client.post(f"/api/hardware/import/reverse/{batch_id}")
    assert rev_res.status_code == 200
    assert rev_res.json()["reversed"] is True

    # Verify products removed cleanly
    p1_after = client.get(f"/api/hardware/products?search=REV-01").json()["items"]
    assert len(p1_after) == 0

def test_hardware_csv_reversal_blocked_when_movements_exist():
    """Verify reversal is rejected if any product has subsequent stock activity."""
    csv_content = """sku,name,unit,opening_stock,min_stock
BLOCKED-01,Product with activity,pcs,25,10
"""
    val_res = client.post("/api/hardware/import/validate", json={"csv_content": csv_content})
    valid_rows = val_res.json()["preview_valid"]

    import_res = client.post("/api/hardware/import/confirm", json={
        "valid_rows": valid_rows,
        "filename": "blocked_batch.csv"
    })
    batch_id = import_res.json()["batch_id"]

    prod = client.get("/api/hardware/products?search=BLOCKED-01").json()["items"][0]
    prod_id = prod["id"]

    # Perform a subsequent Stock Out movement on this product
    client.post("/api/hardware/movements", json={
        "product_id": prod_id,
        "movement_type": "STOCK_OUT",
        "quantity": 5.0,
        "reason": "Sale to customer",
        "user_recorded": "Staff Joe"
    })

    # Now attempt to reverse this batch -> Must be BLOCKED with clear explanation
    rev_res = client.post(f"/api/hardware/import/reverse/{batch_id}")
    assert rev_res.status_code == 409
    err = rev_res.json()["detail"]
    assert "subsequent stock activity" in err.lower()

def test_hardware_export_csv():
    """Verify CSV export endpoint."""
    res = client.get("/api/hardware/export")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    content = res.text
    assert "Product Code / SKU" in content
    assert "Product Name" in content
    assert "BLT-08-040" in content

def test_hardware_business_data_isolation():
    """Verify business tenant isolation."""
    # Product in business 1
    p1_res = client.get("/api/hardware/products?business_id=biz-hardware-01").json()
    assert p1_res["total"] > 0

    # Business 2 should have its own empty or isolated scope
    p2_res = client.get("/api/hardware/products?business_id=biz-other-shop").json()
    assert p2_res["total"] == 0

