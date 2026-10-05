"""Controller for auth: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-02, HU-03): POST /auth/register, POST /auth/login
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])
