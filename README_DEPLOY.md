# Deployment Guide 🚀

This document outlines how to deploy the **SiliconMind FPGA AI Intelligence Platform** to production.

## 1. Backend (Render)

### Steps:
1. Create a new **Web Service** on [Render](https://render.com/).
2. Connect this GitHub repository: `https://github.com/saiprasad367/SILICON_MIND.git`.
3. Set the following configurations:
   - **Root Directory**: `backend` (CRITICAL)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
4. Add **Environment Variables** in Render:
   - `PORT`: `10000` (Render default)
   - `SECRET_KEY`: (Something random)
   - `FLASK_DEBUG`: `0`
   - `PYTHON_VERSION`: `3.11.0`
   - `CORS_ORIGINS`: `https://your-vercel-frontend-url.vercel.app` (Update after frontend deploy)
   - `SUPABASE_URL`: (Optional - Highly recommended for DB persistence on Render)
   - `SUPABASE_KEY`: (Optional)

> [!NOTE]
> Since Render's free tier disk is ephemeral, your SQLite database (`fpgadata.db`) will reset on every deploy. Connect **Supabase** (as configured in `backend/config.py`) to keep your analysis records permanently.

---

## 2. Frontend (Vercel)

### Steps:
1. Create a new project on [Vercel](https://vercel.com/).
2. Connect the same repository.
3. Set the following configurations:
   - **Root Directory**: `frontend`
   - **Framework Preset**: `Vite`
   - **Build Command**: `npm run build`
   - **Output Directory**: `dist`
4. Add **Environment Variables**:
   - `VITE_API_URL`: `https://your-render-backend-url.onrender.com` (The URL provided by Render)

---

## 3. Production Readiness Check

- [x] **Git Push**: Completed. Files are at [saiprasad367/SILICON_MIND](https://github.com/saiprasad367/SILICON_MIND.git).
- [x] **Large Files**: The 84MB dataset was successfully pushed.
- [x] **CORS**: Backend is configured to accept custom origins via environment variables.
- [x] **Production Server**: `gunicorn` is ready in `requirements.txt`.

### How to test your live app:
1. Open your Vercel URL.
2. Upload a sample Vivado report.
3. The "AI engine online" badge should appear if the backend connection is successful.
4. Check the "AI Insights" panel to see the live XGBoost ensemble inference.
