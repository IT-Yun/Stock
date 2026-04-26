---
title: "Pure ASGI AuthMiddleware (BaseHTTPMiddleware 대체)"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/main.py
tags: [architecture, auth, middleware, fastapi, asgi]
---

## 결정

인증 미들웨어를 Starlette의 `BaseHTTPMiddleware`를 사용하지 않고, **ASGI 프로토콜을 직접 구현**하는 순수 ASGI 미들웨어로 작성한다.

```python
class AuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        # ... 인증 로직
        return await self.app(scope, receive, send)
```

### 인증 정책

- **GET/HEAD/OPTIONS**: 항상 통과 (읽기 전용 공개 접근)
- **POST/PUT/DELETE on /api/**: `X-Auth-Nickname` 헤더로 인증 확인
- **예외 경로**: `/api/members/verify`, `/api/members/visit`는 인증 불요
- 허용 멤버 목록은 `members.json`에서 동적 로드

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| `BaseHTTPMiddleware` | 요청 body를 버퍼링하여 메모리 낭비, StreamingResponse 문제, blocking 이슈 |
| FastAPI `Depends()` | 각 라우터마다 반복 선언 필요, 누락 위험 |
| JWT 토큰 인증 | 토큰 관리 복잡도 증가, 소규모 프로젝트에 과도 |
| API Key 방식 | 멤버별 키 관리 필요, 현재 닉네임 기반으로 충분 |

## 이유

- `BaseHTTPMiddleware`는 Starlette에서 공식적으로 성능 문제가 있다고 알려짐:
  - 모든 요청의 body를 메모리에 버퍼링
  - `StreamingResponse`와 호환 문제
  - `run_in_threadpool` 사용으로 불필요한 스레드 전환
- Pure ASGI는 zero-copy로 요청을 다음 미들웨어에 전달
- CORS 미들웨어 뒤에 배치하여 (Starlette이 순서를 역전하므로) preflight 요청이 정상 처리됨
- GET 요청은 아예 인증 로직을 타지 않아 성능 오버헤드 0

## 트레이드오프

- ASGI 프로토콜 직접 다루므로 코드 이해 난이도 높음 (`scope`, `receive`, `send`)
- `request.body()` 같은 편의 메서드 사용 불가 (raw bytes 직접 처리)
- 미들웨어 순서(CORS 뒤에 Auth)를 반드시 지켜야 하며, Starlette의 역순 적용을 이해해야 함
- 닉네임 기반 인증은 보안 수준이 낮음 (헤더 변조 가능)

## 관련 코드

- **`backend/main.py`** 17-61행: `AuthMiddleware` 클래스 전체
- **`backend/main.py`** 240-242행: 미들웨어 등록 순서 (CORS 뒤에 Auth)
- `get_all_allowed()`, `_normalize()` 함수를 `api.members`에서 임포트하여 동적 멤버 확인
