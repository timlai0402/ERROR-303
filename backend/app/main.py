from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.routers import inventory, procurement, forecasting, market, workspace

app = FastAPI(
    title="StockWise AI — Procurement & Inventory Engine",
    description="Statistical Forecasting, GenAI-assisted Human-in-the-Loop Restocking, and Supabase Database Backend.",
    version="2.0.0"
)

# CORS configuration for Frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers with /api prefix
app.include_router(inventory.router, prefix="/api")
app.include_router(procurement.router, prefix="/api")
app.include_router(forecasting.router, prefix="/api")
app.include_router(market.router, prefix="/api")
app.include_router(workspace.router, prefix="/api")

@app.get("/")
def root():
    return {
        "product": "StockWise AI",
        "team": "ERROR 303",
        "status": "operational",
        "docs_url": "/docs",
        "features": [
            "FastAPI Business Logic",
            "GenAI Supplier & ROP Decision Rationale",
            "Supabase PostgreSQL Persistent Storage",
            "Python Statistical Forecasting (SMA / Holt-Winters)",
            "NewsAPI Market Intelligence",
            "Human-in-the-Loop Immutable Governance"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.API_HOST, port=settings.API_PORT, reload=True)

