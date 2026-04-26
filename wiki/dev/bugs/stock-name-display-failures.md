---
title: "종목명이 티커 코드/잘못된 언어로 표시되는 패턴"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "7bf5e25 fix: 랭킹 종목명이 티커코드로 표시되는 버그 수정"
  - "032ca03 fix: 랭킹 종목명 fallback 매핑 추가"
  - "2ecb874 fix: 미국 주식 이름 한국어->영어"
  - "1c96ccc fix: 영어 검색에도 한국 종목 표시"
  - "a4d53fb fix: 뉴스 검색 - 티커가 일반 단어인 종목 엉뚱한 뉴스 방지"
tags: [bug, display, naming, i18n, fallback]
---

## 증상

- 랭킹 페이지에서 "현대자동차" 대신 "005380.KS"가 표시됨
- 미국 주식이 한국어 이름으로 표시됨 (예: "엔비디아" 대신 "NVIDIA"여야 함)
- "lg" 검색 시 LG화학, LG이노텍 등 한국 종목이 나타나지 않음
- "LAKE" 같은 일반 단어 티커로 뉴스 검색 시 호수 관련 뉴스가 나옴

## 원인

종목명 결정 로직에 여러 계층의 문제가 있었다.

1. **이름 우선순위 역전** (`7bf5e25`): `TOP_PICK_NAME_MAP`에 한국어 이름이 있어도, yfinance 캐시에서 가져온 영문 이름이 이를 덮어썼다. `name = TOP_PICK_NAME_MAP.get(...)` 후에 무조건 캐시 이름으로 재할당하는 코드 구조였다.

2. **fallback 매핑 부재** (`032ca03`): `sectors.json`에 없는 종목은 이름을 가져올 곳이 없어 티커 코드 그대로 표시됐다. `_FALLBACK_NAMES` 딕셔너리가 없었다.

3. **언어 혼재** (`2ecb874`): `_FALLBACK_NAMES`에 미국 종목이 한국어로 등록되어 있었다 ("브로드컴", "엔비디아" 등).

4. **검색 API 한글 조건** (`1c96ccc`): 네이버 자동완성 API를 한글 쿼리인 경우에만 호출하여, "lg" 같은 영문 입력으로는 한국 종목이 검색되지 않았다.

5. **shortName == ticker** (`a4d53fb`): yfinance의 `shortName`이 티커 심볼과 동일한 경우(LAKE, AI 등), 그대로 뉴스 검색어로 사용하면 엉뚱한 결과가 나왔다.

## 해결

```python
# 7bf5e25: 이름 우선순위 수정 - TOP_PICK_NAME_MAP을 최우선으로
name = TOP_PICK_NAME_MAP.get(_ticker_key(ticker), "")
if not name:  # MAP에 없을 때만 캐시 참조
    info_cached = _ANALYSIS_CACHE.get(f"info:{ticker}")
    ...

# 032ca03: 40개 종목 fallback 매핑 추가
_FALLBACK_NAMES = {"005380.KS": "현대자동차", ...}

# 2ecb874: US 종목은 영어, KR 종목은 한국어로 통일
_FALLBACK_NAMES = {"AVGO": "Broadcom", "NVDA": "NVIDIA", "005380.KS": "현대자동차", ...}

# 1c96ccc: 네이버 자동완성을 항상 먼저 호출
# (한글 조건 제거)

# a4d53fb: shortName이 티커와 같으면 longName/한국어 이름으로 대체
bare_ticker = normalized.replace(".KS", "").replace(".KQ", "")
if company_name.upper() == bare_ticker.upper() or len(company_name) <= 5:
    if long_name and long_name.upper() != bare_ticker.upper():
        company_name = long_name
```

## 교훈

- **종목명 결정은 명확한 우선순위 체인이 필요하다**: 수동 매핑 > 외부 API > yfinance shortName > longName > 티커 코드. 여러 소스에서 이름을 가져오면 반드시 우선순위를 문서화하고 코드에 반영해야 한다.
- **티커 심볼은 고유 식별자이지 표시 이름이 아니다.** 사용자에게 티커를 직접 보여주는 것은 항상 fallback의 마지막이어야 한다.
- **shortName을 검색어로 사용하면 안 된다.** 특히 1~5글자 영문 티커는 일반 단어와 충돌할 확률이 높다 (LAKE, AI, OPEN, PATH 등).
- **다국어 환경에서는 언어별 이름 관리 정책이 필요하다.** US 종목은 영어, KR 종목은 한국어라는 규칙을 코드에 강제해야 한다.
