from __future__ import annotations

from datetime import datetime

from app.schemas import ActivityItem, DashboardCharts, DashboardSummary

ACRE_PER_HECTARE = 2.47105
QUINTAL_PER_TON = 10.0
LEGACY_TON_HECTARE_THRESHOLD = 100.0
MAX_DASHBOARD_ROWS = 5000


def normalize_ton_hectare(value: float | int | None) -> float:
    raw = float(value or 0.0)
    if raw > LEGACY_TON_HECTARE_THRESHOLD:
        # Legacy records may have stored hg/ha directly.
        return raw / 10000.0
    return raw


async def fetch_dashboard_summary(database, user_id: str) -> DashboardSummary:
    predictions = (
        await database.predictions.find({"user_id": user_id})
        .sort("created_at", -1)
        .to_list(length=MAX_DASHBOARD_ROWS)
    )
    recommendations = await database.recommendations.find({"user_id": user_id}).to_list(length=MAX_DASHBOARD_ROWS)
    surveys = await database.surveys.find({"user_id": user_id}).to_list(length=MAX_DASHBOARD_ROWS)

    latest_ton_hectare = (
        normalize_ton_hectare(predictions[0].get("predicted_yield_ton_hectare")) if predictions else None
    )
    latest_quintal_hectare = (latest_ton_hectare * QUINTAL_PER_TON) if latest_ton_hectare is not None else None
    latest_quintal_acre = (
        (latest_quintal_hectare / ACRE_PER_HECTARE) if latest_quintal_hectare is not None else None
    )

    return DashboardSummary(
        total_predictions=len(predictions),
        total_recommendations=len(recommendations),
        total_surveys=len(surveys),
        latest_prediction=round(latest_ton_hectare, 3) if latest_ton_hectare is not None else None,
        latest_yield_quintal_hectare=(
            round(latest_quintal_hectare, 3) if latest_quintal_hectare is not None else None
        ),
        latest_yield_quintal_acre=round(latest_quintal_acre, 3) if latest_quintal_acre is not None else None,
    )


async def fetch_dashboard_charts(database, user_id: str) -> DashboardCharts:
    predictions = await database.predictions.find({"user_id": user_id}).to_list(length=MAX_DASHBOARD_ROWS)
    surveys = await database.surveys.find({"user_id": user_id}).to_list(length=MAX_DASHBOARD_ROWS)

    monthly_data: dict[str, dict[str, float]] = {}
    crop_data: dict[str, int] = {}
    survey_data: dict[str, dict[str, float]] = {}

    for row in predictions:
        created_at = row.get("created_at")
        if not isinstance(created_at, datetime):
            continue
        month = created_at.strftime("%Y-%m")
        normalized_yield = normalize_ton_hectare(row.get("predicted_yield_ton_hectare"))
        bucket = monthly_data.setdefault(month, {"yield_sum": 0.0, "count": 0.0})
        bucket["yield_sum"] += normalized_yield
        bucket["count"] += 1.0

        crop = str(row.get("input", {}).get("crop") or "unknown")
        crop_data[crop] = crop_data.get(crop, 0) + 1

    for row in surveys:
        created_at = row.get("created_at")
        if not isinstance(created_at, datetime):
            continue
        month = created_at.strftime("%Y-%m")
        score = float(row.get("satisfaction_score") or 0.0)
        bucket = survey_data.setdefault(month, {"score_sum": 0.0, "count": 0.0})
        bucket["score_sum"] += score
        bucket["count"] += 1.0

    monthly_predictions = []
    for month in sorted(monthly_data.keys()):
        count = int(monthly_data[month]["count"])
        if count == 0:
            continue
        avg_yield = monthly_data[month]["yield_sum"] / count
        monthly_predictions.append(
            {
                "month": month,
                "avg_yield": round(avg_yield, 3),
                "avg_yield_quintal_hectare": round(avg_yield * QUINTAL_PER_TON, 3),
                "avg_yield_quintal_acre": round((avg_yield * QUINTAL_PER_TON) / ACRE_PER_HECTARE, 3),
                "predictions": count,
            }
        )

    crop_distribution = [
        {"crop": crop, "count": count}
        for crop, count in sorted(crop_data.items(), key=lambda item: item[1], reverse=True)[:8]
    ]

    survey_trend = []
    for month in sorted(survey_data.keys()):
        count = int(survey_data[month]["count"])
        if count == 0:
            continue
        average = survey_data[month]["score_sum"] / count
        survey_trend.append({"month": month, "avg_satisfaction": round(average, 3)})

    return DashboardCharts(
        monthly_predictions=monthly_predictions,
        crop_distribution=crop_distribution,
        survey_trend=survey_trend,
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
