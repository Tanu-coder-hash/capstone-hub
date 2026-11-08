import pytest
from sqlalchemy.exc import IntegrityError
from app.ideas import service as idea_service
from app.ideas.models import IdeaStatus
from app.ideas.schemas import IdeaCreate
from app.teams import service
from app.teams.models import MemberStatus, RequestStatus, Team, TeamStatus

def user(user_id, role="student"):
    return type("User", (), {"id": user_id, "role": role})()

FACULTY = user(10, "faculty")
OTHER_FACULTY = user(11, "faculty")
LEADER, S2, S3, S4, S5 = (user(i) for i in (20, 21, 22, 23, 24))

def new_idea(db, title="Smart campus energy monitor", owner=FACULTY):
    data = IdeaCreate(
        title=title,
        description=f"{title} with sensors dashboards and prediction models",
        domain="IoT",
        tech_stack="Python",
        difficulty="medium",
    )
    return idea_service.create_idea(db, data, owner)

def full_team(db, name="Alpha", leader=LEADER, others=(S2, S3)):
    team = service.create_team(db, name, leader)
    for member in others:
        invite = service.invite_member(db, team.id, member.id, leader)
        service.respond_invite(db, invite.id, True, member)
    return team

# TEAM-01
def test_student_creates_team_and_is_leader(db):
    team = service.create_team(db, "Alpha", LEADER)
    assert team.leader_id == LEADER.id
    assert team.status == TeamStatus.FORMING
    assert service.accepted_count(db, team.id) == 1

def test_faculty_cannot_create_team(db):
    with pytest.raises(service.Forbidden):
        service.create_team(db, "Alpha", FACULTY)

def test_cannot_create_second_team(db):
    service.create_team(db, "Alpha", LEADER)
    with pytest.raises(service.Conflict, match="already in a team"):
        service.create_team(db, "Beta", LEADER)

def test_duplicate_team_name(db):
    service.create_team(db, "Alpha", LEADER)
    with pytest.raises(service.Conflict, match="name already taken"):
        service.create_team(db, "Alpha", S2)

def test_get_my_team(db):
    with pytest.raises(service.NotFound):
        service.get_my_team(db, LEADER)
    team = service.create_team(db, "Alpha", LEADER)
    assert service.get_my_team(db, LEADER).id == team.id

# TEAM-02 / TEAM-03
def test_invite_accept_makes_team_complete(db):
    team = full_team(db)
    assert team.status == TeamStatus.COMPLETE
    assert service.accepted_count(db, team.id) == 3

def test_only_leader_can_invite(db):
    team = service.create_team(db, "Alpha", LEADER)
    with pytest.raises(service.Forbidden):
        service.invite_member(db, team.id, S3.id, S2)

def test_cannot_invite_self_or_twice(db):
    team = service.create_team(db, "Alpha", LEADER)
    with pytest.raises(service.Conflict, match="yourself"):
        service.invite_member(db, team.id, LEADER.id, LEADER)
    service.invite_member(db, team.id, S2.id, LEADER)
    with pytest.raises(service.Conflict, match="already been invited"):
        service.invite_member(db, team.id, S2.id, LEADER)

def test_cannot_invite_student_in_another_team(db):
    service.create_team(db, "Beta", S5)
    team = service.create_team(db, "Alpha", LEADER)
    with pytest.raises(service.Conflict, match="already in a team"):
        service.invite_member(db, team.id, S5.id, LEADER)

def test_team_size_limit(db):
    team = full_team(db, others=(S2, S3, S4))  # 4 members
    with pytest.raises(service.Conflict, match="at most 4"):
        service.invite_member(db, team.id, S5.id, LEADER)

def test_reject_then_reinvite(db):
    team = service.create_team(db, "Alpha", LEADER)
    invite = service.invite_member(db, team.id, S2.id, LEADER)
    service.respond_invite(db, invite.id, False, S2)
    assert invite.status == MemberStatus.REJECTED
    again = service.invite_member(db, team.id, S2.id, LEADER)
    assert again.status == MemberStatus.INVITED

