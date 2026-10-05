"""Controller for shop: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-23): POST /orders, GET /orders/me, POST /orders/{id}/cancel
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/orders", tags=["shop"])
