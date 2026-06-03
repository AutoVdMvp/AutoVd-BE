# AutoVd-BE 현재 아키텍처

> 버전: 1.3 · 최종 갱신: 2026-06-04 · 브랜치: `dev/ai` · 상태: **현재 현황 (Current / Source of Truth)**
> 문서 역할: 이 문서는 현재 프로젝트 코드와 운영 구성을 설명하는 기준 문서다. 계획/이력/버전 관리 문서는 아래 "문서 체계"를 따른다.

## 문서 체계

`docs/`의 기준 문서는 다음처럼 구분한다.

| 문서 | 역할 | 현재 코드 반영 여부 |
|------|------|------------------|
| [`current/ARCHITECTURE.md`](./ARCHITECTURE.md) | 현재 프로젝트 아키텍처 현황의 단일 기준 문서 | 현재 코드 기준 |
| [`plans/ARCHITECTURE_PLAN_v3.md`](../plans/ARCHITECTURE_PLAN_v3.md) | 목표 설계를 현재 코드에 적용하기 위한 구현 청사진 | 향후 계획 |
| [`governance/DOCUMENT_VERSION_CONTROL.md`](../governance/DOCUMENT_VERSION_CONTROL.md) | 문서 분류, 메타데이터, 버전 관리 규칙 | 관리 규칙 |

새로 온 독자는 먼저 이 문서를 읽어 현재 상태를 파악하고, 리팩토링 의도와 변경 순서는 `plans/`의 계획 문서를 참고한다.

## 프로젝트 개요

**뉴스 기사 URL을 입력받아 AI가 자동으로 유튜브 쇼츠(Shorts) 영상을 생성하는 백엔드 서비스**

기사 크롤링 → AI 영상 기획 → TTS/이미지 자산 생성 → 영상 합성까지의 전 과정을 자동화한다.

---

## 기술 스택

| 분류 | 기술 | 버전 |
|------|------|------|
| 웹 프레임워크 | FastAPI | >= 0.111.0 |
| 비동기 런타임 | Uvicorn | >= 0.29.0 |
| 데이터 검증 | Pydantic v2 + pydantic-settings | >= 2.7.1 |
| ORM / DB | SQLAlchemy (async) + asyncpg | >= 2.0.30 |
| 마이그레이션 | Alembic | >= 1.13.1 |
| DB | PostgreSQL 15 | - |
| 비동기 작업 큐 | Celery + Redis | >= 5.4.0 / >= 5.0.4 |
| 토큰 저장소 | Redis (refresh token 중앙 관리) | 7-alpine |
| AI (영상 기획) | Google Gemini (`gemini-flash-latest`) | >= 0.5.2 |
| TTS | Microsoft Edge TTS (`ko-KR-SunHiNeural`) | >= 6.1.9 |
| 이미지 생성 | Pollinations.AI (무료 외부 API) | - |
| 영상 편집 | MoviePy 1.x + FFmpeg | 1.x 고정 |
| 크롤링 | Selenium (headless Chrome) + webdriver-manager | >= 4.20.0 |
| HTML 파싱 | BeautifulSoup4 | >= 4.12.3 |
| 인증 | Google OAuth2 + Kakao OAuth2 + JWT (PyJWT, HS256) | - |
| 인프라 | Docker Compose | - |

---

## 디렉토리 구조

