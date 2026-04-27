"""Macro 4-page API endpoints.

상응하는 명세 문서:
- wiki/macro/01-commodities.md (52개 원자재)
- wiki/macro/02-indicators.md (27섹터 × 178개 선행지표)
- wiki/macro/03-outlook.md (8개 거시 차원 33개 지표 + 9개 시나리오)
- wiki/macro/04-value-chain.md (27섹터 × 360+ KR 종목 Tier 0~5)

두 가지 데이터 채널:
1. JSON 엔드포인트 (이 파일의 stub) — 핵심 시그널 카드용
2. /api/macro/page/{name} — wiki 원본 markdown 그대로 read (프론트에서 react-markdown + mermaid 렌더)
"""

from fastapi import APIRouter, HTTPException
from pathlib import Path
from typing import Any

from services.macro_commodity import fetch_feed, get_movers, feed_as_dicts
from services.macro_sentiment import all_sector_sentiments, top_sectors
from services.macro_indicators import macro_as_dicts
from services.macro_regime import synthesize_sectors
from services.macro_news import scan_macro_news
from services.commodity_regime_history import (
    load_state as load_regime_state,
    RECOMMENDATION_MATRIX as REGIME_RECOMMENDATION,
)
from services.value_chain_parser import parse_value_chain

router = APIRouter(prefix="/api/macro", tags=["macro"])

# wiki/macro/ 위치 — backend 기준 상위 폴더
_WIKI_MACRO_DIR = Path(__file__).resolve().parent.parent.parent / "wiki" / "macro"

_WIKI_PAGE_MAP = {
    "commodities": "01-commodities.md",
    "indicators": "02-indicators.md",
    "outlook": "03-outlook.md",
    "value-chain": "04-value-chain.md",
}


# ============================================================
# 1. /api/macro/commodities — 원자재 모니터링 매트릭스
# ============================================================

_COMMODITIES_STUB: list[dict[str, Any]] = [
    {
        "id": "crude_wti",
        "name": "WTI 원유",
        "category": "에너지",
        "unit": "USD/barrel",
        "ticker": "CL=F",
        "primary_effects": [
            {"sector": "수소/에너지", "direction": "수혜",
             "tickers_kr": ["SK이노베이션(096770)", "S-Oil(010950)", "GS(078930)"],
             "tickers_us": ["XOM", "CVX", "VLO", "MPC"],
             "mechanism": "유가↑ → 정유 크랙스프레드 확대 → 정유사 단기 EPS↑"},
            {"sector": "우주항공/방산", "direction": "수혜(지정학)",
             "tickers_kr": ["한화에어로스페이스(012450)"],
             "tickers_us": ["LMT", "RTX", "NOC"],
             "mechanism": "유가 급등 = 통상 지정학 동반 → 방산 발주 증가"},
        ],
    },
    {
        "id": "copper",
        "name": "구리",
        "category": "산업금속",
        "unit": "USD/lb",
        "ticker": "HG=F",
        "primary_effects": [
            {"sector": "AI/반도체", "direction": "수요proxy",
             "tickers_kr": ["LS ELECTRIC(010120)", "대한전선(001440)"],
             "tickers_us": ["FCX", "SCCO"],
             "mechanism": "AI 데이터센터 케이블/전력 인프라 폭증 → 구리 수요 6-12개월 선행"},
        ],
    },
    {
        "id": "uranium_u3o8",
        "name": "우라늄 U3O8",
        "category": "에너지",
        "unit": "USD/lb",
        "ticker": None,
        "primary_effects": [
            {"sector": "SMR/원자력", "direction": "수혜",
             "tickers_kr": ["두산에너빌리티(034020)", "한전기술(052690)"],
             "tickers_us": ["CCJ", "URA", "URNM", "NNE", "OKLO", "SMR"],
             "mechanism": "우라늄 spot↑ → 채굴사 마진 확대, SMR 발주 사이클 trigger"},
        ],
    },
    {
        "id": "lithium_carbonate",
        "name": "탄산리튬",
        "category": "희소금속",
        "unit": "USD/ton",
        "ticker": None,
        "primary_effects": [
            {"sector": "이차전지", "direction": "cost_pressure",
             "tickers_kr": ["에코프로비엠(247540)", "포스코퓨처엠(003670)", "엘앤에프(066970)"],
             "tickers_us": ["ALB", "SQM", "LAC"],
             "mechanism": "리튬↑ → 양극재 BOM 원가↑ → 마진 압박/판가 전가"},
        ],
    },
    {
        "id": "iridium",
        "name": "이리듐",
        "category": "양자/방산 특수재",
        "unit": "USD/oz",
        "ticker": None,
        "is_hidden_bottleneck": True,
        "primary_effects": [
            {"sector": "수소/에너지", "direction": "cost_pressure",
             "tickers_kr": ["효성중공업(298040)", "두산퓨얼셀(336260)"],
             "tickers_us": ["PLUG", "BE", "BLDP"],
             "mechanism": "PEM 전해조 핵심 촉매. 연 7-8톤 생산 vs 1GW PEM ~1톤 필요. 그린수소 진짜 병목"},
        ],
    },
    {
        "id": "helium_3",
        "name": "헬륨-3",
        "category": "양자/방산 특수재",
        "unit": "USD/L",
        "ticker": None,
        "is_hidden_bottleneck": True,
        "primary_effects": [
            {"sector": "양자컴퓨팅", "direction": "cost_pressure_severe",
             "tickers_kr": [],
             "tickers_us": ["IONQ", "IBM", "RGTI"],
             "mechanism": "초저온 dilution refrigerator 필수. 민간시장 전무·DOE 배급제. 양자 H/W 캐파의 hidden moat"},
        ],
    },
]

