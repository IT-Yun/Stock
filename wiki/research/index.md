---
title: 애널리스트 cross-check 통합 인덱스
created: 2026-04-26
updated: 2026-04-26
sources:
  - WebSearch (multi-source aggregation)
  - stockanalysis.com
  - marketbeat.com
  - public.com
  - tickernerd.com
  - fool.com
  - benzinga.com
  - investing.com
  - mexc.com
  - cnbc.com
tags: [research, cross-check, index]
related:
  - "[[04-value-chain]]"
  - "[[02-indicators]]"
---

# 애널리스트 cross-check 통합 인덱스

자체 작성한 wiki/macro/04-value-chain.md 매핑을 **공개 sell-side 컨센서스 + 정량 데이터로 검증**한 결과. 9개 핵심 섹터 × 80+ 종목 분석.

## 검증 방법론

- **소스**: 공개 aggregator (Yahoo·Naver·Morningstar는 직접 차단, stockanalysis·marketbeat·public.com·tickernerd·fool·benzinga·investing·CNBC 활용)
- **데이터**: 컨센서스 평균 TP, 등급 분포(Strong Buy/Buy/Hold/Sell), 최근 90일 변동, broker 인용
- **검증 항목**: (a) 매핑이 컨센서스로 지지되는가, (b) 매핑된 종목 중 broker coverage 거의 없는 것, (c) 컨센서스에 자주 등장하지만 내 매핑에 없는 종목, (d) broker 추천이지만 사업구조 검증으로 노출 적은 종목
- **bias 차단**: broker 의견은 "{broker}는 X라 본다" 형식으로 인용. 다수결 따라가지 않음 (memory 룰)

## 섹터별 결과 요약

| # | 섹터 | 검증 신뢰도 | 가장 큰 발견 | 페이지 |
|---|---|---|---|---|
| 1 | AI/반도체 | Medium-High | 솔브레인의 NVDA leading 방향 OK, 시차는 추가 검증 필요. MRVL Tier 1 유지 정당화. | [[ai-semi]] |
| 2 | 로봇 | High (negative) | ⚠️ 에스비비테크 Optimus 공급 **NOT confirmed**, 종목코드 오기 (284450→160190) | [[robotics]] |
| 3 | SMR/원자력 | High | OKLO≠NuScale-SMR, CEG·VST 누락, NNE 강등, 한전KPS Tier 6 신설 | [[smr-nuclear]] |
| 4 | 사이버보안 | High | wiki claim 4건 **전부 검증 통과** ✅ | [[cybersec]] |
| 5 | 우주항공/방산 | High | DSCA → K-방산 G2G 직판매라 적용 안 됨. Boeing 컨센은 commercial 70% | [[aerospace]] |
| 6 | 생명공학 | Medium | 펩트론 본계약 미체결, "선명한 알파" 표현 과장. 알테오젠/에스티팜 격상 | [[biotech]] |
| 7 | 양자컴퓨팅 | Medium-Low | 헬륨-3 병목은 superconducting 한정, IONQ는 trapped-ion이라 무관 | [[quantum]] |
| 8 | 이차전지 | High | SKIET hidden alpha 시장 미반영, 더블유씨피로 라벨 교체. 양극재 4사 차별화 | [[battery]] |
| 9 | 수소/에너지 | High | PLUG/BLDP 컨센 망가짐. BE는 AI DC fuel cell로 변신. 효성중공업·S-Oil 수소 분류 의심 | [[hydrogen-energy]] |

## 가장 중요한 — 수정 시급 (severity)

### 🔴 Critical (bias / 사실 오류)

