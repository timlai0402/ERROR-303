import type { NextApiRequest, NextApiResponse } from 'next';
import { answerInventoryQuestion } from '@/lib/ai';
import { getSession } from '@/lib/session';

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  const session = getSession(req);
  const { question } = req.body;

  if (!question || !question.trim()) {
    return res.status(400).json({ error: 'Question is required.' });
  }

  try {
    const result = await answerInventoryQuestion(session.workspace.id, question.trim(), session.user.role);
    return res.status(200).json(result);
  } catch (err: any) {
    return res.status(500).json({ error: err.message || 'AI processing error' });
  }
}
