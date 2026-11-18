---
title: 거시 전망 (Macro Outlook)
created: 2026-04-25
updated: 2026-04-26
sources:
  - FRED
  - Conference Board
  - ECRI
  - BIS
  - ECB
  - BOJ
  - BOK ECOS
  - MOTIE/관세청
  - Caldara & Iacoviello GPR Index
  - ACLED
  - CBOE
  - ICE BofA
  - Baltic Exchange
  - Drewry WCI
  - Shanghai Shipping Exchange
  - UN World Population Prospects 2024
  - EU Taxation & Customs (CBAM)
tags: [macro, outlook, top-down, asset-allocation, locked]
status: locked-v1
---

# 거시 전망 (Macro Outlook)

## 1. 페이지 철학

이 페이지는 개별 종목의 RSI/MACD나 섹터별 원자재 가격이 아니라, **거시 8개 차원**을 톱다운으로 읽고 8개 섹터(AI/반도체, 로봇, SMR/원자력, 사이버보안, 우주항공/방산, 생명공학, 양자컴퓨팅, 수소/에너지) 중 어디에 비중을 실을지를 결정하는 의사결정 프레임이다.

핵심 가정은 두 가지다. 첫째, **섹터의 운명은 자기 펀더멘털보다 거시 레짐(regime)에 더 크게 좌우된다** — 동일한 AI 기업도 LEI 양전환 + 신용스프레드 축소 국면에서는 멀티플 확대를 받지만, 실질금리 급등 + 위안 약세 국면에서는 같은 실적에도 디레이팅을 당한다. 둘째, **무료 1차 자료만 사용한다** — FRED, Conference Board(요약), BIS Data Portal, BOK ECOS, BOJ Statistics, ECB Statistical Data Warehouse, Caldara & Iacoviello 학술 페이지, ACLED 무료 계정, KRX, 관세청, EU 집행위원회 공식 자료. 유료 데이터(Bloomberg, Refinitiv)는 일절 사용하지 않는다.

이 페이지는 한 번 박으면 변경 불가, 추가만 가능한 v1 잠금 페이지다. 새 차원이나 지표는 아래에 추가하되, 기존 매핑·임계값은 보존한다.

---

## 2. 차원 1: 비즈니스 사이클

### 2.1 Conference Board LEI

```yaml
id: conference_board_lei
name: Conference Board Leading Economic Index (US)
what: "10개 선행 지표 가중평균. 향후 6-9개월 미국 경제 방향 시사"
why_leading: "신규 주문, 소비자 기대, 주식시장(S&P500), 신용스프레드, 평균 주당 노동시간, 신규 실업수당청구, ISM 신규주문, 빌딩 퍼밋, 금리스프레드 등 future-looking 요소"
lead_time: "경기 침체 평균 ~7개월 선행 (1959-2023)"
source:
  primary: Conference Board
  url: https://www.conference-board.org/topics/us-leading-indicators/
  press_pdf: https://www.conference-board.org/pdf_free/press/US%20LEI%20Technical%20Notes%20Dec%202025.pdf
  free: 요약/헤드라인 무료, 상세 컴포넌트 멤버십 필요
  fallback_fred: USSLIND (Philadelphia Fed Leading Index for US — 비슷하지 않지만 유사한 신호)
  fallback_fred_url: https://fred.stlouisfed.org/series/USSLIND
update: 월간 (보통 셋째주 화요일 10:00 ET)
recent_value: "2026년 1월 97.5 (2016=100), MoM -0.1%, 6개월 변화율 -1.3%"
sector_implications:
  - sector: AI/반도체, 로봇 (cyclical, capex 기반)
    bullish_when: "LEI 6M 변화율 양전환 (음→양)"
    bearish_when: "LEI 6M 변화율 -2% 이하"
  - sector: 양자컴퓨팅 (deep cyclical, vc/capex)
    bullish_when: "LEI 양전환 + 신용스프레드 축소"
  - sector: 사이버보안 (defensive)
    bullish_when: "LEI 하락 + 침해사고 증가"
  - sector: 생명공학 (defensive)
    bullish_when: "LEI 하락 → 방어주 로테이션"
  - sector: 우주항공/방산 (defensive + 정책)
    neutral_to_lei: "GPR/정책예산이 LEI보다 강한 드라이버"
threshold_rules:
  recession_signal: "LEI 6M annualized < -4.5%"
  expansion_signal: "LEI 6M annualized > +2%"
  current_state_2026_04: "감속 둔화 (-1.3% 6M, 직전 -2.6%에서 개선)"
```

### 2.2 ECRI Weekly Leading Index

```yaml
id: ecri_wli
name: ECRI Weekly Leading Index (WLI)
what: "주간 선행지수, 통화공급+주식·채권 펀드, JOC-ECRI 산업원자재 가격, 모기지 신청, 신용스프레드, 주가, 채권금리, 신규실업수당청구 합성"
why_weekly: "월간 LEI보다 4-5주 빠른 시그널, 매주 금요일 오전 갱신"
source:
  primary: ECRI (Economic Cycle Research Institute)
  url: https://www.businesscycle.com/ecri-reports-indexes/recession-recovery
  free: 헤드라인 수치/그래프 무료, 컴포넌트 가중치는 비공개(독점)
  republish: Advisor Perspectives (dshort), Moody's Analytics, Haver
update: 주간 (금요일 ~10:30 ET)
sector_implications:
  - "ECRI WLI 성장률(WLIg)이 -3% 이하로 떨어지면 침체 경고: 사이버/바이오 비중 확대 신호"
  - "WLIg 양전환 → AI/반도체/로봇/SMR 비중 확대 신호"
limitation: "성장률 계산식 비공개 — 절대값 신뢰도보다 추세 변화율 활용"
```

### 2.3 산업생산 / 가동률 (US INDPRO, TCU)

```yaml
id: us_indpro_tcu
name: US Industrial Production (INDPRO) & Capacity Utilization (TCU)
what: "Federal Reserve G.17 release. 제조업/광업/유틸리티 산출 지수와 가동률"
source:
  primary_fed: https://www.federalreserve.gov/releases/g17/current/default.htm
  fred_indpro: https://fred.stlouisfed.org/series/INDPRO
  fred_tcu: https://fred.stlouisfed.org/series/TCU
update: 월간 (다음 달 중순)
sector_implications:
  - sector: AI/반도체, 로봇
    rule: "TCU > 80% → capex 사이클 진입, 반도체 장비/자동화 수요 증가"
  - sector: 수소/에너지
    rule: "INDPRO 모멘텀 ↑ → 산업용 전력/에너지 수요 ↑"
threshold_rules:
  expansion: "TCU > 80%"
  contraction_warning: "TCU < 76% 또는 INDPRO YoY < 0%"
```

### 2.4 신규 실업수당 청구 (US ICSA)

