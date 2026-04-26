---
title: "curl_cffi 브라우저 위장 세션 도입"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/services/stock_data.py
tags: [architecture, yfinance, rate-limit, curl-cffi]
---

## 결정

yfinance HTTP 요청에 `curl_cffi` 라이브러리의 `Session(impersonate="chrome")` 을 사용하여 Yahoo Finance의 봇 탐지를 우회한다.

모듈 로드 시점에 전역 `_yf_session` 을 생성하고, 모든 `yf.Ticker()` 호출에 이 세션을 주입한다.

```python
from curl_cffi.requests import Session as CffiSession
_yf_session = CffiSession(impersonate="chrome")

def _make_yf_ticker(ticker: str):
    if _yf_session:
        return yf.Ticker(ticker, session=_yf_session)
    return yf.Ticker(ticker)
```

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| 기본 `requests` 세션 | Yahoo가 TLS fingerprint로 봇을 식별하여 429/403 반환 |
| `fake-useragent` UA 변경 | User-Agent만 바꿔서는 TLS fingerprint 차이를 숨길 수 없음 |
| Yahoo Finance 유료 API | 비용 발생, 무료 프로젝트에 부적합 |
| FinanceDataReader만 사용 | 한국 주식은 가능하지만 미국 주식 데이터 부족 |

## 이유

- Yahoo Finance는 2024년부터 TLS JA3 fingerprint 기반 봇 탐지를 강화함
- `curl_cffi`는 libcurl 기반으로 Chrome의 TLS fingerprint를 완벽히 모방
- yfinance의 `session` 파라미터에 그대로 주입 가능하여 코드 변경 최소화
- `ImportError` 발생 시 자동으로 기본 세션으로 fallback하여 안전

## 트레이드오프

- `curl_cffi`는 C 바이너리 의존성이 있어 일부 환경(Alpine Linux 등)에서 빌드 어려울 수 있음
- Yahoo의 봇 탐지 정책이 변경되면 `impersonate` 버전도 업데이트해야 함
- 법적으로 서비스 약관 위반 가능성 존재 (Yahoo Finance TOS)

## 관련 코드

- **`backend/services/stock_data.py`** 42-58행: `_yf_session` 생성 및 `_make_yf_ticker()` 함수
- curl_cffi 임포트 실패 시 `_yf_session = None`으로 graceful degradation
