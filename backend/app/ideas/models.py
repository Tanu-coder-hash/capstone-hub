
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


def utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class IdeaStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TAKEN = "taken"


class Difficulty(str, enum.Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


class Idea(Base):
    __tablename__ = "ideas"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(150), index=True)
    description: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String(50), index=True)
    tech_stack: Mapped[str] = mapped_column(String(200), default="")
    difficulty: Mapped[Difficulty] = mapped_column(Enum(Difficulty))

    status: Mapped[IdeaStatus] = mapped_column(
        Enum(IdeaStatus),
        default=IdeaStatus.PENDING,
        index=True,
    )

    reject_reason: Mapped[str | None] = mapped_column(
        String(300),
        nullable=True,
    )

    posted_by: Mapped[int] = mapped_column(index=True)
    team_id: Mapped[int | None] = mapped_column(nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
    )

    vote_rows: Mapped[list["IdeaVote"]] = relationship(
        back_populates="idea",
        cascade="all, delete-orphan",
    )


class IdeaVote(Base):
    __tablename__ = "idea_votes"

    __table_args__ = (
        UniqueConstraint(
            "idea_id",
            "user_id",
            name="uq_one_vote_per_user",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    idea_id: Mapped[int] = mapped_column(
        ForeignKey("ideas.id", ondelete="CASCADE"),
        index=True,
    )

    user_id: Mapped[int] = mapped_column(index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        index=True,
    )

    idea: Mapped[Idea] = relationship(back_populates="vote_rows")