```yaml
id: us_icsa
name: US Initial Jobless Claims (ICSA)
what: "주간 신규 실업수당 청구 건수, 노동시장 turning point의 가장 빠른 시그널"
source:
  primary: US Department of Labor (ETA)
  fred: https://fred.stlouisfed.org/series/ICSA
  fred_4week: https://fred.stlouisfed.org/series/IC4WSA
update: 주간 (목요일 8:30 ET)
sector_implications:
  - "4주 이동평균이 250k 돌파 시 cyclical(AI/반도체/로봇) 경계, defensive(바이오/사이버) 비중 확대"
  - "350k 돌파 시 침체 임박 신호 (역사적 경험치)"
threshold_rules:
  healthy: "IC4WSA < 220k"
  caution: "IC4WSA 220-300k 상승 추세"
  recession_warning: "IC4WSA > 350k"
```

### 2.5 한국은행 BSI / ESI

```yaml
id: bok_bsi_esi
name: Bank of Korea Business Survey Index (BSI) & Economic Sentiment Index (ESI)
what: "한국 기업 경기실사지수(전망/실적). ESI는 BSI+CSI 합성, 한국 경기 동행/선행 시그널"
source:
  primary: Bank of Korea ECOS
  url_kr: https://ecos.bok.or.kr/
  url_eng: https://www.bok.or.kr/eng/bbs/E0000634/list.do?menuNo=400069
  api_wrapper: https://github.com/seokhoonj/ecos
update: 월간 (전월 28일경 08:00 KST 발표)
sector_implications:
  - "수출 BSI > 100 + 제조업 BSI > 100 → 한국 AI/반도체/로봇 비중 확대 (삼성전자, SK하이닉스, 한미반도체)"
  - "전 산업 BSI < 80 + ESI < 90 → KR 사이클리컬 축소, 방산/원전 등 정책수혜 섹터로 이동"
  - "건설 BSI 약세 + 제조업 BSI 강세 → AI capex 디커플링 신호 (반도체 단독 강세 가능)"
threshold_rules:
  expansion: "전 산업 BSI 전망 > 100"
  contraction: "전 산업 BSI 전망 < 90"
release_schedule: "ECOS 사이트의 Statistical Calendar 참조"
```

---

## 3. 차원 2: 통화정책 / 금리

### 3.1 Fed Funds Rate + Dot Plot

```yaml
id: fed_funds_dotplot
name: Federal Funds Target Rate + FOMC Summary of Economic Projections (Dot Plot)
what: "Fed의 정책금리. Dot Plot은 분기별 SEP에서 FOMC 위원들의 향후 금리 경로 예측"
source:
  effective_rate_fred: https://fred.stlouisfed.org/series/DFF
  target_upper_fred: https://fred.stlouisfed.org/series/DFEDTARU
  sep: https://www.federalreserve.gov/monetarypolicy/fomccalendars.htm
update: "FOMC 8회/년 (격월 화·수). SEP는 분기 1회 (3·6·9·12월)"
recent_2026_04: "타깃 레인지 3.50–3.75%, April 28-29 FOMC 동결 확률 ~83% (CME FedWatch)"
sector_implications:
  - sector: AI/반도체, 로봇, 양자컴퓨팅 (high-duration growth)
    bullish_when: "Fed 금리 인하 사이클 + Dot Plot 하향"
    bearish_when: "예상보다 매파적 SEP, 인하 횟수 축소"
  - sector: SMR/원자력, 수소/에너지 (장기 capex)
    bullish_when: "장기금리 동반 하락 (10Y < Fed funds rate일 때 유리)"
  - sector: 생명공학 (자본조달 민감)
    bullish_when: "금리 인하 + 신용스프레드 축소"
```

### 3.2 CME FedWatch (SOFR 시장 기대)

```yaml
id: cme_fedwatch
name: CME FedWatch Tool — 30-Day Fed Funds Futures Implied Probabilities
what: "Fed Funds 선물에서 추출한 향후 FOMC 회의별 금리 변경 확률"
source:
  primary: https://www.cmegroup.com/markets/interest-rates/cme-fedwatch-tool.html
  user_guide: https://www.cmegroup.com/tools-information/quikstrike/cme-fedwatch-tool-user-guide.html
  alt_atlanta_fed: https://www.atlantafed.org/cenfis/market-probability-tracker
free: 무료 (CME 공식)
update: 실시간
sector_implications:
  - "다음 FOMC에서 인하 확률 50% 돌파 시점 → 듀레이션 긴 섹터(AI/반도체, 양자) 선제 비중 확대"
  - "확률 변화 속도가 빠를수록 변동성 확대 (VIX 동반 상승 가능)"
```

### 3.3 미국 10Y-2Y 스프레드 (T10Y2Y)

```yaml
id: us_t10y2y
name: 10Y-2Y Treasury Yield Spread
what: "10년물 - 2년물 국채 수익률 차이. 음수(역전) 시 침체 경고"
source:
  fred: https://fred.stlouisfed.org/series/T10Y2Y
  ny_fed_explainer: https://www.newyorkfed.org/research/capital_markets/ycfaq
update: 일간
historical: "1976년 이후 7번 역전 중 6번 침체 선행 (평균 lead time ~15개월). 2022.7-2024.8 역전(25개월, 최장)은 아직 미해결 케이스"
critical_signal: "역전 자체보다 재정상화(re-steepening) 시점이 침체 트리거 — Fed 인하 시작 후 6-12개월"
sector_implications:
  - "역전 진입: 사이버/바이오/방산 (defensive) 선호"
  - "재정상화 + Fed 인하 시작: AI/반도체/로봇/SMR (cyclical) 선제 진입"
  - "스프레드 +50bp 이상 정상화 + LEI 양전환: full-cyclical 모드"
threshold_rules:
  inversion: "T10Y2Y < 0"
  steepening_recovery: "T10Y2Y > +50bp + Fed 인하 진행 중"
```

### 3.4 한국은행 기준금리

```yaml
id: bok_base_rate
name: Bank of Korea Base Rate (한국은행 기준금리)
what: "한국은행 금융통화위원회 결정 기준금리"
source:
  primary: https://www.bok.or.kr/portal/main/contents.do?menuNo=200643
  ecos: https://ecos.bok.or.kr/
update: "MPC 8회/년 (1·2·4·5·7·8·10·11월)"
sector_implications:
  - "BOK가 Fed보다 먼저 인하 → KRW 약세 → 한국 수출주(AI/반도체, 로봇) 단기 호재 + 외인 자금 유출 위험 trade-off"
  - "BOK-Fed 금리차 < -100bp → KRW 1500/USD 돌파 위험, 외인 매도세"
companion_series:
  fred_kr_call_rate: https://fred.stlouisfed.org/series/IRSTCI01KRM156N
```

### 3.5 ECB Deposit Facility Rate / BOJ Policy Rate

