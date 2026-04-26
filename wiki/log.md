---
title: Wiki Change Log
created: 2026-04-18
updated: 2026-04-26
sources: []
tags: [log, changelog]
---

# Wiki Change Log

| 날짜 | 변경 내용 | 관련 페이지 |
|------|----------|------------|
| 2026-04-26 | **9개 섹터 cross-check 통합 완료 + value chain critical 패치** — Hidden Alpha 재정렬: 에스비비테크 "진짜 알파" → "thematic, Optimus 공급 미확인"으로 격하, 펩트론 코드 217340→087010 정정 + "선명한 알파" → "옵션 가치" 톤다운 (LLY 본계약 미체결 평가기간 연장), SKIET hidden alpha 회수 → 더블유씨피로 교체 (FEOC base film 면제 후), 알테오젠/에스티팜/삼성바이오 격상, CEG·VST(원전 운용사) 신규. backend `_HIDDEN_ALPHA_TOP` + wiki/macro/04-value-chain.md 동시 패치 | [[research/index]], 04-value-chain, backend/api/macro.py |
| 2026-04-26 | **wiki/research/ 신규 폴더 + 9개 섹터 cross-check 작성** — AI/반도체·로봇·SMR/원자력·사이버보안·우주항공/방산·생명공학·양자컴퓨팅·이차전지·수소/에너지. 9개 agent 병렬 실행, 80+종목 공개 컨센서스 + sell-side 인용으로 자체 매핑 검증 | [[research/index]], wiki/research/cross-check/* |
| 2026-04-26 | **wiki/research/CLAUDE.md 작성** — 애널리스트 리포트 ingest 워크플로우. PDF 수집 (raw/research/) → 사실/의견 분리 추출 → 사업구조 검증 → 월별 누적. broker bias 차단 룰 명시 | wiki/research/CLAUDE.md |
| 2026-04-26 | **Cybersecurity 섹터 컨센서스 교차 검증 작성** — CRWD/PANW/FTNT/ZS/S/OKTA/NET + KR 안랩·이글루·윈스·시큐브 11종 애널리스트 TP. CRWD outage 회복(Gross retention 97%, FY26 ARR $5.25B) + PANW XSIAM AI ARR $545M(+2.5x) 매출화 입증 + KR structural underperform 확정 | [[cybersec]], index.md |
| 2026-04-26 | **원자재 Regime Phase A 구현 완료** — `backend/services/commodity_regime_history.py` (5년 일봉 캐시 + 25개 항목 regime 분류 + state 영속화 + 일일/주간 리포트). 기존 `_run_daily_refresh` step 5에 통합되어 매일 KST 06:00 자동 실행. 첫 실행 25/25 성공 → `Output/reports/commodity-regime-2026-04-26.md` | `commodity_regime_history.py`, [[05-regime-scoring]] |
| 2026-04-26 | **Phase B 워크플로우 가이드 작성** — `wiki/macro/regime-causes/CLAUDE.md`. regime 변화 감지 시 24시간 내 사실/원인분류(Structural/Transient)/시나리오/종목매핑(사업구조검증)/추천 순으로 누적 | `regime-causes/CLAUDE.md` |
| 2026-04-26 | **원자재 Regime 점수화 v1 (locked) 작성** — Phase A 자동화 대상 정의 + Phase B 수동 hidden bottleneck 워크플로우 + 6 regime 라벨 + 추천 매트릭스(Regime × Cause) + false signal 가드레일. 기존 `macro_commodity.py` 단기 점수 위에 history 레이어로 얹힘 | [[05-regime-scoring]], index.md |
| 2026-04-26 | [lint] index.md 동기화 — `## Dev` 섹션 신규 추가 (architecture 7 + bugs 8 + security 6 + api·crawling·deployment·lessons 4 = 25개 페이지 등록) | index.md |
| 2026-04-26 | [lint] index.md 유령 카테고리 제거 — `concepts/`, `strategies/`, `market/` 폴더 미존재 → 항목 삭제 | index.md |
| 2026-04-26 | [lint] index.md 빈 폴더 표기 추가 — `predictions/`, `technical/`, `dev/design/` "아직 페이지 없음" 명시 | index.md |
| 2026-04-26 | [lint] macro frontmatter 표준화 — `source:` (str) → `sources:` (list) 4건 변환 | [[01-commodities]], [[02-indicators]], [[03-outlook]], [[04-value-chain]] |
| 2026-04-18 | Wiki 시스템 초기화 — raw/, wiki/, Output/ 폴더 구조 생성 | index.md |
| 2026-04-25 | Macro Outlook v1 (locked) 작성 — 8개 거시 차원, 33개 지표, 9개 시나리오 → 섹터 매핑표 | [[03-outlook]], index.md |
| 2026-04-25 | 선행 지표 매트릭스 v1 (locked) 작성 — 8개 섹터 × 53개 지표, 정부·공식 1차 소스만 (한국 산자부 수출, ASML book-to-bill, CISA KEV 등) | [[02-indicators]], index.md |
| 2026-04-25 | 원자재 모니터링 매트릭스 v1 (locked) 작성 — 52개 원자재 × 8개 섹터 매핑, 헬륨-3·이리듐·GLP-1 CDMO 등 hidden bottleneck 포함 | [[01-commodities]], index.md |
| 2026-04-25 | **Macro Phase 1 완주** — 4페이지 구조 중 3개 완성 (commodities·indicators·outlook) | wiki/macro/ |
| 2026-04-25 | **Macro Phase 2 완주** — 19개 섹터 확장 (이차전지·EV·EV소재·조선·철강·디스플레이·플랫폼·게임·K콘텐츠·화장품·음식료·유통·의류·건설·금융·통신·지주사·의료기기·호텔레저), 125개 추가 지표 [[02-indicators]] append | [[02-indicators]], index.md |
| 2026-04-25 | **Macro Phase 3 완주** — Value Chain 페이지 신규 생성. 27개 섹터 × Tier 0~5 × 360+ KR 종목 + 100+ US 종목. Mermaid 다이어그램 + 한국 소부장 요약표 + 신호 전이 cheat sheet | [[04-value-chain]], index.md |
| 2026-04-25 | **🎉 사이트 개편 명세 완료** — 4페이지(commodities·indicators·outlook·value-chain) locked-v1. 다음 단계: 프론트엔드/백엔드 구현 → /macro/* 신규 라우트 4개 | wiki/macro/ 전체 |
