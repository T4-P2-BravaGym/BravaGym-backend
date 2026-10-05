"""Shared FastAPI dependencies: current user and role checks.

TODO(HU-03):
- get_current_user: read the Bearer token (OAuth2PasswordBearer with
  tokenUrl="/api/v1/auth/login" so Swagger's Authorize button works), decode it,
  load the user from the database and reject inactive users -> 401.
- require_roles(*roles): returns a dependency that answers 403 when the current
  user's role is not in `roles`. Use it in routers, never `if` checks in endpoints:
      @router.post("", dependencies=[Depends(require_roles("trainer", "superadmin"))])
"""
