---

# StockWise

> A simple, reliable inventory tracker for independent small hardware shops and auto-mechanics. Turn manual spreadsheets and paper logs into a dependable stock tracking and restocking workflow.

---

## Team Information

| Field                  | Details                                         |
| ---------------------- | -------------------------------------------     |
| **Team Name**          | ERROR 303                                       |
| **Team Domain**        | Domain 2                                        |
| **SDG Track (1–17)**   | SDG 9 — Industry, Innovation and Infrastructure |
| **Team Leader**        | Timothy Lai Yong Fong                           |
| **University**         | Taylor's University                             |
| **Number of Members**  | 3                                               |

## Links

| Resource          | Link                                           |
| ----------------- | ---------------------------------------------- |
| GitHub Repository | https://github.com/timlai0402/ERROR-303.git    |
| Live Demo         | https://stock-wise.replit.app                  |
| Slide Deck        | [SDC2026_ERROR 303_Slide_Desk.pdf](<submission/SDC2026_ERROR 303_Slide_Desk.pdf>) |
| Demo Video        | [https://youtu.be/QjNjUeEtulU](https://youtu.be/QjNjUeEtulU) |
| Pitch Video       | [https://youtu.be/PdYZQNNhst0](https://youtu.be/PdYZQNNhst0) |

---

## Overview

### Problem

Independent hardware stores and auto-mechanic workshops that currently use paper logs or spreadsheets struggle to answer three basic daily questions:
1. **What stock do I have?**
2. **What stock came in or went out?**
3. **What needs restocking?**

**Specific Real SME Pain Point:** In auto-mechanic and small hardware workshops, fast-moving non-expiry maintenance items (such as oil filters, brake cleaners, hex flange bolts, and ball bearings) frequently run out unnoticed midway through a customer repair job. Spreadsheet recount errors, delayed tallying, and unrecorded counter sales cause sudden stockouts, stalled vehicle repairs, lost customer goodwill, and frantic last-minute retail purchasing at inflated prices.

### Solution

**StockWise Hardware Edition** is a focused, dependable inventory tracker designed specifically for independent hardware shops and mechanics dealing with non-expiry inventory. The core promise is:
> *“Know what you have, record stock changes, and see what needs restocking.”*

It automates the complete operational workflow from trigger to visible outcome:
**Trigger &rarr; Connected Data &rarr; Decision Logic &rarr; Human Approval &rarr; Visible Outcome &rarr; Scale**.

### 6-Step Operational Journey (Live Demo)

1. **Trigger:** A counter sale or repair service consumes stock of a fast-moving item (e.g., Oil Filter `FLT-02`), dropping current physical stock below minimum threshold.
2. **Connected Data:** The system instantly connects the SKU, current physical balance, fixed unit (`pcs`), minimum threshold (`20 pcs`), and supplier contact (*Huat Kee Auto Spares, +6012-8889999*).
3. **Decision Logic:** Deterministic rule flags the product as `LOW STOCK` and computes the exact replenishment deficit (`12 pcs`) without AI hallucinations.
4. **Human Approval:** Shop manager reviews delivery note `DO-4481` and authorizes the replenishment quantity.
5. **Visible Outcome:** Atomic stock movement (+12 pcs) updates physical inventory to 20, writes to the immutable ledger, and clears the alert.
6. **Scale:** The shop scales catalog to 1,000+ hardware items with column-matched CSV validation and tenant isolation.

### Core Features

1. **Product List:**
   - Searchable, paginated catalog with SKU uniqueness per business.
   - Preserves leading zeros in SKUs (e.g., `00142`).
   - Fixed stock units (`pcs`, `box`, `set`, `kg`, `meter`, `roll`, `pack`, `pair`, `can`, `bottle`).
   - Disallows unit changes once stock movements exist to prevent ledger corruption.
   - Product archiving support.

2. **Stock Movements (Immutable Audit Ledger):**
   - Atomic recording of `OPENING_STOCK`, `STOCK_IN`, `STOCK_OUT`, and `CORRECTION`.
   - Concurrency-safe row locking (`FOR UPDATE` / thread locks).
   - Rejects movements that would produce negative stock.
   - Idempotency key protection prevents duplicate submissions on double-clicks.

3. **Low-Stock List:**
   - Real-time detection of products where `current_stock < min_stock`.
   - Minimum stock of 0 disables alerts.
   - Highlights critical zero-stock (`OUT_OF_STOCK`) items.
   - 1-click **Stock In** replenishment directly from the low-stock row.

4. **Deterministic CSV Import & Export (Zero AI):**
   - 6-step import wizard: Template download &rarr; Column matching &rarr; Strict validation &rarr; Row-by-row error preview &rarr; Confirmation &rarr; Batch summary.
   - Validates required fields, nonnegative numbers, supported units, file duplicates, and catalog collision.
   - Safe import batch reversal: Allowed only when products have no subsequent stock activity.
   - Direct CSV export with leading-zero preservation.

### Architecture

```
                  HARDWARE SHOP OPERATIONAL JOURNEY
 ┌──────────────────────┐         ┌────────────────────────────────────────────────────────┐
 │ 1. Trigger           │ ──────► │ 2. Connected Data Ingestion                            │
 │ (Counter Sale / Job) │         │    (SKU ◄─► Current Balance ◄─► Threshold ◄─► Supplier)│
 └──────────────────────┘         └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                     ┌─────────────────────────────────────────┐
                                     │ 3. Deterministic Decision Logic         │
                                     │    • Current < Min Threshold Check      │
                                     │    • Exact Deficit Replenishment Qty    │
                                     └────────────────────┬────────────────────┘
                                                          │
                                                          ▼
 ┌───────────────────────────┐       ┌─────────────────────────────────────────┐
 │ 5. Visible Outcome        │ ◄──── │ 4. Human Approval Gate                  │
 │ • Atomic Stock Update     │       │    (Manager verifies Delivery Order &   │
 │ • Immutable Movement Log  │       │     approves Stock In replenishment)    │
 └─────────────┬─────────────┘       └─────────────────────────────────────────┘
               │
               ▼
 ┌─────────────────────────────────────────────────────────────────────────────┐
 │ 6. Scale: Bulk CSV Import with Safe Reversal & Multi-Tenant Business RLS   │
 └─────────────────────────────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer            | Technology                                              |
| ---------------- | ------------------------------------------------------- |
| **Frontend**     | Responsive Vanilla Web Application (Clean, Fast, Zero Build Step) |
| **Backend API**  | FastAPI (Python 3.11), Pydantic v2                      |
| **Database**     | Supabase PostgreSQL with Row-Level Security (RLS) & RPC |
| **Dev / Server** | `serve` (port 3000) & Uvicorn (port 8000)               |

---

## How to Run

### Option 1 — Run Web Frontend
```bash
npm run dev
# Serves the frontend at http://localhost:3000
```

### Option 2 — Run Backend API
```bash
npm run backend
# Starts FastAPI server at http://localhost:8000
# Interactive API Documentation: http://localhost:8000/docs
```

### Option 3 — Run Automated Tests
```bash
backend/.venv/Scripts/pytest backend/tests
# Runs 23 automated tests covering:
# - Product CRUD & SKU uniqueness
# - Atomic movements & negative stock prevention
# - Idempotent double-click protection
# - Low-stock alerts & zero-stock labeling
# - Non-AI CSV validation, import & safe batch reversal
# - CSV inventory export & business isolation
```

---

## Team

| Name                  | Role                           | GitHub                                       |
| --------------------- | ------------------------------ | -------------------------------------------- |
| Timothy Lai Yong Fong | Team Leader / Idea pitching    | [@timlai0402](https://github.com/timlai0402) |
| Zayn Koh Hao Xiang    | Frontend & UI/UX Design        | [@zayn0214](https://github.com/zayn0214)     |
| Chong Zhen Xi         | Documentation & Making slides  | [@Ben-newbie](https://github.com/Ben-newbie) |

---

## License

This project is licensed under the [Apache License 2.0](LICENSE).
