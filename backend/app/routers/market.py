from fastapi import APIRouter, Query, HTTPException
from typing import List, Dict, Any, Optional
from app.services.market_news import market_news
from app.services.ai_advisor import ai_advisor
from app.db.supabase_client import db

router = APIRouter(prefix="/market", tags=["Market Intelligence & External Signals"])

@router.get("/signals")
async def get_market_signals(query: str = Query("supply chain commodity price", description="Search query")):
    """
    Fetches real-time market intelligence headlines from NewsAPI, parsed with sentiment and supply risk ratings.
    """
    signals = await market_news.fetch_supply_chain_news(query=query)
    high_risk_count = sum(1 for s in signals if s.get("supply_risk") == "High")
    avg_sentiment = round(sum(s.get("sentiment", 0) for s in signals) / max(1, len(signals)), 2)

    return {
        "status": "online" if market_news.is_configured() else "simulated_preview",
        "total_signals": len(signals),
        "high_risk_count": high_risk_count,
        "average_sentiment": avg_sentiment,
        "signals": signals
    }

@router.get("/assess-item/{item_id}")
async def assess_item_market_risk(item_id: str):
    """
    Combines item inventory state, supplier lead times, and live NewsAPI headlines
    to produce a KrackedDevs LLM risk evaluation.
    """
    item = db.get_item(item_id)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")

    category = item.get("category", "General")
    signals = await market_news.fetch_supply_chain_news(f"{category} supply chain price", page_size=4)
    headlines = [s["title"] for s in signals]

    # KrackedDevs market disruption analysis
    ai_market_eval = await ai_advisor.assess_market_disruption(item=item, news_articles=signals)

    # KrackedDevs restocking rationale
    rec_qty = float(item.get("minOrder", 10))
    restock_eval = await ai_advisor.explain_restocking_decision(
        item=item,
        rec_quantity=rec_qty,
        market_signals=headlines
    )

    return {
        "item_id": item.get("id") or item.get("sku"),
        "item_name": item.get("name"),
        "category": category,
        "supplier": item.get("supplier"),
        "signals_considered": headlines,
        "market_news_count": len(signals),
        "ai_risk_assessment": ai_market_eval,
        "restock_decision": restock_eval
    }

@router.get("/overview")
async def get_market_overview():
    """
    Comprehensive executive market briefing fusing NewsAPI macro feeds with KrackedDevs AI analysis.
    """
    signals = await market_news.fetch_supply_chain_news(query="manufacturing supply chain ASEAN shipping", page_size=6)
    items = db.get_items()

    high_risk_items = []
    for item in items[:5]:
        avail = float(item.get("physical", 0)) - float(item.get("reserved", 0))
        rop = float(item.get("reorder", 0))
        if avail <= rop:
            high_risk_items.append(item.get("name"))

    return {
        "status": "operational",
        "news_source": "NewsAPI.org (Live)" if market_news.is_configured() else "Cached Fallback",
        "ai_engine": f"KrackedDevs ({ai_advisor.kracked_model})" if ai_advisor.is_kracked_configured() else "Rule Synthesis",
        "items_tracked": len(items),
        "items_needing_attention": len(high_risk_items),
        "signals": signals
    }
