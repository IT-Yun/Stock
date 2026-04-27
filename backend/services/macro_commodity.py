"""52개 원자재 매트릭스용 실시간 가격 + Z-score + 급등/장기추세 감지.

Source: wiki/macro/01-commodities.md 명세에서 yfinance ticker 가능한 원자재만 픽업.
나머지(헬륨-3, 이리듐, 갈륨, JKM 가스 등)는 fetchable=False로 표시 — 추후 별도 소스.

Z-score 계산: 60일 daily return의 표준편차 대비 최근 1일 return.
급등 룰: Z > 1.5 OR 1d > 3% OR 5d > 5%
장기 상승 룰: 20d > 5% AND 60d > 12%, 또는 120d > 20%
"""

from __future__ import annotations

import time
import math
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from services.stock_data import StockDataService


# wiki/macro/01-commodities.md의 52개 원자재 중 yfinance에서 fetch 가능한 것들 매핑.
# (id, name, category, unit, yfinance_ticker, is_etf_proxy)
COMMODITY_FEED: list[dict[str, Any]] = [
    # 에너지
    {"id": "crude_wti", "name": "WTI 원유", "category": "에너지", "unit": "USD/bbl", "ticker": "CL=F"},
    {"id": "crude_brent", "name": "Brent 원유", "category": "에너지", "unit": "USD/bbl", "ticker": "BZ=F"},
    {"id": "natgas_henry_hub", "name": "천연가스 (Henry Hub)", "category": "에너지", "unit": "USD/MMBtu", "ticker": "NG=F"},
    # 산업금속
    {"id": "copper", "name": "구리", "category": "산업금속", "unit": "USD/lb", "ticker": "HG=F"},
    {"id": "aluminum", "name": "알루미늄", "category": "산업금속", "unit": "USD/lb", "ticker": "ALI=F"},
    # 귀금속
    {"id": "gold", "name": "금", "category": "귀금속", "unit": "USD/oz", "ticker": "GC=F"},
    {"id": "silver", "name": "은", "category": "귀금속", "unit": "USD/oz", "ticker": "SI=F"},
    {"id": "platinum", "name": "백금", "category": "귀금속", "unit": "USD/oz", "ticker": "PL=F"},
    {"id": "palladium", "name": "팔라듐", "category": "귀금속", "unit": "USD/oz", "ticker": "PA=F"},
    # 농산물
    {"id": "corn", "name": "옥수수", "category": "농산물", "unit": "USD/bushel", "ticker": "ZC=F"},
    {"id": "soybean", "name": "대두", "category": "농산물", "unit": "USD/bushel", "ticker": "ZS=F"},
    {"id": "wheat", "name": "밀", "category": "농산물", "unit": "USD/bushel", "ticker": "ZW=F"},
    {"id": "coffee", "name": "커피", "category": "농산물", "unit": "USD/lb", "ticker": "KC=F"},
    {"id": "sugar", "name": "설탕", "category": "농산물", "unit": "USD/lb", "ticker": "SB=F"},
    {"id": "cotton", "name": "면화", "category": "농산물", "unit": "USD/lb", "ticker": "CT=F"},
]

# yfinance 조합으로 계산 가능한 항목
COMPUTED_FEED: list[dict[str, Any]] = [
    {
        "id": "crack_321",
        "name": "3-2-1 크랙 스프레드",
        "category": "에너지",
        "unit": "USD/bbl",
        "source": "Computed/yfinance",
        "source_url": "https://www.eia.gov/petroleum/weekly/",
        "source_type": "computed",
        "frequency": "daily",
        "confidence": 72,
        "coverage_status": "computed_proxy",
        "components": {"crude": "CL=F", "gasoline": "RB=F", "heating_oil": "HO=F"},
        "note": "2*RBOB + 1*Heating Oil - 3*WTI 근사. 단위 보정 이슈가 있어 방향성 proxy로 사용",
    },
]

