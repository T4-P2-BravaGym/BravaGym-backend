"""Controller for shop: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-21, HU-22): GET /products, GET /product-categories, admin CRUD
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/products", tags=["shop"])
