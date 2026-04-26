---
title: "인증/인가 & CORS 분석"
created: 2026-04-18
updated: 2026-04-18
severity: critical
category: web
status: open
sources:
  - backend/main.py
  - backend/api/members.py
  - frontend/src/api/client.ts
tags: [security, authentication, cors, authorization]
---

## 위협

### 1. AuthMiddleware -- 닉네임 기반 인증의 구조적 취약점

현재 인증 체계는 `X-Auth-Nickname` HTTP 헤더의 값만으로 사용자를 식별한다.

**코드 흐름** (`backend/main.py:46-54`):
```python
headers = dict(scope.get("headers", []))
nickname = headers.get(b"x-auth-nickname", b"").decode("utf-8", errors="ignore")
decoded = unquote(nickname)
allowed = get_all_allowed()
if decoded and _normalize(decoded) in allowed:
    return await self.app(scope, receive, send)
```

**프론트엔드** (`frontend/src/api/client.ts:98-104`):
```typescript
api.interceptors.request.use((config) => {
  const nickname = localStorage.getItem("stock-nickname");
  if (nickname) {
    config.headers["X-Auth-Nickname"] = encodeURIComponent(nickname);
  }
  return config;
});
```

**문제점**:
- 비밀번호, 토큰, 세션 등 비밀 정보 없이 닉네임만으로 인증
- `localStorage`에 닉네임 평문 저장 -- 브라우저 콘솔에서 변경 가능
- `curl -H "X-Auth-Nickname: 관리자닉네임" -X POST ...`로 관리자 권한 획득 가능
- `/api/members/verify` POST가 인증 면제(`main.py:42`) -- 닉네임 유효성을 누구나 확인 가능하므로 유효 닉네임 열거 가능

### 2. GET 요청 전체 인증 면제

`main.py:34`에서 모든 GET 요청이 인증 없이 통과한다:
```python
if method in ("GET", "HEAD", "OPTIONS"):
    return await self.app(scope, receive, send)
```

**노출되는 엔드포인트**:
- `GET /api/members/list` -- admin 확인은 라우터 레벨에서 수행하지만, AuthMiddleware는 통과
- `GET /api/analysis/{ticker}` -- 모든 종목 분석 데이터
- `GET /api/refresh-status` -- 서버 내부 상태 정보
- `GET /api/analysis/stock-search/{query}` -- 종목 검색

의도적으로 읽기 전용 공개 접근을 허용한 설계이지만, `/api/members/list`와 `/api/members/stats`는 라우터 레벨 admin 검증(`_require_admin`)이 GET 요청에도 적용되어 이중 방어가 작동한다.

### 3. CORS 완전 개방

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**문제점**:
- `allow_origins=["*"]`와 `allow_credentials=True` 동시 사용은 CORS 스펙상 브라우저가 실제로는 credential 전송을 차단하지만, 보안 의도가 모호
- 외부 악성 사이트에서 사용자 브라우저를 통해 API 호출 가능
- Render 배포 환경에서 도메인이 확정되어 있으므로 제한 가능

### 4. `/api/refresh-now` 권한 검증 부재

```python
@app.post("/api/refresh-now")
async def refresh_now():
    """Manually trigger a full data refresh (admin only)."""
    ...
```

docstring에 "admin only"라고 되어 있지만, AuthMiddleware는 닉네임이 allowed 목록에 있는지만 확인한다. admin 여부는 확인하지 않으므로 일반 member도 전체 데이터 새로고침을 트리거할 수 있다.

## 영향

- **계정 탈취**: 닉네임만 알면 해당 사용자의 모든 권한 행사 가능
- **관리자 권한 탈취**: 관리자 닉네임을 알면 멤버 추가/삭제 가능
- **닉네임 열거**: `/api/members/verify`로 유효 닉네임 무차별 대입 가능
- **서비스 남용**: 인증된 멤버가 `/api/refresh-now`로 서버 리소스 소모

## 대응

### 단기 (즉시)
1. **JWT 또는 세션 토큰 도입**: `/api/members/verify` 성공 시 서명된 토큰 발급, 이후 요청에 토큰 검증
2. **CORS 도메인 제한**: `allow_origins`를 Render 배포 도메인으로 한정
   ```python
   allow_origins=["https://stock-analyzer-xxxx.onrender.com"]
   ```
3. **`/api/refresh-now`에 admin 검증 추가**: 라우터 레벨에서 `_require_admin()` 호출

### 중기
4. **Rate Limiting on `/api/members/verify`**: 닉네임 열거 공격 방지 (IP당 분당 10회 등)
5. **민감 GET 엔드포인트 인증 적용**: `/api/refresh-status` 등 내부 정보 엔드포인트에 인증 추가

### 장기
6. **OAuth 2.0 / SSO 도입**: Google/Kakao 소셜 로그인으로 인증 강화
7. **RBAC 미들웨어 통합**: admin/member 역할을 미들웨어 레벨에서 검증

## 우리 프로젝트 적용

현재 이 프로젝트는 소규모 투자 스터디 팀용이므로 공격 동기는 낮지만, Render에 공개 배포되어 있어 누구나 접근 가능하다. 특히 닉네임 기반 인증은 `curl` 한 줄로 우회되므로, 최소한 JWT 토큰 발급 방식으로 전환하는 것이 필요하다.
