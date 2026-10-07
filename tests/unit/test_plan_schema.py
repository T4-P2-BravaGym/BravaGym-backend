
from types import SimpleNamespace

import pytest
from pydantic import ValidationError

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
def test_plan_out_accepts_null_description():
    sample_plan = SimpleNamespace(
        id=2,
        name="Basic",
        description=None,
        monthly_price_cents=2990,
        includes_personal_training=False,
        is_active=True,
    )

    result = PlanOut.model_validate(sample_plan)

    assert result.description is None

def test_plan_out_formats_monthly_price_in_euros():
    sample_plan = SimpleNamespace(
        id=1,
        name="Strength Plus",
        description=None,
        monthly_price_cents=4990,
        includes_personal_training=True,
        is_active=True,
    )

    result = PlanOut.model_validate(sample_plan)

    assert result.model_dump()["monthly_price_formatted"] == "49,90 €"


def test_plan_out_rejects_negative_price():
    sample_plan = SimpleNamespace(
        id=1,
        name="Basic",
        description=None,
        monthly_price_cents=-100,
        includes_personal_training=False,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        PlanOut.model_validate(sample_plan)
def test_plan_out_rejects_name_longer_than_80_characters():
    sample_plan = SimpleNamespace(
        id=1,
        name="A" * 81,
        description=None,
        monthly_price_cents=2990,
        includes_personal_training=False,
        is_active=True,
    )

    with pytest.raises(ValidationError):
        PlanOut.model_validate(sample_plan)