_COMMODITIES_INSIGHTS = {
    "top_signal_kr": [
        "JKM 천연가스 — 한전/KOGAS 분기실적 직결",
        "우라늄(U3O8) — 두산에너빌리티/한전기술 SMR 1차 lead",
        "구리 — LS ELECTRIC/대한전선 AI 데이터센터 6-12개월 선행",
    ],
    "hidden_bottlenecks": [
        "헬륨-3 — 양자컴퓨팅 최대 병목 (DOE 배급제)",
        "이리듐 — 그린수소 진짜 병목 (시장 인지도 낮음)",
        "GLP-1 펩타이드 — 펩트론(217340) CDMO 캐파",
        "갈륨/게르마늄 중국 통제 — RFHIC·대한광통신 수혜",
    ],
}


@router.get("/commodities")
async def get_commodities() -> dict[str, Any]:
    """52개 원자재 모니터링 매트릭스. wiki/macro/01-commodities.md 기반.

    - items: 명세 기반 영향 매핑 카드 (stub)
    - feed: 실시간 가격 + Z-score + 급등 분류 (yfinance, 캐시 30분)
    """
    feed = feed_as_dicts()
    return {
        "status": "live",
        "total_commodities": len(feed),
        "categories": ["에너지", "산업금속", "귀금속", "희소금속", "반도체 가스",
                       "양자/방산 특수재", "농산물", "화학원료", "바이오 원료"],
        "items": _COMMODITIES_STUB,
        "insights": _COMMODITIES_INSIGHTS,
        "feed": feed,
        "movers": get_movers(top_n=5),
    }


@router.get("/commodities/movers")
async def get_commodity_movers(top_n: int = 5) -> dict[str, Any]:
    """급등/급락 TOP N — 상단 알림 카드용."""
    return get_movers(top_n=top_n)


@router.get("/commodities/feed")
async def get_commodity_feed() -> list[dict[str, Any]]:
    """전체 실시간 feed (가격 + Z-score)."""
    return feed_as_dicts()


# ============================================================
# 1-bis. /api/macro/regime — 5년 history 기반 regime 분석
# ============================================================

