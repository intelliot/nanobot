"""Tests for auth_profiles reader."""

import json
import time

from nanobot.providers.auth_profiles import AuthProfileToken, check_token_expiry, load_profile


def _write_profiles(tmp_path, profiles):
    """Helper to write an auth-profiles.json file."""
    path = tmp_path / "auth-profiles.json"
    path.write_text(json.dumps({"version": 1, "profiles": profiles}), encoding="utf-8")
    return str(path)


def test_valid_oauth_profile(tmp_path):
    path = _write_profiles(tmp_path, {
        "openai-codex:default": {
            "type": "oauth",
            "provider": "openai-codex",
            "access": "access-token-123",
            "refresh": "refresh-token-456",
            "expires": int(time.time() * 1000) + 3600_000,
            "accountId": "acct-789",
        }
    })
    token = load_profile(path, "openai-codex:default")
    assert token is not None
    assert token.access == "access-token-123"
    assert token.refresh == "refresh-token-456"
    assert token.account_id == "acct-789"


def test_account_id_snake_case(tmp_path):
    """Also accept account_id (snake_case) in addition to accountId."""
    path = _write_profiles(tmp_path, {
        "test:profile": {
            "type": "oauth",
            "access": "a",
            "refresh": "r",
            "expires": 0,
            "account_id": "snake-id",
        }
    })
    token = load_profile(path, "test:profile")
    assert token is not None
    assert token.account_id == "snake-id"


def test_non_oauth_profile_returns_none(tmp_path):
    path = _write_profiles(tmp_path, {
        "openai:default": {
            "type": "api_key",
            "key": "sk-test",
        }
    })
    assert load_profile(path, "openai:default") is None


def test_wrong_profile_id_returns_none(tmp_path):
    path = _write_profiles(tmp_path, {
        "openai-codex:default": {
            "type": "oauth",
            "access": "a",
            "refresh": "r",
            "expires": 0,
            "accountId": "x",
        }
    })
    assert load_profile(path, "openai-codex:other") is None


def test_missing_file_returns_none():
    assert load_profile("/nonexistent/path/auth-profiles.json", "any") is None


def test_malformed_json(tmp_path):
    path = tmp_path / "auth-profiles.json"
    path.write_text("not json{{{", encoding="utf-8")
    assert load_profile(str(path), "any") is None


def test_expired_token_detected():
    token = AuthProfileToken(
        access="a",
        refresh="r",
        expires=int(time.time() * 1000) - 60_000,  # expired 1 minute ago
        account_id="x",
    )
    assert check_token_expiry(token) is False


def test_valid_token_not_expired():
    token = AuthProfileToken(
        access="a",
        refresh="r",
        expires=int(time.time() * 1000) + 3600_000,  # expires in 1 hour
        account_id="x",
    )
    assert check_token_expiry(token) is True


def test_zero_expires_always_valid():
    token = AuthProfileToken(access="a", refresh="r", expires=0, account_id="x")
    assert check_token_expiry(token) is True
