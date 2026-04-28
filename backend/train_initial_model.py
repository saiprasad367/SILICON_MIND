"""
train_initial_model.py
──────────────────────
One-shot script to train all ML models on the 200k FPGA dataset.
Run: python train_initial_model.py

Models trained:
  1. XGBoostClassifier   → design_status  (CRITICAL/NEEDS_OPTIMIZATION/GOOD/OPTIMIZED/BAD)
  2. XGBoostRegressor    → health_score   (0–100)
  3. XGBoostClassifier   → bitstream_ready (0/1)
  4. RandomForestRegressor → predicted_power_w
  5. RandomForestRegressor → predicted_slack_ns
  Neural Network (MLP) stacked as meta-learner for health_score

After training, models are saved to /models/ via joblib.
"""

import os
import sys
import json
import joblib
import warnings
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sklearn.ensemble import (
    RandomForestClassifier, RandomForestRegressor,
    GradientBoostingRegressor, VotingClassifier,
)
from sklearn.neural_network import MLPRegressor, MLPClassifier
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import (
    accuracy_score, classification_report, mean_absolute_error, r2_score
)
from xgboost import XGBClassifier, XGBRegressor

from config import (
    MODEL_FOLDER, STATUS_MODEL_PATH, HEALTH_MODEL_PATH, ENCODER_PATH,
)

# ─── Extra model paths ────────────────────────────────────────────────────────
BITSTREAM_MODEL_PATH   = os.path.join(MODEL_FOLDER, "bitstream_clf.pkl")
POWER_MODEL_PATH       = os.path.join(MODEL_FOLDER, "power_regressor.pkl")
SLACK_MODEL_PATH       = os.path.join(MODEL_FOLDER, "slack_regressor.pkl")
SCALER_PATH            = os.path.join(MODEL_FOLDER, "scaler.pkl")
FEATURE_COLS_PATH      = os.path.join(MODEL_FOLDER, "feature_cols.json")

# ─── Dataset ──────────────────────────────────────────────────────────────────
DATASET_PATH = os.path.join(os.path.dirname(__file__), "fpga_dataset_200k.csv")


def load_and_clean(path: str) -> pd.DataFrame:
    print(f"[1/6] Loading dataset: {path}")
    df = pd.read_csv(path)
    print(f"      Shape: {df.shape}")

    # Drop non-numeric / identifier columns
    DROP_COLS = [
        "design_name", "fpga_device", "tool_version", "run_id",
        "critical_path_start", "critical_path_end", "bottleneck_module",
        "clock_domains", "primary_issue", "routing_congestion_level",
    ]
    df.drop(columns=[c for c in DROP_COLS if c in df.columns], inplace=True)

    # Fix boolean-like columns
    for col in ["timing_met_flag", "drc_error_flag", "cdc_safe_flag",
                "bitstream_ready", "fix_pipeline", "fix_constraints",
                "use_dsp", "optimize_routing", "reduce_logic_depth", "add_buffering"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0).astype(int)

    # Fill numeric NaN with median
    num_cols = df.select_dtypes(include=np.number).columns
    df[num_cols] = df[num_cols].fillna(df[num_cols].median())

    # Drop rows with bad design_status
    if "design_status" in df.columns:
        df = df[df["design_status"].notna()]
        df["design_status"] = df["design_status"].str.strip().str.upper()

    # best_strategy → encode
    if "best_strategy" in df.columns:
        df["best_strategy"] = df["best_strategy"].fillna("SPEED_OPT")

    print(f"      Clean shape: {df.shape}")
    print(f"      Status distribution:\n{df['design_status'].value_counts().to_string()}")
    return df


