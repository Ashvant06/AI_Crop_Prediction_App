import argparse
from pathlib import Path

import httpx


DATASETS = [
    {
        "name": "yield_df",
        "url": "https://raw.githubusercontent.com/ManikantaSanjay/crop_yield_prediction_regression/master/yield_df.csv",
        "filename": "crop_yield.csv",
        "description": "Global crop yield + rainfall + temperature dataset",
    },
    {
        "name": "india_crop_state",
        "url": "https://raw.githubusercontent.com/nileshely/Crop-Datasets-for-All-Indian-States/main/Crops_data.csv",
        "filename": "india_crop_state.csv",
        "description": "State-wise crop production records in India",
    },
    {
        "name": "climate_soil",
        "url": "https://raw.githubusercontent.com/Kevinbose/Crop-Yield-Prediction/main/crop_yield_climate_soil_data_2019_2023.csv",
        "filename": "climate_soil_crop_yield.csv",
        "description": "Climate + soil + crop yield records",
    },
]


def download_dataset(dataset: dict, out_dir: Path) -> bool:
    out_path = out_dir / dataset["filename"]
    try:
        with httpx.Client(timeout=30.0, follow_redirects=True) as client:
            response = client.get(dataset["url"])
            response.raise_for_status()
            out_path.write_bytes(response.content)
        print(f"[ok] {dataset['name']} -> {out_path}")
        return True
    except Exception as exc:
        print(f"[failed] {dataset['name']} ({dataset['url']}): {exc}")
        return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Download public crop yield datasets.")
    parser.add_argument(
        "--out-dir",
        type=str,
        default="backend/data/raw",
        help="Destination directory for downloaded CSV files",
    )
    parser.add_argument(
        "--primary-only",
        action="store_true",
        help="Download only the primary training dataset as crop_yield.csv",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    targets = DATASETS[:1] if args.primary_only else DATASETS
    success = 0
    for dataset in targets:
        if download_dataset(dataset, out_dir):
            success += 1

    print(f"Downloaded {success}/{len(targets)} dataset(s).")
    if success == 0:
        print(
            "No dataset downloaded. Manually place a CSV at "
            "backend/data/raw/crop_yield.csv and then run backend/train_model.py."
        )


if __name__ == "__main__":
    main()
