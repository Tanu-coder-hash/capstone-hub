
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.deliverables.models import SubmissionStatus


# -------------------------
# MILESTONE SCHEMAS
# -------------------------

class MilestoneCreate(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str | None = None
    deadline: datetime
    max_marks: int = Field(default=100, gt=0)
    weightage: float = Field(default=0.0, ge=0, le=100)
    rubric: dict = Field(default_factory=dict)

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("Milestone title cannot be empty")
        return value


class MilestoneUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    deadline: datetime | None = None
    max_marks: int | None = Field(default=None, gt=0)
    weightage: float | None = Field(default=None, ge=0, le=100)
    rubric: dict | None = None

    @field_validator("title")
    @classmethod
    def validate_title(cls, value):
        if value is not None:
            value = value.strip()
            if not value:
                raise ValueError("Milestone title cannot be empty")
        return value


class MilestoneResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str | None
    deadline: datetime
    max_marks: int
    weightage: float
    rubric: dict
    created_at: datetime


# -------------------------
# SUBMISSION SCHEMAS
# -------------------------

class SubmissionCreate(BaseModel):
    milestone_id: int = Field(gt=0)
    team_id: int = Field(gt=0)
    file_path: str = Field(min_length=1, max_length=500)

    @field_validator("file_path")
    @classmethod
    def validate_file_path(cls, value):
        value = value.strip()
        if not value:
            raise ValueError("File path cannot be empty")
        return value


class SubmissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    milestone_id: int
    team_id: int
    file_path: str
    version: int
    is_late: bool
    submitted_at: datetime
    status: SubmissionStatus
    marks: float | None
    evaluation: dict | None
    feedback: str | None
    graded_by: int | None
    graded_at: datetime | None


# -------------------------
# EVALUATION SCHEMAS
# -------------------------

class SubmissionEvaluation(BaseModel):
    marks: float = Field(ge=0)
    feedback: str | None = None
    evaluation: dict = Field(default_factory=dict)
