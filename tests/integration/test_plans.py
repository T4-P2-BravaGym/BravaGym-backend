import pytest
from app.models.enums import RoleName
from app.models.membership import MembershipPlan


@pytest.mark.parametrize("role", [RoleName.ADMIN, RoleName.SUPERADMIN])
def test_admin_list_includes_retired_plans_but_public_list_hides_them(
    client, auth_headers, make_plan, role
):
    retired = make_plan(name="Retired", is_active=False, monthly_price_cents=100)
    active = make_plan(name="Current", monthly_price_cents=3900)
    response = client.get("/api/v1/plans/admin", headers=auth_headers(role))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert [item["id"] for item in body["items"]] == [active.id, retired.id]
    assert [item["is_active"] for item in body["items"]] == [True, False]
    assert [item["id"] for item in client.get("/api/v1/plans").json()] == [active.id]


def test_admin_list_requires_login(client):
    assert client.get("/api/v1/plans/admin").status_code == 401


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_admin_list_rejects_other_roles(client, auth_headers, role):
    assert (
        client.get("/api/v1/plans/admin", headers=auth_headers(role)).status_code == 403
    )


def test_admin_list_pagination(client, auth_headers, make_plan):
    make_plan(monthly_price_cents=100)
    second = make_plan(monthly_price_cents=200)
    headers = auth_headers(RoleName.ADMIN)
    response = client.get("/api/v1/plans/admin?page=2&size=1", headers=headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["items"][0]["id"] == second.id
    assert (
        client.get("/api/v1/plans/admin?size=101", headers=headers).status_code == 422
    )


def test_admin_can_create_plan(client, db, auth_headers):
    response = client.post(
        "/api/v1/plans",
        headers=auth_headers(RoleName.ADMIN),
        json={
            "name": "Strength",
            "monthly_price_cents": 4500,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Strength"
    assert body["monthly_price_formatted"] == "45,00 €"

    saved_plan = db.get(MembershipPlan, body["id"])
    assert saved_plan is not None
    assert saved_plan.is_active is True


def test_get_plans_is_public_and_returns_formatted_price(client, db):
    plan = MembershipPlan(
        name="Premium",
        description=None,
        monthly_price_cents=5990,
        includes_personal_training=True,
        is_active=True,
    )
    db.add(plan)
    db.commit()

    response = client.get("/api/v1/plans")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": plan.id,
            "name": "Premium",
            "description": None,
            "monthly_price_cents": 5990,
            "includes_personal_training": True,
            "monthly_price_formatted": "59,90 €",
        }
    ]


def test_get_plans_returns_empty_list_when_no_active_plans(client, db):
    db.add(
        MembershipPlan(
            name="Old offer",
            monthly_price_cents=990,
            is_active=False,
        )
    )
    db.commit()

    response = client.get("/api/v1/plans")

    assert response.status_code == 200
    assert response.json() == []


def test_get_plans_returns_only_active_plans_sorted_by_price(client, db):
    db.add_all(
        [
            MembershipPlan(
                name="Premium",
                monthly_price_cents=5990,
                is_active=True,
            ),
            MembershipPlan(
                name="Old offer",
                monthly_price_cents=990,
                is_active=False,
            ),
            MembershipPlan(
                name="Basic",
                monthly_price_cents=2990,
                is_active=True,
            ),
        ]
    )
    db.commit()

    response = client.get("/api/v1/plans")

    assert response.status_code == 200
    assert [plan["name"] for plan in response.json()] == ["Basic", "Premium"]


def test_create_plan_with_duplicate_name_returns_409(
    client, db, auth_headers, make_plan
):
    existing = make_plan(name="Strength", monthly_price_cents=4500)

    response = client.post(
        "/api/v1/plans",
        headers=auth_headers(RoleName.ADMIN),
        json={
            "name": "Strength",
            "monthly_price_cents": 6000,
        },
    )

    assert response.status_code == 409

    plans = db.query(MembershipPlan).all()
    assert len(plans) == 1
    assert plans[0].id == existing.id
    assert plans[0].monthly_price_cents == 4500


def test_create_plan_without_login_returns_401(client, db):
    response = client.post(
        "/api/v1/plans",
        json={
            "name": "Strength",
            "monthly_price_cents": 4500,
        },
    )

    assert response.status_code == 401
    assert db.query(MembershipPlan).count() == 0


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_create_plan_with_wrong_role_returns_403(client, db, auth_headers, role):
    response = client.post(
        "/api/v1/plans",
        headers=auth_headers(role),
        json={
            "name": "Strength",
            "monthly_price_cents": 4500,
        },
    )

    assert response.status_code == 403
    assert db.query(MembershipPlan).count() == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "monthly_price_cents": 4500},
        {"name": "A" * 81, "monthly_price_cents": 4500},
        {"name": "Strength", "monthly_price_cents": -1},
        {"name": "Strength"},
    ],
)
def test_create_plan_with_invalid_data_returns_422(client, db, auth_headers, payload):
    response = client.post(
        "/api/v1/plans",
        headers=auth_headers(RoleName.ADMIN),
        json=payload,
    )

    assert response.status_code == 422
    assert db.query(MembershipPlan).count() == 0


