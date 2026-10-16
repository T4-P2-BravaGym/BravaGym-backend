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


# Swagger groups, in the order they appear, with a Spanish description for each one
OPENAPI_TAGS = [
    {
        "name": "auth",
        "description": "Registro e inicio de sesión. Devuelve el token para el resto de la API.",
    },
    {
        "name": "users",
        "description": "Mi perfil y mi contraseña; y, para administración, buscar, editar, cambiar el rol y dar de baja a usuarias.",
    },
    {"name": "trainers", "description": "Las entrenadoras y su perfil público."},
    {
        "name": "plans",
        "description": "Planes de suscripción: el pricing público y su gestión por administración.",
    },
    {"name": "subscriptions", "description": "Contratar un plan y ver mi suscripción."},
    {
        "name": "class types",
        "description": "Tipos de clase del horario (fuerza, movilidad…) y entrenamiento personal.",
    },
    {
        "name": "sessions",
        "description": "El horario de clases, su gestión por las entrenadoras y las reservas de cada clase.",
    },
    {
        "name": "bookings",
        "description": "Mis reservas: verlas y cancelarlas, con lista de espera.",
    },
    {"name": "exercises", "description": "Catálogo de ejercicios para las rutinas."},
    {
        "name": "routines",
        "description": "Rutinas: las crea la entrenadora y la socia ve la suya.",
    },
    {
        "name": "cancellation requests",
        "description": "Solicitudes de baja de las socias y su revisión por administración.",
    },
    {
        "name": "shop",
        "description": "Tienda: productos, categorías, tallas, fotos y pedidos.",
    },
    {
        "name": "payments",
        "description": "Pagos simulados: los míos, la gestión de administración y la exportación a CSV.",
    },
    {
        "name": "discount codes",
        "description": "Códigos de descuento: su gestión y la validación antes de pagar.",
    },
    {"name": "health", "description": "Comprobar que la API está en marcha."},
]

API_DESCRIPTION = """
API de **Brava**, gimnasio de fuerza para mujeres.

- **Autenticación:** `POST /api/v1/auth/login` devuelve un token. Úsalo en el botón *Authorize*.
- **Errores:** todos llegan como `{"detail": "...", "code": "..."}` (esquema `ErrorOut`),
  salvo la validación de datos (422), que trae la lista de campos con error.
- **Dinero** en céntimos y **fechas** en UTC.
"""
