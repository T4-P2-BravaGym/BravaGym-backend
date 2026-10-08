"""Controller for cancellation requests (HU-19 RN-12, HU-20 RN-13)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import CurrentMember, require_roles
from app.models.enums import CancellationStatus, RoleName
from app.models.user import User
from app.schemas.cancellation import (
    CancellationReject,
    CancellationRequestCreate,
    CancellationRequestOut,
    CancellationRequestPage,
)
from app.services import cancellation_service

router = APIRouter(prefix="/cancellation-requests", tags=["cancellation requests"])

DbSession = Annotated[Session, Depends(get_db)]
CurrentAdmin = Annotated[
    User, Depends(require_roles(RoleName.ADMIN, RoleName.SUPERADMIN))
]

AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only members can use this endpoint"},
}

ADMIN_AUTH_RESPONSES = {
    401: {"description": "Missing, invalid or expired token"},
    403: {"description": "Only admin and superadmin can use this endpoint"},
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


@router.get(
    "",
    response_model=CancellationRequestPage,
    summary="List cancellation requests",
    description=(
        "Paginated admin inbox of cancellation requests, newest first. "
        "Optional filter by status (pending, approved, rejected)."
    ),
    responses={
        **ADMIN_AUTH_RESPONSES,
        422: {"description": "Invalid status, page or size"},
    },
)
def list_cancellation_requests(
        admin: CurrentAdmin,
        db: DbSession,
        status_filter: Annotated[
            CancellationStatus | None,
            Query(alias="status", description="Filter by request status"),
        ] = None,
        page: Annotated[int, Query(ge=1)] = 1,
        size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> CancellationRequestPage:
    del admin  # role gate only
    items, total = cancellation_service.list_cancellation_requests(
        db, status=status_filter, page=page, size=size
    )
    return CancellationRequestPage(
        items=[CancellationRequestOut.model_validate(item) for item in items],
        total=total,
        page=page,
        size=size,
    )


@router.post(
    "/{request_id}/approve",
    response_model=CancellationRequestOut,
    summary="Approve a cancellation request",
    description=(
        "Approves a pending request in one transaction (RN-13): subscription becomes "
        "`cancelled`, the member is deactivated (`is_active=false`, `deactivated_at` set) "
        "and their future bookings are cancelled with waitlist promotion (RN-06)."
    ),
    responses={
        **ADMIN_AUTH_RESPONSES,
        404: {"description": "Cancellation request not found"},
        409: {"description": "The request is not pending"},
    },
)
def approve_cancellation_request(
        request_id: int,
        admin: CurrentAdmin,
        db: DbSession,
) -> CancellationRequestOut:
    request = cancellation_service.approve_cancellation_request(
        db, request_id=request_id, admin=admin
    )
    return CancellationRequestOut.model_validate(request)


@router.post(
    "/{request_id}/reject",
    response_model=CancellationRequestOut,
    summary="Reject a cancellation request",
    description=(
        "Rejects a pending request (RN-13). `admin_notes` is required. "
        "The member and subscription stay active."
    ),
    responses={
        **ADMIN_AUTH_RESPONSES,
        404: {"description": "Cancellation request not found"},
        409: {"description": "The request is not pending"},
        422: {"description": "Missing or empty admin_notes (RN-13)"},
    },
)
def reject_cancellation_request(
        request_id: int,
        data: CancellationReject,
        admin: CurrentAdmin,
        db: DbSession,
) -> CancellationRequestOut:
    request = cancellation_service.reject_cancellation_request(
        db, request_id=request_id, admin=admin, admin_notes=data.admin_notes
    )
    return CancellationRequestOut.model_validate(request)
