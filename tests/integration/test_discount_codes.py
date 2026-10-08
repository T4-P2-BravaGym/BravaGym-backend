from datetime import date, datetime

import pytest
from freezegun import freeze_time

from app.core.security import create_access_token
from app.models import DiscountCode, MembershipPlan, Payment, Subscription
from app.models.enums import PaymentStatus, RoleName

CODES_URL = "/api/v1/discount-codes"
TODAY = "2026-10-08"


def headers_for(user):
    return {"Authorization": f"Bearer {create_access_token(user.id, user.role.name)}"}


def new_code_body(**changes):
    body = {"code": "BRAVA20", "percent_off": 20, "valid_from": "2026-10-01", "valid_until": "2026-10-31", "max_uses": 2}
    return {**body, **changes}


def add_code(db, admin, **changes):
    data = {
        "code": "BRAVA20",
        "percent_off": 20,
        "valid_from": date(2026, 10, 1),
        "valid_until": date(2026, 10, 31),
        "max_uses": 2,
        "is_active": True,
        **changes,
    }
    code = DiscountCode(**data, created_by=admin.id)
    db.add(code)
    db.commit()
    return code


def add_payment(db, make_user, code, status=PaymentStatus.PAID):
    """A payment that used the code. Each one gets its own member and subscription."""
    member = make_user(RoleName.MEMBER)
    plan = MembershipPlan(name=f"Plan {member.id}", monthly_price_cents=5000)
    subscription = Subscription(user=member, plan=plan, start_date=date(2026, 10, 1))
    db.add(
        Payment(
            user_id=member.id,
            subscription=subscription,
            discount_code_id=code.id,
            base_amount_cents=5000,
            final_amount_cents=4000,
            status=status,
            paid_at=datetime(2026, 10, 2) if status == PaymentStatus.PAID else None,
        )
    )
    db.commit()


# --- CRUD (admin) ---


