from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentAdmin, CurrentMember
from app.core.openapi import error
from app.schemas.payment import (
    DiscountCodeCreate,
    DiscountCodeOut,
    DiscountCodePage,
    DiscountCodeUpdate,
    DiscountValidationOut,
    PaymentConcept,
)
from app.services import discount_service

router = APIRouter(prefix="/discount-codes", tags=["discount codes"])

DbSession = Annotated[Session, Depends(get_db)]

ADMIN_ERRORS = {
    401: error("Not logged in"),
    403: error("Not admin"),
}


@router.get(
    "",
    response_model=DiscountCodePage,
    summary="List discount codes",
    responses=ADMIN_ERRORS,
)
def list_codes(
    admin: CurrentAdmin,  # only used to check the role
    db: DbSession,
    page: Annotated[int, Query(ge=1)] = 1,
    size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DiscountCodePage:
    items, total = discount_service.list_codes(db, page=page, size=size)
    return DiscountCodePage(items=items, total=total, page=page, size=size)


@router.post(
    "",
    response_model=DiscountCodeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a discount code",
    responses={
        **ADMIN_ERRORS,
        409: error("A code with that text already exists"),
    },
)
def create_code(
    data: DiscountCodeCreate, admin: CurrentAdmin, db: DbSession
) -> DiscountCodeOut:
    return discount_service.create_code(db, admin, data)


@router.get(
    "/{code}/validate",
    response_model=DiscountValidationOut,
    summary="Check a discount code before paying (RN-14)",
    responses={
        401: error("Not logged in"),
        422: {
            "description": "Unknown, inactive, out of dates, used up or for another concept"
        },
    },
)
def validate_code(
    code: str,
    member: CurrentMember,
    db: DbSession,
    concept: Annotated[
        PaymentConcept | None,
        Query(description="The payment's concept, to check a limited code (T-240)"),
    ] = None,
) -> DiscountValidationOut:
    valid = discount_service.get_valid_code(db, code, concept)
    return DiscountValidationOut(
        code=valid.code, percent_off=valid.percent_off, applies_to=valid.applies_to
    )


@router.patch(
    "/{code_id}",
    response_model=DiscountCodeOut,
    summary="Update a discount code",
    responses={**ADMIN_ERRORS, 404: error("The code does not exist")},
)
def update_code(
    code_id: int, changes: DiscountCodeUpdate, admin: CurrentAdmin, db: DbSession
) -> DiscountCodeOut:
    return discount_service.update_code(db, admin, code_id, changes)


@router.delete(
    "/{code_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a discount code",
    responses={**ADMIN_ERRORS, 404: error("The code does not exist")},
)
def deactivate_code(code_id: int, admin: CurrentAdmin, db: DbSession) -> None:
    discount_service.deactivate_code(db, admin, code_id)
