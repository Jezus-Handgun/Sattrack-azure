"""Read the signed-in user from headers injected by Container Apps authentication (Easy Auth).

Login itself is done by the platform; the app never sees credentials or tokens. The login is also
checked against the optional ALLOWED_USERS allow-list (authorization on top of authentication).
That is safe because Container Apps doesn't let external requests set X-MS-* headers; locally
there is no auth at all, so a hand-made header proves nothing there either way.
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


def is_allowed(login: str | None, allowed_users: str) -> bool:
    """Allow-list check. No login = request didn't pass Easy Auth (local run, platform probe)."""
    allowed = {u.strip().lower() for u in allowed_users.split(",") if u.strip()}
    return not allowed or login is None or login.lower() in allowed


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
