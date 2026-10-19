from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app import models
from app.core.cache import configure_response_cache
from app.core.config import get_settings
from app.core.exceptions import UnexpectedErrorMiddleware, register_exception_handlers
from app.core.logging import setup_logging
from app.core.openapi import API_DESCRIPTION, OPENAPI_TAGS
from app.core.media import MEDIA_URL_PREFIX, PRODUCT_IMAGES_DIR
from app.core.rate_limit import configure_auth_rate_limits
from app.routers import api_routers

settings = get_settings()
setup_logging(settings.debug)
configure_response_cache(settings.cache_ttl_seconds)
configure_auth_rate_limits(
    login_max_attempts=settings.auth_login_max_attempts,
    login_window_seconds=settings.auth_login_window_seconds,
    register_max_attempts=settings.auth_register_max_attempts,
    register_window_seconds=settings.auth_register_window_seconds,
)


app = FastAPI(
    title=settings.app_name,
    version="0.2.0",
    description=API_DESCRIPTION,
    openapi_tags=OPENAPI_TAGS,
)

app.add_middleware(UnexpectedErrorMiddleware)
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

(settings.media_root / PRODUCT_IMAGES_DIR).mkdir(parents=True, exist_ok=True)
app.mount(MEDIA_URL_PREFIX, StaticFiles(directory=settings.media_root), name="media")

@app.get("/health", tags=["health"], summary="Health check")
def health() -> dict[str, str]:
    return {"status": "ok"}