@router.get("/regime")
async def get_regime_state() -> dict[str, Any]:
    """commodity_regime_history.run_daily_update()의 결과 (data/commodity_regime_state.json) 반환.

    명세: wiki/macro/05-regime-scoring.md
    매일 KST 06:00 자동 갱신. 25개 항목 (22 직접 + 3 비율).
    """
    state = load_regime_state()
    items: dict[str, Any] = state.get("items", {}) or {}

    distribution: dict[str, list[dict[str, Any]]] = {k: [] for k in REGIME_RECOMMENDATION}
    changed_today: list[dict[str, Any]] = []

    for iid, it in items.items():
        regime = it.get("current_regime")
        rec = REGIME_RECOMMENDATION.get(regime, {})
        enriched = {
            **it,
            "recommendation": rec.get("action"),
            "recommendation_note": rec.get("note"),
        }
        if regime in distribution:
            distribution[regime].append(enriched)
        if it.get("regime_change"):
            changed_today.append(enriched)

    # 정렬: 백분위 높은 순
    for k in distribution:
        distribution[k].sort(key=lambda x: -((x.get("metrics") or {}).get("pct_5y") or 0))

    return {
        "updated": state.get("updated"),
        "total_items": len(items),
        "regime_changes_today": len(changed_today),
        "distribution": distribution,
        "changed_today": changed_today,
        "items": list(items.values()),
        "errors_last_run": state.get("errors_last_run") or [],
        "recommendation_matrix": REGIME_RECOMMENDATION,
    }


# ============================================================
# 2. /api/macro/indicators — 27섹터 × 178개 선행지표
# ============================================================

_SECTORS = [
    # Phase 1 core 8
    {"id": "ai_semi", "name": "AI/반도체", "phase": 1, "indicator_count": 8},
    {"id": "robotics", "name": "로봇/자동화", "phase": 1, "indicator_count": 7},
    {"id": "smr_nuclear", "name": "SMR/원자력", "phase": 1, "indicator_count": 6},
    {"id": "cybersec", "name": "사이버보안", "phase": 1, "indicator_count": 7},
    {"id": "aerospace", "name": "우주항공/방산", "phase": 1, "indicator_count": 6},
    {"id": "biotech", "name": "생명공학", "phase": 1, "indicator_count": 6},
    {"id": "quantum", "name": "양자컴퓨팅", "phase": 1, "indicator_count": 6},
    {"id": "hydrogen_energy", "name": "수소/에너지", "phase": 1, "indicator_count": 7},
    # Phase 2 한국 제조 6
    {"id": "battery", "name": "이차전지", "phase": 2, "indicator_count": 7},
    {"id": "ev", "name": "전기차 완성차", "phase": 2, "indicator_count": 7},
    {"id": "ev_materials", "name": "EV 소재/부품", "phase": 2, "indicator_count": 6},
    {"id": "shipbuilding", "name": "조선", "phase": 2, "indicator_count": 7},
    {"id": "steel", "name": "철강/비철", "phase": 2, "indicator_count": 7},
    {"id": "display", "name": "디스플레이", "phase": 2, "indicator_count": 7},
    # Phase 2 성장형 3
    {"id": "platform", "name": "인터넷 플랫폼", "phase": 2, "indicator_count": 6},
    {"id": "gaming", "name": "게임", "phase": 2, "indicator_count": 7},
    {"id": "k_content", "name": "K-콘텐츠/엔터", "phase": 2, "indicator_count": 6},
    # Phase 2 소비재 4
    {"id": "cosmetics", "name": "화장품", "phase": 2, "indicator_count": 7},
    {"id": "food", "name": "음식료", "phase": 2, "indicator_count": 7},
    {"id": "retail", "name": "유통/이커머스", "phase": 2, "indicator_count": 6},
    {"id": "apparel", "name": "의류/패션", "phase": 2, "indicator_count": 5},
    # Phase 2 인프라 4
    {"id": "construction", "name": "건설/건자재", "phase": 2, "indicator_count": 7},
    {"id": "finance", "name": "금융", "phase": 2, "indicator_count": 7},
    {"id": "telecom", "name": "통신/유틸리티", "phase": 2, "indicator_count": 6},
    {"id": "holding_reit", "name": "지주사/리츠", "phase": 2, "indicator_count": 6},
    # Phase 2 알파 2
    {"id": "medical_device", "name": "의료기기/미용", "phase": 2, "indicator_count": 7},
    {"id": "hotel_leisure", "name": "호텔/레저/여행", "phase": 2, "indicator_count": 7},
]

