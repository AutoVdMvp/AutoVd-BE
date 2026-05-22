# AutoVd-BE

AutoVd-BE는 영상 콘텐츠 제작을 위한 AI 생성 백엔드입니다. 현재 MVP는 FastAPI 기반으로 프롬프트 템플릿을 YAML로 관리하고, Jinja2로 런타임 변수를 렌더링한 뒤, AI Provider 추상화를 통해 텍스트 생성 API로 전달하는 구조를 제공합니다.

## 주요 기능

- YAML 기반 프롬프트 템플릿 관리
- Jinja2 기반 프롬프트 변수 렌더링
- 프롬프트 목록 조회 및 렌더링 테스트 API
- AI Provider 추상화 계층
- 실제 외부 API 호출 전 개발/테스트를 위한 Stub Provider
- 이미지 생성용 프롬프트 생성 API

## 아키텍처

```txt
FastAPI Router
  -> GenerationService
    -> PromptService
      -> PromptRegistry
      -> PromptRenderer
    -> AIService
      -> StubProvider
```

현재 Provider는 Gemini 이름으로 등록되어 있지만 실제 Gemini API를 호출하지 않고 `StubProvider`가 JSON 형태의 더미 응답을 반환합니다. 이후 `GeminiProvider`, `OpenAIProvider`, `OpenRouterProvider`를 추가하더라도 `GenerationService`의 변경을 최소화할 수 있도록 분리되어 있습니다.

## 프로젝트 구조

```txt
app/
  main.py
  api/
    dependencies.py
    v1/
      router.py
      endpoints/
        generation.py
        prompts.py
  prompts/
    prompt_registry.py
    prompt_renderer.py
    prompt_service.py
    prompt_types.py
    templates/
      image_prompt_generate.yaml
  ai/
    ai_service.py
    providers/
      base.py
      stub_provider.py
  generation/
    generation_service.py
tests/
```

## 실행 준비

이 프로젝트는 `uv`를 기준으로 실행합니다.

```bash
uv sync
```

## 개발 서버 실행

```bash
uv run uvicorn app.main:app --reload
```

서버 실행 후 기본 API prefix는 `/api/v1`입니다.

## 테스트

```bash
uv run pytest
```

## MVP API

### 프롬프트 목록 조회

```http
GET /api/v1/prompts
```

등록된 YAML 프롬프트 템플릿 목록을 반환합니다.

### 프롬프트 렌더링

```http
POST /api/v1/prompts/render
```

요청 예시:

```json
{
  "prompt_id": "image.prompt.generate",
  "variables": {
    "scene_description": "노인이 복지관에서 상담을 받는 장면",
    "character_name": "김영수",
    "character_appearance": "70대 남성, 회색 머리, 따뜻한 인상",
    "character_personality": "차분하고 신중함",
    "style_name": "따뜻한 동화풍",
    "style_prompt": "soft children book illustration, warm pastel colors",
    "negative_prompt": "horror, violent, sexual, distorted face"
  }
}
```

### 이미지 프롬프트 생성

```http
POST /api/v1/generation/image-prompt
```

요청 예시:

```json
{
  "scene_description": "노인이 복지관에서 상담을 받는 장면",
  "character": {
    "name": "김영수",
    "appearance_prompt": "70대 남성, 회색 머리, 따뜻한 인상",
    "personality_prompt": "차분하고 신중함"
  },
  "style": {
    "name": "따뜻한 동화풍",
    "style_prompt": "soft children book illustration, warm pastel colors",
    "negative_prompt": "horror, violent, sexual, distorted face"
  }
}
```

현재 응답의 `raw_result`는 Stub Provider가 생성한 JSON 문자열입니다.

## 다음 개발 단계

- 실제 Gemini Provider 구현
- 생성 결과 JSON 파싱 및 응답 타입 정규화
- 프로젝트, 캐릭터, 스타일 도메인 모델 추가
- GenerationJob 및 UsageLog DB 저장
- API 예외 처리 공통화
