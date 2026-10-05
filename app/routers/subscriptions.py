"""Controller for subscriptions: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-09): POST /subscriptions, GET /subscriptions/me
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])
