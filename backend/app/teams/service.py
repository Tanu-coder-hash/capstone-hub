from sqlalchemy import func, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.ideas import service as idea_service
from app.ideas.models import Idea, IdeaStatus, utcnow
from app.teams.models import (
    CURRENT_SEMESTER,
    MAX_TEAM_SIZE,
    MIN_TEAM_SIZE,
    IdeaRequest,
    MemberStatus,
    RequestStatus,
    Team,
    TeamMember,
    TeamStatus,
)

#
# Custom exceptions (matching Idea module pattern)
#
class TeamError(Exception):
    status_code = 400

class NotFound(TeamError):
    status_code = 404

class Forbidden(TeamError):
    status_code = 403

class Conflict(TeamError):
    status_code = 409

#
# Internal helper functions
#
def _require(user, role: str):
    if user.role != role:
        raise Forbidden(f"Only {role} users can do this")

def _get_team(db: Session, team_id: int) -> Team:
    team = db.get(Team, team_id)
    if team is None or team.status == TeamStatus.DISSOLVED:
        raise NotFound("Team not found")
    return team

def _require_leader(team: Team, user):
    if team.leader_id != user.id:
        raise Forbidden("Only the team leader can do this")

def accepted_count(db: Session, team_id: int) -> int:
    return db.scalar(
        select(func.count(TeamMember.id)).where(
            TeamMember.team_id == team_id,
            TeamMember.status == MemberStatus.ACCEPTED,
        )
    ) or 0

def _invited_count(db: Session, team_id: int) -> int:
    return db.scalar(
        select(func.count(TeamMember.id)).where(
            TeamMember.team_id == team_id,
            TeamMember.status == MemberStatus.INVITED,
        )
    ) or 0

def _refresh_status(db: Session, team: Team):
    """Update status between FORMING and COMPLETE based on accepted count."""
    if team.status in (TeamStatus.ALLOCATED, TeamStatus.DISSOLVED):
        return
    db.flush()
    if accepted_count(db, team.id) >= MIN_TEAM_SIZE:
        team.status = TeamStatus.COMPLETE
    else:
        team.status = TeamStatus.FORMING

#
# Shared functions used by Members 3 and 4
#
def get_team_for_user(
    db: Session,
    user_id: int,
    semester: str = CURRENT_SEMESTER,
) -> Team | None:
    return db.scalar(
        select(Team)
        .join(TeamMember)
        .where(
            TeamMember.user_id == user_id,
            TeamMember.status == MemberStatus.ACCEPTED,
            TeamMember.semester == semester,
            Team.status != TeamStatus.DISSOLVED,
        )
    )

def get_guide(db: Session, team_id: int) -> int | None:
    return _get_team(db, team_id).guide_id

#
# TEAM-01: Create team
#
def create_team(db: Session, name: str, user) -> Team:
    _require(user, "student")
    if get_team_for_user(db, user.id):
        raise Conflict("You are already in a team")
    team = Team(name=name.strip(), leader_id=user.id)
    team.members.append(
        TeamMember(
            user_id=user.id,
            status=MemberStatus.ACCEPTED,
            responded_at=utcnow(),
        )
    )
    db.add(team)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("Team name already taken")
    db.refresh(team)
    return team

def get_my_team(db: Session, user) -> Team:
    team = get_team_for_user(db, user.id)
    if team is None:
        raise NotFound("You are not in a team yet")
    return team

#
# TEAM-02 / TEAM-03: Invitations
#
def invite_member(db: Session, team_id: int, invitee_id: int, user) -> TeamMember:
    team = _get_team(db, team_id)
    _require_leader(team, user)
    if team.status == TeamStatus.ALLOCATED:
        raise Conflict("Cannot invite after an idea is allocated")
    if invitee_id == user.id:
        raise Conflict("You cannot invite yourself")
    if get_team_for_user(db, invitee_id):
        raise Conflict("This student is already in a team")
    if accepted_count(db, team.id) + _invited_count(db, team.id) >= MAX_TEAM_SIZE:
        raise Conflict(f"A team can have at most {MAX_TEAM_SIZE} members")

    existing = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.user_id == invitee_id,
        )
    )
    if existing is not None:
        if existing.status != MemberStatus.REJECTED:
            raise Conflict("This student has already been invited")
        existing.status = MemberStatus.INVITED
        existing.invited_at = utcnow()
        existing.responded_at = None
        db.commit()
        return existing

    invite = TeamMember(team_id=team.id, user_id=invitee_id, status=MemberStatus.INVITED)
    db.add(invite)
    db.commit()
    db.refresh(invite)
    return invite

