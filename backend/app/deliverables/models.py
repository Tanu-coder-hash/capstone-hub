
import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.ideas.models import utcnow

class SubmissionStatus(str, enum.Enum):
    SUBMITTED = "submitted"
    GRADED = "graded"

class Milestone(Base):
    __tablename__ = "milestones"

    __table_args__ = (
        CheckConstraint(
            "weightage >= 0 AND weightage <= 100",
            name="ck_milestone_weightage",
        ),
        CheckConstraint(
            "max_marks > 0",
            name="ck_milestone_max_marks",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    title: Mapped[str] = mapped_column(
        String(100), nullable=False
    )
    description: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    deadline: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, index=True
    )
    max_marks: Mapped[int] = mapped_column(
        Integer, default=100, nullable=False
    )
    weightage: Mapped[float] = mapped_column(
        Float, default=0.0, nullable=False
    )
    rubric: Mapped[dict] = mapped_column(
        JSON, nullable=False, default=dict
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )

    submissions: Mapped[list["Submission"]] = relationship(
        back_populates="milestone",
        cascade="all, delete-orphan",
    )

class Submission(Base):
    __tablename__ = "submissions"

    __table_args__ = (
        CheckConstraint(
            "version >= 1",
            name="ck_submission_version",
        ),
        Index(
            "ix_submission_milestone_team_version",
            "milestone_id",
            "team_id",
            "version",
        ),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, index=True
    )
    milestone_id: Mapped[int] = mapped_column(
        ForeignKey("milestones.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False
    )
    version: Mapped[int] = mapped_column(
        Integer, default=1, nullable=False
    )
    is_late: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, nullable=False
    )
    status: Mapped[SubmissionStatus] = mapped_column(
        Enum(SubmissionStatus),
        default=SubmissionStatus.SUBMITTED,
        nullable=False,
    )
    marks: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )
    evaluation: Mapped[dict | None] = mapped_column(
        JSON, nullable=True
    )
    feedback: Mapped[str | None] = mapped_column(
        Text, nullable=True
    )
    graded_by: Mapped[int | None] = mapped_column(
        Integer, nullable=True
    )
    graded_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    milestone: Mapped["Milestone"] = relationship(
        back_populates="submissions"
    )
    team: Mapped["Team"] = relationship("Team")