```
AutoVd-BE/
├── app/
│   ├── main.py                  # FastAPI 앱 진입점, CORS/StaticFiles, 라우터 등록, lifespan
│   ├── api/
│   │   ├── auth.py              # Google/Kakao OAuth2 로그인 → JWT 발급, refresh/logout
│   │   ├── deps.py              # Bearer JWT 검증 및 현재 사용자 조회 의존성
│   │   ├── projects.py          # 프로젝트 생성(/create). 그 외 엔드포인트는 주석 처리됨
│   │   ├── users.py             # 현재 로그인 사용자 조회(/me)
│   │   └── video.py             # 영상 생성/상태/목록 API (현재 메인 영상 라우터)
│   ├── core/
│   │   ├── config.py            # 환경변수 로딩 (pydantic-settings, .env)
│   │   ├── security.py          # JWT access(60분)/refresh(7일) 토큰 생성, Redis 저장
│   │   └── celery_app.py        # Celery 인스턴스 및 브로커 설정
│   ├── db/
│   │   ├── database.py          # 비동기 DB 엔진, 세션 팩토리, get_db 의존성
│   │   └── redis_client.py      # refresh token 저장/조회용 비동기 Redis 클라이언트
│   ├── models/
│   │   └── models.py            # SQLAlchemy ORM 모델 (User, Project, Scene)
│   ├── schemas/
│   │   ├── auth.py              # 인증 요청/응답 스키마 (Google/Token/Refresh)
│   │   ├── response.py          # 공통 응답 래퍼 (CommonResponse[T])
│   │   └── user.py              # 사용자 응답 스키마
│   └── services/
│       ├── asset_generator.py   # TTS 음성 + AI 이미지 생성 및 파일 저장
│       ├── crawler.py           # Selenium 뉴스 크롤러
│       ├── llm.py               # Gemini API 호출, Scene 기획 생성
│       ├── tasks.py             # Celery 비동기 파이프라인 태스크
│       └── video_editor.py      # MoviePy 영상 합성 (이미지 + 음성 + 자막)
├── docs/
│   ├── README.md                # docs/ 문서 안내
│   ├── current/
│   │   ├── README.md
│   │   └── ARCHITECTURE.md      # (본 문서) 현재 프로젝트 기준 문서
│   ├── plans/
│   │   ├── README.md
│   │   ├── ARCHITECTURE_PLAN_v1.md
│   │   ├── ARCHITECTURE_PLAN_v2.md
│   │   └── ARCHITECTURE_PLAN_v3.md
│   └── governance/
│       ├── README.md
│       └── DOCUMENT_VERSION_CONTROL.md
├── test_ai.py                   # Gemini API 키/사용 가능 모델 점검용 단독 스크립트
├── docker-compose.yml           # PostgreSQL + Redis + API 서버 + Celery 워커
├── Dockerfile                   # 컨테이너 이미지 빌드
├── requirements.txt             # Python 의존성
├── README.md
└── .env.example                 # 환경변수 예시

⚠️ 현재 코드상 즉시 확인되는 기동 차단 요소:
    app/services/crawler.py      # 첫 줄 `wimport time` 구문 오류로 import 시 SyntaxError 발생
```

---

## 데이터베이스 모델

```
User  (테이블: users)
├── id          UUID (PK)
├── email       String (unique, indexed, not null)
├── nickname    String
└── created_at  DateTime (server_default now)

Project  (테이블: projects)
├── id           UUID (PK)
├── user_id      UUID (FK → users.id, CASCADE)
├── original_url String (기사 URL, nullable)
├── status       String (default "pending": "pending" | "processing" | "completed")
├── vd_url       String (완성된 영상 접근 링크, nullable)
└── created_at   DateTime (server_default now)

Scene  (테이블: scenes)   ※ 모델은 정의되어 있으나 파이프라인에서 아직 저장하지 않음
├── id           UUID (PK)
├── project_id   UUID (FK → projects.id, CASCADE)
├── scene_order  Integer (not null)
├── content      JSONB  { narration, image_prompt, ... }  (default {})
├── assets       JSONB  { audio_path, image_path, ... }    (default {})
└── status       String (default "pending")
```

관계: `User 1 ↔ N Project` (back_populates="owner"), `Project 1 ↔ N Scene` (cascade all, delete-orphan)

---

## API 엔드포인트

Base prefix: `/api/v1` (`settings.API_PREFIX`)

