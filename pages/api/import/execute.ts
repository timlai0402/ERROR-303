import type { NextApiRequest, NextApiResponse } from 'next';
import {
  parseSpreadsheetBuffer,
  generateImportPreview,
  executeImport,
  rememberColumnMappings
} from '@/lib/importer';
import { getSession } from '@/lib/session';

export const config = {
  api: {
    bodyParser: {
      sizeLimit: '10mb'
    }
  }
};

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', ['POST']);
    return res.status(405).end(`Method ${req.method} Not Allowed`);
  }

  const session = getSession(req);
  if (session.user.role !== 'OWNER') {
    return res.status(403).json({ error: 'Permission denied: Spreadsheet imports are restricted to the Business Owner.' });
  }

  try {
    const { fileBase64, selectedSheet, mappings, updateStock } = req.body;

    if (!fileBase64 || !mappings) {
      return res.status(400).json({ error: 'File data and column mappings are required.' });
    }

    const buffer = Buffer.from(fileBase64, 'base64');
    const parsed = parseSpreadsheetBuffer(buffer, selectedSheet);

    // Compute preview
    const preview = generateImportPreview(
      session.workspace.id,
      parsed.rows,
      mappings,
      updateStock === true
    );

    if (!preview.canImport) {
      return res.status(400).json({
        error: 'Cannot import spreadsheet: All rows have validation errors.',
        invalidRows: preview.invalidRows
      });
    }

    // Remember confirmed mappings for future uploads
    rememberColumnMappings(session.workspace.id, mappings);

    // Execute atomic import
    const result = executeImport(
      session.workspace.id,
      preview,
      updateStock === true,
      { id: session.user.id, name: session.user.name }
    );

    return res.status(200).json({
      success: true,
      result,
      preview
    });
  } catch (err: any) {
    return res.status(400).json({ error: err.message || 'Import execution failed' });
  }
}
