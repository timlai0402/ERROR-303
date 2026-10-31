import type { NextApiRequest, NextApiResponse } from 'next';
import { parseTransactionIntent } from '@/lib/ai';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  const session = getSession(req);
  const { text } = req.body;

  if (!text || !text.trim()) {
    return res.status(400).json({ error: 'Instruction text is required.' });
  }

  try {
    const draft = parseTransactionIntent(session.workspace.id, text.trim());
    return res.status(200).json(draft);
  } catch (err: any) {
    return res.status(400).json({ error: err.message || 'Failed to parse instruction' });
  }
}
