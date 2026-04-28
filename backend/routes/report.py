"""
report.py - GET /api/report  /  GET /api/report/<design_name>
Generate and download PDF reports.
"""
import os
import logging
from flask import Blueprint, send_file, jsonify, current_app, request

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.reportservice import generate_report
from services.dbservice import get_latest_analysis

report_bp = Blueprint("report", __name__)
logger = logging.getLogger(__name__)


@report_bp.route("/api/report", methods=["GET"])
@report_bp.route("/api/report/<design_name>", methods=["GET"])
def download_report(design_name: str = None):
    """Generate PDF from latest analysis and return as download."""
    session = current_app.config.get("LATEST_SESSION")

    if session:
        analysis_data = {
            "features":   session.get("features", {}),
            "power":      session.get("parsed", {}).get("power", {}),
            "timing":     session.get("parsed", {}).get("timing", {}),
            "drc":        session.get("parsed", {}).get("drc", []),
            "ml_result":  session.get("ml_result", {}),
            "ai_result":  session.get("ai_result", {}),
        }
        name = design_name or session.get("design_name", "fpga_design")
    else:
        record = get_latest_analysis(design_name)
        if not record:
            return jsonify({"error": "No analysis available. Upload reports first."}), 404
        import json
        insights = record.get("ai_insights", "[]")
        if isinstance(insights, str):
            insights = json.loads(insights)
        analysis_data = {
            "features": {
                "total_power_w":           record.get("total_power_w", 0),
                "dynamic_power_w":         record.get("dynamic_power_w", 0),
                "static_power_w":          record.get("static_power_w", 0),
                "worst_negative_slack_ns": record.get("worst_negative_slack_ns", 0),
                "target_freq_mhz":         record.get("target_freq_mhz", 300),
                "achieved_freq_mhz":       record.get("achieved_freq_mhz", 268),
                "lut_util_pct":            record.get("lut_util_pct", 0),
            },
            "power":  {"breakdown": [], "modules": []},
            "timing": {},
            "drc":    [],
            "ml_result": {
                "design_status":       record.get("design_status"),
                "health_score":        record.get("health_score"),
                "bitstream_readiness": record.get("bitstream_readiness"),
                "confidence":          record.get("confidence"),
                "model_used":          record.get("model_used"),
            },
            "ai_result": {
                "insights":        insights,
                "recommendations": [],
                "root_cause":      "",
                "best_strategy":   record.get("best_strategy", ""),
                "confidence":      record.get("confidence", 0),
            },
        }
        name = design_name or record.get("design_name", "fpga_design")

    try:
        pdf_path = generate_report(analysis_data, name)
        return send_file(
            pdf_path,
            as_attachment=True,
            download_name=f"fpga_report_{name}.pdf",
            mimetype="application/pdf",
        )
    except Exception as e:
        logger.exception(f"Report generation failed: {e}")
        return jsonify({"error": str(e)}), 500
