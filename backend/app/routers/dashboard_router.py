from fastapi import APIRouter, Depends, HTTPException, status
from pymongo.errors import PyMongoError

from app.db import get_database
from app.dependencies import get_current_user
from app.schemas import ActivityItem, DashboardCharts, DashboardSummary
from app.services.dashboard_service import (
    fetch_dashboard_charts,
    fetch_dashboard_summary,
    fetch_recent_activities,
)

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def dashboard_summary(user: dict = Depends(get_current_user)) -> DashboardSummary:
    try:
        database = get_database()
        return await fetch_dashboard_summary(database, user["_id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load dashboard summary") from exc


@router.get("/charts", response_model=DashboardCharts)
async def dashboard_charts(user: dict = Depends(get_current_user)) -> DashboardCharts:
    try:
        database = get_database()
        return await fetch_dashboard_charts(database, user["_id"])
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load chart data") from exc


@router.get("/activities", response_model=list[ActivityItem])
async def user_activities(user: dict = Depends(get_current_user)) -> list[ActivityItem]:
    try:
        database = get_database()
        return await fetch_recent_activities(database, user["_id"], limit=30)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except PyMongoError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load activities") from exc
