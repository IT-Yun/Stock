---
title: 양자컴퓨팅 섹터 — 분석가 뷰 교차검증
source: WebSearch (MarketBeat, StockAnalysis, Motley Fool, Science.org, WarOnTheRocks, TheQuantumInsider, IBM Blog)
created: 2026-04-26
updated: 2026-04-26
sector: quantum
tags: [cross-check, quantum, IONQ, RGTI, IBM, QBTS, helium-3]
caveat: 양자는 thematic·high-variance 섹터. 분석가 커버리지 자체가 얇고(IONQ 13명, RGTI 8명) 컨센서스 신뢰도 낮음. 데이터를 인용할 때 신중할 것.
---

# 양자컴퓨팅 섹터 — 분석가 뷰 교차검증

## 1. Pure-play 컨센서스 vs 밸류에이션 (IONQ, RGTI, QBTS)

| 종목 | 컨센서스 | 평균 TP | 2026E 매출 | Forward P/S | 평가 |
|------|---------|--------|-----------|-------------|------|
| IONQ | Strong Buy (13명) | $66.69 (high $100 Jeffries Garrigan) | $225-245M 가이던스 | 약 130x | 사실상 무결점 성장 가정 |
| RGTI | Buy (8명) | $32-33 (high $43-51) | $22.5M (Wall St) | 약 210x | 익스큐션 리스크 큼 |
| QBTS | Strong Buy (15명) | $32.53 (high $45, 컨트래리언 low $4.13) | 5/12 Q1 발표 예정 | 매우 높음 | 과대평가 vs 실행 갭 |

**핵심 모순**: 컨센서스는 Strong Buy이지만, 같은 분석가/매체들이 동시에 "버블" 경고. 닷컴 정점 Cisco/MSFT가 P/S 30-45였는데 RGTI 210x, IONQ 130x. S&P 500 가장 비싼 종목 평균 P/S 55에 맞추려면 RGTI -94%, QBTS -84%, IONQ -63% 조정 필요(Motley Fool, 2026-01).

**결론**: Fair value가 아닌 **theme premium**. EBITDA 손실 가이던스 IONQ -$310~330M(2026). 매출 대비 가치는 명백한 버블 시그널, 단 컨센서스 TP는 모멘텀 반영.

## 2. IBM 신규 칩 영향 (Heron, Nighthawk, Loon)

- **IBM Quantum Heron**: 156-qubit, fixed-frequency + tunable couplers, Eagle 대비 3-5x 성능 향상, cross-talk 사실상 제거
- **Condor 1,121-qubit는 전략 피벗**: 모놀리식 → 모듈러 접근(품질 우선)
- **Nighthawk(120-qubit) + Loon(에러정정 빌딩블록)**: 2025년 발표, 2026년 말 "near-term quantum advantage", 2029년 fault-tolerant 목표
- **분석가 평가**: IBM은 2021 Eagle, 2022 Osprey 등 로드맵을 시간선대로 이행. Pure-play 스타트업과 달리 IBM은 GOOG와 함께 "조용한 강자"로 평가됨. 단 IBM 주가는 양자 단독 모멘텀이 아닌 Watsonx/AI 비중이 더 큼.

## 3. 헬륨-3 병목 — 진짜 vs 과장

**진짜 병목인 측면**:
- DOE가 tritium decay 부산물로 수집·배급(National Nuclear Security Admin 통제)
- Tritium decay = 핵물리 고정 속도, 인위 가속 불가 → "physics-limited bottleneck" (Science.org, WarOnTheRocks 2025-10)
- 가격 1L $1,000~$20,000 (보조금 의존)
- Maybell Quantum이 Interlune와 헬륨-3 공급 계약 체결(2025-05) — 공급 다변화 시도가 곧 부족 인정

**과장된 측면 / 알파 깎는 요인**:
- **Trapped-ion (IONQ, Quantinuum/Honeywell)**: 헬륨-3 의존도 거의 없음. Commodity 재료 + 레이저 시스템으로 대체. "no exotic-materials bottleneck"
- **Neutral atom (Atom Computing, Pasqal, LG-KRISS 협업)**: 마찬가지로 dilution fridge 불필요
- **Superconducting (IBM, Google, RGTI)만** 본질적으로 헬륨-3 의존
- **달 채굴(Interlune)**: 장기 옵션, 아직 SF 영역

**결론**: 헬륨-3 = **superconducting 진영 한정 병목**. Tier 5 "양자 H/W 캐파 hidden moat" 주장은 절반만 맞음. Trapped-ion·neutral atom 진영(IONQ, Honeywell, KRISS-LG)은 영향 없음 → **기존 wiki의 일반화 주장은 수정 필요**.

## 4. 한국 직접 알파 검증

