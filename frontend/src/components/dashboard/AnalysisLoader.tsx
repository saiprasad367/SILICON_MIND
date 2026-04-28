import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Loader2, Sparkles, Cpu, Zap, FileSearch } from "lucide-react";

const PHASES = [
  { icon: FileSearch, label: "Parsing Vivado reports", detail: "Extracting timing, power & utilization data" },
  { icon: Cpu, label: "Building design graph", detail: "Mapping module hierarchy & critical paths" },
  { icon: Sparkles, label: "AI analysis in progress", detail: "Detecting bottlenecks & optimization opportunities" },
  { icon: Zap, label: "Finalizing recommendations", detail: "Ranking fixes by impact & effort" },
];

export const AnalysisLoader = ({ onDone }: { onDone: () => void }) => {
  const [phase, setPhase] = useState(0);
  const [progress, setProgress] = useState(0);

  useEffect(() => {
    const totalMs = 4200;
    const start = performance.now();
    let raf = 0;
    const tick = (t: number) => {
      const p = Math.min(1, (t - start) / totalMs);
      setProgress(p * 100);
      setPhase(Math.min(PHASES.length - 1, Math.floor(p * PHASES.length)));
      if (p < 1) raf = requestAnimationFrame(tick);
      else setTimeout(onDone, 250);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [onDone]);

  return (
    <section className="relative min-h-[70vh]">
      <div className="absolute inset-0 bg-mesh" />
      <div className="relative mx-auto flex min-h-[70vh] max-w-2xl flex-col items-center justify-center px-6 py-16">
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="mb-8 flex h-20 w-20 items-center justify-center rounded-3xl bg-gradient-ai shadow-ai-glow"
        >
          <motion.div animate={{ rotate: 360 }} transition={{ duration: 2, repeat: Infinity, ease: "linear" }}>
            <Loader2 className="h-9 w-9 text-white" />
          </motion.div>
        </motion.div>

        <h2 className="mb-2 text-2xl font-semibold tracking-tight">Analyzing your design</h2>
        <p className="mb-8 text-sm text-muted-foreground">This usually takes a few seconds…</p>

        <div className="mb-8 h-1.5 w-full max-w-md overflow-hidden rounded-full bg-muted">
          <motion.div
            className="h-full bg-gradient-ai"
            style={{ width: `${progress}%` }}
            transition={{ duration: 0.2 }}
          />
        </div>

        <div className="w-full max-w-md space-y-2">
          {PHASES.map((p, i) => {
            const Icon = p.icon;
            const active = i === phase;
            const done = i < phase;
            return (
              <motion.div
                key={i}
                animate={{ opacity: done || active ? 1 : 0.4 }}
                className={`flex items-center gap-3 rounded-xl border p-3 transition-colors ${
                  active ? "border-primary/40 bg-primary/5" : "border-border bg-surface-elevated"
                }`}
              >
                <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${
                  done ? "bg-success/10 text-success" : active ? "bg-gradient-ai text-white" : "bg-muted text-muted-foreground"
                }`}>
                  {active ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Icon className="h-4 w-4" />
                  )}
                </div>
                <div className="flex-1">
                  <p className="text-sm font-medium">{p.label}</p>
                  <AnimatePresence>
                    {active && (
                      <motion.p
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="text-xs text-muted-foreground"
                      >
                        {p.detail}
                      </motion.p>
                    )}
                  </AnimatePresence>
                </div>
              </motion.div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
