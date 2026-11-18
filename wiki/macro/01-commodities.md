---
title: 원자재 모니터링 매트릭스 (Phase 1)
created: 2026-04-25
updated: 2026-04-26
sources:
  - yfinance
  - EIA
  - USGS
  - World Bank Pink Sheet
  - LME
  - Johnson Matthey
  - DOE
  - CME
  - IEA Critical Minerals
tags: [macro, commodities, monitoring, signal-mapping]
status: locked-v1
phase: 1
total_commodities: 52
---

# 원자재 모니터링 매트릭스 (Phase 1)

## 1. 페이지 철학

원자재는 산업의 1차 입력재이자 동시에 거시 충격의 1차 전달경로다. 본 매트릭스는 "원자재 가격 변동 → 어떤 섹터·종목의 EPS·서사에 어떤 방향·시차로 작용하는가"를 사전 규격화한 시그널 맵이다. 한국 투자자가 KR/US 양쪽 종목 매수 결정에 사용한다는 전제로, 1차 소스는 모두 무료 공개 데이터(yfinance, EIA, USGS, World Bank Pink Sheet, LME, Johnson Matthey, DOE, CME, IEA)로 한정했다.

각 항목은 (1) 인과 메커니즘, (2) historical event 검증, (3) lead/lag 추정, (4) false-signal noise 검토 4종을 모두 갖춰야 등재된다. 인과가 명확하지 않으면 등재하지 않는다. 시장이 얕거나(로듐) 구조가 흔들리는(코발트) 항목은 5장에서 신호력 약화로 분류했다.

매트릭스는 v1 잠금 후 추가만 허용하고 변경하지 않는다. Phase 2에서 섹터를 9~27개로 확장할 때 본 파일에 매핑만 보강한다. 사후 백테스트는 분기별로 `Output/commodity-backtest-YYYY-Q.md`에 누적한다.

## 2. 채택 기준

1. **인과 메커니즘 명확**: 원자재 X가 섹터 Y에 영향을 주는 경로가 한 문장 이내로 설명 가능
2. **Historical event 인용**: yyyy.mm 형식으로 과거 충격 사례 1건 이상
3. **무료 1차 소스 URL**: yfinance·EIA·USGS·World Bank·LME·Johnson Matthey·DOE·CME 중 하나
4. **KR/US 종목 매핑**: 각 3-5개씩, KR은 `종목명(6자리)` 형식
5. **False signal noise 검토**: OPEC 회의·재고통계·일시적 cargo disruption 등 단기 잡음 제외 규칙

## 3. Part 1 — 에너지 · 산업금속 · 귀금속

### 3.1 카테고리 A: 에너지 (8)

#### A.1 WTI 원유

```yaml
id: crude_wti
name: WTI Crude Oil
unit: USD/barrel
primary_source:
  type: yfinance
  ticker: CL=F
  free: true
fallback_source:
  name: EIA Petroleum Spot Prices
  url: https://www.eia.gov/dnav/pet/pet_pri_spt_s1_d.htm
volatility_baseline: "60일 표준편차 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
  daily_pct: 4.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜
    tickers_kr: ["SK이노베이션(096770)", "S-Oil(010950)", "GS(078930)", "한국가스공사(036460)"]
    tickers_us: [XOM, CVX, VLO, MPC, COP]
    mechanism: "유가↑ → 정유 크랙스프레드 확대 → 정유사 단기 EPS↑"
    lead_lag: "원유 +1주 → 정유사 +1-2주"
  - sector: 우주항공/방산
    direction: 수혜(지정학 동반시)
    tickers_us: [LMT, RTX, NOC]
    mechanism: "유가 급등 = 통상 지정학 동반 → 방산 발주 증가 분위기"
    lead_lag: "동시 또는 약간 후행"
historical_validation: "2022.02 우크라이나 침공 → WTI $90→$130 (+44%) → XOM +30%, VLO +50% (3개월 누적)"
noise_check: "OPEC 회의·SPR 방출·주간 재고 발표 시 단기 변동성. Z>2 임계 적용 시 ~15% false signal"
```

#### A.2 Brent 원유

```yaml
id: crude_brent
name: Brent Crude Oil
unit: USD/barrel
primary_source:
  type: yfinance
  ticker: BZ=F
  free: true
fallback_source:
  name: EIA Brent Spot
  url: https://www.eia.gov/dnav/pet/hist/RBRTED.htm
volatility_baseline: "60일 표준편차 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
  brent_wti_spread: 5.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜
    tickers_kr: ["SK이노베이션(096770)", "S-Oil(010950)", "현대중공업(329180)"]
    tickers_us: [XOM, CVX, BP, SHEL, TTE]
    mechanism: "한국 정유사 원료가 중동산 두바이에 더 가깝지만 Brent와 강한 동행. Brent↑ → 한국 정유 매출↑"
    lead_lag: "원유 +1주 → 한국 정유사 +1-2주"
  - sector: 우주항공/방산
    direction: 간접 수혜
    tickers_kr: ["한화에어로스페이스(012450)", "LIG넥스원(079550)"]
    mechanism: "Brent 급등은 중동·러시아 지정학 신호. 방산 수출 협상력↑"
    lead_lag: "1-3개월 후행"
historical_validation: "2014.06 ISIS 모술 점령 → Brent $115 (+15%), 6개월 후 한화에어로 +20%"
noise_check: "Brent-WTI 스프레드 5달러 이상 벌어지면 한쪽만 신호. 둘 다 동행할 때만 시그널 채택"
```

#### A.3 Henry Hub 천연가스

```yaml
id: ng_henry_hub
name: Henry Hub Natural Gas
unit: USD/MMBtu
primary_source:
  type: yfinance
  ticker: NG=F
  free: true
fallback_source:
  name: EIA Natural Gas Spot
  url: https://www.eia.gov/dnav/ng/ng_pri_fut_s1_d.htm
volatility_baseline: "60일 표준편차 ~5-8%"
anomaly_threshold:
  zscore_60d: 2.0
  daily_pct: 8.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜
    tickers_kr: ["한국가스공사(036460)", "포스코인터내셔널(047050)"]
    tickers_us: [LNG, EQT, AR, RRC, CHK]
    mechanism: "Henry Hub↑ → 미국 LNG 수출 마진 확대 → Cheniere(LNG) 직접 수혜"
    lead_lag: "동시 또는 +2주"
  - sector: AI/반도체
    direction: 부담(데이터센터 전력비용)
    tickers_us: [MSFT, GOOGL, META]
    mechanism: "미국 데이터센터 전력 30%가 가스 발전. Henry Hub↑ → 클라우드 OPEX 부담"
    lead_lag: "+1-2분기"
historical_validation: "2022.08 EU 가스대란 → Henry Hub $9 (+150% YoY) → LNG +60%, EQT +80%"
noise_check: "주간 EIA 재고통계·기온 예보 단기 충격. 30일 평균선 break일 때만 채택"
```

#### A.4 JKM (Japan-Korea Marker) LNG

```yaml
id: ng_jkm
name: JKM LNG (Asia spot)
unit: USD/MMBtu
primary_source:
  type: S&P Global Platts JKM (월별 무료 요약)
  url: https://www.spglobal.com/commodityinsights/en/market-insights/latest-news/lng
fallback_source:
  name: EIA LNG Monthly
  url: https://www.eia.gov/naturalgas/monthly/
volatility_baseline: "월간 변동 ~10-20%"
anomaly_threshold:
  monthly_pct: 25.0
  jkm_hh_spread: 8.0
primary_effects:
  - sector: 수소/에너지
    direction: 부담(KR 수입), 수혜(US 수출)
    tickers_kr: ["한국가스공사(036460)", "한국전력(015760)", "포스코인터내셔널(047050)"]
    tickers_us: [LNG, NFE, GLNG]
    mechanism: "JKM↑ → KOGAS 원료비 부담↑(요금 후행 반영), 한전 LNG 발전원가↑. 미국 LNG 수출사는 직접 수혜"
    lead_lag: "JKM → KOGAS 분기실적 1-2분기 후행"
  - sector: SMR/원자력
    direction: 간접 수혜(서사)
    tickers_kr: ["두산에너빌리티(034020)", "한전기술(052690)"]
    tickers_us: [CCJ, SMR, BWXT]
    mechanism: "JKM 고공시 원자력 경제성 부각 → SMR 정책 모멘텀"
    lead_lag: "+3-6개월"
historical_validation: "2022.03 JKM $84 (사상최고) → 한국 전력요금 인상 + 두산에너빌리티 +40% (6개월)"
noise_check: "동절기 cargo 단기 충격. 월평균 기준으로만 채택"
```

