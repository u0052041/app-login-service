from tests.factories import create_user


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["data"]


async def test_me_success(client, db_session) -> None:
    await create_user(db_session, email="alice@example.com", username="alice")
    tokens = await _login(client, "alice@example.com", "Secret123!")

    response = await client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["email"] == "alice@example.com"
    assert body["data"]["username"] == "alice"


async def test_me_no_token(client) -> None:
    response = await client.get("/auth/me")
    assert response.status_code in (401, 403)  # HTTPBearer returns 401 or 403


async def test_me_invalid_token(client) -> None:
    response = await client.get(
        "/auth/me",
        headers={"Authorization": "Bearer invalid.token.here"},
    )
    assert response.status_code == 401
