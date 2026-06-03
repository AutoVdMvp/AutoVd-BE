# AutoVd-BE · Services 계층 아키텍처 청사진 (v3 · Implementation-Ready Blueprint)

> 버전: 3.2 · 최종 갱신: 2026-06-04 · 브랜치: `dev/ai` · 상태: **계획 문서 / 구현 준비 청사진 (Implementation Plan)**
> 문서 역할: 이 문서는 현재 프로젝트 전체 현황 문서가 아니라, v2 목표 설계를 현재 코드에 적용하기 위한 단계별 리팩토링 계획 문서다.
> 계보: [`ARCHITECTURE_PLAN_v1.md`](./ARCHITECTURE_PLAN_v1.md)(현 폴더 구조·as-is) → [`ARCHITECTURE_PLAN_v2.md`](./ARCHITECTURE_PLAN_v2.md)(목표 설계·이론) → **v3(본 문서·구현 청사진)**
> 현재 프로젝트 기준 문서: [`../current/ARCHITECTURE.md`](../current/ARCHITECTURE.md)
> 이름 규칙: `pipeline` 은 CI/CD 와 혼동되므로 폴더명으로 쓰지 않는다.

본 문서는 `app/services/`(영상 생성 도메인)의 **구현 준비 청사진**이다. v2가 *"무엇을 지향하는가"* 를 규정했다면, v3는 *"지금 코드에서 거기까지 어떻게, 무엇을 건드려, 무엇을 깨지 않고 가는가"* 를 규정한다. 모든 구조 결정은 현재 레포의 실제 파일에 근거한다.

---

## 0. v2 → v3 무엇이 달라졌나

| 축 | v2 (목표 설계) | v3 (구현 청사진) |
|---|---|---|
| 근거 | 이론적 To-Be("아직 코드 미반영") | **실제 현재 코드에 정렬** — 파일·dict 키·버그까지 매핑 |
| 계약 | `contracts.py` 도입 제안 | 현재 dict 모양 → pydantic **필드 단위 매핑표**(§7) |
| sourcing | `fetch(source)` 제너릭 | 현재 `extract_article(url)` URL 전용 → `source` 일반화 **이행 경로**(ADR-7) |
| 횡단 관심사 | §16 후속으로 나열 | **구현 패턴으로 승격**(§8): 경로 통일·로깅·재시도·부분실패 정책 |
| 경계 강제 | 원칙(말)로만 | **import-linter 규칙 + CI 게이트**(§18) |
| 배포 | 비범위 | 실제 `docker-compose`/`Dockerfile`/Celery 토폴로지 문서화(§13) |
| 발견된 결함 | — | 죽은 `BASE_DIR`, 하드코딩 `FONT_PATH`(이미 `VIDEO_FONT_PATH` 존재), Redis 포트 오타 `6479`, "영상 합치기 안됨" 회귀 — §8·§19에 명시 |

v3는 v2의 **결정을 뒤집지 않는다.** 헥사고날·도메인 로컬 AI·공유 계약·파사드 경계는 그대로 유효하다(§17 ADR-1~5). v3는 그 위에 **실행 가능성**을 입힌다.

---

## 목차
1. 기술 스택 · 패턴 탐지
2. 아키텍처 개요 · 원칙
3. 아키텍처 시각화 (3 레벨)
4. 핵심 도메인 컴포넌트 상세
5. 레이어 · 의존성 규칙 (+ 강제)
6. 데이터 아키텍처 (계약·매핑·경로)
7. 횡단 관심사 구현
8. 서비스 통신 패턴
9. Python 특화 아키텍처 패턴
10. 구현 패턴 · 템플릿
11. 테스트 아키텍처
12. 배포 아키텍처
13. 변경 시나리오 플레이북
14. 확장 · 진화 패턴
15. 현재 → 목표 마이그레이션
16. 아키텍처 결정 기록 (ADR)
17. 아키텍처 거버넌스
18. 신규 개발 청사진 · 흔한 함정
19. 미해결 질문 · 후속

---

## 1. 기술 스택 · 패턴 탐지 (Auto-detected)

| 영역 | 탐지 결과 | 근거 |
|---|---|---|
| 언어/런타임 | Python 3.11 | `Dockerfile: FROM python:3.11-slim` |
| 웹 | FastAPI + Uvicorn | `app/main.py`, `CMD uvicorn app.main:app` |
| 비동기 작업 | Celery (broker/backend = Redis) | `app/core/celery_app.py`, compose `worker` 서비스 |
| 워커 모델 | threads 풀, concurrency=1 | compose `celery ... -P threads --concurrency=1` |
| 설정 | pydantic-settings(`BaseSettings`, `.env`) | `app/core/config.py` |
| 외부 SDK | selenium(크롤), google-generativeai(LLM), httpx+pollinations(이미지), edge-tts(TTS), moviepy(렌더) | 각 단계 모듈 import |
| 영속 | PostgreSQL 15 | compose `db: postgres:15-alpine` |
| 산출물 저장 | 로컬 FS `temp_projects/<project_id>/` | `image/generator.py`, `video/editor.py` |

