from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class UserCreatedEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID = Field(...)
    event_type: str = Field(default="user.created")
    user_id: int = Field(..., gt=0)
    email: str = Field(..., min_length=1)
    created_at: datetime = Field(...)
