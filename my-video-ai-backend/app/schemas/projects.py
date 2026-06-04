from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class ProjectResponse(BaseModel):
    id: UUID
    user_id: UUID
    original_url: Optional[str] = None
    status: str
    vd_url: Optional[str] = None
    created_at: datetime

    class Config:
        from_attribute = True