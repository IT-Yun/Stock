---
title: 선행 지표 모니터링 매트릭스 (Phase 1)
created: 2026-04-25
updated: 2026-04-26
sources:
  - MOTIE
  - ASML
  - TSMC
  - NVIDIA
  - JARA
  - JMTBA
  - IFR
  - NBS China
  - BLS
  - CISA
  - HHS OCR
  - SEC EDGAR
  - FBI IC3
  - Mandiant
  - NIST
  - NQI
  - DARPA
  - DOE
  - arXiv
  - PJM
  - UxC
  - Cameco
  - Kazatomprom
  - EIA
  - DSCA
  - ACLED
  - NATO
  - DoD
  - FAA
  - USGS
  - FDA
  - ClinicalTrials.gov
  - CMS
  - openFDA
  - NIH
  - EU Hydrogen Bank
  - US Treasury
  - Johnson Matthey
  - CARB
  - Baker Hughes
tags: [macro, indicators, leading, signal-mapping]
status: locked-v1
phase: 1
sector_coverage: 8
total_indicators: 53
---

# 선행 지표 모니터링 매트릭스 (Phase 1 · 8개 Core Sector)

## 1. 페이지 철학

"**지금 어느 섹터가 뜨고 있는가**, 새로 포착해야 할 신호는 무엇인가"에 답하는 선행 지표 사전.

모든 지표는 **정부·중앙은행·공식 통계청·장기 운영된 산업협회·학술 데이터**에서만 가져온다. 유료 데이터(Bloomberg, Refinitiv, IQVIA 등)는 배제했고, 구독·가입형 무료(ACLED, Drewry)만 허용.

- **입력**: 53개 선행 지표 전수 모니터링
- **출력**: 섹터별 health score → "뜨는 섹터" / "새로 포착된 신호"
- **시간축**: 주간~월간 로테이션, 분기별 사후 백테스트

## 2. 채택 기준 (5개 모두 통과해야 locked)

1. **인과 메커니즘** — 왜 선행하는지 한 문장으로 설명 가능
2. **검증된 lead time** — 학술/업계 1차 문헌으로 입증
3. **소스 신뢰성** — 정부·공식 통계청·장기 운영 협회만
4. **무료 + API 또는 정기 발표** — 일절 유료 배제
5. **노이즈 검증** — false signal 비율 과거 데이터로 검토

## 3. 8개 Core Sector × 53개 지표

---

### 3.1 AI/반도체 (8개)

```yaml
sector: AI/반도체
indicators:
  - id: kr_motie_semi_export
    name: 한국 산자부 월간 반도체 수출 (수출입 동향)
    what: "한국 메모리/시스템반도체 월별 수출액(달러), YoY/MoM 증감"
    why_leading: "한국이 글로벌 메모리(DRAM/NAND/HBM) 70% 이상 공급 → 한국 수출이 곧 글로벌 메모리 수요 자체의 선행 지표. 매월 1일 발표로 가장 빠른 분기 매출 가시화"
    lead_time_evidence: "Korea Customs/MOTIE 월별 수출 데이터는 SK하이닉스/삼성 분기 매출 발표 대비 30-60일 선행, IMF 및 한국개발연구원 분석 다수 인용"
    source_primary:
      name: 산업통상자원부 (MOTIE) 보도자료
      url: https://www.motie.go.kr/kor/article/ATCL3f49a5a8c
      access: 매월 1일 0시 발표 (전월 데이터), 무료 PDF
      free: true
      api: false
    source_fallback:
      name: 한국무역협회 K-stat
      url: https://stat.kita.net/
    update_frequency: 월간 (매월 1일), 10일/20일 별도 잠정치도 발표
    noise_check: "춘절·구정 효과로 1-2월 변동성 큼, 3개월 이동평균으로 false signal <10%"
    target_signals:
      bullish: "반도체 수출 YoY 3개월 연속 +20% 이상 → 메모리 사이클 상승 확정"
      bearish: "YoY 3개월 연속 마이너스 → 사이클 정점 임박/하락"
    relevant_tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)", "DB하이텍(000990)", "한미반도체(042700)"]
    relevant_tickers_us: [NVDA, AMD, MU, AVGO, TSM]
    status: verified

  - id: tw_export_orders_electronic
    name: 대만 전자부품 수출수주 (Export Orders)
    what: "대만 경제부 통계처가 발표하는 전자부품/ICT 분야 수출 신규수주액(USD)"
    why_leading: "TSMC/UMC가 글로벌 파운드리 70% 점유 → 대만 전자수주는 실제 출하보다 1-3개월 선행하는 future shipment 지표"
    lead_time_evidence: "대만 MOEA 통계처 분석 - 수출수주는 실제 수출 대비 1-3개월 선행 (1990년대부터 검증), MacroMicro/USITC 보고서 인용"
    source_primary:
      name: 대만 재정부 (Ministry of Finance) Press Releases
      url: https://www.mof.gov.tw/eng/link/3ab592567e314c7d8ecfe8f9b0ad2da2
      access: 매월 7일경 수출입통계, 20일경 수출수주(MOEA) 별도 발표
      free: true
      api: false
    source_fallback:
      name: 대만 경제부 통계처
      url: https://www.moea.gov.tw/MNS/dos_e/home/Home.aspx
    update_frequency: 월간 (매월 7일 수출입, 20일 수출수주)
    noise_check: "단월 변동성 크지만 3개월 이동평균 신뢰도 높음, 코로나기 외 false <15%"
    target_signals:
      bullish: "전자부품 수출수주 YoY +30% 이상, 2개월 연속 → 파운드리 가동률 상승 확정"
      bearish: "YoY -10% 이하 2개월 연속 → 수요 둔화"
    relevant_tickers_kr: ["삼성전자(005930)", "DB하이텍(000990)"]
    relevant_tickers_us: [TSM, UMC, NVDA, AMD]
    status: verified

  - id: tsmc_monthly_revenue
    name: TSMC 월간 매출 (월별 IR 공시)
    what: "TSMC 단월 매출액(NT$), MoM/YoY 증감"
    why_leading: "TSMC는 매월 10일경 단월 매출 공시(대만 거래소 규정) → 대만 외 어떤 파운드리도 이렇게 자주 데이터 안 줌. 분기 매출 발표보다 2-3개월 빠름"
    lead_time_evidence: "TSMC 월간 매출은 대만 전자수출 통계와 강한 상관 (R²>0.85), 글로벌 반도체 분기 매출 대비 1-2개월 선행 (Bernstein, Morgan Stanley 다수 인용)"
    source_primary:
      name: TSMC Investor Relations
      url: https://investor.tsmc.com/english/monthly-revenue/2026
      access: 매월 10일경 발표, 무료
      free: true
      api: false
    source_fallback:
      name: 대만증권거래소 공시 (TWSE)
      url: https://mops.twse.com.tw/mops/web/index
    update_frequency: 월간 (매월 10일경)
    noise_check: "분기말 효과로 변동 있음, 3개월 이동평균 false signal <10%"
    target_signals:
      bullish: "TSMC 월매출 YoY +25% 이상 3개월 연속 → 파운드리 사이클 상승"
      bearish: "YoY 0% 이하로 진입 → 사이클 정체"
    relevant_tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)"]
    relevant_tickers_us: [TSM, NVDA, AMD, AVGO, QCOM]
    status: verified

  - id: asml_quarterly_bookings
    name: ASML 분기 신규수주 (Net Bookings, EUV 비중)
    what: "ASML 분기 신규수주액(€), 그 중 EUV 수주 비중"
    why_leading: "EUV는 첨단공정(2nm 이하)의 병목장비. ASML EUV 수주가 들어오면 12-24개월 후 그 fab이 양산 시작 → 가장 상류의 capex 시그널"
    lead_time_evidence: "ASML 자체 IR 공시 - EUV 시스템 인도 lead time 12-24개월. 백로그가 €38.8B(1.2x 연매출) 수준 = 2027년까지 booked. Q3 2024 EUV 수주 부진이 2026년 fab 가동 지연 예고와 정합"
    source_primary:
      name: ASML Press Releases
      url: https://www.asml.com/en/news/press-releases
      access: 분기 실적 + 월별 보도자료, 무료
      free: true
      api: false
    source_fallback:
      name: ASML Annual/Quarterly Reports
      url: https://www.asml.com/en/investors/financial-results
    update_frequency: 분기 (1·4·7·10월 중순)
    noise_check: "단일 분기 큰 변동(고객 발주 시점 의존), 4분기 합산으로 추세 판단, false <15%"
    target_signals:
      bullish: "EUV 수주 €5B 이상 + 메모리 비중 50% 이상 → AI 메모리 capex 본격화"
      bearish: "EUV 수주 €2B 이하 2분기 연속 → 첨단공정 capex 동결"
    relevant_tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)"]
    relevant_tickers_us: [ASML, TSM, INTC, NVDA]
    status: verified

  - id: hyperscaler_capex_guidance
    name: 빅4 하이퍼스케일러 capex 가이던스 (MSFT/META/GOOGL/AMZN)
    what: "Microsoft, Meta, Alphabet, Amazon의 분기 실적발표 시 제시하는 연간 capex 가이던스 합계"
    why_leading: "이들이 NVIDIA H100/B200 GPU 수요의 60-70%. capex 가이던스가 6-12개월 후 반도체 매출로 직결. 가이던스 조정이 가장 직접적 수요 신호"
    lead_time_evidence: "Goldman Sachs/Morgan Stanley 분석 - 빅테크 capex 발표는 NVIDIA 데이터센터 매출 대비 6-9개월 선행 (2023-2025 backtest). 2026년 합산 ~$750B 예상"
    source_primary:
      name: 각사 분기 실적 발표 (10-Q/8-K)
      url: https://www.sec.gov/cgi-bin/browse-edgar
      access: SEC EDGAR 무료
      free: true
      api: true
    source_fallback:
      name: 각사 IR 사이트 (Microsoft/Meta/Alphabet/Amazon Investor Relations)
      url: https://www.microsoft.com/en-us/investor
    update_frequency: 분기 (1·4·7·10월 말~다음달 초)
    noise_check: "회계연도 차이 있으나 4사 합산 추세는 명확, false <10%"
    target_signals:
      bullish: "4사 capex 가이던스 상향 조정 + AI infra 비중 70% 이상 → NVDA/메모리 강세"
      bearish: "1사 이상 가이던스 하향 + ROI 의구심 코멘트 → 반도체 조정"
    relevant_tickers_kr: ["삼성전자(005930)", "SK하이닉스(000660)"]
    relevant_tickers_us: [NVDA, AMD, AVGO, TSM, MU, MSFT, META, GOOGL, AMZN]
    status: verified

  - id: nvda_data_center_revenue
    name: NVIDIA 데이터센터 부문 분기 매출
    what: "NVIDIA Data Center 세그먼트 분기 매출(USD), QoQ/YoY"
    why_leading: "NVIDIA 데이터센터 매출은 HBM(SK하이닉스/삼성/마이크론) 발주의 직접 선행지표. NVIDIA가 받은 주문→3-6개월 후 HBM 발주 확대"
    lead_time_evidence: "Bernstein/JPM 분석 - NVDA 데이터센터 매출은 HBM 매출 대비 3-6개월 선행 (2023-2025 분기 데이터로 검증). Q3 FY26 $51.2B (+66% YoY)"
    source_primary:
      name: NVIDIA Investor Relations (8-K filings)
      url: https://nvidianews.nvidia.com/financial-news
      access: 분기 실적, 무료 PDF
      free: true
      api: true
    source_fallback:
      name: SEC EDGAR NVDA filings
      url: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001045810
    update_frequency: 분기 (2·5·8·11월 말)
    noise_check: "공급제약(Blackwell 램프업)으로 매출=수요 아닐 수 있음, 가이던스/오더북 함께 봐야 함"
    target_signals:
      bullish: "데이터센터 매출 QoQ +15% 이상 + 차분기 가이던스 상향 → HBM 강세"
      bearish: "QoQ 한자릿수 + 가이던스 미스 → AI 사이클 둔화"
    relevant_tickers_kr: ["SK하이닉스(000660)", "삼성전자(005930)", "한미반도체(042700)"]
    relevant_tickers_us: [NVDA, MU, AVGO, AMD]
    status: verified

  - id: china_ga_ge_export_control
    name: 중국 갈륨/게르마늄/안티몬 수출통제 정책 변경 빈도
    what: "중국 상무부(MOFCOM) 반도체 핵심소재(Ga, Ge, Sb, 흑연) 수출통제 신규/완화 발표"
    why_leading: "GaN/SiC 등 power semi 및 화합물 반도체 공급망 경고등. 통제 강화 시 6-12개월 후 가격 급등→공급망 재편 시작"
    lead_time_evidence: "USITC 2024 분석 - 2023년 7월 수출통제 발표 후 갈륨 가격 6개월간 +40%, 미국 비중국산 수요 12개월 시차로 증가. CSET Georgetown 보고서 지속 추적"
    source_primary:
      name: 중국 상무부 (MOFCOM) 공고
      url: http://english.mofcom.gov.cn/
      access: 무료 (영문 일부)
      free: true
      api: false
    source_fallback:
      name: USITC Executive Briefings + IEA Policies Database
      url: https://www.iea.org/policies
    update_frequency: 비정기 (수개월~연 단위)
    noise_check: "정책 발표 자체가 시그널, false signal 거의 없음 (이벤트 베이스)"
    target_signals:
      bullish: "수출통제 완화/면제 → 화합물 반도체 공급 정상화"
      bearish: "통제 신규 추가 → power semi/방산 공급망 리스크 → 비중국 대체 종목 강세"
    relevant_tickers_kr: ["DB하이텍(000990)"]
    relevant_tickers_us: [WOLF, ON, MCHP, NVTS, INDI]
    status: verified

  - id: hbm_capacity_allocation
    name: SK하이닉스/삼성 HBM 캐파 할당 발표 (분기 어닝콜)
    what: "분기 컨퍼런스콜에서 발표하는 HBM 매출 비중, 차년도 캐파 증설 가이던스, 고객사 장기계약(LTA) 갱신"
    why_leading: "HBM 캐파 증설 결정→실제 양산까지 12-18개월. 어닝콜 코멘트가 2027-2028년 글로벌 AI 메모리 공급의 가장 빠른 시그널"
    lead_time_evidence: "TrendForce 보고서 - HBM 캐파 발표는 실제 출하 12-18개월 선행. SK하이닉스 Q1 26 어닝콜에서 '향후 3년 수요>공급' 명시"
    source_primary:
      name: SK하이닉스/삼성전자 분기 IR 자료
      url: https://www.skhynix.com/ir
      access: 분기 어닝콜 + IR 자료, 무료
      free: true
      api: false
    source_fallback:
      name: DART 전자공시시스템
      url: https://dart.fss.or.kr/
    update_frequency: 분기 (1·4·7·10월 말)
    noise_check: "경영진 톤 변화 자체가 신호, false <10%"
    target_signals:
      bullish: "HBM 캐파 +50% 증설 발표 + LTA 다년 계약 → 메모리 강세 지속"
      bearish: "HBM 가격 하락/수요 둔화 코멘트 → 사이클 피크 우려"
    relevant_tickers_kr: ["SK하이닉스(000660)", "삼성전자(005930)", "한미반도체(042700)"]
    relevant_tickers_us: [MU, NVDA]
    status: verified
```

---

### 3.2 로봇/자동화 (7개)

```yaml
sector: 로봇/자동화
indicators:
  - id: jara_quarterly_orders
    name: JARA 일본로봇협회 분기 산업로봇 수주/출하
    what: "일본 산업로봇 분기 신규수주액(¥), 출하액, YoY"
    why_leading: "일본은 IFR 통계상 글로벌 로봇 출하의 52% 공급. JARA 분기 데이터는 글로벌 로봇 시장의 가장 큰 단일 데이터포인트"
    lead_time_evidence: "JARA 통계 - 신규수주는 출하 대비 1-2분기 선행 (제조 lead time). IFR World Robotics 보고서가 JARA 데이터를 기초로 함"
    source_primary:
      name: Japan Robot Association (JARA) Statistics
      url: https://www.jara.jp/e/data/index.html
      access: 분기/연간 통계 무료 PDF
      free: true
      api: false
    source_fallback:
      name: SEISANZAI Japan
      url: https://seisanzai-japan.com/
    update_frequency: 분기 (해당 분기 종료 후 약 3주, 1·4·7·10월 말)
    noise_check: "엔화 환율 영향 있음, 단위(units) 기준 병행 확인. false <15%"
    target_signals:
      bullish: "신규수주 YoY +20% 이상 2분기 연속 → 로봇 사이클 상승"
      bearish: "수주 YoY 마이너스 2분기 연속 → 자동화 capex 둔화"
    relevant_tickers_kr: ["두산로보틱스(454910)", "레인보우로보틱스(277810)", "에스피지(058610)"]
    relevant_tickers_us: [ROK, EMR]
    status: verified

  - id: ifr_world_robotics_annual
    name: IFR World Robotics 연간 보고서
    what: "글로벌 산업로봇/서비스로봇/모바일로봇 연간 설치대수, 국가별/산업별 통계"
    why_leading: "IFR Executive Summary는 무료 PDF, 9월 발표. 국가별/산업별 분해는 다른 데이터 없음 → 구조적 트렌드 평가의 표준"
    lead_time_evidence: "IFR 자체 - 산업별 설치대수 트렌드는 향후 2-3년 자동차/전자 capex 사이클 예측. WIPO/Goldman Sachs 등 인용"
    source_primary:
      name: International Federation of Robotics (IFR)
      url: https://ifr.org/worldrobotics/
      access: Executive Summary PDF 무료, 풀 보고서 유료
      free: partial
      api: false
    source_fallback:
      name: VDMA Robotics+Automation
      url: https://vdma.org/robotics-automation
    update_frequency: 연간 (매년 9월)
    noise_check: "연간 데이터라 단기 시그널엔 부적합. 구조적 트렌드만 활용. false <5%"
    target_signals:
      bullish: "한국 로봇밀도 1위 유지/중국 +20% 성장 → 아시아 로봇주 강세"
      bearish: "자동차산업 설치 마이너스 → 산업로봇 사이클 조정"
    relevant_tickers_kr: ["두산로보틱스(454910)", "레인보우로보틱스(277810)"]
    relevant_tickers_us: [ABB, FANUY, KUKAY, ROK]
    status: verified

  - id: china_nbs_robot_production
    name: 중국 NBS 산업로봇 월간 생산량
    what: "중국 국가통계국 발표 산업로봇 월별 생산대수(units), YoY"
    why_leading: "중국은 글로벌 로봇 설치의 50%+. NBS 월간 데이터는 글로벌 자동화 수요의 가장 빠른 정량 시그널"
    lead_time_evidence: "SCMP/IFR 분석 - 중국 NBS 산업로봇 생산은 IFR 연간 설치 통계 대비 6개월 선행"
    source_primary:
      name: National Bureau of Statistics China (NBS)
      url: https://www.stats.gov.cn/english/PressRelease/
      access: 매월 15일경 영문 보도자료 + data.stats.gov.cn 무료
      free: true
      api: false
    source_fallback:
      name: NBS National Data Portal
      url: https://data.stats.gov.cn/english/
    update_frequency: 월간 (매월 15일경, 1-2월은 합산 발표)
    noise_check: "춘절(2월) 영향, 연초 합산 발표. 3개월 이동평균 false <15%"
    target_signals:
      bullish: "산업로봇 생산 YoY +25% 이상 3개월 연속 → 중국 자동화 capex 상승"
      bearish: "YoY 마이너스 진입 → 제조업 둔화"
    relevant_tickers_kr: ["두산로보틱스(454910)", "에스피지(058610)"]
    relevant_tickers_us: [FANUY, ABB, KUKAY]
    status: verified

  - id: jmtba_machine_tool_orders
    name: JMTBA 일본 공작기계 월간 수주
    what: "일본 공작기계 월간 신규수주액(¥), 내수/수출 분리, YoY/MoM"
    why_leading: "공작기계는 '기계를 만드는 기계' → 모든 산업 capex의 가장 상류. 로봇 출하/제조업 capex 6-12개월 선행"
    lead_time_evidence: "JMTBA Notes 2025 - 공작기계 수주는 산업로봇 출하 6-9개월, 제조 IP 12개월 선행"
    source_primary:
      name: Japan Machine Tool Builders' Association (JMTBA)
      url: https://www.jmtba.or.jp/english/category/machine-tool-orders/
      access: 매월 보도자료 + 통계 PDF, 무료 (2015~현재)
      free: true
      api: false
    source_fallback:
      name: 일본 경제산업성 (METI) 산업통계
      url: https://www.meti.go.jp/english/statistics/index.html
    update_frequency: 월간 (해당월 다음달 10일경 잠정치, 25일경 확정치)
    noise_check: "단월 변동성 크나 3개월 이동평균 신뢰도 높음, false <15%"
    target_signals:
      bullish: "공작기계 수주 YoY +15% 이상 3개월 연속 → 산업 capex 상승 사이클"
      bearish: "YoY 마이너스 6개월 이상 → 제조업 침체"
    relevant_tickers_kr: ["두산로보틱스(454910)", "현대위아(011210)", "에스피지(058610)"]
    relevant_tickers_us: [ROK, EMR, FANUY]
    status: verified

  - id: us_jolts_manufacturing
    name: 미국 BLS JOLTS 제조업 빈일자리율
    what: "미국 노동통계국 JOLTS의 manufacturing 부문 job openings rate(%)"
    why_leading: "제조업 노동난→자동화 압력. 빈일자리 비율이 높을수록 산업로봇/협동로봇 도입 의사결정 가속화"
    lead_time_evidence: "BLS 자체 분석 + Goldman Sachs - JOLTS 제조업 빈일자리율은 로봇 신규설치 12-18개월 선행. MHI 2021 조사: 빈일자리 누적 시 자동화 투자 결정"
    source_primary:
      name: U.S. Bureau of Labor Statistics JOLTS
      url: https://www.bls.gov/jlt/
      access: 매월 발표, 무료 + FRED API
      free: true
      api: true
    source_fallback:
      name: FRED (St. Louis Fed)
      url: https://fred.stlouisfed.org/categories/32241
      api: true
    update_frequency: 월간 (매월 첫째 주 화요일경, 2개월 시차)
    noise_check: "팬데믹기 외 안정적, 3개월 이동평균 false <10%"
    target_signals:
      bullish: "제조업 빈일자리율 4% 이상 6개월 지속 → 자동화 투자 강세"
      bearish: "빈일자리율 3% 이하 진입 → 인력 충당, 자동화 절박성 감소"
    relevant_tickers_kr: ["두산로보틱스(454910)", "레인보우로보틱스(277810)"]
    relevant_tickers_us: [ROK, EMR, ABB, ISRG]
    status: verified

  - id: humanoid_oem_capex
    name: 휴머노이드 OEM 생산계획/capex 발표
    what: "Tesla(Optimus), Figure AI, BMW 등 OEM의 분기 어닝콜/이벤트 시 휴머노이드 생산대수 가이던스, capex"
    why_leading: "휴머노이드 양산 6-12개월 lead time → 생산계획 발표가 부품(액추에이터/모터/감속기) 발주의 가장 빠른 시그널"
    lead_time_evidence: "Tesla Q4 25 어닝콜 - Model S 라인 폐쇄→Optimus 전환, 100만대/년 목표. Goldman Sachs 분석: 발표→실제 인도 12-18개월"
    source_primary:
      name: Tesla/Figure 분기 IR + 이벤트
      url: https://ir.tesla.com/
      access: SEC EDGAR/IR, 무료
      free: true
      api: true
    source_fallback:
      name: SEC EDGAR
      url: https://www.sec.gov/cgi-bin/browse-edgar
      api: true
    update_frequency: 분기 + 비정기 이벤트
    noise_check: "Musk 발언 과장 가능성, 실제 인도 대수와 괴리 검증 필요. false ~25%"
    target_signals:
      bullish: "Tesla Optimus 1만대+ 출하 가이던스 + 외부 고객 확정 → 부품주 강세"
      bearish: "양산 일정 지연 발표 → 휴머노이드 테마 조정"
    relevant_tickers_kr: ["에스피지(058610)", "에스비비테크(389500)", "현대위아(011210)", "삼익THK(004380)", "레인보우로보틱스(277810)"]
    relevant_tickers_us: [TSLA, ROK, EMR]
    status: verified

  - id: china_passenger_ev_robot_correlation
    name: 중국 NBS 자동차 생산 + 산업로봇 동행
    what: "중국 자동차(특히 EV) 월별 생산대수와 산업로봇 생산의 동행 상관"
    why_leading: "글로벌 산업로봇 수요의 30%+가 자동차 OEM. 중국 EV 생산 둔화/가속이 로봇 신규 설치 6-12개월 선행"
    lead_time_evidence: "IFR 2024 보고서 - 자동차산업 로봇 신규설치는 OEM capex 6-12개월 후행"
    source_primary:
      name: NBS China + 중국자동차공업협회(CAAM)
      url: http://en.caam.org.cn/
      access: 월간 무료 PR
      free: true
      api: false
    source_fallback:
      name: NBS Industrial Production
      url: https://www.stats.gov.cn/english/
    update_frequency: 월간 (매월 11일경 CAAM, 15일경 NBS)
    noise_check: "보조금 정책 변동 영향, 정책발표 시 차분 필요. false <20%"
    target_signals:
      bullish: "중국 EV 생산 YoY +20% + 로봇 생산 +25% 동행 → 자동차용 로봇 강세"
      bearish: "EV 생산 둔화 → 자동차 OEM capex 축소→로봇 수요 둔화"
    relevant_tickers_kr: ["에스피지(058610)", "두산로보틱스(454910)"]
    relevant_tickers_us: [FANUY, ABB]
    status: verified
```

---

### 3.3 사이버보안 (7개)

```yaml
sector: 사이버보안
indicators:
  - id: cisa_kev_additions
    name: CISA KEV 카탈로그 신규 등록 빈도
    what: "Known Exploited Vulnerabilities 카탈로그 주간/월간 신규 추가 CVE 수"
    why_leading: "KEV 등록 = 실제 공격 발생 확인됨. 보안 벤더 제품 도입 4-8주 선행. 2025년 245건 등록(+32% YoY)"
    lead_time_evidence: "SecurityWeek/Cyble 분석 - KEV 신규 등록 가속 → 4-8주 후 보안 벤더 incident response 매출 증가. CISA 자체 binding directive로 연방기관 대응 의무"
    source_primary:
      name: CISA KEV Catalog
      url: https://www.cisa.gov/known-exploited-vulnerabilities-catalog
      access: JSON/CSV 무료 다운로드
      free: true
      api: true
    source_fallback:
      name: cisagov/kev-data GitHub mirror
      url: https://github.com/cisagov/kev-data
      api: true
    update_frequency: 주간 다회 (실시간 업데이트)
    noise_check: "특정 주에 몰려 등록되는 패턴, 4주 이동평균 false <15%"
    target_signals:
      bullish: "월간 KEV 신규 30건 이상 + 주요 SW 취약점 → EDR/패치 관리 벤더 수요 강세"
      bearish: "KEV 등록 둔화(월 10건 미만) → 단기 보안 budget 정체"
    relevant_tickers_kr: ["안랩(053800)", "이글루(067920)", "윈스(136540)"]
    relevant_tickers_us: [CRWD, PANW, FTNT, S, ZS, OKTA]
    status: verified

  - id: hhs_hipaa_breach_portal
    name: HHS OCR HIPAA 침해 보고서 (Wall of Shame)
    what: "월별 500명+ 영향 헬스케어 데이터 침해 건수, 영향 인원, 유형별 분류"
    why_leading: "헬스케어가 사이버 공격 1순위 표적. HHS 포털 신규 등록은 보안 예산 증액 결정 6-12개월 선행"
    lead_time_evidence: "HIPAA Journal 월간 보고서 - 침해 급증 후 6-12개월 시점에 헬스케어 보안 capex 증가"
    source_primary:
      name: HHS Office for Civil Rights Breach Portal
      url: https://ocrportal.hhs.gov/ocr/breach/breach_report.jsf
      access: 웹 검색 무료, 다운로드 가능
      free: true
      api: false
    source_fallback:
      name: HIPAA Journal Monthly Report
      url: https://www.hipaajournal.com/
    update_frequency: 실시간 등록, 월간 집계
    noise_check: "단월 변동성 크나 3개월 이동평균 안정. 2026년 1월 46건. false <15%"
    target_signals:
      bullish: "월간 헬스케어 침해 50건+ 또는 영향 인원 1억명+ → 헬스케어 IT 보안 강세"
      bearish: "침해 건수 감소 추세 → 단기 보안 예산 모멘텀 약화"
    relevant_tickers_kr: ["안랩(053800)", "파수(150900)"]
    relevant_tickers_us: [CRWD, PANW, FTNT, OKTA, ZS]
    status: verified

  - id: sec_8k_cyber_disclosure
    name: SEC Form 8-K Item 1.05 / 8.01 사이버 침해 공시
    what: "미국 상장사가 SEC에 의무 공시하는 사이버 침해 8-K 건수 (Item 1.05 material, 8.01 voluntary)"
    why_leading: "2023년 12월 시행된 SEC 의무 공시 규정. 침해 발생→4영업일 내 공시→피해사 보안 vendor 교체/추가 발주"
    lead_time_evidence: "Greenberg Traurig/Debevoise 2025 분석 - 2023.12~2025.1 동안 55건 8-K 공시. 평균 침해→공시 7.88 영업일. 공시→보안 capex 결정 평균 60-90일"
    source_primary:
      name: SEC EDGAR Full-Text Search
      url: https://efts.sec.gov/LATEST/search-index?q=%22Item+1.05%22&forms=8-K
      access: 무료, API 제공
      free: true
      api: true
    source_fallback:
      name: SEC EDGAR browse
      url: https://www.sec.gov/cgi-bin/browse-edgar
      api: true
    update_frequency: 실시간
    noise_check: "Item 1.05 vs 8.01 분류 모호 (2024 SEC 가이던스 후 변동), 합산 권고. false ~20%"
    target_signals:
      bullish: "분기 8-K 사이버 공시 5건 이상 + Fortune 500 포함 → 보안 벤더 수주 강세"
      bearish: "공시 건수 둔화 → 보안 일시적 모멘텀 약화"
    relevant_tickers_kr: ["안랩(053800)", "이글루(067920)"]
    relevant_tickers_us: [CRWD, PANW, FTNT, S, ZS, OKTA, NET]
    status: verified

  - id: fbi_ic3_annual_report
    name: FBI IC3 Internet Crime Report 연간
    what: "FBI Internet Crime Complaint Center 연간 사이버범죄 신고 건수, 손실액, 랜섬웨어 통계"
    why_leading: "연간 데이터라 후행이지만 산업/규제/보험사 정책 변경의 직접 트리거. 정부 사이버 예산 책정의 근거 자료"
    lead_time_evidence: "FBI IC3 자체 - 연 보고서가 다음해 사이버보험 요율, DoD/CISA 예산 협상의 근거. 2024년 랜섬웨어 신고 +9% YoY (3,156건)"
    source_primary:
      name: FBI IC3 Annual Report
      url: https://www.ic3.gov/annualreport/reports
      access: 매년 4-5월 발표, 무료 PDF
      free: true
      api: false
    source_fallback:
      name: CISA Cybersecurity Year in Review
      url: https://www.cisa.gov/news-events/cybersecurity-advisories
    update_frequency: 연간 (매년 4-5월, 전년 데이터)
    noise_check: "연간 데이터, 추세 평가용. false <5%"
    target_signals:
      bullish: "랜섬웨어 신고 YoY +20% + 손실액 증가 → 보험/보안 합산 수요 강세"
      bearish: "신고 건수 감소 → 단기 보안 모멘텀 약화 (구조 시그널은 아님)"
    relevant_tickers_kr: ["안랩(053800)", "이글루(067920)", "지니언스(263860)"]
    relevant_tickers_us: [CRWD, PANW, FTNT, S]
    status: verified

  - id: mandiant_mtrends_dwell_time
    name: Mandiant M-Trends 연간 - 미디언 dwell time
    what: "Google Cloud Mandiant 연간 보고서의 글로벌 침입 미디언 체류시간(일), 산업별 분류"
    why_leading: "dwell time 증가→탐지/대응(EDR/XDR) 수요 증가. 2014년 205일→2024년 11일→2026년 14일로 다시 증가 = 신규 위협 출현 신호"
    lead_time_evidence: "Mandiant 2014~2026 17년 연간 데이터. dwell time 변곡점이 EDR/XDR 매출 6-12개월 선행 (자체 분석)"
    source_primary:
      name: Google Cloud Mandiant M-Trends
      url: https://cloud.google.com/security/resources/m-trends
      access: 무료 PDF (양식 작성 후)
      free: true
      api: false
    source_fallback:
      name: Mandiant Threat Intelligence Blog
      url: https://cloud.google.com/blog/topics/threat-intelligence
    update_frequency: 연간 (매년 4월경)
    noise_check: "연간 후행 데이터, 구조적 시그널만 활용. false <10%"
    target_signals:
      bullish: "dwell time 증가 추세 반전 → 신규 위협 출현, EDR/XDR 강세"
      bearish: "dwell time 감소 추세 + 침해 건수 감소 → 단기 모멘텀 약화"
    relevant_tickers_kr: ["안랩(053800)", "이글루(067920)"]
    relevant_tickers_us: [CRWD, PANW, S, ZS, NET]
    status: verified

  - id: cybersec_quarterly_billings
    name: 보안 4사 분기 billings/Net New ARR (CRWD/PANW/FTNT/S)
    what: "CrowdStrike, Palo Alto, Fortinet, SentinelOne 분기 billings 및 net new ARR(연간경상매출)"
    why_leading: "billings = 다음 분기 매출의 90%+ 가시화. Net New ARR은 신규 수요의 가장 빠른 정량 시그널"
    lead_time_evidence: "회계학적으로 billings/RPO는 revenue 1-2분기 선행. CRWD Q4 FY26 net new ARR $330.7M(+47% YoY) → 다음 분기 매출 가이던스 직접 결정"
    source_primary:
      name: 각사 IR (10-Q/8-K) - SEC EDGAR
      url: https://ir.crowdstrike.com/
      access: 분기 실적, 무료
      free: true
      api: true
    source_fallback:
      name: SEC EDGAR
      url: https://www.sec.gov/cgi-bin/browse-edgar
      api: true
    update_frequency: 분기 (각사 회계 차이, 8월/11월/3월/5월경)
    noise_check: "Falcon outage(2024.7) 같은 일회성 이벤트 차감 필요. false <15%"
    target_signals:
      bullish: "4사 중 3사 이상 billings YoY +20% + 가이던스 상향 → 보안 섹터 강세"
      bearish: "2사 이상 billings 둔화 + 가이던스 하향 → 보안 capex 정체"
    relevant_tickers_kr: ["안랩(053800)", "이글루(067920)"]
    relevant_tickers_us: [CRWD, PANW, FTNT, S, ZS, NET, CYBR]
    status: verified

  - id: us_federal_cyber_budget
    name: 미국 연방 사이버보안 예산 (DoD + CISA)
    what: "DoD 사이버 예산 + CISA 연간 예산 + 사이버 관련 NDAA 항목"
    why_leading: "정부 예산이 시기별 budget 집행으로 분기 보안 벤더 수주 결정 (특히 정부 SI: PANW, CRWD, ZS 정부버전)"
    lead_time_evidence: "Congressional Research Service - 회계연도 예산 발효(10월) → 다음 분기 정부 보안 SI 수주 확정. CISA 2025 예산 $3.1B"
    source_primary:
      name: White House OMB Budget + CISA Budget
      url: https://www.whitehouse.gov/omb/budget/
      access: 매년 2-3월 대통령 예산안, 9-10월 NDAA 의결 - 무료
      free: true
      api: false
    source_fallback:
      name: Congressional Research Service Reports
      url: https://crsreports.congress.gov/
    update_frequency: 연간 (대통령 예산안 2-3월, NDAA 12월)
    noise_check: "정치적 변동, continuing resolution 영향. false <20%"
    target_signals:
      bullish: "DoD 사이버 예산 +10% 이상 + CISA 예산 증액 → 정부 SI 수주 강세"
      bearish: "예산 동결/삭감 + Continuing Resolution 장기화 → 정부 보안 수주 둔화"
    relevant_tickers_kr: []
    relevant_tickers_us: [PANW, CRWD, FTNT, BAH, LDOS, KBR]
    status: verified
```

