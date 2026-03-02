"""Read-only reader for OpenClaw's auth-profiles.json."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from loguru import logger


@dataclass
class AuthProfileToken:
    """OAuth token loaded from an auth-profiles.json profile."""

    access: str
    refresh: str
    expires: int  # ms epoch
    account_id: str


def _read_required_str(profile: dict, *keys: str) -> str | None:
    """Return the first non-empty string value for keys."""
    for key in keys:
        value = profile.get(key)
        if isinstance(value, str):
            value = value.strip()
            if value:
                return value
    return None


def load_profile(profiles_path: str, profile_id: str) -> AuthProfileToken | None:
    """Load a specific OAuth profile from an auth-profiles.json file.

    Returns None if the file is missing, malformed, or the profile doesn't exist / isn't oauth.
    """
    path = Path(profiles_path).expanduser()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        logger.warning(f"Failed to read auth-profiles from {path}: {e}")
        return None

    profiles = data.get("profiles")
    if not isinstance(profiles, dict):
        logger.warning(f"auth-profiles.json missing 'profiles' dict: {path}")
        return None

    profile = profiles.get(profile_id)
    if not isinstance(profile, dict):
        logger.warning(f"Profile '{profile_id}' not found in {path}")
        return None

    if profile.get("type") != "oauth":
        logger.warning(f"Profile '{profile_id}' is type '{profile.get('type')}', expected 'oauth'")
        return None

    access = _read_required_str(profile, "access")
    refresh = _read_required_str(profile, "refresh")
    account_id = _read_required_str(profile, "accountId", "account_id")

    if not (access and refresh and account_id):
        logger.warning(f"Profile '{profile_id}' missing required fields (access/refresh/accountId)")
        return None

    expires_raw = profile.get("expires")
    if expires_raw in (None, ""):
        expires = 0
    else:
        if isinstance(expires_raw, bool):
            logger.warning(f"Profile '{profile_id}' has invalid 'expires' value: {expires_raw!r}")
            return None
        try:
            expires = int(expires_raw)
        except (TypeError, ValueError):
            logger.warning(f"Profile '{profile_id}' has invalid 'expires' value: {expires_raw!r}")
            return None
        if expires < 0:
            logger.warning(f"Profile '{profile_id}' has negative 'expires' value: {expires}")
            return None

    return AuthProfileToken(
        access=access,
        refresh=refresh,
        expires=expires,
        account_id=account_id,
    )


def check_token_expiry(token: AuthProfileToken) -> bool:
    """Return True if the token is still valid (not expired). Tokens with expires=0 are always valid."""
    if token.expires == 0:
        return True
    return token.expires > int(time.time() * 1000)
