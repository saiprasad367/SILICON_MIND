"""
featureengineer.py - Feature transformation utilities.
Uses real dataset column names from fpga_dataset_200k.csv.
"""
import numpy as np
from typing import Dict, Any, List


def power_vs_performance_curve(features: Dict[str, Any]) -> List[Dict]:
    """Generate power-vs-performance sweep data for the analytics chart."""
    base_power  = float(features.get("total_power_w", 4.82) or 4.82)
    target_freq = float(features.get("target_frequency_mhz") or
                        features.get("target_freq_mhz", 300) or 300)
    freqs = [100, 150, 200, 250, 300, 350, 400]
    result = []
    for f in freqs:
        ratio = f / target_freq if target_freq > 0 else 1
        power = round(base_power * (ratio ** 1.3), 2)
        perf  = round(min(100, 32 + 54 * (f / 400) ** 0.7), 1)
        result.append({"freq": f, "power": power, "perf": perf})
    return result


def infer_clocks(timing_data: Dict) -> List[Dict]:
    """Return a synthesized clock domain list from timing analysis."""
    target = timing_data.get("target_freq", 300) or 300
    return [
        {"name": "clk_pl_main",  "freq": target, "domain": "PL",     "status": "active"},
        {"name": "clk_axi_100",  "freq": 100,    "domain": "PL",     "status": "active"},
        {"name": "clk_ddr_533",  "freq": 533,    "domain": "PS-DDR", "status": "active"},
    ]
