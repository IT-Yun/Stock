import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    SECTOR_DATA_PATH: str = os.getenv("SECTOR_DATA_PATH", "../data/sectors.json")
    NEWS_SOURCES: list[str] = os.getenv(
        "NEWS_SOURCES", "naver,google"
    ).split(",")


settings = Settings()
