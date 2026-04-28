"""
train.py - POST /api/retrain
Manually trigger model retraining.
"""
import os
import threading
import logging
from flask import Blueprint, jsonify

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.mlservice import train_models, dataset_row_count

train_bp = Blueprint("train", __name__)
logger = logging.getLogger(__name__)

_training_lock = threading.Lock()
_training_status = {"running": False, "last_result": None}


def _run_training():
    global _training_status
    try:
        _training_status["running"] = True
        success = train_models()
        _training_status["last_result"] = "success" if success else "skipped"
    except Exception as e:
        logger.exception(f"Retraining failed: {e}")
        _training_status["last_result"] = f"failed: {e}"
    finally:
        _training_status["running"] = False


@train_bp.route("/api/retrain", methods=["POST"])
def retrain():
    """Trigger background model retraining."""
    if _training_status["running"]:
        return jsonify({"status": "already_running", "message": "Training already in progress."}), 200

    rows = dataset_row_count()
    if rows < 3:
        return jsonify({
            "status": "insufficient_data",
            "message": f"Only {rows} rows in dataset. Need at least 3.",
        }), 200

    t = threading.Thread(target=_run_training, daemon=True)
    t.start()

    return jsonify({
        "status": "started",
        "message": f"Retraining started on {rows} dataset rows.",
    })


@train_bp.route("/api/retrain/status", methods=["GET"])
def retrain_status():
    return jsonify({
        "running":     _training_status["running"],
        "last_result": _training_status["last_result"],
        "dataset_rows": dataset_row_count(),
    })
