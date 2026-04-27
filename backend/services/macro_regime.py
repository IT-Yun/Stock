"""거시 시나리오 자동 감지 + 종합 섹터 추천.

Step 1: 라이브 매크로 + commodity feed → 9개 시나리오 중 활성 매칭 (강도 0~1)
Step 2: commodity sentiment + 활성 시나리오 영향 → 27섹터 종합 점수
Step 3: 종합 점수 → TOP/BOTTOM 섹터 추천
"""

from __future__ import annotations
from typing import Any
from services.macro_indicators import macro_dict
from services.macro_commodity import fetch_feed
from services.macro_sentiment import all_sector_sentiments


# 시나리오 메타 (wiki/macro/03-outlook.md 기반)
SCENARIO_META: dict[str, dict[str, Any]] = {
    "goldilocks": {
        "name": "골디락스 (성장+저금리)",
        "favorable": ["ai_semi", "robotics", "quantum", "battery", "ev"],
        "unfavorable": ["aerospace", "cybersec"],
        "weight_per_sector": 1.5,
    },
    "stagflation": {
        "name": "스태그플레이션",
        "favorable": ["hydrogen_energy", "aerospace", "steel", "shipbuilding"],
        "unfavorable": ["ai_semi", "battery", "ev_materials", "platform"],
        "weight_per_sector": 2.0,
    },
    "recession": {
        "name": "침체",
        "favorable": ["biotech", "cybersec", "telecom"],
        "unfavorable": ["ai_semi", "robotics", "shipbuilding", "construction", "ev"],
        "weight_per_sector": 2.0,
    },
    "recovery_early": {
        "name": "회복 초기",
        "favorable": ["ai_semi", "robotics", "smr_nuclear", "ev_materials", "battery"],
        "unfavorable": ["aerospace"],
        "weight_per_sector": 1.5,
    },
    "geopolitical_crisis": {
        "name": "중동 전쟁/호르무즈 리스크",
        "favorable": ["aerospace", "shipbuilding", "hydrogen_energy", "smr_nuclear", "cybersec"],
        "unfavorable": ["hotel_leisure", "platform", "k_content", "cosmetics", "ev", "battery"],
        "weight_per_sector": 2.0,
    },
    "ai_capex_acceleration": {
        "name": "AI capex 가속",
        "favorable": ["ai_semi", "smr_nuclear", "battery", "robotics"],
        "unfavorable": [],
        "weight_per_sector": 2.5,
    },
    "yuan_devaluation": {
        "name": "미중 갈등/디커플링",
        "favorable": ["cybersec", "aerospace", "ai_semi", "medical_device"],
        "unfavorable": ["display", "cosmetics", "retail", "k_content"],
        "weight_per_sector": 1.5,
    },
    "boj_carry_unwind": {
        "name": "BOJ 캐리 청산",
        "favorable": ["biotech", "cybersec"],
        "unfavorable": ["ai_semi", "robotics", "battery"],
        "weight_per_sector": 1.5,
    },
    "expansion_late": {
        "name": "확장 후기 / 인플레 재점화",
        "favorable": ["hydrogen_energy", "steel", "aerospace"],
        "unfavorable": ["platform", "k_content", "cosmetics"],
        "weight_per_sector": 1.5,
    },
}

