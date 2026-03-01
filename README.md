# AI Crop Yield Prediction System (React + Python + MongoDB)

Full-stack prototype for agriculture-focused yield prediction with:
- Google authentication
- User-specific saved predictions/surveys/activities
- Gemini-based AI assistant guidance
- Crop recommendation and yield forecasting
- Dashboard charts and analysis
- Tamil/English interface toggle
- Live location-aware weather + IST widgets
- Multi-page responsive frontend with overview/news gallery

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
- (optional) `GEMINI_API_KEY`

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

If MongoDB is unavailable, backend can auto-fallback to a local JSON store:
- `LOCAL_DB_FALLBACK=true`
- `LOCAL_DB_PATH=backend/data/local_store.json`

## 4. Datasets (Real-World CSV)

### Auto download

```bash
python backend/scripts/download_datasets.py
```

Primary training file expected:
- `backend/data/raw/crop_yield.csv`

### Manual download fallback

If auto-download is blocked, manually download and place CSV at:
- `backend/data/raw/crop_yield.csv`

Then train:

```bash
python backend/train_model.py --focus-state "Tamil Nadu"
```

### Tamil Nadu official dataset guidance

Run:

```bash
python backend/scripts/download_datasets.py --official-only
```

This creates:
- `backend/data/raw/OFFICIAL_DATASET_GUIDE.txt`

Use official portals listed there (Tamil Nadu Open Data / data.gov.in / TNAU references), then train with:

```bash
python backend/train_model.py --dataset backend/data/raw/official/<file>.csv --focus-state "Tamil Nadu" --source-name "Official Tamil Nadu Data" --source-url "<official_url>"
```

### Development fallback URL included in code

- `https://raw.githubusercontent.com/ManikantaSanjay/crop_yield_prediction_regression/master/yield_df.csv`

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

If you use multiple Google OAuth web clients, add all backend-accepted IDs in:
- `GOOGLE_CLIENT_IDS=id1.apps.googleusercontent.com,id2.apps.googleusercontent.com`

## 6.1 Demo Login (No Google Setup Required)

If you have not configured Google OAuth yet, use **Continue in Demo Mode** on login page.

- Backend dev auth endpoint: `POST /auth/dev`
- Controlled by `ALLOW_DEV_AUTH=true` in `backend/.env`

## 6.2 Render OAuth Troubleshooting

If Google login keeps returning to the login page:

1. Frontend env (`frontend/.env` or Render Static Site env):
- `VITE_API_BASE_URL=https://<your-backend-service>.onrender.com`
- `VITE_GOOGLE_CLIENT_ID=<web_client_id>.apps.googleusercontent.com`
- Do not wrap values in quotes.

2. Backend env (Render Web Service env):
- `GOOGLE_CLIENT_ID=<same web_client_id>`
- Optional: `GOOGLE_CLIENT_IDS=<comma-separated list of accepted web client ids>`
- `CORS_ORIGINS=https://<your-frontend-site>.onrender.com,http://localhost:5173`
- `CORS_ORIGIN_REGEX=^https://.*\\.onrender\\.com$`

3. Google Cloud Console OAuth client:
- Authorized JavaScript origins must include your frontend URL, for example `https://<your-frontend-site>.onrender.com`.

4. After changing env vars in Render, redeploy both backend and frontend services.

## 7. Features Included

- Google login and JWT session
- Multi-page app routes:
  - `/overview` (intro + news gallery)
  - `/prediction`
  - `/survey`
  - `/dashboard`
  - `/assistant`
- Yield prediction endpoint: `POST /prediction/predict`
- Crop recommendation endpoint: `POST /prediction/recommend`
- Survey save endpoint: `POST /survey/submit`
- Dashboard analytics endpoints:
  - `GET /dashboard/summary`
  - `GET /dashboard/charts`
  - `GET /dashboard/activities`
- Chat/assistant endpoint: `POST /chat/message`
- News endpoint for overview gallery: `GET /news/overview`

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

## 9. Gemini Assistant Setup

Set in `backend/.env`:
- `GEMINI_API_KEY`
- `GEMINI_MODEL` (default: `gemini-1.5-flash`)
- `KNOWLEDGE_BASE_PATHS` (comma-separated JSON files for assistant knowledge)
- `KNOWLEDGE_TOP_K` (retrieval snippets count)

Without Gemini key, assistant still works in command mode (`/predict`, `/summary`, etc.).

### Assistant Knowledge Datasets

Default general agriculture knowledge dataset:
- `backend/data/knowledge/general_agri_knowledge.json`

To feed more datasets into assistant:
1. Add additional JSON files with the same structure (`id`, `title`, `content`, `tags`, `source`, `region`).
2. Add their paths to `KNOWLEDGE_BASE_PATHS` separated by commas.
3. Redeploy backend.

Convert CSV datasets into knowledge JSON quickly:

```bash
python backend/scripts/build_knowledge_from_csv.py --csv backend/data/raw/your_data.csv --out backend/data/knowledge/your_data.generated.json --title-column title --content-column content --source-name "your_source" --region "india"
```

## 10. Generative Chat Assistant With App Access

The chatbot can execute core app features for the signed-in user:
- yield prediction (save to account)
- crop recommendation (save to account)
- survey submission
- dashboard summary and charts
- recent activities/predictions/recommendations lookup

### With Gemini key

- Natural language responses via Gemini
- Command mode actions still available for app operations

### Without Gemini key

- Local intent mode with natural prompts and command fallback.
- Examples:
  - `show dashboard summary`
  - `predict yield for wheat in punjab`
  - `recommend crops for rice in karnataka top 3`
  - `/summary`
  - `/predict {"crop":"rice","state":"karnataka"}`
