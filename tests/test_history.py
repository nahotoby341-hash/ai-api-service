"""历史记录接口测试。"""

from tests.conftest import register_and_login


async def _auth_headers(client) -> dict:
    token = await register_and_login(client)
    return {"Authorization": f"Bearer {token}"}


async def _make_calls(client, headers, count: int, task: str = "translate"):
    """调用 AI 接口造数据。"""
    for _ in range(count):
        resp = await client.post(
            f"/api/v1/ai/{task}",
            json={"text": "hello world", "target_lang": "zh"},
            headers=headers,
        )
        assert resp.status_code == 200


async def test_history_empty(client):
    headers = await _auth_headers(client)
    resp = await client.get("/api/v1/history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["total"] == 0
    assert data["items"] == []


async def test_history_after_calls(client):
    headers = await _auth_headers(client)
    await _make_calls(client, headers, 3)
    resp = await client.get("/api/v1/history", headers=headers)
    data = resp.json()["data"]
    assert data["total"] == 3
    assert len(data["items"]) == 3
    # 时间倒序：第一条是最近一次
    assert data["items"][0]["task_type"] == "translate"
    assert data["items"][0]["input_length"] == 11  # "hello world"


async def test_history_filter_by_type(client):
    headers = await _auth_headers(client)
    await _make_calls(client, headers, 2, task="translate")
    await _make_calls(client, headers, 1, task="summarize")
    resp = await client.get(
        "/api/v1/history?task_type=summarize", headers=headers
    )
    data = resp.json()["data"]
    assert data["total"] == 1
    assert data["items"][0]["task_type"] == "summarize"


async def test_history_pagination(client):
    headers = await _auth_headers(client)
    await _make_calls(client, headers, 5)
    resp = await client.get(
        "/api/v1/history?page=2&page_size=2", headers=headers
    )
    data = resp.json()["data"]
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 2


async def test_history_only_own_records(client):
    """不同用户看不到彼此的历史。"""
    # 用户 A 造 3 条
    token_a = await register_and_login(client)
    headers_a = {"Authorization": f"Bearer {token_a}"}
    await _make_calls(client, headers_a, 3)

    # 用户 B 造 1 条
    await client.post(
        "/api/v1/auth/register",
        json={"email": "other@example.com", "password": "Abc123456"},
    )
    login_b = await client.post(
        "/api/v1/auth/login",
        json={"email": "other@example.com", "password": "Abc123456"},
    )
    headers_b = {"Authorization": f"Bearer {login_b.json()['data']['access_token']}"}
    await _make_calls(client, headers_b, 1)

    resp_b = await client.get("/api/v1/history", headers=headers_b)
    assert resp_b.json()["data"]["total"] == 1

    resp_a = await client.get("/api/v1/history", headers=headers_a)
    assert resp_a.json()["data"]["total"] == 3
