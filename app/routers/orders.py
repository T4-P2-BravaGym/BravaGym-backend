from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember
from app.schemas.order import OrderCreate, OrderOut, OrderPage
from app.services import order_service

router = APIRouter(prefix="/orders", tags=["shop"])

DbSession = Annotated[Session, Depends(get_db)]

AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only members can use this endpoint"},
}


@router.post(
    "",
    response_model=OrderOut,
    status_code=status.HTTP_201_CREATED,
    summary="Place an order",
    description=(
            "Creates a pending order with its lines, takes the stock and creates a pending "
            "payment for the total (RN-17). Send only product ids and quantities: prices "
            "always come from the database. All or nothing: if one product fails, nothing changes."
    ),
    responses={
        **AUTH_RESPONSES,
        409: {"description": "A product is not available or there is not enough stock (RN-17)"},
        422: {"description": "Empty cart, invalid quantity or the same product twice"},
    },
)
def place_order(body: OrderCreate, member: CurrentMember, db: DbSession) -> OrderOut:
    result = order_service.place_order(db, user_id=member.id, data=body)
    return OrderOut.from_order(result.order, result.payment)


@router.get(
    "/me",
    response_model=OrderPage,
    summary="List my orders",
    description="The authenticated member's orders, newest first, with their lines and payment status.",
    responses=AUTH_RESPONSES,
)
def list_my_orders(
        member: CurrentMember,
        db: DbSession,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> OrderPage:
    results, total = order_service.list_my_orders(db, user_id=member.id, page=page, size=size)
    return OrderPage(
        items=[OrderOut.from_order(result.order, result.payment) for result in results],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/{order_id}/cancel",
    response_model=OrderOut,
    summary="Cancel my pending order",
    description=(
            "Puts the stock back and marks the pending payment as cancelled (RN-16, RN-17). "
            "Only for the member's own orders that are still unpaid."
    ),
    responses={
        **AUTH_RESPONSES,
        404: {"description": "The order does not exist or belongs to someone else"},
        409: {"description": "The order or its payment is no longer pending"},
    },
)
def cancel_order(order_id: int, member: CurrentMember, db: DbSession) -> OrderOut:
    result = order_service.cancel_order(db, user_id=member.id, order_id=order_id)
    return OrderOut.from_order(result.order, result.payment)