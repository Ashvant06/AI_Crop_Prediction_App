from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class PhoneAuthRequest(BaseModel):
    phone_number: str = Field(min_length=8, max_length=20)
    name: str = Field(default="Farmer", min_length=2, max_length=80)


class DevAuthRequest(BaseModel):
    name: str = Field(default="Demo Farmer", min_length=2, max_length=80)
    email: str = Field(default="demo.farmer@local.dev", min_length=6, max_length=120)


class UserProfile(BaseModel):
    id: str
    name: str
    email: str
    phone_number: str | None = None
    picture: str | None = None


class AuthResponse(BaseModel):
    access_token: str
    user: UserProfile


class AgroInputBase(BaseModel):
    crop: str = Field(min_length=2, max_length=64)
    state: str = Field(min_length=2, max_length=64)
    district: str | None = Field(default=None, max_length=64)
    year: int = Field(default=2026, ge=2000, le=2100)
    area_hectares: float = Field(default=1.0, gt=0)
    rainfall_mm: float | None = None
    avg_rainfall_mm_per_year: float | None = None
    temperature_c: float | None = None
    avg_temp: float | None = None
    humidity_pct: float | None = None
    nitrogen: float | None = None
    phosphorus: float | None = None
    potassium: float | None = None
    soil_ph: float | None = None
    pesticides_tonnes: float | None = None
    previous_yield_ton_hectare: float | None = None
    ndvi: float | None = None
    user_latitude: float | None = None
    user_longitude: float | None = None
    user_locality: str | None = Field(default=None, max_length=120)

    def feature_dict(self) -> dict[str, float | str | int]:
        values = self.model_dump()
        return {k: v for k, v in values.items() if v is not None}


class PredictionRequest(AgroInputBase):
    pass


class PredictionResponse(BaseModel):
    predicted_yield_ton_hectare: float
    predicted_yield_quintal_hectare: float
    predicted_yield_quintal_acre: float
    predicted_total_tons: float
    predicted_total_quintals: float
    area_hectares: float
    area_acres: float
    model_used: str
    created_at: datetime


class RecommendationRequest(AgroInputBase):
    top_n: int = Field(default=5, ge=1, le=10)


class CropRecommendation(BaseModel):
    crop: str
    predicted_yield_ton_hectare: float
    predicted_yield_quintal_hectare: float
    predicted_yield_quintal_acre: float


class RecommendationResponse(BaseModel):
    recommendations: list[CropRecommendation]
    model_used: str
    created_at: datetime


class SurveyRequest(BaseModel):
    preferred_crops: list[str] = Field(default_factory=list)
    irrigation_method: str | None = None
    risk_appetite: str | None = None
    satisfaction_score: int = Field(ge=1, le=5)
    notes: str | None = Field(default=None, max_length=2000)
    user_latitude: float | None = None
    user_longitude: float | None = None
    user_locality: str | None = Field(default=None, max_length=120)


class ChatHistoryMessage(BaseModel):
    role: Literal["user", "assistant", "system"] = "user"
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatHistoryMessage] = Field(default_factory=list)
    context: dict[str, Any] = Field(default_factory=dict)


class ChatResponse(BaseModel):
    reply: str
    created_at: datetime
    used_tools: list[str] = Field(default_factory=list)
    tool_summaries: list[str] = Field(default_factory=list)


class MonthlyPredictionPoint(BaseModel):
    month: str
    avg_yield: float
    avg_yield_quintal_acre: float
    avg_yield_quintal_hectare: float
    predictions: int


class CropDistributionPoint(BaseModel):
    crop: str
    count: int


class SurveyTrendPoint(BaseModel):
    month: str
    avg_satisfaction: float


class DashboardSummary(BaseModel):
    total_predictions: int
    total_recommendations: int
    total_surveys: int
    latest_prediction: float | None = None
    latest_yield_quintal_acre: float | None = None
    latest_yield_quintal_hectare: float | None = None


class DashboardCharts(BaseModel):
    monthly_predictions: list[MonthlyPredictionPoint]
    crop_distribution: list[CropDistributionPoint]
    survey_trend: list[SurveyTrendPoint]


class ActivityItem(BaseModel):
    id: str
    activity_type: str
    detail: str
    created_at: datetime
