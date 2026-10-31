import Database from 'better-sqlite3';
import path from 'path';
import fs from 'fs';

const dataDir = path.join(process.cwd(), 'data');
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true });
}

const dbPath = path.join(dataDir, 'stockwise.db');
const db = new Database(dbPath);

// Enable WAL mode for high concurrency
db.pragma('journal_mode = WAL');
db.pragma('foreign_keys = ON');

// Initialize schema
db.exec(`
  CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    currency TEXT NOT NULL DEFAULT '$',
    timezone TEXT NOT NULL DEFAULT 'UTC',
    logo_url TEXT,
    accent_color TEXT NOT NULL DEFAULT 'mint',
    item_alias TEXT NOT NULL DEFAULT 'Products',
    low_stock_threshold REAL NOT NULL DEFAULT 5,
    settings_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
  );

  CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    email TEXT NOT NULL,
    name TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('OWNER', 'STAFF')),
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS categories (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    UNIQUE(workspace_id, name)
  );

  CREATE TABLE IF NOT EXISTS units (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    name TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    UNIQUE(workspace_id, name)
  );

  CREATE TABLE IF NOT EXISTS products (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    name TEXT NOT NULL,
    unit TEXT NOT NULL DEFAULT 'piece',
    category TEXT,
    barcode TEXT,
    supplier TEXT,
    unit_cost REAL,
    selling_price REAL,
    min_stock REAL DEFAULT 5,
    notes TEXT,
    photo_url TEXT,
    custom_values_json TEXT DEFAULT '{}',
    current_stock REAL NOT NULL DEFAULT 0,
    is_archived INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE,
    UNIQUE(workspace_id, sku)
  );

  CREATE TABLE IF NOT EXISTS transactions (
    id TEXT PRIMARY KEY,
    workspace_id TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('STOCK_IN', 'STOCK_OUT', 'ADJUSTMENT')),
    reason TEXT NOT NULL,
    date TEXT NOT NULL,
    partner_name TEXT,
    reference TEXT,
    notes TEXT,
    created_by_user_id TEXT,
    created_by_name TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS transaction_items (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL,
    product_id TEXT NOT NULL,
    sku TEXT NOT NULL,
    product_name TEXT NOT NULL,
    unit TEXT NOT NULL,
    quantity REAL NOT NULL,
    balance_before REAL NOT NULL,
    balance_after REAL NOT NULL,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
  );

  CREATE TABLE IF NOT EXISTS saved_column_mappings (
    workspace_id TEXT NOT NULL,
    source_header TEXT NOT NULL,
    target_field TEXT NOT NULL,
    PRIMARY KEY(workspace_id, source_header),
    FOREIGN KEY (workspace_id) REFERENCES workspaces(id) ON DELETE CASCADE
  );

  CREATE INDEX IF NOT EXISTS idx_products_workspace ON products(workspace_id, is_archived);
  CREATE INDEX IF NOT EXISTS idx_transactions_workspace ON transactions(workspace_id, date);
  CREATE INDEX IF NOT EXISTS idx_trans_items_trans ON transaction_items(transaction_id);
  CREATE INDEX IF NOT EXISTS idx_trans_items_prod ON transaction_items(product_id);
`);