#### A.5 TTF (Title Transfer Facility) 유럽 가스

```yaml
id: ng_ttf
name: TTF Dutch Gas
unit: EUR/MWh
primary_source:
  type: ICE Endex (지연 데이터 무료)
  url: https://www.ice.com/products/27996665/Dutch-TTF-Gas-Futures
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "월간 ~10-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜(US LNG 수출)
    tickers_kr: ["삼성중공업(010140)", "현대미포조선(010620)", "한국조선해양(009540)"]
    tickers_us: [LNG, EQT, CTRA]
    mechanism: "TTF 고공 → EU LNG 수입수요↑ → 한국 LNG선 발주↑(2022-2023 KR 조선 슈퍼사이클 핵심 동인)"
    lead_lag: "TTF → 조선 수주 +6-12개월"
  - sector: 화학/생명공학
    direction: 부담(EU 화학기업)
    tickers_us: [DOW]
    mechanism: "TTF↑ → BASF 등 EU 화학사 원가 폭등 → 시장점유율을 LG화학·롯데케미칼이 흡수"
    tickers_kr_secondary: ["LG화학(051910)", "롯데케미칼(011170)"]
    lead_lag: "+1-2분기"
historical_validation: "2022.08 TTF €340 (+1000% YoY) → 한국 조선 3사 LNG선 수주 +300%"
noise_check: "EU 저장 충전율 발표·러시아 가스공급 뉴스 단기 충격. 1주 평균 사용"
```

#### A.6 Newcastle 석탄

```yaml
id: coal_newcastle
name: Newcastle Thermal Coal
unit: USD/ton
primary_source:
  type: World Bank Pink Sheet (월별 무료)
  url: https://www.worldbank.org/en/research/commodity-markets
fallback_source:
  name: IEA Coal Information
  url: https://www.iea.org/topics/coal
volatility_baseline: "월간 ~8-12%"
anomaly_threshold:
  monthly_pct: 15.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜(석탄 발전 사업자), 부담(KR 수입)
    tickers_kr: ["한국전력(015760)", "포스코홀딩스(005490)"]
    tickers_us: [BTU, ARCH, TECK]
    mechanism: "Newcastle↑ → 한전 발전원가↑(석탄 비중 35%), POSCO 코크스 원가↑"
    lead_lag: "코킹 가격 → POSCO 분기실적 1-2분기 후행"
  - sector: SMR/원자력
    direction: 간접 수혜(서사)
    tickers_kr: ["두산에너빌리티(034020)"]
    tickers_us: [CCJ, URNM]
    mechanism: "석탄 고공시 원자력 LCOE 상대 경제성↑ → 정책 모멘텀"
    lead_lag: "+6-12개월"
historical_validation: "2022.09 Newcastle $440 (사상최고) → 한전 적자 32조원, 두산에너빌리티 SMR 모멘텀 강화"
noise_check: "호주 사이클론·중국 수입정책 단기 충격. 월평균만 사용"
```

#### A.7 우라늄 U3O8

```yaml
id: uranium_u3o8
name: Uranium U3O8 Spot
unit: USD/lb
primary_source:
  type: UxC Weekly (월별 무료 요약)
  url: https://www.uxc.com/p/prices/UxCPrices.aspx
fallback_source:
  name: Cameco Uranium Price
  url: https://www.cameco.com/invest/markets/uranium-price
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 15.0
  zscore_60d: 2.0
primary_effects:
  - sector: SMR/원자력
    direction: 수혜
    tickers_kr: ["두산에너빌리티(034020)", "한전기술(052690)", "한전KPS(051600)", "비에이치아이(083650)"]
    tickers_us: [CCJ, URNM, URA, SMR, BWXT, LEU, OKLO]
    mechanism: "U3O8↑ → 우라늄 마이너 직접 수혜. SMR 테마는 우라늄 가격에 1차 sentiment lead"
    lead_lag: "U3O8 +0주 → SMR 테마 동시"
historical_validation: "2023.09 우라늄 $50→$80 랠리 → CCJ +60%, 두산에너빌리티 +90% (6개월)"
noise_check: "Sprott Physical Uranium Trust(SPUT) 매집 시 인위적 가격 상승. 펀더멘털과 분리해서 봐야"
```

#### A.8 3-2-1 크랙 스프레드

```yaml
id: crack_321
name: "3-2-1 Crack Spread (3 crude → 2 gasoline + 1 diesel)"
unit: USD/barrel
primary_source:
  type: EIA Refining Margins
  url: https://www.eia.gov/petroleum/weekly/
fallback_source:
  name: yfinance (CL=F, RB=F, HO=F 합성)
  ticker: "CL=F + RB=F + HO=F"
volatility_baseline: "주간 ~10-15%"
anomaly_threshold:
  weekly_pct: 20.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜
    tickers_kr: ["S-Oil(010950)", "SK이노베이션(096770)", "GS(078930)"]
    tickers_us: [VLO, MPC, PSX, DK, PBF]
    mechanism: "크랙 스프레드 = 정유사 마진의 직접 지표. 원유보다 후행성이 적고 노이즈 적음"
    lead_lag: "크랙 +0주 → 정유사 분기실적 +1분기"
historical_validation: "2022.06 크랙 $60 (사상최고) → S-Oil +50%, VLO +70% (3개월)"
noise_check: "허리케인 시즌(8-10월) 일시 급등 흔함. 4주 평균이 임계 돌파시만 채택"
```

### 3.2 카테고리 B: 산업금속 (9)

#### B.1 구리

```yaml
id: copper
name: LME Copper
unit: USD/ton (LME), USD/lb (COMEX)
primary_source:
  type: yfinance
  ticker: HG=F
  free: true
fallback_source:
  name: LME Copper
  url: https://www.lme.com/en/Metals/Non-ferrous/LME-Copper
volatility_baseline: "60일 표준편차 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
  daily_pct: 3.0
primary_effects:
  - sector: AI/반도체
    direction: 수혜(전력 인프라)
    tickers_kr: ["LS ELECTRIC(010120)", "대한전선(001440)", "LS(006260)", "가온전선(000500)", "일진전기(103590)"]
    tickers_us: [FCX, SCCO, ETN, EMR]
    mechanism: "AI 데이터센터 전력 수요↑ → 변압기·전력 케이블 수요↑ → 구리 수요 6-12개월 선행"
    lead_lag: "구리 → 전력기기 매출 +6-12개월"
  - sector: 로봇
    direction: 간접 수혜
    tickers_kr: ["LS ELECTRIC(010120)"]
    tickers_us: [ETN, ROK]
    mechanism: "로봇 모터·자동화 인프라 구리 함량↑"
    lead_lag: "+6개월"
historical_validation: "2024.03 AI 데이터센터 붐 → 구리 $9000→$11000 (+22%), LS ELECTRIC +120% (6개월)"
noise_check: "중국 부동산 수요·LME 재고 단기 변동. 60일 SMA break + Z>2 동시 충족"
```

#### B.2 알루미늄

```yaml
id: aluminum
name: LME Aluminum
unit: USD/ton
primary_source:
  type: yfinance
  ticker: ALI=F
  free: true
fallback_source:
  name: LME Aluminum
  url: https://www.lme.com/en/Metals/Non-ferrous/LME-Aluminium
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 우주항공/방산
    direction: 부담(원가↑)
    tickers_kr: ["한화에어로스페이스(012450)", "한국항공우주(047810)", "LIG넥스원(079550)"]
    tickers_us: [BA, LMT, RTX, NOC]
    mechanism: "항공기 동체 알루미늄 비중 70%. 알루미늄↑ → 항공기 제조원가↑"
    lead_lag: "+1-2분기"
  - sector: AI/반도체
    direction: 부담(서버 케이스·방열판)
    tickers_us: [DELL, HPE, SMCI]
    mechanism: "서버 섀시·방열 알루미늄 사용. 알루미늄↑ → 서버 BOM↑"
    lead_lag: "+1분기"
historical_validation: "2022.03 러시아 Rusal 제재 위협 → 알루미늄 $4000 (+50%) → BA, 한국항공우주 마진 압박"
noise_check: "중국 전력제한·LME 러시아 재고 정책 단기 변동"
```

