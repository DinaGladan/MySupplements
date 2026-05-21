from fastapi import FastAPI
from app.api import routes_health, routes_parse  # , routes_recommend, routes_nlg
from app.config import settings
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    print("Shutting down...")


app = FastAPI(
    title="My Supplements API",
    description="Backend system for personalized supplement recommendations",
    version=settings.app_version,
    lifespan=lifespan,
)

app.include_router(routes_health.router)
app.include_router(routes_parse.router, prefix="/parse", tags=["Parsing"])
