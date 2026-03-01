from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="AI Crop Yield Prediction API", alias="APP_NAME")
    app_env: str = Field(default="development", alias="APP_ENV")
    api_port: int = Field(default=8000, alias="API_PORT")

    jwt_secret_key: str = Field(default="change_me", alias="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_minutes: int = Field(default=1440, alias="JWT_EXPIRE_MINUTES")

    mongo_uri: str = Field(default="mongodb://localhost:27017", alias="MONGO_URI")
    mongo_db_name: str = Field(default="crop_yield_ai", alias="MONGO_DB_NAME")
    local_db_fallback: bool = Field(default=True, alias="LOCAL_DB_FALLBACK")
    local_db_path: str = Field(default="backend/data/local_store.json", alias="LOCAL_DB_PATH")

    google_client_id: str = Field(default="", alias="GOOGLE_CLIENT_ID")
    allow_dev_auth: bool = Field(default=True, alias="ALLOW_DEV_AUTH")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")

    model_artifact_path: str = Field(
        default="backend/models/crop_yield_model.joblib", alias="MODEL_ARTIFACT_PATH"
    )

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
