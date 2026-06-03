# AutoVd-BE · Services 계층 아키텍처 스펙 (Target / To-Be)

> 버전: 1.2 · 최종 갱신: 2026-06-04 · 브랜치: `dev/ai` · 상태: **계획 문서 / 목표 설계 (Target / To-Be)**
> 문서 역할: 이 문서는 현재 프로젝트 전체 현황 문서가 아니라, `app/services/` 계층이 향후 지향할 목표 아키텍처를 설명하는 계획 문서다.
> 현재 프로젝트 기준 문서: [`../current/ARCHITECTURE.md`](../current/ARCHITECTURE.md)
> 관련 계획 문서: [`ARCHITECTURE_PLAN_v1.md`](./ARCHITECTURE_PLAN_v1.md)(기능 분할 이관 기록) · [`ARCHITECTURE_PLAN_v3.md`](./ARCHITECTURE_PLAN_v3.md)(구현 청사진)
> 이름 규칙: `pipeline` 은 CI/CD 파이프라인과 혼동되므로 폴더명으로 쓰지 않는다.

본 문서는 `app/services/`(영상 생성 도메인)의 **목표 아키텍처**를 규정한다. 코드는 아직 단계 기반 구조이며, 이 스펙은 그 진화 방향이다.

---

## 목차
1. 목적 · 범위 · 비범위
2. 용어 (Ubiquitous Language)
3. 아키텍처 드라이버 (품질 속성)
4. 요구사항 → 아키텍처 대응
5. 아키텍처 스타일: 포트 & 어댑터
6. 도메인 분해 (바운디드 컨텍스트)
7. 도메인 내부 표준 레이아웃
8. 도메인 간 계약 (Shared Kernel)
9. 오케스트레이션
10. 목표 디렉토리 구조
11. **변경 시나리오 플레이북** ⭐
12. 테스트 전략
13. 명명 규칙
14. 현재 → 목표 매핑 · 점진 채택
15. 아키텍처 결정 기록 (ADR)
16. 횡단 관심사 · 후속

---

## 1. 목적 · 범위 · 비범위

**무엇을 만드나.** 기사 URL 또는 검색어를 입력받아 **유튜브 쇼츠(세로 영상)** 를 자동 생성한다.

**전제 — MVP다.** 거의 모든 외부 구성요소가 바뀔 수 있다(크롤링→검색, LLM 모델/프롬프트, 이미지·TTS 공급자, 렌더 방식). 따라서 이 아키텍처의 **제1목표는 "쉽게 바꾸고, 바꿔도 옆을 안 건드리는 것"** 이다.

| 범위(In) | 비범위(Out / Non-Goals) |
|---|---|
| `app/services/` 도메인 분해·경계·인터페이스 | 웹/인증/DB 스키마 (→ [`../current/ARCHITECTURE.md`](../current/ARCHITECTURE.md)) |
| 외부 공급자 교체 전략(포트·어댑터) | 구체적 공급자 SDK 사용법·튜닝 |
| 도메인 간 데이터 계약 | Celery 토폴로지·인프라·배포 |
| 오케스트레이션이 도메인을 호출하는 규약 | 단계별 재시도/보상 트랜잭션 상세(후속) |

---

## 2. 용어 (Ubiquitous Language)

| 용어 | 의미 |
|---|---|
| **Article** | 수집·정제된 기사 본문(제목 + 본문). sourcing의 산출물. |
| **Scene** | 영상의 한 컷. `narration`(1문장) + `image_prompt`. |
| **VideoPlan** | Scene의 순서 있는 목록. planning의 산출물. |
| **SceneAsset** | 한 Scene의 실제 미디어(이미지 파일 + 음성 파일). media의 산출물. |
| **RenderedVideo** | 최종 mp4. assembly의 산출물. |
| **도메인(바운디드 컨텍스트)** | 한 가지 책임을 갖는 자족적 단위(sourcing/planning/media/assembly). |
| **포트(Port)** | 도메인이 *필요로 하는* 능력의 인터페이스(`Protocol`). |
| **어댑터(Adapter)** | 포트의 구체 구현. 외부 SDK는 여기서만 쓴다. **교체 단위.** |
| **도메인 서비스(Service)** | 외부를 모르는 순수 유스케이스·도메인 규칙. |
| **파사드(Facade)** | 도메인의 기본 어댑터를 결선해 노출하는 공개 함수. 바깥은 이것만 본다. |

