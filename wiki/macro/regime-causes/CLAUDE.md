# wiki/macro/regime-causes/ — Phase B 원인 지속성 분석

## 이 폴더의 목적

[[05-regime-scoring]]의 **Phase B (수동 분석)** 산출물을 누적한다.

Phase A (`backend/services/commodity_regime_history.py`)는 매일 KST 06:00에 자동으로 5년 백분위·regime 라벨·매트릭 점수를 산출한다. 그러나 **"regime이 왜 바뀌었는가, 그 원인이 계속될 것인가"** 는 정량 모델로 답할 수 없다. 이 폴더는 그 정성적 분석을 채운다.

## 두 종류의 ingest

### 1. Phase A에서 regime 변화 감지된 항목

`Output/reports/commodity-regime-YYYY-MM-DD.md`에 "오늘 regime 변화 발생" 표가 떴을 때, 그 항목 각각에 대해:

- 파일명: `wiki/macro/regime-causes/{commodity_id}-{YYYY-MM}.md`
- 예: `uranium_etf-2026-04.md`, `copper-2026-05.md`

### 2. 무료 시계열이 없는 hidden bottleneck

`[[01-commodities]]`에서 `fetchable=False`로 표시된 항목 (헬륨-3, 이리듐, 갈륨, 디스프로슘, 네온/크립톤/크세논, GLP-1 펩타이드 CDMO 등). USGS Mineral Commodity Summaries / Johnson Matthey PGM Market Report / DOE 보고서를 분기 1회 (또는 이벤트 발생 시) 수동으로 ingest.

- 파일명: `wiki/macro/regime-causes/{commodity_id}-{YYYY-Q}.md`
- 예: `helium3-2026-Q2.md`, `dysprosium-2026-Q2.md`

## 페이지 템플릿

