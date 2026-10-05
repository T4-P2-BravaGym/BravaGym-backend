"""Controller for users: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-04, HU-05, HU-06): GET/PATCH /users/me, GET /users, PATCH /users/{id}/role
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])
