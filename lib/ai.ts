import db from './db';
import { getProduct, getProducts, getWorkspace } from './inventory';

export interface AiChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  supportingData?: any;
  actionDraft?: any;
}

export interface ParsedDraft {
  type: 'STOCK_IN' | 'STOCK_OUT';
  reason: string;
  partner_name: string;
  items: {
    product_id: string;
    sku: string;
    product_name: string;
    unit: string;
    quantity: number;
    current_stock: number;
    expected_balance: number;
    isAmbiguous?: boolean;
    candidateProducts?: { id: string; name: string; sku: string; current_stock: number }[];
  }[];
  confidence: number;
  rawText: string;
}

// 1. Natural Language Inventory Q&A Engine
export async function answerInventoryQuestion(workspaceId: string, question: string, role: 'OWNER' | 'STAFF' = 'OWNER'): Promise<{
  answer: string;
  supportingData: any;
}> {
  const q = question.toLowerCase().trim();
  const ws = getWorkspace(workspaceId);
  const currency = ws?.currency || '$';

  // Question Type 1: Low stock / out of stock
  if (q.includes('low') || q.includes('shortage') || q.includes('out of stock') || q.includes('reorder') || q.includes('warn')) {
    const lowStock = db.prepare(`
      SELECT sku, name, current_stock, min_stock, unit, supplier
      FROM products
      WHERE workspace_id = ? AND current_stock <= min_stock AND is_archived = 0
      ORDER BY current_stock ASC
    `).all(workspaceId) as any[];

    if (lowStock.length === 0) {
      return {
        answer: 'Good news! All products are currently above their configured minimum stock levels.',
        supportingData: { count: 0, products: [] }
      };
    }

    const itemsSummary = lowStock.map(p =>
      `• **${p.name}** (SKU: \`${p.sku}\`): **${p.current_stock} ${p.unit}** remaining (Minimum alert set at: ${p.min_stock} ${p.unit})${p.supplier ? ` | Supplier: ${p.supplier}` : ''}`
    ).join('\n');

    return {
      answer: `Found **${lowStock.length} product${lowStock.length > 1 ? 's' : ''}** at or below minimum stock threshold:\n\n${itemsSummary}\n\nYou can click **Stock In** on any of these products to replenish your inventory.`,
      supportingData: {
        recordsCount: lowStock.length,
        products: lowStock
      }
    };
  }

  // Question Type 2: Stock Out this week / recent stock out
  if ((q.includes('stock out') || q.includes('out') || q.includes('sold') || q.includes('issued')) && (q.includes('week') || q.includes('recent') || q.includes('today') || q.includes('month'))) {
    const days = q.includes('today') ? 0 : (q.includes('month') ? 30 : 7);
    const dateLimit = new Date();
    dateLimit.setDate(dateLimit.getDate() - days);
    const startDate = dateLimit.toISOString().slice(0, 10);

    const outMoves = db.prepare(`
      SELECT t.id, t.date, t.reason, t.partner_name, t.reference,
             ti.sku, ti.product_name, ti.unit, ti.quantity
      FROM transactions t
      JOIN transaction_items ti ON t.id = ti.transaction_id
      WHERE t.workspace_id = ? AND t.type = 'STOCK_OUT' AND t.date >= ?
      ORDER BY t.date DESC, t.created_at DESC
    `).all(workspaceId, startDate) as any[];

    const totalUnits = outMoves.reduce((acc, cur) => acc + cur.quantity, 0);

    if (outMoves.length === 0) {
      return {
        answer: `No stock out records found since ${startDate}.`,
        supportingData: { dateRange: `From ${startDate} to today`, totalUnits: 0, movements: [] }
      };
    }

    const summaryLines = outMoves.slice(0, 8).map(m =>
      `• **${m.date}** - **${m.quantity} ${m.unit}** of *${m.product_name}* (${m.reason}${m.partner_name ? ` to ${m.partner_name}` : ''})`
    ).join('\n');

    return {
      answer: `Total stock issued since **${startDate}**: **${totalUnits} units** across **${outMoves.length} line items**.\n\n${summaryLines}${outMoves.length > 8 ? `\n...and ${outMoves.length - 8} more movements.` : ''}`,
      supportingData: {
        dateRange: `From ${startDate} to today`,
        totalUnits,
        movements: outMoves
      }
    };
  }

  // Question Type 3: Total inventory value / valuation (Owner only check)
  if (q.includes('value') || q.includes('worth') || q.includes('total cost') || q.includes('valuation')) {
    if (role !== 'OWNER') {
      return {
        answer: 'Inventory valuation and unit costs are restricted to the Business Owner role.',
        supportingData: { restricted: true }
      };
    }

    const prods = db.prepare(`
      SELECT id, name, sku, current_stock, unit_cost, selling_price
      FROM products
      WHERE workspace_id = ? AND is_archived = 0
    `).all(workspaceId) as any[];

    let totalCostVal = 0;
    let totalRetailVal = 0;
    let missingCost = 0;

    prods.forEach(p => {
      if (p.unit_cost !== null && p.unit_cost !== undefined) {
        totalCostVal += p.current_stock * p.unit_cost;
      } else {
        missingCost++;
      }
      if (p.selling_price) {
        totalRetailVal += p.current_stock * p.selling_price;
      }
    });

    return {
      answer: `Estimated Total Inventory Value:\n\n• **Total Cost Basis**: **${currency}${totalCostVal.toFixed(2)}**\n• **Potential Retail Value**: **${currency}${totalRetailVal.toFixed(2)}**\n• **Active Products**: ${prods.length}\n${missingCost > 0 ? `> [!NOTE] ${missingCost} product(s) have no unit cost entered and were calculated as $0.00 cost.` : ''}`,
      supportingData: {
        totalCostBasis: totalCostVal,
        totalRetailValue: totalRetailVal,
        productsCount: prods.length,
        missingCostCount: missingCost
      }
    };
  }

  // Question Type 4: Product Specific Inquiry (e.g. "How many units of notebook do I have?" or "Why did pen quantity change?")
  const allProds = db.prepare('SELECT id, sku, name, unit, current_stock, min_stock FROM products WHERE workspace_id = ? AND is_archived = 0').all(workspaceId) as any[];
  let matchedProd: any = null;

  for (const p of allProds) {
    if (q.includes(p.name.toLowerCase()) || q.includes(p.sku.toLowerCase())) {
      matchedProd = p;
      break;
    }
  }

  // If not exact match, try matching single significant words
  if (!matchedProd) {
    for (const p of allProds) {
      const words = p.name.toLowerCase().split(' ').filter((w: string) => w.length > 3);
      if (words.some((w: string) => q.includes(w))) {
        matchedProd = p;
        break;
      }
    }
  }

  if (matchedProd) {
    // Fetch last 5 movements for this product
    const history = db.prepare(`
      SELECT t.date, t.type, t.reason, t.partner_name, t.created_by_name,
             ti.quantity, ti.balance_before, ti.balance_after
      FROM transaction_items ti
      JOIN transactions t ON ti.transaction_id = t.id
      WHERE t.workspace_id = ? AND ti.product_id = ?
      ORDER BY t.created_at DESC
      LIMIT 5
    `).all(workspaceId, matchedProd.id) as any[];

    const historyLines = history.map(h =>
      `• **${h.date}** [${h.type}]: ${h.type === 'STOCK_IN' ? '+' : '-'}${h.quantity} ${matchedProd.unit} (${h.reason}${h.partner_name ? ` - ${h.partner_name}` : ''}) → Balance changed from ${h.balance_before} to **${h.balance_after}** by *${h.created_by_name}*`
    ).join('\n');

    return {
      answer: `Current balance for **${matchedProd.name}** (SKU: \`${matchedProd.sku}\`):\n\n**${matchedProd.current_stock} ${matchedProd.unit}** (Minimum reorder point: ${matchedProd.min_stock} ${matchedProd.unit}).\n\n**Recent movement history:**\n${historyLines || 'No transaction records found yet.'}`,
      supportingData: {
        product: matchedProd,
        history
      }
    };
  }

  // Default General Summary
  const summary = db.prepare(`
    SELECT COUNT(*) as total_prods, SUM(current_stock) as total_units
    FROM products WHERE workspace_id = ? AND is_archived = 0
  `).get(workspaceId) as any;

  return {
    answer: `Here is a quick overview for **${ws?.name || 'your business'}**:\n\n• **Total Products**: ${summary.total_prods}\n• **Total Units in Stock**: ${summary.total_units || 0}\n\nYou can ask specific questions like:\n- *"Which products are low in stock?"*\n- *"What stock went out this week?"*\n- *"How many units of [product name] do I have?"*\n- *"Received 20 pieces of notebooks from ABC"* (to auto-create a draft!)`,
    supportingData: {
      totalProducts: summary.total_prods,
      totalUnits: summary.total_units
    }
  };
}

