import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from api import sectors_router, analysis_router, news_router


def _warmup_cache():
    """Pre-fetch ALL data at startup so yfinance calls are minimized during usage."""
    import time as _t
    try:
        from services.stock_data import StockDataService
        from services.commodity_data import CommodityDataService
        print("[WARMUP] Phase 1: sectors + commodities...")
        StockDataService.get_all_sectors()
        CommodityDataService.get_commodity_prices()
        print("[WARMUP] Phase 1 done.")

        # Phase 2: pre-fetch checklist for all top-pick stocks (heaviest API usage)
        # This prevents rate limiting during normal usage
        # Phase 2: pre-fetch chart + analysis for top picks (lighter than checklist)
        from api.analysis import TOP_PICK_SECTOR_MAP, _ANALYSIS_CACHE, _ticker_key
        import yfinance as yf_warmup
        tickers = list(TOP_PICK_SECTOR_MAP.keys())
        print(f"[WARMUP] Phase 2: pre-loading {len(tickers)} top-pick stock data...")
        for i, ticker in enumerate(tickers):
            try:
                stock = yf_warmup.Ticker(ticker)
                info = stock.info or {}
                hist = stock.history(period="3mo")
                if info and len(info) > 3:
                    # Cache basic info
                    from services.stock_data import _set_cached as stock_cache
                    stock_cache(f"info:{ticker}", {
                        "ticker": ticker,
                        "name": info.get("shortName", ticker),
                        "price": round(float(hist["Close"].iloc[-1]), 2) if not hist.empty else 0,
                        "change_percent": round(((float(hist["Close"].iloc[-1]) - float(hist["Close"].iloc[-2])) / float(hist["Close"].iloc[-2]) * 100), 2) if len(hist) >= 2 else 0,
                    })
                    print(f"[WARMUP]   ({i+1}/{len(tickers)}) {ticker} OK")
                else:
                    print(f"[WARMUP]   ({i+1}/{len(tickers)}) {ticker} SKIP (no info)")
            except Exception as e:
                print(f"[WARMUP]   ({i+1}/{len(tickers)}) {ticker} SKIP: {e}")
            _t.sleep(1)  # 1초 간격
        print("[WARMUP] Phase 2 done.")
    except Exception as e:
        print(f"[WARMUP] Partial failure (non-fatal): {e}")


def _keep_alive():
    """Ping ourselves every 10 min to prevent Render free tier spin-down."""
    import time
    import requests as req
    port = settings.API_PORT
    while True:
        time.sleep(600)
        try:
            req.get(f"http://127.0.0.1:{port}/health", timeout=5)
        except Exception:
            pass


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm cache in background thread (non-blocking)
    threading.Thread(target=_warmup_cache, daemon=True).start()
    threading.Thread(target=_keep_alive, daemon=True).start()
    yield


app = FastAPI(
    title="Stock Analysis API",
    description="Local stock analysis platform with technical indicators, news, and commodity data",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sectors_router)
app.include_router(analysis_router)
app.include_router(news_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


# ── Serve frontend static files (production build) ──
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

if FRONTEND_DIST.is_dir():
    # Serve static assets (JS, CSS, images)
    app.mount("/assets", StaticFiles(directory=str(FRONTEND_DIST / "assets")), name="assets")

    # Catch-all: serve index.html for any non-API route (SPA routing)
    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # Don't intercept API routes
        if full_path.startswith("api/"):
            return {"error": "not found"}
        # Try to serve the exact file first
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # Fallback to index.html for SPA routing
        return FileResponse(str(FRONTEND_DIST / "index.html"))
else:
    @app.get("/")
    async def root():
        return {"message": "Stock Analysis API is running. Frontend not built yet."}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
