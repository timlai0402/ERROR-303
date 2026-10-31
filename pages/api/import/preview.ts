import type { NextApiRequest, NextApiResponse } from 'next';
import {
  parseSpreadsheetBuffer,
  suggestColumnMappings,
  generateImportPreview,
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

export default async function handler(req: NextApiRequest, res: NextApiResponse) {
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

    if (!fileBase64) {
      return res.status(400).json({ error: 'Spreadsheet file data is required.' });
    }

    const buffer = Buffer.from(fileBase64, 'base64');
    const parsed = parseSpreadsheetBuffer(buffer, selectedSheet);

    // If mappings were not provided yet (step 1), suggest them using AI/heuristics
    let activeMappings = mappings;
    let suggestions = {};

    if (!activeMappings || Object.keys(activeMappings).length === 0) {
      const suggestedObj = suggestColumnMappings(session.workspace.id, parsed.headers);
      suggestions = suggestedObj;
      activeMappings = {};
      for (const [hdr, sugg] of Object.entries(suggestedObj)) {
        if (sugg.suggestedField) {
          activeMappings[hdr] = sugg.suggestedField;
        }
      }
    }

    // Generate preview
    const preview = generateImportPreview(
      session.workspace.id,
      parsed.rows,
      activeMappings,
      updateStock === true
    );

    return res.status(200).json({
      sheetNames: parsed.sheetNames,
      selectedSheet: parsed.selectedSheet,
      headers: parsed.headers,
      totalRows: parsed.totalRows,
      suggestions,
      mappings: activeMappings,
      preview
    });
  } catch (err: any) {
    return res.status(400).json({ error: err.message || 'Failed to process spreadsheet' });
  }
}
