import pytest

from datetime import timedelta

from app.ideas import service
from app.ideas.models import Idea, IdeaStatus, Difficulty, IdeaVote, utcnow
from app.ideas.schemas import IdeaCreate


# -------------------------
# IDEA-01: Create ideas
# -------------------------

def test_faculty_can_create_idea(db, faculty, idea_data):
    result = service.create_idea(db, idea_data, faculty)

    assert result.id is not None
    assert result.title == idea_data.title
    assert result.status == IdeaStatus.APPROVED
    assert result.posted_by == faculty.id
    assert result.votes == 0


def test_student_cannot_create_faculty_idea(db, student, idea_data):
    with pytest.raises(service.Forbidden):
        service.create_idea(db, idea_data, student)


# -------------------------
# IDEA-02: Propose ideas
# -------------------------

def test_student_can_propose_idea(db, student, idea_data):
    result, similar = service.propose_idea(
        db, idea_data, student
    )

    assert result is not None
    assert result.status == IdeaStatus.PENDING
    assert result.posted_by == student.id
    assert similar == []


def test_faculty_cannot_propose_student_idea(db, faculty, idea_data):
    with pytest.raises(service.Forbidden):
        service.propose_idea(db, idea_data, faculty)


def test_duplicate_proposal_is_not_saved_without_force(
    db, student, idea_data, monkeypatch
):
    monkeypatch.setattr(
        service,
        "check_duplicates",
        lambda db, data: [
            {"id": 1, "title": "Existing idea", "score": 0.9}
        ],
    )

    result, similar = service.propose_idea(
        db, idea_data, student
    )

    assert result is None
    assert len(similar) == 1
    assert db.query(Idea).count() == 0


def test_duplicate_proposal_can_be_saved_with_force(
    db, student, idea_data, monkeypatch
):
    monkeypatch.setattr(
        service,
        "check_duplicates",
        lambda db, data: [
            {"id": 1, "title": "Existing idea", "score": 0.9}
        ],
    )

    result, similar = service.propose_idea(
        db, idea_data, student, force=True
    )

    assert result is not None
    assert result.status == IdeaStatus.PENDING
    assert len(similar) == 1
    assert db.query(Idea).count() == 1


# -------------------------
# IDEA-02b: Approve ideas
# -------------------------

def test_faculty_can_approve_pending_idea(
    db, faculty, student, idea_data
):
    proposed, _ = service.propose_idea(
        db, idea_data, student
    )

    result = service.approve_idea(
        db, proposed.id, faculty
    )

    assert result.status == IdeaStatus.APPROVED


def test_student_cannot_approve_idea(
    db, student, idea_data
):
    idea = Idea(
        **idea_data.model_dump(),
        posted_by=student.id,
        status=IdeaStatus.PENDING,
    )
    db.add(idea)
    db.commit()

    with pytest.raises(service.Forbidden):
        service.approve_idea(db, idea.id, student)


def test_approved_idea_cannot_be_approved_again(
    db, faculty, idea_data
):
    result = service.create_idea(db, idea_data, faculty)

    with pytest.raises(service.Conflict):
        service.approve_idea(db, result.id, faculty)


# -------------------------
# IDEA-02b: Reject ideas
# -------------------------

def test_faculty_can_reject_pending_idea(
    db, faculty, student, idea_data
):
    proposed, _ = service.propose_idea(
        db, idea_data, student
    )

    result = service.reject_idea(
        db,
        proposed.id,
        "This idea needs a clearer project scope.",
        faculty,
    )

    assert result.status == IdeaStatus.REJECTED

    saved = db.get(Idea, proposed.id)
    assert saved.reject_reason == (
        "This idea needs a clearer project scope."
    )


def test_rejected_idea_cannot_be_rejected_again(
    db, faculty, student, idea_data
):
    proposed, _ = service.propose_idea(
        db, idea_data, student
    )

    service.reject_idea(
        db,
        proposed.id,
        "Please improve the project scope.",
        faculty,
    )

    with pytest.raises(service.Conflict):
        service.reject_idea(
            db,
            proposed.id,
            "Another rejection reason.",
            faculty,
        )


# -------------------------
# IDEA-03: Search and filter
# -------------------------

def test_search_returns_approved_ideas(
    db, faculty, idea_data
):
    service.create_idea(db, idea_data, faculty)

    result = service.search_ideas(db)

    assert result["total"] == 1
    assert len(result["items"]) == 1
    assert result["items"][0].status == IdeaStatus.APPROVED


def test_search_can_filter_by_domain(
    db, faculty, idea_data
):
    service.create_idea(db, idea_data, faculty)

    result = service.search_ideas(
        db,
        domain="IoT",
    )

    assert result["total"] == 1

    result = service.search_ideas(
        db,
        domain="Healthcare",
    )

    assert result["total"] == 0


def test_search_can_filter_by_keyword(
    db, faculty, idea_data
):
    service.create_idea(db, idea_data, faculty)

    result = service.search_ideas(
        db,
        q="energy",
    )

    assert result["total"] == 1


def test_search_can_filter_by_difficulty(
    db, faculty, idea_data
):
    service.create_idea(db, idea_data, faculty)

    result = service.search_ideas(
        db,
        difficulty=Difficulty.MEDIUM,
    )

    assert result["total"] == 1