**아키텍처 패턴(현재):** 단계 기반 레이어드(stage-based layered). `crawler → ai(+prompts) → image → video` 의 5단 직선 파이프라인을 `services/__init__.py` 파사드가 re-export, `tasks.py`가 순차 호출.

**아키텍처 패턴(목표):** 포트 & 어댑터(Hexagonal) + 도메인별 바운디드 컨텍스트. v2 §5 그대로 유지.

---

## 2. 아키텍처 개요 · 원칙

품질 드라이버(우선순위 순, 충돌 시 위가 이김) — v2 §3 유지:

1. **교체 용이성** — 공급자를 도메인 로직 변경 없이 교체 (MVP 최우선).
2. **격리성** — 한 도메인 변경이 옆으로 번지지 않음.
3. **테스트 용이성** — 외부 호출 없이 도메인 규칙 검증.
4. **튜닝 용이성** — 프롬프트·모델·경로를 코드가 아닌 데이터/설정으로.

핵심 통찰(v2 §5.3 유지): **"AI는 계층이 아니라 어댑터다."** `planning`은 LLM(텍스트), `media`는 이미지/TTS — 서로 다른 도메인이 서로 다른 AI를 쓴다. 그러므로 전역 `ai/`·`prompts/` 폴더를 폐지하고 모델·프롬프트를 *그것을 쓰는 도메인 안에* 둔다.

> v3 추가 원칙 — **경계는 말이 아니라 도구로 지킨다.** 의존성 규칙(§5)은 import-linter로 CI에서 강제한다(§17). 문서에만 적힌 규칙은 깨진다.

---

## 3. 아키텍처 시각화 (3 레벨)

### 3.1 시스템 컨텍스트 (C4 Level 1)
```
        ┌──────────┐   POST /projects/{id}/generate   ┌─────────────────────┐
        │  Client  │ ───────────────────────────────▶ │  FastAPI (web)      │
        └──────────┘                                   │  api/video.py       │
                                                       └──────────┬──────────┘
                                                    enqueue(.delay)│
                                          ┌─────────────────────────▼────────┐
                                          │  Redis (broker + result backend) │
                                          └─────────────────────────┬────────┘
                                                                    │ consume
                                          ┌─────────────────────────▼────────┐
   외부: 뉴스사이트 · Gemini · Pollinations ◀──┤  Celery worker                   │
        · edge-tts · (ffmpeg/moviepy)        │  services/tasks.py → 도메인 4종   │
                                          └─────────────────┬────────────────┘
                                                            │ write
                                          ┌─────────────────▼────────────────┐
                                          │ temp_projects/<id>/*.mp3/.jpg/.mp4 │
                                          └────────────────────────────────────┘
```

### 3.2 컴포넌트 (C4 Level 2 · 목표 헥사고날) — v2 §5.2 유지
```
     ┌────────────────────────┐
     │   services/tasks.py     │   오케스트레이션 (Celery 경계)
     │   순서 제어 · 진행률     │
     └───────────┬────────────┘
                 │  도메인 파사드만 호출 (안정 인터페이스)
   ┌─────────────┼──────────────┬────────────────┐
   ▼             ▼              ▼                ▼
sourcing      planning        media           assembly   ← 도메인 서비스(순수 유스케이스)
   │             │              │                │
ArticleSource  Planner   ImageGen·VoiceGen  VideoComposer ← 포트(도메인이 정의)
   ▲             ▲              ▲                ▲
 selenium      gemini    pollinations·edge   moviepy       ← 어댑터(교체 단위, 외부 SDK 격리)

의존성 화살표(▲)는 전부 안쪽(포트)을 향한다. 어댑터→포트 의존, 그 반대 없음.
```

### 3.3 데이터 흐름 + 시퀀스
```
URL│검색어 ─[sourcing]→ Article ─[planning]→ VideoPlan ─[media]→ list[SceneAsset] ─[assembly]→ RenderedVideo

tasks.generate_video_task(project_id, source):
  10% crawling        article = sourcing.fetch(source)
  30% ai_planning     plan    = planning.generate_video_plan(article)
  60% asset_generation assets = media.generate_assets(project_id, plan)
  80% video_editing   video   = assembly.merge_video(project_id, assets)
 100% success         return {final_video_path, project_id}
```
> 진행률 퍼센트/스텝명은 현재 `tasks.py`의 `update_state` 값과 동일(10/30/60/80). 이 4개 스텝명은 클라이언트 폴링과의 **암묵 계약**이므로 도메인 리네이밍 시에도 유지한다(§8).