```yaml
id: ecb_boj_rates
name: ECB Deposit Facility Rate & Bank of Japan Policy Rate
what: "유럽·일본 중앙은행 정책금리. 글로벌 유동성 레짐 결정"
source:
  ecb_fred: https://fred.stlouisfed.org/series/ECBDFR
  ecb_official: https://www.ecb.europa.eu/stats/policy_and_exchange_rates/key_ecb_interest_rates/
  boj_official: https://www.boj.or.jp/en/statistics/
sector_implications:
  - "BOJ 금리인상 사이클 → JPY 강세 → 일본 캐리 청산 위험 → 글로벌 위험자산 변동성 ↑ (모든 cyclical 부정적)"
  - "ECB 인하 + Fed 동결 → DXY 강세 → 한국 수출주 환차익, but 신흥국 자금이탈"
```

### 3.6 실질금리 (10Y TIPS)

```yaml
id: us_real_yield_10y
name: US 10Y Real Yield (TIPS)
what: "10년물 인플레이션 연동 국채 수익률. 명목금리에서 기대인플레이션 제외한 실질 자본비용"
source:
  fred_dfii10: https://fred.stlouisfed.org/series/DFII10
  fred_t10yie_breakeven: https://fred.stlouisfed.org/series/T10YIE
update: 일간
sector_implications:
  - "DFII10 > 2.0% → 고듀레이션 성장주(AI/반도체, 양자, 바이오) 디레이팅 압력"
  - "DFII10 < 1.0% + 금/은 강세 → SMR/원자력/수소 등 장기 capex 섹터 멀티플 확대"
  - "실질금리 + 0.5%p 급등 (1주~1개월) → 모든 high-multiple 섹터 단기 위험"
threshold_rules:
  growth_friendly: "DFII10 < 1.5%"
  growth_headwind: "DFII10 > 2.0%"
```

---

## 4. 차원 3: 채권시장 시그널

### 4.1 MOVE Index

```yaml
id: move_index
name: ICE BofAML MOVE Index — 미 채권시장 변동성
what: "2Y/5Y/10Y/30Y 금리 스왑 ATM 1개월 옵션 IV 가중평균. 채권시장의 VIX"
source:
  cnbc: https://www.cnbc.com/quotes/.MOVE
  yahoo: https://finance.yahoo.com/quote/%5EMOVE/
  tradingview: https://www.tradingview.com/symbols/TVC-MOVE/
  ice_official: https://developer.ice.com/fixed-income-data-services/catalog/ice-data-indices-move-index
update: 일간
sector_implications:
  - "MOVE > 130 → 채권시장 스트레스, 금융주/리츠/유틸리티 회피, 주식 변동성 확대 (VIX 동반 상승)"
  - "MOVE > 150 → 시스템 리스크 경고, defensive 풀로테이션"
  - "MOVE 80-100 안정 + 신용스프레드 안정 → cyclical/AI capex 적극"
threshold_rules:
  calm: "MOVE < 90"
  elevated: "MOVE 100-130"
  stress: "MOVE > 130"
```

### 4.2 신용 스프레드 (HY OAS, IG OAS)

```yaml
id: us_credit_spreads
name: ICE BofA US High Yield & Investment Grade Option-Adjusted Spreads
what: "정크본드(HY)·투자등급(IG) 회사채와 국채 간 스프레드. 신용 위험 가격"
source:
  fred_hy_oas: https://fred.stlouisfed.org/series/BAMLH0A0HYM2
  fred_ig_oas: https://fred.stlouisfed.org/series/BAMLC0A0CM
  fred_ccc_oas: https://fred.stlouisfed.org/series/BAMLH0A3HYC
  fred_b_oas: https://fred.stlouisfed.org/series/BAMLH0A2HYB
update: 일간
recent_2026_04: "HY OAS 약 2.85% (역사적으로 매우 낮은 수준 — risk-on 시그널)"
sector_implications:
  - "HY OAS < 350bp → risk-on, AI/반도체/로봇/양자/바이오 모두 우호"
  - "HY OAS > 600bp → 신용 스트레스, 자본조달 의존 섹터(바이오, 양자, 우주) 위험"
  - "CCC OAS 급등 (>1000bp) → 침체 임박 시그널"
threshold_rules:
  risk_on: "HY OAS < 400bp"
  caution: "HY OAS 400-600bp"
  stress: "HY OAS > 600bp"
```

### 4.3 한국 회사채 스프레드

```yaml
id: kr_corporate_spreads
name: 한국 회사채 (AA-, BBB-) - 국고채 3년 스프레드
what: "한국 회사채 신용 등급별 스프레드. 한국 신용시장 위험 시그널"
source:
  primary: 금융투자협회 (KOFIA) 채권정보센터
  url: https://www.kofiabond.or.kr/
  ecos: https://ecos.bok.or.kr/ (통계검색 → 시장금리)
update: 일간
sector_implications:
  - "AA- 회사채 스프레드 > 100bp → KR 사이클리컬(반도체, 자동차) 자금조달 부담"
  - "BBB-회사채 급등 → 좀비기업 디폴트 위험 → KOSPI 전체 위험"
  - "스프레드 안정 + KRW 안정 → 한국 AI/반도체 비중 확대 가능"
```

### 4.4 미국채 발행 일정

```yaml
id: us_treasury_issuance
name: US Treasury Refunding Statement & QRA (Quarterly Refunding Announcement)
what: "재무부 분기별 차환 발표. 단기/장기 비중, 총 발행량 → 금리 압력"
source:
  primary: https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding
  tbac: https://home.treasury.gov/policy-issues/financing-the-government/quarterly-refunding/treasury-borrowing-advisory-committee
update: "분기별 (2·5·8·11월 첫째주 수요일)"
sector_implications:
  - "장기물(10Y+) 비중 급증 → 장기금리 상승 압력 → 고듀레이션 섹터 위험"
  - "TGA(재무부 일반계정) 잔고 변화 → 시중 유동성 직접 영향"
```

---

## 5. 차원 4: 글로벌 유동성

### 5.1 Fed 대차대조표 (WALCL, H.4.1)

```yaml
id: fed_balance_sheet
name: Fed Balance Sheet — Total Assets (WALCL, H.4.1 Release)
what: "연준 보유 자산 총액. QT/QE 진행 척도"
source:
  fed_h41: https://www.federalreserve.gov/releases/h41/
  fred_walcl: https://fred.stlouisfed.org/series/WALCL
update: 주간 (목요일 16:30 ET, 수요일 기준)
sector_implications:
  - "QT 종료/속도 둔화 발표 → AI/반도체/양자 등 high-multiple 섹터 멀티플 확대"
  - "QT 가속 → cyclical 디레이팅, defensive 로테이션"
related_series:
  fred_rrp: https://fred.stlouisfed.org/series/RRPONTSYD (역레포)
  fred_tga: https://fred.stlouisfed.org/series/WTREGEN (재무부 잔고)
note: "넷 유동성 = WALCL - RRP - TGA. 이게 더 정확한 자산가격 드라이버"
```

