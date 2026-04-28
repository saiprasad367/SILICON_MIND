"""
compare.py - POST /api/compare
Compare two design analysis sessions.
"""
import os
import logging
from flask import Blueprint, request, jsonify

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from services.dbservice import get_analysis_by_id, get_all_designs

compare_bp = Blueprint("compare", __name__)
logger = logging.getLogger(__name__)

COMPARE_FIELDS = [
    ("health_score",            "Health Score",   ""),
    ("total_power_w",           "Total Power",    "W"),
    ("worst_negative_slack_ns", "WNS",            "ns"),
    ("lut_util_pct",            "LUT Util",       "%"),
    ("ff_util_pct",             "FF Util",        "%"),
    ("congestion_overall",      "Congestion",     "%"),
    ("bitstream_readiness",     "Bitstream Ready", "%"),
]


@compare_bp.route("/api/compare", methods=["POST"])
def compare():
    """
    Body: { "id_a": 1, "id_b": 2 }
    Returns a side-by-side comparison.
    """
    data = request.get_json(force=True, silent=True) or {}
    id_a = data.get("id_a")
    id_b = data.get("id_b")

    if not id_a or not id_b:
        return jsonify({"error": "Provide id_a and id_b"}), 400

    a = get_analysis_by_id(int(id_a))
    b = get_analysis_by_id(int(id_b))

    if not a or not b:
        return jsonify({"error": "One or both analysis IDs not found"}), 404

    comparison = []
    for field, label, unit in COMPARE_FIELDS:
        va = a.get(field)
        vb = b.get(field)
        if va is None or vb is None:
            continue
        delta = round(float(vb) - float(va), 3)
        better_b = (
            (field in ["health_score", "bitstream_readiness"] and delta > 0)
            or (field == "worst_negative_slack_ns" and delta > 0)
            or (field in ["total_power_w", "congestion_overall"] and delta < 0)
        )
        comparison.append({
            "field": field,
            "label": label,
            "unit": unit,
            "design_a": va,
            "design_b": vb,
            "delta": delta,
            "better": "b" if better_b else ("a" if delta != 0 else "equal"),
        })

    return jsonify({
        "design_a": {"id": id_a, "name": a.get("design_name"), "timestamp": a.get("timestamp")},
        "design_b": {"id": id_b, "name": b.get("design_name"), "timestamp": b.get("timestamp")},
        "comparison": comparison,
    })


@compare_bp.route("/api/designs", methods=["GET"])
def list_designs():
    """Return all analyzed designs for the compare UI picker."""
    return jsonify(get_all_designs())
