# AutoVd-BE 아키텍처 분석

## 프로젝트 개요

**뉴스 기사 URL을 입력받아 AI가 자동으로 유튜브 쇼츠(Shorts) 영상을 생성하는 백엔드 서비스**

기사 크롤링 → AI 영상 기획 → TTS/이미지 자산 생성 → 영상 합성까지의 전 과정을 자동화한다.

---

## 기술 스택

| 분류 | 기술 | 버전 |
|------|------|------|
| 웹 프레임워크 | FastAPI | >= 0.111.0 |
| 비동기 런타임 | Uvicorn | >= 0.29.0 |
| 데이터 검증 | Pydantic v2 | >= 2.7.1 |
| ORM / DB | SQLAlchemy (async) + asyncpg | >= 2.0.30 |
| 마이그레이션 | Alembic | >= 1.13.1 |
| DB | PostgreSQL 15 | - |
| 비동기 작업 큐 | Celery + Redis | >= 5.4.0 / >= 5.0.4 |
| AI (영상 기획) | Google Gemini (`gemini-flash-latest`) | >= 0.5.2 |
| TTS | Microsoft Edge TTS (`ko-KR-SunHiNeural`) | >= 6.1.9 |
| 이미지 생성 | Pollinations.AI (무료 외부 API) | - |
| 영상 편집 | MoviePy 1.x + FFmpeg | 1.x 고정 |
| 크롤링 | Selenium (headless Chrome) + webdriver-manager | >= 4.20.0 |
| 인증 | Google OAuth2 + JWT (PyJWT, HS256) | - |
| 인프라 | Docker Compose | - |

---

## 디렉토리 구조

```
AutoVd-BE/
├── app/
│   ├── main.py                  # FastAPI 앱 진입점, 라우터 등록, lifespan 이벤트
│   ├── api/
│   │   ├── auth.py              # Google OAuth2 로그인 → JWT 발급
│   │   ├── projects.py          # 영상 생성/상태 조회/목록 API (메인)
│   │   └── video.py             # 레거시 영상 생성 API (mock project_id 사용, 미사용)
│   ├── core/
│   │   ├── config.py            # 환경변수 로딩 (pydantic-settings, .env)
│   │   ├── security.py          # JWT 토큰 생성 (7일 만료)
│   │   └── celery_app.py        # Celery 인스턴스 및 브로커 설정
│   ├── db/
│   │   └── database.py          # 비동기 DB 엔진, 세션 팩토리, get_db 의존성
│   ├── models/
│   │   └── models.py            # SQLAlchemy ORM 모델 (User, Project, Scene)
│   ├── schemas/
│   │   ├── auth.py              # 인증 요청/응답 스키마
│   │   └── response.py          # 공통 응답 래퍼 (CommonResponse[T])
│   └── services/
│       ├── crawler.py           # Selenium 뉴스 크롤러
│       ├── llm.py               # Gemini API 호출, Scene 기획 생성
│       ├── asset_generator.py   # TTS 음성 + AI 이미지 생성 및 파일 저장
│       ├── video_editor.py      # MoviePy 영상 합성 (이미지 + 음성 + 자막)
│       └── tasks.py             # Celery 비동기 파이프라인 태스크
├── docker-compose.yml           # PostgreSQL + Redis + API 서버 + Celery 워커
├── Dockerfile                   # 컨테이너 이미지 빌드
├── requirements.txt             # Python 의존성
└── .env.example                 # 환경변수 예시
```

---

## 데이터베이스 모델

```
User
├── id          UUID (PK)
├── email       String (unique, indexed)
├── nickname    String
└── created_at  DateTime

Project
├── id           UUID (PK)
├── user_id      UUID (FK → User, CASCADE)
├── original_url String (기사 URL)
├── status       String ("pending" | "processing" | "completed")
├── vd_url       String (완성된 영상 접근 링크)
└── created_at   DateTime

Scene
├── id           UUID (PK)
├── project_id   UUID (FK → Project, CASCADE)
├── scene_order  Integer
├── content      JSONB  { narration, image_prompt, ... }
├── assets       JSONB  { audio_path, image_path, duration, ... }
└── status       String ("pending" | "completed")
```

관계: `User 1 ↔ N Project`, `Project 1 ↔ N Scene`

---

## API 엔드포인트

Base prefix: `/api/v1`

| Method | Path | 설명 |
|--------|------|----|
| GET | `/` | Health Check |
| POST | `/auth/google` | Google ID Token 검증 → JWT 발급 |
| POST | `/projects/prompt/remake_video` | 영상 생성 시작 (Celery 태스크 dispatch) |
| GET | `/projects/prompt/status?id={task_id}` | Celery 작업 진행 상태 조회 |
| GET | `/projects/vd/list?userId={uuid}` | 유저의 영상 목록 조회 |

### 공통 응답 형식

```json
{
  "status": 200,
  "message": "설명 메시지",
  "data": { ... }
}
```

