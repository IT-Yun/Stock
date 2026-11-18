---
title: "CSS @keyframes 이름 충돌로 엉뚱한 애니메이션 적용"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "5253997 fix: 마인드맵/슬라이더 텍스트가 좌->우 이동하는 버그 수정"
  - "1119a68 fix: i18n 번역키 노출 수정 + 네이버 검색 API 교체 + 뉴스 필터링 강화"
  - "7c09bbf fix: 체크리스트에서 뉴스 항목 완전 제거 (캐시 포함)"
tags: [bug, CSS, animation, i18n, data-contamination]
---

## 증상

- 마인드맵 텍스트 그래디언트가 반짝이는 대신 좌에서 우로 이동하는 이상한 애니메이션이 적용됨
- i18n 번역키가 사용자에게 그대로 노출됨 (예: `"verdict.bullish"` 텍스트가 화면에 표시)
- 체크리스트에 뉴스 항목이 섞여 들어가 기본적 분석 점수가 왜곡됨

## 원인

### CSS @keyframes 충돌 (`5253997`)

`globals.css`에 `@keyframes shimmer`가 2번 정의되어 있었다:
- 79행: `background-position` 기반 (텍스트 그래디언트 반짝임용, 정상)
- 197행: `translateX` 기반 (스켈레톤 로딩 애니메이션용)

CSS 사양에 따라 같은 이름의 `@keyframes`는 마지막 정의가 우선된다. 결과적으로 `.text-gradient`에도 `translateX` 기반 shimmer가 적용되어 텍스트가 좌에서 우로 이동했다.

### 데이터 경계 오염 (`7c09bbf`)

뉴스 분석 결과가 체크리스트 캐시에 혼입되었다. "뉴스:", "이슈 모니터링:" 접두사가 붙은 항목이 기본적 분석 체크리스트에 포함되어, 안전/주의/위험 배지 계산과 종합 점수가 왜곡됐다. 백엔드 캐시와 디스크 캐시 양쪽에 오염된 데이터가 남아 있어, 단순 코드 수정만으로는 해결되지 않고 캐시 필터링이 필요했다.

### i18n 번역키 누락 (`1119a68`)

`verdict`, `action` 등 새로 추가된 UI 텍스트에 대한 번역키가 `translations.ts`에 등록되지 않았다. `t("verdict.bullish")`이 fallback 없이 키 문자열 그대로 반환됐다.

## 해결

```css
/* 5253997: 스켈레톤용 shimmer를 고유 이름으로 변경 */
@keyframes skeletonShimmer {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(100%); }
}
/* + 중복 slideIn 정의 제거 */
```

```python
# 7c09bbf: 체크리스트 반환 시 뉴스 항목 필터링
def _strip_news_from_checklist(data):
    data["checklist"] = [
        item for item in data.get("checklist", [])
        if not item.get("is_news_item")
        and not item.get("label", "").startswith(("뉴스:", "이슈 모니터링:"))
    ]
    return data
```

```typescript
// 1119a68: 누락된 번역키 추가
verdict: { bullish: "매수 의견", bearish: "매도 의견", ... }
```

## 교훈

- **CSS @keyframes 이름은 글로벌 스코프다.** 같은 이름이 두 번 정의되면 마지막이 모든 곳에 적용된다. 용도별로 고유한 이름을 사용하거나, CSS Modules/scoped styles를 활용해야 한다.
- **서로 다른 도메인의 데이터(뉴스 vs 기본 분석)는 저장소 단계에서 분리해야 한다.** 같은 캐시 키에 혼합 저장하면 데이터 오염이 발생하고, 이미 오염된 캐시를 소급 정리하는 비용이 크다.
- **i18n 키 누락은 타입 시스템으로 방지할 수 있다.** 번역 함수의 인자를 `keyof Translations`로 타입 지정하면 컴파일 타임에 누락을 감지할 수 있다.