_INDICATORS_FEATURED: list[dict[str, Any]] = [
    {
        "id": "kr_motie_semi_export",
        "sector_id": "ai_semi",
        "sector_name": "AI/반도체",
        "name": "한국 산자부 월간 반도체 수출",
        "what": "한국 메모리/시스템반도체 월별 수출액(달러), YoY/MoM",
        "lead_time": "SK하이닉스/삼성 분기 매출 30-60일 선행",
        "source": {"name": "MOTIE 보도자료", "url": "https://www.motie.go.kr/", "free": True},
        "tickers_kr": ["삼성전자(005930)", "SK하이닉스(000660)", "한미반도체(042700)"],
        "tickers_us": ["NVDA", "MU", "AVGO", "TSM"],
        "is_top_signal": True,
    },
    {
        "id": "asml_quarterly_bookings",
        "sector_id": "ai_semi",
        "sector_name": "AI/반도체",
        "name": "ASML 분기 신규수주 (EUV book-to-bill)",
        "what": "ASML 분기 신규수주액(€), EUV 비중. backlog 2027년까지 booked",
        "lead_time": "fab 양산 12-24개월 선행",
        "source": {"name": "ASML Press Releases", "url": "https://www.asml.com/", "free": True},
        "tickers_kr": ["삼성전자(005930)", "SK하이닉스(000660)"],
        "tickers_us": ["ASML", "TSM", "INTC", "NVDA"],
        "is_top_signal": True,
    },
    {
        "id": "cisa_kev_additions",
        "sector_id": "cybersec",
        "sector_name": "사이버보안",
        "name": "CISA KEV 카탈로그 신규 등록",
        "what": "Known Exploited Vulnerabilities 주간/월간 신규 CVE",
        "lead_time": "보안업체 매출 가이던스 4-8주 선행",
        "source": {"name": "CISA KEV", "url": "https://www.cisa.gov/known-exploited-vulnerabilities-catalog", "free": True, "api": True},
        "tickers_kr": ["안랩(053800)", "이글루(067920)"],
        "tickers_us": ["CRWD", "PANW", "FTNT", "S", "ZS"],
        "is_top_signal": True,
    },
    {
        "id": "pjm_dc_queue",
        "sector_id": "smr_nuclear",
        "sector_name": "SMR/원자력",
        "name": "PJM 데이터센터 interconnection queue",
        "what": "ISO 송전망에 신청한 데이터센터 부하 누적 MW",
        "lead_time": "SMR/원전 PPA 결정 12-18개월 선행",
        "source": {"name": "PJM Queue", "url": "https://www.pjm.com/planning/services-requests/interconnection-queues", "free": True},
        "tickers_kr": ["두산에너빌리티(034020)", "한전기술(052690)"],
        "tickers_us": ["CEG", "VST", "SMR", "OKLO", "NNE", "BWXT"],
        "is_top_signal": True,
    },
    {
        "id": "steamdb_ccu",
        "sector_id": "gaming",
        "sector_name": "게임",
        "name": "SteamDB 동시접속자 (CCU)",
        "what": "Valve 공개 API 기반 실시간 PC 게임 CCU",
        "lead_time": "분기 매출 4-12주 선행, KRAFTON PUBG R²>0.85",
        "source": {"name": "SteamDB", "url": "https://steamdb.info/", "free": True, "api": True},
        "tickers_kr": ["크래프톤(259960)", "엔씨소프트(036570)", "시프트업(462870)"],
        "tickers_us": ["TTWO", "EA"],
        "is_top_signal": True,
    },
    {
        "id": "kfda_medical_device_approval",
        "sector_id": "medical_device",
        "sector_name": "의료기기/미용",
        "name": "식약처 의료기기 신규 인허가",
        "what": "월간 신규 품목허가 + FDA 510(k)/PMA 한국기업 승인",
        "lead_time": "장비 매출 +2-4분기, 소모품 +4-8분기 (2단계 lead)",
        "source": {"name": "식약처 의료기기 정보", "url": "https://emed.mfds.go.kr/", "free": True},
        "tickers_kr": ["클래시스(214150)", "비올(335890)", "제이시스메디칼(287410)"],
        "tickers_us": [],
        "is_top_signal": True,
    },
]


