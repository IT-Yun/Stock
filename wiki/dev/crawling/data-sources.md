---
title: "크롤링/데이터 수집 패턴"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/services/news_crawler.py
  - backend/services/stock_data.py
  - backend/services/commodity_data.py
  - backend/services/fundamentals.py
  - backend/services/runtime_controls.py
tags: [crawling, data-sources, rate-limit, caching, yfinance]
---

# 크롤링/데이터 수집 패턴

---

## 1. 데이터 소스 매핑

### 1.1 주가 데이터 (`stock_data.py`)

| 데이터 | 한국 주식 (KRX) | 미국 주식 |
|--------|----------------|-----------|
| 현재가/등락률 | FinanceDataReader (primary) -> yfinance (fallback) | yfinance |
| 히스토리 (OHLCV) | FinanceDataReader (primary) -> yfinance (fallback) | yfinance |
| 종목 정보 (.info) | yfinance (global cache) | yfinance (global cache) |
| 재무제표 | yfinance quarterly_financials/balance_sheet (global cache) | yfinance (global cache) |

- FinanceDataReader는 KRX 주식에 대해 더 빠르고 안정적
- yfinance는 `curl_cffi` 브라우저 임퍼소네이션 세션을 사용하여 Yahoo Finance 봇 탐지 우회
- ticker 형식 변환: `005930.KS` -> `005930` (FDR용)

### 1.2 펀더멘털 데이터 (`fundamentals.py`)

| 데이터 | 한국 주식 | 미국 주식 |
|--------|-----------|-----------|
| PER, PBR, ROE, 배당수익률 | Naver Finance API (primary) -> HTML 스크래핑 (fallback) | Finnhub API (primary) -> Yahoo Finance 스크래핑 (fallback) |
| 매출/이익 성장률 | Naver Finance API (연간 재무) | Finnhub API |
| 영업이익률, 순이익률 | Naver Finance API | Finnhub / Yahoo Finance |
| 컨센서스 목표가 | Naver Finance (consensus_target_price) | -- |

- Naver Finance: `m.stock.naver.com` JSON API (integration + finance)
- Finnhub: REST API (`finnhub.io/api/v1/stock/metric`)
- Yahoo Finance: `curl_cffi`로 key-statistics 페이지 스크래핑 (Chrome 임퍼소네이션)

### 1.3 뉴스 데이터 (`news_crawler.py`)

| 소스 | 방법 | 대상 |
|------|------|------|
| Naver 뉴스 | HTML 스크래핑 (`search.naver.com`) | 한국어 키워드 검색 |
| Google News | RSS 피드 (`news.google.com/rss`) | 한국어 + 영어 검색 |
| Naver 금융 종목뉴스 | `NaverFinanceService.fetch_stock_news()` | 6자리 종목코드 전용 |

- 섹터 뉴스: Naver + Google(한국어) + Google(영어) 동시 수집
- 한->영 키워드 매핑: `KEYWORD_EN_MAP` (예: "반도체" -> "semiconductor AI chip")
- 잠정실적 크롤링: 뉴스 텍스트에서 정규식으로 금액 추출 (조/억 단위 한국어 + billion/million 영어)
- 중복 제거: 제목 기준 dedup

### 1.4 원자재 데이터 (`commodity_data.py`)

| 원자재 | 심볼 | 단위 |
|--------|------|------|
| 금 | GC=F | 달러/온스 |
| 은 | SI=F | 달러/온스 |
| 원유 (WTI) | CL=F | 달러/배럴 |
| 구리 | HG=F | 달러/파운드 |
| 우라늄 ETF | URA | 달러 |
| 천연가스 | NG=F | 달러/MMBtu |
| 리튬 ETF | LIT | 달러 |

- 모든 원자재는 `StockDataService.get_stock_history()`를 통해 yfinance로 수집
- 섹터별 관련 원자재 매핑: `SECTOR_COMMODITY_MAP` (예: "반도체" -> ["은", "금"])

---

## 2. Rate Limit 전략

### 2.1 Semaphore 기반 동시성 제한 (`runtime_controls.py`)

```
yfinance: BoundedSemaphore(2)  -- YFINANCE_MAX_CONCURRENCY 환경변수로 조정 가능
HTTP:     BoundedSemaphore(6)  -- HTTP_MAX_CONCURRENCY 환경변수로 조정 가능
```

- `limit_yfinance()`: semaphore 획득 + 최소 0.5초 간격 강제 (`YFINANCE_MIN_INTERVAL`)
- `limit_http()`: semaphore만 사용 (간격 제한 없음)
- 모든 yfinance 호출은 `limit_yfinance()` context manager로 감싸야 함
- 모든 외부 HTTP 요청은 `limit_http()` context manager로 감싸야 함

### 2.2 Global yfinance Object Cache (`stock_data.py`)

- `get_yf_info(ticker)`: `.info` 결과를 thread-safe하게 30분 캐시
- `get_yf_financials(ticker)`: `quarterly_financials` + `quarterly_balance_sheet`를 30분 캐시
- 여러 엔드포인트(`/earnings`, `/checklist-live`, `/move-reasons`)가 동일 ticker의 `.info`를 요청할 때 yfinance를 단 1회만 호출

