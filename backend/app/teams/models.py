import enum
from datetime import datetime
from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.db import Base
from app.ideas.models import utcnow

CURRENT_SEMESTER = "2026-ODD"
MIN_TEAM_SIZE = 3
MAX_TEAM_SIZE = 4
MAX_IDEA_PREFERENCES = 3

class TeamStatus(str, enum.Enum):
    FORMING = "forming"
    COMPLETE = "complete"
    ALLOCATED = "allocated"
    DISSOLVED = "dissolved"

class MemberStatus(str, enum.Enum):
    INVITED = "invited"
    ACCEPTED = "accepted"
    REJECTED = "rejected"

class RequestStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    CANCELLED = "cancelled"

class Team(Base):
    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True)
    leader_id: Mapped[int] = mapped_column(index=True)
    semester: Mapped[str] = mapped_column(String(20), default=CURRENT_SEMESTER)
    idea_id: Mapped[int | None] = mapped_column(
        ForeignKey("ideas.id"),
        unique=True,
        nullable=True,
    )
    guide_id: Mapped[int | None] = mapped_column(nullable=True)
    status: Mapped[TeamStatus] = mapped_column(
        Enum(TeamStatus),
        default=TeamStatus.FORMING,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    members: Mapped[list["TeamMember"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )
    requests: Mapped[list["IdeaRequest"]] = relationship(
        back_populates="team",
        cascade="all, delete-orphan",
    )

class TeamMember(Base):
    __tablename__ = "team_members"
    __table_args__ = (
        UniqueConstraint("team_id", "user_id", name="uq_member_once_per_team"),
        Index(
            "uq_one_active_team_per_student",
            "user_id",
            "semester",
            unique=True,
            sqlite_where=text("status = 'ACCEPTED'"),
            postgresql_where=text("status = 'ACCEPTED'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        index=True,
    )
    user_id: Mapped[int] = mapped_column(index=True)
    semester: Mapped[str] = mapped_column(String(20), default=CURRENT_SEMESTER)
    status: Mapped[MemberStatus] = mapped_column(
        Enum(MemberStatus),
        default=MemberStatus.INVITED,
    )
    invited_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    responded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    team: Mapped[Team] = relationship(back_populates="members")

class IdeaRequest(Base):
    __tablename__ = "idea_requests"
    __table_args__ = (
        UniqueConstraint("team_id", "idea_id", name="uq_request_once"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(
        ForeignKey("teams.id", ondelete="CASCADE"),
        index=True,
    )
    idea_id: Mapped[int] = mapped_column(ForeignKey("ideas.id"), index=True)
    preference: Mapped[int] = mapped_column()
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus),
        default=RequestStatus.PENDING,
        index=True,
    )
    reviewed_by: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    team: Mapped[Team] = relationship(back_populates="requests")
