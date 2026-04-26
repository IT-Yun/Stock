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
    r"T(\d+)(?:_\w+)?\s*\[\s*\"((?:[^\"\\]|\\.)*)\"\s*\]"
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


def _parse_mermaid_tiers(mermaid_text: str) -> list[dict[str, Any]]:
    """Mermaid graph에서 T<level> 노드들을 추출."""
    tiers: dict[int, dict[str, Any]] = {}
    for m in RE_TIER_NODE.finditer(mermaid_text):
        level = int(m.group(1))
        raw_label = m.group(2).replace('\\"', '"')
        # 같은 level이 여러 노드에 분리돼 있을 수 있음 (T4_C, T4_A 등) — 합치기
        existing = tiers.setdefault(level, {"level": level, "name_parts": [], "players_kr": [], "players_us": []})
        existing["name_parts"].append(_clean_tier_role(raw_label))
        existing["players_kr"].extend(_extract_kr_players(raw_label))
        existing["players_us"].extend(_extract_us_players(raw_label))
    # name 합치고, 중복 제거
    out: list[dict[str, Any]] = []
    for level in sorted(tiers.keys()):
        t = tiers[level]
        seen_kr_tickers: set[str] = set()
        kr_unique = []
        for p in t["players_kr"]:
            if p["ticker"] in seen_kr_tickers:
                continue
            seen_kr_tickers.add(p["ticker"])
            kr_unique.append(p)
        us_unique = list(dict.fromkeys(t["players_us"]))
        # name: 분리된 부분들 중 unique
        unique_parts = list(dict.fromkeys([p for p in t["name_parts"] if p and p != "—"]))
        name = " · ".join(unique_parts) if unique_parts else f"Tier {level}"
        # 한국 알파 강조: Tier 4 (소재/부품) 또는 KR players가 US players보다 많을 때
        is_korean_alpha = level == 4 or (len(kr_unique) >= 3 and len(kr_unique) >= len(us_unique))
        # 표시용 players 리스트 (이름 + ticker 또는 US 심볼)
        players_display = [
            f"{p['name']}({p['ticker']})" for p in kr_unique
        ] + us_unique
        out.append({
            "level": level,
            "name": name,
            "players": players_display,
            "players_kr": kr_unique,
            "players_us": us_unique,
            "is_korean_alpha": is_korean_alpha,
        })
    return out


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
            tiers = _parse_mermaid_tiers(mermaid_raw)

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
