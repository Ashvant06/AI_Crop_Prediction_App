from __future__ import annotations

from app.schemas import ActivityItem, DashboardCharts, DashboardSummary

ACRE_PER_HECTARE = 2.47105
QUINTAL_PER_TON = 10.0
LEGACY_TON_HECTARE_THRESHOLD = 100.0


def normalize_ton_hectare(value: float | int | None) -> float:
    raw = float(value or 0.0)
    if raw > LEGACY_TON_HECTARE_THRESHOLD:
        # Legacy records may have stored hg/ha directly.
        return raw / 10000.0
    return raw


async def fetch_dashboard_summary(database, user_id: str) -> DashboardSummary:
    total_predictions = await database.predictions.count_documents({"user_id": user_id})
    total_recommendations = await database.recommendations.count_documents({"user_id": user_id})
    total_surveys = await database.surveys.count_documents({"user_id": user_id})
    latest = await database.predictions.find({"user_id": user_id}).sort("created_at", -1).limit(1).to_list(1)

    latest_ton_hectare = normalize_ton_hectare(latest[0].get("predicted_yield_ton_hectare")) if latest else None
    latest_quintal_hectare = (latest_ton_hectare * QUINTAL_PER_TON) if latest_ton_hectare is not None else None
    latest_quintal_acre = (
        (latest_quintal_hectare / ACRE_PER_HECTARE) if latest_quintal_hectare is not None else None
    )

    return DashboardSummary(
        total_predictions=total_predictions,
        total_recommendations=total_recommendations,
        total_surveys=total_surveys,
        latest_prediction=round(latest_ton_hectare, 3) if latest_ton_hectare is not None else None,
        latest_yield_quintal_hectare=(
            round(latest_quintal_hectare, 3) if latest_quintal_hectare is not None else None
        ),
        latest_yield_quintal_acre=round(latest_quintal_acre, 3) if latest_quintal_acre is not None else None,
    )


async def fetch_dashboard_charts(database, user_id: str) -> DashboardCharts:
    monthly_prediction_pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$addFields": {
                "normalized_yield_ton_hectare": {
                    "$cond": [
                        {"$gt": ["$predicted_yield_ton_hectare", LEGACY_TON_HECTARE_THRESHOLD]},
                        {"$divide": ["$predicted_yield_ton_hectare", 10000]},
                        "$predicted_yield_ton_hectare",
                    ]
                }
            }
        },
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
                "avg_yield": {"$avg": "$normalized_yield_ton_hectare"},
                "predictions": {"$sum": 1},
            }
        },
        {"$sort": {"_id": 1}},
    ]
    crop_distribution_pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {"_id": "$input.crop", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
        {"$limit": 8},
    ]
    survey_trend_pipeline = [
        {"$match": {"user_id": user_id}},
        {
            "$group": {
                "_id": {"$dateToString": {"format": "%Y-%m", "date": "$created_at"}},
                "avg_satisfaction": {"$avg": "$satisfaction_score"},
            }
        },
        {"$sort": {"_id": 1}},
    ]

    monthly_rows = await database.predictions.aggregate(monthly_prediction_pipeline).to_list(length=24)
    crop_rows = await database.predictions.aggregate(crop_distribution_pipeline).to_list(length=8)
    survey_rows = await database.surveys.aggregate(survey_trend_pipeline).to_list(length=24)

    return DashboardCharts(
        monthly_predictions=[
            {
                "month": row["_id"],
                "avg_yield": round(row["avg_yield"], 3),
                "avg_yield_quintal_hectare": round(row["avg_yield"] * QUINTAL_PER_TON, 3),
                "avg_yield_quintal_acre": round((row["avg_yield"] * QUINTAL_PER_TON) / ACRE_PER_HECTARE, 3),
                "predictions": row["predictions"],
            }
            for row in monthly_rows
        ],
        crop_distribution=[
            {"crop": row["_id"] or "unknown", "count": row["count"]}
            for row in crop_rows
        ],
        survey_trend=[
            {"month": row["_id"], "avg_satisfaction": round(row["avg_satisfaction"], 3)}
            for row in survey_rows
        ],
    )


async def fetch_recent_activities(database, user_id: str, limit: int = 30) -> list[ActivityItem]:
    effective_limit = max(1, min(limit, 50))
    rows = (
        await database.activities.find({"user_id": user_id})
        .sort("created_at", -1)
        .limit(effective_limit)
        .to_list(length=effective_limit)
    )

    return [
        ActivityItem(
            id=str(row["_id"]),
            activity_type=row.get("activity_type", "activity"),
            detail=row.get("detail", ""),
            created_at=row["created_at"],
        )
        for row in rows
    ]
