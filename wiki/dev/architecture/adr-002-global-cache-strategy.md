---
title: "글로벌 메모리 + 디스크 2계층 캐시 전략"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/services/stock_data.py
tags: [architecture, cache, performance, yfinance]
---

## 결정

모든 외부 API 호출 결과를 **인메모리 캐시(30분 TTL)** 와 **디스크 캐시(6시간 TTL)** 2계층으로 관리한다.

### 인메모리 캐시

```python
_cache: dict[str, tuple[float, object]] = {}
CACHE_TTL = 1800  # 30분
```

### 디스크 캐시

- JSON 데이터: `_save_disk_json()` / `_load_disk_json()` (SHA-256 해시 파일명)
- DataFrame: `_save_disk_frame()` / `_load_disk_frame()` (pickle 형식)
- 경로: `CACHE_DIR` 환경변수 또는 `.cache/market/` 또는 Render의 `/var/data/stock-cache`

### yfinance 전용 글로벌 캐시

동일 ticker에 대해 `/earnings`, `/checklist-live`, `/move-reasons` 등 여러 엔드포인트가 `.info`를 요청하면 한 번만 호출:

```python
_yf_info_cache: dict[str, tuple[float, dict]] = {}
_yf_financials_cache: dict[str, tuple[float, object]] = {}
_yf_lock = threading.Lock()
```

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| Redis | 인프라 추가 비용, Render 무료 티어에서 사용 불가 |
| SQLite | DataFrame 저장에 부적합, pickle 대비 성능 열위 |
| 메모리 캐시만 | 서버 재시작 시 cold start에 모든 API 재호출 필요 |
| 디스크 캐시만 | 매 요청마다 파일 I/O 발생, 응답 지연 |

## 이유

- yfinance 호출을 최소화하여 rate limit 회피 (30분 내 동일 요청 0회)
- 서버 재시작 후에도 디스크 캐시로 즉시 응답 가능 (cold start 보호)
- `allow_stale=True` 옵션으로 API 실패 시에도 stale 데이터 반환 (가용성 우선)
- `threading.Lock()`으로 동시 요청 시 중복 fetch 방지

## 트레이드오프

- 메모리 사용량이 ticker 수에 비례하여 증가 (현재 40개 ticker 기준 문제 없음)
- 디스크 캐시 파일이 누적됨 (자동 정리 미구현)
- 30분간 가격이 stale할 수 있음 (실시간 트레이딩에는 부적합)
- pickle 파일은 Python 버전 간 호환성 문제 가능

## 관련 코드

- **`backend/services/stock_data.py`** 20-27행: 캐시 설정 및 디렉토리 결정
- **`backend/services/stock_data.py`** 30-39행: 인메모리 `_get_cached()` / `_set_cached()`
- **`backend/services/stock_data.py`** 62-119행: `_yf_info_cache` / `_yf_financials_cache` 글로벌 캐시
- **`backend/services/stock_data.py`** 122-169행: 디스크 캐시 읽기/쓰기 유틸
- **`backend/config.py`** 21행: `CACHE_DIR` 환경변수 설정
