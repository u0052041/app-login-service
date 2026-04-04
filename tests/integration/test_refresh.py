from tests.factories import create_user


async def _login(client, email: str, password: str) -> dict:
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["data"]


async def test_refresh_success(client, db_session) -> None:
    await create_user(db_session, email="alice@example.com", username="alice")
    tokens = await _login(client, "alice@example.com", "Secret123!")

    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    # 新的 refresh token 一定不同（opaque 隨機字串）
    assert body["data"]["refresh_token"] != tokens["refresh_token"]
    # access token 欄位存在且非空
    assert body["data"]["access_token"]
    assert body["data"]["token_type"] == "bearer"


async def test_refresh_invalid_token(client) -> None:
    response = await client.post(
        "/auth/refresh", json={"refresh_token": "totally_invalid_token"}
    )
    assert response.status_code == 401


async def test_refresh_token_cannot_be_reused(client, db_session) -> None:
    await create_user(db_session, email="alice@example.com", username="alice")
    tokens = await _login(client, "alice@example.com", "Secret123!")

    # First refresh succeeds
    await client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    # Second use of same token should fail (revoked)
    response = await client.post(
        "/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert response.status_code == 401
