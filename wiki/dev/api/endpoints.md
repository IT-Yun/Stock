---
title: "API 엔드포인트 설계 문서"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/api/analysis.py
  - backend/api/sectors.py
  - backend/api/news.py
  - backend/api/members.py
  - backend/main.py
  - frontend/src/api/client.ts
tags: [api, fastapi, endpoints, frontend]
---

# API 엔드포인트 설계 문서

모든 API는 FastAPI 기반이며, 각 라우터는 `prefix="/api"`로 설정되어 있다.
인증은 `X-Auth-Nickname` 헤더(URI-encoded)를 사용하며, `AuthMiddleware`가 POST/PUT/DELETE 요청에만 적용된다.

---

## 1. 분석 (Analysis) -- `backend/api/analysis.py`

라우터: `APIRouter(prefix="/api", tags=["analysis"])`

### 1.1 종목 기술 분석

| 경로 | 메서드 | 파라미터 | 응답 | 캐시 TTL | 프론트엔드 함수 |
|------|--------|----------|------|----------|----------------|
| `/api/analysis/{ticker}` | GET | `ticker`: path (str) | `AnalysisResult` (RSI, MACD, 볼린저밴드, SMA, 매수/매도 신호, 신뢰도) | 30분 | `fetchAnalysis(ticker)` |
| `/api/analysis/{ticker}/trading-targets` | GET | `ticker`: path (str) | `dict` (매수/매도/손절 목표가, 피보나치, 지지/저항선) | 10분 | `fetchTradingTargets(ticker)` |
| `/api/analysis/{ticker}/chart-data` | GET | `ticker`: path (str), `period`: query (str, default="3mo") | `dict` {ticker, data: ChartDataPoint[], indicators} | 30분 | `fetchChartData(ticker, period)` |
| `/api/analysis/{ticker}/earnings` | GET | `ticker`: path (str) | `dict` (PER, PBR, ROE, 매출, 영업이익, 배당수익률 등) | 30분 | `fetchEarnings(ticker)` |
| `/api/analysis/{ticker}/pattern` | GET | `ticker`: path (str) | `dict` (과거 패턴 분석, 유사도 점수, 현재 설정) | 12시간 | `fetchPatternAnalysis(ticker)` |
| `/api/analysis/{ticker}/prediction` | GET | `ticker`: path (str) | `dict` (50+ 기술 지표 종합 분석, 가격 예측) | 1시간 | `fetchPrediction(ticker)` |
| `/api/analysis/{ticker}/move-reasons` | GET | `ticker`: path (str), `period`: query (str, default="3mo") | `dict` (큰 가격 변동 + 뉴스 원인 분석) | 10분 | `fetchMoveReasons(ticker, period)` |
| `/api/analysis/{ticker}/checklist-live` | GET | `ticker`: path (str) | `dict` (실시간 체크리스트, 스파크라인, 상관계수) | 2시간 | `fetchChecklistLive(ticker)` (timeout 90s) |
| `/api/analysis/{ticker}/research` | GET | `ticker`: path (str) | `dict` (애널리스트 리포트, SEC/DART 공시, 컨센서스) | 30분 | `fetchResearch(ticker)` |
| `/api/analysis/{ticker}/news-analysis` | GET | `ticker`: path (str) | `dict` (뉴스별 의미, 선반영 여부, 향후 예측, 액션) | 5분 | `fetchNewsAnalysis(ticker)` |

### 1.2 종목 검색 및 랭킹

| 경로 | 메서드 | 파라미터 | 응답 | 캐시 TTL | 프론트엔드 함수 |
|------|--------|----------|------|----------|----------------|
| `/api/analysis/stock-search/{query}` | GET | `query`: path (str) | `dict` {query, results: [{ticker, name, market, ...}]} | 10분 | `searchStocks(query)` (cache-bust) |
| `/api/analysis/top-ranked` | GET | 없음 | `dict` {rankings: [...], total_analyzed} | 10분 | -- |
| `/api/analysis/rankings/top-ranked` | GET | 없음 | `dict` (위와 동일, 경로 충돌 방지용) | 10분 | -- |

### 1.3 섹터 펄스

| 경로 | 메서드 | 파라미터 | 응답 | 캐시 TTL | 프론트엔드 함수 |
|------|--------|----------|------|----------|----------------|
| `/api/analysis/sector/{sector_id}/pulse` | GET | `sector_id`: path (str) | `dict` {sector_id, checklist, summary} | 10분 | `fetchSectorPulse(sectorId)` |

### 1.4 매크로 이벤트

| 경로 | 메서드 | 파라미터 | 응답 | 캐시 TTL | 프론트엔드 함수 |
|------|--------|----------|------|----------|----------------|
| `/api/analysis/macro-events` | GET | 없음 | `dict` (지정학/거시경제 이벤트, 영향 평가) | 15분 | `fetchMacroEvents()` |

### 1.5 원자재