#### B.3 니켈

```yaml
id: nickel
name: LME Nickel
unit: USD/ton
primary_source:
  type: LME Nickel
  url: https://www.lme.com/en/Metals/Non-ferrous/LME-Nickel
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
  daily_pct: 8.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(배터리 ESS)
    tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "에코프로비엠(247540)", "엘앤에프(066970)"]
    tickers_us: [TSLA, ALB, LAC]
    mechanism: "NCM/NCA 배터리 양극재 핵심. 니켈↑ → 배터리 BOM↑ → 데이터센터 ESS·EV 부담"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담(특수강)
    tickers_kr: ["세아베스틸(001430)"]
    tickers_us: [HAYN, ATI]
    mechanism: "제트엔진 슈퍼합금 니켈 함량 50%+. 니켈↑ → 엔진 원가↑"
    lead_lag: "+2-3분기"
historical_validation: "2022.03 LME 니켈 쇼트 스퀴즈 → $48000→$100000 (+108% 1주) → 양극재 마진 -10%pt"
noise_check: "LME 거래정지·인도네시아 광산정책 등 빈번한 단기 충격. 월평균 사용"
```

#### B.4 아연

```yaml
id: zinc
name: LME Zinc
unit: USD/ton
primary_source:
  type: LME Zinc
  url: https://www.lme.com/en/Metals/Non-ferrous/LME-Zinc
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 우주항공/방산
    direction: 간접(아연도금강)
    tickers_kr: ["고려아연(010130)", "영풍(000670)", "POSCO홀딩스(005490)"]
    tickers_us: [TECK]
    mechanism: "아연 = 강철 도금 1차 수요. 인프라·방산 강재 부식방지"
    lead_lag: "+1-2분기"
historical_validation: "2022.10 EU 가스대란 → 유럽 아연 제련소 가동중단 → 아연 $4000 (+30%) → 고려아연 +25%"
noise_check: "단일 제련소 가동중단 뉴스 빈번. LME 재고 추세와 동행시만 채택"
```

#### B.5 주석 (Tin)

```yaml
id: tin
name: LME Tin
unit: USD/ton
primary_source:
  type: LME Tin
  url: https://www.lme.com/en/Metals/Non-ferrous/LME-Tin
fallback_source:
  name: USGS Tin Statistics
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-tin.pdf
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(반도체 솔더)
    tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)", "LG이노텍(011070)", "심텍(222800)"]
    tickers_us: [INTC, TXN, AVGO]
    mechanism: "반도체 패키징 솔더 핵심. 주석↑ → IC 패키징 BOM↑"
    lead_lag: "+1-2분기"
historical_validation: "2021.03 미얀마 쿠데타(세계 2위 산지) → 주석 $20k→$50k (+150%) → 반도체 패키징 마진 압박"
noise_check: "인도네시아·미얀마 정치 리스크 빈번. 분기평균 사용"
```

#### B.6 납

```yaml
id: lead
name: LME Lead
unit: USD/ton
primary_source:
  type: LME Lead
  url: https://www.lme.com/en/Metals/Non-ferrous/LME-Lead
fallback_source:
  name: USGS Lead Statistics
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-lead.pdf
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 우주항공/방산
    direction: 수혜(탄약·납축전지)
    tickers_kr: ["풍산(103140)", "고려아연(010130)"]
    tickers_us: [OLN, AYI]
    mechanism: "탄약·소형 무기 납 사용. 풍산은 탄약 납 직접 사용"
    lead_lag: "+1-2분기"
historical_validation: "2022.02 우크라전 → 탄약 수요↑ → 납 +20%, 풍산 +60% (6개월)"
noise_check: "차량 납축전지 수요와 혼재. 방산 발주 데이터와 교차검증"
```

#### B.7 철광석

```yaml
id: iron_ore
name: Iron Ore 62% Fe (Tianjin)
unit: USD/ton
primary_source:
  type: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
fallback_source:
  name: SGX TSI Iron Ore (지연 무료)
  url: https://www.sgx.com/derivatives/products/iron-ore
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 15.0
primary_effects:
  - sector: 우주항공/방산
    direction: 간접(강재)
    tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)"]
    tickers_us: [VALE, RIO, BHP, CLF, X]
    mechanism: "철광석↑ → 제철사 원가↑(매출 후행 반영) / 광산사 직접 수혜"
    lead_lag: "POSCO 마진 -1분기 (원가 충격), 광산사 +0"
historical_validation: "2021.07 철광석 $230 (사상최고) → POSCO 분기 영업이익 -30%"
noise_check: "중국 수요·브라질 댐 사고 단기 충격. 월평균 사용"
```

#### B.8 강철 HRC (Hot-Rolled Coil)

```yaml
id: steel_hrc
name: Hot-Rolled Coil Steel
unit: USD/ton
primary_source:
  type: yfinance
  ticker: HRC=F
  free: true
fallback_source:
  name: World Steel Association
  url: https://worldsteel.org/steel-topics/statistics/
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 우주항공/방산
    direction: 부담→수혜(price-through 가능시)
    tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)", "세아베스틸(001430)"]
    tickers_us: [NUE, X, STLD, CLF]
    mechanism: "HRC 가격 = 제철사 매출 1차 지표. 철광석/석탄 원가와 동시 보면 마진 추정"
    lead_lag: "동시"
  - sector: SMR/원자력
    direction: 간접(원전 압력용기)
    tickers_kr: ["두산에너빌리티(034020)", "비에이치아이(083650)"]
    mechanism: "원자로 압력용기·대형 케이싱 특수강 사용"
    lead_lag: "+2-3분기"
historical_validation: "2021.08 미국 HRC $1900 (사상최고) → NUE +70%, POSCO +30%"
noise_check: "관세·반덤핑 정책 단기 충격. 미·EU·KR 가격 동행 확인"
```

#### B.9 코발트

```yaml
id: cobalt
name: LME Cobalt
unit: USD/ton
primary_source:
  type: LME Cobalt
  url: https://www.lme.com/en/Metals/Minor-metals/LME-Cobalt
fallback_source:
  name: USGS Cobalt
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-cobalt.pdf
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(NCM 배터리)
    tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "에코프로비엠(247540)"]
    tickers_us: [TSLA, ALB]
    mechanism: "NCM 양극재 코발트 함량 10-20%. LFP 전환으로 구조적 약화"
    lead_lag: "+1-2분기"
historical_validation: "2018.04 코발트 $95k (사상최고) → 양극재 마진 -15%pt → 이후 LFP 전환 가속"
noise_check: "LFP 전환으로 신호력 약화. 5장에서 우선순위 하향"
```

### 3.3 카테고리 C: 귀금속 (5)

#### C.1 금

```yaml
id: gold
name: Gold Spot
unit: USD/oz
primary_source:
  type: yfinance
  ticker: GC=F
  free: true
fallback_source:
  name: World Gold Council
  url: https://www.gold.org/goldhub/data/gold-prices
volatility_baseline: "60일 ~1-2%"
anomaly_threshold:
  zscore_60d: 2.0
  daily_pct: 2.5
primary_effects:
  - sector: 사이버보안
    direction: 간접(공포지수 동행)
    tickers_kr: ["안랩(053800)", "라온시큐어(042510)"]
    tickers_us: [CRWD, PANW, ZS, S]
    mechanism: "금 급등 = 지정학·금융 불안. 사이버보안 사고 빈발과 동행"
    lead_lag: "동시 또는 -2주 선행"
  - sector: 우주항공/방산
    direction: 수혜(지정학)
    tickers_kr: ["한화에어로스페이스(012450)", "현대로템(064350)"]
    tickers_us: [LMT, NOC, RTX]
    mechanism: "금 랠리 = 지정학 긴장 → 방산 발주 모멘텀"
    lead_lag: "+1-3개월"
historical_validation: "2024.04 금 $2400 (사상최고) → 한화에어로 +80% (3개월), CRWD +30%"
noise_check: "Fed 금리 기대만으로 움직이는 구간 있음. 달러DXY와 함께 봐야"
```

#### C.2 은