def test_respond_invite_errors(db):
    team = service.create_team(db, "Alpha", LEADER)
    invite = service.invite_member(db, team.id, S2.id, LEADER)
    with pytest.raises(service.NotFound):
        service.respond_invite(db, invite.id, True, S3)
    with pytest.raises(service.NotFound):
        service.respond_invite(db, 999, True, S2)
    service.respond_invite(db, invite.id, True, S2)
    with pytest.raises(service.Conflict, match="already been answered"):
        service.respond_invite(db, invite.id, True, S2)

def test_cannot_accept_two_teams(db):
    a = service.create_team(db, "Alpha", LEADER)
    b = service.create_team(db, "Beta", S5)
    inv_a = service.invite_member(db, a.id, S2.id, LEADER)
    inv_b = service.invite_member(db, b.id, S2.id, S5)
    service.respond_invite(db, inv_a.id, True, S2)
    with pytest.raises(service.Conflict, match="Leave your current team"):
        service.respond_invite(db, inv_b.id, True, S2)

def test_list_my_invites(db):
    team = service.create_team(db, "Alpha", LEADER)
    service.invite_member(db, team.id, S2.id, LEADER)
    invites = service.list_my_invites(db, S2)
    assert len(invites) == 1 and invites[0]["team_name"] == "Alpha"

# TEAM-07
def test_member_leaves_and_team_becomes_forming(db):
    team = full_team(db)
    service.leave_team(db, team.id, S3)
    assert team.status == TeamStatus.FORMING
    assert service.get_team_for_user(db, S3.id) is None

def test_leader_cannot_leave(db):
    team = full_team(db)
    with pytest.raises(service.Conflict, match="leader cannot leave"):
        service.leave_team(db, team.id, LEADER)

def test_non_member_cannot_leave(db):
    team = full_team(db)
    with pytest.raises(service.NotFound):
        service.leave_team(db, team.id, S5)

def test_dissolve_frees_members(db):
    team = full_team(db)
    with pytest.raises(service.Forbidden):
        service.dissolve_team(db, team.id, S2)
    service.dissolve_team(db, team.id, LEADER)
    assert service.get_team_for_user(db, S2.id) is None
    with pytest.raises(service.NotFound):
        service.get_guide(db, team.id)
    assert service.create_team(db, "Gamma", S2).leader_id == S2.id

# TEAM-04
def test_request_ideas_needs_complete_team(db):
    idea = new_idea(db)
    team = service.create_team(db, "Alpha", LEADER)
    with pytest.raises(service.Conflict, match="at least 3"):
        service.request_ideas(db, team.id, [idea.id], LEADER)

def test_request_ideas_validates_ideas(db):
    team = full_team(db)
    with pytest.raises(service.NotFound):
        service.request_ideas(db, team.id, [999], LEADER)
    pending, _ = idea_service.propose_idea(
        db,
        IdeaCreate(
            title="Student proposal idea",
            description="A pending idea nobody approved yet",
            domain="Web",
            tech_stack="",
            difficulty="easy",
        ),
        S5,
    )
    with pytest.raises(service.Conflict, match="not available"):
        service.request_ideas(db, team.id, [pending.id], LEADER)

def test_new_preferences_replace_old(db):
    i1 = new_idea(db, "Smart parking finder")
    i2 = new_idea(db, "Hostel complaint tracker")
    team = full_team(db)
    service.request_ideas(db, team.id, [i1.id, i2.id], LEADER)
    service.request_ideas(db, team.id, [i2.id], LEADER)
    requests = service.list_team_requests(db, team.id, LEADER)
    status_map = {r.idea_id: r.status for r in requests}
    assert status_map == {i1.id: RequestStatus.CANCELLED, i2.id: RequestStatus.PENDING}

