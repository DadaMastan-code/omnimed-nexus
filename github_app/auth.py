"""GitHub App JWT authentication and installation token management."""

from __future__ import annotations

import time
from pathlib import Path

import httpx
import structlog
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.rsa import RSAPrivateKey
import jwt

from config import settings

log = structlog.get_logger()

_installation_tokens: dict[int, tuple[str, float]] = {}  # installation_id → (token, expiry)


def _load_private_key() -> RSAPrivateKey:
    pem = Path(settings.github_app_private_key_path).read_bytes()
    return serialization.load_pem_private_key(pem, password=None)


def _make_jwt() -> str:
    now = int(time.time())
    payload = {
        "iat": now - 60,
        "exp": now + (10 * 60),
        "iss": settings.github_app_id,
    }
    key = _load_private_key()
    return jwt.encode(payload, key, algorithm="RS256")


async def get_installation_token(installation_id: int) -> str:
    """Return a cached or freshly-minted installation access token."""
    cached = _installation_tokens.get(installation_id)
    if cached and cached[1] > time.time() + 60:
        return cached[0]

    app_jwt = _make_jwt()
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
            },
        )
        resp.raise_for_status()
        data = resp.json()

    token = data["token"]
    # tokens expire in 1 hour
    _installation_tokens[installation_id] = (token, time.time() + 3500)
    log.info("installation_token_refreshed", installation_id=installation_id)
    return token