// 2. Natural Language Transaction Draft Parser
// Converts instructions like: "Received 20 pieces of blue notebooks from ABC Supplies"
// or "Sold 5 boxes of black gel pens to City Academy" into structured, editable drafts.
export function parseTransactionIntent(workspaceId: string, text: string): ParsedDraft {
  const t = text.trim();
  const lower = t.toLowerCase();

  // Detect Type
  const isStockIn =
    lower.includes('receive') ||
    lower.includes('received') ||
    lower.includes('bought') ||
    lower.includes('purchase') ||
    lower.includes('incoming') ||
    lower.includes('inward') ||
    lower.includes('got') ||
    lower.includes('return from customer') ||
    lower.includes('stock in');

  const type: 'STOCK_IN' | 'STOCK_OUT' = isStockIn ? 'STOCK_IN' : 'STOCK_OUT';

  // Detect Quantity
  const qtyMatch = t.match(/(\d+(\.\d+)?)/);
  const quantity = qtyMatch ? parseFloat(qtyMatch[1]) : 1;

  // Detect Partner (Supplier or Customer)
  let partnerName = '';
  const fromMatch = t.match(/(?:from|by|vendor|supplier)\s+([A-Za-z0-9\s&.,'-]+?)(?:\s+(?:on|for|ref|notes|\.|$))/i);
  const toMatch = t.match(/(?:to|for|customer)\s+([A-Za-z0-9\s&.,'-]+?)(?:\s+(?:on|for|ref|notes|\.|$))/i);

  if (isStockIn && fromMatch) {
    partnerName = fromMatch[1].trim();
  } else if (!isStockIn && toMatch) {
    partnerName = toMatch[1].trim();
  }

  // Detect Reason
  let reason = isStockIn ? 'Purchase received' : 'Sale';
  if (lower.includes('customer return')) reason = 'Customer return';
  else if (lower.includes('internal use') || lower.includes('office use')) reason = 'Internal use';
  else if (lower.includes('damage') || lower.includes('lost') || lower.includes('broken')) reason = 'Damaged or lost';
  else if (lower.includes('supplier return')) reason = 'Supplier return';

  // Match Product
  const allProds = db.prepare('SELECT id, sku, name, unit, current_stock FROM products WHERE workspace_id = ? AND is_archived = 0').all(workspaceId) as any[];

  let candidateProducts: any[] = [];
  let bestMatch: any = null;

  for (const p of allProds) {
    const prodName = p.name.toLowerCase();
    const sku = p.sku.toLowerCase();

    if (lower.includes(sku)) {
      bestMatch = p;
      break;
    }

    if (lower.includes(prodName)) {
      candidateProducts.push(p);
      continue;
    }

    // Keyword match
    const keywords = prodName.split(' ').filter(k => k.length > 2);
    const matchedKeywords = keywords.filter(k => lower.includes(k));
    if (matchedKeywords.length >= 2 || (keywords.length === 1 && matchedKeywords.length === 1)) {
      candidateProducts.push(p);
    }
  }

  if (!bestMatch && candidateProducts.length === 1) {
    bestMatch = candidateProducts[0];
  }

  const isAmbiguous = !bestMatch && candidateProducts.length > 1;

  const targetProd = bestMatch || candidateProducts[0] || (allProds.length > 0 ? allProds[0] : null);

  const expectedBalance = targetProd
    ? (type === 'STOCK_IN' ? targetProd.current_stock + quantity : Math.max(0, targetProd.current_stock - quantity))
    : 0;

  return {
    type,
    reason,
    partner_name: partnerName,
    items: targetProd ? [
      {
        product_id: targetProd.id,
        sku: targetProd.sku,
        product_name: targetProd.name,
        unit: targetProd.unit,
        quantity,
        current_stock: targetProd.current_stock,
        expected_balance: expectedBalance,
        isAmbiguous,
        candidateProducts: isAmbiguous ? candidateProducts : undefined
      }
    ] : [],
    confidence: bestMatch ? 0.95 : (candidateProducts.length > 0 ? 0.75 : 0.4),
    rawText: text
  };
}
