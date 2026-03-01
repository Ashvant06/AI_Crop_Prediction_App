from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.db import connect_to_mongo, disconnect_mongo
from app.routers.auth_router import router as auth_router
from app.routers.chat_router import router as chat_router
from app.routers.dashboard_router import router as dashboard_router
from app.routers.news_router import router as news_router
from app.routers.prediction_router import router as prediction_router
from app.routers.survey_router import router as survey_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    await connect_to_mongo()
    yield
    await disconnect_mongo()


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(prediction_router)
app.include_router(survey_router)
app.include_router(dashboard_router)
app.include_router(chat_router)
app.include_router(news_router)


@app.get("/health")
async def health() -> dict:
    return {"status": "ok", "service": settings.app_name}