# 명세 전체 커버리지. ticker가 있으면 자동 가격/차트, 없으면 지연/월간/문서 소스로 자동 커버리지 표시.
EXTERNAL_FEED: list[dict[str, Any]] = [
    {"id": "uranium_u3o8", "name": "우라늄 U3O8 (spot)", "category": "에너지",
     "source_url": "https://www.cameco.com/invest/markets/uranium-price",
     "source": "Cameco/UxC", "source_type": "external", "frequency": "weekly", "confidence": 68,
     "coverage_status": "delayed", "ticker": "URNM", "is_proxy": True, "proxy_for": "U3O8 spot",
     "note": "Cameco/UxC 주간 발표 + URNM 프록시"},
    {"id": "iridium", "name": "이리듐", "category": "양자/방산 특수재",
     "source_url": "https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices",
     "source": "Johnson Matthey", "source_type": "external", "frequency": "daily", "confidence": 58,
     "coverage_status": "proxy", "ticker": "SBSW", "is_proxy": True, "proxy_for": "Iridium/PGM specialty metal",
     "note": "Johnson Matthey 일일 base price가 원자료. 자동 차트는 PGM 광산주 SBSW proxy",
     "is_hidden_bottleneck": True},
    {"id": "helium_3", "name": "헬륨-3", "category": "양자/방산 특수재",
     "source_url": "https://www.isotopes.gov/",
     "source": "DOE Isotope Program", "source_type": "external", "frequency": "irregular", "confidence": 40,
     "coverage_status": "proxy", "ticker": "LIN", "is_proxy": True, "proxy_for": "Helium-3 supply chain",
     "note": "DOE 배급제, 민간 spot 시장 전무. LIN은 산업가스 공급망 proxy일 뿐 가격 대체 아님",
     "is_hidden_bottleneck": True},
    {"id": "natgas_jkm", "name": "천연가스 JKM", "category": "에너지",
     "source_url": "https://www.spglobal.com/commodityinsights/en/our-methodology/price-assessments/lng/asia-jkm",
     "source": "S&P Global Platts", "source_type": "external", "frequency": "daily", "confidence": 62,
     "coverage_status": "delayed", "ticker": "UNG", "is_proxy": True, "proxy_for": "Asia JKM LNG",
     "note": "JKM 직접 가격은 폐쇄성이 높아 UNG/Henry Hub를 보조 proxy로 병기"},
    {"id": "natgas_ttf", "name": "TTF 유럽 가스", "category": "에너지",
     "source_url": "https://www.ice.com/products/27996665/Dutch-TTF-Gas-Futures",
     "source": "ICE Endex", "source_type": "external", "frequency": "daily", "confidence": 58,
     "coverage_status": "delayed", "ticker": "UNG", "is_proxy": True, "proxy_for": "Dutch TTF Gas",
     "note": "ICE 지연 데이터 + UNG 보조 proxy"},
    {"id": "coal_newcastle", "name": "Newcastle 석탄", "category": "에너지",
     "source_url": "https://www.worldbank.org/en/research/commodity-markets",
     "source": "World Bank Pink Sheet", "source_type": "external", "frequency": "monthly", "confidence": 55,
     "coverage_status": "monthly", "ticker": "BTU", "is_proxy": True, "proxy_for": "Newcastle thermal coal",
     "note": "월간 가격 + Peabody Energy proxy"},
    {"id": "lithium_carbonate", "name": "탄산리튬 (China spot)", "category": "희소금속",
     "source_url": "https://tradingeconomics.com/commodity/lithium",
     "source": "Trading Economics", "source_type": "external", "frequency": "daily", "confidence": 62,
     "coverage_status": "delayed", "ticker": "LIT", "is_proxy": True, "proxy_for": "Lithium carbonate spot",
     "note": "중국 spot + LIT proxy"},
    {"id": "nickel_lme", "name": "니켈 LME", "category": "산업금속",
     "source_url": "https://www.lme.com/en/Metals/Non-ferrous/LME-Nickel",
     "source": "LME", "source_type": "external", "frequency": "daily", "confidence": 60,
     "coverage_status": "delayed", "ticker": "PICK", "is_proxy": True, "proxy_for": "LME Nickel",
     "note": "LME 공식 가격 + PICK 광산 ETF proxy"},
    {"id": "zinc_lme", "name": "아연 LME", "category": "산업금속",
     "source_url": "https://www.lme.com/en/Metals/Non-ferrous/LME-Zinc",
     "source": "LME", "source_type": "external", "frequency": "daily", "confidence": 58,
     "coverage_status": "delayed", "ticker": "PICK", "is_proxy": True, "proxy_for": "LME Zinc",
     "note": "LME 공식 가격 + PICK 광산 ETF proxy"},
    {"id": "lead_lme", "name": "납 LME", "category": "산업금속",
     "source_url": "https://www.lme.com/en/Metals/Non-ferrous/LME-Lead",
     "source": "LME", "source_type": "external", "frequency": "daily", "confidence": 55,
     "coverage_status": "delayed", "ticker": "PICK", "is_proxy": True, "proxy_for": "LME Lead",
     "note": "LME 공식 가격 + 광산 ETF proxy"},
    {"id": "tin_lme", "name": "주석 LME", "category": "산업금속",
     "source_url": "https://www.lme.com/en/Metals/Non-ferrous/LME-Tin",
     "source": "LME", "source_type": "external", "frequency": "daily", "confidence": 55,
     "coverage_status": "delayed", "ticker": "PICK", "is_proxy": True, "proxy_for": "LME Tin",
     "note": "LME 공식 가격 + 광산 ETF proxy"},
    {"id": "iron_ore", "name": "철광석", "category": "산업금속",
     "source_url": "https://www.worldbank.org/en/research/commodity-markets",
     "source": "World Bank Pink Sheet", "source_type": "external", "frequency": "monthly", "confidence": 60,
     "coverage_status": "monthly", "ticker": "SLX", "is_proxy": True, "proxy_for": "Iron Ore 62% Fe",
     "note": "월간 가격 + 철강 ETF proxy"},
    {"id": "hrc_steel", "name": "HRC 열연강판", "category": "산업금속",
     "source_url": "https://www.cmegroup.com/markets/metals/ferrous/hrc-steel.html",
     "source": "CME/yfinance", "source_type": "yfinance", "frequency": "daily", "confidence": 72,
     "coverage_status": "live", "ticker": "HRC=F", "note": "CME HRC futures"},
    {"id": "cobalt", "name": "코발트", "category": "희소금속",
     "source_url": "https://www.lme.com/en/Metals/EV/LME-Cobalt",
     "source": "LME", "source_type": "external", "frequency": "daily", "confidence": 50,
     "coverage_status": "delayed", "ticker": "PICK", "is_proxy": True, "proxy_for": "LME Cobalt",
     "note": "LFP 전환으로 신호력 약화. 광산 ETF proxy"},
    {"id": "manganese", "name": "망간", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/manganese-statistics-and-information",
     "source": "USGS/World Bank", "source_type": "external", "frequency": "monthly", "confidence": 45,
     "coverage_status": "monthly", "ticker": "PICK", "is_proxy": True, "proxy_for": "Manganese ore",
     "note": "월간/연간 통계 + 광산 ETF proxy"},
    {"id": "natural_graphite", "name": "천연흑연", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/graphite-statistics-and-information",
     "source": "USGS/IEA", "source_type": "external", "frequency": "monthly", "confidence": 45,
     "coverage_status": "monthly", "ticker": "LIT", "is_proxy": True, "proxy_for": "Battery-grade graphite",
     "note": "음극재/중국 통제 이벤트 감시 + LIT proxy"},
    {"id": "gallium", "name": "갈륨", "category": "반도체 가스",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/gallium-statistics-and-information",
     "source": "USGS/Trading Economics", "source_type": "external", "frequency": "irregular", "confidence": 45,
     "coverage_status": "delayed", "ticker": "REMX", "is_proxy": True, "proxy_for": "Gallium metal",
     "note": "GaN/RF/전력반도체 공급망 통제 + REMX proxy"},
    {"id": "germanium", "name": "게르마늄", "category": "반도체 가스",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/germanium-statistics-and-information",
     "source": "USGS/Trading Economics", "source_type": "external", "frequency": "irregular", "confidence": 45,
     "coverage_status": "delayed", "ticker": "REMX", "is_proxy": True, "proxy_for": "Germanium metal",
     "note": "광통신/열영상/방산 소재 + REMX proxy"},
    {"id": "rhodium", "name": "로듐", "category": "귀금속",
     "source_url": "https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices",
     "source": "Johnson Matthey", "source_type": "external", "frequency": "daily", "confidence": 52,
     "coverage_status": "proxy", "ticker": "SBSW", "is_proxy": True, "proxy_for": "Rhodium/PGM basket",
     "note": "Johnson Matthey 로듐 가격이 원자료. 자동 차트는 PGM 광산주 SBSW proxy"},
    {"id": "neodymium", "name": "네오디뮴", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/rare-earths-statistics-and-information",
     "source": "USGS/Shanghai Metals Market", "source_type": "external", "frequency": "daily", "confidence": 50,
     "coverage_status": "delayed", "ticker": "REMX", "is_proxy": True, "proxy_for": "Neodymium oxide",
     "note": "영구자석/EV/방산. REMX proxy"},
    {"id": "dysprosium", "name": "디스프로슘", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/rare-earths-statistics-and-information",
     "source": "USGS/Shanghai Metals Market", "source_type": "external", "frequency": "daily", "confidence": 48,
     "coverage_status": "delayed", "ticker": "REMX", "is_proxy": True, "proxy_for": "Dysprosium oxide",
     "note": "고온 자석 병목. REMX proxy"},
    {"id": "terbium", "name": "터븀", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/rare-earths-statistics-and-information",
     "source": "USGS/Shanghai Metals Market", "source_type": "external", "frequency": "daily", "confidence": 48,
     "coverage_status": "delayed", "ticker": "REMX", "is_proxy": True, "proxy_for": "Terbium oxide",
     "note": "고성능 자석/방산. REMX proxy"},
    {"id": "indium", "name": "인듐", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/indium-statistics-and-information",
     "source": "USGS/Trading Economics", "source_type": "external", "frequency": "monthly", "confidence": 44,
     "coverage_status": "monthly", "ticker": "REMX", "is_proxy": True, "proxy_for": "Indium metal",
     "note": "ITO/디스플레이 소재"},
    {"id": "tellurium_bismuth", "name": "텔루륨/비스무트", "category": "희소금속",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/tellurium-statistics-and-information",
     "source": "USGS/World Bank", "source_type": "external", "frequency": "monthly", "confidence": 42,
     "coverage_status": "monthly", "ticker": "REMX", "is_proxy": True, "proxy_for": "Tellurium/Bismuth",
     "note": "태양광/반도체 특수소재"},
    {"id": "neon", "name": "네온", "category": "반도체 가스",
     "source_url": "https://www.semi.org/en",
     "source": "SEMI/USGS", "source_type": "external", "frequency": "irregular", "confidence": 38,
     "coverage_status": "proxy", "ticker": "LIN", "is_proxy": True, "proxy_for": "Neon specialty gas",
     "note": "반도체 레이저 가스. spot 공개가격 제한, LIN 산업가스 proxy"},
    {"id": "krypton", "name": "크립톤", "category": "반도체 가스",
     "source_url": "https://www.semi.org/en",
     "source": "SEMI", "source_type": "external", "frequency": "irregular", "confidence": 36,
     "coverage_status": "proxy", "ticker": "LIN", "is_proxy": True, "proxy_for": "Krypton specialty gas",
     "note": "반도체 특수가스. 공개가격 제한, LIN 산업가스 proxy"},
    {"id": "xenon", "name": "크세논", "category": "반도체 가스",
     "source_url": "https://www.semi.org/en",
     "source": "SEMI", "source_type": "external", "frequency": "irregular", "confidence": 36,
     "coverage_status": "proxy", "ticker": "LIN", "is_proxy": True, "proxy_for": "Xenon specialty gas",
     "note": "반도체/위성 추진 특수가스. 공개가격 제한, LIN 산업가스 proxy"},
    {"id": "helium", "name": "헬륨", "category": "반도체 가스",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/helium-statistics-and-information",
     "source": "USGS/BLM", "source_type": "external", "frequency": "annual", "confidence": 42,
     "coverage_status": "proxy", "ticker": "LIN", "is_proxy": True, "proxy_for": "Helium industrial gas",
     "note": "MRI/반도체/우주. 공개 spot 제한, LIN 산업가스 proxy"},
    {"id": "titanium", "name": "티타늄", "category": "양자/방산 특수재",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/titanium-statistics-and-information",
     "source": "USGS/World Bank", "source_type": "external", "frequency": "monthly", "confidence": 50,
     "coverage_status": "monthly", "ticker": "ITA", "is_proxy": True, "proxy_for": "Titanium sponge/aerospace chain",
     "note": "항공/방산 소재. ITA 방산항공 ETF proxy"},
    {"id": "sulfuric_acid", "name": "황산", "category": "화학원료",
     "source_url": "https://www.icis.com/explore/commodities/chemicals/sulphuric-acid/",
     "source": "ICIS/World Bank", "source_type": "external", "frequency": "weekly", "confidence": 42,
     "coverage_status": "delayed", "ticker": "MOS", "is_proxy": True, "proxy_for": "Sulfuric acid",
     "note": "리튬 추출/비료/화학 원료. MOS proxy"},
    {"id": "phosphoric_acid", "name": "인산", "category": "화학원료",
     "source_url": "https://www.usgs.gov/centers/national-minerals-information-center/phosphate-rock-statistics-and-information",
     "source": "USGS/World Bank", "source_type": "external", "frequency": "monthly", "confidence": 42,
     "coverage_status": "monthly", "ticker": "MOS", "is_proxy": True, "proxy_for": "Phosphoric acid",
     "note": "LFP/비료 chain. MOS proxy"},
    {"id": "caustic_soda", "name": "가성소다", "category": "화학원료",
     "source_url": "https://www.icis.com/explore/commodities/chemicals/caustic-soda/",
     "source": "ICIS/World Bank", "source_type": "external", "frequency": "weekly", "confidence": 42,
     "coverage_status": "delayed", "ticker": "DOW", "is_proxy": True, "proxy_for": "Caustic soda",
     "note": "알루미나/화학 원료. DOW proxy"},
    {"id": "methanol", "name": "메탄올", "category": "화학원료",
     "source_url": "https://www.methanex.com/our-business/pricing/",
     "source": "Methanex/ICIS", "source_type": "external", "frequency": "monthly", "confidence": 52,
     "coverage_status": "monthly", "ticker": "MEOH", "is_proxy": True, "proxy_for": "Methanol",
     "note": "Methanex posted price + MEOH proxy"},
    {"id": "ammonia_urea", "name": "암모니아·우레아", "category": "화학원료",
     "source_url": "https://www.worldbank.org/en/research/commodity-markets",
     "source": "World Bank/ICIS", "source_type": "external", "frequency": "monthly", "confidence": 48,
     "coverage_status": "monthly", "ticker": "CF", "is_proxy": True, "proxy_for": "Ammonia/Urea",
     "note": "비료/수소 carrier. CF proxy"},
    {"id": "glp1_peptide", "name": "GLP-1 펩타이드 원료", "category": "바이오 원료",
     "source_url": "https://www.bachem.com/investors/financial-reports/",
     "source": "Bachem/IQVIA", "source_type": "external", "frequency": "quarterly", "confidence": 44,
     "coverage_status": "proxy", "ticker": "LLY", "is_proxy": True, "proxy_for": "GLP-1 peptide CDMO capacity",
     "note": "원료 가격보다 CDMO 캐파/수주 감시. LLY/NVO/펩트론 chain"},
    {"id": "antibiotic_api", "name": "항생제 API", "category": "바이오 원료",
     "source_url": "https://www.pharmacompass.com/",
     "source": "PharmaCompass/IQVIA", "source_type": "external", "frequency": "monthly", "confidence": 38,
     "coverage_status": "delayed", "ticker": "XLV", "is_proxy": True, "proxy_for": "Antibiotic API",
     "note": "중국/인도 공급망 가격 공개성 낮음. 헬스케어 ETF 보조 proxy"},
    {"id": "vial_glass", "name": "바이알 글래스", "category": "바이오 원료",
     "source_url": "https://www.schott.com/en-gb/news-and-media/media-relations/financial-reports",
     "source": "Schott/Stevanato", "source_type": "external", "frequency": "quarterly", "confidence": 40,
     "coverage_status": "proxy", "ticker": "STVN", "is_proxy": True, "proxy_for": "Type I borosilicate vial glass",
     "note": "가격보다 수주/캐파 지표. STVN proxy"},
]


