"""Read the signed-in user from headers injected by Container Apps authentication (Easy Auth).

Login itself is done by the platform; the app never sees credentials or tokens. The identity is
used for display only (no access decisions), so a spoofed header locally changes nothing.
"""

import base64
import json

from fastapi import Request


def current_user(request: Request) -> dict:
    login = request.headers.get("x-ms-client-principal-name")
    if not login:
        return {"name": None, "login": None, "mode": "local"}
    return {
        "name": _claim_name(request.headers.get("x-ms-client-principal")) or login,
        "login": login,
        "mode": "azure",
    }


def _claim_name(principal: str | None) -> str | None:
    """Full name from the base64 JSON principal: {"claims": [{"typ": "name", "val": "..."}]}."""
    if not principal:
        return None
    try:
        claims = json.loads(base64.b64decode(principal))["claims"]
        return next((c["val"] for c in claims if c.get("typ") == "name" and c.get("val")), None)
    # Malformed header: fall back to the login name.
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
