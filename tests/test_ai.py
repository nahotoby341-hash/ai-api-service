"""AI 接口测试：摘要 / 翻译 / 认证 / 限流 / 上游异常。"""

from tests.conftest import register_and_login


async def _auth_headers(client) -> dict:
    token = await register_and_login(client)
    return {"Authorization": f"Bearer {token}"}


async def test_summarize_success(client):
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/ai/summarize",
        json={"text": "这是一段需要摘要的长文本。", "max_length": 100},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["result"].startswith("【测试】")
    assert data["provider"] == "mock"
    assert data["usage"]["total_tokens"] == 30
    # 限流剩余额度响应头
    assert resp.headers.get("X-RateLimit-Remaining-Minute") is not None


async def test_translate_success(client):
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/ai/translate",
        json={"text": "Hello world", "target_lang": "zh"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["code"] == 0


async def test_ai_requires_auth(client):
    resp = await client.post(
        "/api/v1/ai/summarize", json={"text": "test", "max_length": 100}
    )
    assert resp.status_code == 401


async def test_translate_unsupported_lang(client):
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/ai/translate",
        json={"text": "hello", "target_lang": "xx"},
        headers=headers,
    )
    assert resp.status_code == 422  # 参数校验失败


async def test_input_too_long(client):
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/ai/summarize",
        json={"text": "a" * 30000, "max_length": 100},
        headers=headers,
    )
    assert resp.status_code == 422


async def test_rate_limit_rejected(client, monkeypatch):
    """限流触发 → 429。"""
    from app.core.exceptions import RateLimitError

    async def fake_check(user_id):
        raise RateLimitError()

    monkeypatch.setattr("app.api.routes.ai.check_rate_limit", fake_check)
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/ai/translate",
        json={"text": "hello", "target_lang": "zh"},
        headers=headers,
    )
    assert resp.status_code == 429
    assert resp.json()["code"] == 42901


async def test_upstream_error(client, monkeypatch):
    """大模型上游异常 → 502。"""
    from app.core.exceptions import UpstreamError

    async def fake_translate(text, target_lang, temperature):
        raise UpstreamError()

    monkeypatch.setattr(
        "app.services.llm.llm_client.translate", fake_translate
    )
    headers = await _auth_headers(client)
    resp = await client.post(
        "/api/v1/ai/translate",
        json={"text": "hello", "target_lang": "zh"},
        headers=headers,
    )
    assert resp.status_code == 502
