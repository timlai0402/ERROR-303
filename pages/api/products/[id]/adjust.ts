import type { NextApiRequest, NextApiResponse } from 'next';
import { correctStockCount } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  const session = getSession(req);
  if (session.user.role !== 'OWNER') {
    return res.status(403).json({ error: 'Permission denied: Correcting stock count is restricted to the Business Owner.' });
  }

  const { id } = req.query;
  const productId = Array.isArray(id) ? id[0] : id;

  if (!productId) {
    return res.status(400).json({ error: 'Product ID required' });
  }

  const { actual_count, reason, notes } = req.body;
  if (actual_count === undefined || actual_count === null || actual_count === '') {
    return res.status(400).json({ error: 'Actual counted quantity is required.' });
  }

  if (!reason || !reason.trim()) {
    return res.status(400).json({ error: 'Reason for count correction is required.' });
  }

  try {
    const updatedProduct = correctStockCount(session.workspace.id, {
      product_id: productId,
      actual_count: Number(actual_count),
      reason: reason.trim(),
      notes: notes ? notes.trim() : undefined
    }, {
      id: session.user.id,
      name: session.user.name
    });

    return res.status(200).json({ success: true, product: updatedProduct });
  } catch (err: any) {
    return res.status(400).json({ error: err.message || 'Failed to correct stock count' });
  }
}
