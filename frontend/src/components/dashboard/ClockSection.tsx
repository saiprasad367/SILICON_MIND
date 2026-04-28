import { motion } from "framer-motion";
import { Activity, Network } from "lucide-react";
import { SectionCard } from "./SectionCard";


// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const ClockSection = ({ clocks, cdc }: { clocks: any[]; cdc: number }) => (
  <SectionCard
    title="Clocks & CDC"
    subtitle={`${clocks.length} domains · ${cdc} CDC issues`}
    icon={<Activity className="h-4 w-4 text-info" />}
    delay={0.1}
  >
    <div className="space-y-2">
      {clocks.map((c, i) => (
        <motion.div
          key={c.name}
          initial={{ opacity: 0, x: -8 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 * i }}
          className="flex items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2.5"
        >
          <div className="relative flex h-6 w-6 items-center justify-center">
            <span className="absolute inset-0 animate-ping rounded-full bg-success/40" style={{ animationDuration: `${1 + i * 0.3}s` }} />
            <Network className="h-3.5 w-3.5 text-success" />
          </div>
          <span className="flex-1 font-mono text-xs">{c.name}</span>
          <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-[10px]">{c.domain}</span>
          <span className="w-20 text-right font-mono text-xs font-semibold">{c.freq} MHz</span>
        </motion.div>
      ))}
    </div>
    {cdc > 0 && (
      <div className="mt-4 rounded-lg border border-warning/30 bg-warning/5 p-3 text-xs">
        <p className="font-semibold text-warning">⚠ {cdc} CDC violations detected</p>
        <p className="mt-1 text-muted-foreground">Suggest inserting 2-FF synchronizers on cross-domain signals between <span className="font-mono">clk_axi_100</span> and <span className="font-mono">clk_pl_300</span>.</p>
      </div>
    )}
  </SectionCard>
);
