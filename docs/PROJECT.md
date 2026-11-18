# 미래 먹거리 주식 분석기 (Future Growth Stock Analyzer)

## 프로젝트 개요
개인 투자 분석 플랫폼. 8개 미래 성장 섹터의 Top 5 종목을 기술적/펀더멘탈 분석 후 매수/매도 의견을 자동 생성한다.

## 기술 스택
- **Frontend**: React 18 + TypeScript + Vite + Tailwind CSS v4 + Recharts
- **Backend**: Python FastAPI + yfinance + pandas + numpy
- **데이터**: yfinance (실시간 주가/재무), Naver/Google News RSS (뉴스)

---

## 프로젝트 구조

```
Stock/
├── frontend/              # React SPA (Vite)
│   ├── src/
│   │   ├── api/client.ts           # 백엔드 API 호출 함수들
│   │   ├── types/index.ts          # TypeScript 타입 정의
│   │   ├── data/sectors.ts         # 8개 섹터 정적 데이터 (종목, 리스크, 지표)
│   │   ├── components/
│   │   │   ├── SectorMindMap.tsx    # 마인드맵 메인 페이지 (/)
│   │   │   ├── SectorDetailPage.tsx # 섹터 상세 페이지 (/sector/:id)
│   │   │   └── Layout.tsx          # 앱 레이아웃 (헤더, full-bleed 처리)
│   │   └── App.tsx                 # 라우터 설정
│   └── vite.config.ts              # Vite 설정 (proxy → :8000)
│
├── backend/               # FastAPI 서버
│   ├── main.py                     # FastAPI 앱 진입점
│   ├── api/
│   │   ├── analysis.py             # 분석 API (차트, 실적, 패턴, 예측, 체크리스트)
│   │   ├── sectors.py              # 섹터 API
│   │   └── news.py                 # 뉴스 API
│   ├── services/
│   │   ├── stock_data.py           # yfinance 주가 데이터 서비스
│   │   ├── technical_analysis.py   # 기술적 분석 서비스 (RSI, MACD, BB, SMA)
│   │   ├── commodity_data.py       # 원자재 가격 서비스
│   │   └── news_crawler.py         # 뉴스 크롤링 서비스
│   └── models/schemas.py           # Pydantic 모델
│
└── docs/                  # 문서
    └── PROJECT.md          # 이 파일
```

---

## 백엔드 API 엔드포인트

### 분석 API (`/api/analysis/`)

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/analysis/{ticker}` | 기본 기술적 분석 (RSI, MACD, BB, SMA, 매수/매도 신호) |
| `GET /api/analysis/{ticker}/chart-data?period=3mo` | OHLCV + 인라인 기술지표 (SMA, BB, RSI, MACD 등) |
| `GET /api/analysis/{ticker}/earnings` | 재무 데이터 (PER, 매출성장률, 이익률, ROE, 분기실적 등) |
| `GET /api/analysis/{ticker}/pattern` | 2년 과거 패턴 분석 (5%+ 변동 찾아 현재와 유사도 비교) |
| `GET /api/analysis/{ticker}/prediction` | **50+ 기술지표** 종합 예측 (추세/모멘텀/변동성/거래량/구조 카테고리) |
| `GET /api/analysis/{ticker}/move-reasons?period=3mo` | 큰 가격 변동 이벤트 + 뉴스 매칭 (이유 추정) |
| `GET /api/analysis/{ticker}/checklist-live` | 종목별 투자 체크리스트 실시간 데이터 (원자재 가격, 재무지표 + 상태등) |

### 원자재 API (`/api/commodities/`)

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/commodities` | 전체 원자재 현재가 |
| `GET /api/commodities/{sector_name}` | 섹터별 관련 원자재 |
| `GET /api/commodities/history/{symbol}?period=6mo` | 원자재/ETF 가격 히스토리 |

