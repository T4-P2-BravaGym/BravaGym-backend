"""Controller for trainers: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-15): GET /trainers, PATCH /trainers/me/profile
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/trainers", tags=["trainers"])
