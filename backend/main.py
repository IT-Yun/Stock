from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from config import settings
from api import sectors_router, analysis_router, news_router

app = FastAPI(
    title="Stock Analysis API",
    description="Local stock analysis platform with technical indicators, news, and commodity data",
    version="1.0.0",
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
