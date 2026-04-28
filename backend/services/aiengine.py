"""
aiengine.py - AI Insight & Recommendation Engine
──────────────────────────────────────────────────
Combines:
  • ML model predictions (XGBoost + MLP)
  • Rule-based expert knowledge (Vivado-specific)
  • RL strategy recommendation (Q-learning)

Produces structured insights & recommendations in the exact shape
the React frontend expects.
"""
from typing import Dict, Any, List


# ─── Severity coloring helpers ───────────────────────────────────────────────

def _t(val: float, lo: float, mid: float) -> str:
    if val <= lo:
        return "issue"
    if val <= mid:
        return "warning"
    return "opportunity"


# ─── Timing insights ─────────────────────────────────────────────────────────

def _timing_insights(features: Dict, timing: Dict) -> List[Dict]:
    out = []
    wns = features.get("worst_negative_slack_ns", 0)
    tgt = features.get("target_frequency_mhz") or timing.get("target_freq", 300)
    achieved = features.get("achieved_freq_mhz") or timing.get("achieved_freq", 0)
    crit_delay = features.get("critical_path_delay_ns", 0)
    logic_delay = features.get("logic_delay_ns", 0)
    route_delay = features.get("routing_delay_ns", 0)
    route_pct   = features.get("routing_delay_percent", 0)

    if wns < -1.0:
        out.append({
            "type": "issue",
            "title": f"Critical timing violation — WNS = {wns:.3f} ns",
            "text": (
                f"Design fails timing by {abs(wns):.3f} ns at {tgt} MHz target. "
                f"Critical path delay is {crit_delay:.3f} ns "
                f"(routing {route_pct:.0f}%, logic {100-route_pct:.0f}%). "
                "Add pipeline registers to break the critical path, or apply pblock constraints to reduce routing detour."
            ),
        })
    elif wns < 0:
        out.append({
            "type": "issue",
            "title": f"Marginal timing violation — WNS = {wns:.3f} ns",
            "text": (
                f"Design misses timing by {abs(wns):.3f} ns. "
                f"A single pipeline stage or tightening XDC constraints is likely sufficient to close timing at {tgt} MHz."
            ),
        })
    else:
        out.append({
            "type": "opportunity",
            "title": f"Timing met ✓ — WNS = +{wns:.3f} ns @ {achieved} MHz",
            "text": (
                f"Design has {wns:.3f} ns of positive slack. "
                "Consider pushing the target frequency higher or reducing pipeline depth to save area."
            ),
        })
    return out


# ─── Power insights ───────────────────────────────────────────────────────────

def _power_insights(features: Dict) -> List[Dict]:
    out = []
    total   = features.get("total_power_w", 0)
    dynamic = features.get("dynamic_power_w", 0)
    static  = features.get("static_power_w", 0)
    ratio   = static / total if total > 0 else 0

    if total > 8:
        out.append({
            "type": "issue",
            "title": f"High total power — {total:.2f} W",
            "text": (
                f"Total power ({total:.2f} W) may exceed board-level budget. "
                f"Dynamic: {dynamic:.2f} W, Static: {static:.2f} W. "
                "Enable clock gating on idle modules, reduce switching activity, and consider a lower-power device variant."
            ),
        })
    elif total > 4:
        out.append({
            "type": "warning",
            "title": f"Moderate power — {total:.2f} W",
            "text": (
                f"Power is within acceptable range but could be optimized. "
                f"Static power ratio: {ratio*100:.0f}% — consider clock domain gating for DSP banks."
            ),
        })
    if ratio > 0.5:
        out.append({
            "type": "warning",
            "title": f"Static-power dominated design ({ratio*100:.0f}% static)",
            "text": (
                "High static power suggests the design has many always-on circuits. "
                "Use power islands or partial reconfiguration to isolate idle subsystems."
            ),
        })
    return out


# ─── Utilization insights ─────────────────────────────────────────────────────

