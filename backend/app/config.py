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
    google_client_ids: str = Field(default="", alias="GOOGLE_CLIENT_IDS")
    allow_dev_auth: bool = Field(default=True, alias="ALLOW_DEV_AUTH")

    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-1.5-flash", alias="GEMINI_MODEL")
    knowledge_base_paths: str = Field(
        default="backend/data/knowledge/general_agri_knowledge.json", alias="KNOWLEDGE_BASE_PATHS"
    )
    knowledge_top_k: int = Field(default=6, alias="KNOWLEDGE_TOP_K")

    model_artifact_path: str = Field(
        default="backend/models/crop_yield_model.joblib", alias="MODEL_ARTIFACT_PATH"
    )

    cors_origins: str = Field(
        default="http://localhost:5173,http://127.0.0.1:5173", alias="CORS_ORIGINS"
    )
    cors_origin_regex: str = Field(default=r"^https://.*\.onrender\.com$", alias="CORS_ORIGIN_REGEX")

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def cors_origin_regex_value(self) -> str | None:
        value = self.cors_origin_regex.strip()
        return value or None

    @property
    def knowledge_base_path_list(self) -> list[str]:
        return [item.strip() for item in self.knowledge_base_paths.split(",") if item.strip()]

    @property
    def google_client_id_list(self) -> list[str]:
        from_google_client_id = [self.google_client_id.strip()] if self.google_client_id.strip() else []
        from_google_client_ids = [item.strip() for item in self.google_client_ids.split(",") if item.strip()]
        merged = from_google_client_id + from_google_client_ids
        deduped: list[str] = []
        for item in merged:
            if item not in deduped:
                deduped.append(item)
        return deduped


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