### 5.2 ECB / BOJ 대차대조표

```yaml
id: ecb_boj_balance_sheets
name: ECB & Bank of Japan Total Assets
what: "유럽·일본 중앙은행 자산 총액. 글로벌 유동성 풀의 일부"
source:
  fred_ecb_assets: https://fred.stlouisfed.org/series/ECBASSETSW
  fred_boj_assets: https://fred.stlouisfed.org/series/JPNASSETS
  boj_official: https://www.boj.or.jp/en/statistics/category/financial.htm
update: "ECB 주간, BOJ 월 2-3회"
recent_2026: "BOJ 자산 ¥677.8조 (2025Q4) — 정점 대비 -10.4%, $502B 축소. JGB 80% 비중"
sector_implications:
  - "BOJ QT 가속 + JPY 강세 → 캐리 트레이드 청산 → 글로벌 risk-off"
  - "ECB QT + Fed QT 동시 가속 → 글로벌 유동성 축소 → cyclical 위험"
```

### 5.3 글로벌 M2

```yaml
id: global_m2
name: Global M2 (US + Eurozone + China + Japan 합산)
what: "주요 4개 통화권 M2 합계. 달러 환산 또는 가중평균. 자산가격 long-cycle 드라이버"
source:
  bis_gli: https://data.bis.org/topics/GLI
  bis_release_schedule: "다음 발표 2026-04-30, 직전 2026-03-16"
  free_aggregator: https://streetstats.finance/liquidity/money
  macromicro: https://en.macromicro.me/charts/3439/major-bank-m2-comparsion
update: 월간
sector_implications:
  - "Global M2 YoY > +8% → 모든 자산군 우호, AI/반도체/양자 강세"
  - "Global M2 YoY < 0% → defensive 비중 확대"
caveat: "달러 환산 시 DXY 변동에 의해 신호가 왜곡됨 — 로컬 통화 가중평균과 함께 봐야 함"
```

### 5.4 DXY (달러 인덱스)

```yaml
id: dxy
name: US Dollar Index (DXY) / FRED DTWEXBGS (Trade-Weighted)
what: "달러 강도. 6개 주요통화 대비(DXY) 또는 무역 가중(DTWEXBGS)"
source:
  ice_dxy: https://www.theice.com/products/194/US-Dollar-Index-Futures
  fred_broad: https://fred.stlouisfed.org/series/DTWEXBGS
  fred_major: https://fred.stlouisfed.org/series/DTWEXM
update: 일간
sector_implications:
  - "DXY > 105 → 신흥국·한국 수출주(AI/반도체) 환율 호재, but 외국인 자금이탈 위험"
  - "DXY < 100 + 원자재 강세 → 수소/에너지/방산(원유 노출) 우호"
  - "DXY 급등 + KRW 급락 동시 → 한국 주식 외인 매도 가속"
threshold_rules:
  strong_dollar: "DXY > 105"
  weak_dollar: "DXY < 100"
```

### 5.5 USD/KRW, EUR/USD, USD/JPY

```yaml
id: major_fx_pairs
name: Major FX Pairs — KRW, EUR, JPY
source:
  fred_krw: https://fred.stlouisfed.org/series/DEXKOUS
  fred_eur: https://fred.stlouisfed.org/series/DEXUSEU
  fred_jpy: https://fred.stlouisfed.org/series/DEXJPUS
  fed_h10: https://www.federalreserve.gov/releases/h10/
update: 일간
recent_2026: "USD/KRW 2026.02 평균 1,447.29; 2026.03 26일 1,509.37 (연중 고점)"
sector_implications:
  - "USD/KRW > 1450: 한국 수출주(삼성전자, SK하이닉스, 한미반도체, 두산에너빌리티) 환차익 모멘텀, but 1500 돌파 시 외인 매도 가속"
  - "USD/JPY > 160: BOJ 개입 임계, 캐리 청산 위험 → 글로벌 risk-off"
  - "EUR/USD > 1.10 + DXY 약세: 글로벌 risk-on 환경"
```

### 5.6 CNH/USD (위안 시그널)

```yaml
id: cnh_usd
name: USD/CNH (역외 위안) + USD/CNY 고시환율
what: "역내(CNY)는 PBOC 관리, 역외(CNH)는 시장. 둘의 갭이 정책 신호"
source:
  pboc_fix: http://www.pbc.gov.cn/en/3688006/3688066/4157847/index.html
  cnh_realtime: https://www.investing.com/currencies/usd-cnh
  fred_cny: https://fred.stlouisfed.org/series/DEXCHUS
update: 일간 (PBOC 고시 09:15 CST)
sector_implications:
  - "USD/CNH > 7.30 + PBOC 갭 확대 → 미중 통화전쟁 신호 → 한국 반도체/디스플레이/배터리 단기 위험 (중국 수요/경쟁 양면)"
  - "위안 약세 + 한국 KRW 동조 약세 → 미국향 수출주 단기 호재"
  - "위안 강세 전환 + 중국 부양 패키지 → 중국 노출 큰 한국 화학/에너지 우호"
```

---

## 6. 차원 5: 시장 변동성 / 위험선호

### 6.1 VIX

```yaml
id: vix
name: CBOE Volatility Index (VIX)
what: "S&P500 30일 IV. 시장의 공포·탐욕 척도"
source:
  cboe: https://www.cboe.com/tradable_products/vix/
  fred: https://fred.stlouisfed.org/series/VIXCLS
update: 실시간 (FRED 일간)
recent_2026_04: "약 19.5 (정상 범위)"
sector_implications:
  - "VIX < 15 + 신용스프레드 축소 → 풀 risk-on, AI/양자/로봇 적극"
  - "VIX 20-25 → 중립, 종목 선별"
  - "VIX > 30 → 패닉, defensive(바이오/사이버) + 현금 비중 확대"
threshold_rules:
  complacency: "VIX < 15"
  normal: "VIX 15-20"
  caution: "VIX 20-30"
  fear: "VIX > 30"
```

### 6.2 VVIX (VIX의 VIX)

```yaml
id: vvix
name: CBOE VVIX Index — Volatility of VIX
what: "VIX 옵션의 IV. 변동성에 대한 변동성. 테일 리스크 신호"
source:
  cboe: https://www.cboe.com/us/indices/dashboard/VVIX/
update: 일간
sector_implications:
  - "VVIX > 130 + VIX 안정 → 표면 아래 변동성 베팅 누적, 향후 VIX 폭등 가능성"
  - "VVIX 급등 시 옵션 헤지 비용 증가 → 변동성 매도 전략 위험"
threshold_rules:
  normal: "VVIX 80-110"
  elevated: "VVIX > 130"
```

### 6.3 SKEW Index