| Method | Path | 라우터 | 설명 |
|--------|------|--------|----|
| GET | `/` | main | Health Check |
| POST | `/api/v1/auth/google` | auth | Google ID Token 검증 → access/refresh 발급 |
| GET | `/api/v1/auth/kakao/login` | auth | Kakao 인가 코드 요청 리다이렉트 |
| GET | `/api/v1/auth/kakao/callback` | auth | Kakao 콜백 → 토큰 교환 → 유저 처리 → JWT 발급 |
| POST | `/api/v1/auth/refresh` | auth | Refresh Token 검증(Redis 대조) → 새 access 발급 |
| POST | `/api/v1/auth/logout` | auth | Redis의 refresh token 삭제 |
| GET | `/api/v1/users/me` | users | Bearer access token 검증 → 현재 사용자 정보 반환 |
| POST | `/api/v1/projects/create` | projects | 프로젝트(기사 URL) 등록 → project_id 발급 |
| POST | `/api/v1/prompt/remake_video` | video | 영상 생성 시작 (Celery 태스크 dispatch) |
| GET | `/api/v1/prompt/status?id={task_id}` | video | Celery 작업 진행 상태 조회 |
| GET | `/api/v1/vd/list?userId={uuid}` | video | 유저의 영상 목록 조회 |

> `/api/v1/users/me`는 `app/api/deps.py`의 `get_current_user`를 통해 Bearer access token을 검증한다.

### 영상 라우터 공통 응답 형식 (`CommonResponse[T]`)

`/projects/create`, `video.py`의 엔드포인트가 사용한다.

```json
{
  "status": 200,
  "message": "설명 메시지",
  "data": { ... }
}
```

### 인증 응답 형식 (`TokenResponse`)

`auth.py`는 위 래퍼 대신 토큰 객체를 직접 반환한다.

```json
{
  "access_token": "...",
  "refresh_token": "...",
  "token_type": "bearer"
}
```

---

## 영상 생성 파이프라인

영상 생성은 Celery 비동기 태스크(`generate_video_task`)로 처리된다. 사전에 `/projects/create`로 프로젝트(기사 URL)를 등록한 뒤, `project_id`로 `/prompt/remake_video`를 호출한다.

```
POST /api/v1/prompt/remake_video  (body: { id: project_id })
        │  DB에서 project_id로 기사 URL 조회 → status="processing" 갱신
        ▼
[Celery 태스크 dispatch] ──────────────────────────────────┐
        │                                                   │
        ▼                                              Redis (브로커)
[1] 기사 크롤링 (10%)                                       │
    Selenium headless Chrome (--no-sandbox)                │
    → 제목 + 본문 추출, 노이즈 제거                           │
        │                                                   │
        ▼                                             Celery Worker
[2] AI 영상 기획 (30%)
    Gemini gemini-flash-latest (response_mime_type=json)
    → 씬별 { scene_number, narration, image_prompt } JSON 생성
        │  (대본은 1문장 = 1씬, 씬 개수 제한 없음)
        ▼
[3] 미디어 자산 생성 (60%)
    ├── Edge TTS → scene_N.mp3 (ko-KR-SunHiNeural)
    └── Pollinations.AI → scene_N.jpg (1080×1920, 최대 3회 재시도)
        │
        ▼
[4] 영상 합성 (80%)
    MoviePy
    ├── 이미지 클립 (음성 길이만큼)
    ├── 자막 클립 (TextClip, caption, 하단 65% 위치)
    └── 음성 병합 → concatenate → MP4 렌더링
        │
        ▼
[완료] temp_projects/{project_id}/{project_id}_final.mp4
```

- **씬 간 딜레이**: 이미지 생성 API 부하 방지를 위해 씬당 3초 대기(`time.sleep(3)`)
- **상태 조회**: `GET /prompt/status?id={task_id}`가 Celery state(`PROGRESS`/`SUCCESS`/`FAILURE`)를 반환. `SUCCESS` 시 `Project.status="completed"`, `vd_url`을 DB에 갱신한다.
- **결과 제공**: 완성 영상은 `app.mount("/static", ...)`를 통해 `http://localhost:8000/static/{파일명}`으로 서빙된다.