@router.get("/indicators")
async def get_indicators(sector_id: str | None = None) -> dict[str, Any]:
    """27섹터 × 178개 선행지표. wiki/macro/02-indicators.md 기반.

    각 섹터마다 commodity feed 기반 sentiment 자동 계산 (bullish/bearish/neutral).
    """
    sentiments = {s["sector_id"]: s for s in all_sector_sentiments()}
    sectors_with_sentiment = []
    for sec in _SECTORS:
        sent = sentiments.get(sec["id"], {"sentiment": "neutral", "score": 0,
                                           "bullish_signals": [], "bearish_signals": [],
                                           "data_coverage": "no_data"})
        sectors_with_sentiment.append({**sec, "live_sentiment": sent})

    return {
        "status": "live",
        "total_sectors": 27,
        "total_indicators": 178,
        "phases": {"phase_1": 53, "phase_2": 125},
        "sectors": sectors_with_sentiment,
        "featured": _INDICATORS_FEATURED if not sector_id else [
            i for i in _INDICATORS_FEATURED if i["sector_id"] == sector_id
        ],
        "top_sectors": top_sectors(top_n=3),
    }


# ============================================================
# 3. /api/macro/outlook — 거시 전망
# ============================================================

_MACRO_DIMENSIONS = [
    {"id": "cycle", "name": "비즈니스 사이클",
     "key_indicators": ["Conference Board LEI", "ECRI WLI", "INDPRO", "ICSA", "BOK BSI"]},
    {"id": "monetary", "name": "통화정책 / 금리",
     "key_indicators": ["Fed Funds Rate", "CME FedWatch", "10Y-2Y 스프레드", "한국은행 기준금리", "10Y TIPS"]},
    {"id": "bond", "name": "채권시장 시그널",
     "key_indicators": ["MOVE Index", "HY OAS", "IG OAS", "한국 회사채 스프레드"]},
    {"id": "liquidity", "name": "글로벌 유동성",
     "key_indicators": ["Fed 대차대조표 H.4.1", "ECB/BOJ 대차대조표", "글로벌 M2", "DXY", "USD/KRW", "CNH/USD"]},
    {"id": "volatility", "name": "변동성 / 위험선호",
     "key_indicators": ["VIX", "VVIX", "SKEW", "VKOSPI", "Citi CESI"]},
    {"id": "geopolitics", "name": "지정학 / 정책",
     "key_indicators": ["GPR Index", "ACLED", "미중 관세", "EU CBAM", "IRA/CHIPS Act"]},
    {"id": "trade", "name": "글로벌 무역 / 운송",
     "key_indicators": ["BDI", "SCFI", "WCI", "한국 수출 잠정치"]},
    {"id": "demographics", "name": "인구구조 / 장기 트렌드",
     "key_indicators": ["출산율", "노동인구 추세", "AI capex 사이클", "탈탄소"]},
]

