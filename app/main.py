"""Brava API entry point. Run with: uvicorn app.main:app --reload"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import models  # noqa: F401  (registers every table in Base.metadata)
from app.core.config import get_settings
from app.core.database import Base, engine
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.routers import api_routers

settings = get_settings()
setup_logging(settings.debug)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # No migrations in this project: create the tables on startup if they do not exist.
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="API de Brava, gimnasio de fuerza para mujeres.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

for router in api_routers:
    app.include_router(router, prefix="/api/v1")


@app.get("/health", tags=["health"], summary="Health check")
def health() -> dict[str, str]:
    """Used by Docker and CI to know the API is up."""
    return {"status": "ok"}
