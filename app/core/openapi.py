"""What Swagger (/docs) and ReDoc (/redoc) show besides the endpoints themselves (T-02).

Routers document their errors with these helpers, so every error shows the ErrorOut body:
    responses={**errors(401, 403, 404), 409: error("Email already in use")}
"""

from app.schemas.common import ErrorOut

ERROR_DESCRIPTIONS = {
    400: "The request cannot be done as sent",
    401: "Missing, invalid or expired token",
    403: "Logged in, but this role cannot do it",
    404: "It does not exist",
    409: "It clashes with the current state",
    429: "Too many attempts, see Retry-After",
}


def error(description: str) -> dict:
    """One error response with its own description."""
    return {"model": ErrorOut, "description": description}


def errors(*codes: int) -> dict[int, dict]:
    """Several error responses with the common descriptions. 422 is left to FastAPI."""
    return {code: error(ERROR_DESCRIPTIONS[code]) for code in codes}
