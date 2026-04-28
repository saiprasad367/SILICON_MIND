import { motion } from "framer-motion";
import { Layers } from "lucide-react";
import { SectionCard } from "./SectionCard";


const colorFor = (pct: number) => {
  if (pct > 80) return "bg-error";
  if (pct > 60) return "bg-warning";
  if (pct < 10) return "bg-info";
  return "bg-success";
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const UtilizationSection = ({ data, congestion }: { data: any[]; congestion: any }) => {
  // Build 8x6 heatmap
  const cols = 8, rows = 6;
  const grid = Array.from({ length: rows * cols }, (_, i) => {
    const x = i % cols, y = Math.floor(i / cols);
    const dCenter = Math.hypot(x - 4, y - 2);
    const noise = Math.sin(i * 1.7) * 0.4 + Math.cos(i * 0.9) * 0.3;
    const base = Math.max(0, Math.min(1, (1 - dCenter / 5) * 0.7 + noise * 0.3 + 0.2));
    // Inject hotspots
    let v = base;
    if (x === 5 && y === 2) v = 0.95;
    if (x === 4 && y === 2) v = 0.78;
    if (x === 3 && y === 3) v = 0.62;
    return v;
  });

  return (
    <SectionCard
      title="Resource Utilization"
      subtitle="Logic, memory & I/O usage with congestion heatmap"
      icon={<Layers className="h-4 w-4 text-primary" />}
      delay={0.15}
    >
      <div className="grid gap-6 lg:grid-cols-[1fr_300px]">
        <div className="space-y-2">
          {data.map((r, i) => (
            <motion.div
              key={r.name}
              initial={{ opacity: 0, y: 4 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.04 * i }}
              className="rounded-lg border border-border bg-surface p-3"
            >
              <div className="mb-1.5 flex items-baseline justify-between">
                <span className="font-mono text-xs font-semibold">{r.name}</span>
                <span className="font-mono text-[11px] text-muted-foreground">
                  {r.used.toLocaleString()} / {r.total.toLocaleString()}
                </span>
              </div>
              <div className="flex items-center gap-3">
                <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-muted">
                  <motion.div
                    className={`h-full ${colorFor(r.pct)}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${Math.max(2, r.pct)}%` }}
                    transition={{ duration: 0.9, delay: 0.04 * i + 0.1 }}
                  />
                </div>
                <span className="w-12 text-right font-mono text-xs font-semibold">{r.pct.toFixed(1)}%</span>
              </div>
            </motion.div>
          ))}
        </div>

        <div>
          <div className="mb-2 flex items-baseline justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Floorplan heatmap</p>
            <span className="font-mono text-[10px] text-muted-foreground">{congestion.overall}% avg</span>
          </div>
          <div className="rounded-xl border border-border bg-foreground/[0.03] p-2">
            <div className="grid gap-0.5" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
              {grid.map((v, i) => {
                const r = Math.round(v * 255);
                const g = Math.round((1 - v) * 180);
                return (
                  <motion.div
                    key={i}
                    initial={{ opacity: 0, scale: 0.6 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: i * 0.008, duration: 0.3 }}
                    className="aspect-square rounded-[3px]"
                    style={{ background: `rgba(${r}, ${g}, 80, ${0.25 + v * 0.7})` }}
                    title={`${(v * 100).toFixed(0)}%`}
                  />
                );
              })}
            </div>
          </div>
          <div className="mt-2 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>Cool</span>
            <div className="h-1.5 flex-1 mx-2 rounded-full" style={{ background: "linear-gradient(90deg, rgba(80,180,80,0.3), rgba(255,180,80,0.7), rgba(255,80,80,0.9))" }} />
            <span>Hot</span>
          </div>
          <div className="mt-3 space-y-1">
            {congestion.hotspots.map((h) => (
              <div key={h.region} className="flex items-center justify-between rounded-lg bg-surface px-2.5 py-1.5">
                <span className="font-mono text-[11px]">{h.region}</span>
                <span className={`font-mono text-[11px] font-semibold ${h.level > 70 ? "text-error" : h.level > 50 ? "text-warning" : "text-success"}`}>
                  {h.level}%
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </SectionCard>
  );
};