```markdown
---
title: "{원자재 한국어명} — 원인 분석 ({YYYY-MM 또는 YYYY-Q})"
created: YYYY-MM-DD
updated: YYYY-MM-DD
tags: [macro, regime-cause, {commodity_id}]
sources:
  - {1차 소스 URL 또는 식별자}
related:
  - "[[01-commodities#{원자재}]]"
  - "[[05-regime-scoring]]"
cause_classification: structural | transient | unknown   # 셋 중 하나
confidence: high | medium | low
---

# {원자재 한국어명} — 원인 분석 ({YYYY-MM 또는 YYYY-Q})

## 1. Regime 상태 (Phase A 산출)

- **현재 regime**: Sleeper / Breakout / Steady / Topping / Crash / Rebound
- **5년 백분위**: NN%
- **이전 regime**: {label} ({N}일 유지 후 변화)
- **지표 스냅샷**: 60d 수익률 +/-N%, vol z = +/-N, 12개월 trend +/-N%
- **Phase A 리포트 링크**: `Output/reports/commodity-regime-YYYY-MM-DD.md`

## 2. 가격 움직임의 원인 (사실)

원본 1차 소스에서 확인된 사실만 기술. 해석/추론은 3장에서.

- **공급측**: {광산 사고, 정부 통제, 신규 투자 등 — 정확한 날짜·규모·소스 인용}
- **수요측**: {수요 산업 변화, 신규 응용처 등}
- **재고/포지션**: {LME·CME 재고, COT 변화 등 — 가능한 경우}

> 인용 형식: "{사실} (출처: {소스 URL/이름}, {날짜})"

## 3. 원인 분류 — 핵심 판단

### Structural (구조적, 수년 지속 가능) — 다음 중 하나 이상이어야

- [ ] 광산 자체 고갈 / 신규 발견 부재 (수년 단위 자본투입 필요)
- [ ] 정부 수출 통제 / 제재 (정치적 해소 어려움)
- [ ] 신규 수요 산업 등장 (EV, AI 데이터센터, SMR 등)
- [ ] 환경 규제 (CBAM, IMO, 등)
- [ ] 대체재 부재 (기술적 1:1 대체 불가)

### Transient (일시적, 해소 시 되돌림) — 다음 중 하나 이상

- [ ] 단일 광산 사고 / 파업
- [ ] 일회성 sanction / 제재
- [ ] 날씨 충격 (단일 시즌)
- [ ] 한시적 OPEC 감산 / 재고 사이클
- [ ] 단기 투기 squeeze (LME 니켈 2022.03 패턴)

### Unknown — 위 둘 다 결정 못 함

데이터 불충분 또는 인과 불명확. 추천 보류.

**최종 판정**: Structural / Transient / Unknown ← {한 가지 선택, 위 체크리스트 근거 명시}

## 4. 시나리오 — 원인 지속/해소 시 가격 경로

### Case A: 원인이 계속될 경우
- 6개월 시계: {예상 가격 방향}
- 트리거: {다음에 일어나면 추세 재확인되는 이벤트}

### Case B: 원인이 해소될 경우
- 해소 시그널: {뭐가 일어나면 해소된 것}
- 6개월 시계: {예상 가격 방향}

## 5. 종목 매핑 (사업구조 검증)

> ⚠️ memory 룰: 데이터 매핑 전 기업 사업구조 기반 논리 검증 필수, 억지로 끼워넣지 말 것.

[[01-commodities#{원자재}]]에 사전 매핑된 KR/US 종목 중, **현재 시점에서 매핑이 여전히 유효한 종목만** 선별:

| 종목 | 영향 방향 | 노출도 검증 (사업구조 기반) | 추천 |
|---|---|---|---|
| {종목명(코드)} | 수혜/피해 | {매출 비중 N%, 사업부 X에서 사용 등 1차 소스} | Buy/Hold/Avoid |

**제외 사유 (있으면)**: {사전 매핑되어 있었으나 현재 사업구조상 해당 원자재 노출이 없거나 작은 종목 — 명시}

## 6. 추천 (Regime × Cause 매트릭스 적용)

[[05-regime-scoring#7-추천-매트릭스-regime--cause]] 표에 따라:

- **현재 Regime**: {label}
- **Cause 분류**: {Structural / Transient / Unknown}
- **매트릭스 결과**: Buy / Hold / Sell / Watch / Trade-Short / Trade-Long
- **신뢰도**: High (Structural + Breakout/Crash) / Mid / Low (Sleeper/Unknown)

**최종 추천**: {action} — {3장 원인 분류 + 5장 종목 검증 근거 요약, 2-3문장}

## 7. 검증 (분기 회고에서 채움)

| 회고 시점 | 가격 변화 | 추천 결과 | 비고 |
|---|---|---|---|
| 작성 후 +30일 | {%} | hit / miss | |
| 작성 후 +90일 | {%} | hit / miss | |
```

## 운영 규칙

1. **Phase A 리포트가 새 regime 변화를 띄우면 24시간 안에 해당 항목 분석 페이지 생성**. 그 안에 못 채우면 시그널이 식는다.
2. **사실 → 분류 → 시나리오 → 종목 → 추천** 순서 엄수. 추천부터 거꾸로 쓰면 cherry-pick 위험.
3. **Phase B 페이지는 한 번 작성 후 갱신만** 하고 삭제하지 않는다. 분기 회고에서 hit/miss 기록.
4. **Cause 판정이 Unknown이면 추천하지 않는다**. "어쨌든 사자/팔자"는 메모리 feedback 룰 위반.
5. **소스는 1차만** — Bloomberg 기사, 트위터 인용 등 2차 소스만으로 Structural 판정 금지. USGS·Johnson Matthey·정부 공시·거래소 공시·기업 IR이어야 한다.

## 분기 회고

`Output/reports/commodity-regime-backtest-YYYY-Q.md`에 분기 1회:
- 그 분기의 Phase B 페이지 모두 +30일 / +90일 hit-rate 평가
- regime × cause 조합별 적중률
- 임계값(`pct_5y` 25%/75%, `vol_z ±0.5/±1` 등) 재검토 필요 여부
- v1 → v2 잠금 해제 조건 충족 여부 ([[05-regime-scoring#10-2-v1-v2-잠금-해제-조건]])
