"""원자재 5년 history + regime persistence + 일일 리포트.

기존 services/macro_commodity.py가 제공하는 단기(120일) 점수 위에 long-context 레이어를 얹는다:
  - 5년 일봉 캐시 (data/commodity_history/{id}.csv) — 한 번 받고 incremental
  - 5y 백분위, 3년 breakout, 12개월 trend, 변동성 regime z-score, momentum 가속
  - 6 regime 라벨 (Sleeper/Breakout/Steady/Topping/Crash/Rebound) — 기존 _classify와 별개 history-aware 라벨
  - state 영속화 (data/commodity_regime_state.json) — regime_since, days_in_zone, prev regime
  - regime 변화 발생 시 자동 일일 리포트 (Output/reports/commodity-regime-YYYY-MM-DD.md)
  - 일요일에 주간 요약 (Output/reports/commodity-regime-weekly-YYYY-Www.md)

명세: wiki/macro/05-regime-scoring.md (locked-v1)
호출: backend/main.py의 _run_daily_refresh() step 5에서 1회/일.
"""
from __future__ import annotations

import json
import math
import os
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yfinance as yf

try:
    from services.runtime_controls import limit_yfinance
except Exception:
    from contextlib import contextmanager

    @contextmanager
    def limit_yfinance():
        yield


# ═══════════════════════════════════════════════════════════════════════════
# 경로
# ═══════════════════════════════════════════════════════════════════════════
DATA_ROOT = Path(os.getenv("STOCK_DATA_DIR", str(Path(__file__).resolve().parents[2] / "data")))
HISTORY_DIR = DATA_ROOT / "commodity_history"
STATE_PATH = DATA_ROOT / "commodity_regime_state.json"
REPORT_DIR = Path(__file__).resolve().parents[2] / "Output" / "reports"


# ═══════════════════════════════════════════════════════════════════════════
# 추적 대상 (직접 ticker 22 + computed ratio 3 = 25)
# ═══════════════════════════════════════════════════════════════════════════
REGIME_TARGETS: list[dict[str, Any]] = [
    # 에너지
    {"id": "crude_wti", "ticker": "CL=F", "name": "WTI 원유", "category": "에너지", "is_proxy": False},
    {"id": "crude_brent", "ticker": "BZ=F", "name": "Brent 원유", "category": "에너지", "is_proxy": False},
    {"id": "natgas_henry_hub", "ticker": "NG=F", "name": "Henry Hub 천연가스", "category": "에너지", "is_proxy": False},
    {"id": "heating_oil", "ticker": "HO=F", "name": "난방유", "category": "에너지", "is_proxy": False},
    {"id": "gasoline_rbob", "ticker": "RB=F", "name": "RBOB 휘발유", "category": "에너지", "is_proxy": False},
    # 산업금속
    {"id": "copper", "ticker": "HG=F", "name": "구리", "category": "산업금속", "is_proxy": False},
    {"id": "aluminum", "ticker": "ALI=F", "name": "알루미늄", "category": "산업금속", "is_proxy": False, "may_be_missing": True},
    {"id": "iron_ore", "ticker": "TIO=F", "name": "철광석 62%", "category": "산업금속", "is_proxy": False, "may_be_missing": True},
    # 귀금속
    {"id": "gold", "ticker": "GC=F", "name": "금", "category": "귀금속", "is_proxy": False},
    {"id": "silver", "ticker": "SI=F", "name": "은", "category": "귀금속", "is_proxy": False},
    {"id": "platinum", "ticker": "PL=F", "name": "백금", "category": "귀금속", "is_proxy": False},
    {"id": "palladium", "ticker": "PA=F", "name": "팔라듐", "category": "귀금속", "is_proxy": False},
    # 농산물
    {"id": "corn", "ticker": "ZC=F", "name": "옥수수", "category": "농산물", "is_proxy": False},
    {"id": "soybean", "ticker": "ZS=F", "name": "대두", "category": "농산물", "is_proxy": False},
    {"id": "wheat", "ticker": "ZW=F", "name": "밀", "category": "농산물", "is_proxy": False},
    {"id": "sugar", "ticker": "SB=F", "name": "설탕", "category": "농산물", "is_proxy": False},
    {"id": "coffee", "ticker": "KC=F", "name": "커피", "category": "농산물", "is_proxy": False},
    {"id": "cotton", "ticker": "CT=F", "name": "면화", "category": "농산물", "is_proxy": False},
    {"id": "cocoa", "ticker": "CC=F", "name": "코코아", "category": "농산물", "is_proxy": False},
    # ETF 프록시 (광산주 바스켓 — equity beta 영향 주의)
    {"id": "uranium_etf", "ticker": "URA", "name": "우라늄 (URA ETF)", "category": "희소금속", "is_proxy": True},
    {"id": "lithium_etf", "ticker": "LIT", "name": "리튬 (LIT ETF)", "category": "희소금속", "is_proxy": True},
    {"id": "rare_earth_etf", "ticker": "REMX", "name": "희토류 (REMX ETF)", "category": "희소금속", "is_proxy": True},
]

