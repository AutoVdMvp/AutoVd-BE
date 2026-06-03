# AutoVd-BE 아키텍처 계획 v1: Services 기능 분할 기록

> 버전: 1.2 · 최종 갱신: 2026-06-04 · 브랜치: `dev/ai` · 상태: **계획 이력 / 이관 완료 (Implemented Plan)**
> 문서 역할: 이 문서는 현재 프로젝트 전체 현황 문서가 아니라, 영상 생성 기능을 `app/services/` 하위 단계 패키지로 분할한 계획과 결과를 보존하는 이력 문서다.
> 현재 프로젝트 기준 문서: [`../current/ARCHITECTURE.md`](../current/ARCHITECTURE.md)
> 다음 계획 문서: 목표 아키텍처는 [`ARCHITECTURE_PLAN_v2.md`](./ARCHITECTURE_PLAN_v2.md), 구현 청사진은 [`ARCHITECTURE_PLAN_v3.md`](./ARCHITECTURE_PLAN_v3.md)를 참조한다.
> 이름 규칙: `pipeline` 은 CI/CD 파이프라인과 혼동되므로 폴더명으로 쓰지 않는다.

---

## 0. 배경

과거 평면 구조에서는 핵심 기능이 웹/인프라 코드와 같은 `services/` 평면에 섞여 있었다.

```
(이전)  app/services/
        ├── crawler.py · llm.py · asset_generator.py · video_editor.py   # 핵심 기능
        └── tasks.py                                                     # 오케스트레이션
```

→ 5개 기능을 **단계별 서브패키지**로 분리해, "한 단계 = 한 폴더" 로 정리했다.

---

## 1. 분할 결과 (현재 구조)

```
app/services/
├── __init__.py              # 엔진 파사드 — 단계 함수 4종 re-export
├── tasks.py                 # Celery 오케스트레이션 (엔진 호출 경계)
├── crawler/                 # [1] 추출   ← 기존 crawler.py
│   ├── __init__.py
│   └── extractor.py
├── ai/                      # [2] 기획   ← 기존 llm.py(모델 호출)
│   ├── __init__.py
│   └── planner.py
├── prompts/                 # [3] 프롬프트(데이터) ← llm.py 하드코딩 문자열
│   ├── __init__.py          #   로더 load_prompt()
│   └── shorts_planning.yaml
├── image/                   # [4] 에셋   ← 기존 asset_generator.py
│   ├── __init__.py
│   └── generator.py
└── video/                   # [5] 합성   ← 기존 video_editor.py
    ├── __init__.py
    └── editor.py
```

---

## 2. 기능 → 디렉토리 매핑

| 단계 | 서브패키지 | 공개 함수 | 이전 위치 |
|------|-----------|-----------|-----------|
| [1] 추출 | `services/crawler/` | `extract_article(url)` | `services/crawler.py` |
| [2] 기획 | `services/ai/` | `generate_video_plan(text)` | `services/llm.py`(모델) |
| [3] 프롬프트 | `services/prompts/` | `load_prompt(name)` | `services/llm.py`(하드코딩) |
| [4] 에셋 | `services/image/` | `generate_assets(pid, plan)` | `services/asset_generator.py` |
| [5] 합성 | `services/video/` | `merge_video(pid, assets)` | `services/video_editor.py` |
| — | `services/tasks.py` | `generate_video_task` | 유지(엔진 호출만) |

---

## 3. 이 분할이 지킨 원칙

- **로직 무변경**: 크롤러·이미지·영상 3개는 파일을 그대로 이동(한 줄도 안 바뀜). `llm.py`만 모델 호출(`ai/`) + 프롬프트 데이터(`prompts/`)로 분리.
- **단계 격리**: 각 기능이 자기 서브패키지 안에 있어 서로 import 하지 않는다.
- **영향 범위 최소**: 기능 모듈을 직접 쓰는 곳은 `tasks.py` 뿐 → import만 파사드(`from app.services import …`)로 변경. `api/`·`main.py` 무변경.

---

## 4. 다음 단계

이 단계 구조는 안정적이지만, 외부 공급자(크롤러·LLM·이미지·TTS·렌더러)가 MVP 동안 자주 바뀐다.
교체 용이성·격리성을 끌어올리는 **도메인/포트·어댑터(헥사고날)** 목표 설계는 → [`ARCHITECTURE_PLAN_v2.md`](./ARCHITECTURE_PLAN_v2.md).
