import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronRight, Zap, Flame } from "lucide-react";
import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts";
import { SectionCard } from "./SectionCard";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";


// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const PowerSection = ({ data }: { data: any }) => {
  const [open, setOpen] = useState<string | null>("video_pipeline_top");
  const total = useAnimatedNumber(data.total, 1200, 2);
  const dynamic = useAnimatedNumber(data.dynamic, 1200, 2);
  const staticP = useAnimatedNumber(data.static, 1200, 2);
  const dynPct = (data.dynamic / data.total) * 100;

  return (
    <SectionCard
      title="Power Intelligence"
      subtitle="Module-level breakdown & efficiency analysis"
      icon={<Zap className="h-4 w-4 text-warning" />}
      delay={0.05}
    >
      <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
        <div>
          <div className="relative h-[200px]">
            <ResponsiveContainer>
              <PieChart>
                <Pie data={data.breakdown} dataKey="value" innerRadius={62} outerRadius={88} paddingAngle={2} stroke="none">
                  {data.breakdown.map((e, i) => <Cell key={i} fill={e.color} />)}
                </Pie>
              </PieChart>
            </ResponsiveContainer>
            <div className="pointer-events-none absolute inset-0 flex flex-col items-center justify-center">
              <span className="font-mono text-3xl font-semibold tracking-tight">{total.toFixed(2)}</span>
              <span className="text-[10px] font-medium uppercase tracking-widest text-muted-foreground">Watts</span>
            </div>
          </div>
          <div className="mt-4 grid grid-cols-2 gap-2">
            <div className="rounded-lg border border-border bg-surface p-2.5">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Dynamic</p>
              <p className="font-mono text-sm font-semibold">{dynamic.toFixed(2)}W</p>
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-muted">
                <motion.div className="h-full bg-warning" initial={{ width: 0 }} animate={{ width: `${dynPct}%` }} transition={{ duration: 1 }} />
              </div>
            </div>
            <div className="rounded-lg border border-border bg-surface p-2.5">
              <p className="text-[10px] uppercase tracking-wider text-muted-foreground">Static</p>
              <p className="font-mono text-sm font-semibold">{staticP.toFixed(2)}W</p>
              <div className="mt-1 h-1 overflow-hidden rounded-full bg-muted">
                <motion.div className="h-full bg-info" initial={{ width: 0 }} animate={{ width: `${100 - dynPct}%` }} transition={{ duration: 1 }} />
              </div>
            </div>
          </div>
        </div>

        <div>
          <div className="mb-3 flex items-center justify-between">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">Module hierarchy</p>
            <p className="text-xs text-muted-foreground">Click to expand</p>
          </div>
          <div className="space-y-1.5">
            {data.modules.map((m, i) => {
              const expanded = open === m.name;
              const pct = (m.power / data.total) * 100;
              return (
                <motion.div
                  key={m.name}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.05 * i }}
                  className="overflow-hidden rounded-lg border border-border"
                >
                  <button
                    onClick={() => setOpen(expanded ? null : m.name)}
                    className="flex w-full items-center gap-3 bg-surface-elevated px-3 py-2.5 text-left transition-colors hover:bg-surface"
                  >
                    <ChevronRight className={`h-3.5 w-3.5 text-muted-foreground transition-transform ${expanded ? "rotate-90" : ""}`} />
                    {m.hot && <Flame className="h-3.5 w-3.5 text-warning" />}
                    <span className="flex-1 font-mono text-xs">{m.name}</span>
                    <div className="h-1 w-24 overflow-hidden rounded-full bg-muted">
                      <motion.div
                        className={`h-full ${m.hot ? "bg-warning" : "bg-primary"}`}
                        initial={{ width: 0 }}
                        animate={{ width: `${pct}%` }}
                        transition={{ duration: 0.8, delay: 0.1 * i }}
                      />
                    </div>
                    <span className="w-16 text-right font-mono text-xs font-semibold">{m.power.toFixed(2)}W</span>
                  </button>
                  <AnimatePresence>
                    {expanded && m.children && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: "auto", opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden bg-surface"
                      >
                        <div className="space-y-1 p-2 pl-9">
                          {m.children.map((c) => (
                            <div key={c.name} className="flex items-center gap-3 rounded px-2 py-1.5">
                              {c.hot && <Flame className="h-3 w-3 text-warning" />}
                              <span className="flex-1 font-mono text-[11px] text-muted-foreground">{c.name}</span>
                              <span className="font-mono text-[11px]">{c.power.toFixed(2)}W</span>
                            </div>
                          ))}
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              );
            })}
          </div>
        </div>
      </div>
    </SectionCard>
  );
};
