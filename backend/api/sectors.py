from fastapi import APIRouter
from models.schemas import Sector, Stock
from services.stock_data import StockDataService

router = APIRouter(prefix="/api", tags=["sectors"])


@router.get("/rankings/top-ranked")
def get_top_ranked_rankings() -> dict:
    """Non-conflicting top-ranked endpoint for the homepage."""
    from api.analysis import get_top_ranked
    return get_top_ranked()


@router.get("/sectors/top-ranked")
def get_top_ranked_under_sectors() -> dict:
    """Stable rankings endpoint under the working /sectors namespace."""
    from api.analysis import get_top_ranked
    return get_top_ranked()


@router.get("/sectors")
def list_sectors() -> list[Sector]:
    """List all sectors with top 3 stocks each."""
    sectors_data = StockDataService.get_all_sectors()
    results = []
    for s in sectors_data:
        stocks = [
            Stock(
                ticker=st["ticker"],
                name=st.get("name", st["ticker"]),
                sector=st.get("sector", s["name"]),
                price=st.get("price", 0.0),
                change_percent=st.get("change_percent", 0.0),
            )
            for st in s.get("stocks", [])
        ]
        results.append(Sector(
            name=s["name"],
            description=s.get("description", ""),
            stocks=stocks,
        ))
    return results


@router.get("/sectors/{sector_name}/stocks")
def get_sector_stocks(sector_name: str) -> list[Stock]:
    """Get detailed stock list for a specific sector."""
    stocks_data = StockDataService.get_sector_stocks(sector_name)
    return [
        Stock(
            ticker=st["ticker"],
            name=st.get("name", st["ticker"]),
            sector=st.get("sector", sector_name),
            price=st.get("price", 0.0),
            change_percent=st.get("change_percent", 0.0),
        )
        for st in stocks_data
    ]