---

## 3. 아키텍처 드라이버 (품질 속성)

우선순위 순. 설계가 충돌하면 위가 이긴다.

1. **교체 용이성(Swappability)** — 공급자를 도메인 로직 변경 없이 교체. *MVP라 최우선.*
2. **격리성(Isolation)** — 한 도메인 변경이 다른 도메인·오케스트레이션으로 번지지 않음.
3. **테스트 용이성(Testability)** — 외부 호출 없이 도메인 로직 검증(포트에 목 주입).
4. **튜닝 용이성** — 프롬프트·모델·경로를 코드가 아닌 데이터/설정으로.

---

## 4. 요구사항 → 아키텍처 대응

| 요구사항(오너) | 아키텍처적 대응 | 스펙 위치 |
|---|---|---|
| 기사 수집을 크롤링 → 검색 API/웹서치로 교체 | **sourcing** 도메인 + `ArticleSource` 포트, 어댑터만 교체 | §6, §11 |
| AI 모델·프롬프트를 **도메인마다 각각, 독립** 변경 | AI를 공용 계층으로 두지 않고 **각 도메인이 자기 모델·프롬프트 소유** | §5, §6 |
| 태스크는 각 도메인 변경에 영향 없게 | 오케스트레이션은 **도메인 파사드(안정 인터페이스)만** 의존 | §9, §11 |

---

## 5. 아키텍처 스타일: 포트 & 어댑터 (Hexagonal)

각 도메인을 **서비스(순수) + 포트(인터페이스) + 어댑터(외부 구현)** 로 나눈다.

### 5.1 의존성 규칙 (가장 중요)
> 의존성은 **항상 안쪽(도메인/포트)을 향한다.** 도메인은 어댑터를 모른다.
> 외부 SDK(`selenium`·`google-generativeai`·`httpx`·`edge-tts`·`moviepy`)는 **오직 어댑터 안에서만** import 한다.

### 5.2 컴포넌트 다이어그램
```
        [ api/video.py ]                      웹: 요청 수신 → 큐 적재
               │ enqueue
               ▼
     ┌────────────────────────┐
     │   services/tasks.py     │             오케스트레이션 (Celery 경계)
     │   순서 제어 · 진행률     │
     └───────────┬────────────┘
                 │  도메인 파사드만 호출 (안정 인터페이스)
   ┌─────────────┼──────────────┬────────────────┐
   ▼             ▼              ▼                ▼
sourcing      planning        media           assembly       ← 도메인 (유스케이스, 순수)
   │             │              │                │
ArticleSource  Planner    ImageGen·VoiceGen  VideoComposer    ← 포트 (도메인이 정의)
   ▲             ▲              ▲                ▲
   │             │              │                │
 selenium      gemini      pollinations        moviepy        ← 어댑터 (교체 대상)
 (→검색API,    (→OpenAI/    edge_tts            (→ffmpeg,
  웹서치)       Claude)     (→SD·ElevenLabs)    클라우드)
   │             │              │                │
   ▼             ▼              ▼                ▼
 [외부]        [외부 LLM]    [외부 AI·TTS]      [외부]

의존성 화살표(▲)는 모두 안쪽(포트)을 향한다. 어댑터가 포트에 의존하지, 그 반대가 아니다.
```

### 5.3 핵심 통찰 — "AI는 계층이 아니라 어댑터다"
기존의 전역 `ai/`·`prompts/` 폴더는 *AI가 하나의 공용 계층*인 듯한 착시를 준다. 실제로는 **planning은 LLM(텍스트), media는 이미지 생성 AI** 로 서로 다른 도메인이 서로 다른 AI를 쓴다. 그래서 AI 모델·프롬프트는 **그 AI를 쓰는 도메인 안에** 둔다 → 도메인마다 독립 교체(요구사항 2).

---

## 6. 도메인 분해 (바운디드 컨텍스트)