_SCENARIOS = [
    {"id": "goldilocks", "name": "골디락스 (성장+저금리)",
     "triggers": ["LEI ↑", "10Y ↓", "DXY ↓"],
     "favorable": ["AI/반도체", "로봇", "양자컴퓨팅", "이차전지"],
     "unfavorable": ["우주항공/방산", "사이버보안"]},
    {"id": "stagflation", "name": "스태그플레이션",
     "triggers": ["LEI ↓", "원유 ↑", "DXY ↑"],
     "favorable": ["수소/에너지", "우주항공/방산", "철강"],
     "unfavorable": ["AI/반도체", "이차전지"]},
    {"id": "recession", "name": "침체",
     "triggers": ["LEI 6M < -4.5%", "신용 스프레드 ↑"],
     "favorable": ["생명공학(방어)", "사이버보안", "통신/유틸리티"],
     "unfavorable": ["AI/반도체", "조선", "건설"]},
    {"id": "recovery_early", "name": "회복 초기",
     "triggers": ["LEI 양전환", "Fed 금리인하"],
     "favorable": ["AI/반도체", "로봇", "SMR/원자력", "EV 소재"],
     "unfavorable": ["방산"]},
    {"id": "geopolitical_crisis", "name": "중동 전쟁/호르무즈 리스크",
     "triggers": ["GPR ↑", "원유 ↑", "DXY ↑"],
     "favorable": ["우주항공/방산", "조선", "수소/에너지", "SMR/원자력", "사이버보안"],
     "unfavorable": ["호텔/레저/여행", "인터넷 플랫폼", "K-콘텐츠", "화장품", "EV/이차전지"]},
    {"id": "ai_capex_acceleration", "name": "AI capex 가속",
     "triggers": ["빅테크 capex ↑", "ASML book-to-bill ↑"],
     "favorable": ["AI/반도체", "SMR/원자력 (전력수요)", "이차전지 (데이터센터)"],
     "unfavorable": []},
    {"id": "yuan_devaluation", "name": "미중 갈등/디커플링",
     "triggers": ["CNH/USD ↑", "수출통제 강화"],
     "favorable": ["사이버보안", "방산", "국내 반도체 소부장 대체"],
     "unfavorable": ["중국 노출 소비재", "디스플레이", "K-콘텐츠"]},
    {"id": "boj_carry_unwind", "name": "BOJ 캐리 청산",
     "triggers": ["JPY 급격 강세", "글로벌 변동성 ↑"],
     "favorable": ["방어주"],
     "unfavorable": ["성장주 전반"]},
    {"id": "expansion_late", "name": "확장 후기 / 인플레 재점화",
     "triggers": ["LEI ↑ but 둔화", "유가 ↑", "임금 ↑"],
     "favorable": ["수소/에너지", "철강"],
     "unfavorable": ["성장주"]},
]


@router.get("/outlook")
async def get_outlook() -> dict[str, Any]:
    """거시 전망 + 시나리오 + 종합 섹터 추천 (라이브).

    - live_indicators: VIX·10Y·DXY·KRW·KOSPI·S&P·NASDAQ 등 실시간
    - active_scenarios: 룰 기반 자동 감지 (강도 0~1)
    - synthesis: commodity sentiment + 시나리오 영향 → 27섹터 종합 점수
    """
    syn = synthesize_sectors()
    return {
        "status": "live",
        "live_indicators": macro_as_dicts(),
        "breaking_issues": scan_macro_news(),
        "current_events": syn["current_events"],
        "active_scenarios": syn["active_scenarios"],
        "synthesis": {
            "top_sectors": syn["top_sectors"],
            "bottom_sectors": syn["bottom_sectors"],
            "all_sectors": syn["all_sectors"],
        },
        "current_regime": {
            "as_of": "2026-04-25",
            "lei_6m_change": -1.3,
            "fed_target_range": "3.50-3.75%",
            "hy_oas": 2.85,
            "vkospi": 62.97,
            "summary": "감속 둔화 중 (직전 -2.6% 대비 개선), HY OAS 매우 낮음 (risk-on), VKOSPI 사상 최초 60 돌파 (중동 지정학 risk-off)",
        },
        "dimensions": _MACRO_DIMENSIONS,
        "scenarios": _SCENARIOS,
        "policy_alerts": [
            "EU CBAM 2026-01-01 본격 발효 — 철강·알루미늄 단가 상승, 수소 수혜",
            "Trump 행정명령 IRA 동결 (2025-01) — 한국 수소/SMR/바이오 일부 피해",
        ],
    }


# ============================================================
# 4. /api/macro/value-chain — Value Chain
# ============================================================

