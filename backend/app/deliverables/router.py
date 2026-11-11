
from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db

from app.deliverables import service
from app.deliverables.schemas import (
    MilestoneCreate,
    MilestoneResponse,
    MilestoneUpdate,
    SubmissionCreate,
    SubmissionEvaluation,
    SubmissionResponse,
)


router = APIRouter(
    prefix="/api/v1/deliverables",
    tags=["Deliverables"],
)


# -------------------------
# Error handling
# -------------------------

def handle_error(error: service.DeliverableError):
    raise HTTPException(
        status_code=error.status_code,
        detail=str(error),
    )


# -------------------------
# MILESTONE ENDPOINTS
# -------------------------

@router.post(
    "/milestones",
    response_model=MilestoneResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_milestone(
    data: MilestoneCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.create_milestone(db, data, user)
    except service.DeliverableError as error:
        handle_error(error)


@router.get(
    "/milestones",
    response_model=list[MilestoneResponse],
)
def list_milestones(
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return service.list_milestones(db)


@router.get(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
)
def get_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.get_milestone(db, milestone_id)
    except service.DeliverableError as error:
        handle_error(error)


@router.patch(
    "/milestones/{milestone_id}",
    response_model=MilestoneResponse,
)
def update_milestone(
    milestone_id: int,
    data: MilestoneUpdate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.update_milestone(
            db, milestone_id, data, user
        )
    except service.DeliverableError as error:
        handle_error(error)


@router.delete(
    "/milestones/{milestone_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_milestone(
    milestone_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        service.delete_milestone(db, milestone_id, user)
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    except service.DeliverableError as error:
        handle_error(error)


# -------------------------
# SUBMISSION ENDPOINTS
# -------------------------

@router.post(
    "/submissions",
    response_model=SubmissionResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_deliverable(
    data: SubmissionCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.submit_deliverable(db, data, user)
    except service.DeliverableError as error:
        handle_error(error)


@router.get(
    "/teams/{team_id}/submissions",
    response_model=list[SubmissionResponse],
)
def list_team_submissions(
    team_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.list_team_submissions(db, team_id, user)
    except service.DeliverableError as error:
        handle_error(error)


@router.get(
    "/milestones/{milestone_id}/teams/{team_id}/history",
    response_model=list[SubmissionResponse],
)
def get_submission_history(
    milestone_id: int,
    team_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.get_submission_history(
            db, milestone_id, team_id, user
        )
    except service.DeliverableError as error:
        handle_error(error)


# -------------------------
# FACULTY EVALUATION
# -------------------------

@router.post(
    "/submissions/{submission_id}/evaluate",
    response_model=SubmissionResponse,
)
def evaluate_submission(
    submission_id: int,
    data: SubmissionEvaluation,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    try:
        return service.evaluate_submission(
            db, submission_id, data, user
        )
    except service.DeliverableError as error:
        handle_error(error)