def test_admin_can_update_price_without_changing_other_fields(
    client, db, auth_headers, make_plan
):
    plan = make_plan(
        name="Strength",
        monthly_price_cents=4500,
        includes_personal_training=True,
    )

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
        json={"monthly_price_cents": 5000},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["monthly_price_cents"] == 5000
    assert body["monthly_price_formatted"] == "50,00 €"
    assert body["name"] == "Strength"
    assert body["includes_personal_training"] is True

    db.refresh(plan)
    assert plan.monthly_price_cents == 5000
    assert plan.name == "Strength"
    assert plan.includes_personal_training is True
    assert plan.is_active is True


def test_update_plan_with_duplicate_name_returns_409(
    client, db, auth_headers, make_plan
):
    make_plan(name="Premium")
    plan = make_plan(name="Basic", monthly_price_cents=3900)

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
        json={"name": "Premium", "monthly_price_cents": 5000},
    )

    assert response.status_code == 409

    db.refresh(plan)
    assert plan.name == "Basic"
    assert plan.monthly_price_cents == 3900


def test_update_missing_plan_returns_404(client, db, auth_headers):
    response = client.patch(
        "/api/v1/plans/999",
        headers=auth_headers(RoleName.ADMIN),
        json={"monthly_price_cents": 5000},
    )

    assert response.status_code == 404


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_update_plan_with_wrong_role_returns_403(
    client, db, auth_headers, make_plan, role
):
    plan = make_plan(name="Basic", monthly_price_cents=3900)

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(role),
        json={"monthly_price_cents": 100},
    )

    assert response.status_code == 403

    db.refresh(plan)
    assert plan.monthly_price_cents == 3900


def test_update_plan_without_login_returns_401(client, db, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=3900)

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        json={"monthly_price_cents": 100},
    )

    assert response.status_code == 401

    db.refresh(plan)
    assert plan.monthly_price_cents == 3900


@pytest.mark.parametrize(
    "payload",
    [
        {"name": ""},
        {"name": "A" * 81},
        {"monthly_price_cents": -1},
        {"name": None},
        {"monthly_price_cents": None},
        {"includes_personal_training": None},
    ],
)
def test_update_plan_with_invalid_data_returns_422(
    client, db, auth_headers, make_plan, payload
):
    plan = make_plan(name="Basic", monthly_price_cents=3900)

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
        json=payload,
    )

    assert response.status_code == 422

    db.refresh(plan)
    assert plan.name == "Basic"
    assert plan.monthly_price_cents == 3900
    assert plan.includes_personal_training is False


