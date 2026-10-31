import type { NextApiRequest, NextApiResponse } from 'next';
import { getProduct, updateProduct, archiveProduct, getProductHistory } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = getSession(req);
  const workspaceId = session.workspace.id;
  const { id } = req.query;
  const productId = Array.isArray(id) ? id[0] : id;

  if (!productId) {
    return res.status(400).json({ error: 'Product ID required' });
  }

  if (req.method === 'GET') {
    const product = getProduct(workspaceId, productId, session.user.role);
    if (!product) return res.status(404).json({ error: 'Product not found' });

    const history = getProductHistory(workspaceId, product.id);
    return res.status(200).json({
      product,
      history
    });
  }

  if (req.method === 'PUT') {
    if (session.user.role !== 'OWNER') {
      return res.status(403).json({ error: 'Permission denied: Modifying products is restricted to the Business Owner.' });
    }

    try {
      const updated = updateProduct(workspaceId, productId, req.body);
      return res.status(200).json(updated);
    } catch (err: any) {
      return res.status(400).json({ error: err.message || 'Failed to update product' });
    }
  }

  if (req.method === 'DELETE') {
    if (session.user.role !== 'OWNER') {
      return res.status(403).json({ error: 'Permission denied: Archiving products is restricted to the Business Owner.' });
    }

    try {
      const result = archiveProduct(workspaceId, productId);
      return res.status(200).json({ success: true, ...result });
    } catch (err: any) {
      return res.status(400).json({ error: err.message || 'Failed to archive product' });
    }
  }

  res.setHeader('Allow', ['GET', 'PUT', 'DELETE']);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
