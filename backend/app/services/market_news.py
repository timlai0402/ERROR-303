import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

class MarketNewsService:
    NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"

    # Default fallback signals for demo, rate-limits & offline mode
    DEFAULT_SIGNALS = [
        {
            "title": "Port congestion increases container dwell times across ASEAN logistics hubs",
            "source": "Logistics Asia Brief",
            "url": "https://newsapi.org",
            "publishedAt": "2026-10-30T04:15:00Z",
            "category": "Logistics & Freight",
            "sentiment": -0.62,
            "supply_risk": "High",
            "impact_summary": "Expect 3-5 days added to overseas sea freight; increase buffer lead times by 20%."
        },
        {
            "title": "Industrial paper and pulp spot prices stabilize after regional mill re-openings",
            "source": "Commodity Wire",
            "url": "https://newsapi.org",
            "publishedAt": "2026-10-28T11:00:00Z",
            "category": "Packaging",
            "sentiment": 0.45,
            "supply_risk": "Low",
            "impact_summary": "Packaging carton cost inflation softening; ideal window to lock forward quarter pricing."
        },
        {
            "title": "Semiconductor and electrical wiring components face tightened supply allocations",
            "source": "Tech Procurement Quarterly",
            "url": "https://newsapi.org",
            "publishedAt": "2026-10-25T08:30:00Z",
            "category": "Electrical & Hardware",
            "sentiment": -0.40,
            "supply_risk": "Medium",
            "impact_summary": "Lead times stretching for micro-fasteners and cable assemblies."
        }
    ]

    def __init__(self):
        self.api_key = getattr(settings, "NEWS_API_KEY", "")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.api_key != "your-newsapi-org-key")

    async def fetch_supply_chain_news(
        self,
        query: str = "supply chain raw materials freight",
        page_size: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Fetches live news headlines from NewsAPI, analyzes sentiment and supply risk.
        """
        if not self.is_configured():
            return self.DEFAULT_SIGNALS

        params = {
            "q": query or "supply chain logistics prices",
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": min(page_size, 15),
            "apiKey": self.api_key
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(self.NEWS_API_BASE_URL, params=params)
                if res.status_code == 200:
                    data = res.json()
                    articles = data.get("articles", [])
                    if not articles:
                        return self.DEFAULT_SIGNALS

                    signals: List[Dict[str, Any]] = []
                    for art in articles:
                        title = (art.get("title") or "").strip()
                        desc = (art.get("description") or "").strip()
                        if not title or "[Removed]" in title:
                            continue

                        text = f"{title} {desc}".lower()

                        # Sentiment & risk heuristics
                        neg_keywords = [
                            "shortage", "delay", "strike", "inflation", "tariff", 
                            "disruption", "surge", "spike", "crisis", "embargo", 
                            "halt", "bottleneck", "port congestion", "soar", "risk"
                        ]
                        pos_keywords = [
                            "drop", "surplus", "stable", "recovery", "ease", 
                            "discount", "smooth", "rebound", "improve", "record output"
                        ]

                        neg_count = sum(1 for kw in neg_keywords if kw in text)
                        pos_count = sum(1 for kw in pos_keywords if kw in text)

                        sentiment = round((pos_count - neg_count) / max(1, pos_count + neg_count), 2)
                        if sentiment < -0.2 or neg_count >= 2:
                            risk = "High"
                            impact = "Significant risk of supplier delays or price increases. Review safety stock."
                        elif sentiment < 0.1:
                            risk = "Medium"
                            impact = "Moderate supply pressure detected. Monitor order confirmations."
                        else:
                            risk = "Low"
                            impact = "Stable procurement environment. Normal reorder rules apply."

                        signals.append({
                            "title": title,
                            "source": art.get("source", {}).get("name", "News"),
                            "url": art.get("url") or "https://newsapi.org",
                            "publishedAt": art.get("publishedAt") or datetime.utcnow().isoformat(),
                            "category": "Supply Market",
                            "sentiment": sentiment,
                            "supply_risk": risk,
                            "impact_summary": impact
                        })

                    return signals if signals else self.DEFAULT_SIGNALS
                else:
                    print(f"[MarketNews] NewsAPI HTTP {res.status_code}: {res.text[:120]}")
        except Exception as e:
            print(f"[MarketNews] Failed to reach NewsAPI: {e}. Serving cached market signals.")

        return self.DEFAULT_SIGNALS

market_news = MarketNewsService()
