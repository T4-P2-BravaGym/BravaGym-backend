"""Controller for plans: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-07, HU-08): GET /plans, POST/PATCH/DELETE /plans
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.plan import PlanOut
from app.services.plan_service import list_active_plans

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get(
    "",
    response_model=list[PlanOut],
    summary="List active membership plans ordered by price",
)
def get_plans(db: Session = Depends(get_db)):
    return list_active_plans(db)
