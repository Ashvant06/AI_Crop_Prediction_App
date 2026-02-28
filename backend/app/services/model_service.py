from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import numpy as np
import pandas as pd

from app.config import get_settings
from app.schemas import CropRecommendation, PredictionRequest


FEATURE_ALIASES: dict[str, list[str]] = {
    "item": ["crop"],
    "crop_name": ["crop"],
    "area": ["state"],
    "province": ["state"],
    "district_name": ["district"],
    "average_rain_fall_mm_per_year": ["avg_rainfall_mm_per_year", "rainfall_mm"],
    "rainfall": ["rainfall_mm", "avg_rainfall_mm_per_year"],
    "rainfall_mm_per_year": ["avg_rainfall_mm_per_year", "rainfall_mm"],
    "avg_temp": ["temperature_c"],
    "temperature": ["temperature_c", "avg_temp"],
    "humidity": ["humidity_pct"],
    "n": ["nitrogen"],
    "p": ["phosphorus"],
    "k": ["potassium"],
    "ph": ["soil_ph"],
    "yield_last_year": ["previous_yield_ton_hectare"],
    "pesticides_tonnes": ["pesticides_tonnes"],
}

DEFAULT_CROPS = [
    "rice",
    "wheat",
    "maize",
    "sugarcane",
    "cotton",
    "soybean",
    "barley",
    "sorghum",
]

ACRE_PER_HECTARE = 2.47105
QUINTAL_PER_TON = 10.0


def _safe_float(value: Any, fallback: float = 0.0) -> float:
    try:
        if value is None:
            return fallback
        return float(value)
    except (TypeError, ValueError):
        return fallback


@dataclass
class ModelOutput:
    yield_ton_hectare: float
    model_used: str
    created_at: datetime


