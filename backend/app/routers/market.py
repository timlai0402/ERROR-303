from fastapi import APIRouter, Query
from typing import List, Dict, Any, Optional
from app.services.market_news import market_news
from app.services.ai_advisor import ai_advisor
from app.db.supabase_client import db

router = APIRouter(prefix="/market", tags=["Market Intelligence & External Signals"])

@router.get("/signals")
async def get_market_signals(query: str = Query("supply chain commodity price", description="Search query")):
    signals = await market_news.fetch_supply_chain_news(query=query)
    return {
        "status": "online" if market_news.api_key else "simulated_preview",
        "total_signals": len(signals),
        "signals": signals
    }

@router.get("/assess-item/{item_id}")
async def assess_item_market_risk(item_id: str):
    item = db.get_item(item_id)
    if not item:
        return {"error": "Item not found"}

    signals = await market_news.fetch_supply_chain_news(f"{item.get('category')} supply disruption", page_size=3)
    headlines = [s["title"] for s in signals]

    ai_result = await ai_advisor.explain_restocking_decision(
        item=item,
        rec_quantity=float(item.get("minOrder", 10)),
        market_signals=headlines
    )

    return {
        "item": item["name"],
        "signals_considered": headlines,
        "ai_risk_assessment": ai_result
    }

