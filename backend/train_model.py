import argparse
import json
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from pandas.api.types import is_numeric_dtype
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor, VotingRegressor
from sklearn.impute import SimpleImputer
from sklearn.metrics import mean_squared_error, r2_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

try:
    from xgboost import XGBRegressor

    HAS_XGB = True
except Exception:
    HAS_XGB = False


TARGET_CANDIDATES = [
    "yield_ton_hectare",
    "yield",
    "target_yield",
    "production_per_hectare",
    "hg_ha_yield",
    "hg_ha",
]

TARGET_SCALE_TO_TON_HECTARE = {
    "yield_ton_hectare": 1.0,
    "yield": 1.0,
    "target_yield": 1.0,
    "production_per_hectare": 1.0,
    "hg_ha_yield": 0.0001,
    "hg_ha": 0.0001,
}


def normalize_columns(frame: pd.DataFrame) -> pd.DataFrame:
    normalized = []
    for col in frame.columns:
        c = str(col).strip().lower()
        c = c.replace(" ", "_").replace("-", "_").replace("/", "_")
        c = c.replace("(", "").replace(")", "").replace(".", "")
        normalized.append(c)
    frame = frame.copy()
    frame.columns = normalized
    return frame


def find_target_column(frame: pd.DataFrame) -> str:
    for candidate in TARGET_CANDIDATES:
        if candidate in frame.columns:
            return candidate
    raise ValueError(
        f"Could not find a target column. Expected one of: {', '.join(TARGET_CANDIDATES)}"
    )


def build_model_pipeline(numeric_features: list[str], categorical_features: list[str]) -> VotingRegressor:
    numeric_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="median")),
            ("scaler", StandardScaler()),
        ]
    )
    categorical_pipeline = Pipeline(
        steps=[
            ("imputer", SimpleImputer(strategy="most_frequent")),
            ("onehot", OneHotEncoder(handle_unknown="ignore")),
        ]
    )

    preprocessor = ColumnTransformer(
        transformers=[
            ("numeric", numeric_pipeline, numeric_features),
            ("categorical", categorical_pipeline, categorical_features),
        ],
        remainder="drop",
    )

    rf_estimator = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            (
                "model",
                RandomForestRegressor(
                    n_estimators=350,
                    random_state=42,
                    n_jobs=-1,
                ),
            ),
        ]
    )

    if HAS_XGB:
        second_model = XGBRegressor(
            objective="reg:squarederror",
            n_estimators=450,
            learning_rate=0.05,
            max_depth=6,
            subsample=0.9,
            colsample_bytree=0.9,
            random_state=42,
        )
        second_name = "xgb"
    else:
        second_model = GradientBoostingRegressor(random_state=42)
        second_name = "gbr"

    second_estimator = Pipeline(
        steps=[
            ("preprocess", preprocessor),
            ("model", second_model),
        ]
    )

    return VotingRegressor(
        estimators=[
            ("rf", rf_estimator),
            (second_name, second_estimator),
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Train crop yield ensemble model.")
    parser.add_argument(
        "--dataset",
        type=str,
        default="backend/data/raw/crop_yield.csv",
        help="Path to training CSV",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="backend/models/crop_yield_model.joblib",
        help="Path to save model artifact",
    )
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Dataset not found at {dataset_path}. Put a CSV there or run scripts/download_datasets.py."
        )

    frame = pd.read_csv(dataset_path)
    frame = normalize_columns(frame)
    target_column = find_target_column(frame)
    target_scale_to_ton_hectare = TARGET_SCALE_TO_TON_HECTARE.get(target_column, 1.0)
    frame = frame.dropna(subset=[target_column]).copy()

    drop_candidates = {"id", "index", "unnamed_0"}
    feature_columns = [c for c in frame.columns if c != target_column and c not in drop_candidates]
    features = frame[feature_columns].copy()
    target = frame[target_column].astype(float)

    categorical_columns = [c for c in features.columns if not is_numeric_dtype(features[c])]
    numeric_columns = [c for c in features.columns if is_numeric_dtype(features[c])]

    for col in categorical_columns:
        features[col] = features[col].astype(str)

    x_train, x_test, y_train, y_test = train_test_split(
        features,
        target,
        test_size=0.2,
        random_state=42,
    )

    model = build_model_pipeline(numeric_columns, categorical_columns)
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)
    rmse = float(np.sqrt(mean_squared_error(y_test, predictions)))
    r2 = float(r2_score(y_test, predictions))
    rmse_ton_hectare = rmse * target_scale_to_ton_hectare

    crop_col = None
    for candidate in ["crop", "item", "crop_name"]:
        if candidate in frame.columns:
            crop_col = candidate
            break
    known_crops = sorted(frame[crop_col].dropna().astype(str).str.lower().unique().tolist()) if crop_col else []

    artifact = {
        "model": model,
        "model_name": "voting_regressor_rf_xgb" if HAS_XGB else "voting_regressor_rf_gbr",
        "feature_columns": feature_columns,
        "categorical_columns": categorical_columns,
        "numeric_columns": numeric_columns,
        "target_column": target_column,
        "target_scale_to_ton_hectare": target_scale_to_ton_hectare,
        "known_crops": known_crops,
        "metrics": {"rmse": rmse, "r2": r2, "rmse_ton_hectare": rmse_ton_hectare},
    }

    output_path = Path(args.out)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(artifact, output_path)

    metrics_path = output_path.with_suffix(".metrics.json")
    metrics_path.write_text(json.dumps(artifact["metrics"], indent=2), encoding="utf-8")

    print(f"Model saved to {output_path}")
    print(f"RMSE (raw target unit): {rmse:.4f}")
    print(f"RMSE (ton/ha): {rmse_ton_hectare:.4f}")
    print(f"R2: {r2:.4f}")


if __name__ == "__main__":
    main()
