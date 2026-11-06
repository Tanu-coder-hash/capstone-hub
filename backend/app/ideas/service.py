
from datetime import timedelta
from math import ceil

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ideas.models import (
    Idea,
    IdeaStatus,
    IdeaVote,
    utcnow,
)
from app.ideas.schemas import IdeaCreate, IdeaOut
from app.ideas.similarity import find_similar


PAGE_SIZE = 10

# Ideas that can receive votes
VOTABLE = (IdeaStatus.APPROVED, IdeaStatus.TAKEN)


# -------------------------
# Custom exceptions
# -------------------------

class IdeaError(Exception):
    status_code = 400


class NotFound(IdeaError):
    status_code = 404


class Forbidden(IdeaError):
    status_code = 403


class Conflict(IdeaError):
    status_code = 409


# -------------------------
# Helper functions
# -------------------------

def _get(db: Session, idea_id: int) -> Idea:
    idea = db.get(Idea, idea_id)

    if idea is None:
        raise NotFound("Idea not found")

    return idea


def _require(user, role: str):
    if user.role != role:
        raise Forbidden(f"Only {role} users can do this")


def _to_out(idea: Idea, votes: int) -> IdeaOut:
    out = IdeaOut.model_validate(idea)
    out.votes = votes
    return out


def count_votes(db: Session, idea_id: int) -> int:
    count = db.scalar(
        select(func.count(IdeaVote.id)).where(
            IdeaVote.idea_id == idea_id
        )
    )
    return count or 0


# -------------------------
# IDEA-01: Faculty creates ideas
# -------------------------

def create_idea(
    db: Session,
    data: IdeaCreate,
    user
) -> IdeaOut:

    _require(user, "faculty")

    idea = Idea(
        **data.model_dump(),
        posted_by=user.id,
        status=IdeaStatus.APPROVED
    )

    db.add(idea)
    db.commit()
    db.refresh(idea)

    return _to_out(idea, 0)


# -------------------------
# IDEA-06: Duplicate detection
# -------------------------

def check_duplicates(
    db: Session,
    data: IdeaCreate
) -> list[dict]:

    rows = db.execute(
        select(
            Idea.id,
            Idea.title,
            Idea.description
        ).where(
            Idea.status != IdeaStatus.REJECTED
        )
    ).all()

    titles = {
        row.id: row.title
        for row in rows
    }

    corpus = [
        (row.id, f"{row.title} {row.description}")
        for row in rows
    ]

    matches = find_similar(
        f"{data.title} {data.description}",
        corpus
    )

    return [
        {
            "id": idea_id,
            "title": titles[idea_id],
            "score": score
        }
        for idea_id, score in matches
    ]


# -------------------------
# IDEA-02: Students propose ideas
# -------------------------

def propose_idea(
    db: Session,
    data: IdeaCreate,
    user,
    force: bool = False
):

    _require(user, "student")

    similar = check_duplicates(db, data)

    # Return similar ideas without saving the proposal
    # unless the student explicitly chooses to continue.
    if similar and not force:
        return None, similar

    idea = Idea(
        **data.model_dump(),
        posted_by=user.id,
        status=IdeaStatus.PENDING
    )

    db.add(idea)
    db.commit()
    db.refresh(idea)

    return _to_out(idea, 0), similar


# -------------------------
# IDEA-02b: Faculty approves ideas
# -------------------------

def approve_idea(
    db: Session,
    idea_id: int,
    user
) -> IdeaOut:

    _require(user, "faculty")

    idea = _get(db, idea_id)

    if idea.status != IdeaStatus.PENDING:
        raise Conflict("Only pending ideas can be approved")

    idea.status = IdeaStatus.APPROVED

    db.commit()

    return _to_out(
        idea,
        count_votes(db, idea_id)
    )


# -------------------------
# IDEA-02b: Faculty rejects ideas
# -------------------------

def reject_idea(
    db: Session,
    idea_id: int,
    reason: str,
    user
) -> IdeaOut:

    _require(user, "faculty")

    idea = _get(db, idea_id)

    if idea.status != IdeaStatus.PENDING:
        raise Conflict("Only pending ideas can be rejected")

    idea.status = IdeaStatus.REJECTED
    idea.reject_reason = reason

    db.commit()

    return _to_out(idea, 0)


