from .sectors import router as sectors_router
from .analysis import router as analysis_router
from .news import router as news_router

__all__ = ["sectors_router", "analysis_router", "news_router"]
