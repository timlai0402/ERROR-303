import type { NextApiRequest, NextApiResponse } from 'next';
import * as XLSX from 'xlsx';
import { getProducts, getTransactions, getWorkspace } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = getSession(req);
  const workspaceId = session.workspace.id;
  const { type, format } = req.query; // type: 'products' | 'transactions' | 'low_stock'

  const ws = getWorkspace(workspaceId);
  const settings = JSON.parse(ws?.settings_json || '{}');
  const customFields: { id: string; label: string }[] = settings.custom_fields || [];

  let dataRows: Record<string, any>[] = [];
  let filename = 'stockwise_export';

  if (type === 'transactions') {
    filename = `${ws?.slug || 'stockwise'}_movements`;
    const txs = getTransactions(workspaceId, { limit: 1000 });
    txs.forEach(t => {
      if (t.items && t.items.length > 0) {
        t.items.forEach((item: any) => {
          dataRows.push({
            'Date': t.date,
            'Type': t.type,
            'Reason': t.reason,
            'SKU': item.sku,
            'Product Name': item.product_name,
            'Quantity': item.quantity,
            'Unit': item.unit,
            'Balance Before': item.balance_before,
            'Balance After': item.balance_after,
            'Partner / Supplier / Customer': t.partner_name || '',
            'Reference': t.reference || '',
            'Created By': t.created_by_name,
            'Notes': t.notes || ''
          });
        });
      }
    });
  } else {
    // Products or Low Stock
    filename = type === 'low_stock' ? `${ws?.slug || 'stockwise'}_low_stock` : `${ws?.slug || 'stockwise'}_products`;
    const products = getProducts(workspaceId, {
      lowStockOnly: type === 'low_stock',
      role: session.user.role,
      includeArchived: false
    });

    dataRows = products.map(p => {
      let customObj: Record<string, any> = {};
      try {
        customObj = JSON.parse(p.custom_values_json || '{}');
      } catch (e) {}

      const row: Record<string, any> = {
        'SKU': p.sku,
        'Product Name': p.name,
        'Category': p.category || '',
        'Current Stock': p.current_stock,
        'Unit': p.unit,
        'Status': p.current_stock <= 0 ? 'Out of Stock' : (p.current_stock <= p.min_stock ? 'Low Stock' : 'In Stock'),
        'Min Stock Level': p.min_stock,
        'Selling Price': p.selling_price !== null ? p.selling_price : '',
        'Barcode': p.barcode || '',
        'Supplier': p.supplier || '',
        'Notes': p.notes || ''
      };

      if (session.user.role === 'OWNER') {
        row['Unit Cost'] = p.unit_cost !== null ? p.unit_cost : '';
        row['Total Valuation (Cost)'] = (p.unit_cost !== null && p.unit_cost !== undefined) ? (p.current_stock * p.unit_cost).toFixed(2) : '';
      }

      // Add custom fields
      customFields.forEach(cf => {
        row[cf.label] = customObj[cf.id] !== undefined ? customObj[cf.id] : '';
      });

      return row;
    });
  }

  const worksheet = XLSX.utils.json_to_sheet(dataRows);
  const workbook = XLSX.utils.book_new();
  XLSX.utils.book_append_sheet(workbook, worksheet, 'Export');

  if (format === 'csv') {
    const csv = XLSX.utils.sheet_to_csv(worksheet);
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', `attachment; filename="${filename}.csv"`);
    return res.status(200).send(csv);
  }

  const xlsxBuffer = XLSX.write(workbook, { type: 'buffer', bookType: 'xlsx' });
  res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  res.setHeader('Content-Disposition', `attachment; filename="${filename}.xlsx"`);
  return res.status(200).send(xlsxBuffer);
}
