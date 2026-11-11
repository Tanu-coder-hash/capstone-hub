
from datetime import datetime, timedelta, timezone

import pytest

from app.deliverables import service
from app.deliverables.models import SubmissionStatus
from app.deliverables.schemas import (
    MilestoneCreate,
    SubmissionCreate,
    SubmissionEvaluation,
)
from app.teams.models import MemberStatus, Team, TeamMember, TeamStatus


def make_deadline(days=7):
    return datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=days)


def make_milestone(db, faculty, deadline=None):
    data = MilestoneCreate(
        title="Project Proposal",
        description="Submit the initial project proposal",
        deadline=deadline or make_deadline(),
        max_marks=100,
        weightage=20,
        rubric={"documentation": 40, "technical": 60},
    )
    return service.create_milestone(db, data, faculty)


def make_allocated_team(db, faculty, student):
    team = Team(
        name="Alpha",
        leader_id=student.id,
        guide_id=faculty.id,
        status=TeamStatus.ALLOCATED,
    )
    db.add(team)
    db.flush()

    member = TeamMember(
        team_id=team.id,
        user_id=student.id,
        status=MemberStatus.ACCEPTED,
    )
    db.add(member)
    db.commit()
    db.refresh(team)

    return team


# DELIV-01: Milestone management

def test_faculty_can_create_milestone(db, faculty):
    milestone = make_milestone(db, faculty)

    assert milestone.id is not None
    assert milestone.title == "Project Proposal"
    assert milestone.max_marks == 100
    assert milestone.weightage == 20


def test_student_cannot_create_milestone(db, student):
    data = MilestoneCreate(
        title="Project Proposal",
        deadline=make_deadline(),
        max_marks=100,
    )

    with pytest.raises(service.Forbidden):
        service.create_milestone(db, data, student)


def test_list_milestones(db, faculty):
    make_milestone(db, faculty, make_deadline(5))
    make_milestone(db, faculty, make_deadline(2))

    milestones = service.list_milestones(db)

    assert len(milestones) == 2
    assert milestones[0].deadline < milestones[1].deadline


def test_update_milestone(db, faculty):
    milestone = make_milestone(db, faculty)

    from app.deliverables.schemas import MilestoneUpdate

    updated = service.update_milestone(
        db,
        milestone.id,
        MilestoneUpdate(title="Final Project Proposal"),
        faculty,
    )

    assert updated.title == "Final Project Proposal"


def test_delete_milestone_without_submissions(db, faculty):
    milestone = make_milestone(db, faculty)

    service.delete_milestone(db, milestone.id, faculty)

    with pytest.raises(service.NotFound):
        service.get_milestone(db, milestone.id)


# DELIV-02 / DELIV-03: Submissions and versioning

def test_student_can_submit_deliverable(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    submission = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/proposal.pdf",
        ),
        student,
    )

    assert submission.version == 1
    assert submission.is_late is False
    assert submission.status == SubmissionStatus.SUBMITTED


def test_resubmission_increments_version(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    first = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/proposal_v1.pdf",
        ),
        student,
    )

    second = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/proposal_v2.pdf",
        ),
        student,
    )

    assert first.version == 1
    assert second.version == 2


def test_late_submission_is_detected(db, faculty, student):
    past_deadline = make_deadline(-1)
    milestone = make_milestone(db, faculty, past_deadline)
    team = make_allocated_team(db, faculty, student)

    submission = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/late_proposal.pdf",
        ),
        student,
    )

    assert submission.is_late is True


def test_non_member_cannot_submit(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    outsider = type("User", (), {"id": 99, "role": "student"})()

    with pytest.raises(service.Forbidden):
        service.submit_deliverable(
            db,
            SubmissionCreate(
                milestone_id=milestone.id,
                team_id=team.id,
                file_path="uploads/proposal.pdf",
            ),
            outsider,
        )


def test_submission_history(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    for filename in ("proposal_v1.pdf", "proposal_v2.pdf"):
        service.submit_deliverable(
            db,
            SubmissionCreate(
                milestone_id=milestone.id,
                team_id=team.id,
                file_path=f"uploads/{filename}",
            ),
            student,
        )

    history = service.get_submission_history(
        db, milestone.id, team.id, student
    )

    assert len(history) == 2
    assert history[0].version == 2
    assert history[1].version == 1


# DELIV-04: Faculty evaluation

def test_faculty_can_evaluate_submission(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    submission = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/proposal.pdf",
        ),
        student,
    )

    evaluated = service.evaluate_submission(
        db,
        submission.id,
        SubmissionEvaluation(
            marks=85,
            feedback="Good work",
            evaluation={"documentation": 35, "technical": 50},
        ),
        faculty,
    )

    assert evaluated.marks == 85
    assert evaluated.feedback == "Good work"
    assert evaluated.graded_by == faculty.id
    assert evaluated.status == SubmissionStatus.GRADED


def test_marks_cannot_exceed_maximum(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    submission = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/proposal.pdf",
        ),
        student,
    )

    with pytest.raises(service.Conflict, match="Marks cannot exceed"):
        service.evaluate_submission(
            db,
            submission.id,
            SubmissionEvaluation(marks=110),
            faculty,
        )


def test_wrong_faculty_cannot_evaluate(db, faculty, student):
    milestone = make_milestone(db, faculty)
    team = make_allocated_team(db, faculty, student)

    submission = service.submit_deliverable(
        db,
        SubmissionCreate(
            milestone_id=milestone.id,
            team_id=team.id,
            file_path="uploads/proposal.pdf",
        ),
        student,
    )

    other_faculty = type(
        "User", (), {"id": 11, "role": "faculty"}
    )()

    with pytest.raises(service.Forbidden):
        service.evaluate_submission(
            db,
            submission.id,
            SubmissionEvaluation(marks=80),
            other_faculty,
        )