```yaml
id: cboe_skew
name: CBOE SKEW Index — 블랙 스완 비용
what: "S&P500 OTM 풋옵션 가격에서 추출한 꼬리 위험 가격. SKEW 100 = 정규분포"
source:
  cboe: https://www.cboe.com/us/indices/dashboard/SKEW/
update: 일간
sector_implications:
  - "SKEW > 145 + VIX 낮음 → 시장 표면적으로 평온하나 헤지 수요 누적, 급락 위험"
  - "SKEW > 150 → defensive 비중 확대 신호"
threshold_rules:
  normal: "SKEW 115-135"
  elevated: "SKEW > 145"
```

### 6.4 VKOSPI (한국 변동성지수)

```yaml
id: vkospi
name: KOSPI 200 Volatility Index (VKOSPI)
what: "KOSPI 200 옵션에서 추출한 30일 IV. KRX가 30초마다 산출"
source:
  krx: https://data.krx.co.kr/
  investing: https://kr.investing.com/indices/kospi-volatility
update: 30초
recent_2026_03: "62.97 (사상 최초 60 돌파, 중동 지정학 리스크 + 글로벌 risk-off)"
sector_implications:
  - "VKOSPI < 20 → KR cyclical(반도체, 로봇) 적극"
  - "VKOSPI 25-35 → 종목 선별, KOSPI 베타 축소"
  - "VKOSPI > 40 → 한국 시장 risk-off, 방산/원전 등 정책수혜 + 현금"
threshold_rules:
  stable: "VKOSPI < 20"
  elevated: "VKOSPI 20-30"
  high_volatility: "VKOSPI > 30"
```

### 6.5 High-Yield 스프레드 (위험선호 cross-check)

위 4.2와 동일 시리즈(BAMLH0A0HYM2). 위험선호 차원에서는 VIX와의 발산을 본다 — VIX 낮은데 HY 스프레드 확대하면 신용시장이 먼저 균열 신호.

### 6.6 Citi Economic Surprise Index (CESI)

```yaml
id: citi_surprise
name: Citi Economic Surprise Index (CESI)
what: "발표된 경제지표가 컨센서스 대비 얼마나 surprise인가의 3개월 롤링 가중 표준편차. 양수 = 데이터 호조"
source:
  yardeni_chart: https://yardeni.com/charts/citigroup-economic-surprise/
  macromicro: https://en.macromicro.me/charts/45866/global-citi-surprise-index
  cbonds: https://cbonds.com/indexes/99130/
  methodology_paper: https://www.federalreserve.gov/pubs/ifdp/2013/1093/ifdp1093.pdf
update: 일간 (헤드라인 무료 차트)
sector_implications:
  - "CESI 음→양 전환 + LEI 양전환 동시 → 강력한 cyclical 진입 신호"
  - "CESI 양수인데 시장 하락 → 시장이 더 비관적, 지표 따라 매수 기회"
country_versions: "US, EU, China, EM, Global 각각 존재 — 한미 동시 양수 시 KR 수출주 강세"
```

---

## 7. 차원 6: 지정학 / 정책

### 7.1 GPR Index (Caldara & Iacoviello 2022)

```yaml
id: gpr_index
name: Geopolitical Risk Index (GPR) — Caldara & Iacoviello
what: "10개 영자신문에서 지정학 위협·사건 단어 빈도 기반 텍스트 인덱스. 1985-현재"
academic_citation: "Caldara, Dario, and Matteo Iacoviello (2022), 'Measuring Geopolitical Risk', American Economic Review, 112(4), 1194-1225"
source:
  matteoiacoviello: https://www.matteoiacoviello.com/gpr.htm
  policyuncertainty: https://www.policyuncertainty.com/gpr.html
  paper_pdf: https://www.matteoiacoviello.com/gpr_files/GPR_PAPER.pdf
  data_icpsr: https://www.openicpsr.org/openicpsr/project/154781/version/V1/view
  country_specific: https://www.matteoiacoviello.com/gpr_country.htm
sub_indexes:
  GPRT: "Geopolitical Threats (전쟁 위협, 핵 위협 등)"
  GPRA: "Geopolitical Acts (실제 군사행동, 테러)"
  GPRH: "Historical Index 1900-현재 (3개 신문)"
update: 월간 (당월 데이터는 다음달 초)
sector_implications:
  - sector: 우주항공/방산 (KAI, 한화에어로스페이스, LIG넥스원, RTX, LMT, NOC)
    bullish_when: "GPR 1년 이동평균 > 100, 특히 GPRA 급등 시"
  - sector: 사이버보안
    bullish_when: "GPR + 국가 행위자 사이버 사건 보도 증가"
  - sector: 수소/에너지 (원유 + LNG)
    bullish_when: "중동 GPR 급등 + 원유 $90+"
  - sector: AI/반도체
    bearish_when: "미중 GPR 급등 + 대만 위협 단어 빈도 ↑ → TSMC/SK하이닉스 단기 위험"
threshold_rules:
  elevated: "GPR > 100 (1985-2019 평균=100)"
  crisis: "GPR > 200"
```

### 7.2 ACLED 분쟁 데이터

```yaml
id: acled
name: ACLED — Armed Conflict Location & Event Data
what: "실시간 지구 전체 무력충돌·시위·정치적 폭력 이벤트 데이터베이스"
source:
  primary: https://acleddata.com/
  conflict_data: https://acleddata.com/conflict-data
  watchlist_2026: https://acleddata.com/conflict-index-2026-watchlist
  hdx_aggregated: https://data.humdata.org/organization/acled
  api_doc: https://acleddata.com/conflict-data/download-data-files
free_access: "myACLED 무료 가입 후 API/Export 사용. HDX 집계 파일은 가입 없이 다운로드 가능 (주간 업데이트)"
update: 주간
sector_implications:
  - "특정 지역(중동, 우크라이나, 대만해협) 이벤트 빈도 급증 → 방산/우주항공 비중 확대"
  - "ACLED Conflict Index 2026 Watchlist 10개국 진척 모니터링 (시리아, 미얀마, 수단 등)"
note: "GPR Index는 미디어 보도 텍스트 기반(market 반응까지 포함), ACLED는 실제 이벤트 카운트. 둘 다 봐야 함"
```

### 7.3 미중 관세 / 수출통제 추적

```yaml
id: us_china_trade_controls
name: 미중 관세 및 수출통제 (Section 301, BIS Entity List, FDPR)
source:
  ustr_section301: https://ustr.gov/issue-areas/enforcement/section-301-investigations
  bis_entity_list: https://www.bis.doc.gov/index.php/policy-guidance/lists-of-parties-of-concern/entity-list
  treasury_ofac: https://ofac.treasury.gov/
  csis_chip_war_tracker: https://www.csis.org/programs/strategic-technologies-program
  rhodium_tracker: https://rhg.com/
update: 비정기 (행정부 발표 시점)
sector_implications:
  - "BIS Entity List에 한국 기업 합작 중국 법인 추가 → 삼성전자/SK하이닉스 중국 fab 단기 위험"
  - "Section 301 추가 관세 발표 → 한국 부품/소재 우회 수혜 가능성"
  - "EUV/HBM 수출통제 강화 → 한미반도체, 동진쎄미켐 등 장비/소재 수혜 vs SK하이닉스/삼성 단기 위험 (양면)"
```

