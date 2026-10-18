"""Controller for trainers: receives the request, checks permissions, calls the service, returns a schema.
Keep endpoints thin: no business rules and no complex queries here.
Every endpoint: response_model, summary, and require_roles(...) when it is not public.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.deps import require_roles
from app.core.openapi import error, errors
from app.models import User
from app.models.enums import RoleName
from app.schemas.user import TrainerOut, TrainerProfileUpdate
from app.services import trainer_service

router = APIRouter(prefix="/trainers", tags=["trainers"])


@router.get(
    "",
    response_model=list[TrainerOut],
    summary="List active trainers with their public profile",
)
def list_trainers(db: Annotated[Session, Depends(get_db)]) -> list[TrainerOut]:
    return trainer_service.list_trainers(db)


@router.patch(
    "/me/profile",
    response_model=TrainerOut,
    summary="Update my public trainer profile (specialty and bio)",
    responses={
        401: error("Not logged in"),
        403: error("Not a trainer"),
    },
)
def update_my_profile(
    changes: TrainerProfileUpdate,
    trainer: Annotated[User, Depends(require_roles(RoleName.TRAINER))],
    db: Annotated[Session, Depends(get_db)],
) -> TrainerOut:
    return trainer_service.update_my_profile(db, trainer, changes)


# T-291: the trainer manages her own photo
CurrentTrainer = Annotated[User, Depends(require_roles(RoleName.TRAINER))]


@router.put(
    "/me/photo",
    response_model=TrainerOut,
    summary="Upload or replace my trainer photo",
    description=(
        "Multipart form with a file field. JPEG, PNG or WebP up to 2 MB: the type is read "
        "from the file content, not from its name. Replaces the previous photo and deletes "
        "its file. The response has photo_url (/media/trainers/...)."
    ),
    responses={
        **errors(401, 403),
        422: {
            "description": "Not a JPEG, PNG or WebP image (code invalid_image) "
            "or larger than 2 MB (code image_too_large)"
        },
    },
)
def upload_my_photo(
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, up to 2 MB")],
    trainer: CurrentTrainer,
    db: Annotated[Session, Depends(get_db)],
) -> TrainerOut:
    return trainer_service.set_my_photo(db, trainer, file.file)


@router.delete(
    "/me/photo",
    response_model=TrainerOut,
    summary="Remove my trainer photo",
    description="Deletes the photo and its file. Without a photo it changes nothing (200).",
    responses=errors(401, 403),
)
def delete_my_photo(
    trainer: CurrentTrainer, db: Annotated[Session, Depends(get_db)]
) -> TrainerOut:
    return trainer_service.remove_my_photo(db, trainer)
