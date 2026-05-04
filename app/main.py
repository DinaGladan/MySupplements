from fastapi import FastAPI
from app.api import routes_health  # routes_parse, routes_recommend
from app.config import settings
from contextlib import asynccontextmanager


@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    yield
    print("Shutting down...")


app = FastAPI(
    title="My Supplements API",
    description="Backend system for personalized supplement recommendations",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(routes_health.router)
# app.include_router(routes_parse.router, prefix="/parse")
# app.include_router(routes_recommend.router, prefix="/recommend")
