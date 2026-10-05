"""Controller for class types: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-11): GET/POST/PATCH/DELETE /class-types
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/class-types", tags=["class types"])