def test_search_can_filter_by_status(
    db, student, idea_data
):
    service.propose_idea(db, idea_data, student)

    result = service.search_ideas(
        db,
        status=IdeaStatus.PENDING,
    )

    assert result["total"] == 1

def test_search_without_status_filter_returns_all_statuses(
    db, student, idea_data
):
    service.propose_idea(db, idea_data, student)

    result = service.search_ideas(
        db,
        status=None,
    )

    assert result["total"] == 1
    assert result["items"][0].status == IdeaStatus.PENDING


def test_search_returns_empty_result_for_no_matches(db):
    result = service.search_ideas(
        db,
        q="something that does not exist",
    )

    assert result["total"] == 0
    assert result["items"] == []
    assert result["pages"] == 1


def test_search_pagination(db, faculty):
    for number in range(12):
        data = IdeaCreate(
            title=f"Campus Project Idea {number}",
            description=(
                f"This is a sufficiently long description "
                f"for campus project idea number {number}."
            ),
            domain="Education",
            tech_stack="Python",
            difficulty=Difficulty.EASY,
        )
        service.create_idea(db, data, faculty)

    first_page = service.search_ideas(db, page=1)
    second_page = service.search_ideas(db, page=2)

    assert first_page["total"] == 12
    assert len(first_page["items"]) == 10
    assert len(second_page["items"]) == 2
    assert first_page["pages"] == 2


# -------------------------
# Get one idea
# -------------------------

def test_get_existing_idea(db, faculty, idea_data):
    created = service.create_idea(db, idea_data, faculty)

    result = service.get_idea(db, created.id)

    assert result.id == created.id
    assert result.title == idea_data.title


def test_get_nonexistent_idea_raises_not_found(db):
    with pytest.raises(service.NotFound):
        service.get_idea(db, 999)


# -------------------------
# IDEA-04: Voting
# -------------------------

def test_student_can_vote_for_approved_idea(
    db, faculty, student, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    votes = service.vote(db, idea.id, student)

    assert votes == 1


def test_user_cannot_vote_twice(
    db, faculty, student, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    service.vote(db, idea.id, student)

    with pytest.raises(service.Conflict):
        service.vote(db, idea.id, student)


def test_cannot_vote_for_pending_idea(
    db, student, idea_data
):
    idea, _ = service.propose_idea(
        db, idea_data, student
    )

    with pytest.raises(service.Conflict):
        service.vote(db, idea.id, student)


def test_user_can_withdraw_vote(
    db, faculty, student, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    service.vote(db, idea.id, student)
    votes = service.unvote(db, idea.id, student)

    assert votes == 0


def test_cannot_withdraw_vote_that_does_not_exist(
    db, faculty, student, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    with pytest.raises(service.NotFound):
        service.unvote(db, idea.id, student)


# -------------------------
# IDEA-05: Trending
# -------------------------

def test_trending_returns_recently_voted_ideas(
    db, faculty, student, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    service.vote(db, idea.id, student)

    result = service.trending(db, days=30, limit=10)

    assert len(result) == 1
    assert result[0].id == idea.id
    assert result[0].votes == 1


def test_trending_excludes_old_votes(
    db, faculty, student, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    old_vote = IdeaVote(
        idea_id=idea.id,
        user_id=student.id,
        created_at=utcnow() - timedelta(days=60),
    )
    db.add(old_vote)
    db.commit()

    result = service.trending(db, days=30)

    assert result == []


def test_trending_respects_limit(db, faculty, student):
    for number in range(3):
        data = IdeaCreate(
            title=f"Trending Project Idea {number}",
            description=(
                f"This is a sufficiently long description "
                f"for trending project idea number {number}."
            ),
            domain="Technology",
            tech_stack="Python",
            difficulty=Difficulty.EASY,
        )

        idea = service.create_idea(db, data, faculty)

        voter = type(
            "User",
            (),
            {"id": 100 + number, "role": "student"},
        )()

        service.vote(db, idea.id, voter)

    result = service.trending(db, limit=2)

    assert len(result) == 2


# -------------------------
# IDEA-07: Mark as taken
# -------------------------

def test_mark_approved_idea_as_taken(
    db, faculty, idea_data
):
    idea = service.create_idea(db, idea_data, faculty)

    result = service.mark_taken(
        db,
        idea.id,
        team_id=55,
    )

    assert result.status == IdeaStatus.TAKEN
    assert result.team_id == 55

    # mark_taken intentionally does not commit.
    db.commit()

    saved = db.get(Idea, idea.id)
    assert saved.status == IdeaStatus.TAKEN
    assert saved.team_id == 55


def test_pending_idea_cannot_be_marked_as_taken(
    db, student, idea_data
):
    idea, _ = service.propose_idea(
        db, idea_data, student
    )

    with pytest.raises(service.Conflict):
        service.mark_taken(
            db,
            idea.id,
            team_id=55,
        )


def test_missing_idea_cannot_be_marked_as_taken(db):
    with pytest.raises(service.NotFound):
        service.mark_taken(
            db,
            idea_id=999,
            team_id=55,
        )