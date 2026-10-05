"""Controller for cancellation requests: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-19, HU-20): POST, GET /me, GET, POST /{id}/approve, POST /{id}/reject
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/cancellation-requests", tags=["cancellation requests"])
