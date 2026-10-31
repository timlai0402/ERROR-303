-- =============================================================================
-- StockWise Hardware SME - Safe Supabase PostgreSQL Schema Migration
-- Designed for Independent Hardware Shops & Mechanics (Non-expiry inventory)
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Businesses Table (Tenant Isolation)
CREATE TABLE IF NOT EXISTS public.businesses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    code TEXT NOT NULL UNIQUE,
    name TEXT NOT NULL,
    currency TEXT NOT NULL DEFAULT 'MYR',
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

-- Seed default business if not existing
INSERT INTO public.businesses (id, code, name, currency)
VALUES ('00000000-0000-0000-0000-000000000001', 'HARDWARE-01', 'Ah Huat Hardware & Auto Parts', 'MYR')
ON CONFLICT (code) DO NOTHING;

-- 2. Hardware Products Table
CREATE TABLE IF NOT EXISTS public.products (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'pcs',
    current_stock NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (current_stock >= 0),
    min_stock NUMERIC(12,2) NOT NULL DEFAULT 0 CHECK (min_stock >= 0),
    supplier_name TEXT,
    supplier_contact TEXT,
    is_archived BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now()),
    CONSTRAINT uq_product_business_sku UNIQUE (business_id, sku)
);

-- Indexes for fast query, sorting, and low-stock alert lookups
CREATE INDEX IF NOT EXISTS idx_products_business_sku ON public.products(business_id, sku);
CREATE INDEX IF NOT EXISTS idx_products_business_archived ON public.products(business_id, is_archived);
CREATE INDEX IF NOT EXISTS idx_products_low_stock ON public.products(business_id, current_stock, min_stock) 
WHERE is_archived = FALSE;

-- 3. Stock Movements Table (Immutable Audit Ledger)
CREATE TABLE IF NOT EXISTS public.stock_movements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    product_id UUID NOT NULL REFERENCES public.products(id) ON DELETE CASCADE,
    movement_type TEXT NOT NULL CHECK (movement_type IN ('OPENING_STOCK', 'STOCK_IN', 'STOCK_OUT', 'CORRECTION')),
    quantity_change NUMERIC(12,2) NOT NULL,
    previous_stock NUMERIC(12,2) NOT NULL,
    resulting_stock NUMERIC(12,2) NOT NULL CHECK (resulting_stock >= 0),
    reason TEXT,
    user_recorded TEXT NOT NULL,
    idempotency_key TEXT UNIQUE,
    batch_id UUID,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_movements_business_product ON public.stock_movements(business_id, product_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_business_created ON public.stock_movements(business_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_movements_batch ON public.stock_movements(batch_id);

-- 4. CSV Import Batches (Auditing & Safe Rollback)
CREATE TABLE IF NOT EXISTS public.import_batches (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    business_id UUID NOT NULL DEFAULT '00000000-0000-0000-0000-000000000001',
    filename TEXT NOT NULL,
    total_rows INT NOT NULL,
    imported_count INT NOT NULL,
    reversed BOOLEAN NOT NULL DEFAULT FALSE,
    reversed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc', now())
);

CREATE INDEX IF NOT EXISTS idx_import_batches_business ON public.import_batches(business_id, created_at DESC);

-- =============================================================================
-- Row Level Security (Business Isolation)
-- =============================================================================
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.stock_movements ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.import_batches ENABLE ROW LEVEL SECURITY;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'products' AND policyname = 'Business products isolation'
    ) THEN
        CREATE POLICY "Business products isolation" ON public.products
            FOR ALL
            USING (
                business_id = '00000000-0000-0000-0000-000000000001'::uuid 
                OR business_id = NULLIF(current_setting('request.jwt.claim.business_id', true), '')::uuid
            );
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_policies WHERE tablename = 'stock_movements' AND policyname = 'Business stock movements isolation'
    ) THEN
        CREATE POLICY "Business stock movements isolation" ON public.stock_movements
            FOR ALL
            USING (
                business_id = '00000000-0000-0000-0000-000000000001'::uuid 
                OR business_id = NULLIF(current_setting('request.jwt.claim.business_id', true), '')::uuid
            );
    END IF;
END $$;