**wiki 기존 주장**: 직접 알파 부족, indirect 5개만, 억지 매핑 회피 — **검증 결과 사실에 가까움**.

**확인된 한국 직접 노출 (모두 정부·공공·대기업 부서, 순수 상장 알파 X)**:
- **KRISS**: 20-qubit superconducting QPU 클라우드 서비스 운영, 2026년 50-qubit 목표 (정부기관, 비상장)
- **ETRI + KAIST**: 6-photon entangled state, integrated silicon photonics (정부/학계)
- **LG전자**: KRISS와 neutral atom QPU 협업 (대기업 사업부, LG전자 주가 알파 미미)
- **Samsung SDS, SK Telecom**: 양자 임베디드 상용제품 (사업부 비중 매우 낮음)
- **Hyundai Motor Group**: IonQ 파트너십 (수요자 측면, 매출 기여 미미)
- **KT(030200)**: 양자통신망 인프라 (텔코 본업 대비 비중 작음)
- **KQC (Korea Quantum Computing Co.)**: IBM Partnerplus 등재, 비상장 합작
- **Qunova Computing**: 한국 첫 양자 솔루션 벤처, 비상장
- **국가 계획**: $2.3B Quantum Act, 1,000-qubit 10년 목표 (2026 Quantum KOREA), 정책 모멘텀은 강하나 상장 알파로 직결 X
- **KIWOOM 미국양자컴퓨팅 ETF (498270)**: 한국 상장이지만 underlying은 미국 종목 — 한국 알파 아님

**한컴인스페이스(417320), 에이텀**: 이번 검색에서 양자 직접 노출 근거 발견 못함. 위성·우주 관련 indirect 가능성은 있으나 **양자 매출 비중 데이터 부재 → wiki에 양자 종목으로 기록할 근거 없음, 매핑 보류 권장**.

**결론**: 한국 직접 양자 상장 알파 부족 — **기존 wiki 주장 유지 정당**. 5개 indirect도 KT를 제외하면 사업부 비중이 매우 작아 stock-level 알파 미미. 정책 수혜는 인정하되 종목 매핑은 신중하게.

---

## 종합 코멘트

1. **버블 vs 컨센서스 양립**: 같은 분석가 풀이 Strong Buy + 버블 경고를 동시에 발신. 기관·헤지펀드 매도 시그널 보고 ($840M warning, Motley Fool 2026-01-14)
2. **헬륨-3 narrative는 superconducting-specific**: 모든 양자 회사에 적용한다는 식의 문구는 수정 필요
3. **한국 indirect 5개는 stock 알파보다 정책·R&D 시그널** — 종목 추천 근거로는 약함
4. **분석가 데이터 자체가 얇음**: IONQ 13명, RGTI 8명. AI/반도체 섹터(50+명)와 비교해 thematic noise > signal. 컨센서스 TP를 무비판 인용 금지

## 출처

- [IonQ Forecast — MarketBeat](https://www.marketbeat.com/stocks/NYSE/IONQ/forecast/)
- [Rigetti Forecast — Public.com](https://public.com/stocks/rgti/forecast-price-target)
- [QBTS Forecast — MarketBeat](https://www.marketbeat.com/stocks/NYSE/QBTS/forecast/)
- [Quantum Bubble Burst — Motley Fool, 2025-12](https://www.fool.com/investing/2025/12/08/prediction-the-quantum-computing-bubble-will-burst/)
- [$840M warning — Motley Fool, 2026-01-14](https://www.fool.com/investing/2026/01/14/quantum-computing-stocks-ionq-840-million-warning/)
- [IBM Quantum Roadmap 2025](https://www.ibm.com/quantum/blog/ibm-quantum-roadmap-2025)
- [IBM Nighthawk & Loon — PostQuantum](https://postquantum.com/industry-news/ibm-loon-nighthawk/)
- [Helium-3 Scarcity — Science.org](https://www.science.org/content/article/helium-3-runs-scarce-researchers-seek-new-ways-chill-quantum-computers)
- [Quantum Supply Chain Chokepoints — WarOnTheRocks 2025-10](https://warontherocks.com/2025/10/the-supply-chain-chokepoints-in-quantum/)
- [Maybell × Interlune — TheQuantumInsider 2025-05](https://thequantuminsider.com/2025/05/08/maybell-quantum-secures-helium-3-supply-from-interlune-for-scalable-cryogenics/)
- [South Korea Quantum — PostQuantum](https://postquantum.com/quantum-computing/quantum-south-korea/)
- [KRISS 20-qubit — BusinessKorea](https://www.businesskorea.co.kr/news/articleView.html?idxno=237878)
- [Quantum KOREA 2026](https://quantum-korea.kr/ko/main)
