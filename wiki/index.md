---
title: Wiki Index
created: 2026-04-18
updated: 2026-04-26
sources: []
tags: [index, navigation]
---

# Wiki Index

Stock Analysis 프로젝트의 지식 베이스 목차.

## Macro (Phase 1+2+3 완료 — 27개 섹터 × locked-v1)

웹사이트 개편의 명세 토대. 4개 페이지 구조, 모두 변경 불가 (추가만 가능).

- [[01-commodities|원자재 모니터링 매트릭스]] (Phase 1) — **52개 원자재** × 8개 섹터 영향 매핑 + KR/US 종목. 헬륨-3·이리듐·GLP-1 펩타이드 CDMO 등 시장 저평가 병목 포함
- [[02-indicators|선행 지표 매트릭스]] (Phase 1+2) — **27개 섹터 × 178개 지표** (Phase 1: 8섹터 53개 + Phase 2: 19섹터 125개). 한국 산자부 수출·ASML EUV·CISA KEV·PJM 큐·DSCA FMS·PDUFA·SteamDB CCU·식약처 인허가·베트남 GSO 등 정부·공식 1차 소스만
- [[03-outlook|거시 전망 (Macro Outlook)]] (Phase 1) — 8개 거시 차원 33개 지표, 9개 시나리오 → 섹터 매핑표
- [[04-value-chain|Value Chain 페이지]] (Phase 3) — **27개 섹터 × 360+ KR 종목 + 100+ US 종목** Tier 0~5 매핑. Mermaid + 한국 소부장 cheat sheet. "엔비디아 어닝 → 어느 한국 소부장" 즉답
- [[05-regime-scoring|원자재 Regime 점수화 & 매매 추천]] (Phase A+B) — 28개 원자재 5년 백분위·breakout·vol regime 자동 계산 + 원인 지속성(Structural/Transient) 수동 분석 → Buy/Sell/Hold 추천 매트릭스. 매주 `Output/commodity-regime-YYYY-WW.md` 적재

## Dev (개발 지식 베이스)

같은 실수를 두 번 하지 않기 위한 개발 노하우 축적.

### Architecture (ADR — 아키텍처 결정 기록)

- [[adr-001-curl-cffi|ADR-001 curl_cffi 브라우저 위장 세션]] — yfinance rate limit 회피 (TLS 핑거프린트)
- [[adr-002-global-cache-strategy|ADR-002 메모리+디스크 2계층 캐시]] — `_ANALYSIS_CACHE` + `.cache/analysis/`, TTL 30분
- [[adr-003-singleflight-rate-limit|ADR-003 Singleflight + Rate Limit 세마포어]] — 동일 키 중복 요청 차단
- [[adr-004-pure-asgi-auth-middleware|ADR-004 Pure ASGI AuthMiddleware]] — BaseHTTPMiddleware 대체, GET 무인증
- [[adr-005-frontend-deduped-get|ADR-005 프론트엔드 dedupedGet + localStorage]] — in-flight 공유, 6시간 fallback
- [[adr-006-sequential-loading|ADR-006 Sequential Loading 전략]] — 단계적 데이터 로딩으로 rate limit 보호
- [[adr-007-background-workers|ADR-007 백그라운드 워커]] — warmup·keep-alive·daily-refresh daemon threads

### Bugs (버그 패턴 & 해결법)

- [[async-blocking-event-loop|async에서 동기 I/O로 이벤트 루프 차단]]
- [[auth-middleware-blocking|Auth 미들웨어가 정상 요청을 차단]]
- [[css-keyframes-collision|CSS @keyframes 이름 충돌]]
- [[external-service-fallback|외부 서비스 장애 시 fallback 부재]]
- [[rate-limit-and-zero-data|외부 API rate limit으로 빈 데이터/0값 표시]]
- [[spa-deploy-blank-screen|SPA 배포 후 빈 화면 (stale asset + 캐시)]]
- [[stock-name-display-failures|종목명이 티커/잘못된 언어로 표시]]
- [[useeffect-dependency-overload|useEffect 의존성 과다로 불필요한 리로드]]

### Security (보안 분석)

- [[current-posture|현재 보안 상태 평가]] (severity: high)
- [[auth-and-cors|인증/인가 & CORS 분석]] (severity: critical)
- [[secrets-management|시크릿/환경변수 관리 분석]] (severity: high)
- [[ai-agent-security|AI 에이전트 보안 분석]] (severity: medium)
- [[api-input-validation|API 입력 검증 분석]] (severity: medium)
- [[dependency-audit|의존성 취약점 감사]] (severity: medium)

### API / Crawling / Deployment / Lessons

- [[endpoints|API 엔드포인트 설계]] — `/api/*` 라우트, 응답 스키마, 인증 정책
- [[data-sources|크롤링/데이터 수집 패턴]] — yfinance·Naver·Google 뉴스·원자재 가격
- [[render-setup|Render 배포 설정]] — `render.yaml`, build.sh, 디스크 캐시, 환경변수
- [[obsidian-vault-git|Obsidian vault의 git 관리 방침]]

## Sectors

섹터별 분석 페이지 — AI/반도체, 바이오, 에너지, 방산, 우주, 양자컴퓨팅, 원자재 등

> 아직 페이지 없음. `wiki/sectors/` 에 추가 예정.

## Stocks

종목별 심층 분석 페이지 — 한국(KR) 및 미국(US) 주요 종목

> 아직 페이지 없음. `wiki/stocks/` 에 추가 예정.

## Predictions

종목/섹터 예측 모델 결과 및 백테스트 기록

> 아직 페이지 없음. `wiki/predictions/` 에 추가 예정.

## Technical

기술적 분석 지표·패턴 노트 (RSI, MACD, Bollinger 등)

> 아직 페이지 없음. `wiki/technical/` 에 추가 예정.

## Dev / Design

UI/UX 디자인 결정 기록 (before/after 스크린샷 포함)

> 아직 페이지 없음. `wiki/dev/design/` 에 추가 예정.

## Research / Cross-check (애널리스트 cross-check)

웹 공개 컨센서스 + sell-side 인용으로 자체 매핑 검증. 80+ 종목 9개 섹터 — broker bias 차단 룰 적용. [워크플로우 가이드](research/CLAUDE.md)

- [[research/index|cross-check 통합 인덱스]] — 9개 섹터 신뢰도 + critical 수정 항목 + 추가/제거 후보 + 다음 단계
- [[ai-semi|AI/반도체]] — 솔브레인 NVDA leading 방향 OK, 시차 추가 검증
- [[robotics|로봇]] — ⚠️ 에스비비테크 Optimus 공급 미확인, 종목코드 오기
- [[smr-nuclear|SMR/원자력]] — OKLO≠NuScale-SMR, CEG·VST 누락
- [[cybersec|사이버보안]] — wiki claim 4건 전부 검증 통과 ✅
- [[aerospace|우주항공/방산]] — DSCA → K-방산 G2G 직판매라 적용 안 됨
- [[biotech|생명공학]] — 펩트론 평가기간 연장, 알테오젠/에스티팜 격상
- [[quantum|양자컴퓨팅]] — 헬륨-3 superconducting 한정, IONQ trapped-ion 무관
- [[battery|이차전지]] — SKIET → 더블유씨피로 hidden alpha 라벨 교체
- [[hydrogen-energy|수소/에너지]] — PLUG/BLDP 컨센 망가짐, 효성중공업·S-Oil 분류 의심
