"""
mlservice.py
─────────────
ML training & inference using:
  • XGBoostClassifier   → design_status
  • XGBoost + MLP stack → health_score (regression)
  • XGBoostClassifier   → bitstream_ready
  • XGBoostRegressor    → predicted_power_w
  • XGBoostRegressor    → predicted_slack_ns

Continuous learning:
  Every new upload appends features to masterdataset.csv.
  After RETRAIN_INTERVAL rows, models auto-retrain in background.
"""

import os
import csv
import json
import logging
import threading
import numpy as np
import pandas as pd
import joblib
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

from xgboost import XGBClassifier, XGBRegressor
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    STATUS_MODEL_PATH, HEALTH_MODEL_PATH, ENCODER_PATH,
    DATASET_PATH, MIN_ROWS_TO_TRAIN, RETRAIN_INTERVAL, MODEL_FOLDER,
)

logger = logging.getLogger(__name__)

# ─── Extra model paths ────────────────────────────────────────────────────────
BITSTREAM_MODEL_PATH = os.path.join(MODEL_FOLDER, "bitstream_clf.pkl")
POWER_MODEL_PATH     = os.path.join(MODEL_FOLDER, "power_regressor.pkl")
SLACK_MODEL_PATH     = os.path.join(MODEL_FOLDER, "slack_regressor.pkl")
SCALER_PATH          = os.path.join(MODEL_FOLDER, "scaler.pkl")
FEATURE_COLS_PATH    = os.path.join(MODEL_FOLDER, "feature_cols.json")
MASTER_DATASET       = os.path.join(MODEL_FOLDER, "..", "fpga_dataset_200k.csv")

# ─── Module-level model cache ─────────────────────────────────────────────────
_models: Dict[str, Any] = {}
_feature_cols: list = []
_upload_count: int = 0
_retrain_lock = threading.Lock()

# ─── Feature columns (loaded from disk or hardcoded fallback) ─────────────────
HARDCODED_FEATURE_COLS = [
    "clock_constraint_ns", "target_frequency_mhz",
    "total_power_w", "dynamic_power_w", "static_power_w",
    "logic_power_w", "signal_power_w", "io_power_w", "clock_power_w",
    "dynamic_power_percent", "static_power_percent",
    "lut_used", "lut_total", "lut_util_percent",
    "ff_used", "ff_total", "ff_util_percent",
    "dsp_used", "dsp_total", "dsp_util_percent",
    "bram_used", "bram_total", "bram_util_percent",
    "worst_negative_slack_ns", "total_negative_slack_ns", "worst_hold_slack_ns",
    "critical_path_delay_ns", "logic_delay_ns", "routing_delay_ns",
    "timing_met_flag", "num_timing_violations",
    "critical_path_logic_levels", "max_gate_delay_ns",
    "logic_delay_percent", "routing_delay_percent",
    "total_drc_violations", "num_nstd_violations", "num_ucio_violations",
    "num_cfgbvs_violations", "drc_error_flag",
    "num_clocks", "cdc_violations", "cdc_safe_flag",
    "congested_regions_count", "route_delay_ns", "routing_efficiency_score",
    "logic_depth", "pipeline_stages", "fanout_max", "fanout_avg",
    "register_to_logic_ratio",
    "approx_mode_percent", "hybrid_mode_percent", "exact_mode_percent",
    "avg_error_percent", "max_error_percent",
    "power_saving_percent", "power_efficiency_score", "performance_score",
    "area_efficiency_score", "timing_risk_score", "power_risk_score",
    "fix_pipeline", "fix_constraints", "use_dsp",
    "optimize_routing", "reduce_logic_depth", "add_buffering",
]

# Simplified feature cols for parsed log data (subset of above)
PARSED_FEATURE_COLS = [
    "total_power_w", "dynamic_power_w", "static_power_w",
    "lut_util_percent", "ff_util_percent", "bram_util_percent", "dsp_util_percent",
    "worst_negative_slack_ns", "timing_met_flag", "target_frequency_mhz",
    "critical_path_delay_ns", "total_drc_violations", "drc_error_flag",
    "congested_regions_count", "routing_efficiency_score",
]


def _get_feature_cols() -> list:
    global _feature_cols
    if _feature_cols:
        return _feature_cols
    if os.path.exists(FEATURE_COLS_PATH):
        with open(FEATURE_COLS_PATH) as f:
            _feature_cols = json.load(f)
        return _feature_cols
    _feature_cols = HARDCODED_FEATURE_COLS
    return _feature_cols


