---
title: "API 입력 검증 분석"
created: 2026-04-18
updated: 2026-04-18
severity: medium
category: web
status: open
sources:
  - backend/api/analysis.py
  - backend/api/news.py
  - backend/api/members.py
  - backend/services/news_crawler.py
tags: [security, input-validation, injection, xss]
---

## 위협

### 1. 현재 입력 검증 현황

**검증이 존재하는 부분:**
- `members.py`: Pydantic `BaseModel`(`VerifyRequest`, `MemberAction`)로 요청 body 타입 검증
- `members.py:138`: `name.strip()`으로 공백 처리, 빈 문자열 체크
- `members.py:99`: `_normalize()`로 정규화 후 비교

**검증이 부재한 부분:**
- `analysis.py`의 모든 `{ticker}` 경로 파라미터 -- 길이, 형식, 허용 문자 검증 없음
- `news.py`의 `{sector_name}`, `{keyword}` 경로 파라미터 -- 검증 없음
- `analysis.py`의 `{query}` 검색 파라미터 -- 검증 없음
- `analysis.py`의 `{symbol}` 원자재 파라미터 -- 검증 없음

### 2. SQL/NoSQL Injection 가능성

**Supabase 쿼리** (`members.py`):
```python
sb.table("members").select("nickname, role").execute()
sb.table("members").insert({"nickname": name, "role": "member"}).execute()
sb.table("members").delete().eq("nickname", name).execute()
```

Supabase Python 클라이언트는 내부적으로 PostgREST를 사용하며, `.eq()`, `.insert()` 등은 파라미터화된 쿼리를 생성한다. 따라서 **직접적인 SQL Injection 위험은 낮다**.

그러나 `nickname` 값 자체에 대한 길이 제한이나 특수문자 필터링이 없으므로:
- 매우 긴 문자열 입력으로 DB 스토리지 남용 가능
- HTML/JS 코드를 닉네임으로 등록 가능 (Stored XSS 전제 조건)

### 3. XSS 가능성

**경로 1: 닉네임을 통한 Stored XSS**
- 사용자가 닉네임을 `<script>alert(1)</script>`로 등록 가능
- `POST /api/members/add`에 닉네임 형식 제한 없음
- `GET /api/members/list`에서 닉네임이 JSON으로 반환
- React 프론트엔드가 `dangerouslySetInnerHTML` 없이 렌더링한다면 React의 자동 이스케이프로 방어됨
- 그러나 API를 직접 소비하는 다른 클라이언트가 있다면 위험

**경로 2: 뉴스 크롤링 데이터를 통한 XSS**
- `news_crawler.py`에서 크롤링한 뉴스 제목/요약에 악성 스크립트가 포함될 수 있음
- `BeautifulSoup`의 `.get_text(strip=True)`로 HTML 태그는 제거되지만, HTML 엔티티나 특수 구성은 통과 가능
- 프론트엔드에서 뉴스 제목을 렌더링할 때 React가 자동 이스케이프하므로 일반적 XSS는 방어됨

**경로 3: 검색 쿼리 반영형 XSS**
- `GET /api/analysis/stock-search/{query}` 응답에 `query`가 그대로 반환됨 (`analysis.py:7067`):
  ```python
  return {"query": query, "results": []}
  ```
- JSON 응답이므로 브라우저가 직접 렌더링하지는 않지만, `Content-Type: application/json` 미설정 시 위험

### 4. ticker/keyword를 통한 외부 서비스 남용

`analysis.py`의 ticker 파라미터는 yfinance, Naver Finance, Gemini API 등 다수 외부 서비스에 그대로 전달된다:
```python
@router.get("/analysis/{ticker}")
def get_analysis(ticker: str) -> AnalysisResult:
    ...
```

악의적 사용자가 대량의 랜덤 ticker를 호출하면:
- yfinance Rate Limit 트리거로 서비스 장애
- Gemini API 과금 증가
- Naver/Google 크롤링에 이상 요청 발생

## 영향

- 외부 API 비용 증가 (Gemini API)
- yfinance Rate Limit으로 전체 서비스 장애
- Stored XSS 가능성 (닉네임 경유)
- DB 스토리지 남용

## 대응

### 즉시 적용
1. **ticker 형식 검증**: 허용 패턴 화이트리스트
   ```python
   import re
   TICKER_PATTERN = re.compile(r"^[A-Z0-9]{1,10}(\.(KS|KQ))?$", re.IGNORECASE)
   
   @router.get("/analysis/{ticker}")
   def get_analysis(ticker: str):
       if not TICKER_PATTERN.match(ticker):
           raise HTTPException(400, "Invalid ticker format")
   ```

2. **닉네임 형식 제한**:
   ```python
   if len(name) > 20 or not re.match(r"^[\w가-힣\s]+$", name):
       raise HTTPException(400, "닉네임은 20자 이내, 한글/영문/숫자만 허용")
   ```

3. **검색 쿼리 길이 제한**: `query` 파라미터를 50자 이내로 제한

### 중기
4. **TOP_PICK_SECTOR_MAP 기반 화이트리스트**: 등록된 종목만 Gemini API 호출 허용
5. **뉴스 데이터 sanitization**: 크롤링 결과에 HTML sanitizer 적용

## 우리 프로젝트 적용

React 프론트엔드의 자동 이스케이프 덕분에 XSS 위험은 낮은 편이다. 그러나 ticker 형식 검증이 없어 외부 API 남용이 가장 현실적인 위협이다. `TICKER_PATTERN` 검증 추가가 가장 비용 대비 효과가 큰 조치다.