@dataclass
class CommodityFeedItem:
    id: str
    name: str
    category: str
    unit: str
    ticker: str | None
    fetchable: bool
    is_proxy: bool = False
    chartable: bool = False
    source: str = "yfinance"
    source_url: str | None = None
    source_type: str = "yfinance"
    fetched_at: str | None = None
    data_as_of: str | None = None
    frequency: str = "daily"
    confidence: int = 80
    coverage_status: str = "live"
    proxy_for: str | None = None
    # Live data
    price: float | None = None
    change_pct_1d: float | None = None
    change_pct_5d: float | None = None
    change_pct_10d: float | None = None
    change_pct_20d: float | None = None
    change_pct_60d: float | None = None
    change_pct_120d: float | None = None
    zscore_60d: float | None = None
    is_anomalous: bool = False
    is_surge: bool = False  # 급등
    is_plunge: bool = False  # 급락
    is_multi_month_uptrend: bool = False  # 몇개월째 상승
    is_multi_month_downtrend: bool = False  # 몇개월째 하락
    trend_label: str | None = None
    trend_score: float | None = None
    surge_reasons: list[str] | None = None
    trend_reasons: list[str] | None = None
    signal_type: str = "neutral"
    timing_action: str = "관망"
    timing_score: float = 0.0
    timing_reasons: list[str] | None = None
    risk_notes: list[str] | None = None
    driver_label: str | None = None
    cause_reasons: list[str] | None = None
    bullish_thesis: str | None = None
    caution: str | None = None
    strategic_watch: bool = False
    strategic_score: float = 0.0
    strategic_label: str | None = None
    strategic_reasons: list[str] | None = None
    fallback_url: str | None = None
    note: str | None = None
    is_hidden_bottleneck: bool = False
    error: str | None = None


