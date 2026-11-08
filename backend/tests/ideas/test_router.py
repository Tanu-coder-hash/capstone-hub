import pytest

from fastapi.testclient import TestClient

from app.main import app
from app.core.db import get_db
from app.core.db import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    TestingSessionLocal = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    # Do not use a context manager here: that would run the
    # application's normal startup against the development DB.
    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


faculty_headers = {
    "x-user-id": "10",
    "x-user-role": "faculty",
}

student_headers = {
    "x-user-id": "20",
    "x-user-role": "student",
}


def sample_idea():
    return {
        "title": "Smart Campus Energy Monitor",
        "description": (
            "Build a smart campus energy monitoring system "
            "that tracks electricity usage and predicts "
            "future consumption using machine learning."
        ),
        "domain": "IoT",
        "tech_stack": "Python, IoT, Machine Learning",
        "difficulty": "medium",
    }


def test_root_endpoint(client):
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["module"] == "Idea Bank and Voting"


def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_faculty_can_create_idea(client):
    response = client.post(
        "/api/v1/ideas",
        json=sample_idea(),
        headers=faculty_headers,
    )

    assert response.status_code == 201
    assert response.json()["status"] == "approved"


def test_student_cannot_create_faculty_idea(client):
    response = client.post(
        "/api/v1/ideas",
        json=sample_idea(),
        headers=student_headers,
    )

    assert response.status_code == 403


def test_student_can_propose_idea(client):
    response = client.post(
        "/api/v1/ideas/propose",
        json=sample_idea(),
        headers=student_headers,
    )

    assert response.status_code == 201
    assert response.json()["idea"]["status"] == "pending"


def test_faculty_can_view_pending_ideas(client):
    client.post(
        "/api/v1/ideas/propose",
        json=sample_idea(),
        headers=student_headers,
    )

    response = client.get(
        "/api/v1/ideas?status=pending",
        headers=faculty_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_student_cannot_view_pending_ideas(client):
    response = client.get(
        "/api/v1/ideas?status=pending",
        headers=student_headers,
    )

    assert response.status_code == 403


def test_student_can_view_approved_ideas(client):
    client.post(
        "/api/v1/ideas",
        json=sample_idea(),
        headers=faculty_headers,
    )

    response = client.get(
        "/api/v1/ideas",
        headers=student_headers,
    )

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_get_idea_endpoint(client):
    created = client.post(
        "/api/v1/ideas",
        json=sample_idea(),
        headers=faculty_headers,
    ).json()

    response = client.get(
        f"/api/v1/ideas/{created['id']}"
    )

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]


def test_get_missing_idea_endpoint(client):
    response = client.get("/api/v1/ideas/999")

    assert response.status_code == 404


def test_faculty_can_approve_idea(client):
    created = client.post(
        "/api/v1/ideas/propose",
        json=sample_idea(),
        headers=student_headers,
    ).json()["idea"]

    response = client.patch(
        f"/api/v1/ideas/{created['id']}/approve",
        headers=faculty_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "approved"


def test_faculty_can_reject_idea(client):
    created = client.post(
        "/api/v1/ideas/propose",
        json=sample_idea(),
        headers=student_headers,
    ).json()["idea"]

    response = client.patch(
        f"/api/v1/ideas/{created['id']}/reject",
        json={"reason": "Needs a clearer project scope."},
        headers=faculty_headers,
    )

    assert response.status_code == 200
    assert response.json()["status"] == "rejected"


def test_student_can_vote_and_withdraw(client):
    created = client.post(
        "/api/v1/ideas",
        json=sample_idea(),
        headers=faculty_headers,
    ).json()

    idea_id = created["id"]

    vote_response = client.post(
        f"/api/v1/ideas/{idea_id}/vote",
        headers=student_headers,
    )

    assert vote_response.status_code == 200
    assert vote_response.json()["votes"] == 1

    withdraw_response = client.delete(
        f"/api/v1/ideas/{idea_id}/vote",
        headers=student_headers,
    )

    assert withdraw_response.status_code == 200
    assert withdraw_response.json()["votes"] == 0


def test_trending_endpoint(client):
    created = client.post(
        "/api/v1/ideas",
        json=sample_idea(),
        headers=faculty_headers,
    ).json()

    client.post(
        f"/api/v1/ideas/{created['id']}/vote",
        headers=student_headers,
    )

    response = client.get(
        "/api/v1/ideas/trending?days=30&limit=10"
    )

    assert response.status_code == 200
    assert len(response.json()) == 1