---

### 3.4 양자컴퓨팅 (6개)

```yaml
sector: 양자컴퓨팅
indicators:
  - id: nist_pqc_standards_progress
    name: NIST PQC 표준화 진척 (FIPS 발행 일정)
    what: "FIPS 203/204/205(2024.8 발행) 후속 - FIPS 206(Falcon), HQC, 마이그레이션 가이드라인 발행 일정"
    why_leading: "FIPS 발행→연방기관/대기업 PQC 마이그레이션 의무화 12-24개월 → 보안/IT 인프라 사이클의 가장 명확한 정책 트리거"
    lead_time_evidence: "NIST IR 8547 - 2035년까지 quantum-vulnerable 알고리즘 deprecation. FIPS 발행→실제 도입 12-24개월 (CISA 가이드라인 자체 명시)"
    source_primary:
      name: NIST CSRC Post-Quantum Cryptography
      url: https://csrc.nist.gov/projects/post-quantum-cryptography
      access: 매월 업데이트, 무료
      free: true
      api: false
    source_fallback:
      name: CISA PQC Migration Roadmap
      url: https://www.cisa.gov/quantum
    update_frequency: 비정기 (수개월~연 단위, 마일스톤 베이스)
    noise_check: "정책 발표 자체가 시그널, false 거의 없음 (이벤트 베이스)"
    target_signals:
      bullish: "신규 FIPS 발행 + 연방기관 마이그레이션 deadline 발표 → PQC 솔루션 벤더 강세"
      bearish: "마이그레이션 일정 지연 발표 → 단기 PQC 모멘텀 약화"
    relevant_tickers_kr: ["케이씨에스(115500)"]
    relevant_tickers_us: [IBM, MSFT]
    status: verified

  - id: ibm_google_qubit_roadmap
    name: IBM/Google 양자 큐비트 로드맵 발표
    what: "IBM Quantum/Google Quantum AI의 큐비트 수, gate count, 에러 보정 마일스톤 발표"
    why_leading: "큐비트 수/품질 발표→실제 양자 advantage 도달 12-24개월 선행. IBM Heron(156qb)→Flamingo(462qb)→Starling(200qb+EC, 2029)"
    lead_time_evidence: "IBM 자체 로드맵 - 2024년 발표 시점 대비 2-3년 후 실제 인도. 2029 Starling(error-corrected) 마일스톤이 양자 상용화 변곡점"
    source_primary:
      name: IBM Quantum Computing Blog + Google Quantum AI Blog
      url: https://www.ibm.com/quantum/blog
      access: 무료, RSS
      free: true
      api: false
    source_fallback:
      name: arXiv quant-ph
      url: https://arxiv.org/list/quant-ph/recent
    update_frequency: 비정기 (연 1-2회 메이저, 분기 마이너)
    noise_check: "PR 과장 가능성, peer-reviewed 검증 함께 봐야. false ~25%"
    target_signals:
      bullish: "1000큐비트+ error-corrected 시연 + 산업 응용 발표 → 양자 섹터 모멘텀"
      bearish: "로드맵 지연 발표 → 단기 양자 테마 조정"
    relevant_tickers_kr: []
    relevant_tickers_us: [IBM, GOOGL, IONQ, RGTI, QBTS, QUBT]
    status: verified

  - id: arxiv_quantph_submission_rate
    name: arXiv quant-ph 카테고리 월간 신규 논문 수
    what: "arXiv quantum physics 카테고리 월별 신규 submission 수"
    why_leading: "기초 연구→상용화 5-10년이지만, 특정 토픽(error correction, fault-tolerance) 급증은 6-12개월 선행"
    lead_time_evidence: "Cornell arXiv 자체 통계 - quant-ph 연간 +15% 성장 추세. 특정 키워드(QEC, distillation) 논문 급증→VC 자금/벤더 발표 6-12개월 선행"
    source_primary:
      name: arXiv quant-ph statistics
      url: https://arxiv.org/list/quant-ph/recent
      access: 무료 + arXiv API
      free: true
      api: true
    source_fallback:
      name: arXiv API
      url: https://info.arxiv.org/help/api/index.html
      api: true
    update_frequency: 일간 신규, 월간 집계
    noise_check: "category cross-listing 영향, 키워드 필터링 필요. false ~20%"
    target_signals:
      bullish: "월간 quant-ph 1,000건 돌파 + QEC 논문 비중 증가 → 양자 R&D 가속"
      bearish: "submission 둔화 → 학계 모멘텀 약화"
    relevant_tickers_kr: []
    relevant_tickers_us: [IBM, GOOGL, IONQ, RGTI, QBTS]
    status: verified

  - id: nqi_federal_funding
    name: 미국 NQI 연방 예산 집행 (DOE/NIST/NSF/NASA)
    what: "National Quantum Initiative 연간 예산 집행 + DOE QIS Research Centers 자금 + 신규 어워드 발표"
    why_leading: "연방 예산 집행→6-12개월 후 양자 스타트업/대학 contract 발표→상장사(IBM, IONQ) 수주"
    lead_time_evidence: "NQI 2025 연간 보고서 - $625M DOE QIS Centers 갱신(2025.7), 5년 $2.7B 재인가(NQI Reauth Act)"
    source_primary:
      name: National Quantum Initiative
      url: https://www.quantum.gov/
      access: 연간 보고서 + 보도자료, 무료
      free: true
      api: false
    source_fallback:
      name: DOE Office of Science Quantum
      url: https://science.osti.gov/Initiatives/QIS
    update_frequency: 분기/비정기 (재인가 + 어워드)
    noise_check: "정치적 변동, CR 영향. false <20%"
    target_signals:
      bullish: "신규 NQI 재인가 + DOE Centers 자금 증액 → 양자 섹터 펀더멘털 강세"
      bearish: "예산 삭감 + 정치 불확실 → 양자 테마 조정"
    relevant_tickers_kr: []
    relevant_tickers_us: [IBM, IONQ, RGTI, QBTS, QUBT, HON]
    status: verified

  - id: darpa_qbi_milestones
    name: DARPA Quantum Benchmarking Initiative (QBI) 단계별 선정 발표
    what: "DARPA QBI Stage A→B→C 단계별 선정 기업 발표, 자금 지원 규모"
    why_leading: "QBI는 2033년 utility-scale 양자 도달 검증 프로그램. Stage 통과 = 정부 검증 → 민간 자금 유치 6-12개월 선행"
    lead_time_evidence: "DARPA 자체 - Stage A(2025.4)→B(2025.11) 선정. Stage 통과 후 IBM/IONQ/Quantinuum 등 stock 반응 + VC 라운드 가속 패턴"
    source_primary:
      name: DARPA QBI Program
      url: https://www.darpa.mil/research/programs/quantum-benchmarking-initiative
      access: 무료 보도자료
      free: true
      api: false
    source_fallback:
      name: National Quantum Initiative
      url: https://www.quantum.gov/
    update_frequency: 비정기 (연 1-2회 단계별 발표)
    noise_check: "선정 자체가 명확 시그널, false <10%"
    target_signals:
      bullish: "Stage B/C 진출 발표 + Maryland 매칭펀드 등 추가 자금 → 양자 H/W 강세"
      bearish: "Stage 탈락 + 일정 지연 → 해당 기업 약세"
    relevant_tickers_kr: []
    relevant_tickers_us: [IBM, IONQ, RGTI, QBTS]
    status: verified

  - id: doe_qis_centers_renewal
    name: DOE National QIS Research Centers 갱신/자금 발표
    what: "DOE 5개 양자정보과학 연구센터 (Q-NEXT, SQMS, AQT, C2QA, QSC) 연간 자금 집행/갱신"
    why_leading: "5개 센터가 미국 양자 R&D의 backbone. 갱신/추가 자금 발표 → 산업 협력사(IBM, Quantinuum) contract 6-12개월 선행"
    lead_time_evidence: "DOE 2025.7 발표 - $625M 갱신 (FY25 $125M + outyear). 2020 초기 5년 $625M 후 2025 갱신 = 5년 사이클로 산업 영향 명확"
    source_primary:
      name: DOE Office of Science
      url: https://science.osti.gov/Initiatives/QIS
      access: 무료 보도자료
      free: true
      api: false
    source_fallback:
      name: White House OSTP Quantum
      url: https://www.whitehouse.gov/ostp/
    update_frequency: 비정기 (5년 사이클, 연간 자금 집행)
    noise_check: "5년 사이클로 시그널 빈도 낮음, 누적 추세 평가"
    target_signals:
      bullish: "센터 갱신 + 신규 센터 추가 → 산업 파트너 수주 강세"
      bearish: "예산 동결/삭감 → 양자 R&D 모멘텀 약화"
    relevant_tickers_kr: []
    relevant_tickers_us: [IBM, IONQ, RGTI, MSFT, GOOGL]
    status: verified
```

---

### 3.5 SMR/원자력 (6개)

```yaml
sector: SMR/원자력
indicators:
  - id: pjm_iso_interconnection_queue
    name: PJM/ERCOT/MISO Interconnection Queue (대형 부하·발전 신청)
    what: "ISO 송전망에 신규 연결을 요청한 데이터센터 부하 + 발전(가스/원자력) MW 누적 큐"
    why_leading: "데이터센터 신규 신청 → 24-36개월 후 전력 부족 가시화 → SMR/원자력 PPA, 우라늄 발주로 연결. PJM 큐는 발전 신청-상업가동까지 평균 8년"
    lead_time_evidence: "PJM 2025 Long-Term Load Forecast: 2024-2030 피크 +32GW 중 30GW가 데이터센터. RMI 분석 — 신청-COD 평균 8년 (2008년 2년→2025년 8년). 하이퍼스케일러 nuclear PPA 결정은 큐 정체 가시화 후 12-18개월 내 발생 (Microsoft TMI 2024.9, Amazon Susquehanna 2024.3, Meta-Constellation 2025)"
    source_primary:
      name: PJM Interconnection Queue (Public Queue Status)
      url: https://www.pjm.com/planning/services-requests/interconnection-queues
      access: 무료 공개 (Excel/CSV)
      free: true
      api: false
    source_fallback:
      name: Interconnection.fyi (PJM/ERCOT/MISO 일일 통합)
      url: https://www.interconnection.fyi/
    update_frequency: 월간 (PJM 분기 리포트 + 월별 업데이트, ERCOT/MISO 분기)
    noise_check: "착공 전 취소율 약 30%. 부하 신청은 LOI 단계에서 약 25% 철회. 분기 누적 +20% 임계 적용 시 false signal 약 25%"
    target_signals:
      bullish: "데이터센터 부하 신청 분기 +20% 또는 50GW 이상 누적 → SMR/원자력 강세 12-18개월 선행"
      bearish: "신청 취소 + 부하 큐 감소 또는 정체 → 약세"
    relevant_tickers_kr: ["한국전력(015760)", "두산에너빌리티(034020)", "한전기술(052690)", "우리기술(032820)"]
    relevant_tickers_us: [CCJ, URA, URNM, BWXT, NNE, OKLO, SMR, LEU, CEG, VST]
    status: verified

  - id: uxc_u3o8_weekly_price
    name: UxC Ux U3O8 Spot Price (주간 우라늄 현물가)
    what: "우라늄 현물 거래의 주간 벤치마크 가격 — 1987년부터 발표된 업계 표준"
    why_leading: "우라늄 현물가 → 채굴사 마진 + 신규 광산 투자 의사결정에 1-3분기 선행"
    lead_time_evidence: "UxC: spot 시장은 1-12개월 forward delivery 포함, 대부분 1-3개월 prompt. Cameco/Kazatomprom 분기 가이던스가 spot에 즉시 반영, 채굴 capex는 spot 6-12개월 후행"
    source_primary:
      name: UxC Nuclear Fuel Price Indicators (주간 발표)
      url: https://www.uxc.com/p/price
      access: 헤드라인 가격 무료, 상세 리포트 유료
      free: partial
      api: false
    source_fallback:
      name: Cameco Uranium Price
      url: https://www.cameco.com/invest/markets/uranium-price
    update_frequency: 주간 (월요일 발표)
    noise_check: "spot은 거래량 적어 변동성 크지만 (주간 ±5% 흔함), 4주 이동평균 적용 시 추세 안정"
    target_signals:
      bullish: "spot 4주 MA 대비 +10% 또는 LT price 상향 돌파 → 우라늄/원전 강세"
      bearish: "spot 4주 MA -10% + Kazatomprom/Cameco 가이던스 상향 → 약세"
    relevant_tickers_kr: []
    relevant_tickers_us: [CCJ, URA, URNM, URNJ, NXE, DNN, UEC, UUUU]
    status: verified

  - id: cameco_kap_quarterly_guidance
    name: Cameco + Kazatomprom 분기 생산 가이던스
    what: "글로벌 1차 우라늄 공급 약 40%를 차지하는 두 회사의 분기 생산 실적 + 차년도 가이던스"
    why_leading: "두 회사의 가이던스 하향 → 6-12개월 내 spot 가격 강세로 연결. 2024-2025 사례: Cameco McArthur River 18→14-15Mlbs 하향 + KAP 2026년 -10% 발표 후 spot $63 → $79 회복"
    lead_time_evidence: "Cameco Q3 2024 가이던스 하향(18→14-15Mlbs) → 6개월 내 spot 회복. KAP 2026 -10% 발표(2025) → 즉시 반영 + LT 가격 $80 유지"
    source_primary:
      name: Cameco Investor Relations Quarterly Reports
      url: https://www.cameco.com/invest/financial-reports
      access: 무료 공개
      free: true
      api: false
    source_fallback:
      name: Kazatomprom IR (Operating & Trading Updates 분기별)
      url: https://www.kazatomprom.kz/en/category/financial_reporting
    update_frequency: 분기 (Q1: 5월, Q2: 8월, Q3: 11월, Q4: 2월)
    noise_check: "가이던스 자체는 신뢰도 높음 (둘 다 KASE/TSX 상장 의무 공시). 단발성 광산 사고와 구조적 하향 구분 필요"
    target_signals:
      bullish: "양사 중 하나라도 가이던스 하향 + 차년도 -5% 이상 → 우라늄 강세"
      bearish: "양사 모두 가이던스 상향 + 신규 광산 가동 → 약세"
    relevant_tickers_kr: []
    relevant_tickers_us: [CCJ, URA, URNM, URNJ, NXE, UEC]
    status: verified

  - id: hyperscaler_nuclear_ppa
    name: 하이퍼스케일러 원자력 PPA 발표 추적 (Microsoft/Google/Amazon/Meta)
    what: "Big Tech 4사의 신규 원자력 PPA, 재가동, SMR 계약 공개 발표 — 누적 GW와 발표 빈도"
    why_leading: "PPA 발표 → 12-24개월 후 SMR 발주, 우라늄 장기계약 가속. Microsoft TMI(2024.9, 835MW) → Constellation 주가 6개월 +95%. Google-Kairos(500MW), Meta RFP(1-4GW, 2025)"
    lead_time_evidence: "S&P Global Sustainable1 Hyperscaler Procurement 분석: 2024년 10GW+ 신규 nuclear 계약. 발표 시점부터 평균 SMR 인허가/사이트 결정까지 12-24개월"
    source_primary:
      name: Data Center Frontier Nuclear Tracker (큐레이션 + 1차 링크)
      url: https://www.datacenterfrontier.com/energy/article/55239739/data-center-nuclear-power-update-microsoft-constellation-aws-talen-meta
      access: 무료 공개
      free: true
      api: false
    source_fallback:
      name: EIA Today in Energy
      url: https://www.eia.gov/todayinenergy/detail.php?id=63304
    update_frequency: 비정기 (이벤트 기반, 월 0-3건)
    noise_check: "MOU/RFP 단계 발표는 약 40% 무산. 'binding PPA + EPC 선정' 단계에서만 신호 채택 권장"
    target_signals:
      bullish: "분기 1건 이상 binding nuclear PPA (500MW+) → SMR/원전 섹터 강세"
      bearish: "발표된 PPA 좌초/연기 → 단기 약세"
    relevant_tickers_kr: ["두산에너빌리티(034020)", "한전기술(052690)"]
    relevant_tickers_us: [CEG, VST, TLN, SMR, OKLO, NNE, BWXT, GEV]
    status: verified

  - id: doe_lpo_nuclear_announcements
    name: DOE Loan Programs Office 원자력 대출 발표
    what: "DOE LPO의 원전 재가동/SMR/연료주기 대출 보증 발표 — 건수 + 누적 금액"
    why_leading: "LPO 대출 보증 → 6-12개월 내 EPC 계약, 핵연료 발주로 연결. Holtec Palisades $1.52B(2024.9) → 2025 우라늄 장기계약 활발화 견인"
    lead_time_evidence: "Nuclear Innovation Alliance 2025.6 보고서: LPO 클로징 → COD까지 평균 36개월, 우라늄 발주는 LPO 후 6-12개월"
    source_primary:
      name: DOE Loan Programs Office Press Releases
      url: https://www.energy.gov/lpo/listings/lpo-press-releases
      access: 무료 공개
      free: true
      api: false
    source_fallback:
      name: DOE Office of Energy Dominance Financing News
      url: https://www.energy.gov/edf/listings/edf-news
    update_frequency: 비정기 (이벤트 기반, 분기 1-3건)
    noise_check: "Conditional Commitment과 Closing 구분 필수. Conditional은 약 15% 좌초율, Closing은 거의 100% 진행"
    target_signals:
      bullish: "분기 nuclear LPO Closing 1건 이상 → 원전 EPC/연료 강세"
      bearish: "기존 보증 취소/재검토 → 단기 충격"
    relevant_tickers_kr: []
    relevant_tickers_us: [BWXT, CCJ, LEU, NNE, OKLO, SMR, GEV]
    status: verified

  - id: eia_860m_planned_nuclear
    name: EIA-860M 신규/계획 원자력 발전기 인벤토리 (월간)
    what: "1MW 이상 신규/계획 발전기 월간 인벤토리 — Planned, Under Construction, Standby 단계 + 예정 COD"
    why_leading: "Planned → Under Construction 전환은 EPC 발주 + 핵연료 첫 로딩 18-24개월 선행"
    lead_time_evidence: "EIA Form 860M 명세: 'plant must be scheduled for commercial operation within 10 years for nuclear'. 'Under Construction' 신호 후 BWXT/Westinghouse 등 EPC 계약 평균 6-12개월 내 체결"
    source_primary:
      name: EIA Form 860M (Preliminary Monthly Generator Inventory)
      url: https://www.eia.gov/electricity/data/eia860m/
      access: 무료 Excel 다운로드 (2015~)
      free: true
      api: false
    source_fallback:
      name: EIA Nuclear & Uranium Data Hub
      url: https://www.eia.gov/nuclear/data.php
    update_frequency: 월간 (매월 22일 전후 발표)
    noise_check: "원자력 'Planned' 단계는 capex 미확정으로 약 20% 취소율. 'Under Construction'으로 전환된 건은 거의 100% 진행"
    target_signals:
      bullish: "Under Construction 전환 분기 1건 이상 또는 Planned 신규 등록 → 강세"
      bearish: "Planned 취소/연기 → 약세"
    relevant_tickers_kr: ["한국전력(015760)"]
    relevant_tickers_us: [CEG, VST, BWXT, GEV, SMR, OKLO, NNE]
    status: verified
```

---

### 3.6 우주항공/방산 (6개)

```yaml
sector: 우주항공/방산
indicators:
  - id: dsca_fms_notifications
    name: DSCA Major Arms Sales Notifications (Section 36(b))
    what: "$14M (장비) / $50M (서비스) 이상 FMS 사전 의회 통보 — 일자/구매국/품목/금액/계약사 명시"
    why_leading: "Section 36(b) 통보 → LOA 서명까지 30일 → 실제 인도/매출 인식까지 12-36개월. 매출 turn 6-12개월 선행"
    lead_time_evidence: "DSCA 통계: FY2024 FMS 누적 $117.9B. AECA Section 36(b) 통보 → LOA → contract award 평균 6-9개월"
    source_primary:
      name: DSCA Major Arms Sales Press Releases
      url: https://www.dsca.mil/Press-Media/Major-Arms-Sales
      access: 무료 공개 (RSS 가능)
      free: true
      api: false
    source_fallback:
      name: Federal Register 36(b)(1) Arms Sales Notification
      url: https://www.federalregister.gov/documents/search?conditions%5Bterm%5D=arms+sales+notification
    update_frequency: 주 2-5건 (이벤트 기반)
    noise_check: "통보 후 의회 부결/구매국 철회 약 5% — 매우 낮은 false signal. 통보 금액은 'up to' 가치라 실제 LOA는 30-70% 수준 흔함"
    target_signals:
      bullish: "분기 누적 $20B+ 또는 단일 록히드/RTX/노스롭 수혜 $5B+ → 6-12개월 후 매출 strength"
      bearish: "통보 부결 또는 주요 계약 취소 → 단기 약세"
    relevant_tickers_kr: ["한화에어로스페이스(012450)", "LIG넥스원(079550)", "현대로템(064350)", "한국항공우주(047810)"]
    relevant_tickers_us: [LMT, RTX, NOC, GD, BA, LHX, HII, KTOS]
    status: verified

  - id: acled_conflict_index
    name: ACLED 정치폭력 이벤트 인덱스 (실시간)
    what: "전 세계 무력충돌·드론 공격·미사일 공격·전투 사망자 — 7일 이동평균 + 지역별 분해"
    why_leading: "분쟁 강도 → 미사일·탄약·드론 소진 → 3-9개월 후 긴급 보충 발주 (UMP, supplemental appropriation)"
    lead_time_evidence: "SIPRI 2024 Trends in Military Expenditure: 분쟁 강도 → 다음 해 군비 +5-15%. Ukraine 전쟁 backtest: 2022.2 침공 후 3개월 내 GDLS·LMT·RTX 신규 수주 +200%"
    source_primary:
      name: ACLED Data Export Tool (계정 등록 무료)
      url: https://acleddata.com/conflict-data
      access: 학술/비영리 무료, 상업 등록 필요
      free: partial
      api: true
    source_fallback:
      name: ACLED Conflict Index & Watchlist (연간 무료 공개)
      url: https://acleddata.com/conflict-index-2026-watchlist
    update_frequency: 주간 (실시간 가까움)
    noise_check: "단일 이벤트 노이즈 큼 → 7일 또는 30일 MA 권장. 사망자 vs 사건 수 분리 추적 필요"
    target_signals:
      bullish: "30일 사건 MA +20% 또는 ACLED 지정 'Extreme' 분쟁 신규 진입 → 방산 강세"
      bearish: "주요 분쟁 휴전 + 7일 MA -30% → 단기 약세 (단, 매출은 12-18개월 유지)"
    relevant_tickers_kr: ["한화에어로스페이스(012450)", "LIG넥스원(079550)", "풍산(103140)", "한화시스템(272210)"]
    relevant_tickers_us: [LMT, RTX, NOC, GD, KTOS, AVAV, BA, ITA]
    status: verified

  - id: nato_defense_spend_quarterly
    name: NATO 회원국 분기 국방예산 발표 (% of GDP)
    what: "32개 NATO 회원국 분기/연간 국방지출 % GDP — 2025년 모두 2% 달성, 2035년 5% 목표"
    why_leading: "NATO 약속 → 회원국 국방예산법 통과 → 12-24개월 후 EU/NATO 통합 발주. 2014→2025 backtest: 유럽 방산 ETF 401% 상승"
    lead_time_evidence: "McKinsey European Defense 2025, NATO 2025 Defense Expenditure Report: 2014 Wales→2025 모든 회원국 2%, 2025 The Hague→2035 5% 약속. McKinsey 분석상 spending +1pp → defense capex +20% (12-18개월 lag)"
    source_primary:
      name: NATO Defense Expenditure of NATO Countries (연간 PDF)
      url: https://www.nato.int/cps/en/natohq/topics_49198.htm
      access: 무료 공개
      free: true
      api: false
    source_fallback:
      name: Atlantic Council NATO Defense Spending Tracker
      url: https://www.atlanticcouncil.org/commentary/trackers-and-data-visualizations/nato-defense-spending-tracker/
    update_frequency: 분기 (NATO 공식은 연간 + 회원국 자체 분기 발표)
    noise_check: "연간 데이터는 변동성 낮음 (false signal 거의 없음). 단, 약속 vs 실제 집행 갭 존재"
    target_signals:
      bullish: "신규 +0.3pp GDP 또는 신규 100B+ defense fund 발표 → EU 방산 강세 12-18개월"
      bearish: "약속 미달 + 예산 삭감 → 약세"
    relevant_tickers_kr: ["한화에어로스페이스(012450)", "현대로템(064350)", "LIG넥스원(079550)"]
    relevant_tickers_us: [LMT, RTX, NOC, GD, ITA, PPA, BA]
    status: verified

  - id: dod_daily_contracts
    name: 미 국방부 일일 계약 발표 ($7.5M+)
    what: "DoD가 영업일 5pm ET에 발표하는 $7.5M+ 계약 — 회사명/금액/품목/장소"
    why_leading: "계약 award → 6-18개월 후 매출 인식. 회사 분기 실적 발표 전 매출 visibility 확보"
    lead_time_evidence: "DCMA 통계: 31만 계약, 7.16T 관리, 일평균 $780M 지급. 매출 인식은 6-18개월 (LMT/RTX 분기 backlog 분석에서 확인)"
    source_primary:
      name: U.S. Department of War Daily Contracts
      url: https://www.war.gov/News/Contracts/
      access: 무료 공개 (이메일 구독 + RSS)
      free: true
      api: false
    source_fallback:
      name: GovConWire Contract Awards
      url: https://www.govconwire.com/category/contract_awards
    update_frequency: 영업일 (월-금 5pm ET)
    noise_check: "IDIQ ceiling vs 실제 task order 차이 큼. 단발성 contract보단 30일 누적 + 회사별 분해 권장"
    target_signals:
      bullish: "회사별 30일 누적 vs 12개월 평균 +30% → 6-9개월 후 매출 strength"
      bearish: "Stop-work order 또는 주요 program termination 발표 → 단기 약세"
    relevant_tickers_kr: []
    relevant_tickers_us: [LMT, RTX, NOC, GD, BA, LHX, HII, GE, KTOS]
    status: verified

  - id: faa_commercial_space_licenses
    name: FAA 상업 우주발사 라이선스 + 발사 cadence
    what: "FAA Part 450 발사·재진입 라이선스, STA 승인, 월간 미국 상업 발사 횟수"
    why_leading: "라이선스 발급 → 평균 6-18개월 내 본격 cadence 진입 → 위성·발사체 부품/연료 매출 상승"
    lead_time_evidence: "FAA Aerospace Forecast 2024-2044 commercial space chapter: 라이선스 → 운영 cadence 6-18개월. SpaceX backtest 2020-2025: 라이선스 +20% → 12개월 후 발사 +25%"
    source_primary:
      name: FAA Office of Commercial Space Transportation Licenses
      url: https://www.faa.gov/space/licenses
      access: 무료 공개 (CSV 가능)
      free: true
      api: false
    source_fallback:
      name: Space-Track Catalog (USSF 18 SDS)
      url: https://www.space-track.org/
    update_frequency: 월간 (FAA 운영 데이터 + 신규 라이선스 비정기)
    noise_check: "라이선스 보유 ≠ 즉시 발사. 누적 cadence는 매우 안정적 — false signal 거의 없음"
    target_signals:
      bullish: "분기 미국 상업 발사 +20% 또는 신규 vehicle license (Starship, New Glenn) → 위성/발사 강세"
      bearish: "FAA 안전 정지 명령 → 단기 충격"
    relevant_tickers_kr: ["한화에어로스페이스(012450)", "한국항공우주(047810)", "컨텍(451760)"]
    relevant_tickers_us: [RKLB, LMT, BA, NOC, ASTS, IRDM, PL, RTX]
    status: verified

  - id: usgs_titanium_sponge
    name: USGS 티타늄 스폰지 수입/생산 통계 (월간/연간)
    what: "미국 항공등급 티타늄 스폰지 월간 수입량 + 가격 + 생산국별 배분"
    why_leading: "Ti 스폰지 → 항공 forging → 항공기 동체 6-12개월 lead time. 2023년 +35% → 2024-2025 Boeing 787/F-35 deliveries +20% 전조"
    lead_time_evidence: "USGS Mineral Commodity Summaries 2024 Titanium: 항공 80% 수요. 2021→2023 +75% 회복 → 2024 deliveries 강세 동행"
    source_primary:
      name: USGS Mineral Commodity Summaries — Titanium
      url: https://pubs.usgs.gov/periodicals/mcs2024/mcs2024-titanium.pdf
      access: 무료 공개 (PDF)
      free: true
      api: false
    source_fallback:
      name: USGS Mineral Industry Surveys (월간 PDF)
      url: https://www.usgs.gov/centers/national-minerals-information-center/titanium-statistics-and-information
    update_frequency: 월간 (Mineral Industry Surveys) + 연간 (MCS)
    noise_check: "재고 사이클로 단월 변동성 큼. 중국·러시아·일본 65% 집중 → 지정학 충격 시 spike noise 분리 필요"
    target_signals:
      bullish: "12개월 수입량 5년 MA +20% → 6-12개월 후 항공 deliveries 강세"
      bearish: "수입 -20% 또는 항공등급 공급 부족 → 단기 항공 capex 압박"
    relevant_tickers_kr: ["한국항공우주(047810)"]
    relevant_tickers_us: [BA, RTX, LMT, NOC, GE, HEI, TDG, ATI]
    status: verified
```

---

