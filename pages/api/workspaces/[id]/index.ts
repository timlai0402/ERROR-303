import type { NextApiRequest, NextApiResponse } from 'next';
import { getWorkspace, updateWorkspaceSettings } from '@/lib/inventory';
import { requireOwner } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { id } = req.query;
  const workspaceId = Array.isArray(id) ? id[0] : id;

  if (!workspaceId) {
    return res.status(400).json({ error: 'Workspace ID required' });
  }

  if (req.method === 'GET') {
    const ws = getWorkspace(workspaceId);
    if (!ws) return res.status(404).json({ error: 'Workspace not found' });
    return res.status(200).json(ws);
  }

  if (req.method === 'PUT') {
    if (!requireOwner(req, res)) return;

    try {
      const updated = updateWorkspaceSettings(workspaceId, req.body);
      return res.status(200).json(updated);
    } catch (err: any) {
      return res.status(500).json({ error: err.message || 'Failed to update settings' });
    }
  }

  res.setHeader('Allow', ['GET', 'PUT']);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