def load_models():
    """Load all persisted models into cache."""
    global _models
    paths = {
        "status":    STATUS_MODEL_PATH,
        "health":    HEALTH_MODEL_PATH,
        "bitstream": BITSTREAM_MODEL_PATH,
        "power":     POWER_MODEL_PATH,
        "slack":     SLACK_MODEL_PATH,
        "encoder":   ENCODER_PATH,
        "scaler":    SCALER_PATH,
    }
    for key, path in paths.items():
        if os.path.exists(path):
            try:
                _models[key] = joblib.load(path)
                logger.info(f"Loaded model: {key}")
            except Exception as e:
                logger.warning(f"Failed to load {key}: {e}")
    _get_feature_cols()
    logger.info(f"Models loaded: {list(_models.keys())}")


def models_ready() -> bool:
    return "status" in _models and "health" in _models


# ─── Dataset helpers ──────────────────────────────────────────────────────────

def _ensure_dataset_header(path: str, cols: list):
    if not os.path.exists(path):
        with open(path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "design_name"] + cols +
                            ["health_score", "design_status", "bitstream_ready"])


def append_to_dataset(features: Dict[str, Any], design_name: str):
    """Append parsed features to masterdataset CSV and trigger retrain if threshold hit."""
    global _upload_count
    path = DATASET_PATH
    cols = list(features.keys())
    _ensure_dataset_header(path, cols)

    health = _rule_health(features)
    status = _rule_status(features, health)
    bitstream = int(_rule_bitstream(features) >= 70)

    row = (
        [datetime.utcnow().isoformat(), design_name]
        + [features.get(c, 0.0) for c in cols]
        + [health, status, bitstream]
    )
    with open(path, "a", newline="") as f:
        csv.writer(f).writerow(row)

    _upload_count += 1
    logger.info(f"Dataset row added (#{_upload_count}): {design_name}")

    # Continuous learning trigger
    if _upload_count % RETRAIN_INTERVAL == 0:
        threading.Thread(target=_incremental_retrain, daemon=True).start()


def dataset_row_count() -> int:
    if not os.path.exists(DATASET_PATH):
        return 0
    with open(DATASET_PATH) as f:
        return max(0, sum(1 for _ in f) - 1)


# ─── Rule-based scoring (used as labels for new data) ────────────────────────

def _rule_health(features: Dict) -> float:
    score = 100.0
    wns = features.get("worst_negative_slack_ns", 0)
    if wns < 0:
        score -= min(35, abs(wns) * 20)
    errors = features.get("drc_error_flag", 0) or features.get("drc_errors", 0)
    warnings = features.get("total_drc_violations", 0) - errors
    score -= min(15, errors * 5)
    score -= min(5, warnings * 1)
    for key in ["lut_util_percent", "ff_util_percent", "bram_util_percent"]:
        pct = features.get(key, 0)
        if pct > 80:
            score -= min(7, (pct - 80) * 0.35)
    power = features.get("total_power_w", 0)
    if power > 10:
        score -= 10
    elif power > 5:
        score -= 5
    cong = features.get("congested_regions_count", 0)
    if cong > 5:
        score -= 10
    elif cong > 2:
        score -= 5
    return round(max(0.0, min(100.0, score)), 1)


def _rule_status(features: Dict, health: float) -> str:
    if features.get("drc_error_flag", 0) > 0:
        return "CRITICAL"
    if features.get("timing_met_flag", 0) == 0:
        return "CRITICAL" if health < 40 else "NEEDS_OPTIMIZATION"
    if health >= 80:
        return "OPTIMIZED"
    if health >= 60:
        return "GOOD"
    return "NEEDS_OPTIMIZATION"


def _rule_bitstream(features: Dict) -> float:
    ready = 100.0
    if features.get("drc_error_flag", 0) > 0:
        ready -= 40
    if features.get("timing_met_flag", 0) == 0:
        ready -= 20
    violations = features.get("total_drc_violations", 0)
    ready -= min(10, violations * 2)
    return round(max(0.0, min(100.0, ready)), 1)


# ─── Inference ────────────────────────────────────────────────────────────────

def _build_feature_vector(features: Dict, feature_cols: list) -> np.ndarray:
    """Align parsed features to the training feature vector."""
    # Map common aliases
    ALIASES = {
        "lut_util_percent":  ["lut_util_pct", "lut_util_percent"],
        "ff_util_percent":   ["ff_util_pct",  "ff_util_percent"],
        "bram_util_percent": ["bram_util_pct","bram_util_percent"],
        "dsp_util_percent":  ["dsp_util_pct", "dsp_util_percent"],
        "target_frequency_mhz": ["target_freq_mhz", "target_frequency_mhz"],
    }
    expanded = dict(features)
    for canonical, aliases in ALIASES.items():
        for alias in aliases:
            if alias in expanded and canonical not in expanded:
                expanded[canonical] = expanded[alias]

    vec = []
    for col in feature_cols:
        val = expanded.get(col, 0.0)
        try:
            vec.append(float(val))
        except (TypeError, ValueError):
            vec.append(0.0)
    return np.array(vec, dtype=float)


