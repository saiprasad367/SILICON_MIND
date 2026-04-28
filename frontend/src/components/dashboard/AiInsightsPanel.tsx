import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Sparkles, AlertTriangle, Lightbulb, TrendingUp } from "lucide-react";
import { SectionCard } from "./SectionCard";


const iconFor = {
  issue: AlertTriangle,
  opportunity: Lightbulb,
  warning: TrendingUp,
};
const colorFor = {
  issue: "text-error",
  opportunity: "text-ai",
  warning: "text-warning",
};

const TypewriterLine = ({ text, delay = 0 }: { text: string; delay?: number }) => {
  const [shown, setShown] = useState("");
  useEffect(() => {
    let i = 0;
    const startT = setTimeout(() => {
      const id = setInterval(() => {
        i++;
        setShown(text.slice(0, i));
        if (i >= text.length) clearInterval(id);
      }, 12);
      return () => clearInterval(id);
    }, delay);
    return () => clearTimeout(startT);
  }, [text, delay]);
  return <span>{shown}{shown.length < text.length && <span className="ml-0.5 inline-block h-3 w-[2px] -mb-0.5 bg-ai animate-blink" />}</span>;
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const AiInsightsPanel = ({ data }: { data: any[] }) => (
  <SectionCard
    title="AI Insights"
    subtitle="Live analysis from the SiliconMind engine"
    icon={
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-gradient-ai shadow-ai-glow">
        <Sparkles className="h-4 w-4 text-white" />
      </div>
    }
    badge={<span className="rounded-full bg-ai/10 px-2 py-0.5 text-[10px] font-semibold text-ai">v2.4</span>}
    delay={0.05}
    className="overflow-hidden"
  >
    <div className="space-y-3">
      {data.map((insight, i) => {
        const Icon = iconFor[insight.type];
        return (
          <motion.div
            key={i}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.5 + 0.2 }}
            className="flex gap-3 rounded-xl border border-border bg-surface p-3.5"
          >
            <div className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-background ${colorFor[insight.type]}`}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <p className="text-sm font-semibold leading-tight">{insight.title}</p>
              <p className="mt-1 text-xs leading-relaxed text-muted-foreground">
                <TypewriterLine text={insight.text} delay={i * 500 + 400} />
              </p>
            </div>
          </motion.div>
        );
      })}
    </div>
  </SectionCard>
);