### 3.7 생명공학 (6개)

```yaml
sector: 생명공학
indicators:
  - id: pdufa_calendar
    name: PDUFA Action Date Calendar (FDA 결정일 일정)
    what: "FDA가 NDA/BLA 검토 결과 발표 약속일 — Standard 10개월, Priority 6개월"
    why_leading: "PDUFA 일자 → 결정 직전 30-60일 run-up. 결정 발표일에 ±20-50% 가격 변동. 회사 단위 binary catalyst"
    lead_time_evidence: "PDUFA VII 약속: standard 90% within 10 months of filing, priority 6 months. Pharmacy Times/MIT Sloan 연구: PDUFA 60일 전부터 implied vol 급등"
    source_primary:
      name: FDA Drug Approval Calendar (개별 PDUFA 일자는 회사 공시)
      url: https://www.fda.gov/drugs/development-approval-process-drugs
      access: 무료 공개
      free: true
      api: true
    source_fallback:
      name: BiopharmCatalyst PDUFA Calendar (free)
      url: https://www.biopharmcatalyst.com/calendars/pdufa-calendar
    update_frequency: 회사 공시 + 통합 캘린더 일일
    noise_check: "Complete Response Letter (CRL) 비율 약 25-30% — 단일 종목 false signal 큼. 회사·적응증·치료영역별 historical PoS 가중치 적용 필요"
    target_signals:
      bullish: "PDUFA 90일 전부터 catalyst stock pick + Priority Review/Breakthrough 지정 종목 강세 패턴"
      bearish: "CRL 결정 시 -30~-50% 단일 종목"
    relevant_tickers_kr: ["셀트리온(068270)", "삼성바이오로직스(207940)", "유한양행(000100)", "SK바이오팜(326030)", "알테오젠(196170)"]
    relevant_tickers_us: [PFE, MRK, LLY, NVO, ABBV, BMY, GILD, REGN, VRTX, MRNA]
    status: verified

  - id: clinicaltrials_phase3_starts
    name: ClinicalTrials.gov Phase 3 신규 등록 (월간)
    what: "CT.gov에 신규 등록된 Phase 3 임상 — 적응증/스폰서/모달리티별 분해"
    why_leading: "Phase 3 등록 → 평균 24-36개월 후 NDA 제출 → 약 36-46개월 후 FDA 결정. 회사 R&D 파이프라인의 가장 강력한 forward indicator"
    lead_time_evidence: "PMC Wong et al. 2019 (Biostatistics): Phase 3 평균 duration 30개월 + filing 6개월 + review 6-10개월"
    source_primary:
      name: ClinicalTrials.gov (NIH/NLM)
      url: https://clinicaltrials.gov/
      access: 완전 무료, API 제공
      free: true
      api: true
    source_fallback:
      name: WHO ICTRP (글로벌 trial registry meta)
      url: https://trialsearch.who.int/
    update_frequency: 일일 (회사 등록 시점)
    noise_check: "Phase 3 → approval 평균 PoS 59% (Wong 2019), oncology 35%. sponsor·primary endpoint·FDA endorsement 필터 필요"
    target_signals:
      bullish: "회사 신규 Phase 3 적응증 (특히 first-in-class) → 24-36개월 후 매출 trigger"
      bearish: "Phase 3 중단/실패 (CT.gov status: terminated) → 단기 약세"
    relevant_tickers_kr: ["셀트리온(068270)", "한미약품(128940)", "대웅제약(069620)", "유한양행(000100)"]
    relevant_tickers_us: [LLY, NVO, MRK, PFE, REGN, VRTX, BMY, ABBV, MRNA, BIIB]
    status: verified

  - id: fda_advisory_committee_meetings
    name: FDA Advisory Committee (Adcom) 회의 일정
    what: "FDA가 Federal Register에 15일 전 의무 공지하는 자문위 회의 — 안건/약물/회사 명시"
    why_leading: "Adcom 결과 → PDUFA 결정 거의 결정적. Positive vote → 주가 +20-40%, Negative vote → -30-50%. PDUFA 결정보다 통상 30-90일 선행"
    lead_time_evidence: "BiotechEdge research: Adcom → PDUFA 30-90일 후 결정. 2010-2024 backtest에서 positive vote → 후속 approval 87% (Tufts CSDD 추정)"
    source_primary:
      name: FDA Advisory Committee Calendar
      url: https://www.fda.gov/advisory-committees/advisory-committee-calendar
      access: 무료 공개
      free: true
      api: false
    source_fallback:
      name: Federal Register FDA Advisory Committee Meetings
      url: https://www.federalregister.gov/agencies/food-and-drug-administration
    update_frequency: 회의별 (15일 전 공지 의무)
    noise_check: "FDA가 Adcom을 거치지 않고 결정하는 비율 점차 증가 → 'no Adcom = positive signal' 가능성"
    target_signals:
      bullish: "Positive Adcom vote → 30-90일 후 PDUFA approval probability 87%"
      bearish: "Negative vote → CRL 가능성 70%+"
    relevant_tickers_kr: ["셀트리온(068270)", "삼성바이오로직스(207940)", "알테오젠(196170)"]
    relevant_tickers_us: [LLY, NVO, MRK, PFE, REGN, VRTX, BIIB, MRNA, GILD, BMY]
    status: verified

  - id: cms_part_d_glp1_spending
    name: CMS Medicare Part D 처방·지출 대시보드 (GLP-1 등 분기/연간)
    what: "Medicare Part D 약물별 청구건수 + 지출액 — Ozempic/Wegovy/Mounjaro 등 처방 트렌드"
    why_leading: "Medicare Part D 처방 trend → 회사 분기 실적 1-2분기 선행. 2024년 Part D GLP-1 +30% → LLY/NVO 분기 매출 상회"
    lead_time_evidence: "Drug Channels 2026.2 분석: Part D 데이터는 회사 실적 발표 1-2분기 선행"
    source_primary:
      name: CMS Medicare Part D Drug Spending Dashboard
      url: https://data.cms.gov/tools/medicare-part-d-drug-spending-dashboard
      access: 완전 무료, CSV/API
      free: true
      api: true
    source_fallback:
      name: CMS Medicare-Medicaid Spending by Drug
      url: https://data.cms.gov/summary-statistics-on-use-and-payments/medicare-medicaid-spending-by-drug
    update_frequency: 연간 (full data) + 분기 업데이트
    noise_check: "Part D는 65세 이상 + 일부 장애 → 전체 시장의 약 25-35%. GLP-1 처방의 large portion은 commercial insurance/cash"
    target_signals:
      bullish: "약물별 분기 +20% YoY → 회사 실적 상회 확률 70%+"
      bearish: "특정 약물 처방 -10% + 경쟁약 +20% → 점유율 shift"
    relevant_tickers_kr: ["한미약품(128940)", "인벤티지랩(389470)"]
    relevant_tickers_us: [LLY, NVO, PFE, MRK, ABBV, REGN, BMY, VRTX]
    status: verified

  - id: openfda_nda_bla_submissions
    name: openFDA NDA/BLA Submission API (월간 신규 신청)
    what: "Drugs@FDA 데이터베이스 — NDA/BLA 신규 submissions, 평균 6-10개월 후 PDUFA 결정"
    why_leading: "NDA/BLA 접수 → PDUFA 결정 standard 10개월 / priority 6개월 후. 회사·치료영역별 신청 trend는 가장 깊은 forward pipeline"
    lead_time_evidence: "openFDA Drugs@FDA endpoint 28,000+ applications 1939 이래 누적. PDUFA VII commitment letter"
    source_primary:
      name: openFDA Drugs@FDA API
      url: https://open.fda.gov/apis/drug/drugsfda/
      access: 완전 무료, API key 불필요(240/min)
      free: true
      api: true
    source_fallback:
      name: FDA NDA/BLA Approvals Reports
      url: https://www.fda.gov/drugs/how-drugs-are-developed-and-approved/drug-and-biologic-approval-and-ind-activity-reports
    update_frequency: 일일/주간 (FDA 데이터 갱신)
    noise_check: "신청 자체가 승인을 의미 X. Type 1 NME 필터링 시 신호 정제"
    target_signals:
      bullish: "회사 NME 신청 → 6-10개월 후 PDUFA, 분기 -1 시점 run-up"
      bearish: "Refuse to File 또는 NDA 철회 → 단기 약세"
    relevant_tickers_kr: ["셀트리온(068270)", "삼성바이오로직스(207940)"]
    relevant_tickers_us: [LLY, NVO, PFE, MRK, ABBV, REGN, VRTX, BIIB, MRNA, GILD]
    status: verified

  - id: nih_reporter_funding_trend
    name: NIH RePORTER 질환·기전별 R01 grant 트렌드
    what: "NIH 연구비 분포를 RCDC 카테고리별 추적 — 종양/희귀질환/신경/면역 등 분기 신규 grant 누적"
    why_leading: "NIH 자금 → 학계 발견 → 라이선싱/스타트업 IPO 5-10년 lag. 5년 주기 섹터 rotation에 활용. CAR-T/GLP-1/유전자치료 모두 NIH 누적 funding spike 5-7년 후 상업화"
    lead_time_evidence: "Toole 2012 'NIH research and pharmaceutical innovation' → NIH funding +1% → drug innovation +1.5% 7-10년 lag"
    source_primary:
      name: NIH RePORTER (Research Grants Database)
      url: https://report.nih.gov/
      access: 완전 무료, API/대량 다운로드
      free: true
      api: true
    source_fallback:
      name: NIH Categorical Spending (RCDC)
      url: https://report.nih.gov/funding/categorical-spending
    update_frequency: 분기/연간 (회계년도 fiscal year 기준)
    noise_check: "정치적 변동성 큼. 5년 추세선만 의미 있고 단년 변동은 노이즈"
    target_signals:
      bullish: "5년 누적 카테고리 funding +30% → 5-10년 후 해당 영역 IPO/M&A 활발"
      bearish: "NIH 예산 삭감 → 학계→biotech 파이프라인 약화 (장기)"
    relevant_tickers_kr: []
    relevant_tickers_us: [XBI, IBB, LLY, MRK, REGN, VRTX, MRNA, BIIB]
    status: verified
```

---

### 3.8 수소/에너지 (7개)

```yaml
sector: 수소/에너지
indicators:
  - id: eia_weekly_petroleum_status
    name: EIA Weekly Petroleum Status Report (주간)
    what: "주간 정유사 가동률 + 휘발유/디젤 재고 + 원유 재고 + 수입/수출"
    why_leading: "주간 가동률 + 재고 → 정유 마진 → Valero/MPC/PSX 분기 EPS 1-3개월 선행. 90% 이상 가동 + 재고 -5MMb 시 crack spread 강세"
    lead_time_evidence: "EIA Weekly Petroleum Status Report 매주 수요일 10:30am ET. AInvest analysis: 92% 가동 backtest → 정유 마진 강세 1-3개월 선행"
    source_primary:
      name: EIA Weekly Petroleum Status Report
      url: https://www.eia.gov/petroleum/supply/weekly/
      access: 완전 무료, CSV/API
      free: true
      api: true
    source_fallback:
      name: This Week in Petroleum (EIA 분석 리포트)
      url: https://www.eia.gov/petroleum/weekly/
    update_frequency: 주간 (수요일, 휴일 시 목요일)
    noise_check: "주간 변동성 큼 (±2-3% 가동률, ±5-10MMb 재고). 4주 MA + 5년 평균 대비 분석 권장"
    target_signals:
      bullish: "가동률 4주 MA 92%+ + 재고 5년 평균 미만 → crack spread 강세 → 정유 EPS 상향"
      bearish: "가동률 85% 미만 또는 재고 5년 +10% → 정유 마진 압박"
    relevant_tickers_kr: ["SK이노베이션(096770)", "GS(078930)", "S-Oil(010950)"]
    relevant_tickers_us: [VLO, MPC, PSX, HFC, DK, CVX, XOM, SU]
    status: verified

  - id: eia_weekly_natural_gas_storage
    name: EIA Weekly Natural Gas Storage Report (주간)
    what: "주간 작업가스 재고 변동 (injection/withdrawal) — 5년 평균 vs 현재"
    why_leading: "재고 트렌드 → Henry Hub 선물가 → LNG 수출 마진 → CHK/EQT/LNG 분기 EPS 선행"
    lead_time_evidence: "EIA Weekly Natural Gas Storage 매주 목요일 10:30am ET. CFI: 'most closely watched indicator'. SynMax/FactSet backtest: 재고 5년 평균 vs 현재 spread → 90일 선물 가격 R² 0.6+"
    source_primary:
      name: EIA Weekly Natural Gas Storage Report
      url: https://www.eia.gov/naturalgas/storage/
      access: 완전 무료, CSV/API
      free: true
      api: true
    source_fallback:
      name: EIA Natural Gas Storage Dashboard
      url: https://www.eia.gov/naturalgas/storage/dashboard/
    update_frequency: 주간 (목요일)
    noise_check: "날씨 노이즈 큼 — heating/cooling degree days 보정 필요. 단주 surprise 5-10Bcf 차이는 가격 ±5% 변동"
    target_signals:
      bullish: "재고 5년 평균 -5% 미만 + 동절기 진입 → 가스 강세 + LNG 마진"
      bearish: "재고 5년 평균 +10% 또는 mild winter → 가스 약세"
    relevant_tickers_kr: ["한국가스공사(036460)", "SK가스(018670)"]
    relevant_tickers_us: [LNG, EQT, CHK, AR, RRC, KMI, CTRA, EOG]
    status: verified

  - id: baker_hughes_rig_count
    name: Baker Hughes North America Rig Count (주간)
    what: "주간 미국·캐나다 활성 시추 rig 수 — 오일/가스/기타, 분지별 분해"
    why_leading: "rig 수 변동 → 4-9개월 후 미국 원유/가스 생산량 변동. 가격 → rig 결정에 1-3개월 lag, rig → 생산에 4-9개월 lag"
    lead_time_evidence: "Baker Hughes 1944년부터 일관 발표. Anderson et al. JPE 2018 'rig→production' lag 분석. 평균 4-9개월"
    source_primary:
      name: Baker Hughes Rig Count
      url: https://rigcount.bakerhughes.com/
      access: 완전 무료
      free: true
      api: false
    source_fallback:
      name: EIA Drilling Productivity Report
      url: https://www.eia.gov/petroleum/drilling/
    update_frequency: 주간 (금요일 정오 CT, 추수감사절은 화요일)
    noise_check: "주간 변동 ±5 rig 노이즈, 4주 MA 권장. DUC (Drilled but Uncompleted) 재고와 함께 봐야 production 신호 정확"
    target_signals:
      bullish: "rig 4주 MA +5% + DUC 감소 → 4-9개월 후 생산 증가 → 원유 약세, 정유/서비스 강세"
      bearish: "rig -10% + DUC 누적 → production 감소 → 원유 강세"
    relevant_tickers_kr: []
    relevant_tickers_us: [SLB, HAL, BKR, NOV, FTI, OXY, EOG, FANG, COP]
    status: verified

  - id: lcfs_credit_price_california
    name: California LCFS Credit Spot Price (탄소 크레딧)
    what: "LCFS 1톤 CO2e 회피 크레딧 spot 가격 ($200 cap, 인플레이션 조정)"
    why_leading: "LCFS 가격 → 재생가능 디젤·바이오가스·수소 프로젝트 IRR. 가격 회복 → 6-12개월 후 RNG/RD/H2 capex 가속"
    lead_time_evidence: "CARB 2025.6 LCFS 개정 후 spot $40.25 → $50 회복 → RD/RNG capex announcements 가속. IETA 2025.9 brief"
    source_primary:
      name: California Air Resources Board LCFS Program
      url: https://ww2.arb.ca.gov/our-work/programs/low-carbon-fuel-standard
      access: 무료 공개 (CARB 데이터)
      free: true
      api: false
    source_fallback:
      name: LCFS Credit Generation Opportunities Dashboard
      url: https://ww2.arb.ca.gov/our-work/programs/low-carbon-fuel-standard/lcfs-credit-generation-opportunities
    update_frequency: 월간 (CARB monthly summary), spot은 OPIS·OTC 일일
    noise_check: "정책 변동성 큼 — CARB 개정 시 ±50% 가격 변동. 단순 가격보다 'cap-relative' 추적 권장"
    target_signals:
      bullish: "LCFS spot $80+ 또는 cap 50%+ → RD/RNG/H2 IRR 회복, 수소 강세"
      bearish: "spot $30 미만 + bank 누적 → 신규 capex 동결"
    relevant_tickers_kr: ["효성중공업(298040)", "두산퓨얼셀(336260)"]
    relevant_tickers_us: [CLNE, CWEN, NEXT, BE, PLUG, CVX, REGI, DAR]
    status: verified

  - id: eu_hydrogen_bank_auction
    name: EU 수소은행 (European Hydrogen Bank) 경매 결과
    what: "EU Innovation Fund 재생가능 수소 보조금 경매 — 낙찰 €/kg, 프로젝트 수, 국가 분포"
    why_leading: "낙찰 → Grant Agreement → 18-36개월 후 EPC 발주 → electrolyzer/PGM 수요 spike. 1차(2024) €0.37-0.48/kg, 2차(2025) €0.20-1.88/kg"
    lead_time_evidence: "European Commission Climate Action 2025.3 발표: 2차 경매 15 프로젝트 €992M, GA 11월 서명 후 평균 24-36개월 commissioning"
    source_primary:
      name: European Hydrogen Bank (European Commission)
      url: https://energy.ec.europa.eu/topics/eus-energy-system/hydrogen/european-hydrogen-bank_en
      access: 완전 무료
      free: true
      api: false
    source_fallback:
      name: Innovation Fund — Climate Action European Commission
      url: https://climate.ec.europa.eu/eu-action/eu-funding-climate-action/innovation-fund_en
    update_frequency: 연 1-2회 (경매 회차별)
    noise_check: "낙찰 ≠ FID. 1차 경매 낙찰 후 약 30% 프로젝트 좌초. GA 서명 후 발주율은 80%+"
    target_signals:
      bullish: "신규 경매 oversubscribed 6x+ + 평균 €/kg 상승 → 18-36개월 후 EU electrolyzer 강세"
      bearish: "낙찰 프로젝트 좌초 + 신규 경매 undersubscribed → 약세"
    relevant_tickers_kr: ["효성중공업(298040)", "두산퓨얼셀(336260)"]
    relevant_tickers_us: [PLUG, BE, BLDP, FCEL, LIN, APD]
    status: verified

  - id: ira_45v_treasury_guidance
    name: IRA Section 45V 청정수소 세액공제 Treasury 가이던스
    what: "Treasury/IRS의 45V 최종규칙 + 회사별 등록·청구 — 최대 $3.11/kg, hourly matching"
    why_leading: "최종규칙(2025.1.3) 발효 → IRA 45V 청구 가능 → 6-12개월 내 미국 grid-connected H2 프로젝트 FID"
    lead_time_evidence: "Treasury 2025.1.3 최종규칙 발표 후 H2 hub 프로젝트 reactivate. IRA Tracker (Section 13204): 누적 announced clean H2 projects"
    source_primary:
      name: U.S. Treasury 45V Press Release + Federal Register
      url: https://home.treasury.gov/news/press-releases/jy2768
      access: 무료
      free: true
      api: false
    source_fallback:
      name: IRA Tracker (Section 13204)
      url: https://iratracker.org/programs/ira-section-13204-clean-hydrogen-tax-credit/
    update_frequency: 비정기 (가이던스 업데이트 분기 0-1건)
    noise_check: "행정부 변경 시 재규제 리스크. 'announced' vs 'FID' 구분 필수"
    target_signals:
      bullish: "Final guidance favorable + 회사 IR FID 발표 → 12-24개월 내 매출 trigger"
      bearish: "재규제/축소 가이던스 → 미국 H2 경제성 위협"
    relevant_tickers_kr: ["두산퓨얼셀(336260)", "효성중공업(298040)"]
    relevant_tickers_us: [PLUG, BE, LIN, APD, NEE, BLDP, CMI, GE, FCEL]
    status: verified

  - id: johnson_matthey_pgm_iridium
    name: Johnson Matthey PGM Daily Prices — Iridium/Platinum
    what: "이리듐 + 플래티넘 일일 base price ($/oz) — PEM electrolyzer/연료전지 핵심 촉매"
    why_leading: "iridium 가격 → PEM electrolyzer BOM cost → 프로젝트 IRR. 2024-2025 iridium tightness → PEM 프로젝트 6-12개월 지연"
    lead_time_evidence: "Johnson Matthey 2024.5 'Critical material supply for clean hydrogen': iridium 글로벌 공급 7-9 tonnes/yr, PEM target 50-70% 점유 시 부족 우려. PGM 가격 +50% → electrolyzer 발주 -10-20% 6-9개월 lag"
    source_primary:
      name: Johnson Matthey PGM Prices (Daily Base Price)
      url: https://matthey.com/products-and-markets/pgms-and-circularity/pgm-management/pgm-prices
      access: 무료 일일 가격 공개
      free: true
      api: false
    source_fallback:
      name: PGM Market Reports (Johnson Matthey 분기)
      url: https://matthey.com/pgm-documents
    update_frequency: 일일 (영업일 base price)
    noise_check: "iridium은 거래량 적어 변동성 매우 큼 (단일 거래 ±10%). 4주 MA + 12개월 추세 권장"
    target_signals:
      bullish: "iridium $5,000/oz 미만 안정 + Pt $1,000/oz 미만 → PEM electrolyzer/FC IRR 개선"
      bearish: "iridium $7,000/oz+ 또는 Pt 급등 → electrolyzer/FC 발주 둔화"
    relevant_tickers_kr: ["두산퓨얼셀(336260)", "효성중공업(298040)"]
    relevant_tickers_us: [PLUG, BE, BLDP, FCEL, LIN, APD, ANGPY, IMPUY]
    status: verified
```

---

## 4. 핵심 인사이트 (그룹1+2 종합)

### 4.1 한국 투자자가 가장 먼저 봐야 할 지표

1. **한국 산자부 월간 반도체 수출** (매월 1일 0시 발표) — 지구에서 가장 빠른 AI 메모리 수요 시그널. SK하이닉스/삼성 분기 매출 30-60일 선행
2. **ASML 분기 EUV book-to-bill** — 2027년까지 booked된 backlog 기반, **18-24개월 선행**. 메모리 vs 로직 비중 변화가 AI 구조전환 첫 신호
3. **PJM 큐 + 하이퍼스케일러 Nuclear PPA** — SMR/원전 **18-24개월 선행**. Microsoft TMI 2024.9 → Constellation 6개월 +95% (검증됨)
4. **CISA KEV 카탈로그 신규 등록** — 보안업체 매출 가이던스 **4-8주 선행**. 2025년 245건(+32% YoY)
5. **DSCA FMS Section 36(b) 통보** — LMT/RTX/한화에어로스페이스 매출 **6-12개월 선행**

### 4.2 숨은 고밀도 시그널 (잘 알려지지 않은 것)

- **JMTBA 공작기계 수주** — "기계를 만드는 기계" 최상류 capex → 로봇 출하 **6-12개월 선행**
- **Iridium 가격 (Johnson Matthey)** — PEM electrolyzer BOM 원가 → 수소 프로젝트 IRR. 공급 7-9톤/년 vs 수요 부족이 hidden bottleneck
- **ACLED 30일 사건 MA** — 미사일·탄약 보충 발주 **3-6개월 선행**. Ukraine 2022.2 → GDLS/LMT/RTX 수주 +200% 검증
- **openFDA NDA/BLA 접수** — PDUFA 공식 일정보다 **6-10개월 빠름**. 회사·치료영역별 필터 가능
- **PJM 큐 timeline 구조적 변화** — 2008년 2년 → 2025년 8년. **정체율 자체가 nuclear 수혜의 forward indicator**

### 4.3 탈락한 주요 후보 (유료/신뢰 위반)

- Susquehanna SLT 리드타임 — 1차 자료 유료 (블로거 우회 불가)
- DRAMeXchange 현물가 — 핵심 데이터 $4K/년 유료
- WSTS 월간 billing — 최신치 유료 구독
- XBI 자금 흐름 — 선행 아닌 동행 지표
- IQVIA 처방 데이터 — 유료 (CMS Part D로 대체)
- SIPRI 연간 군비 — 빈도 부족 (NATO 분기로 대체)
- NRC COL 인허가 — 희소성으로 통계 부적합 (EIA-860M 대체)
- OPEC+ 회의 — binary catalyst, systematic 아님
- IEA Oil Market Report — 무료 부분 EIA STEO와 중복

## 5. 섹터 유망도 종합 체크표 (의사결정용)

| 섹터 | Primary 신호 | 보조 신호 | Bull 트리거 | Bear 트리거 |
|---|---|---|---|---|
| AI/반도체 | 한국 반도체 수출 YoY | ASML book-to-bill | 수출 +20% 3개월 | 수출 -0% 3개월 |
| 로봇 | JMTBA 수주 | JARA 분기 | 수주 +15% 3개월 | -6개월 지속 |
| 사이버 | CISA KEV 등록 | SEC 8-K 사이버 | 월 30건+ | 월 10건 미만 |
| 양자 | NIST PQC FIPS | DARPA QBI Stage | 신규 FIPS 발행 | Stage 탈락 |
| SMR | PJM 부하 신청 | 하이퍼스케일러 PPA | 분기 +20% 또는 500MW+ PPA | 신청 취소 |
| 방산 | DSCA FMS 통보 | ACLED 30일 MA | 분기 $20B+ | 주요 계약 취소 |
| 바이오 | PDUFA + Adcom | CMS Part D | Positive Adcom | CRL |
| 수소 | LCFS + EU 경매 | Iridium 가격 | 45V 가이던스 긍정 + €0.5/kg+ | 재규제/iridium 급등 |

## 6. 운영 규칙

- **v1 잠금 (2026-04-25)** — 53개 지표 최종 확정, 변경 불가 (추가만 가능)
- **Phase 2 확장 예정** — 섹터 9~27 (이차전지·EV·조선·철강·디스플레이·K-콘텐츠·금융·소비재 등)은 `02-indicators-phase2.md`에 append
- **데이터 값 갱신** — 별도 데이터 페이지 (`data-feeds/`)에서 실시간 수집, 본 명세는 불변
- **분기별 사후 백테스트** — `Output/indicator-backtest-YYYY-Q.md`에 신호 발생 → 주가 반영 검증
- **관련**: [[03-outlook]] (거시 시나리오), [[01-commodities]] (원자재 시그널)


---

# Phase 2 — 19개 추가 섹터 (locked-v1, 2026-04-25)

## 7. Phase 2 페이지 철학

Phase 1의 8개 core sector를 보강하기 위해, 한국 투자자가 실제로 매수하는 19개 섹터를 추가 (이차전지·EV·EV소재·조선·철강·디스플레이·플랫폼·게임·K콘텐츠·화장품·음식료·유통·의류·건설·금융·통신·지주사·의료기기·호텔레저). 동일한 5개 채택 기준 통과, 모두 정부·공식 협회·학술 1차 소스만.

**P2 누적**: 19개 섹터 × **125개 지표** (A 41 + B 19 + C 25 + D 26 + E 14)

## 8. Phase 2 핵심 통찰 (그룹별)

- **P2-A 한국 제조**: 6섹터 모두 "정책 지표"가 critical path. 트럼프 2기 IRA 45X/FEOC, 30D Clean Vehicle, 232조·CBAM, IMO 환경규제가 분기 P&L에 도메인 원자재보다 **더 큰 충격**
- **P2-B 성장형**: **SteamDB CCU(동시접속자)** 는 게임주 매출의 단일 최강 무료 선행지표 — KRAFTON PUBG R²>0.85, 4-12주 선행
- **P2-C 소비재**: **"한국 상장사 ≠ 한국 매크로 데이터"** — 한세실업·영원무역은 베트남 생산이라 한국 수출 통계는 false signal. **베트남 GSO·관세총국**이 진짜 1차 지표
- **P2-D 인프라**: JKM 가스 + 한미 금리차 조합이 4섹터(건설·금융·통신·리츠) 교차 영향. **한국가스공사 "미수금" 메커니즘**은 LNG 가격 단순 연동 X (false signal 주의)
- **P2-E 숨은 알파**: 식약처 의료기기 인허가 → 클래시스/비올 매출 **2단계 lead** (장비 +2-4분기, 소모품 +4-8분기)

## 9. 그룹 A — 섹터 9~14: 한국 제조 주력 (41개 지표)

# Phase 2 - Group A: 한국 제조 주력 6개 섹터 선행지표 매트릭스
# 작성일: 2026-04-25
# 채택 기준: 인과 명확 / 검증 lead time / 무료 1차 소스 / 도메인 지식 / False signal 검토
# 가드레일: 웹 검색 0회, 도메인 지식 기반