def predict(features: Dict[str, Any]) -> Dict[str, Any]:
    """Run full ML inference. Falls back to rule-based if models not loaded."""
    health_rb   = _rule_health(features)
    status_rb   = _rule_status(features, health_rb)
    bitstream_rb = _rule_bitstream(features)

    if not models_ready():
        logger.info("Models not ready — rule-based prediction")
        return {
            "design_status": status_rb,
            "health_score": health_rb,
            "bitstream_readiness": bitstream_rb,
            "confidence": 0.72,
            "model_used": "rule_based",
        }

    try:
        feature_cols = _get_feature_cols()
        X = _build_feature_vector(features, feature_cols).reshape(1, -1)

        # ── Design status ────────────────────────────────────────────────────
        status_bundle = _models["status"]
        encoder = _models.get("encoder") or status_bundle.get("encoder")

        proba_xgb = status_bundle["xgb"].predict_proba(X)[0]
        proba_rf  = status_bundle["rf"].predict_proba(X)[0]
        proba_ens = (proba_xgb + proba_rf) / 2
        status_idx = int(np.argmax(proba_ens))
        status_pred = encoder.classes_[status_idx]
        confidence = round(float(proba_ens[status_idx]), 3)

        # ── Health score ──────────────────────────────────────────────────────
        health_bundle = _models["health"]
        scaler        = health_bundle.get("scaler") or _models.get("scaler")
        health_xgb    = float(health_bundle["xgb"].predict(X)[0])
        if scaler and "mlp" in health_bundle:
            X_sc = scaler.transform(X)
            health_mlp = float(health_bundle["mlp"].predict(X_sc)[0])
            health_pred = np.clip(health_xgb * 0.65 + health_mlp * 0.35, 0, 100)
        else:
            health_pred = np.clip(health_xgb, 0, 100)
        health_pred = round(float(health_pred), 1)

        # ── Bitstream readiness ───────────────────────────────────────────────
        if "bitstream" in _models:
            bs_proba = _models["bitstream"].predict_proba(X)[0][1]
            bitstream_pred = round(float(bs_proba) * 100, 1)
        else:
            bitstream_pred = bitstream_rb

        # ── Power & Slack predictions ─────────────────────────────────────────
        pred_power = None
        pred_slack = None
        if "power" in _models:
            pred_power = round(float(_models["power"].predict(X)[0]), 3)
        if "slack" in _models:
            pred_slack = round(float(_models["slack"].predict(X)[0]), 3)

        return {
            "design_status":       status_pred,
            "health_score":        health_pred,
            "bitstream_readiness": bitstream_pred,
            "confidence":          confidence,
            "model_used":          "xgb_mlp_ensemble",
            "predicted_power_w":   pred_power,
            "predicted_slack_ns":  pred_slack,
            "class_probabilities": {
                cls: round(float(p), 3)
                for cls, p in zip(encoder.classes_, proba_ens)
            },
        }

    except Exception as e:
        logger.exception(f"ML inference failed: {e}")
        return {
            "design_status": status_rb,
            "health_score": health_rb,
            "bitstream_readiness": bitstream_rb,
            "confidence": 0.70,
            "model_used": "rule_based_fallback",
        }


# ─── What-if simulation using trained regression models ───────────────────────