```yaml
id: silver
name: Silver Spot
unit: USD/oz
primary_source:
  type: yfinance
  ticker: SI=F
  free: true
fallback_source:
  name: Silver Institute
  url: https://www.silverinstitute.org/silver-price/
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(반도체 본딩 와이어)
    tickers_kr: ["LG이노텍(011070)", "SK하이닉스(000660)", "심텍(222800)"]
    tickers_us: [TSM, AMD, NVDA]
    mechanism: "반도체 본딩 와이어·전도성 페이스트 은 사용. 은↑ → 패키징 원가↑"
    lead_lag: "+1-2분기"
  - sector: 수소/에너지
    direction: 수혜(태양광)
    tickers_kr: ["한화솔루션(009830)", "OCI홀딩스(010060)"]
    tickers_us: [FSLR, ENPH]
    mechanism: "태양광 셀 전극 은 페이스트 사용. 은 가격이 곧 태양광 BOM"
    lead_lag: "+1분기"
historical_validation: "2020.08 은 $30 (+50% YoY) → FSLR +40%, 한화솔루션 +60%"
noise_check: "투자수요(SLV ETF) 변동성 높음. 산업수요 비중 50% 고려"
```

#### C.3 백금

```yaml
id: platinum
name: Platinum Spot
unit: USD/oz
primary_source:
  type: yfinance
  ticker: PL=F
  free: true
fallback_source:
  name: Johnson Matthey PGM Prices
  url: https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 수소/에너지
    direction: 부담(PEM 수소)
    tickers_kr: ["두산퓨얼셀(336260)", "현대모비스(012330)", "효성중공업(298040)"]
    tickers_us: [PLUG, BLDP, BE]
    mechanism: "PEM 수전해/연료전지 촉매 백금. 백금↑ → PEM 수소 CAPEX↑"
    lead_lag: "+2-4분기"
historical_validation: "2021.02 백금 $1300 (+40% YoY) → 두산퓨얼셀 마진 압박, PLUG 가이던스 하향"
noise_check: "디젤차 촉매 수요 감소로 구조적 약화. 수소 수요로 대체 중"
```

#### C.4 팔라듐

```yaml
id: palladium
name: Palladium Spot
unit: USD/oz
primary_source:
  type: yfinance
  ticker: PA=F
  free: true
fallback_source:
  name: Johnson Matthey PGM Prices
  url: https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(MLCC·커넥터)
    tickers_kr: ["삼성전기(009150)", "LG이노텍(011070)"]
    tickers_us: [AVGO]
    mechanism: "MLCC 내부전극·커넥터 도금에 팔라듐 사용. 팔라듐↑ → MLCC 원가↑"
    lead_lag: "+1-2분기"
historical_validation: "2022.03 러시아 제재 우려 → 팔라듐 $3400 (사상최고) → 삼성전기 마진 -3%pt"
noise_check: "내연차 촉매 80% 비중, EV 전환으로 구조적 수요 감소. 단기 시그널만 유효"
```

#### C.5 로듐

```yaml
id: rhodium
name: Rhodium Spot
unit: USD/oz
primary_source:
  type: Johnson Matthey PGM Prices
  url: https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices
fallback_source:
  name: Heraeus PGM
  url: https://www.heraeus.com/en/hpm/products_and_solutions/precious_metals_trading/precious_metal_quotes/precious_metals_quotes.html
volatility_baseline: "주간 ~10-20%"
anomaly_threshold:
  monthly_pct: 30.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(특수 도금)
    tickers_us: [AVGO]
    mechanism: "고급 커넥터 도금. 시장이 매우 얕아 신호 노이즈 큼"
    lead_lag: "+1분기"
historical_validation: "2021.04 로듐 $29000 (사상최고) → 그러나 시장이 얕아 단일 거래로 가격 ±10%"
noise_check: "시장 매우 얕음 (연 30톤). 단일 거래로 가격 ±10%. 5장에서 우선순위 하향"
```

## 4. Part 2 — 희소금속 · 가스 · 농산물 · 화학 · 바이오

### 4.1 카테고리 D: 희소금속/Critical (10)

#### D.1 리튬

```yaml
id: lithium
name: Lithium Carbonate (battery grade)
unit: USD/ton
primary_source:
  type: Fastmarkets / Trading Economics
  url: https://tradingeconomics.com/commodity/lithium
fallback_source:
  name: USGS Lithium
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-lithium.pdf
volatility_baseline: "월간 ~10-20%"
anomaly_threshold:
  monthly_pct: 25.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(데이터센터 ESS)
    tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "에코프로비엠(247540)", "엘앤에프(066970)", "포스코퓨처엠(003670)"]
    tickers_us: [ALB, LAC, SQM, TSLA]
    mechanism: "리튬↑ → 배터리 BOM 30%↑ → ESS·EV 부담"
    lead_lag: "+1-2분기"
historical_validation: "2022.11 리튬 $80k (+500% YoY) → 양극재 마진 일시 +20%pt, 이후 폭락 -90%"
noise_check: "수급 사이클 매우 변동. 6개월 SMA 사용 권장"
```

#### D.2 흑연

```yaml
id: graphite
name: Battery-grade Graphite
unit: USD/ton
primary_source:
  type: USGS Graphite
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-graphite.pdf
fallback_source:
  name: Benchmark Mineral Intelligence (월별 무료 요약)
  url: https://source.benchmarkminerals.com/
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 15.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(배터리 음극재)
    tickers_kr: ["포스코퓨처엠(003670)", "에코프로비엠(247540)"]
    tickers_us: [TSLA]
    mechanism: "음극재 핵심. 중국 90% 점유 → 공급망 안보 이슈"
    lead_lag: "+1-2분기"
historical_validation: "2023.10 중국 흑연 수출통제 → 흑연 +30%, 포스코퓨처엠 +40% (3개월)"
noise_check: "중국 수출쿼터 정책 단기 충격"
```

#### D.3 망간

```yaml
id: manganese
name: Manganese Ore 44%
unit: USD/dmtu
primary_source:
  type: USGS Manganese
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-manganese.pdf
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 15.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(NCM·LFMP 배터리)
    tickers_kr: ["에코프로비엠(247540)", "엘앤에프(066970)"]
    tickers_us: [ALB]
    mechanism: "NCM 양극재 망간 함량 10%, 차세대 LFMP에 더 중요"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담(특수강)
    tickers_kr: ["POSCO홀딩스(005490)"]
    mechanism: "강철 합금 1차 첨가물. 망간↑ → 특수강 원가↑"
    lead_lag: "+1-2분기"
historical_validation: "2024.03 South32 호주 광산 사고 → 망간 +50% → 양극재 비용 영향"
noise_check: "남아공·호주 광산 사고 빈번. 단일 사건 후 정상화 빠름"
```

#### D.4 네오디뮴 (Nd)

```yaml
id: neodymium
name: Neodymium Oxide
unit: USD/kg
primary_source:
  type: USGS Rare Earths
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-rare-earths.pdf
fallback_source:
  name: Shanghai Metals Market
  url: https://www.metal.com/Rare-Earth/201102250057
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: 로봇
    direction: 부담(영구자석 모터)
    tickers_kr: ["현대로템(064350)", "두산로보틱스(454910)", "레인보우로보틱스(277810)"]
    tickers_us: [MP, ABB, ROK]
    mechanism: "NdFeB 영구자석 = 로봇·EV 모터 1차 자석. 중국 70%+ 점유"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담(미사일 유도장치)
    tickers_us: [LMT, RTX]
    mechanism: "정밀 유도무기 영구자석"
    lead_lag: "+2-3분기"
historical_validation: "2010.09 중국 일본 희토류 수출중단 → Nd +400% → MP Materials 상장 추진"
noise_check: "중국 수출쿼터·환경규제 정책 충격 빈번"
```

#### D.5 디스프로슘 (Dy)

```yaml
id: dysprosium
name: Dysprosium Oxide
unit: USD/kg
primary_source:
  type: USGS Rare Earths
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-rare-earths.pdf
fallback_source:
  name: Shanghai Metals Market
  url: https://www.metal.com/Rare-Earth/201102250057
volatility_baseline: "월간 ~5-15%"
anomaly_threshold:
  monthly_pct: 25.0
primary_effects:
  - sector: 로봇
    direction: 부담(고온 영구자석)
    tickers_kr: ["현대로템(064350)", "두산로보틱스(454910)"]
    tickers_us: [MP]
    mechanism: "Dy 첨가 NdFeB 자석은 고온 안정성↑. 로봇·EV·풍력에 필수"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담
    tickers_us: [LMT, RTX, NOC]
    mechanism: "전투기·미사일 액추에이터 고온 영구자석"
    lead_lag: "+2-3분기"
historical_validation: "2011.07 중국 수출쿼터 → Dy $3000/kg (사상최고) → 글로벌 자석 산업 재편"
noise_check: "중국 거의 100% 점유. 정책 리스크가 핵심"
```

