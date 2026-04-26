---
title: "Singleflight 패턴 — yfinance 중복 요청 방지 및 Rate Limit 제어"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/services/runtime_controls.py
  - backend/services/stock_data.py
tags: [architecture, rate-limit, concurrency, semaphore]
---

## 결정

yfinance API 호출을 **세마포어 + 최소 호출 간격**으로 제어한다.

### 세마포어 기반 동시성 제한

```python
YFINANCE_MAX_CONCURRENCY = max(1, int(os.getenv("YFINANCE_MAX_CONCURRENCY", "2")))
_YFINANCE_SEMAPHORE = threading.BoundedSemaphore(YFINANCE_MAX_CONCURRENCY)
```

### 최소 호출 간격 (Token Bucket 변형)

```python
_YF_MIN_INTERVAL = float(os.getenv("YFINANCE_MIN_INTERVAL", "0.5"))

@contextmanager
def limit_yfinance():
    _YFINANCE_SEMAPHORE.acquire()
    try:
        with _yf_rate_lock:
            elapsed = time.time() - _yf_last_call
            if elapsed < _YF_MIN_INTERVAL:
                time.sleep(_YF_MIN_INTERVAL - elapsed)
            _yf_last_call = time.time()
        yield
    finally:
        _YFINANCE_SEMAPHORE.release()
```

### 글로벌 캐시와 결합

`get_yf_info()`, `get_yf_financials()`에서 `_yf_lock`으로 캐시 확인 후, 캐시 miss인 경우에만 `limit_yfinance()` 안에서 API 호출. 동일 ticker에 대한 여러 엔드포인트 요청이 단일 API 호출로 병합됨.

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| asyncio.Semaphore | yfinance가 동기 라이브러리라 threading 기반이 적합 |
| Token Bucket 라이브러리 | 외부 의존성 추가 불필요, 단순 구현으로 충분 |
| 제한 없이 호출 | Render 공유 호스팅에서 Yahoo 429 에러 빈발 |
| 요청 큐(Queue) | 구현 복잡도 대비 이점 없음 |

## 이유

- Render 무료 티어에서 Yahoo Finance가 IP 기반으로 rate limit 적용
- 동시 2개 + 0.5초 간격이면 분당 최대 ~120회로 Yahoo 임계치 이하
- `BoundedSemaphore`는 release 초과 호출을 방지하여 안전
- 환경변수로 동시성/간격 조절 가능 (운영 중 튜닝 가능)
- HTTP 요청용 별도 세마포어(`_HTTP_SEMAPHORE`, 동시 6개)도 제공

## 트레이드오프

- 최소 간격 대기로 인해 다수 ticker 동시 조회 시 응답 지연
- 세마포어 동시성 2는 보수적 — 전용 서버에서는 더 높일 수 있음
- sleep 기반 rate limit은 정밀하지 않음 (실제 네트워크 지연 미포함)

## 관련 코드

- **`backend/services/runtime_controls.py`** 전체: 세마포어 + rate limit context manager
- **`backend/services/stock_data.py`** 72-94행: `get_yf_info()` — lock + limit_yfinance 조합
- **`backend/services/stock_data.py`** 248-263행: `get_stock_info()` — yfinance fallback에서 `limit_yfinance()` 사용