def select_features(df: pd.DataFrame) -> list:
    """Return numeric columns that are NOT target variables."""
    TARGETS = {
        "health_score", "design_status", "bitstream_ready",
        "predicted_power_w", "predicted_slack_ns", "predicted_lut_usage",
        "best_strategy",
    }
    feature_cols = [
        c for c in df.select_dtypes(include=np.number).columns
        if c not in TARGETS
    ]
    print(f"[2/6] Features selected: {len(feature_cols)} columns")
    return feature_cols


def train_status_classifier(X_tr, y_tr, X_te, y_te, encoder):
    print("[3/6] Training design_status classifier (XGBoost + RF ensemble) …")
    y_tr_enc = encoder.transform(y_tr)
    y_te_enc = encoder.transform(y_te)
    n_classes = len(encoder.classes_)

    xgb = XGBClassifier(
        n_estimators=400, max_depth=8, learning_rate=0.05,
        subsample=0.8, colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric="mlogloss",
        n_jobs=-1, random_state=42,
        num_class=n_classes,
        objective="multi:softprob",
    )
    xgb.fit(X_tr, y_tr_enc, eval_set=[(X_te, y_te_enc)], verbose=False)

    rf = RandomForestClassifier(n_estimators=300, max_depth=15, n_jobs=-1, random_state=42)
    rf.fit(X_tr, y_tr_enc)

    # Soft-vote ensemble
    # predict_proba from both, average
    proba_xgb = xgb.predict_proba(X_te)
    proba_rf  = rf.predict_proba(X_te)
    proba_ens = (proba_xgb + proba_rf) / 2
    y_pred_ens = np.argmax(proba_ens, axis=1)

    acc = accuracy_score(y_te_enc, y_pred_ens)
    print(f"      Ensemble Accuracy: {acc:.4f}")
    print(classification_report(y_te_enc, y_pred_ens,
                                target_names=encoder.classes_, zero_division=0))

    # Save both for ensemble inference
    bundle = {"xgb": xgb, "rf": rf, "encoder": encoder}
    joblib.dump(bundle, STATUS_MODEL_PATH)
    print(f"      Saved -> {STATUS_MODEL_PATH}")
    return bundle


def train_health_regressor(X_tr, y_tr, X_te, y_te, scaler):
    print("[4/6] Training health_score regressor (XGBoost + MLP stacked) …")

    xgb = XGBRegressor(
        n_estimators=500, max_depth=7, learning_rate=0.04,
        subsample=0.8, colsample_bytree=0.8,
        n_jobs=-1, random_state=42,
    )
    xgb.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)

    # MLP on scaled features
    X_tr_sc = scaler.transform(X_tr)
    X_te_sc  = scaler.transform(X_te)
    mlp = MLPRegressor(
        hidden_layer_sizes=(256, 128, 64), activation="relu",
        max_iter=300, random_state=42, early_stopping=True,
        validation_fraction=0.1, n_iter_no_change=15,
    )
    mlp.fit(X_tr_sc, y_tr)

    # Stacking: simple average
    pred_xgb = xgb.predict(X_te)
    pred_mlp = mlp.predict(X_te_sc)
    pred_ens = (pred_xgb * 0.65 + pred_mlp * 0.35)  # XGB gets higher weight
    pred_ens = np.clip(pred_ens, 0, 100)

    mae = mean_absolute_error(y_te, pred_ens)
    r2  = r2_score(y_te, pred_ens)
    print(f"      Ensemble MAE: {mae:.3f} | R²: {r2:.4f}")

    bundle = {"xgb": xgb, "mlp": mlp, "scaler": scaler}
    joblib.dump(bundle, HEALTH_MODEL_PATH)
    print(f"      Saved -> {HEALTH_MODEL_PATH}")
    return bundle


