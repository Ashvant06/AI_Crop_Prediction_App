# AI Crop Yield Prediction System (React + Python + MongoDB)

Full-stack prototype for agriculture-focused yield prediction with:
- Google authentication
- User-specific saved predictions/surveys/activities
- AI chatbot guidance
- Crop recommendation and yield forecasting
- Dashboard charts and analysis
- Green-themed responsive frontend

## Tech Stack

- Frontend: React + Vite + Recharts + Google OAuth UI
- Backend: FastAPI + Python ML + JWT auth
- Database: MongoDB
- ML: Random Forest + XGBoost (fallback Gradient Boosting) + Voting ensemble

## Project Structure

```text
backend/
  app/
    main.py
    config.py
    db.py
    schemas.py
    dependencies.py
    routers/
    services/
  scripts/download_datasets.py
  train_model.py
  requirements.txt
frontend/
  src/
    api/
    components/
    context/
    pages/
    styles.css
  package.json
```

## 1. Backend Setup

Use Python `3.12` or `3.13` for best compatibility.

```bash
cd backend
# Example (Windows launcher):
py -3.13 -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate

pip install -r requirements.txt
copy .env.example .env
```

Edit `backend/.env`:
- `MONGO_URI`
- `GOOGLE_CLIENT_ID`
- `JWT_SECRET_KEY`
- (optional) `OPENAI_API_KEY`

Run API:

```bash
uvicorn app.main:app --reload --port 8000
```

## 2. Frontend Setup

```bash
cd frontend
npm install
copy .env.example .env
```

Edit `frontend/.env`:
- `VITE_API_BASE_URL=http://localhost:8000`
- `VITE_GOOGLE_CLIENT_ID=<same Google client id as backend>`

Run web app:

```bash
npm run dev
```

## 3. MongoDB

Run local MongoDB on default port:
- `mongodb://localhost:27017`

Or update `MONGO_URI` in `backend/.env`.

## 4. Datasets (Real-World CSV)

### Auto download

```bash
python backend/scripts/download_datasets.py
```

Primary training file expected:
- `backend/data/raw/crop_yield.csv`

### Manual download fallback

If auto-download is blocked, manually download any crop yield CSV and place it exactly at:
- `backend/data/raw/crop_yield.csv`

Then train:

```bash
python backend/train_model.py
```

### Dataset URLs included in code

- `https://raw.githubusercontent.com/ManikantaSanjay/crop_yield_prediction_regression/master/yield_df.csv`
- `https://raw.githubusercontent.com/nileshely/Crop-Datasets-for-All-Indian-States/main/Crops_data.csv`
- `https://raw.githubusercontent.com/Kevinbose/Crop-Yield-Prediction/main/crop_yield_climate_soil_data_2019_2023.csv`

## 5. Where to Edit for External Dataset Compatibility

If your CSV columns differ, update:

1. Target column detection in `backend/train_model.py`
- edit `TARGET_CANDIDATES`

2. Feature alias mapping for prediction inputs in `backend/app/services/model_service.py`
- edit `FEATURE_ALIASES`

3. Optional: adjust frontend form fields in `frontend/src/components/PredictionForm.jsx`

## 6. Google Authentication

1. Create OAuth client in Google Cloud Console (Web application).
2. Add authorized JS origin:
- `http://localhost:5173`
3. Add backend URL in allowed origins if needed.
4. Put same client id in:
- `backend/.env` as `GOOGLE_CLIENT_ID`
- `frontend/.env` as `VITE_GOOGLE_CLIENT_ID`

## 6.1 Demo Login (No Google Setup Required)

If you have not configured Google OAuth yet, use **Continue in Demo Mode** on login page.

- Backend dev auth endpoint: `POST /auth/dev`
- Controlled by `ALLOW_DEV_AUTH=true` in `backend/.env`

## 7. Features Included

- Google login and JWT session
- Yield prediction endpoint: `POST /prediction/predict`
- Crop recommendation endpoint: `POST /prediction/recommend`
- Survey save endpoint: `POST /survey/submit`
- Dashboard analytics endpoints:
  - `GET /dashboard/summary`
  - `GET /dashboard/charts`
  - `GET /dashboard/activities`
- Chatbot endpoint: `POST /chat/message`

## 7.1 India-Friendly Units

- Input area in frontend: **acres** (auto-converted to hectares for model)
- Yield outputs:
  - `q/acre` (quintal per acre)
  - `q/ha` (quintal per hectare)
  - total forecast in quintals
- Backend also keeps ton/hectare and tons for compatibility.

## 8. Training Notes

The backend runs with a fallback heuristic model if no trained artifact is found.

For ML-based predictions:
1. Add dataset CSV
2. Run `python backend/train_model.py`
3. Ensure artifact exists at `backend/models/crop_yield_model.joblib`

## 9. Optional Chatbot Upgrade

Set `OPENAI_API_KEY` in `backend/.env` to enable LLM responses.
Without it, chatbot uses agriculture-focused fallback guidance logic.

## 10. Generative Chat Assistant With App Access

The chatbot can execute core app features for the signed-in user:
- yield prediction (save to account)
- crop recommendation (save to account)
- survey submission
- dashboard summary and charts
- recent activities/predictions/recommendations lookup

### With OpenAI key

- Natural language + tool-calling (Generative AI mode)

### Without OpenAI key

- Local intent mode with natural prompts and command fallback.
- Examples:
  - `show dashboard summary`
  - `predict yield for wheat in punjab`
  - `recommend crops for rice in karnataka top 3`
  - `/summary`
  - `/predict {"crop":"rice","state":"karnataka"}`