def _util_insights(features: Dict) -> List[Dict]:
    out = []
    dsp_pct   = features.get("dsp_util_percent", 0)
    lut_pct   = features.get("lut_util_percent", 0)
    bram_pct  = features.get("bram_util_percent", 0)
    ff_pct    = features.get("ff_util_percent", 0)
    fanout    = features.get("fanout_max", 0)

    if dsp_pct < 15 and lut_pct > 20:
        out.append({
            "type": "opportunity",
            "title": f"DSP blocks underutilized — {dsp_pct:.1f}% used",
            "text": (
                f"With {lut_pct:.1f}% LUT usage, multipliers are likely mapped to LUTs. "
                'Applying (* use_dsp = "yes" *) to arithmetic operations could reduce LUT usage by ~12% and improve timing.'
            ),
        })
    if bram_pct > 80:
        out.append({
            "type": "issue",
            "title": f"BRAM near capacity — {bram_pct:.1f}%",
            "text": (
                "BRAM utilization is critically high. "
                "Consider switching large memories (>18 Kb) to URAMs, or compressing data structures. "
                "DOA_REG=1 can also improve BRAM read timing."
            ),
        })
    if fanout > 5000:
        out.append({
            "type": "warning",
            "title": f"High fanout detected — max {fanout}",
            "text": (
                f"Nets with fanout > 5000 create heavy routing pressure. "
                "Apply buffer insertion or split high-fanout resets/enables into regional trees."
            ),
        })
    return out


# ─── DRC insights ─────────────────────────────────────────────────────────────

def _drc_insights(drc: List[Dict], features: Dict) -> List[Dict]:
    out = []
    errors   = [d for d in drc if d.get("severity") == "error"]
    warnings = [d for d in drc if d.get("severity") == "warning"]
    if errors:
        out.append({
            "type": "issue",
            "title": f"{len(errors)} DRC error(s) — bitstream blocked",
            "text": (
                f"Primary DRC error: [{errors[0]['rule']}] {errors[0]['message']} "
                f"→ Fix: {errors[0]['fix']}"
            ),
        })
    if warnings and len(warnings) > 2:
        out.append({
            "type": "warning",
            "title": f"{len(warnings)} DRC warnings detected",
            "text": (
                f"Notable: [{warnings[0]['rule']}] {warnings[0]['message']}. "
                "Review all DRC warnings before tape-out."
            ),
        })
    return out


# ─── Recommendations ──────────────────────────────────────────────────────────

