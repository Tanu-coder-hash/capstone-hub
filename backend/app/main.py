
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db import Base, engine

# Import models so SQLAlchemy registers all tables
from app.ideas import models
from app.teams import models as team_models
from app.deliverables import models as deliverable_models

# Import routers
from app.ideas.router import router as ideas_router
from app.teams.router import router as teams_router
from app.deliverables.router import router as deliverables_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create database tables during development.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Capstone Hub API",
    description="Capstone Hub - Ideas, Teams and Deliverables",
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


# Register all module routers
app.include_router(ideas_router)
app.include_router(teams_router)
app.include_router(deliverables_router)
