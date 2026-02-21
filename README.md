# NeuroLens

NeuroLens is a two-part app:
- `backend.py`: FastAPI backend for environment simulation + chatbot API
- `neuro_dashboard.py`: Streamlit frontend for Parent/Child views

## Project Structure

- `backend.py` - FastAPI service
- `neuro_dashboard.py` - Streamlit app
- `requirements.txt` - Python dependencies
- `render.yaml` - Render backend deployment config
- `.env` - local environment variables (not committed)

## Local Setup

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

Create `.env` in project root:

```env
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-8b-instant
```

`GROQ_MODEL` is optional.

### 3. Run backend

```bash
uvicorn backend:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```bash
curl http://127.0.0.1:8000/healthz
```

Expected response:

```json
{"status":"ok"}
```

### 4. Run Streamlit frontend

In a second terminal:

```bash
streamlit run neuro_dashboard.py
```

The frontend uses this API URL priority:
1. `st.secrets["API_URL"]`
2. `API_URL` environment variable
3. default `http://127.0.0.1:8000`

## Deploy Backend (Render)

### Option A: Blueprint (recommended)
1. Push this repo to GitHub.
2. In Render, choose **New + -> Blueprint**.
3. Select this repo.
4. Render reads `render.yaml` and creates the backend service.
5. Add env var:
   - `GROQ_API_KEY` (required for Groq responses)
   - `GROQ_MODEL` (optional)

### Option B: Manual Web Service
Use:
- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn backend:app --host 0.0.0.0 --port $PORT`
- Health check path: `/healthz`

After deploy, note your backend URL, for example:
`https://neurolens-backend.onrender.com`

## Deploy Frontend (Streamlit Community Cloud)

1. Go to Streamlit Community Cloud.
2. Create a new app from your GitHub repo.
3. Set main file path: `neuro_dashboard.py`
4. In app **Settings -> Secrets**, add:

```toml
API_URL = "https://your-render-backend-url"
```

5. Deploy/redeploy.

## GitHub Push

If repo is not initialized yet:

```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/<your-username>/<repo-name>.git
git push -u origin main
```

## Notes

- `.env` is ignored by `.gitignore` and should never be committed.
- If `GROQ_API_KEY` is missing/invalid, chatbot still returns local fallback responses.
