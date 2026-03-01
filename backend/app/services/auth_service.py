from datetime import UTC, datetime

from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from pymongo import ReturnDocument

from app.config import get_settings
from app.db import get_database, to_jsonable
from app.security import create_access_token


class AuthError(Exception):
    pass


def _normalize_client_id(value: str) -> str:
    normalized = str(value or "").strip()
    if normalized.startswith(("'", '"')) and normalized.endswith(("'", '"')) and len(normalized) >= 2:
        normalized = normalized[1:-1].strip()
    return normalized


def _configured_google_client_ids() -> list[str]:
    settings = get_settings()
    values = [_normalize_client_id(item) for item in settings.google_client_id_list]
    return [value for value in values if value and "your_google_oauth_client_id" not in value]


async def _upsert_user(
    *,
    identity_key: str,
    name: str,
    email: str,
    picture: str | None = None,
) -> dict:
    database = get_database()
    now = datetime.now(UTC)

    user_update = {
        "google_sub": identity_key,
        "name": name or "Farmer",
        "email": email or "",
        "picture": picture,
        "updated_at": now,
    }

    user = await database.users.find_one_and_update(
        {"google_sub": identity_key},
        {"$set": user_update, "$setOnInsert": {"created_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )

    user = to_jsonable(user) or {}
    access_token = create_access_token(user["_id"])

    return {
        "access_token": access_token,
        "user": {
            "id": user["_id"],
            "name": user.get("name", ""),
            "email": user.get("email", ""),
            "picture": user.get("picture"),
        },
    }


def verify_google_credential(credential: str) -> dict:
    configured_ids = _configured_google_client_ids()
    if not configured_ids:
        raise AuthError("Google OAuth is not configured. Set GOOGLE_CLIENT_ID or GOOGLE_CLIENT_IDS.")
    request = google_requests.Request()

    try:
        # Verify signature and standard claims first, then validate audience manually.
        token_info = id_token.verify_oauth2_token(credential, request, audience=None)
    except ValueError as exc:
        raise AuthError("Google credential verification failed") from exc

    if token_info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}:
        raise AuthError("Invalid Google token issuer")

    token_aud = str(token_info.get("aud", "")).strip()
    token_azp = str(token_info.get("azp", "")).strip()
    if token_aud not in configured_ids and token_azp not in configured_ids:
        raise AuthError("Google token audience does not match configured client id")

    if token_info.get("email_verified") is not True:
        raise AuthError("Google account email is not verified")

    if not token_info.get("sub"):
        raise AuthError("Google token is missing subject")

    return token_info


async def login_or_create_user(credential: str) -> dict:
    token_info = verify_google_credential(credential)
    return await _upsert_user(
        identity_key=token_info.get("sub", ""),
        name=token_info.get("name", "Farmer"),
        email=token_info.get("email", ""),
        picture=token_info.get("picture"),
    )


async def login_as_dev_user(name: str, email: str) -> dict:
    identity = f"dev::{email.strip().lower() or 'demo.farmer@local.dev'}"
    return await _upsert_user(
        identity_key=identity,
        name=name.strip() or "Demo Farmer",
        email=email.strip() or "demo.farmer@local.dev",
        picture=None,
    )