RATIO_TARGETS: list[dict[str, Any]] = [
    {"id": "copper_gold_ratio", "name": "구리/금 비율", "category": "매크로신호", "numerator": "copper", "denominator": "gold"},
    {"id": "gold_silver_ratio", "name": "금/은 비율", "category": "매크로신호", "numerator": "gold", "denominator": "silver"},
    {"id": "platinum_gold_ratio", "name": "백금/금 비율", "category": "매크로신호", "numerator": "platinum", "denominator": "gold"},
]


# ═══════════════════════════════════════════════════════════════════════════
# 추천 매트릭스 (Regime → action) — Cause는 Phase B 수동, 여기서는 base만 부여
# ═══════════════════════════════════════════════════════════════════════════
RECOMMENDATION_MATRIX: dict[str, dict[str, str]] = {
    "Sleeper": {"action": "Watch", "note": "수년 잠자는 중 — catalyst 등장 시 1차 진입 검토. 원인 확인 전 Buy 금지."},
    "Breakout": {"action": "Buy", "note": "장기 박스권 막 탈출 — 구조적 원인이면 매수, 일시적이면 단기거래."},
    "Steady": {"action": "Hold", "note": "정상 추세 — 보유."},
    "Topping": {"action": "Trim/Sell", "note": "고점 둔화 — 일시적 원인 해소 임박이면 매도, 구조적이면 일부 수익실현."},
    "Crash": {"action": "Watch", "note": "급락 진행 — 바닥 확인 전 진입 금지. 일시적 원인이면 Rebound 신호 대기."},
    "Rebound": {"action": "Buy", "note": "Crash 후 반등 초기 — 추세 재개 가능성. 사업구조 검증 후 [[01-commodities]] 매핑."},
}


# ═══════════════════════════════════════════════════════════════════════════
# History fetch + cache
# ═══════════════════════════════════════════════════════════════════════════
def _today_utc_date():
    return datetime.now(timezone.utc).date()


def _fetch_history(ticker: str, days: int = 5 * 365 + 30) -> pd.DataFrame | None:
    """yfinance로 5년 + 30일 buffer fetch. 실패 시 None."""
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)
    try:
        with limit_yfinance():
            df = yf.download(
                ticker, start=start, end=end + timedelta(days=1),
                progress=False, auto_adjust=False, threads=False,
            )
        if df is None or df.empty:
            return None
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        if "Close" not in df.columns:
            return None
        out = df[["Close"]].dropna()
        out.index = pd.to_datetime(out.index).tz_localize(None)
        return out if not out.empty else None
    except Exception:
        return None


def _load_cached_history(item_id: str) -> pd.DataFrame | None:
    path = HISTORY_DIR / f"{item_id}.csv"
    if not path.exists():
        return None
    try:
        df = pd.read_csv(path, parse_dates=["Date"], index_col="Date")
        df.index = pd.to_datetime(df.index).tz_localize(None)
        return df
    except Exception:
        return None


def _save_history(item_id: str, df: pd.DataFrame) -> None:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    out = df.copy()
    out.index.name = "Date"
    out.to_csv(HISTORY_DIR / f"{item_id}.csv")