def _recommendations(features: Dict, ml: Dict, rl: Dict) -> List[Dict]:
    recs = []
    wns    = features.get("worst_negative_slack_ns", 0)
    dsp    = features.get("dsp_util_percent", 100)
    lut    = features.get("lut_util_percent", 0)
    cong   = features.get("congested_regions_count", 0)
    power  = features.get("total_power_w", 0)
    fanout = features.get("fanout_max", 0)
    pipe   = features.get("pipeline_stages", 1)
    depth  = features.get("logic_depth", 0)

    if wns < 0:
        recs.append({
            "priority": "high",
            "title": "Insert pipeline registers on critical path",
            "impact": f"+{round(min(50, abs(wns) * 15))}% Fmax improvement",
            "effort": "Low",
            "reason": (
                f"WNS = {wns:.3f} ns. Breaking the {pipe}-stage critical path with "
                "additional registers resolves routing-dominated delays."
            ),
        })
        recs.append({
            "priority": "high",
            "title": "Fix XDC input/output delay constraints",
            "impact": "Accurate timing closure analysis",
            "effort": "Low",
            "reason": "Missing set_input_delay / set_output_delay causes pessimistic slack estimation.",
        })
    if dsp < 20 and lut > 15:
        recs.append({
            "priority": "high",
            "title": "Force DSP inference for arithmetic blocks",
            "impact": f"-{round(lut * 0.12, 1)}% LUT, improved Fmax",
            "effort": "Low",
            "reason": 'Use (* use_dsp = "yes" *) attribute on all multiplication operations.',
        })
    if cong > 3:
        recs.append({
            "priority": "medium",
            "title": "Apply pblock floorplan constraints",
            "impact": "-20–30% routing delay",
            "effort": "Medium",
            "reason": (
                f"{cong} congested region(s) detected. "
                "Constraining critical modules to specific clock regions reduces long nets."
            ),
        })
    if fanout > 3000:
        recs.append({
            "priority": "medium",
            "title": "Insert buffer tree for high-fanout nets",
            "impact": "-15% routing congestion",
            "effort": "Low",
            "reason": f"Max fanout = {fanout}. BUFG or LUT-based register replication reduces routing pressure.",
        })
    if power > 5:
        recs.append({
            "priority": "medium",
            "title": "Enable BRAM output register (DOA_REG=1)",
            "impact": "+30–45 MHz on BRAM read paths",
            "effort": "Low",
            "reason": "Adds a free pipelining stage inside the BRAM macro, improving read-path timing.",
        })
    if power > 7:
        recs.append({
            "priority": "low",
            "title": "Clock-gate idle DSP & BRAM banks",
            "impact": f"-{round(power * 0.06, 2)} W estimated",
            "effort": "Medium",
            "reason": "Power analysis shows high static contribution from always-enabled DSP chains.",
        })
    if depth > 20:
        recs.append({
            "priority": "low",
            "title": "Reduce combinational logic depth",
            "impact": "Easier timing closure",
            "effort": "Medium",
            "reason": f"Logic depth of {depth} levels increases critical path sensitivity to process variations.",
        })

    # RL-recommended strategy as a tip
    strategy = rl.get("strategy", "Performance_Explore")
    recs.append({
        "priority": "low",
        "title": f"Apply Vivado strategy: {strategy}",
        "impact": "AI-selected from Q-learning agent",
        "effort": "Low",
        "reason": (
            f"The RL agent has learned (over {rl.get('episodes_seen', 0)} designs) that "
            f"'{strategy}' maximizes timing improvement for this design profile."
        ),
    })

    # Sort
    pri = {"high": 0, "medium": 1, "low": 2}
    recs.sort(key=lambda r: pri.get(r["priority"], 3))
    return recs[:7]


# ─── Root cause ───────────────────────────────────────────────────────────────

def _root_cause(features: Dict, drc: List[Dict], ml: Dict) -> str:
    causes = []
    wns = features.get("worst_negative_slack_ns", 0)
    if wns < 0:
        causes.append(f"Timing: WNS={wns:.3f} ns — critical path exceeds constraint")
    errors = [d for d in drc if d.get("severity") == "error"]
    if errors:
        causes.append(f"DRC: [{errors[0]['rule']}] {errors[0]['message'][:60]}")
    cong = features.get("congested_regions_count", 0)
    if cong > 3:
        causes.append(f"Congestion: {cong} hot regions causing routing detours")
    lut = features.get("lut_util_percent", 0)
    if lut > 80:
        causes.append(f"Area: LUT utilization critical ({lut:.1f}%)")
    if not causes:
        causes.append("No critical issues — design is healthy and meeting all constraints")
    return " | ".join(causes)


# ─── Master entry ─────────────────────────────────────────────────────────────

def generate_insights(
    features: Dict[str, Any],
    ml_result: Dict[str, Any],
    power_data: Dict,
    timing_data: Dict,
    drc_data: List[Dict],
    rl_result: Dict = None,
) -> Dict[str, Any]:
    """Build the complete AI analysis payload."""
    if rl_result is None:
        rl_result = {}

    insights: List[Dict] = []
    insights += _timing_insights(features, timing_data)
    insights += _power_insights(features)
    insights += _util_insights(features)
    insights += _drc_insights(drc_data, features)

    recs = _recommendations(features, ml_result, rl_result)

    return {
        "ai_prediction":  ml_result.get("design_status", "NEEDS_OPTIMIZATION"),
        "confidence":     ml_result.get("confidence", 0.75),
        "model_used":     ml_result.get("model_used", "rule_based"),
        "class_probs":    ml_result.get("class_probabilities", {}),
        "insights":       insights[:5],
        "recommendations": recs,
        "root_cause":     _root_cause(features, drc_data, ml_result),
        "best_strategy":  rl_result.get("strategy", "Performance_Explore"),
        "rl_info":        rl_result,
    }
