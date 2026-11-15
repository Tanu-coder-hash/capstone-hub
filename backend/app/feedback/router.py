
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.feedback import service
from app.feedback.schemas import FeedbackCreate, FeedbackOut
from app.teams.schemas import TeamOut


router = APIRouter(
    prefix="/api/v1/feedback",
    tags=["Faculty Feedback"],
)


def handle_error(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)
    except service.FeedbackError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc


@router.post(
    "/teams/{team_id}",
    response_model=FeedbackOut,
    status_code=201,
)
def submit_team_feedback(
    team_id: int,
    data: FeedbackCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(
        service.submit_feedback,
        db,
        team_id,
        data.feedback,
        user,
    )


@router.get(
    "/teams/{team_id}",
    response_model=list[FeedbackOut],
)
def list_team_feedback(
    team_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(
        service.get_team_feedback,
        db,
        team_id,
        user,
    )


@router.get(
    "/me",
    response_model=list[FeedbackOut],
)
def my_feedback(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(
        service.get_my_feedback,
        db,
        user,
    )


@router.get(
    "/faculty/teams",
    response_model=list[TeamOut],
)
def faculty_teams(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(
        service.get_faculty_teams,
        db,
        user,
    )
