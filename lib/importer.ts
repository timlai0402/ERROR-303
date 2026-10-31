import * as XLSX from 'xlsx';
import db from './db';
import { getProduct, getProducts, getWorkspace } from './inventory';

export interface ColumnSuggestion {
  sourceHeader: string;
  suggestedField: string;
  confidence: number; // 0 to 1
  isCustomField?: boolean;
}

export interface SheetParseResult {
  sheetNames: string[];
  selectedSheet: string;
  headers: string[];
  rows: Record<string, any>[];
  totalRows: number;
}

export interface ImportPreviewResult {
  canImport: boolean;
  totalRows: number;
  newProductsCount: number;
  existingProductsCount: number;
  invalidRowsCount: number;
  stockChangesCount: number;
  totalStockImpact: number;
  newProducts: any[];
  existingProducts: any[];
  invalidRows: { rowIndex: number; row: any; errors: string[] }[];
  mappingUsed: Record<string, string>;
}

// Target fields definition
export const TARGET_FIELDS = [
  { key: 'name', label: 'Product Name', required: true, description: 'Required' },
  { key: 'sku', label: 'SKU / Product Code', required: false, description: 'Auto-generated if empty' },
  { key: 'current_stock', label: 'Stock Quantity', required: false, description: 'Defaults to 0' },
  { key: 'unit', label: 'Unit of Measure', required: false, description: 'Defaults to piece' },
  { key: 'category', label: 'Category', required: false, description: 'Optional' },
  { key: 'barcode', label: 'Barcode', required: false, description: 'Optional' },
  { key: 'supplier', label: 'Supplier / Partner', required: false, description: 'Optional' },
  { key: 'unit_cost', label: 'Unit Cost', required: false, description: 'Owner only' },
  { key: 'selling_price', label: 'Selling Price', required: false, description: 'Optional' },
  { key: 'min_stock', label: 'Minimum Stock Level', required: false, description: 'Optional' },
  { key: 'notes', label: 'Notes', required: false, description: 'Optional' }
];

// Read File Buffer (CSV or XLSX) into sheet names and data
export function parseSpreadsheetBuffer(buffer: Buffer, targetSheet?: string): SheetParseResult {
  const workbook = XLSX.read(buffer, { type: 'buffer', raw: false });
  const sheetNames = workbook.SheetNames;
  if (!sheetNames || sheetNames.length === 0) {
    throw new Error('Spreadsheet does not contain any worksheets.');
  }

  const selectedSheet = targetSheet && sheetNames.includes(targetSheet) ? targetSheet : sheetNames[0];
  const worksheet = workbook.Sheets[selectedSheet];

  // Convert to array of objects with raw strings
  const jsonData = XLSX.utils.sheet_to_json<Record<string, any>>(worksheet, {
    raw: false,
    defval: ''
  });

  // Extract headers from first row
  const headers = jsonData.length > 0 ? Object.keys(jsonData[0]) : [];

  return {
    sheetNames,
    selectedSheet,
    headers,
    rows: jsonData,
    totalRows: jsonData.length
  };
}

