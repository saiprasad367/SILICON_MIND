import { motion } from "framer-motion";
import { Target, TrendingUp } from "lucide-react";
import { SectionCard } from "./SectionCard";


const prioStyles = {
  high: { dot: "bg-error", chip: "bg-error/10 text-error" },
  medium: { dot: "bg-warning", chip: "bg-warning/10 text-warning" },
  low: { dot: "bg-info", chip: "bg-info/10 text-info" },
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const RecommendationsSection = ({ data }: { data: any[] }) => (
  <SectionCard
    title="Recommendations"
    subtitle="Ranked by impact & effort"
    icon={<Target className="h-4 w-4 text-primary" />}
    delay={0.1}
  >
    <div className="space-y-2">
      {data.map((r, i) => {
        const s = prioStyles[r.priority];
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -8 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: 0.05 * i }}
            className="group relative rounded-xl border border-border bg-surface-elevated p-3.5 transition-all hover:border-primary/30 hover:shadow-elev-md"
          >
            <div className="flex items-start gap-3">
              <span className={`mt-1.5 h-2 w-2 shrink-0 rounded-full ${s.dot}`} />
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-center gap-2">
                  <p className="text-sm font-semibold">{r.title}</p>
                  <span className={`rounded-full px-1.5 py-0.5 text-[10px] font-semibold uppercase ${s.chip}`}>{r.priority}</span>
                </div>
                <p className="mt-1.5 text-xs text-muted-foreground">{r.reason}</p>
                <div className="mt-2 flex flex-wrap items-center gap-3 text-[11px]">
                  <span className="flex items-center gap-1 text-success">
                    <TrendingUp className="h-3 w-3" /> <span className="font-mono">{r.impact}</span>
                  </span>
                  <span className="text-muted-foreground">Effort: <span className="font-medium text-foreground">{r.effort}</span></span>
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}
    </div>
  </SectionCard>
);