def test_outsider_cannot_view_team_requests(db):
    team = full_team(db)
    with pytest.raises(service.Forbidden):
        service.list_team_requests(db, team.id, S5)
    assert service.list_team_requests(db, team.id, FACULTY) == []

# TEAM-05 / TEAM-06
def test_faculty_approves_and_idea_is_locked(db):
    idea = new_idea(db)
    team = full_team(db)
    [req] = service.request_ideas(db, team.id, [idea.id], LEADER)
    assert [r.id for r in service.pending_requests_for_faculty(db, FACULTY)] == [req.id]
    assert service.pending_requests_for_faculty(db, OTHER_FACULTY) == []
    team = service.approve_request(db, req.id, FACULTY)
    assert team.status == TeamStatus.ALLOCATED
    assert team.idea_id == idea.id and service.get_guide(db, team.id) == FACULTY.id
    assert idea_service.get_idea(db, idea.id).status == IdeaStatus.TAKEN

def test_only_idea_owner_can_review(db):
    idea = new_idea(db)
    team = full_team(db)
    [req] = service.request_ideas(db, team.id, [idea.id], LEADER)
    with pytest.raises(service.Forbidden):
        service.approve_request(db, req.id, OTHER_FACULTY)
    with pytest.raises(service.Forbidden):
        service.approve_request(db, req.id, LEADER)
    with pytest.raises(service.NotFound):
        service.approve_request(db, 999, FACULTY)

def test_second_team_cannot_get_same_idea(db):
    idea = new_idea(db)
    a = full_team(db, "Alpha", LEADER, (S2, S3))
    b = full_team(db, "Beta", S4, (S5, user(25)))
    [req_a] = service.request_ideas(db, a.id, [idea.id], LEADER)
    [req_b] = service.request_ideas(db, b.id, [idea.id], S4)
    service.approve_request(db, req_a.id, FACULTY)
    db.refresh(req_b)
    assert req_b.status == RequestStatus.CANCELLED
    with pytest.raises(service.Conflict, match="already been reviewed"):
        service.approve_request(db, req_b.id, FACULTY)

def test_mark_taken_failure_is_reported_as_conflict(db):
    idea = new_idea(db)
    team = full_team(db)
    [req] = service.request_ideas(db, team.id, [idea.id], LEADER)
    idea_service.mark_taken(db, idea.id, team_id=999)
    db.commit()
    with pytest.raises(service.Conflict, match="Idea already allocated"):
        service.approve_request(db, req.id, FACULTY)
    assert db.get(Team, team.id).status == TeamStatus.COMPLETE

def test_database_blocks_two_teams_with_same_idea(db):
    idea = new_idea(db)
    db.add_all([
        Team(name="T1", leader_id=1, idea_id=idea.id),
        Team(name="T2", leader_id=2, idea_id=idea.id),
    ])
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

def test_allocated_team_is_frozen(db):
    idea = new_idea(db)
    team = full_team(db)
    [req] = service.request_ideas(db, team.id, [idea.id], LEADER)
    service.approve_request(db, req.id, FACULTY)
    with pytest.raises(service.Conflict):
        service.leave_team(db, team.id, S2)
    with pytest.raises(service.Conflict):
        service.dissolve_team(db, team.id, LEADER)
    with pytest.raises(service.Conflict):
        service.invite_member(db, team.id, S5.id, LEADER)
    with pytest.raises(service.Conflict, match="already has an idea"):
        service.request_ideas(db, team.id, [idea.id], LEADER)

def test_reject_request(db):
    idea = new_idea(db)
    team = full_team(db)
    [req] = service.request_ideas(db, team.id, [idea.id], LEADER)
    assert service.reject_request(db, req.id, FACULTY).status == RequestStatus.REJECTED
    with pytest.raises(service.Conflict, match="already rejected"):
        service.request_ideas(db, team.id, [idea.id], LEADER)