def update_history(item_id: str, ticker: str) -> pd.DataFrame | None:
    """Cold start: 5년 일괄. Warm: 마지막 30일 다시 받아서 merge (yfinance 늦은 데이터 추가 대비)."""
    cached = _load_cached_history(item_id)
    if cached is None or cached.empty:
        df = _fetch_history(ticker, days=5 * 365 + 30)
        if df is not None and not df.empty:
            _save_history(item_id, df)
        return df

    last_date = cached.index[-1]
    today = pd.Timestamp(_today_utc_date())
    days_behind = (today - last_date).days
    if days_behind < 1:
        return cached  # 오늘 이미 갱신됨

    new_df = _fetch_history(ticker, days=max(days_behind + 5, 30))
    if new_df is None or new_df.empty:
        return cached

    merged = pd.concat([cached, new_df])
    merged = merged[~merged.index.duplicated(keep="last")].sort_index()
    cutoff = today - pd.Timedelta(days=5 * 365 + 30)
    merged = merged[merged.index >= cutoff]
    _save_history(item_id, merged)
    return merged


# ═══════════════════════════════════════════════════════════════════════════
# Metric 계산
# ═══════════════════════════════════════════════════════════════════════════
def compute_metrics(history: pd.DataFrame) -> dict[str, Any] | None:
    if history is None or history.empty or len(history) < 60:
        return None
    closes = history["Close"].dropna()
    if len(closes) < 60:
        return None

    price = float(closes.iloc[-1])

    # 5y percentile
    pct_5y = float((closes < price).mean())

    # 5y high/low distance
    high_5y = float(closes.max())
    low_5y = float(closes.min())
    pct_from_high = (price - high_5y) / high_5y if high_5y else 0.0
    pct_from_low = (price - low_5y) / low_5y if low_5y else 0.0

    def _ret(n: int) -> float | None:
        if len(closes) < n + 1:
            return None
        p_n = float(closes.iloc[-(n + 1)])
        return ((price - p_n) / p_n) if p_n else None

    ret_30d = _ret(30)
    ret_60d = _ret(60)
    ret_252d = _ret(252)

    # 변동성 regime: 60일 realized vol vs 5년 rolling-60d vol 평균/표준편차
    daily_returns = closes.pct_change().dropna()
    vol_60d_now = float(daily_returns.iloc[-60:].std()) * math.sqrt(252) if len(daily_returns) >= 60 else None
    vol_z = 0.0
    if len(daily_returns) >= 252 + 60:
        rolling_vol = (daily_returns.rolling(60).std() * math.sqrt(252)).dropna()
        if len(rolling_vol) >= 252:
            mean_v = float(rolling_vol.mean())
            std_v = float(rolling_vol.std())
            if std_v and not math.isnan(std_v) and vol_60d_now is not None:
                vol_z = (vol_60d_now - mean_v) / std_v

    # 12개월 trend (선형회귀 기울기 / 현재가, annualized)
    trend_12m = None
    momentum_accel = None
    if len(closes) >= 252:
        last_year = closes.iloc[-252:]
        x = pd.Series(range(len(last_year)), index=last_year.index, dtype=float)
        x_dev = x - x.mean()
        denom = float((x_dev ** 2).sum())
        if denom > 0:
            slope_252 = float(((last_year - last_year.mean()) * x_dev).sum() / denom)
            trend_12m = (slope_252 * 252) / price if price else None

            if len(closes) >= 60:
                last_60 = closes.iloc[-60:]
                x60 = pd.Series(range(len(last_60)), index=last_60.index, dtype=float)
                x60_dev = x60 - x60.mean()
                denom60 = float((x60_dev ** 2).sum())
                if denom60 > 0:
                    slope_60 = float(((last_60 - last_60.mean()) * x60_dev).sum() / denom60)
                    if abs(slope_252) > 1e-12:
                        momentum_accel = slope_60 / slope_252

    # 3년 breakout/breakdown
    breakout_3y = False
    breakdown_3y = False
    if len(closes) >= 3 * 252:
        high_3y = float(closes.iloc[-3 * 252:].max())
        low_3y = float(closes.iloc[-3 * 252:].min())
        breakout_3y = price >= high_3y * 0.99 and (ret_60d or 0) > 0.10
        breakdown_3y = price <= low_3y * 1.01 and (ret_60d or 0) < -0.10

    return {
        "price": round(price, 4),
        "pct_5y": round(pct_5y, 3),
        "pct_from_high_5y": round(pct_from_high, 3),
        "pct_from_low_5y": round(pct_from_low, 3),
        "ret_30d": round(ret_30d, 3) if ret_30d is not None else None,
        "ret_60d": round(ret_60d, 3) if ret_60d is not None else None,
        "ret_252d": round(ret_252d, 3) if ret_252d is not None else None,
        "vol_60d_annualized": round(vol_60d_now, 3) if vol_60d_now is not None else None,
        "vol_z": round(vol_z, 2),
        "trend_12m": round(trend_12m, 3) if trend_12m is not None else None,
        "momentum_accel": round(momentum_accel, 2) if momentum_accel is not None else None,
        "breakout_3y": breakout_3y,
        "breakdown_3y": breakdown_3y,
        "data_points": int(len(closes)),
    }