---

## 4. 핵심 도메인 컴포넌트 상세

각 도메인 = **service(순수) + ports(인터페이스) + adapters(외부 구현) + __init__(파사드)**. 외부 의존 없는 얇은 도메인은 ports/adapters 생략 가능(v2 §7).

### 4.1 sourcing (수집)
- **책임:** 입력(URL 또는 검색어) → 정제된 `Article` 확보. 정제 규칙(노이즈 제거, 본문 100자 미만 거부)은 **서비스의 도메인 규칙**, 페이지 로딩/셀렉터는 **어댑터 구현**.
- **포트:** `ArticleSource.fetch(source: str) -> Article`
- **파사드:** `sourcing.fetch(source)`
- **현재 어댑터:** selenium(`extract_article`) — 네이버 뉴스 셀렉터 + 정규식 정제 + `p`태그 폴백.
- **진화점:** 검색 API / 웹서치 / RSS 어댑터 추가. `source`가 URL인지 질의인지는 **어댑터가 판단**(ADR-7).
- **현재 결함:** `extract_article(url)`은 URL 전용. 본문 정제 규칙(noise_keywords, 길이 컷)이 어댑터에 박혀 있어 검색 어댑터로 갈 때 복제 위험 → 정제는 service로 끌어올린다.

### 4.2 planning (기획)
- **책임:** `Article` → `VideoPlan`(Scene 목록). 도메인 규칙: 빈 기획 거부, narration 1문장 보정.
- **포트:** `Planner.plan(article: Article) -> VideoPlan`
- **파사드:** `planning.generate_video_plan(article)`
- **현재 어댑터:** gemini(`gemini-flash-latest`, temperature 0.7, JSON mime). 프롬프트는 `prompts/shorts_planning.yaml`.
- **진화점:** OpenAI/Claude 어댑터. 모델명·프롬프트는 **도메인 로컬**(전역 `prompts/`를 `planning/prompts/`로 이동).
- **현재 결함:** 프롬프트 yaml 주석이 `app/pipeline/ai/planner.py`를 가리킴(과거 경로, 죽은 참조) → 이동 시 정정.

### 4.3 media (에셋)
- **책임:** Scene별 이미지 1 + 음성 1 = `SceneAsset` 생성. **씬 순회 루프는 service**, 이미지 생성·TTS는 각각 **포트**.
- **포트 2개:** `ImageGenerator.render(prompt, dest, *, size) -> str`, `VoiceSynthesizer.speak(text, dest, *, voice) -> str`
- **파사드:** `media.generate_assets(project_id, plan)`
- **현재 어댑터:** pollinations(httpx, 1080×1920, 3회 재시도), edge_tts(`ko-KR-SunHiNeural`, asyncio.run).
- **진화점:** SD/ElevenLabs 등 **각 포트 독립 교체**. 규모 커지면 `imaging`/`narration` 분리(v2 §6 판단 유지).
- **현재 결함:** ① 실패 씬을 `continue`로 **조용히 누락**(부분 결과) — 정책을 명시해야 함(ADR-8). ② `BASE_DIR=temp_projects`가 모듈에 박힘 → `settings.WORKSPACE_DIR`로(ADR-6). ③ TTS 실패 시 이미지 다운로드도 생략됨(루프 구조상) — 두 포트가 한 루프에 강결합.

### 4.4 assembly (합성)
- **책임:** `list[SceneAsset]` → 최종 mp4(`RenderedVideo`). 자막 합성·클립 연결·인코딩.
- **포트:** `VideoComposer.compose(project_id, assets) -> RenderedVideo`
- **파사드:** `assembly.merge_video(project_id, assets)`
- **현재 어댑터:** moviepy(`ImageClip`+`TextClip`+`concatenate`, libx264/aac, ultrafast).
- **진화점:** ffmpeg 직접 / 클라우드 렌더.
- **현재 결함:** ① 줄11 `BASE_DIR` 정의 후 미사용(죽은 코드), 줄18은 상대경로 `"temp_projects"` 사용 — 작업 디렉토리 의존(CWD 깨지면 산출물 분실, 최근 "영상 합치기 안됨" 회귀의 유력 후보). ② `FONT_PATH`를 OS 분기로 하드코딩하나 Dockerfile은 이미 `VIDEO_FONT_PATH` env 제공 → env 우선 읽기로 통일.

---

## 5. 레이어 · 의존성 규칙 (+ 강제)

### 5.1 규칙
> 의존성은 **항상 안쪽을 향한다.** `service.py`는 `adapters/`를 import 하지 않는다.
> 외부 SDK(`selenium`·`google-generativeai`·`httpx`·`edge_tts`·`moviepy`)는 **오직 `adapters/` 안에서만** import 한다.
> 도메인끼리 서로 import 하지 않는다. 연결은 `contracts.py`(데이터)와 `tasks.py`(흐름)만.