EVENT_META: dict[str, dict[str, Any]] = {
    "iran_hormuz_war": {
        "title": "이란 전쟁·호르무즈 공급 차질",
        "status": "전쟁/봉쇄 리스크 진행 중",
        "favorable": ["aerospace", "shipbuilding", "hydrogen_energy", "smr_nuclear", "cybersec"],
        "unfavorable": ["hotel_leisure", "platform", "k_content", "cosmetics", "ev", "battery"],
        "weight": 2.6,
        "source_notes": [
            "AP 2026-04-25: 미국이 호르무즈 해협 기뢰 제거 작업을 진행 중이며, 이란 전쟁으로 유가·가스 가격 압력이 커졌다고 보도",
            "EIA: 호르무즈는 세계 원유 해상 운송의 핵심 병목으로 공급 차질 시 에너지 가격 영향이 큼",
        ],
    },
    "ai_power_bottleneck": {
        "title": "AI 데이터센터 전력 병목",
        "status": "구조적 capex 사이클",
        "favorable": ["ai_semi", "smr_nuclear", "hydrogen_energy", "battery", "robotics"],
        "unfavorable": ["telecom", "holding_reit"],
        "weight": 1.8,
        "source_notes": ["전력·냉각·송전망 투자가 AI capex의 병목으로 작동"],
    },
    "us_china_decoupling": {
        "title": "미중 갈등·수출통제",
        "status": "정책 리스크 상시화",
        "favorable": ["cybersec", "aerospace", "ai_semi", "medical_device"],
        "unfavorable": ["display", "cosmetics", "retail", "k_content"],
        "weight": 1.5,
        "source_notes": ["중국 노출 소비재/디스플레이는 수요·정책 리스크, 안보/국산화 체인은 프리미엄"],
    },
    "higher_for_longer": {
        "title": "금리 경로 재상향/고금리 장기화",
        "status": "유가·달러·채권금리로 재평가",
        "favorable": ["finance", "telecom", "biotech"],
        "unfavorable": ["platform", "ev", "battery", "gaming", "k_content"],
        "weight": 1.4,
        "source_notes": ["인플레 재점화는 장기 성장주의 할인율 부담을 키움"],
    },
    "usd_krw_fx_pressure": {
        "title": "달러/원 고환율·아시아 FX 압박",
        "status": "수입원가·외국인 수급 리스크",
        "favorable": ["shipbuilding", "aerospace", "ai_semi", "medical_device"],
        "unfavorable": ["hotel_leisure", "food", "cosmetics", "retail", "battery"],
        "weight": 1.2,
        "source_notes": ["원화 약세는 수출주 매출 환산에는 우호적이나 수입 원가·여행 수요에는 부담"],
    },
    "industrial_reflation": {
        "title": "산업금속·인프라 재평가",
        "status": "중국/AI 전력망/인프라 수요 확인",
        "favorable": ["ai_semi", "steel", "shipbuilding", "robotics", "hydrogen_energy"],
        "unfavorable": ["construction", "ev", "battery"],
        "weight": 1.3,
        "source_notes": ["구리·알루미늄 강세는 경기/전력망 capex proxy이면서 일부 섹터에는 원가 부담"],
    },
    "food_inflation": {
        "title": "식품 원가 인플레",
        "status": "곡물·설탕·커피 가격 압박",
        "favorable": ["finance"],
        "unfavorable": ["food", "retail", "hotel_leisure", "cosmetics"],
        "weight": 1.1,
        "source_notes": ["곡물/커피/설탕 상승은 판가 전가 전까지 식품·소비재 마진 부담"],
    },
    "rare_earth_controls": {
        "title": "희토류·특수금속 수출통제",
        "status": "공급망 병목 프리미엄",
        "favorable": ["aerospace", "cybersec", "ai_semi", "ev_materials"],
        "unfavorable": ["ev", "battery", "display"],
        "weight": 1.4,
        "source_notes": ["갈륨·게르마늄·희토류는 방산/반도체/EV 필수 소재이나 가격 데이터는 proxy 비중이 큼"],
    },
    "credit_volatility": {
        "title": "신용·변동성 스트레스",
        "status": "risk-off/자금조달 비용 점검",
        "favorable": ["cybersec", "telecom", "biotech"],
        "unfavorable": ["platform", "gaming", "k_content", "construction", "holding_reit"],
        "weight": 1.3,
        "source_notes": ["VIX 상승·신용스프레드 확대는 장기 성장주와 레버리지 섹터에 불리"],
    },
}


def _safe(item, attr, default=None):
    try:
        v = getattr(item, attr) if not isinstance(item, dict) else item.get(attr)
        return v if v is not None else default
    except Exception:
        return default


