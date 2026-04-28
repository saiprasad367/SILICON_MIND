"""
config.py - Central configuration for FPGA AI Pilot Backend
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ─── Paths ────────────────────────────────────────────────────────────────────
UPLOAD_FOLDER   = os.path.join(BASE_DIR, "uploads")
MODEL_FOLDER    = os.path.join(BASE_DIR, "models")
DATASET_FOLDER  = os.path.join(BASE_DIR, "dataset")
REPORT_FOLDER   = os.path.join(BASE_DIR, "reports")
RL_AGENT_FOLDER = os.path.join(MODEL_FOLDER, "rlagent")
DB_PATH         = os.path.join(BASE_DIR, "database", "fpgadata.db")

# Main 200k FPGA dataset (always use this as source of truth)
DATASET_PATH    = os.path.join(BASE_DIR, "fpga_dataset_200k.csv")

# ─── Model file names ─────────────────────────────────────────────────────────
STATUS_MODEL_PATH   = os.path.join(MODEL_FOLDER, "predictor.pkl")
HEALTH_MODEL_PATH   = os.path.join(MODEL_FOLDER, "health_regressor.pkl")
ENCODER_PATH        = os.path.join(MODEL_FOLDER, "encoder.pkl")
RL_AGENT_PATH       = os.path.join(RL_AGENT_FOLDER, "ppo_fpga")

# ─── Flask ────────────────────────────────────────────────────────────────────
SECRET_KEY         = os.environ.get("SECRET_KEY", "fpga-ai-pilot-secret-2024")
DEBUG              = os.environ.get("FLASK_DEBUG", "1") == "1"
PORT               = int(os.environ.get("PORT", 5000))
MAX_CONTENT_LENGTH = 50 * 1024 * 1024   # 50 MB

# ─── Supabase ─────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# ─── ML settings ──────────────────────────────────────────────────────────────
MIN_ROWS_TO_TRAIN = 3    # min rows to retrain
RETRAIN_INTERVAL  = 10   # retrain every N new uploads

# ─── Allowed file extensions ──────────────────────────────────────────────────
ALLOWED_EXTENSIONS = {".rpt", ".txt", ".xdc", ".log"}

# ─── CORS -- allow all Vite dev ports + Production ───────────────────────────
_env_cors = os.environ.get("CORS_ORIGINS", "")
if _env_cors:
    CORS_ORIGINS = [o.strip() for o in _env_cors.split(",")]
else:
    CORS_ORIGINS = [
        "http://localhost:5173", "http://localhost:8080",
        "http://localhost:8081", "http://localhost:8082",
        "http://localhost:3000", "http://127.0.0.1:5173",
        "http://127.0.0.1:8081", "http://127.0.0.1:8082",
    ]

# Create all required directories on import
for _dir in [UPLOAD_FOLDER, MODEL_FOLDER, DATASET_FOLDER, REPORT_FOLDER,
             RL_AGENT_FOLDER, os.path.dirname(DB_PATH)]:
    os.makedirs(_dir, exist_ok=True)