### 5.2 허용/금지 매트릭스
| from \ to | contracts | own ports | own service | own adapters | 타 도메인 | 외부 SDK |
|---|---|---|---|---|---|---|
| `service.py` | ✅ | ✅ | — | ❌ | ❌ | ❌ |
| `ports.py` | ✅ | — | ❌ | ❌ | ❌ | ❌ |
| `adapters/*` | ✅ | ✅ | ❌ | — | ❌ | ✅ |
| `__init__`(파사드) | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ |
| `tasks.py` | ✅ | ❌ | ❌ | ❌ | 파사드만 | ❌ |

### 5.3 강제(도구) — v3 신규
규칙을 `pyproject.toml`/`setup.cfg`의 **import-linter** 계약으로 표현하고 CI에서 검사(§17). 예시는 §17.

---

## 6. 데이터 아키텍처 (계약 · 매핑 · 경로)

### 6.1 공유 계약 (`services/contracts.py`, 신규)
```python
# pydantic BaseModel — 도메인 간 DTO. 도메인은 서로 import 않고 계약만 공유.
class Article(BaseModel):       title: str; content: str; source: str | None = None
class Scene(BaseModel):         scene_number: int; narration: str; image_prompt: str
class VideoPlan(BaseModel):     scenes: list[Scene]
class SceneAsset(BaseModel):    scene_number: int; image_path: str; audio_path: str; narration: str
class RenderedVideo(BaseModel): path: str
```

### 6.2 현재 dict → 계약 매핑 (필드 단위, grounded)
| 현재(dict) | 생성 위치 | → 계약 모델 | 비고 |
|---|---|---|---|
| `{"title","content"}` | `crawler/extractor.py` 반환 | `Article` | `source` 신규(입력 보존용) |
| `{"scenes":[{scene_number,narration,image_prompt}]}` | `ai/planner.py` JSON | `VideoPlan`+`Scene` | yaml 출력 스키마와 1:1 |
| `[{scene_number,audio_path,image_path,narration}]` | `image/generator.py` | `list[SceneAsset]` | 키 이름 그대로 |
| `output_path: str` | `video/editor.py` 반환 | `RenderedVideo.path` | 단일 필드 래핑 |

> dict→타입 모델 전환의 가치: 한 도메인이 출력 모양을 바꾸면 변화가 **타입으로 드러나** 옆 도메인을 조용히 깨뜨리지 못한다. 현재는 `scene.get("narration","")`식 방어 코드가 곳곳에 흩어져 있다.

### 6.3 검증
- **입력 검증:** 어댑터 경계에서 pydantic 파싱(`VideoPlan(**raw)`) — LLM이 형식 위반 시 즉시 실패.
- **도메인 규칙 검증:** service.py에서(빈 plan 거부, 본문 길이 컷). 현재 `len < 100` 컷은 sourcing 어댑터에 있음 → service로 승격.

### 6.4 작업물 경로 (단일화) — ADR-6
현재 `"temp_projects"`가 3곳(`main.py` static, `image/generator.py`, `video/editor.py`)에 흩어지고 `video/editor.py`엔 죽은 `BASE_DIR`까지 있음. → `settings.WORKSPACE_DIR` **한 곳**으로 통일. 어댑터·파사드는 이 설정을 읽는다.
```python
# core/config.py
WORKSPACE_DIR: str = "temp_projects"   # 신규
```

---

## 7. 횡단 관심사 구현 — v3에서 후속→구현으로 승격

### 7.1 인증 · 인가
- 영상 도메인 **밖**의 관심사. 경계는 `api/`(FastAPI 의존성, JWT — `core/security.py`)에서 처리. `tasks.py`/도메인은 인증을 모른다(이미 순수). 유지.

### 7.2 에러 처리 · 회복탄력성 (2층 분리)
| 층 | 책임 | 현재 | 목표 |
|---|---|---|---|
| 어댑터(저수준) | 일시적 외부 오류 재시도 | pollinations 3회 `time.sleep(5)` | 백오프·타임아웃 명시, 포트별 결정 |
| tasks(단계) | 단계 실패 → 작업 상태 전이 | `except`→`update_state(FAILURE)`→raise | Celery `autoretry_for`/`retry_backoff` 검토 |
- **부분 실패 정책(ADR-8):** media가 일부 씬 실패 시 현재 `continue`(조용한 누락). v3 결정: **명시적 정책** 필요 — (a) 최소 씬 수 미달 시 전체 실패, (b) 누락 씬을 결과 메타에 보고. 후속 트랜잭션/보상은 미정(§19).

