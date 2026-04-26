---
title: "백그라운드 워커 패턴 — Warmup, Keep-alive, Daily Refresh"
created: 2026-04-18
updated: 2026-04-18
sources:
  - backend/main.py
tags: [architecture, background-worker, cache, render, lifespan]
---

## 결정

FastAPI의 `lifespan` 이벤트에서 4개의 데몬 스레드를 시작하여 백그라운드 작업을 처리한다.

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_warmup_cache, daemon=True).start()
    threading.Thread(target=_keep_alive, daemon=True).start()
    threading.Thread(target=_daily_refresh_worker, daemon=True).start()
    threading.Thread(target=_warmup_checklist_scores, daemon=True).start()
    yield
```

### 1. Cache Warmup (`_warmup_cache`)

서버 시작 직후 섹터 데이터 + 원자재 가격을 미리 로드. 실패해도 non-fatal로 처리.

### 2. Checklist Warmup (`_warmup_checklist_scores`)

30초 대기 후 모든 top pick ticker의 체크리스트 점수를 3초 간격으로 순차 계산. 완료 후 top-ranked 랭킹을 재생성.

### 3. Keep-alive (`_keep_alive`)

10분마다 `http://127.0.0.1:{port}/health`에 self-ping하여 Render 무료 티어의 15분 spin-down 방지.

```python
def _keep_alive():
    while True:
        time.sleep(600)  # 10분
        requests.get(f"http://127.0.0.1:{port}/health", timeout=5)
```

### 4. Daily Refresh (`_daily_refresh_worker`)

매일 KST 06:00에 실행:
1. stale 캐시 키 삭제 (`top-ranked`, `checklist:`, `move-reasons:`)
2. 원자재 가격 갱신
3. 모든 ticker 주가 데이터 순차 갱신 (0.5초 간격)
4. top-ranked 점수 재계산

수동 트리거도 가능: `POST /api/refresh-now`

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| Celery / RQ | Redis 인프라 필요, Render 무료 티어에 부적합 |
| asyncio.create_task | yfinance가 동기 라이브러리라 blocking 발생 |
| APScheduler | 외부 의존성 추가, 단순 sleep 루프로 충분 |
| Cron job (외부) | Render 무료 티어에서 cron 미지원 |
| Render Cron Job | 별도 서비스 비용 발생 |

## 이유

- `daemon=True` 스레드는 메인 프로세스 종료 시 자동 정리
- yfinance가 동기 API라 `threading.Thread`가 가장 자연스러운 선택
- lifespan 컨텍스트 매니저로 시작 시점을 정확히 제어
- keep-alive는 Render 무료 티어에서 필수 (15분 비활성 시 spin-down)
- daily refresh는 한국 시장 개장 전(KST 06:00)에 실행하여 최신 데이터 보장

## 트레이드오프

- daemon 스레드는 graceful shutdown이 어려움 (진행 중 작업이 중단될 수 있음)
- `_last_daily_refresh` dict는 thread-safe하지 않음 (GIL에 의존)
- keep-alive는 자기 자신에게 HTTP 요청을 보내므로 약간의 리소스 소비
- Render가 강제 재시작하면 daily refresh 스케줄이 리셋됨
- workers=2(Render)인 경우 각 워커마다 독립적으로 백그라운드 스레드가 생성됨

## 관련 코드

- **`backend/main.py`** 64-78행: `_warmup_cache()` — 서버 시작 워밍
- **`backend/main.py`** 81-114행: `_warmup_checklist_scores()` — 체크리스트 순차 워밍
- **`backend/main.py`** 117-128행: `_keep_alive()` — 10분 self-ping
- **`backend/main.py`** 131-212행: `_daily_refresh_worker()` + `_run_daily_refresh()` — 일일 갱신
- **`backend/main.py`** 215-222행: `lifespan()` — 4개 스레드 시작
- **`backend/main.py`** 255-267행: `/api/refresh-status`, `/api/refresh-now` 엔드포인트