# 캐시
_FEED_CACHE: tuple[float, list[CommodityFeedItem]] | None = None
_CACHE_TTL = 1800  # 30분 — yfinance rate limit 회피


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _last_index_iso(history) -> str | None:
    try:
        if history is None or history.empty:
            return None
        idx = history.index[-1]
        if hasattr(idx, "isoformat"):
            return idx.isoformat()
        return str(idx)
    except Exception:
        return None


def _compute_metrics(history) -> dict[str, Any]:
    """yfinance history DataFrame → price metrics."""
    if history is None or history.empty or len(history) < 2:
        return {}

    closes = history["Close"].dropna()
    if len(closes) < 2:
        return {}

    price = float(closes.iloc[-1])
    prev = float(closes.iloc[-2])
    change_1d = ((price - prev) / prev * 100) if prev else 0.0

    metrics = {"price": round(price, 4), "change_pct_1d": round(change_1d, 2)}

    if len(closes) >= 6:
        p5 = float(closes.iloc[-6])
        if p5:
            metrics["change_pct_5d"] = round((price - p5) / p5 * 100, 2)

    if len(closes) >= 11:
        p10 = float(closes.iloc[-11])
        if p10:
            metrics["change_pct_10d"] = round((price - p10) / p10 * 100, 2)

    if len(closes) >= 21:
        p20 = float(closes.iloc[-21])
        if p20:
            metrics["change_pct_20d"] = round((price - p20) / p20 * 100, 2)

    if len(closes) >= 61:
        p60 = float(closes.iloc[-60])
        if p60:
            metrics["change_pct_60d"] = round((price - p60) / p60 * 100, 2)

        # Z-score: daily returns의 표준편차 대비 최근 1일 return
        returns = closes.pct_change().dropna().iloc[-60:]
        if len(returns) >= 30:
            mean = float(returns.mean())
            std = float(returns.std())
            if std and not math.isnan(std):
                latest_return = (price - prev) / prev if prev else 0.0
                z = (latest_return - mean) / std
                metrics["zscore_60d"] = round(z, 2)

    if len(closes) >= 121:
        p120 = float(closes.iloc[-121])
        if p120:
            metrics["change_pct_120d"] = round((price - p120) / p120 * 100, 2)

    return metrics


def _build_item(spec: dict[str, Any], *, fetchable: bool = True) -> CommodityFeedItem:
    return CommodityFeedItem(
        id=spec["id"],
        name=spec["name"],
        category=spec["category"],
        unit=spec.get("unit", "—"),
        ticker=spec.get("ticker"),
        fetchable=fetchable,
        is_proxy=spec.get("is_proxy", False),
        chartable=bool(spec.get("ticker")),
        source=spec.get("source", "yfinance"),
        source_url=spec.get("source_url") or spec.get("fallback_url"),
        source_type=spec.get("source_type", "yfinance"),
        frequency=spec.get("frequency", "daily"),
        confidence=int(spec.get("confidence", 80)),
        coverage_status=spec.get("coverage_status", "live"),
        proxy_for=spec.get("proxy_for"),
        fallback_url=spec.get("fallback_url") or spec.get("source_url"),
        note=spec.get("note"),
        is_hidden_bottleneck=spec.get("is_hidden_bottleneck", False),
        fetched_at=_now_iso(),
    )


def _apply_history(item: CommodityFeedItem, history) -> None:
    metrics = _compute_metrics(history)
    for k, v in metrics.items():
        setattr(item, k, v)
    item.data_as_of = _last_index_iso(history)
    if item.price is None:
        item.coverage_status = "unavailable" if not item.ticker else "stale_fallback"
        item.confidence = min(item.confidence, 30)
        item.risk_notes = ["가격 데이터 수집 실패: 소스 직접 확인 필요"]
    _classify(item)


