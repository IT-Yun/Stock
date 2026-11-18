---
title: "Auth 미들웨어가 정상 요청을 차단하는 패턴"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "072887c fix: 빈 화면 + 새로고침 루프 + 순위 로딩 해결"
  - "0457d5d fix: allow public read access to api endpoints"
  - "27fdb14 fix: replace BaseHTTPMiddleware with pure ASGI to eliminate 403 on GET"
  - "adec480 fix: 방문자 통계 0 — /api/members/visit POST가 auth 미들웨어에 차단"
tags: [bug, auth, middleware, 403, CORS]
---

## 증상

- 로그인한 사용자에게 빈 화면이 표시되거나, 403 에러 후 무한 새로고침 루프 발생
- 방문자 통계가 항상 0으로 기록됨
- 배포 전환 시 간헐적으로 GET 요청이 403으로 차단됨
- OPTIONS preflight 요청이 차단되어 CORS 에러 발생

## 원인

`AuthMiddleware`가 지나치게 넓은 범위의 요청을 인증 검사 대상으로 삼았다.

1. **OPTIONS preflight 미처리** (`072887c`): CORS preflight(OPTIONS) 요청에도 `X-Auth-Nickname` 헤더를 요구하여 브라우저의 cross-origin 요청이 전부 실패했다.

2. **GET 요청 차단** (`0457d5d`): 읽기 전용 GET API까지 인증을 요구했는데, `localStorage` 기반 헤더가 없거나 만료되면 정상 사용자도 빈 화면을 보게 됐다.

3. **BaseHTTPMiddleware 간헐 차단** (`27fdb14`): Starlette의 `BaseHTTPMiddleware`가 배포 전환 시 간헐적으로 GET 요청에 403을 반환했다. `call_next()`가 내부적으로 request body를 소비하면서 race condition이 발생.

4. **화이트리스트 누락** (`adec480`): `/api/members/visit` POST 엔드포인트가 auth 화이트리스트에 빠져 있었다. 프론트엔드는 로그인 전 방문 기록을 보내므로 `X-Auth-Nickname` 헤더가 없어 항상 403으로 차단됐다.

## 해결

```python
# 072887c: OPTIONS preflight 통과
if request.method == "OPTIONS":
    return await call_next(request)

# 0457d5d: GET은 무조건 통과
if request.method == "GET" and path.startswith("/api/"):
    return await call_next(request)

# 27fdb14: BaseHTTPMiddleware 제거, pure ASGI 미들웨어로 교체
class AuthMiddleware:
    async def __call__(self, scope, receive, send):
        if method in ("GET", "HEAD", "OPTIONS"):
            return await self.app(scope, receive, send)
        # POST/PUT/DELETE만 인증 검사

# adec480: visit 엔드포인트를 화이트리스트에 추가
if path in ("/api/members/verify", "/api/members/visit"):
    return await self.app(scope, receive, send)
```

## 교훈

- **Auth 미들웨어는 최소 권한 원칙으로 설계해야 한다.** 기본값은 "통과"이고, 변경을 가하는 요청(POST/PUT/DELETE)만 차단하는 것이 안전하다.
- **새 엔드포인트 추가 시 auth 화이트리스트 검토를 체크리스트에 포함할 것.** 인증 불필요 엔드포인트가 누락되면 기능이 완전히 죽지만 에러 로그가 남지 않아 발견이 늦다.
- **Starlette BaseHTTPMiddleware는 프로덕션에서 간헐적 문제를 일으킨다.** Pure ASGI 미들웨어가 더 예측 가능하고 성능도 좋다.
- **CORS preflight(OPTIONS)는 모든 미들웨어에서 무조건 통과시켜야 한다.**
