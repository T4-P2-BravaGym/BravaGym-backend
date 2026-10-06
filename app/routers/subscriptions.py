from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember
from app.schemas.subscription import MySubscriptionsOut, SubscriptionCreate, SubscriptionOut
from app.services import subscription_service

router = APIRouter(prefix="/subscriptions", tags=["subscriptions"])

DbSession = Annotated[Session, Depends(get_db)]

AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only members can use this endpoint"},
}


@router.post(
    "",
    response_model=SubscriptionOut,
    status_code=status.HTTP_201_CREATED,
    summary="Subscribe to a membership plan",
    description=(
            "Creates an active subscription and a pending payment for the monthly fee (RN-11). "
            "The amount is read from the plan, never from the request."
    ),
    responses={
        **AUTH_RESPONSES,
        404: {"description": "The plan does not exist or is no longer active"},
        409: {"description": "The member already has an active subscription (RN-11)"},
    },
)
def subscribe(data: SubscriptionCreate, member: CurrentMember, db: DbSession) -> SubscriptionOut:
    subscription = subscription_service.subscribe(db, user_id=member.id, plan_id=data.plan_id)
    return SubscriptionOut.model_validate(subscription)


@router.get(
    "/me",
    response_model=MySubscriptionsOut,
    summary="Get my current subscription and my past ones",
    responses=AUTH_RESPONSES,
)
def read_my_subscriptions(member: CurrentMember, db: DbSession) -> MySubscriptionsOut:
    current, history = subscription_service.get_my_subscriptions(db, user_id=member.id)
    return MySubscriptionsOut.model_validate({"current": current, "history": history})