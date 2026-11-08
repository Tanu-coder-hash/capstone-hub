import pytest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.db import Base
from app.ideas import models

from app.ideas import models
from app.teams import models as team_models

@pytest.fixture
def db():
    """
    Create a fresh in-memory SQLite database for each test.
    This does not touch backend/dev.db.
    """

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

    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


@pytest.fixture
def faculty():
    return type(
        "User",
        (),
        {"id": 10, "role": "faculty"}
    )()


@pytest.fixture
def student():
    return type(
        "User",
        (),
        {"id": 20, "role": "student"}
    )()


@pytest.fixture
def idea_data():
    from app.ideas.schemas import IdeaCreate

    return IdeaCreate(
        title="Smart Campus Energy Monitor",
        description=(
            "Build a smart campus energy monitoring system "
            "that tracks electricity usage and predicts "
            "future consumption using machine learning."
        ),
        domain="IoT",
        tech_stack="Python, IoT, Machine Learning",
        difficulty="medium",
    )