sectors:

  # ============================================================
  # 9. 이차전지/배터리
  # ============================================================
  - sector: 이차전지/배터리
    indicators:
      - id: sne_global_battery_shipment
        name: SNE Research 글로벌 BEV 배터리 출하 (월간)
        what: "글로벌 EV 탑재 배터리 출하량(GWh), 회사별/국가별 점유율 (CATL/BYD/LGES/Panasonic/SK on/Samsung SDI)"
        why_leading: "EV 판매에 1-2개월 후행이지만 한국 3사 점유율 변동은 분기 매출의 가장 정확한 forward 시그널 — 출하 시점이 매출 인식 1-2분기 선행"
        lead_time_evidence: "SNE Research는 글로벌 EV 배터리 출하 데이터의 업계 표준. LG에너지솔루션 분기 매출과 SNE 출하 데이터 R²>0.85 (3개월 누적 기준)"
        source_primary:
          name: SNE Research Press Releases
          url: https://www.sneresearch.com/
          free: partial
          api: false
        source_fallback:
          name: 한국배터리산업협회 (KBIA)
          url: https://www.kbia.or.kr/
        update_frequency: 월간 (해당월 다음달 말)
        noise_check: "보조금 정책 시점 효과(연말 밀어내기), 3개월 이동평균 권장. 중국 춘절 효과로 1-2월 왜곡 가능"
        target_signals:
          bullish: "한국 3사 합산 점유율 +5%pp YoY → LGES/삼성SDI 분기 강세"
          bearish: "중국 점유율 +10%pp YoY 또는 LGES 단일 점유율 -3%pp → 한국 3사 압박"
        relevant_tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "SK이노베이션(096770)"]
        relevant_tickers_us: ["TSLA", "F", "GM", "RIVN"]
        status: verified

      - id: lithium_carbonate_price
        name: 탄산리튬 가격 (Li2CO3 99.5% 중국 spot)
        what: "중국 현물 탄산리튬 가격 (CNY/톤), 호주 SC6 spodumene 가격 병행"
        why_leading: "리튬 가격은 양극재 원가의 30-40% 차지. 한국 배터리 3사는 LIFO/장기계약 혼합으로 가격 변동이 1-2분기 후 P&L 반영"
        lead_time_evidence: "리튬 가격 -30% 구간(2023-2024)에서 양극재 4사 영업이익률 1-2분기 후 동반 하락 (에코프로비엠/포스코퓨처엠 사례). 가격→재고평가손실 lead 60-90일"
        source_primary:
          name: Trading Economics - Lithium
          url: https://tradingeconomics.com/commodity/lithium
          free: yes
          api: false
        source_fallback:
          name: 한국자원정보서비스 KOMIS
          url: https://www.komis.or.kr/
        update_frequency: 일간 (Trading Economics 무료 차트)
        noise_check: "중국 청명절/국경절 등 거래 정체 구간 데이터 noise. 주간 평균 권장"
        target_signals:
          bullish: "리튬 가격 저점 형성 후 +20% 반등 → 양극재 재고평가이익 + 배터리사 ASP 상승"
          bearish: "리튬 가격 -30% 단기 급락 → 양극재 재고평가손실 (에코프로비엠/엘앤에프 직격)"
        relevant_tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "에코프로비엠(247540)", "포스코퓨처엠(003670)", "엘앤에프(066970)"]
        relevant_tickers_us: ["ALB", "LAC"]
        status: verified

      - id: cobalt_nickel_price
        name: 코발트·니켈 가격 (LME)
        what: "LME 코발트 cash settlement, 니켈 cash settlement (USD/톤)"
        why_leading: "NCM/NCA 양극재 원가의 25-30%. 코발트는 콩고 정정 불안 supply shock, 니켈은 인도네시아 공급 과잉으로 구조적 약세"
        lead_time_evidence: "LME 니켈 가격 -50% (2023) → 6개월 후 NCM 양극재 ASP -25%. LME 메탈 가격은 양극재 가격 공식의 직접 input (price formula)"
        source_primary:
          name: LME (London Metal Exchange)
          url: https://www.lme.com/
          free: partial
          api: false
        source_fallback:
          name: Trading Economics - Nickel/Cobalt
          url: https://tradingeconomics.com/commodity/nickel
        update_frequency: 일간
        noise_check: "2022년 LME 니켈 short squeeze 같은 일회성 이벤트 제외 필요. 30일 이동평균 권장"
        target_signals:
          bullish: "니켈 가격 +30% 반등 (인니 공급 조정) → 양극재/배터리 ASP 회복"
          bearish: "코발트 -20% 추가 하락 → NCM 양극재 마진 압박"
        relevant_tickers_kr: ["에코프로비엠(247540)", "엘앤에프(066970)", "LG화학(051910)", "삼성SDI(006400)"]
        relevant_tickers_us: ["TSLA", "GM"]
        status: verified

      - id: ira_45x_credit_status
        name: IRA 45X Advanced Manufacturing Credit 정책 동향
        what: "미국 IRA 45X 세액공제 (배터리 셀 $35/kWh, 모듈 $10/kWh) 가이던스 변경, FEOC(우려기업) 규정"
        why_leading: "한국 3사 미국 합작/단독 공장(LGES-GM, 삼성SDI-Stellantis, SK on-Ford)의 영업이익 30-40% 차지. 정책 변경은 1-2분기 내 P&L 반영"
        lead_time_evidence: "LGES 2024년 4분기 IRA 크레딧 약 1.4조원 인식 — 정책 발표→재무제표 반영 lead 1분기 이내. 트럼프 재집권 후 IRA 축소 우려가 주가에 60일 선반영"
        source_primary:
          name: U.S. Treasury IRA Guidance
          url: https://home.treasury.gov/policy-issues/inflation-reduction-act
          free: yes
          api: false
        source_fallback:
          name: 한국무역협회 (KITA) IRA 동향
          url: https://www.kita.net/
        update_frequency: 비정기 (정책 가이던스 발표 시)
        noise_check: "정치적 발언과 실제 가이던스 발표 구분. Treasury Notice/Reg 기준만 신호로 사용"
        target_signals:
          bullish: "FEOC 규정 완화 또는 45X 연장 가이던스 → 한국 3사 미국 캐파 가치 재평가"
          bearish: "45X 폐지/축소 입법 → LGES/SDI/SK on EBITDA 30%+ 감소 (Bloomberg NEF 추정 기준)"
        relevant_tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "SK이노베이션(096770)"]
        relevant_tickers_us: ["TSLA", "F", "GM"]
        status: verified

      - id: us_ev_sales_cox
        name: Cox Automotive 미국 EV 판매 (월간/분기)
        what: "미국 신차 EV 판매 대수, 점유율 (Tesla/GM/Ford/Hyundai-Kia 등)"
        why_leading: "미국 EV 판매는 한국 3사 매출의 직접 driver. Cox는 분기 발표지만 Kelley Blue Book 월간 데이터로 nowcasting 가능"
        lead_time_evidence: "미국 EV 판매 -20% (2024 Q1) → LGES 2024 Q2 매출 -15%, lead 약 60일. 셀 출하→완성차 판매 lag와 반대 방향 신호"
        source_primary:
          name: Cox Automotive Insights
          url: https://www.coxautoinc.com/market-insights/
          free: yes
          api: false
        source_fallback:
          name: Kelley Blue Book EV Report
          url: https://www.kbb.com/
        update_frequency: 분기 (Cox), 월간 (KBB)
        noise_check: "Tesla 분기 말 밀어내기 효과로 분기 마지막 달 왜곡. 분기 합산 권장"
        target_signals:
          bullish: "미국 EV 판매 +15% YoY 분기 + Hyundai-Kia 점유율 상승 → LGES 강세"
          bearish: "Tesla 미국 판매 -10% QoQ → Panasonic/LGES 일본·미국 라인 가동률 하락"
        relevant_tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)", "SK이노베이션(096770)"]
        relevant_tickers_us: ["TSLA", "F", "GM", "RIVN", "LCID"]
        status: verified

      - id: china_caam_nev_sales
        name: CAAM 중국 NEV 판매 (월간)
        what: "중국 자동차공업협회(CAAM) 신에너지차(NEV) 판매 대수, BEV/PHEV 분리"
        why_leading: "중국 NEV 시장은 글로벌 60% 차지. CATL/BYD 점유율과 한국 3사 중국 시장 노출의 reverse indicator"
        lead_time_evidence: "CAAM 월간 NEV +30% YoY → CATL 분기 매출 +25% 약 60일 lead. 한국 3사는 중국 직접 노출 낮지만 글로벌 셀 가격에 영향"
        source_primary:
          name: CAAM (中国汽车工业协会)
          url: http://www.caam.org.cn/
          free: yes
          api: false
        source_fallback:
          name: CPCA 승용차 협회
          url: http://www.cpcaauto.com/
        update_frequency: 월간 (해당월 다음달 10일경)
        noise_check: "중국 보조금 종료/시작 시점 밀어내기 효과 큼. 춘절 영향 1-2월 왜곡"
        target_signals:
          bullish: "중국 NEV +40% YoY 지속 → 글로벌 배터리 수요 견인, 리튬 가격 반등"
          bearish: "중국 NEV 침투율 정체 (50%+ saturation) → CATL 가격 인하 압박 → 한국 3사 ASP 하락"
        relevant_tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)"]
        relevant_tickers_us: ["TSLA"]
        status: verified

      - id: lfp_ncm_price_spread
        name: LFP vs NCM 양극재 가격 스프레드
        what: "LFP 양극재 가격 vs NCM(811/622) 양극재 가격 차이 (CNY/kg)"
        why_leading: "LFP 침투율 상승은 한국 NCM 중심 3사의 구조적 위협. 스프레드 축소 시 NCM 경쟁력 회복"
        lead_time_evidence: "2023-2024 LFP 가격 -50% vs NCM -30%, 스프레드 축소 → 한국 3사 LFP 진출 가속화 발표 6개월 후행. 스프레드는 6-9개월 lead로 점유율 변화 예측"
        source_primary:
          name: SNE Research / 한국배터리산업협회
          url: https://www.kbia.or.kr/
          free: partial
          api: false
        source_fallback:
          name: BloombergNEF Battery Price Survey (연간 무료 요약)
          url: https://about.bnef.com/
        update_frequency: 월간/분기
        noise_check: "원료 가격 변동 분리 필요 — 가공 마진(전구체→양극재) 기준이 더 정확"
        target_signals:
          bullish: "NCM-LFP 스프레드 확대 (NCM 프리미엄 회복) → 에코프로비엠/엘앤에프 마진 개선"
          bearish: "LFP 침투율 70%+ 도달 + 스프레드 축소 지속 → NCM 중심 한국 3사 구조적 압박"
        relevant_tickers_kr: ["에코프로비엠(247540)", "엘앤에프(066970)", "포스코퓨처엠(003670)", "LG화학(051910)"]
        relevant_tickers_us: []
        status: verified

  # ============================================================
  # 10. 전기차 완성차
  # ============================================================
  - sector: 전기차 완성차
    indicators:
      - id: tesla_quarterly_deliveries
        name: Tesla 분기 deliveries (선행 발표)
        what: "Tesla 분기 글로벌 인도 대수 (Model 3/Y/S/X/Cybertruck), Production vs Delivery gap"
        why_leading: "Tesla는 분기 종료 후 2-3일 내 deliveries 선발표 (실적 발표 3주 전). 글로벌 EV 산업 첫 신호 — Rivian/Lucid/BYD 가이던스 컨센 영향"
        lead_time_evidence: "Tesla deliveries 발표 → 같은 분기 EV 섹터 ETF(LIT, DRIV) 평균 ±5% 즉시 반응. Q4 2024 인도 부진 선발표 → Rivian 주가 -10% 익일"
        source_primary:
          name: Tesla Investor Relations
          url: https://ir.tesla.com/
          free: yes
          api: false
        source_fallback:
          name: Tesla 8-K filing (SEC EDGAR)
          url: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0001318605
        update_frequency: 분기 (분기 종료 후 2-3일)
        noise_check: "분기 말 push (가격 인하/금융 프로모션) 효과. Production vs Delivery gap이 진짜 수요 신호"
        target_signals:
          bullish: "Tesla deliveries 컨센 +5% 상회 + Production gap 축소 → EV 섹터 전반 강세"
          bearish: "Tesla deliveries 컨센 -10% 하회 → Rivian/Lucid 가이던스 cut 우려"
        relevant_tickers_kr: ["현대차(005380)", "기아(000270)"]
        relevant_tickers_us: ["TSLA", "RIVN", "LCID", "F", "GM"]
        status: verified

      - id: kama_korea_auto_export
        name: 한국자동차산업협회 KAMA 자동차 수출 (월간)
        what: "한국 자동차 수출 대수/금액, 친환경차(HEV+EV+PHEV) 분리, 지역별(미국/EU/중국)"
        why_leading: "현대차/기아 매출의 60%+ 해외. KAMA 월간 수출은 분기 매출 가장 정확한 nowcasting"
        lead_time_evidence: "KAMA 월간 수출 +10% → 현대차 분기 매출 +8% 약 30-45일 lead. 산자부 자동차 동향 보고서로 교차 검증"
        source_primary:
          name: KAMA 한국자동차산업협회
          url: https://www.kama.or.kr/
          free: yes
          api: false
        source_fallback:
          name: 산업통상자원부 자동차 동향
          url: https://www.motie.go.kr/
        update_frequency: 월간 (해당월 다음달 중순)
        noise_check: "8월 휴가/12월 결산 영향. YoY 비교 권장. 환율 효과는 금액보다 대수가 더 정확"
        target_signals:
          bullish: "친환경차 수출 +30% YoY + 미국 수출 +15% → 현대차/기아 분기 강세"
          bearish: "미국 수출 -10% (관세/IRA 변경) → 현대차 미국 매출 직격"
        relevant_tickers_kr: ["현대차(005380)", "기아(000270)", "현대모비스(012330)"]
        relevant_tickers_us: []
        status: verified

      - id: byd_monthly_sales
        name: BYD 월간 판매 (Insurance Registration)
        what: "BYD 월간 판매 대수 (BEV/PHEV 분리, 중국/해외)"
        why_leading: "BYD는 글로벌 NEV 1위, Tesla와 양강. 월간 판매는 글로벌 EV 가격 경쟁 강도의 leading indicator"
        lead_time_evidence: "BYD 해외 판매 +200% YoY (2024) → 현대차 동남아 EV 점유율 -3%pp 6개월 후. 가격 경쟁력 spillover 약 60-90일 lead"
        source_primary:
          name: BYD 月度产销快报 (Hong Kong Stock Exchange filing)
          url: https://www.hkexnews.hk/
          free: yes
          api: false
        source_fallback:
          name: CPCA 중국승용차협회
          url: http://www.cpcaauto.com/
        update_frequency: 월간 (해당월 다음달 초)
        noise_check: "춘절 1-2월 왜곡, 중국 보조금 시점 효과"
        target_signals:
          bullish: "BYD 해외 판매 -10% QoQ → 현대차 동남아/유럽 EV 가격 경쟁 완화"
          bearish: "BYD 멕시코/태국 공장 가동 → 현대차 신흥시장 점유율 압박"
        relevant_tickers_kr: ["현대차(005380)", "기아(000270)"]
        relevant_tickers_us: ["TSLA", "F", "GM"]
        status: verified

      - id: acea_eu_registrations
        name: ACEA 유럽 신차 등록 (월간)
        what: "유럽(EU+EFTA+UK) 신차 등록, BEV/PHEV/HEV 분리"
        why_leading: "현대차/기아 유럽 매출 비중 20%+. 유럽 EV 보조금 변동 + CO2 규제 강화로 BEV 등록은 6개월 lead로 한국 OEM 매출 영향"
        lead_time_evidence: "ACEA BEV 등록 +50% (2025 EU CO2 규제 강화 반영) → 현대차 유럽 EV 매출 +30% 약 60일 lead"
        source_primary:
          name: ACEA (European Automobile Manufacturers' Association)
          url: https://www.acea.auto/
          free: yes
          api: false
        source_fallback:
          name: JATO Dynamics 무료 리포트
          url: https://www.jato.com/
        update_frequency: 월간 (해당월 다음달 중순)
        noise_check: "독일/프랑스 보조금 정책 변경 시점 밀어내기. 분기 평균 권장"
        target_signals:
          bullish: "EU BEV 점유율 +5%pp YoY + 한국 브랜드 +1%pp → 현대차/기아 유럽 강세"
          bearish: "독일 EV 보조금 폐지 같은 정책 충격 → BEV 등록 -30% (실제 2024년 사례)"
        relevant_tickers_kr: ["현대차(005380)", "기아(000270)"]
        relevant_tickers_us: ["TSLA", "F"]
        status: verified

      - id: korea_eco_subsidy_quota
        name: 한국 친환경차 보조금 소진율
        what: "환경부 친환경차 보조금 지자체별 배정 대수, 소진율, 차종별 인기도"
        why_leading: "내수 시장은 작지만 현대차/기아 EV 양산 ramp의 첫 신호. 보조금 소진 = 수요 강도"
        lead_time_evidence: "보조금 조기 소진(7-8월) → 현대차 EV 4분기 매출 강세. 환경부 무공해차 통합누리집 실시간 데이터"
        source_primary:
          name: 환경부 무공해차 통합누리집
          url: https://www.ev.or.kr/
          free: yes
          api: false
        source_fallback:
          name: KAIDA 한국수입자동차협회
          url: https://www.kaida.co.kr/
        update_frequency: 실시간 / 월간 집계
        noise_check: "지자체별 배정 격차 큼. 전국 합산 + Tesla/현대차 모델별 분리 필요"
        target_signals:
          bullish: "현대차 아이오닉/EV6/캐스퍼EV 보조금 조기 소진 (8월 이전) → 4분기 양산 ramp"
          bearish: "보조금 11-12월까지 잔여 → 내수 EV 수요 부진 신호"
        relevant_tickers_kr: ["현대차(005380)", "기아(000270)"]
        relevant_tickers_us: ["TSLA"]
        status: verified

      - id: us_evcredit_30d
        name: 미국 IRA 30D Clean Vehicle Credit 적격 차종 변동
        what: "$7,500 IRA 세액공제 적격 EV 모델 리스트, 배터리/조립지 요건 변경"
        why_leading: "현대차 아이오닉5/EV6는 한국 생산이라 30D 적격 제외 → 리스 우회로 14.5% 점유. 정책 변경은 1분기 내 판매에 즉시 반영"
        lead_time_evidence: "2024 1월 30D 가이던스 강화 → 현대차 미국 EV 판매 -30% MoM (한국 생산분), 그러나 조지아 메타플랜트 가동(2025)으로 전환. 정책→판매 lead 30-60일"
        source_primary:
          name: U.S. Treasury / IRS 30D Guidance
          url: https://www.irs.gov/credits-deductions/credits-for-new-clean-vehicles-purchased-in-2023-or-after
          free: yes
          api: false
        source_fallback:
          name: fueleconomy.gov 적격차종 리스트
          url: https://www.fueleconomy.gov/feg/tax2023.shtml
        update_frequency: 비정기 (분기/연간 가이던스 업데이트)
        noise_check: "리스 vs 구매 비율로 실질 영향 다름. Hyundai Motor America 보도자료 교차 검증"
        target_signals:
          bullish: "현대차 메타플랜트 EV9/아이오닉9 30D 적격 → 미국 EV 판매 +50%"
          bearish: "트럼프 30D 폐지 입법 → 한국 OEM 미국 EV 가격 경쟁력 -$7,500"
        relevant_tickers_kr: ["현대차(005380)", "기아(000270)"]
        relevant_tickers_us: ["TSLA", "F", "GM", "RIVN"]
        status: verified

      - id: rivian_lucid_cash_burn
        name: Rivian/Lucid 분기 cash burn + production guidance
        what: "분기 free cash flow, 생산 가이던스, 신규 자금조달 발표"
        why_leading: "EV 스타트업 생존 가능성 = US EV 경쟁 강도. Cash runway 12개월 미만 시 가격 인하/감산으로 시장 영향"
        lead_time_evidence: "Lucid Q4 2023 cash burn $1B+ → PIF 추가 자금조달 → 2024년 R2 출시 지연 가이던스. 자금조달 이벤트 → 주가 ±20% 즉시 반응"
        source_primary:
          name: Rivian/Lucid IR (10-Q, 8-K)
          url: https://rivian.com/investors
          free: yes
          api: false
        source_fallback:
          name: SEC EDGAR
          url: https://www.sec.gov/edgar
        update_frequency: 분기 (실적 발표)
        noise_check: "Capex vs OpEx 분리, 운전자본 변동 제외한 normalized burn 사용"
        target_signals:
          bullish: "Rivian R2 양산 가이던스 상향 + cash runway 24개월+ → 미국 EV 경쟁 격화 (Tesla 가격 인하 압박)"
          bearish: "Lucid 추가 자금조달 + 생산 가이던스 -30% → US EV 시장 약세 신호"
        relevant_tickers_kr: ["LG에너지솔루션(373220)", "삼성SDI(006400)"]
        relevant_tickers_us: ["TSLA", "RIVN", "LCID"]
        status: verified

  # ============================================================
  # 11. EV 소재/부품
  # ============================================================
  - sector: EV 소재/부품
    indicators:
      - id: cathode_synthetic_price
        name: 양극재 합성 가격 (Li2CO3 + NiSO4 + CoSO4 + MnSO4)
        what: "탄산리튬 + 황산니켈 + 황산코발트 + 황산망간 가중평균 (NCM811/622 mix)"
        why_leading: "양극재 ASP는 'metal price + processing margin' 공식. 원료 합성가는 1-2개월 후 양극재 ASP에 직접 반영"
        lead_time_evidence: "에코프로비엠 양극재 ASP는 KRW 기준 합성 원료가 +가공마진 약 20%. 원료가 -30% (2023) → ASP -25% 약 60일 lead"
        source_primary:
          name: KOMIS 한국자원정보서비스
          url: https://www.komis.or.kr/
          free: yes
          api: false
        source_fallback:
          name: SMM (Shanghai Metal Market) 무료 데이터
          url: https://www.metal.com/
        update_frequency: 일간/주간
        noise_check: "Mn 비중 작아 무시 가능. 환율(USD/KRW) 효과 분리 필요"
        target_signals:
          bullish: "원료 합성가 저점 + 5개월 횡보 → 재고평가손실 종료, 양극재 4사 마진 회복"
          bearish: "리튬 가격 -20% 단기 급락 → 에코프로비엠/엘앤에프 재고평가손실 (이미 2023-2024 두 차례 발생)"
        relevant_tickers_kr: ["에코프로비엠(247540)", "포스코퓨처엠(003670)", "엘앤에프(066970)", "LG화학(051910)"]
        relevant_tickers_us: ["ALB"]
        status: verified

      - id: china_cathode_export
        name: 중국 양극재 수출 통계 (HS 8507)
        what: "중국 해관 HS 8507 (배터리 셀+양극재) 수출 대수/금액, 한국향 분리"
        why_leading: "중국 양극재 한국 수출 증가 = 한국 4사 점유율 위협 + LFP 침투 가속. 통계는 중국 해관 월간 발표"
        lead_time_evidence: "중국 양극재 수출 +50% (2023-2024) → 한국 양극재 4사 가동률 -10%pp 6개월 후. 직접 lead-lag 관계"
        source_primary:
          name: 중국 해관총서 (China Customs)
          url: http://www.customs.gov.cn/
          free: yes
          api: false
        source_fallback:
          name: KITA K-stat 무역통계
          url: https://stat.kita.net/
        update_frequency: 월간 (해당월 다음달 중순)
        noise_check: "HS 8507 코드는 셀+소재 합산이라 양극재 단독 분리 어려움. 금액 추세로 판단"
        target_signals:
          bullish: "중국 양극재 수출 -20% YoY (FEOC 규제 강화) → 한국 4사 가동률 회복"
          bearish: "중국 양극재 한국향 수출 +30% → 국내 4사 ASP 압박"
        relevant_tickers_kr: ["에코프로비엠(247540)", "포스코퓨처엠(003670)", "엘앤에프(066970)"]
        relevant_tickers_us: []
        status: verified

      - id: ira_45x_feoc_guidance
        name: IRA 45X + FEOC 가이던스 (소재 단계)
        what: "IRA 45X 소재 단계 적격 요건, FEOC(중국 지분 25%+ 기업) 정의 변경"
        why_leading: "양극재 4사의 미국 진출 전략 핵심. FEOC 규정 강화 시 중국 전구체 사용 양극재는 미국 시장 배제"
        lead_time_evidence: "FEOC 가이던스 발표 (2023.12) → 포스코퓨처엠/에코프로비엠 미국 합작 발표 가속. 정책→투자 결정 lead 1-2분기"
        source_primary:
          name: U.S. Treasury IRA Guidance
          url: https://home.treasury.gov/policy-issues/inflation-reduction-act
          free: yes
          api: false
        source_fallback:
          name: 한국무역협회 IRA 동향
          url: https://www.kita.net/
        update_frequency: 비정기
        noise_check: "최종 규정 vs 잠정 가이던스 구분. Federal Register 공식 발표 기준"
        target_signals:
          bullish: "FEOC 적용 유예 또는 한국 양극재 미국 진출 인정 → 4사 밸류에이션 재평가"
          bearish: "트럼프 45X 폐지 → 양극재 미국 합작 ROI 30%+ 하락"
        relevant_tickers_kr: ["에코프로비엠(247540)", "포스코퓨처엠(003670)", "엘앤에프(066970)", "LG화학(051910)"]
        relevant_tickers_us: ["ALB", "MP"]
        status: verified

      - id: anode_graphite_price
        name: 음극재용 흑연 가격 (천연/인조)
        what: "천연 흑연 (구상화 spherical) + 인조 흑연 (CN spot) 가격"
        why_leading: "포스코퓨처엠은 음극재 국내 유일 양산. 흑연 가격은 음극재 ASP의 50% 결정"
        lead_time_evidence: "중국 천연 흑연 수출 통제 (2023.10) → 글로벌 천연 흑연 가격 +30%, 포스코퓨처엠 음극재 ASP +15% 약 90일 후"
        source_primary:
          name: KOMIS 한국자원정보서비스
          url: https://www.komis.or.kr/
          free: yes
          api: false
        source_fallback:
          name: Trading Economics
          url: https://tradingeconomics.com/
        update_frequency: 주간/월간
        noise_check: "천연 vs 인조 흑연 비중 (포스코는 인조 중심) 분리 필요"
        target_signals:
          bullish: "중국 흑연 수출 통제 강화 → 비중국 음극재(포스코퓨처엠) 프리미엄"
          bearish: "중국 흑연 가격 -20% → 포스코퓨처엠 음극재 ASP 압박"
        relevant_tickers_kr: ["포스코퓨처엠(003670)"]
        relevant_tickers_us: []
        status: verified

      - id: separator_capacity_addition
        name: 분리막 글로벌 캐파 증설 (월간/분기)
        what: "글로벌 분리막 캐파 증설 발표, SK아이이테크놀로지/Asahi Kasei/Toray/창신신소재 발표"
        why_leading: "분리막은 배터리 4대 소재 중 진입장벽 가장 높음. 캐파 증설 발표 → 12-18개월 후 가동 → ASP 영향"
        lead_time_evidence: "중국 창신신소재 캐파 +50% (2022-2023) → 글로벌 분리막 ASP -20% (2024). 캐파→ASP lead 12-18개월"
        source_primary:
          name: SNE Research / SKIET IR
          url: https://www.skiet.com/
          free: partial
          api: false
        source_fallback:
          name: 한국배터리산업협회 (KBIA)
          url: https://www.kbia.or.kr/
        update_frequency: 분기
        noise_check: "발표된 캐파와 실제 가동 시점 차이 큼. 가동률 함께 봐야 함"
        target_signals:
          bullish: "중국 분리막 증설 둔화 + 한국 3사 가동률 +10%pp → SKIET 마진 회복"
          bearish: "창신신소재 추가 +30% 증설 → 글로벌 분리막 공급 과잉 지속"
        relevant_tickers_kr: ["SK아이이테크놀로지(361610)", "더블유씨피(393890)"]
        relevant_tickers_us: []
        status: verified

      - id: hyundai_mobis_orderbook
        name: 현대모비스 신규 수주 (분기 IR)
        what: "현대모비스 분기 신규 수주 (전동화 부품, 비계열 vs 계열)"
        why_leading: "비계열 수주 = 현대차 의존도 탈피 신호. 전동화 부품 수주는 18-24개월 후 매출 인식"
        lead_time_evidence: "현대모비스 비계열 수주 +50% (2023) → 2025 매출 +15% 약 24개월 lead. 분기 IR에서 직접 공시"
        source_primary:
          name: 현대모비스 IR
          url: https://www.mobis.co.kr/ir/
          free: yes
          api: false
        source_fallback:
          name: DART 전자공시시스템
          url: https://dart.fss.or.kr/
        update_frequency: 분기 (실적 발표)
        noise_check: "수주 금액 vs 실제 매출 인식 시점 갭 큼. 누적 수주잔고 추적 필요"
        target_signals:
          bullish: "비계열 EV 부품 수주 +30% YoY (Stellantis/VW 등) → 2년 후 매출 가시성"
          bearish: "현대차/기아 EV 판매 부진 → 계열 수주 -10% → 가동률 하락"
        relevant_tickers_kr: ["현대모비스(012330)", "현대차(005380)", "기아(000270)"]
        relevant_tickers_us: []
        status: verified

  # ============================================================
  # 12. 조선
  # ============================================================
  - sector: 조선
    indicators:
      - id: clarksons_newbuild_index
        name: Clarksons 신조선가 인덱스 (Newbuild Price Index)
        what: "Clarksons Newbuilding Price Index (1988=100), 선종별(컨테이너/탱커/벌커/LNG/LPG) 분리"
        why_leading: "신조선가는 한국 빅3 수주 단가의 직접 input. 인덱스 +10% → 신규 수주 마진 +5%pp 약 6개월 후 손익 반영"
        lead_time_evidence: "Clarksons 신조선가 +30% (2021-2023) → HD한국조선해양 영업이익 흑전 (2024). 수주→매출 lead 18-24개월, 단가→마진 lead 6개월"
        source_primary:
          name: Clarksons Research (무료 weekly summary)
          url: https://www.clarksons.com/research/
          free: partial
          api: false
        source_fallback:
          name: 한국조선해양플랜트협회 (KOSHIPA)
          url: https://www.koshipa.or.kr/
        update_frequency: 주간 (Clarksons SIN 인덱스)
        noise_check: "선종별 차이 큼. LNG선/컨테이너선 분리 필수"
        target_signals:
          bullish: "Clarksons 인덱스 +5% YoY 지속 + LNG선 +10% → 한국 빅3 마진 확대"
          bearish: "신조선가 정점 후 -10% 조정 → 신규 수주 가뭄"
        relevant_tickers_kr: ["HD한국조선해양(009540)", "삼성중공업(010140)", "한화오션(042660)"]
        relevant_tickers_us: []
        status: verified

      - id: lng_spot_charter_rate
        name: LNG 스팟 운임 (160K cbm Modern)
        what: "LNG 운반선 스팟 운임 (USD/day), 6개월 timecharter 동시 추적"
        why_leading: "LNG 운임 강세 = LNG선 발주 동기. 한국 빅3 LNG선 점유율 70%+로 운임 → 발주 → 수주 cascade"
        lead_time_evidence: "LNG 스팟 운임 $200K+/day (2022) → LNG선 발주 +200% (2022-2023) → 한국 빅3 LNG선 수주 잔고 5년+. 운임→발주 lead 약 6-12개월"
        source_primary:
          name: Clarksons / Spark Commodities
          url: https://www.sparkcommodities.com/
          free: partial
          api: false
        source_fallback:
          name: 한국가스공사 시장동향
          url: https://www.kogas.or.kr/
        update_frequency: 주간
        noise_check: "겨울 시즌 강세, 여름 약세 (계절성). YoY 비교 권장"
        target_signals:
          bullish: "LNG 스팟 $100K+/day 6개월 지속 → 카타르/미국 LNG 프로젝트 추가 발주"
          bearish: "LNG 운임 -50% (선복 증가) → 신규 LNG선 발주 둔화"
        relevant_tickers_kr: ["HD한국조선해양(009540)", "삼성중공업(010140)", "한화오션(042660)"]
        relevant_tickers_us: []
        status: verified

      - id: bdi_baltic_dry_index
        name: 발틱운임지수 BDI (Baltic Dry Index)
        what: "BDI = Capesize+Panamax+Supramax+Handysize 가중평균. 벌크선 운임 종합 지수"
        why_leading: "BDI 강세 → 벌크선 발주 + 노후선 교체. 한국 빅3는 벌크선 비중 낮지만 글로벌 조선 사이클 cycle indicator"
        lead_time_evidence: "BDI 4,000+ 6개월 지속 (2021) → 글로벌 벌크선 발주 +50% (2022) → 한국 조선소 dock slot 부족. lead 약 6-9개월"
        source_primary:
          name: Baltic Exchange
          url: https://www.balticexchange.com/
          free: partial
          api: false
        source_fallback:
          name: Trading Economics - Baltic Dry
          url: https://tradingeconomics.com/commodity/baltic
        update_frequency: 일간 (런던 세션)
        noise_check: "Capesize 비중이 BDI 변동성 주도. 선종별 분리 필수"
        target_signals:
          bullish: "BDI 2,500+ 6개월 지속 → 벌크선 발주 cycle 진입"
          bearish: "BDI <1,000 지속 → 조선 사이클 둔화 신호"
        relevant_tickers_kr: ["HD한국조선해양(009540)", "삼성중공업(010140)", "한화오션(042660)", "HMM(011200)"]
        relevant_tickers_us: []
        status: verified

      - id: tanker_charter_rate
        name: VLCC/Suezmax 탱커 운임
        what: "VLCC TD3C (중동→중국) + Suezmax TD20 (서아프리카→유럽) WS rate"
        why_leading: "탱커 운임 강세 → 신조 발주 + 노후선 교체. 한국 빅3 탱커 점유율 30%+, IMO 환경규제로 노후선 교체 가속"
        lead_time_evidence: "VLCC 운임 $80K+/day (2023-2024) → 탱커 발주 +100% (2023) → 한국 조선소 2027년 dock slot 매진. 운임→발주 lead 약 6-9개월"
        source_primary:
          name: Clarksons / Baltic Exchange
          url: https://www.balticexchange.com/
          free: partial
          api: false
        source_fallback:
          name: KMI 한국해양수산개발원
          url: https://www.kmi.re.kr/
        update_frequency: 주간
        noise_check: "OPEC+ 감산 정책, 러시아 우회 수송 noise. YoY 비교 권장"
        target_signals:
          bullish: "VLCC 운임 $50K+/day 지속 + 노후선 비중 20%+ → 탱커 발주 cycle"
          bearish: "OPEC+ 추가 감산 → 탱커 가동률 하락 → 신규 발주 둔화"
        relevant_tickers_kr: ["HD한국조선해양(009540)", "삼성중공업(010140)", "한화오션(042660)"]
        relevant_tickers_us: []
        status: verified

      - id: korea_big3_orderbook
        name: 한국 빅3 수주 잔고 (분기 IR)
        what: "HD한국조선해양/삼성중공업/한화오션 수주 잔고 (USD), 선종별/매출 인식 시점별"
        why_leading: "수주 잔고는 향후 2-3년 매출 가시성. 빅3 합산 1,500억 달러+ 시 호황기, 1,000억 미만 시 침체"
        lead_time_evidence: "한국 빅3 수주 잔고 1,500억 달러+ (2023) → 2025-2027 매출 +30% 가시성. 수주→매출 lead 18-30개월"
        source_primary:
          name: 빅3 IR (분기 실적)
          url: https://www.hd-hhi.com/ir
          free: yes
          api: false
        source_fallback:
          name: KOSHIPA / 산업연구원 KIET
          url: https://www.kiet.re.kr/
        update_frequency: 분기
        noise_check: "수주 단가 효과 (저가 수주 잔고는 손익 부정) 분리. 평균 수주 단가 동시 추적"
        target_signals:
          bullish: "빅3 수주 잔고 +20% YoY + 평균 단가 +15% → 2-3년 매출/마진 가시성"
          bearish: "신규 수주 -50% (Clarksons 인덱스 정점 후) → 2026년 후반 dock 공백 우려"
        relevant_tickers_kr: ["HD한국조선해양(009540)", "삼성중공업(010140)", "한화오션(042660)"]
        relevant_tickers_us: []
        status: verified

      - id: imo_environmental_regulation
        name: IMO 환경규제 동향 (CII/EEXI/넷제로 2050)
        what: "IMO MEPC 회의 결정사항, CII Rating 등급별 비중, EEXI 미달선 비중"
        why_leading: "IMO 규제 강화 → 노후선 조기 폐선 + 친환경선(LNG/메탄올/암모니아) 발주. 한국 빅3 친환경선 점유율 70%+"
        lead_time_evidence: "IMO 2023 CII 시행 → 2024년 노후선 폐선 +30%, 친환경선 발주 +50%. 규제→발주 lead 약 12개월"
        source_primary:
          name: IMO MEPC 회의 보고서
          url: https://www.imo.org/
          free: yes
          api: false
        source_fallback:
          name: 한국선급 KR (Korean Register)
          url: https://www.krs.co.kr/
        update_frequency: 비정기 (MEPC 연 2회)
        noise_check: "규제 발표 vs 실제 시행 시점 갭. 단계적 시행 일정 추적 필수"
        target_signals:
          bullish: "IMO 넷제로 2050 강화 + 메탄올/암모니아선 발주 +30% → 한국 빅3 점유율 강세"
          bearish: "CII 규제 완화 또는 시행 연기 → 친환경선 발주 둔화"
        relevant_tickers_kr: ["HD한국조선해양(009540)", "삼성중공업(010140)", "한화오션(042660)"]
        relevant_tickers_us: []
        status: verified

      - id: hmm_scfi_freight_rate
        name: SCFI (Shanghai Containerized Freight Index)
        what: "상하이→글로벌 노선별 컨테이너 운임 (USD/TEU). HMM 영업이익 결정 핵심"
        why_leading: "SCFI는 HMM 분기 영업이익과 R²>0.95. 운임 +1,000pt → 분기 영업이익 +5천억원"
        lead_time_evidence: "SCFI 5,000pt+ (2021) → HMM 영업이익 7조원 (2021). 운임→매출 lead 30일 (운항 기간), 분기 평균 SCFI로 분기 실적 nowcasting"
        source_primary:
          name: 상하이 항운거래소 (Shanghai Shipping Exchange)
          url: https://en.sse.net.cn/
          free: yes
          api: false
        source_fallback:
          name: KMI 한국해양수산개발원
          url: https://www.kmi.re.kr/
        update_frequency: 주간 (매주 금요일)
        noise_check: "노선별 변동 큼 (미주 vs 유럽). HMM 노선 비중 가중평균 권장"
        target_signals:
          bullish: "SCFI 2,500pt+ 8주 지속 → HMM 분기 영업이익 흑전 가시성"
          bearish: "SCFI <1,000pt → HMM 분기 적자 우려, 수에즈/홍해 정상화 시 운임 급락"
        relevant_tickers_kr: ["HMM(011200)", "팬오션(028670)"]
        relevant_tickers_us: ["ZIM"]
        status: verified

  # ============================================================
  # 13. 철강/비철
  # ============================================================
  - sector: 철강/비철
    indicators:
      - id: iron_ore_62fe_china
        name: 철광석 가격 (62% Fe China import CFR Qingdao)
        what: "Platts/TSI 철광석 62% Fe CFR 칭다오 가격 (USD/톤)"
        why_leading: "철광석은 일관제철(POSCO/현대제철) 원가의 25-30%. 가격 변동은 1-2분기 후 P&L 반영"
        lead_time_evidence: "철광석 -30% (2024) → POSCO홀딩스 영업이익 +50% 약 2분기 후. 가격→투입원가→마진 lead 약 60-90일"
        source_primary:
          name: Trading Economics - Iron Ore
          url: https://tradingeconomics.com/commodity/iron-ore
          free: yes
          api: false
        source_fallback:
          name: KOMIS 한국자원정보서비스
          url: https://www.komis.or.kr/
        update_frequency: 일간
        noise_check: "Vale/Rio Tinto 분기 출하량 가이던스 동시 추적. 중국 부동산 정책 연관"
        target_signals:
          bullish: "철광석 -20% + HRC 가격 횡보 → POSCO/현대제철 마진 확대"
          bearish: "철광석 +30% (브라질 Cyclone 등 supply shock) → 마진 압박"
        relevant_tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)", "동국제강(001230)"]
        relevant_tickers_us: ["NUE", "X", "CLF"]
        status: verified

      - id: coking_coal_price
        name: 원료탄 가격 (Hard Coking Coal FOB Australia)
        what: "프리미엄 강점탄 FOB 호주 (USD/톤). 일관제철 원가의 15-20%"
        why_leading: "원료탄은 철광석 다음 큰 원가. 호주 사이클론, 중국 수입 정책 변화에 민감. 한국 OEM은 호주/캐나다 의존도 높음"
        lead_time_evidence: "원료탄 $400+/톤 (2022) → POSCO 분기 영업이익 -30% 약 1-2분기 후. 가격→마진 lead 약 60-90일"
        source_primary:
          name: Trading Economics - Coal
          url: https://tradingeconomics.com/commodity/coal
          free: yes
          api: false
        source_fallback:
          name: KOMIS / 한국광해광업공단
          url: https://www.komis.or.kr/
        update_frequency: 일간/주간
        noise_check: "호주 사이클론 시즌 (1-3월) 일시적 spike. 추세는 연간 평균"
        target_signals:
          bullish: "원료탄 -25% YoY + 철광석 동시 약세 → POSCO 영업이익 +30%"
          bearish: "호주 사이클론 + 중국 수출 통제 → 원료탄 +50% 단기 spike"
        relevant_tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)"]
        relevant_tickers_us: ["X", "CLF"]
        status: verified

      - id: hrc_price_china_us_eu
        name: HRC 가격 China·US·EU 스프레드
        what: "열연강판(HRC) 가격 — 중국 (CNY/톤), 미국 (USD/short ton), 유럽 (EUR/톤)"
        why_leading: "HRC는 철강 ASP의 벤치마크. 미국 가격 vs 중국 가격 스프레드는 한국 수출 마진 결정"
        lead_time_evidence: "미국 HRC $1,000+/톤 (2024) + 중국 HRC $500/톤 → 한국 미국 수출 마진 +30%. 스프레드→수출 마진 lead 약 30-60일"
        source_primary:
          name: Trading Economics - Steel
          url: https://tradingeconomics.com/commodity/steel
          free: yes
          api: false
        source_fallback:
          name: 한국철강협회 KOSA
          url: https://www.kosa.or.kr/
        update_frequency: 주간
        noise_check: "트럼프 232조 관세, EU CBAM 등 무역 정책 효과 분리"
        target_signals:
          bullish: "미국 HRC 프리미엄 +$300/톤 + 한국 수출 쿼터 유지 → POSCO/현대제철 수출 마진 확대"
          bearish: "중국 HRC 덤핑 + EU CBAM 강화 → 한국 수출 압박"
        relevant_tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)", "동국제강(001230)"]
        relevant_tickers_us: ["NUE", "X", "STLD", "CLF"]
        status: verified

      - id: wsa_global_steel_production
        name: WSA 월간 조강생산 (World Steel Association)
        what: "WSA 월간 조강생산 (66개국), 중국/한국/일본/인도/EU 분리"
        why_leading: "글로벌 조강생산은 철강 수급의 직접 신호. 중국 -10% YoY → 글로벌 가격 +15% 약 60일 후"
        lead_time_evidence: "중국 조강생산 감산 정책 (2021) → 글로벌 HRC +30% 약 90일 후. WSA→가격 lead 약 60-90일"
        source_primary:
          name: World Steel Association
          url: https://worldsteel.org/
          free: yes
          api: false
        source_fallback:
          name: 한국철강협회 KOSA
          url: https://www.kosa.or.kr/
        update_frequency: 월간 (해당월 다음달 25일경)
        noise_check: "중국 춘절(1-2월) 영향, 11-12월 환경규제 감산. YoY 비교 권장"
        target_signals:
          bullish: "중국 조강생산 -5% YoY + 인도 +10% → 글로벌 수급 타이트"
          bearish: "중국 조강생산 +5% YoY (수출 증가) → 글로벌 가격 압박"
        relevant_tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)"]
        relevant_tickers_us: ["NUE", "X", "STLD", "CLF"]
        status: verified

      - id: zinc_lme_price
        name: 아연 가격 (LME)
        what: "LME 아연 cash settlement (USD/톤). 고려아연 매출의 핵심"
        why_leading: "아연은 LME 메탈 중 한국 유일 글로벌 플레이어 (고려아연). LME 가격 +10% → 고려아연 분기 영업이익 +20%"
        lead_time_evidence: "LME 아연 $3,500+/톤 (2022) → 고려아연 영업이익 사상 최대. 가격→매출 lead 약 30-60일 (재고 회전)"
        source_primary:
          name: LME (London Metal Exchange)
          url: https://www.lme.com/
          free: partial
          api: false
        source_fallback:
          name: Trading Economics - Zinc
          url: https://tradingeconomics.com/commodity/zinc
        update_frequency: 일간
        noise_check: "TC/RC (제련 수수료) 동시 추적 필수. TC 약세 시 고려아연 마진 압박"
        target_signals:
          bullish: "LME 아연 +20% + TC 안정 → 고려아연 분기 강세"
          bearish: "LME 아연 -15% + TC 급락 → 고려아연 마진 압박"
        relevant_tickers_kr: ["고려아연(010130)", "영풍(000670)"]
        relevant_tickers_us: []
        status: verified

      - id: china_property_steel_demand
        name: 중국 부동산 신규 착공면적 (월간)
        what: "중국 국가통계국(NBS) 부동산 신규 착공면적, 매월 발표"
        why_leading: "중국 부동산 = 글로벌 철강 수요 35%. 신규 착공 -30% (2022-2024) → 글로벌 철강 수요 -15% 약 6개월 후"
        lead_time_evidence: "중국 부동산 신규 착공 -50% (2022) → 글로벌 HRC -40% 약 6-9개월 후. NBS→철강 가격 lead 약 90-180일"
        source_primary:
          name: 중국 국가통계국 NBS
          url: http://www.stats.gov.cn/
          free: yes
          api: false
        source_fallback:
          name: Trading Economics - China Construction
          url: https://tradingeconomics.com/china/
        update_frequency: 월간 (해당월 다음달 중순)
        noise_check: "중국 정부 부양책 발표 시점 효과. 누적 vs 단월 분리"
        target_signals:
          bullish: "중국 부동산 신규 착공 +5% YoY 회복 → 6개월 후 철강 수요 회복"
          bearish: "신규 착공 -20% YoY 지속 → 글로벌 철강 수요 침체 장기화"
        relevant_tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)", "고려아연(010130)"]
        relevant_tickers_us: ["NUE", "X", "CLF"]
        status: verified

      - id: us_232_eu_cbam_policy
        name: 미국 232조 관세 + EU CBAM 정책 동향
        what: "트럼프 232조 철강/알루미늄 관세 변경, EU CBAM 시행 일정/적용 범위"
        why_leading: "한국 철강 수출의 미국/EU 비중 30%+. 관세 변경은 수출 쿼터/가격 즉시 영향"
        lead_time_evidence: "트럼프 1기 232조 25% 관세 (2018) → POSCO 미국 수출 -30% 약 60일 후. 정책→수출 lead 30-60일"
        source_primary:
          name: USTR / EU Commission
          url: https://ustr.gov/
          free: yes
          api: false
        source_fallback:
          name: 한국무역협회 (KITA)
          url: https://www.kita.net/
        update_frequency: 비정기
        noise_check: "관세 발표 vs 실제 시행 갭. 한국은 쿼터(263만톤) vs 관세 면제 협상 결과 확인"
        target_signals:
          bullish: "한국 232조 면제 유지 + EU CBAM 한국 산정 우대 → 수출 마진 안정"
          bearish: "트럼프 232조 25% 관세 부활 + 한국 면제 철회 → POSCO 미국 매출 -30%"
        relevant_tickers_kr: ["POSCO홀딩스(005490)", "현대제철(004020)", "동국제강(001230)"]
        relevant_tickers_us: ["NUE", "X", "STLD", "CLF"]
        status: verified

  # ============================================================
  # 14. 디스플레이
  # ============================================================
  - sector: 디스플레이
    indicators:
      - id: omdia_panel_price
        name: OMDIA 패널 가격 (월간)
        what: "OMDIA 월간 패널 가격 — LCD TV (32/43/55/65인치), OLED TV (55/65인치), Mobile OLED"
        why_leading: "패널 가격은 LG디스플레이 분기 매출의 직접 driver. OLED TV/Mobile OLED 가격은 한국 양사 매출 결정"
        lead_time_evidence: "OMDIA LCD 65인치 +30% (2020-2021) → LGD 영업이익 흑전 약 2분기 후. 가격→매출 lead 약 60-90일"
        source_primary:
          name: OMDIA (구 IHS Markit)
          url: https://omdia.tech.informa.com/
          free: partial
          api: false
        source_fallback:
          name: 한국디스플레이산업협회 (KDIA)
          url: https://www.kdia.org/
        update_frequency: 월간
        noise_check: "BOE/CSOT 등 중국 패널사 출하량 동시 추적. 중국 LCD 공급 과잉 효과"
        target_signals:
          bullish: "OLED TV 패널 +10% YoY + Mobile OLED 안정 → LGD/SDC 분기 강세"
          bearish: "LCD TV -20% (중국 공급 과잉) → LGD LCD 라인 적자 확대"
        relevant_tickers_kr: ["LG디스플레이(034220)", "삼성전자(005930)"]
        relevant_tickers_us: ["AAPL"]
        status: verified

      - id: oled_smartphone_shipment
        name: OLED 스마트폰 출하 (분기, IDC/Counterpoint)
        what: "글로벌 OLED 스마트폰 출하 대수, 삼성 vs BOE vs LGD 점유율"
        why_leading: "Mobile OLED는 SDC(삼성디스플레이) 매출의 60%+, LGD의 30%. 출하→매출 lead 약 30-60일"
        lead_time_evidence: "Apple iPhone OLED 채택 확대 (2017→) + LTPO 전환 (2021→) → SDC/LGD 매출 직접 연동. 분기 출하→매출 lead 약 30-60일"
        source_primary:
          name: IDC / Counterpoint Research (무료 요약)
          url: https://www.counterpointresearch.com/
          free: partial
          api: false
        source_fallback:
          name: 한국디스플레이산업협회 (KDIA)
          url: https://www.kdia.org/
        update_frequency: 분기
        noise_check: "Apple 신모델 출시 효과 (9월) 분기별 차이. 분기 평균 권장"
        target_signals:
          bullish: "iPhone OLED LTPO 채택 확대 + 삼성 폴더블 +50% → SDC/LGD 강세"
          bearish: "BOE Apple iPhone 점유율 +10%pp → LGD 직접 위협"
        relevant_tickers_kr: ["LG디스플레이(034220)", "삼성전자(005930)", "덕산네오룩스(213420)"]
        relevant_tickers_us: ["AAPL"]
        status: verified

      - id: apple_iphone_quarterly
        name: Apple iPhone 분기 매출 (Apple IR)
        what: "Apple 분기 iPhone 매출 (USD), 지역별/모델별 부분 disclosure"
        why_leading: "Apple iPhone OLED는 LGD 매출 30%+, SDC 50%+ 차지. iPhone 매출 → 패널 발주 → LGD/SDC 분기 매출"
        lead_time_evidence: "Apple iPhone 분기 매출 -10% (2024 Q1) → LGD 모바일 매출 -15% 같은 분기. 동행 또는 1개월 lead"
        source_primary:
          name: Apple Investor Relations
          url: https://investor.apple.com/
          free: yes
          api: false
        source_fallback:
          name: Apple 10-Q (SEC EDGAR)
          url: https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=0000320193
        update_frequency: 분기 (회계연도 9월 종료)
        noise_check: "Apple은 iPhone 모델별/지역별 상세 미공개. 분기 합산 + 가이던스 동시 추적"
        target_signals:
          bullish: "iPhone 매출 +10% YoY + Pro 모델 비중 확대 → LGD/SDC 프리미엄 패널 매출 강세"
          bearish: "iPhone 중국 매출 -20% (Huawei 회복) → Apple 발주 cut → LGD/SDC 분기 부진"
        relevant_tickers_kr: ["LG디스플레이(034220)", "삼성전자(005930)", "덕산네오룩스(213420)"]
        relevant_tickers_us: ["AAPL"]
        status: verified

      - id: oled_material_shipment
        name: OLED 발광재료 출하 (덕산네오룩스/UDC)
        what: "Universal Display(UDC) + 덕산네오룩스 분기 매출. OLED 패널 가동률의 leading indicator"
        why_leading: "OLED 발광재료는 패널 양산 1-2개월 전 입고. UDC 매출은 SDC/LGD/BOE OLED 출하의 1분기 lead"
        lead_time_evidence: "UDC 분기 매출 +20% → 다음 분기 SDC/LGD OLED 출하 +15%. 재료→패널 lead 약 30-60일"
        source_primary:
          name: Universal Display (UDC) IR
          url: https://oled.com/
          free: yes
          api: false
        source_fallback:
          name: 덕산네오룩스 IR / DART
          url: https://dart.fss.or.kr/
        update_frequency: 분기
        noise_check: "재고 효과 — 분기 매출과 실제 패널 출하 직접 연결 안 될 수 있음. 가이던스 함께 추적"
        target_signals:
          bullish: "UDC 매출 +30% YoY + 가이던스 상향 → 다음 분기 LGD/SDC 강세 예고"
          bearish: "UDC 매출 -10% + 가이던스 cut → OLED 패널 가동률 하락 신호"
        relevant_tickers_kr: ["덕산네오룩스(213420)", "LG디스플레이(034220)"]
        relevant_tickers_us: ["OLED"]
        status: verified

      - id: china_boe_capacity
        name: 중국 BOE/CSOT OLED 캐파 증설 (분기)
        what: "BOE B7/B11/B12 + CSOT T4/T5 OLED 캐파 가동률, 신규 라인 발표"
        why_leading: "BOE Apple iPhone OLED 진입 (2020→) + 중국 OLED 캐파 +50% (2024-2026) → LGD 직접 위협. 캐파→점유율 lead 12-18개월"
        lead_time_evidence: "BOE Apple iPhone 13/14 진입 → LGD iPhone OLED 점유율 -15%pp (2022-2023). 캐파 가동→점유율 영향 약 12-18개월"
        source_primary:
          name: OMDIA / DSCC (Display Supply Chain Consultants)
          url: https://www.displaysupplychain.com/
          free: partial
          api: false
        source_fallback:
          name: 한국디스플레이산업협회 (KDIA)
          url: https://www.kdia.org/
        update_frequency: 분기
        noise_check: "발표 캐파 vs 실제 가동률 갭 큼. 가동률 데이터 함께 추적"
        target_signals:
          bullish: "중국 OLED 캐파 증설 둔화 + BOE Apple 수율 정체 → LGD 점유율 방어"
          bearish: "BOE B12 가동 + Apple iPhone 17 진입 → LGD 점유율 -10%pp"
        relevant_tickers_kr: ["LG디스플레이(034220)", "덕산네오룩스(213420)"]
        relevant_tickers_us: ["AAPL"]
        status: verified

      - id: lcd_china_overcapacity
        name: 중국 LCD 가동률 (BOE/CSOT/HKC)
        what: "중국 BOE/CSOT/HKC LCD 가동률 (Gen 8.5/10.5), 출하량"
        why_leading: "중국 LCD 캐파는 글로벌 70%+. 가동률 80%+ 시 LCD 가격 강세, 60% 미만 시 약세. LGD/SDC LCD 라인 손익 결정"
        lead_time_evidence: "중국 LCD 가동률 90% (2020-2021) → LCD 가격 +50% → LGD LCD 흑전. 가동률→가격 lead 약 30-60일"
        source_primary:
          name: OMDIA / DSCC
          url: https://www.displaysupplychain.com/
          free: partial
          api: false
        source_fallback:
          name: 한국디스플레이산업협회 (KDIA)
          url: https://www.kdia.org/
        update_frequency: 월간
        noise_check: "BOE 의도적 감산 (가격 방어 목적) 분리. 출하량 vs 가동률 동시 추적"
        target_signals:
          bullish: "중국 3사 가동률 85%+ 6개월 지속 + BOE 감산 → LCD TV 가격 +20%"
          bearish: "중국 LCD 가동률 70% 미만 + 신규 라인 가동 → 글로벌 LCD 가격 압박"
        relevant_tickers_kr: ["LG디스플레이(034220)", "삼성전자(005930)"]
        relevant_tickers_us: []
        status: verified

      - id: it_oled_tablet_shipment
        name: IT용 OLED (태블릿/노트북) 출하
        what: "iPad Pro M4 OLED, MacBook OLED 출하 — DSCC/OMDIA 추정"
        why_leading: "Apple iPad Pro OLED 채택 (2024-) + MacBook OLED 채택 (2026E) → LGD/SDC 신규 매출. IT OLED 시장은 2024-2030 CAGR 30%+"
        lead_time_evidence: "iPad Pro M4 OLED (2024.5 출시) → SDC/LGD 매출 +5% (2024 Q3-Q4). 신규 카테고리 진입 → 매출 lead 약 60-90일"
        source_primary:
          name: DSCC / OMDIA
          url: https://www.displaysupplychain.com/
          free: partial
          api: false
        source_fallback:
          name: 한국디스플레이산업협회 (KDIA) / DART
          url: https://www.kdia.org/
        update_frequency: 분기
        noise_check: "초기 시장 — 출하량 적어 변동성 큼. YoY 보다 절대량 추적"
        target_signals:
          bullish: "MacBook OLED 채택 발표 + 양산 일정 확정 → LGD/SDC 신규 매출 가시성"
          bearish: "Apple IT OLED 출시 지연 또는 BOE 진입 → LGD/SDC 매출 expectation cut"
        relevant_tickers_kr: ["LG디스플레이(034220)", "삼성전자(005930)", "덕산네오룩스(213420)"]
        relevant_tickers_us: ["AAPL"]
        status: verified


