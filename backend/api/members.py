"""Member management API — Supabase DB for persistent storage, JSON fallback."""

import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/members", tags=["members"])

MEMBERS_FILE = Path(__file__).resolve().parent.parent / "data" / "members.json"

# ── Supabase client (lazy init) ──
_supabase = None


def _get_supabase():
    global _supabase
    if _supabase is not None:
        return _supabase
    try:
        from config import settings
        if settings.SUPABASE_URL and settings.SUPABASE_KEY:
            from supabase import create_client
            _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            print("[MEMBERS] Supabase connected")
            return _supabase
    except Exception as e:
        print(f"[MEMBERS] Supabase init failed, using JSON fallback: {e}")
    return None


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())


# ── JSON fallback ──

def _read_json() -> dict:
    try:
        return json.loads(MEMBERS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {"admins": [], "members": []}


def _write_json(data: dict):
    MEMBERS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ── Unified data access ──

def _read_members() -> dict:
    """Read members from Supabase if available, otherwise JSON file."""
    sb = _get_supabase()
    if sb:
        try:
            rows = sb.table("members").select("nickname, role").execute().data
            admins = [r["nickname"] for r in rows if r["role"] == "admin"]
            members = [r["nickname"] for r in rows if r["role"] == "member"]
            return {"admins": admins, "members": members}
        except Exception as e:
            print(f"[MEMBERS] Supabase read failed: {e}")
    return _read_json()


def get_all_allowed() -> set[str]:
    """Return normalized set of all allowed nicknames (admins + members)."""
    data = _read_members()
    return {_normalize(n) for n in data.get("admins", []) + data.get("members", [])}


def get_admin_set() -> set[str]:
    data = _read_members()
    return {_normalize(n) for n in data.get("admins", [])}


def _require_admin(nickname: str):
    if not nickname or _normalize(nickname) not in get_admin_set():
        raise HTTPException(status_code=403, detail="관리자 권한이 필요합니다")


# ── Routes ──

class VerifyRequest(BaseModel):
    nickname: str


@router.post("/verify")
async def verify_member(body: VerifyRequest):
    """Check if a nickname is allowed to login. Returns role without exposing full list."""
    name = body.nickname.strip()
    if not name:
        return {"allowed": False}

    norm = _normalize(name)
    admin_set = get_admin_set()
    if norm in admin_set:
        return {"allowed": True, "role": "admin"}

    all_allowed = get_all_allowed()
    if norm in all_allowed:
        return {"allowed": True, "role": "member"}

    return {"allowed": False}


@router.get("/list")
async def list_members(x_auth_nickname: str = Header("")):
    """Admin only: return full member list for management UI."""
    decoded = unquote(x_auth_nickname)
    _require_admin(decoded)

    data = _read_members()
    return {
        "admins": data.get("admins", []),
        "members": data.get("members", []),
    }


class MemberAction(BaseModel):
    nickname: str


@router.post("/add")
async def add_member(
    body: MemberAction,
    x_auth_nickname: str = Header(""),
):
    decoded = unquote(x_auth_nickname)
    _require_admin(decoded)

    name = body.nickname.strip()
    if not name:
        raise HTTPException(status_code=400, detail="닉네임을 입력해주세요")

    all_allowed = get_all_allowed()
    if _normalize(name) in all_allowed:
        raise HTTPException(status_code=409, detail=f"'{name}'은(는) 이미 등록된 멤버입니다")

    sb = _get_supabase()
    if sb:
        try:
            sb.table("members").insert({"nickname": name, "role": "member"}).execute()
            return {"message": f"'{name}' 멤버 추가 완료"}
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB 저장 실패: {e}")

    data = _read_json()
    data["members"].append(name)
    _write_json(data)
    return {"message": f"'{name}' 멤버 추가 완료", "total": len(data["members"])}


@router.delete("/remove")
async def remove_member(
    body: MemberAction,
    x_auth_nickname: str = Header(""),
):
    decoded = unquote(x_auth_nickname)
    _require_admin(decoded)

    name = body.nickname.strip()
    norm = _normalize(name)

    sb = _get_supabase()
    if sb:
        try:
            result = sb.table("members").delete().eq("nickname", name).execute()
            if not result.data:
                rows = sb.table("members").select("id, nickname").execute().data
                match = [r for r in rows if _normalize(r["nickname"]) == norm]
                if match:
                    sb.table("members").delete().eq("id", match[0]["id"]).execute()
                else:
                    raise HTTPException(status_code=404, detail=f"'{name}'을(를) 찾을 수 없습니다")
            return {"message": f"'{name}' 멤버 삭제 완료"}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"DB 삭제 실패: {e}")

    data = _read_json()
    original_len = len(data["members"])
    data["members"] = [m for m in data["members"] if _normalize(m) != norm]
    if len(data["members"]) == original_len:
        raise HTTPException(status_code=404, detail=f"'{name}'을(를) 찾을 수 없습니다")
    _write_json(data)
    return {"message": f"'{name}' 멤버 삭제 완료", "total": len(data["members"])}


