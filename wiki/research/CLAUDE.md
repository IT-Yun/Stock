# wiki/research/ — 애널리스트 리포트 분석 누적

이 폴더의 목적: 한국·미국 sell-side 리포트, 공개 컨센서스 데이터, 자체 검증 결과를 **사실/의견 분리** 방식으로 누적한다. 산업 이해도 보강용 + value chain 매핑·sentiment 임계값의 self-audit.

## 핵심 원칙

1. **bias 차단** (memory 룰): broker target price·추천을 그대로 받지 않는다. 1차 사실(수치, 가이던스, 공급망 언급)만 추출 → 사업구조와 cross-check.
2. **사실/의견 명시 분리**: "{broker}는 X라고 본다" 형식. 사실은 따로 한 줄.
3. **여러 broker 의견 비교**: consensus vs outlier — 한쪽으로 쏠리면 신호. outlier 발견 시 "왜 이쪽만 다른가" 명시.
4. **paywall은 솔직하게**: 못 받은 건 "raw/research/에 PDF 필요"로 표기, 추정 금지.
5. **억지 매핑 금지** (memory 룰): broker가 X종목 매핑한다고 그대로 받지 말고 사업구조 다시 검증.

## 폴더 구조

```
wiki/research/
├── CLAUDE.md                    # 본 파일 — 워크플로우 가이드
├── index.md                     # 누적 인덱스 (브로커별/섹터별/종목별)
├── cross-check/                 # 자체 검증 (공개 컨센서스 vs 내 매핑)
│   ├── ai-semi.md
│   ├── battery.md
│   ├── smr-nuclear.md
│   └── ...
├── reports/                     # 사용자가 raw/research/에 올린 PDF 리포트 정제본
│   ├── samsung-secu/
│   │   ├── 2026-04_sk-hynix.md
│   │   └── 2026-04_lg-energy.md
│   ├── mirae/
│   ├── kbsec/
│   ├── morgan-stanley/
│   ├── jpmorgan/
│   └── ...
└── monthly-summary/             # 월별 누적 요약 (consensus 변화 추적)
    ├── 2026-04.md
    └── 2026-05.md
```

## 워크플로우 1 — 자체 cross-check (Phase 1, 자동화)

**언제**: 분기 1회 또는 value chain 매핑 변경 시.

**방법**:
1. 8 Phase 1 섹터 + 19 Phase 2 섹터 = 27개 섹터에 대해 agent 병렬 실행
2. 각 agent: WebSearch로 stock별 공개 컨센서스 수집 (Yahoo/Morningstar/Naver는 차단됨, aggregator 사이트 사용)
3. 결과를 `wiki/research/cross-check/{sector_id}.md`에 누적
4. 4 섹션 포맷: 종목별 컨센서스 / 내 작업물 검증 (지지/충돌/누락) / 새 인사이트 / 데이터 한계

**산출물 검증 항목**:
- value chain Tier 매핑이 컨센서스로 지지되는지
- 매핑된 종목 중 broker coverage 거의 없는 종목 (실효 노출 의심)
- 컨센서스에서 자주 언급되지만 내 매핑에 없는 종목 (추가 후보)
- broker가 추천했지만 사업구조 검증 시 노출 적은 종목 (제거 후보)

## 워크플로우 2 — PDF 리포트 ingest (Phase 2, 사용자 협업)

**필요한 이유**: 자체 검증으로 잡히는 건 공개 컨센서스 수준. 풀 분석가 thesis·산업 모델·hidden assumption은 풀 PDF 리포트에만 있다. paywall 사이트 (한국 sell-side, Seeking Alpha Premium, Bloomberg, Morningstar Premium)는 사용자 본인 계정으로 다운로드 후 폴더에 넣어주셔야 한다.

### 사용자 액션

1. 리포트를 `raw/research/{broker}/{ticker}-{YYYY-MM-DD}.pdf` 형태로 저장
   - 예: `raw/research/samsung-secu/000660-2026-04-15.pdf`
   - 한국: 삼성증권, 미래에셋, 한국투자, KB증권, NH투자, 하나증권, 키움증권 등
   - 미국: Morgan Stanley, JPMorgan, Goldman Sachs, BofA, Citi, Wells Fargo, Jefferies, Wedbush 등
2. `/ingest` 슬래시 커맨드 실행

### 제가 (AI가) 하는 일

1. **PDF 읽기** (Read tool, pages 파라미터로 분할 가능)
2. **추출** — 다음 4가지를 분리해서 정리:
   - **사실 (Facts)**: 인용된 수치, 가이던스, 공급망 언급, 일정·이벤트
   - **broker 의견 (Opinion)**: target price, rating, buy/sell call, thesis 요약 — 모두 "{broker}는 X라 본다" 형식
   - **위험 (Risk)**: broker가 명시한 downside risk, key uncertainty
   - **모델 가정 (Assumption)**: 매출 성장률, 마진 가정, 환율·원자재 가정
3. **사업구조 검증**: target price·추천을 그대로 받지 않고, 회사 매출 비중·사업부 구조 (IR 자료)와 cross-check. 매핑이 억지면 "broker는 X라 보지만 사업구조상 Y"라고 명시.
4. **wiki/research/reports/{broker}/{ticker}-{YYYY-MM}.md** 생성
5. **value chain 영향**: 리포트 내용이 기존 `wiki/macro/04-value-chain.md` 매핑과 충돌·보강하면 `wiki/research/cross-check/{sector}.md`에 추가
6. **monthly-summary 업데이트**: `wiki/research/monthly-summary/{YYYY-MM}.md`에 그 달의 broker 의견 변화 기록

