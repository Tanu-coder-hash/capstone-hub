from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator
from app.teams.models import (
    MAX_IDEA_PREFERENCES,
    MemberStatus,
    RequestStatus,
    TeamStatus,
)

class TeamCreate(BaseModel):
    name: str = Field(min_length=3, max_length=80)

class InviteIn(BaseModel):
    user_id: int = Field(gt=0)

class InviteResponse(BaseModel):
    accept: bool
class IdeaRequestIn(BaseModel):
    idea_ids: list[int] = Field(min_length=1, max_length=MAX_IDEA_PREFERENCES)

    @field_validator("idea_ids")
    @classmethod
    def no_duplicates(cls, value: list[int]) -> list[int]:
        if len(set(value)) != len(value):
            raise ValueError("Idea preferences must be different ideas")
        return value

class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    status: MemberStatus

class TeamOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    leader_id: int
    semester: str
    status: TeamStatus
    idea_id: int | None
    guide_id: int | None
    created_at: datetime
    members: list[MemberOut]

class InviteOut(BaseModel):
    id: int
    team_id: int
    team_name: str
    status: MemberStatus

class IdeaRequestOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    team_id: int
    idea_id: int
    preference: int
    status: RequestStatus