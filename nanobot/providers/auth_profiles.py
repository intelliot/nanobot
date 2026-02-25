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

    access = profile.get("access")
    refresh = profile.get("refresh")
    account_id = profile.get("accountId") or profile.get("account_id")
    expires = profile.get("expires")

    if not (access and refresh and account_id):
        logger.warning(f"Profile '{profile_id}' missing required fields (access/refresh/accountId)")
        return None

    return AuthProfileToken(
        access=access,
        refresh=refresh,
        expires=int(expires) if expires else 0,
        account_id=account_id,
    )


def check_token_expiry(token: AuthProfileToken) -> bool:
    """Return True if the token is still valid (not expired). Tokens with expires=0 are always valid."""
    if token.expires == 0:
        return True
    return token.expires > int(time.time() * 1000)
