import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.core.db import Base, get_db
from app.main import app

@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()

def h(user_id, role="student"):
    return {"x-user-id": str(user_id), "x-user-role": role}

FAC = h(10, "faculty")
IDEA = {
    "title": "Smart campus energy monitor",
    "description": "Track electricity usage across campus buildings with sensors",
    "domain": "IoT",
    "tech_stack": "Python",
    "difficulty": "medium",
}

def make_full_team(client):
    team = client.post("/api/v1/teams", json={"name": "Alpha"}, headers=h(20)).json()
    for uid in (21, 22):
        inv = client.post(
            f"/api/v1/teams/{team['id']}/invites",
            json={"user_id": uid},
            headers=h(20),
        ).json()
        client.post(
            f"/api/v1/teams/invites/{inv['id']}/respond",
            json={"accept": True},
            headers=h(uid),
        )
    return team["id"]

def test_full_allocation_flow(client):
    idea_id = client.post("/api/v1/ideas", json=IDEA, headers=FAC).json()["id"]
    team_id = make_full_team(client)
    r = client.get("/api/v1/teams/me", headers=h(21))
    assert r.status_code == 200 and r.json()["status"] == "complete"

    r = client.post(
        f"/api/v1/teams/{team_id}/idea-requests",
        json={"idea_ids": [idea_id]},
        headers=h(20),
    )
    assert r.status_code == 201
    req_id = r.json()[0]["id"]

    pending = client.get("/api/v1/teams/idea-requests/pending", headers=FAC).json()
    assert [p["id"] for p in pending] == [req_id]

    r = client.patch(f"/api/v1/teams/idea-requests/{req_id}/approve", headers=FAC)
    assert r.status_code == 200
    assert r.json()["status"] == "allocated" and r.json()["guide_id"] == 10
    assert client.get(f"/api/v1/ideas/{idea_id}").json()["status"] == "taken"

def test_validation_errors(client):
    assert client.post("/api/v1/teams", json={"name": "A"}, headers=h(20)).status_code == 422
    team_id = make_full_team(client)
    r = client.post(
        f"/api/v1/teams/{team_id}/idea-requests",
        json={"idea_ids": [1, 1]},
        headers=h(20),
    )
    assert r.status_code == 422
    r = client.post(
        f"/api/v1/teams/{team_id}/idea-requests",
        json={"idea_ids": [1, 2, 3, 4]},
        headers=h(20),
    )
    assert r.status_code == 422

def test_error_codes(client):
    assert client.get("/api/v1/teams/me", headers=h(20)).status_code == 404
    assert client.post("/api/v1/teams", json={"name": "Alpha"}, headers=FAC).status_code == 403
    team_id = make_full_team(client)
    r = client.post(f"/api/v1/teams/{team_id}/invites", json={"user_id": 30}, headers=h(21))
    assert r.status_code == 403
    assert client.patch("/api/v1/teams/idea-requests/999/approve", headers=FAC).status_code == 404

def test_invites_leave_and_dissolve(client):
    team = client.post("/api/v1/teams", json={"name": "Alpha"}, headers=h(20)).json()
    client.post(f"/api/v1/teams/{team['id']}/invites", json={"user_id": 21}, headers=h(20))
    invites = client.get("/api/v1/teams/invites/me", headers=h(21)).json()
    assert invites[0]["team_name"] == "Alpha"

    client.post(
        f"/api/v1/teams/invites/{invites[0]['id']}/respond",
        json={"accept": True},
        headers=h(21),
    )
    r = client.delete(f"/api/v1/teams/{team['id']}/members/me", headers=h(21))
    assert r.status_code == 200 and len([m for m in r.json()["members"] if m["status"] == "accepted"]) == 1
    assert client.delete(f"/api/v1/teams/{team['id']}", headers=h(20)).status_code == 204

def test_reject_request_and_list(client):
    idea_id = client.post("/api/v1/ideas", json=IDEA, headers=FAC).json()["id"]
    team_id = make_full_team(client)
    req_id = client.post(
        f"/api/v1/teams/{team_id}/idea-requests",
        json={"idea_ids": [idea_id]},
        headers=h(20),
    ).json()[0]["id"]
    r = client.patch(f"/api/v1/teams/idea-requests/{req_id}/reject", headers=FAC)
    assert r.status_code == 200 and r.json()["status"] == "rejected"
    listed = client.get(f"/api/v1/teams/{team_id}/idea-requests", headers=h(21)).json()
    assert listed[0]["status"] == "rejected"
