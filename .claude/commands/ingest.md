# /ingest — raw/ 파일을 wiki/에 소화하는 스킬

raw/ 폴더에 새로 추가된 파일을 읽고, 핵심 내용을 추출하여 wiki/ 페이지로 변환한다.
인자로 `quick`이 오면 사용자 질문 없이 자동 처리한다.

사용자 입력: $ARGUMENTS

---

## 절대 규칙

- **raw/ 파일은 절대 수정하지 않는다.** 읽기만 한다.
- 새 wiki 페이지를 만들기 전에, 기존 페이지에 내용을 추가할 수 있는지 먼저 확인한다.
- 모든 wiki 페이지에는 YAML frontmatter를 포함한다.
- 내부 링크는 `[[wikilink]]` 형식을 사용한다.

---

## 단계별 실행

### 1단계: raw/ 스캔

raw/ 하위 폴더를 모두 스캔한다:
- `raw/articles/` — 뉴스 기사, 블로그 글
- `raw/research/` — 리서치 보고서, 논문
- `raw/market-data/` — 시장 데이터, 통계
- `raw/references/` — 참고 자료, 문서
- `raw/ideas/` — 아이디어 메모, 브레인스토밍

각 파일의 경로와 수정일을 기록한다.

### 2단계: 인제스트 여부 확인

`wiki/log.md`를 읽어 이미 인제스트된 파일 목록을 확인한다.
아직 인제스트되지 않은 파일만 대상으로 선별한다.
인제스트할 파일이 없으면 "새로 인제스트할 파일이 없습니다"라고 알리고 종료한다.

### 3단계: 각 파일 처리

인제스트 대상 파일 각각에 대해:

1. **파일 읽기**: raw/ 파일 내용을 읽는다 (수정 금지).
2. **소스 요약 생성**: 다음을 추출한다:
   - 핵심 주장 / 결론
   - 언급된 엔티티 (종목, 기업, 인물, 기관)
   - 핵심 개념 / 키워드
   - 관련 섹터 (예: AI/반도체, 바이오, 에너지, 로보틱스, 양자컴퓨팅, 원자재)
   - 데이터 포인트 (수치, 날짜, 가격 등)

3. **사용자 질문** (quick 모드가 아닌 경우):
   사용자에게 다음을 질문한다:
   - "이 자료를 왜 캡처했나요?"
   - "현재 진행 중인 작업과 어떤 연결점이 있나요?"
   - "이 자료를 어떻게 활용할 계획인가요?"

   quick 모드(`$ARGUMENTS`에 'quick' 포함)이면 질문을 건너뛴다.

4. **wiki 페이지 생성/업데이트**:
   - 관련 기존 wiki 페이지가 있으면 해당 페이지에 섹션을 추가한다.
   - 없으면 적절한 wiki/ 하위 폴더에 새 페이지를 생성한다:
     - `wiki/sectors/` — 섹터별 분석 (예: ai-semiconductor.md, bio-pharma.md)
     - `wiki/stocks/` — 개별 종목 (예: nvidia.md, samsung-bio.md)
     - `wiki/concepts/` — 투자 개념 (예: per-valuation.md, momentum.md)
     - `wiki/strategies/` — 투자 전략 (예: sector-rotation.md)
     - `wiki/market/` — 시장 동향 (예: 2026-q1-outlook.md)

   wiki 페이지 YAML frontmatter 형식:
   ```yaml
   ---
   title: "페이지 제목"
   created: YYYY-MM-DD
   updated: YYYY-MM-DD
   tags: [태그1, 태그2]
   sources:
     - raw/경로/파일명
   related:
     - "[[관련페이지]]"
   ---
   ```

### 4단계: index.md 업데이트

`wiki/index.md`에 새로 생성하거나 업데이트한 페이지 링크를 추가한다.
카테고리별로 정리하여 목록을 유지한다.

### 5단계: log.md 업데이트

`wiki/log.md`에 인제스트 기록을 추가한다:
```
## YYYY-MM-DD
- [ingest] raw/경로/파일명 → wiki/경로/페이지명.md (신규생성|업데이트)
  - 요약: 한 줄 요약
```

### 6단계: 결과 보고

처리 결과를 요약하여 보고한다:
- 인제스트한 파일 수
- 생성한 wiki 페이지 목록
- 업데이트한 wiki 페이지 목록
- 새로 발견된 [[wikilink]] 연결
