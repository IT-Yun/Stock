import asyncio
import hashlib
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from api import sectors_router, analysis_router, news_router


# ── Auth: allowed nickname hashes (same list as frontend LoginGate) ──
_ALLOWED_NICKNAMES = [
    "admin", "seungyun", "이승윤",
    "2차전지 네오", "공학관복사기", "퓨차차",
    "pk 난 중국이 좋아(cweb)", "pk 미래로", "pk 뿅뿅 네오",
    "pk ㅇㅇ", "pk_coriny", "pk.", "pknu흥",
    "pk고고 xx", "pk기타치는 튜브", "pk마블",
    "pk불나게 일하는 니오", "pk신라젠", "pk연", "pk응애",
    "pk주릉", "pk주린코린", "pk코인이미래다", "pk하암",
    "가난뱅이", "개초보", "건배하는 프로도",
    "내가사면떨어짐", "눈물 흘리는 제이지",
    "다래락빌런", "도지 이스 굿", "돌집", "모래로지은집",
    "무지성", "베센트", "비트코이너", "서경", "수대 물고기",
    "엔비 브컴 암페놀(전cs 주린이)", "원금만 찾게 해줘",
    "제이지", "좌절하는 제이지", "주린이", "지하수",
    "차를 사자", "초코바나나", "카피머신 1호 팬", "카피머신 비서",
    "피카츄", "하트뽀뽀 어피치", "홀인원 강자", ".",
]

def _normalize(s: str) -> str:
    import re as _re
    return _re.sub(r"\s+", " ", s.strip().lower())

_ALLOWED_SET = {_normalize(n) for n in _ALLOWED_NICKNAMES}
# Also store SHA-256 hashes for token-based auth
_ALLOWED_HASHES = {hashlib.sha256(_normalize(n).encode()).hexdigest() for n in _ALLOWED_NICKNAMES}


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

        # POST/PUT/DELETE on /api/ — check auth
        headers = dict(scope.get("headers", []))
        nickname = headers.get(b"x-auth-nickname", b"").decode("utf-8", errors="ignore")
        token = headers.get(b"x-auth-token", b"").decode("utf-8", errors="ignore")

        if token and token in _ALLOWED_HASHES:
            return await self.app(scope, receive, send)
        if nickname and _normalize(nickname) in _ALLOWED_SET:
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

# Auth: pure ASGI middleware — only blocks POST/PUT/DELETE on /api/
# Must be added AFTER CORS so CORS wraps it (Starlette reverses order)
app.add_middleware(AuthMiddleware)

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
    import os
    is_render = bool(os.getenv("RENDER"))
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=not is_render,
        workers=2 if is_render else 1,
    )
