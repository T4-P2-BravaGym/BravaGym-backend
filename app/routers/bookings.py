"""Controller for bookings: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-12, HU-13): GET /bookings/me, POST /bookings/{id}/cancel
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/bookings", tags=["bookings"])
