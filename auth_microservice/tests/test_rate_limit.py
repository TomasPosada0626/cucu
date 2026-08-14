from __future__ import annotations

from unittest import mock

from app.rate_limit import rate_limited


def test_11th_login_attempt_within_a_minute_is_throttled(client):
    payload = {"email": "nadie@example.com", "password": "wrong"}
    for _ in range(10):
        response = client.post("/api/v3/auth/login", json=payload)
        assert response.status_code != 429

    response = client.post("/api/v3/auth/login", json=payload)
    assert response.status_code == 429
    assert response.get_json()["error"]["code"] == "rate_limited"


def test_rate_limit_is_scoped_per_endpoint_not_global(client):
    payload = {"email": "nadie@example.com", "password": "wrong"}
    for _ in range(10):
        client.post("/api/v3/auth/login", json=payload)

    # El endpoint de registro tiene su propio presupuesto: no deberia
    # heredar el agotado por /login para el mismo cliente.
    response = client.post(
        "/api/v3/auth/register",
        json={"username": "nuevo", "email": "nuevo@example.com", "password": "secret123"},
    )
    assert response.status_code != 429


def test_rate_limit_is_scoped_per_client_ip(client):
    payload = {"email": "nadie@example.com", "password": "wrong"}
    for _ in range(10):
        client.post("/api/v3/auth/login", json=payload, environ_overrides={"REMOTE_ADDR": "10.0.0.1"})

    response = client.post(
        "/api/v3/auth/login", json=payload, environ_overrides={"REMOTE_ADDR": "10.0.0.2"}
    )
    assert response.status_code != 429


def test_rate_limit_prefers_x_forwarded_for_header(client):
    payload = {"email": "nadie@example.com", "password": "wrong"}
    for _ in range(10):
        client.post("/api/v3/auth/login", json=payload, headers={"X-Forwarded-For": "203.0.113.9"})

    response = client.post(
        "/api/v3/auth/login", json=payload, headers={"X-Forwarded-For": "203.0.113.9"}
    )
    assert response.status_code == 429


def test_window_resets_after_expiry(client):
    payload = {"email": "nadie@example.com", "password": "wrong"}
    fake_time = [1000.0]
    with mock.patch("app.rate_limit.time.time", side_effect=lambda: fake_time[0]):
        for _ in range(10):
            client.post("/api/v3/auth/login", json=payload)
        blocked = client.post("/api/v3/auth/login", json=payload)
        assert blocked.status_code == 429

        fake_time[0] += 61
        allowed = client.post("/api/v3/auth/login", json=payload)
    assert allowed.status_code != 429


def test_rate_limited_decorator_returns_wrapped_function_result_when_allowed(app):
    calls = []

    @rate_limited(max_requests=100, window_seconds=60)
    def view():
        calls.append(1)
        return "ok"

    with app.test_request_context("/whatever"):
        result = view()
    assert result == "ok"
    assert calls == [1]
