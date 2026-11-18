---
title: "Sequential Loading 전략 — 단계적 데이터 로딩"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/main.py
  - backend/services/stock_data.py
  - frontend/src/api/client.ts
  - frontend/src/data/sectors.ts
tags: [architecture, loading, rate-limit, ux]
---

## 결정

서버 시작 시와 프론트엔드 렌더링 시 데이터를 **순차적(sequential)으로 로딩**하여 외부 API rate limit을 회피한다.

### 서버 사이드: Warmup Phase 분리

```python
def _warmup_cache():
    """Phase 1: 공유 캐시만 워밍 (섹터 + 원자재)"""
    StockDataService.get_all_sectors()
    CommodityDataService.get_commodity_prices()
```

- Phase 1: 섹터 + 원자재 (서버 시작 직후)
- Phase 2: Checklist 점수 (30초 대기 후, ticker당 3초 간격)
- Daily refresh: 모든 ticker를 0.5초 간격으로 순차 갱신

### 프론트엔드: Static-first 렌더링

`sectors.ts`에 8개 섹터의 정적 데이터(이름, 설명, 종목 목록, 리스크 등)를 하드코딩하여 API 응답 전에 UI 렌더링:

```typescript
export const SECTORS: SectorDef[] = [
  { id: "ai-semi", name: "AI / 반도체", picks: [...], risks: [...], ... },
  // ... 8개 섹터
];
```

API 실패 시 이 정적 데이터에서 fallback 랭킹을 생성.

### 순차 요청의 원칙

- 동시 yfinance 호출을 최대 2개로 제한 (세마포어)
- 호출 간 최소 0.5초 대기 (rate limit)
- warmup에서 per-ticker 호출을 하지 않음 (cold boot 시 burst 방지)

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| 모든 ticker 병렬 fetch | cold start에서 Yahoo 429 에러 폭발 |
| 요청 시점에만 로딩 (lazy) | 첫 사용자 경험 저하, 캐시 miss 동시 다발 |
| 전체 데이터 DB 저장 | DB 인프라 비용, 무료 티어 부적합 |
| CDN 캐시 | 동적 주가 데이터에는 부적합 |

## 이유

- Render 무료 티어에서 IP 공유로 인해 Yahoo Finance rate limit이 특히 엄격
- cold start 시 40개 ticker를 동시 호출하면 100% 차단됨
- 순차 로딩 + 캐시 워밍으로 사용자 첫 요청 시 캐시 hit 보장
- 정적 섹터 데이터로 API 응답 전에도 UI가 즉시 렌더링됨

## 트레이드오프

- 전체 워밍에 수 분 소요 (40 tickers * 3초 = ~2분)
- 워밍 완료 전 접속한 사용자는 일부 데이터 누락 가능
- 정적 데이터(`sectors.ts`)와 서버 데이터(`sectors.json`)의 동기화 필요
- 순차 처리로 인해 전체 throughput이 낮음

## 관련 코드

- **`backend/main.py`** 64-78행: `_warmup_cache()` — Phase 1 워밍
- **`backend/main.py`** 81-114행: `_warmup_checklist_scores()` — Phase 2 순차 워밍 (3초 간격)
- **`backend/main.py`** 183-196행: `_run_daily_refresh()` — 순차 갱신 (0.5초 간격)
- **`frontend/src/data/sectors.ts`** 62-260행: 8개 섹터 정적 정의
- **`frontend/src/api/client.ts`** 51-68행: static fallback 생성
