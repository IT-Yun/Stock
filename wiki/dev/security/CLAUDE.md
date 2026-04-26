# wiki/dev/security/ — 보안 지식 베이스

웹사이트 + AI 에이전트 보안 관련 지식을 축적하는 공간.

## 다루는 영역

### 웹 보안 (OWASP Top 10 기반)
- XSS (Cross-Site Scripting)
- SQL/NoSQL Injection
- CSRF (Cross-Site Request Forgery)
- 인증/인가 취약점
- API 보안 (rate limit, input validation)
- CORS 설정
- 환경변수/시크릿 관리

### AI 에이전트 보안
- Prompt Injection (직접/간접)
- Tool Use 악용 (파일 시스템, 네트워크 접근)
- 데이터 유출 (PII, API 키)
- AI 출력 신뢰성 검증
- 에이전트 권한 최소화 원칙
- MCP 서버 보안

### 인프라 보안
- Render 배포 보안 (환경변수, HTTPS)
- Supabase RLS (Row Level Security)
- 의존성 취약점 (npm audit, pip audit)

## 페이지 구조

```yaml
---
title: "보안 이슈/패턴 제목"
created: 2026-04-18
updated: 2026-04-18
severity: critical | high | medium | low
category: web | ai-agent | infra
status: mitigated | open | monitoring
sources: []
tags: [security, 관련태그]
---
```

- `## 위협` — 어떤 공격/취약점인가
- `## 영향` — 악용되면 뭐가 위험한가
- `## 대응` — 어떻게 방어하는가
- `## 우리 프로젝트 적용` — 현재 코드에서 어떻게 적용했는가