def list_my_invites(db: Session, user) -> list[dict]:
    rows = db.execute(
        select(TeamMember, Team.name)
        .join(Team)
        .where(
            TeamMember.user_id == user.id,
            TeamMember.status == MemberStatus.INVITED,
            Team.status != TeamStatus.DISSOLVED,
        )
        .order_by(TeamMember.invited_at.desc())
    ).all()
    return [
        {
            "id": member.id,
            "team_id": member.team_id,
            "team_name": team_name,
            "status": member.status,
        }
        for member, team_name in rows
    ]

def respond_invite(db: Session, membership_id: int, accept: bool, user) -> TeamMember:
    invite = db.get(TeamMember, membership_id)
    if invite is None or invite.user_id != user.id:
        raise NotFound("Invitation not found")
    if invite.status != MemberStatus.INVITED:
        raise Conflict("This invitation has already been answered")

    team = _get_team(db, invite.team_id)
    invite.responded_at = utcnow()

    if not accept:
        invite.status = MemberStatus.REJECTED
        db.commit()
        return invite

    if get_team_for_user(db, user.id):
        raise Conflict("Leave your current team before joining another")
    if accepted_count(db, team.id) >= MAX_TEAM_SIZE:
        raise Conflict("Team is already full")

    invite.status = MemberStatus.ACCEPTED
    try:
        _refresh_status(db, team)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise Conflict("You are already in a team")
    return invite

#
# TEAM-07: Leave or dissolve (before allocation only)
#
def leave_team(db: Session, team_id: int, user) -> Team:
    team = _get_team(db, team_id)
    if team.status == TeamStatus.ALLOCATED:
        raise Conflict("Cannot leave after an idea is allocated")
    if team.leader_id == user.id:
        raise Conflict("The leader cannot leave; dissolve the team instead")

    member = db.scalar(
        select(TeamMember).where(
            TeamMember.team_id == team.id,
            TeamMember.user_id == user.id,
            TeamMember.status == MemberStatus.ACCEPTED,
        )
    )
    if member is None:
        raise NotFound("You are not a member of this team")

    db.delete(member)
    _refresh_status(db, team)
    if team.status == TeamStatus.FORMING:
        _cancel_pending_requests(db, team_id=team.id)
    db.commit()
    return team

def dissolve_team(db: Session, team_id: int, user) -> None:
    team = _get_team(db, team_id)
    _require_leader(team, user)
    if team.status == TeamStatus.ALLOCATED:
        raise Conflict("Cannot dissolve a team after an idea is allocated")

    _cancel_pending_requests(db, team_id=team.id)
    for member in list(team.members):
        db.delete(member)
    team.status = TeamStatus.DISSOLVED
    db.commit()

def _cancel_pending_requests(db: Session, team_id=None, idea_id=None, keep_id=None):
    conditions = [IdeaRequest.status == RequestStatus.PENDING]
    if keep_id is not None:
        conditions.append(IdeaRequest.id != keep_id)
    targets = []
    if team_id is not None:
        targets.append(IdeaRequest.team_id == team_id)
    if idea_id is not None:
        targets.append(IdeaRequest.idea_id == idea_id)
    conditions.append(or_(*targets))
    db.execute(
        update(IdeaRequest)
        .where(*conditions)
        .values(status=RequestStatus.CANCELLED)
        .execution_options(synchronize_session="fetch")
    )