def _computed_crack_321(spec: dict[str, Any]) -> CommodityFeedItem:
    item = _build_item(spec, fetchable=True)
    item.chartable = False
    try:
        c = spec["components"]
        crude = StockDataService.get_stock_history(c["crude"], period="6mo")["Close"].dropna()
        gasoline = StockDataService.get_stock_history(c["gasoline"], period="6mo")["Close"].dropna()
        heating = StockDataService.get_stock_history(c["heating_oil"], period="6mo")["Close"].dropna()
        df = pd.concat([crude.rename("crude"), gasoline.rename("gasoline"), heating.rename("heating")], axis=1).dropna()
        # RBOB/Heating Oil are quoted in USD/gallon. Convert to USD/barrel by *42.
        spread = (2 * df["gasoline"] * 42 + df["heating"] * 42 - 3 * df["crude"]) / 3
        hist = pd.DataFrame({"Close": spread})
        _apply_history(item, hist)
    except Exception as e:
        item.error = str(e)[:120]
        item.coverage_status = "unavailable"
        item.confidence = 25
        item.timing_reasons = ["구성 선물 데이터 부족"]
        item.risk_notes = ["CL/RB/HO 중 하나라도 실패하면 계산 불가"]
        _assign_cause(item)
        _classify_strategic_watch(item)
    return item


def _classify(item: CommodityFeedItem) -> None:
    """급등/급락/장기추세 + 매수/매도 타이밍 분류."""
    reasons: list[str] = []

    z = item.zscore_60d
    d1 = item.change_pct_1d
    d5 = item.change_pct_5d
    d20 = item.change_pct_20d
    d60 = item.change_pct_60d
    d120 = item.change_pct_120d

    # 급등 조건: 단순 양봉이 아니라 단기 비정상 움직임만 급등으로 분류
    if z is not None and z > 1.8:
        reasons.append(f"Z-score {z:+.1f} (60일 비정상 급등)")
    if d1 is not None and d1 >= 3:
        reasons.append(f"하루 +{d1:.1f}%")
    if d5 is not None and d5 >= 6:
        reasons.append(f"5일 +{d5:.1f}%")

    if reasons:
        item.is_surge = True
        item.is_anomalous = True
        item.surge_reasons = reasons

    # 급락 조건
    plunge_reasons: list[str] = []
    if z is not None and z < -1.8:
        plunge_reasons.append(f"Z-score {z:.1f} (60일 비정상 급락)")
    if d1 is not None and d1 <= -3:
        plunge_reasons.append(f"하루 {d1:.1f}%")
    if d5 is not None and d5 <= -6:
        plunge_reasons.append(f"5일 {d5:.1f}%")

    if plunge_reasons:
        item.is_plunge = True
        item.is_anomalous = True
        item.surge_reasons = plunge_reasons

    # 몇개월 추세 조건
    trend_reasons: list[str] = []
    if d20 is not None and d60 is not None and d20 > 8 and d60 > 18:
        trend_reasons.append(f"1개월 +{d20:.1f}% / 3개월 +{d60:.1f}%")
    if d120 is not None and d120 > 30:
        trend_reasons.append(f"6개월 +{d120:.1f}%")
    if d60 is not None and d120 is not None and d60 > 12 and d120 > 20:
        trend_reasons.append("3개월·6개월 동시 상승")
    if trend_reasons:
        item.is_multi_month_uptrend = True
        item.trend_reasons = trend_reasons

    downtrend_reasons: list[str] = []
    if d20 is not None and d60 is not None and d20 < -8 and d60 < -18:
        downtrend_reasons.append(f"1개월 {d20:.1f}% / 3개월 {d60:.1f}%")
    if d120 is not None and d120 < -30:
        downtrend_reasons.append(f"6개월 {d120:.1f}%")
    if downtrend_reasons:
        item.is_multi_month_downtrend = True
        item.trend_reasons = downtrend_reasons

    score = 0.0
    for value, weight in [(d1, 0.15), (d5, 0.20), (d20, 0.25), (d60, 0.25), (d120, 0.15)]:
        if value is not None:
            score += max(-100.0, min(100.0, value)) * weight
    item.trend_score = round(score, 2)

    if item.is_surge:
        item.signal_type = "now_surge"
        item.trend_label = "지금 급등"
    elif item.is_plunge:
        item.signal_type = "now_plunge"
        item.trend_label = "지금 급락"
    elif item.is_multi_month_uptrend:
        item.signal_type = "multi_month_uptrend"
        item.trend_label = "몇개월째 상승"
    elif item.is_multi_month_downtrend:
        item.signal_type = "multi_month_downtrend"
        item.trend_label = "몇개월째 하락"
    elif d60 is not None and d60 > 8:
        item.signal_type = "slow_uptrend"
        item.trend_label = "완만한 상승"
    elif d60 is not None and d60 < -8:
        item.signal_type = "slow_downtrend"
        item.trend_label = "완만한 하락"
    else:
        item.signal_type = "neutral"
        item.trend_label = "중립"

    _classify_timing(item)
    _assign_cause(item)
    _classify_strategic_watch(item)


