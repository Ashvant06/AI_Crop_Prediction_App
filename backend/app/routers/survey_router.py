from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.db import get_database
from app.dependencies import get_current_user
from app.schemas import SurveyRequest
from app.services.activity_service import log_activity

router = APIRouter(prefix="/survey", tags=["survey"])


@router.post("/submit")
async def submit_survey(payload: SurveyRequest, user: dict = Depends(get_current_user)) -> dict:
    now = datetime.now(UTC)
    document = {
        "user_id": user["_id"],
        **payload.model_dump(),
        "created_at": now,
    }

    try:
        database = get_database()
        await database.surveys.insert_one(document)
        await log_activity(
            user["_id"],
            "survey",
            f"Survey submitted (satisfaction: {payload.satisfaction_score}/5)",
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save survey") from exc

    return {"status": "ok", "created_at": now}
