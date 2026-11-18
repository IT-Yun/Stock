---
title: "프론트엔드 dedupedGet + localStorage 캐시"
created: 2026-04-18
updated: 2026-04-18
sources:
  - frontend/src/api/client.ts
tags: [architecture, frontend, cache, deduplication, axios]
---

## 결정

프론트엔드에서 모든 GET API 호출을 **`dedupedGet()` 함수**로 래핑하여 (1) 동일 요청 중복 제거, (2) localStorage 캐시, (3) 실패 시 stale 데이터 fallback을 구현한다.

### Inflight 요청 중복 제거 (Singleflight)

```typescript
const inflightRequests = new Map<string, Promise<any>>();

function dedupedGet<T>(url: string, config?): Promise<{ data: T }> {
  const key = buildRequestKey(url, config?.params);
  const existing = inflightRequests.get(key);
  if (existing) return existing;  // 동일 요청 진행 중이면 기존 Promise 재사용

  const request = api.get<T>(url, config)
    .then((response) => { writeResponseCache(key, response.data); return response; })
    .catch((error) => {
      const fallback = readResponseCache<T>(key);
      if (fallback !== null) return { data: fallback };
      throw error;
    })
    .finally(() => { inflightRequests.delete(key); });

  inflightRequests.set(key, request);
  return request;
}
```

### localStorage 캐시 (6시간 TTL)

```typescript
const responseCacheTtlMs = 1000 * 60 * 60 * 6;
// 성공 시 localStorage에 저장, 실패 시 stale 데이터 반환
```

### 자동 재시도

Axios interceptor로 네트워크 에러, 5xx, 403에 대해 최대 2회 재시도 (1.5초 * 시도횟수 대기).

### Static Fallback

`/sectors/top-ranked` API 실패 시 `sectors.ts`의 정적 데이터에서 fallback 랭킹 생성.

## 대안

| 방법 | 검토 결과 |
|------|-----------|
| React Query / SWR | 외부 라이브러리 의존성 추가, 현재 규모에 과도 |
| Service Worker 캐시 | 구현 복잡도 높음, localStorage로 충분 |
| 중복 제거 없이 호출 | React 렌더 사이클에서 같은 API 2-3회 중복 호출 발생 |
| sessionStorage | 탭 닫으면 사라짐, 페이지 재방문 시 보호 불가 |

## 이유

- React의 useEffect/Strict Mode에서 같은 컴포넌트가 2번 마운트되어 동일 API를 중복 호출
- `inflightRequests` Map으로 진행 중인 Promise를 공유하면 네트워크 요청 1회로 병합
- localStorage 캐시로 네트워크 실패 시에도 사용자에게 이전 데이터 표시 (offline-first)
- `buildRequestKey()`로 URL + params를 직렬화하여 정확한 중복 탐지
- quota/storage 에러는 catch에서 무시하여 런타임 안정성 확보

## 트레이드오프

- localStorage는 도메인당 5-10MB 제한 — 데이터 많아지면 quota 초과 가능
- 6시간 stale 데이터가 표시될 수 있음 (fresh 표시와 구분 없음)
- `inflightRequests`는 메모리 Map이라 페이지 새로고침 시 초기화
- static fallback은 가격 0, 점수 50으로 표시되어 사용자 혼란 가능

## 관련 코드

- **`frontend/src/api/client.ts`** 17-19행: inflight Map 및 캐시 TTL 설정
- **`frontend/src/api/client.ts`** 70-95행: `dedupedGet()` 핵심 구현
- **`frontend/src/api/client.ts`** 107-120행: Axios 자동 재시도 interceptor
- **`frontend/src/api/client.ts`** 51-68행: `buildStaticTopRankedFallback()` 정적 fallback