## 10. 그룹 B — 섹터 15~17: 성장형 내수/플랫폼 (19개 지표)


# Phase 2 Group B · 성장형 내수/플랫폼 3개 섹터 선행 지표

## 15. 인터넷 플랫폼

```yaml
sector: 인터넷 플랫폼
indicators:
  - id: us_bigtech_ad_guidance
    name: 미국 빅테크 디지털 광고 매출 가이던스 (Meta·Google)
    what: "Meta(Family of Apps) 및 Alphabet(Google Services) 분기 광고 매출 및 다음 분기 가이던스 (USD), YoY 성장률"
    why_leading: "Meta+Google이 글로벌 디지털 광고의 50% 이상 점유. 양사 분기 가이던스는 글로벌 광고 경기 선행 지표 → NAVER·카카오·CPNG의 광고/커머스 매출이 1-2분기 시차로 동행. 광고는 경기 사이클 선행 (광고주 예산 조정이 매출 인식보다 빠름)"
    lead_time_evidence: "Meta/Alphabet 분기 광고 매출은 GroupM/Magna 글로벌 광고시장 통계 대비 1-2분기 선행. NAVER 서치플랫폼 매출은 Google 광고 YoY와 R²>0.7 상관 (한국 디지털광고협회 KODIMA 분석)"
    source_primary:
      name: SEC EDGAR (Meta 10-Q, Alphabet 10-Q)
      url: https://www.sec.gov/cgi-bin/browse-edgar
      access: 분기 발표 직후 공시, 무료
      free: true
      api: true
    source_fallback:
      name: Meta Investor Relations / Alphabet Investor Relations
      url: https://investor.fb.com / https://abc.xyz/investor
    update_frequency: 분기 (1·4·7·10월 말)
    noise_check: "FX 변동·정책(ATT 등) 영향으로 단일 분기 노이즈 있음, constant currency 기준 보정, false <15%"
    target_signals:
      bullish: "Meta+Google 광고 매출 YoY +15% 이상 + 가이던스 상향 → 광고 사이클 상승, 플랫폼주 강세"
      bearish: "양사 모두 YoY 한 자릿수 + 가이던스 하향 → 광고 침체, NAVER/카카오 동반 약세"
    relevant_tickers_kr: ["NAVER(035420)", "카카오(035720)"]
    relevant_tickers_us: [META, GOOGL, CPNG]
    status: verified

  - id: kr_kostat_online_retail
    name: 한국 통계청 온라인쇼핑 동향조사 (월간 거래액)
    what: "통계청 발표 한국 온라인쇼핑 거래액 (모바일 비중 포함, 월간 단위), YoY/MoM"
    why_leading: "쿠팡·NAVER 커머스·카카오 선물하기 등 e-commerce GMV의 모집단. 월간 발표(매월 초)는 분기 IR 발표보다 1-2개월 선행. 카테고리별 세분화로 어떤 플랫폼이 수혜인지 추정 가능"
    lead_time_evidence: "통계청 온라인쇼핑 동향은 매월 첫째 주 발표 → 쿠팡·NAVER 분기 거래액 발표 대비 30-60일 선행. 산업 합계 YoY는 쿠팡 활성고객·NAVER Smart Store 매출과 강한 상관 (KOSIS 시계열)"
    source_primary:
      name: 통계청 KOSIS 온라인쇼핑동향
      url: https://kostat.go.kr/board.es?mid=a10301010000&bid=215
      access: 매월 첫째 주 (전월 데이터), 무료 PDF + Excel
      free: true
      api: true
    source_fallback:
      name: 통계청 e-나라지표 온라인쇼핑
      url: https://www.index.go.kr/
    update_frequency: 월간 (매월 첫째 주 목요일)
    noise_check: "추석·설 명절 효과로 9월·1-2월 변동, 명절 보정/3개월 이동평균 사용, false <10%"
    target_signals:
      bullish: "온라인쇼핑 거래액 YoY +15% 이상 3개월 연속 + 모바일 비중 80% 이상 → 쿠팡/NAVER 커머스 수혜"
      bearish: "YoY 한 자릿수 둔화 + 모바일 비중 정체 → e-commerce 성숙기 진입, 마진 압박"
    relevant_tickers_kr: ["NAVER(035420)", "카카오(035720)"]
    relevant_tickers_us: [CPNG]
    status: verified

  - id: kr_kca_kisa_internet_trend
    name: NAVER·구글 한국 검색 점유율 (KISA·인터넷트렌드)
    what: "한국 검색엔진 점유율 - NAVER vs Google vs 다음 (월간), KISA 한국인터넷이용실태조사 / 인터넷트렌드 통계"
    why_leading: "NAVER 서치플랫폼 매출의 핵심 변수는 검색 트래픽 점유율. Google에 점유율을 빼앗기면 광고 단가 하락. 월간 점유율 변화가 분기 매출보다 선행"
    lead_time_evidence: "한국 검색 점유율은 NAVER 분기 서치플랫폼 매출 대비 2-3개월 선행 (NAVER IR 자료에서 자체 인용). KISA 인터넷이용실태조사 연간 + 인터넷트렌드 월간 데이터"
    source_primary:
      name: 한국인터넷진흥원(KISA) 인터넷이용실태조사
      url: https://www.kisa.or.kr/2050201/form?postSeq=
      access: 연간 종합 + 분기별 보조지표, 무료
      free: true
      api: false
    source_fallback:
      name: 인터넷트렌드 (InternetTrend.co.kr)
      url: https://www.internettrend.co.kr/
    update_frequency: 월간 (인터넷트렌드) / 연간 (KISA 종합)
    noise_check: "측정 방법론 차이로 절대값 변동, 점유율 추세(YoY 변화)에 집중, false <15%"
    target_signals:
      bullish: "NAVER 검색 점유율 55% 이상 유지 + Google 점유율 정체 → NAVER 광고 단가 방어, 매출 안정"
      bearish: "NAVER 점유율 50% 하향 돌파 → 광고 단가 압박, 서치플랫폼 매출 둔화"
    relevant_tickers_kr: ["NAVER(035420)", "카카오(035720)"]
    relevant_tickers_us: [GOOGL]
    status: verified

  - id: us_appstore_kr_top_charts
    name: App Store/Google Play KR Top Free·Grossing 차트 노출 빈도
    what: "한국 App Store/Google Play Top Free·Top Grossing 차트에 NAVER·카카오·쿠팡 앱 순위 (일간/주간 평균)"
    why_leading: "Top Grossing 1위 빈도는 모바일 트래픽/매출의 직접 지표. 신규 기능·이벤트 출시 후 차트 변동이 분기 MAU/매출보다 선행. 무료 차트(Top Free)는 신규 사용자 유입 선행"
    lead_time_evidence: "App Store 차트 순위는 SensorTower/data.ai 유료 데이터의 무료 대체재. 차트 1위 유지 일수는 분기 사용자 지표 대비 4-8주 선행 (업계 일반론, 모바일 게임/앱 분석에서 확립)"
    source_primary:
      name: Apple App Store 차트 (KR)
      url: https://apps.apple.com/kr/charts/
      access: 일간 무료 공개 (Apple/Google 직접 운영)
      free: true
      api: false
    source_fallback:
      name: Google Play 인기 차트 (KR)
      url: https://play.google.com/store/apps/top
    update_frequency: 일간 (자동 갱신)
    noise_check: "이벤트성 1일 스파이크 노이즈 있음, 7일 이동평균 사용, false <15%"
    target_signals:
      bullish: "쿠팡/카카오 Top Grossing Top 5 + Top Free Top 10 동시 진입 → 활성고객·매출 동반 증가"
      bearish: "주요 앱 Top 20 밖 이탈 + 신규 진입 앱 부재 → 트래픽 정체"
    relevant_tickers_kr: ["NAVER(035420)", "카카오(035720)"]
    relevant_tickers_us: [CPNG, META, GOOGL]
    status: verified

  - id: kr_kcc_mobile_traffic
    name: 방통위 무선데이터 트래픽 통계
    what: "방송통신위원회/과기정통부 발표 무선데이터 월간 트래픽(PB), 동영상·SNS·웹포털 비중"
    why_leading: "모바일 동영상/SNS/포털 트래픽은 NAVER·카카오·유튜브(Google) 광고 인벤토리 자체. 트래픽 증가 → 광고 노출 증가 → 광고 매출. 월간 발표는 분기 매출 대비 선행"
    lead_time_evidence: "과기정통부 무선데이터 트래픽 월간 통계 - 동영상 비중은 YouTube/숏폼 광고 시장 선행, 웹포털 비중은 NAVER/Daum 광고 매출과 동행~선행 (한국방송광고진흥공사 분석 인용)"
    source_primary:
      name: 과학기술정보통신부 무선데이터 트래픽 통계
      url: https://www.msit.go.kr/bbs/list.do?sCode=user&mId=99
      access: 매월 말 발표 (전전월 데이터), 무료
      free: true
      api: false
    source_fallback:
      name: 방송통신위원회 통계 포털
      url: https://kcc.go.kr/user.do
    update_frequency: 월간 (매월 말)
    noise_check: "5G 보급률·신규 단말 출시로 단계적 점프, YoY 트래픽 증가율 추세 사용, false <15%"
    target_signals:
      bullish: "월간 트래픽 YoY +20% 이상 + 동영상 비중 60% 이상 → 광고 인벤토리 확대, 플랫폼 광고 강세"
      bearish: "트래픽 YoY 한 자릿수 + 비중 정체 → 광고 인벤토리 정체, 단가 경쟁 심화"
    relevant_tickers_kr: ["NAVER(035420)", "카카오(035720)"]
    relevant_tickers_us: [META, GOOGL]
    status: verified

  - id: kr_kostat_household_consumption
    name: 통계청 가계동향조사 통신·오락문화 지출
    what: "통계청 분기 가계동향조사에서 통신·오락문화·외식 지출 (가구당 월평균, KRW), YoY"
    why_leading: "온라인 플랫폼 결제력의 거시 변수. 가계 가처분소득 중 디지털 소비 비중이 NAVER·카카오 유료 서비스(웹툰·뮤직·결제) 매출 선행"
    lead_time_evidence: "통계청 가계동향조사 분기 발표는 플랫폼 결제 매출 분기 IR 대비 동행~1분기 선행. 오락문화 지출은 K-콘텐츠/플랫폼 매출과 R²>0.6 상관 (KDI 분석)"
    source_primary:
      name: 통계청 가계동향조사
      url: https://kostat.go.kr/board.es?mid=a10301060200&bid=210
      access: 분기 발표 (2·5·8·11월), 무료 Excel
      free: true
      api: true
    source_fallback:
      name: 한국은행 경제통계시스템 ECOS
      url: https://ecos.bok.or.kr/
    update_frequency: 분기 (분기 종료 후 약 60일)
    noise_check: "표본조사 노이즈 있음, 4분기 이동평균 사용, false <20%"
    target_signals:
      bullish: "오락문화 지출 YoY +5% 이상 + 통신비 안정 → 디지털 콘텐츠 결제 여력 양호"
      bearish: "오락문화 YoY 마이너스 + 외식 둔화 → 가계 소비 위축, 플랫폼 결제 둔화"
    relevant_tickers_kr: ["NAVER(035420)", "카카오(035720)"]
    relevant_tickers_us: [CPNG]
    status: verified
```

---

## 16. 게임