### 페이지 템플릿 (`wiki/research/reports/{broker}/{ticker}-{YYYY-MM}.md`)

```markdown
---
title: "{broker} {종목명}({ticker}) — {YYYY-MM-DD}"
created: YYYY-MM-DD
updated: YYYY-MM-DD
broker: "{broker명}"
ticker: "{ticker}"
sector_id: "{매핑된 섹터 id}"
report_type: "기업분석" | "산업분석" | "이슈분석" | "Initiation"
target_price: {목표가 숫자}
rating: "BUY" | "HOLD" | "SELL" | "Outperform" | "Neutral" | "Underperform"
sources: ["raw/research/{broker}/{filename}"]
tags: [research, broker-report, {sector_tag}]
related: ["[[04-value-chain]]", "[[종목 wiki 페이지가 있다면]]"]
---

# {broker} {종목명}({ticker}) — {YYYY-MM-DD}

## 1. 요약 (One-line)

{broker}는 {종목}을 {rating}로 평가, 목표주가 {price}원 ({업사이드 %}). 핵심 thesis는 {1-2줄}.

## 2. 사실 (Facts — broker가 인용한 1차 자료)

- {수치 1, 출처 페이지·인용}
- {가이던스, 출처}
- {공급망 언급, 출처}
- {이벤트·일정, 출처}

## 3. broker 의견 (Opinion — 검증 전)

> ⚠️ 이 섹션은 broker의 주관적 view. 다음 섹션에서 사업구조와 검증한다.

- target price 산정 근거: {DCF? Multiple? 비교군?}
- 핵심 thesis 3-5점 (broker 인용)
- buy/sell call의 핵심 trigger

## 4. 사업구조 검증 (자체)

> memory 룰 적용: 데이터 매핑 전 기업 사업구조 기반 논리 검증, 억지로 끼워넣지 말 것.

- broker가 매출 X% 비중 사업부 Y 강조 → IR 자료·DART 공시 확인 → {일치/불일치}
- broker가 공급망 Z에 노출이라 함 → 실제 매출 기여도 {%} → {타당/과장/불명}
- broker가 가정한 시장 사이즈 → 1차 자료 (USGS·정부통계·산업협회)와 비교 → {합리/낙관/비관}

## 5. 위험 / 가정

- broker 명시 downside risks
- broker 핵심 모델 가정 (성장률, 마진, 환율, 원자재 가격)
- 가정이 깨지면 어떻게 되는가

## 6. value chain 영향

기존 [[04-value-chain]] 매핑 검증·보강:
- 지지하는 항목: ...
- 수정 필요 항목: ...
- 추가 후보: ...

## 7. 다른 broker 의견과 비교

| broker | rating | TP | 핵심 thesis |
|---|---|---|---|
| {broker A} | BUY | 280,000 | HBM 점유율 |
| {broker B} | HOLD | 220,000 | DRAM 사이클 우려 |

→ outlier가 있으면 표기. consensus 평균 대비 ±20% 벗어나면 별표.

## 8. 종합 판단 (사용자 의사결정용)

**broker 의견 (비편향 인용)**: ...
**자체 검증 결과**: ...
**추천 판단 보류 사유**: (사업구조 검증에서 충돌·불명확이 발견된 경우)
```

## 워크플로우 3 — 월별 요약

매월 말, 그 달에 ingest된 모든 리포트를 통합:

```markdown
# wiki/research/monthly-summary/{YYYY-MM}.md

## {YYYY-MM} broker 의견 변화

### 신규 ingest 리포트
- {broker} {ticker} ({date}) — {rating} → 새 thesis: ...

### Rating 변화
- {ticker}: {prev rating} → {new rating} by {broker}

### TP 변화 (≥10% 조정)
- {ticker}: {prev TP} → {new TP} by {broker}

### consensus 변화
- {sector}: 평균 TP {prev} → {new} ({N} broker 평균)

### outlier 의견
- {broker}는 {ticker}에 대해 평균 대비 {outlier 방향}: 사유 {요약}

### value chain 매핑 변경 후보
- 추가: {ticker} ({근거})
- 제거: {ticker} ({근거})
- 위 변경은 wiki/macro/04-value-chain.md 검토 후 적용
```

## 운영 규칙

1. **사실/의견 절대 섞지 마라**: 한 문장 안에서도 "{broker}는 ~라 본다"와 "실제로는 ~다"를 분리.
2. **paywall 인용 금지**: 사용자가 다운받은 PDF만 인용. WebFetch로 가져오지 못한 paywall 사이트 내용을 추정해서 쓰지 않는다.
3. **broker bias 패턴 인식**: 같은 broker가 같은 종목을 4분기 연속 BUY 추천 후 갑자기 HOLD = 신호. 한국 broker가 자기 IB cover 종목에 우호 — flag.
4. **outlier 존중**: 한 broker만 SELL인데 사업구조 검증으로 타당하면 그게 가장 가치 있는 의견. 다수결 따라가지 않는다.
5. **사용자 의사결정 분리**: 본 폴더는 "broker는 이렇게 봤다" 정보 제공. **매수·매도 판단은 사용자**.

## 관련 문서

- [[04-value-chain]] — 매핑이 검증·수정되는 단일 소스
- [[02-indicators]] — 섹터 sentiment의 watchlist 지표 정의
- [[05-regime-scoring]] — 원자재 regime의 Cause 분석 (Phase B와 연동)
- `~/.claude/projects/-Users-seungyunlee-Desktop-Stock/memory/feedback_analyst_reports.md` — bias 차단 메모리 룰
- `~/.claude/projects/-Users-seungyunlee-Desktop-Stock/memory/feedback_analysis_verification.md` — 사업구조 검증 메모리 룰
