from enum import StrEnum


class RoleName(StrEnum):
    MEMBER = "member"
    TRAINER = "trainer"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    CANCELLED = "cancelled"
    EXPIRED = "expired"


class CancellationStatus(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class BookingStatus(StrEnum):
    CONFIRMED = "confirmed"
    WAITLISTED = "waitlisted"
    CANCELLED = "cancelled"


class OrderStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"


class PaymentStatus(StrEnum):
    PENDING = "pending"
    PAID = "paid"
    FAILED = "failed"
    REFUNDED = "refunded"


class PaymentMethod(StrEnum):
    SIMULATED = "simulated"
    STRIPE = "stripe"