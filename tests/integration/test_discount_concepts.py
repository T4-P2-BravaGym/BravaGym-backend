"""T-240: a discount code can be limited to one payment concept (RN-14)."""

from datetime import date

from app.models import DiscountCode, MembershipPlan, Payment, Subscription
from app.models.enums import PaymentStatus, RoleName
from freezegun import freeze_time

from tests.conftest import auth_header_for

CODES_URL = "/api/v1/discount-codes"
TODAY = "2026-10-08"


def add_code(db, admin, **changes):
    code = DiscountCode(
        code="CLASES10",
        percent_off=10,
        valid_from=date(2026, 10, 1),
        valid_until=date(2026, 10, 31),
        created_by=admin.id,
        **changes,
    )
    db.add(code)
    db.commit()
    return code


def add_subscription_payment(db, member):
    plan = MembershipPlan(name=f"Plan {member.id}", monthly_price_cents=5000)
    subscription = Subscription(user=member, plan=plan, start_date=date(2026, 10, 1))
    payment = Payment(
        user_id=member.id,
        subscription=subscription,
        base_amount_cents=5000,
        final_amount_cents=5000,
        status=PaymentStatus.PENDING,
    )
    db.add(payment)
    db.commit()
    return payment


def new_code_body(**changes):
    body = {
        "code": "clases10",
        "percent_off": 10,
        "valid_from": "2026-10-01",
        "valid_until": "2026-10-31",
    }
    return {**body, **changes}


# --- Admin ---


def test_admin_creates_a_code_for_classes_only(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.post(
        CODES_URL,
        json=new_code_body(applies_to="booking"),
        headers=auth_header_for(admin),
    )

    assert response.status_code == 201
    assert response.json()["applies_to"] == "booking"


def test_a_code_without_applies_to_is_for_everything(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.post(
        CODES_URL, json=new_code_body(), headers=auth_header_for(admin)
    )

    assert response.status_code == 201
    assert response.json()["applies_to"] is None


def test_an_unknown_concept_returns_422(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.post(
        CODES_URL,
        json=new_code_body(applies_to="tienda"),
        headers=auth_header_for(admin),
    )

    assert response.status_code == 422


def test_sending_null_makes_the_code_valid_for_everything_again(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    code = add_code(db, admin, applies_to="booking")

    response = client.patch(
        f"{CODES_URL}/{code.id}",
        json={"applies_to": None},
        headers=auth_header_for(admin),
    )

    assert response.status_code == 200
    assert response.json()["applies_to"] is None


# --- Validation before paying ---


@freeze_time(TODAY)
def test_validating_with_another_concept_returns_422(client, db, make_user):
    add_code(db, make_user(RoleName.ADMIN), applies_to="booking")
    member = make_user(RoleName.MEMBER)

    response = client.get(
        f"{CODES_URL}/CLASES10/validate?concept=order", headers=auth_header_for(member)
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "Este código solo vale para clases."


@freeze_time(TODAY)
def test_validating_with_the_right_concept_or_without_one_works(client, db, make_user):
    add_code(db, make_user(RoleName.ADMIN), applies_to="booking")
    member = make_user(RoleName.MEMBER)
    headers = auth_header_for(member)

    with_concept = client.get(
        f"{CODES_URL}/CLASES10/validate?concept=booking", headers=headers
    )
    without = client.get(f"{CODES_URL}/CLASES10/validate", headers=headers)

    assert with_concept.status_code == 200
    assert with_concept.json()["applies_to"] == "booking"
    assert without.status_code == 200


# --- Paying ---


@freeze_time(TODAY)
def test_paying_a_fee_with_a_code_for_classes_returns_422(client, db, make_user):
    add_code(db, make_user(RoleName.ADMIN), applies_to="booking")
    member = make_user(RoleName.MEMBER)
    payment = add_subscription_payment(db, member)

    response = client.post(
        f"/api/v1/payments/{payment.id}/pay",
        json={"discount_code": "CLASES10"},
        headers=auth_header_for(member),
    )

    assert response.status_code == 422
    db.refresh(payment)
    assert payment.status == PaymentStatus.PENDING
    assert payment.discount_code_id is None


@freeze_time(TODAY)
def test_paying_a_fee_with_a_code_for_fees_applies_the_discount(client, db, make_user):
    add_code(db, make_user(RoleName.ADMIN), applies_to="subscription")
    member = make_user(RoleName.MEMBER)
    payment = add_subscription_payment(db, member)

    response = client.post(
        f"/api/v1/payments/{payment.id}/pay",
        json={"discount_code": "CLASES10"},
        headers=auth_header_for(member),
    )

    assert response.status_code == 200
    assert response.json()["final_amount_cents"] == 4500