### 7.4 EU CBAM (탄소국경세)

```yaml
id: eu_cbam
name: EU Carbon Border Adjustment Mechanism (CBAM)
what: "EU 수입 시 탄소 배출량 기준 부담금. 시멘트, 철강, 알루미늄, 비료, 전력, 수소 6개 품목"
source:
  ec_taxation_customs: https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism_en
  enter_force_2026: https://taxation-customs.ec.europa.eu/news/cbam-successfully-entered-force-1-january-2026-2026-01-14_en
status_2026:
  effective_date: "2026-01-01 본격 발효 (compliance phase)"
  threshold: "연간 50톤 초과 수입 시 CBAM 인증 declarant 등록 필수, 2026-03-31까지 신청"
  certificates: "2027-02-01부터 CBAM 인증서 판매, 2027-09-30까지 첫 surrender"
sector_implications:
  - sector: 수소/에너지 (수소 직접 대상)
    bullish_when: "EU 그린수소 수요 ↑ → 한국 수소 인프라/연료전지(두산퓨얼셀, 효성중공업) 잠재적 수혜"
  - sector: 우주항공/방산
    indirect: "철강·알루미늄 단가 상승 → 한화에어로스페이스, KAI 원가 부담"
  - sector: AI/반도체
    indirect: "장기적으로 데이터센터 전력 그린화 압력 → SMR/원자력 우호"
```

### 7.5 미국 IRA / CHIPS Act 집행률

```yaml
id: us_ira_chips_execution
name: US Inflation Reduction Act + CHIPS and Science Act 집행 현황
source:
  treasury_ira: https://home.treasury.gov/policy-issues/inflation-reduction-act
  tigta_oversight: https://www.tigta.gov/inflation-reduction-act-oversight
  chips_gov: https://www.chips.gov/
  ira_tracker: https://iratracker.org/actions/
status_2026:
  ira_irs_spending: "2025-03-31 기준 IRS IRA 집행 $13.8B (37%)"
  trump_freeze: "2025-01 'Unleashing American Energy' 행정명령으로 IRA 자금 디스버스먼트 동결 — 정책 불확실성 ↑"
  chips_awards: "삼성전자(테일러 TX), SK하이닉스(인디애나), TSMC, 인텔 등 awards 진행"
update: 분기 (TIGTA), 비정기 (CHIPS awards)
sector_implications:
  - sector: AI/반도체
    bullish_when: "CHIPS 보조금 disbursement 진행 → 삼성전자 테일러 fab, SK하이닉스 패키징 가시화"
    bearish_when: "추가 동결 또는 deal renegotiation 위험"
  - sector: SMR/원자력
    bullish_when: "IRA 핵 ITC 살아남으면 NuScale, BWXT 우호. 동결 지속 시 장기 불확실성"
  - sector: 수소/에너지
    bearish_risk: "IRA 45V 수소 ITC 동결 = 한국 수소 밸류체인 직접 부정적"
```

### 7.6 한국 K-칩스법 / 반도체 특별법

```yaml
id: kr_chips_act
name: K-칩스법 (조세특례제한법) + 반도체 특별법
what: "한국 반도체 등 국가전략기술 시설투자 세액공제 + 임시투자세액공제"
source:
  primary: 기획재정부, 산업통상자원부
  kim_chang_brief: https://www.kimchang.com/ko/insights/detail.kc?sch_section=4&idx=27332
status_2026:
  k_chips_passed: "2025-02-27 본회의 통과, 2023-04-11 공포 후 개정"
  semi_special_law: "반도체 특별법 별도 진행 중 (52시간 예외 등 쟁점)"
  yongin_cluster: "용인 시스템반도체 클러스터 2042년까지 300조원 규모"
update: "법안 통과 시점 + 시행령 개정"
sector_implications:
  - sector: AI/반도체 (한국)
    bullish_when: "세액공제율 상향 + 클러스터 부지 확정 → 삼성전자, SK하이닉스, 한미반도체, 동진쎄미켐, 솔브레인"
  - sector: 로봇 (산업용 자동화)
    bullish_when: "용인 클러스터 자동화 발주 → 두산로보틱스, 레인보우로보틱스, 한신기계"
```

---

## 8. 차원 7: 글로벌 무역 / 운송

### 8.1 BDI (Baltic Dry Index)

```yaml
id: bdi
name: Baltic Dry Index — 벌크선 운임 지수
what: "철광석, 석탄, 곡물 등 건화물 해상운임 지수. Capesize/Panamax/Supramax/Handysize 가중평균"
source:
  baltic_exchange: https://www.balticexchange.com/en/data-services/market-information0/dry-services.html
  handybulk_daily: https://www.handybulk.com/baltic-dry-index/
  cnbc: https://www.cnbc.com/quotes/.BADI
  trading_economics: https://tradingeconomics.com/commodity/baltic
update: 일간 (런던 13:00)
sector_implications:
  - "BDI > 2000 + 중국 PMI > 50 → 글로벌 산업 사이클 회복, 한국 조선/철강/석유화학 수혜 → 간접적으로 AI/반도체 capex 회복 시그널"
  - "BDI 급락 + 중국 부동산 위기 신호 → 글로벌 cyclical 디레이팅"
note: "BDI는 직접 섹터 매핑보다 글로벌 산업 활동의 thermometer로 사용"
```

### 8.2 SCFI (Shanghai Containerized Freight Index)

```yaml
id: scfi
name: Shanghai Containerized Freight Index
what: "상하이 출발 컨테이너 운임 스팟 지수. 글로벌 무역 수급 시그널"
source:
  primary: https://en.sse.net.cn/indices/scfinew.jsp
  ccfi: https://en.sse.net.cn/indices/ccfinew.jsp
  trading_economics: https://tradingeconomics.com/commodity/containerized-freight-index
update: 주간 (금요일)
recent_2026_02: "월 평균 1,283.71"
recent_2026_04: "약 1,886 (4월 24일)"
sector_implications:
  - "SCFI 급등(>3000) → 무역 병목, 인플레 재점화 위험 → 실질금리 ↑ → 고듀레이션 섹터 위험"
  - "SCFI 안정 + 한국 수출 BSI ↑ → 한국 AI/반도체 수출 모멘텀 우호"
```

### 8.3 WCI (Drewry World Container Index)