#### D.6 터븀 (Tb)

```yaml
id: terbium
name: Terbium Oxide
unit: USD/kg
primary_source:
  type: USGS Rare Earths
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-rare-earths.pdf
fallback_source:
  name: Shanghai Metals Market
  url: https://www.metal.com/Rare-Earth/201102250057
volatility_baseline: "월간 ~10-20%"
anomaly_threshold:
  monthly_pct: 25.0
primary_effects:
  - sector: 우주항공/방산
    direction: 부담(고온 자석 첨가)
    tickers_us: [LMT, RTX, MP]
    mechanism: "Dy와 함께 고온 자석 첨가물. F-35 한 대당 ~400kg 희토류"
    lead_lag: "+2-3분기"
  - sector: 로봇
    direction: 부담
    tickers_kr: ["현대로템(064350)"]
    mechanism: "정밀 로봇 모터 고온 자석"
    lead_lag: "+1-2분기"
historical_validation: "2023.07 중국 갈륨·게르마늄 통제 직후 Tb $1300/kg → 자석 가격 동반 +15%"
noise_check: "시장 매우 얕음(연 ~500톤). 정책 충격이 사실상 유일한 시그널"
```

#### D.7 갈륨

```yaml
id: gallium
name: Gallium Metal 99.99%
unit: USD/kg
primary_source:
  type: USGS Gallium
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-gallium.pdf
fallback_source:
  name: Trading Economics
  url: https://tradingeconomics.com/commodity/gallium
volatility_baseline: "월간 ~10-20%"
anomaly_threshold:
  monthly_pct: 30.0
primary_effects:
  - sector: AI/반도체
    direction: 부담→수혜(KR 대체공급)
    tickers_kr: ["RFHIC(218410)", "DB하이텍(000990)"]
    tickers_us: [WOLF, NVDA]
    mechanism: "GaN 반도체(전력·5G·AI 가속기) 핵심. 중국 80%+ 점유. 2023.7 통제 → KR/JP 대체 수혜"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담(레이다·EW)
    tickers_kr: ["LIG넥스원(079550)", "한화시스템(272210)"]
    tickers_us: [RTX, LMT, NOC]
    mechanism: "AESA 레이다·전자전 GaN 송수신 모듈"
    lead_lag: "+2-3분기"
historical_validation: "2023.07 중국 갈륨 수출통제 → 가격 +50%, RFHIC +40% (3개월)"
noise_check: "중국 통제 정책 직접 시그널. 통제 강화/완화 발표가 가장 강한 신호"
```

#### D.8 게르마늄

```yaml
id: germanium
name: Germanium Metal
unit: USD/kg
primary_source:
  type: USGS Germanium
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-germanium.pdf
fallback_source:
  name: Trading Economics
  url: https://tradingeconomics.com/commodity/germanium
volatility_baseline: "월간 ~10-20%"
anomaly_threshold:
  monthly_pct: 30.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(고속 광통신)
    tickers_kr: ["대한광통신(010170)", "오이솔루션(138080)"]
    tickers_us: [LITE, COHR]
    mechanism: "광섬유·광검출기·SiGe 반도체 핵심. 중국 60% 점유"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담(야간투시·열영상)
    tickers_us: [LMT, RTX]
    mechanism: "적외선 광학 렌즈. 군용 야간투시·미사일 열추적"
    lead_lag: "+2-3분기"
historical_validation: "2023.07 중국 게르마늄 통제 → 가격 +60% → 광통신 BOM↑"
noise_check: "갈륨과 동시 통제. 둘을 함께 보면 신호 정합도↑"
```

#### D.9 인듐

```yaml
id: indium
name: Indium Metal
unit: USD/kg
primary_source:
  type: USGS Indium
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-indium.pdf
fallback_source:
  name: Trading Economics
  url: https://tradingeconomics.com/commodity/indium
volatility_baseline: "월간 ~5-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(ITO·디스플레이)
    tickers_kr: ["LG디스플레이(034220)", "이녹스첨단소재(272290)"]
    tickers_us: [AAPL]
    mechanism: "ITO(투명전극) 필수. 디스플레이·터치패널·태양광 CIGS"
    lead_lag: "+1-2분기"
  - sector: 수소/에너지
    direction: 부담(CIGS 태양광)
    tickers_us: [FSLR]
    mechanism: "CIGS 박막 태양광 핵심"
    lead_lag: "+1분기"
historical_validation: "2022.05 중국 인듐 수출규제 → 가격 +40% → LG디스플레이 BOM 영향"
noise_check: "디스플레이 수요 사이클과 혼재"
```

#### D.10 텔루륨/비스무트

```yaml
id: tellurium_bismuth
name: Tellurium & Bismuth
unit: USD/kg
primary_source:
  type: USGS Tellurium / Bismuth
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-tellurium.pdf
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "월간 ~10-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: 수소/에너지
    direction: 부담(CdTe 태양광)
    tickers_us: [FSLR]
    tickers_kr: ["한화솔루션(009830)"]
    mechanism: "Te = First Solar CdTe 박막 핵심. 텔루륨 시장 매우 얕음"
    lead_lag: "+1-2분기"
  - sector: 생명공학
    direction: 부담(약품 첨가물)
    tickers_kr: ["대웅제약(069620)"]
    mechanism: "비스무트 = 위장약(Pepto-Bismol) 원료. 시장 작지만 의약품에 필수"
    lead_lag: "+2-3분기"
historical_validation: "2022.04 텔루륨 +50% → FSLR 가이던스 하향"
noise_check: "두 원자재 모두 시장이 얕음. 단일 거래로 가격 ±10%"
```

### 4.2 카테고리 E: 반도체 특수가스 (4)

#### E.1 네온 (Ne)

```yaml
id: neon
name: Neon Gas (semiconductor grade)
unit: USD/m3
primary_source:
  type: 한국가스공업협회·SEMI 보고서 (월별 무료)
  url: https://www.semi.org/en
fallback_source:
  name: USGS Helium (네온은 부산물)
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-helium.pdf
volatility_baseline: "월간 ~10-30%"
anomaly_threshold:
  monthly_pct: 50.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(EUV/DUV 리소그래피)
    tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)", "TEMC(425040)", "원익머트리얼즈(104830)"]
    tickers_us: [TSM, INTC, ASML, AMAT]
    mechanism: "리소그래피 엑시머 레이저 핵심 가스. 우크라이나 50%+ 점유 → 전쟁 충격"
    lead_lag: "+1-2분기"
historical_validation: "2022.03 우크라전 → 네온 +600% → 삼성/SK하이닉스 가스 다변화 가속, TEMC 수혜"
noise_check: "우크라이나 정세 직접 영향. 한국 국산화 진행 중"
```

#### E.2 크립톤 (Kr)

```yaml
id: krypton
name: Krypton Gas
unit: USD/m3
primary_source:
  type: SEMI / 산업가스 보고서
  url: https://www.semi.org/en
fallback_source:
  name: 한국산업가스 협회 자료 (분기 무료)
volatility_baseline: "월간 ~10-30%"
anomaly_threshold:
  monthly_pct: 50.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(KrF 리소그래피·NAND 식각)
    tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)", "원익머트리얼즈(104830)"]
    tickers_us: [TSM, MU, ASML]
    mechanism: "KrF 엑시머 레이저, 메모리 식각. 우크라이나·러시아 60%+"
    lead_lag: "+1-2분기"
historical_validation: "2022.03 우크라전 → 크립톤 +400% → 메모리 가스 다변화"
noise_check: "네온과 같은 ASU 부산물. 두 가스 동시 모니터링"
```

#### E.3 크세논 (Xe)

