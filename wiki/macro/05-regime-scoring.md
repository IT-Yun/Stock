---
title: 원자재 Regime 점수화 & 매매 추천 (Phase A+B)
created: 2026-04-26
updated: 2026-04-26
sources:
  - yfinance
  - World Bank Pink Sheet
  - LME
  - USGS Mineral Commodity Summaries
  - Johnson Matthey PGM Market Report
  - EIA STEO
tags: [macro, commodities, regime, scoring, recommendation]
status: locked-v1
phase: regime-v1
related:
  - "[[01-commodities]]"
---

# 원자재 Regime 점수화 & 매매 추천 (Phase A+B)

## 1. 페이지 철학

`[[01-commodities]]`는 **정적 신호 지도** (원자재 → 섹터 → 종목 인과 매핑)다. 본 페이지는 그 위에 얹히는 **동적 평가 레이어**로, 두 가지 질문에 답한다:

1. **regime 변화 감지**: "몇 년간 잠자던 원자재가 막 깨어나고 있나? 추락 후 막 반등 시작했나? 고점에서 둔화되고 있나?"
2. **원인 지속성 평가**: "이 변화는 구조적인가(수년 지속) 일시적인가(해소 시 되돌림)? 따라서 사야 하나, 팔아야 하나, 관찰할까?"

표면 가격이 아니라 **5년 맥락 + 변곡점 + 원인 분류**를 결합한다. "지금 비싸다/싸다"가 아니라 "**왜 지금 움직이는가, 이 원인이 계속되면 어디까지 가는가**"를 답한다.

원칙은 [[01-commodities]]와 동일: 인과가 명확하지 않으면 추천하지 않는다. 데이터가 없으면 공백으로 두고 억지로 매핑하지 않는다.

## 2. 운영 모델: Phase A (자동) + Phase B (수동)

### Phase A — Quant regime 점수 (매일 자동, KST 06:00)

무료 시계열 데이터로 5년 일봉 수집이 가능한 원자재만 대상. `backend/main.py`의 기존 `_run_daily_refresh` step 5에 통합되어 매일 KST 06:00에 자동 실행 (US 시장 마감 직후). 일요일에는 주간 요약 추가 생성.

산출물:
- `data/commodity_history/{id}.csv` — 5년 일봉 캐시 (incremental update)
- `data/commodity_regime_state.json` — regime_since, days_in_zone, prev regime 영속화
- `Output/reports/commodity-regime-YYYY-MM-DD.md` — regime 변화 발생 시에만 생성
- `Output/reports/commodity-regime-weekly-YYYY-Www.md` — 일요일 주간 요약

구현: `backend/services/commodity_regime_history.py`

### Phase B — 원인 지속성 분석 (수동, 변화 감지 시 24시간 내 + 분기 1회)

Phase A에서 regime 변화가 감지된 항목 + 무료 시계열이 없는 hidden bottleneck (헬륨-3, 이리듐, 갈륨, 디스프로슘 등) 대상. USGS·Johnson Matthey 월간 레포트, 정부 수출 통계 등을 수동으로 ingest하여 `wiki/macro/regime-causes/{commodity_id}-{YYYY-MM 또는 YYYY-Q}.md`에 누적.

워크플로우 가이드: `wiki/macro/regime-causes/CLAUDE.md`

## 3. Phase A 대상 원자재 (28개 — 직접 선물/현물 시계열 가능)