| 경로 | 메서드 | 파라미터 | 응답 | 캐시 TTL | 프론트엔드 함수 |
|------|--------|----------|------|----------|----------------|
| `/api/commodities` | GET | 없음 | `list[CommodityPrice]` | 30분 | `fetchCommodities()` |
| `/api/commodities/{sector_name}` | GET | `sector_name`: path (str) | `list[CommodityPrice]` (섹터 관련 원자재) | 30분 | -- |
| `/api/commodities/history/{symbol}` | GET | `symbol`: path (str), `period`: query (str, default="6mo") | `dict` {symbol, data: [{date, close, volume}]} | -- | `fetchCommodityHistory(symbol, period)` |

---

## 2. 섹터 (Sectors) -- `backend/api/sectors.py`

라우터: `APIRouter(prefix="/api", tags=["sectors"])`

| 경로 | 메서드 | 파라미터 | 응답 | 프론트엔드 함수 |
|------|--------|----------|------|----------------|
| `/api/sectors` | GET | 없음 | `list[Sector]` (각 섹터 이름, 설명, top 3 종목) | `fetchSectors()` |
| `/api/sectors/{sector_name}/stocks` | GET | `sector_name`: path (str) | `list[Stock]` (ticker, name, sector, price, change_percent) | `fetchSectorStocks(sectorName)` |
| `/api/sectors/top-ranked` | GET | 없음 | `dict` (top ranked 종목 랭킹) | `fetchTopRanked()` |
| `/api/rankings/top-ranked` | GET | 없음 | `dict` (위와 동일, 별도 경로) | -- |

---

## 3. 뉴스 (News) -- `backend/api/news.py`

라우터: `APIRouter(prefix="/api", tags=["news"])`

| 경로 | 메서드 | 파라미터 | 응답 | 프론트엔드 함수 |
|------|--------|----------|------|----------------|
| `/api/news/{sector_name}` | GET | `sector_name`: path (str) | `list[NewsArticle]` (title, url, source, published_at, summary) | `fetchNews(sectorName)` |
| `/api/news/search/{keyword}` | GET | `keyword`: path (str) | `list[NewsArticle]` | `searchNews(keyword)` |

---

## 4. 멤버 관리 (Members) -- `backend/api/members.py`

라우터: `APIRouter(prefix="/api/members", tags=["members"])`

저장소: Supabase (primary) + JSON 파일 (fallback: `backend/data/members.json`)

| 경로 | 메서드 | 파라미터 | 응답 | 인증 |
|------|--------|----------|------|------|
| `/api/members/verify` | POST | body: `{nickname: str}` | `{allowed: bool, role?: "admin"\|"member"}` | 없음 |
| `/api/members/list` | GET | 없음 | `{admins: str[], members: str[]}` | Admin (X-Auth-Nickname) |
| `/api/members/add` | POST | body: `{nickname: str}` | `{message: str}` | Admin |
| `/api/members/remove` | DELETE | body: `{nickname: str}` | `{message: str}` | Admin |
| `/api/members/visit` | POST | body: `{nickname: str}` | `{ok: true}` | 없음 |
| `/api/members/stats` | GET | 없음 | `{stats: [{nickname, visit_count, last_visit}], total_visits}` | Admin |

---

## 5. 시스템 (main.py)

| 경로 | 메서드 | 파라미터 | 응답 | 프론트엔드 함수 |
|------|--------|----------|------|----------------|
| `/health` | GET | 없음 | `{status: "ok"}` | -- |
| `/api/refresh-status` | GET | 없음 | `{status, last_refresh, ...}` | `fetchRefreshStatus()` |
| `/api/refresh-now` | POST | 없음 | `{message: str}` | `triggerRefreshNow()` |

---

## 프론트엔드 연동 현황 (`frontend/src/api/client.ts`)

### HTTP 클라이언트 설정
- **baseURL**: `/api` (프록시/같은 서버)
- **timeout**: 60초 (기본), checklist-live는 90초
- **인증**: 모든 요청에 `X-Auth-Nickname` 헤더 자동 추가 (localStorage에서 읽음, URI-encoded)
- **자동 재시도**: 네트워크 에러, 5xx, 403 에러 시 최대 2회 재시도 (1.5초 간격)

### 요청 중복 제거 (dedupedGet)
동일한 URL+params 조합의 동시 요청을 하나로 합침 (`inflightRequests` Map 사용).

### 응답 캐시 (localStorage)
- prefix: `stock-api-cache:`
- TTL: 6시간
- API 실패 시 캐시된 데이터를 fallback으로 반환
- `fetchTopRanked()`는 API 실패/빈 응답 시 localStorage 캐시 -> static fallback 순서로 대응

### 프론트엔드에서 호출하지만 백엔드에 직접 정의되지 않은 엔드포인트
- 없음. 모든 프론트엔드 함수가 백엔드 엔드포인트와 1:1 대응.

### Top-Ranked 엔드포인트 중복 경로 정리
`/api/sectors/top-ranked`, `/api/rankings/top-ranked`, `/api/analysis/top-ranked`, `/api/analysis/rankings/top-ranked` -- 4개 경로 모두 같은 `get_top_ranked()` 함수를 호출. 프론트엔드는 `/api/sectors/top-ranked`를 사용.
