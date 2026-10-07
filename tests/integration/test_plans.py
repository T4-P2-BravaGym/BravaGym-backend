from app.models.membership import MembershipPlan


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
    db.add_all([
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
    ])
    db.commit()

    response = client.get("/api/v1/plans")

    assert response.status_code == 200
    assert [plan["name"] for plan in response.json()] == ["Basic", "Premium"]
