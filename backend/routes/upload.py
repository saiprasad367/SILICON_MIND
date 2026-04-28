"""
upload.py - POST /api/upload
Real file upload → parse → ML → AI → RL → store
"""
import os
import uuid
import threading
import logging
from flask import Blueprint, request, jsonify, current_app
from werkzeug.utils import secure_filename

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import UPLOAD_FOLDER

upload_bp = Blueprint("upload", __name__)
logger = logging.getLogger(__name__)


def _allowed(filename: str) -> bool:
    _, ext = os.path.splitext(filename.lower())
    return ext in {".rpt", ".txt", ".xdc", ".log", ".csv"}


def _run_pipeline(session_id: str, session_dir: str, app):
    """Full analysis pipeline — runs in background thread."""
    with app.app_context():
        try:
            from services.parserservice import parse_all
            from services.mlservice import predict, append_to_dataset
            from services.aiengine import generate_insights
            from services.rlservice import get_rl_recommendation
            from services.dbservice import save_analysis

            # 1. Parse Vivado reports
            parsed  = parse_all(session_dir)
            features = parsed["features"]
            design_name = parsed.get("design_name") or session_id

            # ─── RL Learning Loop ───────────────────────────────────────────
            # If the same design is uploaded again, treat this as the outcome
            # of the strategy recommended in the previous session.
            prev_session = current_app.config.get("LATEST_SESSION")
            if prev_session and prev_session.get("design_name") == design_name:
                prev_rl = prev_session.get("rl_result")
                if prev_rl and "action_idx" in prev_rl:
                    from services.rlservice import record_outcome
                    reward = record_outcome(
                        prev_session["features"],
                        prev_rl["action_idx"],
                        features
                    )
                    logger.info(f"RL agent updated: reward={reward:.2f} for design '{design_name}'")
            # ────────────────────────────────────────────────────────────────

            # 2. ML inference
            ml_result = predict(features)

            # 3. RL strategy recommendation
            rl_result = get_rl_recommendation(features)

            # 4. AI insights (rule-based + ML + RL combined)
            ai_result = generate_insights(
                features, ml_result,
                parsed["power"], parsed["timing"],
                parsed["drc"], rl_result,
            )

            # 5. Persist features → CSV (triggers auto-retrain)
            append_to_dataset(features, design_name)

            # 6. Save to DB
            save_analysis(design_name, features, ml_result, ai_result)

            # 7. Store full in-memory session for /api/analyze
            current_app.config["LATEST_SESSION"] = {
                "session_id":  session_id,
                "design_name": design_name,
                "parsed":      parsed,
                "features":    features,
                "ml_result":   ml_result,
                "ai_result":   ai_result,
                "rl_result":   rl_result,
            }
            current_app.config["ANALYSIS_READY"] = True
            logger.info(
                f"Pipeline done: session={session_id}, "
                f"status={ml_result['design_status']}, "
                f"health={ml_result['health_score']}, "
                f"model={ml_result['model_used']}"
            )

        except Exception as e:
            logger.exception(f"Pipeline failed for session {session_id}: {e}")
            current_app.config["ANALYSIS_ERROR"] = str(e)


@upload_bp.route("/api/upload", methods=["POST"])
def upload_files():
    files = request.files.getlist("files")
    if not files or all(f.filename == "" for f in files):
        return jsonify({"error": "No files provided"}), 400

    session_id  = str(uuid.uuid4())
    session_dir = os.path.join(UPLOAD_FOLDER, session_id)
    os.makedirs(session_dir, exist_ok=True)

    # Reset ready flag
    current_app.config["ANALYSIS_READY"] = False
    current_app.config["ANALYSIS_ERROR"]  = None

    saved = []
    for f in files:
        if f and f.filename:
            fname = secure_filename(f.filename)
            f.save(os.path.join(session_dir, fname))
            saved.append(fname)

    if not saved:
        return jsonify({"error": "No files could be saved"}), 400

    # Start pipeline in background
    app = current_app._get_current_object()
    t   = threading.Thread(target=_run_pipeline, args=(session_id, session_dir, app), daemon=True)
    t.start()

    return jsonify({
        "status":         "processing",
        "session_id":     session_id,
        "files_received": saved,
        "message":        f"Received {len(saved)} file(s) — AI analysis running.",
    })


@upload_bp.route("/api/analysis_ready", methods=["GET"])
def analysis_ready():
    """Lightweight polling endpoint — avoids re-running full analysis."""
    ready = current_app.config.get("ANALYSIS_READY", False)
    error = current_app.config.get("ANALYSIS_ERROR")
    return jsonify({"ready": ready, "error": error})
