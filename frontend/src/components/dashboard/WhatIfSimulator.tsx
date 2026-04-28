import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { FlaskConical } from "lucide-react";
import { SectionCard } from "./SectionCard";
import { Slider } from "@/components/ui/slider";
import { runWhatIf, type AnalysisResponse } from "@/lib/api";

interface Props {
  baseFeatures?: AnalysisResponse | null;
}

export const WhatIfSimulator = ({ baseFeatures }: Props) => {
  const [freq, setFreq] = useState(300);
  const [pipeline, setPipeline] = useState(2);
  const [mode, setMode] = useState<"perf" | "balanced" | "power">("balanced");
  const [sim, setSim] = useState({
    projected_fmax_mhz: 268,
    predicted_slack_ns: -0.124,
    predicted_power_w: 4.82,
    lut_delta_pct: 0,
    timing_status: "FAIL" as "PASS" | "FAIL",
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const timeout = setTimeout(async () => {
      setLoading(true);
      try {
        const result = await runWhatIf({ clock: freq, pipeline, mode });
        setSim(result as any);
      } catch {
        // Analytic fallback (no backend)
        const modeBoost = mode === "perf" ? 1.15 : mode === "power" ? 0.85 : 1;
        const pipeBoost = 1 + (pipeline - 1) * 0.06;
        const projectedFmax = Math.round(268 * (1 + (pipeline - 1) * 0.08) * (mode === "perf" ? 1.05 : 1));
        const power = +((freq / 300) * 4.82 * modeBoost).toFixed(2);
        const slack = +((projectedFmax - freq) / projectedFmax * 1.2).toFixed(3);
        const utilDelta = Math.round((pipeline - 1) * 4.5 * pipeBoost);
        setSim({
          projected_fmax_mhz: projectedFmax,
          predicted_slack_ns: slack,
          predicted_power_w: power,
          lut_delta_pct: utilDelta,
          timing_status: slack >= 0 ? "PASS" : "FAIL",
        });
      } finally {
        setLoading(false);
      }
    }, 400); // debounce
    return () => clearTimeout(timeout);
  }, [freq, pipeline, mode]);

  const status = sim.timing_status;

  return (
    <SectionCard
      title="What-If Simulator"
      subtitle="Predict outcomes before re-synthesis"
      icon={<FlaskConical className="h-4 w-4 text-ai" />}
      delay={0.1}
    >
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="space-y-5">
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Target frequency</label>
              <span className="font-mono text-sm font-semibold">{freq} MHz</span>
            </div>
            <Slider value={[freq]} min={100} max={500} step={10} onValueChange={(v) => setFreq(v[0])} />
          </div>
          <div>
            <div className="mb-2 flex items-baseline justify-between">
              <label className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Pipeline depth</label>
              <span className="font-mono text-sm font-semibold">{pipeline} stage{pipeline > 1 ? "s" : ""}</span>
            </div>
            <Slider value={[pipeline]} min={1} max={6} step={1} onValueChange={(v) => setPipeline(v[0])} />
          </div>
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Optimization mode</p>
            <div className="grid grid-cols-3 gap-1.5 rounded-lg border border-border bg-surface p-1">
              {(["perf", "balanced", "power"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={`rounded-md px-2 py-1.5 text-xs font-medium capitalize transition-colors ${
                    mode === m ? "bg-card shadow-elev-sm" : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  {m}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-3">
          {[
            { label: "Projected Fmax", val: `${sim.projected_fmax_mhz}`, unit: "MHz", color: "text-foreground" },
            { label: "Slack",  val: sim.predicted_slack_ns.toFixed(3), unit: "ns",  color: status === "PASS" ? "text-success" : "text-error" },
            { label: "Power",  val: sim.predicted_power_w.toFixed(2),   unit: "W",   color: "text-warning" },
            { label: "LUT delta", val: (sim.lut_delta_pct >= 0 ? "+" : "") + sim.lut_delta_pct, unit: "%", color: "text-info" },
          ].map((s) => (
            <motion.div
              key={s.label}
              layout
              className={`rounded-xl border border-border bg-surface p-4 ${loading ? "opacity-50" : ""} transition-opacity`}
            >
              <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{s.label}</p>
              <motion.p
                key={s.val}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                className={`font-mono text-2xl font-semibold ${s.color}`}
              >
                {s.val}<span className="ml-1 text-xs text-muted-foreground">{s.unit}</span>
              </motion.p>
            </motion.div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
};
