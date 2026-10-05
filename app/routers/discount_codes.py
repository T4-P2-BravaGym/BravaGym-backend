"""Controller for discount codes: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-25): CRUD, GET /discount-codes/{code}/validate
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/discount-codes", tags=["discount codes"])
