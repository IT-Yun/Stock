---
title: "Render 배포 설정"
created: 2026-04-18
updated: 2026-04-18
sources:
  - render.yaml
  - build.sh
  - backend/config.py
tags: [deployment, render, configuration]
---

# Render 배포 설정

---

## 1. Render 서비스 구성 (`render.yaml`)

| 항목 | 값 |
|------|-----|
| 서비스 타입 | Web Service |
| 서비스 이름 | `stock-analyzer` |
| 런타임 | Python |
| 플랜 | Starter |
| 빌드 명령어 | `bash build.sh` |
| 시작 명령어 | `cd backend && uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}` |
| Health Check | `/health` |

### 디스크 (Persistent Storage)

| 항목 | 값 |
|------|-----|
| 디스크 이름 | `stock-cache` |
| 마운트 경로 | `/var/data` |
| 크기 | 5GB |

디스크 캐시 디렉토리: `/var/data/stock-cache` (환경변수 `CACHE_DIR`로 설정)

### 환경변수 (render.yaml에 정의된 것)

| 변수 | 값 | 용도 |
|------|-----|------|
| `PYTHON_VERSION` | 3.11 | Python 버전 |
| `NODE_VERSION` | 20 | Node.js 버전 (프론트엔드 빌드용) |
| `CACHE_DIR` | `/var/data/stock-cache` | 디스크 캐시 경로 |

---

## 2. 빌드 프로세스 (`build.sh`)

순차 실행:

1. **백엔드 의존성 설치**: `pip install -r backend/requirements.txt`
2. **프론트엔드 의존성 설치**: `cd frontend && npm install`
3. **프론트엔드 빌드**: `npm run build`
4. **검증**: `ls -la frontend/dist/`

빌드 결과물: `frontend/dist/` 디렉토리가 생성되며, 백엔드(`main.py`)가 이를 정적 파일로 서빙한다.

---

## 3. 애플리케이션 설정 (`backend/config.py`)

`Settings` 클래스가 환경변수를 읽어 설정을 구성한다.

### 서버 설정

| 환경변수 | 기본값 | 용도 |
|----------|--------|------|
| `API_HOST` | `0.0.0.0` | 서버 바인드 주소 |
| `PORT` / `API_PORT` | `8000` | 서버 포트 (Render는 `PORT` 제공) |
| `SECTOR_DATA_PATH` | `{프로젝트루트}/data/sectors.json` | 섹터 메타데이터 파일 경로 |
| `NEWS_SOURCES` | `naver,google` | 뉴스 소스 (쉼표 구분) |
| `CACHE_DIR` | `""` (빈 문자열) | 디스크 캐시 디렉토리 |

### 외부 서비스 키

| 환경변수 | 용도 |
|----------|------|
| `SUPABASE_URL` | Supabase 프로젝트 URL |
| `SUPABASE_KEY` | Supabase API 키 (멤버 관리/방문 기록) |
| `FINNHUB_API_KEY` | Finnhub API 키 (미국 주식 펀더멘털) |
| `GEMINI_API_KEY` | Google Gemini API 키 (체크리스트 검증/분석) |

### Rate Limit 관련 환경변수 (runtime_controls.py)

| 환경변수 | 기본값 | 용도 |
|----------|--------|------|
| `YFINANCE_MAX_CONCURRENCY` | `2` | yfinance 동시 호출 수 제한 |
| `HTTP_MAX_CONCURRENCY` | `6` | 외부 HTTP 요청 동시 수 제한 |
| `YFINANCE_MIN_INTERVAL` | `0.5` (초) | yfinance 호출 간 최소 간격 |

---

## 4. 프론트엔드 서빙 아키텍처

`backend/main.py`에서 SPA를 직접 서빙한다:

1. `/assets/*`: `frontend/dist/assets/` 정적 파일 (Vite 빌드 결과)
2. `/api/*`: FastAPI 라우터 (위 경로와 충돌 방지)
3. `/{그 외 모든 경로}`: `frontend/dist/index.html` 반환 (SPA 라우팅)
   - `Cache-Control: no-cache` 헤더로 항상 최신 HTML 제공
   - `/assets/`로 시작하는데 파일이 없으면 404 반환 (HTML을 JS로 파싱하는 에러 방지)

---

## 5. 미들웨어 구성

`main.py`에서 다음 순서로 미들웨어가 적용된다:

1. **CORS Middleware**: 모든 origin 허용
2. **AuthMiddleware**: POST/PUT/DELETE 요청에 대해 `X-Auth-Nickname` 헤더 검증 (멤버 인증)

---

## 6. 백그라운드 작업

- **Daily Refresh**: 매일 데이터 갱신 (`_run_daily_refresh`)
- `/api/refresh-now`로 수동 트리거 가능
- `/api/refresh-status`로 상태 확인
