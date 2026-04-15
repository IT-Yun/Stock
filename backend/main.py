from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sectors_router)
app.include_router(analysis_router)
app.include_router(news_router)


@app.get("/")
async def root():
    return {"message": "Stock Analysis API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
    )
