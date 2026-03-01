from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pymongo.errors import PyMongoError
from bson import ObjectId

from app.db import get_database, to_jsonable
from app.security import decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing token")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub", "")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token subject")

    database = get_database()
    user = None
    lookup_candidates: list[object] = [user_id]

    try:
        lookup_candidates.insert(0, ObjectId(user_id))
    except Exception:
        pass

    try:
        for candidate in lookup_candidates:
            user = await database.users.find_one({"_id": candidate})
            if user is not None:
                break
    except PyMongoError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User lookup failed")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return to_jsonable(user) or {}
