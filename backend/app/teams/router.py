from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session
from app.auth.deps import get_current_user
from app.core.db import get_db
from app.teams import service
from app.teams.schemas import (
    IdeaRequestIn,
    IdeaRequestOut,
    InviteIn,
    InviteOut,
    InviteResponse,
    MemberOut,
    TeamCreate,
    TeamOut,
)

router = APIRouter(
    prefix="/api/v1/teams",
    tags=["Teams"],
)

def handle_error(func, *args, **kwargs):
    """Convert service-layer errors into standard HTTP responses."""
    try:
        return func(*args, **kwargs)
    except service.TeamError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc

#
# Static endpoints first (avoids collisions with /{team_id})
#

@router.post("", response_model=TeamOut, status_code=status.HTTP_201_CREATED)
def create_team(
    data: TeamCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return TeamOut.model_validate(handle_error(service.create_team, db, data.name, user))

@router.get("/me", response_model=TeamOut)
def my_team(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return TeamOut.model_validate(handle_error(service.get_my_team, db, user))

@router.get("/invites/me", response_model=list[InviteOut])
def my_invites(db: Session = Depends(get_db), user=Depends(get_current_user)):
    return service.list_my_invites(db, user)

@router.post("/invites/{membership_id}/respond", response_model=MemberOut)
def respond_invite(
    membership_id: int,
    data: InviteResponse,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return MemberOut.model_validate(
        handle_error(service.respond_invite, db, membership_id, data.accept, user)
    )

@router.get("/idea-requests/pending", response_model=list[IdeaRequestOut])
def pending_requests(db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = handle_error(service.pending_requests_for_faculty, db, user)
    return [IdeaRequestOut.model_validate(r) for r in rows]

@router.patch("/idea-requests/{request_id}/approve", response_model=TeamOut)
def approve_request(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return TeamOut.model_validate(handle_error(service.approve_request, db, request_id, user))

@router.patch("/idea-requests/{request_id}/reject", response_model=IdeaRequestOut)
def reject_request(
    request_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return IdeaRequestOut.model_validate(handle_error(service.reject_request, db, request_id, user))

#
# Endpoints with {team_id} parameter
#

@router.post("/{team_id}/invites", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
def invite(
    team_id: int,
    data: InviteIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return MemberOut.model_validate(
        handle_error(service.invite_member, db, team_id, data.user_id, user)
    )

@router.delete("/{team_id}/members/me", response_model=TeamOut)
def leave(team_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    return TeamOut.model_validate(handle_error(service.leave_team, db, team_id, user))

@router.delete("/{team_id}", status_code=status.HTTP_204_NO_CONTENT)
def dissolve(team_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    handle_error(service.dissolve_team, db, team_id, user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.post(
    "/{team_id}/idea-requests",
    response_model=list[IdeaRequestOut],
    status_code=status.HTTP_201_CREATED,
)
def request_ideas(
    team_id: int,
    data: IdeaRequestIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    rows = handle_error(service.request_ideas, db, team_id, data.idea_ids, user)
    return [IdeaRequestOut.model_validate(r) for r in rows]

@router.get("/{team_id}/idea-requests", response_model=list[IdeaRequestOut])
def team_requests(team_id: int, db: Session = Depends(get_db), user=Depends(get_current_user)):
    rows = handle_error(service.list_team_requests, db, team_id, user)
    return [IdeaRequestOut.model_validate(r) for r in rows]