### 뉴스 API (`/api/news/`)

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/news/{sector_name}` | 섹터 뉴스 |
| `GET /api/news/search/{keyword}` | 키워드 뉴스 검색 |

### 섹터 API (`/api/sectors/`)

| 엔드포인트 | 설명 |
|---|---|
| `GET /api/sectors` | 전체 섹터 목록 (Top 3 종목 포함) |
| `GET /api/sectors/{sector_name}/stocks` | 섹터별 종목 상세 |

---

## 프론트엔드 라우팅

| 경로 | 컴포넌트 | 설명 |
|---|---|---|
| `/` | `SectorMindMap` | 8개 섹터 마인드맵 (SVG 곡선 연결) |
| `/sector/:id` | `SectorDetailPage` | 2패널: 왼쪽=종목 리스트, 오른쪽=분석 카드 |
| `/stock/:ticker` | StockDetailPage | 개별 종목 전체 차트 |

---

## 핵심 로직: SectorDetailPage.tsx

### 분석 엔진 (프론트엔드 내장, 사용자에게 원시 지표 미표시)

1. **`analyzeChart(analysis, chartData)`**
   - RSI, MACD, Bollinger Band 위치, SMA 크로스, SMA200 거리, MACD 히스토그램 추세, 거래량 추세
   - → 점수 정규화 → `strong_buy / buy / neutral / sell / strong_sell`

2. **`analyzeFundamentals(earnings, patternData)`**
   - 매출성장률, 이익성장률, Forward PE vs Trailing PE, 이익률, ROE, 패턴 상승확률, 52주 위치
   - → 점수 정규화 → `매수 / 긍정적 / 중립 / 부정적 / 매도`

3. **`getOverallVerdict(chartV, fundV)`**
   - 차트 + 실적 점수 합산 → `적극 매수 / 매수 추천 / 관망 / 비중 축소 / 매도 권고`
   - 각 등급별 행동 가이드 (예: "목표 비중 50~70% 분할 매수")

### 50+ 지표 예측 엔진 (백엔드 `/prediction`)

**추세 (Trend)**: SMA 5/10/20/50/100/200, EMA 5/10/12/20/26/50, DEMA, TEMA, Ichimoku (전환선/기준선), VWAP, Parabolic SAR, SMA 크로스 (20/50, 50/200), 선형회귀 기울기

**모멘텀 (Momentum)**: RSI 7/14/21, Stochastic %K/%D, Williams %R, MACD (크로스 + 히스토그램 추세), CCI, MFI, ROC 5/10/20, Momentum 10, Ultimate Oscillator

**변동성 (Volatility)**: Bollinger Band 위치/폭, ATR, Keltner Channel, Donchian Channel, Z-Score

**거래량 (Volume)**: OBV 추세, 거래량 SMA 비율, Chaikin Money Flow, A/D Line

**구조 (Structure)**: 52주 고저 위치, ADX (+DI/-DI), Fibonacci 되돌림, SMA200 거리

→ 각 지표별 -1~+1 스코어 → 카테고리별 합산 → 전체 종합 점수 (-100 ~ +100)
→ 1주/1달 목표가 + 손절가 자동 산출

### UI 구성 (StockAnalysisCard)

1. **종합 판정 카드** (상단)
   - 대형 B/S/H 아이콘 + 그라디언트 배경
   - 차트/실적 스코어 바 (좌=매도, 우=매수, 중간선 기준)
   - 카테고리별 bullish/bearish 카운트 뱃지
   - 1주/1달 목표가, 손절가

2. **차트** (클릭 가능한 이벤트)
   - 깔끔한 가격 + 거래량 (지표 오버레이 없음)
   - 2.5%+ 변동 시점에 점선 + 클릭 가능한 태그
   - 클릭 시 해당 날짜의 급등/급락 이유 + 거래량 상황 표시
   - 호버 툴팁에도 이벤트 정보 포함

3. **모멘텀 섹션** (별도 대형 카드)
   - 종목별 현재 주요 카탈리스트/모멘텀 목록
   - 각 항목에 펄스 애니메이션 인디케이터

4. **투자 체크리스트** (실시간 데이터)
   - 종목별 체크리스트 항목에 실제 가격/지표 데이터 연결
   - 긍정(초록)/부정(빨강)/중립(노랑) 상태등 자동 판단
   - 가격 추이가 있는 항목에 미니 스파크라인 차트

5. **AI 예측 상세** (하단)
   - 카테고리별 스코어 바 (추세/모멘텀/변동성/거래량/구조)
   - 전체 강매도~강매수 게이지 바
   - 신뢰도 표시

### 데이터 로딩 전략

- **Phase 1** (빠른 로드): chart-data, analysis, earnings, pattern → UI 즉시 렌더링
- **Phase 2** (비동기): prediction, move-reasons, checklist-live → 각각 독립 로드, 도착하면 추가 표시

---

## 8개 섹터 (data/sectors.ts)

| ID | 이름 | 대표 종목 |
|---|---|---|
| `ai-semi` | AI 반도체 | NVDA, TSM, AVGO, 000660.KS, 005930.KS |
| `robotics` | 로보틱스 | TSLA, ISRG, FANUY, ABB, 0992.HK |
| `smr-nuclear` | SMR/원자력 | CEG, CCJ, BWXT, NNE, SMR |
| `cybersec` | 사이버보안 | CRWD, PANW, FTNT, ZS, S |
| `space` | 우주항공 | RKLB, LUNR, ASTS, RDW, MNTS |
| `biotech` | 생명공학 | CRSP, LLY, ILMN, 207940.KS, 068270.KS |
| `quantum` | 양자컴퓨팅 | IONQ, RGTI, QUBT, QBTS, ARQQ |
| `hydrogen` | 수소/에너지 | BE, PLUG, FCEL, BLDP, NEE |

각 섹터에는 `risks[]` (리스크 목록, severity 포함), `trackingIndicators[]` (추종 지표), `materials[]` (관련 원자재) 포함.

---

## 종목별 체크리스트 데이터 소스 (backend CHECKLIST_SOURCES)

각 종목별로 투자 시 중요한 지표를 실시간 데이터에 연결:

- **earnings_metric**: yfinance info에서 재무지표 조회 (revenue_growth, profit_margin, roe 등)
- **commodity**: yfinance로 관련 ETF/원자재 3개월 가격 추이 조회 + 미니 차트 데이터

예시 (NVDA):
- 데이터센터 매출 성장률 → earnings.revenue_growth (> 10%이면 positive)
- HBM/GPU 수요 → SOXX ETF 가격 추이 (상승이면 positive)
- AI 캡엑스 → MSFT 주가 추이 (상승이면 positive)
- 경쟁사 AMD → AMD 주가 추이 (하락이면 positive)
- 구리 가격 → HG=F (안정이면 positive)
- 영업이익률 → earnings.profit_margin (> 20%이면 positive)

---

## 종목별 모멘텀 & STOCK_META (프론트엔드 정적)

`STOCK_META` (SectorDetailPage.tsx): 15개 주요 종목에 대해:
- `checklist: string[]` — 투자 시 확인 항목 (텍스트, 백엔드 CHECKLIST_SOURCES와 별도)
- `momentum: string[]` — 현재 주요 카탈리스트/이벤트

---

## 개발 환경

```bash
# 백엔드 실행
cd backend
python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

# 프론트엔드 실행
cd frontend
npx vite --port 5173

# TypeScript 체크
cd frontend && npx tsc --noEmit
```

Vite proxy: `localhost:5173/api/*` → `localhost:8000/api/*` (vite.config.ts)

---

## 디자인 원칙

1. **다크 테마** — CSS 변수 기반 (`--color-bg-primary`, `--color-text-primary` 등)
2. **글래스모피즘** — `backdrop-filter: blur()`, 반투명 배경
3. **간결한 차트** — 지표 오버레이 없음, 가격+거래량만, 큰 변동에 주석
4. **사용자에게 원시 지표 미표시** — 분석 엔진이 내부에서 처리, 결과만 보여줌
5. **2단계 로딩** — 핵심 데이터 빠르게, 부가 데이터 비동기