def test_delete_plan_deactivates_it_and_preserves_subscription(
    client, db, auth_headers, make_user, make_plan, make_subscription
):
    member = make_user()
    plan = make_plan(name="Basic")
    subscription = make_subscription(user=member, plan=plan)

    original_values = (
        subscription.user_id,
        subscription.plan_id,
        subscription.start_date,
        subscription.end_date,
        subscription.status,
    )

    response = client.delete(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
    )

    assert response.status_code == 200

    db.refresh(plan)
    assert plan.is_active is False
    assert db.get(MembershipPlan, plan.id) is not None

    db.refresh(subscription)
    assert (
        subscription.user_id,
        subscription.plan_id,
        subscription.start_date,
        subscription.end_date,
        subscription.status,
    ) == original_values

    public_response = client.get("/api/v1/plans")
    assert public_response.status_code == 200
    assert public_response.json() == []


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.TRAINER])
def test_delete_plan_with_wrong_role_returns_403(
    client, db, auth_headers, make_plan, role
):
    plan = make_plan(name="Basic")

    response = client.delete(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(role),
    )

    assert response.status_code == 403

    db.refresh(plan)
    assert plan.is_active is True


def test_delete_plan_without_login_returns_401(client, db, make_plan):
    plan = make_plan(name="Basic")

    response = client.delete(f"/api/v1/plans/{plan.id}")

    assert response.status_code == 401

    db.refresh(plan)
    assert plan.is_active is True


def test_delete_missing_plan_returns_404(client, auth_headers):
    response = client.delete(
        "/api/v1/plans/999",
        headers=auth_headers(RoleName.ADMIN),
    )

    assert response.status_code == 404


def test_update_plan_can_keep_its_own_name(client, db, auth_headers, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=3900)

    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
        json={"name": "Basic", "monthly_price_cents": 4500},
    )

    assert response.status_code == 200

    db.refresh(plan)
    assert plan.name == "Basic"
    assert plan.monthly_price_cents == 4500


def test_superadmin_can_create_update_and_deactivate_plan(client, db, auth_headers):
    headers = auth_headers(RoleName.SUPERADMIN)
    created = client.post(
        "/api/v1/plans",
        headers=headers,
        json={"name": "Superadmin plan", "monthly_price_cents": 4500},
    )
    assert created.status_code == 201
    plan_id = created.json()["id"]
    updated = client.patch(
        f"/api/v1/plans/{plan_id}",
        headers=headers,
        json={"monthly_price_cents": 5000},
    )
    assert updated.status_code == 200
    assert updated.json()["monthly_price_cents"] == 5000
    retired = client.delete(f"/api/v1/plans/{plan_id}", headers=headers)
    assert retired.status_code == 200
    plan = db.get(MembershipPlan, plan_id)
    db.refresh(plan)
    assert plan.is_active is False


def test_admin_can_clear_plan_description(client, db, auth_headers, make_plan):
    plan = make_plan(name="Description test")
    plan.description = "Original description"
    db.commit()
    response = client.patch(
        f"/api/v1/plans/{plan.id}",
        headers=auth_headers(RoleName.ADMIN),
        json={"description": None},
    )
    assert response.status_code == 200
    assert response.json()["description"] is None
    db.refresh(plan)
    assert plan.description is None
    assert plan.name == "Description test"


def test_deactivating_retired_plan_preserves_subscription(
    client, db, auth_headers, make_user, make_plan, make_subscription
):
    plan = make_plan(name="Already retired", is_active=False)
    subscription = make_subscription(user=make_user(), plan=plan)
    original = (
        subscription.plan_id,
        subscription.status,
        subscription.start_date,
        subscription.end_date,
    )
    headers = auth_headers(RoleName.ADMIN)
    for _ in range(2):
        response = client.delete(f"/api/v1/plans/{plan.id}", headers=headers)
        assert response.status_code == 200
    db.refresh(plan)
    db.refresh(subscription)
    assert plan.is_active is False
    assert (
        subscription.plan_id,
        subscription.status,
        subscription.start_date,
        subscription.end_date,
    ) == original
