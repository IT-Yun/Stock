# /lint — wiki/ 점검 및 정리 스킬 (도서관 사서)

wiki/ 전체를 스캔하여 구조적 문제를 식별하고, 사용자 확인 후 수정한다.

---

## 절대 규칙

- **raw/ 파일은 절대 수정하지 않는다.**
- 수정 전 반드시 사용자에게 확인을 받는다.
- 모든 수정 사항은 `wiki/log.md`에 기록한다.

---

## 단계별 실행

### 1단계: wiki/ 전체 스캔

wiki/ 하위의 모든 `.md` 파일을 스캔한다:
- `wiki/sectors/` — 섹터별 분석 페이지
- `wiki/stocks/` — 개별 종목 페이지
- `wiki/concepts/` — 투자 개념 페이지
- `wiki/strategies/` — 투자 전략 페이지
- `wiki/market/` — 시장 동향 페이지
- `wiki/index.md` — 전체 인덱스
- `wiki/log.md` — 변경 기록

각 파일의 내용과 frontmatter를 읽는다.

### 2단계: 문제 식별

다음 항목들을 점검한다:

#### 2-1. 깨진 [[wikilink]]
- 모든 페이지에서 `[[wikilink]]`를 추출한다.
- 링크 대상 페이지가 실제로 존재하는지 확인한다.
- 존재하지 않는 링크를 "깨진 링크"로 분류한다.

#### 2-2. YAML frontmatter 검증
- 모든 페이지에 YAML frontmatter가 있는지 확인한다.
- 필수 필드 확인: `title`, `created`, `updated`, `tags`, `sources`
- 날짜 형식(YYYY-MM-DD)이 올바른지 확인한다.
- `updated` 날짜가 `created` 이전인 경우를 식별한다.

#### 2-3. index.md 정합성
- `wiki/index.md`에 등록된 페이지가 실제로 존재하는지 확인한다.
- 실제 존재하지만 `index.md`에 없는 페이지를 식별한다.

#### 2-4. 중복 페이지
- 제목이나 내용이 유사한 페이지를 식별한다.
- 같은 종목이나 개념을 다루는 중복 페이지를 찾는다.
  - 예: `nvidia.md`와 `nvda.md`가 둘 다 존재하는 경우

#### 2-5. 오래된 정보
- `updated` 날짜가 90일 이상 지난 페이지를 식별한다.
- 시장 동향(`wiki/market/`) 페이지는 30일 기준으로 점검한다.

#### 2-6. 고아 소스
- `sources` 필드에 명시된 raw/ 파일이 실제로 존재하는지 확인한다.

### 3단계: 문제 리포트 생성

발견된 문제를 카테고리별로 정리하여 보고한다:

```
## Wiki 점검 결과

### 깨진 링크 (N건)
- [[페이지A]] → 대상 없음 (wiki/stocks/페이지A.md에서 참조)

### Frontmatter 오류 (N건)
- wiki/stocks/example.md — title 필드 누락

### Index 불일치 (N건)
- wiki/concepts/momentum.md — index.md에 미등록
- [[삭제된페이지]] — index.md에 있지만 파일 없음

### 중복 의심 (N건)
- nvidia.md ↔ nvda.md — 동일 종목 중복 가능

### 오래된 페이지 (N건)
- wiki/market/2025-q4.md — 마지막 업데이트: 2025-12-15 (120일 전)

### 고아 소스 (N건)
- wiki/stocks/example.md → raw/articles/deleted.md (소스 파일 없음)
```

### 4단계: 사용자 확인

리포트를 보여준 후, 각 카테고리별로 수정 여부를 사용자에게 확인한다:
- "깨진 링크를 제거하거나 대상 페이지를 생성할까요?"
- "누락된 frontmatter를 추가할까요?"
- "index.md를 업데이트할까요?"
- "중복 페이지를 병합할까요?"
- "오래된 페이지에 리뷰 태그를 추가할까요?"

### 5단계: 수정 실행

사용자가 승인한 항목에 대해서만 수정을 실행한다:
- 깨진 링크: 링크 제거 또는 stub 페이지 생성
- Frontmatter: 누락 필드 추가, 오류 수정
- Index: 미등록 페이지 추가, 삭제된 페이지 항목 제거
- 중복: 두 페이지를 하나로 병합 (내용 통합)
- 오래된 페이지: frontmatter에 `needs_review: true` 태그 추가

### 6단계: log.md 업데이트

수정한 내용을 `wiki/log.md`에 기록한다:
```
## YYYY-MM-DD
- [lint] 깨진 링크 N건 수정
- [lint] frontmatter 오류 N건 수정
- [lint] index.md 동기화: 추가 N건, 제거 N건
- [lint] 중복 페이지 병합: 페이지A + 페이지B → 페이지A
- [lint] 오래된 페이지 N건에 needs_review 태그 추가
```

### 7단계: 결과 보고

최종 결과를 요약한다:
- 발견된 총 문제 수
- 수정 완료 건수
- 사용자가 건너뛴 건수
- 남은 조치 사항
