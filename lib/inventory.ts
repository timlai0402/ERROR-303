import db from './db';

export interface WorkspaceSettings {
  visible_fields: string[];
  visible_columns: string[];
  custom_fields: { id: string; label: string; type: 'text' | 'number' | 'dropdown'; options?: string[] }[];
}

export interface ProductRecord {
  id: string;
  workspace_id: string;
  sku: string;
  name: string;
  unit: string;
  category: string | null;
  barcode: string | null;
  supplier: string | null;
  unit_cost: number | null;
  selling_price: number | null;
  min_stock: number;
  notes: string | null;
  photo_url: string | null;
  custom_values_json: string;
  current_stock: number;
  is_archived: number;
  created_at: string;
  updated_at: string;
}

export interface TransactionItemInput {
  product_id: string;
  quantity: number;
}

// Get Workspace by ID or Slug
export function getWorkspace(idOrSlug: string) {
  return db.prepare(`
    SELECT * FROM workspaces WHERE id = ? OR slug = ?
  `).get(idOrSlug, idOrSlug) as any;
}

// Get All Workspaces
export function getAllWorkspaces() {
  return db.prepare(`SELECT * FROM workspaces ORDER BY name ASC`).all() as any[];
}

// Create Workspace
export function createWorkspace(data: {
  name: string;
  currency: string;
  timezone: string;
  logo_url?: string;
  accent_color?: string;
}) {
  const id = `ws_${Date.now()}_${Math.random().toString(36).substring(2, 7)}`;
  const slug = data.name.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '') || `ws-${Date.now()}`;
  const now = new Date().toISOString();

  const defaultSettings: WorkspaceSettings = {
    visible_fields: ['category', 'barcode', 'supplier', 'unit_cost', 'selling_price', 'min_stock', 'notes'],
    visible_columns: ['sku', 'name', 'category', 'current_stock', 'unit', 'status', 'selling_price', 'unit_cost', 'actions'],
    custom_fields: []
  };

  db.prepare(`
    INSERT INTO workspaces (id, name, slug, currency, timezone, logo_url, accent_color, item_alias, low_stock_threshold, settings_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'Products', 5, ?, ?)
  `).run(
    id,
    data.name,
    slug,
    data.currency || '$',
    data.timezone || 'UTC',
    data.logo_url || null,
    data.accent_color || 'mint',
    JSON.stringify(defaultSettings),
    now
  );

  // Default owner user
  db.prepare(`INSERT INTO users (id, workspace_id, email, name, role, created_at) VALUES (?, ?, ?, ?, 'OWNER', ?)`).run(
    `usr_${Date.now()}`, id, 'owner@stockwise.com', 'Business Owner', now
  );

  // Default common units
  const defaultUnits = ['piece', 'box', 'pack', 'pair', 'kilogram', 'metre', 'set'];
  const insertUnit = db.prepare('INSERT OR IGNORE INTO units (id, workspace_id, name) VALUES (?, ?, ?)');
  defaultUnits.forEach((u, i) => insertUnit.run(`unit_${id}_${i}`, id, u));

  // Default common categories
  const defaultCats = ['General', 'Office', 'Retail', 'Miscellaneous'];
  const insertCat = db.prepare('INSERT OR IGNORE INTO categories (id, workspace_id, name) VALUES (?, ?, ?)');
  defaultCats.forEach((c, i) => insertCat.run(`cat_${id}_${i}`, id, c));

  return getWorkspace(id);
}

// Update Workspace Settings
export function updateWorkspaceSettings(workspaceId: string, updates: {
  name?: string;
  currency?: string;
  timezone?: string;
  logo_url?: string;
  accent_color?: string;
  item_alias?: string;
  low_stock_threshold?: number;
  settings?: WorkspaceSettings;
}) {
  const current = getWorkspace(workspaceId);
  if (!current) throw new Error('Workspace not found');

  const name = updates.name !== undefined ? updates.name : current.name;
  const currency = updates.currency !== undefined ? updates.currency : current.currency;
  const timezone = updates.timezone !== undefined ? updates.timezone : current.timezone;
  const logo_url = updates.logo_url !== undefined ? updates.logo_url : current.logo_url;
  const accent_color = updates.accent_color !== undefined ? updates.accent_color : current.accent_color;
  const item_alias = updates.item_alias !== undefined ? updates.item_alias : current.item_alias;
  const low_stock_threshold = updates.low_stock_threshold !== undefined ? updates.low_stock_threshold : current.low_stock_threshold;
  const settings_json = updates.settings !== undefined ? JSON.stringify(updates.settings) : current.settings_json;

  db.prepare(`
    UPDATE workspaces
    SET name = ?, currency = ?, timezone = ?, logo_url = ?, accent_color = ?, item_alias = ?, low_stock_threshold = ?, settings_json = ?
    WHERE id = ?
  `).run(name, currency, timezone, logo_url, accent_color, item_alias, low_stock_threshold, settings_json, workspaceId);

  return getWorkspace(workspaceId);
}

