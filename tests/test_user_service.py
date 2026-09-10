import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_register_login_and_get_user():
    unique = uuid.uuid4().hex
    email = f"{unique}@example.com"
    payload = {
        "email": email,
        "full_name": "Phase 3 User",
        "password": "password123",
    }

    register_response = client.post("/users", json=payload)
    assert register_response.status_code == 201, register_response.text
    created = register_response.json()
    assert created["email"] == email
    assert created["id"] > 0

    login_response = client.post("/users/login", json={"email": email, "password": "password123"})
    assert login_response.status_code == 200, login_response.text
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["access_token"]

    user_response = client.get(f"/users/{created['id']}")
    assert user_response.status_code == 200, user_response.text
    user = user_response.json()
    assert user["email"] == email
    assert user["full_name"] == "Phase 3 User"