```yaml
id: xenon
name: Xenon Gas
unit: USD/m3
primary_source:
  type: SEMI 보고서
  url: https://www.semi.org/en
fallback_source:
  name: 한국산업가스 협회
volatility_baseline: "월간 ~15-30%"
anomaly_threshold:
  monthly_pct: 50.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(고급 식각·이온주입)
    tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)"]
    tickers_us: [LRCX, AMAT, TSM]
    mechanism: "고급 노드 식각·이온주입. 시장 매우 얕음(연 50톤)"
    lead_lag: "+1-2분기"
  - sector: 우주항공/방산
    direction: 부담(이온 추진 위성)
    tickers_us: [LMT, NOC, MAXR]
    mechanism: "위성 이온엔진 추진제. SpaceX Starlink 사용"
    lead_lag: "+2-3분기"
historical_validation: "2022.03 우크라전 → 크세논 +500%, 위성 발사 비용 영향"
noise_check: "시장 매우 얕아 단일 거래 충격 큼"
```

#### E.4 헬륨

```yaml
id: helium
name: Helium-4 (industrial grade)
unit: USD/Mcf
primary_source:
  type: USGS Helium
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-helium.pdf
fallback_source:
  name: BLM Helium Sale Report (반기 무료)
  url: https://www.blm.gov/programs/energy-and-minerals/helium
volatility_baseline: "분기 ~10-20%"
anomaly_threshold:
  quarterly_pct: 25.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(쿨링·리소그래피)
    tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)"]
    tickers_us: [TSM, ASML, AMAT, APD, LIN]
    mechanism: "반도체 fab 쿨링·MRI·리소그래피. 카타르·미국 70%+ 점유"
    lead_lag: "+1-2분기"
  - sector: 양자컴퓨팅
    direction: 부담(극저온 쿨링)
    tickers_us: [IBM, GOOGL, IONQ, RGTI, QBTS]
    mechanism: "초전도 큐비트 He-4 dilution refrigerator 핵심. 헬륨↑ → 양자 OPEX↑"
    lead_lag: "+1-2분기"
  - sector: 생명공학
    direction: 부담(MRI)
    tickers_us: [GE, MDT]
    mechanism: "MRI 초전도 자석 냉각"
    lead_lag: "+2-4분기"
historical_validation: "2022.06 BLM 매각·러시아 Amur 가스 플랜트 사고 → 헬륨 +135% (Helium Shortage 4.0) → ASML, 양자 기업 OPEX 압박"
noise_check: "BLM(미 정부 비축) 매각 일정 정책 충격"
```

### 4.3 카테고리 F: 양자/방산 특수재 (3)

#### F.1 헬륨-3 (He-3)

```yaml
id: helium_3
name: Helium-3 Isotope
unit: USD/liter (STP)
primary_source:
  type: DOE Isotope Program
  url: https://www.isotopes.gov/
fallback_source:
  name: Linde Isotopes (가격 미공개, 정부 배급)
volatility_baseline: "연 ~10-30% (정부 배급가 기반)"
anomaly_threshold:
  yearly_pct: 30.0
primary_effects:
  - sector: 양자컴퓨팅
    direction: 부담(극저온 쿨링 핵심)
    tickers_us: [IBM, GOOGL, IONQ, RGTI, QBTS, HON]
    mechanism: "He-3/He-4 dilution refrigerator는 mK 도달 유일한 실용기술. He-3↑ = 양자 캐파 한계"
    lead_lag: "+1-2분기 (장비 생산 주기)"
  - sector: 우주항공/방산
    direction: 부담(중성자 검출기)
    tickers_us: [LMT, RTX, NOC]
    mechanism: "He-3 중성자 검출기는 핵 탐지·세관 검색에 필수. DHS 핵심 수요"
    lead_lag: "+2-3분기"
historical_validation: "2008-2010 He-3 배급 위기 → 미국 DHS·양자 연구 동시 차질, DOE 가격 4배 인상"
noise_check: "민간시장 사실상 없음, DOE 배급제. 양자컴퓨팅 hidden moat — 시장 저평가"
```

#### F.2 이리듐 (Ir)

```yaml
id: iridium
name: Iridium Metal
unit: USD/oz
primary_source:
  type: Johnson Matthey PGM Prices
  url: https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices
fallback_source:
  name: Heraeus PGM
  url: https://www.heraeus.com/en/hpm/products_and_solutions/precious_metals_trading/precious_metal_quotes/precious_metals_quotes.html
volatility_baseline: "월간 ~5-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: 수소/에너지
    direction: 부담(PEM 수전해 진짜 병목)
    tickers_kr: ["두산퓨얼셀(336260)", "효성중공업(298040)"]
    tickers_us: [PLUG, BLDP, BE]
    mechanism: "PEM 수전해 OER 촉매 핵심. 연 7-8톤 채굴 vs 1GW PEM ~1톤 필요 → 진짜 병목"
    lead_lag: "+2-4분기"
  - sector: 우주항공/방산
    direction: 부담(고온 합금)
    tickers_us: [GE, RTX]
    mechanism: "제트엔진 일부 부품, 우주선 추력기 노즐"
    lead_lag: "+2-3분기"
historical_validation: "2021.04 이리듐 $6500/oz (사상최고) → PEM 수전해 BOM 50%↑ 우려, 그린수소 CAPEX 재산정"
noise_check: "백금족 중 가장 희소. 시장 저평가 — Pt/Pd보다 진짜 병목"
```

#### F.3 티타늄

```yaml
id: titanium
name: Titanium Sponge
unit: USD/kg
primary_source:
  type: USGS Titanium
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-titanium.pdf
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "월간 ~5-10%"
anomaly_threshold:
  monthly_pct: 15.0
primary_effects:
  - sector: 우주항공/방산
    direction: 부담(항공기 동체·엔진)
    tickers_kr: ["한국항공우주(047810)", "한화에어로스페이스(012450)", "현대비앤지스틸(004560)"]
    tickers_us: [BA, LMT, RTX, ATI, HAYN, TMST]
    mechanism: "항공기 동체·엔진 핵심. F-35 동체 25%, 787 동체 15% 티타늄. 러시아 VSMPO 30%+ 점유"
    lead_lag: "+1-2분기"
  - sector: 생명공학
    direction: 부담(임플란트)
    tickers_kr: ["오스템임플란트(048260)", "덴티움(145720)"]
    tickers_us: [SYK, ZBH, MDT]
    mechanism: "치과·정형외과 임플란트 의료등급 티타늄"
    lead_lag: "+2-3분기"
historical_validation: "2022.03 러시아 VSMPO 제재 우려 → 티타늄 +30% → BA, 한국항공우주 공급망 재편"
noise_check: "러시아 의존도가 핵심 리스크. 제재·관세 정책 직접 시그널"
```

### 4.4 카테고리 G: 농산물 (6)

#### G.1 옥수수

```yaml
id: corn
name: Corn
unit: USD/bushel
primary_source:
  type: yfinance
  ticker: ZC=F
  free: true
fallback_source:
  name: USDA WASDE
  url: https://www.usda.gov/oce/commodity/wasde
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 생명공학
    direction: 부담(사료·식품)
    tickers_kr: ["하림(136480)", "마니커(027740)", "팜스코(036580)"]
    tickers_us: [TSN, ADM, BG, PPC]
    mechanism: "사료·에탄올·식품 1차 원료. 옥수수↑ → 축산·식품 마진 압박"
    lead_lag: "+1-2분기"
  - sector: 수소/에너지
    direction: 수혜(에탄올)
    tickers_us: [ADM, GPRE]
    mechanism: "미국 에탄올의 40% 옥수수 사용"
    lead_lag: "+1분기"
historical_validation: "2022.05 우크라전 → 옥수수 $8 (사상최고) → CJ제일제당 사료 마진 -10%pt"
noise_check: "WASDE 발표·기상 예보 단기 충격. 월평균 사용"
```

#### G.2 대두

```yaml
id: soybean
name: Soybean
unit: USD/bushel
primary_source:
  type: yfinance
  ticker: ZS=F
  free: true
fallback_source:
  name: USDA WASDE
  url: https://www.usda.gov/oce/commodity/wasde
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 생명공학
    direction: 부담(식품·사료)
    tickers_kr: ["CJ제일제당(097950)", "삼양사(145990)", "사조산업(007160)"]
    tickers_us: [ADM, BG, TSN]
    mechanism: "식용유·사료 1차 원료. 한국은 거의 100% 수입 의존"
    lead_lag: "+1-2분기"
historical_validation: "2022.06 대두 $17 (사상최고) → CJ제일제당 식용유 마진 -8%pt"
noise_check: "중국·브라질 무역 정책·기상 충격. 월평균 사용"
```