---

## 인증 흐름

### Google 로그인

```
클라이언트 (Google 로그인)
        │ Google ID Token (credential)
        ▼
POST /api/v1/auth/google
        │ google-auth로 토큰 검증 (settings.GOOGLE_CLIENT_ID)
        ▼
User 조회 (email 기준) → 없으면 신규 생성
        ▼
access_token (HS256, sub=user_id, 60분) + refresh_token (7일)
        │ refresh_token은 Redis `refresh_token:{user_id}`에 TTL 저장
        ▼
클라이언트에 { access_token, refresh_token } 반환
```

### Kakao 로그인

```
GET /api/v1/auth/kakao/login → 카카오 인가 페이지로 RedirectResponse
        ▼
GET /api/v1/auth/kakao/callback?code=...
        │ 인가 코드 → access token 교환 → 사용자 정보 조회 (requests)
        │ email 없으면 kakao_{id}@kakao.dummy.com 으로 대체
        ▼
User 조회/생성 → access/refresh 발급 (Google과 동일)
```

### 토큰 재발급 / 로그아웃

- `POST /auth/refresh`: refresh token 서명 검증 후 **Redis에 저장된 값과 일치하는지 대조**. 일치하지 않거나 없으면 거부(폐기된 토큰 차단). 통과 시 새 access token 발급.
- `POST /auth/logout`: Redis에서 `refresh_token:{user_id}` 삭제.
- `GET /users/me`: access token의 `sub` claim을 사용자 ID로 해석해 DB에서 현재 사용자를 조회한다.

---

## 인프라 구성 (Docker Compose)

```
┌──────────────────────────────────────────────────────────┐
│                      Docker Network                        │
│                                                            │
│  ┌──────────────┐        ┌──────────────┐                  │
│  │ db           │        │ redis        │                  │
│  │ postgres:15  │        │ redis:7      │                  │
│  │   :5432      │        │   :6379      │                  │
│  └──────┬───────┘        └──────┬───────┘                  │
│         │                       │                          │
│  ┌──────┴───────────┐    ┌──────┴────────────────────────┐ │
│  │ api              │    │ worker                        │ │
│  │ FastAPI :8000    │    │ celery -P threads             │ │
│  │ (uvicorn)        │    │ --concurrency=1, shm 2gb      │ │
│  └──────────────────┘    └───────────────────────────────┘ │
│   depends_on: db, redis    depends_on: db, redis, api      │
└──────────────────────────────────────────────────────────┘
```

- DB 연결 풀: `pool_size=10`, `max_overflow=20` (`database.py`, `echo=True`)
- Celery 브로커/백엔드: `redis://redis:6379/0` (`CELERY_BROKER_URL`)
- 워커 풀: `threads` (MoviePy/FFmpeg 동기 작업 고려), `--concurrency=1`, `shm_size: 2gb`
- 코드는 `volumes: .:/app`로 마운트 (개발 모드)

---

## 환경변수

| 변수명 | 필수 | 설명 |
|--------|:---:|------|
| `PROJECT_NAME` | ✅ | API 프로젝트 이름 |
| `VERSION` | ✅ | API 버전 |
| `API_PREFIX` | ✅ | URL prefix (예: `/api/v1`) |
| `DATABASE_URL` | ✅ | PostgreSQL 연결 문자열 (asyncpg) |
| `JWT_SECRET_KEY` | ✅ | JWT 서명 키 (HS256) |
| `JWT_ALGORITHM` | ✅ | JWT 알고리즘 (예: `HS256`) |
| `LLM_API_KEY` | ✅ | LLM API 키 |
| `GEMINI_API_KEY` | ✅ | Google Gemini API 키 |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` / `GOOGLE_REDIRECT_URI` | ⬜ | Google OAuth (없으면 `None`) |
| `KAKAO_CLIENT_ID` / `KAKAO_CLIENT_SECRET` / `KAKAO_REDIRECT_URI` | ⬜ | Kakao OAuth (없으면 `None`) |
| `REDIS_URL` | ⬜ | refresh token 저장용 Redis URL (기본값 `redis://redis:6479/0` — 포트 오타 추정) |
| `CELERY_BROKER_URL` / `CELERY_RESULT_BACKEND` | ⬜ | Celery용 (compose에서 주입, 기본 `redis://redis:6379/0`) |

