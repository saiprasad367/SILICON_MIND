import { motion } from "framer-motion";
import { Cpu, Activity, CheckCircle2, AlertTriangle } from "lucide-react";
import { useAnimatedNumber } from "@/hooks/useAnimatedNumber";
import type { AnalysisResponse } from "@/lib/api";

const ScoreRing = ({ value, color, label, size = 56 }: { value: number; color: string; label: string; size?: number }) => {
  const v = useAnimatedNumber(value, 1400);
  const r = (size - 6) / 2;
  const c = 2 * Math.PI * r;
  const off = c - (v / 100) * c;
  return (
    <div className="flex items-center gap-3">
      <div className="relative" style={{ width: size, height: size }}>
        <svg width={size} height={size} className="-rotate-90">
          <circle cx={size / 2} cy={size / 2} r={r} stroke="hsl(var(--muted))" strokeWidth="4" fill="none" />
          <motion.circle
            cx={size / 2} cy={size / 2} r={r}
            stroke={color} strokeWidth="4" fill="none" strokeLinecap="round"
            strokeDasharray={c} strokeDashoffset={off}
            transition={{ duration: 1 }}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center font-mono text-sm font-semibold">
          {Math.round(v)}
        </div>
      </div>
      <div>
        <p className="text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{label}</p>
        <p className="text-xs text-foreground">
          {value >= 80 ? "Excellent" : value >= 60 ? "Good" : value >= 40 ? "Needs work" : "Critical"}
        </p>
      </div>
    </div>
  );
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const StatusBar = ({ data }: { data: AnalysisResponse & { timing: any; drc: any[] } }) => {
  const healthColor = data.design.healthScore >= 80 ? "hsl(var(--success))" : data.design.healthScore >= 60 ? "hsl(var(--warning))" : "hsl(var(--error))";
  const bsColor = data.design.bitstreamReadiness >= 80 ? "hsl(var(--success))" : "hsl(var(--warning))";
  const timingPass = data.timing.status === "PASS";

  return (
    <motion.div
      initial={{ opacity: 0, y: -8 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky top-14 z-40 border-b border-border bg-background/85 backdrop-blur-xl"
    >
      <div className="mx-auto flex max-w-[1600px] flex-wrap items-center gap-x-6 gap-y-3 px-6 py-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10">
            <Cpu className="h-4 w-4 text-primary" />
          </div>
          <div>
            <p className="font-mono text-sm font-semibold leading-tight">{data.design.name}</p>
            <p className="font-mono text-[10px] text-muted-foreground">{data.design.device}</p>
          </div>
        </div>

        <div className="ml-auto flex flex-wrap items-center gap-5">
          <div className={`flex items-center gap-2 rounded-full border px-3 py-1.5 ${timingPass ? "border-success/30 bg-success/5" : "border-error/30 bg-error/5"}`}>
            {timingPass ? <CheckCircle2 className="h-3.5 w-3.5 text-success" /> : <AlertTriangle className="h-3.5 w-3.5 text-error" />}
            <span className="text-xs font-semibold">Timing {data.timing.status}</span>
            <span className="font-mono text-xs text-muted-foreground">{data.timing.slack.toFixed(3)}ns</span>
          </div>

          <div className="flex items-center gap-1.5 text-xs">
            <Activity className="h-3.5 w-3.5 text-muted-foreground" />
            <span className="text-muted-foreground">DRC</span>
            <span className="font-mono font-semibold">{data.drc.length}</span>
          </div>

          <ScoreRing value={data.design.healthScore} color={healthColor} label="Health" />
          <ScoreRing value={data.design.bitstreamReadiness} color={bsColor} label="Bitstream" />
        </div>
      </div>
    </motion.div>
  );
};