```yaml
id: wci_drewry
name: Drewry World Container Index
what: "글로벌 8개 주요 컨테이너 항로 가중평균. 매주 목요일 갱신"
source:
  drewry: https://www.drewry.co.uk/supply-chain-advisors/supply-chain-expertise/world-container-index-assessed-by-drewry
update: 주간 (목요일)
recent_2026_04: "$2,232 / 40ft (4월 23일, 주간 -1%)"
sector_implications:
  - SCFI와 cross-check, WCI는 글로벌 평균이라 더 안정
  - "WCI > $4,000 → 무역 병목 재현, 인플레 재점화"
  - "WCI < $1,500 → 무역 위축, cyclical 위험"
```

### 8.4 한국 수출 (관세청 잠정치)

```yaml
id: kr_exports_monthly
name: 한국 월간 수출입 잠정치 (관세청 + 산업통상자원부)
what: "월별 1일 발표(전월 잠정치). 한국 수출 사이클의 가장 빠른 시그널 + 10일/20일 잠정치도 발표"
source:
  korea_kr: https://www.korea.kr/briefing/pressReleaseView.do
  motie: https://www.motie.go.kr/
  kita_kstat: https://stat.kita.net/
update: "매월 1일 (전월 잠정치), 11일 (전월 1-10일), 21일 (전월 1-20일)"
recent_2026:
  jan: "$65.9B (+33.9% YoY, 1월 사상 최대)"
  feb: "$67.45B (+29% YoY)"
  mar: "$86.1B (+48.3% YoY)"
sector_implications:
  - "반도체 수출 YoY > +30% + DRAM/HBM 단가 ↑ → 삼성전자/SK하이닉스 어닝 비트 확률 ↑"
  - "자동차 수출 YoY ↑ + 미국 ISM ↑ → 한국 부품/2차전지 우호"
  - "수출 YoY 음전환 → KR 사이클리컬 축소, 방산/원전 등 정책수혜로 이동"
top_export_items: "반도체, 자동차, 석유제품, 선박, 일반기계, 디스플레이"
```

---

## 9. 차원 8: 인구구조 / 장기 트렌드

### 9.1 출산율 / 인구 (UN WPP 2024)

```yaml
id: un_wpp_fertility
name: UN World Population Prospects 2024 — Fertility Rate & Working-Age Population
source:
  un_wpp_main: https://population.un.org/wpp/
  summary_pdf: https://population.un.org/wpp/assets/Files/WPP2024_Summary-of-Results.pdf
  unfpa_dashboard: https://www.unfpa.org/data/world-population-dashboard
update: 2-3년 (다음 release 2027 예상)
key_facts_2024:
  global_tfr: "2.2 births/woman (1990: 3.3)"
  countries_below_replacement: "237개국 중 131개국(55%)이 TFR < 2.1, 글로벌 인구의 68%"
  women_15_49: "2024 약 20억 → 2050년대 후반 22억 정점"
country_specific_tfr_recent:
  korea: "0.72-0.78 (세계 최저 수준, 통계청 자료)"
  japan: "1.20 수준"
  us: "1.66"
  china: "1.0 수준 (급락)"
sector_implications:
  - sector: 로봇 (특히 산업용/서비스 로봇)
    bullish_long_term: "한국·일본·중국 노동인구 감소 → 자동화 capex 구조적 증가 (두산로보틱스, 레인보우로보틱스, 화낙, ABB)"
  - sector: 생명공학 (고령화 노출)
    bullish_long_term: "노인 인구 비중 확대 → 항암, 치매(알츠하이머), 비만/당뇨 시장 장기 확장 (셀트리온, 삼성바이오로직스, Lilly, Novo Nordisk)"
  - sector: AI/반도체
    bullish_long_term: "노동력 부족 → AI 자동화 채택 가속"
```

### 9.2 세계 노동인구 추세

UN WPP 2024와 동일 소스. 추가 변수:
- 중국 노동인구는 2014 정점 이후 감소 진행 중
- 인도가 2040년경까지 노동인구 1위 유지 — AI/IT 서비스 인력 풀
- 한국 생산가능인구(15-64세)는 2017 정점 후 감소

섹터 함의: **장기적으로 자동화·로봇·AI는 demographic tailwind**, 부동산·저숙련 노동집약 산업은 headwind.

### 9.3 AI Capex 사이클

```yaml
id: ai_capex_cycle
name: AI Capex Cycle Position
what: "하이퍼스케일러(MS, Google, Meta, Amazon) capex + 엔비디아 데이터센터 매출 + ASML book-to-bill + TSMC 매출 = AI capex 사이클 thermometer"
source:
  hyperscaler_filings: 분기 10-Q/10-K 직접 (Apple/MS/GOOG/META/AMZN IR pages)
  asml_quarterly: https://www.asml.com/en/investors/financial-results
  tsmc_monthly: https://investor.tsmc.com/english/monthly-revenue
  nvidia_dc_revenue: NVIDIA 분기 IR
  semi_book_bill: https://www.semi.org/en/products-services/market-data/billing-reports
update: 분기 (capex), 월간 (TSMC 매출)
sector_implications:
  - "ASML book-to-bill > 1.0 + TSMC 월 매출 YoY > +30% → AI capex 사이클 가속, 한미반도체/HBM/SK하이닉스 강세 지속"
  - "하이퍼스케일러 capex YoY 둔화 → AI 사이클 피크 경고"
  - "구글/메타 capex 분기별 상향 → AI/반도체 + SMR(데이터센터 전력) 동시 우호"
```

### 9.4 탈탄소 / 에너지 전환

```yaml
id: energy_transition
name: 글로벌 탈탄소 / 에너지 전환 진척
source:
  iea_world_energy_outlook: https://www.iea.org/reports/world-energy-outlook-2024 (연간, 무료)
  irena: https://www.irena.org/Data
  bnef_summary: 무료 헤드라인만 (디테일 유료)
  ember_climate: https://ember-energy.org/ (전력 부문 무료 데이터)
key_metrics:
  - "세계 신재생 발전 설치량 (GW/year)"
  - "전기차 판매 비중 (% of new sales)"
  - "그린수소 capacity announcements"
  - "원자력 신규 승인 건수 (특히 SMR)"
sector_implications:
  - sector: SMR/원자력
    bullish_when: "데이터센터 전력 수요 + 탈탄소 동시 압박 → SMR 정책 가속 (NuScale, BWXT, 두산에너빌리티)"
  - sector: 수소/에너지
    bullish_when: "EU CBAM 발효 + 그린수소 단가 하락 → 한국 연료전지(두산퓨얼셀, 효성중공업)"
  - sector: AI/반도체
    indirect: "데이터센터 전력 비용 상승 → 효율 칩 (NVIDIA Blackwell, AMD MI series) 가치 ↑"
```

---

## 10. 거시 시나리오 → 섹터 매핑표 (핵심 의사결정 표)