def _classify_timing(item: CommodityFeedItem) -> None:
    """원자재 매매 타이밍 룰.

    투자 조언 확정이 아니라, 가격 위치/추세/과열도를 기반으로 한 관심 구간 분류.
    """
    d1 = item.change_pct_1d
    d5 = item.change_pct_5d
    d20 = item.change_pct_20d
    d60 = item.change_pct_60d
    d120 = item.change_pct_120d
    z = item.zscore_60d

    score = 0.0
    reasons: list[str] = []
    risks: list[str] = []

    # 매수 후보는 "중기 추세는 살아 있고, 단기만 눌린" 경우로 제한한다.
    medium_up = (
        (d60 is not None and d60 >= 10)
        or (d120 is not None and d120 >= 25 and d60 is not None and d60 >= 3)
    )
    short_pullback = (
        (d5 is not None and -8 <= d5 <= -1.5)
        or (d1 is not None and d1 <= -1.5 and (z is None or z <= 0.3))
    )
    deep_fall = (d5 is not None and d5 < -8) or (z is not None and z < -2.2)

    if medium_up:
        score += 20
        reasons.append(f"중기 상승 추세 유지: 3개월 {d60:+.1f}% / 6개월 {d120:+.1f}%")
    if short_pullback:
        score += 25
        reasons.append(f"단기 눌림: 1일 {d1:+.1f}% / 5일 {d5:+.1f}%")
    if z is not None and -1.5 <= z <= 0.3 and short_pullback:
        score += 10
        reasons.append(f"Z {z:+.1f}: 과열이 아닌 눌림 구간")
    if deep_fall:
        score -= 30
        risks.append("단기 낙폭이 커서 falling knife 위험")

    # 과열/추격 위험
    if d5 is not None and d5 >= 6:
        score -= 30
        risks.append(f"5일 {d5:+.1f}% 급등: 추격 매수 위험")
    if z is not None and z >= 1.8:
        score -= 25
        risks.append(f"Z {z:+.1f}: 단기 과열")
    if d20 is not None and d20 >= 15:
        score -= 15
        risks.append(f"1개월 {d20:+.1f}%: 되돌림 리스크")

    # 구조적 하락: 싸 보여도 회피
    if d60 is not None and d60 <= -8:
        score -= 25
        risks.append(f"3개월 {d60:.1f}%: 중기 하락 추세")
    if d120 is not None and d120 <= -20:
        score -= 20
        risks.append(f"6개월 {d120:.1f}%: 장기 하락 추세")

    if score >= 45 and short_pullback and medium_up and not deep_fall:
        action = "분할 매수 관심"
    elif score >= 30 and short_pullback and medium_up and not deep_fall:
        action = "눌림 매수 후보"
    elif score <= -35:
        action = "매도·회피"
    elif score <= -15:
        action = "추격 금지"
    elif item.is_multi_month_uptrend:
        action = "보유·추세 확인"
        if not reasons:
            reasons.append("몇개월째 상승: 보유자는 추세 확인")
    else:
        action = "관망"
        if not reasons and not risks:
            reasons.append("뚜렷한 매수/매도 타이밍 없음")

    if action in {"분할 매수 관심", "눌림 매수 후보"} and item.confidence < 55:
        risks.append(f"신뢰도 {item.confidence}%: proxy/지연 데이터라 매수 후보에서 제외")
        action = "관망"

    if action in {"분할 매수 관심", "눌림 매수 후보"} and item.is_proxy and item.confidence < 65:
        risks.append("직접 spot이 아닌 proxy라 매수 타이밍 확정 불가")
        action = "관망"

    item.timing_action = action
    item.timing_score = round(score, 1)
    item.timing_reasons = reasons[:4]
    item.risk_notes = risks[:4]


STRATEGIC_MATERIALS: dict[str, tuple[str, list[str]]] = {
    "copper": ("전력망·AI 데이터센터 핵심금속", ["AI 전력망", "전선/변압기", "전기차"]),
    "aluminum": ("전력망·차량경량화·전력기기 소재", ["송전망", "전기차", "데이터센터 설비"]),
    "silver": ("태양광·전장·반도체 전도성 소재", ["태양광", "전장", "반도체 패키징"]),
    "uranium_u3o8": ("AI 전력 병목과 에너지 안보의 구조 원료", ["원전", "SMR", "데이터센터 PPA"]),
    "natgas_henry_hub": ("전력 피크와 LNG 수급의 변동성 원료", ["발전", "LNG", "전력가격"]),
    "lithium_carbonate": ("EV/ESS 배터리 원가의 핵심 소재", ["EV", "ESS", "양극재"]),
    "nickel_lme": ("고에너지밀도 배터리와 스테인리스 원료", ["배터리", "스테인리스", "방산"]),
    "cobalt": ("배터리·항공합금 공급망 민감 소재", ["배터리", "항공합금", "공급망"]),
    "natural_graphite": ("음극재·중국 통제 리스크 핵심 소재", ["음극재", "EV", "수출통제"]),
    "manganese": ("LMFP·배터리 다변화 소재", ["LMFP", "ESS", "양극재"]),
    "gallium": ("GaN 전력반도체·RF·방산 소재", ["전력반도체", "RF", "수출통제"]),
    "germanium": ("광통신·열영상·방산 소재", ["광통신", "방산", "수출통제"]),
    "neodymium": ("영구자석·로봇·EV·방산 소재", ["영구자석", "로봇", "EV"]),
    "dysprosium": ("고온 영구자석 병목 소재", ["EV 모터", "방산", "로봇"]),
    "terbium": ("고성능 자석·방산 소재", ["자석", "방산", "공급망"]),
    "titanium": ("항공기·미사일·우주 구조재", ["항공", "방산", "우주"]),
    "iridium": ("PEM 전해조 촉매 병목", ["수소", "PEM 전해조", "공급병목"]),
    "helium": ("반도체·MRI·우주 극저온 가스", ["반도체", "MRI", "우주"]),
    "neon": ("반도체 노광 가스", ["EUV/DUV", "반도체", "공급차질"]),
    "krypton": ("반도체 특수가스", ["반도체", "식각/노광", "공급차질"]),
    "xenon": ("반도체·위성 추진 특수가스", ["반도체", "우주", "방산"]),
}


def _classify_strategic_watch(item: CommodityFeedItem) -> None:
    """많이 빠졌지만 산업 필수성이 높은 원료를 '바로 매수'와 분리해 관찰한다."""
    meta = STRATEGIC_MATERIALS.get(item.id)
    if not meta:
        return

    thesis, use_cases = meta
    d20 = item.change_pct_20d
    d60 = item.change_pct_60d
    d120 = item.change_pct_120d
    confidence = item.confidence or 0
    score = 0.0
    reasons: list[str] = [thesis, f"용도: {', '.join(use_cases)}"]

    if d60 is not None and d60 <= -10:
        score += min(35, abs(d60) * 1.2)
        reasons.append(f"3개월 {d60:+.1f}%: 낙폭 과대 후보")
    if d120 is not None and d120 <= -20:
        score += min(35, abs(d120))
        reasons.append(f"6개월 {d120:+.1f}%: 장기 낙폭 확인")
    if d20 is not None and d20 > 0 and d60 is not None and d60 < 0:
        score += 12
        reasons.append(f"1개월 {d20:+.1f}%: 장기 하락 뒤 반등 시도")
    if item.is_plunge:
        score -= 18
        reasons.append("단기 급락 중이라 가격 안정 확인 전까지 관망")
    if item.is_surge:
        score -= 20
        reasons.append("이미 단기 급등이라 전략 관심보다 추격 위험이 큼")
    if confidence < 45:
        score -= 10
        reasons.append(f"신뢰도 {confidence}%: 공개 가격 제한/월간 데이터")

    item.strategic_score = round(max(0.0, score), 1)
    item.strategic_watch = item.strategic_score >= 12 and not item.is_surge
    if item.strategic_watch:
        item.strategic_label = "낙폭+핵심원료 관찰"
        item.strategic_reasons = reasons[:5]
    elif score > 0:
        item.strategic_label = "핵심원료 감시"
        item.strategic_reasons = reasons[:4]