| 항목 | 현재 wiki claim | 검증 결과 | 조치 |
|---|---|---|---|
| **에스비비테크 Optimus 공급** | "Optimus 감속기 국산화, 휴머노이드 사이클의 진짜 알파" | Tesla 공식 공급사: 中 Green Harmonic + Zhejiang Shuanghuan. 한국 누구도 진입 확정 없음. 2025년 당기순손실 -94.5억 (YoY +954% 적자 확대) | **"진짜 알파" → "thematic, 미검증" 격하**. wiki/macro/04-value-chain.md `_HIDDEN_ALPHA_TOP` + Tier 4 description 수정 |
| **하이젠알앤엠 종목코드** | 284450 | 실제 코드 160190 | **즉시 정정** |
| **펩트론 LLY/NVO 알파** | "LLY/NVO보다 선명한 한국 알파" | LLY 본계약 미체결, 평가기간 24개월 연장 (2025-12). 옵션 가치는 있으나 실적 미반영 | **"옵션 가치 후보"로 톤다운**. 알테오젠(키트루다 SC FDA+EU 승인 완료)·에스티팜(매출 +21%, OP +99%, 올리고 84%)으로 1순위 격상 |
| **DSCA → K-방산 선행지표** | wiki/macro/02-indicators.md에 K-방산 지표로 등록 | K-방산은 G2G 직판매라 DSCA 밖. 방사청·KOPEC 공시가 실제 lead | **DSCA 항목에 scope 주석**: "미국 FMS 한정. K-방산은 별도 방사청·KOPEC 공시 병용" |

### 🟡 High (구조 누락 / 잘못된 등급화)

| 항목 | 조치 |
|---|---|
| **SMR/원자력 — Tier 0 누락** | CEG (Constellation), VST (Vistra) 추가. 원전 운용사 = AI DC 전력 proxy로 컨센서스 모멘텀 강함 |
| **SMR/원자력 — 등급 차별화** | OKLO (Strong Buy $99) ≠ NuScale-SMR (Hold $18, -70%/6M, 인사이더 매도). NNE는 커버 4명·우주 mandate 의존 — Tier 1 → Tier 1.5 강등 |
| **SMR/원자력 — Tier 누락** | 비에이치아이(083650) Tier 2 (BOP, 보조기기), 한전KPS(051600) Tier 6 (O&M, 정비) 신설 |
| **이차전지 — SKIET 라벨** | "FEOC 중국 분리막 배제 시 ASP 프리미엄"은 시장이 무시 (eBest: base film FEOC 면제 확정, 1Q26 OP -701억). **SKIET → 더블유씨피(393890)로 hidden alpha 라벨 교체** (KB +82% 11K→20K, 다올 58K) |
| **이차전지 — 양극재 차별화** | "K-양극재 묶음" 매수 깨짐. 엘앤에프(Tesla NCMA 독점, KB 44% TP↑) > 포스코퓨처엠(LFP+음극재 동시) > 에코프로비엠(NCM9 가동률 36→20%, Buy 7중 2명만) |
| **양자 — 헬륨-3 일반화** | "양자 H/W 캐파 hidden moat"는 superconducting (IBM/GOOG/RGTI) 한정. trapped-ion (IONQ, Quantinuum) + neutral atom (LG-KRISS)은 dilution fridge 불필요 → **"superconducting 한정" 명시** |
| **수소 — 효성중공업·S-Oil 분류** | 효성중공업 컨센은 100% 변압기/AI DC, 수소 거의 안 나옴. S-Oil은 정제마진/Shaheen. **수소 섹터 분류 재검토** — 효성중공업은 AI/반도체 Tier 4(전력기기) 또는 통신/유틸리티로 |
| **수소 — IRA 동결 가설** | OBBBA(2025-07): 그린수소(45V) 컷, 연료전지 ITC 30%는 2032까지 유지 → 두산퓨얼셀 오히려 美 데이터센터 SOFC 모멘텀 (SK 38,500→42,000 TP↑). "한국 수소 IRA 피해"는 **그린수소 한정**으로 한정 |

### 🟢 Validated (수정 불필요)

- **사이버보안** — wiki claim 4건 모두 검증 통과
- **AI/반도체** — Tier 1~4 매핑 컨센서스로 강하게 지지됨. 솔브레인의 HBM TSV 식각액 leading은 신한·메리츠·삼성 리포트 명시
- **방산 K-방산 backlog** — 한화에어로(JPM 1.5M Buy), 로템(평균 296k 전원 Strong Buy), LIG (786k Buy)
- **생명공학 GLP-1 메가트렌드** — LLY $1,221 Buy, NVO Buy(분산 큼). Trump-LLY-NVO 합의(2025-11)로 MFN 리스크 부분 현실화

## 새로 발견한 추가 후보

### 추가 매핑 검토 종목