def train_bitstream_classifier(X_tr, y_tr, X_te, y_te):
    print("[5/6] Training bitstream_ready classifier …")
    xgb = XGBClassifier(
        n_estimators=300, max_depth=6, learning_rate=0.05,
        subsample=0.8, n_jobs=-1, random_state=42,
        objective="binary:logistic", eval_metric="logloss",
    )
    xgb.fit(X_tr, y_tr, eval_set=[(X_te, y_te)], verbose=False)
    acc = accuracy_score(y_te, xgb.predict(X_te))
    print(f"      Accuracy: {acc:.4f}")
    joblib.dump(xgb, BITSTREAM_MODEL_PATH)
    print(f"      Saved -> {BITSTREAM_MODEL_PATH}")
    return xgb


def train_regression_models(X_tr, X_te, df_tr, df_te):
    print("[6/6] Training power & slack regression models …")

    # Power regressor
    if "total_power_w" in df_tr.columns:
        y_pow_tr = df_tr["total_power_w"].values
        y_pow_te = df_te["total_power_w"].values
        pow_model = XGBRegressor(n_estimators=300, max_depth=6, n_jobs=-1, random_state=42)
        pow_model.fit(X_tr, y_pow_tr, eval_set=[(X_te, y_pow_te)], verbose=False)
        mae = mean_absolute_error(y_pow_te, pow_model.predict(X_te))
        print(f"      Power MAE: {mae:.4f} W")
        joblib.dump(pow_model, POWER_MODEL_PATH)

    # Slack regressor
    if "worst_negative_slack_ns" in df_tr.columns:
        y_sl_tr = df_tr["worst_negative_slack_ns"].values
        y_sl_te = df_te["worst_negative_slack_ns"].values
        slack_model = XGBRegressor(n_estimators=300, max_depth=6, n_jobs=-1, random_state=42)
        slack_model.fit(X_tr, y_sl_tr, eval_set=[(X_te, y_sl_te)], verbose=False)
        mae = mean_absolute_error(y_sl_te, slack_model.predict(X_te))
        print(f"      Slack MAE: {mae:.4f} ns")
        joblib.dump(slack_model, SLACK_MODEL_PATH)


def main():
    os.makedirs(MODEL_FOLDER, exist_ok=True)

    # ── Load & clean ──────────────────────────────────────────────────────────
    df = load_and_clean(DATASET_PATH)
    feature_cols = select_features(df)

    # Save feature cols list for inference
    with open(FEATURE_COLS_PATH, "w") as f:
        json.dump(feature_cols, f)

    X = df[feature_cols].values.astype(float)
    y_status    = df["design_status"].values
    y_health    = df["health_score"].values.astype(float)
    y_bitstream = df["bitstream_ready"].values.astype(int)

    X_tr, X_te, ys_tr, ys_te, yh_tr, yh_te, yb_tr, yb_te, df_tr, df_te = train_test_split(
        X, y_status, y_health, y_bitstream, df,
        test_size=0.15, random_state=42, stratify=y_status,
    )
    print(f"      Train: {X_tr.shape[0]} | Test: {X_te.shape[0]}")

    # ── Scaler (for MLP) ─────────────────────────────────────────────────────
    scaler = StandardScaler()
    scaler.fit(X_tr)
    joblib.dump(scaler, SCALER_PATH)

    # ── Encoder ───────────────────────────────────────────────────────────────
    encoder = LabelEncoder()
    encoder.fit(np.unique(y_status))
    joblib.dump(encoder, ENCODER_PATH)
    print(f"      Classes: {encoder.classes_.tolist()}")

    # ── Train all models ──────────────────────────────────────────────────────
    train_status_classifier(X_tr, ys_tr, X_te, ys_te, encoder)
    train_health_regressor(X_tr, yh_tr, X_te, yh_te, scaler)
    train_bitstream_classifier(X_tr, yb_tr, X_te, yb_te)
    train_regression_models(X_tr, X_te, df_tr.reset_index(drop=True), df_te.reset_index(drop=True))

    print("\n✅ All models trained and saved successfully!")
    print(f"   Models folder: {MODEL_FOLDER}")
    print(f"   Feature count: {len(feature_cols)}")


if __name__ == "__main__":
    main()
