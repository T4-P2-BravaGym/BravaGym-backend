"""Import every model module here so Base.metadata knows all the tables."""
from app.models import classes, membership, payments, routines, shop, user  # noqa: F401
