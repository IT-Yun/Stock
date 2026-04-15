from fastapi import APIRouter
from models.schemas import NewsArticle
from services.news_crawler import NewsCrawlerService

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/news/{sector_name}")
async def get_sector_news(sector_name: str) -> list[NewsArticle]:
    """Get latest news for a sector."""
    return NewsCrawlerService.get_sector_news(sector_name)


@router.get("/news/search/{keyword}")
async def search_news(keyword: str) -> list[NewsArticle]:
    """Search news by keyword."""
    return NewsCrawlerService.search_news(keyword)
