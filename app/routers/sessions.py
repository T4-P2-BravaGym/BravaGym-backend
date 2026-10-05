"""Controller for sessions: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-10, HU-11, HU-12): GET/POST/PATCH /sessions, POST /sessions/{id}/cancel, GET/POST /sessions/{id}/bookings
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/sessions", tags=["sessions"])