def detect_active_scenarios() -> list[dict[str, Any]]:
    """현재 활성화된 시나리오 detection (강도 0~1)."""
    macro = macro_dict()
    feed = {f.id: f for f in fetch_feed()}

    vix = _safe(macro.get("vix"), "price")
    ten_y = _safe(macro.get("treasury_10y"), "price")
    three_m = _safe(macro.get("treasury_3m"), "price")
    dxy = _safe(macro.get("dxy"), "price")
    krw = _safe(macro.get("usd_krw"), "price")
    krw_z = _safe(macro.get("usd_krw"), "zscore_60d", 0)
    jpy = _safe(macro.get("usd_jpy"), "price")
    sp_z = _safe(macro.get("sp500"), "zscore_60d", 0)
    sp_5d = _safe(macro.get("sp500"), "change_pct_5d", 0)
    nasdaq_z = _safe(macro.get("nasdaq"), "zscore_60d", 0)
    kospi_z = _safe(macro.get("kospi"), "zscore_60d", 0)
    krw_z = _safe(macro.get("usd_krw"), "zscore_60d", 0)
    jpy_5d = _safe(macro.get("usd_jpy"), "change_pct_5d", 0)

    # commodity 신호
    wti = feed.get("crude_wti")
    brent = feed.get("crude_brent")
    gold = feed.get("gold")
    oil_5d_max = max([_safe(wti, "change_pct_5d", 0), _safe(brent, "change_pct_5d", 0)])
    oil_surge = _safe(wti, "is_surge") or _safe(brent, "is_surge")
    gold_5d = _safe(gold, "change_pct_5d", 0)

    active: list[dict[str, Any]] = []

    # 1. 골디락스: VIX 낮음, 금리 안정, 주가 강세
    if vix and vix < 22 and ten_y and 3.0 < ten_y < 5.0:
        score = 0.0
        ev = [f"VIX {vix:.1f} (저변동)", f"10Y {ten_y:.2f}% (안정 범위)"]
        if vix < 18:
            score += 0.3
        if 3.5 < ten_y < 4.5:
            score += 0.2
        if (sp_z or 0) > 0:
            score += 0.3
            ev.append(f"S&P Z {sp_z:+.1f}")
        if (kospi_z or 0) > 0:
            score += 0.1
        if not oil_surge:
            score += 0.1
        if score > 0.4:
            active.append({"id": "goldilocks", "strength": min(1.0, score), "evidence": ev})

    # 2. 지정학 위기: 유가 급등 + 금 강세 + 달러 강세
    if oil_surge or oil_5d_max > 8:
        ev = []
        score = 0.4
        ev.append(f"유가 5일 +{oil_5d_max:.1f}%")
        if gold_5d > 2:
            score += 0.2
            ev.append(f"금 5일 +{gold_5d:.1f}% (안전자산)")
        if dxy and dxy > 100:
            score += 0.1
            ev.append(f"DXY {dxy:.1f} (달러 강세)")
        if vix and vix > 22:
            score += 0.2
            ev.append(f"VIX {vix:.1f} ↑")
        active.append({"id": "geopolitical_crisis", "strength": min(1.0, score), "evidence": ev})

    # 3. AI capex 가속: NASDAQ + S&P 동반 강세
    if (nasdaq_z or 0) > 0.8 and (sp_z or 0) > 0.3:
        score = min(1.0, ((nasdaq_z or 0) + (sp_z or 0)) / 3)
        active.append({
            "id": "ai_capex_acceleration", "strength": score,
            "evidence": [f"NASDAQ Z {nasdaq_z:+.1f}", f"S&P Z {sp_z:+.1f}"],
        })

    # 4. 스태그플레이션: 유가 ↑ + 10Y ↑ + 주가 약세
    if oil_5d_max > 5 and ten_y and ten_y > 4.3 and (sp_z or 0) < 0:
        active.append({
            "id": "stagflation", "strength": 0.6,
            "evidence": [f"유가 5일 +{oil_5d_max:.1f}%", f"10Y {ten_y:.2f}%", f"S&P Z {sp_z:+.1f}"],
        })

    # 5. 침체: VIX 높음 + 주가 약세 + 장단기 역전
    if vix and vix > 25 and (sp_z or 0) < -1:
        score = 0.6
        ev = [f"VIX {vix:.1f} (불안)", f"S&P Z {sp_z:+.1f}"]
        if ten_y and three_m and ten_y < three_m:
            score += 0.2
            ev.append(f"장단기 역전 ({ten_y:.2f}<{three_m:.2f})")
        active.append({"id": "recession", "strength": min(1.0, score), "evidence": ev})

    # 6. 회복 초기: VIX 정상화 + Fed 금리인하 기대 (10Y < 3M 해소)
    if vix and 14 < vix < 22 and ten_y and three_m and ten_y > three_m and (sp_z or 0) > 0:
        if (kospi_z or 0) > 0.3 or (sp_z or 0) > 0.5:
            active.append({
                "id": "recovery_early", "strength": 0.5,
                "evidence": [f"VIX 정상화 {vix:.1f}", f"기간 spread {ten_y - three_m:.2f}pp"],
            })

    # 7. 위안 평가절하 / 미중 디커플링: KRW 약세 + DXY 강세
    if krw and krw > 1450 and (krw_z or 0) > 1:
        active.append({
            "id": "yuan_devaluation", "strength": 0.5,
            "evidence": [f"USD/KRW {krw:.0f} (Z {krw_z:+.1f})"],
        })

    # 8. BOJ 캐리 청산: USD/JPY 급등락
    if abs(jpy_5d) > 3:
        active.append({
            "id": "boj_carry_unwind", "strength": 0.5,
            "evidence": [f"USD/JPY 5일 {jpy_5d:+.1f}%"],
        })

    # 9. 확장 후기: 유가 점진 ↑ + 10Y ↑ + 주가 ↑ (모두 약하게)
    if oil_5d_max > 3 and oil_5d_max < 8 and ten_y and ten_y > 4.2 and (sp_z or 0) > 0:
        active.append({
            "id": "expansion_late", "strength": 0.5,
            "evidence": [f"유가 5일 +{oil_5d_max:.1f}%", f"10Y {ten_y:.2f}%", "S&P 강세 지속"],
        })

    # 시나리오 메타 합성
    for s in active:
        meta = SCENARIO_META.get(s["id"], {})
        s["name"] = meta.get("name", s["id"])
        s["favorable_sectors"] = meta.get("favorable", [])
        s["unfavorable_sectors"] = meta.get("unfavorable", [])

    return sorted(active, key=lambda x: x["strength"], reverse=True)