> `.env.example`에는 현재 Core/DB/JWT/AI 키만 들어 있고 **`GOOGLE_*`, `KAKAO_*`, `REDIS_URL`이 누락**되어 있어 OAuth/토큰 기능 사용 시 별도 추가가 필요하다.

---

## 알려진 문제점 및 개선 필요 사항

### 🔴 치명적 (현재 기동/실행 차단)

| 위치 | 문제 | 내용 |
|------|------|------|
| `app/services/crawler.py:1` | 구문 오류 | `wimport time`으로 시작해 `app.services.crawler` import 시 SyntaxError 발생 |
| `config.py` (`REDIS_URL`) | 기본 포트 오타 추정 | 기본값 `redis://redis:6479/0` — Redis 표준 포트는 `6379` |

### 🟡 구조적 개선 사항 (유효)

| 항목 | 현황 | 개선 방향 |
|------|------|-----------|
| Scene DB 미저장 | `tasks.py`가 생성한 씬 데이터를 `Scene` 테이블에 저장하지 않음 | 파이프라인에 Scene 저장 로직 추가 |
| `projects.py` 죽은 코드 | `/generate`, `/tasks/{id}` 등 대부분 주석 처리되어 `/create`만 활성 | 정리 또는 `video.py`와 책임 정리 |
| 보호 API 적용 범위 제한 | `get_current_user`는 구현됐지만 현재 적용된 엔드포인트는 `/users/me` 중심 | 사용자별 프로젝트/영상 API에도 인증 의존성 적용 검토 |
| 임시 파일 관리 없음 | `temp_projects/`가 무한 증가 | 완료 후 정리 로직 또는 오브젝트 스토리지(S3 등) 연동 |
| 영상 URL 하드코딩 | `video.py`가 `http://localhost:8000/static/...`로 고정 | 환경변수 기반 베이스 URL 구성 |
| 작업물 경로 불일치 | `asset_generator.py`는 절대 `BASE_DIR`, `video_editor.py`는 일부 상대경로 `"temp_projects"` 사용 | 설정 기반 작업 디렉토리로 통일 |
| `.env.example` 불완전 | OAuth/Redis 변수 누락 | 실제 `config.py` 항목과 동기화 |

### 🟢 이전 문서 대비 해결된 항목 (참고)

| 위치 | 과거 문제 | 현재 상태 |
|------|-----------|-----------|
| `app/api/users.py` | 파일 부재로 users 라우터 ImportError | 파일 추가됨. `/api/v1/users/me` 제공 |
| `app/db/redis_client.py` | 파일 부재로 Redis client ImportError | 파일 추가됨. `settings.REDIS_URL` 기반 async Redis 클라이언트 제공 |
| `app/api/deps.py` | JWT 검증 의존성 부재 | `get_current_user` 구현됨 |
| `asset_generator.py` | URL 파라미터 오타 `%seed=` | `&seed=`로 수정됨 |
| `auth.py` | `GOOGLE_CLIENT_ID` 하드코딩 | `settings.GOOGLE_CLIENT_ID`로 이동 |
| `security.py` | `Settings.JWT_SECRET_KEY` 미사용 | `settings.JWT_SECRET_KEY`로 수정 |
| `video_editor.py` | 폰트 경로 Windows 절대경로 고정 | `os.name` 분기 (Windows malgun / Linux NanumGothic) |
| `video.py` | 레거시/미사용 라우터 | 현재 메인 영상 라우터로 활성화, Project DB 갱신 포함 |
