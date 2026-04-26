---
title: "SPA 배포 후 빈 화면 (stale asset + 캐시 문제)"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "bff5e73 fix: add no-cache on index.html + 404 for stale assets"
tags: [bug, deploy, cache, SPA, assets]
---

## 증상

- 새 버전 배포 후 일부 사용자에게 빈 화면이 표시됨
- 브라우저 콘솔에 JavaScript parse 에러 발생
- 강제 새로고침(Ctrl+Shift+R)하면 정상 작동

## 원인

Vite 빌드는 JS/CSS 파일명에 content hash를 포함한다 (예: `main-abc123.js`). 배포 시 새 빌드의 파일명이 바뀌지만, 브라우저가 `index.html`을 캐시하고 있으면 이전 빌드의 해시가 포함된 파일명을 요청한다.

두 가지 문제가 동시에 발생했다:

1. **index.html 캐시**: `Cache-Control` 헤더 없이 서빙되어 브라우저가 오래된 `index.html`을 사용. 이 HTML은 이미 삭제된 구 버전 JS 파일을 참조.

2. **SPA fallback이 stale asset 요청을 가로챔**: 존재하지 않는 `/assets/main-abc123.js` 요청이 SPA fallback 라우트에 잡혀 `index.html`(HTML)을 JS 파일로 반환. 브라우저가 HTML을 JavaScript로 파싱 시도하여 parse 에러 발생.

## 해결

```python
# index.html은 항상 최신 버전을 받도록 no-cache 설정
return Response(
    content=content,
    media_type="text/html",
    headers={
        "Cache-Control": "no-cache, no-store, must-revalidate",
        "Pragma": "no-cache"
    },
)

# /assets/* 경로의 없는 파일은 SPA fallback 대신 404 반환
if full_path.startswith("assets/"):
    return JSONResponse(status_code=404, content={"error": "asset not found"})
```

## 교훈

- **SPA의 `index.html`은 절대 캐시하면 안 된다.** `no-cache, no-store, must-revalidate`를 반드시 설정해야 한다. 해시된 JS/CSS 파일은 장기 캐시해도 되지만, 진입점인 HTML은 항상 최신이어야 한다.
- **SPA fallback 라우트는 `/assets/*` 경로를 제외해야 한다.** 존재하지 않는 asset 요청에 HTML을 반환하면 브라우저가 MIME type 불일치로 파싱 에러를 일으킨다.
- **배포 후 빈 화면 이슈는 개발 환경에서 재현이 어렵다.** HMR이 있는 개발 서버에서는 발생하지 않으므로, 스테이징 환경에서 캐시된 상태로 배포를 시뮬레이션해야 한다.
