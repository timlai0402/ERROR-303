import type { NextApiRequest, NextApiResponse } from 'next';
import { createWorkspace, getAllWorkspaces } from '@/lib/inventory';
import { getSession } from '@/lib/session';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    const workspaces = getAllWorkspaces();
    return res.status(200).json(workspaces);
  }

  if (req.method === 'POST') {
    const { name, currency, timezone, logo_url, accent_color } = req.body;
    if (!name || !name.trim()) {
      return res.status(400).json({ error: 'Business name is required.' });
    }

    try {
      const workspace = createWorkspace({
        name: name.trim(),
        currency: currency || '$',
        timezone: timezone || 'UTC',
        logo_url: logo_url || undefined,
        accent_color: accent_color || 'mint'
      });

      // Switch cookie to this new workspace
      res.setHeader('Set-Cookie', [
        `stockwise_workspace_id=${workspace.id}; Path=/; SameSite=Lax`,
        `stockwise_role=OWNER; Path=/; SameSite=Lax`
      ]);

      return res.status(201).json(workspace);
    } catch (err: any) {
      return res.status(500).json({ error: err.message || 'Failed to create workspace' });
    }
  }

  res.setHeader('Allow', ['GET', 'POST']);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