-- =============================================================================
-- Concurrency-Safe Atomic Stock Movement Procedure
-- =============================================================================
CREATE OR REPLACE FUNCTION public.record_hardware_stock_movement(
    p_business_id UUID,
    p_product_id UUID,
    p_type TEXT,
    p_quantity NUMERIC,
    p_reason TEXT,
    p_user TEXT,
    p_idempotency_key TEXT DEFAULT NULL
)
RETURNS JSONB
LANGUAGE plpgsql
SECURITY DEFINER
AS $$
DECLARE
    v_product RECORD;
    v_prev_stock NUMERIC;
    v_new_stock NUMERIC;
    v_change NUMERIC;
    v_movement_id UUID;
    v_existing_movement RECORD;
BEGIN
    -- 1. Idempotency Check: Prevent duplicate form submissions
    IF p_idempotency_key IS NOT NULL THEN
        SELECT * INTO v_existing_movement FROM public.stock_movements
        WHERE idempotency_key = p_idempotency_key;
        IF FOUND THEN
            RETURN jsonb_build_object(
                'status', 'idempotent_duplicate',
                'movement_id', v_existing_movement.id,
                'resulting_stock', v_existing_movement.resulting_stock
            );
        END IF;
    END IF;

    -- 2. Lock Product Row FOR UPDATE (Eliminates Race Conditions)
    SELECT * INTO v_product FROM public.products
    WHERE id = p_product_id AND business_id = p_business_id
    FOR UPDATE;

    IF NOT FOUND THEN
        RAISE EXCEPTION 'Product % not found in business %', p_product_id, p_business_id;
    END IF;

    IF v_product.is_archived THEN
        RAISE EXCEPTION 'Cannot record movement for archived product %', v_product.sku;
    END IF;

    v_prev_stock := v_product.current_stock;

    -- 3. Calculate Resulting Stock based on Movement Type
    IF p_type = 'STOCK_IN' THEN
        IF p_quantity <= 0 THEN
            RAISE EXCEPTION 'Stock In quantity must be strictly greater than 0';
        END IF;
        v_change := p_quantity;
        v_new_stock := v_prev_stock + p_quantity;

    ELSIF p_type = 'STOCK_OUT' THEN
        IF p_quantity <= 0 THEN
            RAISE EXCEPTION 'Stock Out quantity must be strictly greater than 0';
        END IF;
        IF v_prev_stock < p_quantity THEN
            RAISE EXCEPTION 'Insufficient stock: current stock is %, requested out is %', v_prev_stock, p_quantity;
        END IF;
        v_change := -p_quantity;
        v_new_stock := v_prev_stock - p_quantity;

    ELSIF p_type = 'CORRECTION' THEN
        IF p_quantity < 0 THEN
            RAISE EXCEPTION 'Stock correction quantity cannot be negative';
        END IF;
        v_change := p_quantity - v_prev_stock;
        v_new_stock := p_quantity;

    ELSIF p_type = 'OPENING_STOCK' THEN
        IF p_quantity < 0 THEN
            RAISE EXCEPTION 'Opening stock quantity cannot be negative';
        END IF;
        v_change := p_quantity;
        v_new_stock := p_quantity;

    ELSE
        RAISE EXCEPTION 'Invalid movement type: %', p_type;
    END IF;

    -- 4. Update Product Stock Level
    UPDATE public.products
    SET current_stock = v_new_stock, updated_at = timezone('utc', now())
    WHERE id = p_product_id;

    -- 5. Write to Stock Movements Ledger
    INSERT INTO public.stock_movements (
        business_id, product_id, movement_type, quantity_change,
        previous_stock, resulting_stock, reason, user_recorded, idempotency_key
    ) VALUES (
        p_business_id, p_product_id, p_type, v_change,
        v_prev_stock, v_new_stock, p_reason, p_user, p_idempotency_key
    ) RETURNING id INTO v_movement_id;

    RETURN jsonb_build_object(
        'status', 'success',
        'movement_id', v_movement_id,
        'product_id', p_product_id,
        'sku', v_product.sku,
        'previous_stock', v_prev_stock,
        'resulting_stock', v_new_stock,
        'quantity_change', v_change
    );
END;
$$;

