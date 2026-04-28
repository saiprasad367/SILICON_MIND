"""
predict.py - GET /api/analyze
Transforms backend session data → frontend-ready JSON payload.
NO mock data — returns 404 if no analysis has been run.
"""
import os
import logging
from flask import Blueprint, jsonify, current_app

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.dbservice import get_latest_analysis
from services.featureengineer import power_vs_performance_curve, infer_clocks

predict_bp = Blueprint("predict", __name__)
logger = logging.getLogger(__name__)


def _build_frontend_payload(session: dict) -> dict:
    """Map backend session → exact shape the React frontend expects."""
    parsed   = session.get("parsed", {})
    features = session.get("features", {})
    ml       = session.get("ml_result", {})
    ai       = session.get("ai_result", {})
    timing   = parsed.get("timing", {})
    power    = parsed.get("power", {})
    drc_list = parsed.get("drc", [])
    util     = parsed.get("utilization", [])
    cong     = parsed.get("congestion", {})
    rl       = session.get("rl_result", {})

    return {
        "design": {
            "name":               session.get("design_name", "fpga_design"),
            "device":             features.get("fpga_device", "xczu7ev-ffvc1156-2-e"),
            "family":             "Zynq UltraScale+ MPSoC",
            "healthScore":        ml.get("health_score", 0),
            "bitstreamReadiness": ml.get("bitstream_readiness", 0),
            "designStatus":       ml.get("design_status", "UNKNOWN"),
            "confidence":         ml.get("confidence", 0),
            "modelUsed":          ml.get("model_used", "rule_based"),
            "classProbabilities": ml.get("class_probabilities", {}),
        },
        "power": {
            "total":     features.get("total_power_w", 0),
            "dynamic":   features.get("dynamic_power_w", 0),
            "static":    features.get("static_power_w", 0),
            "breakdown": power.get("breakdown", []),
            "modules":   power.get("modules", []),
        },
        "timing": {
            "slack":        timing.get("slack", 0),
            "status":       timing.get("status", "UNKNOWN"),
            "targetFreq":   timing.get("target_freq", 0),
            "achievedFreq": timing.get("achieved_freq", 0),
            "criticalPath": timing.get("critical_path", {}),
        },
        "utilization":  util,
        "congestion":   cong,
        "drc":          drc_list,
        "insights":     ai.get("insights", []),
        "recommendations": ai.get("recommendations", []),
        "rootCause":    ai.get("root_cause", ""),
        "bestStrategy": ai.get("best_strategy", ""),
        "aiPrediction": ai.get("ai_prediction", ""),
        "rlInfo":       rl,
        "powerVsPerf":  power_vs_performance_curve(features),
        "clocks":       infer_clocks(timing),
        "cdcViolations": features.get("cdc_violations", 0),
    }


@predict_bp.route("/api/analyze", methods=["GET"])
def analyze():
    # Priority 1: fresh upload session in memory
    session = current_app.config.get("LATEST_SESSION")
    if session:
        return jsonify(_build_frontend_payload(session))

    # Priority 2: last record from DB
    record = get_latest_analysis()
    if record:
        import json as _json
        insights = record.get("ai_insights", "[]")
        if isinstance(insights, str):
            try:
                insights = _json.loads(insights)
            except Exception:
                insights = []

        features = {
            "total_power_w":           record.get("total_power_w", 0),
            "dynamic_power_w":         record.get("dynamic_power_w", 0),
            "static_power_w":          record.get("static_power_w", 0),
            "lut_util_percent":        record.get("lut_util_pct", 0),
            "ff_util_percent":         record.get("ff_util_pct", 0),
            "bram_util_percent":       record.get("bram_util_pct", 0),
            "dsp_util_percent":        record.get("dsp_util_pct", 0),
            "worst_negative_slack_ns": record.get("worst_negative_slack_ns", 0),
            "timing_met_flag":         record.get("timing_met_flag", 0),
            "target_frequency_mhz":   record.get("target_freq_mhz", 300),
            "achieved_freq_mhz":       record.get("achieved_freq_mhz", 0),
            "total_drc_violations":    record.get("total_drc_violations", 0),
            "drc_error_flag":          record.get("drc_errors", 0),
            "congested_regions_count": record.get("congestion_overall", 0),
        }
        session = {
            "design_name": record.get("design_name", "fpga_design"),
            "parsed": {
                "power": {"breakdown": [], "modules": []},
                "timing": {
                    "slack":        features["worst_negative_slack_ns"],
                    "status":       "PASS" if features["timing_met_flag"] else "FAIL",
                    "target_freq":  features["target_frequency_mhz"],
                    "achieved_freq": features["achieved_freq_mhz"],
                    "critical_path": {},
                },
                "utilization": [],
                "congestion":  {"overall": features["congested_regions_count"], "hotspots": []},
                "drc": [],
            },
            "features":  features,
            "ml_result": {
                "design_status":       record.get("design_status", "UNKNOWN"),
                "health_score":        record.get("health_score", 0),
                "bitstream_readiness": record.get("bitstream_readiness", 0),
                "confidence":          record.get("confidence", 0),
                "model_used":          record.get("model_used", "rule_based"),
            },
            "ai_result": {
                "ai_prediction":   record.get("design_status", "UNKNOWN"),
                "confidence":      record.get("confidence", 0),
                "insights":        insights,
                "recommendations": [],
                "root_cause":      "",
                "best_strategy":   record.get("best_strategy", ""),
            },
            "rl_result": {},
        }
        return jsonify(_build_frontend_payload(session))

    return jsonify({
        "error": "No analysis available. Please upload your Vivado report files first.",
        "code": "NO_ANALYSIS",
    }), 404


@predict_bp.route("/api/status", methods=["GET"])
def status():
    ready = current_app.config.get("ANALYSIS_READY", False)
    error = current_app.config.get("ANALYSIS_ERROR")
    has_session = current_app.config.get("LATEST_SESSION") is not None
    return jsonify({
        "status":          "ok",
        "analysis_ready":  ready or has_session,
        "has_session":     has_session,
        "error":           error,
        "message":         "FPGA AI Pilot backend running.",
    })
