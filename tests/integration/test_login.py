from tests.factories import create_user


async def test_login_success(client, db_session) -> None:
    await create_user(
        db_session, email="alice@example.com", username="alice", password="Secret123!"
    )
    response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "Secret123!"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "access_token" in body["data"]
    assert "refresh_token" in body["data"]
    assert body["data"]["token_type"] == "bearer"


async def test_login_wrong_password(client, db_session) -> None:
    await create_user(db_session, email="alice@example.com", username="alice")
    response = await client.post(
        "/auth/login",
        json={"email": "alice@example.com", "password": "WrongPass1!"},
    )
    assert response.status_code == 401
    assert response.json()["success"] is False


async def test_login_nonexistent_email(client) -> None:
    response = await client.post(
        "/auth/login",
        json={"email": "ghost@example.com", "password": "Secret123!"},
    )
    assert response.status_code == 401


async def test_login_inactive_user(client, db_session) -> None:
    await create_user(
        db_session, email="inactive@example.com", username="inactive", is_active=False
    )
    response = await client.post(
        "/auth/login",
        json={"email": "inactive@example.com", "password": "Secret123!"},
    )
    assert response.status_code == 403