// AI and Heuristic Column Matching
export function suggestColumnMappings(
  workspaceId: string,
  headers: string[]
): Record<string, ColumnSuggestion> {
  const ws = getWorkspace(workspaceId);
  const settings = JSON.parse(ws?.settings_json || '{}');
  const customFields: { id: string; label: string }[] = settings.custom_fields || [];

  // 1. Fetch previously remembered mappings for this business
  const savedMappings = db.prepare(`
    SELECT source_header, target_field FROM saved_column_mappings WHERE workspace_id = ?
  `).all(workspaceId) as { source_header: string; target_field: string }[];

  const savedMap = new Map(savedMappings.map(m => [m.source_header.toLowerCase().trim(), m.target_field]));

  // Standard heuristics & multilingual aliases
  const standardAliases: Record<string, string[]> = {
    name: [
      'product name', 'item name', 'name', 'product', 'item', 'description', 'title', 'goods',
      '品名', '商品名称', '物品名称', '商品名', '名称', '物料名称'
    ],
    sku: [
      'sku', 'item code', 'product code', 'code', 'part number', 'part #', 'item #', 'sku code',
      '编码', '商品编码', '商品货号', '货号', '物料代码', '代码'
    ],
    current_stock: [
      'current stock', 'stock', 'quantity', 'qty', 'balance', 'on hand', 'opening stock', 'inventory', 'count',
      '库存', '库存量', '现有库存', '当前库存', '初始库存', '数量', '在库'
    ],
    unit: [
      'unit', 'uom', 'unit of measure', 'unit type',
      '单位', '计量单位', '规格单位'
    ],
    category: [
      'category', 'group', 'type', 'dept', 'department', 'class',
      '分类', '类别', '商品类别', '所属分类'
    ],
    barcode: [
      'barcode', 'upc', 'ean', 'isbn', 'barcode number',
      '条码', '条形码', '一维码'
    ],
    supplier: [
      'supplier', 'vendor', 'partner', 'distributor', 'source',
      '供应商', '往来单位', '供货商', '来往单位'
    ],
    unit_cost: [
      'unit cost', 'cost price', 'cost', 'buy price', 'purchase price',
      '成本', '成本价', '进价', '采购单价'
    ],
    selling_price: [
      'selling price', 'price', 'retail price', 'sale price', 'list price', 'unit price',
      '售价', '销售单价', '单价', '零售价'
    ],
    min_stock: [
      'min stock', 'minimum stock', 'reorder level', 'reorder point', 'safety stock', 'threshold',
      '最低库存', '最低保有量', '预警库存', '警戒库存'
    ],
    notes: [
      'notes', 'note', 'remarks', 'comment', 'memo',
      '备注', '说明', '附注'
    ]
  };

  const suggestions: Record<string, ColumnSuggestion> = {};

  for (const header of headers) {
    const cleanHeader = header.trim();
    const lowerHeader = cleanHeader.toLowerCase();

    // Check saved mapping first
    if (savedMap.has(lowerHeader)) {
      suggestions[header] = {
        sourceHeader: header,
        suggestedField: savedMap.get(lowerHeader)!,
        confidence: 0.99
      };
      continue;
    }

    // Check custom fields
    let customMatch: string | null = null;
    for (const cf of customFields) {
      if (cf.label.toLowerCase() === lowerHeader || cf.id.toLowerCase() === lowerHeader) {
        customMatch = `custom_${cf.id}`;
        break;
      }
    }

    if (customMatch) {
      suggestions[header] = {
        sourceHeader: header,
        suggestedField: customMatch,
        confidence: 0.95,
        isCustomField: true
      };
      continue;
    }

    // Check standard aliases
    let matchedField: string = '';
    let highestConfidence = 0;

    for (const [targetKey, aliases] of Object.entries(standardAliases)) {
      for (const alias of aliases) {
        if (lowerHeader === alias) {
          matchedField = targetKey;
          highestConfidence = 0.95;
          break;
        } else if (lowerHeader.includes(alias) || alias.includes(lowerHeader)) {
          if (highestConfidence < 0.75) {
            matchedField = targetKey;
            highestConfidence = 0.75;
          }
        }
      }
      if (highestConfidence >= 0.95) break;
    }

    suggestions[header] = {
      sourceHeader: header,
      suggestedField: matchedField,
      confidence: highestConfidence
    };
  }

  return suggestions;
}

// Remember column mappings for future uploads
export function rememberColumnMappings(
  workspaceId: string,
  mappings: Record<string, string>
) {
  const insert = db.prepare(`
    INSERT OR REPLACE INTO saved_column_mappings (workspace_id, source_header, target_field)
    VALUES (?, ?, ?)
  `);

  const tx = db.transaction(() => {
    for (const [src, tgt] of Object.entries(mappings)) {
      if (tgt && tgt.trim()) {
        insert.run(workspaceId, src.trim(), tgt.trim());
      }
    }
  });
  tx();
}