// Seed function to insert rich realistic demo data if empty
export function seedDatabaseIfEmpty() {
  const count = db.prepare('SELECT count(*) as count FROM workspaces').get() as { count: number };
  if (count.count > 0) return;

  const now = new Date().toISOString();
  const today = now.slice(0, 10);

  // 1. Create Workspace: Apex Stationery & Supplies
  const apexSettings = {
    visible_fields: ['category', 'barcode', 'supplier', 'unit_cost', 'selling_price', 'min_stock', 'notes'],
    visible_columns: ['sku', 'name', 'category', 'current_stock', 'unit', 'status', 'selling_price', 'unit_cost', 'actions'],
    custom_fields: [
      { id: 'brand', label: 'Brand', type: 'text' },
      { id: 'color', label: 'Color', type: 'text' },
      { id: 'shelf_loc', label: 'Shelf Location', type: 'text' }
    ]
  };

  db.prepare(`
    INSERT INTO workspaces (id, name, slug, currency, timezone, logo_url, accent_color, item_alias, low_stock_threshold, settings_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    'ws_apex',
    'Apex Stationery & Supplies',
    'apex-stationery',
    '$',
    'America/New_York',
    'https://images.unsplash.com/photo-1586075010923-2dd4570fb338?w=100&auto=format&fit=crop&q=60',
    'mint',
    'Products',
    5,
    JSON.stringify(apexSettings),
    now
  );

  // Users for Apex
  db.prepare(`INSERT INTO users (id, workspace_id, email, name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)`).run(
    'usr_apex_owner', 'ws_apex', 'owner@stockwise.com', 'Sarah Jenkins (Owner)', 'OWNER', now
  );
  db.prepare(`INSERT INTO users (id, workspace_id, email, name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)`).run(
    'usr_apex_staff', 'ws_apex', 'staff@stockwise.com', 'Leo Martinez (Staff)', 'STAFF', now
  );

  // Categories & Units for Apex
  const apexCategories = ['Writing & Pens', 'Notebooks & Paper', 'Desk Organization', 'Filing & Folders', 'Adhesives & Tapes'];
  const apexUnits = ['piece', 'box', 'pack', 'pair', 'kilogram', 'metre', 'set'];

  const insertCat = db.prepare('INSERT OR IGNORE INTO categories (id, workspace_id, name) VALUES (?, ?, ?)');
  apexCategories.forEach((c, idx) => insertCat.run(`cat_apex_${idx}`, 'ws_apex', c));

  const insertUnit = db.prepare('INSERT OR IGNORE INTO units (id, workspace_id, name) VALUES (?, ?, ?)');
  apexUnits.forEach((u, idx) => insertUnit.run(`unit_apex_${idx}`, 'ws_apex', u));

  // Products for Apex
  const apexProducts = [
    {
      id: 'prd_001',
      sku: '00101',
      name: 'A5 Hardcover Grid Notebook',
      unit: 'piece',
      category: 'Notebooks & Paper',
      barcode: '890123456001',
      supplier: 'Midori Paper Co.',
      unit_cost: 3.20,
      selling_price: 7.99,
      min_stock: 15,
      current_stock: 42,
      notes: '120gsm fountain pen friendly paper',
      custom: { brand: 'ApexCraft', color: 'Navy Blue', shelf_loc: 'A1-03' }
    },
    {
      id: 'prd_002',
      sku: '00102',
      name: 'Gel Ink Pen 0.5mm (Black)',
      unit: 'box',
      category: 'Writing & Pens',
      barcode: '890123456002',
      supplier: 'Sakura Global Imports',
      unit_cost: 6.50,
      selling_price: 14.50,
      min_stock: 10,
      current_stock: 4, // LOW STOCK!
      notes: '12 pens per box, quick-dry pigment ink',
      custom: { brand: 'Fineline', color: 'Black', shelf_loc: 'B2-01' }
    },
    {
      id: 'prd_003',
      sku: '00103',
      name: 'Retractable Highlighter Assorted',
      unit: 'pack',
      category: 'Writing & Pens',
      barcode: '890123456003',
      supplier: 'Zebra Stationery',
      unit_cost: 2.80,
      selling_price: 6.25,
      min_stock: 8,
      current_stock: 24,
      notes: 'Pack of 5 pastel fluorescent colors',
      custom: { brand: 'GlowTone', color: 'Pastel Set', shelf_loc: 'B2-04' }
    },
    {
      id: 'prd_004',
      sku: '00104',
      name: 'Heavy Duty Metal Stapler',
      unit: 'piece',
      category: 'Desk Organization',
      barcode: '890123456004',
      supplier: 'Bostitch Industrial',
      unit_cost: 8.40,
      selling_price: 18.00,
      min_stock: 5,
      current_stock: 2, // LOW STOCK!
      notes: 'Takes standard 24/6 and 26/6 staples',
      custom: { brand: 'ProClamp', color: 'Matte Grey', shelf_loc: 'C1-02' }
    },
    {
      id: 'prd_005',
      sku: '00105',
      name: 'Kraft Expansion File Folder',
      unit: 'piece',
      category: 'Filing & Folders',
      barcode: '890123456005',
      supplier: 'EcoFile Supplies',
      unit_cost: 1.15,
      selling_price: 3.50,
      min_stock: 20,
      current_stock: 58,
      notes: '13 expandable accordion pockets',
      custom: { brand: 'EcoDoc', color: 'Kraft Brown', shelf_loc: 'D3-11' }
    },
    {
      id: 'prd_006',
      sku: '00106',
      name: 'Sticky Notes 3x3 Canary Yellow',
      unit: 'pack',
      category: 'Notebooks & Paper',
      barcode: '890123456006',
      supplier: '3M Distributors',
      unit_cost: 4.10,
      selling_price: 8.95,
      min_stock: 12,
      current_stock: 0, // OUT OF STOCK!
      notes: 'Pack of 12 pads, 100 sheets per pad',
      custom: { brand: 'StickSmart', color: 'Yellow', shelf_loc: 'A2-05' }
    },
    {
      id: 'prd_007',
      sku: '00107',
      name: 'Double-Sided Craft Tape 18mm',
      unit: 'roll',
      category: 'Adhesives & Tapes',
      barcode: '890123456007',
      supplier: 'Tesa Bond Tech',
      unit_cost: 0.90,
      selling_price: 2.40,
      min_stock: 15,
      current_stock: 35,
      notes: 'High adhesion acid-free craft tape',
      custom: { brand: 'BondUltra', color: 'Clear', shelf_loc: 'E1-09' }
    }
  ];

  const insertProd = db.prepare(`
    INSERT INTO products (
      id, workspace_id, sku, name, unit, category, barcode, supplier,
      unit_cost, selling_price, min_stock, notes, custom_values_json,
      current_stock, is_archived, created_at, updated_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
  `);

  apexProducts.forEach(p => {
    insertProd.run(
      p.id,
      'ws_apex',
      p.sku,
      p.name,
      p.unit,
      p.category,
      p.barcode,
      p.supplier,
      p.unit_cost,
      p.selling_price,
      p.min_stock,
      p.notes,
      JSON.stringify(p.custom),
      p.current_stock,
      now,
      now
    );
  });

  // Recent transactions for Apex
  const insertTx = db.prepare(`
    INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  const insertItem = db.prepare(`
    INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
  `);

  // TX 1: Stock In (Purchase received today)
  insertTx.run(
    'tx_001', 'ws_apex', 'STOCK_IN', 'Purchase received', today, 'Midori Paper Co.', 'PO-9821',
    'Morning weekly replenishment delivery', 'usr_apex_owner', 'Sarah Jenkins (Owner)', now
  );
  insertItem.run('txi_001', 'tx_001', 'prd_001', '00101', 'A5 Hardcover Grid Notebook', 'piece', 20, 22, 42);
  insertItem.run('txi_002', 'tx_001', 'prd_003', '00103', 'Retractable Highlighter Assorted', 'pack', 10, 14, 24);

  // TX 2: Stock Out (Sale today)
  insertTx.run(
    'tx_002', 'ws_apex', 'STOCK_OUT', 'Sale', today, 'City Academy Library', 'INV-4019',
    'School supply order', 'usr_apex_staff', 'Leo Martinez (Staff)', now
  );
  insertItem.run('txi_003', 'tx_002', 'prd_002', '00102', 'Gel Ink Pen 0.5mm (Black)', 'box', 6, 10, 4);
  insertItem.run('txi_004', 'tx_002', 'prd_005', '00105', 'Kraft Expansion File Folder', 'piece', 12, 70, 58);

  // TX 3: Stock Out (Damaged or lost)
  insertTx.run(
    'tx_003', 'ws_apex', 'STOCK_OUT', 'Damaged or lost', today, '', 'DISP-01',
    'Water damage on top shelf during rain', 'usr_apex_owner', 'Sarah Jenkins (Owner)', now
  );
  insertItem.run('txi_005', 'tx_003', 'prd_006', '00106', 'Sticky Notes 3x3 Canary Yellow', 'pack', 5, 5, 0);

  // 2. Create Workspace 2: Metro Hardware & Tools
  const metroSettings = {
    visible_fields: ['category', 'barcode', 'supplier', 'unit_cost', 'selling_price', 'min_stock', 'notes'],
    visible_columns: ['sku', 'name', 'category', 'current_stock', 'unit', 'status', 'selling_price', 'unit_cost', 'actions'],
    custom_fields: [
      { id: 'material', label: 'Material', type: 'text' },
      { id: 'size_spec', label: 'Size / Spec', type: 'text' },
      { id: 'bin_number', label: 'Bin Number', type: 'text' }
    ]
  };

  db.prepare(`
    INSERT INTO workspaces (id, name, slug, currency, timezone, logo_url, accent_color, item_alias, low_stock_threshold, settings_json, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  `).run(
    'ws_metro',
    'Metro Hardware & Tools',
    'metro-hardware',
    '£',
    'Europe/London',
    'https://images.unsplash.com/photo-1581783898377-1c85bf937427?w=100&auto=format&fit=crop&q=60',
    'blue',
    'Parts',
    10,
    JSON.stringify(metroSettings),
    now
  );

  db.prepare(`INSERT INTO users (id, workspace_id, email, name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)`).run(
    'usr_metro_owner', 'ws_metro', 'owner@stockwise.com', 'Dave Miller (Owner)', 'OWNER', now
  );
  db.prepare(`INSERT INTO users (id, workspace_id, email, name, role, created_at) VALUES (?, ?, ?, ?, ?, ?)`).run(
    'usr_metro_staff', 'ws_metro', 'staff@stockwise.com', 'Tom Clark (Staff)', 'STAFF', now
  );

  const metroCategories = ['Fasteners & Screws', 'Hand Tools', 'Electrical', 'Plumbing', 'Power Tool Accessories'];
  metroCategories.forEach((c, idx) => insertCat.run(`cat_metro_${idx}`, 'ws_metro', c));
  ['piece', 'box', 'pack', 'pair', 'kilogram', 'metre', 'set'].forEach((u, idx) => insertUnit.run(`unit_metro_${idx}`, 'ws_metro', u));

  const metroProducts = [
    {
      id: 'prd_m01',
      sku: '00201',
      name: 'Stainless Steel Wood Screws 4x40mm',
      unit: 'box',
      category: 'Fasteners & Screws',
      barcode: '501234567001',
      supplier: 'Apex Fasteners UK',
      unit_cost: 3.50,
      selling_price: 8.50,
      min_stock: 10,
      current_stock: 35,
      notes: '200 screws per box, countersunk head',
      custom: { material: 'Stainless A2', size_spec: '4x40mm', bin_number: 'BIN-14' }
    },
    {
      id: 'prd_m02',
      sku: '00202',
      name: 'Adjustable Wrench 250mm (10 inch)',
      unit: 'piece',
      category: 'Hand Tools',
      barcode: '501234567002',
      supplier: 'Bahco Tooling',
      unit_cost: 11.20,
      selling_price: 24.99,
      min_stock: 4,
      current_stock: 2, // LOW STOCK
      notes: 'Phosphated finish with ergonomic grip',
      custom: { material: 'Chrome Vanadium', size_spec: '250mm', bin_number: 'TOOL-02' }
    },
    {
      id: 'prd_m03',
      sku: '00203',
      name: 'Masonry Drill Bit Set (5-Piece)',
      unit: 'set',
      category: 'Power Tool Accessories',
      barcode: '501234567003',
      supplier: 'Bosch Professional',
      unit_cost: 5.80,
      selling_price: 13.50,
      min_stock: 6,
      current_stock: 18,
      notes: 'Tungsten carbide tipped 4-10mm',
      custom: { material: 'Carbide', size_spec: '4,5,6,8,10mm', bin_number: 'DRILL-08' }
    }
  ];

  metroProducts.forEach(p => {
    insertProd.run(
      p.id,
      'ws_metro',
      p.sku,
      p.name,
      p.unit,
      p.category,
      p.barcode,
      p.supplier,
      p.unit_cost,
      p.selling_price,
      p.min_stock,
      p.notes,
      JSON.stringify(p.custom),
      p.current_stock,
      now,
      now
    );
  });

  // Saved column mappings for instant spreadsheet recognition
  const insertMap = db.prepare('INSERT OR REPLACE INTO saved_column_mappings (workspace_id, source_header, target_field) VALUES (?, ?, ?)');
  const defaultMappings = [
    ['Item Code', 'sku'],
    ['SKU', 'sku'],
    ['Product Code', 'sku'],
    ['编码', 'sku'],
    ['Item Name', 'name'],
    ['Product Name', 'name'],
    ['品名', 'name'],
    ['Balance', 'current_stock'],
    ['Qty', 'current_stock'],
    ['On Hand', 'current_stock'],
    ['Stock Quantity', 'current_stock'],
    ['库存', 'current_stock'],
    ['UOM', 'unit'],
    ['Unit', 'unit'],
    ['单位', 'unit'],
    ['Cost Price', 'unit_cost'],
    ['Unit Cost', 'unit_cost'],
    ['成本', 'unit_cost'],
    ['Selling Price', 'selling_price'],
    ['Price', 'selling_price'],
    ['售价', 'selling_price'],
    ['Reorder Level', 'min_stock'],
    ['Min Stock', 'min_stock'],
    ['最低库存', 'min_stock'],
    ['Category', 'category'],
    ['分类', 'category'],
    ['Barcode', 'barcode'],
    ['条形码', 'barcode'],
    ['Supplier', 'supplier'],
    ['往来单位', 'supplier']
  ];

  ['ws_apex', 'ws_metro'].forEach(wsId => {
    defaultMappings.forEach(([hdr, fld]) => insertMap.run(wsId, hdr, fld));
  });
}

// Automatically seed on startup
seedDatabaseIfEmpty();

export default db;
