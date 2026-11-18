## 프로젝트 개요

Stock Analysis Platform — FastAPI + React/Vite 기반 주식 분석 웹앱
- 8개 섹터(AI/반도체, 로봇, SMR/원자력, 사이버보안, 우주항공, 생명공학, 양자컴퓨팅, 수소/에너지)의 한미 주식 분석
- 기술적 지표(RSI, MACD, Bollinger, SMA), 뉴스, 원자재 가격, 체크리스트 기반 종합 점수 제공
- Render에 배포, Supabase를 회원/방문 DB로 사용

## 기술 스택

- **Backend**: Python 3.11, FastAPI, yfinance, curl_cffi, BeautifulSoup, Supabase, Google Gemini API
- **Frontend**: React 18, TypeScript, Vite, Recharts, Axios, Tailwind CSS, Lucide Icons
- **배포**: Render (Starter plan), 5GB 디스크 캐시, uvicorn 2 workers
- **외부 API**: yfinance(주가), Finnhub(US 펀더멘탈), Gemini(AI 체크리스트), Naver/Google(뉴스)

## 프로젝트 구조

```
backend/
  main.py              # FastAPI 앱, AuthMiddleware, 백그라운드 워커
  config.py            # 환경변수 기반 설정 (Settings 클래스)
  api/
    analysis.py        # /api/analysis/* — 기술분석, 체크리스트, 예측, 랭킹
    sectors.py         # /api/sectors — 섹터 목록, top-ranked
    news.py            # /api/news/* — 섹터별/키워드 뉴스
    members.py         # /api/members/* — 회원 관리, 방문 추적
  services/
    stock_data.py      # yfinance 래퍼, 글로벌 캐시
    technical_analysis.py  # RSI, MACD, Bollinger 계산
    commodity_data.py  # 원자재 가격 조회
    news_crawler.py    # Naver/Google 뉴스 크롤링
    fundamentals.py    # Finnhub 펀더멘탈 데이터
    research.py        # 애널리스트 리포트, SEC 공시
    runtime_controls.py  # HTTP/yfinance rate limit 세마포어
  models/schemas.py    # Pydantic 모델
frontend/
  src/
    App.tsx            # 라우팅 (/, /list, /sector/:id, /stock/:ticker)
    api/client.ts      # Axios 클라이언트, 중복요청 제거, localStorage 캐시
    data/sectors.ts    # 8개 섹터 정의 (종목, 리스크, 원자재, 성장곡선)
    types/index.ts     # TypeScript 인터페이스
    components/        # React 컴포넌트 (Layout, SectorMindMap, AdminPanel 등)
data/
  sectors.json         # 섹터-종목 매핑 설정
  members.json         # 회원 목록 (Supabase fallback)
render.yaml            # Render 배포 설정
```

## 핵심 아키텍처 패턴

- **AuthMiddleware (Pure ASGI)**: GET은 인증 없이 통과, POST/PUT/DELETE만 `X-Auth-Nickname` 헤더로 인증. BaseHTTPMiddleware 사용 안 함
- **글로벌 캐시 (메모리 + 디스크)**: `_ANALYSIS_CACHE` dict 기반 메모리 캐시 + `.cache/analysis/` 디스크 캐시. TTL 30분
- **curl_cffi 세션**: yfinance rate limit 회피를 위해 curl_cffi 사용 (브라우저 TLS 핑거프린트)
- **Singleflight 패턴**: `_SINGLEFLIGHT_LOCK` + `_SINGLEFLIGHT_EVENTS`로 동일 키 중복 요청 방지
- **Rate Limit 보호**: `runtime_controls.py`의 세마포어로 동시 HTTP/yfinance 호출 수 제한
- **백그라운드 워커 (daemon threads)**:
  - `_warmup_cache`: 시작 시 섹터 + 원자재 캐시 워밍
  - `_warmup_checklist_scores`: 30초 후 Gemini 체크리스트 점수 사전 계산
  - `_keep_alive`: 10분마다 self-ping (Render 슬립 방지)
  - `_daily_refresh_worker`: KST 06:00 전체 데이터 갱신
- **프론트엔드 중복요청 제거**: `dedupedGet`으로 동일 URL in-flight 요청 공유, localStorage 6시간 캐시 fallback
- **SPA 서빙**: FastAPI가 프로덕션 빌드된 `frontend/dist/`를 직접 서빙, catch-all로 React Router 지원

## 개발 규칙

- 한국어 UI 기본 (에러 메시지, 버튼 텍스트 등)
- yfinance 호출 최소화: 캐시 우선, sequential 로딩, rate limit 세마포어 사용
- 캐시 TTL 30분 (`ANALYSIS_CACHE_TTL = 1800`)
- 새 종목 추가 시 `frontend/src/data/sectors.ts`의 `SECTORS` 배열과 `backend/api/analysis.py`의 `TOP_PICK_SECTOR_MAP` 동기화 필요
- Render 배포 시 `build.sh` 실행 (프론트엔드 빌드 포함), 디스크 캐시 `/var/data/stock-cache`
- Supabase 연결 실패 시 JSON 파일 fallback 자동 전환
- Axios 요청에 자동 retry (최대 2회, 1.5초 간격)

## LLM Wiki 운영 규칙

Karpathy의 LLM Wiki 패턴 기반:

1. **raw/는 절대 수정 금지** — 원본 자료는 불변. 요약/편집은 wiki/에서만
2. **wiki 변경 시 index.md + log.md 필수 업데이트** — 변경 내역 추적
3. **Wikilink 형식 사용** — `[[페이지명]]` 또는 `[[페이지명|표시텍스트]]`
4. **YAML frontmatter 필수** — 모든 wiki 페이지에 title, source, created, updated 메타데이터
5. **소스 요약은 사실만** — 의견/해석 추가 금지, 원문에 있는 정보만 기술
6. **새 페이지보다 기존 페이지 업데이트 우선** — 중복 방지
7. **index.md 항목 120자 이내** — 간결한 한 줄 설명
8. **Output/은 결과물 전용** — 분석 결과, 생성된 보고서 저장
9. **커밋 메시지에 변경 파일 명시** — `wiki: update [[페이지명]]`
10. **검증 후 기록** — 데이터 매핑 전 기업 사업구조 기반 논리 검증 필수

## 폴더 구조 (LLM Wiki)

```
raw/         # 불변 원본 자료 (PDF, 텍스트, 스크린샷 등) — 수정 금지
wiki/        # AI 컴파일 위키 — index.md(목차), log.md(변경이력)
Output/      # 분석 결과물, 생성된 보고서
```

## 스킬

- `/ingest` — 새 자료를 raw/에 저장하고 wiki/에 요약 페이지 생성
- `/query` — 위키 기반으로 질문에 답변 (RAG 패턴)
- `/lint` — 위키 정합성 검사 (깨진 링크, frontmatter 누락, index 동기화)