### 7.3 로깅 · 관측
- **현재:** 전부 `print()` + Celery `update_state`. 구조화/상관ID 없음.
- **목표:** ① `logging`(또는 structlog)로 교체, `project_id`를 상관키로. ② **진행률은 단일 관측 계약**: `update_state(state, meta={step, percent})` 만이 외부 노출. 도메인 내부는 로깅만, 진행률 보고는 tasks가 독점(도메인이 Celery를 모르게 유지).

### 7.4 검증 — §6.3 참조.

### 7.5 설정 · 시크릿
- `core/config.Settings`(pydantic, `.env`). API 키(`GEMINI_API_KEY` 등)·모델명·`WORKSPACE_DIR`·폰트 경로는 설정/도메인 로컬 상수로, **어댑터가 읽는다.**
- **발견된 불일치:** `config.py` 기본 `REDIS_URL=redis://redis:6479/0`(오타) vs compose/celery `6379`. celery는 env로 덮어써 동작하나, FastAPI측이 기본값을 쓰면 broker 불일치. → `6379`로 정정(§19).
- 모델명·temperature 등 **튜닝 파라미터는 어댑터 상수**(도메인 로컬), 프롬프트는 yaml(데이터).

---

## 8. 서비스 통신 패턴
- **web → worker:** 비동기. `api/video.py`가 `generate_video_task.delay(project_id, source)` 로 Redis 큐 적재. 결과는 result backend 폴링.
- **tasks → 도메인:** 동기 함수 호출(파사드 시그니처만). 4단 직선.
- **도메인 → 외부:** 어댑터가 SDK로(동기 httpx/selenium/moviepy, edge_tts는 `asyncio.run`으로 동기 래핑).
- **버저닝/계약 안정성:** 외부 노출 계약은 ① 파사드 시그니처 4종, ② 진행률 스텝명(`crawling/ai_planning/asset_generation/video_editing`) + percent. 도메인 리네이밍이 이 둘을 깨면 안 됨.
- **현재 시그니처 격차:** `tasks.py`는 `extract_article(article_url)` / `generate_video_plan(clean_text)`(dict 언팩)로 호출 → 목표 `sourcing.fetch(source)` / `planning.generate_video_plan(article)`(계약 객체)로 이행(§15).

---

## 9. Python 특화 아키텍처 패턴
- **포트 = `typing.Protocol`** (구조적 타이핑). 어댑터가 명시적 상속 없이 시그니처만 맞추면 됨 → 결합 최소.
- **DI = 기본 인자 주입.** `generate_video_plan(article, planner: Planner = ...)`; 파사드가 기본 어댑터를 결선, 테스트는 Fake 주입.
- **패키지 = 파사드.** 도메인 `__init__.py`가 공개 함수만 노출, 내부(service/ports/adapters)는 캡슐화.
- **비동기 경계 격리.** `edge_tts` 같은 async-only SDK는 **어댑터 내부에서** `asyncio.run`으로 가두고, 도메인/포트는 동기 시그니처 유지(현재 패턴 그대로 권장).
- **프롬프트 = 데이터(yaml) + 로더.** `load_prompt(name)` → `planning/prompts/<name>.yaml`. 도메인 로컬.

---

## 10. 구현 패턴 · 템플릿

### 10.1 포트
```python
# <domain>/ports.py
from typing import Protocol
from app.services.contracts import Article, VideoPlan

class Planner(Protocol):
    def plan(self, article: Article) -> VideoPlan: ...
```

### 10.2 서비스(순수 유스케이스)
```python
# <domain>/service.py — 외부 SDK 모름. 도메인 규칙만.
from app.services.contracts import Article, VideoPlan
from app.services.planning.ports import Planner

def generate_video_plan(article: Article, planner: Planner) -> VideoPlan:
    plan = planner.plan(article)
    if not plan.scenes:
        raise ValueError("빈 기획안")          # 도메인 규칙
    return plan
```

### 10.3 어댑터(교체 단위, 외부 SDK 격리)
```python
# planning/adapters/gemini.py
import json, google.generativeai as genai
from app.core.config import settings
from app.services.contracts import Article, VideoPlan, Scene
from app.services.planning.prompts import load_prompt
genai.configure(api_key=settings.GEMINI_API_KEY)

class GeminiPlanner:                       # Planner 구현(구조적)
    MODEL = "gemini-flash-latest"          # ← 이 도메인만의 모델 선택
    def plan(self, article: Article) -> VideoPlan:
        model = genai.GenerativeModel(self.MODEL,
            system_instruction=load_prompt("shorts_planning"),
            generation_config={"temperature": 0.7, "response_mime_type": "application/json"})
        raw = json.loads(model.generate_content(article.content).text)
        return VideoPlan(scenes=[Scene(**s) for s in raw["scenes"]])
```

### 10.4 파사드(기본 결선)
```python
# planning/__init__.py — 바깥은 이것만 본다. 교체는 이 한 줄.
from app.services.planning.service import generate_video_plan as _run
from app.services.planning.adapters.gemini import GeminiPlanner

def generate_video_plan(article):
    return _run(article, planner=GeminiPlanner())
```