| ID | 이름 | yfinance ticker | 카테고리 | 비고 |
|---|---|---|---|---|
| crude_wti | WTI 원유 | CL=F | 에너지 | |
| crude_brent | Brent 원유 | BZ=F | 에너지 | |
| natgas_henry | Henry Hub 천연가스 | NG=F | 에너지 | |
| heating_oil | 난방유 | HO=F | 에너지 | |
| gasoline_rbob | RBOB 휘발유 | RB=F | 에너지 | |
| copper | 구리 | HG=F | 산업금속 | |
| iron_ore | 철광석 62% | TIO=F | 산업금속 | yfinance 결측 잦음 — fallback로 World Bank Pink Sheet 월간값 |
| gold | 금 | GC=F | 귀금속 | |
| silver | 은 | SI=F | 귀금속 | |
| platinum | 백금 | PL=F | 귀금속 | |
| palladium | 팔라듐 | PA=F | 귀금속 | |
| corn | 옥수수 | ZC=F | 농산물 | |
| soybean | 대두 | ZS=F | 농산물 | |
| wheat | 밀 | ZW=F | 농산물 | |
| sugar | 설탕 | SB=F | 농산물 | |
| coffee | 커피 | KC=F | 농산물 | |
| cotton | 면화 | CT=F | 농산물 | |
| cocoa | 코코아 | CC=F | 농산물 | |
| lumber | 목재 | LBR=F | 산업원자재 | |
| oats | 귀리 | ZO=F | 농산물 | |
| uranium_etf | 우라늄 (ETF 프록시) | URA, URNM | 에너지 | 직접 U3O8 시계열은 UxC 유료 — ETF로 추세 대용 |
| lithium_etf | 리튬 (ETF 프록시) | LIT | 희소금속 | 광산주 비중 → equity beta 혼재 주의 |
| rare_earth_etf | 희토류 (ETF 프록시) | REMX | 희소금속 | 동일 caveat |
| crack_321 | 3-2-1 크랙 스프레드 | (CL=F, RB=F, HO=F 합성) | 에너지 | 자체 계산 |
| copper_gold_ratio | 구리/금 비율 | (HG=F / GC=F) | 매크로 신호 | 위험선호도 프록시 |
| gold_silver_ratio | 금/은 비율 | (GC=F / SI=F) | 매크로 신호 | |
| platinum_gold_ratio | 백금/금 비율 | (PL=F / GC=F) | 매크로 신호 | |
| oil_natgas_ratio | 원유/천연가스 비율 | (CL=F / NG=F) | 매크로 신호 | |

**ETF 프록시 주의사항**: URA·LIT·REMX는 광산기업 주가 바스켓이라 equity beta(시장 위험)가 섞인다. 따라서 ETF regime이 변해도 "원자재 가격 자체가 움직였는가"는 별도 검증 필요. Phase B에서 USGS 월간 가격으로 재확인.

## 4. Phase B 대상 (수동 — hidden bottleneck)

[[01-commodities]]에서 강조한 항목 중 무료 일봉 시계열이 없는 것들. 분기 1회 USGS Mineral Commodity Summaries / Johnson Matthey PGM Market Report / DOE 보고서로 수동 업데이트.

- **희토류 개별 산화물**: 디스프로슘(Dy), 터븀(Tb), 네오디뮴(Nd) — Shanghai Metals Market 월간
- **반도체 가스**: 네온(Ne), 크립톤(Kr), 크세논(Xe) — 거래소 가격 비공개, 업계 레포트 인용
- **헬륨**: BLM 가격 + 민간 거래 추정치, 분기 변동
- **헬륨-3**: DOE 경매가, 연 1-2회만 갱신
- **이리듐**: Johnson Matthey 월간
- **갈륨/게르마늄/인듐**: USGS 월간 + 중국 수출 통계
- **흑연·코발트·망간**: Benchmark Mineral Intelligence (일부 무료) + LME 코발트
- **GLP-1 펩타이드 CDMO 가격**: 공개 시계열 없음 — 기업 IR 레포트 인용

**규칙**: Phase B 항목은 가격이 부재하면 **regime 점수 부여 금지**. 대신 "가용 정보: 마지막 USGS 보고 YYYY-MM, 해당 시점 가격, 코멘트"만 기록한다. 억지로 점수화하지 않는다.

## 5. Regime 분류 (5+1 카테고리)

각 Phase A 원자재에 매주 하나의 regime 라벨이 부여된다.

### 5.1 5년 가격 백분위 (`pct_5y`)

현재 가격이 5년 일봉 분포에서 차지하는 위치. 0% = 5년 최저, 100% = 5년 최고.

### 5.2 5개 핵심 지표

