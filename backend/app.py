"""
app.py - FPGA AI Pilot · Flask Backend Entry Point
"""
import os
import sys
import logging

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify
from flask_cors import CORS

from config import SECRET_KEY, DEBUG, PORT, MAX_CONTENT_LENGTH, CORS_ORIGINS
from services.dbservice import init_db
from services.mlservice import load_models
from services.rlservice import load_agent
from routes.upload  import upload_bp
from routes.predict import predict_bp
from routes.whatif  import whatif_bp
from routes.compare import compare_bp
from routes.report  import report_bp
from routes.train   import train_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("fpga-ai-pilot")


def create_app() -> Flask:
    app = Flask(__name__, static_folder="static", template_folder="templates")
    app.secret_key              = SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = MAX_CONTENT_LENGTH
    app.config["LATEST_SESSION"]     = None
    app.config["ANALYSIS_READY"]     = False
    app.config["ANALYSIS_ERROR"]     = None

    CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}},
         supports_credentials=True)

    for bp in [upload_bp, predict_bp, whatif_bp, compare_bp, report_bp, train_bp]:
        app.register_blueprint(bp)

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large (max 50 MB)"}), 413

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error", "detail": str(e)}), 500

    @app.route("/")
    def root():
        from services.mlservice import models_ready
        return jsonify({
            "service":       "FPGA AI Pilot Backend",
            "version":       "2.0.0",
            "status":        "running",
            "models_ready":  models_ready(),
            "endpoints": [
                "POST /api/upload",
                "GET  /api/analyze",
                "GET  /api/analysis_ready",
                "POST /api/whatif",
                "POST /api/compare",
                "GET  /api/designs",
                "GET  /api/report",
                "POST /api/retrain",
                "GET  /api/status",
            ],
        })

    return app


# ─── Production Entry Point ───────────────────────────────────────────────────

# 1. Initialize core services
logger.info("🚀 Initialising FPGA AI Pilot backend …")
init_db()
load_models()
load_agent()

# 2. Create the Flask app instance at module level (required for Gunicorn)
app = create_app()

from services.mlservice import models_ready
if not models_ready():
    logger.warning(
        "⚠️  ML models not found! Backend will run in rule-based fallback mode."
    )
else:
    logger.info("✅ ML models loaded — XGBoost + MLP ensemble ready")

# ─── Dev Server ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logger.info(f"✅ Dev server starting — http://localhost:{PORT}")
    app.run(host="0.0.0.0", port=PORT, debug=DEBUG, threaded=True)