# ═══════════════════════════════════════════════════════════════════════════
# Regime 분류 (priority: Crash > Rebound > Breakout > Topping > Sleeper > Steady)
# ═══════════════════════════════════════════════════════════════════════════
def classify_regime(metrics: dict[str, Any], prev_regime: str | None) -> str:
    pct = metrics["pct_5y"]
    ret_30 = metrics.get("ret_30d") or 0.0
    ret_60 = metrics.get("ret_60d") or 0.0
    pct_from_high = metrics.get("pct_from_high_5y") or 0.0
    vol_z = metrics.get("vol_z") or 0.0
    trend = metrics.get("trend_12m") or 0.0
    accel = metrics.get("momentum_accel")
    breakout_3y = metrics.get("breakout_3y", False)

    # Crash: 60일 -25% OR 5년 고점 대비 -40% (60일 안에 진입)
    if ret_60 < -0.25 or (pct_from_high < -0.40 and ret_60 < -0.10):
        return "Crash"

    # Rebound: 직전이 Crash + 30일 +15% 이상 + vol 여전히 확장
    if prev_regime == "Crash" and ret_30 > 0.15 and vol_z > 0:
        return "Rebound"

    # Breakout: 3년 고점 돌파 OR (백분위 ≥45% 빠르게 + vol 확장 + 60일 +20%)
    if breakout_3y or (pct >= 0.45 and ret_60 > 0.20 and vol_z > 0.5):
        return "Breakout"

    # Topping: 백분위 ≥75% + momentum 둔화 + vol 확장
    if pct >= 0.75 and accel is not None and accel < 0.7 and vol_z > 0:
        return "Topping"

    # Sleeper: 백분위 ≤25% + vol 압축 + 추세 평탄
    if pct <= 0.25 and vol_z < -0.5 and -0.05 <= trend <= 0.05:
        return "Sleeper"

    return "Steady"


# ═══════════════════════════════════════════════════════════════════════════
# State 영속화
# ═══════════════════════════════════════════════════════════════════════════
def load_state() -> dict[str, Any]:
    if not STATE_PATH.exists():
        return {"updated": None, "items": {}, "errors_last_run": []}
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {"updated": None, "items": {}, "errors_last_run": []}


def save_state(state: dict[str, Any]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2, default=str), encoding="utf-8")


def _update_item(state: dict[str, Any], spec: dict[str, Any], regime: str, metrics: dict[str, Any]) -> dict[str, Any]:
    today_iso = _today_utc_date().isoformat()
    items = state.setdefault("items", {})
    item = items.get(spec["id"], {})
    prev = item.get("current_regime")

    if prev != regime:
        item["previous_regime"] = prev
        item["previous_regime_since"] = item.get("regime_since")
        item["previous_regime_days"] = item.get("days_in_zone", 0)
        item["regime_since"] = today_iso
        item["days_in_zone"] = 0
        item["regime_change"] = True
    else:
        since = item.get("regime_since") or today_iso
        item["regime_since"] = since
        try:
            d = (_today_utc_date() - datetime.fromisoformat(since).date()).days
            item["days_in_zone"] = max(d, 0)
        except Exception:
            item["days_in_zone"] = 0
        item["regime_change"] = False

    item["id"] = spec["id"]
    item["name"] = spec.get("name", spec["id"])
    item["category"] = spec.get("category")
    item["is_proxy"] = bool(spec.get("is_proxy"))
    item["current_regime"] = regime
    item["metrics"] = metrics
    item["last_update"] = today_iso
    items[spec["id"]] = item
    return item


