
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import Base, engine
from app.ideas import models
from app.ideas.router import router as ideas_router

from app.teams import models as team_models  # noqa: F401
from app.teams.router import router as teams_router

from app.notifications import models as notification_models
from app.notifications.router import router as notifications_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables during development.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Capstone Hub API",
    description="Idea Bank and Voting API",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def root():
    return {
        "message": "Capstone Hub API is running",
        "module": "Idea Bank and Voting",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


app.include_router(ideas_router)
app.include_router(teams_router)
app.include_router(notifications_router)