| 지표 | 정의 | 임계값 |
|---|---|---|
| `pct_5y` | 5년 가격 백분위 | — |
| `breakout_score` | 3년 고점 대비 거리 + 6개월 박스권 이탈 여부 | breakout = 3년 고점 돌파 후 30일 유지 |
| `vol_regime` | 60일 실현 vol vs 5년 평균 vol의 z-score | 압축: z<-1, 확장: z>+1 |
| `trend_12m` | 252일 선형회귀 기울기 / 현재가 (연율화 수익률) | 강세: >+15%, 약세: <-15% |
| `momentum_accel` | 최근 60일 기울기 vs 252일 기울기 비율 | 가속: >1.5, 둔화: <0.5 |

### 5.3 Regime 라벨 정의

| 라벨 | 조건 (전부 충족) | 의미 |
|---|---|---|
| **Sleeper** | `pct_5y` ≤ 25% AND `vol_regime` < -0.5 (압축) AND `trend_12m` ∈ [-5%, +5%] AND days_in_zone > 365 | 수년간 잠자는 중. 큰 움직임 직전 가능성. |
| **Breakout** | (지난 90일 내 `pct_5y` ≤ 30%였음) AND 현재 `pct_5y` ≥ 45% AND `vol_regime` > +0.5 (확장) AND 60일 수익률 > +20% | 저점 박스권 막 탈출. 추세 시작 가능성. |
| **Steady** | `pct_5y` ∈ [25%, 75%] AND `trend_12m` > 0 AND `vol_regime` ∈ [-1, +1] | 정상적 추세 진행. |
| **Topping** | `pct_5y` ≥ 75% AND `momentum_accel` < 0.7 (둔화) AND `vol_regime` > 0 | 고점에서 동력 약화. |
| **Crash** | 60일 수익률 < -25% OR (5년 고점 대비 < -40% AND 진입 후 60일 미경과) | 급락 진행 중. |
| **Rebound** | (지난 180일 내 Crash 이력) AND 30일 수익률 > +15% AND `vol_regime` 여전히 > 0 | 급락 후 반등 초기. |

**우선순위**: 라벨이 중복 적용 가능하면 Crash > Rebound > Breakout > Topping > Steady > Sleeper 순으로 1개만 부여.

### 5.4 days_in_zone 추적

각 원자재의 직전 regime 라벨과 진입일을 `Output/commodity-regime-state.json`에 영속화. 같은 라벨이 30일 이상 지속될 때만 "확정" 라벨, 그 미만은 "잠정"으로 표기.

## 6. 원인 지속성 분류 (Phase B 수동)

regime 변화가 감지되면, 원인을 다음 3개 중 하나로 분류:

### 6.1 Structural (구조적 — 수년 지속 가능)

가격 변동의 원인이 **수요/공급 구조 자체의 변화**에 있는 경우. 해소되려면 수년 단위 자본 투입이나 기술 대체가 필요.

예시:
- 광산 자체 고갈 / 신규 발견 부재 (구리 — Codelco 생산량 장기 감소)
- 정부 수출 통제 (중국 갈륨·게르마늄·희토류 — 2023.07 시행)
- 신규 수요 산업 등장 (리튬 — EV 보급률, 우라늄 — SMR·AI 데이터센터 전력)
- 환경 규제 (저유황 연료 IMO 2020, 탄소국경세 CBAM)

→ regime이 Sleeper/Breakout이면 **매수 후보**. Topping이어도 단기 조정은 매수 기회.

### 6.2 Transient (일시적 — 해소 시 되돌림)

특정 사건이 가격을 움직였고, 그 사건이 끝나면 가격도 원래대로 돌아갈 가능성이 높은 경우.

예시:
- 단일 광산 사고 (BHP 칠레 광산 파업)
- 일회성 sanction / 재고 사이클 (LME 니켈 squeeze 2022.03)
- 날씨 충격 (브라질 커피 서리)
- OPEC 한시적 감산 (분기 단위)

→ regime이 Topping/Rebound이면 **매도 후보** 또는 **단기 거래**. Crash이면 **매수 후보** (반등).

### 6.3 Unknown (확인 불가)

데이터 부족 또는 인과 불명확. 추천하지 않고 **관찰**만.

## 7. 추천 매트릭스 (Regime × Cause)

