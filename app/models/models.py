"""
SQLAlchemy ORM 데이터베이스 모델 정의 모듈

데이터베이스 테이블 구조를 Python 클래스로 정의합니다.

테이블 관계:
    User (1) ──< Project (1) ──< Scene (N)
    - 하나의 User는 여러 Project를 가질 수 있음
    - 하나의 Project는 여러 Scene으로 구성됨
    - User 삭제 시 관련 Project 모두 삭제 (CASCADE)
    - Project 삭제 시 관련 Scene 모두 삭제 (CASCADE)
"""

from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base


class User(Base):
    """
    사용자 테이블 (users).

    Google OAuth2 로그인 시 자동으로 생성됩니다.
    """

    __tablename__ = "users"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )  # 자동 생성 UUID PK
    email = Column(
        String, unique=True, index=True, nullable=False
    )  # 구글 계정 이메일 (유일)
    nickname = Column(String)  # 구글 계정 표시 이름
    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # 가입 일시 (DB 자동 설정)

    # 이 User에 속한 Project 목록 (양방향 관계)
    projects = relationship("Project", back_populates="owner")


class Project(Base):
    """
    영상 생성 프로젝트 테이블 (projects).

    사용자가 기사 URL을 등록하면 생성되며,
    영상 생성 진행 상태와 완성된 영상 URL을 관리합니다.
    """

    __tablename__ = "projects"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )  # 자동 생성 UUID PK
    user_id = Column(  # 소유자 User FK
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )

    original_url = Column(String, nullable=True)  # 영상 원본이 되는 뉴스 기사 URL

    # 프로젝트 상태:
    #   pending    - 생성 대기 중
    #   processing - 영상 생성 중 (Celery Task 실행 중)
    #   completed  - 영상 생성 완료
    status = Column(String, default="pending")

    vd_url = Column(
        String, nullable=True
    )  # 완성된 영상 파일 접근 URL (생성 전에는 None)

    created_at = Column(
        DateTime(timezone=True), server_default=func.now()
    )  # 프로젝트 생성 일시

    # 양방향 관계: Project ↔ User, Project ↔ Scene
    owner = relationship("User", back_populates="projects")
    scenes = relationship(
        "Scene", back_populates="project", cascade="all, delete-orphan"
    )


class Scene(Base):
    """
    영상 씬(장면) 테이블 (scenes).

    하나의 Project는 여러 Scene으로 구성됩니다.
    각 Scene은 AI가 생성한 나레이션, 이미지 프롬프트, 그리고
    실제 생성된 TTS 오디오 / 이미지 파일 경로를 저장합니다.
    """

    __tablename__ = "scenes"

    id = Column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )  # 자동 생성 UUID PK
    project_id = Column(  # 소속 Project FK
        UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE")
    )

    scene_order = Column(Integer, nullable=False)  # 영상 내 씬 순서 (1, 2, 3 ...)

    # AI가 생성한 씬 기획 정보 (JSONB)
    # 예시: {"narration": "오늘 가장 화제가...", "image_prompt": "A cinematic shot..."}
    content = Column(JSONB, default={})

    # 생성된 미디어 Asset 경로 정보 (JSONB)
    # 예시: {"audio_path": "temp_projects/.../scene_1.mp3", "image_path": "...scene_1.jpg"}
    assets = Column(JSONB, default={})

    status = Column(String, default="pending")  # 씬 처리 상태 (pending / completed)

    project = relationship("Project", back_populates="scenes")