def detect_current_events() -> list[dict[str, Any]]:
    """정치·전쟁·정책 이벤트를 시장 데이터와 결합해 섹터 영향으로 변환."""
    macro = macro_dict()
    feed = {f.id: f for f in fetch_feed()}

    vix = _safe(macro.get("vix"), "price")
    ten_y = _safe(macro.get("treasury_10y"), "price")
    dxy = _safe(macro.get("dxy"), "price")
    krw = _safe(macro.get("usd_krw"), "price")
    krw_z = _safe(macro.get("usd_krw"), "zscore_60d", 0)
    nasdaq_z = _safe(macro.get("nasdaq"), "zscore_60d", 0)
    sp_z = _safe(macro.get("sp500"), "zscore_60d", 0)

    wti = feed.get("crude_wti")
    brent = feed.get("crude_brent")
    gold = feed.get("gold")
    natgas = feed.get("natgas_henry_hub")
    uranium = feed.get("uranium_u3o8")
    copper = feed.get("copper")
    aluminum = feed.get("aluminum")
    coffee = feed.get("coffee")
    sugar = feed.get("sugar")
    wheat = feed.get("wheat")
    corn = feed.get("corn")
    gallium = feed.get("gallium")
    germanium = feed.get("germanium")
    neodymium = feed.get("neodymium")

    oil_5d_max = max([_safe(wti, "change_pct_5d", 0), _safe(brent, "change_pct_5d", 0)])
    oil_120d_max = max([_safe(wti, "change_pct_120d", 0), _safe(brent, "change_pct_120d", 0)])
    oil_surge = bool(_safe(wti, "is_surge") or _safe(brent, "is_surge") or oil_5d_max > 5 or oil_120d_max > 20)
    gold_5d = _safe(gold, "change_pct_5d", 0)
    natgas_5d = _safe(natgas, "change_pct_5d", 0)
    uranium_60d = _safe(uranium, "change_pct_60d", 0)
    copper_60d = _safe(copper, "change_pct_60d", 0)
    aluminum_60d = _safe(aluminum, "change_pct_60d", 0)

    events: list[dict[str, Any]] = []

    # 2026-04 현재 뉴스 레이어: 호르무즈/이란 전쟁은 뉴스로 확인된 기본 이벤트.
    hormuz_score = 0.55
    hormuz_evidence = ["AP: 호르무즈 기뢰 제거·이란 전쟁으로 에너지 운송 차질 보도"]
    if oil_surge:
        hormuz_score += 0.2
        hormuz_evidence.append(f"원유 5일 최대 {oil_5d_max:+.1f}% / 6개월 최대 {oil_120d_max:+.1f}%")
    if gold_5d > 1.5:
        hormuz_score += 0.1
        hormuz_evidence.append(f"금 5일 {gold_5d:+.1f}%: 안전자산 수요")
    if natgas_5d > 3:
        hormuz_score += 0.08
        hormuz_evidence.append(f"천연가스 5일 {natgas_5d:+.1f}%: 에너지 공급 불안")
    if vix and vix > 22:
        hormuz_score += 0.07
        hormuz_evidence.append(f"VIX {vix:.1f}: 위험회피")
    events.append(_event_payload("iran_hormuz_war", hormuz_score, hormuz_evidence))

    ai_score = 0.0
    ai_evidence: list[str] = []
    if (nasdaq_z or 0) > 0.6 and (sp_z or 0) > 0:
        ai_score += 0.35
        ai_evidence.append(f"NASDAQ Z {nasdaq_z:+.1f}, S&P Z {sp_z:+.1f}: AI 성장주 수요")
    if (uranium_60d or 0) > 5:
        ai_score += 0.25
        ai_evidence.append(f"우라늄 3개월 {uranium_60d:+.1f}%: 원전/전력 병목 기대")
    if (copper_60d or 0) > 5:
        ai_score += 0.2
        ai_evidence.append(f"구리 3개월 {copper_60d:+.1f}%: 전력망/데이터센터 투자 proxy")
    if ai_score >= 0.35:
        events.append(_event_payload("ai_power_bottleneck", ai_score, ai_evidence))

    decoupling_score = 0.35
    decoupling_evidence = ["수출통제·관세·안보 공급망 재편은 상시 리스크"]
    if dxy and dxy > 100:
        decoupling_score += 0.1
        decoupling_evidence.append(f"DXY {dxy:.1f}: 달러 강세")
    if krw and krw > 1400:
        decoupling_score += 0.1
        decoupling_evidence.append(f"USD/KRW {krw:.0f}: 아시아 FX 압박")
    events.append(_event_payload("us_china_decoupling", decoupling_score, decoupling_evidence))

    if ten_y and ten_y > 4.2:
        rate_score = 0.45
        rate_evidence = [f"미 10년물 {ten_y:.2f}%: 할인율 부담"]
        if oil_surge:
            rate_score += 0.15
            rate_evidence.append("유가 충격은 인플레/금리인하 지연 리스크")
        events.append(_event_payload("higher_for_longer", rate_score, rate_evidence))

    if krw and krw > 1400:
        fx_score = 0.35 + (0.15 if (krw_z or 0) > 1 else 0)
        fx_evidence = [f"USD/KRW {krw:.0f}: 수입원가·외국인 수급 부담"]
        if (krw_z or 0) > 1:
            fx_evidence.append(f"KRW Z {krw_z:+.1f}: 60일 대비 원화 약세")
        events.append(_event_payload("usd_krw_fx_pressure", fx_score, fx_evidence))

    industrial_score = 0.0
    industrial_evidence: list[str] = []
    if (copper_60d or 0) > 8:
        industrial_score += 0.3
        industrial_evidence.append(f"구리 3개월 {copper_60d:+.1f}%: 전력망/산업 capex proxy")
    if (aluminum_60d or 0) > 8:
        industrial_score += 0.25
        industrial_evidence.append(f"알루미늄 3개월 {aluminum_60d:+.1f}%: 전력기기/차량 경량화 소재")
    if industrial_score >= 0.25:
        events.append(_event_payload("industrial_reflation", industrial_score, industrial_evidence))

    food_moves = [
        ("커피", coffee),
        ("설탕", sugar),
        ("밀", wheat),
        ("옥수수", corn),
    ]
    food_evidence = []
    for name, obj in food_moves:
        ret60 = _safe(obj, "change_pct_60d", 0)
        ret5 = _safe(obj, "change_pct_5d", 0)
        if (ret60 or 0) > 8:
            food_evidence.append(f"{name} 3개월 {ret60:+.1f}%")
        elif _safe(obj, "is_surge") and (ret5 or 0) > 0:
            food_evidence.append(f"{name} 단기 급등: 5일 {ret5:+.1f}%")
    if food_evidence:
        events.append(_event_payload("food_inflation", min(0.75, 0.25 + len(food_evidence) * 0.12), food_evidence))

    rare_evidence = []
    for label, obj in [("갈륨", gallium), ("게르마늄", germanium), ("네오디뮴", neodymium)]:
        if _safe(obj, "is_surge") or (_safe(obj, "change_pct_60d", 0) or 0) > 10:
            rare_evidence.append(f"{label}: 수출통제/방산·반도체 소재 병목 proxy")
    if rare_evidence:
        events.append(_event_payload("rare_earth_controls", min(0.75, 0.35 + len(rare_evidence) * 0.1), rare_evidence))

    if vix and vix > 22:
        events.append(_event_payload("credit_volatility", min(0.8, 0.35 + (vix - 22) / 30), [f"VIX {vix:.1f}: 변동성 확대"]))

    return sorted(events, key=lambda x: x["severity"], reverse=True)