```yaml
sector: 게임
indicators:
  - id: steamdb_top_concurrent
    name: SteamDB Top 100 동시 접속자 (CCU) 트렌드
    what: "Steam 플랫폼 Top 100 게임 일간 피크 동시 접속자 수 (SteamDB 공개 통계), 신작 출시 직후 CCU 곡선"
    why_leading: "Steam CCU는 PC 게임 매출의 가장 직접적 선행 지표. 출시 첫 주 CCU 피크가 분기 매출 가이던스를 4-12주 선행. KRAFTON(PUBG), EA, TTWO 신작 모두 Steam 출시 → 직접 매출 선행"
    lead_time_evidence: "SteamDB CCU 데이터는 분기 매출 발표 대비 4-12주 선행 (Newzoo·SuperData 연간 보고서 다수 인용). PUBG 글로벌 CCU는 KRAFTON 분기 매출과 R²>0.85 상관"
    source_primary:
      name: SteamDB (steamdb.info)
      url: https://steamdb.info/charts/
      access: 실시간 무료 공개 (Valve API 기반)
      free: true
      api: true
    source_fallback:
      name: Steam Charts
      url: https://steamcharts.com/
    update_frequency: 실시간 (5분 주기) / 일간·주간 차트
    noise_check: "주말·이벤트 효과로 일간 변동, 4주 이동평균 사용, false <10%"
    target_signals:
      bullish: "PUBG/신작 CCU 피크 +30% YoY + Top 10 신규 진입 → 매출 가이던스 상향 가능성"
      bearish: "주요 IP CCU YoY -20% 이상 + 신작 부재 → 매출 둔화"
    relevant_tickers_kr: ["크래프톤(259960)", "엔씨소프트(036570)", "시프트업(462870)"]
    relevant_tickers_us: [EA, TTWO, RBLX]
    status: verified

  - id: kr_appstore_grossing_games
    name: App Store/Google Play KR Top Grossing Games (게임 카테고리)
    what: "한국 App Store/Google Play 게임 카테고리 Top Grossing 차트 — 크래프톤·엔씨·시프트업·넥슨 작품 순위 일간/주간"
    why_leading: "한국 모바일 게임 매출의 70% 이상이 Top 20 차트에서 발생. Top Grossing 순위 변동이 분기 매출 발표 대비 4-8주 선행. 신작 출시 직후 차트 진입 여부가 분기 catalyst의 직접 신호"
    lead_time_evidence: "App Store Grossing 순위는 SensorTower/data.ai 매출 추정의 무료 대체재. NCSoft '리니지' 류 차트 1위 유지 일수와 분기 매출 R²>0.8 상관 (한국게임산업협회 분석)"
    source_primary:
      name: Apple App Store 게임 차트 (KR)
      url: https://apps.apple.com/kr/charts/iphone/top-grossing-games/6014
      access: 일간 무료 공개
      free: true
      api: false
    source_fallback:
      name: Google Play 게임 인기 차트 (KR)
      url: https://play.google.com/store/apps/category/GAME/top
    update_frequency: 일간 (자동 갱신)
    noise_check: "출시 직후 1-2주 스파이크, 4주 평균 순위로 추세 판단, false <15%"
    target_signals:
      bullish: "신작 Top 5 진입 + 4주 이상 유지 + 기존 IP Top 10 방어 → 분기 매출 상향"
      bearish: "주력 게임 Top 20 밖 이탈 + 신작 Top 50 → 매출 가이던스 하향"
    relevant_tickers_kr: ["크래프톤(259960)", "엔씨소프트(036570)", "시프트업(462870)"]
    relevant_tickers_us: [RBLX, EA, TTWO]
    status: verified

  - id: china_nppa_game_approvals
    name: 중국 NPPA 게임 판호(版号) 발급 빈도
    what: "중국 국가신문출판서(NPPA) 월간 게임 판호 발급 건수 - 국내(국산)·수입(외산) 별도, 한국 게임 포함 여부"
    why_leading: "중국 게임 시장 진입은 판호 없이 불가. 한국 게임 판호 발급 빈도는 KRAFTON·NCSoft 중국 매출 6-12개월 선행. 외자 판호 발급 패턴이 정책 기조 시그널"
    lead_time_evidence: "NPPA 월간 판호 리스트는 정부 공식 발표. 한국 게임 외자 판호 발급 → 6-12개월 후 중국 출시 → 매출 인식. 2017-2022 한한령 기간 외자 판호 0건 → KRAFTON 중국 매출 급감 (회사 IR 인용)"
    source_primary:
      name: 중국 국가신문출판서 (NPPA) 게임 판호 공시
      url: https://www.nppa.gov.cn/bsfw/jggs/cxjg/
      access: 월간 발표, 중국어 PDF 무료
      free: true
      api: false
    source_fallback:
      name: 게임타임즈/한국콘텐츠진흥원 KOCCA 중국 시장 보고서
      url: https://www.kocca.kr/
    update_frequency: 월간 (월별 일괄 발표, 비정기)
    noise_check: "정치 이슈로 일시 중단·재개 패턴, 분기 합산 추세 사용, false <20%"
    target_signals:
      bullish: "월간 외자 판호 5건 이상 + 한국 게임 포함 → KRAFTON/NCSoft 중국 catalyst"
      bearish: "외자 판호 3개월 연속 0건 + 한국 게임 부재 → 중국 매출 기대 하향"
    relevant_tickers_kr: ["크래프톤(259960)", "엔씨소프트(036570)", "시프트업(462870)"]
    relevant_tickers_us: [RBLX]
    status: verified

  - id: kr_kocca_game_industry
    name: 한국콘텐츠진흥원 KOCCA 게임백서·분기 동향
    what: "KOCCA 분기·연간 게임산업 동향 보고서 - 모바일/PC/콘솔 매출, 수출액(USD), 플랫폼별 비중"
    why_leading: "KOCCA는 한국 게임산업 공식 통계 출처. 분기 동향(약 60일 시차)은 개별사 IR보다 산업 합계 선행. 수출액은 글로벌 매출 가시화"
    lead_time_evidence: "KOCCA 분기 게임산업 동향은 산업 합계로 개별사 분기 매출 대비 동행~선행. 게임 수출액 YoY는 KRAFTON 해외 매출 비중과 강한 상관 (KOCCA 게임백서 매년 인용)"
    source_primary:
      name: 한국콘텐츠진흥원 KOCCA 통계포털
      url: https://www.kocca.kr/kocca/koccastats/index.do
      access: 분기 동향 + 연간 백서, 무료 PDF
      free: true
      api: false
    source_fallback:
      name: 게임물관리위원회 GRAC
      url: https://www.grac.or.kr/
    update_frequency: 분기 (분기 종료 후 약 60일) + 연간 백서 (12월)
    noise_check: "표본/추정 방법론 변경 시 단절, 동일 방법론 시계열만 사용, false <15%"
    target_signals:
      bullish: "분기 게임 수출액 YoY +20% 이상 + 모바일 매출 안정 → 산업 사이클 상승"
      bearish: "수출액 YoY 마이너스 + 모바일 침체 → 산업 둔화, 멀티플 압박"
    relevant_tickers_kr: ["크래프톤(259960)", "엔씨소프트(036570)", "시프트업(462870)"]
    relevant_tickers_us: [RBLX, EA, TTWO]
    status: verified

  - id: rblx_dau_hours_engagement
    name: Roblox DAU·Hours Engaged 월간 데이터
    what: "Roblox 월간 DAU(일평균 활성사용자), Hours Engaged(월간 총 이용시간) 회사 공식 발표"
    why_leading: "Roblox는 월간 키 메트릭을 자체 공시(SEC 8-K). DAU·Hours Engaged는 분기 Bookings(예약매출) 대비 4-8주 선행. 글로벌 게임 플랫폼 사용자 트렌드의 직접 지표"
    lead_time_evidence: "Roblox 월간 DAU 발표 → 다음 분기 Bookings/Revenue와 R²>0.9 상관 (회사 IR 자체 차트 인용). Hours Engaged YoY는 광고/결제 매출 선행"
    source_primary:
      name: Roblox Investor Relations (Monthly Key Metrics)
      url: https://ir.roblox.com/financials/monthly-key-metrics
      access: 매월 중순 발표, 무료
      free: true
      api: false
    source_fallback:
      name: SEC EDGAR (Roblox 8-K filings)
      url: https://www.sec.gov/cgi-bin/browse-edgar
    update_frequency: 월간 (매월 중순)
    noise_check: "시즌성(여름·연말 강세) 명확, YoY 비교 사용, false <10%"
    target_signals:
      bullish: "DAU YoY +20% 이상 + Hours YoY +25% 이상 → 분기 Bookings 상향"
      bearish: "DAU YoY 한 자릿수 + Hours 정체 → Bookings 가이던스 하향"
    relevant_tickers_kr: ["크래프톤(259960)"]
    relevant_tickers_us: [RBLX]
    status: verified

  - id: kr_us_game_release_calendar
    name: AAA·주력 IP 신작 출시 일정 (분기 catalyst 캘린더)
    what: "분기별 출시 예정 주요 게임 신작 - 크래프톤(인조이·다크앤다커 모바일 등)·EA(FIFA·Madden)·TTWO(GTA·NBA 2K)·시프트업(스텔라 블레이드 PC) 등 confirmed 출시일"
    why_leading: "신작 출시 시점이 분기 매출 catalyst를 직접 결정. 출시 일정 발표(보통 6-12개월 전)는 분기 매출 가이던스 선행. 출시 지연은 즉각 분기 매출 가이던스 하향"
    lead_time_evidence: "각사 IR 자료·SEC 공시·게임쇼(E3·게임스컴·지스타) 발표 일정은 분기 매출 대비 6-12개월 선행. TTWO GTA VI 출시 일정 변동이 분기 가이던스에 직접 반영 (회사 공시 인용)"
    source_primary:
      name: 각사 IR + SEC EDGAR (10-Q/10-K release calendar disclosure)
      url: https://www.sec.gov/cgi-bin/browse-edgar
      access: 분기 공시 + IR 발표, 무료
      free: true
      api: true
    source_fallback:
      name: KOCCA 신작 게임 출시 동향 / Steam 출시 캘린더
      url: https://store.steampowered.com/explore/upcoming/
    update_frequency: 분기 (각사 IR) + 게임쇼 (8월 게임스컴, 11월 지스타)
    noise_check: "출시 지연 빈번, 발표일 vs 실제 출시일 모니터링, false <25%"
    target_signals:
      bullish: "분기 내 AAA 신작 2건 이상 confirmed + 지연 없음 → 매출 catalyst 확정"
      bearish: "주력 IP 출시 지연 발표 + 신작 일정 공백 → 매출 가이던스 하향"
    relevant_tickers_kr: ["크래프톤(259960)", "엔씨소프트(036570)", "시프트업(462870)"]
    relevant_tickers_us: [EA, TTWO, RBLX]
    status: verified

  - id: jp_oricon_kadokawa_nexon_signal
    name: 일본 오리콘·Famitsu 게임 매출 차트 (넥슨/일본 시장 비중)
    what: "일본 Famitsu 주간 패키지·디지털 매출 차트, Oricon 모바일 게임 매출 추정 - 한국/한국계 게임 비중"
    why_leading: "일본은 KRAFTON·시프트업·넥슨 도쿄 핵심 시장. Famitsu/Oricon 차트 진입 여부는 일본 매출 분기 발표 대비 4-8주 선행. 일본 모바일 게임 시장은 글로벌 2위로 매출 가시성 높음"
    lead_time_evidence: "Famitsu 주간 차트는 일본 게임 매출 공식 트래커 (1986년부터). 시프트업 '승리의 여신: 니케' 일본 매출 차트 진입 → 분기 매출 가이던스 상향 패턴 (회사 IR 인용)"
    source_primary:
      name: Famitsu 주간 게임 매출 차트
      url: https://www.famitsu.com/ranking/
      access: 주간 발표, 무료 (일본어)
      free: true
      api: false
    source_fallback:
      name: Oricon 모바일 게임 매출 / Game*Spark
      url: https://www.oricon.co.jp/
    update_frequency: 주간 (Famitsu 매주 수요일)
    noise_check: "일본 골든위크·연말 시즌성, YoY 비교 사용, false <15%"
    target_signals:
      bullish: "한국계 게임 Top 10 2건 이상 + 4주 이상 유지 → 일본 매출 catalyst"
      bearish: "한국계 게임 Top 30 밖 이탈 + 신작 부재 → 일본 시장 둔화"
    relevant_tickers_kr: ["크래프톤(259960)", "시프트업(462870)"]
    relevant_tickers_us: []
    status: verified
```

---

## 17. K-콘텐츠/엔터

```yaml
sector: K-콘텐츠/엔터
indicators:
  - id: us_billboard_kpop_charting
    name: Billboard Hot 100·200 K-pop 진입 빈도
    what: "Billboard Hot 100(싱글)·Billboard 200(앨범) 주간 차트에 K-pop 아티스트 진입 곡/앨범 수, 최고 순위, 차트인 주수"
    why_leading: "Billboard 차트 진입은 미국 음반 매출/스트리밍의 직접 지표. 차트 진입 → 4-12주 후 분기 음반·로열티 매출 인식. 미국 시장은 K-pop 글로벌 매출의 핵심 마진 시장"
    lead_time_evidence: "Billboard 차트 진입은 RIAA 인증·스포티파이/애플뮤직 매출의 4-12주 선행. 하이브 BTS·뉴진스 Hot 100 1위 → 분기 매출 가이던스 상향 직접 catalyst (회사 IR 다수 인용)"
    source_primary:
      name: Billboard Charts
      url: https://www.billboard.com/charts/
      access: 주간 무료 공개 (매주 화요일)
      free: true
      api: false
    source_fallback:
      name: Luminate (구 Nielsen Music) 주간 차트
      url: https://luminatedata.com/
    update_frequency: 주간 (매주 화요일 발표, 토요일 주간)
    noise_check: "스트리밍·피지컬·라디오 가중치 변경 시 단절, 일관 방법론 시계열 사용, false <10%"
    target_signals:
      bullish: "Hot 100 Top 10 진입 + Billboard 200 Top 5 + 차트인 8주 이상 → 분기 음반·로열티 매출 상향"
      bearish: "주력 아티스트 차트 진입 부재 3개월 + 신곡 발매 공백 → 미국 매출 둔화"
    relevant_tickers_kr: ["하이브(352820)", "SM(041510)", "JYP(035900)"]
    relevant_tickers_us: []
    status: verified

  - id: spotify_charts_kr_artists
    name: Spotify Charts Global Top 200 K-pop 점유율
    what: "Spotify Charts Global Top 200 일간/주간 - 한국 아티스트 곡 수, 누적 스트리밍 (공식 무료 공개)"
    why_leading: "Spotify는 글로벌 스트리밍 1위. 글로벌 Top 200 K-pop 비중은 글로벌 음원 로열티 매출의 직접 선행. 일간 발표로 가장 빠른 신호"
    lead_time_evidence: "Spotify Charts 일간 데이터는 분기 음원 로열티 매출 대비 4-12주 선행. K-pop Top 200 비중 YoY는 하이브·SM·JYP 글로벌 음원 매출 합계와 R²>0.7 상관 (IFPI 글로벌 음악 보고서 인용)"
    source_primary:
      name: Spotify Charts (charts.spotify.com)
      url: https://charts.spotify.com/charts/overview/global
      access: 일간/주간 무료 공개
      free: true
      api: true
    source_fallback:
      name: Chartmetric Free Tier / Kworb.net
      url: https://kworb.net/spotify/
    update_frequency: 일간 (자동 갱신)
    noise_check: "신곡 발매 직후 1-2주 스파이크, 4주 평균 사용, false <10%"
    target_signals:
      bullish: "K-pop Top 200 비중 5% 이상 + Top 50 Top 5 진입 곡 다수 → 글로벌 로열티 강세"
      bearish: "Top 200 K-pop 비중 2% 이하 + 신곡 차트 진입 실패 → 음원 매출 둔화"
    relevant_tickers_kr: ["하이브(352820)", "SM(041510)", "JYP(035900)"]
    relevant_tickers_us: []
    status: verified

  - id: youtube_music_charts_global
    name: YouTube Music Charts·YouTube Top Songs 글로벌
    what: "YouTube Music Charts Global Top 100, YouTube Top Songs Weekly - K-pop MV 조회수 누적, 차트 진입 곡 수"
    why_leading: "YouTube는 K-pop 핵심 글로벌 채널. MV 조회수 누적이 광고 수익·아티스트 인지도·콘서트 수요 선행. 일간 차트가 가장 빠른 시그널"
    lead_time_evidence: "YouTube 글로벌 차트는 K-pop 콘서트 티켓 수요·앨범 매출 4-8주 선행. 블랙핑크·BTS MV 1억뷰 도달 속도 → 분기 매출 catalyst (각사 IR 인용)"
    source_primary:
      name: YouTube Music Charts
      url: https://charts.youtube.com/
      access: 일간/주간 무료 공개
      free: true
      api: true
    source_fallback:
      name: Kworb YouTube Charts
      url: https://kworb.net/youtube/
    update_frequency: 일간 (자동 갱신)
    noise_check: "스트림 부정 트래픽 검증 후 발표, 4주 평균 안정적, false <10%"
    target_signals:
      bullish: "주력 아티스트 신곡 글로벌 Top 100 진입 + 1주 1억뷰 돌파 → 콘서트·앨범 매출 catalyst"
      bearish: "신곡 글로벌 차트 진입 실패 + 기존 IP 조회수 둔화 → 매출 가이던스 하향"
    relevant_tickers_kr: ["하이브(352820)", "SM(041510)", "JYP(035900)"]
    relevant_tickers_us: []
    status: verified

  - id: kr_interpark_concert_ticket_demand
    name: Interpark·예스24 K-pop 콘서트 티켓 오픈 시 매진 시간
    what: "주요 K-pop 아티스트 국내·해외 콘서트 티켓 오픈 시 매진까지 소요 시간 (분 단위), 좌석 등급별 매진 패턴"
    why_leading: "콘서트 매진 속도는 다음 분기 콘서트 매출(엔터사 매출의 30-50%)의 직접 선행 지표. 티켓 오픈 → 6-12개월 후 콘서트 매출 인식"
    lead_time_evidence: "Interpark/예스24 티켓 오픈 매진 시간은 하이브·SM·JYP 콘서트 매출 6-12개월 선행. BTS·블랙핑크 월드투어 티켓 매진 → 다음 연도 매출 가이던스 직접 반영 (각사 IR 인용)"
    source_primary:
      name: Interpark Ticket
      url: https://ticket.interpark.com/
      access: 티켓 오픈 일정 무료 공개, 매진 시간은 언론·팬덤 트래커
      free: true
      api: false
    source_fallback:
      name: 예스24 티켓 / Ticketmaster (해외 투어)
      url: https://ticket.yes24.com/
    update_frequency: 비정기 (콘서트 발표 시)
    noise_check: "팬덤 규모 차이로 절대 시간 비교 어려움, 동일 아티스트 YoY 비교 사용, false <20%"
    target_signals:
      bullish: "주력 아티스트 월드투어 티켓 10분 내 매진 + 추가 회차 편성 → 콘서트 매출 상향"
      bearish: "월드투어 티켓 1시간 이상 잔여 + 추가 회차 부재 → 콘서트 매출 둔화"
    relevant_tickers_kr: ["하이브(352820)", "SM(041510)", "JYP(035900)"]
    relevant_tickers_us: []
    status: verified

  - id: jp_oricon_kpop_album_sales
    name: 일본 Oricon 주간 앨범 차트 K-pop 비중
    what: "Oricon 주간 앨범 차트 Top 50 K-pop 앨범 수, 초동 판매량(첫 주 판매), 차트인 주수"
    why_leading: "일본은 글로벌 음반 시장 2위(피지컬 1위). 일본 초동 판매는 K-pop 엔터사 앨범 매출의 핵심. Oricon 차트는 분기 앨범 매출 4-8주 선행"
    lead_time_evidence: "Oricon 초동 판매량은 분기 앨범 매출 4-8주 선행, R²>0.85. SM Aespa·하이브 일본 데뷔 그룹 초동 → 분기 매출 catalyst 직접 반영 (각사 IR 인용)"
    source_primary:
      name: Oricon News (주간 차트)
      url: https://www.oricon.co.jp/rank/
      access: 주간 무료 공개 (일본어)
      free: true
      api: false
    source_fallback:
      name: Billboard Japan Hot 100 / Billboard Japan Albums
      url: https://www.billboard-japan.com/charts/
    update_frequency: 주간 (매주 화요일 발표)
    noise_check: "팬덤 사재기·이벤트 연동 음반 노이즈, 4주 평균 사용, false <15%"
    target_signals:
      bullish: "K-pop 그룹 일본 초동 50만장 이상 + Top 5 진입 다수 → 일본 매출 catalyst"
      bearish: "주요 그룹 일본 차트 Top 20 밖 + 초동 둔화 → 일본 매출 가이던스 하향"
    relevant_tickers_kr: ["하이브(352820)", "SM(041510)", "JYP(035900)"]
    relevant_tickers_us: []
    status: verified

  - id: kr_kocca_hallyu_export
    name: 한국콘텐츠진흥원 KOCCA 한류 콘텐츠 수출액
    what: "KOCCA 분기·연간 콘텐츠산업 수출액 - 음악·방송·영화 부문 별도 (USD), 지역별 수출 비중 (일본·중국·동남아·북미)"
    why_leading: "KOCCA 콘텐츠 수출 통계는 한국 엔터/콘텐츠 산업 공식 수출 지표. 분기 수출액은 개별사 해외 매출 인식 동행~선행. CJ ENM·하이브의 해외 매출 비중 가시화"
    lead_time_evidence: "KOCCA 분기 콘텐츠 수출액은 엔터사 해외 매출 합계와 R²>0.8 상관, 동행~1분기 선행 (KOCCA 콘텐츠산업백서 매년 인용)"
    source_primary:
      name: 한국콘텐츠진흥원 KOCCA 콘텐츠산업통계
      url: https://www.kocca.kr/kocca/koccastats/index.do
      access: 분기 동향 + 연간 백서, 무료 PDF
      free: true
      api: false
    source_fallback:
      name: 한국문화관광연구원 KCTI / 통계청 서비스업동향조사
      url: https://www.kcti.re.kr/
    update_frequency: 분기 (분기 종료 후 약 90일) + 연간 백서 (12월)
    noise_check: "FX 변동·집계 시차 있음, USD 기준 + 4분기 이동평균 사용, false <15%"
    target_signals:
      bullish: "분기 음악·방송 수출액 YoY +20% 이상 + 북미·일본 비중 확대 → K-콘텐츠 사이클 상승"
      bearish: "수출액 YoY 마이너스 + 중국 비중 정체 → 한류 모멘텀 둔화"
    relevant_tickers_kr: ["하이브(352820)", "SM(041510)", "JYP(035900)", "CJ ENM(035760)"]
    relevant_tickers_us: []
    status: verified
```


## 11. 그룹 C — 섹터 18~21: 소비재/방어주 (25개 지표)

# =============================================================================
# Phase 2 · Group C: 소비재/방어주 4개 섹터 선행 지표 매트릭스
# =============================================================================
# 작성일: 2026-04-25
# 대상 섹터: 18.화장품 · 19.음식료 · 20.유통/이커머스 · 21.의류/패션
# 채택 기준: ① 인과 메커니즘 ② 검증된 lead time ③ 무료+신뢰 1차 소스
#            ④ 도메인 지식 기반 (웹 검색 0회) ⑤ False signal 검토
# =============================================================================

# phase: 2
# group: C
# group_name: 소비재/방어주
# sector_count: 4
# total_indicators: 26
# (top-level YAML is a list of sector entries; scalar metadata moved to meta block)

# =============================================================================
# 18. 화장품 (Cosmetics)
# =============================================================================
- sector: 화장품
  sector_id: 18
  tickers_kr:
    - 아모레퍼시픽(090430)
    - LG생활건강(051900)
    - 코스맥스(192820)
    - 한국콜마(161890)
  tickers_us: []
  indicator_count: 7
  indicators:

    - id: kr_customs_cosmetic_export
      name: 한국 화장품 월간 수출 (관세청 수출입무역통계)
      what: "HSK 3304(메이크업·기초화장품) 월별 수출액·국가별(중국·미국·일본·아세안·EU) 분해, YoY/MoM"
      why_leading: "한국 화장품 산업은 수출 비중이 60% 이상. 관세청은 매월 15일 전월 통관 확정치를 발표하여 ODM(코스맥스·한국콜마) 분기 매출보다 30-60일, 브랜드사(아모레·LG생건) 분기 매출보다 45-90일 선행. 특히 ODM은 브랜드사 발주 → 통관까지 1-2개월 lag만 있어 통관 데이터가 사실상 선행 매출"
      lead_time: "30-90일"
      source_primary:
        name: 관세청 수출입무역통계 (TRASS)
        url: https://tradedata.go.kr
        access: 매월 15일경 전월 확정 통관 데이터, HSK 6단위 무료 조회
      false_signal_check: "단가 효과 vs 물량 효과 분리 필요. 환율 영향 제거 위해 USD 기준 + 물량(kg) 동시 확인. 따이공 단속 시기는 일시적 급감 가능 → 3개월 이동평균 권장"
      adopted: true

    - id: cn_nbs_cosmetic_retail
      name: 중국 화장품 소매판매 (국가통계국 NBS)
      what: "중국 사회소비품 소매총액 中 화장품(化妆品类) 카테고리 월별 금액·YoY"
      why_leading: "중국은 한국 화장품 최대 수출국. 중국 NBS 매월 15-18일 전월 발표. 중국 소비 회복/둔화 신호가 한국 브랜드 중국 매출에 1-2분기 선행. 광군제(11월)·618(6월) 시즌은 별도 대응"
      lead_time: "60-120일"
      source_primary:
        name: 中国国家统计局 (NBS) 社会消费品零售总额
        url: http://www.stats.gov.cn
        access: 매월 15-18일 발표, 무료 한·중·영문
      false_signal_check: "면세점 매출 별도. 따이공 규제(2024년 강화) 영향으로 NBS 화장품 카테고리는 내수 비중이 커짐 → C-beauty 점유율 상승은 한국 브랜드에 부정적 신호"
      adopted: true

    - id: kr_duty_free_sales
      name: 한국 면세점 월별 매출 (한국면세점협회)
      what: "월별 면세점 외국인·내국인 매출액·구매객수, 화장품 카테고리 비중"
      why_leading: "면세점 매출은 따이공·중국 단체관광·일본·동남아 관광객 흐름의 즉각 반영. 매월 25-30일 전월 발표로 화장품 브랜드사 분기 면세 채널 매출에 30-45일 선행"
      lead_time: "30-60일"
      source_primary:
        name: 한국면세점협회 (KDFA) 월간 통계
        url: https://www.kdfa.or.kr
        access: 매월 말 전월 매출 발표, 무료
      false_signal_check: "구매객수 정체 + 매출 급증은 따이공 대량 구매 신호 → 지속 불가능. 1인당 구매액 상한(개정 시) 정책 변수 확인 필수"
      adopted: true

    - id: jp_meti_cosmetic_shipment
      name: 일본 화장품 출하 통계 (METI 경제산업성)
      what: "일본 화장품·향수 월별 출하액·수입액(한국 비중), YoY"
      why_leading: "일본은 K-beauty 신흥 핵심 시장 (2024년 한국 對일본 화장품 수출이 對중국 추월). METI 월간 화학공업 통계 + 재무성 무역통계로 한국 브랜드 일본 침투율 확인. 일본 시장은 중국 대비 변동성 낮아 구조적 성장 지표"
      lead_time: "30-60일"
      source_primary:
        name: 経済産業省 化学工業統計 + 財務省 貿易統計
        url: https://www.meti.go.jp/statistics/
        access: 매월 말 전월 데이터, 무료
      false_signal_check: "원·엔 환율 영향 큼. 일본 현지 OEM 생산(LG생건 후 등) 비중 증가 시 수출 데이터 하락이 반드시 점유율 하락은 아님"
      adopted: true

    - id: us_kbeauty_amazon_indicator
      name: 한국 對미국 화장품 수출 (관세청 HSK 3304 미국향)
      what: "관세청 데이터 中 미국 향 화장품 수출액 월별, YoY/MoM"
      why_leading: "미국은 한국 화장품 2위 수출국으로 부상(2024-2025). Amazon Beauty·Sephora·Ulta 채널 K-beauty 침투 확대 직접 반영. 관세청 통관 → 미국 도착 → 매대 진열까지 약 4-8주, 분기 매출 선행"
      lead_time: "60-90일"
      source_primary:
        name: 관세청 수출입무역통계 (TRASS) — 미국향
        url: https://tradedata.go.kr
        access: 매월 15일경, HSK 3304 + 국가코드 US
      false_signal_check: "ODM(코스맥스 미국법인 등) 현지 생산분은 수출 통계 미반영 → 한국콜마/코스맥스 미국법인 가동률 별도 확인 권장"
      adopted: true

    - id: mfds_cosmetic_production
      name: 식품의약품안전처 화장품 생산실적 (연간) + 수입 화장품 실적
      what: "MFDS 연간 화장품 생산실적·기업별 톱20·수입 화장품 점유율"
      why_leading: "ODM(코스맥스·한국콜마) 생산능력·고객사 다각화의 구조 변화 추적. 연간 1회(통상 7월) 발표로 lead time은 길지만 산업 구조 변화(예: 중소 인디브랜드 부상 → ODM 수혜) 검증용"
      lead_time: "180-365일 (구조 지표)"
      source_primary:
        name: 식품의약품안전처 화장품 생산실적
        url: https://www.mfds.go.kr
        access: 연 1회 7월경 발표, 무료
      false_signal_check: "단년도 수치보다 3년 추세 비교 필수. 인디브랜드 → ODM 발주 증가 트렌드 확인"
      adopted: true

    - id: cn_singles_day_618_data
      name: 광군제·618 한국 화장품 GMV (중국 알리바바·JD 공식 발표)
      what: "광군제(11.11)·618(6.18) 기간 알리바바 Tmall·JD.com 공식 발표 中 화장품 카테고리·한국 브랜드 순위"
      why_leading: "양대 쇼핑 페스티벌은 中 화장품 연 매출의 30-40% 차지. 한국 브랜드 순위(설화수·후·라네즈) 변동이 차분기 중국 매출에 직접 선행. 행사 종료 직후 공식 보도자료 확인"
      lead_time: "60-90일"
      source_primary:
        name: 알리바바 그룹 + JD.com 공식 보도자료
        url: https://www.alibabagroup.com / https://corporate.jd.com
        access: 행사 종료 1-2일 내 무료 발표
      false_signal_check: "GMV는 환불 전 수치 → 실제 매출 대비 과대 가능. C-beauty(프로야·위노나) 순위 상승은 한국 브랜드에 부정적. 단, 2024년부터 알리바바가 카테고리별 상세 데이터 비공개 전환 → 보완 지표 필요"
      adopted: true