# ═══════════════════════════════════════════════════════════════════════════
# 리포트 생성
# ═══════════════════════════════════════════════════════════════════════════
def _vol_label(z: float) -> str:
    if z > 0.5:
        return "확장"
    if z < -0.5:
        return "압축"
    return "정상"


def _accel_label(a: float | None) -> str:
    if a is None:
        return "n/a"
    if a > 1.5:
        return "가속"
    if a < 0.5:
        return "둔화"
    return "유지"


def generate_daily_report(state: dict[str, Any], force: bool = False) -> Path | None:
    today = _today_utc_date()
    items: dict[str, Any] = state.get("items", {})
    changed = [(iid, it) for iid, it in items.items() if it.get("regime_change")]

    if not changed and not force:
        return None

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"commodity-regime-{today.isoformat()}.md"

    lines: list[str] = [
        "---",
        f"title: 원자재 Regime 일일 리포트 — {today.isoformat()}",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "tags: [macro, commodities, regime, daily]",
        "phase: regime-v1",
        "---",
        "",
        f"# 원자재 Regime 일일 리포트 — {today.isoformat()}",
        "",
        f"생성: {datetime.now(timezone.utc).isoformat()}  ",
        f"전체 추적: **{len(items)}개** / 오늘 변화: **{len(changed)}개**  ",
        "명세: [[05-regime-scoring]] | 인과 매핑: [[01-commodities]]",
        "",
    ]

    if changed:
        lines += ["## ⚠️ 오늘 regime 변화 발생", ""]
        lines += [
            "| 원자재 | 이전 (일수) | → | 현재 | 5y 백분위 | 60d | vol z | 추천 |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for iid, it in sorted(changed, key=lambda kv: -((kv[1].get("metrics") or {}).get("pct_5y") or 0)):
            m = it.get("metrics") or {}
            rec = RECOMMENDATION_MATRIX.get(it["current_regime"], {})
            lines.append(
                f"| {it.get('name', iid)} | {it.get('previous_regime') or '—'}"
                f" ({it.get('previous_regime_days', '—')}일) | → | **{it['current_regime']}**"
                f" | {(m.get('pct_5y') or 0) * 100:.0f}% | {(m.get('ret_60d') or 0) * 100:+.1f}%"
                f" | {m.get('vol_z', 0):+.1f} | {rec.get('action', '—')} |"
            )
        lines.append("")

        for iid, it in changed:
            m = it.get("metrics") or {}
            rec = RECOMMENDATION_MATRIX.get(it["current_regime"], {})
            proxy_warn = "  \n> ⚠️ ETF 프록시 — equity beta 영향. 분기 USGS로 실제 가격 재확인 필요." if it.get("is_proxy") else ""
            lines += [
                f"### {it.get('name', iid)} (`{iid}`)",
                "",
                f"- **이전 regime**: {it.get('previous_regime') or '—'} ({it.get('previous_regime_days', 0)}일 유지)",
                f"- **현재 regime**: **{it['current_regime']}** (오늘 시작)",
                f"- **5년 백분위**: {(m.get('pct_5y') or 0) * 100:.0f}%  (5년 고점 대비 {(m.get('pct_from_high_5y') or 0) * 100:+.1f}%, 5년 저점 대비 {(m.get('pct_from_low_5y') or 0) * 100:+.1f}%)",
                f"- **수익률**: 30일 {(m.get('ret_30d') or 0) * 100:+.1f}%, 60일 {(m.get('ret_60d') or 0) * 100:+.1f}%, 12개월 {(m.get('ret_252d') or 0) * 100:+.1f}%",
                f"- **추세**: 12개월 {(m.get('trend_12m') or 0) * 100:+.1f}% (annualized) — momentum {_accel_label(m.get('momentum_accel'))} ({m.get('momentum_accel') or 'n/a'})",
                f"- **변동성**: 60일 vol {(m.get('vol_60d_annualized') or 0) * 100:.0f}% (vs 5년 평균 z={m.get('vol_z', 0):+.1f}, {_vol_label(m.get('vol_z') or 0)})",
                f"- **추천 (Cause 분석 전)**: **{rec.get('action', '—')}** — {rec.get('note', '')}{proxy_warn}",
                "",
                "**다음 단계 (Phase B 수동)**: 원인 지속성을 Structural / Transient / Unknown 중 하나로 분류 → "
                "`wiki/macro/regime-causes/` ingest. 사업구조 검증 후 [[01-commodities]] 매핑으로 KR/US 종목 변환.",
                "",
            ]

    # 전체 스냅샷
    lines += ["## 전체 현황 스냅샷", "",
              "| 원자재 | regime | 일수 | 5y % | 30d | 60d | trend 12m | vol z |",
              "|---|---|---|---|---|---|---|---|"]
    for iid, it in sorted(items.items(), key=lambda kv: kv[0]):
        m = it.get("metrics") or {}
        lines.append(
            f"| {it.get('name', iid)} | {it.get('current_regime', '—')}"
            f" | {it.get('days_in_zone', 0)}일 | {(m.get('pct_5y') or 0) * 100:.0f}%"
            f" | {(m.get('ret_30d') or 0) * 100:+.1f}% | {(m.get('ret_60d') or 0) * 100:+.1f}%"
            f" | {(m.get('trend_12m') or 0) * 100:+.1f}% | {m.get('vol_z', 0):+.1f} |"
        )

    errors = state.get("errors_last_run") or []
    if errors:
        lines += ["", "## 데이터 결측 / 결함", "", "| 원자재 | 사유 |", "|---|---|"]
        for e in errors:
            lines.append(f"| {e.get('id', '—')} | {e.get('reason', '—')} |")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def generate_weekly_summary(state: dict[str, Any]) -> Path | None:
    today = _today_utc_date()
    iso = today.isocalendar()
    year, week = iso[0], iso[1]
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    path = REPORT_DIR / f"commodity-regime-weekly-{year}-W{week:02d}.md"

    items: dict[str, Any] = state.get("items", {})

    # regime별 집계
    counts: dict[str, list[str]] = {k: [] for k in RECOMMENDATION_MATRIX}
    for iid, it in items.items():
        r = it.get("current_regime")
        if r in counts:
            counts[r].append(it.get("name", iid))

    lines = [
        "---",
        f"title: 원자재 Regime 주간 요약 — {year} W{week:02d}",
        f"created: {today.isoformat()}",
        f"updated: {today.isoformat()}",
        "tags: [macro, commodities, regime, weekly]",
        "phase: regime-v1",
        "---",
        "",
        f"# 원자재 Regime 주간 요약 — {year} W{week:02d}",
        "",
        f"기준일: {today.isoformat()} (UTC)  ",
        f"전체 추적: **{len(items)}개**  ",
        "명세: [[05-regime-scoring]] | 인과 매핑: [[01-commodities]]",
        "",
        "## Regime 분포",
        "",
        "| Regime | 개수 | 항목 |",
        "|---|---|---|",
    ]
    for regime, names in counts.items():
        lines.append(f"| {regime} | {len(names)} | {', '.join(names) if names else '—'} |")

    lines += ["", "## 이번 주 주목 — Buy/Sell 추천", ""]
    actionable = []
    for iid, it in items.items():
        rec = RECOMMENDATION_MATRIX.get(it.get("current_regime"), {})
        if rec.get("action") in {"Buy", "Trim/Sell"}:
            actionable.append((iid, it, rec))

    if actionable:
        lines += [
            "| 원자재 | regime | 일수 | 5y % | 60d | 추천 | 비고 |",
            "|---|---|---|---|---|---|---|",
        ]
        for iid, it, rec in actionable:
            m = it.get("metrics") or {}
            lines.append(
                f"| {it.get('name', iid)} | {it['current_regime']} | {it.get('days_in_zone', 0)}일"
                f" | {(m.get('pct_5y') or 0) * 100:.0f}%"
                f" | {(m.get('ret_60d') or 0) * 100:+.1f}%"
                f" | **{rec['action']}** | {rec['note']} |"
            )
    else:
        lines.append("(이번 주 Buy/Sell 시그널 없음 — 모두 Hold/Watch)")

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


# ═══════════════════════════════════════════════════════════════════════════
# 메인 실행
# ═══════════════════════════════════════════════════════════════════════════
def run_daily_update(verbose: bool = False) -> dict[str, Any]:
    """매일 1회 실행: history incremental update → regime 분류 → state 영속화 → 리포트."""
    state = load_state()
    state.setdefault("items", {})
    errors: list[dict[str, str]] = []
    updated = 0
    histories: dict[str, pd.DataFrame] = {}

    # Direct tickers
    for spec in REGIME_TARGETS:
        try:
            hist = update_history(spec["id"], spec["ticker"])
            if hist is None or len(hist) < 60:
                reason = "insufficient_data" if hist is not None else "fetch_failed"
                if spec.get("may_be_missing"):
                    reason += " (may_be_missing)"
                errors.append({"id": spec["id"], "reason": reason})
                continue
            histories[spec["id"]] = hist
            metrics = compute_metrics(hist)
            if metrics is None:
                errors.append({"id": spec["id"], "reason": "metrics_failed"})
                continue
            prev = (state["items"].get(spec["id"]) or {}).get("current_regime")
            regime = classify_regime(metrics, prev)
            _update_item(state, spec, regime, metrics)
            updated += 1
            if verbose:
                print(f"  [{spec['id']:24}] {regime:9} pct_5y={metrics['pct_5y'] * 100:5.1f}% ret_60d={(metrics.get('ret_60d') or 0) * 100:+5.1f}%")
        except Exception as e:
            errors.append({"id": spec["id"], "reason": f"exception: {type(e).__name__}: {e}"})
            if verbose:
                traceback.print_exc()

    # Computed ratios
    for spec in RATIO_TARGETS:
        try:
            num = histories.get(spec["numerator"])
            den = histories.get(spec["denominator"])
            if num is None or den is None:
                errors.append({"id": spec["id"], "reason": "missing_components"})
                continue
            ratio_df = pd.DataFrame({"Close": num["Close"] / den["Close"]}).dropna()
            if len(ratio_df) < 60:
                errors.append({"id": spec["id"], "reason": "ratio_insufficient"})
                continue
            metrics = compute_metrics(ratio_df)
            if metrics is None:
                continue
            prev = (state["items"].get(spec["id"]) or {}).get("current_regime")
            regime = classify_regime(metrics, prev)
            _update_item(state, spec, regime, metrics)
            updated += 1
            if verbose:
                print(f"  [{spec['id']:24}] {regime:9} pct_5y={metrics['pct_5y'] * 100:5.1f}%")
        except Exception as e:
            errors.append({"id": spec["id"], "reason": f"ratio_exception: {type(e).__name__}: {e}"})

    state["updated"] = datetime.now(timezone.utc).isoformat()
    state["errors_last_run"] = errors
    save_state(state)

    daily_report = generate_daily_report(state)
    weekly_report = None
    if datetime.now(timezone.utc).weekday() == 6:
        weekly_report = generate_weekly_summary(state)

    return {
        "updated_count": updated,
        "errors_count": len(errors),
        "errors": errors,
        "regime_changes": sum(1 for it in state["items"].values() if it.get("regime_change")),
        "daily_report": str(daily_report) if daily_report else None,
        "weekly_report": str(weekly_report) if weekly_report else None,
        "state_path": str(STATE_PATH),
    }


if __name__ == "__main__":
    result = run_daily_update(verbose=True)
    print("\n=== run_daily_update 결과 ===")
    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
