"""
whatif.py - POST /api/whatif
Parametric what-if simulation endpoint.
"""
import os
import logging
from flask import Blueprint, request, jsonify, current_app

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.mlservice import predict_whatif

whatif_bp = Blueprint("whatif", __name__)
logger = logging.getLogger(__name__)


@whatif_bp.route("/api/whatif", methods=["POST"])
def whatif():
    """
    Body (JSON):
    {
      "clock": 300,          // target frequency MHz
      "pipeline": 2,         // pipeline stages
      "mode": "balanced"     // perf | balanced | power
    }
    """
    data = request.get_json(force=True, silent=True) or {}

    clock    = float(data.get("clock", 300))
    pipeline = int(data.get("pipeline", 2))
    mode     = str(data.get("mode", "balanced"))

    # Use base features from latest session if available
    session  = current_app.config.get("LATEST_SESSION")
    base_features = session.get("features", {}) if session else {}

    result = predict_whatif(base_features, clock_mhz=clock, pipeline_stages=pipeline, mode=mode)
    return jsonify(result)
