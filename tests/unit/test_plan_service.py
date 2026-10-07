from app.models.membership import MembershipPlan
from app.services.plan_service import list_active_plans

def test_list_active_plans_filters_and_sorts(db):
    expensive = MembershipPlan(
        name="Premium",
        monthly_price_cents=5990,
        includes_personal_training=True,
        is_active=True,
    )

    inactive = MembershipPlan(
        name="Old offer",
        monthly_price_cents=990,
        is_active=False,
    )

    affordable = MembershipPlan(
        name="Basic",
        monthly_price_cents=2990,
        is_active=True,
    )

    db.add_all([expensive, inactive, affordable])
    db.commit()

    result = list_active_plans(db)

    assert [plan.name for plan in result] == ["Basic", "Premium"]