"""Password hashing and JWT helpers.

TODO(HU-02, HU-03): implement these functions. Security rules (AGENTS.md, section 7):
- Passwords with bcrypt, cost 12 or more. Never store or log the plain password.
- JWT: sign with settings.secret_key and settings.jwt_algorithm; include only
  "sub" (user id), "role", "exp", "iss" and "aud".
- When decoding, pin the algorithm (algorithms=[settings.jwt_algorithm]) and
  validate exp, iss and aud. Any error -> the caller answers 401 (fail closed).
"""


def hash_password(plain_password: str) -> str:
    raise NotImplementedError("TODO(HU-02)")


def verify_password(plain_password: str, password_hash: str) -> bool:
    raise NotImplementedError("TODO(HU-02)")


def create_access_token(user_id: int, role: str) -> str:
    raise NotImplementedError("TODO(HU-03)")


def decode_access_token(token: str) -> dict:
    raise NotImplementedError("TODO(HU-03)")
