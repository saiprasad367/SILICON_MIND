"""
parserservice.py - Vivado report parser.
Extracts features using the EXACT column names from fpga_dataset_200k.csv
so ML models trained on that dataset receive correctly-named features.
"""
import re
import os
import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _find(upload_dir: str, keywords: List[str]) -> str:
    for fname in os.listdir(upload_dir):
        fl = fname.lower()
        if any(kw in fl for kw in keywords):
            return os.path.join(upload_dir, fname)
    return ""


# ─── Power parser ─────────────────────────────────────────────────────────────

def parse_power(text: str) -> Dict[str, Any]:
    def _num(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return float(m.group(1)) if m else None

    total   = _num(r"Total On-Chip Power.*?(\d+\.\d+)")
    dynamic = _num(r"Dynamic.*?(\d+\.\d+)\s*W")
    static  = _num(r"(?:Device Static|Static).*?(\d+\.\d+)\s*W")
    logic   = _num(r"Logic.*?(\d+\.\d+)\s*W")
    signal  = _num(r"Signals?.*?(\d+\.\d+)\s*W")
    io      = _num(r"\bI/O\b.*?(\d+\.\d+)\s*W")
    clock_p = _num(r"Clocks?.*?(\d+\.\d+)\s*W")

    # Build breakdown for charting
    COLORS = {
        "Clocks":  "hsl(239 84% 67%)",
        "Signals": "hsl(258 90% 66%)",
        "Logic":   "hsl(217 91% 60%)",
        "BRAM":    "hsl(160 84% 39%)",
        "DSP":     "hsl(38 92% 50%)",
        "I/O":     "hsl(12 90% 60%)",
    }
    breakdown = []
    for label, color in COLORS.items():
        m = re.search(rf"{label}.*?(\d+\.\d+)\s*W", text, re.IGNORECASE)
        if m:
            breakdown.append({"name": label, "value": float(m.group(1)), "color": color})

    # Module hierarchy
    modules = []
    for m2 in re.finditer(r"\|\s*([\w/]+)\s*\|\s*(\d+\.\d+)\s*\|", text):
        name, pwr = m2.group(1), float(m2.group(2))
        if pwr > 0.01 and len(modules) < 6:
            modules.append({"name": name, "power": pwr})

    return {
        "total_power_w":   total,
        "dynamic_power_w": dynamic,
        "static_power_w":  static,
        "logic_power_w":   logic,
        "signal_power_w":  signal,
        "io_power_w":      io,
        "clock_power_w":   clock_p,
        "breakdown":       breakdown,
        "modules":         modules,
    }


# ─── Timing parser ────────────────────────────────────────────────────────────

def parse_timing(text: str) -> Dict[str, Any]:
    def _num(pattern):
        m = re.search(pattern, text, re.IGNORECASE)
        return float(m.group(1)) if m else None

    wns        = _num(r"Slack\s*[:\(].*?(-?\d+\.\d+)\s*ns")
    tns        = _num(r"Total Negative Slack.*?(-?\d+\.\d+)")
    hold_slack = _num(r"Worst Hold Slack.*?(-?\d+\.\d+)")
    data_delay = _num(r"Data Path Delay:\s*(\d+\.\d+)")
    logic_del  = _num(r"Logic Levels?.*?(\d+\.\d+)")
    route_del  = _num(r"Net Delay.*?(\d+\.\d+)")

    # Target freq from clock period
    period_ns = _num(r"Clock Period\s*:\s*(\d+\.\d+)") or _num(r"Requirement\s*:\s*(\d+\.\d+)")
    target_freq = round(1000 / period_ns) if period_ns and period_ns > 0 else 300

    timing_met = 1 if (wns is not None and wns >= 0) else 0
    achieved   = round(1000 / (period_ns - wns)) if (period_ns and wns is not None and (period_ns - wns) > 0) else None

    # Path stages (first 5 path elements)
    stages = []
    for m2 in re.finditer(r"([\w/]+)\s+(\w+)\s+(\d+\.\d+)\s+(\d+\.\d+)", text):
        stages.append({"name": m2.group(1), "type": m2.group(2), "delay": float(m2.group(4))})
        if len(stages) >= 5:
            break

    violations = 0
    m = re.search(r"(\d+)\s+(?:timing\s+)?violation", text, re.IGNORECASE)
    if m:
        violations = int(m.group(1))

    logic_pct = round((logic_del / data_delay * 100) if (logic_del and data_delay) else 40, 1)
    route_pct = round(100 - logic_pct, 1)

    return {
        "slack":       wns,
        "status":      "PASS" if timing_met else "FAIL",
        "target_freq": target_freq,
        "achieved_freq": achieved or target_freq,
        "timing_met_flag": timing_met,
        "worst_negative_slack_ns": wns or 0,
        "total_negative_slack_ns": tns or 0,
        "worst_hold_slack_ns":     hold_slack or 0,
        "critical_path_delay_ns":  data_delay or 0,
        "logic_delay_ns":          logic_del or 0,
        "routing_delay_ns":        route_del or 0,
        "logic_delay_percent":     logic_pct,
        "routing_delay_percent":   route_pct,
        "num_timing_violations":   violations,
        "critical_path": {
            "delay":        data_delay or 0,
            "logicDelay":   logic_del or 0,
            "routingDelay": route_del or 0,
            "stages":       stages,
        },
    }


# ─── Utilization parser ───────────────────────────────────────────────────────

def parse_utilization(text: str) -> Dict[str, Any]:
    RESOURCES = [
        ("LUT",  "lut",  r"LUT as Logic\s*\|\s*(\d+)\s*\|\s*(\d+)"),
        ("FF",   "ff",   r"Register as Flip Flop\s*\|\s*(\d+)\s*\|\s*(\d+)"),
        ("DSP",  "dsp",  r"DSPs\s*\|\s*(\d+)\s*\|\s*(\d+)"),
        ("BRAM", "bram", r"Block RAM Tile\s*\|\s*(\d+)\s*\|\s*(\d+)"),
        ("URAM", "uram", r"URAM\s*\|\s*(\d+)\s*\|\s*(\d+)"),
        ("IO",   "io",   r"Bonded IOB\s*\|\s*(\d+)\s*\|\s*(\d+)"),
    ]
    util_list = []
    flat = {}
    for name, key, pattern in RESOURCES:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            used, total = int(m.group(1)), int(m.group(2))
            pct = round(used / total * 100, 2) if total > 0 else 0
            util_list.append({"name": name, "used": used, "total": total, "pct": pct})
            flat[f"{key}_used"]         = used
            flat[f"{key}_total"]        = total
            flat[f"{key}_util_percent"] = pct

    # Logic depth & pipeline stages
    depth = 0
    m = re.search(r"Logic Levels\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        depth = int(m.group(1))
    pipe = 0
    m = re.search(r"Pipeline Stages?\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        pipe = int(m.group(1))

    # Fanout
    fanout_max = 0
    m = re.search(r"Max Fanout\s*[:=]\s*(\d+)", text, re.IGNORECASE)
    if m:
        fanout_max = int(m.group(1))

    flat.update({"logic_depth": depth, "pipeline_stages": pipe, "fanout_max": fanout_max, "fanout_avg": 0})

    # Congestion
    congestion = _parse_congestion(text)
    flat.update(congestion["flat"])

    return {
        "resources":  util_list,
        "congestion": congestion,
        "flat":       flat,
    }


def _parse_congestion(text: str) -> Dict:
    overall  = 0
    hotspots = []
    m = re.search(r"Congestion.*?(\d+)%", text, re.IGNORECASE)
    if m:
        overall = int(m.group(1))
    congested_count = 0
    for m2 in re.finditer(r"(X\d+Y\d+).*?(\d+)%", text):
        level = int(m2.group(2))
        hotspots.append({"region": m2.group(1), "level": level})
        if level > 50:
            congested_count += 1
    return {
        "overall":  overall,
        "hotspots": hotspots,
        "flat": {
            "congested_regions_count":  congested_count,
            "routing_efficiency_score": round(max(0, 1 - overall / 100), 3),
            "route_delay_ns":           0,
        },
    }


# ─── DRC parser ───────────────────────────────────────────────────────────────

def parse_drc(text: str) -> Dict[str, Any]:
    violations = []
    SEV_MAP = {"ERROR": "error", "WARNING": "warning", "INFO": "info", "ADVISORY": "info"}
    FIX_MAP = {
        "TIMING": "Add set_input_delay / set_output_delay constraints",
        "PLCK":   "Insert BUFG / BUFGCE primitive",
        "RTSTAT": "Apply pblock constraints to congested region",
        "REQP":   "Re-place via LOC constraint",
        "PDRC":   "Check I/O standard and voltage settings",
    }

    for m in re.finditer(r"(ERROR|WARNING|INFO|ADVISORY)\s*\[([^\]]+)\]\s*([^\n]+)", text, re.IGNORECASE):
        sev_raw, rule, msg = m.group(1).upper(), m.group(2).strip(), m.group(3).strip()
        sev    = SEV_MAP.get(sev_raw, "info")
        prefix = rule.split("-")[0].upper()
        fix    = FIX_MAP.get(prefix, "Review Vivado DRC report")
        violations.append({
            "id":       f"DRC-{len(violations)+1:03d}",
            "severity": sev,
            "rule":     rule,
            "message":  msg[:120],
            "fix":      fix,
        })

    errors   = sum(1 for v in violations if v["severity"] == "error")
    nstd     = sum(1 for v in violations if "NSTD" in v["rule"])
    ucio     = sum(1 for v in violations if "UCIO" in v["rule"])
    cfgbvs   = sum(1 for v in violations if "CFGBVS" in v["rule"])

    return {
        "violations":          violations,
        "total_drc_violations": len(violations),
        "drc_error_flag":      1 if errors > 0 else 0,
        "num_nstd_violations": nstd,
        "num_ucio_violations": ucio,
        "num_cfgbvs_violations": cfgbvs,
    }


# ─── Clock domain parser ──────────────────────────────────────────────────────

def parse_clocks(text: str) -> Dict[str, Any]:
    clocks = []
    for m in re.finditer(r"([\w_]+)\s+\|\s+(\d+\.?\d*)\s+\|", text):
        name, freq = m.group(1), float(m.group(2))
        if 1 < freq < 5000:
            clocks.append({"name": name, "freq": freq, "domain": "PL", "status": "active"})
    num_clocks = len(clocks) or 1
    cdc = 0
    m = re.search(r"(\d+)\s*CDC", text, re.IGNORECASE)
    if m:
        cdc = int(m.group(1))
    return {"clocks": clocks[:6], "num_clocks": num_clocks, "cdc_violations": cdc, "cdc_safe_flag": 1 if cdc == 0 else 0}


# ─── Master parser ────────────────────────────────────────────────────────────

def parse_all(upload_dir: str) -> Dict[str, Any]:
    """Parse all available report files → merged feature dict."""
    power_path = _find(upload_dir, ["power"])
    timing_path = _find(upload_dir, ["timing", "timing_paths"])
    util_path   = _find(upload_dir, ["util", "utilization", "hierarchical"])
    drc_path    = _find(upload_dir, ["drc"])
    clock_path  = _find(upload_dir, ["clock", "timing"])

    # Extract design name from any available text
    design_name = None
    all_texts = [_read(p) for p in [power_path, timing_path, util_path] if p]
    for text in all_texts:
        m = re.search(r"Design Name\s*:\s*([\w\-\.]+)", text, re.IGNORECASE)
        if m:
            design_name = m.group(1)
            break

    # Parse reports
    power_data  = parse_power(all_texts[0] if power_path else "")
    timing_data = parse_timing(all_texts[1] if timing_path else "")
    util_data   = parse_utilization(all_texts[2] if util_path else "")
    drc_data    = parse_drc(_read(drc_path))
    clock_data  = parse_clocks(_read(clock_path or timing_path))

    # Flat feature dict (matches 200k dataset column names)
    features: Dict[str, Any] = {}

    # Power
    features["total_power_w"]   = power_data["total_power_w"] or 4.82
    features["dynamic_power_w"] = power_data["dynamic_power_w"] or 3.96
    features["static_power_w"]  = power_data["static_power_w"] or 0.86
    features["logic_power_w"]   = power_data["logic_power_w"] or 0
    features["signal_power_w"]  = power_data["signal_power_w"] or 0
    features["io_power_w"]      = power_data["io_power_w"] or 0
    features["clock_power_w"]   = power_data["clock_power_w"] or 0
    total = features["total_power_w"]
    features["dynamic_power_percent"] = round(features["dynamic_power_w"] / total * 100, 1) if total > 0 else 0
    features["static_power_percent"]  = round(features["static_power_w"] / total * 100, 1) if total > 0 else 0

    # Timing
    features["worst_negative_slack_ns"] = timing_data["worst_negative_slack_ns"]
    features["total_negative_slack_ns"] = timing_data["total_negative_slack_ns"]
    features["worst_hold_slack_ns"]     = timing_data["worst_hold_slack_ns"]
    features["critical_path_delay_ns"]  = timing_data["critical_path_delay_ns"]
    features["logic_delay_ns"]          = timing_data["logic_delay_ns"]
    features["routing_delay_ns"]        = timing_data["routing_delay_ns"]
    features["timing_met_flag"]         = timing_data["timing_met_flag"]
    features["num_timing_violations"]   = timing_data["num_timing_violations"]
    features["logic_delay_percent"]     = timing_data["logic_delay_percent"]
    features["routing_delay_percent"]   = timing_data["routing_delay_percent"]
    features["target_frequency_mhz"]   = float(timing_data["target_freq"])
    features["clock_constraint_ns"]    = round(1000 / timing_data["target_freq"], 3) if timing_data["target_freq"] > 0 else 3.33
    features["achieved_freq_mhz"]      = float(timing_data.get("achieved_freq", timing_data["target_freq"]))
    features["max_gate_delay_ns"]      = 0
    features["critical_path_logic_levels"] = 0

    # Utilization
    flat_util = util_data.get("flat", {})
    for key in ["lut_used", "lut_total", "lut_util_percent",
                "ff_used",  "ff_total",  "ff_util_percent",
                "dsp_used", "dsp_total", "dsp_util_percent",
                "bram_used","bram_total","bram_util_percent"]:
        features[key] = flat_util.get(key, 0)
    features["logic_depth"]       = flat_util.get("logic_depth", 0)
    features["pipeline_stages"]   = flat_util.get("pipeline_stages", 0)
    features["fanout_max"]        = flat_util.get("fanout_max", 0)
    features["fanout_avg"]        = flat_util.get("fanout_avg", 0)
    features["register_to_logic_ratio"] = (
        features["ff_used"] / features["lut_used"]
        if features["lut_used"] > 0 else 0
    )

    # Congestion
    cong_flat = util_data.get("congestion", {}).get("flat", {})
    features["congested_regions_count"]  = cong_flat.get("congested_regions_count", 0)
    features["routing_efficiency_score"] = cong_flat.get("routing_efficiency_score", 0.9)
    features["route_delay_ns"]           = cong_flat.get("route_delay_ns", 0)

    # DRC
    features["total_drc_violations"]  = drc_data["total_drc_violations"]
    features["drc_error_flag"]        = drc_data["drc_error_flag"]
    features["num_nstd_violations"]   = drc_data["num_nstd_violations"]
    features["num_ucio_violations"]   = drc_data["num_ucio_violations"]
    features["num_cfgbvs_violations"] = drc_data["num_cfgbvs_violations"]

    # Clocks / CDC
    features["num_clocks"]      = clock_data["num_clocks"]
    features["cdc_violations"]  = clock_data["cdc_violations"]
    features["cdc_safe_flag"]   = clock_data["cdc_safe_flag"]

    # Derived scores (rule-based)
    features["timing_risk_score"] = round(min(100, max(0, abs(features["worst_negative_slack_ns"]) * 20)), 1)
    features["power_risk_score"]  = round(min(100, features["total_power_w"] * 8), 1)
    features["approx_mode_percent"] = 0
    features["hybrid_mode_percent"] = 50
    features["exact_mode_percent"]  = 50
    features["avg_error_percent"]   = 0
    features["max_error_percent"]   = 0
    features["power_saving_percent"] = 0
    features["power_efficiency_score"] = round(min(100, 100 / (features["total_power_w"] + 0.1)), 1)
    features["performance_score"]    = 100 if features["timing_met_flag"] else max(0, 100 + features["worst_negative_slack_ns"] * 20)
    features["area_efficiency_score"] = round(max(0, 100 - features.get("lut_util_percent", 0)), 1)
    features["fix_pipeline"]   = 1 if features["worst_negative_slack_ns"] < 0 else 0
    features["fix_constraints"] = 1 if features["total_drc_violations"] > 0 else 0
    features["use_dsp"]        = 1 if features.get("dsp_util_percent", 0) < 10 and features.get("lut_util_percent", 0) > 15 else 0
    features["optimize_routing"] = 1 if features["congested_regions_count"] > 3 else 0
    features["reduce_logic_depth"] = 1 if features["logic_depth"] > 20 else 0
    features["add_buffering"]   = 1 if features["fanout_max"] > 3000 else 0

    # design_name is already set or None

    return {
        "design_name": design_name,
        "power":  {
            **power_data,
            "breakdown": power_data["breakdown"],
            "modules":   power_data["modules"],
        },
        "timing":       timing_data,
        "utilization":  util_data["resources"],
        "congestion":   util_data["congestion"],
        "drc":          drc_data["violations"],
        "clocks":       clock_data["clocks"],
        "features":     features,
    }
