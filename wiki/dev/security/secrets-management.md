---
title: "시크릿/환경변수 관리 분석"
created: 2026-04-18
updated: 2026-04-18
severity: high
category: infra
status: open
sources:
  - backend/config.py
  - .env.example
  - .gitignore
  - render.yaml
  - backend/api/analysis.py
tags: [security, secrets, api-keys, environment]
---

## 위협

### 1. API 키 관리 현황

프로젝트에서 사용하는 외부 서비스 API 키:

| 서비스 | 환경변수 | 용도 | 위험도 |
|--------|----------|------|--------|
| Gemini AI | `GEMINI_API_KEY` | 체크리스트 검증, 뉴스 분석 | **High** -- 과금 발생 |
| Finnhub | `FINNHUB_API_KEY` | 미국 주식 펀더멘탈 | Medium -- 무료 티어 존재 |
| Supabase | `SUPABASE_URL`, `SUPABASE_KEY` | 멤버/방문 DB | **High** -- DB 접근 |

모든 키는 `backend/config.py`에서 `os.getenv()`로 로드:
```python
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY: str = os.getenv("SUPABASE_KEY", "")
FINNHUB_API_KEY: str = os.getenv("FINNHUB_API_KEY", "")
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
```

### 2. Gemini API 키 URL 노출 (Critical)

`backend/api/analysis.py`에서 Gemini API 호출 시 키를 URL 쿼리 파라미터로 전달한다:

```python
# analysis.py:1260
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"
resp = requests.post(url, json={...}, timeout=25)

# analysis.py:2461
url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}"

# analysis.py:2651 (동일 패턴)
```

**위험**:
- URL은 서버 로그(uvicorn, Render), 프록시 로그, 네트워크 모니터링 도구에 기록됨
- Render 대시보드의 로그에서 API 키가 평문으로 노출될 수 있음
- `requests` 라이브러리의 에러 메시지에 URL이 포함됨

**수정 방법**: HTTP 헤더로 전달
```python
url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
resp = requests.post(url, json={...}, headers={"x-goog-api-key": api_key}, timeout=25)
```

### 3. .env / render.yaml 분석

**.env 파일**:
- `.gitignore`에 `.env` 포함 -- git에 커밋되지 않음
- git 이력 확인 결과 `.env`가 커밋된 적 없음 (`.env.example`만 존재)
- `.env.example`에는 실제 키 값 없음 -- 안전

**render.yaml**:
```yaml
envVars:
  - key: PYTHON_VERSION
    value: "3.11"
  - key: NODE_VERSION
    value: "20"
  - key: CACHE_DIR
    value: /var/data/stock-cache
```
- `render.yaml`에는 비밀 키가 포함되어 있지 않음
- Gemini, Supabase, Finnhub 키는 Render 대시보드에서 환경변수로 설정하는 구조로 보임 -- 적절

### 4. Supabase 키 종류 미확인

`SUPABASE_KEY`가 `anon` key인지 `service_role` key인지 코드에서 확인 불가:
- `anon` key: Row Level Security(RLS) 적용, 클라이언트 노출 가능
- `service_role` key: RLS 우회, 절대 클라이언트 노출 금지

서버 사이드에서만 사용하므로 `service_role` key를 사용해도 직접적 위험은 낮지만, RLS 정책이 설정되어 있는지 확인 필요.

### 5. 기본값이 빈 문자열

```python
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
```

환경변수 미설정 시 빈 문자열로 동작한다. 에러 대신 기능이 조용히 비활성화되는데, 이는 의도된 동작이다 (`analysis.py:1218`: `if not api_key: return None`). 다만 Supabase 키가 없을 때 JSON 파일 fallback으로 전환되는 점은 데이터 일관성 리스크가 있다.

## 영향

- Gemini API 키 노출 시: 무단 사용으로 과금 발생
- Supabase 키 노출 시: 멤버 DB 무단 접근/수정
- Finnhub 키 노출 시: 타인의 Rate Limit 소모

## 대응

### 즉시 적용
1. **Gemini API 키를 HTTP 헤더로 전달**: URL 쿼리 파라미터 대신 `x-goog-api-key` 헤더 사용. `analysis.py`에서 3곳 수정 필요 (line 1260, 2461, 2651)
2. **Supabase RLS 정책 확인**: Supabase 대시보드에서 `members`, `visits` 테이블의 RLS 활성화 확인

### 중기
3. **키 로테이션 절차 수립**: 분기별 API 키 교체 프로세스
4. **Render 환경변수에 시크릿 타입 사용**: Render는 `secret` 타입 환경변수를 지원하며, 로그에 마스킹됨

### 장기
5. **시크릿 매니저 도입**: HashiCorp Vault 또는 AWS Secrets Manager (현재 규모에서는 불필요)

## 우리 프로젝트 적용

전반적으로 시크릿 관리는 양호하다. `.env`가 git에 노출된 적 없고, `render.yaml`에도 키가 없다. 가장 급한 조치는 Gemini API 호출 3곳에서 키를 URL에서 헤더로 옮기는 것이다. 코드 변경량은 적지만 보안 효과가 크다.