| 시나리오 | 트리거 신호 (AND 조건) | 유리 섹터 | 불리 섹터 | 자산배분 가이드 |
|---------|---------------------|---------|---------|-------------|
| **골디락스** (성장+저금리+낮은 변동성) | LEI 6M 양전환 + T10Y2Y 정상화 + DXY < 100 + DFII10 < 1.5% + VIX < 15 + HY OAS < 350bp | AI/반도체, 로봇, 양자컴퓨팅, 생명공학(소형주) | 우주항공/방산, 사이버보안 (방어 비중 축소) | 주식 75-85%, 채권 10%, 현금 5-10%, 풀 cyclical |
| **확장 후기 / 인플레 재점화** | TCU > 80% + 원유 > $90 + DFII10 > 2.0% + SCFI/WCI 급등 + Citi Surprise 양수 지속 | 수소/에너지, 우주항공/방산(원자재 익스포저), SMR(전력 수요) | AI/반도체(밸류 부담), 양자컴퓨팅, 생명공학(소형주) | 주식 65%, 단기채 25%, 원자재 10% |
| **스태그플레이션** | LEI ↓ + 원유 ↑ + DXY ↑ + DFII10 > 2.5% + Citi Surprise 음수 + HY OAS 확대 | 수소/에너지, 우주항공/방산, SMR/원자력 | AI/반도체, 로봇, 양자컴퓨팅 | 주식 50%, TIPS 20%, 원자재 15%, 현금 15% |
| **침체 (recession)** | LEI 6M < -4.5% + IC4WSA > 350k + HY OAS > 600bp + T10Y2Y 재정상화 + Fed 인하 시작 | 생명공학 (대형 캐시 부자), 사이버보안 | AI/반도체, 로봇, 양자컴퓨팅, SMR(자본조달 어려움) | 주식 40-50%, 장기 국채 30%, 현금 20% |
| **회복 초기** | LEI 6M 양전환 + Fed 첫 인하 후 6개월 + HY OAS 축소 + Citi Surprise 음→양 + ISM 신규주문 > 50 | AI/반도체, 로봇, SMR/원자력, 양자컴퓨팅 | 우주항공/방산(상대적 underperform), 바이오 대형주 | 주식 80%, 채권 15%, 현금 5%, 베타 풀가속 |
| **지정학 위기** | GPR > 200 + 중동/대만 ACLED 이벤트 급증 + 원유 ↑ + DXY ↑ + VIX > 25 | 우주항공/방산, 수소/에너지, 사이버보안, SMR(에너지안보) | AI/반도체 (대만 위험), 로봇 | 주식 55%, 채권 20%, 현금 15%, 금 10% |
| **AI capex 사이클 가속** | ASML book-to-bill > 1.0 + TSMC 월매출 YoY > +30% + 하이퍼스케일러 capex 상향 + HBM 단가 ↑ | AI/반도체 (메모리·장비·소재), SMR(데이터센터 전력 수요), 양자컴퓨팅 (테마 수혜) | 전통 cyclical은 상대적 underperform | AI 풀 익스포저, 단 PE 부담 시 SMR로 일부 분산 |
| **위안 평가절하 / 미중 디커플링 가속** | USD/CNH > 7.30 + BIS Entity List 추가 + 한국 대중 수출 음전환 | 우주항공/방산, 사이버보안, 미국향 한국 수출주(자동차, 일부 반도체 우회) | 중국 노출 큰 화학/배터리, 일부 디스플레이 | 한국 종목 내 미국향 비중 높은 종목 선별 |
| **BOJ 정책 전환 / 캐리 청산** | USD/JPY < 145 (5%+ 1주 강세) + BOJ 추가 인상 + JGB 10Y > 1.5% | 사이버보안, 생명공학(방어) | AI/반도체 (글로벌 risk-off 동반), 로봇, 양자 | 일시적 디리스크: 현금 비중 ↑ |

---

## 11. 자산배분 신호 (부록)

### 11.1 60/40 vs All-Stock vs Barbell 룰

```yaml
allocation_signals:
  full_60_40:
    condition: "VIX 15-25 + HY OAS 350-500bp + LEI 보합 + DFII10 1.0-2.0%"
    rationale: "정상 사이클, 채권이 주식 헤지 역할"
  
  all_stock_overweight:
    condition: "LEI 6M 양전환 + Fed 인하 사이클 진입 + HY OAS < 350bp + VIX < 18"
    rationale: "회복 초기. 채권은 금리 인하로 가격 상승 제한적, 주식 베타가 우월"
  
  barbell_defense_growth:
    condition: "VIX 25-35 + GPR > 100 + LEI 음수 둔화"
    rationale: "방산/바이오/사이버 + 현금/단기채로 양극화. 미들 cyclical 회피"
  
  cash_heavy:
    condition: "MOVE > 130 + HY OAS > 600bp + VIX > 30 + DFII10 급등"
    rationale: "시스템 리스크, 자산 간 상관계수 ↑, 분산 효과 소실"
```

### 11.2 KR vs US 비중 가이드

```yaml
kr_vs_us:
  kr_overweight:
    condition: "USD/KRW 1300-1450 안정 + 한국 수출 YoY > +15% + 외국인 KOSPI 순매수 + BSI 전망 > 100"
    sectors: "AI/반도체(삼성전자/SK하이닉스), 로봇(두산로보틱스), SMR(두산에너빌리티), 방산(한화에어로스페이스/KAI)"
  
  us_overweight:
    condition: "DXY > 105 + USD/KRW > 1500 + 외국인 KOSPI 순매도 + GPR 한국 부분지수 ↑"
    sectors: "AI/반도체(NVDA/AVGO/AMD), 사이버(CRWD/PANW/ZS), 우주항공(LMT/RTX/NOC), 바이오(LLY/NVO)"
  
  balanced:
    condition: "위 어느 쪽도 명확하지 않을 때"
    allocation: "섹터별로 KR-US 5:5에서 시작, 종목 펀더멘털로 조정"
```

### 11.3 신호 강도 점수 (Signal Strength Score)

각 시나리오의 트리거 조건은 모두 AND로 묶여 있으므로, 충족된 조건 개수 ÷ 총 조건 개수 = 신호 강도. 0.7 이상일 때만 시나리오에 따른 비중 조정 실행. 0.4-0.7은 관망, 0.4 미만은 무시.

---

## 12. 업데이트 / 리뷰 규칙

- **이 페이지는 v1 잠금**: 차원·임계값·시나리오 매핑은 변경하지 않는다. 추가만 가능 (예: 새 차원 9 추가, 시나리오 추가)
- **데이터 값 갱신**: `recent_value`, `recent_2026_04` 같은 필드는 별도 데이터 페이지(`wiki/macro/03-outlook-data.md`)에서 추적. 본 페이지 본문은 손대지 않는다
- **분기 리뷰**: 매 분기 첫째주 시나리오 매핑 정확도 사후검증 (`Output/macro-backtest-YYYY-Q.md` 작성)
- **검증 후 기록**: 새 지표 추가 시 무료 1차 자료 URL 살아있는지 WebFetch로 확인 후 추가