def _assign_cause(item: CommodityFeedItem) -> None:
    """가격 움직임의 실질 원인과 깨지는 조건을 산업별로 붙인다."""
    cid = item.id
    cat = item.category
    d5 = item.change_pct_5d or 0
    d60 = item.change_pct_60d or 0

    if cid in {"crude_wti", "crude_brent"}:
        item.driver_label = "중동/호르무즈 공급 리스크 + 원유 재고/달러"
        item.cause_reasons = [
            "원유는 운송로와 산유국 공급 차질에 바로 반응한다.",
            "현재 중동·호르무즈 리스크가 남아 있으면 전쟁 프리미엄이 가격에 붙을 수 있다.",
            "다만 휴전/항로 정상화/재고 증가가 나오면 프리미엄이 빠지며 되돌림이 빠르다.",
        ]
        item.bullish_thesis = "전쟁·봉쇄·제재가 길어지고 5일/1개월 가격이 계속 고점을 높이면 에너지 chain은 더 갈 수 있다."
        item.caution = "전쟁 리스크가 완화되면 급등분은 매수 근거가 아니라 매도/차익실현 근거로 바뀐다."
    elif "natgas" in cid:
        item.driver_label = "날씨·LNG 수급·재고"
        item.cause_reasons = [
            "가스는 원유보다 날씨와 재고 민감도가 높다.",
            "JKM/TTF는 직접 가격 공개가 제한되어 proxy 신뢰도가 낮다.",
            "겨울/폭염 수요, LNG 운송 차질, 유럽 저장률이 실제 원인이다.",
        ]
        item.bullish_thesis = "재고가 줄고 LNG 운송 차질이 이어질 때만 상승 지속성이 높다."
        item.caution = "기온 정상화나 재고 증가가 나오면 급락이 잦다."
    elif cid == "crack_321":
        item.driver_label = "정제마진: 제품 수요가 원유보다 강한지"
        item.cause_reasons = [
            "크랙 스프레드는 원유 자체보다 휘발유/디젤 제품 마진을 본다.",
            "정유사 실적에는 원유 가격보다 크랙 스프레드가 더 직접적이다.",
            "여행/운송 수요가 강하거나 정제설비 차질이 있으면 오른다.",
        ]
        item.bullish_thesis = "크랙이 오르면 정유사 EPS 기대가 붙는다."
        item.caution = "원유만 오르고 제품 수요가 못 따라오면 정유 마진은 꺾인다."
    elif cid in {"gold", "silver"}:
        item.driver_label = "실질금리·달러·안전자산"
        item.cause_reasons = [
            "금/은은 실질금리 하락, 달러 약세, 전쟁/금융불안에서 강해진다.",
            "금은 안전자산, 은은 산업금속 성격도 같이 가진다.",
        ]
        item.bullish_thesis = "금리인하 기대와 지정학 불안이 동시에 있으면 상승 지속성이 높다."
        item.caution = "실질금리 재상승이나 달러 강세가 나오면 눌릴 수 있다."
    elif cid in {"platinum", "palladium", "rhodium"}:
        item.driver_label = "자동차 촉매·남아공/러시아 공급"
        item.cause_reasons = [
            "백금족은 자동차 촉매와 광산 공급 차질이 핵심이다.",
            "EV 전환은 장기 수요를 누르지만, 공급 차질은 단기 급등을 만든다.",
        ]
        item.bullish_thesis = "광산 공급 이슈와 내연기관 촉매 수요가 같이 살아야 지속된다."
        item.caution = "EV 전환/수요 둔화가 나오면 랠리는 짧게 끝날 수 있다."
    elif cid in {"copper", "aluminum", "iron_ore", "hrc_steel"}:
        item.driver_label = "중국 경기 + AI 전력망/인프라 capex"
        item.cause_reasons = [
            "산업금속은 중국 제조/건설 수요와 글로벌 capex를 가장 먼저 반영한다.",
            "구리·알루미늄은 AI 데이터센터 전력망, 케이블, 냉각/서버 소재 수요와 연결된다.",
            "철광석/HRC는 철강 마진과 건설·조선·방산 수요를 같이 봐야 한다.",
        ]
        item.bullish_thesis = "중국 부양, 재고 감소, 전력망/데이터센터 투자가 같이 확인되면 지속성이 높다."
        item.caution = "중국 수요 부진이나 재고 증가가 나오면 원자재 가격만 먼저 꺾일 수 있다."
    elif cid in {"lithium_carbonate", "cobalt", "natural_graphite", "manganese", "nickel_lme"}:
        item.driver_label = "배터리 소재 수급 + EV/ESS 수요"
        item.cause_reasons = [
            "배터리 소재는 EV 판매, ESS 수요, 중국 재고, 광산 공급 증설이 핵심이다.",
            "리튬/니켈/흑연은 배터리 원가와 직접 연결되지만, LFP 전환은 코발트 신호력을 약화시킨다.",
        ]
        item.bullish_thesis = "EV/ESS 수요 회복과 재고 소진이 같이 보여야 진짜 턴어라운드다."
        item.caution = "공급 과잉이나 중국 가격 덤핑이 남아 있으면 급등은 짧다."
    elif cid in {"neodymium", "dysprosium", "terbium", "gallium", "germanium", "indium", "tellurium_bismuth"}:
        item.driver_label = "중국 수출통제 + 방산/반도체 공급망"
        item.cause_reasons = [
            "희토류/특수금속은 실제 산업 필수성이 높고 공급이 중국에 집중된 항목이 많다.",
            "수출통제, 방산 수요, 전력반도체/GaN, 광통신 병목이 가격을 움직인다.",
            "대부분 proxy라 가격보다 정책 뉴스와 재고 이벤트를 같이 확인해야 한다.",
        ]
        item.bullish_thesis = "미중 갈등/수출통제가 강화되면 공급망 프리미엄이 붙을 수 있다."
        item.caution = "정책 완화나 대체 공급 발표가 나오면 테마성 프리미엄은 빠진다."
    elif cid in {"neon", "krypton", "xenon", "helium", "helium_3"}:
        item.driver_label = "반도체/우주 특수가스 공급 병목"
        item.cause_reasons = [
            "특수가스는 spot 공개 가격이 제한되어 차트보다 공급 이벤트가 중요하다.",
            "반도체 레이저/식각, 위성 추진, MRI/극저온 장비에 필수라 공급 차질 때 영향이 크다.",
        ]
        item.bullish_thesis = "전쟁/수출통제/정제설비 차질이 있으면 관련 장비·소재 chain에 프리미엄이 붙는다."
        item.caution = "가격 데이터가 제한적이므로 매매 근거는 반드시 뉴스/공급 계약과 교차 확인해야 한다."
    elif cat == "농산물":
        item.driver_label = "작황·날씨·수출제한"
        item.cause_reasons = [
            "농산물은 날씨, 작황, USDA 수급 전망, 수출 제한이 핵심이다.",
            "식품 기업에는 원가 부담이고, 곡물/비료 chain에는 수혜가 될 수 있다.",
        ]
        item.bullish_thesis = "작황 악화와 수출 제한이 같이 나오면 상승 지속성이 높다."
        item.caution = "날씨 정상화나 풍작 전망이 나오면 급등분은 빠르게 되돌린다."
    elif cat == "화학원료":
        item.driver_label = "에너지 원가 + 중국 가동률 + downstream 수요"
        item.cause_reasons = [
            "화학원료는 천연가스/석탄 같은 원료비와 중국 가동률이 핵심이다.",
            "황산/인산은 리튬 추출·비료·LFP chain과 연결되고, 메탄올/암모니아는 에너지 가격에 민감하다.",
        ]
        item.bullish_thesis = "원료 공급 차질과 downstream 수요가 동시에 확인될 때 지속된다."
        item.caution = "proxy 종목은 실제 spot과 괴리가 커서 신뢰도 배지를 반드시 봐야 한다."
    else:
        item.driver_label = "공급망/수요 proxy"
        item.cause_reasons = [
            "직접 spot 가격 공개가 제한되어 관련 기업/ETF proxy로 감시한다.",
            "실제 매매는 가격보다 수주, 캐파, 공급 계약, 규제 이벤트와 같이 봐야 한다.",
        ]
        item.bullish_thesis = "수요 증가와 공급 병목이 동시에 확인될 때만 지속성이 높다."
        item.caution = "proxy 기반 신호라 원자재 자체 가격과 다를 수 있다."

    if item.is_proxy and item.proxy_for:
        item.cause_reasons = [
            *(item.cause_reasons or []),
            f"주의: 현재 수치는 {item.proxy_for} 직접 가격이 아니라 {item.ticker} proxy 움직임이다.",
        ]

    if d5 >= 6:
        item.cause_reasons = [*(item.cause_reasons or []), f"단기 5일 {d5:+.1f}%라 원인이 확인되지 않으면 추격 위험이 크다."]
    if d60 >= 18:
        item.cause_reasons = [*(item.cause_reasons or []), f"3개월 {d60:+.1f}% 상승은 단순 하루 이슈보다 구조적 수요/공급 변화를 의심할 구간이다."]


