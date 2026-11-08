from app.core.db import Base, SessionLocal, engine
from app.ideas import service as idea_service
from app.ideas.schemas import IdeaCreate
from app.main import app  # noqa: F401 (imports every model so all tables exist)
from app.teams import service as team_service

def user(user_id, role="student"):
    return type("User", (), {"id": user_id, "role": role})()

FACULTY_A, FACULTY_B = user(10, "faculty"), user(11, "faculty")

IDEAS = [
    (
        "Smart Campus Energy Monitor",
        "IoT",
        "Track electricity use in campus buildings with sensors and predict monthly consumption.",
    ),
    (
        "AI Timetable Generator",
        "AI/ML",
        "Generate clash-free class timetables from faculty availability and room capacity constraints.",
    ),
    (
        "Lost and Found Portal",
        "Web",
        "Students report lost and found items with photos and get matched automatically by category and location.",
    ),
    (
        "Placement Readiness Tracker",
        "Data",
        "Dashboard showing each student's aptitude, coding and interview practice scores before placements.",
    ),
]

def main():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        ideas = []
        for i, (title, domain, description) in enumerate(IDEAS):
            owner = FACULTY_A if i % 2 == 0 else FACULTY_B
            data = IdeaCreate(
                title=title,
                description=description,
                domain=domain,
                tech_stack="Python, React",
                difficulty="medium",
            )
            ideas.append(idea_service.create_idea(db, data, owner))

        # Team Alpha: complete, requested idea 1 (ready for the approval demo)
        alpha = team_service.create_team(db, "Team Alpha", user(20))
        for sid in (21, 22):
            inv = team_service.invite_member(db, alpha.id, sid, user(20))
            team_service.respond_invite(db, inv.id, True, user(sid))
        team_service.request_ideas(db, alpha.id, [ideas[0].id, ideas[1].id], user(20))

        # Team Beta: complete, also wants idea 1 (demonstrates conflict)
        beta = team_service.create_team(db, "Team Beta", user(30))
        for sid in (31, 32):
            inv = team_service.invite_member(db, beta.id, sid, user(30))
            team_service.respond_invite(db, inv.id, True, user(sid))
        team_service.request_ideas(db, beta.id, [ideas[0].id], user(30))

        # Team Gamma: still forming, one pending invite for student 41
        gamma = team_service.create_team(db, "Team Gamma", user(40))
        team_service.invite_member(db, gamma.id, 41, user(40))

        print("Seeded 4 ideas and 3 teams.")
    finally:
        db.close()

if __name__ == "__main__":
    main()