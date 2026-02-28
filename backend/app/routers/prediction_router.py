from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.db import get_database
from app.dependencies import get_current_user
from app.schemas import (
    PredictionRequest,
    PredictionResponse,
    RecommendationRequest,
    RecommendationResponse,
)
from app.services.activity_service import log_activity
from app.services.model_service import model_service

router = APIRouter(prefix="/prediction", tags=["prediction"])
ACRE_PER_HECTARE = 2.47105
QUINTAL_PER_TON = 10.0


@router.post("/predict", response_model=PredictionResponse)
async def predict_yield(
    payload: PredictionRequest,
    user: dict = Depends(get_current_user),
) -> PredictionResponse:
    output = model_service.predict(payload)
    area_hectares = payload.area_hectares
    area_acres = area_hectares * ACRE_PER_HECTARE
    yield_ton_hectare = output.yield_ton_hectare
    yield_quintal_hectare = yield_ton_hectare * QUINTAL_PER_TON
    yield_quintal_acre = yield_quintal_hectare / ACRE_PER_HECTARE
    total_tons = yield_ton_hectare * area_hectares
    total_quintals = total_tons * QUINTAL_PER_TON

    try:
        database = get_database()
        await database.predictions.insert_one(
            {
                "user_id": user["_id"],
                "input": payload.model_dump(),
                "predicted_yield_ton_hectare": yield_ton_hectare,
                "predicted_yield_quintal_hectare": yield_quintal_hectare,
                "predicted_yield_quintal_acre": yield_quintal_acre,
                "predicted_total_tons": total_tons,
                "predicted_total_quintals": total_quintals,
                "area_hectares": area_hectares,
                "area_acres": area_acres,
                "model_used": output.model_used,
                "created_at": output.created_at,
            }
        )
        detail = (
            f"{payload.crop.title()} in {payload.state.title()}: "
            f"{yield_quintal_acre:.2f} q/acre ({yield_quintal_hectare:.2f} q/ha)"
        )
        await log_activity(user["_id"], "prediction", detail)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save prediction") from exc

    return PredictionResponse(
        predicted_yield_ton_hectare=round(yield_ton_hectare, 3),
        predicted_yield_quintal_hectare=round(yield_quintal_hectare, 3),
        predicted_yield_quintal_acre=round(yield_quintal_acre, 3),
        predicted_total_tons=round(total_tons, 3),
        predicted_total_quintals=round(total_quintals, 3),
        area_hectares=round(area_hectares, 3),
        area_acres=round(area_acres, 3),
        model_used=output.model_used,
        created_at=output.created_at,
    )


@router.post("/recommend", response_model=RecommendationResponse)
async def recommend_crops(
    payload: RecommendationRequest,
    user: dict = Depends(get_current_user),
) -> RecommendationResponse:
    now = datetime.now(UTC)
    request = PredictionRequest(**payload.model_dump())
    recommendations, model_used = model_service.recommend(request, top_n=payload.top_n)

    try:
        database = get_database()
        await database.recommendations.insert_one(
            {
                "user_id": user["_id"],
                "input": payload.model_dump(),
                "recommendations": [item.model_dump() for item in recommendations],
                "model_used": model_used,
                "created_at": now,
            }
        )
        crops = ", ".join([r.crop for r in recommendations[:3]])
        await log_activity(user["_id"], "recommendation", f"Top crops suggested: {crops}")
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save recommendation") from exc

    return RecommendationResponse(recommendations=recommendations, model_used=model_used, created_at=now)
