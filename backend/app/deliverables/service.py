
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ideas.models import utcnow
from app.teams.models import (
    MemberStatus,
    Team,
    TeamMember,
    TeamStatus,
)

from app.deliverables.models import (
    Milestone,
    Submission,
    SubmissionStatus,
)
from app.deliverables.schemas import (
    MilestoneCreate,
    MilestoneUpdate,
    SubmissionCreate,
    SubmissionEvaluation,
)


# -------------------------
# Custom exceptions
# -------------------------

class DeliverableError(Exception):
    status_code = 400


class NotFound(DeliverableError):
    status_code = 404


class Forbidden(DeliverableError):
    status_code = 403


class Conflict(DeliverableError):
    status_code = 409


# -------------------------
# Helper functions
# -------------------------

def _require(user, role: str):
    if user.role != role:
        raise Forbidden(f"Only {role} users can do this")


def _get_milestone(db: Session, milestone_id: int) -> Milestone:
    milestone = db.get(Milestone, milestone_id)

    if milestone is None:
        raise NotFound("Milestone not found")

    return milestone


def _get_submission(db: Session, submission_id: int) -> Submission:
    submission = db.get(Submission, submission_id)

    if submission is None:
        raise NotFound("Submission not found")

    return submission


def _get_team(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)

    if team is None or team.status == TeamStatus.DISSOLVED:
        raise NotFound("Team not found")

    return team


def _require_team_member(db: Session, team_id: int, user_id: int):
    member = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.user_id == user_id,
            TeamMember.status == MemberStatus.ACCEPTED,
        )
    )

    if member is None:
        raise Forbidden("You are not an accepted member of this team")


def _require_team_guide(team: Team, user):
    if team.guide_id != user.id:
        raise Forbidden("Only the assigned faculty guide can evaluate this team's submissions")


def _require_submission_access(db: Session, submission: Submission, user):
    team = _get_team(db, submission.team_id)

    if user.role == "faculty":
        _require_team_guide(team, user)
    elif user.role == "student":
        _require_team_member(db, team.id, user.id)
    else:
        raise Forbidden("You do not have permission to view this submission")

    return team


# -------------------------
# DELIV-01: Milestone management
# -------------------------

def create_milestone(
    db: Session,
    data: MilestoneCreate,
    user,
) -> Milestone:
    _require(user, "faculty")

    milestone = Milestone(**data.model_dump())

    db.add(milestone)
    db.commit()
    db.refresh(milestone)

    return milestone


def list_milestones(db: Session) -> list[Milestone]:
    return list(
        db.scalars(
            select(Milestone).order_by(Milestone.deadline)
        )
    )


def get_milestone(db: Session, milestone_id: int) -> Milestone:
    return _get_milestone(db, milestone_id)


def update_milestone(
    db: Session,
    milestone_id: int,
    data: MilestoneUpdate,
    user,
) -> Milestone:
    _require(user, "faculty")

    milestone = _get_milestone(db, milestone_id)

    updates = data.model_dump(exclude_unset=True)

    for field, value in updates.items():
        setattr(milestone, field, value)

    db.commit()
    db.refresh(milestone)

    return milestone


def delete_milestone(
    db: Session,
    milestone_id: int,
    user,
) -> None:
    _require(user, "faculty")

    milestone = _get_milestone(db, milestone_id)

    if milestone.submissions:
        raise Conflict(
            "Cannot delete a milestone that already has submissions"
        )

    db.delete(milestone)
    db.commit()


# -------------------------
# DELIV-02 / DELIV-03:
# Deliverable submission and version control
# -------------------------

def submit_deliverable(
    db: Session,
    data: SubmissionCreate,
    user,
) -> Submission:
    _require(user, "student")

    milestone = _get_milestone(db, data.milestone_id)
    team = _get_team(db, data.team_id)

    _require_team_member(db, team.id, user.id)

    if team.status != TeamStatus.ALLOCATED:
        raise Conflict(
            "Only teams with an allocated project can submit deliverables"
        )

    latest = db.scalar(
        select(Submission)
        .where(
            Submission.milestone_id == milestone.id,
            Submission.team_id == team.id,
        )
        .order_by(Submission.version.desc())
    )

    next_version = latest.version + 1 if latest else 1

    submitted_at = utcnow()
    is_late = submitted_at > milestone.deadline

    submission = Submission(
        milestone_id=milestone.id,
        team_id=team.id,
        file_path=data.file_path,
        version=next_version,
        is_late=is_late,
        submitted_at=submitted_at,
        status=SubmissionStatus.SUBMITTED,
    )

    db.add(submission)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Could not save the submission. Please try again.")

    db.refresh(submission)

    return submission


def get_submission_history(
    db: Session,
    milestone_id: int,
    team_id: int,
    user,
) -> list[Submission]:
    _get_milestone(db, milestone_id)
    team = _get_team(db, team_id)

    if user.role == "faculty":
        _require_team_guide(team, user)
    elif user.role == "student":
        _require_team_member(db, team.id, user.id)
    else:
        raise Forbidden("You do not have permission to view submission history")

    return list(
        db.scalars(
            select(Submission)
            .where(
                Submission.milestone_id == milestone_id,
                Submission.team_id == team_id,
            )
            .order_by(Submission.version.desc())
        )
    )


def list_team_submissions(
    db: Session,
    team_id: int,
    user,
) -> list[Submission]:
    team = _get_team(db, team_id)

    if user.role == "faculty":
        _require_team_guide(team, user)
    elif user.role == "student":
        _require_team_member(db, team.id, user.id)
    else:
        raise Forbidden("You do not have permission to view these submissions")

    return list(
        db.scalars(
            select(Submission)
            .where(Submission.team_id == team_id)
            .order_by(Submission.submitted_at.desc())
        )
    )


# -------------------------
# DELIV-04: Faculty evaluation
# -------------------------

def evaluate_submission(
    db: Session,
    submission_id: int,
    data: SubmissionEvaluation,
    user,
) -> Submission:
    _require(user, "faculty")

    submission = _get_submission(db, submission_id)
    team = _get_team(db, submission.team_id)

    _require_team_guide(team, user)

    milestone = _get_milestone(db, submission.milestone_id)

    if data.marks > milestone.max_marks:
        raise Conflict(
            f"Marks cannot exceed the milestone maximum of {milestone.max_marks}"
        )

    submission.marks = data.marks
    submission.feedback = data.feedback
    submission.evaluation = data.evaluation
    submission.graded_by = user.id
    submission.graded_at = utcnow()
    submission.status = SubmissionStatus.GRADED

    db.commit()
    db.refresh(submission)

    return submission