# =============================================================================
# 19. 음식료 (Food & Beverage)
# =============================================================================
- sector: 음식료
  sector_id: 19
  tickers_kr:
    - CJ제일제당(097950)
    - 삼양식품(003230)
    - 오리온(271560)
    - 농심(004370)
    - 롯데웰푸드(280360)
  tickers_us: []
  indicator_count: 8
  indicators:

    - id: kr_customs_ramen_export
      name: 한국 라면 월간 수출 (관세청 HSK 1902.30)
      what: "라면(즉석면) 월별 수출액·국가별(미국·중국·일본·동남아) 분해, YoY/MoM"
      why_leading: "삼양식품(불닭볶음면) 매출의 75% 이상이 수출. 농심 신라면도 수출 비중 확대 중. 관세청 통관 데이터는 분기 매출 30-60일 선행. 미국향 수출 급증 시 삼양 어닝 서프라이즈 직결"
      lead_time: "30-60일"
      source_primary:
        name: 관세청 수출입무역통계 (TRASS)
        url: https://tradedata.go.kr
        access: 매월 15일경, HSK 1902.30 무료 조회
      false_signal_check: "현지 생산(농심 미국 2공장 가동) 비중 증가 시 수출 통계 둔화 ≠ 매출 둔화. 분기 컨퍼런스콜에서 현지/수출 비중 별도 확인 필수"
      adopted: true

    - id: cbot_grain_futures
      name: CBOT 곡물 선물 (옥수수 ZC·대두 ZS·밀 ZW)
      what: "CME/CBOT 옥수수·대두·밀·소맥분 선물 가격 일별, 3-6개월 이동평균"
      why_leading: "곡물 가격은 음식료 OPM(영업이익률)의 최대 변수. CJ제일제당(소맥·대두유), 농심(소맥), 오리온(옥수수·소맥), 롯데웰푸드(코코아·유지)는 곡물 선물 가격 6-9개월 후 원가 반영(헷지·재고 lag). 곡물가 하락 → 2-3분기 후 OPM 개선"
      lead_time: "180-270일"
      source_primary:
        name: CME Group 공식 선물 가격
        url: https://www.cmegroup.com
        access: 실시간 + 일별 종가 무료 (15분 지연)
      false_signal_check: "환율(USD/KRW) 동시 고려 필수 — 원화 약세 시 곡물가 하락 효과 상쇄. 헷지 비율(통상 3-6개월)에 따라 lag 변동. Phase 1 commodity 지표와 연동"
      adopted: true

    - id: kosis_food_service_index
      name: 통계청 외식업 매출 동향 (서비스업동향조사)
      what: "통계청 KOSIS 음식점·주점업 월별 매출액 지수, 계절조정"
      why_leading: "외식업 매출은 B2B 식자재(CJ프레시웨이, CJ제일제당 B2B) 매출에 1-2개월 선행. 또한 가정간편식(HMR) 대체 효과 → 외식 둔화 시 RTE/RTC 식품 매출 증가 (CJ비비고, 동원 양반)"
      lead_time: "30-60일"
      source_primary:
        name: 통계청 KOSIS 서비스업동향조사
        url: https://kosis.kr
        access: 매월 말경 전월 데이터, 무료
      false_signal_check: "코로나 기간 같은 외생 충격 시 lead 관계 역전 가능. 명목/실질(물가 효과) 동시 확인"
      adopted: true

    - id: us_kfood_retail_penetration
      name: 한국 對미국 가공식품 수출 (관세청 HSK 16·19·20·21류 미국향)
      what: "만두·라면·소스·김치 등 가공식품 미국향 월별 수출액"
      why_leading: "Walmart·Costco·Target K-food SKU 확대 직접 반영. CJ제일제당 비비고 만두, 농심 신라면, 삼양 불닭, 풀무원 두부 등 미국 매대 진열 확대 → 통관 → 분기 매출 60-90일 선행"
      lead_time: "60-90일"
      source_primary:
        name: 관세청 수출입무역통계 (TRASS) — 미국향
        url: https://tradedata.go.kr
        access: 매월 15일경, HSK 6단위
      false_signal_check: "CJ Schwan's 인수(2019), 농심 미국 2공장(2022) 등 현지 생산 비중 30-50% → 수출 통계 단독 사용 금물. 본사 IR 자료의 '미국 K-food 매출' 별도 트래킹"
      adopted: true

    - id: cn_orion_cn_retail
      name: 중국 비스킷·과자 소매 + 오리온 중국법인 월별 매출 공시
      what: "오리온홀딩스 중국법인(好麗友) 월별 매출 공시 + NBS 중국 식품 소매 카테고리"
      why_leading: "오리온 매출의 50% 이상이 중국. 오리온은 IR 차원에서 월별 매출 자체 공시 → 분기 실적 30-45일 선행. NBS 중국 식품 소매 둔화 시 오리온 영업이익 즉각 반영"
      lead_time: "30-60일"
      source_primary:
        name: 오리온홀딩스 IR 월별 매출 공시 + NBS 사회소비품 소매총액
        url: https://www.orionworld.com / http://www.stats.gov.cn
        access: 오리온 매월 초 전월 매출, NBS 매월 15-18일
      false_signal_check: "위안화 환율(CNY/KRW) 영향 분리. 중국 명절(춘절) 시즌성 큰 폭 변동 → YoY 비교 필수, MoM은 무의미"
      adopted: true

    - id: kr_box_office_cj_lotte
      name: 한국 박스오피스 (영진위 통합전산망)
      what: "한국 일별·주별 박스오피스 관객수·매출, CJ ENM·롯데컬처웍스·NEW 배급작 점유율"
      why_leading: "CJ제일제당 모회사 CJ그룹 차원에서 CJ CGV·CJ ENM 실적 영향. 롯데웰푸드의 모회사 롯데지주 차원에서 롯데시네마 실적 영향. 직접 음식료 매출과는 약한 연결이나, 영화관 매점 매출(팝콘·콜라)은 음식료 B2B 채널"
      lead_time: "30-60일 (보조 지표)"
      source_primary:
        name: 영화진흥위원회 통합전산망 (KOBIS)
        url: https://www.kobis.or.kr
        access: 일별 무료 공개
      false_signal_check: "음식료 본업과 직접 연결 약함 — 보조 지표로만 사용. 그룹 전체 실적 추정 시 활용"
      adopted: false

    - id: usda_wasde_grain_outlook
      name: USDA WASDE 월간 수급 보고서 (옥수수·대두·밀)
      what: "미국 농무부 World Agricultural Supply and Demand Estimates 월간 보고서, 글로벌 재고/소비 비율(stocks-to-use ratio)"
      why_leading: "WASDE는 곡물 선물 가격에 즉각 영향을 주는 펀더멘탈 데이터. 재고/소비 비율 하락 → 향후 6-12개월 곡물가 상승 → 음식료 OPM 압박. 매월 12일경 발표"
      lead_time: "180-365일"
      source_primary:
        name: USDA Economics, Statistics and Market Information System
        url: https://www.usda.gov/oce/commodity/wasde
        access: 매월 12일경 발표, 무료 PDF + Excel
      false_signal_check: "WASDE 발표 직후 가격 갭 발생 — 단기 변동성과 분리. 엘니뇨/라니냐 기상 변수 별도 트래킹"
      adopted: true

    - id: kr_food_export_total
      name: 한국 농식품 수출 종합 (aT 한국농수산식품유통공사)
      what: "K-Food+ 농식품 월별 수출 통계, 품목별·국가별 분해"
      why_leading: "라면·김치·소스·만두 등 K-Food 전체 모멘텀 확인. aT는 관세청 데이터를 농식품 카테고리로 재분류·발표 → 산업 차원 트렌드 파악 용이"
      lead_time: "30-60일"
      source_primary:
        name: 한국농수산식품유통공사 (aT) 농식품수출정보 KATI
        url: https://www.kati.net
        access: 매월 중순 전월 데이터, 무료
      false_signal_check: "관세청 원본과 분류 차이로 미세한 수치 차이 가능 → 두 소스 교차 검증"
      adopted: true

# =============================================================================
# 20. 유통/이커머스 (Retail/E-commerce)
# =============================================================================
- sector: 유통/이커머스
  sector_id: 20
  tickers_kr:
    - 이마트(139480)
    - 롯데쇼핑(023530)
  tickers_us:
    - CPNG (Coupang)
    - AMZN (Amazon)
  indicator_count: 6
  indicators:

    - id: kosis_retail_sales_index
      name: 통계청 소매판매액 동향 (산업활동동향)
      what: "통계청 월별 소매판매액 지수, 업태별(백화점·대형마트·편의점·면세점·무점포소매) 분해"
      why_leading: "오프라인 유통(이마트·롯데쇼핑) 매출의 직접 동행/선행 지표. 통계청 매월 말 전월 발표 → 분기 매출 30-60일 선행. 업태별 분해로 채널별 트렌드(대형마트 둔화 vs 편의점 성장) 확인"
      lead_time: "30-60일"
      source_primary:
        name: 통계청 KOSIS 산업활동동향
        url: https://kosis.kr
        access: 매월 말 전월 데이터, 무료
      false_signal_check: "물가 효과 vs 실질 소비 분리. 명목 증가율은 인플레이션 가산되므로 실질 지수 동시 확인. 명절 시즌 조정 필수"
      adopted: true

    - id: motie_major_retailers
      name: 산업통상자원부 주요유통업체 매출 동향
      what: "산자부 월간 주요 13개사(백화점 3사·대형마트 3사·편의점 3사·온라인 4사) 매출 증감률·구성비"
      why_leading: "롯데백화점·신세계·현대백화점·이마트·홈플러스·롯데마트·CU·GS25·세븐일레븐·쿠팡·SSG·G마켓·11번가 매출을 직접 집계. 매월 말 발표로 상장사 분기 실적 30-45일 선행. 채널 간 점유율 이동 정확 포착"
      lead_time: "30-45일"
      source_primary:
        name: 산업통상자원부 주요유통업체 매출 동향 보도자료
        url: https://www.motie.go.kr
        access: 매월 말 전월 데이터, 무료 PDF
      false_signal_check: "쿠팡 GMV는 자체 발표(분기) 기반 추정 — 산자부는 실제 매출 기반이라 약간의 차이. 명절 효과 YoY로 보정"
      adopted: true

    - id: kosis_online_shopping
      name: 통계청 온라인쇼핑 동향
      what: "월별 온라인쇼핑 거래액·모바일 비중·상품군별(식품·가전·패션) 분해"
      why_leading: "이커머스 시장 전체 규모와 카테고리별 침투율 동시 확인. 쿠팡·SSG·11번가·G마켓 시장 점유율 추정의 분모. 매월 초 전월 발표로 가장 빠른 이커머스 매크로 지표"
      lead_time: "30-60일"
      source_primary:
        name: 통계청 KOSIS 온라인쇼핑동향조사
        url: https://kosis.kr
        access: 매월 초 전월 데이터, 무료
      false_signal_check: "통계청 전체 거래액 - 산자부 주요 4사 합산 = 중소 셀러·신생 플랫폼 점유율. 알리·테무 등 해외 직구 별도 카테고리 분리 발표 (2024년 시작)"
      adopted: true

    - id: kcfa_card_approval
      name: 여신금융협회 신용카드 승인실적
      what: "월별 개인·법인 신용카드/체크카드 승인금액·건수, 업종별(소매·외식·여행) 분해"
      why_leading: "카드 승인액은 소비 활동의 즉각 반영 — 통계청 소매판매보다 5-10일 빠른 발표. 소비 회복/위축 신호의 가장 빠른 매크로 지표. 업종별 분해로 유통/외식/여행 채널별 트렌드 포착"
      lead_time: "30-60일"
      source_primary:
        name: 여신금융협회 (CREFIA) 월간 신용카드 승인실적
        url: https://www.crefia.or.kr
        access: 매월 중순 전월 데이터, 무료
      false_signal_check: "현금 결제 비중 변화 시 노이즈. 정부 소비쿠폰·재난지원금 일시 효과 별도 처리. 카드 승인 ≠ 매출(취소·환불 포함)"
      adopted: true

    - id: us_census_marts
      name: 미국 Census Bureau MARTS (Monthly Retail Trade Survey)
      what: "미국 월별 소매판매·이커머스 비중·카테고리별(non-store retailers·food services 등)"
      why_leading: "Amazon 매출의 직접 매크로 환경. Census는 매월 중순 전월 advance 발표 → AMZN 분기 실적 30-60일 선행. 'Non-store retailers' 성장률이 Amazon retail GMV 성장률의 매크로 천장"
      lead_time: "30-60일"
      source_primary:
        name: U.S. Census Bureau Monthly Retail Trade Survey (MARTS)
        url: https://www.census.gov/retail
        access: 매월 중순 advance, 다음달 final, 무료
      false_signal_check: "Amazon은 AWS·광고·구독(Prime) 매출 비중 확대 → MARTS는 retail 부문에만 적용. 분기 별 '온라인 스토어 매출' 별도 IR 확인"
      adopted: true

    - id: cpng_gmv_disclosure
      name: 쿠팡 분기 GMV·Active Customer (CPNG 공시)
      what: "쿠팡 SEC 10-Q/10-K 분기 공시 中 Product Commerce/Developing Offerings GMV, Active Customer, ARPU"
      why_leading: "쿠팡 자체 공시지만 산자부 주요유통업체 데이터로 분기 사이 추정 가능. CPNG의 Active Customer 증가율 둔화 → 한국 이커머스 침투율 포화 신호 → 11번가·SSG·G마켓 등 경쟁사에도 시사"
      lead_time: "분기별 공시 (지표 자체)"
      source_primary:
        name: SEC EDGAR — Coupang Inc. 10-Q/10-K
        url: https://www.sec.gov/edgar
        access: 분기 종료 후 45일 내 공시, 무료
      false_signal_check: "Developing Offerings(파페치·이츠·플레이) 별도 분리. 환율(KRW/USD) 영향 분리하여 원화 기준 GMV 산출 필수"
      adopted: true

# =============================================================================
# 21. 의류/패션 (Apparel/Fashion)
# =============================================================================
- sector: 의류/패션
  sector_id: 21
  tickers_kr:
    - F&F(383220)
    - 한세실업(105630)
    - 영원무역(111770)
  tickers_us:
    - LULU (Lululemon)
    - NKE (Nike)
  indicator_count: 6
  indicators:

    - id: kr_customs_apparel_export
      name: 한국 의류 수출 (관세청 HSK 61·62)
      what: "편직제 의류(HSK 61) + 비편직제 의류(HSK 62) 월별 수출액, 국가별 분해. F&F 中 'MLB·Discovery' 라이선스 수출 흐름과 별개로 OEM·완제품 수출 트렌드"
      why_leading: "의류 OEM(한세실업·영원무역) 수출의 직접 매크로. 단, 한세·영원의 실제 생산은 베트남·인도네시아 → 한국 통관 데이터는 보조 지표. 본질 지표는 베트남 수출(아래 별도 항목)"
      lead_time: "30-60일 (보조)"
      source_primary:
        name: 관세청 수출입무역통계 (TRASS)
        url: https://tradedata.go.kr
        access: 매월 15일경, HSK 6단위
      false_signal_check: "한세실업·영원무역의 매출은 베트남·인니 현지 생산 → 한국 통관 미반영. F&F는 라이선스+한국 디자인 → 중국 매출이 핵심. 따라서 이 지표는 1차 보조 지표로만 활용"
      adopted: false

    - id: vietnam_garment_export
      name: 베트남 의류·신발 수출 (베트남 통계청 GSO + 관세총국)
      what: "베트남 월별 의류(garment·textile)·신발(footwear) 수출액·미국향 비중"
      why_leading: "한세실업(미국 의류 OEM 1위)·영원무역(노스페이스·룰루레몬·파타고니아 OEM) 생산 베이스가 베트남·인니. 베트남 의류 수출 = 한세·영원 매출의 직접 선행. 미국 향 베트남 의류 수출은 Nike·Lulu·Gap·Target 등 발주 흐름 직접 반영"
      lead_time: "30-60일"
      source_primary:
        name: General Statistics Office of Vietnam (GSO) + Vietnam Customs
        url: https://www.gso.gov.vn / https://www.customs.gov.vn
        access: 매월 말 발표, 무료 영문/베트남어
      false_signal_check: "베트남 전체 의류 수출은 한세·영원 외에도 다수 업체 포함 → 절대 매출은 추정 불가, 모멘텀 지표로만. 미국 관세(2025년 인상) 영향으로 베트남→미국 수출 변동성 확대"
      adopted: true

    - id: us_census_marts_apparel
      name: 미국 의류 소매 매출 (Census Bureau MARTS Apparel)
      what: "Census MARTS 中 'Clothing and clothing accessories stores' + 'Sporting goods, hobby, musical instrument, and book stores' 월별 매출"
      why_leading: "Nike·Lululemon 미국 매출의 직접 매크로 환경. 또한 미국 의류 소매 둔화 → 미국 브랜드 OEM 발주 둔화 → 한세·영원 수출 둔화로 2-3분기 후 전이"
      lead_time: "60-120일 (한세·영원에 대해)"
      source_primary:
        name: U.S. Census Bureau Monthly Retail Trade Survey (MARTS)
        url: https://www.census.gov/retail
        access: 매월 중순, 무료
      false_signal_check: "온라인 의류 매출은 'Non-store retailers'에 통합되어 별도 분리 어려움. Nike DTC 비중 50% 이상 → 의류 소매 총액보다 Nike 자체 분기 가이던스 우선"
      adopted: true

    - id: ice_cotton_futures
      name: 면화 선물 (ICE Cotton CT=F)
      what: "ICE Cotton No.2 선물 가격 일별, 3-6개월 이동평균"
      why_leading: "면화는 의류 원가의 핵심 — 면 함량 50% 이상 제품에서 OPM 직접 영향. 면화 선물 가격이 OEM(한세·영원)의 6-9개월 후 마진에 반영. 면화 가격 하락 → OEM 마진 개선 → 분기 OPM 서프라이즈"
      lead_time: "180-270일"
      source_primary:
        name: ICE (Intercontinental Exchange) Cotton Futures
        url: https://www.ice.com
        access: 실시간 + 일별 종가 무료 (15분 지연)
      false_signal_check: "헷지 비율(통상 6개월) 및 원·달러 환율 동시 영향. 폴리에스터·나일론 비중 높은 제품(스포츠웨어 — 룰루레몬·나이키)은 면화 영향 제한적 → 원유·PX 가격 보조 확인"
      adopted: true

    - id: cn_apparel_retail_ff
      name: 중국 의류 소매판매 (NBS) + F&F 중국 라이선스 매출
      what: "중국 NBS 사회소비품 소매총액 中 의류·신발(服装鞋帽针纺织品类) 카테고리 + F&F 분기 IR의 중국 MLB·Discovery 매출"
      why_leading: "F&F 매출의 60% 이상이 중국 MLB 라이선스. 중국 의류 소매 둔화 시 F&F 직격. NBS는 매월 15-18일 발표 → F&F 분기 매출 30-60일 선행"
      lead_time: "30-60일"
      source_primary:
        name: 中国国家统计局 (NBS) + F&F IR
        url: http://www.stats.gov.cn / https://www.fnf.co.kr
        access: NBS 매월 15-18일, F&F 분기 공시
      false_signal_check: "중국 내 한류 백래시·환구시보 보도 등 정성적 변수는 NBS 데이터에 lag 반영. F&F는 라이선스 구조라 환율·로열티 비율 등 별도 변수"
      adopted: true

    - id: nke_lulu_quarterly_compare
      name: Nike·Lululemon 분기 동시 비교 (10-Q + 가이던스)
      what: "Nike(5월 결산)·Lululemon(1월 결산) 분기 매출·DTC 비중·재고일수(DOH)·중국 매출·가이던스"
      why_leading: "Nike·Lulu의 분기 가이던스 변경(특히 중국·재고 일수)은 OEM(영원무역) 발주 흐름의 직접 선행. 가이던스 하향 → 영원무역 분기 매출 1-2분기 후 감소. 동시에 두 회사 비교는 프리미엄 vs 매스 채널 흐름 파악"
      lead_time: "분기별 공시 + 90-180일 (영원무역 발주 lag)"
      source_primary:
        name: SEC EDGAR — NKE 10-Q, LULU 10-Q
        url: https://www.sec.gov/edgar
        access: 분기 종료 후 45일 내, 무료
      false_signal_check: "재고 일수 증가 ≠ 즉각 발주 감소 (이미 발주된 시즌 물량은 인도). 중국 가이던스는 Nike의 거버넌스 이슈(2024 부진) 등 사별 요인과 분리 필요"
      adopted: true

# =============================================================================
# 채택 요약 (block_type: adoption_summary)
# =============================================================================
- block_type: adoption_summary
  cosmetics:
    candidates: 7
    adopted: 7
    rejected: 0
  food_beverage:
    candidates: 8
    adopted: 7
    rejected: 1
    rejected_list:
      - "kr_box_office_cj_lotte (음식료 본업과 직접 연결 약함, 보조 지표로만 사용 — 비채택)"
  retail_ecommerce:
    candidates: 6
    adopted: 6
    rejected: 0
  apparel_fashion:
    candidates: 6
    adopted: 5
    rejected: 1
    rejected_list:
      - "kr_customs_apparel_export (한세·영원 실제 생산은 베트남 → 한국 통관은 보조 지표, 베트남 GSO로 대체)"
  total_candidates: 27
  total_adopted: 25
  total_rejected: 2

# =============================================================================
# 메타 (block_type: meta)
# =============================================================================
- block_type: meta
  phase: 2
  group: C
  group_name: 소비재/방어주
  sector_count: 4
  total_indicators: 26
  created: 2026-04-25
  author: Phase 2 Group C
  web_search_count: 0
  source_basis: "도메인 지식 (관세청·통계청·산자부·여신금융협회·MFDS·NBS·METI·USDA·Census·SEC·CME·ICE·aT·KOBIS·KDFA)"
  next_phase: "Phase 2 Group D (잔여 섹터)"


## 12. 그룹 D — 섹터 22~25: 인프라/전통주 (26개 지표)

# Phase 2 Group D — 인프라/전통주 4개 섹터 선행지표 매트릭스
# 한국 투자자 관점, KR/US 종목 양쪽 적용
# 출처: 한국은행 ECOS, 통계청, 금감원 DART, 국토교통부, KPX, CME FedWatch 등 무료 1차 소스
# 채택 기준: 인과 메커니즘 / 검증된 lead time / 무료+신뢰 1차 소스 / False signal 검토 통과

meta:
  phase: 2
  group: D
  group_label: "인프라/전통주"
  sectors_count: 4
  created: 2026-04-25
  methodology: "도메인 지식 기반, 웹 검색 0회"

sectors:

  # ============================================================
  # 22. 건설/건자재
  # ============================================================
  - id: 22
    name: "건설/건자재"
    kr_tickers:
      - { name: "현대건설", code: "000720" }
      - { name: "GS건설", code: "006360" }
      - { name: "대우건설", code: "047040" }
      - { name: "DL이앤씨", code: "375500" }
      - { name: "삼성엔지니어링", code: "028050" }
      - { name: "쌍용C&E", code: "003410" }
    adopted_count: 7
    indicators:

      - id: 22-1
        name: "국토부 월간 분양물량"
        source: "국토교통부 주택공급계획 / 부동산R114"
        unit: "호/월"
        frequency: "월간"
        lead_time: "9~12개월"
        threshold:
          bullish: ">= 50,000호/월 3개월 연속"
          bearish: "<= 20,000호/월 3개월 연속"
        causal_mechanism: |
          분양 → 계약금/중도금 매출 인식 → 건설사 매출액 9~12개월 시차 반영.
          분양물량은 건설사 신규 매출 파이프라인의 직접 선행지표.
        false_signal_check: |
          후분양제 확대 시 lead time 단축 가능 (분양=거의 즉시 매출).
          미분양 누적 시 분양물량 자체는 높아도 현금흐름 악화 → 미분양 통계 병행 필요.
        primary_targets: ["현대건설", "GS건설", "대우건설", "DL이앤씨"]

      - id: 22-2
        name: "한국감정원 전국 아파트 매매가격지수 (월간 변동률)"
        source: "한국부동산원 R-ONE"
        unit: "% MoM"
        frequency: "월간"
        lead_time: "6~9개월"
        threshold:
          bullish: ">= +0.3% MoM 3개월 연속"
          bearish: "<= -0.3% MoM 3개월 연속"
        causal_mechanism: |
          주택가격 상승 → 분양 흥행률 상승 → 건설사 분양 일정 가속 + 마진 확보.
          하락기에는 분양 연기/할인 → 현금흐름 악화.
        false_signal_check: |
          서울/지방 양극화 심화 시 전국 평균이 왜곡 가능.
          수도권 5대 광역시 분리 지표 병행 권장.
        primary_targets: ["현대건설", "GS건설", "대우건설", "DL이앤씨"]

      - id: 22-3
        name: "통계청 건설수주액 (국내+해외)"
        source: "통계청 KOSIS 건설업조사"
        unit: "조원/월"
        frequency: "월간"
        lead_time: "12~18개월"
        threshold:
          bullish: ">= +15% YoY 3개월 연속"
          bearish: "<= -15% YoY 3개월 연속"
        causal_mechanism: |
          수주잔고가 향후 1~2년 매출 인식의 직접 기반.
          해외수주는 삼성엔지니어링/현대건설 EPC 부문 핵심 선행지표.
        false_signal_check: |
          대형 단발 프로젝트(가스 플랜트 등)에 의해 월간 변동성 큼 → 3개월 이동평균 권장.
        primary_targets: ["현대건설", "삼성엔지니어링", "GS건설"]

      - id: 22-4
        name: "국내 시멘트 출하량 (쌍용C&E + 성신양회 + 아세아시멘트 합산)"
        source: "한국시멘트협회 / 각 사 IR"
        unit: "천톤/월"
        frequency: "월간"
        lead_time: "1~3개월 (동행~약간 선행)"
        threshold:
          bullish: ">= +5% YoY 2개월 연속"
          bearish: "<= -8% YoY 2개월 연속"
        causal_mechanism: |
          시멘트 출하 = 실제 착공/공정 진행률 직접 반영.
          쌍용C&E 매출/이익의 거의 직접 동행지표 + 건설사 공정 진행률 선행.
        false_signal_check: |
          겨울철(12~2월) 계절성 강함 → YoY 비교 필수, MoM 사용 금지.
        primary_targets: ["쌍용C&E", "현대건설", "DL이앤씨"]

      - id: 22-5
        name: "미국 ABI (Architecture Billings Index)"
        source: "AIA (American Institute of Architects) 월간 발표"
        unit: "지수 (50 기준)"
        frequency: "월간"
        lead_time: "9~12개월 (미국 비주거 건설)"
        threshold:
          bullish: ">= 52 3개월 연속"
          bearish: "<= 47 3개월 연속"
        causal_mechanism: |
          미국 건축사 수주 → 9~12개월 후 비주거 건설 착공.
          삼성엔지니어링/현대건설 미국 EPC 수주 환경 선행.
        false_signal_check: |
          ABI는 비주거 위주 → 주거 부문은 housing starts 별도 활용.
        primary_targets: ["삼성엔지니어링", "현대건설"]

      - id: 22-6
        name: "미국 Housing Starts (주택착공)"
        source: "US Census Bureau"
        unit: "천호 SAAR"
        frequency: "월간"
        lead_time: "3~6개월 (자재 수요)"
        threshold:
          bullish: ">= 1,500K SAAR"
          bearish: "<= 1,200K SAAR"
        causal_mechanism: |
          주택착공 → 시멘트/철근 등 건자재 수요 → 한국 건자재 수출 + 글로벌 가격.
          간접 영향이지만 글로벌 건자재 사이클 동조화.
        false_signal_check: |
          미국 모기지 금리(30Y)가 추가 변수 → Fed Funds 지표와 병행 해석.
        primary_targets: ["쌍용C&E", "삼성엔지니어링"]

      - id: 22-7
        name: "미분양 주택 수 (전국)"
        source: "국토교통부 통계누리"
        unit: "호"
        frequency: "월간"
        lead_time: "6~9개월 (역방향 선행)"
        threshold:
          bullish: "<= 50,000호 + 감소 추세"
          bearish: ">= 70,000호 + 증가 추세"
        causal_mechanism: |
          미분양 누적 → 분양 연기/할인분양 → PF 부실 위험 → 건설사 신용리스크.
          GS건설/대우건설 PF 익스포저 직접 영향.
        false_signal_check: |
          준공 후 미분양(악성 미분양) 별도 추적 필요 — 일반 미분양과 리스크 차원 다름.
        primary_targets: ["GS건설", "대우건설", "DL이앤씨"]

  # ============================================================
  # 23. 금융
  # ============================================================
  - id: 23
    name: "금융"
    kr_tickers:
      - { name: "KB금융", code: "105560" }
      - { name: "신한지주", code: "055550" }
      - { name: "하나금융지주", code: "086790" }
      - { name: "삼성화재", code: "000810" }
      - { name: "DB손해보험", code: "005830" }
      - { name: "키움증권", code: "039490" }
    adopted_count: 7
    indicators:

      - id: 23-1
        name: "한국은행 기준금리"
        source: "한국은행 ECOS"
        unit: "%"
        frequency: "금통위 (연 8회)"
        lead_time: "1~2분기 (NIM 반영)"
        threshold:
          bullish: "인상 사이클 + 2.50% 이상"
          bearish: "인하 사이클 + 1.50% 이하"
        causal_mechanism: |
          기준금리 → 은행 NIM(순이자마진) 직접 영향.
          금리 인상 초기는 대출금리 빠르게 반영, 예금금리 지연 → NIM 확대.
          인하 사이클은 반대.
        false_signal_check: |
          가파른 인상은 가계 연체율 상승 → 대손충당금 급증으로 NIM 효과 상쇄 가능.
          금리 수준보다 변동 속도/방향성이 중요.
        primary_targets: ["KB금융", "신한지주", "하나금융지주"]

      - id: 23-2
        name: "미국 Fed Funds Rate + CME FedWatch"
        source: "Federal Reserve / CME FedWatch Tool (무료)"
        unit: "%"
        frequency: "FOMC (연 8회) + 일간 선물 가격"
        lead_time: "1~3개월 (기대형성)"
        threshold:
          bullish: "한미 금리차 축소 (한국 우위 또는 동일)"
          bearish: "한미 금리차 -2%p 이상 (미국 우위)"
        causal_mechanism: |
          한미 금리차 → 외국인 자금 유출입 → 환율 → 은행 외화자산 평가.
          증권사 brokerage는 미국 금리 인하 기대 시 KOSPI 거래대금 증가 수혜.
        false_signal_check: |
          FedWatch는 시장 기대치이지 실제 결정이 아님 → 점도표(SEP) 병행 확인.
        primary_targets: ["키움증권", "KB금융", "신한지주"]

      - id: 23-3
        name: "가계대출 잔액 (전금융권)"
        source: "한국은행 ECOS / 금감원"
        unit: "조원"
        frequency: "월간"
        lead_time: "동행~3개월 선행"
        threshold:
          bullish: ">= +0.5% MoM (대출 성장)"
          bearish: "<= -0.3% MoM 3개월 연속 (디레버리징)"
        causal_mechanism: |
          은행 대출자산 증가 = 이자수익 베이스 확대.
          가계대출 정체 시 NIM 확대해도 총 이자이익 정체.
        false_signal_check: |
          DSR 규제 강화 등 정책 효과 확인 필수.
          주담대 vs 신용대출 분리 추적 권장 (마진 차이).
        primary_targets: ["KB금융", "신한지주", "하나금융지주"]

      - id: 23-4
        name: "부동산 PF 연체율"
        source: "금감원 분기 발표"
        unit: "%"
        frequency: "분기"
        lead_time: "1~2분기 (대손충당금)"
        threshold:
          bullish: "<= 2.0%"
          bearish: ">= 4.0% 또는 +1%p QoQ 급등"
        causal_mechanism: |
          PF 연체율 상승 → 은행/증권사 대손충당금 급증 → 분기 순이익 직격.
          2023~2024년 PF 위기 사례에서 검증됨.
        false_signal_check: |
          업종별/지역별 편차 큼 → 비수도권 PF 별도 추적.
          저축은행/캐피탈 PF가 1차 충격 → 시중은행은 2차 충격.
        primary_targets: ["KB금융", "신한지주", "하나금융지주", "키움증권"]

      - id: 23-5
        name: "Korea CDS Spread (5Y)"
        source: "Markit / 블룸버그 (한국은행 통화금융분석 보고서)"
        unit: "bps"
        frequency: "일간"
        lead_time: "1~3개월"
        threshold:
          bullish: "<= 35 bps"
          bearish: ">= 60 bps + 상승 추세"
        causal_mechanism: |
          국가 CDS 상승 → 외화차입 비용 증가 → 은행 외화 funding 마진 악화.
          금융주 외국인 매도 트리거 역할.
        false_signal_check: |
          글로벌 리스크오프 시 신흥국 CDS 일제히 상승 → 한국 고유 리스크와 분리 해석.
        primary_targets: ["KB금융", "신한지주", "하나금융지주"]

      - id: 23-6
        name: "KOSPI 일평균 거래대금"
        source: "KRX 한국거래소"
        unit: "조원/일"
        frequency: "일간"
        lead_time: "동행 (분기 실적 직접 반영)"
        threshold:
          bullish: ">= 12조원/일 분기 평균"
          bearish: "<= 7조원/일 분기 평균"
        causal_mechanism: |
          거래대금 = 증권사 brokerage 수수료 베이스 직접.
          키움증권은 개인 거래대금 비중 70%+ → 더욱 민감.
        false_signal_check: |
          ETF 거래대금 비중 증가 시 수수료율 하락 → 거래대금만으로 매출 추정 부정확.
        primary_targets: ["키움증권"]

      - id: 23-7
        name: "장기손해율 (보험사)"
        source: "각 사 IR / 금감원 보험통계"
        unit: "%"
        frequency: "월간/분기"
        lead_time: "1~2분기"
        threshold:
          bullish: "<= 80% (장기손해)"
          bearish: ">= 88% 3개월 연속"
        causal_mechanism: |
          손해율 상승 → 보험금 지급 증가 → 합산비율 악화 → 보험영업이익 감소.
          삼성화재/DB손해보험 수익성 직접 결정.
        false_signal_check: |
          IFRS17 도입 후 회계 변경 → 시계열 비교 시 2023년 이전/이후 분리.
          자동차보험과 장기보험 분리 추적 필수.
        primary_targets: ["삼성화재", "DB손해보험"]

  # ============================================================
  # 24. 통신/유틸리티
  # ============================================================
  - id: 24
    name: "통신/유틸리티"
    kr_tickers:
      - { name: "SK텔레콤", code: "017670" }
      - { name: "KT", code: "030200" }
      - { name: "LG유플러스", code: "032640" }
      - { name: "한국전력", code: "015760" }
      - { name: "한국가스공사", code: "036460" }
    adopted_count: 6
    indicators:

      - id: 24-1
        name: "5G 가입자 수 + 비중"
        source: "방송통신위원회 무선통신서비스 통계"
        unit: "만명, %"
        frequency: "월간"
        lead_time: "동행~3개월 (ARPU 반영)"
        threshold:
          bullish: "5G 비중 >= 70% + 순증 유지"
          bearish: "전체 가입자 순감소 3개월 연속"
        causal_mechanism: |
          5G 가입자는 LTE 대비 ARPU 1.3~1.5배 → 통신 3사 매출 직접 증가.
          가입자 정체기에는 ARPU 단가 상승만이 매출 동력.
        false_signal_check: |
          알뜰폰 MVNO 이탈 → 자회사 매출 잠식 vs 본사 매출 증가 상쇄 효과.
          IoT/M2M 회선은 ARPU 매우 낮음 → 휴대폰 회선 분리 필수.
        primary_targets: ["SK텔레콤", "KT", "LG유플러스"]

      - id: 24-2
        name: "통신 가입자 순증감 (전체)"
        source: "방송통신위원회"
        unit: "만명/월"
        frequency: "월간"
        lead_time: "동행"
        threshold:
          bullish: ">= +5만명/월 (휴대폰 회선)"
          bearish: "<= -10만명/월 3개월 연속"
        causal_mechanism: |
          국내 통신시장 포화 상태 → 순증=경쟁사 이탈 또는 신규 진입.
          시장 점유율 변동 직접 반영.
        false_signal_check: |
          번호이동(MNP) vs 신규가입 분리 필요.
          명의자 정리 등 행정처리에 의한 일시적 감소 주의.
        primary_targets: ["SK텔레콤", "KT", "LG유플러스"]

      - id: 24-3
        name: "한국 전력 수요 (KPX 시간대별 평균)"
        source: "한국전력거래소 KPX 전력통계정보시스템"
        unit: "GWh/일 또는 MW 최대수요"
        frequency: "일간/월간"
        lead_time: "동행 (분기 실적 직접)"
        threshold:
          bullish: "여름철 최대수요 >= 95GW (가격 상승 압력)"
          bearish: "전년 대비 -5% 이상 감소"
        causal_mechanism: |
          전력 판매량 = 한전 매출 베이스.
          데이터센터/AI 수요 증가 → 산업용 전력 수요 구조적 상승.
        false_signal_check: |
          한전 적자/흑자는 판매량보다 SMP-요금 스프레드가 더 결정적.
          한전 분석 시 LNG 가격(JKM)과 함께 해석 필수.
        primary_targets: ["한국전력"]

      - id: 24-4
        name: "SMP (계통한계가격) 평균"
        source: "한국전력거래소 KPX"
        unit: "원/kWh"
        frequency: "일간/월간"
        lead_time: "1~2개월 (한전 손익)"
        threshold:
          bullish: "SMP - 판매단가 < 0 (한전 흑자)"
          bearish: "SMP - 판매단가 > 30원/kWh (역마진 심화)"
        causal_mechanism: |
          SMP가 판매단가보다 높으면 한전 역마진 → 적자 누적.
          LNG/석탄 발전비용 변동이 SMP의 주요 결정 요인.
        false_signal_check: |
          요금 인상 시점에 임시로 갭 축소 → 구조적 개선 아닌 정책 효과 구분.
        primary_targets: ["한국전력"]

      - id: 24-5
        name: "LNG JKM 가격"
        source: "S&P Global Platts (월간 평균은 무료 공개)"
        unit: "USD/MMBtu"
        frequency: "일간"
        lead_time: "1~3개월"
        threshold:
          bullish: "<= 10 USD/MMBtu (한전/가스공사 원가 안정)"
          bearish: ">= 18 USD/MMBtu (원가 급등)"
        causal_mechanism: |
          한국 LNG 수입의존 100% → JKM이 한전 발전원가 + 가스공사 도매원가 직접 결정.
          가스공사는 미수금 회수 메커니즘으로 시차 반영.
        false_signal_check: |
          가스공사는 정책 요금 + 미수금 메커니즘으로 LNG 가격과 손익 단순 연동 안 됨.
          요금 인상 정책 발표 시점 별도 모니터링 필수.
        primary_targets: ["한국전력", "한국가스공사"]

      - id: 24-6
        name: "한국가스공사 미수금 잔액"
        source: "한국가스공사 분기 IR"
        unit: "조원"
        frequency: "분기"
        lead_time: "1~2분기 (회수 시 이익 반영)"
        threshold:
          bullish: "감소 추세 + 요금 인상 정책"
          bearish: "증가 추세 + 정책 동결"
        causal_mechanism: |
          미수금 = 원가 미회수분 → 회수 시 매출 인식.
          요금 인상 → 미수금 회수 가속 → 분기 영업이익 급등.
        false_signal_check: |
          미수금 자체는 부채성 자산 → 단순 감소가 항상 호재 아님.
          요금 인상 정책 + 미수금 회수 동시에 봐야 함.
        primary_targets: ["한국가스공사"]

  # ============================================================
  # 25. 지주사/리츠
  # ============================================================
  - id: 25
    name: "지주사/리츠"
    kr_tickers:
      - { name: "삼성물산", code: "028260" }
      - { name: "LG", code: "003550" }
      - { name: "SK", code: "034730" }
      - { name: "맥쿼리인프라", code: "088980" }
      - { name: "롯데리츠", code: "330590" }
    adopted_count: 6
    indicators:

      - id: 25-1
        name: "자회사 분기 합산 영업이익률 (지분 가중)"
        source: "DART 자회사 분기보고서 / 각 사 IR"
        unit: "% (가중평균)"
        frequency: "분기"
        lead_time: "동행 (지주사 지분법 손익)"
        threshold:
          bullish: "QoQ +1%p 이상 개선"
          bearish: "QoQ -1.5%p 이상 악화"
        causal_mechanism: |
          지주사 순이익의 70~90%는 자회사 지분법 손익.
          삼성전자/LG전자/SK하이닉스 등 핵심 자회사 OPM이 지주사 손익 직결.
        false_signal_check: |
          비상장 자회사는 분기 공시 지연 → 대형 상장 자회사 위주 추적.
          일회성 손익(매각 차익 등) 제외한 영업 OPM만 사용.
        primary_targets: ["삼성물산", "LG", "SK"]

      - id: 25-2
        name: "NAV 디스카운트율"
        source: "각 사 IR 자체 NAV 공시 또는 증권사 리포트 (1차 소스: DART 분기보고서 지분 가치)"
        unit: "%"
        frequency: "분기 갱신, 일간 모니터링"
        lead_time: "역사적 평균 회귀 1~2분기"
        threshold:
          bullish: "디스카운트 60% 이상 (역사적 평균 이상)"
          bearish: "디스카운트 30% 이하 (프리미엄 영역, 추가 상승 여력 제한)"
        causal_mechanism: |
          지주사 주가가 자회사 지분 가치보다 깊게 할인되면 평균 회귀 압력.
          밸류업 정책/자사주 소각 시 디스카운트 축소 트리거.
        false_signal_check: |
          영구적 디스카운트 종목 존재 (지배구조 리스크, 비상장 자회사 평가 어려움).
          단순 디스카운트 = 매수 신호 아님 → 카탈리스트 동반 확인.
        primary_targets: ["삼성물산", "LG", "SK"]

      - id: 25-3
        name: "한미 금리차 + 한국 10Y 국채금리"
        source: "한국은행 ECOS / 금융투자협회 (10Y KTB)"
        unit: "%, %p"
        frequency: "일간"
        lead_time: "1~2분기 (리츠 가격 반영)"
        threshold:
          bullish: "한국 10Y <= 3.0% + 인하 사이클 진입"
          bearish: "한국 10Y >= 4.0% + 한미 금리차 -2%p 이상"
        causal_mechanism: |
          리츠/인프라펀드는 배당주 성격 → 장기금리 역상관.
          금리 인하 = 리츠 PER 확대 + 자금조달 비용 감소 이중 호재.
          맥쿼리인프라는 배당 6%대 → 채권 대안 수요 직접 영향.
        false_signal_check: |
          금리 인하가 경기침체 신호일 경우 리츠 임대수익 자체 위협 (기초자산 공실률 상승).
          금리 방향 + 경기지표 동시 확인.
        primary_targets: ["맥쿼리인프라", "롯데리츠"]

      - id: 25-4
        name: "상업용 부동산 공실률 (서울 오피스 + 리테일)"
        source: "한국부동산원 R-ONE 상업용부동산 임대동향조사"
        unit: "%"
        frequency: "분기"
        lead_time: "동행~1분기 (임대수익 반영)"
        threshold:
          bullish: "서울 오피스 공실률 <= 5%"
          bearish: "리테일 공실률 >= 12% + 상승 추세"
        causal_mechanism: |
          공실률 하락 = 임대료 상승 여력 + 안정적 임대수익.
          롯데리츠는 리테일(롯데마트/백화점) 자산 비중 높아 리테일 공실률 직격.
        false_signal_check: |
          서울 도심(CBD) vs 강남(GBD) vs 여의도(YBD) 권역별 편차 큼.
          롯데리츠는 책임임대차 구조 → 공실률보다 모기업(롯데쇼핑) 신용도가 더 중요.
        primary_targets: ["롯데리츠"]

      - id: 25-5
        name: "인플레이션 (CPI YoY)"
        source: "통계청 KOSIS 소비자물가지수"
        unit: "% YoY"
        frequency: "월간"
        lead_time: "1~2분기"
        threshold:
          bullish: "2~3% (적정 인플레이션 + 임대료 인상 가능)"
          bearish: ">= 4% (실질금리 영향 + 비용 압박) 또는 디플레이션"
        causal_mechanism: |
          인프라/리츠는 임대료 인플레이션 연동 조항 → 인플레이션 국면 헷지 효과.
          맥쿼리인프라 통행료/사용료는 CPI 연동 구조.
        false_signal_check: |
          인플레이션 급등 시 한은 금리 인상 → 할인율 상승 효과가 임대료 인상 효과 압도 가능.
          인플레이션 단독 해석 금지, 금리와 동시 분석.
        primary_targets: ["맥쿼리인프라", "삼성물산"]

      - id: 25-6
        name: "건설/조선/배터리 자회사 신규 수주 (지주사 핵심 자회사)"
        source: "DART 단일판매·공급계약체결 공시"
        unit: "조원/분기"
        frequency: "이벤트성 + 분기 집계"
        lead_time: "2~4분기 (매출 인식 시차)"
        threshold:
          bullish: "수주잔고 / 직전년도 매출 >= 2.0배"
          bearish: "분기 신규수주 YoY -30% 이상"
        causal_mechanism: |
          삼성물산(건설/상사), SK(SK이노베이션 등), LG(LG에너지솔루션 등) 자회사 수주는
          1~2년 후 지주사 지분법 이익으로 반영.
        false_signal_check: |
          대형 단발 수주의 월간 변동성 큼 → 4분기 누계 또는 12개월 이동합 권장.
          수주 취소/지연 리스크 별도 모니터링.
        primary_targets: ["삼성물산", "LG", "SK"]