### 10.5 media — 두 포트 한 서비스
```python
# media/service.py — 씬 순회는 여기. 두 포트 주입.
def generate_assets(project_id, plan, *, images: ImageGenerator,
                    voices: VoiceSynthesizer, workspace: str) -> list[SceneAsset]:
    dest = os.path.join(workspace, project_id); os.makedirs(dest, exist_ok=True)
    assets = []
    for sc in plan.scenes:
        audio = voices.speak(sc.narration, f"{dest}/scene_{sc.scene_number}.mp3", voice="ko-KR-SunHiNeural")
        image = images.render(sc.image_prompt, f"{dest}/scene_{sc.scene_number}.jpg", size=(1080,1920))
        assets.append(SceneAsset(scene_number=sc.scene_number, image_path=image,
                                 audio_path=audio, narration=sc.narration))
    return assets   # 부분 실패 정책(ADR-8)은 여기서 결정
```

---

## 11. 테스트 아키텍처 — v2 §12 유지 + 구체화

| 층 | 대상 | 방법 | 외부 호출 |
|---|---|---|---|
| 단위 | `service.py` 도메인 규칙 | 포트에 Fake 주입 | 없음 |
| 계약 | `adapter` ↔ 포트 시그니처 | 어댑터가 포트 형태로 입출력 | 실제/모킹 |
| 통합 | `tasks` 전체 흐름 | 파사드를 Fake로 교체, 순서·전달 검증 | 없음(e2e 별도) |

```python
class FakePlanner:
    def plan(self, article): return VideoPlan(scenes=[Scene(scene_number=1, narration="a", image_prompt="b")])
def test_rejects_empty():
    with pytest.raises(ValueError):
        generate_video_plan(Article(title="t", content="c"), planner=EmptyPlanner())
```
> 현재 레포에 테스트 디렉토리 부재 → `tests/services/<domain>/` 신설을 마이그레이션과 동반(§15).

---

## 12. 배포 아키텍처 (grounded)
```
docker-compose:
  db     postgres:15-alpine
  redis  redis:7-alpine        :6379  (broker + result backend)
  web    build . → uvicorn app.main:app :8000   depends_on db,redis
  worker build . → celery -A app.core.celery_app worker -P threads --concurrency=1
```
- **단일 이미지(`Dockerfile`)** 를 web/worker가 공유. 이미지에 ffmpeg·imagemagick·fonts-nanum·google-chrome-stable 포함(무거운 런타임 의존).
- **워커 모델:** threads 풀, concurrency=1 — moviepy/selenium이 프로세스 무거워서로 보임. 동시성 확장은 별도 검토.
- **환경 변수 경계:** `CELERY_BROKER_URL`/`RESULT_BACKEND`는 compose에서 주입, `VIDEO_FONT_PATH`는 Dockerfile에서 설정(현재 코드가 안 읽음 → §7.5 정정 대상).
- **상태:** 산출물은 컨테이너 로컬 FS(`temp_projects/`) — 영속/공유 스토리지 아님(스케일아웃 시 재검토, §19).

---

## 13. 변경 시나리오 플레이북 ⭐ (v2 §11 유지 · 확장)

| 바꾸고 싶은 것 | 건드리는 곳 | 보장: 안 건드리는 곳 |
|---|---|---|
| 크롤링 → 검색 API | `sourcing/adapters/search_api.py` + 결선 1줄 | planning·media·assembly·tasks·contracts |
| LLM Gemini → OpenAI | `planning/adapters/openai.py` + 결선 1줄 | 타 도메인·tasks·프롬프트 |
| 기획 프롬프트 튜닝 | `planning/prompts/*.yaml`(데이터) | **코드 전부** |
| 이미지 Pollinations → SD | `media/adapters/stable_diffusion.py` + 결선 | 음성 어댑터·타 도메인·tasks |
| TTS Edge → ElevenLabs | `media/adapters/elevenlabs.py` + 결선 | 이미지 어댑터·타 도메인·tasks |
| 렌더 MoviePy → ffmpeg | `assembly/adapters/ffmpeg.py` + 결선 | 타 도메인·tasks |
| 단계 추가(배경음악) | 새 도메인 폴더 + tasks 호출 1줄 | 기존 도메인 내부 |
| 순서·재시도 변경 | `tasks.py`만 | 도메인 전부 |
| 계약 변경(Scene 필드 추가) | `contracts.py` + 해당 도메인 | 무관 도메인(타입체크로 누락 발견) |
| **작업 경로 변경**(v3) | `core/config.WORKSPACE_DIR` 1곳 | 어댑터 코드(설정만 읽음) |
| **폰트 변경**(v3) | `VIDEO_FONT_PATH` env | assembly 코드 |