### 2.3 curl_cffi 브라우저 임퍼소네이션

- yfinance의 기본 세션을 `curl_cffi.requests.Session(impersonate="chrome")`으로 교체
- Yahoo Finance의 TLS 핑거프린팅 기반 봇 탐지를 우회
- fundamentals.py의 Yahoo 스크래핑에서도 동일하게 사용

### 2.4 Singleflight 패턴 (`analysis.py`)

- `_run_singleflight(key, producer, ttl, model_cls)`: 동일 key에 대해 동시 요청 시 하나만 실행, 나머지는 대기
- `threading.Event` 기반, 최대 30초 대기
- 실패 시 stale disk cache 반환

---

## 3. 에러 핸들링 패턴

### 3.1 3단계 Fallback 구조

모든 데이터 수집 서비스에서 동일한 패턴을 따름:

```
1. Memory Cache (TTL 내) -> 즉시 반환
2. Disk Cache (TTL 내) -> 반환 + memory cache 갱신
3. API 호출 시도
   - 성공: memory + disk cache 갱신
   - 실패: stale disk cache 반환 (TTL 무시)
   - stale도 없으면: 빈 결과 또는 에러 반환
```

### 3.2 서비스별 에러 처리

| 서비스 | 에러 시 행동 |
|--------|-------------|
| `StockDataService.get_stock_info()` | stale disk cache -> `{price: 0.0, change_percent: 0.0}` |
| `StockDataService.get_stock_history()` | stale disk cache -> 빈 DataFrame |
| `NewsCrawlerService` | 각 소스 독립 try/except, 실패해도 다른 소스 결과 반환 |
| `fetch_fundamentals()` | KRX: Naver -> HTML fallback. US: Finnhub -> Yahoo fallback |
| `CommodityDataService` | 개별 원자재 실패 시 해당 항목만 제외 |
| Members API | Supabase 실패 -> JSON 파일 fallback |

### 3.3 프론트엔드 에러 처리

- 자동 재시도: 5xx, 403, 네트워크 에러 시 최대 2회 (1.5초 * retry_count 간격)
- localStorage 캐시 fallback: API 실패 시 6시간 이내 캐시 데이터 반환
- Top-Ranked 특별 처리: API -> localStorage cache -> static fallback (sectors.ts 데이터)

---

## 4. 캐시 전략

### 4.1 Memory Cache (in-process dict)

| 서비스 | 캐시 키 패턴 | TTL |
|--------|-------------|-----|
| 주가 정보 | `info:{ticker}` | 30분 |
| 히스토리 | `hist:{ticker}:{period}` | 30분 |
| 전체 섹터 | `all_sectors` | 30분 |
| 분석 결과 | `analysis:{ticker}` | 30분 |
| 트레이딩 타겟 | `targets:{ticker}` | 10분 |
| 차트 데이터 | `chart-data:{ticker}:{period}` | 30분 |
| 실적 | `earnings:{ticker}` | 30분 |
| 패턴 분석 | `pattern:{ticker}` | 12시간 |
| 예측 | `prediction:{ticker}` | 1시간 |
| 급등/급락 원인 | `move-reasons:{ticker}:{period}` | 10분 |
| 체크리스트 | `checklist-live:{ticker}` | 2시간 |
| 종목 검색 | `stock-search:{query}` | 10분 |
| 섹터 펄스 | `sector-pulse:{sector_id}` | 10분 |
| 매크로 이벤트 | `macro-events:global` | 15분 |
| 리서치 | `research:{ticker}` | 30분 |
| 뉴스 분석 | `news-analysis:{ticker}` | 5분 |
| 펀더멘털 | `fund:{ticker}` | 30분 |
| 뉴스 | `naver:{keyword}`, `google:{lang}:{keyword}` 등 | 3분 |
| 원자재 (전체) | `_all_cache` | 30분 |
| 원자재 (개별) | `_commodity_cache[name]` | 30분 |

### 4.2 Disk Cache (JSON/Pickle 파일)

- 경로: `settings.CACHE_DIR` 또는 `/var/data/stock-cache` (Render) 또는 `.cache/market` (로컬)
- JSON: `_save_disk_json()` / `_load_disk_json()` -- 주가 정보용
- Pickle: `_save_disk_frame()` / `_load_disk_frame()` -- DataFrame용
- 파일명: SHA-256 해시 기반 (`{prefix}-{hash}.{json|pkl}`)
- 기본 TTL: 6시간 (`DISK_CACHE_TTL`)
- `allow_stale=True` 옵션으로 TTL 무시하고 stale 데이터 반환 가능

### 4.3 프론트엔드 캐시 (localStorage)

- prefix: `stock-api-cache:`
- TTL: 6시간
- API 성공 시 자동 저장, 실패 시 자동 복원
- 요청 중복 제거: `inflightRequests` Map으로 동일 요청 합침
