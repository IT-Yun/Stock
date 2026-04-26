---
title: "외부 서비스 장애 시 fallback 부재로 기능 중단"
created: 2026-04-18
updated: 2026-04-18
sources:
  - "0a37c76 fix: 멤버 추가/삭제 시 Supabase StreamReset 에러 -> JSON fallback 처리"
  - "1119a68 fix: 네이버 검색 API 교체 (searchList.naver 404)"
tags: [bug, resilience, fallback, Supabase, external-api]
---

## 증상

- 멤버 추가/삭제 시 500 에러가 발생하여 멤버 관리가 완전히 불가능해짐
- 종목 검색 자동완성이 동작하지 않음 (네이버 API 404 반환)

## 원인

1. **Supabase 단일 의존** (`0a37c76`): 멤버 데이터를 Supabase에만 저장했다. Supabase 연결이 `StreamReset` 에러로 실패하면 `raise HTTPException(500)`으로 즉시 중단되어 JSON 파일 fallback으로 내려가지 않았다.

```python
# 문제: 예외 시 즉시 500 반환, fallback 도달 불가
try:
    sb.table("members").insert({"nickname": name}).execute()
    return {"message": "추가 완료"}
except Exception as e:
    raise HTTPException(status_code=500, detail=f"DB 저장 실패: {e}")
# 아래의 JSON fallback 코드에 도달하지 않음
```

2. **API 엔드포인트 변경** (`1119a68`): 네이버 금융 검색 API(`searchList.naver`)가 404를 반환하기 시작했다. 대체 API 없이 단일 엔드포인트에만 의존하고 있었다.

## 해결

```python
# 0a37c76: 예외 시 raise 대신 fall through
try:
    sb.table("members").insert({"nickname": name}).execute()
    return {"message": "추가 완료"}
except Exception as e:
    print(f"[MEMBERS] Supabase add failed, falling back to JSON: {e}")
    # Fall through to JSON fallback (raise 제거)

# JSON fallback 코드가 정상 실행됨
data = _read_json()
data["members"].append(name)
_write_json(data)
```

```python
# 1119a68: 네이버 검색 API를 ac.stock.naver.com 자동완성 API로 교체
# + 프론트엔드에 cache-bust 타임스탬프 추가
```

## 교훈

- **외부 서비스 호출이 실패해도 핵심 기능은 동작해야 한다.** `try/except`에서 `raise`로 즉시 중단하지 말고, 로컬 fallback(JSON 파일, SQLite 등)으로 graceful degradation을 구현해야 한다.
- **외부 API는 예고 없이 사라진다.** 특히 비공식 API(네이버 금융 검색)는 언제든 엔드포인트가 변경되거나 폐기될 수 있다. 가능하면 공식 API를 사용하고, 대안 엔드포인트를 미리 파악해두어야 한다.
- **fallback 경로는 정상 경로와 동일하게 테스트해야 한다.** Supabase가 정상일 때 JSON fallback 경로는 실행되지 않으므로, 의도적으로 Supabase 연결을 끊고 테스트해봐야 한다.
