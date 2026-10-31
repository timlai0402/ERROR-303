import httpx
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.config import settings

class MarketNewsService:
    NEWS_API_BASE_URL = "https://newsapi.org/v2/everything"

    # Default fallback signals for demo & offline mode
    DEFAULT_SIGNALS = [
        {
            "title": "Port congestion increases container dwell times across ASEAN logistics hubs",
            "source": "Logistics Asia Brief",
            "url": "https://example.com/logistics-congestion",
            "publishedAt": "2026-10-30T04:15:00Z",
            "category": "Logistics & Freight",
            "sentiment": -0.62,
            "supply_risk": "High",
            "impact_summary": "Expect 3-5 days added to overseas sea freight; increase buffer lead times by 20%."
        },
        {
            "title": "Industrial paper and pulp spot prices stabilize after regional mill re-openings",
            "source": "Commodity Wire",
            "url": "https://example.com/packaging-pulp",
            "publishedAt": "2026-10-28T11:00:00Z",
            "category": "Packaging",
            "sentiment": 0.45,
            "supply_risk": "Low",
            "impact_summary": "Packaging carton cost inflation softening; ideal window to lock forward quarter pricing."
        },
        {
            "title": "Semiconductor and electrical wiring components face tightened supply allocations",
            "source": "Tech Procurement Quarterly",
            "url": "https://example.com/component-shortage",
            "publishedAt": "2026-10-25T08:30:00Z",
            "category": "Electrical & Hardware",
            "sentiment": -0.40,
            "supply_risk": "Medium",
            "impact_summary": "Lead times stretching for micro-fasteners and cable assemblies."
        }
    ]

    def __init__(self):
        self.api_key = settings.NEWS_API_KEY

    async def fetch_supply_chain_news(self, query: str = "supply chain raw materials price", page_size: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches live news headlines from NewsAPI, evaluates sentiment and potential supply risk.
        """
        if not self.api_key:
            return self.DEFAULT_SIGNALS

        params = {
            "q": query,
            "language": "en",
            "sortBy": "publishedAt",
            "pageSize": page_size,
            "apiKey": self.api_key
        }

        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                res = await client.get(self.NEWS_API_BASE_URL, params=params)
                if res.status_code == 200:
                    data = res.json()
                    articles = data.get("articles", [])
                    signals = []
                    for art in articles:
                        title = art.get("title", "")
                        desc = art.get("description", "")
                        text = f"{title} {desc}".lower()

                        # Lightweight sentiment & risk heuristics
                        neg_keywords = ["shortage", "delay", "strike", "inflation", "tariff", "disruption", "surge", "spike"]
                        pos_keywords = ["drop", "surplus", "stable", "recovery", "ease", "discount", "smooth"]

                        neg_count = sum(1 for kw in neg_keywords if kw in text)
                        pos_count = sum(1 for kw in pos_keywords if kw in text)

                        sentiment = (pos_count - neg_count) / max(1, pos_count + neg_count)
                        if sentiment < -0.2:
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
                            "url": art.get("url"),
                            "publishedAt": art.get("publishedAt"),
                            "category": "Supply Market",
                            "sentiment": round(sentiment, 2),
                            "supply_risk": risk,
                            "impact_summary": impact
                        })
                    return signals if signals else self.DEFAULT_SIGNALS
        except Exception as e:
            print(f"[MarketNews] Failed to reach NewsAPI: {e}. Serving cached market signals.")

        return self.DEFAULT_SIGNALS

market_news = MarketNewsService()