def predict_whatif(
    base_features: Dict[str, Any],
    clock_mhz: Optional[float] = None,
    pipeline_stages: Optional[int] = None,
    mode: str = "balanced",
) -> Dict[str, Any]:
    feat = dict(base_features)
    target = clock_mhz or feat.get("target_frequency_mhz") or feat.get("target_freq_mhz", 300)
    pipe   = pipeline_stages or int(feat.get("pipeline_stages", 2))
    mode_factor = {"perf": 1.15, "balanced": 1.0, "power": 0.85}.get(mode, 1.0)

    # Update simulation features
    feat["target_frequency_mhz"] = target
    feat["pipeline_stages"] = pipe
    feat["clock_constraint_ns"] = round(1000 / target, 3) if target > 0 else 3.33

    # Use ML slack model if available
    if "slack" in _models and models_ready():
        try:
            feature_cols = _get_feature_cols()
            X = _build_feature_vector(feat, feature_cols).reshape(1, -1)
            predicted_slack = round(float(_models["slack"].predict(X)[0]), 3)
            predicted_power = None
            if "power" in _models:
                predicted_power = round(float(_models["power"].predict(X)[0]) * mode_factor, 3)
        except Exception as e:
            logger.warning(f"What-if ML failed: {e}")
            predicted_slack = None
            predicted_power = None
    else:
        predicted_slack = None
        predicted_power = None

    # Analytic fallback / enhancement
    base_slack = float(feat.get("worst_negative_slack_ns", -0.5))
    slack_delta = (pipe - 1) * 0.18 * mode_factor
    predicted_slack = predicted_slack if predicted_slack is not None else round(base_slack + slack_delta, 3)

    base_power  = float(feat.get("total_power_w", 4.82))
    base_target = float(feat.get("target_frequency_mhz", 300)) or 300
    predicted_power = predicted_power if predicted_power is not None else round(
        base_power * (target / base_target) * mode_factor, 3
    )

    base_freq = float(feat.get("achieved_freq_mhz", 268) or 268)
    projected_fmax = round(base_freq * (1 + (pipe - 1) * 0.08) * (1.05 if mode == "perf" else 1.0))
    lut_delta = round((pipe - 1) * 4.5)

    return {
        "predicted_slack_ns":   predicted_slack,
        "predicted_power_w":    predicted_power,
        "projected_fmax_mhz":   projected_fmax,
        "lut_delta_pct":        lut_delta,
        "timing_status":        "PASS" if predicted_slack >= 0 else "FAIL",
    }


# ─── Incremental retraining ───────────────────────────────────────────────────

def _incremental_retrain():
    """Background re-train from the growing uploaded dataset."""
    with _retrain_lock:
        logger.info("Incremental retrain started …")
        try:
            if not os.path.exists(DATASET_PATH):
                return
            df = pd.read_csv(DATASET_PATH)
            if len(df) < MIN_ROWS_TO_TRAIN:
                return

            # Pull numeric feature cols
            DROP_TARGETS = {"health_score", "design_status", "bitstream_ready", "timestamp", "design_name"}
            feat_cols = [c for c in df.select_dtypes(include=np.number).columns if c not in DROP_TARGETS]
            X = df[feat_cols].fillna(0).values.astype(float)
            y_status = df["design_status"].values
            y_health = df["health_score"].values.astype(float)
            y_bs     = df["bitstream_ready"].values.astype(int)

            X_tr, X_te, ys_tr, ys_te, yh_tr, yh_te, yb_tr, yb_te = train_test_split(
                X, y_status, y_health, y_bs, test_size=0.2, random_state=42
            )

            enc = LabelEncoder()
            enc.fit(np.unique(y_status))

            # Fast retrain (fewer trees for speed)
            xgb_s = XGBClassifier(n_estimators=100, max_depth=6, n_jobs=-1,
                                   use_label_encoder=False, eval_metric="mlogloss",
                                   random_state=42)
            xgb_s.fit(X_tr, enc.transform(ys_tr))
            rf_s  = RandomForestClassifier(n_estimators=100, n_jobs=-1, random_state=42)
            rf_s.fit(X_tr, enc.transform(ys_tr))
            joblib.dump({"xgb": xgb_s, "rf": rf_s, "encoder": enc}, STATUS_MODEL_PATH)

            xgb_h = XGBRegressor(n_estimators=200, max_depth=5, n_jobs=-1, random_state=42)
            xgb_h.fit(X_tr, yh_tr)
            sc = StandardScaler()
            sc.fit(X_tr)
            mlp_h = MLPRegressor(hidden_layer_sizes=(128, 64), max_iter=100, random_state=42)
            mlp_h.fit(sc.transform(X_tr), yh_tr)
            joblib.dump({"xgb": xgb_h, "mlp": mlp_h, "scaler": sc}, HEALTH_MODEL_PATH)

            # Reload into cache
            _models["status"]  = joblib.load(STATUS_MODEL_PATH)
            _models["health"]  = joblib.load(HEALTH_MODEL_PATH)
            _models["encoder"] = enc
            _feature_cols.clear()
            _feature_cols.extend(feat_cols)
            with open(FEATURE_COLS_PATH, "w") as fp:
                json.dump(feat_cols, fp)

            logger.info(f"Incremental retrain complete — {len(df)} rows")
        except Exception as e:
            logger.exception(f"Incremental retrain failed: {e}")


def train_models() -> bool:
    """Manual full retrain trigger."""
    try:
        _incremental_retrain()
        return True
    except Exception:
        return False
