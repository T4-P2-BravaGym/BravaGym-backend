"""Controller for discount codes: receives the request, checks permissions, calls the service, returns a schema (HU-25).
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember, require_roles
from app.models import User
from app.models.enums import RoleName
from app.schemas.payment import (
    DiscountCodeCreate,
    DiscountCodeOut,
    DiscountCodePage,
    DiscountCodeUpdate,
    DiscountValidationOut,
)
from app.services import discount_service

router = APIRouter(prefix="/discount-codes", tags=["discount codes"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[User, Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))]
ADMIN_ERRORS = {401: {"description": "Not logged in"}, 403: {"description": "Not admin"}}


@router.get("", response_model=DiscountCodePage, summary="List discount codes", responses=ADMIN_ERRORS)
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
    responses={**ADMIN_ERRORS, 409: {"description": "A code with that text already exists"}},
)
def create_code(data: DiscountCodeCreate, admin: CurrentAdmin, db: DbSession) -> DiscountCodeOut:
    return discount_service.create_code(db, admin, data)


@router.get(
    "/{code}/validate",
    response_model=DiscountValidationOut,
    summary="Check a discount code before paying (RN-14)",
    responses={401: {"description": "Not logged in"}, 422: {"description": "Unknown, inactive, out of dates or used up"}},
)
def validate_code(code: str, member: CurrentMember, db: DbSession) -> DiscountValidationOut:
    valid = discount_service.get_valid_code(db, code)
    return DiscountValidationOut(code=valid.code, percent_off=valid.percent_off)


@router.patch(
    "/{code_id}",
    response_model=DiscountCodeOut,
    summary="Update a discount code",
    responses={**ADMIN_ERRORS, 404: {"description": "The code does not exist"}},
)
def update_code(code_id: int, changes: DiscountCodeUpdate, admin: CurrentAdmin, db: DbSession) -> DiscountCodeOut:
    return discount_service.update_code(db, admin, code_id, changes)


@router.delete(
    "/{code_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a discount code",
    responses={**ADMIN_ERRORS, 404: {"description": "The code does not exist"}},
)
def deactivate_code(code_id: int, admin: CurrentAdmin, db: DbSession) -> None:
    discount_service.deactivate_code(db, admin, code_id)