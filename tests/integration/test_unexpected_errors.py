from app.core.config import get_settings
from app.services import trainer_service


def test_unexpected_error_returns_generic_500_with_cors_headers(client, monkeypatch):
    def broken_list_trainers(_db):
        raise RuntimeError("database out of date")

    monkeypatch.setattr(trainer_service, "list_trainers", broken_list_trainers)
    origin = get_settings().cors_origins[0]

    response = client.get("/api/v1/trainers", headers={"Origin": origin})

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Ha ocurrido un error inesperado.",
        "code": "internal_error",
    }
    assert response.headers["access-control-allow-origin"] == origin