# -------------------------
# IDEA-03: Search and filter ideas
# -------------------------

def search_ideas(
    db: Session,
    q=None,
    domain=None,
    difficulty=None,
    status=IdeaStatus.APPROVED,
    sort="newest",
    page=1
) -> dict:

    votes = func.count(IdeaVote.id).label("votes")

    stmt = (
        select(Idea, votes)
        .outerjoin(IdeaVote)
        .group_by(Idea.id)
    )

    if q:
        like = f"%{q.strip()}%"

        stmt = stmt.where(
            or_(
                Idea.title.ilike(like),
                Idea.description.ilike(like)
            )
        )

    if domain:
        stmt = stmt.where(Idea.domain == domain)

    if difficulty:
        stmt = stmt.where(Idea.difficulty == difficulty)

    if status:
        stmt = stmt.where(Idea.status == status)

    total = db.scalar(
        select(func.count()).select_from(
            stmt.subquery()
        )
    ) or 0

    order = (
        votes.desc()
        if sort == "votes"
        else Idea.created_at.desc()
    )

    stmt = (
        stmt
        .order_by(order, Idea.id.desc())
        .offset((page - 1) * PAGE_SIZE)
        .limit(PAGE_SIZE)
    )

    items = [
        _to_out(idea, count)
        for idea, count in db.execute(stmt).all()
    ]

    return {
        "items": items,
        "total": total,
        "page": page,
        "pages": max(1, ceil(total / PAGE_SIZE))
    }


# -------------------------
# Get one idea
# -------------------------

def get_idea(
    db: Session,
    idea_id: int
) -> IdeaOut:

    idea = _get(db, idea_id)

    return _to_out(
        idea,
        count_votes(db, idea_id)
    )


# -------------------------
# IDEA-04: Upvote an idea
# -------------------------

def vote(
    db: Session,
    idea_id: int,
    user
) -> int:

    idea = _get(db, idea_id)

    if idea.status not in VOTABLE:
        raise Conflict("You can only vote on approved ideas")

    db.add(
        IdeaVote(
            idea_id=idea_id,
            user_id=user.id
        )
    )

    try:
        db.commit()

    except IntegrityError:
        db.rollback()
        raise Conflict("Already voted")

    return count_votes(db, idea_id)


# -------------------------
# IDEA-04: Withdraw a vote
# -------------------------

def unvote(
    db: Session,
    idea_id: int,
    user
) -> int:

    _get(db, idea_id)

    row = db.scalar(
        select(IdeaVote).where(
            IdeaVote.idea_id == idea_id,
            IdeaVote.user_id == user.id
        )
    )

    if row is None:
        raise NotFound("You have not voted on this idea")

    db.delete(row)
    db.commit()

    return count_votes(db, idea_id)


# -------------------------
# IDEA-05: Trending ideas
# -------------------------

def trending(
    db: Session,
    days: int = 30,
    limit: int = 10
) -> list[IdeaOut]:

    since = utcnow() - timedelta(days=days)

    votes = func.count(IdeaVote.id).label("votes")

    stmt = (
        select(Idea, votes)
        .join(IdeaVote)
        .where(
            IdeaVote.created_at >= since,
            Idea.status.in_(VOTABLE)
        )
        .group_by(Idea.id)
        .order_by(votes.desc(), Idea.id)
        .limit(limit)
    )

    return [
        _to_out(idea, count)
        for idea, count in db.execute(stmt).all()
    ]


# -------------------------
# IDEA-07: Mark idea as taken
# -------------------------

def mark_taken(
    db: Session,
    idea_id: int,
    team_id: int
) -> Idea:

    idea = _get(db, idea_id)

    if idea.status != IdeaStatus.APPROVED:
        raise Conflict("Idea is not available")

    idea.status = IdeaStatus.TAKEN
    idea.team_id = team_id

    # Do not commit here.
    # Member 2 calls this inside their allocation transaction.

    return idea
