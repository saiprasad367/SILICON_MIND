import { motion } from "framer-motion";
import { Clock, AlertTriangle, CheckCircle2, ArrowRight } from "lucide-react";
import { SectionCard } from "./SectionCard";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";


// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const TimingSection = ({ data }: { data: any }) => {
  const slack = useAnimatedNumber(Math.abs(data.slack), 1200, 3);
  const fmax = useAnimatedNumber(data.achievedFreq, 1400);
  const cp = useAnimatedNumber(data.criticalPath.delay, 1400, 3);
  const pass = data.status === "PASS";
  const logicPct = (data.criticalPath.logicDelay / data.criticalPath.delay) * 100;

  return (
    <SectionCard
      title="Timing Analysis"
      subtitle="Critical path & slack diagnostics"
      icon={<Clock className="h-4 w-4 text-info" />}
      badge={
        <span className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${pass ? "bg-success/10 text-success" : "bg-error/10 text-error"}`}>
          {data.status}
        </span>
      }
      delay={0.1}
    >
      <div className="grid gap-3 sm:grid-cols-3">
        <div className={`rounded-xl border p-4 ${pass ? "border-success/30 bg-success/5" : "border-error/30 bg-error/5"}`}>
          <div className="mb-1 flex items-center gap-1.5">
            {pass ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : <AlertTriangle className="h-3.5 w-3.5 text-error" />}
            <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Worst slack</p>
          </div>
          <p className={`font-mono text-2xl font-semibold ${pass ? "text-success" : "text-error"}`}>
            {data.slack < 0 ? "-" : ""}{slack.toFixed(3)}<span className="ml-1 text-xs text-muted-foreground">ns</span>
          </p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Achieved Fmax</p>
          <p className="font-mono text-2xl font-semibold">{fmax}<span className="ml-1 text-xs text-muted-foreground">MHz</span></p>
          <p className="mt-1 text-[10px] text-muted-foreground">Target {data.targetFreq} MHz</p>
        </div>
        <div className="rounded-xl border border-border bg-surface p-4">
          <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">Critical path</p>
          <p className="font-mono text-2xl font-semibold">{cp.toFixed(3)}<span className="ml-1 text-xs text-muted-foreground">ns</span></p>
          <p className="mt-1 text-[10px] text-muted-foreground">{data.criticalPath.stages.length} stages</p>
        </div>
      </div>

      <div className="mt-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Path composition</p>
        <div className="flex h-2 overflow-hidden rounded-full">
          <motion.div initial={{ width: 0 }} animate={{ width: `${logicPct}%` }} transition={{ duration: 1 }} className="bg-info" />
          <motion.div initial={{ width: 0 }} animate={{ width: `${100 - logicPct}%` }} transition={{ duration: 1, delay: 0.1 }} className="bg-warning" />
        </div>
        <div className="mt-1.5 flex justify-between text-[11px] text-muted-foreground">
          <span><span className="font-mono">{data.criticalPath.logicDelay}ns</span> logic</span>
          <span><span className="font-mono">{data.criticalPath.routingDelay}ns</span> routing</span>
        </div>
      </div>

      <div className="mt-5">
        <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">Critical path trace</p>
        <div className="space-y-1">
          {data.criticalPath.stages.map((s, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.05 * i + 0.2 }}
              className={`flex items-center gap-3 rounded-lg border px-3 py-2 ${s.bottleneck ? "border-error/30 bg-error/5" : "border-border bg-surface"}`}
            >
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-background font-mono text-[10px] font-semibold">{i + 1}</span>
              <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{s.type}</span>
              <span className="flex-1 font-mono text-xs">{s.name}</span>
              {s.bottleneck && <span className="rounded-full bg-error/10 px-1.5 py-0.5 text-[10px] font-semibold text-error">bottleneck</span>}
              <span className="font-mono text-xs font-semibold">{s.delay.toFixed(2)}ns</span>
              {i < data.criticalPath.stages.length - 1 && <ArrowRight className="hidden h-3 w-3 text-muted-foreground sm:block" />}
            </motion.div>
          ))}
        </div>
      </div>
    </SectionCard>
  );
};
