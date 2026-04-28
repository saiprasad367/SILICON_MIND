"""
dbservice.py - Database layer using SQLite (local) + Supabase (cloud sync).
Stores design analyses, predictions, and best strategies.
"""
import sqlite3
import json
import logging
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DB_PATH, SUPABASE_URL, SUPABASE_KEY

logger = logging.getLogger(__name__)

# Optional Supabase client
_supabase = None
if SUPABASE_URL and SUPABASE_KEY:
    try:
        from supabase import create_client
        _supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        logger.info("Supabase client initialized.")
    except ImportError:
        logger.warning("supabase-py not installed — using SQLite only.")
    except Exception as e:
        logger.warning(f"Supabase init failed: {e}")


# ─── SQLite schema ────────────────────────────────────────────────────────────

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS fpga_analyses (
    id                      INTEGER PRIMARY KEY AUTOINCREMENT,
    design_name             TEXT    NOT NULL,
    timestamp               TEXT    NOT NULL,
    total_power_w           REAL,
    dynamic_power_w         REAL,
    static_power_w          REAL,
    lut_util_pct            REAL,
    ff_util_pct             REAL,
    bram_util_pct           REAL,
    dsp_util_pct            REAL,
    worst_negative_slack_ns REAL,
    timing_met_flag         INTEGER,
    target_freq_mhz         REAL,
    achieved_freq_mhz       REAL,
    total_drc_violations    INTEGER,
    drc_errors              INTEGER,
    congestion_overall      REAL,
    design_status           TEXT,
    health_score            REAL,
    bitstream_readiness     REAL,
    ai_insights             TEXT,    -- JSON blob
    best_strategy           TEXT,
    confidence              REAL,
    model_used              TEXT
);
"""


def _get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize SQLite database."""
    conn = _get_conn()
    conn.execute(CREATE_TABLE)
    conn.commit()
    conn.close()
    logger.info("SQLite DB initialized.")


# ─── Write ────────────────────────────────────────────────────────────────────

def save_analysis(
    design_name: str,
    features: Dict[str, Any],
    ml_result: Dict[str, Any],
    ai_result: Dict[str, Any],
) -> int:
    """Insert a complete analysis record. Returns the new row ID."""
    ts = datetime.utcnow().isoformat()
    row = {
        "design_name":             design_name,
        "timestamp":               ts,
        "total_power_w":           features.get("total_power_w"),
        "dynamic_power_w":         features.get("dynamic_power_w"),
        "static_power_w":          features.get("static_power_w"),
        "lut_util_pct":            features.get("lut_util_pct"),
        "ff_util_pct":             features.get("ff_util_pct"),
        "bram_util_pct":           features.get("bram_util_pct"),
        "dsp_util_pct":            features.get("dsp_util_pct"),
        "worst_negative_slack_ns": features.get("worst_negative_slack_ns"),
        "timing_met_flag":         features.get("timing_met_flag"),
        "target_freq_mhz":         features.get("target_freq_mhz"),
        "achieved_freq_mhz":       features.get("achieved_freq_mhz"),
        "total_drc_violations":    features.get("total_drc_violations"),
        "drc_errors":              features.get("drc_errors"),
        "congestion_overall":      features.get("congestion_overall"),
        "design_status":           ml_result.get("design_status"),
        "health_score":            ml_result.get("health_score"),
        "bitstream_readiness":     ml_result.get("bitstream_readiness"),
        "ai_insights":             json.dumps(ai_result.get("insights", [])),
        "best_strategy":           ai_result.get("best_strategy"),
        "confidence":              ml_result.get("confidence"),
        "model_used":              ml_result.get("model_used"),
    }

    # SQLite insert
    cols = ", ".join(row.keys())
    placeholders = ", ".join("?" * len(row))
    conn = _get_conn()
    cur = conn.execute(
        f"INSERT INTO fpga_analyses ({cols}) VALUES ({placeholders})",
        list(row.values()),
    )
    new_id = cur.lastrowid
    conn.commit()
    conn.close()
    logger.info(f"Analysis saved to SQLite: id={new_id}, design={design_name}")

    # Supabase sync (non-blocking, best-effort)
    if _supabase:
        try:
            _supabase.table("fpga_analyses").insert(row).execute()
            logger.info("Analysis synced to Supabase.")
        except Exception as e:
            logger.warning(f"Supabase sync failed: {e}")

    return new_id


# ─── Read ─────────────────────────────────────────────────────────────────────

def get_latest_analysis(design_name: Optional[str] = None) -> Optional[Dict]:
    """Fetch the most recent analysis record."""
    conn = _get_conn()
    if design_name:
        row = conn.execute(
            "SELECT * FROM fpga_analyses WHERE design_name=? ORDER BY id DESC LIMIT 1",
            (design_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT * FROM fpga_analyses ORDER BY id DESC LIMIT 1"
        ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_all_designs() -> List[Dict]:
    """Return summary of all analyzed designs."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, design_name, timestamp, health_score, design_status, bitstream_readiness "
        "FROM fpga_analyses ORDER BY id DESC LIMIT 50"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_analysis_by_id(analysis_id: int) -> Optional[Dict]:
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM fpga_analyses WHERE id=?", (analysis_id,)
    ).fetchone()
    conn.close()
    return dict(row) if row else None
