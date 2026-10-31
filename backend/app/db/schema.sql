-- =============================================================================
-- StockWise AI - Database Schema for Supabase (PostgreSQL)
-- Supports deterministic inventory, statistical forecasting, and GenAI audit trails.
-- =============================================================================

-- Enable UUID generation
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Stores Table
CREATE TABLE IF NOT EXISTS public.stores (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    location TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 2. Suppliers Table
CREATE TABLE IF NOT EXISTS public.suppliers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    items_desc TEXT,
    lead_days INT NOT NULL DEFAULT 5,
    reliability NUMERIC(5,2) NOT NULL DEFAULT 95.0,
    terms TEXT DEFAULT 'Net 30',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 3. Inventory Items Table
CREATE TABLE IF NOT EXISTS public.inventory_items (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sku TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    unit TEXT NOT NULL,
    physical_stock NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (physical_stock >= 0),
    reserved_stock NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (reserved_stock >= 0),
    reorder_point NUMERIC(12,2) NOT NULL DEFAULT 10,
    safety_stock NUMERIC(12,2) NOT NULL DEFAULT 5,
    unit_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    daily_usage NUMERIC(12,2) NOT NULL DEFAULT 0,
    min_order_qty NUMERIC(12,2) NOT NULL DEFAULT 1,
    store_id UUID REFERENCES public.stores(id) ON DELETE SET NULL,
    supplier_id UUID REFERENCES public.suppliers(id) ON DELETE SET NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 4. Demand Orders Table
CREATE TABLE IF NOT EXISTS public.demand_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    reference_number TEXT NOT NULL UNIQUE,
    customer TEXT NOT NULL,
    demand_type TEXT NOT NULL DEFAULT 'Sales order',
    quantity NUMERIC(12,2) NOT NULL CHECK (quantity > 0),
    reserved_quantity NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (reserved_quantity >= 0),
    due_date DATE,
    status TEXT NOT NULL DEFAULT 'PLANNING' CHECK (status IN ('PLANNING', 'CONFIRMED', 'COMPLETED', 'CANCELLED')),
    item_id UUID NOT NULL REFERENCES public.inventory_items(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 5. Purchase Orders Table
CREATE TABLE IF NOT EXISTS public.purchase_orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    po_number TEXT NOT NULL UNIQUE,
    item_id UUID NOT NULL REFERENCES public.inventory_items(id) ON DELETE CASCADE,
    supplier_id UUID REFERENCES public.suppliers(id) ON DELETE SET NULL,
    quantity NUMERIC(12,2) NOT NULL CHECK (quantity > 0),
    unit_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    total_cost NUMERIC(12,2) NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'DRAFT' CHECK (status IN ('DRAFT', 'SUBMITTED', 'APPROVED', 'RETURNED', 'REJECTED', 'CANCELLED', 'RECEIVED')),
    reason TEXT NOT NULL,
    additional_reason TEXT,
    source TEXT NOT NULL DEFAULT 'manual',
    decision_reason TEXT,
    revision INT NOT NULL DEFAULT 0,
    created_by_id TEXT NOT NULL,
    created_by_name TEXT NOT NULL,
    submitted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 6. Purchase Order Events (Audit Log)
CREATE TABLE IF NOT EXISTS public.purchase_order_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    purchase_order_id UUID NOT NULL REFERENCES public.purchase_orders(id) ON DELETE CASCADE,
    action TEXT NOT NULL,
    status TEXT NOT NULL,
    actor_id TEXT NOT NULL,
    actor_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'WORKER',
    quantity NUMERIC(12,2) NOT NULL,
    previous_quantity NUMERIC(12,2),
    reason TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- 7. Restock Decisions Snapshot Table
CREATE TABLE IF NOT EXISTS public.restock_decisions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    item_id UUID NOT NULL REFERENCES public.inventory_items(id) ON DELETE CASCADE,
    calculated_need NUMERIC(12,2) NOT NULL,
    recommended_qty NUMERIC(12,2) NOT NULL,
    risk_level TEXT NOT NULL CHECK (risk_level IN ('HEALTHY', 'WARNING', 'CRITICAL', 'OUT_OF_STOCK')),
    available_stock NUMERIC(12,2) NOT NULL,
    days_remaining NUMERIC(8,2),
    horizon_days INT NOT NULL,
    approved_supply NUMERIC(12,2) NOT NULL,
    projected_stock NUMERIC(12,2) NOT NULL,
    generated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);