#### G.3 밀

```yaml
id: wheat
name: Wheat
unit: USD/bushel
primary_source:
  type: yfinance
  ticker: ZW=F
  free: true
fallback_source:
  name: USDA WASDE
  url: https://www.usda.gov/oce/commodity/wasde
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 생명공학
    direction: 부담(식품)
    tickers_kr: ["CJ제일제당(097950)", "대한제분(001130)", "삼양사(145990)", "농심(004370)"]
    tickers_us: [ADM, GIS, K]
    mechanism: "제분·라면·빵 1차 원료. 한국 99% 수입"
    lead_lag: "+1-2분기"
historical_validation: "2022.03 우크라전 → 밀 $13 (사상최고) → 농심·오뚜기 라면 가격 인상"
noise_check: "흑해 곡물협정·러우 정세 직접 충격. 월평균 사용"
```

#### G.4 커피

```yaml
id: coffee
name: Coffee Arabica
unit: USD/lb
primary_source:
  type: yfinance
  ticker: KC=F
  free: true
fallback_source:
  name: ICO Coffee Statistics
  url: https://www.ico.org/prices/po-production.pdf
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 생명공학
    direction: 부담(F&B)
    tickers_kr: ["스타벅스코리아(비상장·SCK)", "동서식품(비상장)"]
    tickers_us: [SBUX, KDP]
    mechanism: "원두 가격 = F&B 매출원가. 한국 시장은 SCK·동서식품 영향"
    lead_lag: "+1-2분기"
historical_validation: "2024.04 브라질 가뭄 → Arabica $4 (사상최고) → SBUX 가이던스 하향"
noise_check: "브라질·베트남 기상 충격 빈번. 분기평균 사용"
```

#### G.5 설탕

```yaml
id: sugar
name: Sugar No.11
unit: USD/lb
primary_source:
  type: yfinance
  ticker: SB=F
  free: true
fallback_source:
  name: ISO Sugar Statistics
  url: https://www.isosugar.org/
volatility_baseline: "60일 ~3-5%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 생명공학
    direction: 부담(F&B)
    tickers_kr: ["삼양사(145990)", "대한제당(001790)", "CJ제일제당(097950)"]
    tickers_us: [KO, PEP, MDLZ]
    mechanism: "음료·과자 1차 원료. 브라질 50%+ 점유"
    lead_lag: "+1-2분기"
historical_validation: "2023.11 인도 수출제한·브라질 기상 → 설탕 $0.28 (12년 최고) → 코카콜라 가격 인상"
noise_check: "에탄올 가격과 동행. 브라질이 사탕수수→에탄올로 돌리면 설탕 부족"
```

#### G.6 면화

```yaml
id: cotton
name: Cotton
unit: USD/lb
primary_source:
  type: yfinance
  ticker: CT=F
  free: true
fallback_source:
  name: USDA Cotton Outlook
  url: https://www.ers.usda.gov/topics/crops/cotton-and-wool/
volatility_baseline: "60일 ~2-3%"
anomaly_threshold:
  zscore_60d: 2.0
primary_effects:
  - sector: 생명공학
    direction: 간접(의료용 면)
    tickers_kr: ["효성티앤씨(298020)", "한세실업(105630)"]
    tickers_us: [HBI, RL, NKE]
    mechanism: "의류·의료용 면. 비교적 신호력 약함"
    lead_lag: "+2-3분기"
historical_validation: "2022.05 면화 $1.5 (10년 최고) → 한세실업 마진 -5%pt"
noise_check: "신호력 약함. 우선순위 낮음"
```

### 4.5 카테고리 H: 화학원료 (5)

#### H.1 황산

```yaml
id: sulfuric_acid
name: Sulfuric Acid
unit: USD/ton
primary_source:
  type: World Bank Pink Sheet (간접 — 황 가격)
  url: https://www.worldbank.org/en/research/commodity-markets
fallback_source:
  name: ICIS Chemical (월별 무료 요약)
  url: https://www.icis.com/explore/commodities/chemicals/sulphuric-acid/
volatility_baseline: "월간 ~10-20%"
anomaly_threshold:
  monthly_pct: 25.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(반도체 세정)
    tickers_kr: ["이엔에프테크놀로지(102710)", "동진쎄미켐(005290)", "솔브레인(357780)"]
    tickers_us: [TSM, INTC, MU]
    mechanism: "반도체 웨이퍼 세정 핵심. 초고순도 황산 한국 일부 국산화"
    lead_lag: "+1-2분기"
  - sector: 수소/에너지
    direction: 부담(배터리·비료)
    tickers_kr: ["LG화학(051910)", "에코프로비엠(247540)"]
    mechanism: "리튬 추출·니켈 정련 황산 다량 사용"
    lead_lag: "+1-2분기"
historical_validation: "2022.03 비료 가격 폭등 → 황산 +60% → 반도체 케미칼 마진 압박"
noise_check: "비료·구리 제련 부산물 동시 변동. 월평균 사용"
```

#### H.2 인산

```yaml
id: phosphoric_acid
name: Phosphoric Acid (P2O5)
unit: USD/ton
primary_source:
  type: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
fallback_source:
  name: USGS Phosphate Rock
  url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-phosphate.pdf
volatility_baseline: "월간 ~10-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(LFP 배터리·반도체 식각)
    tickers_kr: ["LG에너지솔루션(373220)", "에코프로비엠(247540)", "포스코퓨처엠(003670)"]
    tickers_us: [TSLA, ALB]
    mechanism: "LFP 양극재(LiFePO4) 인산 핵심. ESS·저가 EV 표준화로 수요↑"
    lead_lag: "+1-2분기"
historical_validation: "2022.03 모로코 OCP 인산 +70% → LFP 배터리 BOM 영향"
noise_check: "비료·식품 산업과 혼재. 분기평균 사용"
```

#### H.3 가성소다 (NaOH)

```yaml
id: caustic_soda
name: Caustic Soda
unit: USD/ton
primary_source:
  type: ICIS / S&P Platts (월별 무료)
  url: https://www.icis.com/explore/commodities/chemicals/caustic-soda/
fallback_source:
  name: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
volatility_baseline: "월간 ~10-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: AI/반도체
    direction: 부담(반도체·디스플레이)
    tickers_kr: ["LG화학(051910)", "한화솔루션(009830)", "OCI홀딩스(010060)"]
    tickers_us: [DOW, OLN]
    mechanism: "반도체·디스플레이 에칭, 알루미나 정련. NaOH↑ → 케미칼 매출↑(생산자 수혜)"
    lead_lag: "+1분기"
historical_validation: "2022.04 EU 가스대란으로 NaOH +80% → 한화솔루션 케미칼 부문 +30%"
noise_check: "PVC 부산물(염소) 가격과 함께 봐야 정확"
```

#### H.4 메탄올

```yaml
id: methanol
name: Methanol
unit: USD/ton
primary_source:
  type: Methanex Posted Price (월별 무료)
  url: https://www.methanex.com/our-business/pricing/
fallback_source:
  name: ICIS Methanol
  url: https://www.icis.com/explore/commodities/chemicals/methanol/
volatility_baseline: "월간 ~5-15%"
anomaly_threshold:
  monthly_pct: 20.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜(녹색메탄올 선박연료)
    tickers_kr: ["삼성중공업(010140)", "현대미포조선(010620)", "한국조선해양(009540)", "롯데케미칼(011170)"]
    tickers_us: [MEOH]
    mechanism: "IMO 2050 탈탄소 → 녹색메탄올 선박연료. 한국 조선 메탄올 추진선 수주↑"
    lead_lag: "+2-4분기"
historical_validation: "2023.09 Maersk 첫 메탄올 컨테이너선 인도(현대미포) → 메탄올 선박 발주 글로벌 확산"
noise_check: "천연가스(원료)와 강한 동행. 가스 별도로 봐야 메탄올 마진 추정"
```

#### H.5 암모니아·우레아

