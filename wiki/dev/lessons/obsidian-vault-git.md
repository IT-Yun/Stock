---
title: "Obsidian vault의 git 관리 방침"
created: 2026-04-18
updated: 2026-04-18
sources: []
tags: [lessons, obsidian, git, gitignore]
---

# Obsidian vault의 git 관리 방침

## 결정

`.obsidian/` 폴더 전체를 `.gitignore`에 추가하여 git 추적에서 제외한다.

## 맥락

이 프로젝트는 `wiki/`, `raw/` 등의 `.md` 파일을 Obsidian vault로 열어 사용한다. Obsidian은 vault 루트에 `.obsidian/` 폴더를 생성해 설정·UI 상태를 저장한다.

## 대안

| 옵션 | 내용 | 장점 | 단점 |
|------|------|------|------|
| A. `workspace.json`만 제외 | 플러그인/그래프 설정은 동기화 | 여러 기기에서 설정 일치 | 혼자 한 기기면 불필요한 복잡성 |
| **B. `.obsidian/` 통째로 제외** | **모든 Obsidian 설정 무시** | **단순·깔끔, 커밋 노이즈 제로** | 다른 기기 clone 시 플러그인 재설정 필요 |

## 이유

- 집 1대 환경에서만 사용 → 기기 간 동기화 불필요
- `workspace.json`은 창 위치·열린 탭 등 **개인 UI 상태**로 커밋 노이즈 유발
- `.obsidian/`은 Obsidian이 필요 시 자동 재생성하므로 삭제해도 안전
- vault 본체는 `.md` 파일들이지 `.obsidian/`이 아님

## 트레이드오프

- 새 기기에서 프로젝트를 clone하면 Obsidian 플러그인·테마를 다시 켜야 함
- 현재는 해당 시나리오가 없어 수용 가능

## 교훈

- IDE/에디터의 개인 UI 상태 파일(`.vscode/`, `.idea/`, `.obsidian/workspace.json` 등)은 기본적으로 gitignore 대상
- vault 본체와 설정 폴더를 구분해서 판단 — 설정은 재생성 가능

## 관련

- [[adr-002-global-cache-strategy]] — "개인 상태 vs 공유 상태" 분리 원칙 (유사 맥락)
