from datetime import UTC, datetime
import re

from pymongo import ReturnDocument

from app.db import get_database, to_jsonable
from app.security import create_access_token


class AuthError(Exception):
    pass


PHONE_NON_DIGIT_RE = re.compile(r"\D+")
PHONE_ALPHA_RE = re.compile(r"[A-Za-z]")


def _normalize_phone_number(value: str) -> str:
    raw_value = str(value or "").strip()
    if not raw_value:
        raise AuthError("Phone number is required.")
    if PHONE_ALPHA_RE.search(raw_value):
        raise AuthError("Phone number cannot include letters.")
    if raw_value.startswith("00"):
        raw_value = f"+{raw_value[2:]}"
    digits_only = PHONE_NON_DIGIT_RE.sub("", raw_value)
    if not digits_only:
        raise AuthError("Phone number must contain digits.")
    if len(digits_only) < 10 or len(digits_only) > 15:
        raise AuthError("Phone number must contain 10 to 15 digits.")
    return f"+{digits_only}"


async def _upsert_user(
    *,
    identity_key: str,
    name: str,
    email: str,
    phone_number: str | None = None,
    picture: str | None = None,
) -> dict:
    database = get_database()
    now = datetime.now(UTC)

    user_update = {
        # Keep a neutral identity field and support old google_sub records on lookup.
        "auth_identity": identity_key,
        "name": name or "Farmer",
        "email": email or "",
        "phone_number": phone_number,
        "picture": picture,
        "updated_at": now,
    }

    user = await database.users.find_one_and_update(
        {"$or": [{"auth_identity": identity_key}, {"google_sub": identity_key}]},
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
            "phone_number": user.get("phone_number"),
            "picture": user.get("picture"),
        },
    }


async def login_or_create_user_with_phone(phone_number: str, name: str) -> dict:
    normalized_phone = _normalize_phone_number(phone_number)
    return await _upsert_user(
        identity_key=f"phone::{normalized_phone}",
        name=name.strip() or "Farmer",
        email="",
        phone_number=normalized_phone,
        picture=None,
    )


async def login_as_dev_user(name: str, email: str) -> dict:
    identity = f"dev::{email.strip().lower() or 'demo.farmer@local.dev'}"
    return await _upsert_user(
        identity_key=identity,
        name=name.strip() or "Demo Farmer",
        email=email.strip() or "demo.farmer@local.dev",
        phone_number=None,
        picture=None,
    )
