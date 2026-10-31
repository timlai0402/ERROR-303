from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import inventory, procurement, forecasting, market, workspace, hardware
from app.services.ai_advisor import ai_advisor
from app.services.market_news import market_news
from app.db.supabase_client import db

app = FastAPI(
    title="StockWise — Small Hardware Shop Inventory Tracker",
    description="Simple, reliable inventory tracker for independent hardware shops and mechanics answering: What stock do I have? What came in or went out? What needs restocking?",
    version="3.0.0"
)

# CORS configuration for Frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register Hardware Shop core inventory routers
app.include_router(hardware.router, prefix="/api")

# Register legacy routers safely for backward compatibility
app.include_router(inventory.router, prefix="/api")
app.include_router(procurement.router, prefix="/api")
app.include_router(forecasting.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(workspace.router, prefix="/api")

@app.get("/")
def root():
    return {
        "product": "StockWise AI",
        "sub_product": "StockWise Hardware Inventory Tracker",
        "team": "ERROR 303",
        "status": "operational",
        "docs_url": "/docs",
        "purpose": "Know what you have, record stock changes, and see what needs restocking.",
        "core_features": [
            "1. Product list with SKU uniqueness, fixed units, searching, pagination, and archiving",
            "2. Atomic stock movements (Stock In, Stock Out, Stock Correction) with negative stock rejection",
            "3. Deterministic low-stock alerts and zero-stock indicators",
            "4. Non-AI CSV import with full column matching, strict validation, and safe reversal",
            "5. Direct CSV product inventory export",
            "6. 1-Click Operational SME Journey Demo"
        ],
        "features": [
            "FastAPI Business Logic",
            "KrackedDevs Chief Procurement AI Rationale",
            "NewsAPI Real-time Supply Chain Market Intelligence",
            "Supabase PostgreSQL Persistent Storage",
            "Python Statistical Forecasting (SMA / Holt-Winters)",
            "Human-in-the-Loop Immutable Governance"
        ]
    }

@app.get("/health")
@app.get("/api/health")
async def health_check():
    return {
        "status": "ok",
        "fastapi": "running",
        "kracked_ai": {
            "configured": ai_advisor.is_kracked_configured(),
            "model": ai_advisor.kracked_model,
            "base_url": ai_advisor.kracked_base_url
        },
        "news_api": {
            "configured": market_news.is_configured(),
            "base_url": market_news.NEWS_API_BASE_URL
        },
        "supabase": {
            "connected": bool(db.client),
            "url": settings.SUPABASE_URL
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)
