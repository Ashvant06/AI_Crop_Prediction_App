from fastapi import APIRouter

from app.services.news_service import fetch_tamil_nadu_agri_news

router = APIRouter(prefix="/news", tags=["news"])


@router.get("/overview")
async def overview_news(limit: int = 9) -> dict:
    return {"items": await fetch_tamil_nadu_agri_news(limit=limit)}