// Categories & Units
export function getCategories(workspaceId: string) {
  return db.prepare('SELECT name FROM categories WHERE workspace_id = ? ORDER BY name ASC').all(workspaceId).map((r: any) => r.name);
}

export function addCategory(workspaceId: string, name: string) {
  const trimmed = name.trim();
  if (!trimmed) return;
  db.prepare('INSERT OR IGNORE INTO categories (id, workspace_id, name) VALUES (?, ?, ?)').run(
    `cat_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`, workspaceId, trimmed
  );
}

export function getUnits(workspaceId: string) {
  return db.prepare('SELECT name FROM units WHERE workspace_id = ? ORDER BY name ASC').all(workspaceId).map((r: any) => r.name);
}

export function addUnit(workspaceId: string, name: string) {
  const trimmed = name.trim();
  if (!trimmed) return;
  db.prepare('INSERT OR IGNORE INTO units (id, workspace_id, name) VALUES (?, ?, ?)').run(
    `unit_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`, workspaceId, trimmed
  );
}

// Auto-generate Next SKU (preserves leading zero format e.g. 00108)
export function generateNextSku(workspaceId: string): string {
  const products = db.prepare('SELECT sku FROM products WHERE workspace_id = ? ORDER BY created_at DESC').all(workspaceId) as { sku: string }[];
  if (products.length === 0) return '00101';

  // Find highest numeric SKU or format
  let maxNum = 100;
  let digits = 5;
  for (const p of products) {
    const num = parseInt(p.sku, 10);
    if (!isNaN(num) && num > maxNum) {
      maxNum = num;
      digits = Math.max(digits, p.sku.length);
    }
  }
  return String(maxNum + 1).padStart(digits, '0');
}

// Get Products
export function getProducts(workspaceId: string, filters?: {
  search?: string;
  category?: string;
  lowStockOnly?: boolean;
  includeArchived?: boolean;
  role?: 'OWNER' | 'STAFF';
}) {
  let query = `SELECT * FROM products WHERE workspace_id = ?`;
  const params: any[] = [workspaceId];

  if (!filters?.includeArchived) {
    query += ` AND is_archived = 0`;
  }

  if (filters?.category && filters.category !== 'All') {
    query += ` AND category = ?`;
    params.push(filters.category);
  }

  if (filters?.lowStockOnly) {
    query += ` AND current_stock <= min_stock`;
  }

  if (filters?.search && filters.search.trim()) {
    const term = `%${filters.search.trim()}%`;
    query += ` AND (name LIKE ? OR sku LIKE ? OR barcode LIKE ? OR supplier LIKE ?)`;
    params.push(term, term, term, term);
  }

  query += ` ORDER BY name ASC`;

  const rows = db.prepare(query).all(...params) as ProductRecord[];

  // Redact unit_cost if Staff
  if (filters?.role === 'STAFF') {
    rows.forEach(r => {
      r.unit_cost = null;
    });
  }

  return rows;
}

// Get Single Product by ID or SKU
export function getProduct(workspaceId: string, idOrSku: string, role?: 'OWNER' | 'STAFF') {
  const row = db.prepare(`
    SELECT * FROM products
    WHERE workspace_id = ? AND (id = ? OR sku = ?)
  `).get(workspaceId, idOrSku, idOrSku) as ProductRecord | undefined;

  if (!row) return null;

  if (role === 'STAFF') {
    row.unit_cost = null;
  }
  return row;
}