#
# TEAM-04: Request up to 3 ideas
#
def request_ideas(db: Session, team_id: int, idea_ids: list[int], user) -> list[IdeaRequest]:
    team = _get_team(db, team_id)
    _require_leader(team, user)
    if team.status == TeamStatus.ALLOCATED:
        raise Conflict("Your team already has an idea")
    if team.status != TeamStatus.COMPLETE:
        raise Conflict(f"A team needs at least {MIN_TEAM_SIZE} members to request ideas")

    for idea_id in idea_ids:
        idea = db.get(Idea, idea_id)
        if idea is None:
            raise NotFound(f"Idea {idea_id} not found")
        if idea.status != IdeaStatus.APPROVED:
            raise Conflict(f"Idea {idea_id} is not available")

    # Cancel older pending requests before registering the new preference list
    db.execute(
        update(IdeaRequest)
        .where(IdeaRequest.team_id == team.id)
        .where(IdeaRequest.status == RequestStatus.PENDING)
        .values(status=RequestStatus.CANCELLED)
        .execution_options(synchronize_session="fetch")
    )

    created = []
    for preference, idea_id in enumerate(idea_ids, start=1):
        existing = db.scalar(
            select(IdeaRequest).where(
                IdeaRequest.team_id == team.id,
                IdeaRequest.idea_id == idea_id,
            )
        )
        if existing is not None:
            if existing.status == RequestStatus.REJECTED:
                raise Conflict(f"Idea {idea_id} was already rejected for your team")
            existing.status = RequestStatus.PENDING
            existing.preference = preference
            created.append(existing)
        else:
            req = IdeaRequest(team_id=team.id, idea_id=idea_id, preference=preference)
            db.add(req)
            created.append(req)

    db.commit()
    for req in created:
        db.refresh(req)
    return created

def list_team_requests(db: Session, team_id: int, user) -> list[IdeaRequest]:
    team = _get_team(db, team_id)
    if get_team_for_user(db, user.id) is not team and user.role != "faculty":
        raise Forbidden("You can only view your own team's requests")
    return list(
        db.scalars(
            select(IdeaRequest)
            .where(IdeaRequest.team_id == team.id)
            .order_by(IdeaRequest.preference)
        )
    )

#
# TEAM-05 / TEAM-06: Faculty reviews requests
#
def pending_requests_for_faculty(db: Session, user) -> list[IdeaRequest]:
    _require(user, "faculty")
    return list(
        db.scalars(
            select(IdeaRequest)
            .join(Idea, Idea.id == IdeaRequest.idea_id)
            .where(
                Idea.posted_by == user.id,
                IdeaRequest.status == RequestStatus.PENDING,
            )
            .order_by(IdeaRequest.created_at)
        )
    )

def _get_request_for_owner(db: Session, request_id: int, user):
    _require(user, "faculty")
    req = db.get(IdeaRequest, request_id)
    if req is None:
        raise NotFound("Request not found")
    idea = db.get(Idea, req.idea_id)
    if idea.posted_by != user.id:
        raise Forbidden("Only the faculty who posted this idea can review it")
    if req.status != RequestStatus.PENDING:
        raise Conflict("This request has already been reviewed")
    return req

def approve_request(db: Session, request_id: int, user) -> Team:
    req = _get_request_for_owner(db, request_id, user)
    team = _get_team(db, req.team_id)
    if team.status != TeamStatus.COMPLETE:
        raise Conflict("Team is not eligible for allocation")

    # Layer 2: Lock the idea row in PostgreSQL for concurrency safety
    db.execute(select(Idea).where(Idea.id == req.idea_id).with_for_update())

    try:
        # Layer 1: Call Member 1's service (marks APPROVED -> TAKEN)
        idea_service.mark_taken(db, req.idea_id, team.id)
        team.idea_id = req.idea_id
        team.guide_id = user.id
        team.status = TeamStatus.ALLOCATED
        req.status = RequestStatus.APPROVED
        req.reviewed_by = user.id

        # Cancel remaining requests
        _cancel_pending_requests(db, team_id=team.id, idea_id=req.idea_id, keep_id=req.id)
        db.commit()
    except idea_service.IdeaError:
        db.rollback()
        raise Conflict("Idea already allocated")
    except IntegrityError:
        # Layer 3: Database UNIQUE constraint enforcement
        db.rollback()
        raise Conflict("Idea already allocated")

    db.refresh(team)
    return team

def reject_request(db: Session, request_id: int, user) -> IdeaRequest:
    req = _get_request_for_owner(db, request_id, user)
    req.status = RequestStatus.REJECTED
    req.reviewed_by = user.id
    db.commit()
    return req
