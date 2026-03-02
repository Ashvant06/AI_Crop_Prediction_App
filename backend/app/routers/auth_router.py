from fastapi import APIRouter, HTTPException, status
from pymongo.errors import PyMongoError

from app.config import get_settings
from app.schemas import AuthResponse, DevAuthRequest, PhoneAuthRequest
from app.services.auth_service import AuthError, login_as_dev_user, login_or_create_user_with_phone

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()


@router.post("/phone", response_model=AuthResponse)
async def phone_login(payload: PhoneAuthRequest) -> AuthResponse:
    try:
        result = await login_or_create_user_with_phone(phone_number=payload.phone_number, name=payload.name)
    except AuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Phone authentication failed") from exc

    return AuthResponse(**result)


@router.post("/dev", response_model=AuthResponse)
async def dev_login(payload: DevAuthRequest) -> AuthResponse:
    if not settings.allow_dev_auth:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Dev login is disabled. Enable ALLOW_DEV_AUTH in backend/.env.",
        )
    try:
        result = await login_as_dev_user(name=payload.name, email=payload.email)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Database error") from exc

    return AuthResponse(**result)
