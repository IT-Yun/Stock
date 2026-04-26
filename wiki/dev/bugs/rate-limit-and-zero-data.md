---
title: "외부 API Rate Limit으로 인한 빈 데이터/0값 표시"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "502c0fc fix: harden data loading against provider rate limits"
  - "5579777 fix: 리튬/원자재 가격 $0.0 표시 버그 수정"
  - "69d8871 fix: never show empty data - keep loading until real data arrives"
tags: [bug, rate-limit, cache, yfinance, zero-data]
---

## 증상

- 원자재(리튬 등) 가격이 $0.0으로 표시됨
- 종목 분석 페이지가 데이터 없이 빈 화면으로 표시됨
- yfinance rate limit에 걸리면 전체 서비스가 수 분간 먹통이 됨

## 원인

yfinance 및 외부 데이터 소스의 rate limit에 대한 방어가 없었다.

1. **캐시 부재** (`502c0fc`): 메모리 캐시만 있고 디스크 캐시가 없어서, 서버 재시작 시 모든 데이터를 yfinance에서 다시 가져와야 했다. 짧은 시간에 수십 개 종목을 조회하면 rate limit에 걸렸다.

2. **all-zero 캐시 오염** (`5579777`): yfinance가 rate limit 상태에서 all-zero close 값을 반환하는 경우가 있다. 이 데이터가 캐시에 저장되면 TTL 동안 $0.0이 계속 표시됐다. 캐시 무효화 로직이 없었다.

3. **빈 데이터 표시** (`69d8871`): API 호출이 실패하더라도 로딩 화면이 해제되어 빈 화면이 그대로 표시됐다. `Promise.allSettled()` 후 성공/실패를 구분하지 않고 일괄 로딩 해제했다.

## 해결

```python
# 502c0fc: 2계층 캐시 (메모리 30분 + 디스크 6시간) + stale 데이터 허용
def _load_disk_frame(key, max_age=DISK_CACHE_TTL, allow_stale=False):
    ...
# rate limit 시 디스크 캐시의 오래된 데이터라도 반환

# 5579777: all-zero 감지 + 캐시 무효화 + 재시도
if closes.max() == 0:
    # 캐시된 데이터가 all-zero면 즉시 재시도
    hist = StockDataService.get_stock_history(sym, period="1y")
    commodity_cache[sym] = hist
# 재시도 후에도 0이면 에러로 처리 (0값 표시 방지)
if closes.max() == 0:
    raise ValueError(f"All-zero close prices for {sym}")
```

```typescript
// 69d8871: 필수 데이터 없으면 로딩 유지 + 자동 재시도
if (!chartOk && !hasAnalysisData) {
    setLoadError(true);
    setTimeout(() => setRetryCount((c) => c + 1), 5000);
    return; // loading=true 유지, 빈 화면 표시하지 않음
}
```

## 교훈

- **외부 API 의존 서비스는 반드시 다계층 캐시를 구축해야 한다.** 메모리 -> 디스크 -> stale 데이터 순으로 fallback하여 rate limit 시에도 기존 데이터를 보여줘야 한다.
- **0값/빈값은 유효한 데이터가 아니라 에러로 취급해야 한다.** 캐시에 저장하기 전에 데이터 유효성을 검증하는 guard가 필요하다.
- **프론트엔드는 "데이터 없음"과 "로딩 중"을 구분해야 한다.** API 실패 시 빈 화면 대신 로딩 + 재시도 UI를 유지하는 것이 사용자 경험상 훨씬 낫다.
- **yfinance는 rate limit 시 에러 대신 all-zero 데이터를 반환하는 경우가 있다.** 단순한 `try/except`로는 잡을 수 없으므로 반환값 검증이 필수다.
