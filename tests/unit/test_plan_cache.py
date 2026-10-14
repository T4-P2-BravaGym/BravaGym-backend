"""HU-28: plans list cache hit, TTL expiry and CRUD invalidation."""

from freezegun import freeze_time

from app.core.cache import PLANS_CACHE_KEY, configure_response_cache, response_cache
from app.models.membership import MembershipPlan
from app.schemas.plan import PlanCreate, PlanUpdate
from app.services import plan_service


def test_second_list_active_plans_call_is_a_cache_hit(db, make_plan):
    make_plan(name="Basic", monthly_price_cents=2990)

    first = plan_service.list_active_plans(db)
    assert [plan.name for plan in first] == ["Basic"]
    assert response_cache.get(PLANS_CACHE_KEY) is not None

    # Bypass the service so the cache is the only source of truth.
    stale = db.get(MembershipPlan, first[0].id)
    stale.name = "Changed in DB"
    db.commit()

    second = plan_service.list_active_plans(db)
    assert [plan.name for plan in second] == ["Basic"]


def test_create_plan_invalidates_plans_cache(db, make_plan):
    make_plan(name="Basic", monthly_price_cents=2990)
    plan_service.list_active_plans(db)
    assert response_cache.get(PLANS_CACHE_KEY) is not None

    plan_service.create_plan(
        db,
        PlanCreate(name="Premium", monthly_price_cents=5990),
    )
    assert response_cache.get(PLANS_CACHE_KEY) is None
    assert [plan.name for plan in plan_service.list_active_plans(db)] == [
        "Basic",
        "Premium",
    ]


def test_update_plan_invalidates_plans_cache(db, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=2990)
    plan_service.list_active_plans(db)

    plan_service.update_plan(db, plan.id, PlanUpdate(name="Strength"))
    assert response_cache.get(PLANS_CACHE_KEY) is None
    assert plan_service.list_active_plans(db)[0].name == "Strength"


def test_deactivate_plan_invalidates_plans_cache(db, make_plan):
    plan = make_plan(name="Basic", monthly_price_cents=2990)
    plan_service.list_active_plans(db)

    plan_service.deactivate_plan(db, plan.id)
    assert response_cache.get(PLANS_CACHE_KEY) is None
    assert plan_service.list_active_plans(db) == []


def test_plans_cache_expires_after_ttl(db, make_plan):
    configure_response_cache(30)
    make_plan(name="Basic", monthly_price_cents=2990)

    with freeze_time("2026-10-14 12:00:00") as frozen:
        first = plan_service.list_active_plans(db)
        plan = db.get(MembershipPlan, first[0].id)
        plan.name = "After TTL"
        db.commit()

        frozen.tick(31)
        assert plan_service.list_active_plans(db)[0].name == "After TTL"
