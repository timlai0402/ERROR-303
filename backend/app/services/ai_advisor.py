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

        # Fallback Gemini settings
        self.gemini_api_key = getattr(settings, "GEMINI_API_KEY", "") or os.getenv("GEMINI_API_KEY", "")
        self.gemini_model = getattr(settings, "GEMINI_MODEL", "") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

        if self.is_kracked_configured():
            print(f"[AI Advisor] KrackedDevs API configured (URL: {self.kracked_base_url}, Model: {self.kracked_model})")
        elif self.gemini_api_key:
            print(f"[AI Advisor] Gemini API configured (Model: {self.gemini_model})")
        else:
            print("[AI Advisor] No active API key found. Using deterministic rule-based synthesis.")

    def is_kracked_configured(self) -> bool:
        return bool(self.kracked_api_key and self.kracked_api_key != "your_actual_key")

    async def _call_kracked(self, prompt: str) -> Optional[Dict[str, Any]]:
        url = f"{self.kracked_base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.kracked_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.kracked_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are the Chief Procurement AI for StockWise, an automated inventory control system for Malaysian SMEs. Respond strictly in valid JSON format without markdown code blocks."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.2
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
            content = data["choices"][0]["message"]["content"].strip()

            # Clean markdown code fences if wrapped
            if "```" in content:
                lines = [line for line in content.splitlines() if not line.strip().startswith("```")]
                content = "\n".join(lines).strip()

            parsed = json.loads(content)
            return {
                "action_recommendation": parsed.get("action_recommendation", "ORDER_ROUTINE"),
                "executive_rationale": parsed.get("executive_rationale", ""),
                "supply_risk_level": parsed.get("supply_risk_level", "LOW"),
                "supplier_negotiation_tip": parsed.get("supplier_negotiation_tip", "")
            }

    async def _call_gemini(self, prompt: str) -> Optional[Dict[str, Any]]:
        from google import genai
        client = genai.Client(api_key=self.gemini_api_key)
        response = client.models.generate_content(
            model=self.gemini_model,
            contents=prompt
        )
        text = response.text.strip()
        if "```" in text:
            lines = [line for line in text.splitlines() if not line.strip().startswith("```")]
            text = "\n".join(lines).strip()
        parsed = json.loads(text)
        return {
            "action_recommendation": parsed.get("action_recommendation", "ORDER_ROUTINE"),
            "executive_rationale": parsed.get("executive_rationale", ""),
            "supply_risk_level": parsed.get("supply_risk_level", "LOW"),
            "supplier_negotiation_tip": parsed.get("supplier_negotiation_tip", "")
        }

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

        # 1. Primary: KrackedDevs API
        if self.is_kracked_configured():
            try:
                res = await self._call_kracked(prompt)
                if res:
                    return res
            except Exception as e:
                print(f"[AI Advisor] KrackedDevs API call failed: {e}. Falling back...")

        # 2. Secondary: Gemini API
        if self.gemini_api_key:
            try:
                res = await self._call_gemini(prompt)
                if res:
                    return res
            except Exception as e:
                print(f"[AI Advisor] Gemini API call failed: {e}. Falling back to rule-based synthesis.")

        # 3. High-precision deterministic fallback
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