```yaml
id: ammonia_urea
name: Ammonia & Urea
unit: USD/ton
primary_source:
  type: World Bank Pink Sheet
  url: https://www.worldbank.org/en/research/commodity-markets
fallback_source:
  name: ICIS Fertilizer
  url: https://www.icis.com/explore/commodities/chemicals/ammonia/
volatility_baseline: "월간 ~10-20%"
anomaly_threshold:
  monthly_pct: 25.0
primary_effects:
  - sector: 수소/에너지
    direction: 수혜(블루/그린 암모니아 운반체)
    tickers_kr: ["롯데케미칼(011170)", "한화솔루션(009830)", "포스코홀딩스(005490)", "한국조선해양(009540)"]
    tickers_us: [CF, NTR, MOS]
    mechanism: "암모니아 = 수소 운반체. 그린암모니아 → 그린수소 핵심 매개. 우레아는 디젤 SCR(요소수)"
    lead_lag: "+2-4분기"
  - sector: 생명공학
    direction: 부담(비료→식품)
    tickers_kr: ["하림(136480)"]
    tickers_us: [ADM, BG]
    mechanism: "비료 핵심. 농업 비용↑ → 식품 가격↑"
    lead_lag: "+2-3분기"
historical_validation: "2021.10 중국 우레아 수출제한 → 한국 요소수 대란 → 암모니아 +200%"
noise_check: "천연가스 원료(메탄→암모니아)와 강한 동행. 가스 별도 모니터링"
```

### 4.6 카테고리 I: 바이오 원료 (3)

#### I.1 GLP-1 펩타이드 원료 (CDMO 캐파)

```yaml
id: glp1_peptide
name: GLP-1 Peptide API & CDMO Capacity
unit: USD/g (semaglutide API), CDMO booking lead time (months)
primary_source:
  type: Pharma Industry Reports (Bachem·PolyPeptide 분기실적)
  url: https://www.bachem.com/investors/financial-reports/
fallback_source:
  name: Evaluate Pharma·IQVIA (요약 무료)
  url: https://www.iqvia.com/insights
volatility_baseline: "분기 변동 ~5-15%"
anomaly_threshold:
  cdmo_lead_time_months: 18.0
primary_effects:
  - sector: 생명공학
    direction: 수혜(병목 보유자)
    tickers_kr: ["펩트론(217340)", "셀트리온(068270)", "삼성바이오로직스(207940)"]
    tickers_us: [LLY, NVO]
    mechanism: "GLP-1 진짜 병목은 LLY/NVO가 아닌 펩타이드 CDMO. 펩트론은 약효 지속형 GLP-1 IP 보유. Bachem(BCHM.SW)·PolyPeptide(PPL.SW)도 핵심 CDMO"
    lead_lag: "CDMO 캐파 발표 → 주가 +0~3개월"
historical_validation: "2023.10 Wegovy/Ozempic 공급부족 → Bachem +120%, PolyPeptide +80%, 펩트론 +400% (12개월)"
noise_check: "LLY/NVO 임상 결과 발표가 더 큰 단기 노이즈. CDMO 캐파 가이던스 분기 발표가 진짜 시그널"
```

#### I.2 항생제 API

```yaml
id: antibiotic_api
name: Antibiotic Active Pharmaceutical Ingredients
unit: USD/kg
primary_source:
  type: IQVIA / WHO Essential Medicines List
  url: https://www.iqvia.com/insights
fallback_source:
  name: PharmaCompass (월별 가격 일부 무료)
  url: https://www.pharmacompass.com/
volatility_baseline: "분기 ~10-20%"
anomaly_threshold:
  quarterly_pct: 25.0
primary_effects:
  - sector: 생명공학
    direction: 부담→수혜(KR/US 대체공급)
    tickers_kr: ["종근당(185750)", "한미약품(128940)", "유한양행(000100)", "대웅제약(069620)"]
    tickers_us: [PFE, MRK, ABBV]
    mechanism: "API 80%+ 중국·인도. 공급망 안보 강화로 KR/US 대체 모멘텀"
    lead_lag: "+2-4분기"
historical_validation: "2020.03 코로나 초기 인도 락다운 → API 부족 → 종근당·유한양행 단기 +30%"
noise_check: "중국·인도 환경규제 단기 충격. 분기평균 사용"
```

#### I.3 바이알 글래스 (Type I Borosilicate)

```yaml
id: vial_glass
name: Type I Borosilicate Glass Vials
unit: USD/vial, 캐파 부킹 lead time
primary_source:
  type: Schott / Corning / SGD 분기실적
  url: https://www.schott.com/en-gb/news-and-media/media-relations/financial-reports
fallback_source:
  name: BioPharma International
volatility_baseline: "분기 캐파 lead time ~6-18개월"
anomaly_threshold:
  lead_time_months: 12.0
primary_effects:
  - sector: 생명공학
    direction: 수혜(병목 보유자)
    tickers_kr: ["삼성바이오로직스(207940)", "셀트리온(068270)"]
    tickers_us: [GLW, WST, BAX]
    mechanism: "GLP-1 주사제·백신 충전 핵심. Type I 보로실리케이트 캐파 매우 제한. Corning Valor가 핵심"
    lead_lag: "캐파 부킹 → 매출 +6-12개월"
historical_validation: "2021.01 코로나 백신 → 바이알 부족 → Corning Valor 캐파 풀가동, WST +60%"
noise_check: "GLP-1 + 차세대 항체약 동시 수요 폭증. 신호력 매우 강함"
```

## 5. 종합 인사이트

### 5.1 한국 투자자에 신호력 높은 TOP 3

1. **JKM 천연가스** — 한국가스공사(036460)·한국전력(015760) 분기실적에 1-2분기 후행 직결. 정책 리스크(요금 인상 지연)와 동반되어 lead 신호로 작용
2. **우라늄 U3O8** — 두산에너빌리티(034020)·한전기술(052690) SMR 테마 1차 sentiment lead. U3O8 + SPUT 매집을 함께 보면 정확도↑
3. **구리** — LS ELECTRIC(010120)·대한전선(001440) AI 데이터센터 인프라 6-12개월 선행. 2024년 LS ELECTRIC +120% 랠리의 lead 시그널이었음

### 5.2 시장 저평가 — 숨은 보틀넥

1. **헬륨-3** — 양자컴퓨팅 최대 단일 병목. 민간시장 전무, DOE 배급제. IONQ/IBM/RGTI/QBTS 캐파가 He-3 재생회로 기술에 종속 → 양자 hidden moat. 시장이 백금족·희토류만 보고 있음
2. **이리듐** — 그린수소 진짜 병목. 연 7-8톤 채굴 vs 1GW PEM ~1톤 필요. 백금/팔라듐보다 훨씬 희소. PLUG/BLDP/두산퓨얼셀 CAPEX의 진짜 제약
3. **GLP-1 펩타이드 CDMO** — 진짜 병목은 LLY/NVO가 아닌 Bachem·PolyPeptide·**펩트론(217340)**. 펩트론은 약효 지속형 GLP-1 IP 보유로 CDMO+IP 동시 강점
4. **갈륨/게르마늄 중국 통제(2023.7)** — RFHIC(218410)·대한광통신(010170) 공급망 안보 직접 수혜. 갈륨은 GaN 5G/AI 가속기, 게르마늄은 광통신·열영상에 필수
5. **바이알 글래스(Type I)** — Corning Valor·West Pharma의 hidden moat. GLP-1 주사제 폭증으로 캐파 lead time 12-18개월

### 5.3 신호력 약화 — 우선순위 하향

- **로듐** — 시장이 매우 얕음(연 30톤). 단일 거래로 가격 ±10%, false signal 비율 높음
- **코발트** — LFP 전환으로 NCM 수요 구조적 약화. 신호 의미 점진 감소
- **팔라듐** — 내연차 촉매 80% 비중, EV 전환으로 구조적 수요 감소
- **면화** — 신호력 약함. 의류 매크로와 혼재
- **백금(촉매용)** — 디젤차 촉매 수요 감소, 수소 수요로 대체 중이지만 PEM은 이리듐이 진짜 병목

## 6. 운영 규칙

- **v1 잠금** (2026-04-25): 52개 원자재 최종 확정. 변경 금지, 추가만 허용
- **Phase 2 확장**: 섹터를 9~27개로 확장할 때 본 매트릭스에 매핑만 보강
- **사후 백테스트**: 분기별 `Output/commodity-backtest-YYYY-Q.md`에 누적
- **데이터 검증**: 월 1회 1차 소스 URL 정상 응답 확인
- **임계 발생시**: Z-score>2 또는 임계 percent 돌파시 `Output/commodity-alert-YYYY-MM-DD.md` 생성
- **관련 문서**: [[02-indicators]], [[03-outlook]], [[index]]
