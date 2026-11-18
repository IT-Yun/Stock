# wiki/ — AI 컴파일 지식 베이스

wiki/는 raw/ 원본을 가공하여 구조화된 지식으로 만드는 공간이다.

## YAML Frontmatter 필수

```yaml
---
title: "페이지 제목"
created: 2026-04-18
updated: 2026-04-18
sources:
  - raw/articles/2026-04-18_예시.md
tags: [태그1, 태그2]
---
```

## 카테고리 (하위 폴더)

- `sectors/` — 섹터별 분석 (AI/반도체, 바이오, 에너지 등)
- `stocks/` — 종목별 분석
- `concepts/` — 투자 개념 (PER, 기술적 분석 등)
- `strategies/` — 투자 전략
- `market/` — 시장 동향 및 매크로

## 규칙

1. 내부 참조는 `[[wikilink]]` 형식 사용
2. 새 페이지보다 기존 페이지 업데이트 우선
3. 변경 시 반드시 `index.md`와 `log.md` 업데이트
4. 소스 요약은 사실만 기술, 해석은 개념 페이지에서
5. 모순 발견 시 양쪽 소스 모두 인용
