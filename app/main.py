from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api import (
    routes_health,
    routes_parse,
    routes_recommend,
    routes_supplements,
)
from app.config import settings
from app.db.database import engine, Base
import app.models  # noqa: F401  registers Supplement table with SQLAlchemy


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    print("Shutting down...")


app = FastAPI(
    title="My Supplements API",
    description="Backend system for personalized supplement recommendations",
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(routes_health.router, tags=["Health"])
app.include_router(
    routes_supplements.router, prefix="/supplements", tags=["Supplements"]
)
app.include_router(routes_parse.router, prefix="/parse", tags=["Parsing"])
app.include_router(routes_recommend.router, prefix="/recommend", tags=["Recommend"])
