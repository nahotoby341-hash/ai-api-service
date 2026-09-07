"""认证接口测试：注册 / 登录 / 令牌。"""


async def test_register_success(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "new@example.com", "password": "Abc123456"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["code"] == 0
    assert data["data"]["email"] == "new@example.com"
    assert data["data"]["user_id"] > 0


async def test_register_duplicate_email(client):
    for _ in range(2):
        resp = await client.post(
            "/api/v1/auth/register",
            json={"email": "dup@example.com", "password": "Abc123456"},
        )
    assert resp.status_code == 409
    assert resp.json()["code"] == 40901


async def test_register_weak_password(client):
    resp = await client.post(
        "/api/v1/auth/register",
        json={"email": "weak@example.com", "password": "12345678"},
    )
    assert resp.status_code == 422  # 纯数字，不含字母


async def test_login_success(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "login@example.com", "password": "Abc123456"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "login@example.com", "password": "Abc123456"},
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["access_token"]
    assert data["refresh_token"]
    assert data["token_type"] == "bearer"


async def test_login_wrong_password(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "wrong@example.com", "password": "Abc123456"},
    )
    resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "wrong@example.com", "password": "WrongPass999"},
    )
    assert resp.status_code == 401
    assert resp.json()["code"] == 40102


async def test_refresh_token(client):
    await client.post(
        "/api/v1/auth/register",
        json={"email": "rf@example.com", "password": "Abc123456"},
    )
    login = await client.post(
        "/api/v1/auth/login",
        json={"email": "rf@example.com", "password": "Abc123456"},
    )
    refresh_token = login.json()["data"]["refresh_token"]

    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["access_token"]


async def test_refresh_with_invalid_token(client):
    resp = await client.post(
        "/api/v1/auth/refresh", json={"refresh_token": "not-a-valid-token"}
    )
    assert resp.status_code == 401


async def test_protected_route_requires_auth(client):
    resp = await client.get("/api/v1/history")
    assert resp.status_code == 401
