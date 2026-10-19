"""T-12: trainers see the routine history of a member."""

from datetime import date

import pytest
from app.models import Routine
from app.models.enums import RoleName

from tests.conftest import auth_header_for

ROUTINES_URL = "/api/v1/routines"


def add_routine(db, member, trainer, name, start_date, *, is_active=False):
    """Routine without lines: for the history we only need the header."""
    routine = Routine(
        member=member,
        trainer=trainer,
        name=name,
        start_date=start_date,
        is_active=is_active,
    )
    db.add(routine)
    db.commit()
    return routine


def test_history_is_sorted_by_start_date_newest_first(client, db, make_user):
    member = make_user(RoleName.MEMBER)
    trainer = make_user(RoleName.TRAINER)
    # The newest routine is created FIRST, so ordering by id and by date give
    # different results. If both orders matched, the test would prove nothing
    add_routine(db, member, trainer, "Octubre", date(2026, 10, 1), is_active=True)
    add_routine(db, member, trainer, "Septiembre", date(2026, 9, 1))

    response = client.get(
        ROUTINES_URL,
        params={"member_id": member.id},
        headers=auth_header_for(trainer),
    )

    assert response.status_code == 200
    # We only compare the names: they show the order clearly
    assert [r["name"] for r in response.json()] == ["Octubre", "Septiembre"]


def test_same_start_date_newest_routine_first(client, db, make_user):
    # Same date: the tie is broken by id, so the one created later goes first
    member = make_user(RoleName.MEMBER)
    trainer = make_user(RoleName.TRAINER)

    add_routine(db, member, trainer, "Primera", date(2026, 10, 1))
    add_routine(db, member, trainer, "Segunda", date(2026, 10, 1), is_active=True)

    response = client.get(
        ROUTINES_URL,
        params={"member_id": member.id},
        headers=auth_header_for(trainer),
    )

    assert [r["name"] for r in response.json()] == ["Segunda", "Primera"]


def test_member_without_routines_gets_empty_list(client, make_user):
    member = make_user(RoleName.MEMBER)
    trainer = make_user(RoleName.TRAINER)

    response = client.get(
        ROUTINES_URL,
        params={"member_id": member.id},
        headers=auth_header_for(trainer),
    )

    # An empty history is not an error: 200 with an empty list, not 404
    assert response.status_code == 200
    assert response.json() == []


def test_list_routines_without_token_returns_401(client):
    assert client.get(ROUTINES_URL).status_code == 401


@pytest.mark.parametrize("role", [RoleName.MEMBER, RoleName.ADMIN])
def test_only_trainers_list_routines(client, make_user, role):
    # A member must not read other members' routines (nor her own from here)
    response = client.get(ROUTINES_URL, headers=auth_header_for(make_user(role)))

    assert response.status_code == 403