| 종목 (코드/티커) | 섹터 | 근거 |
|---|---|---|
| **CEG** (Constellation) | SMR/원자력 Tier 0 | MS/JPM 상향, AI DC 전력 운용사 |
| **VST** (Vistra) | SMR/원자력 Tier 0 | 동일 logic |
| **APD** (Air Products) | 수소/에너지 Tier 1 (산업가스) | $3.1B 손상 후 자본규율 신호로 JPM Hold→Buy (2026-03), NEOM 90%+ 완료 |
| **HII** (Huntington Ingalls) | 우주항공/방산 Tier 1 | Citi $450 TP, Golden Fleet FF(X) |
| **하이젠알앤엠** (160190, 코드 정정) | 로봇 Tier 4 | 액추에이터 일체화 capa — 에스비비테크 대안 |
| **시큐브** (131090) | 사이버보안 small-cap | 생성형 AI 보안 수주 turnaround 시그널 |
| **더블유씨피** (393890) | 이차전지 분리막 hidden alpha | KB +82% (11K→20K), 다올 58K |

### 격하 / 제거 후보

| 종목 | 사유 |
|---|---|
| 에스비비테크 (389500) — Tier 4 휴머노이드 | Optimus 공급 미검증, 적자 확대 → thematic으로 격하 |
| NuScale-SMR (티커 SMR) — Tier 1 동급 | Hold $18, -70%/6M, 인사이더 매도 → OKLO와 분리, 별도 grade |
| 펩트론 (217340) — 생명공학 1순위 | 본계약 미체결, 평가기간 연장 → 옵션 가치 후보로 강등 |
| 효성중공업 (298040) — 수소 섹터 | 컨센은 100% 변압기/AI DC → AI/반도체 Tier 4 또는 통신/유틸리티로 재배치 |
| S-Oil (010950) — 수소 섹터 | 컨센은 정제마진/Shaheen → 수소 카테고리 부적절 |

## 시스템 학습 (메모리 등재 검토)

이번 cross-check에서 드러난 패턴 — **future me 적용 룰**:

1. **"진짜 알파", "선명한 알파" 같은 강한 표현은 1차 사실 + sell-side 다수 인용으로 뒷받침되어야 한다.** 옵션 가치(미체결 계약, 미양산 부품)는 "옵션 가치"로 명시.
2. **"X 종목이 Y 공급사" 주장은 공시·broker 인용·기업 IR 중 최소 1개 1차 소스로 검증.** 검증 안 된 추측은 "thematic"으로 분류.
3. **종목코드는 KRX 또는 한국거래소 공식 자료로 한 번 더 확인** (284450→160190 케이스).
4. **선행지표는 적용 범위(scope) 명시** — 미국 정부 통계(DSCA)를 한국 G2G 거래에 그대로 적용 금지.
5. **"메가트렌드 = 일률 매수" 프레임 회피** — 양극재 4사 같은 묶음에서도 가동률·고객 다양화로 구분.

## 한계 / 데이터 부족

- **PDF 풀 리포트 부재**: 한국 sell-side (삼성·미래·KB·NH·키움) 풀 리포트는 paywall. 본 cross-check는 공개 aggregator + 매체 인용 수준.
- **양자컴퓨팅 / 한국 일부 small-cap**: 분석가 커버리지 자체가 얇음 (<5명). 컨센서스 신뢰도 낮음.
- **2025년 후반~2026년 초 정책 변화 (OBBBA, MFN 합의)**: 효과 측정 미완. 2026 Q2~Q3 실적 통해 재확인 필요.

## 다음 단계 권장 순서

1. **즉시**: critical 항목(에스비비테크, 하이젠알앤엠 코드, 펩트론 톤다운, DSCA scope) → wiki/macro/04-value-chain.md 패치
2. **다음 분기**: high 항목(SMR Tier 재구조, SKIET→더블유씨피, 헬륨-3 scope) → 명세 재잠금 (locked-v2)
3. **PDF 누적**: 사용자가 raw/research/에 PDF 1차 자료 추가 → 본 결과 정량 보강
4. **분기 cross-check 반복**: 본 워크플로우를 분기 1회 자동 실행 → 컨센서스 변화 추적
