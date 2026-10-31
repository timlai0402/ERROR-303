import { NextApiRequest, NextApiResponse } from 'next';
import db from './db';
import { getWorkspace } from './inventory';

export interface UserSession {
  user: {
    id: string;
    email: string;
    name: string;
    role: 'OWNER' | 'STAFF';
  };
  workspace: any;
}

export function getSession(req: NextApiRequest): UserSession {
  // Read workspace from cookie or query or default
  const cookies = req.headers.cookie || '';
  const wsMatch = cookies.match(/stockwise_workspace_id=([^;]+)/);
  const roleMatch = cookies.match(/stockwise_role=([^;]+)/);

  const workspaceId = (req.headers['x-workspace-id'] as string) || (wsMatch ? wsMatch[1] : 'ws_apex');
  const roleOverride = (req.headers['x-user-role'] as string) || (roleMatch ? (roleMatch[1] as 'OWNER' | 'STAFF') : 'OWNER');

  let workspace = getWorkspace(workspaceId);
  if (!workspace) {
    workspace = db.prepare('SELECT * FROM workspaces LIMIT 1').get() as any;
  }

  // Find user for this workspace or fallback
  let user = db.prepare('SELECT * FROM users WHERE workspace_id = ? AND role = ? LIMIT 1').get(workspace.id, roleOverride) as any;
  if (!user) {
    user = {
      id: `usr_${roleOverride.toLowerCase()}_${workspace.id}`,
      email: `${roleOverride.toLowerCase()}@stockwise.com`,
      name: roleOverride === 'OWNER' ? 'Business Owner' : 'Staff Member',
      role: roleOverride,
      workspace_id: workspace.id
    };
  } else {
    // If user role was overridden by the header/cookie switcher
    user.role = roleOverride;
  }

  return {
    user,
    workspace
  };
}

export function requireOwner(req: NextApiRequest, res: NextApiResponse): boolean {
  const session = getSession(req);
  if (session.user.role !== 'OWNER') {
    res.status(403).json({ error: 'Permission denied: This action is restricted to the Business Owner.' });
    return false;
  }
  return true;
}
