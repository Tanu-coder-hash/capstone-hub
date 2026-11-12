
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.ideas.models import utcnow


class FacultyFeedback(Base):
    __tablename__ = "faculty_feedback"

    __table_args__ = (
        Index(
            "ix_faculty_feedback_team_created",
            "team_id",
            "created_at",
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    faculty_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )

    feedback: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=utcnow,
        nullable=False,
    )