// Generate Preview and Validate
export function generateImportPreview(
  workspaceId: string,
  rows: Record<string, any>[],
  mappings: Record<string, string>,
  updateStockFromSpreadsheet: boolean = false
): ImportPreviewResult {
  const existingProducts = getProducts(workspaceId, { includeArchived: true });
  const skuToProduct = new Map(existingProducts.map(p => [p.sku.toLowerCase(), p]));
  const nameToProduct = new Map(existingProducts.map(p => [p.name.toLowerCase(), p]));

  const seenSkusInFile = new Set<string>();
  const invalidRows: { rowIndex: number; row: any; errors: string[] }[] = [];
  const newProductsList: any[] = [];
  const existingProductsList: any[] = [];
  let totalStockImpact = 0;
  let stockChangesCount = 0;

  rows.forEach((row, idx) => {
    const rowIndex = idx + 1;
    const errors: string[] = [];

    // Extract mapped values
    const item: Record<string, any> = {};
    const customValues: Record<string, any> = {};

    for (const [header, targetKey] of Object.entries(mappings)) {
      if (!targetKey) continue;
      const rawVal = row[header];
      const strVal = rawVal !== undefined && rawVal !== null ? String(rawVal).trim() : '';

      if (targetKey.startsWith('custom_')) {
        const customId = targetKey.replace('custom_', '');
        customValues[customId] = strVal;
      } else {
        item[targetKey] = strVal;
      }
    }

    // Validation 1: Required product name
    if (!item.name || !item.name.trim()) {
      errors.push('Missing required Product Name.');
    }

    // Preserve leading zeros in SKU if provided
    let sku = item.sku ? String(item.sku).trim() : '';
    if (sku) {
      if (seenSkusInFile.has(sku.toLowerCase())) {
        errors.push(`Duplicate SKU "${sku}" appears multiple times in this spreadsheet.`);
      } else {
        seenSkusInFile.add(sku.toLowerCase());
      }
    }

    // Number validations
    let stockQty = 0;
    if (item.current_stock !== undefined && item.current_stock !== '') {
      const num = Number(item.current_stock);
      if (isNaN(num) || num < 0) {
        errors.push(`Invalid stock quantity: "${item.current_stock}". Must be a non-negative number.`);
      } else {
        stockQty = num;
      }
    }

    let unitCost: number | null = null;
    if (item.unit_cost !== undefined && item.unit_cost !== '') {
      const num = Number(item.unit_cost);
      if (isNaN(num) || num < 0) {
        errors.push(`Invalid unit cost: "${item.unit_cost}".`);
      } else {
        unitCost = num;
      }
    }

    let sellingPrice: number | null = null;
    if (item.selling_price !== undefined && item.selling_price !== '') {
      const num = Number(item.selling_price);
      if (isNaN(num) || num < 0) {
        errors.push(`Invalid selling price: "${item.selling_price}".`);
      } else {
        sellingPrice = num;
      }
    }

    let minStock: number = 5;
    if (item.min_stock !== undefined && item.min_stock !== '') {
      const num = Number(item.min_stock);
      if (isNaN(num) || num < 0) {
        errors.push(`Invalid minimum stock: "${item.min_stock}".`);
      } else {
        minStock = num;
      }
    }

    if (errors.length > 0) {
      invalidRows.push({ rowIndex, row, errors });
      return;
    }

    // Check if this matches an existing product by SKU or Name
    let existing = (sku && skuToProduct.get(sku.toLowerCase())) || nameToProduct.get(item.name.toLowerCase());

    const preparedItem = {
      rowIndex,
      sku: sku || 'Auto-generate',
      name: item.name,
      unit: item.unit || 'piece',
      category: item.category || 'General',
      barcode: item.barcode || '',
      supplier: item.supplier || '',
      unit_cost: unitCost,
      selling_price: sellingPrice,
      min_stock: minStock,
      notes: item.notes || '',
      custom_values: customValues,
      file_stock: stockQty,
      existing_stock: existing ? existing.current_stock : 0,
      stock_delta: existing ? (stockQty - existing.current_stock) : stockQty
    };

    if (existing) {
      if (updateStockFromSpreadsheet && preparedItem.stock_delta !== 0) {
        stockChangesCount++;
        totalStockImpact += preparedItem.stock_delta;
      }
      existingProductsList.push({
        ...preparedItem,
        existing_id: existing.id,
        existing_sku: existing.sku
      });
    } else {
      newProductsList.push(preparedItem);
      if (stockQty > 0) {
        totalStockImpact += stockQty;
        stockChangesCount++;
      }
    }
  });

  return {
    canImport: invalidRows.length === 0 || newProductsList.length > 0 || existingProductsList.length > 0,
    totalRows: rows.length,
    newProductsCount: newProductsList.length,
    existingProductsCount: existingProductsList.length,
    invalidRowsCount: invalidRows.length,
    stockChangesCount,
    totalStockImpact,
    newProducts: newProductsList,
    existingProducts: existingProductsList,
    invalidRows,
    mappingUsed: mappings
  };
}

