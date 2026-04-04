
from tests.factories import create_user


async def test_register_success(client) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "username": "bob", "password": "Secret123!"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "bob@example.com"
    assert body["data"]["username"] == "bob"
    assert body["message"] == "Registration successful"


async def test_register_duplicate_email(client, db_session) -> None:
    await create_user(db_session, email="dup@example.com", username="dup1")
    response = await client.post(
        "/auth/register",
        json={"email": "dup@example.com", "username": "dup2", "password": "Secret123!"},
    )
    assert response.status_code == 409
    body = response.json()
    assert body["success"] is False
    assert "Email" in body["message"]


async def test_register_duplicate_username(client, db_session) -> None:
    await create_user(db_session, email="u1@example.com", username="dupname")
    response = await client.post(
        "/auth/register",
        json={"email": "u2@example.com", "username": "dupname", "password": "Secret123!"},
    )
    assert response.status_code == 409
    assert "Username" in response.json()["message"]


async def test_register_invalid_email(client) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "not-an-email", "username": "bob", "password": "Secret123!"},
    )
    assert response.status_code == 422


async def test_register_weak_password(client) -> None:
    response = await client.post(
        "/auth/register",
        json={"email": "bob@example.com", "username": "bob", "password": "weakpass"},
    )
    assert response.status_code == 422