def fetch_feed(force: bool = False) -> list[CommodityFeedItem]:
    """52개 원자재 매트릭스용 가격 feed (캐시 30분)."""
    global _FEED_CACHE
    now = time.time()
    if not force and _FEED_CACHE and (now - _FEED_CACHE[0] < _CACHE_TTL):
        return _FEED_CACHE[1]

    items: list[CommodityFeedItem] = []

    # yfinance direct/proxy
    for spec in COMMODITY_FEED:
        item = _build_item({
            **spec,
            "source": "yfinance",
            "source_type": "yfinance",
            "source_url": f"https://finance.yahoo.com/quote/{spec['ticker']}",
            "coverage_status": "proxy" if spec.get("is_proxy") else "live",
            "confidence": 65 if spec.get("is_proxy") else 82,
            "frequency": "daily",
        })
        try:
            hist = StockDataService.get_stock_history(spec["ticker"], period="6mo")
            _apply_history(item, hist)
        except Exception as e:
            item.error = str(e)[:100]
            item.coverage_status = "stale_fallback"
            item.confidence = min(item.confidence, 30)
            _classify(item)
        items.append(item)

    # computed feeds
    for spec in COMPUTED_FEED:
        items.append(_computed_crack_321(spec))

    # external/delayed/proxy feeds: keep every spec visible; use ticker proxy when available.
    for spec in EXTERNAL_FEED:
        item = _build_item(spec, fetchable=True)
        if item.ticker:
            try:
                hist = StockDataService.get_stock_history(item.ticker, period="6mo")
                _apply_history(item, hist)
                if item.is_proxy and item.proxy_for:
                    item.timing_reasons = [
                        *(item.timing_reasons or []),
                        f"{item.proxy_for} 직접 가격 대신 {item.ticker} proxy 사용",
                    ][:4]
            except Exception as e:
                item.error = str(e)[:100]
                item.coverage_status = "stale_fallback"
                item.confidence = min(item.confidence, 28)
                item.risk_notes = ["proxy 가격 수집 실패: 소스 링크 확인 필요"]
                _classify(item)
        else:
            item.fetchable = True
            item.chartable = False
            item.timing_action = "소스 확인"
            item.timing_score = 0
            item.trend_label = "가격 제한"
            item.signal_type = "source_only"
            item.timing_reasons = [item.note or "공개 가격 제한: 소스 이벤트 확인"]
            item.risk_notes = ["차트/정량 판정 불가: 공개 spot 데이터 제한"]
            _assign_cause(item)
            _classify_strategic_watch(item)
        items.append(item)

    _FEED_CACHE = (now, items)
    return items


def get_movers(top_n: int = 5) -> dict[str, list[dict[str, Any]]]:
    """급등/급락 TOP N — 상단 알림 카드용."""
    items = fetch_feed()
    # 급등 우선순위: Z-score 절대값 > daily_pct
    surges = sorted(
        [i for i in items if i.is_surge],
        key=lambda x: (x.zscore_60d or 0, x.change_pct_1d or 0),
        reverse=True,
    )[:top_n]
    plunges = sorted(
        [i for i in items if i.is_plunge],
        key=lambda x: (x.zscore_60d or 0, x.change_pct_1d or 0),
    )[:top_n]
    uptrends = sorted(
        [i for i in items if i.is_multi_month_uptrend and not i.is_surge],
        key=lambda x: (x.change_pct_120d or 0, x.change_pct_60d or 0),
        reverse=True,
    )[:top_n]
    downtrends = sorted(
        [i for i in items if i.is_multi_month_downtrend and not i.is_plunge],
        key=lambda x: (x.change_pct_120d or 0, x.change_pct_60d or 0),
    )[:top_n]
    return {
        "surges": [asdict(i) for i in surges],
        "plunges": [asdict(i) for i in plunges],
        "uptrends": [asdict(i) for i in uptrends],
        "downtrends": [asdict(i) for i in downtrends],
    }


def feed_as_dicts() -> list[dict[str, Any]]:
    return [asdict(i) for i in fetch_feed()]