// Execute Import into Database (Atomic Transaction)
export function executeImport(
  workspaceId: string,
  preview: ImportPreviewResult,
  updateStockFromSpreadsheet: boolean,
  user: { id: string; name: string }
) {
  const now = new Date().toISOString();
  const today = now.slice(0, 10);
  let importedCount = 0;
  let updatedCount = 0;

  const tx = db.transaction(() => {
    // 1. Insert New Products
    for (const item of preview.newProducts) {
      const id = `prd_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
      const sku = item.sku !== 'Auto-generate' ? item.sku : undefined;

      const newProd = db.prepare(`
        INSERT INTO products (
          id, workspace_id, sku, name, unit, category, barcode, supplier,
          unit_cost, selling_price, min_stock, notes, custom_values_json,
          current_stock, is_archived, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
      `).run(
        id,
        workspaceId,
        sku || `SKU-${Date.now().toString().slice(-4)}`,
        item.name,
        item.unit,
        item.category,
        item.barcode || null,
        item.supplier || null,
        item.unit_cost,
        item.selling_price,
        item.min_stock,
        item.notes || null,
        JSON.stringify(item.custom_values || {}),
        item.file_stock,
        now,
        now
      );

      // Record transaction if opening stock > 0
      if (item.file_stock > 0) {
        const txId = `tx_imp_${id}`;
        db.prepare(`
          INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
          VALUES (?, ?, 'STOCK_IN', 'Opening stock', ?, ?, 'SPREADSHEET-IMPORT', 'Imported from spreadsheet', ?, ?, ?)
        `).run(
          txId,
          workspaceId,
          today,
          item.supplier || '',
          user.id,
          user.name,
          now
        );

        db.prepare(`
          INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
          VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?)
        `).run(
          `txi_${txId}_1`,
          txId,
          id,
          item.sku,
          item.name,
          item.unit,
          item.file_stock,
          item.file_stock
        );
      }
      importedCount++;
    }

    // 2. Update Existing Products
    for (const item of preview.existingProducts) {
      if (updateStockFromSpreadsheet && item.stock_delta !== 0) {
        // Record explicit adjustment
        const txId = `tx_adj_imp_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`;
        db.prepare(`
          INSERT INTO transactions (id, workspace_id, type, reason, date, partner_name, reference, notes, created_by_user_id, created_by_name, created_at)
          VALUES (?, ?, 'ADJUSTMENT', 'Spreadsheet import adjustment', ?, ?, 'IMPORT-ADJUSTMENT', ?, ?, ?, ?)
        `).run(
          txId,
          workspaceId,
          today,
          item.supplier || '',
          `Spreadsheet updated stock from ${item.existing_stock} to ${item.file_stock} ${item.unit}`,
          user.id,
          user.name,
          now
        );

        db.prepare(`
          INSERT INTO transaction_items (id, transaction_id, product_id, sku, product_name, unit, quantity, balance_before, balance_after)
          VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        `).run(
          `txi_${Date.now()}_${Math.random().toString(36).substring(2, 6)}`,
          txId,
          item.existing_id,
          item.existing_sku,
          item.name,
          item.unit,
          Math.abs(item.stock_delta),
          item.existing_stock,
          item.file_stock
        );

        db.prepare(`
          UPDATE products
          SET name = ?, unit = ?, category = ?, barcode = ?, supplier = ?,
              unit_cost = COALESCE(?, unit_cost), selling_price = COALESCE(?, selling_price),
              min_stock = ?, current_stock = ?, updated_at = ?
          WHERE workspace_id = ? AND id = ?
        `).run(
          item.name, item.unit, item.category, item.barcode || null, item.supplier || null,
          item.unit_cost, item.selling_price, item.min_stock, item.file_stock, now,
          workspaceId, item.existing_id
        );
      } else {
        // Update details without touching stock
        db.prepare(`
          UPDATE products
          SET name = ?, unit = ?, category = ?, barcode = ?, supplier = ?,
              unit_cost = COALESCE(?, unit_cost), selling_price = COALESCE(?, selling_price),
              min_stock = ?, updated_at = ?
          WHERE workspace_id = ? AND id = ?
        `).run(
          item.name, item.unit, item.category, item.barcode || null, item.supplier || null,
          item.unit_cost, item.selling_price, item.min_stock, now,
          workspaceId, item.existing_id
        );
      }
      updatedCount++;
    }
  });

  tx();
  return {
    success: true,
    importedCount,
    updatedCount,
    totalProcessed: importedCount + updatedCount
  };
}

// Generate Error File buffer for rejected rows
export function generateErrorWorkbook(invalidRows: { rowIndex: number; row: any; errors: string[] }[]) {
  const data = invalidRows.map(r => ({
    ...r.row,
    '_STOCKWISE_ROW': r.rowIndex,
    '_STOCKWISE_ERRORS': r.errors.join('; ')
  }));
  const ws = XLSX.utils.json_to_sheet(data);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Rejected Rows');
  return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
}

// Generate Sample Template
export function generateSampleTemplate(type: 'csv' | 'xlsx' = 'xlsx') {
  const sampleData = [
    {
      'Item Code': '00108',
      'Item Name': 'A4 Spiral Notebook 80-Pages',
      'Unit': 'piece',
      'Category': 'Notebooks & Paper',
      'Stock Quantity': 50,
      'Unit Cost': 1.85,
      'Selling Price': 4.50,
      'Min Stock': 15,
      'Supplier': 'National Paper Mills',
      'Barcode': '890123456008',
      'Notes': 'Perforated sheets, college ruled'
    },
    {
      'Item Code': '00109',
      'Item Name': 'Correction Tape 5mm x 12m',
      'Unit': 'piece',
      'Category': 'Writing & Pens',
      'Stock Quantity': 12,
      'Unit Cost': 0.95,
      'Selling Price': 2.25,
      'Min Stock': 10,
      'Supplier': 'Tombow Supply',
      'Barcode': '890123456009',
      'Notes': 'Tear-resistant tape'
    },
    {
      'Item Code': '00110',
      'Item Name': 'Binder Clips Medium 25mm (Pack of 12)',
      'Unit': 'pack',
      'Category': 'Desk Organization',
      'Stock Quantity': 4,
      'Unit Cost': 1.10,
      'Selling Price': 2.99,
      'Min Stock': 8,
      'Supplier': 'OfficeDirect',
      'Barcode': '890123456010',
      'Notes': 'Tempered steel construction'
    }
  ];

  const ws = XLSX.utils.json_to_sheet(sampleData);
  const wb = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(wb, ws, 'Inventory');

  if (type === 'csv') {
    return XLSX.utils.sheet_to_csv(ws);
  }
  return XLSX.write(wb, { type: 'buffer', bookType: 'xlsx' });
}