_VALUE_CHAIN_FEATURED = [
    {
        "sector_id": "ai_semi",
        "sector_name": "AI 데이터센터 밸류체인",
        "tiers": [
            {"level": 0, "name": "Compute · Hyperscalers / AI Cloud", "players": ["Microsoft( MSFT )", "Amazon( AMZN )", "Alphabet( GOOGL )", "Oracle( ORCL )", "Meta( META )", "CoreWeave( CRWV )"]},
            {"level": 1, "name": "Semiconductors · Memory / GPU / ASIC", "players": ["NVIDIA( NVDA )", "AMD( AMD )", "Broadcom( AVGO )", "Micron( MU )", "TSMC( TSM )", "SK하이닉스(000660)", "삼성전자(005930)"]},
            {"level": 2, "name": "IT Infrastructure · Servers / Networking / Storage", "players": ["Dell( DELL )", "Super Micro( SMCI )", "Arista( ANET )", "Cisco( CSCO )", "Marvell( MRVL )", "NetApp( NTAP )", "Pure Storage( PSTG )"]},
            {"level": 3, "name": "Data Centers · Developers / Operators", "players": ["Equinix( EQIX )", "Digital Realty( DLR )", "Vantage", "QTS", "데이터센터 REITs"]},
            {"level": 4, "name": "Industrial Equipment · Power / Cooling", "players": ["Vertiv( VRT )", "Schneider Electric( SBGSY )", "Eaton( ETN )", "ABB( ABBNY )", "Siemens( SIEGY )", "LS ELECTRIC(010120)", "HD현대일렉트릭(267260)"], "is_korean_alpha": True},
            {"level": 5, "name": "Energy · Nuclear / Renewables / Gas / Batteries", "players": ["Constellation( CEG )", "Vistra( VST )", "Cameco( CCJ )", "GE Vernova( GEV )", "Exxon Mobil( XOM )", "Chevron( CVX )", "두산에너빌리티(034020)", "LG에너지솔루션(373220)"], "is_korean_alpha": True},
        ],
        "hidden_alpha": "AI capex는 GPU만 보는 게 아니라 전력·냉각·네트워킹·데이터센터 운영까지 같이 봐야 함. 한국 알파는 HBM(하이닉스/삼성), 전력기기(LS ELECTRIC/HD현대일렉트릭), 원전 기자재(두산에너빌리티)에 집중.",
    },
    {
        "sector_id": "battery",
        "sector_name": "이차전지",
        "tiers": [
            {"level": 0, "name": "EV OEM", "players": ["Tesla", "BYD", "현대차(005380)", "기아(000270)"]},
            {"level": 1, "name": "셀 제조", "players": ["LG에너지솔루션(373220)", "삼성SDI(006400)", "SK이노베이션(096770)", "CATL", "Panasonic"]},
            {"level": 4, "name": "양극재 (한국 알파)", "players": ["에코프로비엠(247540)", "포스코퓨처엠(003670)", "엘앤에프(066970)"], "is_korean_alpha": True},
            {"level": 4, "name": "분리막", "players": ["SKIET(361610)", "더블유씨피(393890)"], "is_korean_alpha": True},
            {"level": 4, "name": "전해액", "players": ["엔켐(348370)", "동화기업(025900)"], "is_korean_alpha": True},
            {"level": 5, "name": "광물", "players": ["리튬", "코발트", "니켈", "망간", "흑연"]},
        ],
        "hidden_alpha": "SKIET — IRA FEOC 중국 분리막 배제 시 ASP 프리미엄. 시장 저평가",
    },
    {
        "sector_id": "medical_device",
        "sector_name": "의료기기/미용",
        "tiers": [
            {"level": 0, "name": "수요 (피부과·미용 클리닉)", "players": ["한·중·일·미·동남아"]},
            {"level": 1, "name": "기기 제조", "players": ["클래시스(214150) 슈링크/올리지오", "비올(335890) 실펌X", "제이시스메디칼(287410)"], "is_korean_alpha": True},
            {"level": 1, "name": "톡신·필러", "players": ["메디톡스(086900)", "휴젤(145020)", "파마리서치(214450)"], "is_korean_alpha": True},
        ],
        "hidden_alpha": "클래시스·비올·제이시스 자체 OEM 영업이익률 40-55%. FDA 510(k) 승인이 미국 진출 trigger",
    },
]

