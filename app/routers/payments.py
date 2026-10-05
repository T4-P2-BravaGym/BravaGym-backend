"""Controller for payments: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-24, HU-26): GET /payments/me, POST /payments/{id}/pay, GET /payments, GET /payments/export, POST /payments/{id}/refund
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/payments", tags=["payments"])
