# Dataset Notes

Use `backend/scripts/download_datasets.py` to fetch public CSV datasets into `backend/data/raw`.

## Primary expected file

- `backend/data/raw/crop_yield.csv`

The training script (`backend/train_model.py`) reads this file by default.

## If auto-download fails

1. Download any crop yield CSV manually.
2. Put it at `backend/data/raw/crop_yield.csv`.
3. Ensure the target column is one of:
- `yield_ton_hectare`
- `yield`
- `target_yield`
- `production_per_hectare`
- `hg_ha_yield`
- `hg_ha`
4. Run: `python backend/train_model.py`

### Unit handling note

If dataset target is `hg_ha_yield` / `hg_ha`, training stores a scale factor and API converts predictions to `ton/ha`, `q/ha`, and `q/acre` automatically.

## Public dataset sources configured in script

- Global crop yield + climate:
  `https://raw.githubusercontent.com/ManikantaSanjay/crop_yield_prediction_regression/master/yield_df.csv`
- India crop production records:
  `https://raw.githubusercontent.com/nileshely/Crop-Datasets-for-All-Indian-States/main/Crops_data.csv`
- Climate + soil + crop yield:
  `https://raw.githubusercontent.com/Kevinbose/Crop-Yield-Prediction/main/crop_yield_climate_soil_data_2019_2023.csv`
