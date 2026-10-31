import type { NextApiRequest, NextApiResponse } from 'next';
import { generateSampleTemplate } from '@/lib/importer';

export default function handler(req: NextApiRequest, res: NextApiResponse) {
  const { format } = req.query;

  if (format === 'csv') {
    const csv = generateSampleTemplate('csv') as string;
    res.setHeader('Content-Type', 'text/csv');
    res.setHeader('Content-Disposition', 'attachment; filename="stockwise_template.csv"');
    return res.status(200).send(csv);
  }

  const xlsxBuffer = generateSampleTemplate('xlsx') as Buffer;
  res.setHeader('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
  res.setHeader('Content-Disposition', 'attachment; filename="stockwise_template.xlsx"');
  return res.status(200).send(xlsxBuffer);
}
