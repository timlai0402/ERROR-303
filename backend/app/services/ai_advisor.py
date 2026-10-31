import os
import json
import httpx
from typing import Dict, Any, List, Optional
from app.config import settings

class AIAdvisorService:
    def __init__(self):
        # KrackedDevs settings (LiteLLM proxy / OpenAI-compatible endpoint)
        self.kracked_api_key = getattr(settings, "KRACKED_API_KEY", "") or os.getenv("KRACKED_API_KEY", "")
        self.kracked_base_url = (getattr(settings, "KRACKED_BASE_URL", "") or os.getenv("KRACKED_BASE_URL", "https://litellm.rapidscreen.io/v1")).rstrip("/")
        self.kracked_model = getattr(settings, "KRACKED_MODEL", "") or os.getenv("KRACKED_MODEL", "gpt-5.5")

        if self.is_kracked_configured():
            print(f"[AI Advisor] KrackedDevs API connected (Base: {self.kracked_base_url}, Model: {self.kracked_model})")
        else:
            print("[AI Advisor] KrackedDevs API key not configured. Operating with deterministic rule synthesis.")

    def is_kracked_configured(self) -> bool:
        return bool(self.kracked_api_key and self.kracked_api_key != "your_actual_key")

    async def _call_kracked(self, prompt: str, system_prompt: Optional[str] = None) -> Optional[Dict[str, Any]]:
        url = f"{self.kracked_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.kracked_api_key}",
            "Content-Type": "application/json"
        }
        
        sys_msg = system_prompt or (
            "You are the Chief Procurement AI for StockWise, an automated inventory control system for Malaysian SMEs. "
            "Analyze inventory, lead times, and live supply chain news signals. "
            "You must respond strictly with valid JSON without conversational filler or markdown code blocks."
        )

        payload = {
            "model": self.kracked_model,
            "messages": [
                {"role": "system", "content": sys_msg},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=25.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown code fences if wrapped
            if "```" in content:
                lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
                content = "\n".join(lines).strip()

            parsed = json.loads(content)
            return parsed

    async def explain_restocking_decision(
        self,
        item: Dict[str, Any],
        rec_quantity: float,
        deficit: float = 0.0,
        market_signals: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Interprets inventory deficit, supplier lead time, and live NewsAPI market context
        via KrackedDevs LLM to generate actionable justification for human manager approval.
        """
        item_id = item.get("id") or item.get("sku", "N/A")
        item_name = item.get("name", "Unknown Item")
        available = float(item.get("physical", 0)) - float(item.get("reserved", 0))
        rop = float(item.get("reorder", 0))
        safety = float(item.get("safety", 0))
        lead_days = int(item.get("lead", 3))
        unit_cost = float(item.get("cost", 0))
        supplier = item.get("supplier", "Primary Vendor")

        signals_text = "; ".join(market_signals) if market_signals else "No immediate supply disruptions reported."

        prompt = f"""
Analyze the following restocking request and return a JSON object with your assessment.

Item: {item_name} ({item_id})
Current Available Stock: {available} {item.get('unit', 'units')}
Reorder Point (ROP): {rop}
Safety Stock Threshold: {safety}
Supplier: {supplier} (Lead Time: {lead_days} days)
Unit Cost: MYR {unit_cost}
Calculated Recommended Restock Qty: {rec_quantity}
Active Deficit from confirmed orders: {deficit}
Live NewsAPI Market Signals: {signals_text}

Respond strictly with valid JSON with keys:
- "action_recommendation": one of "ORDER_IMMEDIATELY", "ORDER_ROUTINE", "HOLD_REVIEW"
- "executive_rationale": 2-3 concise sentences justifying the decision to the business owner
- "supply_risk_level": "LOW", "MEDIUM", or "HIGH"
- "supplier_negotiation_tip": 1 actionable tip (e.g. bulk tier or lead time buffer)
"""

        # 1. Primary: KrackedDevs API
        if self.is_kracked_configured():
            try:
                res = await self._call_kracked(prompt)
                if res and "executive_rationale" in res:
                    return {
                        "action_recommendation": res.get("action_recommendation", "ORDER_ROUTINE"),
                        "executive_rationale": res.get("executive_rationale", ""),
                        "supply_risk_level": res.get("supply_risk_level", "LOW").upper(),
                        "supplier_negotiation_tip": res.get("supplier_negotiation_tip", "")
                    }
            except Exception as e:
                print(f"[AI Advisor] KrackedDevs API call failed: {e}. Falling back to deterministic rule synthesis.")

        # 2. High-precision deterministic fallback
        if available <= 0 or deficit > 0:
            rec = "ORDER_IMMEDIATELY"
            risk = "HIGH"
            rationale = (
                f"Available stock is in deficit ({available} {item.get('unit', 'units')}) against active commitments. "
                f"With a {lead_days}-day lead time from {supplier}, an immediate purchase of {rec_quantity} units "
                f"is necessary to prevent production stoppage."
            )
        elif available <= safety:
            rec = "ORDER_IMMEDIATELY"
            risk = "MEDIUM"
            rationale = (
                f"Available reserves have breached the safety stock threshold ({safety} {item.get('unit', 'units')}). "
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

    async def assess_market_disruption(
        self,
        item: Dict[str, Any],
        news_articles: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Synthesizes live NewsAPI supply chain headlines into an actionable KrackedDevs risk assessment for an item.
        """
        item_name = item.get("name", "Unknown Item")
        category = item.get("category", "General")
        supplier = item.get("supplier", "Vendor")

        headlines = [f"- {a.get('title', '')} ({a.get('source', 'News')})" for a in news_articles[:5]]
        news_block = "\n".join(headlines) if headlines else "No recent supply disruption news."

        prompt = f"""
Evaluate the market supply risk for item '{item_name}' (Category: {category}, Supplier: {supplier}) given these recent news headlines:

{news_block}

Return a valid JSON object with:
- "risk_level": "LOW", "MEDIUM", or "HIGH"
- "risk_score": float between 0.0 (safest) and 1.0 (severe disruption)
- "impact_analysis": 2 sentences explaining how external news affects procurement/pricing for this item
- "proactive_action": 1 recommended action for procurement managers (e.g. advance purchase, dual-sourcing)
"""
        if self.is_kracked_configured():
            try:
                res = await self._call_kracked(prompt)
                if res and "impact_analysis" in res:
                    return {
                        "risk_level": res.get("risk_level", "MEDIUM").upper(),
                        "risk_score": float(res.get("risk_score", 0.5)),
                        "impact_analysis": res.get("impact_analysis", ""),
                        "proactive_action": res.get("proactive_action", "Maintain regular replenishment cycle.")
                    }
            except Exception as e:
                print(f"[AI Advisor] KrackedDevs market evaluation failed: {e}. Falling back to default risk analysis.")

        # Deterministic fallback
        return {
            "risk_level": "MEDIUM",
            "risk_score": 0.45,
            "impact_analysis": f"Potential macroeconomic or logistics friction may impact {category} lead times. Monitor supplier confirmations.",
            "proactive_action": f"Verify quotation stability with {supplier} before placing bulk replenishment."
        }

ai_advisor = AIAdvisorService()