def _event_payload(event_id: str, severity: float, evidence: list[str]) -> dict[str, Any]:
    meta = EVENT_META[event_id]
    return {
        "id": event_id,
        "title": meta["title"],
        "severity": round(max(0.0, min(1.0, severity)), 2),
        "status": meta["status"],
        "evidence": evidence,
        "favorable_sectors": meta["favorable"],
        "unfavorable_sectors": meta["unfavorable"],
        "source_notes": meta["source_notes"],
    }


def synthesize_sectors() -> dict[str, Any]:
    """commodity sentiment + 활성 시나리오 → 27섹터 종합 점수 + TOP/BOTTOM."""
    sentiments = {s["sector_id"]: s for s in all_sector_sentiments()}
    active = detect_active_scenarios()
    current_events = detect_current_events()

    # 모든 27 섹터 초기 score = commodity sentiment score
    scores: dict[str, float] = {sid: float(s.get("score", 0)) for sid, s in sentiments.items()}
    drivers: dict[str, list[str]] = {sid: [] for sid in sentiments.keys()}

    # commodity 사유는 이미 sentiment에 들어 있음
    for sid, s in sentiments.items():
        for sig in s.get("bullish_signals", []):
            drivers[sid].append(f"+ {sig}")
        for sig in s.get("bearish_signals", []):
            drivers[sid].append(f"− {sig}")

    # 시나리오 영향 합산
    for scen in active:
        meta = SCENARIO_META.get(scen["id"], {})
        weight = scen["strength"] * meta.get("weight_per_sector", 1.5)
        for sec in meta.get("favorable", []):
            scores[sec] = scores.get(sec, 0) + weight
            drivers.setdefault(sec, []).append(f"+ [{scen['name']}] 시나리오 우호")
        for sec in meta.get("unfavorable", []):
            scores[sec] = scores.get(sec, 0) - weight
            drivers.setdefault(sec, []).append(f"− [{scen['name']}] 시나리오 부정")

    # 현재 정치/전쟁/정책 이벤트 영향 합산
    for event in current_events:
        meta = EVENT_META.get(event["id"], {})
        weight = event["severity"] * meta.get("weight", 1.5)
        for sec in event.get("favorable_sectors", []):
            scores[sec] = scores.get(sec, 0) + weight
            drivers.setdefault(sec, []).append(f"+ [현재 이슈] {event['title']} 수혜")
        for sec in event.get("unfavorable_sectors", []):
            scores[sec] = scores.get(sec, 0) - weight
            drivers.setdefault(sec, []).append(f"− [현재 이슈] {event['title']} 부담")

    # 각 섹터 종합 dict
    enriched: list[dict[str, Any]] = []
    for sid in sentiments.keys():
        score = round(scores.get(sid, 0), 2)
        sentiment = "bullish" if score > 0.5 else "bearish" if score < -0.5 else "neutral"
        enriched.append({
            "sector_id": sid,
            "synthesis_score": score,
            "synthesis_sentiment": sentiment,
            "drivers": drivers.get(sid, []),
        })

    sorted_secs = sorted(enriched, key=lambda x: x["synthesis_score"], reverse=True)
    return {
        "current_events": current_events,
        "active_scenarios": active,
        "all_sectors": enriched,
        "top_sectors": sorted_secs[:5],
        "bottom_sectors": [s for s in sorted_secs[-5:] if s["synthesis_score"] < 0][::-1],
    }