class ModelService:
    def __init__(self) -> None:
        self._artifact: dict[str, Any] | None = None
        self._artifact_mtime: float | None = None

    def _resolve_model_path(self) -> Path | None:
        settings = get_settings()
        configured = Path(settings.model_artifact_path)
        repo_root = Path(__file__).resolve().parents[3]
        backend_root = Path(__file__).resolve().parents[2]
        candidates = []

        if configured.is_absolute():
            candidates.append(configured)
        else:
            candidates.extend(
                [
                    Path.cwd() / configured,
                    backend_root / configured,
                    repo_root / configured,
                    backend_root / "models" / "crop_yield_model.joblib",
                    repo_root / "backend" / "models" / "crop_yield_model.joblib",
                ]
            )

        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_artifact(self) -> dict[str, Any] | None:
        model_path = self._resolve_model_path()
        if model_path is None:
            return None

        mtime = model_path.stat().st_mtime
        if self._artifact is not None and self._artifact_mtime == mtime:
            return self._artifact

        artifact = joblib.load(model_path)
        self._artifact = artifact
        self._artifact_mtime = mtime
        return artifact

    def _target_scale_to_ton_hectare(self, artifact: dict[str, Any]) -> float:
        explicit_scale = artifact.get("target_scale_to_ton_hectare")
        if explicit_scale is not None:
            return max(0.0, float(explicit_scale))

        target_column = str(artifact.get("target_column", "")).lower()
        if target_column in {"hg_ha_yield", "hg_ha"}:
            # 1 hectogram = 0.1 kg = 0.0001 ton
            return 0.0001
        return 1.0

    def _value_for_feature(self, feature: str, payload: dict[str, Any], is_categorical: bool) -> Any:
        if feature in payload and payload[feature] is not None:
            return payload[feature]

        for alias in FEATURE_ALIASES.get(feature, []):
            if alias in payload and payload[alias] is not None:
                return payload[alias]

        # Handle common reverse aliases where user payload has model-style names.
        for source, aliases in FEATURE_ALIASES.items():
            if feature in aliases and source in payload and payload[source] is not None:
                return payload[source]

        if is_categorical:
            return "unknown"
        return 0.0

    def _build_dataframe(self, request: PredictionRequest, artifact: dict[str, Any]) -> pd.DataFrame:
        feature_columns: list[str] = artifact.get("feature_columns", [])
        categorical_columns: list[str] = artifact.get("categorical_columns", [])
        payload = request.feature_dict()

        row: dict[str, Any] = {}
        for feature in feature_columns:
            value = self._value_for_feature(feature, payload, feature in categorical_columns)
            if feature in categorical_columns:
                row[feature] = str(value)
            else:
                row[feature] = _safe_float(value, 0.0)
        return pd.DataFrame([row], columns=feature_columns)

    def _fallback_yield(self, request: PredictionRequest) -> float:
        rainfall = request.rainfall_mm or request.avg_rainfall_mm_per_year or 900.0
        temp = request.temperature_c or request.avg_temp or 25.0
        humidity = request.humidity_pct or 65.0
        soil_ph = request.soil_ph or 6.5
        n = request.nitrogen or 70.0
        p = request.phosphorus or 40.0
        k = request.potassium or 40.0
        previous = request.previous_yield_ton_hectare or 3.0

        ph_bonus = max(0.0, 1.2 - abs(soil_ph - 6.5) * 0.35)
        moisture_bonus = min(1.6, rainfall / 1000.0)
        temp_bonus = max(0.2, 1.3 - abs(temp - 24.0) * 0.05)
        nutrition_bonus = min(2.2, (n + p + k) / 120.0)
        humidity_bonus = min(1.1, humidity / 80.0)
        history_bonus = min(1.5, previous / 3.0)

        crop_factor_map = {
            "rice": 1.15,
            "wheat": 1.0,
            "maize": 0.95,
            "sugarcane": 1.35,
            "cotton": 0.9,
            "soybean": 0.85,
        }
        crop_factor = crop_factor_map.get(request.crop.lower(), 1.0)

        raw = (ph_bonus + moisture_bonus + temp_bonus + nutrition_bonus + humidity_bonus + history_bonus) * crop_factor
        return float(np.clip(raw, 0.5, 12.0))

    def predict(self, request: PredictionRequest) -> ModelOutput:
        artifact = self._load_artifact()
        timestamp = datetime.now(UTC)

        if artifact is None:
            return ModelOutput(
                yield_ton_hectare=self._fallback_yield(request),
                model_used="fallback_heuristic",
                created_at=timestamp,
            )

        model = artifact["model"]
        frame = self._build_dataframe(request, artifact)
        raw_prediction = float(model.predict(frame)[0])
        prediction = raw_prediction * self._target_scale_to_ton_hectare(artifact)

        return ModelOutput(
            yield_ton_hectare=max(0.0, prediction),
            model_used=artifact.get("model_name", type(model).__name__),
            created_at=timestamp,
        )

    def recommend(self, request: PredictionRequest, top_n: int = 5) -> tuple[list[CropRecommendation], str]:
        artifact = self._load_artifact()
        if artifact is None:
            model_used = "fallback_heuristic"
            candidate_crops = DEFAULT_CROPS
        else:
            known_crops = artifact.get("known_crops") or []
            candidate_crops = [str(c).strip().lower() for c in known_crops if str(c).strip()]
            if not candidate_crops:
                candidate_crops = DEFAULT_CROPS
            model_used = artifact.get("model_name", "ensemble_model")

        scored: list[CropRecommendation] = []
        for crop in candidate_crops[:25]:
            candidate = request.model_copy(update={"crop": crop})
            output = self.predict(candidate)
            ton_per_hectare = round(output.yield_ton_hectare, 3)
            quintal_per_hectare = round(output.yield_ton_hectare * QUINTAL_PER_TON, 3)
            quintal_per_acre = round(quintal_per_hectare / ACRE_PER_HECTARE, 3)
            scored.append(
                CropRecommendation(
                    crop=crop,
                    predicted_yield_ton_hectare=ton_per_hectare,
                    predicted_yield_quintal_hectare=quintal_per_hectare,
                    predicted_yield_quintal_acre=quintal_per_acre,
                )
            )

        ranked = sorted(scored, key=lambda item: item.predicted_yield_ton_hectare, reverse=True)
        return ranked[:top_n], model_used


model_service = ModelService()
