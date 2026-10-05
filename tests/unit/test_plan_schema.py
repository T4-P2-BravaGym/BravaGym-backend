from types import SimpleNamespace

from app.schemas.plan import PlanOut


def test_plan_out_reads_plan_attributes():
    sample_plan = SimpleNamespace(
        id=1,
        name="Strength Plus",
        description="Entrenamiento con sesiones personales",
        monthly_price_cents=4990,
        includes_personal_training=True,
        is_active=True,
    )

    result = PlanOut.model_validate(sample_plan)

    assert result.id == 1
    assert result.name == "Strength Plus"
    assert result.monthly_price_cents == 4990
    assert result.includes_personal_training is True
