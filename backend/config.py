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


settings = Settings()