| 도메인 | 책임 | 포트 (시그니처) | 파사드 (공개 함수) | 현재→미래 어댑터 |
|---|---|---|---|---|
| **sourcing** 수집 | 입력 → 기사 확보·정제 | `ArticleSource.fetch(source: str) -> Article` | `sourcing.fetch(source)` | selenium → 검색API·웹서치·RSS |
| **planning** 기획 | 기사 → 씬 기획안 | `Planner.plan(article: Article) -> VideoPlan` | `planning.generate_video_plan(article)` | gemini → OpenAI·Claude |
| **media** 에셋 | 씬별 이미지·음성 생성 | `ImageGenerator.render(prompt, dest, *, size) -> str`<br>`VoiceSynthesizer.speak(text, dest, *, voice) -> str` | `media.generate_assets(project_id, plan)` | pollinations·edge_tts → SD·ElevenLabs |
| **assembly** 합성 | 에셋 → 최종 mp4 | `VideoComposer.compose(project_id, assets) -> RenderedVideo` | `assembly.merge_video(project_id, assets)` | moviepy → ffmpeg·클라우드 |

**도메인 독립 원칙**: 도메인끼리 서로 import 하지 않는다. 연결은 공유 계약(§8)과 오케스트레이션(§9)만 담당한다.

> **판단(media)**: 이미지·음성은 공급자가 다르지만 "씬당 한 쌍의 에셋"이라는 한 유스케이스라 **media 한 도메인 + 포트 2개**로 둔다(각각 독립 교체). 규모가 커지면 `imaging`/`narration` 으로 분리한다.

---

## 7. 도메인 내부 표준 레이아웃

한 도메인 = 아래 요소. 외부 의존이 없는 얇은 도메인은 `ports`/`adapters` 생략 가능.

```
services/planning/
├── __init__.py          # 파사드: 기본 어댑터 결선 → 공개 함수
├── service.py           # 유스케이스(순수). 외부 SDK import 금지
├── ports.py             # 이 도메인이 필요로 하는 인터페이스(Protocol)
├── prompts/             # (AI 도메인) 프롬프트 = 데이터. 도메인 로컬
│   └── shorts_planning.yaml
└── adapters/            # 포트 구현 = 교체 단위. 외부 SDK는 여기서만
    └── gemini.py
```

### 코드 스케치
```python
# planning/ports.py
from typing import Protocol
from app.services.contracts import Article, VideoPlan
class Planner(Protocol):
    def plan(self, article: Article) -> VideoPlan: ...

# planning/service.py — 순수 유스케이스(외부 SDK 모름)
from app.services.contracts import Article, VideoPlan
from app.services.planning.ports import Planner
def generate_video_plan(article: Article, planner: Planner) -> VideoPlan:
    plan = planner.plan(article)
    # 도메인 규칙(예: 빈 기획 거부, 씬 1문장 보정)은 여기서
    return plan

# planning/adapters/gemini.py — 교체 대상. 모델·프롬프트가 도메인 로컬
import json, google.generativeai as genai
from app.core.config import settings
from app.services.contracts import Article, VideoPlan, Scene
from app.services.planning.prompts import load_prompt
genai.configure(api_key=settings.GEMINI_API_KEY)
class GeminiPlanner:                        # Planner 구현
    MODEL = "gemini-flash-latest"           # ← 이 도메인만의 모델 선택
    def plan(self, article: Article) -> VideoPlan:
        model = genai.GenerativeModel(self.MODEL,
            system_instruction=load_prompt("shorts_planning"),
            generation_config={"temperature": 0.7, "response_mime_type": "application/json"})
        raw = json.loads(model.generate_content(article.content).text)
        return VideoPlan(scenes=[Scene(**s) for s in raw["scenes"]])

# planning/__init__.py — 기본 결선(파사드). 바깥은 이것만 본다
from app.services.planning.service import generate_video_plan as _run
from app.services.planning.adapters.gemini import GeminiPlanner
def generate_video_plan(article):
    return _run(article, planner=GeminiPlanner())   # ← 어댑터 교체는 이 한 줄
```

---

## 8. 도메인 간 계약 (Shared Kernel)

도메인 사이를 오가는 데이터는 **공유 계약 모듈** 하나에 둔다. 도메인은 서로를 import 하지 않고 *계약만* 공유한다(결합 제거).

```python
# services/contracts.py  (pydantic BaseModel)
class Article(BaseModel):       title: str; content: str; source: str | None = None
class Scene(BaseModel):         scene_number: int; narration: str; image_prompt: str
class VideoPlan(BaseModel):     scenes: list[Scene]
class SceneAsset(BaseModel):    scene_number: int; image_path: str; audio_path: str; narration: str
class RenderedVideo(BaseModel): path: str
```

