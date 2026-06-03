# AutoVd-BE 문서 안내

> 버전: 1.1 · 최종 갱신: 2026-06-04 · 브랜치: `dev/ai` · 상태: **현재 현황 안내 (Docs Index)**
> 문서 역할: `docs/` 폴더의 문서 역할과 하위 폴더별 관리 기준을 구분하는 진입점이다. 프로젝트의 현재 구조 설명은 [`current/ARCHITECTURE.md`](./current/ARCHITECTURE.md)를 기준으로 한다.

## 먼저 읽을 문서

현재 프로젝트의 실제 코드, API, 데이터 모델, 인프라 구성을 확인하려면 [`current/ARCHITECTURE.md`](./current/ARCHITECTURE.md)를 먼저 읽는다.

## 폴더 구분

| 폴더 | 구분 | 관리 기준 |
|------|------|-----------|
| [`current/`](./current/) | 현재 기준 문서 | 현재 코드와 운영 구성을 설명한다. 최신 현황은 이 폴더에서 관리한다. |
| [`plans/`](./plans/) | 계획/이력 문서 | 리팩토링 계획, 목표 설계, 구현 청사진, 이관 기록을 보존한다. |
| [`governance/`](./governance/) | 문서 관리 규칙 | 문서 분류, 메타데이터, 버전 관리 방식을 규정한다. |

## 주요 문서

| 문서 | 구분 | 설명 |
|------|------|------|
| [`current/ARCHITECTURE.md`](./current/ARCHITECTURE.md) | 현재 기준 문서 | 현재 프로젝트 내용의 단일 기준 문서 |
| [`plans/ARCHITECTURE_PLAN_v3.md`](./plans/ARCHITECTURE_PLAN_v3.md) | 구현 계획 | 목표 설계를 현재 코드에 적용하는 청사진 |
| [`governance/DOCUMENT_VERSION_CONTROL.md`](./governance/DOCUMENT_VERSION_CONTROL.md) | 관리 규칙 | 문서 분류, 메타데이터, 버전 관리 규칙 |

`plans/`의 문서는 현재 상태를 대체하지 않는다. 계획이 코드에 반영되면 [`current/ARCHITECTURE.md`](./current/ARCHITECTURE.md)를 함께 갱신한다.