def test_admin_creates_a_code_in_capitals(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.post(CODES_URL, json=new_code_body(code="  brava20 "), headers=headers_for(admin))

    assert response.status_code == 201
    assert response.json()["code"] == "BRAVA20"
    assert response.json()["uses"] == 0
    assert response.json()["is_active"] is True


def test_creating_a_repeated_code_returns_409(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    add_code(db, admin)

    response = client.post(CODES_URL, json=new_code_body(code="brava20"), headers=headers_for(admin))

    assert response.status_code == 409


@pytest.mark.parametrize("percent", [0, 101, -5])
def test_percent_outside_1_to_100_returns_422(client, make_user, percent):
    admin = make_user(RoleName.ADMIN)

    response = client.post(CODES_URL, json=new_code_body(percent_off=percent), headers=headers_for(admin))

    assert response.status_code == 422


def test_end_date_before_start_date_returns_422(client, make_user):
    admin = make_user(RoleName.ADMIN)

    response = client.post(
        CODES_URL, json=new_code_body(valid_from="2026-10-31", valid_until="2026-10-01"), headers=headers_for(admin)
    )

    assert response.status_code == 422


def test_admin_lists_codes_with_their_uses(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    code = add_code(db, admin)
    add_payment(db, make_user, code)

    response = client.get(CODES_URL, headers=headers_for(admin))

    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["uses"] == 1


def test_admin_updates_only_the_fields_sent(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    code = add_code(db, admin)

    response = client.patch(f"{CODES_URL}/{code.id}", json={"percent_off": 15}, headers=headers_for(admin))

    assert response.status_code == 200
    assert response.json()["percent_off"] == 15
    assert response.json()["max_uses"] == 2


def test_update_that_leaves_the_dates_reversed_returns_422(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    code = add_code(db, admin)

    response = client.patch(f"{CODES_URL}/{code.id}", json={"valid_until": "2026-09-01"}, headers=headers_for(admin))

    assert response.status_code == 422


def test_delete_deactivates_the_code_instead_of_removing_it(client, db, make_user):
    admin = make_user(RoleName.ADMIN)
    code = add_code(db, admin)

    response = client.delete(f"{CODES_URL}/{code.id}", headers=headers_for(admin))

    assert response.status_code == 204
    assert client.get(CODES_URL, headers=headers_for(admin)).json()["items"][0]["is_active"] is False


def test_update_or_delete_an_unknown_code_returns_404(client, make_user):
    admin = make_user(RoleName.ADMIN)

    assert client.patch(f"{CODES_URL}/999", json={"percent_off": 10}, headers=headers_for(admin)).status_code == 404
    assert client.delete(f"{CODES_URL}/999", headers=headers_for(admin)).status_code == 404


def test_member_cannot_manage_codes_returns_403(client, make_user):
    member = make_user(RoleName.MEMBER)

    assert client.get(CODES_URL, headers=headers_for(member)).status_code == 403
    assert client.post(CODES_URL, json=new_code_body(), headers=headers_for(member)).status_code == 403


def test_manage_codes_without_token_returns_401(client):
    assert client.get(CODES_URL).status_code == 401
    assert client.post(CODES_URL, json=new_code_body()).status_code == 401


# --- Validation (member, RN-14) ---


@freeze_time(TODAY)
def test_rn14_valid_code_returns_its_percent(client, db, make_user):
    code = add_code(db, make_user(RoleName.ADMIN))
    member = make_user(RoleName.MEMBER)

    response = client.get(f"{CODES_URL}/brava20/validate", headers=headers_for(member))

    assert response.status_code == 200
    assert response.json() == {"code": "BRAVA20", "percent_off": code.percent_off}


@freeze_time(TODAY)
def test_rn14_unknown_code_returns_422(client, make_user):
    member = make_user(RoleName.MEMBER)

    response = client.get(f"{CODES_URL}/NOEXISTE/validate", headers=headers_for(member))

    assert response.status_code == 422


@freeze_time(TODAY)
def test_rn14_inactive_code_returns_422(client, db, make_user):
    add_code(db, make_user(RoleName.ADMIN), is_active=False)
    member = make_user(RoleName.MEMBER)

    response = client.get(f"{CODES_URL}/BRAVA20/validate", headers=headers_for(member))

    assert response.status_code == 422


@pytest.mark.parametrize(
    ("today", "status_code"),
    [("2026-09-30", 422), ("2026-10-01", 200), ("2026-10-31", 200), ("2026-11-01", 422)],
)
def test_rn14_code_only_works_between_its_dates(client, db, make_user, today, status_code):
    add_code(db, make_user(RoleName.ADMIN))
    member = make_user(RoleName.MEMBER)

    with freeze_time(today):
        response = client.get(f"{CODES_URL}/BRAVA20/validate", headers=headers_for(member))

    assert response.status_code == status_code


@freeze_time(TODAY)
def test_rn14_code_used_max_uses_times_returns_422(client, db, make_user):
    code = add_code(db, make_user(RoleName.ADMIN), max_uses=2)
    add_payment(db, make_user, code)
    member = make_user(RoleName.MEMBER)
    assert client.get(f"{CODES_URL}/BRAVA20/validate", headers=headers_for(member)).status_code == 200

    add_payment(db, make_user, code)
    response = client.get(f"{CODES_URL}/BRAVA20/validate", headers=headers_for(member))

    assert response.status_code == 422


@freeze_time(TODAY)
def test_rn14_pending_payments_do_not_count_as_uses(client, db, make_user):
    code = add_code(db, make_user(RoleName.ADMIN), max_uses=1)
    add_payment(db, make_user, code, status=PaymentStatus.PENDING)
    member = make_user(RoleName.MEMBER)

    response = client.get(f"{CODES_URL}/BRAVA20/validate", headers=headers_for(member))

    assert response.status_code == 200


@freeze_time(TODAY)
def test_rn14_code_without_max_uses_has_no_limit(client, db, make_user):
    code = add_code(db, make_user(RoleName.ADMIN), max_uses=None)
    for _ in range(3):
        add_payment(db, make_user, code)
    member = make_user(RoleName.MEMBER)

    response = client.get(f"{CODES_URL}/BRAVA20/validate", headers=headers_for(member))

    assert response.status_code == 200


def test_validate_without_token_returns_401(client):
    assert client.get(f"{CODES_URL}/BRAVA20/validate").status_code == 401

    