### 데이터 흐름
```
URL│검색어 ─[sourcing]→ Article ─[planning]→ VideoPlan ─[media]→ list[SceneAsset] ─[assembly]→ RenderedVideo
```

> dict 대신 타입 모델을 계약으로 쓰면, 한 도메인이 출력 모양을 바꿀 때 변화가 코드(타입)로 드러나 옆 도메인을 조용히 깨뜨리지 못한다.

---

## 9. 오케스트레이션 (services/tasks.py)

Celery 워커 진입점. **도메인 파사드를 순서대로 호출하고 진행률만 보고**한다. 도메인 내부(어댑터·모델·프롬프트) 변경에 **불변**(요구사항 3).

```python
from app.services import sourcing, planning, media, assembly   # 도메인 파사드만

@celery_app.task(bind=True)
def generate_video_task(self, project_id: str, source: str):
    article = sourcing.fetch(source)                   # [1] 수집 (URL/검색어)
    plan    = planning.generate_video_plan(article)    # [2] 기획
    assets  = media.generate_assets(project_id, plan)  # [3] 에셋
    video   = assembly.merge_video(project_id, assets) # [4] 합성
    return {"status": "success", "final_video_path": video.path, "project_id": project_id}
```

tasks는 포트·어댑터·SDK를 **모른다.** 파사드 시그니처만 안다. 진행률 보고(`update_state`)는 생략 표기.

---

## 10. 목표 디렉토리 구조

```
app/services/
├── __init__.py              # 패키지 파사드: 도메인 4종 노출
├── contracts.py             # 공유 계약 (도메인 간 DTO)        ← 신규
├── tasks.py                 # 오케스트레이션 (Celery 경계)
│
├── sourcing/                # 수집 — 크롤링/검색 교체 지점
│   ├── __init__.py · service.py · ports.py
│   └── adapters/ selenium.py            (→ search_api.py · web_search.py)
│
├── planning/                # 기획 — LLM·프롬프트 도메인 로컬
│   ├── __init__.py · service.py · ports.py
│   ├── prompts/ shorts_planning.yaml
│   └── adapters/ gemini.py              (→ openai.py)
│
├── media/                   # 에셋 — 이미지·음성 각각 독립 교체
│   ├── __init__.py · service.py · ports.py
│   └── adapters/ pollinations.py · edge_tts.py
│
└── assembly/                # 합성
    ├── __init__.py · service.py · ports.py
    └── adapters/ moviepy.py             (→ ffmpeg.py)
```

---

## 11. 변경 시나리오 플레이북 ⭐

MVP의 실질 가치. "이걸 바꾸려면 어디만 건드리고, 어디는 절대 안 건드리는가."

| 바꾸고 싶은 것 | 건드리는 곳 | 보장: 안 건드리는 곳 |
|---|---|---|
| 크롤링 → 검색 API | `sourcing/adapters/search_api.py` 추가 + `__init__` 결선 1줄 | planning·media·assembly·tasks·contracts |
| LLM Gemini → OpenAI | `planning/adapters/openai.py` 추가 + 결선 1줄 | 다른 도메인·tasks·프롬프트 |
| 기획 프롬프트 튜닝 | `planning/prompts/*.yaml` (데이터만) | **코드 전부** |
| 이미지 Pollinations → SD | `media/adapters/stable_diffusion.py` + 결선 | 음성 어댑터·다른 도메인·tasks |
| TTS Edge → ElevenLabs | `media/adapters/elevenlabs.py` + 결선 | 이미지 어댑터·다른 도메인·tasks |
| 렌더 MoviePy → ffmpeg | `assembly/adapters/ffmpeg.py` + 결선 | 다른 도메인·tasks |
| 단계 추가(예: 배경음악) | 새 도메인 폴더 + `tasks.py`에 호출 1줄 | 기존 도메인 내부 |
| 작업 순서·재시도 변경 | `tasks.py` 만 | 도메인 전부 |
| 계약 변경(예: Scene 필드 추가) | `contracts.py` + 해당 도메인 | 무관 도메인(타입체크로 누락 즉시 발견) |

원칙: **교체는 `adapters/`에 추가 + 파사드 결선 한 줄.** 시그니처(포트·파사드·계약)가 유지되는 한 파급은 0이다.