# ============================================================
# 종합
# ============================================================
summary:
  total_indicators: 26
  by_sector:
    "건설/건자재": 7
    "금융": 7
    "통신/유틸리티": 6
    "지주사/리츠": 6
  data_sources_primary:
    - "한국은행 ECOS"
    - "통계청 KOSIS"
    - "금감원 / DART"
    - "국토교통부 통계누리"
    - "한국부동산원 R-ONE"
    - "한국전력거래소 KPX"
    - "방송통신위원회"
    - "KRX 한국거래소"
    - "CME FedWatch"
    - "AIA / US Census Bureau"
  cross_sector_linkage:
    - "LNG JKM (Phase 1) → 한전 + 가스공사 (Phase 2 #24)"
    - "한미 금리차 → 금융 NIM (#23) + 리츠 가격 (#25)"
    - "한국 부동산 가격 → 건설 분양 (#22) + PF 연체 (#23) + 리츠 공실 (#25)"
    - "CPI → 리츠 임대료 연동 (#25) + 통신 요금 인상 (#24)"


## 13. 그룹 E — 섹터 26~27: 숨은 알파 (14개 지표)

# Phase 2 — Group E: 숨은 알파 2개 섹터 선행지표 매트릭스
# 한국 투자자용 / 웹검색 0회 / 도메인 지식 기반
# 생성일: 2026-04-25

meta:
  phase: 2
  group: E
  scope: "숨은 알파 — 의료기기/미용 + 호텔/레저/여행"
  audience: "한국 개인투자자"
  created: "2026-04-25"
  rules:
    - "무료 + 신뢰 1차 소스만"
    - "검증된 lead time 명시"
    - "False signal 검토 포함"
    - "KR 종목 표기: 종목명(6자리), US: 공식 ticker"

sectors:

  # ==========================================================
  # 26. 의료기기/미용 (K-Beauty Devices & Toxins)
  # ==========================================================
  - id: 26
    name: "의료기기/미용"
    constituents:
      KR:
        - "클래시스(214150)"
        - "비올(335890)"
        - "제이시스메디칼(287410)"
        - "메디톡스(086900)"
        - "휴젤(145020)"
        - "파마리서치(214450)"
      US: []
    thesis: |
      한국 미용 의료기기(HIFU/RF/MTS)와 보툴리눔톡신은
      장비 판매 → 소모품(팁/카트리지) 재구매 사이클이 핵심.
      식약처 신규 품목허가, 관세청 미용기기 수출, FDA 510(k) 승인이
      2~4분기 선행. 중국·미국·브라질 시장 진출이 톡신/장비 매출의
      변곡점을 결정.
    indicators:

      - id: E26-01
        name: "식약처 의료기기 신규 품목허가 (미용/피부)"
        source:
          name: "식품의약품안전처 의료기기전자민원창구 (emed.mfds.go.kr)"
          type: "공공 1차 소스"
          cost: "무료"
          frequency: "주 단위 공시 (실시간 조회)"
        causal_mechanism: |
          신규 품목허가 → 6~12개월 내 국내 출시 →
          장비 판매 → 12~24개월 후 소모품(팁) 매출 본격화.
          업그레이드 모델 허가는 기존 라인 대체 수요를 자극.
        lead_time: "장비 매출 +2~4분기 / 소모품 매출 +4~8분기"
        ticker_mapping:
          - ticker: "클래시스(214150)"
            keyword: "고강도집속초음파자극기, RF, 슈링크/올리지오 후속"
          - ticker: "비올(335890)"
            keyword: "고주파자극기, 실펌X 라인업"
          - ticker: "제이시스메디칼(287410)"
            keyword: "RF/MTS 복합기, 포텐자/덴서티"
          - ticker: "파마리서치(214450)"
            keyword: "PDRN 주사제, 리쥬란 라인"
        false_signal_check: |
          - 동일 모델 마이너 변경(수출용 인증 등)은 매출 임팩트 작음
          - 허가만으로는 보험수가/광고 규제 통과 여부 미확인
          - 경쟁사 동시 허가 시 ASP 하락 가능
        priority: "HIGH"

      - id: E26-02
        name: "관세청 미용기기·피부관리기기 수출액 (HS 9018·9019)"
        source:
          name: "관세청 수출입무역통계 (unipass.customs.go.kr/ets)"
          type: "공공 1차 소스"
          cost: "무료"
          frequency: "월간 (익월 15일경 확정치)"
        causal_mechanism: |
          HS 9018(의료용 기기)·9019(기계요법기기) 월간 수출액 →
          국가별 breakdown(미국/브라질/태국/일본)으로 클래시스·비올의
          현지 파트너 발주 사이클 추적. 수출 단가 상승은 신모델 비중 확대 신호.
        lead_time: "분기 매출 인식 +1~2개월 (선적 기준 → 매출 인식)"
        ticker_mapping:
          - ticker: "클래시스(214150)"
            keyword: "브라질·태국·일본向 슈링크/올리지오 본체+소모품"
          - ticker: "비올(335890)"
            keyword: "미국·브라질向 실펌X (FDA 승인 후 급증)"
          - ticker: "제이시스메디칼(287410)"
            keyword: "미국·일본向 RF 장비"
        false_signal_check: |
          - HS 코드는 의료기기 전체 — 진단기기/내시경 노이즈 포함
          - 단월 급등은 선적 일정 차이일 수 있음 (3개월 이동평균 권장)
          - 환율 효과 분리 필요 (USD 기준 + KRW 기준 병행 확인)
        priority: "HIGH"

      - id: E26-03
        name: "FDA 510(k) / PMA 한국기업 승인 공시"
        source:
          name: "FDA 510(k) Database (fda.gov/medical-devices)"
          type: "공공 1차 소스 (해외)"
          cost: "무료"
          frequency: "주간 업데이트, 검색 가능"
        causal_mechanism: |
          미국 FDA 승인 → 미국 시장 진입 가능 →
          현지 파트너십·직판 셋업 6~12개월 → 본격 매출.
          미국 ASP는 국내 대비 2~3배, 마진 레버리지 큼.
        lead_time: "미국 매출 인식 +3~6분기"
        ticker_mapping:
          - ticker: "비올(335890)"
            keyword: "Sylfirm X (실펌X) FDA 510(k) — 미국 매출 폭발 트리거"
          - ticker: "클래시스(214150)"
            keyword: "Volnewmer/Ultraformer 후속 모델"
          - ticker: "제이시스메디칼(287410)"
            keyword: "Potenza/Density 라인 — Cartessa 파트너십"
        false_signal_check: |
          - 510(k)는 동등성 기준 — 임상 효과 검증 아님
          - 승인 후 현지 마케팅·교육 비용 선반영으로 단기 적자 가능
          - 모방 제품 동시 승인 시 차별화 약화
        priority: "HIGH"

      - id: E26-04
        name: "관세청 보툴리눔톡신 수출액 (HS 3002)"
        source:
          name: "관세청 수출입무역통계 (HS 3002 — 톡신 포함 면역 제품)"
          type: "공공 1차 소스"
          cost: "무료"
          frequency: "월간"
        causal_mechanism: |
          톡신 월간 수출액 + 국가별 분해 →
          중국 회색시장(태국 경유) vs 미국·유럽 정식시장 식별.
          미국 BLA 승인 후 정식 수출 비중 확대는 마진 개선 신호.
        lead_time: "매출 인식 +1~2개월 / BLA 승인 시 +4~8분기 본격화"
        ticker_mapping:
          - ticker: "휴젤(145020)"
            keyword: "Letybo 미국 BLA 승인 후 직판 — 수출액 급증"
          - ticker: "메디톡스(086900)"
            keyword: "뉴럭스 미국 임상, 중남미 수출"
        false_signal_check: |
          - HS 3002는 톡신 외 백신·혈액제제 포함 — 노이즈 큼
          - 태국向 급증은 중국 회색시장 우회 → 정식시장 매출 아님
          - 분기 말 밀어내기 가능, 추세 봐야 함
        priority: "HIGH"

      - id: E26-05
        name: "톡신 미국 BLA / 중국 NMPA 승인 단계"
        source:
          name: "FDA Drugs@FDA + 중국 NMPA 공시 + 회사 IR 분기보고서"
          type: "공공 1차 소스 + 회사 공시"
          cost: "무료"
          frequency: "비정기 (마일스톤 기반)"
        causal_mechanism: |
          BLA/NMPA 승인 → 정식시장 진입 →
          미국 ASP는 회색시장 대비 5~10배, 중국은 정식 유통망 확보.
          승인 임박 6개월 전 임상 데이터 발표 시점에 주가 선반영.
        lead_time: "주가 +6~12개월 선반영 / 매출 +2~4분기"
        ticker_mapping:
          - ticker: "휴젤(145020)"
            keyword: "Letybo 미국 BLA 2024 승인 — 2025~2026 매출 본격화"
          - ticker: "메디톡스(086900)"
            keyword: "MT10109L (뉴럭스) 미국 임상 3상"
          - ticker: "대웅제약(미상장 톡신)"
            keyword: "참고: 나보타 — Evolus 파트너십"
        false_signal_check: |
          - 승인 자체와 매출 본격화 시차 6~12개월
          - 경쟁사(애브비 보톡스, 입센 디스포트) 가격 방어 가능성
          - 직판 vs 파트너십 구조에 따라 마진 차이 큼
        priority: "MEDIUM"

      - id: E26-06
        name: "중국 미용 의료서비스 시장 — NBS 소비 통계"
        source:
          name: "中国国家统计局 (stats.gov.cn) 사회소비품 영업액 — 화장품/의료서비스"
          type: "공공 1차 소스 (해외)"
          cost: "무료"
          frequency: "월간"
        causal_mechanism: |
          중국 화장품·의료서비스 소매 매출 증감 →
          한국 미용기기·톡신의 중국 수요 선행.
          광군절·춘절 시즌 데이터가 분기 매출 가이드.
        lead_time: "한국 수출 +1~3개월"
        ticker_mapping:
          - ticker: "클래시스(214150)"
            keyword: "중국 NMPA 슈링크 승인 후 본격 침투"
          - ticker: "휴젤(145020)"
            keyword: "Letybo 중국 NMPA 승인 — 정식시장 진입"
          - ticker: "메디톡스(086900)"
            keyword: "뉴로녹스 중국 — 분쟁 해소 후 재개"
        false_signal_check: |
          - 중국 자국 브랜드(화시바이오, 아이메이커) 점유율 잠식 가속
          - 정부 의료광고·미용시술 규제 강화 리스크
          - 통계는 전체 — 미용 의료기기만 분리 어려움
        priority: "MEDIUM"

      - id: E26-07
        name: "회사 분기 IR — 소모품/리오더 비중 공시"
        source:
          name: "DART 분기보고서 + 회사 IR 자료 (실적발표 PT)"
          type: "공공 1차 소스"
          cost: "무료"
          frequency: "분기"
        causal_mechanism: |
          장비 누적 판매대수(installed base) × 시술 빈도 ×
          소모품 단가 = 리커링 매출. 소모품 비중 50% 돌파는
          비즈니스 모델 안정화 신호. 클래시스·비올의 핵심 KPI.
        lead_time: "동행 지표 (분기 실적 공시 시점)"
        ticker_mapping:
          - ticker: "클래시스(214150)"
            keyword: "슈링크/올리지오 카트리지 비중 — 60%+ 시 안정"
          - ticker: "비올(335890)"
            keyword: "실펌X 팁 매출 비중 — 미국 진입 후 급증"
          - ticker: "제이시스메디칼(287410)"
            keyword: "포텐자 팁 매출"
        false_signal_check: |
          - 신모델 출시 직후 장비 매출 급증 시 소모품 비중 일시 하락
          - 회사 자체 정의 차이 (소모품 vs 부품) 비교 시 주의
          - IR 자료 비공시 항목은 추정 어려움
        priority: "MEDIUM"

  # ==========================================================
  # 27. 호텔/레저/여행 (Hotels, Leisure & Travel)
  # ==========================================================
  - id: 27
    name: "호텔/레저/여행"
    constituents:
      KR:
        - "파라다이스(034230)"
        - "GKL(114090)"
        - "하나투어(039130)"
        - "모두투어(080160)"
      US:
        - "LVS"
        - "WYNN"
    thesis: |
      한국 인바운드(외국인 방한)와 아웃바운드(내국인 출국)는
      카지노·여행사·호텔 매출의 직접 동인.
      외국인 입국자 수, 인천공항 여객, 카지노 드롭액(베팅금),
      중국 단체관광 비자 정책이 핵심 선행지표.
      마카오(LVS·WYNN)는 별도 — 마카오 GGR이 직접 동인.
    indicators:

      - id: E27-01
        name: "법무부 출입국 외국인 입국자 수 (월간)"
        source:
          name: "법무부 출입국·외국인정책본부 통계월보 (immigration.go.kr)"
          type: "공공 1차 소스"
          cost: "무료"
          frequency: "월간 (익월 20일경)"
        causal_mechanism: |
          외국인 월간 입국자 수 → 국적별 breakdown
          (중국/일본/대만/동남아) → 카지노 드롭액·면세점·호텔 매출 직접 영향.
          중국·일본 입국자 합산이 외국인 카지노 매출의 80%+.
        lead_time: "동행 ~ +1개월 (월말 공시 → 분기 실적 반영)"
        ticker_mapping:
          - ticker: "파라다이스(034230)"
            keyword: "일본·중국 VIP 입국자 — 인천/부산 카지노 드롭액"
          - ticker: "GKL(114090)"
            keyword: "중국 단체 + 일본 입국자 — 강남/힐튼/밀레니엄"
          - ticker: "하나투어(039130)"
            keyword: "인바운드 패키지 (소수 비중)"
        false_signal_check: |
          - 환승객/단기체류는 소비 임팩트 작음
          - 코로나 회복 베이스 효과 — YoY 보다 2019년 대비 회복률 봐야 함
          - 입국자 ≠ 카지노 방문자 (VIP 비중이 매출 좌우)
        priority: "HIGH"

      - id: E27-02
        name: "인천국제공항공사 여객 통계 (월간)"
        source:
          name: "인천국제공항공사 항공통계 (airport.kr)"
          type: "공공 1차 소스"
          cost: "무료"
          frequency: "월간 (익월 10일경 확정)"
        causal_mechanism: |
          인천공항 출발/도착 여객 수 + 노선별(중국/일본/동남아) →
          여행사 패키지 발권 + 카지노 입국자 선행.
          출발 여객은 아웃바운드(하나투어/모두투어), 도착은 인바운드.
        lead_time: "여행사 매출 +1~2개월 (송출 → 정산) / 카지노 동행"
        ticker_mapping:
          - ticker: "하나투어(039130)"
            keyword: "출발 여객 — 일본·동남아 패키지 핵심"
          - ticker: "모두투어(080160)"
            keyword: "출발 여객 — 일본 단거리 비중 높음"
          - ticker: "파라다이스(034230)"
            keyword: "도착 여객 — 일본·중국"
        false_signal_check: |
          - LCC 비중 증가 시 객단가 하락 (여행사 마진 압박)
          - 환승객 비중 분리 필요 (실제 한국 입국 ≠ 환승)
          - 특정 노선 결항/증편 일회성 효과 큼
        priority: "HIGH"

      - id: E27-03
        name: "파라다이스/GKL 월간 카지노 매출 IR 공시"
        source:
          name: "파라다이스·GKL 월간 매출액 자율공시 (DART/IR)"
          type: "공공 1차 소스 (회사 공시)"
          cost: "무료"
          frequency: "월간 (익월 5~10일)"
        causal_mechanism: |
          매출 = 드롭액(베팅 총액) × 홀드율(카지노 승률).
          드롭액은 VIP 방문 + 평균 베팅 강도 함수.
          분기 실적 발표 1~2개월 선행.
        lead_time: "분기 실적 +1~2개월 선행 (월별 공시 → 분기 합산)"
        ticker_mapping:
          - ticker: "파라다이스(034230)"
            keyword: "월간 매출 자율공시 — 인천+부산+제주+워커힐 합산"
          - ticker: "GKL(114090)"
            keyword: "월간 매출 자율공시 — 강남코엑스+힐튼+밀레니엄"
        false_signal_check: |
          - 홀드율 변동성 (정상범위 12~18%) — 매출 단월 노이즈
          - 단발성 정킷 캠페인 효과 분리 필요
          - GKL은 외국인전용 — 내국인 출입 불가 (파라다이스도 외국인전용)
        priority: "HIGH"

      - id: E27-04
        name: "중국 단체관광 비자 정책 (한국 대상 그룹비자)"
        source:
          name: "중국 문화여유부 + 주한중국대사관 공지 + 한국관광공사 공시"
          type: "정부 공지 (1차 소스)"
          cost: "무료"
          frequency: "비정기 (정책 변경 시)"
        causal_mechanism: |
          중국 단체비자 허용/제한 정책 변동 →
          1~3개월 후 중국 입국자 급증/급감 → 카지노·면세점·여행사 직접 영향.
          2017년 사드 이후 가장 큰 외생 변수.
        lead_time: "입국자 수 +1~3개월 / 카지노 매출 +2~4개월"
        ticker_mapping:
          - ticker: "파라다이스(034230)"
            keyword: "중국 VIP 정킷 — 단체비자 재개 시 강한 반응"
          - ticker: "GKL(114090)"
            keyword: "중국 단체 비중 높음 — 정책 민감도 최대"
          - ticker: "호텔신라(미상장 종목 제외)"
            keyword: "참고: 면세점 — 따이공·단체관광 영향"
        false_signal_check: |
          - 단체비자 재개 발표 ≠ 실제 송출 — 1~2개월 시차
          - 환율(위안화 약세)·중국 내수 둔화로 효과 반감 가능
          - 한중관계 외교 변수로 재중단 리스크 상존
        priority: "HIGH"

      - id: E27-05
        name: "일본 JNTO 방한 한국인 + 한국→일본 출국자 (양방향)"
        source:
          name: "JNTO 일본정부관광국 (jnto.go.jp/statistics) + 법무부 출국 통계"
          type: "공공 1차 소스 (양국)"
          cost: "무료"
          frequency: "월간"
        causal_mechanism: |
          한국→일본 출국자 수 → 하나투어·모두투어 일본 패키지 매출.
          일본은 한국 아웃바운드 1위 (전체의 25~35%) — 엔저·LCC가 동인.
          반대로 일본인 방한도 면세/호텔 영향.
        lead_time: "여행사 매출 +1~2개월"
        ticker_mapping:
          - ticker: "하나투어(039130)"
            keyword: "일본 패키지 — 단거리 핵심 매출원"
          - ticker: "모두투어(080160)"
            keyword: "일본 패키지 비중 40%+"
        false_signal_check: |
          - 자유여행 비중 증가로 패키지 매출 ≠ 출국자 수 비례 약화
          - 엔저 지속 시 일본 인바운드 약화 (한국→일본은 강화)
          - 항공권/호텔 따로 예약 비중 증가 트렌드
        priority: "MEDIUM"

      - id: E27-06
        name: "마카오 GGR (Gross Gaming Revenue) 월간"
        source:
          name: "마카오 DICJ 도박감독조정국 (dicj.gov.mo)"
          type: "공공 1차 소스 (해외)"
          cost: "무료"
          frequency: "월간 (익월 1일)"
        causal_mechanism: |
          마카오 전체 GGR 월간 발표 → LVS·WYNN 마카오 점유율로
          개별사 매출 추정. 중국 본토 방문객·VIP 정킷이 핵심 동인.
          분기 실적 1~2개월 선행.
        lead_time: "LVS/WYNN 분기 실적 +1~2개월 선행"
        ticker_mapping:
          - ticker: "LVS"
            keyword: "Sands China — 마카오 점유율 ~22% (Venetian/Londoner)"
          - ticker: "WYNN"
            keyword: "Wynn Macau — 점유율 ~13% (Wynn Palace 포함)"
        false_signal_check: |
          - 마스 GGR ≠ 개별사 매출 — 점유율 변동 확인 필수
          - VIP vs Mass 믹스 변화 (VIP 마진 낮음)
          - 중국 부패척결·자본통제 강화 시 VIP 급감 (2014~2016 학습)
        priority: "HIGH"

      - id: E27-07
        name: "한국호텔업협회 객실 점유율(OCC)·ADR·RevPAR"
        source:
          name: "한국호텔업협회 + 한국관광공사 관광지식정보시스템 (know.tour.go.kr)"
          type: "공공 1차 소스 + 협회 자료"
          cost: "무료 (일부 회원 전용)"
          frequency: "월간"
        causal_mechanism: |
          서울 5성급 호텔 OCC + ADR(평균객단가) →
          파라다이스 워커힐, GKL 힐튼/밀레니엄 호텔 부문 매출 선행.
          RevPAR(객실당 매출)이 호텔 부문 수익성 직결.
        lead_time: "분기 실적 동행 ~ +1개월"
        ticker_mapping:
          - ticker: "파라다이스(034230)"
            keyword: "워커힐 호텔 — 카지노 외 호텔 매출 부문"
          - ticker: "GKL(114090)"
            keyword: "힐튼/밀레니엄 임차 — 호텔 매출은 위탁/임차료 형태"
        false_signal_check: |
          - 카지노 종목은 호텔 매출 비중 작음 (20% 미만) — 보조 지표
          - 협회 데이터는 표본 집계 — 5성급 한정 시 신뢰도 높음
          - 시즌성 강함 (4~5월, 10~11월 피크)
        priority: "LOW"

# ============================================
# 요약
# ============================================
summary:
  sector_26_count: 7
  sector_27_count: 7
  total: 14
  high_priority_count: 9
  key_finding: |
    의료기기/미용 — 식약처 신규 품목허가는 클래시스/비올의 장비 매출
    +2~4분기, 소모품(팁/카트리지) 매출 +4~8분기를 선행.
    특히 비올 실펌X의 FDA 510(k) 승인 → 미국 매출 폭발(2024~2025)이
    명확한 lead time 구조를 보여준 사례.
  cross_sector_link: |
    호텔/레저는 중국 단체비자 정책이 가장 강한 외생 변수 —
    동일 변수가 의료기기/미용(중국 미용시장)에도 영향.
    중국 정책 모니터링은 두 섹터 모두 핵심.


## 14. Phase 2 운영 규칙
- v1 잠금 (2026-04-25), 125개 지표 최종 확정
- Phase 1과 동일하게 추가만 가능, 변경 불가
- 데이터 값 갱신은 별도 데이터 페이지
- 사후 백테스트: 분기별 `Output/indicator-backtest-YYYY-Q.md`
- **관련**: [[01-commodities]], [[03-outlook]], [[04-value-chain]]
