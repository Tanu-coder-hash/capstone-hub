
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth.deps import CurrentUser
from app.feedback.models import FacultyFeedback
from app.teams.models import Team, TeamMember, MemberStatus, TeamStatus


class FeedbackError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        self.status_code = status_code
        super().__init__(message)


def submit_feedback(
    db: Session,
    team_id: int,
    feedback_text: str,
    user: CurrentUser,
) -> FacultyFeedback:
    # Only faculty can submit feedback.
    if user.role != "faculty":
        raise FeedbackError("Only faculty can submit feedback", 403)

    # Check whether the team exists.
    team = db.get(Team, team_id)

    if team is None:
        raise FeedbackError("Team not found", 404)

    # Only the assigned faculty guide can submit feedback.
    if team.guide_id != user.id:
        raise FeedbackError(
            "You are not assigned to this team",
            403,
        )

    if team.status != TeamStatus.ALLOCATED:
        raise FeedbackError(
            "Feedback can only be submitted for allocated teams",
            400,
        )

    feedback = FacultyFeedback(
        team_id=team_id,
        faculty_id=user.id,
        feedback=feedback_text,
    )

    db.add(feedback)
    db.flush()

    # Notify all accepted team members.
    from app.notifications import service as notification_service
    from app.notifications.models import NotificationType

    members = db.scalars(
        select(TeamMember).where(
            TeamMember.team_id == team_id,
            TeamMember.status == MemberStatus.ACCEPTED,
        )
    ).all()

    for member in members:
        notification_service.create_notification(
            db=db,
            user_id=member.user_id,
            team_id=team_id,
            notification_type=NotificationType.FACULTY_FEEDBACK,
            message=f"Your faculty guide has posted new feedback for {team.name}.",
            commit=False,
        )

    db.commit()
    db.refresh(feedback)

    return feedback


def get_team_feedback(
    db: Session,
    team_id: int,
    user: CurrentUser,
) -> list[FacultyFeedback]:
    team = db.get(Team, team_id)

    if team is None:
        raise FeedbackError("Team not found", 404)

    if user.role == "faculty":
        if team.guide_id != user.id:
            raise FeedbackError(
                "You are not assigned to this team",
                403,
            )

    elif user.role == "student":
        membership = db.scalar(
            select(TeamMember).where(
                TeamMember.team_id == team_id,
                TeamMember.user_id == user.id,
                TeamMember.status == MemberStatus.ACCEPTED,
            )
        )

        if membership is None:
            raise FeedbackError(
                "You are not a member of this team",
                403,
            )

    else:
        raise FeedbackError("Access denied", 403)

    return list(
        db.scalars(
            select(FacultyFeedback)
            .where(FacultyFeedback.team_id == team_id)
            .order_by(FacultyFeedback.created_at.desc())
        ).all()
    )


def get_my_feedback(
    db: Session,
    user: CurrentUser,
) -> list[FacultyFeedback]:
    if user.role != "student":
        raise FeedbackError(
            "Only students can access their own team feedback",
            403,
        )

    membership = db.scalar(
        select(TeamMember).where(
            TeamMember.user_id == user.id,
            TeamMember.status == MemberStatus.ACCEPTED,
        )
    )

    if membership is None:
        raise FeedbackError("You are not part of a team", 404)

    return get_team_feedback(db, membership.team_id, user)


def get_faculty_teams(
    db: Session,
    user: CurrentUser,
) -> list[Team]:
    if user.role != "faculty":
        raise FeedbackError(
            "Only faculty can view assigned teams",
            403,
        )

    return list(
        db.scalars(
            select(Team)
            .where(
                Team.guide_id == user.id,
                Team.status == TeamStatus.ALLOCATED,
            )
            .order_by(Team.created_at.desc())
        ).all()
    )
