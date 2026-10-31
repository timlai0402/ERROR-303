import type { NextApiRequest, NextApiResponse } from 'next';
import { getProducts, createProduct, generateNextSku, getCategories, getUnits } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = getSession(req);
  const workspaceId = session.workspace.id;

  if (req.method === 'GET') {
    const { search, category, lowStock, archived } = req.query;

    const products = getProducts(workspaceId, {
      search: typeof search === 'string' ? search : undefined,
      category: typeof category === 'string' ? category : undefined,
      lowStockOnly: lowStock === 'true',
      includeArchived: archived === 'true',
      role: session.user.role
    });

    const categories = getCategories(workspaceId);
    const units = getUnits(workspaceId);
    const nextSku = generateNextSku(workspaceId);

    return res.status(200).json({
      products,
      categories,
      units,
      nextSku
    });
  }

  if (req.method === 'POST') {
    if (session.user.role !== 'OWNER') {
      return res.status(403).json({ error: 'Permission denied: Adding or managing products is restricted to the Business Owner.' });
    }

    try {
      const {
        name, sku, unit, category, barcode, supplier,
        unit_cost, selling_price, min_stock, opening_stock,
        notes, photo_url, custom_values
      } = req.body;

      if (!name || !name.trim()) {
        return res.status(400).json({ error: 'Product name is required.' });
      }

      const product = createProduct(workspaceId, {
        name: name.trim(),
        sku: sku ? sku.trim() : undefined,
        unit: unit || 'piece',
        category: category || undefined,
        barcode: barcode || undefined,
        supplier: supplier || undefined,
        unit_cost: unit_cost !== undefined && unit_cost !== '' ? Number(unit_cost) : undefined,
        selling_price: selling_price !== undefined && selling_price !== '' ? Number(selling_price) : undefined,
        min_stock: min_stock !== undefined && min_stock !== '' ? Number(min_stock) : 5,
        opening_stock: opening_stock !== undefined && opening_stock !== '' ? Number(opening_stock) : 0,
        notes: notes || undefined,
        photo_url: photo_url || undefined,
        custom_values: custom_values || {}
      }, {
        id: session.user.id,
        name: session.user.name
      });

      return res.status(201).json(product);
    } catch (err: any) {
      return res.status(400).json({ error: err.message || 'Failed to create product' });
    }
  }

  res.setHeader('Allow', ['GET', 'POST']);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
