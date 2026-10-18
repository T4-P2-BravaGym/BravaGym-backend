from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentAdmin
from app.core.openapi import error
from app.schemas.plan import (
    AdminPlanOut,
    AdminPlanPage,
    PlanCreate,
    PlanOut,
    PlanUpdate,
)
from app.services.plan_service import (
    create_plan,
    deactivate_plan,
    list_active_plans,
    list_admin_plans,
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


@router.get(
    "/admin",
    response_model=AdminPlanPage,
    summary="List active and retired membership plans for administration",
    responses={
        401: error("Missing, invalid or expired token"),
        403: error("Caller is not an admin or superadmin"),
        200: {
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": 1,
                                "name": "Basic",
                                "description": None,
                                "monthly_price_cents": 3900,
                                "monthly_price_formatted": "39,00 €",
                                "includes_personal_training": False,
                                "is_active": False,
                            }
                        ],
                        "total": 1,
                        "page": 1,
                        "size": 20,
                    }
                }
            }
        },
    },
)
def get_admin_plans(
    _: CurrentAdmin,
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
):
    items, total = list_admin_plans(db, page=page, size=size)
    return AdminPlanPage(
        items=[AdminPlanOut.model_validate(plan) for plan in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "",
    response_model=PlanOut,
    status_code=201,
    summary="Create a membership plan",
    responses={
        401: error("Missing, invalid or expired token"),
        403: error("Caller is not an admin or superadmin"),
        409: error("A plan with that name already exists"),
    },
)
def post_plan(
    body: PlanCreate,
    _: CurrentAdmin,
    db: Session = Depends(get_db),
):
    return create_plan(db, body)


@router.patch(
    "/{plan_id}",
    response_model=PlanOut,
    summary="Update a membership plan",
    responses={
        401: error("Missing, invalid or expired token"),
        403: error("Caller is not an admin or superadmin"),
        404: error("Plan not found"),
        409: error("A plan with that name already exists"),
    },
)
def patch_plan(
    plan_id: int,
    body: PlanUpdate,
    _: CurrentAdmin,
    db: Session = Depends(get_db),
):
    return update_plan(db, plan_id, body)


@router.delete(
    "/{plan_id}",
    response_model=PlanOut,
    summary="Deactivate a membership plan",
    description=(
        "Soft delete: sets is_active=false. Existing subscriptions remain unchanged."
    ),
    responses={
        401: error("Missing, invalid or expired token"),
        403: error("Caller is not an admin or superadmin"),
        404: error("Plan not found"),
    },
)
def delete_plan(
    plan_id: int,
    _: CurrentAdmin,
    db: Session = Depends(get_db),
):
    return deactivate_plan(db, plan_id)
