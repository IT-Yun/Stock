import asyncio
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from api import sectors_router, analysis_router, news_router, members_router
from api.members import get_all_allowed, _normalize


class AuthMiddleware:
    """Pure ASGI middleware — no BaseHTTPMiddleware overhead or blocking issues.
    Only enforces auth on mutating (POST/PUT/DELETE) /api/ requests.
    All GET requests pass through unconditionally for read-only public access.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        method = scope.get("method", "GET")
        path = scope.get("path", "")

        # GET/HEAD/OPTIONS — always pass through (read-only public access)
        if method in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)

        # Non-API routes — always pass through
        if not path.startswith("/api"):
            return await self.app(scope, receive, send)

        # Login verification — allow without auth (user isn't logged in yet)
        if path == "/api/members/verify":
            return await self.app(scope, receive, send)

        # POST/PUT/DELETE on /api/ — check auth
        headers = dict(scope.get("headers", []))
        nickname = headers.get(b"x-auth-nickname", b"").decode("utf-8", errors="ignore")

        # Dynamically read allowed members from members.json
        from urllib.parse import unquote
        decoded = unquote(nickname)
        allowed = get_all_allowed()
        if decoded and _normalize(decoded) in allowed:
            return await self.app(scope, receive, send)

        # Reject
        response = JSONResponse(
            status_code=403,
            content={"error": "접근 권한이 없습니다. 로그인이 필요합니다."},
        )
        return await response(scope, receive, send)


def _warmup_cache():
    """Warm only the high-value shared caches at startup.

    Avoid aggressive per-ticker warmup here. On cold boot that burst can trigger
    external provider rate limits before real users even load the page.
    """
    try:
        from services.stock_data import StockDataService
        from services.commodity_data import CommodityDataService
        print("[WARMUP] Phase 1: sectors + commodities...")
        StockDataService.get_all_sectors()
        CommodityDataService.get_commodity_prices()
        print("[WARMUP] Phase 1 done.")
    except Exception as e:
        print(f"[WARMUP] Partial failure (non-fatal): {e}")


def _warmup_checklist_scores():
    """Gradually pre-warm checklist-live scores for all top picks.
    This runs after initial warmup so ranking scores match the detail page 종합점수.
    Delays between calls to respect Gemini rate limits.
    """
    import time
    time.sleep(30)  # let initial warmup finish first
    try:
        from api.analysis import TOP_PICK_SECTOR_MAP, get_checklist_live, _ANALYSIS_CACHE
        tickers = list(TOP_PICK_SECTOR_MAP.keys())
        warmed = 0
        for ticker in tickers:
            cache_key = f"checklist-live:{ticker}"
            if cache_key in _ANALYSIS_CACHE:
                continue  # already cached
            try:
                get_checklist_live(ticker)
                warmed += 1
                print(f"[CHECKLIST-WARMUP] {ticker} done ({warmed}/{len(tickers)})")
                time.sleep(3)  # respect Gemini rate limit
            except Exception as e:
                print(f"[CHECKLIST-WARMUP] {ticker} failed: {e}")
                time.sleep(2)
        print(f"[CHECKLIST-WARMUP] Complete: {warmed} new scores warmed")
        # Regenerate top-ranked with real scores
        try:
            from api.analysis import get_top_ranked, _ANALYSIS_CACHE as ac
            ac.pop("top-ranked-v2", None)  # clear stale ranking
            get_top_ranked()
            print("[CHECKLIST-WARMUP] Top-ranked regenerated with real scores")
        except Exception:
            pass
    except Exception as e:
        print(f"[CHECKLIST-WARMUP] Failed: {e}")


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


# ── Daily auto-refresh: updates all stock scores & data once per day ──
_last_daily_refresh: dict = {"ts": None, "status": "idle", "stocks_updated": 0, "errors": 0}

def _daily_refresh_worker():
    """Background thread: refresh all stock data once per day (KST 06:00)."""
    import time
    from datetime import datetime, timezone, timedelta

    KST = timezone(timedelta(hours=9))

    while True:
        now = datetime.now(KST)
        # Calculate next 06:00 KST
        target = now.replace(hour=6, minute=0, second=0, microsecond=0)
        if now >= target:
            target += timedelta(days=1)
        wait_secs = (target - now).total_seconds()
        print(f"[DAILY-REFRESH] Next refresh at {target.strftime('%Y-%m-%d %H:%M KST')} (in {wait_secs/3600:.1f}h)")
        time.sleep(wait_secs)

        _run_daily_refresh()


def _run_daily_refresh():
    """Execute the daily refresh: clear caches and re-score all stocks."""
    from datetime import datetime, timezone, timedelta
    from concurrent.futures import ThreadPoolExecutor, as_completed

    KST = timezone(timedelta(hours=9))
    _last_daily_refresh["status"] = "running"
    _last_daily_refresh["ts"] = datetime.now(KST).isoformat()
    print("[DAILY-REFRESH] Starting daily refresh...")

    try:
        from api.analysis import (
            TOP_PICK_SECTOR_MAP, _ANALYSIS_CACHE, get_top_ranked,
            get_technical_prediction, StockDataService, CommodityDataService,
        )

        # 1. Clear stale caches
        stale_keys = [k for k in _ANALYSIS_CACHE if k.startswith(("top-ranked", "checklist:", "move-reasons:"))]
        for k in stale_keys:
            _ANALYSIS_CACHE.pop(k, None)
        print(f"[DAILY-REFRESH] Cleared {len(stale_keys)} stale cache entries")

        # 2. Refresh commodities
        try:
            CommodityDataService.get_commodity_prices()
            print("[DAILY-REFRESH] Commodities refreshed")
        except Exception as e:
            print(f"[DAILY-REFRESH] Commodity refresh failed: {e}")

        # 3. Refresh stock data for all tracked tickers (sequentially to avoid rate limits)
        all_tickers = list(TOP_PICK_SECTOR_MAP.keys())
        updated = 0
        errors = 0
        import time

        for ticker in all_tickers:
            try:
                StockDataService.get_stock_history(ticker, period="3mo")
                updated += 1
                time.sleep(0.5)  # Rate limit protection
            except Exception:
                errors += 1

        print(f"[DAILY-REFRESH] Stock data: {updated} updated, {errors} errors")

        # 4. Regenerate top-ranked scores
        try:
            get_top_ranked()
            print("[DAILY-REFRESH] Top-ranked regenerated")
        except Exception as e:
            print(f"[DAILY-REFRESH] Top-ranked failed: {e}")

        _last_daily_refresh["stocks_updated"] = updated
        _last_daily_refresh["errors"] = errors
        _last_daily_refresh["status"] = "done"
        print(f"[DAILY-REFRESH] Complete! {updated}/{len(all_tickers)} stocks updated")

    except Exception as e:
        _last_daily_refresh["status"] = f"error: {e}"
        print(f"[DAILY-REFRESH] FAILED: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: warm cache in background thread (non-blocking)
    threading.Thread(target=_warmup_cache, daemon=True).start()
    threading.Thread(target=_keep_alive, daemon=True).start()
    threading.Thread(target=_daily_refresh_worker, daemon=True).start()
    threading.Thread(target=_warmup_checklist_scores, daemon=True).start()
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

# Auth: pure ASGI middleware — only blocks POST/PUT/DELETE on /api/
# Must be added AFTER CORS so CORS wraps it (Starlette reverses order)
app.add_middleware(AuthMiddleware)

app.include_router(sectors_router)
app.include_router(analysis_router)
app.include_router(news_router)
app.include_router(members_router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/refresh-status")
async def refresh_status():
    """Check when the last daily data refresh happened."""
    return _last_daily_refresh


@app.post("/api/refresh-now")
async def refresh_now():
    """Manually trigger a full data refresh (admin only)."""
    if _last_daily_refresh["status"] == "running":
        return {"message": "이미 새로고침 진행 중입니다."}
    threading.Thread(target=_run_daily_refresh, daemon=True).start()
    return {"message": "새로고침을 시작했습니다. /api/refresh-status에서 진행상황을 확인하세요."}


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
        # Try to serve the exact file first (but NOT stale .js/.css with wrong hash)
        file_path = FRONTEND_DIST / full_path
        if file_path.is_file():
            return FileResponse(str(file_path))
        # If browser requests a hashed asset that no longer exists → 404 (not index.html!)
        # This prevents serving HTML as JS, which causes parse errors
        if full_path.startswith("assets/"):
            return JSONResponse(status_code=404, content={"error": "asset not found"})
        # SPA fallback: always serve fresh index.html (no-cache so browser gets latest JS refs)
        from starlette.responses import Response
        index_path = FRONTEND_DIST / "index.html"
        content = index_path.read_bytes()
        return Response(
            content=content,
            media_type="text/html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate", "Pragma": "no-cache"},
        )
else:
    @app.get("/")
    async def root():
        return {"message": "Stock Analysis API is running. Frontend not built yet."}


if __name__ == "__main__":
    import os
    is_render = bool(os.getenv("RENDER"))
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=not is_render,
        workers=2 if is_render else 1,
    )