원칙: **교체 = `adapters/` 추가 + 파사드 결선 한 줄.** 시그니처(포트·파사드·계약)가 유지되면 파급은 0.

---

## 14. 확장 · 진화 패턴
- **기능 추가(새 단계):** 새 도메인 폴더(동일 표준 레이아웃) → `contracts`에 새 DTO(필요시) → `tasks`에 호출 1줄. 기존 도메인 불변.
- **어댑터 추가:** 포트만 구현하면 됨. 파사드 결선 교체로 활성화. A/B는 파사드에서 분기 가능.
- **외부 시스템 통합(부패 방지층):** 외부 응답을 어댑터가 **계약 모델로 즉시 번역**. 외부 스키마가 도메인으로 새지 않게(현재 LLM JSON→`VideoPlan` 번역이 이 패턴).
- **분리(media → imaging/narration):** 규모 시 포트 2개를 두 도메인으로 승격, tasks가 두 번 호출. 계약(SceneAsset)은 유지.

---

## 15. 현재 → 목표 마이그레이션

### 15.1 격차표 (실제 파일 기준)
| 현재 | 목표 | 작업 |
|---|---|---|
| `crawler/extractor.py` (dict, url) | `sourcing/`(service·ports·adapters/selenium, Article) | 정제 로직을 service로, 어댑터는 fetch 구현 |
| `ai/planner.py` + 전역 `prompts/` | `planning/`(+ prompts 로컬, VideoPlan) | 프롬프트 폴더 이동, JSON→계약 파싱 |
| `image/generator.py`(이미지+TTS 한 루프) | `media/`(포트 2개, service 순회) | 두 어댑터 분리, 부분실패 정책 |
| `video/editor.py`(상대경로·죽은 BASE_DIR·하드코딩 폰트) | `assembly/`(adapters/moviepy, WORKSPACE_DIR·env 폰트) | 경로/폰트 정정 + 회귀 수정 |
| dict 전반 | `contracts.py` | pydantic 5종 신설 |
| — | `tests/services/` | 도메인별 단위 테스트 |

### 15.2 점진 채택 순서(가변성 큰 순) — v2 §14 유지
**① sourcing**(곧 검색 교체) → **② planning**(모델/프롬프트 잦은 변경) → **③ media** → **④ assembly**(가장 안정). 단, **0순위로 `contracts.py` + `WORKSPACE_DIR`** 를 먼저 도입(모든 도메인의 공통 토대이자 현 회귀의 원인). 각 단계는 파사드 시그니처를 유지하면 tasks·타 도메인 무영향.

> v3 권장 진입점: 현재 "영상 합치기 안됨"(commit 6fb802c) 회귀가 assembly 경로 문제일 가능성이 높으므로, **0순위 경로 통일을 먼저 처리**해 동작 복구 후 도메인 리팩터를 진행.

---

## 16. 아키텍처 결정 기록 (ADR)

v2 ADR 유지:
- **ADR-1** 포트&어댑터 채택 — 외부 공급자 대부분 가변, 교체성 1순위.
- **ADR-2** AI를 도메인 로컬로 — 전역 `ai/`·`prompts/` 폐지.
- **ADR-3** 공유 계약 모듈(`contracts.py`) — 도메인 직접 import 금지.
- **ADR-4** 오케스트레이션은 파사드만 의존.
- **ADR-5** `pipeline` 명칭 배제.

v3 신규:
- **ADR-6 작업 경로 단일화(`WORKSPACE_DIR`)** — 3곳 분산 + 죽은 `BASE_DIR` + 상대경로 의존이 산출물 분실·회귀를 유발. 설정 1곳으로 통일, 어댑터는 읽기만. *결과:* CWD 비의존, 변경 1곳.
- **ADR-7 sourcing 입력 일반화(`source: str`)** — 크롤→검색 교체가 시그니처 변경을 일으키지 않도록 입력을 URL이 아닌 `source`로. URL/질의 판별은 어댑터 책임. *비용:* api층이 `source` 의미를 알아야 함(원래 `original_url` 전달).
- **ADR-8 부분 실패 정책 명문화** — media의 조용한 `continue`를 금지. 최소 씬 수 게이트 + 누락 보고를 계약화. *미정:* 보상 트랜잭션(§19).
- **ADR-9 경계의 도구 강제(import-linter)** — 의존성 규칙(§5)을 CI 게이트로. *결과:* 문서-코드 드리프트 차단. *비용:* 린터 설정·유지.
- **ADR-10 폰트 경로 env화** — 하드코딩 OS 분기 제거, 기존 `VIDEO_FONT_PATH` env 사용.

각 결정은 *맥락(왜 필요)·고려요소·결과(±)* 를 위에 명시. 부정적 결과(간접층/파일 증가)는 v2 ADR-1대로 **가변성 높은 도메인부터 점진 적용**으로 상쇄.

