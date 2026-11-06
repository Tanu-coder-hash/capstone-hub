
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.ideas.models import Difficulty, IdeaStatus


class IdeaCreate(BaseModel):
    title: str = Field(min_length=5, max_length=150)
    description: str = Field(min_length=20, max_length=5000)
    domain: str = Field(min_length=2, max_length=50)
    tech_stack: str = Field(default="", max_length=200)
    difficulty: Difficulty


class IdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    description: str
    domain: str
    tech_stack: str
    difficulty: Difficulty
    status: IdeaStatus
    posted_by: int
    created_at: datetime
    votes: int = 0


class IdeaPage(BaseModel):
    items: list[IdeaOut]
    total: int
    page: int
    pages: int


class SimilarIdea(BaseModel):
    id: int
    title: str
    score: float


class ProposeResult(BaseModel):
    idea: IdeaOut | None
    similar: list[SimilarIdea]


class RejectIn(BaseModel):
    reason: str = Field(min_length=5, max_length=300)


class VoteOut(BaseModel):
    idea_id: int
    votes: int
