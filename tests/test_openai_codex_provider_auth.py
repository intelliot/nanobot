"""Auth profile behavior tests for OpenAI Codex provider."""

import json
import time
from types import SimpleNamespace

import pytest

import nanobot.providers.openai_codex_provider as codex_module
from nanobot.providers.openai_codex_provider import OpenAICodexProvider


def _write_profiles(tmp_path, profiles):
    path = tmp_path / "auth-profiles.json"
    path.write_text(json.dumps({"version": 1, "profiles": profiles}), encoding="utf-8")
    return str(path)


@pytest.mark.asyncio
async def test_chat_returns_actionable_error_when_profile_is_expired(tmp_path, monkeypatch):
    path = _write_profiles(tmp_path, {
        "openai-codex:default": {
            "type": "oauth",
            "provider": "openai-codex",
            "access": "expired-access",
            "refresh": "refresh-token",
            "expires": int(time.time() * 1000) - 60_000,
            "accountId": "acct-123",
        }
    })
    provider = OpenAICodexProvider(
        auth_config=SimpleNamespace(profiles_path=path, profile="openai-codex:default")
    )

    def _unexpected_fallback():
        raise AssertionError("oauth_cli_kit fallback should not be used when auth config is set")

    monkeypatch.setattr(codex_module, "get_codex_token", _unexpected_fallback)

    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert response.finish_reason == "error"
    assert response.content is not None
    assert "token is expired" in response.content
    assert "refresh it in OpenClaw" in response.content


@pytest.mark.asyncio
async def test_chat_returns_error_when_configured_profile_missing(tmp_path, monkeypatch):
    path = _write_profiles(tmp_path, {})
    provider = OpenAICodexProvider(
        auth_config=SimpleNamespace(profiles_path=path, profile="openai-codex:default")
    )

    def _unexpected_fallback():
        raise AssertionError("oauth_cli_kit fallback should not be used when auth config is set")

    monkeypatch.setattr(codex_module, "get_codex_token", _unexpected_fallback)

    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert response.finish_reason == "error"
    assert response.content is not None
    assert "Failed to load auth profile" in response.content
    assert "auth.profilesPath/auth.profile" in response.content


@pytest.mark.asyncio
async def test_chat_returns_error_when_auth_config_is_incomplete(monkeypatch):
    provider = OpenAICodexProvider(auth_config=SimpleNamespace(profiles_path="/tmp/x", profile=""))

    def _unexpected_fallback():
        raise AssertionError("oauth_cli_kit fallback should not be used for incomplete auth config")

    monkeypatch.setattr(codex_module, "get_codex_token", _unexpected_fallback)

    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert response.finish_reason == "error"
    assert response.content is not None
    assert "Auth profile config is incomplete" in response.content


@pytest.mark.asyncio
async def test_chat_falls_back_to_oauth_cli_when_auth_config_not_set(monkeypatch):
    provider = OpenAICodexProvider(auth_config=SimpleNamespace(profiles_path=None, profile=None))
    fallback_token = SimpleNamespace(access="fallback-access", account_id="acct-fallback")

    monkeypatch.setattr(codex_module, "get_codex_token", lambda: fallback_token)

    async def _fake_request(url, headers, body):
        assert headers["Authorization"] == "Bearer fallback-access"
        assert headers["chatgpt-account-id"] == "acct-fallback"
        return "ok", [], "stop"

    monkeypatch.setattr(codex_module, "_request_codex", _fake_request)

    response = await provider.chat(messages=[{"role": "user", "content": "hello"}])
    assert response.finish_reason == "stop"
    assert response.content == "ok"
