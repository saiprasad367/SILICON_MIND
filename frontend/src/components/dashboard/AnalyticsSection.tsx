import { motion } from "framer-motion";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Area, AreaChart } from "recharts";
import { BarChart3 } from "lucide-react";
import { SectionCard } from "./SectionCard";


const tooltipStyle = {
  background: "hsl(var(--card))",
  border: "1px solid hsl(var(--border))",
  borderRadius: 8,
  fontSize: 12,
  fontFamily: "JetBrains Mono, monospace",
  boxShadow: "var(--shadow-md)",
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const AnalyticsSection = ({ data }: { data: any[] }) => (
  <SectionCard
    title="Visual Analytics"
    subtitle="Power vs performance curve"
    icon={<BarChart3 className="h-4 w-4 text-info" />}
    delay={0.15}
  >
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ delay: 0.2, duration: 0.6 }}
      className="h-[260px] w-full"
    >
      <ResponsiveContainer>
        <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id="powerGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--warning))" stopOpacity={0.3} />
              <stop offset="100%" stopColor="hsl(var(--warning))" stopOpacity={0} />
            </linearGradient>
            <linearGradient id="perfGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="hsl(var(--ai))" stopOpacity={0.35} />
              <stop offset="100%" stopColor="hsl(var(--ai))" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" vertical={false} />
          <XAxis dataKey="freq" tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="hsl(var(--muted-foreground))" tickLine={false} />
          <YAxis tick={{ fontSize: 10, fontFamily: "JetBrains Mono" }} stroke="hsl(var(--muted-foreground))" tickLine={false} axisLine={false} />
          <Tooltip contentStyle={tooltipStyle} cursor={{ stroke: "hsl(var(--border))" }} />
          <Area type="monotone" dataKey="power" stroke="hsl(var(--warning))" strokeWidth={2} fill="url(#powerGrad)" name="Power (W)" />
          <Area type="monotone" dataKey="perf" stroke="hsl(var(--ai))" strokeWidth={2} fill="url(#perfGrad)" name="Perf score" />
        </AreaChart>
      </ResponsiveContainer>
    </motion.div>
    <div className="mt-2 flex flex-wrap items-center gap-4 text-[11px]">
      <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-warning" /> Power consumption (W)</span>
      <span className="flex items-center gap-1.5"><span className="h-2 w-2 rounded-full bg-ai" /> Performance index</span>
      <span className="ml-auto text-muted-foreground">Sweet spot: <span className="font-mono font-semibold text-foreground">300 MHz</span></span>
    </div>
  </SectionCard>
);