---

## 영상 생성 파이프라인

영상 생성은 Celery 비동기 태스크(`generate_video_task`)로 처리된다.

```
POST /projects/prompt/remake_video
        │
        ▼
[Celery 태스크 dispatch] ──────────────────────────────────┐
        │                                                   │
        ▼                                              Redis (브로커)
[1] 기사 크롤링 (10%)                                       │
    Selenium headless Chrome                               │
    → 제목 + 본문 추출, 노이즈 제거                           │
        │                                                   │
        ▼                                             Celery Worker
[2] AI 영상 기획 (30%)
    Gemini gemini-flash-latest
    → 씬별 { narration, image_prompt } JSON 생성
        │
        ▼
[3] 미디어 자산 생성 (60%)
    ├── Edge TTS → scene_N.mp3 (ko-KR-SunHiNeural)
    └── Pollinations.AI → scene_N.jpg (1080×1920)
        │
        ▼
[4] 영상 합성 (80%)
    MoviePy
    ├── 이미지 클립 (음성 길이만큼)
    ├── 자막 클립 (TextClip, 하단 65% 위치)
    └── 음성 병합 → concatenate → MP4 렌더링
        │
        ▼
[완료] temp_projects/{project_id}/{project_id}_final.mp4
```

**씬 간 딜레이**: 이미지 생성 API 부하 방지를 위해 씬당 5초 대기(`time.sleep(5)`)

---

## 인증 흐름

```
클라이언트 (Google 로그인)
        │ Google ID Token
        ▼
POST /api/v1/auth/google
        │ google-auth 라이브러리로 토큰 검증
        ▼
User 조회 (email 기준)
        │ 없으면 신규 생성 (소셜 로그인 방식)
        ▼
JWT 발급 (HS256, payload: { sub: user_id }, 7일 만료)
        │
        ▼
클라이언트에 access_token 반환
```

---

## 인프라 구성 (Docker Compose)

```
┌─────────────────────────────────────────────────┐
│                  Docker Network                  │
│                                                  │
│  ┌──────────┐     ┌──────────┐                   │
│  │PostgreSQL│     │  Redis   │                   │
│  │  :5432   │     │  :6379   │                   │
│  └────┬─────┘     └────┬─────┘                   │
│       │                │                         │
│  ┌────┴──────────┐  ┌──┴──────────┐              │
│  │  API 서버     │  │Celery Worker │              │
│  │  FastAPI:8000 │  │  (영상 처리)  │              │
│  └───────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────┘
```

DB 연결 풀: `pool_size=10`, `max_overflow=20`

---

## 환경변수

| 변수명 | 설명 |
|--------|------|
| `PROJECT_NAME` | API 프로젝트 이름 |
| `VERSION` | API 버전 |
| `API_PREFIX` | URL prefix (기본값: `/api/v1`) |
| `DATABASE_URL` | PostgreSQL 연결 문자열 (asyncpg) |
| `JWT_SECRET_KEY` | JWT 서명 키 (HS256) |
| `JWT_ALGORITHM` | JWT 알고리즘 (기본값: `HS256`) |
| `LLM_API_KEY` | LLM API 키 |
| `GEMINI_API_KEY` | Google Gemini API 키 |

---

## 알려진 문제점 및 개선 필요 사항

### 버그

| 위치 | 문제 | 내용 |
|------|------|------|
| `asset_generator.py:43` | URL 파라미터 오타 | `%seed=` → `&seed=` (URL 인코딩 오류) |
| `auth.py:14` | 하드코딩된 플레이스홀더 | `GOOGLE_CLIENT_ID`가 코드에 직접 기재됨, 환경변수로 이동 필요 |
| `security.py:18` | Settings 인스턴스 미사용 | `Settings.JWT_SECRET_KEY` → `settings.JWT_SECRET_KEY`로 수정 필요 |

### 구조적 개선 사항

| 항목 | 현황 | 개선 방향 |
|------|------|-----------|
| Scene DB 미저장 | 파이프라인에서 생성한 씬 데이터를 DB에 저장하지 않음 | `Scene` 테이블에 실제 저장 로직 추가 |
| 레거시 라우터 | `app/api/video.py`가 mock ID를 사용하는 구버전으로 방치 | 제거 또는 통합 |
| 폰트 경로 하드코딩 | `video_editor.py`에 Windows 절대경로 고정 | OS별 분기 또는 프로젝트 내 폰트 파일 번들링 |
| Project DB 업데이트 미완 | 영상 완성 후 `vd_url`, `status` 미갱신 | Celery 태스크 완료 시 DB 업데이트 로직 추가 |
| JWT 검증 미들웨어 부재 | 대부분의 API에 인증 미적용 | `Depends(get_current_user)` 의존성 추가 필요 |
| 임시 파일 관리 없음 | `temp_projects/` 폴더가 무한 증가 | 완료 후 정리 로직 또는 오브젝트 스토리지(S3 등) 연동 |