// Create Product
export function createProduct(workspaceId: string, data: {
  sku?: string;
  name: string;
  unit?: string;
  category?: string;
  barcode?: string;
  supplier?: string;
  unit_cost?: number;
  selling_price?: number;
  min_stock?: number;
  opening_stock?: number;
  notes?: string;
  photo_url?: string;
  custom_values?: Record<string, any>;
}, user?: { id: string; name: string }) {
  const now = new Date().toISOString();
  const id = `prd_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
  const sku = (data.sku && data.sku.trim()) || generateNextSku(workspaceId);
  const unit = data.unit || 'piece';
  const openingStock = Number(data.opening_stock) || 0;

  // Check SKU uniqueness in workspace
  const existing = db.prepare('SELECT id FROM products WHERE workspace_id = ? AND sku = ?').get(workspaceId, sku);
  if (existing) {
    throw new Error(`A product with SKU "${sku}" already exists in this business.`);
  }

  const tx = db.transaction(() => {
    db.prepare(`
      INSERT INTO products (
        id, workspace_id, sku, name, unit, category, barcode, supplier,
        unit_cost, selling_price, min_stock, notes, photo_url,
        custom_values_json, current_stock, is_archived, created_at, updated_at
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
    `).run(
      id,
      workspaceId,
      sku,
      data.name.trim(),
      unit,
      data.category || null,
      data.barcode || null,
      data.supplier || null,
      data.unit_cost !== undefined && data.unit_cost !== null ? Number(data.unit_cost) : null,
      data.selling_price !== undefined && data.selling_price !== null ? Number(data.selling_price) : null,
      data.min_stock !== undefined && data.min_stock !== null ? Number(data.min_stock) : 5,
      data.notes || null,
      data.photo_url || null,
      JSON.stringify(data.custom_values || {}),
      openingStock,
      now,
      now
    );

    // If opening stock > 0, log an initial stock in transaction
    if (openingStock > 0) {
      const txId = `tx_init_${id}`;
      db.prepare(`
        INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
        VALUES (?, ?, 'STOCK_IN', 'Opening stock', ?, ?, 'OPENING-STOCK', 'Initial balance upon product registration', ?, ?, ?)
      `).run(
        txId,
        workspaceId,
        now.slice(0, 10),
        data.supplier || '',
        user?.id || 'system',
        user?.name || 'System / Setup',
        now
      );

      db.prepare(`
        INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
        VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
      `).run(
        `txi_${txId}_1`,
        txId,
        id,
        sku,
        data.name.trim(),
        unit,
        openingStock,
        openingStock
      );
    }
  });

  tx();
  return getProduct(workspaceId, id);
}

// Update Product
export function updateProduct(workspaceId: string, productId: string, data: Partial<{
  name: string;
  sku: string;
  unit: string;
  category: string;
  barcode: string;
  supplier: string;
  unit_cost: number;
  selling_price: number;
  min_stock: number;
  notes: string;
  photo_url: string;
  custom_values: Record<string, any>;
}>) {
  const current = getProduct(workspaceId, productId);
  if (!current) throw new Error('Product not found');

  if (data.sku && data.sku !== current.sku) {
    const existing = db.prepare('SELECT id FROM products WHERE workspace_id = ? AND sku = ? AND id != ?').get(workspaceId, data.sku, productId);
    if (existing) {
      throw new Error(`SKU "${data.sku}" is already in use by another product.`);
    }
  }

  const now = new Date().toISOString();
  db.prepare(`
    UPDATE products SET
      name = COALESCE(?, name),
      sku = COALESCE(?, sku),
      unit = COALESCE(?, unit),
      category = COALESCE(?, category),
      barcode = COALESCE(?, barcode),
      supplier = COALESCE(?, supplier),
      unit_cost = ?,
      selling_price = ?,
      min_stock = COALESCE(?, min_stock),
      notes = COALESCE(?, notes),
      photo_url = COALESCE(?, photo_url),
      custom_values_json = COALESCE(?, custom_values_json),
      updated_at = ?
    WHERE workspace_id = ? AND id = ?
  `).run(
    data.name !== undefined ? data.name.trim() : null,
    data.sku !== undefined ? data.sku.trim() : null,
    data.unit !== undefined ? data.unit.trim() : null,
    data.category !== undefined ? data.category : null,
    data.barcode !== undefined ? data.barcode : null,
    data.supplier !== undefined ? data.supplier : null,
    data.unit_cost !== undefined ? Number(data.unit_cost) : current.unit_cost,
    data.selling_price !== undefined ? Number(data.selling_price) : current.selling_price,
    data.min_stock !== undefined ? Number(data.min_stock) : null,
    data.notes !== undefined ? data.notes : null,
    data.photo_url !== undefined ? data.photo_url : null,
    data.custom_values !== undefined ? JSON.stringify(data.custom_values) : null,
    now,
    workspaceId,
    productId
  );

  return getProduct(workspaceId, productId);
}

// Archive Product (Soft Delete to protect ledger integrity)
export function archiveProduct(workspaceId: string, productId: string) {
  const current = getProduct(workspaceId, productId);
  if (!current) throw new Error('Product not found');

  // Check if product has transactions
  const txItem = db.prepare('SELECT id FROM transaction_items WHERE product_id = ?').get(productId);

  if (!txItem) {
    // If no transaction history ever, hard delete is safe
    db.prepare('DELETE FROM products WHERE workspace_id = ? AND id = ?').run(workspaceId, productId);
    return { deleted: true };
  } else {
    // Archive product so reports and audit logs remain intact
    db.prepare('UPDATE products SET is_archived = 1, updated_at = ? WHERE workspace_id = ? AND id = ?').run(
      new Date().toISOString(), workspaceId, productId
    );
    return { archived: true };
  }
}

// Stock In Transaction (Atomic)
export function recordStockIn(workspaceId: string, data: {
  reason: string;
  date?: string;
  partner_name?: string;
  reference?: string;
  notes?: string;
  items: { product_id: string; quantity: number }[];
}, user: { id: string; name: string }) {
  if (!data.items || data.items.length === 0) {
    throw new Error('At least one item is required for Stock In.');
  }

  const now = new Date().toISOString();
  const date = data.date || now.slice(0, 10);
  const txId = `tx_in_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

  const tx = db.transaction(() => {
    // Create transaction header
    db.prepare(`
      INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
      VALUES (?, ?, 'STOCK_IN', ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      txId,
      workspaceId,
      data.reason || 'Purchase received',
      date,
      data.partner_name || '',
      data.reference || '',
      data.notes || '',
      user.id,
      user.name,
      now
    );

    const updateProductStock = db.prepare(`
      UPDATE products SET current_stock = current_stock + ?, updated_at = ? WHERE workspace_id = ? AND id = ?
    `);

    const insertTxItem = db.prepare(`
      INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    for (const item of data.items) {
      const qty = Number(item.quantity);
      if (isNaN(qty) || qty <= 0) {
        throw new Error(`Quantity must be a positive number.`);
      }

      const prod = db.prepare('SELECT * FROM products WHERE workspace_id = ? AND id = ?').get(workspaceId, item.product_id) as ProductRecord | undefined;
      if (!prod) throw new Error(`Product not found: ${item.product_id}`);

      const balanceBefore = prod.current_stock;
      const balanceAfter = balanceBefore + qty;

      updateProductStock.run(qty, now, workspaceId, prod.id);
      insertTxItem.run(
        `txi_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        txId,
        prod.id,
        prod.sku,
        prod.name,
        prod.unit,
        qty,
        balanceBefore,
        balanceAfter
      );
    }
  });

  tx();
  return getTransactionDetails(workspaceId, txId);
}

// Stock Out Transaction (Atomic with strict balance check)
export function recordStockOut(workspaceId: string, data: {
  reason: string;
  date?: string;
  partner_name?: string;
  reference?: string;
  notes?: string;
  items: { product_id: string; quantity: number }[];
}, user: { id: string; name: string }) {
  if (!data.items || data.items.length === 0) {
    throw new Error('At least one item is required for Stock Out.');
  }

  const now = new Date().toISOString();
  const date = data.date || now.slice(0, 10);
  const txId = `tx_out_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

  const tx = db.transaction(() => {
    // 1. Verify all stock balances FIRST before modifying anything
    for (const item of data.items) {
      const qty = Number(item.quantity);
      if (isNaN(qty) || qty <= 0) {
        throw new Error(`Quantity must be greater than zero.`);
      }

      const prod = db.prepare('SELECT * FROM products WHERE workspace_id = ? AND id = ?').get(workspaceId, item.product_id) as ProductRecord | undefined;
      if (!prod) throw new Error(`Product not found: ${item.product_id}`);

      if (prod.current_stock < qty) {
        throw new Error(
          `Cannot stock out ${qty} ${prod.unit} of "${prod.name}" (SKU: ${prod.sku}). Available stock is only ${prod.current_stock} ${prod.unit}.`
        );
      }
    }

    // 2. Create transaction header
    db.prepare(`
      INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
      VALUES (?, ?, 'STOCK_OUT', ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      txId,
      workspaceId,
      data.reason || 'Sale',
      date,
      data.partner_name || '',
      data.reference || '',
      data.notes || '',
      user.id,
      user.name,
      now
    );

    const updateProductStock = db.prepare(`
      UPDATE products SET current_stock = current_stock - ?, updated_at = ? WHERE workspace_id = ? AND id = ?
    `);

    const insertTxItem = db.prepare(`
      INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `);

    for (const item of data.items) {
      const qty = Number(item.quantity);
      const prod = db.prepare('SELECT * FROM products WHERE workspace_id = ? AND id = ?').get(workspaceId, item.product_id) as ProductRecord;

      const balanceBefore = prod.current_stock;
      const balanceAfter = balanceBefore - qty;

      updateProductStock.run(qty, now, workspaceId, prod.id);
      insertTxItem.run(
        `txi_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
        txId,
        prod.id,
        prod.sku,
        prod.name,
        prod.unit,
        qty,
        balanceBefore,
        balanceAfter
      );
    }
  });

  tx();
  return getTransactionDetails(workspaceId, txId);
}

// Correct Stock Count (Owner Only Adjustment)
export function correctStockCount(workspaceId: string, data: {
  product_id: string;
  actual_count: number;
  reason: string;
  notes?: string;
}, user: { id: string; name: string }) {
  const prod = db.prepare('SELECT * FROM products WHERE workspace_id = ? AND id = ?').get(workspaceId, data.product_id) as ProductRecord | undefined;
  if (!prod) throw new Error('Product not found');

  const actualCount = Number(data.actual_count);
  if (isNaN(actualCount) || actualCount < 0) {
    throw new Error('Actual count must be a non-negative number.');
  }

  const diff = actualCount - prod.current_stock;
  if (diff === 0) {
    throw new Error('Counted quantity equals current recorded balance. No adjustment needed.');
  }

  const now = new Date().toISOString();
  const txId = `tx_adj_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;

  const tx = db.transaction(() => {
    db.prepare(`
      INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
      VALUES (?, ?, 'ADJUSTMENT', ?, ?, '', 'COUNT-CORRECTION', ?, ?, ?, ?)
    `).run(
      txId,
      workspaceId,
      data.reason || 'Owner Stock Count Correction',
      now.slice(0, 10),
      data.notes ? `Count adjustment: ${data.notes}` : `Adjusted from ${prod.current_stock} to ${actualCount} ${prod.unit}`,
      user.id,
      user.name,
      now
    );

    db.prepare(`
      UPDATE products SET current_stock = ?, updated_at = ? WHERE workspace_id = ? AND id = ?
    `).run(actualCount, now, workspaceId, prod.id);

    db.prepare(`
      INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    `).run(
      `txi_${Date.now()}`,
      txId,
      prod.id,
      prod.sku,
      prod.name,
      prod.unit,
      Math.abs(diff),
      prod.current_stock,
      actualCount
    );
  });

  tx();
  return getProduct(workspaceId, prod.id);
}

// Get Transaction Details
export function getTransactionDetails(workspaceId: string, transactionId: string) {
  const tx = db.prepare(`
    SELECT * FROM transactions WHERE workspace_id = ? AND id = ?
  `).get(workspaceId, transactionId) as any;

  if (!tx) return null;

  const items = db.prepare(`
    SELECT * FROM transaction_items WHERE transaction_id = ?
  `).all(transactionId);

  return { ...tx, items };
}

// Get Transactions (Ledger & Activity History)
export function getTransactions(workspaceId: string, options?: {
  type?: 'STOCK_IN' | 'STOCK_OUT' | 'ADJUSTMENT';
  productId?: string;
  limit?: number;
  startDate?: string;
  endDate?: string;
}) {
  let query = `
    SELECT t.*,
           COUNT(ti.id) as item_count,
           SUM(ti.quantity) as total_units
    FROM transactions t
    LEFT JOIN transaction_items ti ON t.id = ti.transaction_id
    WHERE t.workspace_id = ?
  `;
  const params: any[] = [workspaceId];

  if (options?.type) {
    query += ` AND t.type = ?`;
    params.push(options.type);
  }

  if (options?.productId) {
    query += ` AND ti.product_id = ?`;
    params.push(options.productId);
  }

  if (options?.startDate) {
    query += ` AND t.date >= ?`;
    params.push(options.startDate);
  }

  if (options?.endDate) {
    query += ` AND t.date <= ?`;
    params.push(options.endDate);
  }

  query += ` GROUP BY t.id ORDER BY t.created_at DESC`;

  if (options?.limit) {
    query += ` LIMIT ?`;
    params.push(options.limit);
  }

  const rows = db.prepare(query).all(...params) as any[];

  // Attach items for each transaction
  const getItems = db.prepare('SELECT * FROM transaction_items WHERE transaction_id = ?');
  return rows.map(r => ({
    ...r,
    items: getItems.all(r.id)
  }));
}

// Get Stock Movement History for a specific product
export function getProductHistory(workspaceId: string, productId: string) {
  return db.prepare(`
    SELECT ti.*, t.type, t.reason, t.date, t.partner_name, t.reference, t.notes, t.created_by_name, t.created_at as tx_time
    FROM transaction_items ti
    JOIN transactions t ON ti.transaction_id = t.id
    WHERE t.workspace_id = ? AND ti.product_id = ?
    ORDER BY t.created_at DESC
  `).all(workspaceId, productId);
}

// Today's Activity Metrics
export function getTodayMetrics(workspaceId: string) {
  const today = new Date().toISOString().slice(0, 10);

  // Stock In count today
  const inRow = db.prepare(`
    SELECT COUNT(DISTINCT t.id) as tx_count, COALESCE(SUM(ti.quantity), 0) as total_units
    FROM transactions t
    JOIN transaction_items ti ON t.id = ti.transaction_id
    WHERE t.workspace_id = ? AND t.type = 'STOCK_IN' AND t.date = ?
  `).get(workspaceId, today) as any;

  // Stock Out count today
  const outRow = db.prepare(`
    SELECT COUNT(DISTINCT t.id) as tx_count, COALESCE(SUM(ti.quantity), 0) as total_units
    FROM transactions t
    JOIN transaction_items ti ON t.id = ti.transaction_id
    WHERE t.workspace_id = ? AND t.type = 'STOCK_OUT' AND t.date = ?
  `).get(workspaceId, today) as any;

  // New products created today
  const newRow = db.prepare(`
    SELECT COUNT(*) as count FROM products WHERE workspace_id = ? AND date(created_at) = ? AND is_archived = 0
  `).get(workspaceId, today) as any;

  // Low stock products count
  const lowRow = db.prepare(`
    SELECT COUNT(*) as count FROM products WHERE workspace_id = ? AND current_stock <= min_stock AND is_archived = 0
  `).get(workspaceId) as any;

  return {
    todayStockInCount: inRow?.tx_count || 0,
    todayStockInUnits: inRow?.total_units || 0,
    todayStockOutCount: outRow?.tx_count || 0,
    todayStockOutUnits: outRow?.total_units || 0,
    todayNewProductsCount: newRow?.count || 0,
    lowStockCount: lowRow?.count || 0
  };
}

// Reports Generator
export function getReportsData(workspaceId: string, role: 'OWNER' | 'STAFF' = 'OWNER') {
  const products = getProducts(workspaceId, { role, includeArchived: false });
  const txs = getTransactions(workspaceId, { limit: 200 });

  let totalProducts = products.length;
  let totalStockUnits = 0;
  let totalCostValue = 0;
  let totalRetailValue = 0;
  let missingCostCount = 0;
  let lowStockProducts: ProductRecord[] = [];

  for (const p of products) {
    totalStockUnits += p.current_stock;
    if (p.current_stock <= p.min_stock) {
      lowStockProducts.push(p);
    }
    if (role === 'OWNER') {
      if (p.unit_cost !== null && p.unit_cost !== undefined) {
        totalCostValue += p.current_stock * p.unit_cost;
      } else {
        missingCostCount++;
      }
      if (p.selling_price) {
        totalRetailValue += p.current_stock * p.selling_price;
      }
    }
  }

  // Category breakdown
  const categoryMap: Record<string, { count: number; units: number; value: number }> = {};
  for (const p of products) {
    const cat = p.category || 'Uncategorized';
    if (!categoryMap[cat]) categoryMap[cat] = { count: 0, units: 0, value: 0 };
    categoryMap[cat].count++;
    categoryMap[cat].units += p.current_stock;
    if (role === 'OWNER' && p.unit_cost) {
      categoryMap[cat].value += p.current_stock * p.unit_cost;
    }
  }

  return {
    summary: {
      totalProducts,
      totalStockUnits,
      lowStockCount: lowStockProducts.length,
      totalCostValue: role === 'OWNER' ? totalCostValue : null,
      totalRetailValue: role === 'OWNER' ? totalRetailValue : null,
      missingCostCount: role === 'OWNER' ? missingCostCount : null,
    },
    lowStockProducts,
    categoryBreakdown: Object.entries(categoryMap).map(([name, data]) => ({
      name,
      ...data
    })),
    recentMovements: txs.slice(0, 50)
  };
}
