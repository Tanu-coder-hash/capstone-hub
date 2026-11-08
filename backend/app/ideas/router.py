
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.deps import get_current_user
from app.core.db import get_db
from app.ideas import service
from app.ideas.models import Difficulty, IdeaStatus
from app.ideas.schemas import (
    IdeaCreate,
    IdeaOut,
    IdeaPage,
    ProposeResult,
    RejectIn,
    VoteOut,
)

router = APIRouter(
    prefix="/api/v1/ideas",
    tags=["Idea Bank"],
)


def handle_error(func, *args, **kwargs):
    """Convert service-layer errors into HTTP responses."""
    try:
        return func(*args, **kwargs)
    except service.IdeaError as exc:
        raise HTTPException(
            status_code=exc.status_code,
            detail=str(exc),
        ) from exc


# GET /api/v1/ideas/trending
# Keep this route before /{idea_id}.
@router.get("/trending", response_model=list[IdeaOut])
def get_trending(
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    return service.trending(db, days, limit)


# GET /api/v1/ideas
@router.get("", response_model=IdeaPage)
def list_ideas(
    q: str | None = None,
    domain: str | None = None,
    difficulty: Difficulty | None = None,
    status_filter: IdeaStatus = Query(
        default=IdeaStatus.APPROVED,
        alias="status",
    ),
    sort: str = Query(default="newest", pattern="^(newest|votes)$"),
    page: int = Query(default=1, ge=1),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    # Pending and rejected proposals are faculty-only.
    if status_filter != IdeaStatus.APPROVED:
        if user.role != "faculty":
            raise HTTPException(
                status_code=403,
                detail="Only faculty can view non-approved ideas",
            )

    return service.search_ideas(
        db=db,
        q=q,
        domain=domain,
        difficulty=difficulty,
        status=status_filter,
        sort=sort,
        page=page,
    )


# POST /api/v1/ideas
@router.post(
    "",
    response_model=IdeaOut,
    status_code=status.HTTP_201_CREATED,
)
def create_idea(
    data: IdeaCreate,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(service.create_idea, db, data, user)


# POST /api/v1/ideas/propose
@router.post(
    "/propose",
    response_model=ProposeResult,
    status_code=status.HTTP_201_CREATED,
)
def propose_idea(
    data: IdeaCreate,
    force: bool = Query(default=False),
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    idea, similar = handle_error(
        service.propose_idea,
        db,
        data,
        user,
        force,
    )

    return {
        "idea": idea,
        "similar": similar,
    }


# GET /api/v1/ideas/{idea_id}
@router.get("/{idea_id}", response_model=IdeaOut)
def get_idea(
    idea_id: int,
    db: Session = Depends(get_db),
):
    return handle_error(service.get_idea, db, idea_id)


# PATCH /api/v1/ideas/{idea_id}/approve
@router.patch("/{idea_id}/approve", response_model=IdeaOut)
def approve_idea(
    idea_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(
        service.approve_idea,
        db,
        idea_id,
        user,
    )


# PATCH /api/v1/ideas/{idea_id}/reject
@router.patch("/{idea_id}/reject", response_model=IdeaOut)
def reject_idea(
    idea_id: int,
    data: RejectIn,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    return handle_error(
        service.reject_idea,
        db,
        idea_id,
        data.reason,
        user,
    )


# POST /api/v1/ideas/{idea_id}/vote
@router.post("/{idea_id}/vote", response_model=VoteOut)
def vote(
    idea_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    votes = handle_error(
        service.vote,
        db,
        idea_id,
        user,
    )

    return {
        "idea_id": idea_id,
        "votes": votes,
    }


# DELETE /api/v1/ideas/{idea_id}/vote
@router.delete("/{idea_id}/vote", response_model=VoteOut)
def withdraw_vote(
    idea_id: int,
    db: Session = Depends(get_db),
    user=Depends(get_current_user),
):
    votes = handle_error(
        service.unvote,
        db,
        idea_id,
        user,
    )

    return {
        "idea_id": idea_id,
        "votes": votes,
    }