| Regime \ Cause | Structural | Transient | Unknown |
|---|---|---|---|
| **Sleeper** | Watch (catalyst 대기, 1차 매수 진입 검토) | Skip | Watch |
| **Breakout** | **Buy** (구조적 추세 시작 가능성) | Trade-Short (해소 후 되돌림 노림) | Watch |
| **Steady** | Hold (보유) | Hold | Hold |
| **Topping** | Trim (일부 수익실현) | **Sell** (사건 해소 임박) | Watch |
| **Crash** | Watch (바닥 확인 후 진입) | **Buy** (반등 초기 진입) | Watch |
| **Rebound** | **Buy** (추세 재개 가능성) | Trade-Long (단기 반등) | Watch |

**규칙**:
- Buy/Sell 추천은 **반드시 [[01-commodities]]의 인과 매핑을 거쳐 KR/US 종목으로 변환**. 원자재 자체를 직접 추천하지 않는다 (한국 개인투자자 접근성 문제).
- 종목 추천 시 [[memory feedback_analysis_verification]] 룰 적용: 기업 사업구조 검증 후 매핑. 억지로 끼워넣지 않는다.
- 추천 신뢰도 등급: **High** (구조적 + Breakout/Crash) / **Mid** (Steady·Rebound·Topping) / **Low** (Sleeper·Unknown).

## 8. 출력 포맷

### 8.1 매주 리포트: `Output/commodity-regime-YYYY-WW.md`

```markdown
# Commodity Regime Report — YYYY 주차 W

생성: YYYY-MM-DD KST 22:00
대상: Phase A 28개 원자재

## 이번 주 주목 (regime 변화 발생)

| 원자재 | 이전 regime | 현재 regime | 신뢰도 | 추천 | 관련 종목 |
|---|---|---|---|---|---|
| 우라늄 ETF (URA) | Sleeper (412일) | Breakout | Mid | Buy | [[01-commodities#우라늄]] 참조 |

각 항목별 상세:
- ## 우라늄 ETF (URA)
  - 5년 백분위: 32% → 58% (지난 60일 +24%)
  - vol regime: -0.8 (압축) → +1.4 (확장)
  - 추세: 12개월 +28% (가속)
  - 원인 (Phase B 분석): Structural — SMR 발주 가속, AI 데이터센터 전력 수요
  - 추천: Buy / 종목: Cameco(CCJ), 두산에너빌리티(034020) 외 [[01-commodities#우라늄]] 매핑
  - 위험: 신뢰도 Mid (ETF 프록시이므로 실제 U3O8 가격 USGS 분기 보고 재확인 필요)

## Steady / Hold (변화 없음)

| 원자재 | regime | 일수 | 트렌드 |
|---|---|---|---|

## 데이터 결측 / 결함

| 원자재 | 사유 |
|---|---|
| TIO=F (철광석) | 지난 주 yfinance 결측 3일 — World Bank Pink Sheet 월간값으로 fallback |
```

### 8.2 영속 상태: `Output/commodity-regime-state.json`

```json
{
  "updated": "2026-04-26",
  "items": {
    "uranium_etf": {
      "current_regime": "Breakout",
      "regime_since": "2026-04-19",
      "previous_regime": "Sleeper",
      "previous_regime_days": 412,
      "metrics": {
        "pct_5y": 0.58,
        "breakout_score": 0.71,
        "vol_regime_z": 1.4,
        "trend_12m": 0.28,
        "momentum_accel": 1.8
      }
    }
  }
}
```

## 9. False Signal 가드레일

다음 경우 regime 변화 신호 무시:

1. **거래일 부족**: 60일 이내 결측이 5일 초과면 그 주 점수 산출 skip
2. **선물 만기 롤오버 점프**: yfinance 연결 선물에서 만기일 ±2영업일 가격 변동은 무시 (CL=F 등)
3. **단일 거래일 spike**: 일중 ±10% 이동 후 다음날 절반 이상 되돌리면 "noise"로 처리
4. **규제 보고일 noise**: EIA 주간 재고(수요일), CFTC COT(금요일) 발표 직후 24시간 내 신호는 다음 영업일 마감 후 재확인
5. **ETF 프록시의 equity beta**: URA·LIT·REMX의 60일 수익률이 S&P500 60일 수익률과 0.7 초과 상관일 경우 "주식시장 동조"로 분류, 원자재 신호 신뢰도 1단계 하향

## 10. 백테스트 / 자기 검증 계획

