# raw/ — 불변 원본 저장소

**핵심 규칙: 한 번 저장된 파일은 절대 수정 금지. 원본 그대로 보존.**

## 폴더 구조

- `articles/` — 웹 아티클 (뉴스, 블로그 등)
- `research/` — 리서치 및 분석 리포트
- `market-data/` — 시장 데이터 스냅샷
- `references/` — 참고 자료 (논문, 공시 등)
- `ideas/` — 아이디어 메모 원본

## 파일 명명 규칙

`YYYY-MM-DD_제목.md` (예: `2026-04-18_반도체-섹터-전망.md`)

## YAML Frontmatter 필수

모든 파일은 아래 frontmatter를 포함해야 한다:

```yaml
---
title: "문서 제목"
source: "출처 URL 또는 이름"
date: 2026-04-18
type: article | research | market-data | reference | idea
tags: [태그1, 태그2]
---
```

## 금지 사항

- 기존 파일 내용 수정 금지 (오타 수정도 불가 — 정정은 wiki/에서)
- 파일 삭제 금지
- frontmatter 없는 파일 저장 금지
