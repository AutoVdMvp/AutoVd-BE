from sqlalchemy import Column, String, ForeignKey, DateTime, func, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from app.db.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, index=True, nullable=False)
    nickname = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationship Setup
    projects = relationship("Project", back_populates="owner")

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))

    # 기사 link
    original_url = Column(String, nullable=True)

    # pending, processing, completed
    status = Column(String, default="pending")

    # 최종 완성된 비디오 접근 링크를 저장할 컬럼
    vd_url = Column(String, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="projects")
    scenes = relationship("Scene", back_populates="project", cascade="all, delete-orphan")

class Scene(Base):
    __tablename__ = "scenes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))

    # Scene 순서
    scene_order = Column(Integer, nullable=False)

    # AI가 생성한 Narration, Visual Prompt 등 저장
    content = Column(JSONB, default={})
    
    # 생성된 Image URL, TTS URL, Duration 저장
    assets = Column(JSONB, default={})

    status = Column(String, default="pending")

    project = relationship("Project", back_populates="scenes")