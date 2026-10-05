"""Controller for routines: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-17, HU-18): POST/GET/PATCH/DELETE /routines, /routines/{id}/exercises, GET /routines/me
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/routines", tags=["routines"])
