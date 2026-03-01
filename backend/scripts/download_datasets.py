import argparse
from pathlib import Path

import httpx

DATASETS = [
    {
        "name": "tn_open_sample",
        "url": "https://raw.githubusercontent.com/ManikantaSanjay/crop_yield_prediction_regression/master/yield_df.csv",
        "filename": "crop_yield.csv",
        "description": "Sample fallback dataset (non-official) for development only",
    },
]

OFFICIAL_DATA_GUIDE = """Tamil Nadu focused official dataset guidance:
1. Government of Tamil Nadu Open Data Portal: https://tn.data.gov.in/
2. India Open Government Data (Agriculture): https://www.data.gov.in/
3. TNAU AgriTech Portal references: https://www.agritech.tnau.ac.in/

Download district/state crop-yield CSV files from official portals and place them under:
backend/data/raw/official/

Then train with:
python backend/train_model.py --dataset backend/data/raw/official/<your_file>.csv --focus-state "Tamil Nadu" --source-name "Official Tamil Nadu Data" --source-url "<portal_url>"
"""


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
    parser = argparse.ArgumentParser(description="Download dataset for local development and print official-source guide.")
    parser.add_argument(
        "--out-dir",
        type=str,
        default="backend/data/raw",
        help="Destination directory for downloaded CSV files",
    )
    parser.add_argument(
        "--official-only",
        action="store_true",
        help="Skip fallback downloads and print only official dataset guidance",
    )
    args = parser.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    guide_path = out_dir / "OFFICIAL_DATASET_GUIDE.txt"
    guide_path.write_text(OFFICIAL_DATA_GUIDE, encoding="utf-8")
    print(f"[info] Official dataset guide -> {guide_path}")

    if args.official_only:
        print("Skipped fallback downloads (--official-only).")
        return

    success = 0
    for dataset in DATASETS:
        if download_dataset(dataset, out_dir):
            success += 1

    print(f"Downloaded {success}/{len(DATASETS)} dataset(s).")


if __name__ == "__main__":
    main()
