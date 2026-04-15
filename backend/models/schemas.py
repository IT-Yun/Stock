from pydantic import BaseModel, Field


class Stock(BaseModel):
    ticker: str
    name: str
    sector: str
    price: float
    change_percent: float


class Sector(BaseModel):
    name: str
    description: str
    stocks: list[Stock] = Field(default_factory=list)


class TechnicalIndicators(BaseModel):
    rsi: float | None = None
    macd: float | None = None
    macd_signal: float | None = None
    bollinger_upper: float | None = None
    bollinger_middle: float | None = None
    bollinger_lower: float | None = None
    sma_20: float | None = None
    sma_50: float | None = None
    sma_200: float | None = None
    buy_sell_signal: str | None = None


class NewsArticle(BaseModel):
    title: str
    url: str
    source: str
    published_at: str | None = None
    summary: str | None = None


class CommodityPrice(BaseModel):
    name: str
    symbol: str
    price: float
    change_percent: float
    unit: str


class AnalysisResult(BaseModel):
    ticker: str
    indicators: TechnicalIndicators
    recommendation: str
    confidence_score: float
