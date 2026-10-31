import type { NextApiRequest, NextApiResponse } from 'next';
import { getSession } from '@/lib/session';
import { getAllWorkspaces, getWorkspace } from '@/lib/inventory';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method === 'GET') {
    const session = getSession(req);
    const workspaces = getAllWorkspaces();
    return res.status(200).json({
      ...session,
      allWorkspaces: workspaces
    });
  }

  if (req.method === 'POST') {
    // Switch role or workspace
    const { role, workspaceId } = req.body;
    const cookiesToSet: string[] = [];

    if (role && (role === 'OWNER' || role === 'STAFF')) {
      cookiesToSet.push(`stockwise_role=${role}; Path=/; SameSite=Lax`);
    }

    if (workspaceId) {
      const ws = getWorkspace(workspaceId);
      if (ws) {
        cookiesToSet.push(`stockwise_workspace_id=${ws.id}; Path=/; SameSite=Lax`);
      }
    }

    if (cookiesToSet.length > 0) {
      res.setHeader('Set-Cookie', cookiesToSet);
    }

    const session = getSession(req);
    return res.status(200).json({ success: true, ...session });
  }

  res.setHeader('Allow', ['GET', 'POST']);
  res.status(405).end(`Method ${req.method} Not Allowed`);
}
