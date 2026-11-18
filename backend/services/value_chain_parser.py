"""wiki/macro/04-value-chain.md → 27개 섹터 구조화 추출.

각 섹터 블록의 Mermaid graph에서 Tier 노드를 파싱한다.
Mermaid는 27개 모두 일관되게 작성되어 있어 가장 안정적인 소스다.

YAML 블록(있을 때만)에서 추가 메타데이터(role, signal_map, cost_drivers) 보강.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

# 섹터 한글명 → API id 매핑 (wiki/macro/02-indicators.md의 27섹터와 동기화)
SECTOR_ID_MAP: dict[str, str] = {
    "AI/반도체": "ai_semi",
    "로봇": "robotics",
    "SMR/원자력": "smr_nuclear",
    "사이버보안": "cybersec",
    "우주항공/방산": "aerospace",
    "생명공학": "biotech",
    "양자컴퓨팅": "quantum",
    "수소/에너지": "hydrogen_energy",
    "이차전지/배터리": "battery",
    "전기차 완성차": "ev",
    "EV 소재/부품": "ev_materials",
    "조선": "shipbuilding",
    "철강/비철": "steel",
    "디스플레이": "display",
    "인터넷 플랫폼": "platform",
    "게임": "gaming",
    "K-콘텐츠/엔터": "k_content",
    "화장품": "cosmetics",
    "음식료": "food",
    "유통/이커머스": "retail",
    "의류/패션": "apparel",
    "건설/건자재": "construction",
    "금융": "finance",
    "통신/유틸리티": "telecom",
    "지주사/리츠": "holding_reit",
    "의료기기/미용": "medical_device",
    "호텔/레저/여행": "hotel_leisure",
}

WIKI_VALUE_CHAIN = Path(__file__).resolve().parents[2] / "wiki" / "macro" / "04-value-chain.md"

# 캐시 (mtime 기반)
_PARSED_CACHE: tuple[float, list[dict[str, Any]]] | None = None


# ─────────────────────────────────────────────────────────
# 정규식
# ─────────────────────────────────────────────────────────
RE_SECTOR_HEADING = re.compile(r"^## (\d+)\.\s+(.+?)\s*$", re.MULTILINE)
RE_MERMAID_BLOCK = re.compile(r"```mermaid\s*\n(.*?)\n```", re.DOTALL)
RE_TIER_NODE = re.compile(
    r"(T(\d+)(?:_\w+)?)\s*\[\s*\"((?:[^\"\\]|\\.)*)\"\s*\]"
)
RE_KR_TICKER = re.compile(r"([가-힣A-Za-z][가-힣A-Za-z0-9·\-\.\s]*)\((\d{6})\)")
RE_US_TICKER = re.compile(r"\b([A-Z]{1,6})(?:\s*\(US\))?\b")
RE_HIDDEN_ALPHA = re.compile(r"^>\s*\*\*Hidden Alpha\*\*[:：]?\s*(.+?)$", re.MULTILINE | re.DOTALL)
RE_TIER_YAML_BLOCK = re.compile(r"```yaml\s*\n(.*?)\n```", re.DOTALL)

# Tier 라벨 prefix(이모지 + 역할 일반어) 추출 — 어떤 게 있어도 끝 위치까지
RE_TIER_HEADER = re.compile(r"^([\W_]{1,4})?\s*Tier\s*\d+\s*([^\n<]+)?", re.IGNORECASE)


def _split_sectors(text: str) -> list[tuple[int, str, int, int]]:
    """`## N. 섹터명` 헤딩으로 본문을 분할. (sector_no, name, start, end) 반환.

    헤딩 번호가 1~27인 것만 채택. 1·2·3은 도입부(페이지 철학, Tier 정의, 27개 섹터 커버리지)와
    실제 섹터(1.AI/반도체, 2.로봇, 3.SMR)가 충돌하니, 도입부 패턴은 이름 휴리스틱으로 제외.
    """
    matches = list(RE_SECTOR_HEADING.finditer(text))
    sectors: list[tuple[int, str, int, int]] = []
    for i, m in enumerate(matches):
        no = int(m.group(1))
        name = m.group(2).strip()
        # 도입부 헤딩 제외
        if name in ("페이지 철학", "Tier 정의", "27개 섹터 커버리지", "종합", "메타 정보", "Tier 정의 (공통)"):
            continue
        if no < 1 or no > 27:
            continue
        # 다음 헤딩(또는 EOF)까지가 본문
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        sectors.append((no, name, m.end(), end))
    return sectors


def _extract_kr_players(label: str) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    seen: set[str] = set()
    for m in RE_KR_TICKER.finditer(label):
        name = m.group(1).strip().rstrip("·,")
        ticker = m.group(2)
        if ticker in seen:
            continue
        seen.add(ticker)
        # 이름 정리: "에이·비" → "에이비" 같은 노이즈 제거 X (그대로 유지)
        out.append({"name": name, "ticker": ticker})
    return out


def _extract_us_players(label: str) -> list[str]:
    """대문자 토큰 중 흔한 false positive 제거."""
    blacklist = {
        "T", "TIER", "AI", "EV", "ESS", "GPU", "CPU", "ASIC", "RAM", "DRAM", "NAND",
        "HBM", "TSV", "EUV", "DUV", "ALD", "CVD", "CMP", "PR", "OEM", "ODM", "ETF",
        "API", "USD", "EUR", "JPY", "KRW", "CAGR", "CDMO", "FDA", "PDUFA", "GLP",
        "PEM", "MRI", "SMR", "PJM", "ASIC", "II", "III", "IV", "AMR", "AGV", "PCB",
        "OLED", "LED", "LCD", "QLED", "LFP", "LMFP", "MES", "ERP", "ESS", "BMS",
        "VR", "AR", "MR", "XR", "CRM", "B2B", "B2C", "DTC", "K", "VIP", "FSC", "LCC",
        "YoY", "MoM", "QoQ", "EPS", "PER", "PBR", "ROE", "EBITDA", "GAAP",
    }
    out: list[str] = []
    seen: set[str] = set()
    for m in RE_US_TICKER.finditer(label):
        sym = m.group(1)
        if sym in blacklist or sym in seen or len(sym) < 2:
            continue
        # 한글이 바로 앞뒤에 붙어있으면 ticker가 아닐 가능성 높음
        seen.add(sym)
        out.append(sym)
    return out


def _clean_tier_role(label: str) -> str:
    """Mermaid 라벨의 첫 줄(이모지 + 'Tier N' + 역할)을 깔끔하게 정리.

    예: "🏢 Tier 0 수요<br/>MSFT·META·..." → "수요"
    """
    # <br/> 분리: 첫 청크만 사용
    head = re.split(r"<br\s*/?>", label, maxsplit=1)[0]
    # 이모지 + 'Tier N' 제거
    head = re.sub(r"[^\w가-힣\s/·\-]+", "", head, count=1).strip()
    head = re.sub(r"^Tier\s*\d+\s*", "", head, flags=re.IGNORECASE).strip()
    return head or "—"


def _parse_inline_list(text: str) -> list[str]:
    text = text.strip()
    if not (text.startswith("[") and text.endswith("]")):
        return []
    return [p.strip().strip("\"'") for p in text[1:-1].split(",") if p.strip()]


def _clean_yaml_value(value: str) -> str:
    return value.strip().strip("\"'")


def _empty_tier_detail() -> dict[str, Any]:
    return {
        "roles": [],
        "signals": [],
        "cost_drivers": [],
        "signal_map": [],
        "materials": [],
        "players_kr": [],
        "players_kr_display": [],
        "players_us": [],
        "players_foreign": [],
    }


def _parse_yaml_object(item: str) -> dict[str, str]:
    item = item.strip()
    if item.startswith("{") and item.endswith("}"):
        item = item[1:-1]
    out: dict[str, str] = {}
    for m in re.finditer(r"([A-Za-z_]+)\s*:\s*(\"[^\"]*\"|'[^']*'|[^,}]+)", item):
        out[m.group(1)] = _clean_yaml_value(m.group(2))
    return out


def _yaml_player_display(item: str, source_key: str) -> tuple[str | None, dict[str, str] | None]:
    item = item.strip().strip("\"'")
    if not item:
        return None, None
    obj = _parse_yaml_object(item) if item.startswith("{") else {}
    if source_key == "players_kr":
        name = obj.get("name")
        ticker = obj.get("ticker")
        if name and ticker:
            display = f"{name}({ticker})"
            player = {"name": name, "ticker": ticker} if ticker.isdigit() and len(ticker) == 6 else None
            return display, player
        kr_match = RE_KR_TICKER.search(item)
        if kr_match:
            name = kr_match.group(1).strip()
            ticker = kr_match.group(2)
            return f"{name}({ticker})", {"name": name, "ticker": ticker}
        return item, None

    ticker = obj.get("ticker")
    company = obj.get("company") or obj.get("name")
    if ticker:
        return ticker, None
    if company:
        return company, None
    return item, None


def _merge_unique(target: list[Any], value: Any, key: str | None = None) -> None:
    if not value:
        return
    if key and isinstance(value, dict):
        if any(isinstance(v, dict) and v.get(key) == value.get(key) for v in target):
            return
    elif value in target:
        return
    target.append(value)


def _parse_yaml_tier_details(yaml_text: str) -> dict[str, dict[str, Any]]:
    """YAML block에서 화면에 필요한 tier 설명만 가볍게 추출.

    PyYAML 의존성을 추가하지 않고 role/signal/cost_drivers/signal_map/materials만 잡는다.
    """
    details: dict[str, dict[str, Any]] = {}
    current_level: int | None = None
    current_key: str | None = None
    current_list: str | None = None

    for raw in yaml_text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue

        top = re.match(r"^(tier_(\d+)_[A-Za-z0-9_]+):\s*$", line)
        if top:
            current_key = top.group(1)
            current_level = int(top.group(2))
            details.setdefault(current_key, {**_empty_tier_detail(), "level": current_level, "yaml_key": current_key})
            current_list = None
            continue

        if current_level is None or current_key is None or not line.startswith("  "):
            current_list = None
            continue

        bucket = details[current_key]
        stripped = line.strip()
        kv = re.match(r"^([A-Za-z_]+):\s*(.*)$", stripped)
        if kv:
            key, value = kv.group(1), kv.group(2)
            current_list = key if value == "" else None
            if key == "role" and value:
                role = _clean_yaml_value(value)
                if role not in bucket["roles"]:
                    bucket["roles"].append(role)
            elif key == "signal" and value:
                signal = _clean_yaml_value(value)
                if signal not in bucket["signals"]:
                    bucket["signals"].append(signal)
            elif key == "cost_drivers" and value:
                for item in _parse_inline_list(value):
                    if item not in bucket["cost_drivers"]:
                        bucket["cost_drivers"].append(item)
            elif key.startswith("players_") and value:
                target_key = "players_kr_display" if key == "players_kr" else "players_us" if key == "players_us" else "players_foreign"
                for item in _parse_inline_list(value):
                    display, kr_player = _yaml_player_display(item, key)
                    if display:
                        _merge_unique(bucket[target_key], display)
                    if kr_player:
                        _merge_unique(bucket["players_kr"], kr_player, "ticker")
            continue

        if stripped.startswith("- ") and current_list:
            item = stripped[2:].strip()
            item = item.strip("\"'")
            if current_list.startswith("players_"):
                target_key = "players_kr_display" if current_list == "players_kr" else "players_us" if current_list == "players_us" else "players_foreign"
                display, kr_player = _yaml_player_display(item, current_list)
                if display:
                    _merge_unique(bucket[target_key], display)
                if kr_player:
                    _merge_unique(bucket["players_kr"], kr_player, "ticker")
                continue
            if item.startswith("{") and item.endswith("}"):
                item = item[1:-1]
                parts = []
                for piece in item.split(","):
                    if ":" in piece:
                        k, v = piece.split(":", 1)
                        if k.strip() in {"name", "use", "source", "role"}:
                            parts.append(_clean_yaml_value(v))
                item = " · ".join(parts) if parts else item
            target = "signal_map" if current_list == "signal_map" else "materials" if current_list == "materials" else ""
            if target and item and item not in bucket[target]:
                bucket[target].append(item)

    return details


def _select_yaml_detail(
    node_id: str,
    tier_name: str,
    level: int,
    yaml_details: dict[str, dict[str, Any]],
    level_counts: dict[int, int],
) -> dict[str, Any]:
    candidates = [d for d in yaml_details.values() if d.get("level") == level]
    if not candidates:
        return {}
    if level_counts.get(level, 0) <= 1 or len(candidates) == 1:
        merged = _empty_tier_detail()
        for detail in candidates:
            for key, values in detail.items():
                if key in {"level", "yaml_key"}:
                    continue
                for value in values:
                    _merge_unique(merged[key], value, "ticker" if key == "players_kr" else None)
        return merged

    tokens = [t.lower() for t in re.findall(r"[가-힣A-Za-z0-9]+", tier_name) if len(t) >= 2]
    best: tuple[int, dict[str, Any]] = (0, {})
    for detail in candidates:
        haystack = " ".join(
            [
                str(detail.get("yaml_key", "")),
                *detail.get("roles", []),
                *detail.get("signals", []),
            ]
        ).lower()
        score = sum(1 for token in tokens if token in haystack)
        if score > best[0]:
            best = (score, detail)
    return best[1] if best[0] > 0 else {}


def _parse_mermaid_tiers(mermaid_text: str, yaml_details: dict[str, dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Mermaid graph에서 T<level> 노드들을 추출.

    같은 T4라도 양극재/음극재/분리막처럼 세부 공정이 갈라지면 합치지 않고 별도 카드로 노출한다.
    """
    tiers: list[dict[str, Any]] = []
    seen_node_ids: set[str] = set()
    matches = list(RE_TIER_NODE.finditer(mermaid_text))
    level_counts: dict[int, int] = {}
    for m in matches:
        level = int(m.group(2))
        level_counts[level] = level_counts.get(level, 0) + 1
    for m in matches:
        node_id = m.group(1)
        if node_id in seen_node_ids:
            continue
        seen_node_ids.add(node_id)
        level = int(m.group(2))
        raw_label = m.group(3).replace('\\"', '"')
        tier_name = _clean_tier_role(raw_label)
        kr_players = _extract_kr_players(raw_label)
        us_players = _extract_us_players(raw_label)
        detail = _select_yaml_detail(node_id, tier_name, level, yaml_details or {}, level_counts)

        seen_kr_tickers: set[str] = set()
        kr_unique = []
        for p in kr_players:
            if p["ticker"] in seen_kr_tickers:
                continue
            seen_kr_tickers.add(p["ticker"])
            kr_unique.append(p)
        for p in detail.get("players_kr", []):
            if p["ticker"] in seen_kr_tickers:
                continue
            seen_kr_tickers.add(p["ticker"])
            kr_unique.append(p)
        us_unique = list(dict.fromkeys(us_players))
        for p in detail.get("players_us", []):
            if p not in us_unique:
                us_unique.append(p)
        kr_display = [f"{p['name']}({p['ticker']})" for p in kr_unique]
        for p in detail.get("players_kr_display", []):
            ticker_match = re.search(r"\((\d{6})\)", p)
            if ticker_match and ticker_match.group(1) in seen_kr_tickers:
                continue
            if p not in kr_display:
                kr_display.append(p)
        foreign_unique = []
        for p in detail.get("players_foreign", []):
            if p not in us_unique and p not in foreign_unique:
                foreign_unique.append(p)
        is_korean_alpha = level == 4 or (len(kr_unique) >= 3 and len(kr_unique) >= len(us_unique))
        players_display = kr_display + us_unique + foreign_unique
        tiers.append({
            "node_id": node_id,
            "level": level,
            "name": tier_name or f"Tier {level}",
            "players": players_display,
            "players_kr": kr_unique,
            "players_kr_all": kr_display,
            "players_us": us_unique,
            "players_foreign": foreign_unique,
            "is_korean_alpha": is_korean_alpha,
            "roles": detail.get("roles", [])[:4],
            "signals": detail.get("signals", [])[:4],
            "cost_drivers": detail.get("cost_drivers", [])[:8],
            "signal_map": detail.get("signal_map", [])[:8],
            "materials": detail.get("materials", [])[:10],
        })
    return tiers