# ── Visit tracking ──

VISITS_FILE = Path(__file__).resolve().parent.parent / "data" / "visits.json"


def _read_visits_json() -> dict:
    try:
        return json.loads(VISITS_FILE.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _write_visits_json(data: dict):
    VISITS_FILE.parent.mkdir(parents=True, exist_ok=True)
    VISITS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@router.post("/visit")
async def record_visit(body: VerifyRequest):
    """Record a user visit. Called on each login/page load."""
    name = body.nickname.strip()
    if not name:
        return {"ok": True}

    now = datetime.now(timezone.utc).isoformat()

    sb = _get_supabase()
    if sb:
        try:
            sb.table("visits").insert({"nickname": name, "visited_at": now}).execute()
            return {"ok": True}
        except Exception as e:
            print(f"[VISITS] Supabase insert failed: {e}")
            # Fall through to JSON

    # JSON fallback
    visits = _read_visits_json()
    if name not in visits:
        visits[name] = {"count": 0, "last_visit": None, "history": []}
    visits[name]["count"] += 1
    visits[name]["last_visit"] = now
    # Keep last 100 visits per user
    visits[name].setdefault("history", []).append(now)
    visits[name]["history"] = visits[name]["history"][-100:]
    _write_visits_json(visits)
    return {"ok": True}


@router.get("/stats")
async def get_visit_stats(x_auth_nickname: str = Header("")):
    """Admin only: get visit counts per member."""
    decoded = unquote(x_auth_nickname)
    _require_admin(decoded)

    sb = _get_supabase()
    if sb:
        try:
            # Get visit counts grouped by nickname
            rows = sb.table("visits").select("nickname, visited_at").execute().data
            stats: dict[str, dict] = {}
            for row in rows:
                nick = row["nickname"]
                if nick not in stats:
                    stats[nick] = {"count": 0, "last_visit": None}
                stats[nick]["count"] += 1
                visit_time = row.get("visited_at")
                if visit_time and (stats[nick]["last_visit"] is None or visit_time > stats[nick]["last_visit"]):
                    stats[nick]["last_visit"] = visit_time

            result = []
            for nick, info in sorted(stats.items(), key=lambda x: x[1]["count"], reverse=True):
                result.append({
                    "nickname": nick,
                    "visit_count": info["count"],
                    "last_visit": info["last_visit"],
                })
            return {"stats": result, "total_visits": sum(s["count"] for s in stats.values())}
        except Exception as e:
            print(f"[VISITS] Supabase stats failed: {e}")

    # JSON fallback
    visits = _read_visits_json()
    result = []
    for nick, info in sorted(visits.items(), key=lambda x: x[1].get("count", 0), reverse=True):
        result.append({
            "nickname": nick,
            "visit_count": info.get("count", 0),
            "last_visit": info.get("last_visit"),
        })
    return {"stats": result, "total_visits": sum(v.get("count", 0) for v in visits.values())}
