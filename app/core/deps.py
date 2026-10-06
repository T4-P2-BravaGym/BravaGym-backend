from collections.abc import Callable
from typing import Annotated

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.exceptions import PermissionDeniedError, UnauthorizedError
from app.core.security import decode_access_token
from app.models import User
from app.models.enums import RoleName


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)

INVALID_SESSION = "Sesión no válida o caducada. Vuelve a iniciar sesión."


def get_current_user(
        token: Annotated[str | None, Depends(oauth2_scheme)],
        db: Annotated[Session, Depends(get_db)],
) -> User:
    if not token:
        raise UnauthorizedError(INVALID_SESSION)
    try:
        payload = decode_access_token(token)
        user_id = int(payload["sub"])
    except (jwt.InvalidTokenError, ValueError):
        raise UnauthorizedError(INVALID_SESSION) from None

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise UnauthorizedError(INVALID_SESSION)
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: RoleName) -> Callable[[User], User]:


    def check_role(current_user: CurrentUser) -> User:
        if current_user.role.name not in roles:
            raise PermissionDeniedError("No tienes permiso para realizar esta acción.")
        return current_user

    return check_role