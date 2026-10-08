"""Controller for member cancellation requests (HU-19, RN-12).

Admin approve/reject endpoints belong to HU-20 (RN-13).
"""
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember
from app.schemas.cancellation import CancellationRequestCreate, CancellationRequestOut
from app.services import cancellation_service

router = APIRouter(prefix="/cancellation-requests", tags=["cancellation requests"])

DbSession = Annotated[Session, Depends(get_db)]

AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only members can use this endpoint"},
}


@router.post(
    "",
    response_model=CancellationRequestOut,
    status_code=status.HTTP_201_CREATED,
    summary="Request membership cancellation",
    description=(
        "Creates a pending cancellation request with a reason (RN-12). "
        "The member stays active until an admin approves the request. "
        "Only one pending request per active subscription is allowed."
    ),
    responses={
        **AUTH_RESPONSES,
        404: {"description": "The member has no active subscription"},
        409: {"description": "The member already has a pending cancellation request (RN-12)"},
    },
)
def create_cancellation_request(
        data: CancellationRequestCreate,
        member: CurrentMember,
        db: DbSession,
) -> CancellationRequestOut:
    request = cancellation_service.create_cancellation_request(
        db, user=member, reason=data.reason
    )
    return CancellationRequestOut.model_validate(request)


@router.get(
    "/me",
    response_model=CancellationRequestOut,
    summary="Get my latest cancellation request",
    description="Returns the member's most recent cancellation request and its status.",
    responses={
        **AUTH_RESPONSES,
        404: {"description": "The member has no cancellation request"},
    },
)
def read_my_cancellation_request(member: CurrentMember, db: DbSession) -> CancellationRequestOut:
    request = cancellation_service.get_my_cancellation_request(db, user_id=member.id)
    return CancellationRequestOut.model_validate(request)
