import importlib.util
import sys
import time
import uuid
from pathlib import Path

from fastapi.testclient import TestClient
from jose import jwt

ROOT = Path(__file__).resolve().parents[1]


def load_module(module_name: str, relpath: str):
    for name in list(sys.modules):
        if name == "app" or name.startswith("app."):
            del sys.modules[name]

    service_root = (ROOT / relpath).resolve().parents[1]
    for path in list(sys.path):
        if Path(path).resolve() == service_root:
            sys.path.remove(path)
    sys.path.insert(0, str(service_root))

    spec = importlib.util.spec_from_file_location(module_name, ROOT / relpath)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


gateway_module = load_module("astra_gateway_main", "apps/api-gateway/app/main.py")
user_module = load_module("astra_user_main", "apps/user-service/app/main.py")


def build_valid_token(subject: str = "42") -> str:
    now = int(time.time())
    return jwt.encode({"sub": subject, "iat": now, "exp": now + 3600}, "test-secret", algorithm="HS256")


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_gateway_register_login_and_profile_flow(monkeypatch):
    unique_email = f"gateway-user-{uuid.uuid4().hex}@example.com"

    async def fake_request(self, method, url, json=None, headers=None, timeout=None):
        if method == "POST" and url.endswith("/users"):
            return FakeResponse(201, {"id": 42, "email": unique_email, "full_name": "Gateway User", "is_active": True})
        if method == "POST" and url.endswith("/users/login"):
            return FakeResponse(200, {"access_token": "fake-jwt-token", "token_type": "bearer"})
        if method == "GET" and url.endswith("/users/42"):
            return FakeResponse(200, {"id": 42, "email": unique_email, "full_name": "Gateway User", "is_active": True})
        raise AssertionError(f"unexpected call: {method} {url}")

    monkeypatch.setattr("httpx.AsyncClient.request", fake_request)

    token = build_valid_token("42")

    with TestClient(gateway_module.app) as client:
        register_response = client.post(
            "/api/users",
            json={
                "email": unique_email,
                "full_name": "Gateway User",
                "password": "password123",
            },
        )
        assert register_response.status_code == 201, register_response.text
        created = register_response.json()
        assert created["email"] == unique_email

        login_response = client.post(
            "/api/users/login",
            json={"email": unique_email, "password": "password123"},
        )
        assert login_response.status_code == 200, login_response.text
        assert login_response.json()["access_token"] == "fake-jwt-token"

        me_response = client.get(
            "/api/users/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert me_response.status_code == 200, me_response.text
        assert "user" in me_response.json()

        unauth_response = client.get("/api/users/me")
        assert unauth_response.status_code == 401, unauth_response.text


def test_gateway_returns_service_unavailable_when_user_service_is_down(monkeypatch):
    async def fake_request(self, method, url, json=None, headers=None, timeout=None):
        raise RuntimeError("downstream unavailable")

    monkeypatch.setattr("httpx.AsyncClient.request", fake_request)

    with TestClient(gateway_module.app) as client:
        response = client.post("/api/users", json={"email": "nope@example.com", "full_name": "Nope", "password": "password123"})
        assert response.status_code == 503, response.text
