import json
from typing import Dict, Any, List, Optional
from app.config import settings

class AIAdvisorService:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.client = None

        if self.api_key:
            try:
                # Prefer google.genai if available, fallback to google.generativeai
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                print(f"[AI Advisor] Google GenAI client initialized with model: {self.model_name}")
            except Exception as e:
                print(f"[AI Advisor] Could not initialize google.genai ({e}). Checking alternative...")

    async def explain_restocking_decision(
        self,
        item: Dict[str, Any],
        rec_quantity: float,
        deficit: float = 0.0,
        market_signals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Interprets inventory deficit, supplier lead time, and market context
        to generate actionable plain-language justification for human manager approval.
        """
        item_id = item.get("id", "N/A")
        item_name = item.get("name", "Unknown Item")
        available = float(item.get("physical", 0)) - float(item.get("reserved", 0))
        rop = float(item.get("reorder", 0))
        safety = float(item.get("safety", 0))
        lead_days = int(item.get("lead", 3))
        unit_cost = float(item.get("cost", 0))
        supplier = item.get("supplier", "Primary Vendor")

        signals_text = "; ".join(market_signals) if market_signals else "No immediate supply disruptions reported."

        prompt = f"""
You are the Chief Procurement AI for StockWise, an automated inventory control system for Malaysian SMEs.
Analyze the following restocking request and return a JSON object with your assessment.

Item: {item_name} ({item_id})
Current Available Stock: {available} {item.get('unit', 'units')}
Reorder Point (ROP): {rop}
Safety Stock Threshold: {safety}
Supplier: {supplier} (Lead Time: {lead_days} days)
Unit Cost: MYR {unit_cost}
Calculated Recommended Restock Qty: {rec_quantity}
Active Deficit from confirmed orders: {deficit}
Market Intelligence Signals: {signals_text}

Respond strictly with valid JSON with keys:
- "action_recommendation": one of "ORDER_IMMEDIATELY", "ORDER_ROUTINE", "HOLD_REVIEW"
- "executive_rationale": 2-3 concise sentences justifying the decision to the business owner
- "supply_risk_level": "LOW", "MEDIUM", or "HIGH"
- "supplier_negotiation_tip": 1 actionable tip (e.g. bulk tier or lead time buffer)
"""

        # If live Gemini client is available, run prompt
        if self.client:
            try:
                response = self.client.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                text = response.text.strip()
                # Clean markdown blocks if returned
                if text.startswith("```json"):
                    text = text.replace("```json", "").replace("```", "").strip()
                parsed = json.loads(text)
                return {
                    "action_recommendation": parsed.get("action_recommendation", "ORDER_ROUTINE"),
                    "executive_rationale": parsed.get("executive_rationale", ""),
                    "supply_risk_level": parsed.get("supply_risk_level", "LOW"),
                    "supplier_negotiation_tip": parsed.get("supplier_negotiation_tip", "")
                }
            except Exception as e:
                print(f"[AI Advisor] Gemini API call failed: {e}. Falling back to rule-based synthesis.")

        # High-precision deterministic fallback if Gemini key is not yet configured
        if available <= 0 or deficit > 0:
            rec = "ORDER_IMMEDIATELY"
            risk = "HIGH"
            rationale = (
                f"Available stock is in deficit ({available} {item.get('unit')}) against active commitments. "
                f"With a {lead_days}-day lead time from {supplier}, an immediate purchase of {rec_quantity} units "
                f"is necessary to prevent production stoppage."
            )
        elif available <= safety:
            rec = "ORDER_IMMEDIATELY"
            risk = "MEDIUM"
            rationale = (
                f"Available reserves have breached the safety stock threshold ({safety} {item.get('unit')}). "
                f"Ordering {rec_quantity} units now buffers against delivery variability from {supplier}."
            )
        else:
            rec = "ORDER_ROUTINE"
            risk = "LOW"
            rationale = (
                f"Inventory is approaching reorder point ({rop}). Economic Order Quantity suggests {rec_quantity} units "
                f"to optimize total carrying vs. transaction cost."
            )

        negotiation = f"Request priority dispatch given the {lead_days}-day lead time agreement with {supplier}."

        return {
            "action_recommendation": rec,
            "executive_rationale": rationale,
            "supply_risk_level": risk,
            "supplier_negotiation_tip": negotiation
        }

ai_advisor = AIAdvisorService()

