
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class FeedbackCreate(BaseModel):
    feedback: str = Field(
        min_length=5,
        max_length=5000,
        description="Feedback provided by the faculty member",
    )


class FeedbackOut(BaseModel):
    id: int
    team_id: int
    faculty_id: int
    feedback: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