---

## 17. 아키텍처 거버넌스

### 17.1 자동 검사(권장)
```ini
# setup.cfg — import-linter (예시)
[importlinter]
root_package = app

[importlinter:contract:domain-isolation]
name = 도메인은 서로 import 하지 않는다
type = independence
modules =
    app.services.sourcing
    app.services.planning
    app.services.media
    app.services.assembly

[importlinter:contract:no-sdk-in-service]
name = service는 외부 SDK를 모른다
type = forbidden
source_modules = app.services.planning.service
forbidden_modules = google.generativeai
```
- **CI 게이트:** `lint-imports` 실패 시 머지 차단. + `ruff`/`mypy`(계약 타입 검사로 도메인 간 누락 조기 발견).

### 17.2 리뷰 체크리스트
- [ ] 새 외부 SDK import가 `adapters/` 밖에 있는가? → 거부.
- [ ] 도메인이 타 도메인을 import 하는가? → 거부(`contracts`/`tasks`만).
- [ ] 경로/폰트/모델키를 코드에 하드코딩했는가? → 설정으로.
- [ ] 파사드 시그니처/진행률 스텝명을 바꿨는가? → 계약 영향 검토.

### 17.3 문서 정합성
현재 프로젝트 현황=`../current/ARCHITECTURE.md`, 기능 분할 이력=`ARCHITECTURE_PLAN_v1.md`, 목표 설계=`ARCHITECTURE_PLAN_v2.md`, **구현 청사진=`ARCHITECTURE_PLAN_v3.md`(본 문서)**. 코드가 §15 순서로 도메인화되면 v1·v2를 본 문서로 통합 검토한다.

---

## 18. 신규 개발 청사진 · 흔한 함정

### 18.1 워크플로(새 기능/어댑터)
1. 계약 영향 확인(`contracts.py`) → 필요 시 DTO 추가.
2. 포트 정의/확인(`ports.py`).
3. 서비스에 도메인 규칙(`service.py`, 외부 SDK 금지).
4. 어댑터 구현(`adapters/<provider>.py`, SDK 격리).
5. 파사드 결선(`__init__.py` 한 줄).
6. tasks는 **흐름이 바뀔 때만** 수정.
7. 단위 테스트(Fake 주입) + import-linter 통과.

### 18.2 표준 파일 배치
```
services/<domain>/
├── __init__.py          # 파사드: 기본 어댑터 결선 → 공개 함수
├── service.py           # 순수 유스케이스(외부 SDK 금지)
├── ports.py             # Protocol
├── prompts/             # (AI 도메인) 데이터 yaml + load_prompt
└── adapters/<provider>.py
```

### 18.3 흔한 함정 (현 코드에서 관측된 것 포함)
- **상대경로 산출물** — `os.path.join("temp_projects", ...)`는 CWD에 의존(현 assembly 회귀 후보). 항상 `settings.WORKSPACE_DIR` 절대경로.
- **죽은 설정** — `video/editor.py`의 미사용 `BASE_DIR`처럼 정의-후-미사용은 혼동 유발. 제거.
- **env 무시** — `VIDEO_FONT_PATH`가 있는데 코드가 OS 분기 하드코딩. 제공된 env 우선.
- **조용한 누락** — `except: continue`로 부분 결과를 만들면 영상이 말없이 짧아짐. 정책화(ADR-8).
- **dict 방어 코드** — `.get(k, default)` 남발은 계약 부재의 증상. pydantic으로 형식 강제.
- **설정 드리프트** — `REDIS_URL` 기본 `6479`(오타) vs 실제 `6379`. 기본값도 정확히.
- **SDK 누수** — service에서 `import httpx` 같은 유혹 → 어댑터로.

---

## 19. 미해결 질문 · 후속
- **보상 트랜잭션:** media 부분 실패/assembly 실패 시 롤백·재개 전략(ADR-8 연장).
- **산출물 영속:** `temp_projects/` 로컬 FS → 객체 스토리지(S3 등) 이전 시점(워커 스케일아웃 전제).
- **워커 동시성:** concurrency=1 한계. 도메인별 큐 분리(크롤/렌더 격리) 검토.
- **`REDIS_URL` 오타(6479) 즉시 수정** 및 web/worker 브로커 설정 단일화.
- **assembly 회귀("영상 합치기 안됨") 원인 확정** — 경로(ADR-6) 우선 적용 후 재현 테스트.

---

> _이 청사진은 2026-06-04 기준 실제 레포(`dev/ai`) 코드에 정렬해 생성됨. 도메인화(§15)가 진행될 때마다 §6 매핑표·§16 ADR·§17 린터 계약을 함께 갱신할 것. 코드가 목표 구조에 도달하면 상태를 "구현 청사진"에서 "현행 표준"으로 승격한다._