def _extract_hidden_alpha(body: str) -> str:
    m = RE_HIDDEN_ALPHA.search(body)
    if m:
        # 첫 줄(혹은 첫 paragraph)만 - 너무 길어지지 않도록
        text = m.group(1).strip()
        # 줄바꿈으로 자르고 공백 정리
        text = re.sub(r"\s+", " ", text.replace("\n", " "))
        return text[:500]
    return ""


def parse_value_chain() -> list[dict[str, Any]]:
    """전체 wiki를 파싱해 27개 섹터 데이터 반환."""
    global _PARSED_CACHE
    if not WIKI_VALUE_CHAIN.exists():
        return []
    mtime = WIKI_VALUE_CHAIN.stat().st_mtime
    if _PARSED_CACHE and _PARSED_CACHE[0] == mtime:
        return _PARSED_CACHE[1]

    text = WIKI_VALUE_CHAIN.read_text(encoding="utf-8")
    sectors = _split_sectors(text)

    results: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for no, name, body_start, body_end in sectors:
        body = text[body_start:body_end]
        # 헤딩에서 괄호로 둘러싼 부가설명 제거 ("EV 소재/부품 (양극재·...)" → "EV 소재/부품")
        clean_name = re.sub(r"\s*\([^)]*\)\s*$", "", name).strip()
        sector_id = SECTOR_ID_MAP.get(clean_name)
        if not sector_id:
            # 공백 무시하고 매칭
            normalized = clean_name.replace(" ", "")
            for k, v in SECTOR_ID_MAP.items():
                if k.replace(" ", "") == normalized:
                    sector_id = v
                    break
        # 표시용 이름은 clean_name 사용 (괄호 제거)
        if sector_id:
            name = clean_name
        if not sector_id or sector_id in seen_ids:
            continue
        seen_ids.add(sector_id)

        # Mermaid 파싱
        mermaid_match = RE_MERMAID_BLOCK.search(body)
        tiers: list[dict[str, Any]] = []
        mermaid_raw = ""
        if mermaid_match:
            mermaid_raw = mermaid_match.group(1).strip()
            yaml_details: dict[str, dict[str, Any]] = {}
            for yaml_match in RE_TIER_YAML_BLOCK.finditer(body):
                for key, detail in _parse_yaml_tier_details(yaml_match.group(1)).items():
                    target = yaml_details.setdefault(
                        key,
                        {**_empty_tier_detail(), "level": detail.get("level"), "yaml_key": key},
                    )
                    for key, values in detail.items():
                        if key in {"level", "yaml_key"}:
                            continue
                        for value in values:
                            _merge_unique(target[key], value, "ticker" if key == "players_kr" else None)
            tiers = _parse_mermaid_tiers(mermaid_raw, yaml_details)

        hidden_alpha = _extract_hidden_alpha(body)

        results.append({
            "sector_id": sector_id,
            "sector_no": no,
            "sector_name": name,
            "tiers": tiers,
            "hidden_alpha": hidden_alpha,
            "mermaid": mermaid_raw,
            "wiki_section_anchor": f"#{no}-{sector_id}",
        })

    # 정렬: wiki 순서 유지
    results.sort(key=lambda x: x["sector_no"])

    _PARSED_CACHE = (mtime, results)
    return results


if __name__ == "__main__":
    sectors = parse_value_chain()
    print(f"Parsed {len(sectors)} sectors:")
    for s in sectors:
        kr_count = sum(len(t["players_kr"]) for t in s["tiers"])
        us_count = sum(len(t["players_us"]) for t in s["tiers"])
        print(f"  {s['sector_no']:2}. {s['sector_name']:20} — {len(s['tiers'])} tiers, {kr_count} KR, {us_count} US")