_HIDDEN_ALPHA_TOP = [
    {"company": "솔브레인·한솔케미칼", "tickers": ["357780", "014680"],
     "thesis": "HBM TSV 식각액 글로벌 1위, NVDA 어닝 leading (방향 확인, 시차 추가 검증 中)"},
    {"company": "더블유씨피", "tickers": ["393890"],
     "thesis": "분리막 알파. KB +82% (11K→20K), 다올 58K. SKIET 대비 신규 베팅 (FEOC base film 면제 후)"},
    {"company": "알테오젠", "tickers": ["196170"],
     "thesis": "SC 제형 변경 IP. 2025-09 FDA + 2025-11 EU 키트루다 SC 승인 완료 → 머크 로열티 본격화"},
    {"company": "에스티팜", "tickers": ["237690"],
     "thesis": "올리고뉴클레오타이드 글로벌 2위 (매출 +21%, OP +99%, 올리고 84%)"},
    {"company": "삼성바이오로직스", "tickers": ["207940"],
     "thesis": "CDMO 글로벌 1위 capa. 2025년 수주 6조 돌파, 5공장 78.4만L 가동"},
    {"company": "펩트론", "tickers": ["087010"],
     "thesis": "⚠️ 옵션 가치 — LLY 본계약 미체결, 평가기간 24개월 연장 (2025-12). 실적 미반영"},
    {"company": "에스비비테크", "tickers": ["389500"],
     "thesis": "⚠️ thematic — Tesla Optimus 공급 미확인 (공식: 中 Green Harmonic), 2025 당기순손실 -94.5억"},
    {"company": "코스맥스·한국콜마", "tickers": ["192820", "161890"],
     "thesis": "화장품 ODM, e.l.f./Rare Beauty OEM, K-beauty + 인디 이중 레버리지"},
    {"company": "CEG·VST (US)", "tickers": ["CEG", "VST"],
     "thesis": "원전 운용사 (AI DC 전력 proxy). MS/JPM 상향, AI capex 사이클 직접 베타"},
    {"company": "다우데이타", "tickers": ["032190"],
     "thesis": "키움증권 wrapper, 거래대금 폭발 시 더블 레버리지"},
    {"company": "삼성물산", "tickers": ["028260"],
     "thesis": "상속 + 삼바 43% + 밸류업 트리플 트리거, NAV 50%+ 디스카운트"},
]


@router.get("/value-chain")
async def get_value_chain(sector_id: str | None = None) -> dict[str, Any]:
    """27섹터 × Tier 0~5 Value Chain. wiki/macro/04-value-chain.md를 런타임 파싱하여 노출.

    각 섹터: tiers (Mermaid에서 추출한 KR/US 종목 매핑) + hidden_alpha + raw mermaid 다이어그램.
    """
    parsed = parse_value_chain()
    if sector_id:
        parsed = [s for s in parsed if s["sector_id"] == sector_id]

    total_kr = sum(sum(len(t["players_kr"]) for t in s["tiers"]) for s in parsed)
    total_us = sum(sum(len(t["players_us"]) for t in s["tiers"]) for s in parsed)

    return {
        "status": "mapped",
        "source": "wiki/macro/04-value-chain.md (parsed)",
        "total_sectors": len(parsed),
        "total_kr_stocks": total_kr,
        "total_us_stocks": total_us,
        "sectors": parsed,
        "hidden_alpha_top": _HIDDEN_ALPHA_TOP,
        "warnings": [
            "Mermaid 다이어그램 파싱 기반 — 일부 종목명·역할 텍스트는 wiki 원문 참조 권장 (/api/macro/page/value-chain)",
        ],
    }


# ============================================================
# 5. /api/macro/page/{name} — wiki 원본 markdown read
# ============================================================

@router.get("/page/{name}")
async def get_wiki_page(name: str) -> dict[str, Any]:
    """wiki/macro/*.md 원본 markdown 그대로 반환.
    프론트에서 react-markdown + mermaid로 렌더.
    """
    if name not in _WIKI_PAGE_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown page: {name}")

    file_path = _WIKI_MACRO_DIR / _WIKI_PAGE_MAP[name]
    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"File not found: {file_path}")

    try:
        content = file_path.read_text(encoding="utf-8")
        return {
            "name": name,
            "filename": _WIKI_PAGE_MAP[name],
            "content": content,
            "size_bytes": len(content.encode("utf-8")),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Read failed: {e}")
