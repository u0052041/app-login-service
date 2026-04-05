from tests.factories import create_user


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["data"]


async def test_logout_success(client, db_session) -> None:
    await create_user(db_session, email="alice@example.com", username="alice")
    tokens = await _login(client, "alice@example.com", "Secret123!")

    response = await client.post(
        "/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["message"] == "Logged out successfully"


async def test_logout_revokes_refresh_token(client, db_session) -> None:
    await create_user(db_session, email="alice@example.com", username="alice")
    tokens = await _login(client, "alice@example.com", "Secret123!")

    await client.post("/auth/logout", json={"refresh_token": tokens["refresh_token"]})

    # Refresh token should now be invalid
    response = await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert response.status_code == 401


async def test_logout_invalid_token(client) -> None:
    response = await client.post("/auth/logout", json={"refresh_token": "invalid_token"})
    assert response.status_code == 401
