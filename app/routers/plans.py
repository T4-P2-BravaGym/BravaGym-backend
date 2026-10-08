"""Controller for plans: receives the request, checks permissions, calls the service, returns a schema.

TODO(HU-07, HU-08): GET /plans, POST/PATCH/DELETE /plans
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.models.enums import RoleName
from app.schemas.plan import PlanCreate, PlanOut, PlanUpdate
from app.services.plan_service import (
    create_plan,
    deactivate_plan,
    list_active_plans,
    update_plan,
)

router = APIRouter(prefix="/plans", tags=["plans"])


@router.get(
    "",
    response_model=list[PlanOut],
    summary="List active membership plans ordered by price",
    responses={
        200: {
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": 1,
                            "name": "Premium",
                            "description": "Incluye entrenamiento personal",
                            "monthly_price_cents": 5990,
                            "includes_personal_training": True,
                            "monthly_price_formatted": "59,90 €",
                        }
                    ]
                }
            }
        }
    },
)
def get_plans(db: Session = Depends(get_db)):
    return list_active_plans(db)


@router.post(
    "",
    response_model=PlanOut,
    status_code=201,
    summary="Create a membership plan",
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not an admin or superadmin"},
        409: {"description": "A plan with that name already exists"},
    },
)
def post_plan(
    body: PlanCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN)),
):
    return create_plan(db, body)


@router.patch(
    "/{plan_id}",
    response_model=PlanOut,
    summary="Update a membership plan",
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not an admin or superadmin"},
        404: {"description": "Plan not found"},
        409: {"description": "A plan with that name already exists"},
    },
)
def patch_plan(
    plan_id: int,
    body: PlanUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN)),
):
    return update_plan(db, plan_id, body)


@router.delete(
    "/{plan_id}",
    response_model=PlanOut,
    summary="Deactivate a membership plan",
    description=(
        "Soft delete: sets is_active=false. "
        "Existing subscriptions remain unchanged."
    ),
    responses={
        401: {"description": "Missing, invalid or expired token"},
        403: {"description": "Caller is not an admin or superadmin"},
        404: {"description": "Plan not found"},
    },
)
def delete_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN)),
):
    return deactivate_plan(db, plan_id)
