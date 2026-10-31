import type { NextApiRequest, NextApiResponse } from 'next';
import { getTransactions, recordStockIn, recordStockOut } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const session = getSession(req);
  const workspaceId = session.workspace.id;

  if (req.method === 'GET') {
    const { type, productId, startDate, endDate, limit } = req.query;

    const txs = getTransactions(workspaceId, {
      type: typeof type === 'string' && (type === 'STOCK_IN' || type === 'STOCK_OUT' || type === 'ADJUSTMENT') ? type : undefined,
      productId: typeof productId === 'string' ? productId : undefined,
      startDate: typeof startDate === 'string' ? startDate : undefined,
      endDate: typeof endDate === 'string' ? endDate : undefined,
      limit: limit ? Number(limit) : 100
    });

    return res.status(200).json(txs);
  }

  if (req.method === 'POST') {
    const { type, reason, date, partner_name, reference, notes, items } = req.body;

    if (!type || (type !== 'STOCK_IN' && type !== 'STOCK_OUT')) {
      return res.status(400).json({ error: 'Transaction type must be STOCK_IN or STOCK_OUT.' });
    }

    if (!reason || !reason.trim()) {
      return res.status(400).json({ error: 'Reason is required.' });
    }

    if (!items || !Array.isArray(items) || items.length === 0) {
      return res.status(400).json({ error: 'At least one item must be added to this transaction.' });
    }

    try {
      const user = { id: session.user.id, name: session.user.name };

      if (type === 'STOCK_IN') {
        const tx = recordStockIn(workspaceId, {
          reason: reason.trim(),
          date,
          partner_name,
          reference,
          notes,
          items
        }, user);
        return res.status(201).json(tx);
      } else {
        const tx = recordStockOut(workspaceId, {
          reason: reason.trim(),
          date,
          partner_name,
          reference,
          notes,
          items
        }, user);
        return res.status(201).json(tx);
      }
    } catch (err: any) {
      return res.status(400).json({ error: err.message || 'Failed to record transaction' });
    }
  }

  res.setHeader('Allow', ['GET', 'POST']);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
