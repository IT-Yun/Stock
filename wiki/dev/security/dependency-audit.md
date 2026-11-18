---
title: "의존성 취약점 감사"
created: 2026-04-18
updated: 2026-04-18
severity: medium
category: infra
status: open
sources:
  - frontend/package.json
  - backend/requirements.txt
tags: [security, dependencies, supply-chain, audit]
---

## 위협

### 1. Backend -- requirements.txt 분석

```
fastapi
uvicorn[standard]
yfinance
curl_cffi
pandas
numpy
requests
beautifulsoup4
feedparser
pydantic
python-dotenv
supabase
```

**핵심 문제: 버전 미고정**

모든 패키지가 버전 지정 없이 명시되어 있다. `pip install -r requirements.txt` 실행 시 항상 최신 버전이 설치되며, 이는 다음 위험을 수반한다:

- **공급망 공격**: 패키지 메인테이너 계정 탈취 시 악성 코드 포함 버전 배포 가능
- **호환성 파괴**: 메이저 버전 업데이트로 기존 코드가 동작하지 않을 수 있음
- **재현 불가능한 빌드**: 같은 코드라도 설치 시점에 따라 다른 패키지 버전이 설치됨

**패키지별 보안 프로필**:

| 패키지 | 보안 관련 역할 | 주의사항 |
|--------|----------------|----------|
| `fastapi` | 웹 프레임워크 | 자체 보안은 양호, 버전에 따라 취약점 패치 여부 다름 |
| `requests` | HTTP 클라이언트 | SSL 검증 기본 활성화, 취약점 패치 이력 있음 |
| `beautifulsoup4` | HTML 파싱 | 파싱 전용이므로 직접적 취약점 낮음 |
| `curl_cffi` | HTTP 클라이언트 (yfinance rate limit 우회용) | C 바인딩 포함, 네이티브 코드 취약점 가능 |
| `supabase` | DB 클라이언트 | 인증 토큰 관리, 버전 중요 |
| `yfinance` | 금융 데이터 | 비공식 API 스크래핑, 자주 변경됨 |
| `feedparser` | RSS 파싱 | XML 파싱 취약점 이력 있음 (XXE 등) |
| `pydantic` | 데이터 검증 | v1/v2 호환성 이슈 |
| `pandas`/`numpy` | 데이터 처리 | C 확장 포함, 버전별 보안 패치 |

### 2. Frontend -- package.json 분석

```json
{
  "dependencies": {
    "@radix-ui/react-tooltip": "^1.2.8",
    "axios": "^1.7.9",
    "framer-motion": "^12.38.0",
    "lucide-react": "^1.8.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-router-dom": "^6.28.0",
    "recharts": "^2.15.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.0.0",
    "@types/react": "^18.3.12",
    "@types/react-dom": "^18.3.1",
    "@vitejs/plugin-react": "^4.3.4",
    "tailwindcss": "^4.0.0",
    "typescript": "^5.6.3",
    "vite": "^6.0.0"
  }
}
```

**양호한 점**:
- `^` (caret) 범위로 메이저 버전은 고정, 마이너/패치는 자동 업데이트
- `package-lock.json`이 있다면 정확한 버전이 lock됨 (확인 필요)
- 의존성 수가 적어 공격 표면이 작음

**주의 패키지**:

| 패키지 | 위험도 | 이유 |
|--------|--------|------|
| `axios` ^1.7.9 | Low | HTTP 클라이언트, SSRF 관련 패치 이력 |
| `vite` ^6.0.0 | Low | 빌드 도구, 개발 서버에서만 사용 |
| `react` ^18.3.1 | Low | 잘 관리되는 프로젝트 |

프론트엔드 의존성은 전반적으로 양호하다. 프로덕션 의존성이 8개로 최소화되어 있고, 잘 알려진 라이브러리만 사용한다.

### 3. 전이적(Transitive) 의존성

직접 의존성뿐 아니라 간접 의존성에도 취약점이 존재할 수 있다:
- `supabase` Python 패키지는 `httpx`, `gotrue`, `postgrest` 등 다수의 하위 의존성을 가짐
- `yfinance`는 내부적으로 `requests`, `lxml`, `appdirs` 등을 사용
- `curl_cffi`는 libcurl 네이티브 바인딩 포함

## 영향

- 알려진 취약점이 있는 패키지 버전이 설치될 경우 원격 코드 실행(RCE), 서비스 거부(DoS) 등 가능
- 빌드 재현성 부재로 배포 환경 간 불일치 발생 가능
- 공급망 공격 시 서버 전체 장악 가능

## 대응

### 즉시 적용
1. **requirements.txt 버전 고정**:
   ```bash
   pip freeze > requirements-lock.txt
   ```
   또는 최소한 주요 패키지 버전 명시:
   ```
   fastapi>=0.115,<1.0
   uvicorn[standard]>=0.32,<1.0
   requests>=2.32,<3.0
   supabase>=2.10,<3.0
   ```

2. **npm audit 실행**: 프론트엔드 취약점 확인
   ```bash
   cd frontend && npm audit
   ```

3. **pip-audit 실행**: 백엔드 취약점 확인
   ```bash
   pip install pip-audit && pip-audit
   ```

### 중기
4. **Dependabot 또는 Renovate 설정**: GitHub에서 자동 의존성 업데이트 PR 생성
5. **package-lock.json을 git에 커밋**: 프론트엔드 빌드 재현성 보장

### 장기
6. **CI/CD에 보안 스캔 통합**: GitHub Actions에서 `npm audit`, `pip-audit` 자동 실행
7. **SBOM(Software Bill of Materials) 생성**: 전체 의존성 목록 관리

## 우리 프로젝트 적용

프론트엔드는 의존성이 적고 잘 관리되어 양호하다. 백엔드 `requirements.txt`에 버전이 없는 것이 가장 큰 문제다. `pip freeze` 결과를 기반으로 버전을 고정하는 것이 첫 번째 단계이고, Render 배포 시마다 일관된 환경을 보장할 수 있다.