---

## 12. 테스트 전략

| 층 | 대상 | 방법 | 외부 호출 |
|---|---|---|---|
| 단위 | `service.py` 도메인 규칙 | 포트에 **가짜 어댑터(Fake)** 주입 | 없음 |
| 계약 | 각 `adapter` ↔ 포트 시그니처 | 어댑터가 포트 형태로 입출력하는지 | 실제/모킹 |
| 통합 | `tasks` 전체 흐름 | 파사드를 가짜로 바꿔 순서·전달 검증 | 없음(또는 e2e 별도) |

핵심: 도메인 로직은 어댑터 없이 테스트된다. `generate_video_plan(article, planner=FakePlanner())`.

---

## 13. 명명 규칙

- **도메인 폴더** = 도메인 명사: `sourcing`·`planning`·`media`·`assembly`.
- **포트** = 능력 인터페이스: `ArticleSource`·`Planner`·`ImageGenerator`·`VoiceSynthesizer`·`VideoComposer`.
- **어댑터 파일** = 공급자/기술 이름: `selenium.py`·`gemini.py`·`pollinations.py`·`edge_tts.py`·`moviepy.py`.
- **파사드 함수** = 도메인 동사: `fetch`·`generate_video_plan`·`generate_assets`·`merge_video`.
- **프롬프트 파일** = `<용도>.yaml`, 로더 `load_prompt("<용도>")`. 도메인 로컬.

---

## 14. 현재 → 목표 매핑 · 점진 채택

| 현재(단계 기준) | 목표(도메인 기준) |
|---|---|
| `crawler/extractor.py` | `sourcing/`(service·ports·adapters/selenium) |
| `ai/planner.py` + `prompts/` | `planning/`(+ prompts 로컬) |
| `image/generator.py` | `media/`(adapters/pollinations·edge_tts, 포트 2개) |
| `video/editor.py` | `assembly/`(adapters/moviepy) |
| `__init__.py` · `tasks.py` | 유지(호출 대상만 도메인 파사드로) |
| — | `contracts.py` 신규(dict → 타입 모델) |

**점진 채택**: 한 번에 다 만들지 않는다. **가변성 큰 순서**로 도입 — ① sourcing(곧 검색 교체) → ② planning(모델/프롬프트 잦은 변경) → ③ media → ④ assembly(가장 안정적). 각 단계는 파사드 시그니처를 유지하면 tasks·타 도메인 무영향.

---

## 15. 아키텍처 결정 기록 (ADR)

- **ADR-1 포트 & 어댑터 채택** — MVP라 외부 공급자 4/5가 가변. 교체성을 1순위로. *비용*(파일·간접층 증가)은 가변성 높은 도메인부터 점진 적용으로 상쇄.
- **ADR-2 AI를 도메인 로컬로** — 전역 `ai/`·`prompts/` 폐지. 도메인이 모델·프롬프트 소유 → 독립 변경.
- **ADR-3 공유 계약 모듈(`contracts.py`)** — 도메인 간 직접 import 금지, 계약만 공유. 5개 내외 DTO라 단일 모듈로 충분.
- **ADR-4 오케스트레이션은 파사드만 의존** — 도메인 내부 교체가 tasks로 번지지 않게.
- **ADR-5 `pipeline` 명칭 배제** — CI/CD와 충돌. `services/`를 도메인 홈으로.

---

## 16. 횡단 관심사 · 후속

- **공통 작업물 경로**: `"temp_projects"` 가 3곳(`main.py` static·media·assembly)에 흩어짐, `video/editor.py`의 `BASE_DIR`는 죽은 코드. → `core/config.settings.WORKSPACE_DIR` 한 곳으로 통일.
- **설정/시크릿**: API 키·모델명·경로는 `core/config`(또는 도메인 로컬 설정). 어댑터가 읽는다.
- **에러·재시도**: 어댑터(저수준 재시도) + tasks(단계 재시도) 이층 분리. 보상 트랜잭션은 후속.
- **문서 정합성**: 현재 프로젝트 현황은 `../current/ARCHITECTURE.md`, 폴더 분할 기록은 `ARCHITECTURE_PLAN_v1.md`, 목표 설계는 본 문서, 구현 청사진은 `ARCHITECTURE_PLAN_v3.md`가 맡는다. 안정화되면 통합 검토.
