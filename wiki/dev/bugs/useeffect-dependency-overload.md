---
title: "useEffect 의존성 과다로 불필요한 전체 리로드"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "d89b50e fix: 차트 기간 변경 시 전체 페이지 새로고침 방지"
  - "7be30a2 fix: 개별 종목 검색 시 섹터를 찾을 수 없습니다 에러 수정"
  - "ca5bffd fix: 모바일 초기 렌더링 시 데스크톱 레이아웃 깜빡임 수정"
tags: [bug, React, useEffect, UX, rendering]
---

## 증상

- 차트 기간(1개월/3개월/1년)을 변경하면 분석, 뉴스, 체크리스트 등 모든 데이터가 리셋되고 전체 로딩이 다시 시작됨
- 개별 종목 검색 시 "섹터를 찾을 수 없습니다" 에러 페이지가 표시됨
- 모바일에서 첫 로딩 시 데스크톱 레이아웃이 잠깐 보였다가 모바일로 전환됨 (깜빡임)

## 원인

1. **useEffect 의존성 과다** (`d89b50e`): `period` 상태가 메인 데이터 로딩 `useEffect`의 dependency array에 포함되어 있었다. 기간 변경 시 차트만 다시 가져오면 되는데, 분석/뉴스/체크리스트까지 전부 리셋되고 재요청됐다.

```typescript
// 문제: period가 바뀌면 모든 state가 리셋됨
useEffect(() => {
    setAnalysis(null);
    setChartData([]);
    setChecklistLive(null);
    // ... 전체 데이터 로딩
}, [pick.ticker, period, retryCount]);  // period가 여기 있음
```

2. **렌더링 순서 문제** (`7be30a2`): `sector` 존재 여부 체크가 `isDynamic` 체크보다 먼저 실행되어, 검색으로 진입한 종목(특정 섹터에 속하지 않는)이 "섹터를 찾을 수 없습니다" 에러로 빠졌다.

3. **초기값 문제** (`ca5bffd`): `dims` 상태의 초기값이 하드코딩된 `{ w: 1200, h: 800 }`이었다. 모바일 기기에서도 첫 렌더링은 `w=1200`으로 데스크톱 분기를 탔고, `useEffect`에서 `window.innerWidth`를 읽어 갱신되기 전까지 데스크톱 레이아웃이 표시됐다.

## 해결

```typescript
// d89b50e: useEffect 분리 - 메인 effect에서 period 제거
useEffect(() => {
    // 분석, 뉴스, 체크리스트 로딩
}, [pick.ticker, retryCount]);  // period 제거

// 별도 effect: period 변경 시 차트만 재요청
useEffect(() => {
    if (period === initialPeriodRef.current) return; // 초기 마운트 스킵
    fetchChartData(pick.ticker, period).then(setChartData);
}, [pick.ticker, period]);

// 7be30a2: isDynamic 체크를 sector 존재 체크보다 먼저 배치
if (isDynamic && selectedPick) {
    return <분석 뷰 />;  // sector 없어도 정상 동작
}
// ... 이후에 sector 존재 체크

// ca5bffd: 초기값을 실제 화면 크기로 설정
const [dims, setDims] = useState({
    w: typeof window !== "undefined" ? window.innerWidth : 1200,
    h: typeof window !== "undefined" ? window.innerHeight : 800
});
```

## 교훈

- **useEffect의 dependency array는 최소한으로 유지해야 한다.** 하나의 거대한 effect보다, 관심사별로 분리된 작은 effect들이 불필요한 재실행을 방지한다.
- **조건부 렌더링의 순서가 중요하다.** 더 구체적인 조건(isDynamic)을 더 일반적인 조건(sector 존재) 앞에 배치해야 한다.
- **React 상태의 초기값은 가능하면 실제 런타임 값을 사용해야 한다.** SSR이 아닌 환경에서는 `window` 객체에 안전하게 접근할 수 있으므로, 하드코딩된 기본값 대신 실제 값을 쓰면 첫 렌더링 깜빡임을 예방한다.
