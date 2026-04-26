---
title: "async def에서 동기 I/O 호출로 이벤트 루프 차단"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "a99cec9 fix: async def -> sync def to unblock event loop on Render"
tags: [bug, async, FastAPI, performance, blocking]
---

## 증상

- 한 사용자가 종목 분석을 요청하면 다른 모든 사용자의 요청이 멈춤
- API 응답 시간이 yfinance 호출 시간에 비례하여 수십 초까지 증가
- Render 배포 환경에서 timeout 빈발

## 원인

모든 FastAPI 엔드포인트가 `async def`로 정의되어 있었지만, 내부에서 `yfinance`, `requests` 등 동기 HTTP 호출을 수행했다.

FastAPI에서 `async def` 핸들러는 메인 이벤트 루프에서 직접 실행된다. 동기 I/O가 블로킹되면 단일 스레드 이벤트 루프 전체가 멈춰서, 해당 yfinance 호출이 끝날 때까지 다른 모든 요청이 큐에 대기한다.

```python
# 문제 코드
@router.get("/analysis/{ticker}")
async def get_analysis(ticker: str):  # async def + 동기 I/O = 이벤트 루프 차단
    stock = yfinance.Ticker(ticker)   # 블로킹 HTTP 호출
    hist = stock.history(period="1y")  # 수 초간 이벤트 루프 점유
```

## 해결

`async def`를 `def`(동기)로 변경했다. FastAPI는 `def` 핸들러를 자동으로 threadpool에서 실행하므로 동기 I/O가 이벤트 루프를 차단하지 않는다.

```python
@router.get("/analysis/{ticker}")
def get_analysis(ticker: str):        # sync def -> threadpool에서 실행
    stock = yfinance.Ticker(ticker)   # 이 스레드만 블로킹, 다른 요청 정상 처리
```

추가로 Render 배포 시 uvicorn worker를 2개로 늘리고 reload를 비활성화했다.

## 교훈

- **FastAPI에서 `async def`는 내부의 모든 I/O가 `await` 가능할 때만 사용해야 한다.** 동기 라이브러리(yfinance, requests)를 호출하면 반드시 `def`(sync)를 써야 한다.
- **`async def` + 동기 I/O 조합은 성능 병목의 가장 흔한 원인이다.** 개발 환경에서는 동시 요청이 적어 발견하기 어렵고, 프로덕션에서 부하가 걸리면 갑자기 나타난다.
- 대안: `run_in_executor`로 동기 코드를 감싸거나, `httpx.AsyncClient`로 비동기 HTTP를 사용할 수도 있지만, yfinance 같은 서드파티 라이브러리는 내부에 동기 코드가 깊이 있어 `def`가 가장 현실적인 해결책이다.