### 10.1 분기 회고 (`Output/commodity-regime-backtest-YYYY-Q.md`)

각 분기말에 직전 분기의 추천 결과를 평가:
- Buy 추천 종목의 분기 수익률 vs S&P500 / KOSPI
- 추천 신뢰도(High/Mid/Low)별 hit rate
- 잘못 분류된 regime (오인된 Breakout, 놓친 Crash) 재분석

### 10.2 v1 → v2 잠금 해제 조건

본 스펙은 v1로 잠금. 다음 조건 충족 시에만 v2로 갱신:
- 분기 회고 4회 누적 (12개월 운영) 후
- 임계값(`pct_5y`, `vol_regime z`, `breakout_score` 등)이 명백히 false signal을 양산할 때
- v2 업데이트는 본 페이지에 append, 기존 v1 정의는 삭제하지 않고 보존 (히스토리 추적)

## 11. 구현 로드맵

| 순서 | 항목 | 산출물 | 상태 |
|---|---|---|---|
| 1 | 본 스펙 lock (locked-v1) | `wiki/macro/05-regime-scoring.md` | ✅ 2026-04-26 |
| 2 | Phase A 자동화 스크립트 | `backend/services/commodity_regime_history.py` | ✅ 2026-04-26 |
| 3 | Phase A daily cron 통합 | `backend/main.py` `_run_daily_refresh` step 5 | ✅ 2026-04-26 |
| 4 | Phase B 워크플로우 가이드 | `wiki/macro/regime-causes/CLAUDE.md` | ✅ 2026-04-26 |
| 5 | 첫 실행 검증 | `Output/reports/commodity-regime-{YYYY-MM-DD}.md` | 진행 중 |
| 6 | 분기 회고 1차 | `Output/reports/commodity-regime-backtest-2026-Q3.md` | 2026-09 예정 |

### 11.1 기존 시스템과의 관계

본 모듈은 기존 `services/macro_commodity.py` (832줄, 30분 캐시 기반 단기 점수)를 **대체하지 않고 위에 얹는다**:

- `macro_commodity.py`: 60일 Z-score, 1d/5d/20d/60d/120d 변화율, 급등/급락/장기추세 라벨, 매수/매도 타이밍 — **단기/실시간 신호용** (API `/api/macro/commodities`, `/movers`, `/feed`)
- `commodity_regime_history.py` (본 모듈): 5년 일봉 캐시, 5년 백분위, 3년 breakout, 변동성 regime z-score, momentum 가속, 6 regime 라벨 + persistence — **장기/regime 변화 감지용** (일일 리포트 + 주간 요약 markdown)

두 모듈은 데이터·실행 주기·산출물이 완전히 분리되어 있으며, 인과 매핑 (`[[01-commodities]]`)을 공통 토대로 사용한다.

## 12. 한계 명시 (Honest Limitations)

본 시스템의 신뢰성에 영향을 주는 요소:

- **무료 데이터의 일봉 결측**: yfinance는 한국 새벽 시간 갱신 지연 빈번. 매주 일요일 22:00 KST에 산출하지만, 결측 시 토요일 데이터 사용.
- **ETF 프록시의 한계**: 우라늄·리튬·희토류는 광산주 ETF이므로 원자재 가격 자체와 30-50% 괴리 가능. 진짜 가격 신호는 분기 1회 USGS로만 확정.
- **개별 희토류 산화물 결측**: 디스프로슘·터븀 등 핵심 hidden bottleneck은 자동화 불가. 분기 1회 수동 ingest에 의존.
- **regime 정의의 임의성**: 백분위 25%/75%, vol z-score ±1 등 임계값은 v1 임의 선택. 분기 회고에서 검증.
- **원인 분류의 주관성**: Structural/Transient 구분은 수동 판단. Phase B에서 [[memory feedback_analysis_verification]] 룰을 강제 적용하여 사업구조 기반 검증.

## 13. 변경 이력 (이 페이지 자체)

| 날짜 | 버전 | 변경 |
|---|---|---|
| 2026-04-26 | v1 (locked) | 초기 작성. Phase A 28개 + Phase B 수동 워크플로우 정의. 5+1 regime, 추천 매트릭스, false signal 가드레일 포함. |
