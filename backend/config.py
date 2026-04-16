import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()
BASE_DIR = Path(__file__).resolve().parent


class Settings:
    """Application settings loaded from environment variables."""

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("PORT", os.getenv("API_PORT", "8000")))
    SECTOR_DATA_PATH: str = str(
        Path(os.getenv("SECTOR_DATA_PATH", str(BASE_DIR.parent / "data" / "sectors.json"))).resolve()
    )
    NEWS_SOURCES: list[str] = os.getenv(
        "NEWS_SOURCES", "naver,google"
    ).split(",")
    CACHE_DIR: str = os.getenv("CACHE_DIR", "")

    # Supabase
    SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")

    # Finnhub — US stock fundamentals
    FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")

    # Gemini AI — checklist validation & custom analysis
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()
