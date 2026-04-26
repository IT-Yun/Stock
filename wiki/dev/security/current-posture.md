---
title: "현재 보안 상태 평가"
created: 2026-04-18
updated: 2026-04-18
severity: high
category: web
status: open
sources:
  - backend/main.py
  - backend/api/members.py
  - backend/api/analysis.py
  - backend/api/news.py
  - backend/config.py
  - backend/services/news_crawler.py
  - frontend/src/api/client.ts
  - render.yaml
tags: [security, overview, audit]
---

## 위협

프로젝트 전반에 걸쳐 인증 체계의 구조적 약점, CORS 완전 개방, 입력 검증 부재 등 복합적인 보안 위협이 존재한다.

## 영향

- 비인가 사용자가 관리자 기능을 사용할 수 있음
- 외부에서 API를 무제한 호출 가능
- Gemini API 키가 URL 쿼리 파라미터에 노출되어 로그에 기록될 위험

## 대응

### 현재 잘하고 있는 보안 조치

1. **환경변수 기반 시크릿 관리**: API 키(Gemini, Finnhub, Supabase)를 모두 `os.getenv()`로 로드하고 `.env`는 `.gitignore`에 포함 (`backend/config.py`)
2. **.env 파일 git 제외**: `.gitignore`에 `.env`가 명시되어 있고, git 이력에 `.env` 파일이 커밋된 적 없음 (`.env.example`만 존재)
3. **Pydantic 모델 기반 요청 검증**: `VerifyRequest`, `MemberAction` 등 Pydantic BaseModel로 요청 body를 타입 검증 (`backend/api/members.py`)
4. **관리자 권한 분리**: `_require_admin()` 함수로 admin/member 역할 분리 구현 (`backend/api/members.py:81`)
5. **URL 인코딩 처리**: 프론트엔드에서 `encodeURIComponent()`로 파라미터 인코딩, 백엔드에서 `unquote()`로 디코딩 (`frontend/src/api/client.ts:99`, `backend/api/members.py`)
6. **SPA fallback에서 asset 분리**: `assets/` 경로 요청시 존재하지 않으면 404 반환 (index.html이 JS로 파싱되는 버그 방지) (`backend/main.py:289`)
7. **뉴스 크롤링 타임아웃 설정**: 외부 HTTP 요청에 `timeout=10` 설정 (`backend/services/news_crawler.py:45`)
8. **캐시를 통한 Rate Limit 보호**: 뉴스 3분, 분석 30분 TTL 캐시로 외부 API 남용 방지

### 취약한 부분

| # | 취약점 | Severity | 위치 | 설명 |
|---|--------|----------|------|------|
| 1 | 인증이 헤더 닉네임 기반 (비밀번호 없음) | **Critical** | `main.py:47` | `X-Auth-Nickname` 헤더만으로 인증. 누구나 닉네임만 알면 해당 사용자로 행세 가능 |
| 2 | CORS `allow_origins=["*"]` | **High** | `main.py:233` | 모든 도메인에서 API 호출 가능. `allow_credentials=True`와 함께 사용 중 |
| 3 | Gemini API 키가 URL에 노출 | **High** | `analysis.py:1260,2461` | `?key={api_key}` 형태로 URL에 포함. 서버 로그, 프록시 로그에 키 노출 위험 |
| 4 | GET 요청 전체 인증 면제 | **Medium** | `main.py:34` | 모든 GET /api/ 요청이 인증 없이 통과. 분석 데이터, 멤버 통계 등 노출 |
| 5 | Rate Limiting 없음 | **Medium** | `main.py` 전체 | API 엔드포인트에 요청 횟수 제한 없음. DDoS 또는 API 남용 가능 |
| 6 | `/api/refresh-now` POST 관리자 검증 부재 | **Medium** | `main.py:262` | AuthMiddleware가 닉네임만 확인하고 admin 여부는 미확인. 일반 멤버도 전체 데이터 새로고침 트리거 가능 |
| 7 | 뉴스 크롤링 SSRF 가능성 | **Low** | `news_crawler.py:40` | `keyword` 파라미터가 URL에 직접 삽입됨. 직접적 SSRF는 아니지만 의도치 않은 외부 요청 유발 가능 |
| 8 | requirements.txt 버전 미고정 | **Medium** | `backend/requirements.txt` | 모든 패키지가 버전 없이 명시. 빌드 시 취약한 버전이 설치될 수 있음 |

### 우선 수정해야 할 것

1. **[P0] 인증 체계 강화**: 최소한 비밀번호 또는 토큰 기반 인증 도입. 현재는 닉네임만 알면 누구나 관리자 행세 가능
2. **[P0] Gemini API 키 URL 노출 제거**: HTTP header(`x-goog-api-key`)로 전달하도록 변경
3. **[P1] CORS 도메인 제한**: 운영 도메인만 허용하도록 `allow_origins` 설정
4. **[P1] Rate Limiting 도입**: FastAPI 미들웨어 또는 slowapi 패키지 활용
5. **[P2] requirements.txt 버전 고정**: `pip freeze` 결과로 버전 핀 설정

## 우리 프로젝트 적용

이 프로젝트는 소규모 팀 내부용이지만, 공개 인터넷(Render)에 배포되어 있으므로 외부 공격 면적이 존재한다. 특히 Gemini API 키 노출과 인증 부재는 즉시 조치가 필요하다.

관련 페이지:
- [[auth-and-cors]] -- 인증/CORS 상세 분석
- [[api-input-validation]] -- 입력 검증 분석
- [[secrets-management]] -- 시크릿 관리 분석
- [[ai-agent-security]] -- AI 에이전트 보안
- [[dependency-audit]] -- 의존성 감사
