import type { NextApiRequest, NextApiResponse } from 'next';
import { getTodayMetrics } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', ['GET']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  const session = getSession(req);
  const metrics = getTodayMetrics(session.workspace.id);

  return res.status(200).json(metrics);
}
